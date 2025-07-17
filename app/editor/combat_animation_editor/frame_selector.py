import os

from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QListView, QDialog, \
    QPushButton, QFileDialog, QMessageBox, QGroupBox, QFormLayout, QSpinBox, \
    QCheckBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon, QImage, QPainter

from app.constants import WINWIDTH, WINHEIGHT

from app import utilities
from app.data.resources import combat_anims, combat_palettes, map_sprites
from app.data.resources.resources import RESOURCES

from app.editor.settings import MainSettingsController

from app.extensions.custom_gui import Dialog
from app.editor.base_database_gui import ResourceCollectionModel
from app.editor.icon_editor.icon_view import IconView
from app.editor.map_sprite_editor import map_sprite_model
from app.editor.combat_animation_editor import combat_animation_model
from app.editor.combat_animation_editor.animation_import_utils import update_anim_full_image

import app.editor.utilities as editor_utilities

class FrameModel(ResourceCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            frame = self._data[index.row()]
            text = frame.nid
            return text
        elif role == Qt.DecorationRole:
            frame = self._data[index.row()]
            im = self.window.palette_swap(frame.pixmap)
            pix = QPixmap.fromImage(im)
            return QIcon(pix)
        return None

class FrameSelector(Dialog):
    def __init__(self, combat_anim, weapon_anim, parent=None):
        super().__init__(parent)
        self.window = parent
        self.setWindowTitle("Animation Frames")
        self.settings = MainSettingsController()

        self.combat_anim = combat_anim
        self.weapon_anim = weapon_anim
        self.current_palette_nid = self.window.get_current_palette()
        # Get a reference to the color change function
        self.frames = weapon_anim.frames
        if self.frames:
            self.current = self.frames[0]
        else:
            self.current = None
        # animations aren't loaded yet
        if not self.current or not self.current.pixmap:
            try:
                from app.editor.combat_animation_editor.new_combat_animation_properties import populate_anim_pixmaps
                populate_anim_pixmaps(combat_anim)
            except:
                if isinstance(combat_anim, map_sprites.MapSprite):
                    from app.editor.map_sprite_editor.new_map_sprite_properties import populate_map_sprite_pixmaps
                    populate_map_sprite_pixmaps(combat_anim)
                else:
                    from app.editor.combat_animation_editor.new_combat_effect_properties import populate_effect_pixmaps
                    populate_effect_pixmaps(combat_anim)


        self.display = IconView(self)
        self.display.static_size = True
        self.display.setSceneRect(0, 0, WINWIDTH, WINHEIGHT)

        offset_section = QGroupBox(self)
        offset_section.setTitle("Offset")
        offset_layout = QFormLayout()
        self.x_box = QSpinBox()
        self.x_box.setValue(0)
        self.x_box.setRange(-WINWIDTH, WINWIDTH)
        self.x_box.valueChanged.connect(self.on_x_changed)
        offset_layout.addRow("X:", self.x_box)
        self.y_box = QSpinBox()
        self.y_box.setValue(0)
        self.y_box.setRange(-WINHEIGHT, WINHEIGHT)
        self.y_box.valueChanged.connect(self.on_y_changed)
        offset_layout.addRow("Y:", self.y_box)
        offset_section.setLayout(offset_layout)

        anim_marker_path = os.path.join("app", "editor", "combat_animation_editor", "assets")
        self.anim_background = QImage(WINWIDTH, WINHEIGHT, QImage.Format_ARGB32)
        self.anim_background.load(os.path.join(anim_marker_path, "combat-markers.png"))

        self.anim_background_check = QCheckBox(self)
        self.anim_background_check.stateChanged.connect(self.on_anim_background_changed)
        self.anim_background_check.setText("Use default background")
        self.anim_background_check.setChecked(self.settings.get_default_anim_background())

        self.view = QListView(self)
        self.view.currentChanged = self.on_item_changed

        self.model = FrameModel(self.frames, self)
        self.view.setModel(self.model)

        self.delete_button = QPushButton("Delete Current Frame")
        self.delete_button.clicked.connect(self.delete_frame)
        self.add_button = QPushButton("Add Frames...")
        self.add_button.clicked.connect(self.import_frames)
        self.export_button = QPushButton("Export Frames...")
        self.export_button.clicked.connect(self.export_frames)

        layout = QVBoxLayout()
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.view)
        if not isinstance(combat_anim, map_sprites.MapSprite):
            left_layout.addWidget(self.add_button)
            left_layout.addWidget(self.delete_button)
            left_layout.addWidget(self.export_button)
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.display)
        right_layout.addWidget(self.anim_background_check)
        right_layout.addWidget(offset_section)
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        layout.addLayout(main_layout)
        layout.addWidget(self.buttonbox)
        self.setLayout(layout)

        self.set_current(self.current)

    def on_item_changed(self, curr, prev):
        if self.frames:
            new_data = curr.internalPointer()
            if not new_data:
                new_data = self.frames[curr.row()]
            self.set_current(new_data)

    def on_x_changed(self, val):
        if self.current:
            self.current.offset = (val, self.current.offset[1])
        self.draw()

    def on_y_changed(self, val):
        if self.current:
            self.current.offset = (self.current.offset[0], val)
        self.draw()

    def on_anim_background_changed(self, val):
        self.settings.set_default_anim_background(bool(val))
        self.draw()

    def export_frames(self):
        starting_path = self.settings.get_last_open_path()
        fn_dir = QFileDialog.getExistingDirectory(
            self, "Export Frames", starting_path)
        if fn_dir:
            self.settings.set_last_open_path(fn_dir)
            self.export(fn_dir)
            QMessageBox.information(self, "Export Complete", "Export of frames complete!")

    def set_current(self, frame):
        self.current = frame
        if self.current:
            self.x_box.setEnabled(True)
            self.y_box.setEnabled(True)
            self.x_box.setValue(self.current.offset[0])
            self.y_box.setValue(self.current.offset[1])
            self.draw()
        else:
            self.x_box.setEnabled(False)
            self.y_box.setEnabled(False)

    def delete_frame(self):
        if self.current:
            idx = self.frames.index(self.current.nid)
            new_idx = self.model.delete(idx)
            if new_idx:
                new_frame = self.frames[new_idx.row()]
                self.set_current(new_frame)

    def palette_swap(self, pixmap):
        if isinstance(self.combat_anim, map_sprites.MapSprite):
            im = map_sprite_model.palette_swap(pixmap, self.current_palette_nid)
        else:
            im = combat_animation_model.palette_swap(pixmap, self.current_palette_nid)
        return im

    def draw(self):
        if self.anim_background_check.isChecked():
            base_image = QImage(WINWIDTH, WINHEIGHT, QImage.Format_ARGB32)
            base_image.fill(editor_utilities.qCOLORKEY)
        else:
            base_image = QImage(self.anim_background)

        if self.current:
            painter = QPainter()
            painter.begin(base_image)
            pixmap = self.current.pixmap
            im = self.palette_swap(pixmap)
            painter.drawImage(self.current.offset[0], self.current.offset[1], im)
            painter.end()

        self.display.set_image(QPixmap.fromImage(base_image))
        self.display.show_image()

    @classmethod
    def get(cls, combat_anim, weapon_anim, parent=None):
        dlg = cls(combat_anim, weapon_anim, parent)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            return dlg.current, True
        else:
            return None, False

    def import_frames(self):
        starting_path = self.settings.get_last_open_path()
        fns, ok = QFileDialog.getOpenFileNames(self.window, "Select Frames", starting_path, "PNG Files (*.png);;All Files(*)")
        error = False
        if fns and ok:
            pixmaps = []
            crops = []
            nids = []
            # Get files and crop them to right size
            for fn in fns:
                if fn.endswith('.png'):
                    nid = os.path.split(fn)[-1][:-4]
                    nids.append(nid)
                    pix = QPixmap(fn)
                    x, y, width, height = editor_utilities.get_bbox(pix.toImage())
                    pix = pix.copy(x, y, width, height)
                    pixmaps.append(pix)
                    crops.append((x, y, width, height))
                elif not error:
                    error = True
                    QMessageBox.critical(self.window, "File Type Error!", "Frame must be PNG format!")

            # Now determine palette to use for ingestion
            all_palette_colors = editor_utilities.find_palette_from_multiple([pix.toImage() for pix in pixmaps])
            my_palette = None
            for palette_name, palette_nid in self.combat_anim.palettes:
                palette = RESOURCES.combat_palettes.get(palette_nid)
                if palette and palette.is_similar(all_palette_colors):
                    my_palette = palette
                    break
            else:
                nid = utilities.get_next_name("New Palette", RESOURCES.combat_palettes.keys())
                my_palette = combat_palettes.Palette(nid)
                RESOURCES.combat_palettes.append(my_palette)
                self.combat_anim.palettes.append(["New Palette", my_palette.nid])
                self.current_palette_nid = my_palette.nid
                my_palette.assign_colors(all_palette_colors)

            convert_dict = editor_utilities.get_color_conversion(my_palette)
            for idx, pix in enumerate(pixmaps):
                im = pix.toImage()
                im = editor_utilities.color_convert(im, convert_dict)
                pix = QPixmap.fromImage(im)
                nid = utilities.get_next_name(nids[idx], self.frames.keys())
                x, y, width, height = crops[idx]
                # rect is None because it hasn't been placed in a sheet yet
                new_frame = combat_anims.Frame(nid, None, (x, y), pix)
                self.frames.append(new_frame)
                self.set_current(new_frame)

            update_anim_full_image(self.weapon_anim)
            self.model.layoutChanged.emit()

            parent_dir = os.path.split(fns[-1])[0]
            self.settings.set_last_open_path(parent_dir)

    def export(self, fn_dir):
        index = {}
        for frame in self.frames:
            index[frame.nid] = (frame.rect, frame.offset)
            # Draw frame
            base_image = QImage(WINWIDTH, WINHEIGHT, QImage.Format_ARGB32)
            base_image.fill(editor_utilities.qCOLORKEY)
            painter = QPainter()
            painter.begin(base_image)
            pixmap = frame.pixmap
            im = self.palette_swap(pixmap)
            painter.drawImage(frame.offset[0], frame.offset[1], im)
            painter.end()
            path = os.path.join(fn_dir, '%s.png' % frame.nid)
            base_image.save(path)

        index_path = os.path.join(fn_dir, '%s-%s-Index.txt' % (self.combat_anim.nid, self.weapon_anim.nid))
        with open(index_path, 'w') as fn:
            frames = sorted(index.items())
            for frame in frames:
                nid, (rect, offset) = frame
                fn.write('%s;%d,%d;%d,%d;%d,%d\n' % (nid, *rect, *offset))
