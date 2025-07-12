from __future__ import annotations

import random

from typing import Any, List, Set, Tuple, TYPE_CHECKING

from app.utilities.typing import Pos

if TYPE_CHECKING:
    from app.map_maker.terrain import Terrain

RANDOM_SEED = 0

def get_random_seed() -> int:
    return RANDOM_SEED

def set_random_seed(val: int):
    global RANDOM_SEED
    RANDOM_SEED = val

def random_choice(choices: List[Any], pos: Pos, seed: int = None, offset: int = 0) -> Any:
    if seed is None:
        seed = RANDOM_SEED
    random.seed(seed + pos[0] * 1024**2 + pos[1] * 1024 + offset)
    return random.choice(choices)

def random_random(pos: Pos, seed: int = None, offset: int = 0) -> float:
    if seed is None:
        seed = RANDOM_SEED
    random.seed(seed + pos[0] * 1024**2 + pos[1] * 1024 + offset)
    return random.random()

def edge_random(pos1: Pos, pos2: Pos, seed: int = None) -> float:
    """
    Uses two positions (essentially the edge between these two positions)
    to seed the RNG
    north, then south; west, then east
    """
    if seed is None:
        seed = RANDOM_SEED
    random.seed(seed + pos1[0] * 1024**3 + pos1[1] * 1024**2 + pos2[0] * 1024 + pos2[1])
    return random.random()

def flood_fill(tilemap, pos: Pos, 
               diagonal: bool = False, match: Set[Terrain] = None,
               match_only_these_positions: Set[Pos] = None) -> Set[Pos]:
    """
    # tilemap - the Dungeon tilemap to work on
    # pos - Which position to start the flood fill on 
    # diagonal (optional) - Whether to flood fill diagonally in addition to cardinally
    # match - Set of terrain that counts as a match
    # match_only_these_positions - Set of positions that count as being valid to flood fill onto
    """
    blob_positions = set()
    unexplored_stack = []
    # Get coords like current coord in current_layer
    if not match:
        current_tile = tilemap.get_terrain(pos)
        match = {current_tile}

    def find_similar(starting_pos: Pos, match: set):
        unexplored_stack.append(starting_pos)

        counter = 0
        while unexplored_stack and counter < 99999:
            current_pos = unexplored_stack.pop()

            if current_pos in blob_positions:
                continue
            if not tilemap.check_bounds(current_pos):
                continue
            if match_only_these_positions:  # Just check if it's in the set
                if current_pos not in match_only_these_positions:
                    continue
            else:
                nid = tilemap.get_terrain(current_pos)
                if nid not in match:
                    continue

            blob_positions.add(current_pos)
            unexplored_stack.append((current_pos[0] + 1, current_pos[1]))
            unexplored_stack.append((current_pos[0] - 1, current_pos[1]))
            unexplored_stack.append((current_pos[0], current_pos[1] + 1))
            unexplored_stack.append((current_pos[0], current_pos[1] - 1))
            if diagonal:
                unexplored_stack.append((current_pos[0] - 1, current_pos[1] - 1))
                unexplored_stack.append((current_pos[0] - 1, current_pos[1] + 1))
                unexplored_stack.append((current_pos[0] + 1, current_pos[1] - 1))
                unexplored_stack.append((current_pos[0] + 1, current_pos[1] + 1))
            counter += 1
        if counter >= 99999:
            raise RuntimeError("Unexpected infinite loop in generic flood_fill")

    # Determine which coords should be flood-filled
    find_similar(pos, match)
    return blob_positions

def find_bounds(tilemap, group: Set[Pos]) -> Tuple[int, int, int, int, int, int, int, int]:
    left_most = min(p[0] for p in group)
    right_most = max(p[0] for p in group)
    top_most = min(p[1] for p in group)
    bottom_most = max(p[1] for p in group)
    # Extend to out of bounds when we are on a tilemap edge
    if left_most == 0 and right_most == tilemap.width - 1:
        left_most = -tilemap.width
        right_most = tilemap.width*2 - 1
    elif left_most == 0:
        left_most = -right_most
    elif right_most == tilemap.width - 1:
        right_most = left_most + 2*(tilemap.width - left_most)
    if top_most == 0 and bottom_most == tilemap.height - 1:
        top_most = -tilemap.height
        bottom_most = tilemap.height*2 - 1
    elif top_most == 0:
        top_most = -bottom_most
    elif bottom_most == tilemap.height - 1:
        bottom_most = top_most + 2*(tilemap.height - top_most)
    right_most += 1
    bottom_most += 1
    blob_width = (right_most - left_most)
    blob_height = (bottom_most - top_most)
    center_x = (right_most - left_most)/2 + left_most
    center_y = (bottom_most - top_most)/2 + top_most
    return left_most, right_most, top_most, bottom_most, blob_width, blob_height, center_x, center_y

def find_bounding_rect(coords: set) -> tuple:
    left_most = min(p[0] for p in coords)
    right_most = max(p[0] for p in coords)
    top_most = min(p[1] for p in coords)
    bottom_most = max(p[1] for p in coords)
    right_most += 1
    bottom_most += 1
    blob_width = (right_most - left_most)
    blob_height = (bottom_most - top_most)
    return left_most, top_most, blob_width, blob_height
