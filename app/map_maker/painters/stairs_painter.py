from app.utilities.typing import Pos

from app.map_maker.terrain import Terrain
from app.map_maker.painter_utils import Painter

class StairsUpDownPainter(Painter):
    """
    Determines which coordinate should be used for the stairs based
    on a small set of adjacency rules
    """
    terrain_like = (Terrain.STAIRS_UPDOWN, )

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        _, east, _, west = tilemap.get_cardinal_terrain(pos)
        left, right = False, False
        if east and east not in self.terrain_like:
            right = True
        if west and west not in self.terrain_like:
            left = True

        if left and right:
            coord = (0, 0)
        elif left:
            coord = (1, 0)
        elif right:
            coord = (2, 0)
        else:
            coord = (3, 0)
        return coord

class StairsLeftPainter(Painter):
    """
    Determines which coordinate should be used for the stairs based
    on a small set of adjacency rules
    """
    terrain_like = (Terrain.STAIRS_LEFT, )

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        north, _, south, _ = tilemap.get_cardinal_terrain(pos)
        if north and north not in self.terrain_like:
            coord = (0, 0)
        else:
            coord = (1, 0)
        return coord

class StairsRightPainter(StairsLeftPainter):
    """
    Determines which coordinate should be used for the stairs based
    on a small set of adjacency rules
    """
    terrain_like = (Terrain.STAIRS_RIGHT, )
