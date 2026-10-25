from typing import Any, Dict, Tuple

from enum import StrEnum

from app.utilities.data import Data
from app.utilities.typing import NID

from app.dungeon_maker.themes import ThemeParameter, percent

class MacroLayout(StrEnum):
    """Coarse guaranteed macro structure blended into the elevation field (Civ's HintedWorld)."""
    none = "none"
    pangaea = "pangaea"
    continents = "continents"
    coastal = "coastal"

theme_parameters = Data([
    ThemeParameter('size', "Map Size", (25, 25), Tuple[int, int]),
    ThemeParameter('starting_frequency', "Frequency", 0.125, float, "How close together samples are on the noise wave; smaller frequency is closer sampling"),
    ThemeParameter('forest_starting_frequency', "Forest Frequency", 0.2, float, "How close together samples are on the noise wave; smaller frequency is closer sampling"),
    ThemeParameter('cliff_threshold', "Cliff Threshold", 0.3, float, "Necessary discontinuity in noise value to produce a cliff"),
    ThemeParameter('forest_threshold', "Forest Chance", 0.35, percent, "Height of forest noise map that produces forests"),
    ThemeParameter('thick_forest_threshold', "Thick Forest Chance", 0.2, percent, "Height of forest noise map that produces thick forests"),
    ThemeParameter('tiles_per_river_tile', "Tiles Per River Tile", 40, int, "One river tile is targeted per this many land tiles per landmass; 0 disables rivers"),
    ThemeParameter('lake_frequency', "Lake Frequency", 0.08, float, "How close together samples are on the lake noise wave; smaller frequency is closer sampling"),
    ThemeParameter('lake_percent', "Lake Percent", 0.03, percent, "Portion of land turned into inland lakes (SEA); 0 disables lakes"),
    ThemeParameter('desert_frequency', "Desert Frequency", 0.10, float, "How close together samples are on the desert noise wave; smaller frequency is closer sampling"),
    ThemeParameter('desert_percent', "Desert Percent", 0.0, percent, "Portion of land that is arid biome (desert core + sand skirt); 0 disables deserts"),
    ThemeParameter('deep_desert_percent', "Deep Desert Percent", 0.35, percent, "Portion of the arid biome that is true desert core (rest is sand skirt)"),
    ThemeParameter('desert_rock_chance', "Desert Rock Chance", 0.06, percent, "Per-desert-tile chance of scattering a desert rock"),
    ThemeParameter('macro_layout', "Macro Layout", MacroLayout.none, MacroLayout, "Guaranteed coarse land/sea structure blended into elevation; 'none' = pure noise"),
    ThemeParameter('hint_weight', "Macro Hint Weight", 0.55, float, "How strongly the macro layout pulls the elevation field (0 = ignore, 1 = layout dominates)"),
    ThemeParameter('water_border', "Set Sea Border", False, bool, "Add a sea border around the map"),
    ThemeParameter('sea_percent', "Sea Percent", 0.35, percent, "Portion of map that is sea"),
    ThemeParameter('sand_percent', "Sand Percent", 0.05, percent, "Portion of map that is beach/sand (above sea)"),
    ThemeParameter('hill_frequency', "Hill Frequency", 0.15, float, "How close together samples are on the hill/mountain noise wave"),
    ThemeParameter('highland_percent', "Highland Percent", 0.30, percent, "Portion of land that is hills+mountains"),
    ThemeParameter('peak_percent', "Peak Percent", 0.40, percent, "Portion of highland that is mountains (rest is hills)"),
])

theme_presets: Dict[str, Dict[NID, Any]] = {
    "Default": {},
    "Pangaea": {"macro_layout": MacroLayout.pangaea}
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
