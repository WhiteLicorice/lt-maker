import os

from typing import Optional

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox

from app.data.database.database import DB
from app.editor import timer
from app.data.database.klass import ClassCatalog
from app.editor.new_editor_tab import NewEditorTab
from app.editor.data_editor import SingleDatabaseEditor

from app.editor.settings import MainSettingsController
from app.editor.class_editor import class_model, class_import, new_class_properties
from app.extensions.custom_gui import DeletionTab, DeletionDialog
from app.utilities.typing import NID

class NewClassDatabase(NewEditorTab):
    catalog_type = ClassCatalog
    properties_type = new_class_properties.NewClassProperties

    @property
    def data(self):
        return self._db.classes

    @classmethod
    def edit(cls, parent=None):
        window = SingleDatabaseEditor(cls, parent)
        window.exec_()

    def get_icon(self, class_nid: NID) -> Optional[QIcon]:
        if not self.data.get(class_nid):
            return None
        num = timer.get_timer().passive_counter.count
        pix = class_model.get_map_sprite_icon(self.data.get(class_nid), num)
        if pix:
            return QIcon(pix.scaled(32, 32))
        return None

    def create_new(self, nid):
        if self.data.get(nid):
            QMessageBox.warning(self, 'Warning', 'ID %s already in use' % nid)
            return False
        new_class = self.catalog_type.datatype(nid, nid, '')
        self.data.append(new_class)
        return True

    def tick(self):
        self.on_icon_change()

    def import_data(self):
        settings = MainSettingsController()
        starting_path = settings.get_last_open_path()
        fn, ok = QFileDialog.getOpenFileName(self, _("Import classes from class_info.xml"), starting_path, "Class Info XML (class_info.xml);;All Files(*)")
        if ok and fn:
            parent_dir = os.path.split(fn)[0]
            settings.set_last_open_path(parent_dir)
            new_units = class_import.get_from_xml(parent_dir, fn)
            for unit in new_units:
                self._data.append(unit)
            self.reset()

    def _on_nid_changed(self, old_nid: NID, new_nid: NID):
        class_model.on_nid_changed(old_nid, new_nid)

    def _on_delete(self, nid: NID) -> bool:
        swap, ok = class_model.check_delete(nid, self)
        if ok:
            if swap is not None:
                class_model.on_nid_changed(nid, swap.nid)
            return True
        else:
            return False

# Testing
# Run "python -m app.editor.class_editor.class_tab" from main directory
if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    from app import dark_theme
    d = dark_theme.QDarkBGPalette()
    d.set_app(app)
    from app.data.resources.resources import RESOURCES
    RESOURCES.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
    from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
    DB.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
    window = SingleDatabaseEditor(ClassDatabase)
    # MEME
    window.setStyleSheet("QDialog {background-image:url(icons/bg.png)};")
    window.show()
    app.exec_()
