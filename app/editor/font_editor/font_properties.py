import os
import shutil
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QSpinBox, QCheckBox, QPushButton,
    QFileDialog, QColorDialog, QScrollArea,
    QListWidget, QInputDialog, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPixmap

from app.data.resources.fonts import Font
from app.engine.bmpfont import BmpFont
from app.engine import engine
from app.extensions.custom_gui import ComboBox, PropertyBox, PropertyCheckBox
from app.editor.font_editor.font_model import seed_default_palette
from app.editor.settings import MainSettingsController


class PaletteEditor(QWidget):
    palette_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font: Optional[Font] = None

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        self.setLayout(body)

        # left: palette list + add/delete buttons
        list_panel = QVBoxLayout()
        list_panel.setSpacing(2)
        self.palette_list = QListWidget()
        self.palette_list.setFixedWidth(90)
        self.palette_list.setToolTip("The default palette holds the sprite sheet's own colors and is read-only; "
                                     "every other palette remaps it color for color")
        self.palette_list.currentTextChanged.connect(self._rebuild_swatches)
        list_panel.addWidget(self.palette_list)
        list_btns = QHBoxLayout()
        list_btns.setSpacing(2)
        add_btn = QPushButton("+")
        add_btn.setFixedWidth(40)
        add_btn.setToolTip("Add palette")
        add_btn.clicked.connect(self._add_palette)
        del_btn = QPushButton("−")
        del_btn.setFixedWidth(40)
        del_btn.setToolTip("Delete selected palette")
        del_btn.clicked.connect(self._delete_palette)
        list_btns.addWidget(add_btn)
        list_btns.addWidget(del_btn)
        list_panel.addLayout(list_btns)
        body.addLayout(list_panel)

        # right: two labelled swatch rows
        swatch_panel = QVBoxLayout()
        swatch_panel.setSpacing(0)

        self._label_default = QLabel("Default")
        self._label_default.setFixedHeight(24)
        self._label_default.setStyleSheet("color: #888; font-size: 10px;")
        swatch_panel.addWidget(self._label_default)

        scroll_default = QScrollArea()
        scroll_default.setWidgetResizable(True)
        scroll_default.setFixedHeight(34)
        scroll_default.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_default.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._default_swatch_widget = QWidget()
        self._default_swatch_layout = QHBoxLayout()
        self._default_swatch_layout.setAlignment(Qt.AlignLeft)
        self._default_swatch_layout.setSpacing(4)
        self._default_swatch_layout.setContentsMargins(0, 0, 0, 0)
        self._default_swatch_widget.setLayout(self._default_swatch_layout)
        scroll_default.setWidget(self._default_swatch_widget)
        swatch_panel.addWidget(scroll_default)

        self._label_palette = QLabel("")
        self._label_palette.setFixedHeight(24)
        self._label_palette.setStyleSheet("font-size: 10px; font-weight: bold;")
        swatch_panel.addWidget(self._label_palette)

        scroll_edit = QScrollArea()
        scroll_edit.setWidgetResizable(True)
        scroll_edit.setFixedHeight(34)
        scroll_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._edit_swatch_widget = QWidget()
        self._edit_swatch_layout = QHBoxLayout()
        self._edit_swatch_layout.setAlignment(Qt.AlignLeft)
        self._edit_swatch_layout.setSpacing(4)
        self._edit_swatch_layout.setContentsMargins(0, 0, 0, 0)
        self._edit_swatch_widget.setLayout(self._edit_swatch_layout)
        scroll_edit.setWidget(self._edit_swatch_widget)
        swatch_panel.addWidget(scroll_edit)
        swatch_panel.addStretch()

        body.addLayout(swatch_panel)

    def set_font(self, font: Optional[Font]):
        self._font = font
        self._repopulate_list()
        self._rebuild_swatches()

    # -- internal --

    def _repopulate_list(self, select: str = None):
        self.palette_list.blockSignals(True)
        self.palette_list.clear()
        if self._font:
            for name in self._font.palettes:
                self.palette_list.addItem(name)
        if select:
            items = self.palette_list.findItems(select, Qt.MatchExactly)
            if items:
                self.palette_list.setCurrentItem(items[0])
        elif self.palette_list.count():
            self.palette_list.setCurrentRow(0)
        self.palette_list.blockSignals(False)

    def _rebuild_swatches(self):
        for layout in (self._default_swatch_layout, self._edit_swatch_layout):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

        if not self._font:
            self._label_palette.setText("")
            return
        list_item = self.palette_list.currentItem()
        palette_name = list_item.text() if list_item else None
        if not palette_name or palette_name not in self._font.palettes:
            self._label_palette.setText("")
            return
        is_default = palette_name == self._font.default_color
        self._label_palette.setText(
            (palette_name + " (read-only — these are the sprite sheet's colors)") if is_default else palette_name)
        # The reference row would only repeat the palette itself when it *is* the default
        self._label_default.setText("" if is_default else "Default")

        default_palette = self._font.palettes.get(self._font.default_color, [])
        edit_palette = self._font.palettes[palette_name]

        for i, color in enumerate(edit_palette):
            if not is_default and i < len(default_palette):
                r, g, b, *_ = default_palette[i]
                ref = QLabel()
                ref.setFixedSize(24, 24)
                ref.setStyleSheet(f"background-color: rgb({r},{g},{b}); border: 1px solid #666;")
                ref.setToolTip(f"Default: ({r},{g},{b})")
                self._default_swatch_layout.addWidget(ref)

            r, g, b, *_ = color
            if is_default:
                swatch = QLabel()
                swatch.setToolTip(f"({r},{g},{b})")
            else:
                swatch = QPushButton()
                swatch.setToolTip(f"({r},{g},{b}) — click to edit")
                swatch.clicked.connect(lambda *_, idx=i, pname=palette_name: self._pick_color(pname, idx))
            swatch.setFixedSize(24, 24)
            swatch.setStyleSheet(f"background-color: rgb({r},{g},{b}); border: 1px solid #444;")
            self._edit_swatch_layout.addWidget(swatch)

    def _add_palette(self):
        if not self._font:
            return
        # A palette is a remap of the default one, so the font needs a default first
        seed_default_palette(self._font)
        default_palette = self._font.palettes.get(self._font.default_color)
        if not default_palette:
            QMessageBox.warning(
                self, "No Default Palette",
                "Could not read any colors from this font's PNG, so there is "
                "nothing for a new palette to recolor.")
            return
        name, ok = QInputDialog.getText(self, "Add Palette", "Palette name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self._font.palettes:
            return
        self._font.palettes[name] = default_palette.copy()
        self._repopulate_list(select=name)
        self._rebuild_swatches()
        self.palette_changed.emit()

    def _delete_palette(self):
        if not self._font:
            return
        item = self.palette_list.currentItem()
        if not item:
            return
        if item.text() == self._font.default_color:
            QMessageBox.warning(
                self, "Cannot Delete Default Palette",
                "'%s' is this font's default palette. Every other palette is "
                "defined as a recoloring of it." % item.text())
            return
        self._font.palettes.pop(item.text(), None)
        self._repopulate_list()
        self._rebuild_swatches()
        self.palette_changed.emit()

    def _pick_color(self, palette_name: str, index: int):
        if not self._font or palette_name not in self._font.palettes:
            return
        c = self._font.palettes[palette_name][index]
        r, g, b = c[0], c[1], c[2]
        a = c[3] if len(c) > 3 else 255
        color = QColorDialog.getColor(QColor(r, g, b, a), self,
                                      f"Edit '{palette_name}' colour {index}",
                                      QColorDialog.ShowAlphaChannel)
        if not color.isValid():
            return
        self._font.palettes[palette_name][index] = (color.red(), color.green(), color.blue(), color.alpha())
        self._rebuild_swatches()
        self.palette_changed.emit()


class FontProperties(QWidget):
    def __init__(self, parent, current: Optional[Font] = None):
        super().__init__(parent)
        self.window = parent
        self._data = self.window._data
        self.current: Optional[Font] = current
        self._bmp_font: Optional[BmpFont] = None

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # -- Text preview --
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        preview_group.setLayout(preview_layout)

        input_row = QHBoxLayout()
        self.preview_input = QLineEdit()
        self.preview_input.setPlaceholderText("Type preview text…")
        self.preview_input.setText("What? How?")
        self.preview_input.textChanged.connect(self._update_preview)
        input_row.addWidget(self.preview_input)
        self.preview_color_box = ComboBox()
        self.preview_color_box.setFixedWidth(90)
        self.preview_color_box.setToolTip("Preview palette")
        self.preview_color_box.currentTextChanged.connect(self._update_preview)
        input_row.addWidget(self.preview_color_box)
        self.bg_color_button = QPushButton()
        self.bg_color_button.setFixedWidth(28)
        self.bg_color_button.setToolTip("Pick background color")
        self.bg_color_button.clicked.connect(self._pick_bg_color)
        input_row.addWidget(self.bg_color_button)
        preview_layout.addLayout(input_row)

        self._preview_bg = QColor(0xE0, 0xE0, 0xD8)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(64)
        preview_layout.addWidget(self.preview_label)
        self._apply_preview_bg()

        main_layout.addWidget(preview_group)

        # -- Metadata fields --
        meta_group = QGroupBox("Properties")
        meta_layout = QVBoxLayout()
        meta_group.setLayout(meta_layout)

        ttf_row = QHBoxLayout()
        self.fallback_ttf_box = PropertyBox("Fallback TTF", QLineEdit, self)
        self.fallback_ttf_box.edit.setPlaceholderText("(none)")
        self.fallback_ttf_box.edit.textChanged.connect(self._fallback_ttf_changed)
        ttf_row.addWidget(self.fallback_ttf_box)
        self.browse_ttf_button = QPushButton("Browse...")
        self.browse_ttf_button.setFixedWidth(80)
        self.browse_ttf_button.clicked.connect(self._browse_ttf)
        ttf_row.addWidget(self.browse_ttf_button)
        meta_layout.addLayout(ttf_row)

        self.fallback_size_box = PropertyBox("Fallback Size", QSpinBox, self)
        self.fallback_size_box.edit.setRange(1, 128)
        self.fallback_size_box.edit.valueChanged.connect(self._fallback_size_changed)
        meta_layout.addWidget(self.fallback_size_box)

        self.default_color_box = PropertyBox("Default Color", ComboBox, self)
        self.default_color_box.edit.setToolTip(
            "Which palette holds the sprite sheet's own colors")
        self.default_color_box.edit.currentTextChanged.connect(self._default_color_changed)
        meta_layout.addWidget(self.default_color_box)

        self.outline_font_box = PropertyCheckBox("Outline Font", QCheckBox, self)
        self.outline_font_box.edit.stateChanged.connect(self._outline_font_changed)
        meta_layout.addWidget(self.outline_font_box)

        main_layout.addWidget(meta_group)

        # -- Palette editor --
        palette_group = QGroupBox("Palettes")
        palette_group_layout = QVBoxLayout()
        palette_group.setLayout(palette_group_layout)
        self.palette_editor = PaletteEditor(self)
        self.palette_editor.palette_changed.connect(self._on_palette_changed)
        palette_group_layout.addWidget(self.palette_editor)
        main_layout.addWidget(palette_group)

        main_layout.setAlignment(Qt.AlignTop)

    def set_current(self, current: Optional[Font]):
        self.current = current
        if not current:
            self.setEnabled(False)
            return
        self.setEnabled(True)

        ttf_basename = os.path.basename(current.fallback_ttf) if current.fallback_ttf else ""
        self.fallback_ttf_box.edit.blockSignals(True)
        self.fallback_ttf_box.edit.setText(ttf_basename)
        self.fallback_ttf_box.edit.blockSignals(False)

        self.fallback_size_box.edit.blockSignals(True)
        self.fallback_size_box.edit.setValue(current.fallback_size)
        self.fallback_size_box.edit.blockSignals(False)

        self._refresh_color_boxes()

        self.outline_font_box.edit.blockSignals(True)
        self.outline_font_box.edit.setChecked(bool(current.outline_font))
        self.outline_font_box.edit.blockSignals(False)

        self.palette_editor.set_font(current)

        self._reinit_bmp_font()

    def _refresh_color_boxes(self):
        """Rebuild both palette drop-downs from the font's current palettes."""
        current = self.current
        if not current:
            return

        self.default_color_box.edit.blockSignals(True)
        self.default_color_box.edit.clear()
        self.default_color_box.edit.addItem("")
        for color_name in current.palettes:
            self.default_color_box.edit.addItem(color_name)
        if current.default_color:
            # Show a default_color with no palette behind it rather than silently dropping it
            if self.default_color_box.edit.findText(current.default_color) < 0:
                self.default_color_box.edit.addItem(current.default_color)
            self.default_color_box.edit.setCurrentIndex(
                self.default_color_box.edit.findText(current.default_color))
        else:
            self.default_color_box.edit.setCurrentIndex(0)
        self.default_color_box.edit.blockSignals(False)

        preview_color = self.preview_color_box.currentText()
        self.preview_color_box.blockSignals(True)
        self.preview_color_box.clear()
        for color_name in current.palettes:
            self.preview_color_box.addItem(color_name)
        idx = self.preview_color_box.findText(preview_color)
        if idx < 0:
            idx = self.preview_color_box.findText(current.default_color or "")
        self.preview_color_box.setCurrentIndex(max(idx, 0))
        self.preview_color_box.blockSignals(False)

    def _on_palette_changed(self):
        if not self.current:
            return
        self._refresh_color_boxes()
        self._reinit_bmp_font()

    def _reinit_bmp_font(self):
        self._bmp_font = None
        if not self.current:
            return
        png_path = self.current.image_path()
        if png_path and os.path.exists(png_path) and self.current.font_index:
            try:
                self._bmp_font = BmpFont(self.current, headless=True)
            except Exception:
                pass
        self._update_preview()

    def _update_preview(self):
        text = self.preview_input.text()
        if not self._bmp_font or not text:
            self.preview_label.clear()
            return
        try:
            import pygame
            w = max(self._bmp_font.width(text), 1) + 10
            h = self._bmp_font.height + 3
            surf = pygame.Surface((w, h), pygame.SRCALPHA, 32)
            color = self.preview_color_box.currentText() or None
            self._bmp_font.blit(text, surf, color=color)
            raw = engine.surf_to_raw(surf, 'RGBA')
            img = QImage(raw, w, h, QImage.Format_RGBA8888)
            pix = QPixmap.fromImage(img)
            scaled = pix.scaled(w * 3, h * 3, Qt.KeepAspectRatio, Qt.FastTransformation)
            self.preview_label.setPixmap(scaled)
        except Exception as e:
            print("error rendering preview: %s" % e)
            self.preview_label.setText(f"Error: {e}")

    def _apply_preview_bg(self):
        c = self._preview_bg
        self.bg_color_button.setStyleSheet(
            f"background-color: {c.name()}; border: 1px solid #444;")
        if hasattr(self, 'preview_label'):
            self.preview_label.setStyleSheet(
                f"background-color: {c.name()}; border: 1px solid #444;")

    def _pick_bg_color(self):
        color = QColorDialog.getColor(self._preview_bg, self, "Preview Background")
        if color.isValid():
            self._preview_bg = color
            self._apply_preview_bg()

    def _fallback_ttf_changed(self, text):
        if self.current:
            self.current.fallback_ttf = text if text else None
            self._reinit_bmp_font()

    def _browse_ttf(self):
        if not self.current:
            return
        settings = MainSettingsController()
        font_dir = (os.path.dirname(self.current.file_name)
                    if self.current.file_name else settings.get_last_open_path())
        fn, ok = QFileDialog.getOpenFileName(
            self, "Select Fallback TTF", font_dir,
            "TrueType Font Files (*.ttf);;All Files(*)")
        if ok and fn:
            basename = os.path.basename(fn)
            dest = os.path.join(font_dir, basename)
            if os.path.abspath(fn) != os.path.abspath(dest):
                shutil.copy2(fn, dest)
            self.current.fallback_ttf = basename
            self.fallback_ttf_box.edit.blockSignals(True)
            self.fallback_ttf_box.edit.setText(basename)
            self.fallback_ttf_box.edit.blockSignals(False)
            self._reinit_bmp_font()

    def _fallback_size_changed(self, val):
        if self.current:
            self.current.fallback_size = val
            self._reinit_bmp_font()

    def _default_color_changed(self, text):
        if self.current:
            self.current.default_color = text if text else None
            # The default palette is the read-only reference row, so the swatches change with it
            self.palette_editor.set_font(self.current)
            self._reinit_bmp_font()

    def _outline_font_changed(self, state):
        if self.current:
            self.current.outline_font = bool(state)
            self._reinit_bmp_font()
