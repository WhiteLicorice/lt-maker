from typing import Optional

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QMessageBox

from app.data.resources.resources import RESOURCES
from app.data.resources.combat_palettes import PaletteCatalog

from app.editor.data_editor import SingleResourceEditor
from app.editor.new_editor_tab import NewEditorTab

from app.editor.combat_animation_editor import new_palette_properties, palette_model
from app.utilities.typing import NID

class NewPaletteDatabase(NewEditorTab):
    catalog_type = PaletteCatalog
    properties_type = new_palette_properties.NewPaletteProperties
    allow_rename = True

    def create_new(self, nid):
        if self.data.get(nid):
            QMessageBox.warning(self, 'Warning', 'ID %s already in use' % nid)
            return False
        new_class = self.catalog_type.datatype(nid)
        self.data.append(new_class)
        return True

    @classmethod
    def edit(cls, parent=None):
        window = SingleResourceEditor(NewPaletteDatabase, ['combat_palettes'], parent)
        window.exec_()

    @property
    def data(self):
        return self._res.combat_palettes

    def get_icon(self, palette_nid: NID) -> Optional[QIcon]:
        if not self.data.get(palette_nid):
            return None
        palette = self.data.get(palette_nid)
        pix = palette_model.get_palette_pixmap(palette)
        if pix:
            return QIcon(pix)
        return None

    def _on_nid_changed(self, old_nid: NID, new_nid: NID):
        palette_model.on_nid_changed(old_nid, new_nid)

    def _on_delete(self, nid: NID) -> bool:
        swap, ok = palette_model.check_delete(nid, self)
        if ok:
            if swap is not None:
                palette_model.on_nid_changed(nid, swap.nid)
            return True
        else:
            return False

def get():
    window = SingleResourceEditor(NewPaletteDatabase, ['combat_palettes'])
    result = window.exec_()
    if result == QDialog.Accepted:
        selected_palette = window.tab.right_frame.current
        return selected_palette, True
    else:
        return None, False

# Testing
# Run "python -m app.editor.combat_animation_editor.new_palette_tab" from main directory
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    from app.editor.combat_animation_editor.new_combat_animation_properties import populate_anim_pixmaps
    app = QApplication(sys.argv)
    from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
    RESOURCES.load('sacred_stones.ltproj', CURRENT_SERIALIZATION_VERSION)
    for anim in RESOURCES.combat_anims:
        populate_anim_pixmaps(anim)
    window = SingleResourceEditor(NewPaletteDatabase, ['combat_palettes'])
    window.show()
    app.exec_()
