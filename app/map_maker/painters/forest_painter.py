from app.utilities.typing import Pos

from app.map_maker.painter_utils import Painter
from app.map_maker.terrain import Terrain
from app.map_maker.utilities import \
    flood_fill, find_bounds, edge_random, random_choice

from app.utilities.algorithms.interpolation import lerp
from app.utilities.utils import clamp

class ForestPainter(Painter):
    forest_like = (Terrain.FOREST, Terrain.THICKET)
    base_coord = (14, 0)
    
    @property
    def check_flood_fill(self):
        return True

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        north, east, south, west = tilemap.get_cardinal_terrain(pos)
        blob_positions = flood_fill(tilemap, pos)
        _, _, _, _, blob_width, blob_height, center_x, center_y = \
            find_bounds(tilemap, blob_positions)
        my_radius_width: float = abs(pos[0] + 0.5 - center_x)
        my_radius_height: float = abs(pos[1] + 0.5 - center_y)
        depth_w: float = (blob_width / 2) - my_radius_width
        depth_h: float = (blob_height / 2) - my_radius_height
        chance_w: float = lerp(1, 0, depth_w/4)
        chance_h: float = lerp(1, 0, depth_h/4)
        chance_to_lose_adjacent_edges: float = clamp(max(chance_w, chance_h), 0, 1)

        north_edge = bool(north and north not in self.forest_like)  # Whether we don't border a forest
        if not north_edge and north and north != Terrain.THICKET:  # We border a forest
            north_edge = (edge_random((pos[0], pos[1] - 1), pos) < chance_to_lose_adjacent_edges)
        east_edge = bool(east and east not in self.forest_like)
        if not east_edge and east and east != Terrain.THICKET:  # We border a forest
            east_edge = (edge_random(pos, (pos[0] + 1, pos[1])) < chance_to_lose_adjacent_edges)
        south_edge = bool(south and south not in self.forest_like)
        if not south_edge and south and south != Terrain.THICKET:  # We border a forest
            south_edge = (edge_random(pos, (pos[0], pos[1] + 1)) < chance_to_lose_adjacent_edges)
        west_edge = bool(west and west not in self.forest_like)
        if not west_edge and west and west != Terrain.THICKET:  # We border a forest
            west_edge = (edge_random((pos[0] - 1, pos[1]), pos) < chance_to_lose_adjacent_edges)
        
        total_index = \
            north_edge + 2 * east_edge + 4 * south_edge + 8 * west_edge
        index1 = north_edge + 8 * west_edge
        index2 = north_edge + 2 * east_edge
        index3 = 4 * south_edge + 2 * east_edge
        index4 = 4 * south_edge + 8 * west_edge
        if total_index == 15 and random_choice([1, 2, 3], pos) != 3:  # When by itself
            y = random_choice([0, 2], pos)
            new_coord1 = (14, y)
            new_coord2 = (15, y)
            new_coord3 = (15, y + 1)
            new_coord4 = (14, y + 1)
        else:
            new_coord1 = (index1, {0: 0, 1: 0, 8: 0, 9: 0}[index1])
            new_coord2 = (index2, {0: 1, 1: 1, 2: 0, 3: 0}[index2])
            new_coord3 = (index3, {0: 3, 2: 1, 4: 1, 6: 0}[index3])
            new_coord4 = (index4, {0: 2, 4: 0, 8: 1, 12: 0}[index4])
        
        return new_coord1, new_coord2, new_coord3, new_coord4
