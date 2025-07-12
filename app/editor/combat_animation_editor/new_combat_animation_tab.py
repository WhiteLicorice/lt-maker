from typing import Optional

from PyQt5.QtGui import QIcon, QBrush, QColor
from PyQt5.QtWidgets import QDialog, QWidget

from app.data.resources.resources import RESOURCES
from app.data.resources.combat_anims import CombatCatalog, CombatEffectCatalog

from app.editor.new_editor_tab import NewEditorTab
from app.editor.combat_animation_editor import combat_animation_model, combat_effect_model
from app.editor.item_editor import  item_model
from app.editor.combat_animation_editor.new_combat_animation_properties import NewCombatAnimProperties
from app.editor.combat_animation_editor.new_combat_effect_properties import NewCombatEffectProperties
from app.editor.combat_animation_editor.new_palette_tab import NewPaletteDatabase
from app.editor.data_editor import SingleResourceEditor, NewMultiResourceEditor
from app.utilities.typing import NID

class NewSimpleCombatAnimProperties(QWidget):
    title = "Combat Animation"

    def __init__(self, parent, current=None):
        QWidget.__init__(self, parent)
        self.window = parent
        self.current = current

    def set_current(self, current):
        if not current:
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            self.current = current

class NewCombatAnimDatabase(NewEditorTab):
    catalog_type = CombatCatalog
    properties_type = NewCombatAnimProperties
    allow_rename = True

    @classmethod
    def edit(cls, parent=None):
        window = SingleResourceEditor(NewCombatAnimDatabase, ['combat_anims'], parent)
        window.exec_()

    @property
    def data(self):
        return self._res.combat_anims

    def get_icon(self, combat_anim_nid: NID) -> Optional[QIcon]:
        if not self.data.get(combat_anim_nid):
            return None
        pix = combat_animation_model.get_combat_anim_icon(combat_anim_nid)
        if pix:
            return QIcon(pix)
        return None

    def _on_nid_changed(self, old_nid: NID, new_nid: NID):
        combat_animation_model.on_nid_changed(old_nid, new_nid)

    def _on_delete(self, nid: NID) -> bool:
        ok = combat_animation_model.check_delete(nid, self)
        if ok:
            combat_animation_model.on_delete(nid)
            return True
        else:
            return False

class NewSimpleCombatAnimTab(NewCombatAnimDatabase):
    properties_type = NewSimpleCombatAnimProperties

    @classmethod
    def edit(cls, parent=None):
        window = SingleResourceEditor(NewSimpleCombatAnimTab, ['combat_anims'], parent)
        window.exec_()

class NewCombatEffectDatabase(NewEditorTab):
    catalog_type = CombatEffectCatalog
    properties_type = NewCombatEffectProperties
    allow_rename = True

    @classmethod
    def edit(cls, parent=None):
        window = SingleResourceEditor(NewCombatEffectDatabase, ['combat_effects'], parent)
        window.exec_()

    @property
    def data(self):
        return self._res.combat_effects

    def get_icon(self, combat_effect_nid: NID) -> Optional[QIcon]:
        if not self._db.items.get(combat_effect_nid):
            return None
        pix = item_model.get_pixmap(self._db.items.get(combat_effect_nid))
        if pix:
            return QIcon(pix.scaled(32, 32))
        return None

    def get_foreground(self, unit_nid: NID) -> Optional[QBrush]:
        effect = self.data.get(unit_nid)
        if effect and not effect.palettes:
            return QBrush(QColor("cyan"))
        return None

    def _on_nid_changed(self, old_nid: NID, new_nid: NID):
        combat_effect_model.on_nid_changed(old_nid, new_nid)

    def _on_delete(self, nid: NID) -> bool:
        ok = combat_effect_model.check_delete(nid, self)
        if ok:
            combat_effect_model.on_delete(nid)
            return True
        else:
            return False

def get_full_editor() -> NewMultiResourceEditor:
    editor = NewMultiResourceEditor((NewCombatAnimDatabase, NewCombatEffectDatabase, NewPaletteDatabase),
                                 ('combat_anims', 'combat_effects', 'combat_palettes'))
    editor.setWindowTitle("Combat Animation Editor")
    return editor

def get_animations() -> tuple:
    window = SingleResourceEditor(NewSimpleCombatAnimTab, ['combat_anims'])
    result = window.exec_()
    if result == QDialog.Accepted:
        selected_combat_anim = window.tab.right_frame.current
        return selected_combat_anim, True
    else:
        return None, False
