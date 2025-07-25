import os

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon, QImage, QPainter, QColor, QTransform

from app.data.resources.map_sprites import MapSprite
from app.data.resources.resources import RESOURCES

from app.utilities.data import Data
from app.data.database.database import DB
from app.data.resources.default_palettes import default_palettes

from app.extensions.custom_gui import DeletionTab, DeletionDialog
from app.editor.settings import MainSettingsController
from app.editor.base_database_gui import ResourceCollectionModel
import app.editor.utilities as editor_utilities
from app.utilities import str_utils
from app.utilities.typing import NID

import logging

def get_basic_icon(pixmap: QPixmap, num: int, active: bool = False, team: NID = 'player') -> QPixmap:
    if active:
        one_frame = pixmap.copy(num*64 + 16, 96 + 16, 32, 32)
    else:
        one_frame = pixmap.copy(num*64 + 16, 0 + 16, 32, 32)
    # pixmap = pixmap.copy(16, 16, 32, 32)
    one_frame = one_frame.toImage()
    one_frame = color_shift_team(one_frame, team)
    pixmap = QPixmap.fromImage(one_frame)
    return pixmap

def get_map_sprite_icon(nid, num=0, current=False, team: NID = 'player', variant=None):
    res = None
    if variant and nid:
        res = RESOURCES.map_sprites.get(nid + variant)
    if nid and (not variant or not res):
        res = RESOURCES.map_sprites.get(nid)
    if not res:
        return None
    if not res.standing_pixmap:
        res.standing_pixmap = QPixmap(res.stand_full_path)
    pixmap = res.standing_pixmap
    pixmap = get_basic_icon(pixmap, num, current, team)
    return pixmap

def color_shift_team(im: QImage, team: NID) -> QImage:
    team_obj = DB.teams.get(team)
    if team_obj and team_obj.map_sprite_palette:
        map_sprite_palette = RESOURCES.combat_palettes.get(team_obj.map_sprite_palette)
        if map_sprite_palette:
            conversion_dict = {a: b for a, b in zip(default_palettes['map_sprite_blue'], map_sprite_palette.get_colors())}
            color_transform = editor_utilities.rgb_convert(conversion_dict)
            im = editor_utilities.color_convert(im, color_transform)
        else:
            logging.error("Map Sprite conversion unable to locate combat palette with nid: %s" % team_obj.map_sprite_palette)
    # Must convert colorkey last, or else color conversion doesn't work correctly
    im = editor_utilities.convert_colorkey(im)
    return im

def gray_shift_team(im: QImage) -> QImage:
    map_sprite_palette = RESOURCES.combat_palettes.get('map_sprite_wait')
    if map_sprite_palette:
        colors = map_sprite_palette.get_colors()
    else:
        logging.error("Map Sprite conversion unable to locate combat palette with nid: map_sprite_wait")
        colors = default_palettes['map_sprite_wait']
    conversion_dict = {a: b for a, b in zip(default_palettes['map_sprite_blue'], colors)}
    color_transform = editor_utilities.rgb_convert(conversion_dict)
    im = editor_utilities.color_convert(im, color_transform)
        
    # Must convert colorkey last, or else color conversion doesn't work correctly
    im = editor_utilities.convert_colorkey(im)
    return im

def palette_swap(pixmap: QPixmap, palette_nid: NID, with_colorkey=True) -> QImage:
    palette = RESOURCES.combat_palettes.get(palette_nid)
    if not palette:
        return pixmap.toImage()
    im = pixmap.toImage()
    conv_dict = {a: b for a, b in zip(default_palettes['map_sprite_blue'], palette.get_colors())}
    color_transform = editor_utilities.rgb_convert(conv_dict)
    im = editor_utilities.color_convert(im, color_transform)
    if with_colorkey:
        im = editor_utilities.convert_colorkey(im)
    return im

def check_delete(nid: NID, window) -> bool:
    # Check to see what is using me?
    affected_classes = [klass for klass in DB.classes if nid == klass.map_sprite_nid]
    if affected_classes:
        from app.editor.class_editor.class_model import ClassModel
        model = ClassModel
        msg = "Deleting Map Sprite <b>%s</b> would affect these classes." % nid
        deletion_tab = DeletionTab(affected_classes, model, msg, "Classes")
        return DeletionDialog.inform([deletion_tab], window)
    return True

def on_delete(nid: NID):
    # What uses map sprites
    # Classes
    for klass in DB.classes:
        if klass.map_sprite_nid == nid:
            klass.map_sprite_nid = None

def on_nid_changed(old_nid, new_nid):
    # What uses map sprites
    # Classes
    for klass in DB.classes:
        if klass.map_sprite_nid == old_nid:
            klass.map_sprite_nid = new_nid

def create_new(window):
    settings = MainSettingsController()
    starting_path = settings.get_last_open_path()
    nid = None
    stand_full_path, move_full_path = None, None
    standing_pix, moving_pix = None, None
    lion_throne_mode = True
    fn, sok = QFileDialog.getOpenFileName(window, "Choose Standing Map Sprite", starting_path)
    first_fn = fn
    if sok:
        if fn.endswith('.png'):
            nid = os.path.split(fn)[-1][:-4]
            standing_pix = QPixmap(fn)
            nid = str_utils.get_next_name(nid, [d.nid for d in RESOURCES.map_sprites])
            stand_full_path = fn
            if standing_pix.width() == 192 and standing_pix.height() == 144:
                lion_throne_mode = True
            elif 16 <= standing_pix.width() <= 64 and 48 <= standing_pix.height() <= 144 and standing_pix.height() % 3 == 0:  # Try for GBA mode
                lion_throne_mode = False
            else:
                QMessageBox.critical(window, "Error", "Standing Map Sprite is not correct size for Legacy import (192x144 px) or GBA import (16x48 px)")
                return
        else:
            QMessageBox.critical(window, "Error", "Image must be PNG format")
            return
        parent_dir = os.path.split(fn)[0]
        settings.set_last_open_path(parent_dir)
    else:
        return
    starting_path = settings.get_last_open_path()
    fn, mok = QFileDialog.getOpenFileName(window, "Choose Moving Map Sprite (Choose Standing Sprite Again If No Moving Sprite)", starting_path)
    gba_overhang = False
    gba_no_move = False
    if mok:
        if fn.endswith('.png'):
            moving_pix = QPixmap(fn)
            move_full_path = fn
            if lion_throne_mode:
                if moving_pix.width() == 192 and moving_pix.height() == 160:
                    pass
                else:
                    QMessageBox.critical(window, "Error", "Moving Map Sprite is not correct size for Legacy import (192x160 px)")
                    return
            else:
                if fn == first_fn:
                    gba_no_move = True
                elif moving_pix.width() == 32 and moving_pix.height() == 32 * 15:
                    pass
                elif moving_pix.width() == 32 and moving_pix.height() == 32 * 15 + 8:
                    gba_overhang = True
                else:
                    QMessageBox.critical(window, "Error", "Moving Map Sprite is not correct size for GBA import (either 32x480 or 32x488 px)")
                    return

        else:
            QMessageBox.critical(window, "Error", "Image must be png format")
            return
    else:
        return
    if sok and mok and nid:
        if lion_throne_mode:
            new_map_sprite = window.catalog_type.datatype(nid, stand_full_path, move_full_path)
        else:
            current_proj = settings.get_current_project()
            if current_proj:
                standing_pix, moving_pix = import_gba_map_sprite(standing_pix, moving_pix, gba_overhang, gba_no_move)
                stand_full_path = os.path.join(current_proj, 'resources', 'map_sprites', nid + '-stand.png')
                move_full_path = os.path.join(current_proj, 'resources', 'map_sprites', nid + '-move.png')
                standing_pix.save(stand_full_path)
                moving_pix.save(move_full_path)
                new_map_sprite = window.catalog_type.datatype(nid, stand_full_path, move_full_path)
            else:
                QMessageBox.critical(window, "Error", "Cannot load GBA map sprites without having saved the project")
                return
        window.data.append(new_map_sprite)
        parent_dir = os.path.split(fn)[0]
        settings.set_last_open_path(parent_dir)
        return new_map_sprite

def import_gba_map_sprite(standing_pix: QPixmap, moving_pix: QPixmap, gba_overhang:bool=False, gba_no_move:bool=False) -> tuple[QPixmap, QPixmap]:
    s_width = standing_pix.width()
    s_height = standing_pix.height()
    new_s = QPixmap(192, 144)
    new_s.fill(QColor(editor_utilities.qCOLORKEY))
    new_m = QPixmap(192, 160)
    new_m.fill(QColor(editor_utilities.qCOLORKEY))

    passive1 = standing_pix.copy(0, 0, s_width, s_height//3)
    passive2 = standing_pix.copy(0, s_height//3, s_width, s_height//3)
    passive3 = standing_pix.copy(0, 2*s_height//3, s_width, s_height//3)
        
    if not gba_no_move:
        left1 = moving_pix.copy(0, 0, 32, 32)
        left2 = moving_pix.copy(0, 32, 32, 32)
        left3 = moving_pix.copy(0, 32*2, 32, 32)
        left4 = moving_pix.copy(0, 32*3, 32, 32)

        down1 = moving_pix.copy(0, 32*4, 32, 32)
        down2 = moving_pix.copy(0, 32*5, 32, 32)
        down3 = moving_pix.copy(0, 32*6, 32, 32)
        down4 = moving_pix.copy(0, 32*7, 32, 32)

        up1 = moving_pix.copy(0, 32*8, 32, 32)
        up2 = moving_pix.copy(0, 32*9, 32, 32)
        up3 = moving_pix.copy(0, 32*10, 32, 32)
        up4 = moving_pix.copy(0, 32*11, 32, 32)

        focus1 = moving_pix.copy(0, 32*12, 32, 32)
        focus2 = moving_pix.copy(0, 32*13, 32, 32)
        focus3 = moving_pix.copy(0, 32*14, 32, 32)
    else:
        frames = [QPixmap(32, 32) for _ in range(12)]
        for frame in frames:
            frame.fill(QColor(editor_utilities.qCOLORKEY))
            
        left1, left2, left3, left4, down1, down2, down3, down4, up1, up2, up3, up4 = frames
        
        # We still want reactivity for corpses (i.e. when viewing the info_menu or hovering on map) so we just copy the standing frames here
        focus1 = standing_pix.copy(0, 0, s_width, s_height//3)
        focus2 = standing_pix.copy(0, s_height//3, s_width, s_height//3)
        focus3 = standing_pix.copy(0, 2*s_height//3, s_width, s_height//3)

    if gba_overhang:
        overhang = moving_pix.copy(0, 32*15, 32, 8)

    if s_height//3 == 16:
        new_height = 24
    else:
        new_height = 8
    if s_width == 16:
        new_width = 24
    else:
        new_width = 16

    painter = QPainter()
    
    # Standing pixmap
    painter.begin(new_s)
    painter.drawPixmap(new_width, new_height, passive1)
    painter.drawPixmap(new_width + 64, new_height, passive2)
    painter.drawPixmap(new_width + 128, new_height, passive3)
    
    # If a corpse, the focus row is essentially just the standing row shifted downward - so we need to mirror base width & height
    focus1_pt = (new_width if gba_no_move else 16), (new_height if gba_no_move else 8) + 96
    focus2_pt = (new_width if gba_no_move else 16) + 64, (new_height if gba_no_move else 8) + 96
    focus3_pt = (new_width if gba_no_move else 16) + 128, (new_height if gba_no_move else 8) + 96
    
    painter.drawPixmap(*focus1_pt, focus1)
    painter.drawPixmap(*focus2_pt, focus2)
    painter.drawPixmap(*focus3_pt, focus3)

    if gba_overhang:
        painter.drawPixmap(16 + 128, 8 + 96 - 8, overhang)  # right above focus3

    painter.end()
    # Moving pixmap
    painter.begin(new_m)
    painter.drawPixmap(8, 8, down1)
    painter.drawPixmap(8 + 48, 8, down2)
    painter.drawPixmap(8 + 48 * 2, 8, down3)
    painter.drawPixmap(8 + 48 * 3, 8, down4)
    painter.drawPixmap(8, 48, left1)
    painter.drawPixmap(8 + 48, 48, left2)
    painter.drawPixmap(8 + 48 * 2, 48, left3)
    painter.drawPixmap(8 + 48 * 3, 48, left4)
    # Right direction pixmaps
    painter.drawPixmap(8, 88, left1.transformed(QTransform().scale(-1, 1)))
    painter.drawPixmap(8 + 48, 88, left2.transformed(QTransform().scale(-1, 1)))
    painter.drawPixmap(8 + 48 * 2, 88, left3.transformed(QTransform().scale(-1, 1)))
    painter.drawPixmap(8 + 48 * 3, 88, left4.transformed(QTransform().scale(-1, 1)))
    painter.drawPixmap(8, 128, up1)
    painter.drawPixmap(8 + 48, 128, up2)
    painter.drawPixmap(8 + 48 * 2, 128, up3)
    painter.drawPixmap(8 + 48 * 3, 128, up4)
    painter.end()

    return new_s, new_m

class MapSpriteModel(ResourceCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            map_sprite = self._data[index.row()]
            text = map_sprite.nid
            return text
        elif role == Qt.DecorationRole:
            map_sprite = self._data[index.row()]
            if not map_sprite.standing_pixmap:
                map_sprite.standing_pixmap = QPixmap(map_sprite.stand_full_path)
            if not map_sprite.moving_pixmap:
                map_sprite.moving_pixmap = QPixmap(map_sprite.move_full_path)
            pixmap = map_sprite.standing_pixmap
            # num = TIMER.passive_counter.count
            num = 0
            pixmap = get_basic_icon(pixmap, num, index == self.window.view.currentIndex())
            if pixmap:
                return QIcon(pixmap)
        return None

    def delete(self, idx):
        # check to make sure nothing else is using me!!!
        res = self._data[idx]
        nid = res.nid
        ok = check_delete(nid)
        if ok:
            on_delete(nid)
        else:
            return
        super().delete(idx)