from __future__ import annotations

from PyQt5 import QtGui
from PyQt5.QtCore import Qt

from typing import Dict, Set, Optional
from app.utilities.typing import Color3

from app.constants import COLORKEY
from app.data.resources.combat_palettes import Palette
from app.data.resources.combat_anims import Frame
from app.data.resources.default_palettes import blue as default_blue_palette

qCOLORKEY = QtGui.qRgb(*COLORKEY)
qEFFECT_COLORKEY = QtGui.qRgb(0, 0, 0)
qAlpha = QtGui.qRgba(0, 0, 0, 0)

def rgb_convert(conversion: Dict[Color3, Color3]) -> Dict[QtGui.qRgb, QtGui.qRgb]:
    return {QtGui.qRgb(*k): QtGui.qRgb(*v) for k, v in conversion.items()}

def convert_colorkey_slow(image: QtGui.QImage) -> QtGui.QImage:
    image.convertTo(QtGui.QImage.Format_ARGB32)
    for x in range(image.width()):
        for y in range(image.height()):
            if image.pixel(x, y) == qCOLORKEY:
                image.setPixel(x, y, qAlpha)
    return image

def convert_colorkey(image: QtGui.QImage) -> QtGui.QImage:
    new_image = image.convertToFormat(QtGui.QImage.Format_Indexed8)
    num_colors = new_image.colorCount()
    if num_colors > 192:
        return convert_colorkey_slow(image)
    for i in range(new_image.colorCount()):
        if new_image.color(i) == qCOLORKEY:
            new_image.setColor(i, qAlpha)
            break
    image = new_image.convertToFormat(QtGui.QImage.Format_ARGB32)
    return image

def color_convert_slow(image, conversion_dict):
    image.convertTo(QtGui.QImage.Format_ARGB32)
    for x in range(image.width()):
        for y in range(image.height()):
            current_color = image.pixel(x, y)
            if current_color in conversion_dict:
                new_color = conversion_dict[current_color]
                image.setPixel(x, y, new_color)
    return image

def color_convert(image, conversion_dict):
    new_image = image.convertToFormat(QtGui.QImage.Format_Indexed8)
    num_colors = new_image.colorCount()
    if num_colors > 192:
        return color_convert_slow(image, conversion_dict)
    # Figure out what color conversions to make
    color_conv = {}
    for old_color, new_color in conversion_dict.items():
        for i in range(new_image.colorCount()):
            if new_image.color(i) == old_color:
                color_conv[i] = new_color
    # Actually make them
    # Got to do this so swapped colors don't just replace all of one of the color with the second color swapped
    for i, new_color in color_conv.items():
        new_image.setColor(i, new_color)
    return new_image.convertToFormat(QtGui.QImage.Format_RGB32)

def color_convert_pixmap(pixmap: QtGui.QPixmap, convert_dict: dict) -> QtGui.QPixmap:
    im = pixmap.toImage()
    im = color_convert(im, convert_dict)
    pixmap = QtGui.QPixmap.fromImage(im)
    return pixmap

def convert_to_correct_colorkey(pixmap: QtGui.QPixmap) -> QtGui.QPixmap:
    """
    Checks if the topleft pixel is the correct colorkey backgroun
    If it's not, converts all of that color to the correct colorkey
    """
    im = pixmap.toImage()
    if im.pixel(0, 0) != qCOLORKEY:
        im = color_convert(im, {im.pixel(0, 0): qCOLORKEY})
        pixmap = QtGui.QPixmap.fromImage(im)
    return pixmap

def find_palette(image: QtGui.QImage) -> list:
    palette = []
    # Goes row by row, finding the palette in that order
    assert image.width() > 0 and image.height() > 0
    for y in range(image.height()):
        for x in range(image.width()):
            current_color = image.pixel(x, y)
            if current_color not in palette:
                palette.append(current_color)
    color_palette = [QtGui.QColor(p) for p in palette]
    true_palette = [(c.red(), c.green(), c.blue()) for c in color_palette]
    return true_palette

def find_palette_from_multiple(images: list) -> list:
    palette = []
    for image in images:
        assert image.width() > 0 and image.height() > 0
        for y in range(image.height()):
            for x in range(image.width()):
                current_color = image.pixel(x, y)
                if current_color not in palette:
                    palette.append(current_color)
    color_palette = [QtGui.QColor(p) for p in palette]
    true_palette = [(c.red(), c.green(), c.blue()) for c in color_palette]
    return true_palette

def get_full_palette(image) -> list:
    """
    Returns list of 3-tuples
    """
    palette = []
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            palette.append((color.red(), color.green(), color.blue()))
    return palette

def get_color_conversion(palette: Palette) -> dict:
    return {QtGui.qRgb(*color[:3]): QtGui.qRgb(0, *coord) for coord, color in palette.colors.items()}

def assign_new_colors(palette: Palette, colors: list) -> dict:
    """
    Returns the coord -> color entries for each of `colors` the palette does not
    already contain, placed in the palette's next free slots
    """
    existing = set(palette.colors.values())
    new_colors = []
    for color in colors:
        if color not in existing and color not in new_colors:
            new_colors.append(color)
    start = len(palette.colors)
    return {(int((idx + start) % 8), int((idx + start) / 8)): color
            for idx, color in enumerate(new_colors)}

def find_unconvertible_colors(image: QtGui.QImage, convert_dict: dict) -> list:
    """
    Returns the colors in the image that the conversion dict has no entry for.
    Those pixels survive into the sheet as literal RGB, where every later reader
    misinterprets them as the palette coord (green, blue)
    """
    return [color for color in find_palette(image) if QtGui.qRgb(*color) not in convert_dict]

def get_coord_conversion(palette: Palette) -> dict:
    return {QtGui.qRgb(0, *coord): QtGui.qRgb(*color[:3]) for coord, color in palette.colors.items()}

def get_coords_used_in_frame(frame: Frame) -> list:
    im = QtGui.QImage(frame.pixmap)
    unique_colors = find_palette(im)
    coords = [(uc[1], uc[2]) for uc in unique_colors]
    return coords

def convert_gba(image):
    for i in range(image.colorCount()):
        color = QtGui.QColor(image.color(i))
        new_color = (color.red() // 8 * 8), (color.green() // 8 * 8), (color.blue() // 8 * 8)
        image.setColor(i, QtGui.qRgb(*new_color))
    return image

def find_closest_match(color: QtGui.QColor, palette: Set[Color3]) -> Optional[Color3]:
    #   Given a color and a palette, find the palette color that closest matches the color
    #   Return None if color is present in the palette

    rgb = (color.red(), color.green(), color.blue())
    if rgb in palette:
        return None

    closest_diff = (256 ** 2) * 3   # Largest value possible
    for c in palette:
        diff = sum((c[i] - rgb[i])**2 for i in range(3))
        if diff < closest_diff:
            closest_rgb = c
            closest_diff = diff
    return closest_rgb

def convert_default_palette(image: QtGui.QImage) -> Optional[QtGui.QImage]:
    #   Recolor the given image using only colors from the default palette
    #   Return None if no recolor needed (the image already uses only colors from default palette)

    did_something = False
    palette = set(default_blue_palette)
    for i in range(image.colorCount()):
        color = QtGui.QColor(image.color(i))
        if new_color := find_closest_match(color, palette):
            image.setColor(i, QtGui.qRgb(*new_color))
            did_something = True
    if did_something:
        return image

def convert_default_palette_pixmap(pixmap: QtGui.QPixmap) -> Optional[QtGui.QPixmap]:
    #   Recolor the given image using only colors from the default palette
    #   Return None if no recolor needed (the image already uses only colors from default palette)

    im = pixmap.toImage()
    im.convertTo(QtGui.QImage.Format_Indexed8)
    if im := convert_default_palette(im):
        pixmap = QtGui.QPixmap.fromImage(im)
        return pixmap

def get_bbox(image, exclude_color: Optional[QtGui.qRgb] = None):
    min_x, max_x = image.width(), 0
    min_y, max_y = image.height(), 0

    # Assumes topleft color is exclude color
    # unless top right is qCOLORKEY, then uses qCOLORKEY
    if not exclude_color:
        exclude_color = image.pixel(0, 0)
        test_color = image.pixel(image.width() - 1, 0)
        if test_color == qCOLORKEY:
            exclude_color = qCOLORKEY

    for x in range(image.width()):
        for y in range(image.height()):
            current_color = image.pixel(x, y)
            if current_color != exclude_color:
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y
    # Returns x, y, width, height rect
    return (min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)

def qtkey_to_string(qtkey: Qt.Key):
    return QtGui.QKeySequence(qtkey).toString()

def human_readable(convert_dict) -> dict:
    return {
        (QtGui.QColor(k).red(), QtGui.QColor(k).green(), QtGui.QColor(k).blue()):
        (QtGui.QColor(v).red(), QtGui.QColor(v).green(), QtGui.QColor(v).blue())
        for k, v in convert_dict.items()}
