from app.map_maker.painter_utils import Painter
from app.map_maker.qt_renderers.qt_palette import QtPalette
from app.map_maker.qt_renderers.renderer_utils import find_limit16

from app.map_maker.qt_renderers import SimpleRenderer8

class SeaRenderer(SimpleRenderer8):
    def __init__(self, painter: Painter, palette: QtPalette):
        self.painter = painter
        self.set_palette(palette)

    def set_palette(self, palette: QtPalette):
        self.palette = palette

        limit = {k: find_limit16(palette.get_full_pixmap(), k) for k in range(16)}
        sand_limit = {k: find_limit16(palette.get_full_pixmap(), k, self.painter.sand_start_px) for k in range(16)}
        self.painter.set_limit(limit)
        self.painter.sand_limit = sand_limit
