from typing import Dict

from app.utilities.typing import Pos

from PyQt5.QtGui import QPixmap

from app.map_maker.painter_utils import Painter
from app.map_maker.qt_renderers.qt_palette import QtPalette
from app.map_maker.qt_renderers.renderer_utils import find_limit8, find_limit16

class SimpleRenderer:
    def __init__(self, painter: Painter, palette: QtPalette):
        self.painter = painter
        self.set_palette(palette)

    def set_palette(self, palette: QtPalette):
        self.palette = palette
        limit = find_limit16(palette.get_full_pixmap(), 0)
        self.painter.set_limit({0: limit})

    def get_display_pixmap(self) -> QPixmap:
        return self.palette.get_pixmap16(self.painter, self.painter.base_coord, 0)

    def determine_sprite(self, tilemap, position: Pos, autotile_num: int) -> QPixmap:
        coord = self.painter.get_coord(tilemap, position)
        return self.palette.get_pixmap16(self.painter, coord, autotile_num)

class SimpleRenderer8(SimpleRenderer):
    def __init__(self, painter: Painter, palette: QtPalette):
        self.painter = painter

    def set_palette(self, palette: QtPalette):
        self.palette = palette
        limit = find_limit8(palette.get_full_pixmap(), 0)
        self.painter.set_limit({0: limit})

    def get_display_pixmap(self) -> QPixmap:
        coord1 = self.painter.base_coord
        coord2 = self.painter.base_coord[0], self.painter.base_coord[1] + 1
        coord3 = self.painter.base_coord[0], self.painter.base_coord[1] + 2
        coord4 = self.painter.base_coord[0], self.painter.base_coord[1] + 3
        return self.palette.get_pixmap8(self.painter, coord1, coord2, coord3, coord4, 0)

    def determine_sprite(self, tilemap, position: Pos, autotile_num: int) -> QPixmap:
        coord1, coord2, coord3, coord4 = self.painter.get_coord(tilemap, position)
        return self.palette.get_pixmap8(self.painter, coord1, coord2, coord3, coord4, autotile_num)

class DisplayRenderer8(SimpleRenderer8):
    """Identical to SimpleRenderer8 just modifies 
    how the display pixmap is drawn
    to always use the base coord position of the base image
    """
    def get_display_pixmap(self) -> QPixmap:
        coord1 = self.painter.base_coord
        coord2 = self.painter.base_coord[0] + 1, self.painter.base_coord[1]
        coord3 = self.painter.base_coord[0] + 1, self.painter.base_coord[1] + 1
        coord4 = self.painter.base_coord[0], self.painter.base_coord[1] + 1
        return self.palette.get_pixmap8(self.painter, coord1, coord2, coord3, coord4, 0)

class LimitRenderer16(SimpleRenderer):
    """
    Finds the full vertical limit of the drawn part of the .png
    for each column (0 - 15)
    """
    def __init__(self, painter: Painter, palette: QtPalette):
        self.painter = painter
        self.set_palette(palette)

    def set_palette(self, palette: QtPalette):
        self.palette = palette
        limit: Dict[int, int] = {i: find_limit16(palette.get_full_pixmap(), i) for i in range(16)}
        self.painter.set_limit(limit)

class LimitRenderer8(SimpleRenderer8):
    """
    Finds the full vertical limit of the drawn part of the .png
    for each column (0 - 15)
    """
    def __init__(self, painter: Painter, palette: QtPalette):
        self.painter = painter
        self.set_palette(palette)
        
    def set_palette(self, palette: QtPalette):
        self.palette = palette
        limit: Dict[int, int] = {i: find_limit8(palette.get_full_pixmap(), i) for i in range(16)}
        self.painter.set_limit(limit)
