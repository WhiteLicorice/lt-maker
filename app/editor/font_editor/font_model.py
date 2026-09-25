import os
from collections import Counter
from typing import List, Optional

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QIcon, QPainter

from app.data.resources.fonts import Font
from app.data.resources.fonts import FontIndex
from app.data.resources.resources import RESOURCES
from app.editor.base_database_gui import ResourceCollectionModel
from app.editor.settings import MainSettingsController
from app.utilities import str_utils
from app.utilities.typing import Color4

# Characters tried in order when looking for a preview glyph
_PREVIEW_CANDIDATES = (
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
)


_ICON_SIZE = 32

#: Name given to the palette seeded from the sprite sheet's own colors.
DEFAULT_PALETTE_NID = 'default'

#: Upper bound on how many sheet colors get seeded into the base palette.
#: Bitmap fonts use a handful of colors; an anti-aliased sheet could otherwise
#: produce hundreds of swatches and make the palette editor unusable.
_MAX_SEEDED_COLORS = 32


def extract_default_palette(png_path: str, max_colors: int = _MAX_SEEDED_COLORS) -> List[Color4]:
    """Return the fully-opaque colors of the sprite sheet at *png_path*.

    Every other palette on a font remaps this one index for index
    (see :class:`app.engine.bmpfont.BmpFont`), so the palette named by
    ``Font.base_palette_nid`` has to be the colors that actually appear in the
    PNG -- which is why it is not simply whichever palette text defaults to
    rendering in. Ordered most-common first, so
    index 0 is the dominant glyph color and index 1 its shadow -- the order
    ``Font.primary_color``/``secondary_color`` expect.
    """
    image = QImage(png_path)
    if image.isNull():
        return []
    image = image.convertToFormat(QImage.Format_RGBA8888)
    counts = Counter()
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.alpha() == 255:
                counts[(color.red(), color.green(), color.blue(), 255)] += 1
    return [color for color, _count in counts.most_common(max_colors)]


def detect_base_palette(font: Font) -> Optional[str]:
    """Name the palette holding the sprite sheet's own colors, by reading the PNG.

    Fonts saved before ``base_color`` existed only say which palette text
    defaults to, and for a font whose default was moved off the sheet that is
    the wrong answer -- so ask the PNG instead of trusting ``default_color``.
    Returns None when no palette matches, leaving the caller to fall back.
    """
    png_path = font.image_path()
    if not font.palettes or not png_path or not os.path.exists(png_path):
        return None
    sheet_colors = {tuple(color) for color in extract_default_palette(png_path)}
    if not sheet_colors:
        return None
    # The current default first, so a font that is already correct keeps its answer
    # even if some other palette happens to hold the same colors
    names = [font.default_color] + [name for name in font.palettes if name != font.default_color]
    for name in names:
        palette = font.palettes.get(name)
        if palette and all(tuple(color) in sheet_colors for color in palette):
            return name
    return None


def seed_default_palette(font: Font) -> bool:
    """Give *font* a palette of its sprite sheet's colors read off its PNG, if it has none yet."""
    base_nid = font.base_palette_nid
    if base_nid and base_nid in font.palettes:
        return False
    png_path = font.image_path()
    if not png_path or not os.path.exists(png_path):
        return False
    palette = extract_default_palette(png_path)
    if not palette:
        return False
    nid = base_nid or DEFAULT_PALETTE_NID
    font.palettes[nid] = palette
    font.base_color = nid
    if not font.default_color:
        font.default_color = nid
    return True


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
        seed_default_palette(new_font)
        RESOURCES.fonts.append(new_font)
        settings.set_last_open_path(os.path.dirname(fn))
        return new_font

    def delete(self, idx):
        super().delete(idx)

    def on_nid_changed(self, old_nid, new_nid):
        self._icon_cache.pop(old_nid, None)
