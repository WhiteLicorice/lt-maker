from typing import Tuple

from app.utilities.typing import Pos

from PyQt5.QtGui import QPixmap, qRgb

def _get_pixmap(pixmap: QPixmap, coord: Pos, tile_size: Tuple[int, int]) -> QPixmap:
    width, height = tile_size
    pix = pixmap.copy(
        coord[0] * width,
        coord[1] * height,
        width, height)
    return pix

def get_pixmap8(pixmap: QPixmap, coord: Pos) -> QPixmap:
    return _get_pixmap(pixmap, coord, (8, 8))

def get_pixmap16(pixmap: QPixmap, coord: Pos) -> QPixmap:
    return _get_pixmap(pixmap, coord, (16, 16))

def _find_limit(pixmap: QPixmap, idx: int, skip: Tuple[int, int], offset: int = 0) -> int:
    bg_color = qRgb(0, 0, 0)
    img = pixmap.toImage()
    x = idx * skip[0]
    if x >= img.width():
        return 0
    for y in range(offset, img.height(), skip[1]):
        current_color = img.pixel(x, y)
        # If we've reached the bottom of the column in our image
        if current_color == bg_color:
            return (y - offset) // skip[1]
    return img.height() // skip[1]

def find_limit8(pixmap: QPixmap, idx: int, offset: int = 0) -> int:
    return _find_limit(pixmap, idx, (8, 8), offset)

def find_limit16(pixmap: QPixmap, idx: int, offset: int = 0) -> int:
    return _find_limit(pixmap, idx, (16, 16), offset)
