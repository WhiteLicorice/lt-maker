import logging
import time, random
import traceback

from PyQt5.QtWidgets import QMessageBox, QWidget, QHBoxLayout, QSpinBox, \
    QVBoxLayout, QGridLayout, QPushButton, QSizePolicy, QFrame, QSplitter, \
    QCheckBox, QProgressDialog
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QPainter, QIcon, QPen

from app.data.resources.portraits import INFO_PORTRAIT_WIDTH, INFO_PORTRAIT_HEIGHT
from app.extensions.spinbox_xy import SpinBoxXY
from app.extensions.custom_gui import PropertyBox, PropertyCheckBox
from app.editor import timer
from app.editor.icon_editor.icon_view import IconView
from app.editor.portrait_editor import portrait_model
from app.editor.component_editor_types import T
from app.events.event_portrait import update_talk
from app.utilities import utils
from app.utilities.typing import NID
import app.editor.utilities as editor_utilities

from typing import Callable, Optional

TIME_PER_BLINK_FRAME = 60 # ms

class NewPortraitProperties(QWidget):
    title = "Unit Portrait"

    def __init__(self, parent, current: Optional[T] = None,
                 attempt_change_nid: Optional[Callable[[NID, NID], bool]] = None,
                 on_icon_change: Optional[Callable] = None):
        QWidget.__init__(self, parent)
        self.window = parent
        self._data = self.window.data

        self.current: Optional[T] = current
        self.cached_nid: Optional[NID] = self.current.nid if self.current else None
        self.attempt_change_nid = attempt_change_nid
        self.on_icon_change = on_icon_change

        # Populate resources
        for resource in self._data:
            resource.pixmap = QPixmap(resource.full_path)

        self.current = current

        self.smile_on = False
        self.talk_on = False
        self.reverse = False
        # For talking
        self.talk_state = 0
        self.last_talk_update = 0
        self.next_talk_update = 0
        # For blinking
        self.blink_on = False
        self.blink_update = 0

        left_section = QGridLayout()

        self.portrait_view = IconView(self)
        self.portrait_view.setMinimumHeight(80 + 2)
        left_section.addWidget(self.portrait_view, 0, 0, 1, 3)

        self.smile_button = QPushButton(self)
        self.smile_button.setText("Smile")
        self.smile_button.setCheckable(True)
        self.smile_button.clicked.connect(self.smile_button_clicked)
        self.talk_button = QPushButton(self)
        self.talk_button.setText("Talk")
        self.talk_button.setCheckable(True)
        self.talk_button.clicked.connect(self.talk_button_clicked)
        self.blink_button = QPushButton(self)
        self.blink_button.setText("Blink")
        self.blink_button.setCheckable(True)
        self.blink_button.clicked.connect(self.blink_button_clicked)
        left_section.addWidget(self.smile_button)
        left_section.addWidget(self.talk_button)
        left_section.addWidget(self.blink_button)

        right_section = QGridLayout()
        self.blinking_offset = PropertyBox("Blink Frame Offset", SpinBoxXY, self)
        self.blinking_offset.edit.setSingleStep(8)
        self.blinking_offset.edit.coordsChanged.connect(self.blinking_changed)
        self.smiling_offset = PropertyBox("Mouth Frame Offset", SpinBoxXY, self)
        self.smiling_offset.edit.setSingleStep(8)
        self.smiling_offset.edit.coordsChanged.connect(self.smiling_changed)
        self.info_offset = PropertyBox("Info Menu Offset", SpinBoxXY, self)
        self.info_offset.edit.setSingleStep(8)
        self.info_offset.edit.coordsChanged.connect(self.info_offset_changed)
        right_section.addWidget(self.blinking_offset, 0, 0)
        right_section.addWidget(self.smiling_offset, 0, 1)
        right_section.addWidget(self.info_offset, 3, 0)
        self.auto_frame_button = QPushButton("Auto-guess Offsets")
        self.auto_frame_button.clicked.connect(self.auto_guess_offset)
        self.auto_colorkey_button = QPushButton("Automatically colorkey")
        self.auto_colorkey_button.clicked.connect(self.auto_colorkey)
        right_section.addWidget(self.auto_frame_button, 4, 0)
        right_section.addWidget(self.auto_colorkey_button, 5, 0)

        self.face_size = PropertyBox("Face Frame Size", SpinBoxXY, self)
        self.blink_size = PropertyBox("Blink Frame Size", SpinBoxXY, self)
        self.mouth_size = PropertyBox("Mouth Frame Size", SpinBoxXY, self)
        self.chibi_coord = PropertyBox("Chibi Frame Coordinates", SpinBoxXY, self)
        self.blink_frames = PropertyBox("Number of Blink Frames", QSpinBox, self)
        self.mouth_frames = PropertyBox("Number of Mouth Frames", QSpinBox, self)
        self.blink_size.edit.setMinimum(32, 16)
        self.mouth_size.edit.setMinimum(32, 16)
        self.chibi_coord.edit.setSingleStep(8)
        self.blink_frames.edit.setMinimum(1)
        self.mouth_frames.edit.setMinimum(1)
        self.face_size.edit.coordsChanged.connect(self.face_size_changed)
        self.blink_size.edit.coordsChanged.connect(self.blink_size_changed)
        self.mouth_size.edit.coordsChanged.connect(self.mouth_size_changed)
        self.chibi_coord.edit.coordsChanged.connect(self.chibi_coord_changed)
        self.blink_frames.edit.valueChanged.connect(self.blink_frames_changed)
        self.mouth_frames.edit.valueChanged.connect(self.mouth_frames_changed)
        right_section.addWidget(self.face_size, 3, 1)
        right_section.addWidget(self.blink_size, 1, 0)
        right_section.addWidget(self.mouth_size, 1, 1)
        right_section.addWidget(self.blink_frames, 2, 0)
        right_section.addWidget(self.mouth_frames, 2, 1)
        right_section.addWidget(self.chibi_coord, 4, 1, 2, 1)

        self.bound_box = PropertyCheckBox("Display bounding boxes in Raw View?", QCheckBox, self)
        self.bound_box.edit.setChecked(True)
        self.bound_box.edit.stateChanged.connect(self.bound_box_clicked)
        right_section.addWidget(self.bound_box, 6, 0, 1, 2)
        right_section.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

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

        msg = "Auto-guessing Offsets..."
        self.progress_dialog = QProgressDialog(msg, "Cancel", 0, 100, self)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setWindowTitle(msg)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.progress_dialog.reset()

    def set_current(self, current):
        if not current:
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            self.current = current

            bo = self.current.blinking_offset
            so = self.current.smiling_offset
            self.blinking_offset.edit.set_current(bo[0], bo[1])
            self.smiling_offset.edit.set_current(so[0], so[1])
            self.info_offset.edit.set_current(*current.info_offset)

            self.face_size.edit.set_current(*current.face_size)
            self.blink_size.edit.set_current(*current.blink_size)
            self.mouth_size.edit.set_current(*current.mouth_size)
            self.chibi_coord.edit.set_current(*current.chibi_coord)
            self.blink_frames.edit.setValue(current.blink_frames)
            self.mouth_frames.edit.setValue(current.mouth_frames)

            self.draw_portrait()
            self.draw_raw_image()

    def tick(self):
        self.draw_portrait()

    def update_talk(self):
        current_time = time.time()*1000
        # update mouth
        if self.talk_on and current_time - self.last_talk_update > self.next_talk_update:
            self.last_talk_update = current_time
            self.talk_state, self.next_talk_update, self.reverse = \
                update_talk(self.talk_state, self.current.mouth_frames, self.reverse)
        if not self.talk_on:
            self.talk_state = 0
            self.reverse = False

    def draw_portrait(self):
        self.update_talk()
        if not self.current:
            return
        # Face
        main_portrait = self.current.pixmap.copy(*self.current.get_face_frame())
        main_portrait = main_portrait.toImage()

        # Mouth
        idx = self.talk_state
        mouth_image = self.current.pixmap.copy(*self.current.get_mouth_frame(idx, self.smile_on))
        mouth_image = mouth_image.toImage()

        # Blink
        time_passed = time.time()*1000 - self.blink_update
        blink_state = (int(time_passed) // TIME_PER_BLINK_FRAME) + 1
        if self.blink_on:
            idx = max(self.current.blink_frames - blink_state, 0)
            blink_image = self.current.pixmap.copy(*self.current.get_blink_frame(idx))
        elif blink_state < self.current.blink_frames:
            idx = blink_state
            blink_image = self.current.pixmap.copy(*self.current.get_blink_frame(idx))
        else:
            blink_image = None
        # Draw image
        painter = QPainter()
        main_portrait = editor_utilities.convert_colorkey(main_portrait)
        painter.begin(main_portrait)
        if blink_image:
            blink_image = blink_image.toImage()
            blink_image = editor_utilities.convert_colorkey(blink_image)
            painter.drawImage(*self.current.get_blink_coord(), blink_image)
        mouth_image = editor_utilities.convert_colorkey(mouth_image)
        painter.drawImage(*self.current.get_mouth_coord(), mouth_image)
        painter.setPen(QPen(Qt.black, 1, Qt.DashLine))
        painter.setOpacity(0.75)
        painter.drawRect(*self.current.get_info_coord(), INFO_PORTRAIT_WIDTH, INFO_PORTRAIT_HEIGHT)
        painter.end()

        final_pix = QPixmap.fromImage(main_portrait)
        self.portrait_view.set_image(final_pix)

        self.portrait_view.show_image()

    def blinking_changed(self, x, y):
        self.current.blinking_offset = [x, y]

    def smiling_changed(self, x, y):
        self.current.smiling_offset = [x, y]

    def info_offset_changed(self, x, y):
        self.current.info_offset = (x, y)

    def auto_guess_offset(self):
        portrait_model.auto_frame_portrait(self.current, self.progress_dialog)
        self.set_current(self.current)

    def auto_colorkey(self):
        try:
            portrait_model.auto_colorkey(self.current)
        except Exception as e:
            logging.error("colorkeying failed")
            logging.exception(e)
            QMessageBox.warning(self, 'Colorkey Failed', 'Automatic Colorkeying failed with error: \n' + traceback.format_exc())
        self.set_current(self.current)

    def talk_button_clicked(self, checked):
        self.talk_on = checked

    def smile_button_clicked(self, checked):
        self.smile_on = checked

    def blink_button_clicked(self, checked):
        self.blink_update = time.time()*1000
        self.blink_on = checked

    def chibi_coord_changed(self, x, y):
        self.current.chibi_coord = (x, y)
        self.draw_raw_image()

    def face_size_changed(self, x, y):
        self.current.face_size = (x, y)
        self.draw_raw_image()

    def blink_size_changed(self, x, y):
        self.current.blink_size = (x, y)
        self.current.face_size = (min(self.current.pixmap.width() - x,
                                      self.current.face_size[0]),
                                  self.current.face_size[1])
        self.face_size.edit.set_current(*self.current.face_size)
        self.draw_raw_image()

    def mouth_size_changed(self, x, y):
        self.current.mouth_size = (x, y)
        self.current.face_size = (self.current.face_size[0],
                                  min(self.current.face_size[1],
                                      self.current.pixmap.height() - y*2))
        self.face_size.edit.set_current(*self.current.face_size)
        self.draw_raw_image()

    def blink_frames_changed(self, val):
        self.current.blink_frames = val
        self.draw_raw_image()

    def mouth_frames_changed(self, val):
        self.current.mouth_frames = val
        self.draw_raw_image()

    def bound_box_clicked(self, state):
        self.draw_raw_image()

    def draw_raw_image(self):
        raw_image = self.current.pixmap.toImage()
        if self.bound_box.edit.isChecked():
            painter = QPainter()
            painter.begin(raw_image)

            # Face Frame
            painter.setPen(QPen(Qt.cyan, 2, Qt.DotLine))
            painter.drawRect(*self.current.get_face_frame())

            # Blink Frame
            painter.setPen(QPen(Qt.magenta, 2, Qt.DotLine))
            for i in range(self.current.blink_frames):
                painter.drawRect(*self.current.get_blink_frame(i))

            # Mouth Frame
            painter.setPen(QPen(Qt.yellow, 2, Qt.DotLine))
            for i in range(self.current.mouth_frames):
                painter.drawRect(*self.current.get_mouth_frame(i))
                painter.drawRect(*self.current.get_mouth_frame(i, smile=True))

            # Chibi Frame
            painter.setPen(QPen(Qt.red, 2, Qt.DotLine))
            painter.drawRect(*self.current.get_minimug())
            painter.end()

        final_pix = QPixmap.fromImage(raw_image)
        self.raw_view.edit.set_image(final_pix)
        self.raw_view.edit.show_image()
