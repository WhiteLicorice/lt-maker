from typing import Any, Dict, Tuple, Type

from dataclasses import dataclass
from enum import StrEnum

from app.utilities.data import Data
from app.utilities.typing import NID

from app.map_maker.terrain import Terrain

class PillarArrangement(StrEnum):
    NoPillars = "NoPillars"
    Middle = "Middle"
    OnEdge = "OnEdge"
    FourCorners = "FourCorners"
    NearEdge = "NearEdge"

@dataclass
class ThemeParameter:
    nid: NID
    name: str
    value: Any
    _type: Type
    desc: str = ""

theme_parameters = Data([
    ThemeParameter('size', "Map Size", (30, 18), Tuple[int, int]),
    ThemeParameter('section_grid', "Section Grid", (4, 3), Tuple[int, int], "Individual sections to fill with rooms"),
    ThemeParameter('floor_upper', "Upper Floor Terrain", Terrain.FLOOR_1, Terrain, "Which terrain to use for the upper floor"),
    ThemeParameter('floor_lower', "Lower Floor Terrain", Terrain.FLOOR_2, Terrain, "Which terrain to use for the lower floor"),
    ThemeParameter('room_chance', "Room Chance", 0.6, float, "Chance of a full size room in a section"),
    ThemeParameter('hallway_chance', "Hallway Chance", 0.4, float, "Chance of hallway (instead of a room) in a section"),
    ThemeParameter('connection_chance', "Connection Chance", 1.0, float, "Chance that adjacent rooms connect"),
    ThemeParameter('wide_hallway_chance', "Wide Hallway Chance", 0.5, float, "Chance that a given hallway is 2-wide"),
    ThemeParameter('floor_lower_chance', "Lower Floor Chance", 0.5, float, "Chance that a room is on the lower floor"),
    ThemeParameter('use_water_chance', "Pool Chance", 0, float, "Chance to use pool and pool bridge on lower floor"),
    ThemeParameter('room_size_min_x', "Minimum Width of Room", 3, int, "All rooms generated will have width >= value"),
    ThemeParameter('room_size_min_y', "Mimumum Height of Room", 3, int, "All rooms generated will have height >= value"),
    ThemeParameter('small_floor_section_area', "Minimum Size of Floor", 2, int, "Swap any areas of floor smaller than this to the other floor"),
    ThemeParameter('pillar_chance', "Pillar Chance", 0.5, float, "Chance that any room has pillars"),
    ThemeParameter('horiz_symmetry', "Horizontally Symmetric", False, bool),
    ThemeParameter('vert_symmetry', "Vertically Symmetric", False, bool),
    ThemeParameter('fill_in_empty_areas', "Fill in Empty Areas", False, bool, "Attempt to fill large areas of void with floor?"),
    ThemeParameter('use_global_section', "Fill Outside", False, bool, "Fill the outside of the map with lower floor"),
    ThemeParameter('convert_void_to_water', "Void -> Pool", False, bool, "Convert all void to pool terrain"),
])

theme_presets: Dict[str, Dict[NID, Any]] = {
    "Default": {},
    "Labyrinth": {
        "size": (21, 25),
        "section_grid": (4, 6),
        "room_chance": 1.0,
        "hallway_chance": 0.0,
        "wide_hallway_chance": 0.0,
        "floor_lower_chance": 0.2,
        "room_size_min_x": 2,
        "room_size_min_y": 2,
        "pillar_chance": 0.33,
        "horiz_symmetry": True,
    },
    "Winding Hallways": {
        "size": (27, 27),
        "section_grid": (4, 4),
        "room_chance": 0.5,
        "hallway_chance": 0.5,
        "connection_chance": 0.8,
        "wide_hallway_chance": 1.0,
        "floor_lower_chance": 0.25,
        "pillar_chance": 0.5,
        "small_floor_section_area": 5,
        "fill_in_empty_areas": True,
    },
    "Enemy Complex": {
        "size": (26, 36),
        "section_grid": (5, 6),
        "room_chance": 0.45,
        "hallway_chance": 0,
        "connection_chance": 0.8,
        "floor_lower_chance": 0,
        "room_size_min_y": 2,
        "pillar_chance": 0.25,
        "use_global_section": True,
    },
    "Sewers": {
        "size": (25, 25),
        "section_grid": (4, 4),
        "room_chance": 0.55,
        "hallway_chance": 0.45,
        "connection_chance": 0.8,
        "wide_hallway_chance": 1.0,
        "floor_lower_chance": 0.75,
        "use_water_chance": 0.5,
        "room_size_min_y": 2,
    },
    "Grand Entrance": {
        "size": (25, 15),
        "room_chance": 0.5,
        "hallway_chance": 0.4,
        "connection_chance": 0.5,
        "pillar_chance": 0.25,
        "small_floor_section_area": 4,
        "convert_void_to_water": True,
    },
    "Castle": {
        "size": (20, 30),
        "section_grid": (4, 4),
        "connection_chance": 0.75,
        "wide_hallway_chance": 1.0,
        "room_size_min_y": 4,
        "pillar_chance": 0.4,
        "small_floor_section_area": 4,
        "fill_in_empty_areas": True,
    },
}

def get_default_theme() -> Dict[NID, Any]:
    new_theme = {}
    for parameter in theme_parameters:
        new_theme[parameter.nid] = parameter.value
    return new_theme

def get_theme(preset: NID) -> Dict[NID, Any]:
    """Given a theme preset's nid, return the theme
    parameters for it"""
    base_theme = get_default_theme()
    theme_preset = theme_presets[preset]
    base_theme.update(theme_preset)
    return base_theme
