"""
# References:
https://pokemon-dungeoneer.vercel.app/
https://github.com/EpicYoshiMaster/dungeon-mystery
https://www.youtube.com/watch?v=fudOO713qYo
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Set, Tuple

from app.utilities import utils
from app.utilities.typing import Pos, NID
from app.utilities.direction import Direction, get_cardinal_positions, get_diagonal_positions
from app.utilities import static_random

import app.map_maker.utilities as map_utils
from app.map_maker.terrain import Terrain
from app.dungeon_maker.themes import PillarArrangement
from app.dungeon_maker.floor_level import FloorLevel
from app.dungeon_maker.dungeon_section import DungeonSection

import logging

PRINT = True

def generate_terrain(theme: Dict[NID, Any], seed: int) -> DungeonTileMap:
    while True:
        result = _generate_terrain_process(theme, seed)
        seed += 1  # If that didn't work, try a different seed
        if result:
            break

    return result

def _generate_terrain_process(theme: Dict[NID, Any], seed: int) -> Optional[DungeonTileMap]:
    tilemap = DungeonTileMap(theme, seed)

    # 1. Create a big old field of walls
    tilemap.reset_grid(Terrain.WALL_TOP)

    # 2. Divide walls into grid (3x3, 2x3, 5x2, etc.)
    # 3. In each subgrid, create a room, hallway anchor, or blank
    # 3.2. Randomly determine size (XxY) if room
    # 3.3. Randomly determine position in subgrid if room or hallway anchor
    num_rooms = tilemap.generate_rooms()
    if num_rooms < 2:  # Need at least 2 rooms
        return

    tilemap.print_sections()

    # 4. Connect rooms together with hallways
    # 4.1 Adjacent grids with rooms, randomly select a hallway size (1 or 2)
    # 4.2 Select an anchor point on each wall randomly
    # 4.3 If not perfect, on grid line is able to turn to match up with other room
    tilemap.connect_rooms()

    # 4.4 If some rooms were generated as blanks and using global background section, 
    #     connect all rooms with background
    if theme["use_global_section"]:
        tilemap.connect_global()

    # 5. Converts rooms and hallways to terrain (Floors, Walls, Stairs)
    tilemap.coerce_terrain()

    # 6. Any large empty areas with no terrain are filled with Floors and then connected to outside
    if theme["fill_in_empty_areas"]:
        tilemap.fill_in_empty_areas()

    tilemap.print_terrain_grid()

    if theme["use_water_chance"]:
        tilemap.generate_water()
        tilemap.print_terrain_grid()

    # All floor tiles must be reachable
    if not tilemap.is_fully_connected():
        return

    # 7. Make sure all walls are at least 2 tiles high if grounded on the lower level
    tilemap.make_walls_two_high()

    # 8. Add pillars to rooms
    # 8.1 Randomly determine which pillar pattern will be used for this room
    # 8.2 convert terrain to PILLAR
    tilemap.add_pillars()

    # At this point, sections can't matter anymore, only terrain matters now
    # 9. Flip top and left section over the x and/or y axis through the middle
    #    of the map to make the map symmetrical
    if theme["horiz_symmetry"]:
        tilemap.flip_over_y_axis()
    if theme["vert_symmetry"]:
        tilemap.flip_over_x_axis()

    # 11. Finalize walls and void positioning
    # 11.1 Takes the entire map and wraps it in 2 layers of walls to make sure there
    #      are no paths to outside the map
    # 11.2 Fills in any tiles surrounded on three sides by walls (does this twice)
    # 11.3 Converts walls, as appropriate, to WALL_BOTTOM
    # 11.4 Removes any wall that has no adjacent walls
    # 11.5 Crops the map to it's minimum possible size
    if not theme["use_global_section"]:
        tilemap.wrap_in_walls()
    tilemap.fill_in_crevices()
    tilemap.fill_in_crevices()  # Do it twice on purpose
    tilemap.split_walls()
    tilemap.remove_useless_stairs()
    tilemap.remove_single_wall()
    tilemap.print_terrain_grid()
    tilemap.crop_void()
    if theme["convert_void_to_water"]:
        tilemap.convert_void_to_water()
    # All floor tiles must be reachable
    if not tilemap.is_fully_connected():
        return

    tilemap.print_terrain_grid()

    return tilemap

class DungeonTileMap:
    def __init__(self, theme: Dict[NID, Any], seed: int):
        self.random = static_random.LCG(seed)
        print("Random Seed: %d" % seed)
        self.theme = theme
        self.width, self.height = theme["size"]
        self.terrain_grid: Dict[Pos, Terrain] = {}
        self.floor_grid: Dict[Pos, FloorLevel] = {}
        self.grid_size: Tuple[int, int] = theme["section_grid"]
        self.sections: Dict[Pos, DungeonSection] = {}
        self.global_empty_sections: List[Pos] = []  # If no room/hallway node is chosen, it goes here

        self.set_sections()

    def get_terrain(self, pos: Pos) -> Optional[Terrain]:
        return self.terrain_grid.get(pos, None)

    def get_open_tiles(self) -> List[Pos]:
        return [pos for pos, terrain in self.terrain_grid.items() if terrain in Terrain.floor_terrain()]

    def swap_terrain(self, terrain1: Terrain, terrain2: Terrain):
        """
        Converts all tiles with terrain of type terrain1 to 
        terrain of type terrain2
        """
        swap_to = set()
        for pos, terrain in self.terrain_grid.items():
            if terrain == terrain1:
                swap_to.add(pos)
        for pos in swap_to:
            self.terrain_grid[pos] = terrain2

    def check_bounds(self, pos: Pos) -> bool:
        return 0 <= pos[0] < self.width and 0 <= pos[1] < self.height

    def reset_grid(self, terrain: Terrain):
        for x in range(self.width):
            for y in range(self.height):
                self.terrain_grid[(x, y)] = terrain
        self.floor_grid.clear()

    def flip_over_x_axis(self):
        midpoint = self.height // 2
        # Flips the terrain
        for x in range(self.width):
            for y in range(midpoint):
                self.terrain_grid[(x, self.height - y - 1)] = self.terrain_grid[(x, y)]
                self.floor_grid[(x, self.height - y - 1)] = self.floor_grid.get((x, y))

    def flip_over_y_axis(self):
        midpoint = self.width // 2
        # Flips the terrain
        for x in range(midpoint):
            for y in range(self.height):
                if self.terrain_grid[(x, y)] == Terrain.STAIRS_LEFT:
                    new_terrain = Terrain.STAIRS_RIGHT
                elif self.terrain_grid[(x, y)] == Terrain.STAIRS_RIGHT:
                    new_terrain = Terrain.STAIRS_LEFT
                else:
                    new_terrain = self.terrain_grid[(x, y)]
                self.terrain_grid[(self.width - x - 1, y)] = new_terrain
                self.floor_grid[(self.width - x - 1, y)] = self.floor_grid.get((x, y))

    def is_fully_connected(self) -> bool:
        floor_terrain = Terrain.get_all_floor()
        floor_tiles = {pos for pos, terrain in self.terrain_grid.items() 
                       if terrain in floor_terrain}
        test_pos = floor_tiles.pop()
        traversable_terrain = Terrain.get_all_indoor_traversable()
        can_reach = map_utils.flood_fill(self, test_pos, match=traversable_terrain)
        floor_tiles -= can_reach
        if floor_tiles:
            self.print_terrain_grid()
            # There are some tiles that haven't been reached
            logging.debug("Could not find these tiles:", sorted(floor_tiles))
            logging.debug(sorted(can_reach))
            return False
        return True

    def set_sections(self):
        x, y = self.grid_size
        xsize = self.width / x
        ysize = self.height / y 
        for xi in range(x):
            for yi in range(y):
                offset = (int(xi * xsize), int(yi * ysize))
                self.sections[(xi, yi)] = \
                    DungeonSection((int(xsize), int(ysize)), offset, self)

    def generate_rooms(self) -> int:
        """
        Returns the number of rooms generated
        """
        full_rooms_generated = 0
        for spos, section in self.sections.items():
            val = self.random.random()
            if val < self.theme["room_chance"]:
                section.generate_room()
                full_rooms_generated += 1
            elif val < self.theme["room_chance"] + self.theme["hallway_chance"]:
                section.generate_hallway_node()
            else:
                self.global_empty_sections.append(spos)
        return full_rooms_generated

    def connect_rooms(self):
        complete: Set[Tuple[Pos, Pos]] = set()
        coords = sorted(self.sections.keys())
        for coord in coords:
            section = self.sections.get(coord)
            if not section.room:
                continue
            x, y = coord
            # Only need to support these two directions
            directions = [
                # ((x - 1, y), Direction.WEST), 
                ((x + 1, y), Direction.EAST),
                # ((x, y - 1), Direction.NORTH),
                ((x, y + 1), Direction.SOUTH),
            ]
            for adj, direction in directions:
                # Don't do it twice
                if (coord, adj) in complete or (adj, coord) in complete:
                    continue
                adj_section = self.sections.get(adj)
                if adj_section and adj_section.room:
                    section.connect(adj_section, direction)
                    complete.add((coord, adj))
                    self.print_sections()

    def connect_global(self):
        # now build hallways
        coords = sorted(self.sections.keys())
        for spos in coords:
            section = self.sections.get(spos)
            if not section.room:
                continue
            x, y = spos
            directions = [
                ((x - 1, y), Direction.WEST), 
                ((x + 1, y), Direction.EAST),
                ((x, y - 1), Direction.NORTH),
                ((x, y + 1), Direction.SOUTH),
            ]
            for adj, direction in directions:
                adj_section = self.sections.get(adj)
                if adj_section and not adj_section.room:
                    logging.debug(spos, adj, direction)
                    section.connect_global(direction)
                    self.print_sections()

    def coerce_terrain(self):
        """
        All areas that are not covered by a room or hallway, fill with Terrain.FLOOR_LOWER
        Then connect them to the main sections
        """

        # Fill all rooms
        for section_pos, section in self.sections.items():    
            if section.room:
                # If the room should be upper
                # Only time this would work is if the room is not a full room (just a hallway node)
                # AND none of it's adjacent rooms are UPPER rooms
                if section.room.floor_level == FloorLevel.UPPER \
                        and (section.has_full_room() 
                             or any(adj.room and adj.room.floor_level == FloorLevel.UPPER for adj in self._get_adj_sections(section_pos))):
                    terrain = self.theme["floor_upper"]
                    level = FloorLevel.UPPER
                else:
                    terrain = self.theme["floor_lower"]
                    level = FloorLevel.LOWER
                for pos in section.room.get_true_positions():
                    self.terrain_grid[pos] = terrain
                    self.floor_grid[pos] = level

        # print("--- After Room Fill ---")
        # self.print_terrain_grid()

        # Fill in global area
        if self.theme["use_global_section"]:
            wall_terrain = Terrain.WALL_TOP
            wall_tiles = {pos for pos, terrain in self.terrain_grid.items() 
                          if terrain == wall_terrain
                          and all(not aterrain or aterrain == wall_terrain for aterrain in (self.get_cardinal_terrain(pos) + self.get_diagonal_terrain(pos)))}
            # Actually convert areas
            for pos in wall_tiles:
                self.terrain_grid[pos] = self.theme["floor_lower"]
                self.floor_grid[pos] = FloorLevel.LOWER

        # print("--- After Global Fill ---")
        # self.print_terrain_grid()

        # Fill all hallways
        for section_pos, section in self.sections.items():
            for direction, hallway in section.hallways.items():
                other_section = self._get_section_in_direction(section_pos, direction)
                if section.room.floor_level == FloorLevel.UPPER and other_section \
                        and other_section.room and other_section.room.floor_level == FloorLevel.UPPER:
                    terrain = self.theme["floor_upper"]
                    level = FloorLevel.UPPER
                else:
                    terrain = self.theme["floor_lower"]
                    level = FloorLevel.LOWER
                for pos in hallway:
                    self.terrain_grid[pos] = terrain
                    self.floor_grid[pos] = level

        # print("--- After Hallway Fill ---")
        # self.print_terrain_grid()

        # Make sure stairs won't go straight into a wall
        while True:
            walls = (Terrain.WALL_TOP, Terrain.WALL_BOTTOM, Terrain.COLUMN)
            to_fix = set()
            for pos, terrain in self.terrain_grid.items():
                if self.floor_grid.get(pos) != FloorLevel.LOWER:
                    continue
                north, east, south, west = self.get_cardinal_terrain(pos)
                ne, se, sw, nw = self.get_diagonal_terrain(pos)
                nfl, efl, sfl, wfl = self.get_cardinal_floor_level(pos)
                if efl == FloorLevel.UPPER and west in walls:
                    to_fix.add(pos)
                elif wfl == FloorLevel.UPPER and east in walls:
                    to_fix.add(pos)
                elif nfl == FloorLevel.UPPER and south in walls:
                    to_fix.add(pos)
                elif sfl == FloorLevel.UPPER and north in walls:
                    to_fix.add(pos)
                # Prevent building a wall above stairs that would result in a hallway being blocked
                elif wfl == FloorLevel.UPPER and efl == FloorLevel.LOWER \
                        and nfl == FloorLevel.LOWER and ne in walls and nw in walls:
                    to_fix.add(pos)
                elif efl == FloorLevel.UPPER and wfl == FloorLevel.LOWER \
                        and nfl == FloorLevel.LOWER and ne in walls and nw in walls:
                    to_fix.add(pos)
            for pos in to_fix:
                self.terrain_grid[pos] = self.theme["floor_upper"]
                self.floor_grid[pos] = FloorLevel.UPPER
            if not to_fix:
                break
            to_fix.clear()

        # print("--- After Stairs should not run into walls ---")
        # self.print_terrain_grid()

        # Flood fill to find small areas of floor surrounded by areas of other kind and switch them
        floor_tiles = {pos for pos, terrain in self.terrain_grid.items() 
                       if terrain in Terrain.get_all_floor()}
        while floor_tiles:
            test_pos = floor_tiles.pop()
            swap_to = self.theme["floor_lower"] \
                if self.floor_grid.get(test_pos) == FloorLevel.UPPER \
                else self.theme["floor_upper"]
            swap_to_floor_level = FloorLevel.LOWER \
                if self.floor_grid.get(test_pos) == FloorLevel.UPPER \
                else FloorLevel.UPPER
            friends = map_utils.flood_fill(self, test_pos)
            if len(friends) <= self.theme["small_floor_section_area"]:  # Very conservative
                # Section is too small, swap to other side
                for pos in friends:
                    self.terrain_grid[pos] = swap_to
                    self.floor_grid[pos] = swap_to_floor_level
            floor_tiles -= friends

        # print("--- Remove Small Areas ---")
        # self.print_terrain_grid()

        # Create stairs
        for pos, terrain in self.terrain_grid.items():
            if self.floor_grid.get(pos) != FloorLevel.LOWER:
                continue
            east_pos = (pos[0] + 1, pos[1])
            west_pos = (pos[0] - 1, pos[1])
            north_pos = (pos[0], pos[1] - 1)
            south_pos = (pos[0], pos[1] + 1)
            if self.floor_grid.get(east_pos) == FloorLevel.UPPER:
                self.terrain_grid[pos] = Terrain.STAIRS_RIGHT
                self.floor_grid[pos] = None
            elif self.floor_grid.get(west_pos) == FloorLevel.UPPER:
                self.terrain_grid[pos] = Terrain.STAIRS_LEFT
                self.floor_grid[pos] = None
            elif self.floor_grid.get(north_pos) == FloorLevel.UPPER:
                self.terrain_grid[pos] = Terrain.STAIRS_UPDOWN
                self.floor_grid[pos] = None
            elif self.floor_grid.get(south_pos) == FloorLevel.UPPER:
                self.terrain_grid[pos] = Terrain.STAIRS_UPDOWN
                self.floor_grid[pos] = None

        # print("--- After Creating Stairs ---")
        # self.print_terrain_grid()

        def set_to_wall_by_stairs(new_pos: Pos, check_terrain: Terrain, 
                                  direction: Direction, stair_terrains: Tuple[Terrain]):
            while check_terrain in stair_terrains:
                new_pos = Direction.next(direction, new_pos)
                check_terrain = self.terrain_grid.get(new_pos)
            if check_terrain:
                self.terrain_grid[new_pos] = Terrain.WALL_TOP

        # Make sure stairs have a wall above them
        for pos, terrain in self.terrain_grid.items():
            stair_terrains = (Terrain.STAIRS_RIGHT, Terrain.STAIRS_LEFT)
            if terrain in stair_terrains:
                set_to_wall_by_stairs(pos, terrain, Direction.NORTH, stair_terrains)
                set_to_wall_by_stairs(pos, terrain, Direction.SOUTH, stair_terrains)

            stair_terrains = (Terrain.STAIRS_UPDOWN,)
            if terrain in stair_terrains:
                set_to_wall_by_stairs(pos, terrain, Direction.EAST, stair_terrains)
                set_to_wall_by_stairs(pos, terrain, Direction.WEST, stair_terrains)

        # print("--- After making sure stairs have a wall above them ---")
        # self.print_terrain_grid()

    def generate_water(self):
        """
        Randomly select rooms/hallways (of lower floor) that should be considered on water
        For each wall/void in the section, convert to water
        Convert terrain.FLOOR_LOWER -> terrain.POOL_BRIDGE if no longer touching any wall
        """
        # Find low sections
        water_sections = []
        for section_pos, section in self.sections.items():    
            if section.room and section.room.floor_level == FloorLevel.LOWER \
                    and self.random.random() < self.theme["use_water_chance"]:
                water_sections.append(section)

        # Get all positions in those sections
        all_terrain_positions = []
        for section in water_sections:
            all_terrain_positions += section.get_true_positions()

        # Swap Walls and Void to Water
        # And Swap Floor to Water Bridge
        wall_terrain_to_change = []
        floor_terrain_to_change = []
        for pos, terrain in self.terrain_grid.items():
            if pos in all_terrain_positions:
                # Don't change walls above stairs
                if terrain in (Terrain.WALL_TOP, Terrain.VOID) \
                        and self.terrain_grid.get((pos[0], pos[1] + 1)) not in (Terrain.STAIRS_RIGHT, Terrain.STAIRS_LEFT, self.theme["floor_upper"]) \
                        and self.terrain_grid.get((pos[0], pos[1] - 1)) not in (Terrain.STAIRS_RIGHT, Terrain.STAIRS_LEFT, self.theme["floor_upper"]) \
                        and self.terrain_grid.get((pos[0] - 1, pos[1])) not in (Terrain.STAIRS_UPDOWN, self.theme["floor_upper"]) \
                        and self.terrain_grid.get((pos[0] + 1, pos[1])) not in (Terrain.STAIRS_UPDOWN, self.theme["floor_upper"]):
                    wall_terrain_to_change.append(pos)
                elif self.floor_grid.get(pos) == FloorLevel.LOWER:
                    floor_terrain_to_change.append(pos)
        for pos in wall_terrain_to_change:
            self.terrain_grid[pos] = Terrain.POOL        
        for pos in floor_terrain_to_change:
            self.terrain_grid[pos] = Terrain.POOL_BRIDGE
            self.floor_grid[pos] = None

    def generate_void(self):
        convert_to_void: Set[Pos] = set()
        for pos, terrain in self.terrain_grid.items():
            if terrain not in (Terrain.get_all_wall()):
                continue
            adj_positions = get_cardinal_positions(pos) + get_diagonal_positions(pos)
            adj_positions = [adj for adj in adj_positions if self.check_bounds(adj)]
            if all(self.terrain_grid[adj] in Terrain.get_all_wall() for adj in adj_positions):
                convert_to_void.add(pos)

        for pos in convert_to_void:
            self.terrain_grid[pos] = Terrain.VOID

    def get_cardinal_terrain(self, pos: Pos) -> List[Optional[Terrain]]:
        return [self.get_terrain(adj) for adj in get_cardinal_positions(pos)]

    def get_diagonal_terrain(self, pos: Pos) -> List[Optional[Terrain]]:
        return [self.get_terrain(adj) for adj in get_diagonal_positions(pos)]

    def get_cardinal_floor_level(self, pos: Pos) -> List[Optional[FloorLevel]]:
        return [self.floor_grid.get(adj) for adj in get_cardinal_positions(pos)]

    def _get_section(self, pos: Pos) -> Optional[DungeonSection]:
        for section in self.sections.values():
            if pos in section.get_true_positions():
                return section
        return None

    def _get_section_in_direction(self, pos: Pos, direction: Direction) -> Optional[DungeonSection]:
        """
        Uses Section positions, not true positions
        """
        section_pos = Direction.next(direction, pos)
        return self.sections.get(section_pos)

    def _get_adj_sections(self, pos: Pos) -> List[DungeonSection]:
        """
        Uses section positions, not true positions
        """
        x, y = pos
        directions = [
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
            ]
        adj_sections = [self.sections.get(adj) for adj in directions]
        adj_sections = [_ for _ in adj_sections if _]
        return adj_sections

    def _is_low_floor(self, pos: Pos) -> bool:
        terrain = self.get_terrain(pos)
        return terrain in ( 
            Terrain.STAIRS_UPDOWN, 
            Terrain.POOL_BRIDGE,
            ) or self.floor_grid.get(pos) == FloorLevel.LOWER

    def _is_high_floor(self, pos: Pos) -> bool:
        terrain = self.get_terrain(pos)
        return terrain in (
            Terrain.STAIRS_LEFT, 
            Terrain.STAIRS_RIGHT,
            ) or self.floor_grid.get(pos) == FloorLevel.UPPER

    def _determine_floor_level(self, pos: Pos) -> FloorLevel:
        """
        Returns whether this is on floor level 1 (low) or 2 (high)
        Nothing else should use this, since the user of this painter should never
        have to care
        """
        while self.terrain_grid.get(pos):
            if self._is_high_floor(pos):
                return FloorLevel.UPPER
            elif self._is_low_floor(pos):
                return FloorLevel.LOWER
            pos = (pos[0], pos[1] + 1)
        return FloorLevel.LOWER

    def make_walls_two_high(self):
        """
        Any walls that are adjacent on the bottom side of their group
        to a LOWER_FLOOR must be at least 2 tiles high
        """

        # Figure out which spots should be swapped
        turn_into_walls = set()
    
        # Locate walls that are only 1 tile tall above FLOOR_LOWER
        bad_walls: Set[Pos] = set()
        for pos, val in self.terrain_grid.items():
            north, _, south, _ = self.get_cardinal_terrain(pos)
            south_floor = self.floor_grid.get((pos[0], pos[1] + 1))
            if val == Terrain.WALL_TOP and north and south \
                    and north != Terrain.WALL_TOP \
                    and south != Terrain.WALL_TOP \
                    and south_floor != FloorLevel.UPPER \
                    and south != Terrain.STAIRS_LEFT \
                    and south != Terrain.STAIRS_RIGHT:
                bad_walls.add(pos)

        # Handle each of these walls in groups
        while bad_walls:
            test_pos = next(iter(bad_walls))
            wall_group = map_utils.flood_fill(self, test_pos, match_only_these_positions=bad_walls)
            # Figure out which side (top or bottom) handles a wall addition better
            # If all of the positions south 2 tiles are exist and are not wall
            # Easy fix to make it lower by 1
            if all(self.terrain_grid.get((pos[0], pos[1] + 2), Terrain.WALL_TOP) != Terrain.WALL_TOP for pos in wall_group):
                for pos in wall_group:
                    turn_into_walls.add((pos[0], pos[1] + 1))
            # If all of the positions north 2 tiles are exist and are not wall
            # Easy fix to make it higher by 1
            elif all(self.terrain_grid.get((pos[0], pos[1] - 2), Terrain.WALL_TOP) != Terrain.WALL_TOP for pos in wall_group):
                for pos in wall_group:
                    turn_into_walls.add((pos[0], pos[1] - 1))
            # Fallback option is turn the south into a wall
            else:
                for pos in wall_group:
                    turn_into_walls.add((pos[0], pos[1] + 1))
            bad_walls -= wall_group

        # Actually swap them
        for pos in turn_into_walls:
            self.terrain_grid[pos] = Terrain.WALL_TOP
            self.floor_grid[pos] = None

    def add_pillars(self, upper_floor_only: bool = False):
        """
        For each room, determines what pillar arrangement should exist
        """
        final_pillar_positions = set()
        final_column_positions = set()
        for section_grid_pos, section in self.sections.items():
            if self.random.random() > self.theme["pillar_chance"]:
                continue
            if not section.has_big_room():
                continue
            if upper_floor_only and section.room.floor_level == FloorLevel.LOWER:
                continue
            ox, oy = section.room.get_true_offset()
            # Whether the room is taller than it is wide
            is_vertical = section.room.height >= section.room.width
            # Determine whether the smaller width of the room is even or odd
            if is_vertical:
                is_odd = section.room.width % 2 == 1
            else:
                is_odd = section.room.height % 2 == 1
            if is_odd:
                arrs = [
                    PillarArrangement.OnEdge, 
                    PillarArrangement.FourCorners, 
                    PillarArrangement.NearEdge, 
                    PillarArrangement.Middle, 
                    PillarArrangement.Middle,
                ]
            else:
                arrs = [
                    PillarArrangement.OnEdge, 
                    PillarArrangement.FourCorners, 
                    PillarArrangement.NearEdge, 
                ]
            arr = self.random.choice(arrs)
            pillar_positions = set()
            if arr == PillarArrangement.NoPillars:
                continue  # No need to do anything at all
            elif arr == PillarArrangement.OnEdge:
                if is_vertical:
                    # Find positions on height
                    pillar_positions |= {(ox, oy + y) for y in range(1, section.room.height, 3)}
                    pillar_positions |= {(ox + section.room.width - 1, oy + y) for y in range(1, section.room.height, 3)}
                else:
                    pillar_positions |= {(ox + x, oy) for x in range(1, section.room.width, 3)}
                    pillar_positions |= {(ox + x, oy + section.room.height - 1) for x in range(1, section.room.width, 3)}
            elif arr == PillarArrangement.NearEdge:
                if is_vertical:
                    # Find positions on height
                    pillar_positions |= {(ox + 1, oy + y) for y in range(1, section.room.height - 1, 3)}
                    pillar_positions |= {(ox + section.room.width - 2, oy + y) for y in range(1, section.room.height - 1, 3)}
                else:
                    pillar_positions |= {(ox + x, oy + 1) for x in range(1, section.room.width - 1, 3)}
                    pillar_positions |= {(ox + x, oy + section.room.height - 2) for x in range(1, section.room.width - 1, 3)}
            elif arr == PillarArrangement.Middle:
                if is_vertical:
                    # Find positions on height
                    pillar_positions |= {(ox + section.room.width // 2, oy + y) for y in range(1, section.room.height, 3)}
                else:
                    pillar_positions |= {(ox + x, oy + section.room.height // 2) for x in range(1, section.room.width, 3)}
            elif arr == PillarArrangement.FourCorners:
                inner_positions = section.room.get_true_inner_positions()
                if inner_positions:
                    topleft = sorted(inner_positions)[0]
                    bottomright = sorted(inner_positions, reverse=True)[0]
                    topright = sorted(inner_positions, key=lambda pos: (-pos[0], pos[1]))[0]
                    bottomleft = sorted(inner_positions, key=lambda pos: (pos[0], -pos[1]))[0]
                    pillar_positions |= {topleft, topright, bottomright, bottomleft}

            # Decide whether these should be pillars or columns
            # Columns only for certain arrangements with a big enough room
            if arr in (PillarArrangement.FourCorners,) \
                    and section.room.width >= 5 and section.room.height >= 5 \
                    and section.room.floor_level == FloorLevel.LOWER:
                sorted_positions = sorted(pillar_positions, key=lambda pos: pos[1])
                top_positions = set(sorted_positions[:2])
                bottom_positions = set(sorted_positions[2:])

                column_positions = set()
                column_positions |= top_positions
                # Make the bottom columns point up instead of taking up space below them
                column_positions |= {(pos[0], pos[1] - 1) for pos in bottom_positions}
                # If we are near the top, point the columns up more
                if section_grid_pos[1] < self.grid_size[1] - 1:
                    column_positions |= {(pos[0], pos[1] - 1) for pos in column_positions}
                else:
                    column_positions |= {(pos[0], pos[1] + 1) for pos in column_positions}
                final_column_positions |= column_positions
            else:
                final_pillar_positions |= pillar_positions

        final_pillar_positions = [pos for pos in final_pillar_positions if self.terrain_grid[(pos[0], pos[1] + 1)] in Terrain.get_all_floor()]
        final_column_positions = [pos for pos in final_column_positions if self.terrain_grid[(pos[0], pos[1] + 1)] in Terrain.get_all_floor()]

        for pos in final_pillar_positions:
            self.terrain_grid[pos] = Terrain.PILLAR
            self.floor_grid[pos] = None
        for pos in final_column_positions:
            self.terrain_grid[pos] = Terrain.COLUMN
            self.floor_grid[pos] = None

    def fill_in_empty_areas(self):
        """
        Find large empty areas (of walls) and fill in with Terrain.FLOOR_LOWER
        """
        # Find the large wall areas
        wall_terrain = Terrain.WALL_TOP
        wall_tiles = {pos for pos, terrain in self.terrain_grid.items() 
                      if terrain == wall_terrain
                      and all(aterrain == wall_terrain for aterrain in (self.get_cardinal_terrain(pos) + self.get_diagonal_terrain(pos)))}
        orig_wall_tiles = wall_tiles.copy()
        new_floor_sections: List[Set[Pos]] = []  # List of sets of positions that can be converted to floor
        border_sections: List[Set[Pos]] = []  # List of walls around the the wall section
        outside_sections: List[Set[Pos]] = []  # List of outside areas

        while wall_tiles:
            test_pos = wall_tiles.pop()
            can_reach = map_utils.flood_fill(self, test_pos, match_only_these_positions=orig_wall_tiles)
            wall_tiles -= can_reach
            new_floor_sections.append(can_reach)

        # Only care about big sections
        new_floor_sections = [section for section in new_floor_sections if len(section) >= 10]

        # Find bordering walls
        for section in new_floor_sections:
            border = set()
            for pos in section:
                for apos in get_cardinal_positions(pos):
                    if apos not in section and self.terrain_grid.get(apos) == Terrain.WALL_TOP:
                        border.add(apos)
            border_sections.append(border)

        # Find nearby good directions we can tunnel to
        for section in border_sections:
            all_outside_positions = set()
            for pos in section:
                for apos in get_cardinal_positions(pos):
                    if self.terrain_grid.get(apos) in Terrain.get_all_floor():
                        all_outside_positions.add(apos)
            outside_sections.append(all_outside_positions)

        for section in new_floor_sections:
            for pos in section:
                self.terrain_grid[pos] = self.theme["floor_lower"]
                self.floor_grid[pos] = FloorLevel.LOWER

        def get_adjacent_positions(pos: Pos) -> List[Pos]:
            x, y = pos
            adjs = ((x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1))
            return adjs

        # Find a couple random border positions that are adjacent to both main section and outside section
        # Remove them and replace them with floor or stairs
        for idx in range(len(new_floor_sections)):
            counter = 0
            borders = sorted(border_sections[idx])
            while counter < 6 and borders:
                pos = self.random.choice(borders)
                borders.remove(pos)
                x, y = pos
                if any(apos in outside_sections[idx] for apos in get_adjacent_positions(pos)) \
                        and any(apos in new_floor_sections[idx] for apos in get_adjacent_positions(pos)):
                    if (x - 1, y) in new_floor_sections[idx] and (x + 1, y) in outside_sections[idx]:
                        if self.floor_grid.get((x + 1, y)) == FloorLevel.UPPER:
                            self.terrain_grid[pos] = Terrain.STAIRS_RIGHT
                            self.floor_grid[pos] = None
                        else:
                            self.terrain_grid[pos] = self.theme["floor_lower"]
                            self.floor_grid[pos] = FloorLevel.LOWER
                    elif (x + 1, y) in new_floor_sections[idx] and (x - 1, y) in outside_sections[idx]:
                        if self.floor_grid.get((x - 1, y)) == FloorLevel.UPPER:
                            self.terrain_grid[pos] = Terrain.STAIRS_LEFT
                            self.floor_grid[pos] = None
                        else:
                            self.terrain_grid[pos] = self.theme["floor_lower"]
                            self.floor_grid[pos] = FloorLevel.LOWER
                    elif (x, y - 1) in new_floor_sections[idx] and (x, y + 1) in outside_sections[idx]:
                        if self.floor_grid.get((x, y + 1)) == FloorLevel.UPPER:
                            self.terrain_grid[pos] = Terrain.STAIRS_DOWN
                            self.floor_grid[pos] = None
                        else:
                            self.terrain_grid[pos] = self.theme["floor_lower"]
                            self.floor_grid[pos] = FloorLevel.LOWER
                    elif (x, y + 1) in new_floor_sections[idx] and (x, y - 1) in outside_sections[idx]:
                        if self.floor_grid.get((x, y - 1)) == FloorLevel.UPPER:
                            self.terrain_grid[pos] = Terrain.STAIRS_UPDOWN
                            self.floor_grid[pos] = None
                        else:
                            self.terrain_grid[pos] = self.theme["floor_lower"]
                            self.floor_grid[pos] = FloorLevel.LOWER
                    else:
                        continue
                    counter += 1
                
    def wrap_in_walls(self):
        """
        Takes the entire map and wraps it in 2 layers of walls to make sure there
        are no paths to outside the map
        """
        # Enlarge the terrain_grid
        # Move the grid 1 to the right and 2 the bottom
        new_terrain_grid, new_floor_grid = {}, {}
        for pos, val in self.terrain_grid.items():
            new_terrain_grid[(pos[0] + 1, pos[1] + 2)] = val
        for pos, val in self.floor_grid.items():
            new_floor_grid[(pos[0] + 1, pos[1] + 2)] = val

        # Now add the surrounding walls
        for x in [0, self.width + 1]:
            for y in range(self.height + 4):
                new_terrain_grid[(x, y)] = Terrain.WALL_TOP
                new_floor_grid[(x, y)] = None
        for y in [0, 1, self.height + 2, self.height + 3]:
            for x in range(self.width + 2):
                new_terrain_grid[(x, y)] = Terrain.WALL_TOP
                new_floor_grid[(x, y)] = None

        self.terrain_grid = new_terrain_grid
        self.floor_grid = new_floor_grid
        self.width += 2
        self.height += 4

    def fill_in_crevices(self):
        """
        Finds "crevices" and fills them in as walls
        If # is walls and _ is not a wall
        # # _
        # _ _
        # # _
        the middle tile would be a crevice
        """
        to_fix = set()
        for pos, terrain in self.terrain_grid.items():
            if terrain == Terrain.WALL_TOP:
                continue
            north, east, south, west = self.get_cardinal_terrain(pos)
            if sum(t == Terrain.WALL_TOP for t in [north, east, south, west]) >= 3:
                to_fix.add(pos)
        for pos in to_fix:
            self.terrain_grid[pos] = Terrain.WALL_TOP
            self.floor_grid[pos] = None

    def split_walls(self):
        """
        Converts walls from ALL WALL_TOP, and determines which should become WALL_BOTTOM and/or VOID
        whether we need a TOP wall or a BOTTOM wall for this sprite
        """
        all_walls = {pos for pos, terrain in self.terrain_grid.items() if terrain == Terrain.WALL_TOP}

        def is_wall(terrain: Terrain) -> bool:
            return terrain == Terrain.WALL_TOP or terrain == Terrain.WALL_BOTTOM

        # First, build standalone columns
        for pos in all_walls.copy():
            north, east, south, west = self.get_cardinal_terrain(pos)
            if not is_wall(east) and not is_wall(west) and not is_wall(south):
                if self._determine_floor_level(pos) == FloorLevel.LOWER \
                        and north == Terrain.WALL_TOP:
                    self.terrain_grid[pos] = Terrain.WALL_BOTTOM
                all_walls.remove(pos)

        for pos in all_walls.copy():
            south_pos = (pos[0], pos[1] + 1)
            if is_wall(self.terrain_grid.get(south_pos)) or not self.check_bounds(south_pos):
                all_walls.remove(pos)

        for pos in all_walls.copy():
            south_pos = (pos[0], pos[1] + 1)
            north_pos = (pos[0], pos[1] - 1)
            north, _, south, _ = self.get_cardinal_terrain(pos)
            if (is_wall(north) or not self.check_bounds(north_pos)) \
                    and not is_wall(south) \
                    and (self._determine_floor_level(pos) == FloorLevel.LOWER
                         or self._determine_floor_level(south_pos) == FloorLevel.LOWER):
                self.terrain_grid[pos] = Terrain.WALL_BOTTOM
                all_walls.remove(pos)

        # Convert pieces that are surrounded to void
        convert_to_void: Set[Pos] = set()
        for pos in self.terrain_grid.keys():
            if self.terrain_grid.get(pos) == Terrain.WALL_TOP \
                    and all(terrain == Terrain.WALL_TOP or not self.check_bounds(adj) for terrain, adj in 
                            zip(self.get_cardinal_terrain(pos) + self.get_diagonal_terrain(pos),
                                get_cardinal_positions(pos) + get_diagonal_positions(pos))):
                convert_to_void.add(pos)

        for pos in convert_to_void:
            self.terrain_grid[pos] = Terrain.VOID
            self.floor_grid[pos] = None

    def remove_single_wall(self):
        """
        Any single wall by itself should be converted to nearby floor
        """
        convert_to_floor: Set[Pos] = set()
        for pos in self.terrain_grid.keys():
            if self.terrain_grid.get(pos) == Terrain.WALL_TOP \
                and all(terrain not in (Terrain.WALL_TOP, Terrain.WALL_BOTTOM) and self.check_bounds(adj) for terrain, adj in
                        zip(self.get_cardinal_terrain(pos), get_cardinal_positions(pos))):
                convert_to_floor.add(pos)

        for pos in convert_to_floor:
            self.terrain_grid[pos] = self.theme["floor_upper"]
            self.floor_grid[pos] = FloorLevel.UPPER

    def remove_useless_stairs(self):
        convert_to_floor_upper = set()
        convert_to_floor_lower = set()
        for pos, terrain in self.terrain_grid.items():
            if terrain == Terrain.STAIRS_RIGHT and self.terrain_grid.get((pos[0] + 1, pos[1])) == Terrain.STAIRS_LEFT:
                convert_to_floor_lower.add(pos)
                convert_to_floor_lower.add((pos[0] + 1, pos[1]))
            elif terrain == Terrain.STAIRS_LEFT and self.terrain_grid.get((pos[0] + 1, pos[1])) == Terrain.STAIRS_RIGHT:
                convert_to_floor_upper.add(pos)
                convert_to_floor_upper.add((pos[0] + 1, pos[1]))

        for pos in convert_to_floor_upper:
            self.terrain_grid[pos] = self.theme["floor_upper"]
            self.floor_grid[pos] = FloorLevel.UPPER
        for pos in convert_to_floor_lower:
            self.terrain_grid[pos] = self.theme["floor_lower"]
            self.floor_grid[pos] = FloorLevel.LOWER

    def crop_void(self):
        # Now crop out areas of just void
        # Left Columns
        while all(self.terrain_grid[(0, y)] == Terrain.VOID for y in range(self.height)):
            for y in range(self.height):
                del self.terrain_grid[(0, y)]
                del self.floor_grid[(0, y)]
            new_terrain_grid = {}
            new_floor_grid = {}
            for pos, val in self.terrain_grid.items():
                new_terrain_grid[(pos[0] - 1, pos[1])] = val
            for pos, val in self.floor_grid.items():
                new_floor_grid[(pos[0] - 1, pos[1])] = val
            self.terrain_grid = new_terrain_grid
            self.floor_grid = new_floor_grid
            self.width -= 1
        # Right Columns
        while all(self.terrain_grid[(self.width - 1, y)] == Terrain.VOID for y in range(self.height)):
            for y in range(self.height):
                del self.terrain_grid[(self.width - 1, y)]
                del self.floor_grid[(self.width - 1, y)]
            self.width -= 1
        # Top Rows
        while all(self.terrain_grid[(x, 0)] == Terrain.VOID for x in range(self.width)):
            for x in range(self.width):
                del self.terrain_grid[(x, 0)]
                del self.floor_grid[(x, 0)]
            new_terrain_grid = {}
            new_floor_grid = {}
            for pos, val in self.terrain_grid.items():
                new_terrain_grid[(pos[0], pos[1] - 1)] = val
            for pos, val in self.floor_grid.items():
                new_floor_grid[(pos[0], pos[1] - 1)] = val
            self.terrain_grid = new_terrain_grid
            self.floor_grid = new_floor_grid
            self.height -= 1
        # Right Columns
        while all(self.terrain_grid[(x, self.height - 1)] == Terrain.VOID for x in range(self.width)):
            for x in range(self.width):
                del self.terrain_grid[(x, self.height - 1)]
                del self.floor_grid[(x, self.height - 1)]
            self.height -= 1

    def convert_void_to_water(self):
        convert = set()
        for pos, terrain in self.terrain_grid.items():
            if terrain == Terrain.VOID:
                convert.add(pos)
        for pos in convert:
            self.terrain_grid[pos] = Terrain.POOL

    def print_terrain_grid(self):
        if not PRINT:
            return
        print("   ", end='')
        for x in range(self.width):
            print("%1d" % (x % 10), end='')
        print("\n", end='')
        for y in range(self.height):
            print("%02d " % y, end='')
            for x in range(self.width):
                terrain = self.terrain_grid[(x, y)]
                floor_level = self.floor_grid.get((x, y))
                if floor_level == FloorLevel.LOWER:
                    print("_", end='')
                elif floor_level == FloorLevel.UPPER:
                    print("=", end='')
                elif terrain == Terrain.WALL_TOP:
                    print("#", end='')
                elif terrain == Terrain.WALL_BOTTOM:
                    print("|", end='')
                elif terrain == Terrain.VOID:
                    print(" ", end='')
                elif terrain == Terrain.PILLAR:
                    print("%", end='')
                elif terrain == Terrain.STAIRS_UPDOWN:
                    print("v", end='')
                elif terrain == Terrain.STAIRS_LEFT:
                    print("<", end='')
                elif terrain == Terrain.STAIRS_RIGHT:
                    print(">", end='')
                elif terrain == Terrain.POOL:
                    print("~", end='')
                else:
                    print("?", end='')
            print("\n", end='')

    def print_sections(self):
        if not PRINT:
            return
        all_hallways = utils.flatten_list([list(section.hallways.values()) for section in self.sections.values()])
        print("   ", end='')
        for x in range(self.width):
            print("%1d" % (x % 10), end='')
        print("\n", end='')
        for y in range(self.height):
            print("%02d " % y, end='')
            for x in range(self.width):
                section = self._get_section((x, y))
                if (x, y) in all_hallways:
                    print("X", end='')
                elif section and section.room and (x, y) in section.room.get_true_positions():
                    if section.room.floor_level == FloorLevel.UPPER:
                        print("+", end='')
                    else:
                        print("-", end='')
                else:
                    print(" ", end='')
            print("\n", end='')

# python -m app.dungeon_maker.terrain_generation
if __name__ == '__main__':
    generate_terrain(seed=1)
