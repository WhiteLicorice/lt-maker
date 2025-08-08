from __future__ import annotations

from typing import TYPE_CHECKING, Dict
from enum import Enum

from app.data.database.database import DB

if TYPE_CHECKING:
    from app.engine.game_state import GameState
    from app.engine.objects.unit import UnitObject

from app.engine.overworld.overworld_map_sprites import OverworldUnitSprite
from app.engine.unit_sound import UnitSound
from app.utilities.typing import NID, Point

import logging

class OverworldEntityTypes(Enum):
    PARTY = 'party'
    ENCOUNTER = 'encounter'
    UNIT = 'unit'
    UNIT_OBJ = 'unit_obj'

class OverworldEntityObject():
    def __init__(self):
        # an OverworldEntityObject is an object that represents a party, unit, or encounter on the overworld.
        self.nid: NID = None                    # NID of this entity.

        self.dtype: OverworldEntityTypes = None # what this entity is associated with
        self.dnid: NID = None                   # the nid of the data this entity is associated with

        self.on_node: NID = None                 # NID of node on which the unit is standing
        self.team: NID = 'player'                # team of party. @TODO: Implement non-player entities.

        # unsaved data
        self.sprite: OverworldUnitSprite = None    # sprite for the entity
        self.sound: UnitSound = None               # sound associated

        # private data
        self._display_position: Point = None        # display position for drawing purposes

    @classmethod
    def from_party_prefab(cls, initial_node: NID, party_prefab_nid: NID, unit_registry: Dict[NID, UnitObject] = None):
        entity = cls()
        entity.nid = party_prefab_nid
        entity.dtype = OverworldEntityTypes.PARTY
        entity.dnid = party_prefab_nid
        entity.on_node = initial_node

        # create unit
        party_prefab = DB.parties.get(party_prefab_nid)
        if not party_prefab:
            logging.error("OverworldEntityObject cannot find party %s, using default party %s", party_prefab_nid, DB.parties.values()[0].nid)
            party_prefab = DB.parties.values()[0]

        if unit_registry and party_prefab.leader in unit_registry:
            unit = unit_registry.get(party_prefab.leader)
        elif party_prefab.leader in DB.units:
            unit = DB.units.get(party_prefab.leader)
        else:
            unit = DB.units.values()[0]
            logging.error("OverworldEntityObject cannot find unit %s", party_prefab.leader)
        entity.sprite = OverworldUnitSprite(unit, entity, 'player')

        from app.engine import unit_sound
        entity.sound = unit_sound.UnitSound(unit)
        return entity

    @classmethod
    def from_unit_prefab(cls, nid: NID, initial_position: Point, unit_nid: NID, team: NID):
        entity = cls()
        entity.nid = nid
        entity.dnid = unit_nid
        entity.dtype = OverworldEntityTypes.UNIT
        entity.on_node = None
        entity.team = team

        unit = DB.units.get(unit_nid)
        if not unit:
            logging.error("OverworldEntityObject cannot find unit %s, using default unit %s", unit_nid, DB.units.values()[0].nid)
            unit = DB.units.values()[0]

        entity.sprite = OverworldUnitSprite(unit, entity, team)

        entity.display_position = initial_position

        from app.engine import unit_sound
        entity.sound = unit_sound.UnitSound(unit)
        return entity

    @classmethod
    def from_unit_object(cls, nid: NID, initial_position: Point, unit_nid: NID, unit_registry: Dict[NID, UnitObject]):
        if unit_nid in unit_registry:
            unit = unit_registry[unit_nid]
        else:
            logging.error("OverworldEntityObject cannot find unit %s, trying prefab...", unit_nid)
            return cls.from_unit_prefab(nid, initial_position, unit_nid, 'player')

        entity = cls()
        entity.nid = nid
        entity.dnid = unit.nid
        entity.dtype = OverworldEntityTypes.UNIT_OBJ
        entity.team = unit.team

        entity.sprite = OverworldUnitSprite(unit, entity, unit.team)
        
        entity.display_position = initial_position

        from app.engine import unit_sound
        entity.sound = unit_sound.UnitSound(unit)
        return entity

    def save(self):
        s_dict = {'nid': self.nid,
                  'dtype': self.dtype.name,
                  'dnid': self.dnid,
                  'on_node_nid': self.on_node,

                  # only used for dummy entities
                  'position': self.display_position,
                  'team': self.team}
        return s_dict

    @classmethod
    def restore(cls, s_dict, game: GameState) -> OverworldEntityObject:
        entity_nid = s_dict['nid']
        prefab_nid = s_dict['dnid']
        entity_dtype = OverworldEntityTypes[s_dict['dtype']]
        if entity_dtype == OverworldEntityTypes.PARTY:
            on_node_nid = s_dict['on_node_nid']
            entity_object = OverworldEntityObject.from_party_prefab(on_node_nid, prefab_nid, game.unit_registry)
            entity_object.team = s_dict['team']
            return entity_object
        elif entity_dtype == OverworldEntityTypes.UNIT:  # dummy entity
            entity_position = s_dict['position']
            entity_object = OverworldEntityObject.from_unit_prefab(entity_nid, entity_position, prefab_nid, s_dict['team'])
            return entity_object
        elif entity_dtype == OverworldEntityTypes.UNIT_OBJ:
            entity_position = s_dict['position']
            entity_object = OverworldEntityObject.from_unit_object(entity_nid, entity_position, prefab_nid, game.unit_registry)
            return entity_object
        else:
            raise TypeError("Unknown OverworldEntityType")

    @property
    def display_position(self) -> Point:
        if self._display_position:
            return self._display_position
        elif self.sprite.fake_position:
            return self.sprite.fake_position
        elif self.on_node:
            for overworld in DB.overworlds.values():
                node = overworld.overworld_nodes.get(self.on_node, None)
                if node is not None:
                    return node.pos
        else:
            return None

    @display_position.setter
    def display_position(self, pos: Point):
        self._display_position = pos

    @property
    def prefab(self):
        if self.dtype == OverworldEntityTypes.PARTY:
            return DB.parties.get(self.dnid)
        elif self.dtype in (OverworldEntityTypes.UNIT, OverworldEntityTypes.UNIT_OBJ):
            return DB.units.get(self.dnid)
        else:
            raise TypeError("Unknown OverworldEntityType")
