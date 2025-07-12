from typing import Tuple

from app.utilities.typing import Pos

from app.map_maker.utilities import random_choice, random_random, edge_random, get_random_seed
from app.map_maker.painters import WangEdge16Painter
from app.map_maker.terrain import Terrain
from app.utilities import utils

class SeaPainter(WangEdge16Painter):
    terrain_like = (Terrain.SEA, Terrain.RIVER, Terrain.BRIDGEH, Terrain.BRIDGEV, Terrain.WALL_TOP, Terrain.WALL_BOTTOM)
    base_coord = (15, 0)
    serration_chance = 0.6
    sand_start_px = 144
    sand_limit = {}

    autotiles = {
        (0, 4): 0, (0, 5): 1, (0, 6): 2, (0, 7): 2, (0, 8): 3, (0, 9): 3, (0, 10): 3, (0, 11): 2, (0, 12): 4, (0, 13): 2, (0, 14): 5, (0, 15): 3, (0, 16): 2,
        (0, 17): 4, (1, 0): 6, (1, 1): 7, (1, 4): 2, (1, 5): 3, (1, 6): 2, (1, 7): 2, (1, 8): 3, (1, 9): 3, (1, 10): 2, (1, 11): 3, (1, 12): 3, (1, 13): 3,
        (1, 14): 3, (1, 15): 3, (1, 16): 4, (1, 17): 2, (2, 1): 8, (2, 18): 9, (3, 0): 10, (3, 18): 11, (5, 18): 12, (6, 0): 13, (6, 2): 14, (6, 6): 15, 
        (6, 18): 9, (7, 1): 16, (7, 2): 17, (7, 3): 18, (7, 4): 19, (7, 6): 19, (7, 7): 20, (7, 18): 2, (7, 19): 21, (8, 1): 22, (9, 1): 23, (10, 0): 24, 
        (10, 1): 25, (10, 18): 26, (10, 19): 27, (10, 20): 28, (10, 21): 29, (11, 0): 30, (11, 1): 6, (12, 1): 31, (12, 3): 32, (12, 5): 33, (12, 7): 34, 
        (12, 19): 35, (13, 1): 36, (13, 2): 37, (13, 4): 38, (13, 5): 39, (13, 6): 40, (13, 7): 41, (13, 18): 42, (13, 19): 43, (14, 1): 44, (14, 2): 24, 
        (14, 3): 25, (14, 4): 45, (14, 5): 46, (14, 7): 25, (14, 18): 26, (14, 19): 27, (14, 20): 28, (14, 21): 29, (15, 2): 2, (15, 3): 43, (15, 4): 2, 
        (15, 5): 43, (15, 6): 2, (15, 7): 43, (15, 18): 2, (15, 19): 43, (15, 20): 2, (15, 21): 43, (16, 18): 47, (16, 19): 48, (18, 1): 49, (18, 3): 50, 
        (18, 4): 0, (18, 6): 0, (18, 7): 51, (18, 18): 0, (18, 19): 48, (19, 0): 52, (19, 6): 53, (19, 18): 11, (20, 18): 54, (20, 19): 55, (20, 20): 56, 
        (21, 18): 57, (21, 19): 58, (21, 20): 59, (22, 1): 60, (22, 2): 0, (22, 3): 61, (22, 5): 61, (22, 7): 60, (22, 10): 62, (22, 11): 53, (22, 18): 0, 
        (22, 19): 63, (22, 20): 0, (22, 21): 55, (23, 0): 2, (23, 1): 64, (23, 3): 64, (23, 4): 2, (23, 5): 65, (23, 7): 65, (23, 18): 2, (23, 19): 58, 
        (23, 20): 2, (23, 21): 58, (24, 1): 66, (24, 2): 67, (24, 4): 68, (24, 5): 69, (24, 6): 70, (24, 7): 71, (24, 18): 47, (24, 19): 62, (25, 1): 72, 
        (25, 3): 73, (25, 5): 74, (25, 7): 75, (25, 19): 76, (26, 2): 0, (26, 3): 62, (26, 4): 0, (26, 5): 62, (26, 6): 0, (26, 7): 62, (26, 18): 0, (26, 19): 62, 
        (26, 20): 0, (26, 21): 62, (27, 0): 10, (27, 2): 30, (27, 3): 6, (27, 4): 7, (27, 5): 77, (27, 6): 53, (27, 7): 68, (27, 18): 78, (27, 19): 79, 
        (27, 20): 80, (27, 21): 81, (28, 1): 82, (28, 18): 54, (28, 19): 62, (28, 20): 83, (28, 21): 62, (28, 22): 76, (28, 23): 43, (29, 18): 57, (29, 19): 43, 
        (29, 20): 57, (29, 21): 43, (29, 22): 35, (29, 23): 62, (30, 0): 0, (30, 1): 62, (30, 2): 0, (30, 3): 62, (30, 4): 0, (30, 5): 62, (30, 6): 0, (30, 7): 1, 
        (30, 8): 0, (30, 9): 62, (31, 0): 2, (31, 1): 43, (31, 2): 2, (31, 3): 43, (31, 4): 2, (31, 5): 3, (31, 6): 2, (31, 7): 43, (31, 8): 2, (31, 9): 43
    }

    @property
    def check_flood_fill(self):
        return True

    def has_autotiles(self) -> bool:
        return True

    def _determine_index(self, tilemap, pos: Pos) -> int:
        north, east, south, west = tilemap.get_cardinal_terrain(pos)
        north_edge = bool(not north or north in self.terrain_like)
        south_edge = bool(not south or south in self.terrain_like)
        east_edge = bool(not east or east in self.terrain_like)
        west_edge = bool(not west or west in self.terrain_like)
        index = 1 * north_edge + 2 * east_edge + 4 * south_edge + 8 * west_edge
        return index

    def _near_sand(self, tilemap, pos: Pos) -> bool:
        return any(_ == Terrain.SAND for _ in tilemap.get_cardinal_terrain(pos))

    def _modify_index(self, index: int, tilemap, pos: Pos) -> int:
        # For randomly serrating the straight edges of the sea
        odd = bool((pos[0] + pos[1] + get_random_seed()) % 2)
        even = not odd
        # Left
        if index == 13:
            if odd and self._determine_index(tilemap, (pos[0], pos[1] - 1)) == 13 and edge_random((pos[0], pos[1] - 1), pos) < self.serration_chance:
                index = 12
            elif even and self._determine_index(tilemap, (pos[0], pos[1] + 1)) == 13 and edge_random(pos, (pos[0], pos[1] + 1)) < self.serration_chance:
                index = 9
        # Right
        elif index == 7:
            if odd and self._determine_index(tilemap, (pos[0], pos[1] - 1)) == 7 and edge_random((pos[0], pos[1] - 1), pos) < self.serration_chance:
                index = 6
            elif even and self._determine_index(tilemap, (pos[0], pos[1] + 1)) == 7 and edge_random(pos, (pos[0], pos[1] + 1)) < self.serration_chance:
                index = 3
        # Top
        elif index == 11:
            if odd and self._determine_index(tilemap, (pos[0] - 1, pos[1])) == 11 and edge_random((pos[0] - 1, pos[1]), pos) < self.serration_chance:
                index = 3
            elif even and self._determine_index(tilemap, (pos[0] + 1, pos[1])) == 11 and edge_random(pos, (pos[0] + 1, pos[1])) < self.serration_chance:
                index = 9
        # Bottom
        elif index == 14:
            if odd and self._determine_index(tilemap, (pos[0] - 1, pos[1])) == 14 and edge_random((pos[0] - 1, pos[1]), pos) < self.serration_chance:
                index = 6
            elif even and self._determine_index(tilemap, (pos[0] + 1, pos[1])) == 14 and edge_random(pos, (pos[0] + 1, pos[1])) < self.serration_chance:
                index = 12

        return index

    def _distance_to_closest_land(self, tilemap, pos: Pos) -> float:
        min_distance = 99
        for other_pos in tilemap.terrain_grid.keys():
            if tilemap.get_terrain(other_pos) not in (Terrain.SEA, Terrain.BRIDGEV, Terrain.BRIDGEH):
                distance = utils.distance(pos, other_pos)
                if distance < min_distance:
                    min_distance = distance
        return min_distance

    def get_coord(self, tilemap, pos: Pos) -> Tuple[Pos, Pos, Pos, Pos]:
        index = self._determine_index(tilemap, pos)
        index = self._modify_index(index, tilemap, pos)

        if index == 15:
            dist = self._distance_to_closest_land(tilemap, pos)
            if dist > (2 + 2 * random_random(pos)):  # Open Sea (adds random number between 0 and 1 for rng)
                # Measure distance to closest non sea, bridge terrain
                new_coords = [(0, k) for k in range(2, 9)]
            else:
                new_coords = [(index, k) for k in range(self.limit[index])]
        else:
            if self._near_sand(tilemap, pos):
                new_coords = [(index, k + self.sand_start_px//16) for k in range(self.sand_limit[index])]
            else:
                new_coords = [(index, k) for k in range(self.limit[index])]

        coord = random_choice(new_coords, pos)

        # Even though this should be able to use the 16x16
        # pixmaps, the sea autotiles are not set up to use 
        # 16x16, but 8x8, so we need to do this
        coord1 = (coord[0] * 2, coord[1] * 2)
        coord2 = (coord[0] * 2 + 1, coord[1] * 2)
        coord3 = (coord[0] * 2 + 1, coord[1] * 2 + 1)
        coord4 = (coord[0] * 2, coord[1] * 2 + 1)

        return coord1, coord2, coord3, coord4
