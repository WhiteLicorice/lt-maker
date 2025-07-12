from PyQt5.QtCore import Qt
from PyQt5.QtGui import qRgb, QIcon, QBrush, QColor, QImage

from app.utilities.typing import NID

from app.data.database.database import DB
from app.data.resources.resources import RESOURCES
from app.data.resources import combat_anims

from app.editor.base_database_gui import ResourceCollectionModel
from app.editor.item_editor import item_model

from app.extensions.custom_gui import DeletionTab, DeletionDialog

from app.utilities import str_utils

def check_delete(nid: NID, window):
    # Check to see what is using me?
    affected_items = [item for item in DB.items if item.nid == nid]
    affected_anims = []
    affected_effects = []
    for combat_anim in RESOURCES.combat_anims:
        for weapon_anim in combat_anim.weapon_anims:
            for pose in weapon_anim.poses:
                for command in pose.timeline:
                    if command.has_effect() and command.value[0] == nid and not combat_anim in affected_anims:
                        affected_anims.append(combat_anim)
    for effect_anim in RESOURCES.combat_effects:
        for pose in effect_anim.poses:
            for command in pose.timeline:
                if command.has_effect() and command.value[0] == nid and not effect_anim in affected_effects:
                    affected_effects.append(effect_anim)

    deletion_tabs = []
    if affected_items:
        from app.editor.item_editor.item_model import ItemModel
        model = ItemModel
        msg = "Deleting Combat Effect <b>%s</b> would affect these items." % nid
        deletion_tabs.append(DeletionTab(affected_items, model, msg, "Items"))
    if affected_anims:
        from app.editor.combat_animation_editor.combat_animation_model import CombatAnimModel
        model = CombatAnimModel
        msg = "Deleting Combat Effect <b>%s</b> would affect these Combat Animations" % nid
        deletion_tabs.append(DeletionTab(affected_anims, model, msg, "Combat Animations"))
    if affected_effects:
        from app.editor.combat_animation_editor.combat_effect_model import CombatEffectModel
        model = CombatEffectModel
        msg = "Deleting Combat Effect <b>%s</b> would affect these Combat Effects" % nid
        deletion_tabs.append(DeletionTab(affected_effects, model, msg, "Combat Effects"))

    if deletion_tabs:
        ok = DeletionDialog.inform(deletion_tabs, window)
        return ok
    return True

def on_delete(nid: NID):
    # What uses combat effects
    # Combat Anims
    for combat_anim in RESOURCES.combat_anims:
        for weapon_anim in combat_anim.weapon_anims:
            for pose in weapon_anim.poses:
                for command in pose.timeline:
                    if command.has_effect() and command.value[0] == nid:
                        command.value = (None,) + tuple(command.value[1:])
    # Combat Effects
    for effect_anim in RESOURCES.combat_effects:
        for pose in effect_anim.poses:
            for command in pose.timeline:
                if command.has_effect() and command.value[0] == nid:
                    command.value = (None,) + tuple(command.value[1:])

def on_nid_changed(old_nid, new_nid):
    for combat_anim in RESOURCES.combat_anims:
        for weapon_anim in combat_anim.weapon_anims:
            for pose in weapon_anim.poses:
                for command in pose.timeline:
                    if command.has_effect() and command.value[0] == old_nid:
                        command.value = (new_nid,) + tuple(command.value[1:])
    for effect_anim in RESOURCES.combat_effects:
        for pose in effect_anim.poses:
            for command in pose.timeline:
                if command.has_effect() and command.value[0] == old_nid:
                    command.value = (new_nid,) + tuple(command.value[1:])

class CombatEffectModel(ResourceCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            animation = self._data[index.row()]
            text = animation.nid
            return text
        elif role == Qt.DecorationRole:
            animation = self._data[index.row()]
            text = animation.nid
            item = DB.items.get(text)
            if item:
                pix = item_model.get_pixmap(item)
                if pix:
                    pix = pix.scaled(16, 16)
                    return QIcon(pix)
            return None
        elif role == Qt.ForegroundRole:
            animation = self._data[index.row()]
            if not animation.palettes:
                return QBrush(QColor("cyan"))
        return None

    def create_new(self):
        nid = str_utils.get_next_name('New Combat Effect', self._data.keys())
        new_anim = combat_anims.EffectAnimation(nid)
        self._data.append(new_anim)
        return new_anim
    