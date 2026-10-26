from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Tuple

from dataclasses import dataclass, field

from PyQt5.QtGui import QPixmap, QPainter

from app.utilities.typing import Pos

from app.map_maker.painter_utils import Painter
from app.map_maker.qt_renderers.renderer_utils import get_pixmap8, get_pixmap16
if TYPE_CHECKING:
    from app.map_maker.palette_collection import Palette, PaletteCollection

@dataclass
class QtPalette:
    parent: PaletteCollection
    fn: str
    autotile_fn: str = None
    shading_fn: str = None
    pixmap: QPixmap = None
    autotile_pixmap: QPixmap = None
    shading_pixmap: QPixmap = None
    # Key: (painter, coord1, coord2, coord3, coord4, autotile_num), Value: get_pixmap8 of them
    pixmap8_cache: Dict[Tuple[Painter, Pos, Pos, Pos, Pos, int], QPixmap] = field(default_factory=dict)

    def get_full_pixmap(self) -> QPixmap:
        if not self.pixmap:
            self.pixmap = QPixmap(self.fn)
        return self.pixmap

    def get_pixmap16(self, painter: Painter, coord: Pos, autotile_num: int) -> QPixmap:
        if not self.pixmap:
            self.pixmap = QPixmap(self.fn)
        if painter.has_autotiles() and coord in painter.autotiles:
            column = painter.autotiles[coord]
            if not self.autotile_pixmap:
                self.autotile_pixmap = QPixmap(self.autotile_fn)
            return get_pixmap16(self.autotile_pixmap, (column, autotile_num))
        else:
            return get_pixmap16(self.pixmap, coord)

    def get_shading_pixmap16(self, painter: Painter, coord: Pos) -> QPixmap:
        if not self.shading_pixmap:
            self.shading_pixmap = QPixmap(self.shading_fn)
        return get_pixmap16(self.shading_pixmap, coord)

    def subsurface8(self, painter: Painter, coord: Pos, autotile_num: int) -> QPixmap:
        if not self.pixmap:
            self.pixmap = QPixmap(self.fn)
        if painter.has_autotiles() and coord in painter.autotiles:
            column = painter.autotiles[coord]
            if not self.autotile_pixmap:
                self.autotile_pixmap = QPixmap(self.autotile_fn)
            return get_pixmap8(self.autotile_pixmap, (column, autotile_num))
        else:
            return get_pixmap8(self.pixmap, coord)

    def get_pixmap8(
            self, painter: Painter, 
            coord1: Pos, coord2: Pos, coord3: Pos, coord4: Pos, 
            autotile_num: int) -> QPixmap:
        # Many tiles share the same four quarters, so each combination is put together once
        key = (painter, coord1, coord2, coord3, coord4, autotile_num)
        if key not in self.pixmap8_cache:
            if not self.pixmap:
                self.pixmap = QPixmap(self.fn)
            base_pixmap = QPixmap(16, 16)
            topleft = self.subsurface8(painter, coord1, autotile_num)
            topright = self.subsurface8(painter, coord2, autotile_num)
            bottomright = self.subsurface8(painter, coord3, autotile_num)
            bottomleft = self.subsurface8(painter, coord4, autotile_num)
            qpainter = QPainter()
            qpainter.begin(base_pixmap)
            qpainter.drawPixmap(0, 0, topleft)
            qpainter.drawPixmap(8, 0, topright)
            qpainter.drawPixmap(0, 8, bottomleft)
            qpainter.drawPixmap(8, 8, bottomright)
            qpainter.end()
            self.pixmap8_cache[key] = base_pixmap
        # The copy shares the cached pixels, but painting on it leaves the cache as it is
        return QPixmap(self.pixmap8_cache[key])

_qt_palette_cache: Dict[int, QtPalette] = {}

def get_qt_palette(palette: Palette) -> QtPalette:
    """Wraps a framework-agnostic Palette in a QtPalette (cached by identity
    so the underlying pixmaps are only loaded once per palette)."""
    key = id(palette)
    if key not in _qt_palette_cache:
        _qt_palette_cache[key] = QtPalette(
            palette.parent, palette.fn, palette.autotile_fn, palette.shading_fn)
    return _qt_palette_cache[key]
