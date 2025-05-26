from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

class FogOfWarType(IntEnum):
    GBA_DEPRECATED = 0
    GBA = 1
    THRACIA = 2
    HYBRID = 3

@dataclass
class FogOfWarLevelConfig:
    is_active: bool
    mode: FogOfWarType
    default_radius: int
    ai_radius: int
    other_radius: int
