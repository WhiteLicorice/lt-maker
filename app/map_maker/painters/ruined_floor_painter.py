from typing import Dict, Tuple

from app.utilities.typing import Pos
from app.map_maker.terrain import Terrain
from app.map_maker.painters import FloorPainter
from app.map_maker.painters.noise_interface import NoiseInterface
from app.map_maker.utilities import random_choice

class RuinedFloorPainter(NoiseInterface, FloorPainter):
    """
    # Implements 16x16 Floor with Ruins
    """
    base_coord = (5, 0)
    noise_threshold: float = 0.5

    def _get_index(self, tilemap, pos: Pos) -> int:
        center = self.noise_vertices.get((pos[0]*2 + 1, pos[1]*2 + 1), False) 
        north = self.noise_vertices.get((pos[0]*2 + 1, pos[1]*2), False)
        east = self.noise_vertices.get((pos[0]*2 + 2, pos[1]*2 + 1), False)
        south = self.noise_vertices.get((pos[0]*2 + 1, pos[1]*2 + 2), False)
        west = self.noise_vertices.get((pos[0]*2, pos[1]*2 + 1), False)
        northwest = self.noise_vertices.get((pos[0]*2, pos[1]*2), False)
        northeast = self.noise_vertices.get((pos[0]*2 + 2, pos[1]*2), False)
        southwest = self.noise_vertices.get((pos[0]*2, pos[1]*2 + 2), False)
        southeast = self.noise_vertices.get((pos[0]*2 + 2, pos[1]*2 + 2), False)

        topleft = center + north + west + northwest >= 3
        topright = center + north + east + northeast >= 3
        bottomleft = center + south + west + southwest >= 3
        bottomright = center + south + east + southeast >= 3

        index = 1 * topright + \
            2 * bottomright + \
            4 * bottomleft + \
            8 * topleft
        return index

    def get_coord(self, tilemap, pos: Pos) -> Tuple[Pos, Pos]:
        index = self._get_index(tilemap, pos)
        coord = random_choice([(index, k) for k in range(self.limit[index])], pos)
        return coord

class GrassFloorPainter(NoiseInterface, FloorPainter):
    """
    Implements 16x16 floor with grass
    """
    base_coord = (5, 0)
    noise_threshold: float = 0.55
    noise_frequency = 0.5
    terrain_like = (*Terrain.get_all_floor(),
                    *Terrain.get_all_wall(),
                    Terrain.PILLAR,
                    *Terrain.get_all_stairs(),
                    )

    def _get_index(self, tilemap, pos: Pos) -> int:
        north, east, south, west = tilemap.get_cardinal_terrain(pos)
        northeast, southeast, southwest, northwest = tilemap.get_diagonal_terrain(pos)
        north_edge = bool(north and north not in self.terrain_like)
        south_edge = bool(south and south not in self.terrain_like)
        east_edge = bool(east and east not in self.terrain_like)
        west_edge = bool(west and west not in self.terrain_like)
        northeast_edge = bool(northeast and northeast not in self.terrain_like)
        southeast_edge = bool(southeast and southeast not in self.terrain_like)
        southwest_edge = bool(southwest and southwest not in self.terrain_like)
        northwest_edge = bool(northwest and northwest not in self.terrain_like)

        # Get Noise
        center_noise = self.noise_vertices.get((pos[0]*2 + 1, pos[1]*2 + 1), False) 
        north_noise = self.noise_vertices.get((pos[0]*2 + 1, pos[1]*2), False)
        east_noise = self.noise_vertices.get((pos[0]*2 + 2, pos[1]*2 + 1), False)
        south_noise = self.noise_vertices.get((pos[0]*2 + 1, pos[1]*2 + 2), False)
        west_noise = self.noise_vertices.get((pos[0]*2, pos[1]*2 + 1), False)
        northwest_noise = self.noise_vertices.get((pos[0]*2, pos[1]*2), False)
        northeast_noise = self.noise_vertices.get((pos[0]*2 + 2, pos[1]*2), False)
        southwest_noise = self.noise_vertices.get((pos[0]*2, pos[1]*2 + 2), False)
        southeast_noise = self.noise_vertices.get((pos[0]*2 + 2, pos[1]*2 + 2), False)

        n = max(north_edge, north_noise)
        s = max(south_edge, south_noise)
        e = max(east_edge, east_noise)
        w = max(west_edge, west_noise)
        nw = max(northwest_edge, northwest_noise)
        ne = max(northeast_edge, northeast_noise)
        sw = max(southwest_edge, southwest_noise)
        se = max(southeast_edge, southeast_noise)

        topleft = center_noise + n + w + nw >= 3
        topright = center_noise + n + e + ne >= 3
        bottomleft = center_noise + s + w + sw >= 3
        bottomright = center_noise + s + e + se >= 3

        index = 1 * topright + \
            2 * bottomright + \
            4 * bottomleft + \
            8 * topleft
        # Never go full grass
        # if index == 15:
        #     index = 0
        return index

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        index = self._get_index(tilemap, pos)
        coord = random_choice([(index, k) for k in range(self.limit[index])], pos)
        return coord
