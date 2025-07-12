from typing import Dict
from app.utilities.typing import Pos

from PyQt5.QtGui import QPixmap, QPainter

from app.map_maker.painter_utils import Painter
from app.map_maker.painters import FloorPainter, RuinedFloorPainter, GrassFloorPainter
from app.map_maker.qt_renderers.qt_palette import QtPalette
from app.map_maker.qt_renderers.renderer_utils import find_limit16
from app.map_maker.qt_renderers import SimpleRenderer

class SimpleShadingRenderer(SimpleRenderer):
    def determine_sprite(self, tilemap, position: Pos, autotile_num: int) -> QPixmap:
        coord = self.painter.get_coord(tilemap, position)
        shading_coord = self.painter.get_shading_coord(tilemap, position)
        base_pix = self.palette.get_pixmap16(self.painter, coord, autotile_num)

        shading_pix = None
        if shading_coord is not None:
            shading_pix = self.palette.get_shading_pixmap16(self.painter, shading_coord)

        if shading_pix:
            qpainter = QPainter(base_pix)
            qpainter.drawPixmap(0, 0, shading_pix)
            qpainter.end()
        return base_pix

class PoolShadingRenderer(SimpleShadingRenderer):
    """
    Only difference is that limit is set to 2
    To handle both open and non-open pool
    """
    def set_palette(self, palette: QtPalette):
        self.palette = palette
        limit: Dict[int, int] = {i: find_limit16(palette.get_full_pixmap(), i) for i in range(2)}
        self.painter.set_limit(limit)

class FloorShadingRenderer(SimpleRenderer):
    """
    Floor Shading Renderer needs to be able to switch between painters at runtime
    depending on which palette collection is selected
    """
    def __init__(self, metadata_arg: str, palette: QtPalette):
        self.metadata_arg = metadata_arg
        self.painters = {
            'default': FloorPainter(),
            'ruins': RuinedFloorPainter(),
            'grass': GrassFloorPainter(),
        }

    def set_palette(self, palette: QtPalette):
        self.palette = palette
        zero_limit = find_limit16(palette.get_full_pixmap(), 0)
        self.painters['default'].set_limit({0: zero_limit})
        full_limit = {k: find_limit16(palette.get_full_pixmap(), k) for k in range(16)}
        self.painters['ruins'].set_limit(full_limit)
        self.painters['grass'].set_limit(full_limit)

    @property
    def painter(self) -> Painter:
        palette_collection = self.palette.parent
        floor_type = palette_collection.metadata.get(self.metadata_arg, 'default')
        return self.painters.get(floor_type, self.painters['default'])

    def determine_sprite(self, tilemap, position: Pos, autotile_num: int) -> QPixmap:
        coord = self.painter.get_coord(tilemap, position)
        shading_coord = self.painter.get_shading_coord(tilemap, position)

        base_pix = self.palette.get_pixmap16(self.painter, coord, autotile_num)

        shading_pix = None
        if shading_coord is not None:
            shading_pix = self.palette.get_shading_pixmap16(self.painter, shading_coord)

        extra_pix = None
        pillar_coord = self.painter.get_pillar_coord(tilemap, position)
        if pillar_coord:
            extra_pix = self.palette.get_shading_pixmap16(self.painter, pillar_coord)
        elif self.painter.is_column_bottom(tilemap, position):
            extra_pix = self.palette.get_shading_pixmap16(self.painter, (7, 0))

        qpainter = QPainter(base_pix)
        if shading_pix:
            qpainter.drawPixmap(0, 0, shading_pix)
        if extra_pix:
            qpainter.drawPixmap(0, 0, extra_pix)
        qpainter.end()

        return base_pix

# class CheckerboardFloorShadingRenderer:
#     def __init__(self, painter: Painter, 
#                  main_alpha_image_fn: str, shading_alpha_image_fn: str,
#                  main_beta_image_fn: str, shading_beta_image_fn: str):
#         self.painter = painter
#         self.main_alpha_image = engine.image_load(main_alpha_image_fn)
#         self.shading_alpha_image = engine.image_load(shading_alpha_image_fn)
#         self.main_beta_image = engine.image_load(main_beta_image_fn)
#         self.shading_beta_image = engine.image_load(shading_beta_image_fn)
#         alpha_limit: int = find_limit16(self.main_alpha_image, 0)
#         beta_limit: int = find_limit16(self.main_beta_image, 0)
#         self.painter.set_limit({0: min(alpha_limit, beta_limit)})

#     def determine_sprite(self, dungeon_tilemap: DungeonTileMap,
#                          position: Pos) -> engine.Surface:
#         coord = self.painter.get_coord(dungeon_tilemap, position)
#         shading_coord = self.painter.get_shading_coord(dungeon_tilemap, position)

#         if (position[0] + position[1]) % 2 == 1:
#             main_image = self.main_beta_image
#             shadow_image = self.shading_beta_image
#         else:
#             main_image = self.main_alpha_image
#             shadow_image = self.shading_alpha_image

#         base_image = get_image16(main_image, coord)
#         shading_image = None
#         if shading_coord is not None:
#             shading_image = get_image16(shadow_image, shading_coord)

#         extra_image = None
#         pillar_coord = self.painter.get_pillar_coord(dungeon_tilemap, position)
#         if pillar_coord:
#             extra_image = get_image16(shadow_image, pillar_coord)
#         elif self.painter.is_column_bottom(dungeon_tilemap, position):
#             extra_image = get_image16(shadow_image, (7, 0))

#         if shading_image:
#             base_image.blit(shading_image, (0, 0))
#         if extra_image:
#             base_image.blit(extra_image, (0, 0))

#         return base_image

# class Limit8ShadingRenderer(FloorShadingRenderer):
#     def __init__(self, painter: Painter, main_image_fn: str, shading_image_fn: str):
#         self.painter = painter
#         self.main_image = engine.image_load(main_image_fn)
#         self.shading_image = engine.image_load(shading_image_fn)
#         limit: Dict[int, int] = {k: find_limit8(self.main_image, k) for k in range(self.main_image.get_width() // 8)}
#         self.painter.set_limit(limit)

#     def determine_sprite(self, dungeon_tilemap: DungeonTileMap, 
#                          position: Pos) -> engine.Surface:
#         regular_coords, shading_coord = self.painter.get_coord(dungeon_tilemap, position)
#         coord1, coord2, coord3, coord4 = regular_coords

#         base_image = engine.create_surface((16, 16))
#         base_image.blit(get_image8(self.main_image, coord1), (0, 0))
#         base_image.blit(get_image8(self.main_image, coord2), (8, 0))
#         base_image.blit(get_image8(self.main_image, coord3), (8, 8))
#         base_image.blit(get_image8(self.main_image, coord4), (0, 8))

#         shading_image = None
#         if shading_coord is not None:
#             shading_image = get_image16(self.shading_image, shading_coord)

#         extra_image = None
#         pillar_coord = self.painter.get_pillar_coord(dungeon_tilemap, position)
#         if pillar_coord:
#             extra_image = get_image16(self.shading_image, pillar_coord)
#         elif self.painter.is_column_bottom(dungeon_tilemap, position):
#             extra_image = get_image16(self.shading_image, (7, 0))

#         if shading_image:
#             base_image.blit(shading_image, (0, 0))
#         if extra_image:
#             base_image.blit(extra_image, (0, 0))

#         return base_image

# class Limit16ShadingRenderer(FloorShadingRenderer):
#     def __init__(self, painter: Painter, main_image_fn: str, shading_image_fn: str):
#         self.painter = painter
#         self.main_image = engine.image_load(main_image_fn)
#         self.shading_image = engine.image_load(shading_image_fn)
#         limit: Dict[int, int] = {k: find_limit16(self.main_image, k) for k in range(self.main_image.get_width() // 16)}
#         self.painter.set_limit(limit)

#     def determine_sprite(self, dungeon_tilemap: DungeonTileMap, 
#                          position: Pos) -> engine.Surface:
#         coord, shading_coord = self.painter.get_coord(dungeon_tilemap, position)

#         base_image = get_image16(self.main_image, coord)

#         shading_image = None
#         if shading_coord is not None:
#             shading_image = get_image16(self.shading_image, shading_coord)

#         extra_image = None
#         pillar_coord = self.painter.get_pillar_coord(dungeon_tilemap, position)
#         if pillar_coord:
#             extra_image = get_image16(self.shading_image, pillar_coord)
#         elif self.painter.is_column_bottom(dungeon_tilemap, position):
#             extra_image = get_image16(self.shading_image, (7, 0))

#         if shading_image:
#             base_image.blit(shading_image, (0, 0))
#         if extra_image:
#             base_image.blit(extra_image, (0, 0))

#         return base_image
