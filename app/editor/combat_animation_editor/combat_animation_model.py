from PyQt5.QtCore import Qt
from PyQt5.QtGui import qRgb, QPixmap, QIcon, QBrush, QColor, QImage

from app.utilities.typing import NID

from app.utilities.data import Data
from app.data.database.database import DB
from app.data.resources.resources import RESOURCES
from app.data.resources import combat_anims

from app.editor.base_database_gui import ResourceCollectionModel

from app.extensions.custom_gui import DeletionTab, DeletionDialog

from app.utilities import str_utils
from app.editor import utilities as editor_utilities

def palette_swap(pixmap: QPixmap, palette_nid: NID, with_colorkey=True) -> QImage:
    palette = RESOURCES.combat_palettes.get(palette_nid)
    if not palette:
        return pixmap.toImage()
    im = pixmap.toImage()
    conv_dict = editor_utilities.get_coord_conversion(palette)
    # print("palette_swap: %s" % editor_utilities.human_readable(conv_dict))
    im = editor_utilities.color_convert(im, conv_dict)
    if with_colorkey:
        im = editor_utilities.convert_colorkey(im)
    return im

def get_combat_anim_icon(combat_anim_nid: str):
    combat_anim = RESOURCES.combat_anims.get(combat_anim_nid)
    if not combat_anim or not combat_anim.weapon_anims:
        return None
    weapon_anim = combat_anim.weapon_anims.get('Unarmed', combat_anim.weapon_anims[0])
    pose = weapon_anim.poses.get('Stand')
    if not pose:
        return None

    # Get palette and apply palette
    if not combat_anim.palettes:
        return None
    palette_names = [palette[0] for palette in combat_anim.palettes]
    if 'GenericBlue' in palette_names:
        idx = palette_names.index('GenericBlue')
        palette_name, palette_nid = combat_anim.palettes[idx]
    else:
        palette_name, palette_nid = combat_anim.palettes[0]
    palette = RESOURCES.combat_palettes.get(palette_nid)
    if not palette:
        return None
    convert_dict = editor_utilities.get_coord_conversion(palette)

    # Get first command that displays a frame
    for command in pose.timeline:
        if command.nid in ('frame', 'over_frame', 'under_frame', 'dual_frame'):
            frame_nid = command.value[1]
            frame = weapon_anim.frames.get(frame_nid)
            if not frame:
                continue
            if not frame.pixmap:
                frame.pixmap = QPixmap(weapon_anim.full_path).copy(*frame.rect)
            pixmap = frame.pixmap
            im = pixmap.toImage()
            im = editor_utilities.color_convert(im, convert_dict)
            im = editor_utilities.convert_colorkey(im)
            pixmap = QPixmap.fromImage(im)
            return pixmap
    return None

def check_delete(nid: NID, window):
    # Check to see what is using me?
    affected_classes = [klass for klass in DB.classes if klass.combat_anim_nid == nid]

    if affected_classes:
        from app.editor.class_editor.class_model import ClassModel
        model = ClassModel
        msg = "Deleting Combat Animation <b>%s</b> would affect these classes" % nid
        deletion_tab = DeletionTab(affected_classes, model, msg, "Classes")
        return DeletionDialog.inform([deletion_tab], window)
    return True

def on_delete(nid: NID):
    # What uses map sprites
    # Classes
    for klass in DB.classes:
        if klass.combat_anim_nid == nid:
            klass.combat_anim_nid = None

def on_nid_changed(old_nid, new_nid):
    for klass in DB.classes:
        if klass.combat_anim_nid == old_nid:
            klass.combat_anim_nid = new_nid

class CombatAnimModel(ResourceCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            animation = self._data[index.row()]
            text = animation.nid
            return text
        elif role == Qt.DecorationRole:
            animation = self._data[index.row()]
            nid = animation.nid
            pix = get_combat_anim_icon(nid)
            if pix:
                return QIcon(pix)
        return None

    def create_new(self):
        nid = str_utils.get_next_name('New Combat Anim', self._data.keys())
        new_anim = combat_anims.CombatAnimation(nid)
        self._data.append(new_anim)
        return new_anim
    