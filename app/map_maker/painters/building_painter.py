from typing import Set
from app.utilities.typing import Pos

from app.map_maker.painter_utils import Painter
from app.map_maker.utilities import random_choice
from app.map_maker.terrain import Terrain

class BuildingPainter(Painter):
    organization = {}  # Key: position, value: type

    @property
    def check_flood_fill(self):
        return True

    def single_process(self, tilemap):
        raise NotImplementedError

    def _finalize(self, positions: Set[Pos], position: Pos, sprite_type: str, offset: tuple):
        actual_position = (position[0] + offset[0], position[1] + offset[1])
        self.organization[actual_position] = (sprite_type, offset)
        positions.discard(actual_position)

    @staticmethod
    def _fits_3x3(positions: Set[Pos], position: Pos) -> bool:
        return \
            position in positions and \
            (position[0], position[1] + 1) in positions and \
            (position[0], position[1] + 2) in positions and \
            (position[0] + 1, position[1]) in positions and \
            (position[0] + 1, position[1] + 1) in positions and \
            (position[0] + 1, position[1] + 2) in positions and \
            (position[0] + 2, position[1]) in positions and \
            (position[0] + 2, position[1] + 1) in positions and \
            (position[0] + 2, position[1] + 2) in positions

    @staticmethod
    def _fits_3x2(positions: Set[Pos], position: Pos) -> bool:
        return \
            position in positions and \
            (position[0], position[1] + 1) in positions and \
            (position[0] + 1, position[1]) in positions and \
            (position[0] + 1, position[1] + 1) in positions and \
            (position[0] + 2, position[1]) in positions and \
            (position[0] + 2, position[1] + 1) in positions

    @staticmethod
    def _fits_2x2(positions: Set[Pos], position: Pos) -> bool:
        return \
            position in positions and \
            (position[0], position[1] + 1) in positions and \
            (position[0] + 1, position[1]) in positions and \
            (position[0] + 1, position[1] + 1) in positions

    @staticmethod
    def _fits_2x1(positions: Set[Pos], position: Pos) -> bool:
        return \
            position in positions and \
            (position[0] + 1, position[1]) in positions

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        sprite_type, offset = self.organization[pos]
        coords = [(c[0] + offset[0], c[1] + offset[1]) for c in self.data[sprite_type]]

        # So it always uses the same set of coords...
        base_pos = (pos[0] - offset[0], pos[1] - offset[1])
        coord = random_choice(coords, base_pos)
        return coord        

class CastlePainter(BuildingPainter):
    base_coord = (0, 0)
    data = {'single': [(0, 0), (0, 1)], 
            '3x3': [(0, 2), (0, 5), (0, 8), (0, 11), (0, 14), (0, 17)]}
    organization = {}

    def single_process(self, tilemap):
        self.organization.clear()
        positions: set = tilemap.get_all_terrain(Terrain.CASTLE)
        order: list = sorted(positions)
        while order:
            position = order.pop(0)
            if position not in positions:
                continue
            if self._fits_3x3(positions, position):
                self._finalize(positions, position, '3x3', (0, 0))
                self._finalize(positions, position, '3x3', (0, 1))
                self._finalize(positions, position, '3x3', (0, 2))
                self._finalize(positions, position, '3x3', (1, 0))
                self._finalize(positions, position, '3x3', (1, 1))
                self._finalize(positions, position, '3x3', (1, 2))
                self._finalize(positions, position, '3x3', (2, 0))
                self._finalize(positions, position, '3x3', (2, 1))
                self._finalize(positions, position, '3x3', (2, 2))
            else:
                self._finalize(positions, position, 'single', (0, 0))
    
class RuinsPainter(BuildingPainter):
    base_coord = (0, 0)
    data = {'single': [(0, 0), (1, 0)], 
            '3x3': [(0, 3)], 
            '2x2': [(0, 1)], 
            '2x1': [(0, 2)], 
            '3x2': [(0, 6)]}
    organization = {}

    def single_process(self, tilemap):
        self.organization.clear()
        positions: set = tilemap.get_all_terrain(Terrain.RUINS)
        order: list = sorted(positions)
        while order:
            position = order.pop(0)
            if position not in positions:
                continue
            if self._fits_3x3(positions, position):
                self._finalize(positions, position, '3x3', (0, 0))
                self._finalize(positions, position, '3x3', (0, 1))
                self._finalize(positions, position, '3x3', (0, 2))
                self._finalize(positions, position, '3x3', (1, 0))
                self._finalize(positions, position, '3x3', (1, 1))
                self._finalize(positions, position, '3x3', (1, 2))
                self._finalize(positions, position, '3x3', (2, 0))
                self._finalize(positions, position, '3x3', (2, 1))
                self._finalize(positions, position, '3x3', (2, 2))
            elif self._fits_3x2(positions, position):
                self._finalize(positions, position, '3x2', (0, 0))
                self._finalize(positions, position, '3x2', (0, 1))
                self._finalize(positions, position, '3x2', (1, 0))
                self._finalize(positions, position, '3x2', (1, 1))
                self._finalize(positions, position, '3x2', (2, 0))
                self._finalize(positions, position, '3x2', (2, 1))
            elif self._fits_2x2(positions, position):
                self._finalize(positions, position, '2x2', (0, 0))
                self._finalize(positions, position, '2x2', (0, 1))
                self._finalize(positions, position, '2x2', (1, 0))
                self._finalize(positions, position, '2x2', (1, 1))
            elif self._fits_2x1(positions, position):
                self._finalize(positions, position, '2x1', (0, 0))
                self._finalize(positions, position, '2x1', (1, 0))
            else:
                self._finalize(positions, position, 'single', (0, 0))

class HousePainter(BuildingPainter):
    base_coord = (0, 0)
    data = {'single': [(0, 0)], 
            '3x3': [(0, 1)], 
            '3x2': [(0, 4)]}
    organization = {}

    def single_process(self, tilemap):
        self.organization.clear()
        positions: set = tilemap.get_all_terrain(Terrain.HOUSE)
        order: list = sorted(positions)
        while order:
            position = order.pop(0)
            if position not in positions:
                continue
            if self._fits_3x3(positions, position):
                self._finalize(positions, position, '3x3', (0, 0))
                self._finalize(positions, position, '3x3', (0, 1))
                self._finalize(positions, position, '3x3', (0, 2))
                self._finalize(positions, position, '3x3', (1, 0))
                self._finalize(positions, position, '3x3', (1, 1))
                self._finalize(positions, position, '3x3', (1, 2))
                self._finalize(positions, position, '3x3', (2, 0))
                self._finalize(positions, position, '3x3', (2, 1))
                self._finalize(positions, position, '3x3', (2, 2))
            elif self._fits_3x2(positions, position):
                self._finalize(positions, position, '3x2', (0, 0))
                self._finalize(positions, position, '3x2', (0, 1))
                self._finalize(positions, position, '3x2', (1, 0))
                self._finalize(positions, position, '3x2', (1, 1))
                self._finalize(positions, position, '3x2', (2, 0))
                self._finalize(positions, position, '3x2', (2, 1))
            else:
                self._finalize(positions, position, 'single', (0, 0))

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        sprite_type, offset = self.organization[pos]
        coords = [(c[0] + offset[0], c[1] + offset[1]) for c in self.data[sprite_type]]

        # So it always uses the same set of coords...
        base_pos = (pos[0] - offset[0], pos[1] - offset[1])
        coord = random_choice(coords, base_pos)
        if coord == (0, 0) and sum([Terrain.sand_like(t) for t in tilemap.get_cardinal_terrain(pos)]) > 2:
            coord = (1, 0)
        return coord
