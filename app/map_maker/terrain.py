from __future__ import annotations

from typing import List

from collections import namedtuple
from enum import Enum

class Terrain(namedtuple("Terrain", "value outdoor"), Enum):
    # Outdoors
    GRASS = 'Grass', True
    LIGHT_GRASS = 'Light Grass', True
    NOISY_GRASS = 'Noisy Grass', True
    SAND = 'Sand', True
    ROAD = 'Road', True
    SPARSE_FOREST = 'Sparse Forest', True
    FOREST = 'Forest', True
    THICKET = 'Thicket', True
    CLIFF = 'Cliff', True
    HILL = 'Hill', True
    MOUNTAIN = 'Mountain', True
    RIVER = 'River', True
    SEA = 'Sea', True
    BRIDGEH = 'Bridge H', True
    BRIDGEV = 'Bridge V', True
    HOUSE = 'House', True
    CASTLE = 'Castle', True
    RUINS = 'Ruins', True

    # Indoors
    VOID = 'Void', False
    WALL_TOP = 'Wall Top', False
    WALL_BOTTOM = 'Wall Bottom', False
    COLUMN = 'Column', False
    FLOOR_1 = 'Floor 1', False
    FLOOR_2 = 'Floor 2', False
    FLOOR_3 = 'Floor 3', False
    STAIRS_UPDOWN = 'Stairs UpDown', False
    STAIRS_LEFT = 'Stairs Left', False
    STAIRS_RIGHT = 'Stairs Right', False
    STAIRS_CENTER = 'Stairs Center', False
    PILLAR = 'Pillar', False
    POOL = 'Pool', False
    POOL_BRIDGE = 'Pool Bridge', False
    TREASURE = 'Treasure Chest', False

    @staticmethod
    def list() -> List["Terrain"]:
        return [_ for _ in Terrain]

    @staticmethod
    def indoor_terrain() -> List["Terrain"]:
        return [t for t in Terrain if not t.outdoor]

    @staticmethod
    def outdoor_terrain() -> List["Terrain"]:
        return [t for t in Terrain if t.outdoor]

    @staticmethod
    def name_list() -> List[str]:
        return [t.value for t in Terrain]

    @staticmethod
    def light_grass_adjacent(terrain: "Terrain") -> bool:
        return terrain in (Terrain.NOISY_GRASS, )

    @staticmethod
    def cliff(terrain: "Terrain") -> bool:
        return terrain in (Terrain.CLIFF, )

    @staticmethod
    def wall(terrain: "Terrain") -> bool:
        return terrain in (Terrain.WALL_TOP, Terrain.WALL_BOTTOM, Terrain.COLUMN)

    @staticmethod
    def floor(terrain: "Terrain") -> bool:
        return terrain in (Terrain.FLOOR_1, Terrain.FLOOR_2, Terrain.FLOOR_3)

    @staticmethod
    def sand_like(terrain: "Terrain") -> bool:
        return terrain in (Terrain.ROAD, Terrain.SAND)

    @staticmethod
    def get_all_floor() -> List[Terrain]:
        return (Terrain.FLOOR_1, Terrain.FLOOR_2, Terrain.FLOOR_3)

    @staticmethod
    def get_all_wall() -> List[Terrain]:
        return (Terrain.WALL_TOP, Terrain.WALL_BOTTOM, Terrain.COLUMN)

    @staticmethod
    def get_all_stairs() -> List[Terrain]:
        return (Terrain.STAIRS_LEFT, Terrain.STAIRS_RIGHT, Terrain.STAIRS_UPDOWN, Terrain.STAIRS_CENTER)

    @staticmethod
    def get_all_indoor_traversable() -> List[Terrain]:
        return (Terrain.FLOOR_1,
                Terrain.FLOOR_2,
                Terrain.FLOOR_3,
                Terrain.STAIRS_LEFT,
                Terrain.STAIRS_RIGHT,
                Terrain.STAIRS_UPDOWN,
                Terrain.STAIRS_CENTER,
                Terrain.PILLAR,
                Terrain.POOL_BRIDGE,
                )
