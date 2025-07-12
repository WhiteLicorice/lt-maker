from typing import Set, Tuple

from app.utilities.typing import Pos

from app.map_maker.painters import WangCorner8Painter
from app.map_maker.terrain import Terrain

class SandPainter(WangCorner8Painter):
    terrain_like = (
        Terrain.SAND,
        Terrain.ROAD, 
        Terrain.SEA,
        Terrain.BRIDGEV,
        Terrain.BRIDGEH,
        Terrain.HOUSE,
        Terrain.CASTLE,
        )
    base_coord = (15, 0)
    corner_chance = 0.6
    edge_chance = 0.4
    vertices: dict = {}

    def single_process(self, tilemap):
        # For each vertex, assign a random value
        # Then go through each vertex and determine if corner, edge, or neither
        # Check values for each vertex to decide if it should be removed
        # Save data somewhere
        positions: Set[Pos] = tilemap.get_all_terrain(Terrain.SAND)
        self.vertices.clear()
        for pos in positions:
            self.determine_vertex(tilemap, pos)

    def _determine_index(self, tilemap, pos: Pos) -> Tuple[int, int, int, int]:
        center, left, right, top, bottom, \
            topleft, topright, bottomleft, bottomright = \
            self._pos_to_vertices(pos)
        center_edge = True
        left_edge = bool(self.vertices[left][0])
        right_edge = bool(self.vertices[right][0])
        top_edge = bool(self.vertices[top][0])
        bottom_edge = bool(self.vertices[bottom][0])
        topleft_edge = bool(self.vertices[topleft][0])
        topright_edge = bool(self.vertices[topright][0])
        bottomleft_edge = bool(self.vertices[bottomleft][0])
        bottomright_edge = bool(self.vertices[bottomright][0])

        # If adjacent to non-sand, don't remove
        north, east, south, west = tilemap.get_cardinal_terrain(pos)
        force_north_edge = north in self.terrain_like and north != Terrain.SAND
        force_south_edge = south in self.terrain_like and south != Terrain.SAND
        force_east_edge = east in self.terrain_like and east != Terrain.SAND
        force_west_edge = west in self.terrain_like and west != Terrain.SAND

        # Randomly determine some to remove
        if self.vertices[center][0] == 3 and self.vertices[center][1] < self.edge_chance:
            center_edge = False
        if self.vertices[center][0] == 2 and self.vertices[center][1] < self.corner_chance:
            center_edge = False
        if not force_west_edge and self.vertices[left][0] in (2, 3) and self.vertices[left][1] < self.edge_chance:
            left_edge = False
        if not force_east_edge and self.vertices[right][0] in (2, 3) and self.vertices[right][1] < self.edge_chance:
            right_edge = False
        if not force_north_edge and self.vertices[top][0] in (2, 3) and self.vertices[top][1] < self.edge_chance:
            top_edge = False
        if not force_south_edge and self.vertices[bottom][0] in (2, 3) and self.vertices[bottom][1] < self.edge_chance:
            bottom_edge = False

        index1 = 1 * top_edge + \
            2 * center_edge + \
            4 * left_edge + \
            8 * topleft_edge
        index2 = 1 * topright_edge + \
            2 * right_edge + \
            4 * center_edge + \
            8 * top_edge
        index3 = 1 * right_edge + \
            2 * bottomright_edge + \
            4 * bottom_edge + \
            8 * center_edge
        index4 = 1 * center_edge + \
            2 * bottom_edge + \
            4 * bottomleft_edge + \
            8 * left_edge
        return index1, index2, index3, index4
