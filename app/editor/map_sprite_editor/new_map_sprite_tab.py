from typing import (Optional)

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QMessageBox

from app.data.resources.resources import RESOURCES

from app.data.resources.map_sprites import MapSpriteCatalog
from app.editor.new_editor_tab import NewEditorTab
from app.editor.data_editor import SingleResourceEditor

from app.editor.map_sprite_editor import map_sprite_model, new_map_sprite_properties
from app.utilities.typing import NID

class NewMapSpriteDatabase(NewEditorTab):
    catalog_type = MapSpriteCatalog
    properties_type = new_map_sprite_properties.NewMapSpriteProperties
    allow_rename = True

    @classmethod
    def edit(cls, parent=None):
        window = SingleResourceEditor(NewMapSpriteDatabase, ['map_sprites'], parent)
        window.exec_()

    @property
    def data(self):
        return self._res.map_sprites

    def get_icon(self, map_sprite_nid: NID) -> Optional[QIcon]:
        if not self.data.get(map_sprite_nid):
            return None
        pix = map_sprite_model.get_map_sprite_icon(map_sprite_nid)
        if pix:
            return QIcon(pix.scaled(32, 32))
        return None

    def create_new(self, nid):
        if self.data.get(nid):
            QMessageBox.warning(self, 'Warning', 'ID %s already in use' % nid)
            return False
        new_map_sprite = map_sprite_model.create_new(self)
        if new_map_sprite:
            self.reset()
        
        return False

    def _on_nid_changed(self, old_nid: NID, new_nid: NID):
        map_sprite_model.on_nid_changed(old_nid, new_nid)

    def _on_delete(self, nid: NID) -> bool:
        ok = map_sprite_model.check_delete(nid, self)
        if ok:
            map_sprite_model.on_delete(nid)
            return True
        else:
            return False

def get():
    window = SingleResourceEditor(NewMapSpriteDatabase, ['map_sprites'])
    result = window.exec_()
    if result == QDialog.Accepted:
        selected_map_sprite = window.tab.right_frame.current
        return selected_map_sprite, True
    else:
        return None, False

# Testing
# Run "python -m app.editor.map_sprite_editor.new_map_sprite_tab" from main directory
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    RESOURCES.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
    window = SingleResourceEditor(NewMapSpriteDatabase, ['map_sprites'])
    window.show()
    app.exec_()