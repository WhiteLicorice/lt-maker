from __future__ import annotations
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from app.dungeon_maker.terrain_generation import DungeonTileMap

from app.utilities.typing import Pos
from app.utilities.direction import Direction
from app.dungeon_maker.floor_level import FloorLevel

class DungeonSection:
    def __init__(self, size: Pos, offset: Pos, tilemap: DungeonTileMap):
        self.width, self.height = size
        self.offset = offset
        self.tilemap = tilemap
        self.room: Optional[DungeonRoom] = None
        self.hallways: Dict[Direction, List[Pos]] = {}  # True positions

    def get_true_positions(self) -> List[Pos]:
        positions = []
        for x in range(self.width):
            for y in range(self.height):
                positions.append((self.offset[0] + x, self.offset[1] + y))
        return positions

    def has_full_room(self) -> bool:
        return self.room and (self.room.width > 2 or self.room.height > 2)

    def has_big_room(self) -> bool:
        return self.room and self.room.width >= 3 and self.room.height >= 3

    def generate_room(self):
        width = self.tilemap.random.randint(self.tilemap.theme["room_size_min_x"], self.width - 1)
        height = self.tilemap.random.randint(self.tilemap.theme["room_size_min_y"], self.height - 1)
        offset_x = self.tilemap.random.randint(0, self.width - width - 1)
        offset_y = self.tilemap.random.randint(0, self.height - height - 1)
        floor_level = FloorLevel.LOWER if self.tilemap.random.random() < self.tilemap.theme["floor_lower_chance"] else FloorLevel.UPPER

        self.room = DungeonRoom((width, height), (offset_x, offset_y), self, self.tilemap, floor_level)

    def generate_hallway_node(self):
        size = 2 if self.tilemap.random.random() < self.tilemap.theme["wide_hallway_chance"] else 1
        offset_x = self.tilemap.random.randint(0, self.width - size - 1)
        offset_y = self.tilemap.random.randint(0, self.height - size - 1)
        floor_level = FloorLevel.LOWER if self.tilemap.random.random() < self.tilemap.theme["floor_lower_chance"] else FloorLevel.UPPER

        self.room = DungeonRoom((size, size), (offset_x, offset_y), self, self.tilemap, floor_level)

    def get_east_start(self) -> Tuple[int, int]:
        random_point = self.tilemap.random.randrange(self.room.height)
        start = random_point + self.offset[1] + self.room.offset[1]
        return random_point, start

    def get_west_start(self) -> Tuple[int, int]:
        random_point = self.tilemap.random.randrange(self.room.height)
        start = random_point + self.offset[1]
        return random_point, start

    def get_south_start(self) -> Tuple[int, int]:
        random_point = self.tilemap.random.randrange(self.room.width)
        start = random_point + self.offset[0] + self.room.offset[0]
        return random_point, start

    def get_north_start(self) -> Tuple[int, int]:
        random_point = self.tilemap.random.randrange(self.room.width)
        start = random_point + self.offset[0]
        return random_point, start

    def connect_global(self, direction: Direction):
        """
        Connects to the global background room if there is no room normally in this direction
        """
        # Chance to skip connecting
        if self.tilemap.random.random() > self.tilemap.theme["connection_chance"]:
            return
        hallway_width = 2 if self.tilemap.random.random() < self.tilemap.theme["wide_hallway_chance"] else 1
        hallway = []

        if direction == Direction.EAST:
            # Find where to start on the right wall of me and the left wall of them
            start_room_panel, start_on_wall = self.get_east_start()
            # Find x starting point
            start: int = self.offset[0] + self.room.offset[0] + self.room.width

            # Determine which side the wide hallways should spawn on
            if start_room_panel == self.room.height - 1:
                hallway_side = -1
            elif start_room_panel == 0:
                hallway_side = 1
            else:
                hallway_side = self.tilemap.random.choice([-1, 1])

            x = start
            hallway.append((x, start_on_wall))
            # Make the hallway wider if possible
            if hallway_width == 2 and self.room.height > 1:
                hallway.append((x, start_on_wall + hallway_side))

        elif direction == Direction.WEST:
            # Find where to start on the right wall of me and the left wall of them
            start_room_panel, start_on_wall = self.get_west_start()
            # Find x starting point
            start: int = self.offset[0] + self.room.offset[0]

            # Determine which side the wide hallways should spawn on
            if start_room_panel == self.room.height - 1:
                hallway_side = -1
            elif start_room_panel == 0:
                hallway_side = 1
            else:
                hallway_side = self.tilemap.random.choice([-1, 1])

            x = start - 1
            hallway.append((x, start_on_wall))
            # Make the hallway wider if possible
            if hallway_width == 2 and self.room.height > 1:
                hallway.append((x, start_on_wall + hallway_side))

        elif direction == Direction.SOUTH:
            # Find where to start on the bottom wall of me and the top wall of them
            start_room_panel, start_on_wall = self.get_south_start()
            # Find y starting point
            start: int = self.offset[1] + self.room.offset[1] + self.room.height

            # Determine which side the wide hallways should spawn on
            if start_room_panel == self.room.width - 1:
                hallway_side = -1
            elif start_room_panel == 0:
                hallway_side = 1
            else:
                hallway_side = self.tilemap.random.choice([-1, 1])

            y = start
            hallway.append((start_on_wall, y))
            # Make the hallway wider if possible
            if hallway_width == 2 and self.room.width > 1:
                hallway.append((start_on_wall + hallway_side, y))

        elif direction == Direction.NORTH:
            # Find where to start on the bottom wall of me and the top wall of them
            start_room_panel, start_on_wall = self.get_north_start()
            # Find y starting point
            start: int = self.offset[1] + self.room.offset[1]

            # Determine which side the wide hallways should spawn on
            if start_room_panel == self.room.width - 1:
                hallway_side = -1
            elif start_room_panel == 0:
                hallway_side = 1
            else:
                hallway_side = self.tilemap.random.choice([-1, 1])

            y = start - 1
            hallway.append((start_on_wall, y))
            # Make the hallway wider if possible
            if hallway_width == 2 and self.room.width > 1:
                hallway.append((start_on_wall + hallway_side, y))

        self.hallways[direction] = hallway

    def connect(self, other: DungeonSection, direction: Direction):
        # Chance to skip connecting the two rooms
        if self.tilemap.random.random() > self.tilemap.theme["connection_chance"]:
            return
        hallway_width = 2 if self.tilemap.random.random() < self.tilemap.theme["wide_hallway_chance"] else 1
        hallway = []

        if direction == Direction.EAST:
            # Find where to start on the right wall of me and the left wall of them
            start_room_panel, start_on_wall = self.get_east_start()
            other_start_room_panel, other_start_on_wall = other.get_east_start()
            # Find x starting point
            start: int = self.offset[0] + self.room.offset[0] + self.room.width
            end: int = other.offset[0] + other.room.offset[0]
            midpoint: int = other.offset[0]

            # Determine which side the wide hallways should spawn on
            if start_room_panel == self.room.height - 1:
                begin_side = -1
            elif start_room_panel == 0:
                begin_side = 1
            else:
                begin_side = self.tilemap.random.choice([-1, 1])

            middle_side = self.tilemap.random.choice([-1, 1])

            if other_start_room_panel == other.room.height - 1:
                end_side = -1
            elif other_start_room_panel == 0:
                end_side = 1
            else:
                end_side = self.tilemap.random.choice([-1, 1])

            for x in range(start, midpoint):
                hallway.append((x, start_on_wall))
                # Make the hallway wider if possible
                if hallway_width == 2 and self.room.height > 1:
                    hallway.append((x, start_on_wall + begin_side))
            if start_on_wall < other_start_on_wall:
                for y in range(start_on_wall, other_start_on_wall + 1):
                    hallway.append((midpoint, y))
                    if hallway_width == 2:
                        hallway.append((midpoint + middle_side, y))
            else:
                for y in range(other_start_on_wall, start_on_wall + 1):
                    hallway.append((midpoint, y))
                    if hallway_width == 2:
                        hallway.append((midpoint + middle_side, y))
            for x in range(midpoint, end):
                hallway.append((x, other_start_on_wall))
                # Make the hallway wider if possible
                if hallway_width == 2 and other.room.height > 1:
                    hallway.append((x, other_start_on_wall + end_side))

        elif direction == Direction.SOUTH:
            # Find where to start on the bottom wall of me and the top wall of them
            start_room_panel, start_on_wall = self.get_south_start()
            other_start_room_panel, other_start_on_wall = other.get_south_start()
            # Find x starting point
            start: int = self.offset[1] + self.room.offset[1] + self.room.height
            end: int = other.offset[1] + other.room.offset[1]
            midpoint: int = other.offset[1]

            # Determine which side the wide hallways should spawn on
            if start_room_panel == self.room.width - 1:
                begin_side = -1
            elif start_room_panel == 0:
                begin_side = 1
            else:
                begin_side = self.tilemap.random.choice([-1, 1])

            middle_side = self.tilemap.random.choice([-1, 1])

            if other_start_room_panel == other.room.width - 1:
                end_side = -1
            elif other_start_room_panel == 0:
                end_side = 1
            else:
                end_side = self.tilemap.random.choice([-1, 1])

            for y in range(start, midpoint):
                hallway.append((start_on_wall, y))
                # make the hallway wider if possible
                if hallway_width == 2 and self.room.width > 1:
                    hallway.append((start_on_wall + begin_side, y))
            if start_on_wall < other_start_on_wall:
                for x in range(start_on_wall, other_start_on_wall + 1):
                    hallway.append((x, midpoint))
                    if hallway_width == 2:
                        hallway.append((x, midpoint + middle_side))
            else:
                for x in range(other_start_on_wall, start_on_wall + 1):
                    hallway.append((x, midpoint))
                    if hallway_width == 2:
                        hallway.append((x, midpoint + middle_side))
            for y in range(midpoint, end):
                hallway.append((other_start_on_wall, y))
                # make the hallway wider if possible
                if hallway_width == 2 and other.room.width > 1:
                    hallway.append((other_start_on_wall + end_side, y))

        self.hallways[direction] = hallway
                
class DungeonRoom:
    def __init__(self, size: Pos, offset: Pos, section: DungeonSection, 
                 tilemap: DungeonTileMap, floor_level: FloorLevel):
        self.width, self.height = size
        self.offset = offset
        self.section = section
        self.tilemap = tilemap
        self.floor_level = floor_level
        self.positions: List[Pos] = \
            [(x + self.offset[0], y + self.offset[1]) for x in range(self.width) for y in range(self.height)]

    def get_rect(self) -> Tuple[int, int, int, int]:
        """
        Returns the left, top, width, and height of the room
        """
        x, y = self.get_true_offset()
        return (x + 1, y + 1, self.width - 1, self.height - 1)

    def get_true_offset(self) -> Pos:
        """
        Returns the true top left position of the room
        """
        ox, oy = self.section.offset
        x, y = self.offset
        return (ox + x, oy + y)

    def get_true_positions(self) -> List[Pos]:
        ox, oy = self.section.offset
        return [(x + ox, y + oy) for (x, y) in self.positions]

    def get_true_inner_positions(self) -> List[Pos]:
        ox, oy = self.section.offset
        pos = [(x + ox, y + oy) for (x, y) in self.positions 
               if x > self.offset[0] 
               and y > self.offset[1]
               and x - self.offset[0] < self.width - 1
               and y - self.offset[1] < self.height - 1]
        return pos
