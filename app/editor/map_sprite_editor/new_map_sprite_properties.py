import os

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QCheckBox, \
    QGridLayout, QPushButton, QSizePolicy, QFrame, QSplitter, QButtonGroup
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QImage, QColor

from app.data.database.database import DB
from app.data.resources.combat_anims import Frame
from app.extensions.custom_gui import PropertyBox, PropertyCheckBox
from app.editor.custom_widgets import TeamBox

from app.editor import timer
from app.editor.icon_editor.icon_view import IconView
from app.engine.unit_sprite import MapSprite
from app.editor.map_sprite_editor import map_sprite_model
from app.editor.component_editor_types import T
from app.engine.game_state import game
from app.utilities.typing import NID

from typing import (List, Callable, Optional)

class NewMapSpriteProperties(QWidget):
    title = "Map Sprite"

    standing_width, standing_height = 192, 144
    moving_width, moving_height = 192, 160

    def __init__(self, parent, current: Optional[T] = None,
                 attempt_change_nid: Optional[Callable[[NID, NID], bool]] = None,
                 on_icon_change: Optional[Callable] = None):
        super().__init__(parent)
        self.window = parent
        self._data = self.window.data

        self.current: Optional[T] = current
        self.cached_nid: Optional[NID] = self.current.nid if self.current else None
        self.attempt_change_nid = attempt_change_nid
        self.on_icon_change = on_icon_change

        # Populate resources
        for resource in self._data:
            if resource.stand_full_path:
                resource.standing_pixmap = QPixmap(resource.stand_full_path)
            if resource.move_full_path:
                resource.moving_pixmap = QPixmap(resource.move_full_path)

        self.current = current

        left_section = QHBoxLayout()

        self.frame_view = IconView(self)
        self.frame_view.sourceChanged.connect(self.on_icon_changed)
        left_section.addWidget(self.frame_view)

        right_section = QVBoxLayout()

        button_section = QGridLayout()
        self.up_arrow = QPushButton(self)
        self.left_arrow = QPushButton(self)
        self.right_arrow = QPushButton(self)
        self.down_arrow = QPushButton(self)
        self.focus = QPushButton(self)
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(False)
        self.button_group.buttonPressed.connect(self.button_clicked)
        self.buttons = [self.up_arrow, self.left_arrow, self.right_arrow, self.down_arrow, self.focus]
        positions = [(0, 1), (1, 0), (1, 2), (2, 1), (1, 1)]
        text = ["^", "<-", "->", "v", "O"]
        for idx, button in enumerate(self.buttons):
            button_section.addWidget(button, *positions[idx])
            button.setCheckable(True)
            button.setText(text[idx])
            button.setMaximumWidth(40)
            # button.clicked.connect(self.a_button_clicked)
            self.button_group.addButton(button)
            self.button_group.setId(button, idx)
        button_section.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.team_box = TeamBox(self)
        self.team_box.edit.setValue('player')
        self.team_box.edit.activated.connect(self.team_changed)
        self.team_box.setMaximumWidth(120)

        self.gray_box = PropertyCheckBox("Display exhausted sprite?", QCheckBox, self)

        bg_section = QHBoxLayout()
        self.bg_button = QPushButton(self)
        self.bg_button.setCheckable(True)
        self.bg_button.setText("Show Background")
        # self.bg_button.buttonPressed.connect(self.bg_toggled)
        self.grid_button = QPushButton(self)
        self.grid_button.setCheckable(True)
        self.grid_button.setText("Show Grid")
        # self.grid_button.buttonPressed.connect(self.grid_toggled)
        bg_section.addWidget(self.bg_button)
        bg_section.addWidget(self.grid_button)
        bg_section.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        right_section.addLayout(button_section)
        right_section.addWidget(self.team_box)
        right_section.addWidget(self.gray_box)
        right_section.addLayout(bg_section)

        left_frame = QFrame(self)
        left_frame.setLayout(left_section)
        right_frame = QFrame(self)
        right_frame.setLayout(right_section)

        top_splitter = QSplitter(self)
        top_splitter.setChildrenCollapsible(False)
        top_splitter.addWidget(left_frame)
        top_splitter.addWidget(right_frame)

        self.raw_view = PropertyBox("Raw Sprite", IconView, self)
        self.raw_view.edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        final_splitter = QSplitter(self)
        final_splitter.setOrientation(Qt.Vertical)
        final_splitter.setChildrenCollapsible(False)
        final_splitter.addWidget(top_splitter)
        final_splitter.addWidget(self.raw_view)

        final_section = QHBoxLayout()
        self.setLayout(final_section)
        final_section.addWidget(final_splitter)

        timer.get_timer().tick_elapsed.connect(self.tick)

    def on_icon_changed(self):
        if self.current and self.on_icon_change:
            self.on_icon_change()

    def nid_changed(self, text):
        if self.current:
            # Also change name if they are identical
            if self.current.name == self.current.nid.replace('_', ' '):
                self.name_box.edit.setText(text.replace('_', ' '))
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

    def set_current(self, current):
        if not current:
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            self.current = current
            if not current.standing_pixmap:
                current.standing_pixmap = QPixmap(current.stand_full_path)
            if not current.moving_pixmap:
                current.moving_pixmap = QPixmap(current.move_full_path)

            # Painting
            base_image = QImage(self.standing_width + self.moving_width,
                                max(self.standing_height, self.moving_height),
                                QImage.Format_ARGB32)
            base_image.fill(QColor(0, 0, 0, 0))
            painter = QPainter()
            painter.begin(base_image)
            if self.current.standing_pixmap:
                painter.drawImage(0, 8, self.current.standing_pixmap.toImage())
            if self.current.moving_pixmap:
                painter.drawImage(self.standing_width, 0, self.current.moving_pixmap.toImage())
            painter.end()

            self.raw_view.edit.set_image(QPixmap.fromImage(base_image))
            self.raw_view.edit.show_image()

            if self.current:
                self.draw_frame()

    def tick(self):
        # self.window.update_list()
        if self.current:
            self.draw_frame()

    def draw_frame(self):
        if self.left_arrow.isChecked():
            num = timer.get_timer().move_sprite_counter.count
            frame = self.current.moving_pixmap.copy(num*48, 40, 48, 40)
        elif self.right_arrow.isChecked():
            num = timer.get_timer().move_sprite_counter.count
            frame = self.current.moving_pixmap.copy(num*48, 80, 48, 40)
        elif self.up_arrow.isChecked():
            num = timer.get_timer().move_sprite_counter.count
            frame = self.current.moving_pixmap.copy(num*48, 120, 48, 40)
        elif self.down_arrow.isChecked():
            num = timer.get_timer().move_sprite_counter.count
            frame = self.current.moving_pixmap.copy(num*48, 0, 48, 40)
        elif self.focus.isChecked():
            num = timer.get_timer().active_counter.count
            frame = self.current.standing_pixmap.copy(num*64, 96, 64, 48)
        else:
            num = timer.get_timer().passive_counter.count
            frame = self.current.standing_pixmap.copy(num*64, 0, 64, 48)
        frame = frame.toImage()
        if self.gray_box.edit.isChecked():
            frame = map_sprite_model.gray_shift_team(frame)
        else:
            team_nid = self.team_box.edit.currentText()
            frame = map_sprite_model.color_shift_team(frame, team_nid)

        # Background stuff
        image = QImage(48, 56, QImage.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))
        painter = QPainter()
        painter.begin(image)

        if self.bg_button.isChecked():
            painter.drawImage(0, 8, QImage('resources/map_sprite_bg.png'))

        if self.grid_button.isChecked():
            grid_image = QImage('resources/map_sprite_grid.png')
            painter.drawImage(0, 8, grid_image)

        x, y = -(frame.width() - 48)//2, -(frame.height() - 48)//2
        painter.drawImage(x, 0, frame)
        painter.end()

        pix = QPixmap.fromImage(image)
        self.frame_view.set_image(pix)
        self.frame_view.show_image()

    def button_clicked(self, spec_button):
        """
        Needs to first uncheck all buttons, then, set
        the specific button to its correct state
        """
        checked = spec_button.isChecked()
        for button in self.buttons:
            button.setChecked(False)
        spec_button.setChecked(checked)
        self.draw_frame()

    def team_changed(self, val):
        self.draw_frame()