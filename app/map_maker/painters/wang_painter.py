from typing import Dict, Tuple
from app.utilities.typing import Pos

from app.map_maker.painter_utils import Painter
from app.map_maker.utilities import random_choice, random_random
from app.map_maker.terrain import Terrain

class WangEdge16Painter(Painter):
    """
    Selects the correct painter coordinate for the tile by determining which
    cardinally adjacent tiles are of a similar terrain type.
    Which column is determined by the method below, and which row is randomized
    from available rows.
    0 - No adjacent
    1 - North
    2 - East
    3 - North and East
    4 - South
    5 - South and North
    6 - South and East
    etc.
    """
    terrain_like: Tuple[Terrain] = tuple()

    def _determine_index(self, tilemap, pos: Pos) -> int:
        north, east, south, west = tilemap.get_cardinal_terrain(pos)
        north_edge = bool(not north or north in self.terrain_like)
        south_edge = bool(not south or south in self.terrain_like)
        east_edge = bool(not east or east in self.terrain_like)
        west_edge = bool(not west or west in self.terrain_like)
        index = 1 * north_edge + 2 * east_edge + 4 * south_edge + 8 * west_edge
        return index

    def get_coord(self, tilemap, position: Pos) -> Pos:
        col_idx = self._determine_index(tilemap, position)
        coord = random_choice([(col_idx, k) for k in range(self.limit[col_idx])], position)
        return coord

class WangEdge8Painter(Painter):
    """
    Selects the correct painter coordinates for the tile by determining which
    cardinally adjacent tiles are of a similar terrain type.
    Which column is determined by the method below, and which row is randomized
    from available rows.
    0 - No adjacent
    1 - North
    2 - East
    3 - North and East
    4 - South
    5 - South and North
    6 - South and East
    etc.
    Finds the correct 8x8 coordinate, so it needs to find 4 different coordinates.
    """
    terrain_like: Tuple[Terrain] = tuple()

    def _determine_index(self, tilemap, pos: Pos) -> Tuple[int, int, int, int]:
        north, east, south, west = tilemap.get_cardinal_terrain(pos)
        north_edge = bool(not north or north in self.terrain_like)
        south_edge = bool(not south or south in self.terrain_like)
        east_edge = bool(not east or east in self.terrain_like)
        west_edge = bool(not west or west in self.terrain_like)
        index1 = 6 + 1 * north_edge + 8 * west_edge
        index2 = 12 + 1 * north_edge + 2 * east_edge
        index3 = 9 + 4 * south_edge + 2 * east_edge
        index4 = 3 + 4 * south_edge + 8 * west_edge
        return index1, index2, index3, index4

    def get_coord(self, tilemap, position: Pos) -> Tuple[Pos, Pos, Pos, Pos]:
        col_idx1, col_idx2, col_idx3, col_idx4 = self._determine_index(tilemap, position)
        coord1 = random_choice([(col_idx1, k) for k in range(self.limit[col_idx1])], position)
        coord2 = random_choice([(col_idx2, k) for k in range(self.limit[col_idx2])], position, offset=1)
        coord3 = random_choice([(col_idx3, k) for k in range(self.limit[col_idx3])], position, offset=2)
        coord4 = random_choice([(col_idx4, k) for k in range(self.limit[col_idx4])], position, offset=3)
        return coord1, coord2, coord3, coord4

class WangCorner8Painter(Painter):
    """
    """
    terrain_like: Tuple[Terrain] = tuple()
    vertices: Dict[Pos, Tuple[int, float]] = {}

    def _pos_to_vertices(self, pos: Pos) -> Tuple[Pos, Pos, Pos, Pos, Pos, Pos, Pos, Pos, Pos]:
        """Given a standard 16x16 tile gridded position
        returns the 9 8x8 tile gridded positions that make up it,
        center first
        """
        center_vertex_pos = pos[0]*2 + 1, pos[1]*2 + 1
        left_vertex_pos = pos[0]*2, pos[1]*2 + 1
        right_vertex_pos = pos[0]*2 + 2, pos[1]*2 + 1
        top_vertex_pos = pos[0]*2 + 1, pos[1]*2
        bottom_vertex_pos = pos[0]*2 + 1, pos[1]*2 + 2
        topleft_vertex_pos = pos[0]*2, pos[1]*2
        topright_vertex_pos = pos[0]*2 + 2, pos[1]*2
        bottomleft_vertex_pos = pos[0]*2, pos[1]*2 + 2
        bottomright_vertex_pos = pos[0]*2 + 2, pos[1]*2 + 2
        return center_vertex_pos, left_vertex_pos, right_vertex_pos, \
            top_vertex_pos, bottom_vertex_pos, topleft_vertex_pos, \
            topright_vertex_pos, bottomleft_vertex_pos, bottomright_vertex_pos

    def get_edges(self, tilemap, pos: Pos) -> Tuple[bool, bool, bool, bool, bool, bool, bool, bool]:
        north, east, south, west = tilemap.get_cardinal_terrain(pos)
        north_edge = bool(not north or north in self.terrain_like)
        south_edge = bool(not south or south in self.terrain_like)
        east_edge = bool(not east or east in self.terrain_like)
        west_edge = bool(not west or west in self.terrain_like)
        northeast, southeast, southwest, northwest = tilemap.get_diagonal_terrain(pos)
        northeast_edge = bool(not northeast or northeast in self.terrain_like)
        southeast_edge = bool(not southeast or southeast in self.terrain_like)
        southwest_edge = bool(not southwest or southwest in self.terrain_like)
        northwest_edge = bool(not northwest or northwest in self.terrain_like)
        return north_edge, south_edge, east_edge, west_edge, \
            northeast_edge, northwest_edge, southeast_edge, southwest_edge

    def determine_vertex(self, tilemap, pos: Pos):
        north_edge, south_edge, east_edge, west_edge, \
            northeast_edge, northwest_edge, southeast_edge, southwest_edge \
            = self.get_edges(tilemap, pos)
        # 0 is patch
        # 1 is end
        # 2 is corner (unless north and south or east and west, then end)
        # 3 is edge
        # 4 is center
        center_vertex_type = \
            sum((north_edge, south_edge, east_edge, west_edge))
        if center_vertex_type == 2 and ((north_edge and south_edge) or (east_edge and west_edge)):
            center_vertex_type = 1
        # if not north: 0
        # if north: 0
        # if north and ((east and northeast) or (west and northwest)): edge
        # if north and both: center
        left_vertex_type = west_edge + (south_edge and southwest_edge) + (north_edge and northwest_edge)
        if left_vertex_type == 3:
            left_vertex_type = 4
        elif left_vertex_type == 2 and west_edge:
            left_vertex_type = 3
        else:
            left_vertex_type = west_edge
        right_vertex_type = east_edge + (south_edge and southeast_edge) + (north_edge and northeast_edge)
        if right_vertex_type == 3:
            right_vertex_type = 4
        elif right_vertex_type == 2 and east_edge:
            right_vertex_type = 3
        else:
            right_vertex_type = east_edge
        top_vertex_type = north_edge + (west_edge and northwest_edge) + (east_edge and northeast_edge)
        if top_vertex_type == 3:
            top_vertex_type = 4
        elif top_vertex_type == 2 and north_edge:
            top_vertex_type = 3
        else:
            top_vertex_type = north_edge
        bottom_vertex_type = south_edge + (west_edge and southwest_edge) + (east_edge and southeast_edge)
        if bottom_vertex_type == 3:
            bottom_vertex_type = 4
        elif bottom_vertex_type == 2 and south_edge:
            bottom_vertex_type = 3
        else:
            bottom_vertex_type = south_edge
        # 0 is not possible
        # 1 is empty
        # 2 is empty
        # 3 is empty
        # 4 is center
        topleft_vertex_type = 4 if (1 + sum((north_edge, west_edge, northwest_edge))) == 4 else 0
        bottomleft_vertex_type = 4 if (1 + sum((south_edge, west_edge, southwest_edge))) == 4 else 0
        topright_vertex_type = 4 if (1 + sum((north_edge, east_edge, northeast_edge))) == 4 else 0
        bottomright_vertex_type = 4 if (1 + sum((south_edge, east_edge, southeast_edge))) == 4 else 0

        center, left, right, top, bottom, \
            topleft, topright, bottomleft, bottomright \
            = self._pos_to_vertices(pos)

        self.vertices[center] = (center_vertex_type, random_random(center))
        self.vertices[left] = (left_vertex_type, random_random(left))
        self.vertices[right] = (right_vertex_type, random_random(right))
        self.vertices[top] = (top_vertex_type, random_random(top))
        self.vertices[bottom] = (bottom_vertex_type, random_random(bottom))
        self.vertices[topleft] = (topleft_vertex_type, random_random(topleft))
        self.vertices[topright] = (topright_vertex_type, random_random(topright))
        self.vertices[bottomleft] = (bottomleft_vertex_type, random_random(bottomleft))
        self.vertices[bottomright] = (bottomright_vertex_type, random_random(bottomright))

    def _determine_index(self, tilemap, pos: Pos) -> int:
        north, east, south, west = tilemap.get_cardinal_terrain(pos)
        ne, se, sw, nw = tilemap.get_diagonal_terrain(pos)
        north_edge = bool(not north or north in self.terrain_like)
        south_edge = bool(not south or south in self.terrain_like)
        east_edge = bool(not east or east in self.terrain_like)
        west_edge = bool(not west or west in self.terrain_like)
        index1 = 1 * north_edge + \
            2 * True + \
            4 * west_edge + \
            8 * (bool(not nw or nw in self.terrain_like) and north_edge and west_edge)
        index2 = 1 * (bool(not ne or ne in self.terrain_like) and north_edge and east_edge) + \
            2 * east_edge + \
            4 * True + \
            8 * north_edge
        index3 = 1 * east_edge + \
            2 * (bool(not se or se in self.terrain_like) and south_edge and east_edge) + \
            4 * south_edge + \
            8 * True
        index4 = 1 * True + \
            2 * south_edge + \
            4 * (bool(not sw or sw in self.terrain_like) and south_edge and west_edge) + \
            8 * west_edge
        return index1, index2, index3, index4

    def get_coord(self, tilemap, position: Pos) -> Tuple[Pos, Pos, Pos, Pos]:
        col_idx1, col_idx2, col_idx3, col_idx4 = self._determine_index(tilemap, position)
        coord1 = random_choice([(col_idx1, k) for k in range(self.limit[col_idx1])], position)
        coord2 = random_choice([(col_idx2, k) for k in range(self.limit[col_idx2])], position, offset=1)
        coord3 = random_choice([(col_idx3, k) for k in range(self.limit[col_idx3])], position, offset=2)
        coord4 = random_choice([(col_idx4, k) for k in range(self.limit[col_idx4])], position, offset=3)
        return coord1, coord2, coord3, coord4
