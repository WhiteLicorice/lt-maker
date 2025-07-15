from __future__ import annotations
from typing import Dict, Optional

from app.utilities.typing import Pos

class Painter:
    base_coord: Pos = (0, 0)

    def __init__(self, display_coord: Optional[Pos] = None):
        self.limit: Optional[Dict[int, int]] = None
        self.base_coord = display_coord or self.base_coord or (0, 0)

    def set_limit(self, limit: Dict[int, int]):
        self.limit = limit

    def has_autotiles(self) -> bool:
        return False

    @property
    def check_flood_fill(self):
        return False

    def single_process(self, tilemap) -> None:
        pass

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        return self.base_coord
