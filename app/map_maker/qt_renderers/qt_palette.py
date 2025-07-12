from __future__ import annotations
from typing import TYPE_CHECKING

from dataclasses import dataclass

from PyQt5.QtGui import QPixmap, QPainter

from app.utilities.typing import Pos

from app.map_maker.painter_utils import Painter
from app.map_maker.qt_renderers.renderer_utils import get_pixmap8, get_pixmap16
if TYPE_CHECKING:
    from app.map_maker.palette_collection import PaletteCollection

@dataclass
class QtPalette:
    parent: PaletteCollection
    fn: str
    autotile_fn: str = None
    shading_fn: str = None
    pixmap: QPixmap = None
    autotile_pixmap: QPixmap = None
    shading_pixmap: QPixmap = None

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
        if not self.pixmap:
            self.pixmap = QPixmap(self.fn)
        base_pixmap = QPixmap(16, 16)
        topleft = self.subsurface8(painter, coord1, autotile_num)
        topright = self.subsurface8(painter, coord2, autotile_num)
        bottomright = self.subsurface8(painter, coord3, autotile_num)
        bottomleft = self.subsurface8(painter, coord4, autotile_num)
        painter = QPainter()
        painter.begin(base_pixmap)
        painter.drawPixmap(0, 0, topleft)
        painter.drawPixmap(8, 0, topright)
        painter.drawPixmap(0, 8, bottomleft)
        painter.drawPixmap(8, 8, bottomright)
        painter.end()
        return base_pixmap
