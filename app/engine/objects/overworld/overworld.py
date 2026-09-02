from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from app.constants import TILEHEIGHT, TILEWIDTH
from app.data.database.database import DB
from app.data.resources.resources import RESOURCES
from app.utilities.utils import magnitude, tuple_sub

if TYPE_CHECKING:
    from app.data.database.overworld import OverworldPrefab
    from app.data.database.units import UnitPrefab
    from app.data.database.overworld_node import OverworldNodePrefab
    from app.engine.game_state import GameState
    from app.engine.objects.party import PartyObject
    from app.engine.objects.unit import UnitObject

from app.engine.objects.tilemap import TileMapObject
from app.engine.overworld.overworld_map_sprites import (OverworldNodeSprite,
                                                        OverworldRoadSprite,
                                                        OverworldUnitSprite)
from app.engine.unit_sound import UnitSound
from app.data.resources.sounds import SongPrefab
from app.utilities.typing import NID, Point
from .overworld_entity import OverworldEntityObject

import logging

class OverworldNodeProperty():
    IS_NEXT_LEVEL = "IS_NEXT_LEVEL"

class OverworldNodeObject():
    def __init__(self):
        self.prefab: OverworldNodePrefab = None # prefab info
        self.sprite: OverworldNodeSprite = None # sprite

    @property
    def position(self) -> Point:
        return self.prefab.pos

    @property
    def nid(self) -> NID:
        return self.prefab.nid

    @property
    def name(self) -> str:
        return self.prefab.name

    @classmethod
    def from_prefab(cls, prefab: OverworldNodePrefab):
        node = cls()
        node.prefab = prefab
        node.sprite = OverworldNodeSprite(prefab)
        node.menu_options = prefab.menu_options
        return node

class RoadObject():
    def __init__(self):
        self.nid: NID = None
        self.prefab: List[Point] = None # "prefab", lol, really this is just the list of points
        self.sprite: OverworldRoadSprite = None # sprite

    def get_segments(self, road: List[Point]) -> List[Tuple[Point, Point]]:
        """turns road ( a list of points in sequence) into a list of road
        segments ( a list of two endpoints describing a line) for ease of use.

        Returns:
            List[Tuple[Point, Point]]: a list of road segments (two points) in sequence.
        """
        segments = []
        for i in range(len(road) - 1):
            segment = (road[i], road[i+1])
            segments.append(segment)
        return segments

    def road_in_pixel_coords(self) -> List[Point]:
        """Returns the same list of points that make up the road,
        but converted to pixel coordinates instead of tile coordinates
        for ease of drawing

        Returns:
            List[Point]: list of road point coordinates in pixels
        """
        pix_list = []
        for point in self.prefab:
            pix_x = point[0] * TILEWIDTH + TILEWIDTH / 2
            pix_y = point[1] * TILEHEIGHT + TILEHEIGHT / 2
            pix_list.append((pix_x, pix_y))
        return pix_list

    @property
    def pixel_length(self) -> float:
        """Property, returns total pixel length of the road.
        Useful for transitions.

        Returns:
            float: the pixel length of the road
        """
        length = 0
        pixel_road = self.road_in_pixel_coords()
        for segment in self.get_segments(pixel_road):
            length += (segment[1] - segment[0]).length()
        return length

    @property
    def tile_length(self) -> float:
        """Returns the "length" of the road in tiles.

        Returns:
            float: road length in tiles
        """
        length = 0
        for segment in self.get_segments(self.prefab):
            length += magnitude(tuple_sub(segment[1], segment[0]))
        return length

    @classmethod
    def from_prefab(cls, prefab: List[Point], nid: NID):
        # as above, this isn't actually a prefab, but follows the convention for ease of use
        road = cls()
        road.nid = nid
        road.prefab = [tuple(point) for point in prefab]
        road.sprite = OverworldRoadSprite(road)
        return road

# Main Overworld Object used by engine
class OverworldObject():
    def __init__(self):
        self.prefab: OverworldPrefab = None # the prefab information itself
        self.tilemap: TileMapObject = None  # tilemap
        self.enabled_nodes: Set[NID] = set() # set of ids of nodes that are accessible right now
        self.enabled_roads: Set[NID] = set() # set of ids of roads that are accessible right now
        self.enabled_menu_options: Dict[NID, Dict[NID, bool]] = {} # dict of node ids and node menu events that are accessible right now
        self.visible_menu_options: Dict[NID, Dict[NID, bool]] = {} # dict of node ids and node menu events that are visible right now
        self.overworld_entities: Dict[NID, OverworldEntityObject] = {} # list of entities on the map (e.g. player party, wandering encounters)

        self.selected_party_nid: NID = None

        self.node_properties: Dict[NID, Set[str]] = {}                     # allows us to assign arbitrary properties to nodes. Currently, only one property is supported:
                                                                            # "is_objective", indicating whether or not this node is the next objective (and whether or not to fly the little flag
                                                                            # on top of it) Could be useful for other properties in the future.
        # not saved since it's just a property
        self._music: SongPrefab = None # filename of overworld music file

    @property
    def nid(self) -> NID:
        return self.prefab.nid

    @property
    def name(self) -> str:
        return self.prefab.name

    @property
    def music(self) -> SongPrefab:
        if not self._music:
            self._music = RESOURCES.music.get(self.prefab.music)
        return self._music

    @classmethod
    def from_prefab(cls, prefab: OverworldPrefab, party_registry: Dict[NID, PartyObject], unit_registry: Dict[NID, UnitObject]):
        overworld = cls()
        tilemap_prefab = RESOURCES.tilemaps.get(prefab.tilemap)
        if tilemap_prefab:
            overworld.tilemap = TileMapObject.from_prefab(tilemap_prefab)
        overworld.prefab = prefab
        for pnid in party_registry.keys():
            overworld_party = OverworldEntityObject.from_party_prefab(None, pnid, unit_registry)
            overworld.overworld_entities[pnid] = overworld_party
        for node in overworld.prefab.overworld_nodes:
            overworld.enabled_menu_options[node.nid] = {}
            overworld.visible_menu_options[node.nid] = {}
            for option in node.menu_options:
                overworld.enabled_menu_options[node.nid][option.nid] = option.enabled
                overworld.visible_menu_options[node.nid][option.nid] = option.visible
        return overworld

    def save(self):
        s_dict = {'tilemap': self.tilemap.save() if self.tilemap else None,
                  'enabled_nodes': list(self.enabled_nodes),
                  'enabled_roads': list(self.enabled_roads),
                  'prefab_nid': self.nid,
                  'overworld_entities': [entity.save() for entity in self.overworld_entities.values()],
                  'selected_party_nid': self.selected_party_nid,
                  'node_properties': self.node_properties,
                  'enabled_menu_options':self.enabled_menu_options,
                  'visible_menu_options':self.visible_menu_options
                  }
        return s_dict

    @staticmethod
    def _restore_menu_options(from_prefab: Dict[NID, Dict[NID, bool]],
                              saved: Dict[NID, Dict[NID, bool]]) -> Dict[NID, Dict[NID, bool]]:
        """Which nodes exist, and which options they offer, is the prefab's to say. A save
        can only speak for the ones it knew about, so a node or option added since keeps the
        setting the prefab gives it, and one deleted since is dropped."""
        for node_nid, options in saved.items():
            if node_nid not in from_prefab:
                continue
            for option_nid, setting in options.items():
                if option_nid in from_prefab[node_nid]:
                    from_prefab[node_nid][option_nid] = setting
        return from_prefab

    @classmethod
    def restore(cls, s_dict: Dict, game: GameState) -> Optional[OverworldObject]:
        """Rebuilds a saved overworld, or returns None if the project no longer has it."""
        prefab = DB.overworlds.get(s_dict['prefab_nid'])
        if not prefab:
            logging.error("Save refers to overworld '%s', which is not in the database. "
                          "It was probably renamed or deleted since the save was made.",
                          s_dict['prefab_nid'])
            return None
        overworld = OverworldObject.from_prefab(prefab, game.parties, game.unit_registry)
        overworld.tilemap = TileMapObject.restore(s_dict['tilemap']) if s_dict['tilemap'] else None
        overworld.enabled_nodes = set(s_dict['enabled_nodes'])
        overworld.enabled_roads = set(s_dict['enabled_roads'])
        overworld.node_properties = s_dict.get('node_properties', {})
        overworld.enabled_menu_options = cls._restore_menu_options(
            overworld.enabled_menu_options, s_dict.get('enabled_menu_options', {}))
        overworld.visible_menu_options = cls._restore_menu_options(
            overworld.visible_menu_options, s_dict.get('visible_menu_options', {}))

        for entity in s_dict['overworld_entities']:
            entity_obj = OverworldEntityObject.restore(entity, game)
            overworld.overworld_entities[entity_obj.nid] = entity_obj

        overworld.selected_party_nid = s_dict['selected_party_nid']
        return overworld
