from typing import Any, Dict, Iterable, List, Set, Tuple

from app.utilities.typing import NID, Pos

from app.utilities import utils
from app.utilities.data import Prefab
import app.map_maker.utilities as map_utils
from app.map_maker.terrain import Terrain
from app.map_maker.palette_collection import PaletteCollection
from app.map_maker.painter_database import PAINTERS
from app.map_maker.painters.sea_painter import SeaPainter
from app.map_maker.painters.pool_painter import PoolPainter

TILEX, TILEY = 15, 10

# Whether a sea or pool tile is open water depends on the closest
# land or non-pool tile up to this many tiles away along each axis
OPEN_WATER_SEARCH_RADIUS: Dict[Terrain, int] = {
    Terrain.SEA: SeaPainter.land_search_radius,
    Terrain.POOL: PoolPainter.nonpool_search_radius,
}

class MapPrefab(Prefab):
    def __init__(self, nid: NID):
        self.nid: NID = nid
        self.width, self.height = TILEX, TILEY
        self.autotile_fps: int = 29

        self.pixmap = None
        
        self.terrain_grid: Dict[Pos, Terrain] = {}
        self.terrain_grid_to_update: Set[Pos] = set()  # Positions
        self.tile_grid = {}  # Key: Position, Value: Tileset Coordinate (same size as terrain_grid)
        # Positions whose tile_grid entry was set or removed since a view last drew them
        self.tile_grid_changed: Set[Pos] = set()
        self.autotile_set: Set[Pos] = set()  # Positions
        # Key: Position in autotile_set, Value: its renderer's sprite coord,
        # so new autotile frames are drawn without recomputing it
        self.autotile_coords: Dict[Pos, Any] = {}

        self.cliff_markers: List[Pos] = [(7, 5)]  # Markers for how to point cliffs

        self.current_indoor_palette: PaletteCollection = None
        self.current_outdoor_palette: PaletteCollection = None

        # Per-map RNG seed. Kept in sync with the module-level RANDOM_SEED in
        # map_maker.utilities (which other painters still read); the mountain
        # painter/solver read it off the prefab as self.tilemap.seed.
        self.seed: int = 0

    def reset_all(self):
        for position in self.terrain_grid:
            self.terrain_grid_to_update.add(position)

    def set(self, pos: Pos, old_terrain: Terrain, new_terrain: Terrain):
        old_terrain_painter = PAINTERS.get(old_terrain)
        new_terrain_painter = PAINTERS.get(new_terrain)
        if old_terrain and old_terrain_painter.check_flood_fill:
            # Need to check flood fill both before and after changing terrain
            self._update_flood_fill(pos, old_terrain_painter.check_flood_fill == 'diagonal')
        self._place_terrain(pos, new_terrain)
        if new_terrain_painter.check_flood_fill:
            self._update_flood_fill(pos, new_terrain_painter.check_flood_fill == 'diagonal')

    def set_many(self, new_terrains: Dict[Pos, Terrain]):
        """
        set() for every position at once. Flood fills each blob once before and
        once after all the changes, rather than once per position -- a bucket
        fill of n tiles of a flood filled terrain would otherwise visit n^2 tiles
        """
        self._update_blobs_around(new_terrains.keys())
        for pos, new_terrain in new_terrains.items():
            self._place_terrain(pos, new_terrain)
        self._update_blobs_around(new_terrains.keys())

    def _place_terrain(self, pos: Pos, new_terrain: Terrain):
        self.terrain_grid[pos] = new_terrain
        self.terrain_grid_to_update.add(pos)
        self._update_adjacent(pos)
        self._update_diagonal(pos)
        self._update_nearby_open_water(pos)

        if PAINTERS.get(new_terrain).has_autotiles():
            self.autotile_set.add(pos)
        else:
            self.autotile_set.discard(pos)
            self.autotile_coords.pop(pos, None)

    def _update_blobs_around(self, positions: Iterable[Pos]):
        # Marks the blob at each of these positions whose terrain needs flood fill.
        # A blob holds one terrain, so a position in one already filled has the same blob
        filled: Set[Pos] = set()
        for pos in positions:
            terrain = self.get_terrain(pos)
            if pos in filled or not terrain:
                continue
            check_flood_fill = PAINTERS.get(terrain).check_flood_fill
            if check_flood_fill:
                blob_positions = map_utils.flood_fill(self, pos, check_flood_fill == 'diagonal')
                filled |= blob_positions
                self.terrain_grid_to_update |= blob_positions

    def set_new_terrain_grid(self, size: Tuple[int, int], terrain_grid: Dict[Pos, Terrain]):
        self.width, self.height = size
        self.terrain_grid = terrain_grid
        self.autotile_set.clear()
        self.autotile_coords.clear()
        for pos, terrain in self.terrain_grid.items():
            terrain_painter = PAINTERS.get(terrain)
            if terrain_painter.has_autotiles():
                self.autotile_set.add(pos)
        self.reset_all()

    def _update_adjacent(self, pos: Pos):
        # Now ask to update all the adjacent ones as well
        north, east, south, west = (pos[0], pos[1] - 1), (pos[0] + 1, pos[1]), (pos[0], pos[1] + 1), (pos[0] - 1, pos[1])
        if self.check_bounds(north) and self.get_terrain(north):
            self.terrain_grid_to_update.add(north)
        if self.check_bounds(east) and self.get_terrain(east):
            self.terrain_grid_to_update.add(east)
        if self.check_bounds(south) and self.get_terrain(south):
            self.terrain_grid_to_update.add(south)
        if self.check_bounds(west) and self.get_terrain(west):
            self.terrain_grid_to_update.add(west)

    def _update_diagonal(self, pos: Pos):
        # Now ask to update all the adjacent ones as well
        northeast, southeast, southwest, northwest = (pos[0] + 1, pos[1] - 1), (pos[0] + 1, pos[1] + 1), (pos[0] - 1, pos[1] + 1), (pos[0] - 1, pos[1] - 1)
        if self.check_bounds(northeast) and self.get_terrain(northeast):
            self.terrain_grid_to_update.add(northeast)
        if self.check_bounds(southeast) and self.get_terrain(southeast):
            self.terrain_grid_to_update.add(southeast)
        if self.check_bounds(southwest) and self.get_terrain(southwest):
            self.terrain_grid_to_update.add(southwest)
        if self.check_bounds(northwest) and self.get_terrain(northwest):
            self.terrain_grid_to_update.add(northwest)

    def _update_nearby_open_water(self, pos: Pos):
        # Sea and pool tiles within their open water search radius
        # of this position may change between open and closed water
        r = max(OPEN_WATER_SEARCH_RADIUS.values())
        for x in range(pos[0] - r, pos[0] + r + 1):
            for y in range(pos[1] - r, pos[1] + r + 1):
                terrain = self.get_terrain((x, y))
                if terrain in OPEN_WATER_SEARCH_RADIUS:
                    if max(abs(x - pos[0]), abs(y - pos[1])) <= OPEN_WATER_SEARCH_RADIUS[terrain]:
                        self.terrain_grid_to_update.add((x, y))

    def _update_flood_fill(self, pos: Pos, diagonal: bool = False):
        blob_positions = map_utils.flood_fill(self, pos, diagonal)
        for p in blob_positions:
            self.terrain_grid_to_update.add(p)

    def get_terrain(self, pos: Pos) -> Terrain:
        return self.terrain_grid.get(pos)

    def erase_terrain(self, pos: Pos, old_terrain: Terrain):
        old_terrain_painter = PAINTERS.get(old_terrain)
        if old_terrain and old_terrain_painter.check_flood_fill:
            self._update_flood_fill(pos, old_terrain_painter.check_flood_fill == 'diagonal')
        if pos in self.terrain_grid:
            del self.terrain_grid[pos]
        self.autotile_set.discard(pos)
        self.autotile_coords.pop(pos, None)

        if pos in self.tile_grid:
            del self.tile_grid[pos]
            self.tile_grid_changed.add(pos)

        self._update_adjacent(pos)
        self._update_diagonal(pos)
        self._update_nearby_open_water(pos)

    def get_cardinal_terrain(self, pos: Pos) -> Tuple[Terrain, Terrain, Terrain, Terrain]:
        north = self.get_terrain((pos[0], pos[1] - 1))
        east = self.get_terrain((pos[0] + 1, pos[1]))
        south = self.get_terrain((pos[0], pos[1] + 1))
        west = self.get_terrain((pos[0] - 1, pos[1]))
        return north, east, south, west

    def get_diagonal_terrain(self, pos: Pos) -> Tuple[Terrain, Terrain, Terrain, Terrain]:
        northeast = self.get_terrain((pos[0] + 1, pos[1] - 1))
        southeast = self.get_terrain((pos[0] + 1, pos[1] + 1))
        southwest = self.get_terrain((pos[0] - 1, pos[1] + 1))
        northwest = self.get_terrain((pos[0] - 1, pos[1] - 1))
        return northeast, southeast, southwest, northwest

    def clear(self):
        self.width, self.height = TILEX, TILEY
        self.terrain_grid.clear()
        self.terrain_grid_to_update.clear()
        self.tile_grid_changed.update(self.tile_grid)
        self.tile_grid.clear()
        self.autotile_set.clear()
        self.autotile_coords.clear()

    def check_bounds(self, pos: Pos):
        return 0 <= pos[0] < self.width and 0 <= pos[1] < self.height

    def get_all_terrain(self, terrain: Terrain) -> Set[Pos]:
        all_positions = set()
        for position, t in self.terrain_grid.items():
            if t == terrain:
                all_positions.add(position)
        return all_positions

    def resize(self, width: int, height: int, x_offset: int, y_offset: int):
        self.width = width
        self.height = height

        new_terrain_grid = {}
        for pos, terrain in self.terrain_grid.items():
            new_pos = pos[0] + x_offset, pos[1] + y_offset
            if self.check_bounds(new_pos):
                new_terrain_grid[new_pos] = terrain
        self.terrain_grid = new_terrain_grid

        new_tile_grid = {}
        for pos, tile_coord in self.tile_grid.items():
            new_pos = pos[0] + x_offset, pos[1] + y_offset
            if self.check_bounds(new_pos):
                new_tile_grid[new_pos] = tile_coord
        self.tile_grid_changed.update(self.tile_grid)
        self.tile_grid = new_tile_grid
        self.tile_grid_changed.update(self.tile_grid)

        # The autotile positions must be shifted along with the terrain they
        # belong to. Leaving them at their old positions means draw_tilemap's
        # autotile pass calls determine_sprite() on whatever terrain happens to
        # have moved onto that position -- bypassing the terrain_grid_to_update
        # gate -- and painters that build their coords in single_process()
        # (mountain, cliff, ...) have no entry for it yet.
        new_autotile_set = set()
        for pos in self.autotile_set:
            new_pos = pos[0] + x_offset, pos[1] + y_offset
            if self.check_bounds(new_pos):
                new_autotile_set.add(new_pos)
        self.autotile_set = new_autotile_set
        # reset_all() below recomputes every autotile coord
        self.autotile_coords.clear()

        # Cliff markers are map positions as well
        self.cliff_markers = [(int(utils.clamp(pos[0] + x_offset, 0, width - 1)),
                               int(utils.clamp(pos[1] + y_offset, 0, height - 1)))
                              for pos in self.cliff_markers]

        # Every painter's cached organization is keyed off position, so all of
        # it is stale now -- kill any in-flight solve (it would report sprites
        # at pre-resize positions) and force a full recompute on the next draw
        for painter in PAINTERS.values():
            painter.quit_all_threads()
        self.terrain_grid_to_update.clear()
        self.reset_all()

    def save(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['size'] = self.width, self.height
        if self.width == 0 or self.height == 0:
            print("TileMap: Width or Height == 0!!!")
        s_dict['autotile_fps'] = self.autotile_fps
        s_dict['cliff_markers'] = self.cliff_markers[:]
        s_dict['terrain_grid'] = {}
        for coord, terrain in self.terrain_grid.items():
            str_coord = "%d,%d" % (coord[0], coord[1])
            s_dict['terrain_grid'][str_coord] = terrain.name
        s_dict['autotile_set'] = ["%d,%d" % (coord[0], coord[1]) for coord in self.autotile_set]
        s_dict['seed'] = map_utils.get_random_seed()
        s_dict['indoor_palette'] = self.current_indoor_palette
        s_dict['outdoor_palette'] = self.current_outdoor_palette
        return s_dict

    @classmethod
    def restore(cls, s_dict):
        self = cls(s_dict['nid'])
        self.width, self.height = s_dict['size']
        self.autotile_fps = s_dict.get('autotile_fps', 29)
        self.cliff_markers = s_dict.get('cliff_markers', [(0, 0)])
        self.cliff_markers = [tuple(_) for _ in self.cliff_markers]
        for str_coord, terrain in s_dict['terrain_grid'].items():
            coord = tuple(int(_) for _ in str_coord.split(','))
            self.terrain_grid[coord] = Terrain[terrain]
        self.autotile_set.clear()
        for str_coord in s_dict['autotile_set']:
            coord = tuple(int(_) for _ in str_coord.split(','))
            self.autotile_set.add(coord)
        self.seed = s_dict.get('seed', 0)
        map_utils.set_random_seed(self.seed)
        self.current_indoor_palette = s_dict.get('indoor_palette')
        self.current_outdoor_palette = s_dict.get('outdoor_palette')
        return self

    # @classmethod
    # def from_terrain_grid(cls, nid: NID, width: int, height: int, terrain_grid: Dict[Pos, Terrain]):
    #     self = cls(nid)
    #     self.width, self.height = width, height
    #     self.autotile_fps = 29
    #     self.cliff_markers = [(0, 0)]
    #     self.terrain_grid = terrain_grid
    #     self.autotile_set.clear()
    #     self.current_indoor_palette = PALETTES.indoor_palettes()[0]
    #     self.current_outdoor_palette = PALETTES.outdoor_palettes()[0]
    #     return self
