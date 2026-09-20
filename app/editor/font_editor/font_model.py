import os
from typing import Optional

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon, QPainter

from app.data.resources.fonts import Font
from app.data.resources.fonts import FontIndex
from app.data.resources.resources import RESOURCES
from app.editor.base_database_gui import ResourceCollectionModel
from app.editor.settings import MainSettingsController
from app.utilities import str_utils

# Characters tried in order when looking for a preview glyph
_PREVIEW_CANDIDATES = (
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
)


_ICON_SIZE = 32


def _to_uniform_icon(pixmap: QPixmap) -> QPixmap:
    """Scale *pixmap* to fit within a square canvas of _ICON_SIZE, centered."""
    scaled = pixmap.scaled(
        _ICON_SIZE, _ICON_SIZE,
        Qt.KeepAspectRatio, Qt.SmoothTransformation)
    canvas = QPixmap(_ICON_SIZE, _ICON_SIZE)
    canvas.fill(Qt.gray)
    painter = QPainter(canvas)
    x = (_ICON_SIZE - scaled.width()) // 2
    y = (_ICON_SIZE - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)
    painter.end()
    return canvas


def get_font_preview_pixmap(font: Font) -> Optional[QPixmap]:
    """Return a cropped QPixmap of the first available alphanumeric glyph."""
    idx_path = font.index_path()
    png_path = font.image_path()
    if not idx_path or not os.path.exists(idx_path):
        return None
    if not png_path or not os.path.exists(png_path):
        return None

    try:
        index = FontIndex.from_path(idx_path)
    except Exception:
        return None

    sheet = QPixmap(png_path)
    if sheet.isNull():
        return None

    for ch in _PREVIEW_CANDIDATES:
        glyph = index.get(ch)
        if glyph is not None:
            cropped = sheet.copy(glyph.x, glyph.y, index.char_width, index.char_height)
            return _to_uniform_icon(cropped)

    return None


class FontModel(ResourceCollectionModel):
    def __init__(self, data, window):
        super().__init__(data, window)
        self._icon_cache: dict[str, Optional[QPixmap]] = {}

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            font = self._data[index.row()]
            return font.nid
        elif role == Qt.DecorationRole:
            font = self._data[index.row()]
            icon_pixmap = self._get_icon_pixmap(font)
            if icon_pixmap:
                return QIcon(icon_pixmap)
        return None

    def _get_icon_pixmap(self, font: Font) -> Optional[QPixmap]:
        if font.nid not in self._icon_cache:
            self._icon_cache[font.nid] = get_font_preview_pixmap(font)
        return self._icon_cache[font.nid]

    def create_new(self):
        settings = MainSettingsController()
        starting_path = settings.get_last_open_path()
        fn, ok = QFileDialog.getOpenFileName(
            self.window, "Select Font Image", starting_path,
            "PNG Files (*.png);;All Files(*)")
        if not ok:
            return None
        if not fn.endswith('.png'):
            QMessageBox.critical(self.window, "File Type Error!", "Font image must be a PNG file!")
            return None
        file_name_no_ext = fn[:-4]
        idx_path = file_name_no_ext + '.idx'
        if not os.path.exists(idx_path):
            QMessageBox.warning(
                self.window, 'Missing Index File',
                'No matching .idx file found for %s.\n'
                'The font may not render correctly without one.' % os.path.basename(fn))
        nid = os.path.splitext(os.path.basename(fn))[0]
        nid = str_utils.get_next_name(nid, [d.nid for d in RESOURCES.fonts])
        new_font = Font(nid=nid)
        new_font.set_full_path(file_name_no_ext)
        RESOURCES.fonts.append(new_font)
        settings.set_last_open_path(os.path.dirname(fn))
        return new_font

    def delete(self, idx):
        super().delete(idx)

    def on_nid_changed(self, old_nid, new_nid):
        self._icon_cache.pop(old_nid, None)
