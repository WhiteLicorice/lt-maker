from typing import Type
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, pyqtSignal

from app import dark_theme

from app.data.resources.resources import RESOURCES
from app.editor.map_sprite_editor import map_sprite_tab, map_sprite_model

import app.editor.utilities as editor_utilities

from app.utilities.enums import Orientation
from app.utilities.typing import NID

class PushableIcon16(QPushButton):
    sourceChanged = pyqtSignal(str, int, int)
    width, height = 16, 16
    display_width = 64
    database = RESOURCES.icons16

    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self._nid = None
        self.x, self.y = 0, 0

        self.setMinimumHeight(self.display_width)
        self.setMaximumHeight(self.display_width)
        self.setMinimumWidth(self.display_width)
        self.setMaximumWidth(self.display_width)
        self.resize(self.display_width, self.display_width)
        self.setStyleSheet("QPushButton {qproperty-iconSize: %dpx;}" % (self.display_width))
        self.pressed.connect(self.onIconSourcePicker)

    def render(self):
        if self._nid:
            res = self.database.get(self._nid)
            if not res:
                return
            if not res.pixmap:
                res.pixmap = QPixmap(res.full_path)
            if res.pixmap.width() > 0 and res.pixmap.height() > 0:
                pic = res.pixmap.copy(self.x*self.width, self.y*self.height, self.width, self.height)
                pic = QPixmap.fromImage(editor_utilities.convert_colorkey(pic.toImage()))
                pic = pic.scaled(self.display_width, self.display_width * self.height // self.width)
                pic = QIcon(pic)
                self.setIcon(pic)
        else:
            self.setIcon(QIcon())

    def change_icon(self, nid, icon_index):
        self._nid = nid
        self.x = icon_index[0]
        self.y = icon_index[1]
        self.render()

    def onIconSourcePicker(self):
        from app.editor.icon_editor import icon_tab
        res, ok = icon_tab.get(self.width, self._nid)
        if res and ok:
            self.change_icon(res.nid, res.icon_index)
            self.sourceChanged.emit(self._nid, self.x, self.y)

class PushableIcon32(PushableIcon16):
    width, height = 32, 32
    database = RESOURCES.icons32

class PushableIcon80(PushableIcon16):
    width, height = 80, 72
    display_width = 80
    database = RESOURCES.icons80

class ItemIcon16(QWidget):
    sourceChanged = pyqtSignal(str)
    width, height = 16, 16
    child_icon = PushableIcon16

    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent

        hbox = QHBoxLayout()
        self.setLayout(hbox)
        hbox.setContentsMargins(0, 0, 0, 0)

        self.icon = self.child_icon(self)
        hbox.addWidget(self.icon, Qt.AlignCenter)

        self.icon.sourceChanged.connect(self.on_icon_changed)

    def set_current(self, nid, icon_index):
        self.icon.change_icon(nid, icon_index)

    def on_icon_changed(self, nid, x, y):
        if self.window.current:
            self.window.current.icon_nid = nid
            self.window.current.icon_index = (x, y)
            self.window.window.update_list()

class ItemIcon32(ItemIcon16):
    width, height = 32, 32
    child_icon = PushableIcon32

class ItemIcon80(ItemIcon16):
    width, height = 80, 72
    child_icon = PushableIcon80

class UnitPortrait(QPushButton):
    sourceChanged = pyqtSignal(str)
    width, height = 96, 80
    database = RESOURCES.portraits

    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self._nid = None

        self.setMinimumHeight(self.height)
        self.setMaximumHeight(self.height)
        self.setMinimumWidth(self.width)
        self.setMaximumWidth(self.width)
        self.resize(self.width, self.height)
        self.setStyleSheet("QPushButton {qproperty-iconSize: %dpx %dpx;}" % (self.width, self.height))
        self.pressed.connect(self.onIconSourcePicker)

    def render(self):
        if self._nid:
            res = self.database.get(self._nid)
            if not res:
                self.setIcon(QIcon())
                return
            if not res.pixmap:
                res.pixmap = QPixmap(res.full_path)
            pixmap = res.pixmap.copy(0, 0, self.width, self.height)
            pic = QPixmap.fromImage(editor_utilities.convert_colorkey(pixmap.toImage()))
            pic = QIcon(pic)
            self.setIcon(pic)
        else:
            self.setIcon(QIcon())

    def change_icon(self, nid):
        self._nid = nid
        self.sourceChanged.emit(self._nid)
        self.render()

    def set_current(self, nid):
        self.change_icon(nid)

    def onIconSourcePicker(self):
        from app.editor.portrait_editor import portrait_tab
        res, ok = portrait_tab.get()
        if res and ok:
            self.change_icon(res.nid)

class MapIconButton(QPushButton):
    sourceChanged = pyqtSignal(str)
    width, height = 48, 48
    database = RESOURCES.map_icons

    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self._nid = None

        self.setMinimumHeight(self.height)
        self.setMaximumHeight(self.height)
        self.setMinimumWidth(self.width)
        self.setMaximumWidth(self.width)
        self.resize(self.width, self.height)
        self.setStyleSheet("QPushButton {qproperty-iconSize: %dpx %dpx;}" % (self.width, self.height))
        self.pressed.connect(self.onIconSourcePicker)

    def render(self):
        if self._nid:
            res = self.database.get(self._nid)
            if not res:
                self.setIcon(QIcon())
                return
            if not res.pixmap:
                res.pixmap = QPixmap(res.full_path)
            pixmap = res.pixmap.copy(0, 0, self.width, self.height)
            pic = QPixmap.fromImage(editor_utilities.convert_colorkey(pixmap.toImage()))
            pic = QIcon(pic)
            self.setIcon(pic)
        else:
            self.setIcon(QIcon())

    def change_icon(self, nid):
        self._nid = nid
        self.sourceChanged.emit(self._nid)
        self.render()

    def set_current(self, nid):
        self._nid = nid
        self.render()

    def onIconSourcePicker(self):
        from app.editor.icon_editor import icon_tab
        res, ok = icon_tab.get_map_icon_editor()
        if res and ok:
            self.change_icon(res.nid)

class MapSpriteBox(QWidget):
    sourceChanged = pyqtSignal(str)

    def __init__(self, parent=None, current=None, display_width=32, orient: Orientation = Orientation.HORIZONTAL):
        super().__init__(parent)
        self.window = parent
        self.current = current
        self.display_width = display_width

        self.map_sprite_label = QLabel()
        self.map_sprite_label.setMaximumWidth(display_width)

        self.map_sprite_box = QPushButton(("Choose Map Sprite..."))
        self.map_sprite_box.clicked.connect(self.select_map_sprite)

        theme = dark_theme.get_theme()
        icon_folder = theme.icon_dir()

        self.map_sprite_auto_box = QPushButton()
        self.map_sprite_auto_box.setIcon(QIcon(f"{icon_folder}/autoassign.png"))
        self.map_sprite_auto_box.setMaximumWidth(32)
        self.map_sprite_auto_box.setToolTip(_("Auto-assign map sprite with the same unique ID"))
        self.map_sprite_auto_box.clicked.connect(self.autoselect_map_sprite)

        if orient == Orientation.VERTICAL:
            self.buttons_tab = QHBoxLayout()
            self.buttons_tab.addWidget(self.map_sprite_box)    
            self.buttons_tab.addWidget(self.map_sprite_auto_box)

            self.layout = QVBoxLayout()
            self.layout.addWidget(self.map_sprite_label)
            self.layout.addLayout(self.buttons_tab)
            self.setLayout(self.layout)

        else:
            self.layout = QHBoxLayout()           
            self.layout.addWidget(self.map_sprite_label)
            self.layout.addWidget(self.map_sprite_box)
            self.layout.addWidget(self.map_sprite_auto_box)
            self.setLayout(self.layout)

    def select_map_sprite(self):
        res, ok = map_sprite_tab.get()
        if ok:
            nid = res.nid
            pix = self.get_map_sprite_icon(nid, num=0)
            self.map_sprite_label.setPixmap(pix)
            self.sourceChanged.emit(nid)

    def autoselect_map_sprite(self):        
        nid = self.current.nid
        res = RESOURCES.map_sprites.get(nid)
        if res:
            nid = res.nid
            pix = self.get_map_sprite_icon(nid, num=0)
            self.map_sprite_label.setPixmap(pix)
            self.sourceChanged.emit(nid)

    def get_map_sprite_icon(self, nid, num, current=False, team: NID = 'player', variant=None):
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
        pixmap = map_sprite_model.get_basic_icon(pixmap, num, current, team)
        pixmap = pixmap.scaled(self.display_width, self.display_width)
        return pixmap

    def set_current(self, current, nid):
        self.current = current
        pix = self.get_map_sprite_icon(nid, num=0)
        if pix:
            self.map_sprite_label.setPixmap(pix)
        else:
            self.map_sprite_label.clear()