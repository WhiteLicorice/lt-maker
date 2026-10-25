from typing import Dict

import pygame

from app.utilities.typing import Pos

from app.map_maker.painter_utils import Painter
from app.map_maker.palette_collection import Palette
from app.map_maker.pygame_renderers.pygame_palette import get_pygame_palette
from app.map_maker.pygame_renderers.renderer_utils import find_limit8, find_limit16

class SimpleRenderer:
    def __init__(self, painter: Painter, palette: Palette):
        self.painter = painter
        self.set_palette(palette)

    def set_palette(self, palette: Palette):
        self.palette = get_pygame_palette(palette)
        limit = find_limit16(self.palette.get_full_image(), 0)
        self.painter.set_limit({0: limit})

    def get_display_sprite(self) -> pygame.Surface:
        return self.palette.get_image16(self.painter, self.painter.base_coord, 0)

    def get_sprite_coord(self, tilemap, position: Pos):
        """Everything draw_sprite needs to draw this position.
        Does not depend on the autotile frame, so the autotile
        frames of a position can be drawn from a single call"""
        return self.painter.get_coord(tilemap, position)

    def draw_sprite(self, coord, autotile_num: int) -> pygame.Surface:
        return self.palette.get_image16(self.painter, coord, autotile_num)

    def determine_sprite(self, tilemap, position: Pos, autotile_num: int) -> pygame.Surface:
        return self.draw_sprite(self.get_sprite_coord(tilemap, position), autotile_num)

class SimpleRenderer8(SimpleRenderer):
    # Unlike the Qt version, __init__ (inherited) applies the palette
    # immediately -- the engine has no editor to call set_palette later

    def set_palette(self, palette: Palette):
        self.palette = get_pygame_palette(palette)
        limit = find_limit8(self.palette.get_full_image(), 0)
        self.painter.set_limit({0: limit})

    def get_display_sprite(self) -> pygame.Surface:
        coord1 = self.painter.base_coord
        coord2 = self.painter.base_coord[0], self.painter.base_coord[1] + 1
        coord3 = self.painter.base_coord[0], self.painter.base_coord[1] + 2
        coord4 = self.painter.base_coord[0], self.painter.base_coord[1] + 3
        return self.palette.get_image8(self.painter, coord1, coord2, coord3, coord4, 0)

    def draw_sprite(self, coord, autotile_num: int) -> pygame.Surface:
        coord1, coord2, coord3, coord4 = coord
        return self.palette.get_image8(self.painter, coord1, coord2, coord3, coord4, autotile_num)

class DisplayRenderer8(SimpleRenderer8):
    """Identical to SimpleRenderer8 just modifies
    how the display sprite is drawn
    to always use the base coord position of the base image
    """
    def get_display_sprite(self) -> pygame.Surface:
        coord1 = self.painter.base_coord
        coord2 = self.painter.base_coord[0] + 1, self.painter.base_coord[1]
        coord3 = self.painter.base_coord[0] + 1, self.painter.base_coord[1] + 1
        coord4 = self.painter.base_coord[0], self.painter.base_coord[1] + 1
        return self.palette.get_image8(self.painter, coord1, coord2, coord3, coord4, 0)

class LimitRenderer16(SimpleRenderer):
    """
    Finds the full vertical limit of the drawn part of the .png
    for each column (0 - 15)
    """
    def __init__(self, painter: Painter, palette: Palette):
        self.painter = painter
        self.set_palette(palette)

    def set_palette(self, palette: Palette):
        self.palette = get_pygame_palette(palette)
        limit: Dict[int, int] = {i: find_limit16(self.palette.get_full_image(), i) for i in range(16)}
        self.painter.set_limit(limit)

class LimitRenderer8(SimpleRenderer8):
    """
    Finds the full vertical limit of the drawn part of the .png
    for each column (0 - 15)
    """
    def __init__(self, painter: Painter, palette: Palette):
        self.painter = painter
        self.set_palette(palette)

    def set_palette(self, palette: Palette):
        self.palette = get_pygame_palette(palette)
        limit: Dict[int, int] = {i: find_limit8(self.palette.get_full_image(), i) for i in range(16)}
        self.painter.set_limit(limit)
