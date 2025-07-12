from PyQt5.QtGui import QPixmap, QIcon, QPainter, QImage
from PyQt5.QtCore import Qt

from app.data.database.database import DB
from app.data.database import supports
import app.editor.utilities as editor_utilities

from app.editor.portrait_editor import portrait_model
from app.editor.base_database_gui import DragDropCollectionModel

def get_pixmap(support_pair):
    unit1_chibi, unit2_chibi = None, None
    if support_pair.unit1 and support_pair.unit1 in DB.units:
        unit1 = DB.units.get(support_pair.unit1)
        unit1_chibi = portrait_model.get_chibi(unit1.portrait_nid)
    if support_pair.unit2 and support_pair.unit2 in DB.units:
        unit2 = DB.units.get(support_pair.unit2)
        unit2_chibi = portrait_model.get_chibi(unit2.portrait_nid)

    if unit1_chibi and unit2_chibi:
        combined_chibi = QImage(64, 32, QImage.Format_RGB32)
        combined_chibi.fill(editor_utilities.qCOLORKEY)
        painter = QPainter()
        painter.begin(combined_chibi)
        painter.drawImage(0, 0, unit1_chibi.toImage())
        painter.drawImage(32, 0, unit2_chibi.toImage())
        painter.end()
        combined_chibi = QPixmap.fromImage(editor_utilities.convert_colorkey(combined_chibi))
        return combined_chibi
    return None

class SupportPairModel(DragDropCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            support_pair = self._data[index.row()]
            text = support_pair.nid
            return text
        elif role == Qt.DecorationRole:
            support_pair = self._data[index.row()]
            pixmap = get_pixmap(support_pair)
            if pixmap:
                return QIcon(pixmap)
        return None

    def delete(self, idx):
        # Delete watchers
        # None needed -- Nothing else in editor/data uses support pairs
        super().delete(idx)

    def on_nid_changed(self, old_value, new_value):
        pass

    def create_new(self):
        # Try to create a unique support pair
        for unit1 in DB.units:
            for unit2 in DB.units:
                new_support_pair = supports.SupportPair(
                    unit1.nid, unit2.nid, False, supports.SupportRankRequirementList())
                if new_support_pair.nid in DB.support_pairs:
                    continue
                else:
                    DB.support_pairs.append(new_support_pair)
                    return new_support_pair
        # If no unique support pair can be created, just fail silently
        return None

    def duplicate(self, idx):
        obj = self._data[idx]
        other_units = [o.unit2 for o in self._data if o.unit1 == obj.unit1]
        new_unit = None
        for unit in DB.units.keys():
            if unit in other_units:
                continue
            else:
                new_unit = unit
                break
        if not new_unit:
            return False
        serialized_obj = obj.save()
        new_obj = self._data.datatype.restore(serialized_obj)
        new_obj.unit2 = new_unit
        self.layoutAboutToBeChanged.emit()
        self._data.insert(idx + 1, new_obj)
        self.layoutChanged.emit()
        new_index = self.index(idx + 1, 0)
        return new_index
