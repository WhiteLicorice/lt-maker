from typing import (Optional)

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QMessageBox

from app.data.resources.resources import RESOURCES

from app.data.resources.portraits import PortraitCatalog
from app.extensions.custom_gui import ResourceListView
from app.editor.data_editor import SingleResourceEditor
from app.editor.base_database_gui import DatabaseTab
from app.editor.new_editor_tab import NewEditorTab

from app.editor.portrait_editor import portrait_model, new_portrait_properties
from app.utilities.typing import NID

from app.editor import timer

class NewPortraitDatabase(NewEditorTab):
    catalog_type = PortraitCatalog
    properties_type = new_portrait_properties.NewPortraitProperties
    allow_rename = True

    @classmethod
    def edit(cls, parent=None):
        window = SingleResourceEditor(NewPortraitDatabase, ['portraits'], parent)
        window.exec_()

    @property
    def data(self):
        return self._res.portraits

    def get_icon(self, portrait_nid: NID) -> Optional[QIcon]:
        if not self.data.get(portrait_nid):
            return None
        pix = portrait_model.get_chibi(portrait_nid)
        if pix:
            return QIcon(pix.scaled(32, 32))
        return None

    def create_new(self, nid):
        if self.data.get(nid):
            QMessageBox.warning(self, 'Warning', 'ID %s already in use' % nid)
            return False
        portrait = portrait_model.create_new(self)
        if portrait:
            self.reset()
        
        return False

    def _on_nid_changed(self, old_nid: NID, new_nid: NID):
        portrait_model.on_nid_changed(old_nid, new_nid)

    def _on_delete(self, nid: NID) -> bool:
        ok = portrait_model.check_delete(nid, self)
        if ok:
            portrait_model.on_delete(nid)
            return True
        else:
            return False

def get():
    timer.get_timer().start_for_editor()
    window = SingleResourceEditor(NewPortraitDatabase, ['portraits'])
    result = window.exec_()
    timer.get_timer().stop_for_editor()
    if result == QDialog.Accepted:
        selected_portrait = window.tab.right_frame.current
        return selected_portrait, True
    else:
        return None, False

# Testing
# Run "python -m app.editor.portrait_editor.new_portrait_tab" from main directory
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
    RESOURCES.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
    window = SingleResourceEditor(NewPortraitDatabase, ['portraits'])
    window.show()
    app.exec_()