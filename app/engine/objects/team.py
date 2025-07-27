from __future__ import annotations
from app.data.database.teams import Team
from app.utilities.typing import NID
from app.utilities.data import Prefab

class TeamObject(Prefab):
    def __init__(self, nid: NID = None, map_sprite_palette: NID = None, 
                    combat_variant_palette: str = None, combat_color: str = None):
        self.nid = nid
        self.map_sprite_palette = map_sprite_palette            # Used for map sprites
        self.combat_variant_palette = combat_variant_palette    # Used for battle animations
        self.combat_color = combat_color                        # Used for misc. ui (rescue icons, combat displays, etc.)

    def save(self):
        return {'nid': self.nid,
                'map_sprite_palette': self.map_sprite_palette,
                'combat_variant_palette': self.combat_variant_palette,
                'combat_color': self.combat_color,
                }

    @classmethod
    def restore(cls, s_dict):
        team = cls(s_dict['nid'], s_dict.get('map_sprite_palette'), 
                    s_dict.get('combat_variant_palette'), s_dict.get('combat_color', 'red'))
        return team

    @classmethod
    def from_prefab(cls, prefab: Team) -> TeamObject:
        team = cls(prefab.nid, prefab.map_sprite_palette, 
                    prefab.combat_variant_palette, prefab.combat_color)
        return team

    def change_palettes(self, map_sprite_palette = None, combat_variant_palette = None, combat_color = None):
        if map_sprite_palette:
            self.map_sprite_palette = map_sprite_palette
        if combat_variant_palette:
            self.combat_variant_palette = combat_variant_palette
        if combat_color:
            self.combat_color = combat_color