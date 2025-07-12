from typing import Dict

from app.map_maker.painters import CliffPainter
from app.map_maker.qt_renderers.qt_palette import QtPalette
from app.map_maker.qt_renderers.renderer_utils import find_limit16
from app.map_maker.qt_renderers import SimpleRenderer

class CliffRenderer(SimpleRenderer):
    """
    The specific renderer used from CliffPainter
    """
    def __init__(self, painter: CliffPainter, palette: QtPalette):
        self.painter = painter
        self.set_palette(palette)

    def set_palette(self, palette: QtPalette):
        self.palette = palette
        limit: Dict[int, int] = {i: find_limit16(palette.get_full_pixmap(), i) for i in range(16)}
        self.painter.set_limit(limit)
        second_limit: Dict[int, int] = {i: find_limit16(palette.get_full_pixmap(), i, self.painter.second_start_px) for i in range(16)}
        self.painter.set_second_limit(second_limit)
