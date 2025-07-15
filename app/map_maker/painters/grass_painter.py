from typing import Dict, Tuple

from app.utilities.typing import Pos
from app.map_maker.painter_utils import Painter
from app.map_maker.painters import WangCorner8Painter
from app.map_maker.painters.noise_interface import NoiseInterface
from app.map_maker.utilities import random_choice
from app.map_maker.terrain import Terrain

CLIFF_COORDS = [(13, 9), (13, 10), (14, 9), (14, 10)]  # Topright, Bottomright, Bottomleft, Topleft

def handle_cliffs(tilemap, pos: Pos, new_coord1: Pos, new_coord2: Pos, new_coord3: Pos, new_coord4: Pos) -> Tuple[Pos, Pos, Pos, Pos]:
    old_coord1, old_coord2, old_coord3, old_coord4 = new_coord1, new_coord2, new_coord3, new_coord4
    north, east, south, west = tilemap.get_cardinal_terrain(pos)
    northeast, southeast, southwest, northwest = tilemap.get_diagonal_terrain(pos)
    num_swaps = 0  # Keeps track of how many cliff edges we have on grass
    # Only allow up to 2
    if north and north == Terrain.CLIFF and east and east == Terrain.CLIFF and not (northeast and northeast == Terrain.CLIFF):
        new_coord2 = CLIFF_COORDS[1]
        num_swaps += 1
    if north and north == Terrain.CLIFF and west and west == Terrain.CLIFF and not (northwest and northwest == Terrain.CLIFF):
        new_coord1 = CLIFF_COORDS[3]
        num_swaps += 1
    if south and south == Terrain.CLIFF and east and east == Terrain.CLIFF and not (southeast and southeast == Terrain.CLIFF):
        new_coord3 = CLIFF_COORDS[0]
        num_swaps += 1
    if south and south == Terrain.CLIFF and west and west == Terrain.CLIFF and not (southwest and southwest == Terrain.CLIFF):
        new_coord4 = CLIFF_COORDS[2]
        num_swaps += 1
    # Handle seacliffs
    if north and north == Terrain.SEA and east and east == Terrain.SEA and northeast and northeast == Terrain.SEA:
        new_coord2 = CLIFF_COORDS[1]
        num_swaps += 1
    if north and north == Terrain.SEA and west and west == Terrain.SEA and northwest and northwest == Terrain.SEA:
        new_coord1 = CLIFF_COORDS[3]
        num_swaps += 1
    if south and south == Terrain.SEA and east and east == Terrain.SEA and southeast and southeast == Terrain.SEA:
        new_coord3 = CLIFF_COORDS[0]
        num_swaps += 1
    if south and south == Terrain.SEA and west and west == Terrain.SEA and southwest and southwest == Terrain.SEA:
        new_coord4 = CLIFF_COORDS[2]
        num_swaps += 1

    if num_swaps <= 2:
        return new_coord1, new_coord2, new_coord3, new_coord4
    else:
        return old_coord1, old_coord2, old_coord3, old_coord4

class GrassPainter(Painter):
    def get_coord(self, tilemap, pos: Pos) -> Tuple[Pos, Pos, Pos, Pos]:
        new_coord1 = random_choice([(0, k) for k in range(self.limit[0])], pos)
        new_coord2 = random_choice([(0, k) for k in range(self.limit[0])], pos, offset=1)
        new_coord3 = random_choice([(0, k) for k in range(self.limit[0])], pos, offset=2)
        new_coord4 = random_choice([(0, k) for k in range(self.limit[0])], pos, offset=3)

        # Handle cliffs
        new_coord1, new_coord2, new_coord3, new_coord4 = \
            handle_cliffs(tilemap, pos, new_coord1, new_coord2, new_coord3, new_coord4)

        # shading_coord = self.get_shading_coord(tilemap, pos)

        return new_coord1, new_coord2, new_coord3, new_coord4

class LightGrassPainter(WangCorner8Painter, Painter):
    terrain_like = (Terrain.LIGHT_GRASS, )
    base_coord = (15, 0)
    corner_chance = 0.8
    edge_chance = 0.6
    vertices: dict = {}

    def single_process(self, tilemap):
        # For each vertex, assign a random value
        # Then go through each vertex and determine if corner, edge, or neither
        # Check values for each vertex to decide if it should be removed
        # Save data somewhere
        positions: set = tilemap.get_all_terrain(Terrain.LIGHT_GRASS)
        self.vertices.clear()
        for pos in positions:
            self.determine_vertex(tilemap, pos)

    def _determine_index(self, tilemap, pos: tuple) -> tuple:
        center, left, right, top, bottom, topleft, topright, bottomleft, bottomright = self._pos_to_vertices(pos)
        center_edge = True
        left_edge = bool(self.vertices[left][0])
        right_edge = bool(self.vertices[right][0])
        top_edge = bool(self.vertices[top][0])
        bottom_edge = bool(self.vertices[bottom][0])
        topleft_edge = bool(self.vertices[topleft][0])
        topright_edge = bool(self.vertices[topright][0])
        bottomleft_edge = bool(self.vertices[bottomleft][0])
        bottomright_edge = bool(self.vertices[bottomright][0])

        # Randomly determine some to remove
        if self.vertices[center][0] == 3 and self.vertices[center][1] < self.edge_chance:
            center_edge = False
        if self.vertices[center][0] == 2 and self.vertices[center][1] < self.corner_chance:
            center_edge = False
        if self.vertices[left][0] in (2, 3) and self.vertices[left][1] < self.edge_chance:
            left_edge = False
        if self.vertices[right][0] in (2, 3) and self.vertices[right][1] < self.edge_chance:
            right_edge = False
        if self.vertices[top][0] in (2, 3) and self.vertices[top][1] < self.edge_chance:
            top_edge = False
        if self.vertices[bottom][0] in (2, 3) and self.vertices[bottom][1] < self.edge_chance:
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
            
    def get_coord(self, tilemap, pos: Pos) -> Pos:
        index1, index2, index3, index4 = self._determine_index(tilemap, pos)

        new_coord1 = random_choice([(index1, k) for k in range(self.limit[index1])], pos)
        new_coord2 = random_choice([(index2, k) for k in range(self.limit[index2])], pos, offset=1)
        new_coord3 = random_choice([(index3, k) for k in range(self.limit[index3])], pos, offset=2)
        new_coord4 = random_choice([(index4, k) for k in range(self.limit[index4])], pos, offset=3)

        # Handle cliffs
        # Handle cliffs
        new_coord1, new_coord2, new_coord3, new_coord4 = \
            handle_cliffs(tilemap, pos, new_coord1, new_coord2, new_coord3, new_coord4)

        # shading_coord = self.get_shading_coord(tilemap, pos)

        return new_coord1, new_coord2, new_coord3, new_coord4

class NoisyGrassPainter(NoiseInterface, Painter):
    """
    # Implements 8x8 Floor with Grass
    """
    noise_vertices: Dict[Pos, bool] = {}
    noise_threshold: float = 0.55

    def get_index(self, tilemap, pos: Pos) -> Tuple[int, int, int, int]:
        center = self.noise_vertices.get((pos[0]*2 + 1, pos[1]*2 + 1), False) 
        north = self.noise_vertices.get((pos[0]*2 + 1, pos[1]*2), False)
        east = self.noise_vertices.get((pos[0]*2 + 2, pos[1]*2 + 1), False)
        south = self.noise_vertices.get((pos[0]*2 + 1, pos[1]*2 + 2), False)
        west = self.noise_vertices.get((pos[0]*2, pos[1]*2 + 1), False)
        northwest = self.noise_vertices.get((pos[0]*2, pos[1]*2), False)
        northeast = self.noise_vertices.get((pos[0]*2 + 2, pos[1]*2), False)
        southwest = self.noise_vertices.get((pos[0]*2, pos[1]*2 + 2), False)
        southeast = self.noise_vertices.get((pos[0]*2 + 2, pos[1]*2 + 2), False)

        # since it doesn't look good, make sure the green sections don't overlap
        # the forest tiles
        n, e, s, w = tilemap.get_cardinal_terrain(pos)
        ne, se, sw, nw = tilemap.get_diagonal_terrain(pos)
        north &= (all(Terrain.light_grass_adjacent(k) or k is None for k in (n, ne, nw, e, w)))
        east &= (all(Terrain.light_grass_adjacent(k) or k is None for k in (e, ne, se, s, n)))
        south &= (all(Terrain.light_grass_adjacent(k) or k is None for k in (s, se, sw, e, w)))
        west &= (all(Terrain.light_grass_adjacent(k) or k is None for k in (w, nw, sw, s, n)))
        northeast &= (all(Terrain.light_grass_adjacent(k) or k is None for k in (ne, n, e)))
        southeast &= (all(Terrain.light_grass_adjacent(k) or k is None for k in (se, s, e)))
        southwest &= (all(Terrain.light_grass_adjacent(k) or k is None for k in (sw, s, w)))
        northwest &= (all(Terrain.light_grass_adjacent(k) or k is None for k in (nw, n, w)))
        center &= (all(Terrain.light_grass_adjacent(k) or k is None for k in (n, e, s, w)))

        # Topleft
        index1 = 1 * north + \
            2 * center + \
            4 * west + \
            8 * northwest
        # Topright
        index2 = 1 * northeast + \
            2 * east + \
            4 * center + \
            8 * north
        # Bottomright
        index3 = 1 * east + \
            2 * southeast + \
            4 * south + \
            8 * center
        # Bottomleft
        index4 = 1 * center + \
            2 * south + \
            4 * southwest + \
            8 * west
        return index1, index2, index3, index4

    def get_coord(self, tilemap, pos: Pos) -> Tuple[Tuple[Pos, Pos, Pos, Pos], Pos]:
        index1, index2, index3, index4 = self.get_index(tilemap, pos)
        coord1 = random_choice([(index1, k) for k in range(self.limit[index1])], (pos[0] * 2, pos[1] * 2))
        coord2 = random_choice([(index2, k) for k in range(self.limit[index2])], (pos[0] * 2 + 1, pos[1] * 2))
        coord3 = random_choice([(index3, k) for k in range(self.limit[index3])], (pos[0] * 2 + 1, pos[1] * 2 + 1))
        coord4 = random_choice([(index4, k) for k in range(self.limit[index4])], (pos[0] * 2, pos[1] * 2 + 1))

        # shading_coord = self.get_shading_coord(tilemap, pos)

        return coord1, coord2, coord3, coord4
