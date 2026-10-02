from typing import Callable, Optional

from PyQt5.QtWidgets import QWidget, QLineEdit, QVBoxLayout, QTextEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics

from app.data.database.lore import Lore
from app.extensions.custom_gui import PropertyBox
from app.editor.lib.components.validated_line_edit import NidLineEdit

from app.utilities.typing import NID

class NewLoreProperties(QWidget):
    title = "Lore"

    def __init__(self, parent, current: Optional[Lore] = None,
                 attempt_change_nid: Optional[Callable[[NID, NID], bool]] = None,
                 on_icon_change: Optional[Callable] = None):
        super().__init__(parent)
        self.window = parent

        self.current: Optional[Lore] = current
        self.cached_nid: Optional[NID] = self.current.nid if self.current else None
        self.attempt_change_nid = attempt_change_nid
        self.on_icon_change = on_icon_change

        name_section = QVBoxLayout()

        self.nid_box = PropertyBox(_("Unique ID"), NidLineEdit, self)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)
        name_section.addWidget(self.nid_box)

        self.short_name_box = PropertyBox(_("Short Name"), QLineEdit, self)
        self.short_name_box.edit.textChanged.connect(self.short_name_changed)
        name_section.addWidget(self.short_name_box)

        self.long_name_box = PropertyBox(_("Long Name"), QLineEdit, self)
        self.long_name_box.edit.textChanged.connect(self.long_name_changed)
        name_section.addWidget(self.long_name_box)

        self.category_box = PropertyBox(_("Category"), QLineEdit, self)
        self.category_box.edit.textChanged.connect(self.category_changed)
        name_section.addWidget(self.category_box)

        self.desc_box = PropertyBox(_("Description Text"), QTextEdit, self)
        font_height = QFontMetrics(self.desc_box.edit.font())
        self.desc_box.edit.setFixedHeight(font_height.lineSpacing() * 20 + 20)
        self.desc_box.edit.textChanged.connect(self.desc_changed)

        total_section = QVBoxLayout()
        self.setLayout(total_section)
        total_section.addLayout(name_section)
        total_section.addWidget(self.desc_box)

        total_section.setAlignment(Qt.AlignTop)

        self.set_current(self.current)

    def nid_changed(self, text):
        if self.current:
            # Also change names if they are identical
            if self.current.name == self.current.nid.replace('_', ' '):
                self.short_name_box.edit.setText(text.replace('_', ' '))
            if self.current.title == self.current.nid.replace('_', ' '):
                self.long_name_box.edit.setText(text.replace('_', ' '))
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

    def short_name_changed(self, text):
        self.current.name = text

    def long_name_changed(self, text):
        self.current.title = text

    def category_changed(self, category):
        self.current.category = category

    def desc_changed(self, text=None):
        self.current.text = self.desc_box.edit.toPlainText()

    def set_current(self, current):
        if not current:
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            self.current = current
            self.cached_nid = current.nid
            self.nid_box.edit.setText(current.nid)
            self.short_name_box.edit.setText(current.name)
            self.long_name_box.edit.setText(current.title)
            self.category_box.edit.setText(current.category)
            self.desc_box.edit.setText(current.text)
