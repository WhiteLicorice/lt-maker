from typing import Dict

import pygame

from app.utilities.typing import Pos

from app.map_maker.painter_utils import Painter
from app.map_maker.painters import FloorPainter, RuinedFloorPainter, GrassFloorPainter
from app.map_maker.palette_collection import Palette
from app.map_maker.pygame_renderers.pygame_palette import get_pygame_palette
from app.map_maker.pygame_renderers.renderer_utils import find_limit16
from app.map_maker.pygame_renderers import SimpleRenderer

class SimpleShadingRenderer(SimpleRenderer):
    def get_sprite_coord(self, tilemap, position: Pos):
        coord = self.painter.get_coord(tilemap, position)
        shading_coord = self.painter.get_shading_coord(tilemap, position)
        return coord, shading_coord

    def draw_sprite(self, coord, autotile_num: int) -> pygame.Surface:
        coord, shading_coord = coord
        base_image = self.palette.get_image16(self.painter, coord, autotile_num)

        if shading_coord is not None:
            shading_image = self.palette.get_shading_image16(self.painter, shading_coord)
            base_image.blit(shading_image, (0, 0))
        return base_image

class PoolShadingRenderer(SimpleShadingRenderer):
    """
    Only difference is that limit is set to 2
    To handle both open and non-open pool
    """
    def set_palette(self, palette: Palette):
        self.palette = get_pygame_palette(palette)
        limit: Dict[int, int] = {i: find_limit16(self.palette.get_full_image(), i) for i in range(2)}
        self.painter.set_limit(limit)

class FloorShadingRenderer(SimpleRenderer):
    """
    Floor Shading Renderer needs to be able to switch between painters at runtime
    depending on which palette collection is selected
    """
    def __init__(self, metadata_arg: str, palette: Palette):
        self.metadata_arg = metadata_arg
        self.painters = {
            'default': FloorPainter(),
            'ruins': RuinedFloorPainter(),
            'grass': GrassFloorPainter(),
        }
        self.set_palette(palette)

    def set_palette(self, palette: Palette):
        self.palette = get_pygame_palette(palette)
        zero_limit = find_limit16(self.palette.get_full_image(), 0)
        self.painters['default'].set_limit({0: zero_limit})
        full_limit = {k: find_limit16(self.palette.get_full_image(), k) for k in range(16)}
        self.painters['ruins'].set_limit(full_limit)
        self.painters['grass'].set_limit(full_limit)

    @property
    def painter(self) -> Painter:
        palette_collection = self.palette.parent
        floor_type = palette_collection.metadata.get(self.metadata_arg, 'default')
        return self.painters.get(floor_type, self.painters['default'])

    def get_sprite_coord(self, tilemap, position: Pos):
        coord = self.painter.get_coord(tilemap, position)
        shading_coord = self.painter.get_shading_coord(tilemap, position)

        extra_coord = None
        pillar_coord = self.painter.get_pillar_coord(tilemap, position)
        if pillar_coord:
            extra_coord = pillar_coord
        elif self.painter.is_column_bottom(tilemap, position):
            extra_coord = (7, 0)
        return coord, shading_coord, extra_coord

    def draw_sprite(self, coord, autotile_num: int) -> pygame.Surface:
        coord, shading_coord, extra_coord = coord

        base_image = self.palette.get_image16(self.painter, coord, autotile_num)

        shading_image = None
        if shading_coord is not None:
            shading_image = self.palette.get_shading_image16(self.painter, shading_coord)

        extra_image = None
        if extra_coord:
            extra_image = self.palette.get_shading_image16(self.painter, extra_coord)

        if shading_image:
            base_image.blit(shading_image, (0, 0))
        if extra_image:
            base_image.blit(extra_image, (0, 0))

        return base_image
