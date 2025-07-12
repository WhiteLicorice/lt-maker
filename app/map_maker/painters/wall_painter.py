from app.utilities.typing import Pos

from app.map_maker.painter_utils import Painter
from app.map_maker.painters import WangEdge16Painter
from app.map_maker.utilities import random_choice
from app.map_maker.terrain import Terrain

class WallTopPainter(WangEdge16Painter):
    terrain_like = (Terrain.WALL_TOP, Terrain.COLUMN)
    base_coord = (2, 0)

    @staticmethod
    def get_index(tilemap, pos: Pos) -> int:
        north, east, south, west = tilemap.get_cardinal_terrain(pos)
        north_edge = bool(north in WallTopPainter.terrain_like)
        south_edge = bool(south in WallTopPainter.terrain_like)
        east_edge = bool(east in WallTopPainter.terrain_like)
        west_edge = bool(west in WallTopPainter.terrain_like)
        # Makes sure a wall going off the edge of the map appears to keep going off the edge
        if not north and not east_edge and not west_edge:
            north_edge = True
        if not south and not east_edge and not west_edge:
            south_edge = True
        if not east and not north_edge and not south_edge:
            east_edge = True
        if not west and not north_edge and not south_edge:
            west_edge = True
        index = 1 * north_edge + 2 * east_edge + 4 * south_edge + 8 * west_edge
        return index

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        index = WallTopPainter.get_index(tilemap, pos)
        ne, se, sw, nw = tilemap.get_diagonal_terrain(pos)
        # Edge is true when we have an adjacent walllike
        coord = random_choice([(index, k) for k in range(self.limit[index])], pos)

        if index in (12, 13) and sw == Terrain.WALL_TOP:
            coord = (15, 5)  # Requires walls at at least (W, SW, S)
        elif index in (6, 7) and se == Terrain.WALL_TOP:
            coord = (15, 4)  # Requires walls at at least (S, SE, E)
        elif index in (14, 15) and se == Terrain.WALL_TOP and sw == Terrain.WALL_TOP:
            coord = (15, 3)  # Requires walls at at least (S, SE, SW, E, W)
        elif index in (14, 15) and sw == Terrain.WALL_TOP:
            coord = (14, 5)  # Requires walls at at least (S, SW, E, W)
        elif index in (14, 15) and se == Terrain.WALL_TOP:
            coord = (14, 4)  # Requires walls at at least (S, SE, E, W)
        return coord

class WallBottomPainter(WangEdge16Painter):
    terrain_like = (Terrain.WALL_TOP, Terrain.WALL_BOTTOM, Terrain.COLUMN)

    # Used by Floor Painter
    @staticmethod
    def is_a_column(tilemap, pos: Pos) -> bool:
        north, east, south, west = tilemap.get_cardinal_terrain(pos)
        if west not in WallBottomPainter.terrain_like and east not in WallBottomPainter.terrain_like:
            north_pos = (pos[0], pos[1] - 1)
            # If north has no adjacent friends
            if north == Terrain.WALL_TOP and WallTopPainter.get_index(tilemap, north_pos) == 0:
                return True
        return False

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        north, east, south, west = tilemap.get_cardinal_terrain(pos)
        ne, se, sw, nw = tilemap.get_diagonal_terrain(pos)

        ends_on_left, ends_on_right, shadow = True, True, False
        if west in self.terrain_like:
            ends_on_left = False
        if east in self.terrain_like:
            ends_on_right = False

        if west == Terrain.WALL_TOP:
            shadow = True
        elif sw == Terrain.WALL_TOP:
            shadow = True
        elif west == Terrain.PILLAR:
            shadow = True

        north_pos = (pos[0], pos[1] - 1)
        # If north has no adjacent friends
        if north == Terrain.WALL_TOP and WallTopPainter.get_index(tilemap, north_pos) == 0:
            index = 6  # Is a column
        elif ends_on_left and ends_on_right:
            if shadow:
                index = 5  # shadowcast on a wall that ends on both right and left
            else:
                index = 0  # Wall ends on both right and left
        elif shadow:
            if ends_on_right:
                index = 5  # shadowcast on a wall that ends on right
            else:
                index = 4  # Wall has a shadow cast on it
        elif ends_on_right:
            index = 2  # Wall ends on the right
        elif ends_on_left:
            index = 1  # Wall ends on the left
        else:
            index = 3  # Wall does not end on either side

        coord = index, 0
        return coord

class ColumnPainter(Painter):
    terrain_like = (Terrain.WALL_TOP, Terrain.WALL_BOTTOM, Terrain.COLUMN,)
    column_index = 0

    @property
    def check_flood_fill(self):
        return True

    def single_process(self, tilemap):
        self.column_index = random_choice([0, 1], (0, 0))

    @staticmethod
    def distance_to_column_top(tilemap, pos: Pos) -> int:
        n, _, _, _ = tilemap.get_cardinal_terrain(pos)
        if n == Terrain.COLUMN:
            return 1 + ColumnPainter.distance_to_column_top(tilemap, (pos[0], pos[1] - 1))
        return 0

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        distance = ColumnPainter.distance_to_column_top(tilemap, pos)
        if distance == 0:
            coord = (self.column_index, 0)
        elif distance == 1:
            coord = (self.column_index, 1)
        elif distance % 2:
            coord = (self.column_index, 3)
        else:
            coord = (self.column_index, 2)
        return coord
