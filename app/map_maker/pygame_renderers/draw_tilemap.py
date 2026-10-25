# pygame mirror of app/map_maker/editor/draw_tilemap.py
from typing import Set
import time

import pygame

from app.constants import TILEWIDTH, TILEHEIGHT, AUTOTILE_FRAMES

from app.map_maker.map_prefab import MapPrefab
from app.map_maker.terrain import Terrain

from app.map_maker.pygame_renderers.renderer_database import RENDERERS

last_autotile_num = 0

def draw_tilemap(tilemap: MapPrefab, autotile_fps=29) -> pygame.Surface:
    image = pygame.Surface((tilemap.width * TILEWIDTH,
                            tilemap.height * TILEHEIGHT),
                           pygame.SRCALPHA, 32)

    ms = time.time_ns() // 1_000_000
    if autotile_fps:
        autotile_wait = autotile_fps * 16.66
        autotile_num = int(ms / autotile_wait) % AUTOTILE_FRAMES
    else:
        autotile_num = 0

    # Process terrain
    processed_terrains: Set[Terrain] = set()
    for pos in sorted(tilemap.terrain_grid):
        # Determine what terrain is in this position
        terrain = tilemap.get_terrain(pos)
        if not terrain:
            continue

        # Only process the ones that need to be updated
        if pos in tilemap.terrain_grid_to_update:
            renderer = RENDERERS.get(terrain)
            if terrain not in processed_terrains:
                renderer.painter.single_process(tilemap)
                processed_terrains.add(terrain)
            coord = renderer.get_sprite_coord(tilemap, pos)
            if pos in tilemap.autotile_set:
                tilemap.autotile_coords[pos] = coord
            tilemap.tile_grid[pos] = renderer.draw_sprite(coord, autotile_num)

    # Autotiles
    global last_autotile_num
    if autotile_num != last_autotile_num:
        for pos in sorted(tilemap.autotile_set):
            if pos not in tilemap.terrain_grid_to_update:
                # Determine what terrain is in this position
                terrain = tilemap.get_terrain(pos)
                if not terrain:
                    continue
                # Only the frame changed, so reuse the coord from the last update
                coord = tilemap.autotile_coords[pos]
                tilemap.tile_grid[pos] = RENDERERS.get(terrain).draw_sprite(coord, autotile_num)
        last_autotile_num = autotile_num

    # Draw the tile grid
    for pos, sprite in tilemap.tile_grid.items():
        assert sprite.get_width() == TILEWIDTH, (pos, sprite.get_width())
        assert sprite.get_height() == TILEHEIGHT, (pos, sprite.get_height())
        image.blit(sprite, (pos[0] * TILEWIDTH, pos[1] * TILEHEIGHT))

    # Make sure we don't need to update it anymore
    tilemap.terrain_grid_to_update.clear()

    return image

def simple_draw_tilemap(tilemap: MapPrefab) -> pygame.Surface:
    image = pygame.Surface((tilemap.width * TILEWIDTH,
                            tilemap.height * TILEHEIGHT),
                           pygame.SRCALPHA, 32)

    # Draw the tile grid
    for pos, sprite in tilemap.tile_grid.items():
        assert sprite.get_width() == TILEWIDTH, sprite.get_width()
        assert sprite.get_height() == TILEHEIGHT, sprite.get_height()
        image.blit(sprite, (pos[0] * TILEWIDTH, pos[1] * TILEHEIGHT))

    return image
