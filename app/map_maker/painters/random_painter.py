from typing import Tuple

from app.utilities.typing import Pos

from app.map_maker.painter_utils import Painter
from app.map_maker.utilities import random_choice

class RandomPainter(Painter):
    def get_coord(self, tilemap, pos: Pos) -> Pos:
        new_coord = random_choice(self.data, pos)
        return new_coord

class Random8Painter(Painter):
    def get_coord(self, tilemap, pos: Pos) -> Tuple[Pos, Pos, Pos, Pos]:
        new_coord1 = random_choice([(p[0]*2, p[1]*2) for p in self.data], pos)
        new_coord2 = random_choice([(p[0]*2 + 1, p[1]*2) for p in self.data], pos, offset=1)
        new_coord3 = random_choice([(p[0]*2 + 1, p[1]*2 + 1) for p in self.data], pos, offset=2)
        new_coord4 = random_choice([(p[0]*2, p[1]*2 + 1) for p in self.data], pos, offset=3)

        return new_coord1, new_coord2, new_coord3, new_coord4
