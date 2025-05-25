from PyQt5.QtWidgets import QWidget, QLineEdit, QVBoxLayout, QTextEdit, QStackedWidget
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFontMetrics, QIcon

from app.data.resources.resources import RESOURCES
from app.data.resources.resource_types import ResourceType

from app.extensions.custom_gui import PropertyBox, ComboBox
from app.extensions.list_widgets import AppendMultiListWidget
from app.extensions.key_value_delegate import KeyValueDelegate, KeyValueDoubleListModel

from app.editor.icons import PushableIcon16, MapSpriteBox
from app.editor.icon_editor import icon_tab
from app.editor.lib.components.validated_line_edit import NidLineEdit

from app.utilities.enums import Orientation
from app.utilities.typing import NID

from typing import (Callable, Optional)

class NewCreditProperties(QWidget):
    title = 'Credit'

    CREDIT_TYPES = [credit_type for credit_type in ResourceType
                    if credit_type in (ResourceType.ICONS16, ResourceType.ICONS32, ResourceType.ICONS80, 
                                       ResourceType.MAP_ICONS, ResourceType.MAP_SPRITES, 
                                       ResourceType.PORTRAITS, ResourceType.PANORAMAS)] + ['List', 'Text']

    def __init__(self, parent, current = None,
                 attempt_change_nid: Optional[Callable[[NID, NID], bool]] = None,
                 on_icon_change: Optional[Callable] = None):
        super().__init__(parent)

        self.current = current
        self.cached_nid: Optional[NID] = self.current.nid if self.current else None
        self.attempt_change_nid = attempt_change_nid
        self.on_icon_change = on_icon_change

        self.nid_box = PropertyBox("Unique ID", NidLineEdit, self)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)

        self.type_box = PropertyBox(("Type"), ComboBox, self)
        for credit_type in self.CREDIT_TYPES:
            self.type_box.edit.addItem(credit_type.name.replace('_', ' ').capitalize() 
                                            if isinstance(credit_type, ResourceType) 
                                            else credit_type, 
                                       userData=credit_type)
        self.type_box.edit.currentIndexChanged.connect(self.type_changed)

        self.category_box = PropertyBox("Category", QLineEdit, self)
        self.category_box.edit.textChanged.connect(self.category_changed)

        self.desc_box = QStackedWidget(self)
        for credit_type in self.CREDIT_TYPES:
            if credit_type in (ResourceType.ICONS16, ResourceType.ICONS32, ResourceType.ICONS80, 
                               ResourceType.MAP_ICONS, ResourceType.PORTRAITS):
                desc_box = IconDesc(self, credit_type)
            elif credit_type == ResourceType.MAP_SPRITES:
                desc_box = MapSpriteDesc(self)
            elif credit_type == ResourceType.PANORAMAS:
                desc_box = PanoramaDesc(self)
            elif credit_type == "List":
                desc_box = ListDesc(self)
            elif credit_type == "Text":
                desc_box = TextDesc(self)
            self.desc_box.addWidget(desc_box)

        total_section = QVBoxLayout()
        self.setLayout(total_section)
        total_section.addWidget(self.nid_box)  
        total_section.addWidget(self.type_box)   
        total_section.addWidget(self.category_box)
        total_section.addWidget(self.desc_box)

        total_section.setAlignment(Qt.AlignTop)

        self.set_current(self.current)

    def nid_changed(self, text):
        self.current.nid = text

    def nid_done_editing(self):
        if self.current and self.cached_nid:
            self.nid_box.edit.blockSignals(True)  # message box causes focus loss which double triggers nid_done_editing
            # Check validity of nid!
            if self.attempt_change_nid and self.attempt_change_nid(self.cached_nid, self.current.nid):
                self.cached_nid = self.current.nid
            else:
                self.current.nid = self.cached_nid
                self.nid_box.edit.setText(self.cached_nid)
            self.nid_box.edit.blockSignals(False)

    def type_changed(self, index):
        credit_type = self.type_box.edit.currentData()
        self.current.credit_type = credit_type

        if self.current.credit_type in ["List", "Text"]:
            self.category_box.setEnabled(True)
        else:
            self.category_box.setEnabled(False)
            self.category_box.edit.setText('Graphics')

        idx = self.CREDIT_TYPES.index(credit_type)
        self.desc_box.setCurrentIndex(idx)
        self.desc_box.currentWidget().set_current(self.current)

    def category_changed(self, category):
        self.current.category = category

    def set_current(self, current):
        if not current:
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            self.current = current
            self.cached_nid = current.nid
            self.nid_box.edit.setText(current.nid)

            idx = 0
            if current.credit_type in self.CREDIT_TYPES:
                idx = self.CREDIT_TYPES.index(current.credit_type)
            self.type_box.edit.setCurrentIndex(idx)

            self.category_box.edit.setText(current.category)
            self.desc_box.currentWidget().set_current(current)

class TextDesc(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        self.layout = QVBoxLayout()

        self.header_box = PropertyBox("Header", QLineEdit, self)
        self.header_box.edit.textChanged.connect(self.header_changed)

        self.desc_box = PropertyBox("Description", QTextEdit, self)
        font_height = QFontMetrics(self.desc_box.edit.font())
        self.desc_box.edit.setFixedHeight(font_height.lineSpacing() * 20 + 20)
        self.desc_box.edit.textChanged.connect(self.desc_changed)

        self.layout.addWidget(self.header_box)
        self.layout.addWidget(self.desc_box)
        self.setLayout(self.layout)

    def header_changed(self, text=None):
        self.window.current.sub_nid = text

    def desc_changed(self, text=None):
        text = self.desc_box.edit.toPlainText()
        if text:
            self.window.current.contrib = [(None, text)]

    def set_current(self, current):
        self.header_box.edit.setText(current.sub_nid)

        if current.contrib:
            self.desc_box.edit.setText(current.contrib[0][1])
        else:
            self.desc_box.edit.clear()

class PanoramaDesc(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        self.layout = QVBoxLayout()

        self.panorama_box = PropertyBox("Contribution", ComboBox, self)
        self.panorama_box.edit.addItem(QIcon(), 'None')
        for panorama in RESOURCES.panoramas:
            icon = QIcon(panorama.get_all_paths()[0])
            self.panorama_box.edit.addItem(icon, panorama.nid)
        self.panorama_box.edit.setIconSize(QSize(240, 160))
        self.panorama_box.edit.currentIndexChanged.connect(self.panorama_changed)

        self.contrib_box = PropertyBox("Name", QLineEdit, self)
        self.contrib_box.edit.textChanged.connect(self.contrib_changed)

        self.author_box = PropertyBox("Author", QLineEdit, self)
        self.author_box.edit.textChanged.connect(self.author_changed)

        self.layout.addWidget(self.panorama_box)
        self.layout.addWidget(self.contrib_box)
        self.layout.addWidget(self.author_box)
        self.layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.layout)

    def panorama_changed(self, index):
        contrib = self.window.current.contrib
        sub_nid = self.panorama_box.edit.currentText()
        if not contrib or not len(contrib[0]) > 1 or \
            contrib[0][1] == self.window.current.sub_nid.replace('_', ' '):
                self.contrib_box.edit.setText(sub_nid.replace('_', ' '))
        self.window.current.sub_nid = sub_nid

    def contrib_changed(self, text):
        if not text:
            return
        author = None
        contrib = self.window.current.contrib
        if contrib and contrib[0]:
            author = contrib[0][0]
        self.window.current.contrib = [(author, text)]

    def author_changed(self, text):
        if not text:
            return
        desc = None
        contrib = self.window.current.contrib
        if contrib and len(contrib[0]) > 1:
            desc = contrib[0][1]
        self.window.current.contrib = [(text, desc)]

    def set_current(self, current):
        try:
            self.panorama_box.edit.setValue(current.sub_nid)
        except: # spec isn't compatible
            self.panorama_box.edit.clear()

        if current.contrib:
            self.contrib_box.edit.setText(current.contrib[0][1])
            self.author_box.edit.setText(current.contrib[0][0])
        else:
            self.contrib_box.edit.clear()
            self.author_box.edit.clear()

class CreditPushableIcon(PushableIcon16):
    display_width = 160

    def setType(self, credit_type):
        self.credit_type = credit_type
        if credit_type == ResourceType.ICONS16:
            self.width, self.height = 16, 16
            self.database = RESOURCES.icons16
        elif credit_type == ResourceType.ICONS32:
            self.width, self.height = 32, 32
            self.database = RESOURCES.icons32
        elif credit_type == ResourceType.ICONS80:
            self.width, self.height = 80, 72
            self.database = RESOURCES.icons80
        elif credit_type == ResourceType.MAP_ICONS:
            self.width, self.height = 48, 48
            self.database = RESOURCES.map_icons
        elif credit_type == ResourceType.PORTRAITS:
            self.width, self.height = 96, 80
            self.database = RESOURCES.portraits

    def onIconSourcePicker(self):
        if self.credit_type == ResourceType.PORTRAITS:
            from app.editor.portrait_editor import portrait_tab
            res, ok = portrait_tab.get()
        else:           
            from app.editor.icon_editor import icon_tab
            if self.credit_type == ResourceType.MAP_ICONS:
                res, ok = icon_tab.get_map_icon_editor()
            else:
                res, ok = icon_tab.get(self.width, self._nid)

        if res and ok:
            icon_index = (0, 0)
            if self.credit_type in (ResourceType.ICONS16, ResourceType.ICONS32, ResourceType.ICONS80):
                icon_index = res.icon_index

            self.change_icon(res.nid, icon_index)
            self.sourceChanged.emit(self._nid, self.x, self.y)

class IconDesc(QWidget):
    def __init__(self, parent=None, credit_type='16x16_Icons'):
        super().__init__(parent)
        self.window = parent

        self.layout = QVBoxLayout()       

        self.icon_box = PropertyBox("Contribution", CreditPushableIcon, self)
        self.icon_box.edit.setType(credit_type)
        self.icon_box.edit.sourceChanged.connect(self.on_icon_changed)

        self.contrib_box = PropertyBox("Name", QLineEdit, self)
        self.contrib_box.edit.textChanged.connect(self.contrib_changed)

        self.author_box = PropertyBox("Author", QLineEdit, self)
        self.author_box.edit.textChanged.connect(self.author_changed)

        self.layout.addWidget(self.icon_box)
        self.layout.addWidget(self.contrib_box)
        self.layout.addWidget(self.author_box)
        self.layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.layout)

    def on_icon_changed(self, nid, x, y):
        contrib = self.window.current.contrib
        if not contrib or not len(contrib[0]) > 1 or not contrib[0][1] or \
            (self.window.current.sub_nid and contrib[0][1] == self.window.current.sub_nid.replace('_', ' ')):
                self.contrib_box.edit.setText(nid.replace('_', ' '))

        self.window.current.sub_nid = nid
        self.window.current.icon_index = (x, y)

    def contrib_changed(self, text):
        if not text:
            return
        author = None
        contrib = self.window.current.contrib
        if contrib and contrib[0]:
            author = contrib[0][0]
        self.window.current.contrib = [(author, text)]

    def author_changed(self, text):
        if not text:
            return           
        desc = None
        contrib = self.window.current.contrib
        if contrib and len(contrib[0]) > 1:
            desc = contrib[0][1]
        self.window.current.contrib = [(text, desc)]

    def set_current(self, current):
        try:
            self.icon_box.edit.change_icon(current.sub_nid, current.icon_index)
        except:
            self.icon_box.edit.change_icon(None, (0, 0))

        if current.contrib:
            self.contrib_box.edit.setText(current.contrib[0][1])
            self.author_box.edit.setText(current.contrib[0][0])
        else:
            self.contrib_box.edit.clear()
            self.author_box.edit.clear()

class MapSpriteDesc(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        self.map_sprite_box = MapSpriteBox(self, self.window.current, display_width=160, orient=Orientation.VERTICAL)
        self.map_sprite_box.sourceChanged.connect(self.select_map_sprite)

        self.author_box = PropertyBox("Author", QLineEdit, self)
        self.author_box.edit.textChanged.connect(self.author_changed)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.map_sprite_box)
        self.layout.addWidget(self.author_box)
        self.layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.layout)

    def select_map_sprite(self, nid):
        self.window.current.sub_nid = nid

    def author_changed(self, text):
        if text:
            self.window.current.contrib = [(text, None)]

    def set_current(self, current):
        self.map_sprite_box.set_current(current, current.sub_nid)

        if current.contrib:
            self.author_box.edit.setText(current.contrib[0][0])
        else:
            self.author_box.edit.clear()

class CreditListModel(KeyValueDoubleListModel):
    def setData(self, index, value, role):
        if not index.isValid():
            return False

        row = list(self._data[index.row()])
        row[index.column()] = value
        self._data[index.row()] = tuple(row)

        self.dataChanged.emit(index, index)
        return True

class ListDesc(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        self.layout = QVBoxLayout()

        self.header_box = PropertyBox("Header", QLineEdit, self)
        self.header_box.edit.textChanged.connect(self.header_changed)

        attrs = ("Author", "Contribution")
        self.desc_box = AppendMultiListWidget([], "List of Contributions", attrs, KeyValueDelegate, self, model=CreditListModel)

        self.layout.addWidget(self.header_box)
        self.layout.addWidget(self.desc_box)
        self.setLayout(self.layout)

    def header_changed(self, text=None):
        self.window.current.sub_nid = text

    def set_current(self, current):
        self.header_box.edit.setText(current.sub_nid)
        self.desc_box.set_current(current.contrib)