from typing import Optional, Tuple
from app.utilities.typing import Pos
from app.utilities import utils

from app.map_maker.terrain import Terrain
from app.map_maker.painter_utils import Painter
from app.map_maker.utilities import random_choice, random_random

class PoolPainter(Painter):
    """
    Selects the correct painter coordinate for the tile by determining
    what kind of shading should be painted on the water.
    For instance, if a wall/floor is to the left of this tile, the painter
    will select a tile that has shading on the left to make the shadow appear
    """
    autotiles = {
        (0, 0): 0, (1, 0): 1, (1, 1): 2, (1, 2): 3, (1, 3): 4, (1, 4): 5,
        (2, 0): 6, (3, 0): 7, (4, 0): 7,
    }

    # How far _distance_to_closest_nonpool looks for a non-pool tile. MapPrefab
    # marks the pool within this radius of every edit for update, so it must match
    nonpool_search_radius = 2

    def has_autotiles(self) -> bool:
        return True

    @staticmethod
    def _distance_to_closest_nonpool(tilemap, pos: Pos) -> float:
        """
        get_coord only compares this distance against an open pool threshold
        below 3, so only non-pool tiles less than 3 tiles away matter. All of
        them lie within nonpool_search_radius tiles along each axis; anything
        farther counts as no non-pool tile (99)
        """
        min_distance: float = 99
        r = PoolPainter.nonpool_search_radius
        for x in range(pos[0] - r, pos[0] + r + 1):
            for y in range(pos[1] - r, pos[1] + r + 1):
                other_pos = (x, y)
                if other_pos in tilemap.terrain_grid and tilemap.get_terrain(other_pos) != Terrain.POOL:
                    distance = utils.distance(pos, other_pos)
                    if distance < min_distance:
                        min_distance = distance
        return min_distance

    @staticmethod
    def is_column_bottom(tilemap, pos: Pos) -> bool:
        """
        Returns whether the position is the bottom of a wall column
        """
        north, _, _, _ = tilemap.get_cardinal_terrain(pos)
        return north == Terrain.COLUMN

    @staticmethod
    def get_shading(tilemap, pos: Pos) -> Tuple[bool, bool, bool]:
        north, _, _, west = tilemap.get_cardinal_terrain(pos)
        top, left, column = False, False, False

        if north and north != Terrain.POOL:
            top = True
        if west and west != Terrain.POOL:
            left = True
        if PoolPainter.is_column_bottom(tilemap, pos):
            column = True
        return top, left, column

    def get_shading_coord(self, tilemap, pos: Pos) -> Optional[Pos]:
        top, left, column = self.get_shading(tilemap, pos)

        shading_coord = None
        if left and top:
            pass  # Handled by regular sprite
        elif left:
            shading_coord = (0, 0)
        elif top:
            shading_coord = (1, 0)

        return shading_coord

    def get_column_coord(self, tilemap, pos: Pos) -> Optional[Pos]:
        top, left, column = self.get_shading(tilemap, pos)

        column_coord = None
        if column and left:
            column_coord = (4, 0)
        elif column:
            column_coord = (3, 0)
        elif top and left:
            column_coord = (2, 0)

        return column_coord

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        dist = PoolPainter._distance_to_closest_nonpool(tilemap, pos)
        # _distance_to_closest_nonpool relies on this threshold staying below 3
        if dist > (1 + 2*random_random(pos)):  # Open Sea
            coord = random_choice([(1, k) for k in range(self.limit[1])], pos)
        else:  # Close Sea
            coord = random_choice([(0, k) for k in range(self.limit[0])], pos)
        column_coord = self.get_column_coord(tilemap, pos)
        # Overwrite coord
        if column_coord in ((2, 0), (3, 0), (4, 0)):
            coord = column_coord
        return coord

class PoolBridgePainter(Painter):
    def get_coord(self, tilemap, pos: Pos) -> Pos:
        coord = random_choice([(0, k) for k in range(self.limit[0])], pos)
        return coord

    @staticmethod
    def get_shading(tilemap, pos: Pos) -> bool:
        _, _, _, west = tilemap.get_cardinal_terrain(pos)
        left = False

        if west not in (Terrain.POOL, Terrain.POOL_BRIDGE, *Terrain.get_all_floor()):
            left = True
        return left

    def get_shading_coord(self, tilemap, pos: Pos) -> Optional[Pos]:
        left = self.get_shading(tilemap, pos)

        shading_coord = None
        if left:
            shading_coord = (1, 0)

        return shading_coord
