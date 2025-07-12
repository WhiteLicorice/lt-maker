from typing import Dict, List, Set, Tuple

import math

from app.utilities.typing import Pos

from app.map_maker.utilities import random_choice, edge_random, flood_fill
from app.map_maker.terrain import Terrain
from app.utilities.utils import distance
# from app.map_maker.painters import WangCorner8Painter
from app.map_maker.painter_utils import Painter

class CliffPainter(Painter):
    terrain_like = (Terrain.CLIFF,)
    base_coord = (15, 0)
    second_start_px = 96
    organization = {}
    second_limit = {}

    @property
    def check_flood_fill(self) -> str:
        return 'diagonal'

    def set_second_limit(self, limit: Dict[int, int]):
        self.second_limit = limit

    def _find_longest_path(self, group: Set[Pos]) -> List[Pos]:
        # https://stackoverflow.com/questions/21880419/how-to-find-the-longest-simple-path-in-a-graph
        EARLY_STOP = 100000
        path = []
        best_path = []
        used = set()
        counter = 0

        def find_path(pos):
            nonlocal path
            nonlocal best_path
            nonlocal counter
            counter += 1
            used.add(pos)
            adj = {(pos[0] - 1, pos[1] - 1), (pos[0], pos[1] - 1), (pos[0] + 1, pos[1] - 1),
                   (pos[0] - 1, pos[1]), (pos[0] + 1, pos[1]),
                   (pos[0] - 1, pos[1] + 1), (pos[0], pos[1] + 1), (pos[0] + 1, pos[1] + 1)}
            for v in (adj & group):
                if v not in used:
                    path.append(v)
                    if len(path) > len(best_path):
                        best_path = path[:]
                    if counter > EARLY_STOP:
                        return
                    find_path(v)
                    path.pop()
            used.discard(pos)

        for pos in group:
            path.append(pos)
            if len(path) > len(best_path):
                best_path = path[:]
            if counter > EARLY_STOP:
                return best_path
            find_path(pos)
            path.pop()

        return best_path

    def _calc_corners(self, tilemap, pos: Pos, partners: list) -> Tuple[bool, bool, bool, bool]:
        corner_topleft = False
        corner_bottomleft = False
        corner_topright = False
        corner_bottomright = False
        for other_pos in partners:
            # Topleft
            if other_pos[0] == pos[0] - 1 and other_pos[1] == pos[1] - 1:
                corner_topleft = True
            # Topright
            elif other_pos[0] == pos[0] + 1 and other_pos[1] == pos[1] - 1:
                corner_topright = True
            # Bottomleft
            elif other_pos[0] == pos[0] - 1 and other_pos[1] == pos[1] + 1:
                corner_bottomleft = True
            # Bottomright
            elif other_pos[0] == pos[0] + 1 and other_pos[1] == pos[1] + 1:
                corner_bottomright = True
            # Top
            elif other_pos[0] == pos[0] and other_pos[1] == pos[1] - 1:
                # if edge_random(other_pos, pos) < 0.5:
                if edge_random(other_pos, pos) < 0.5:
                    corner_topright = True
                else:
                    corner_topleft = True
            # Bottom
            elif other_pos[0] == pos[0] and other_pos[1] == pos[1] + 1:
                if edge_random(pos, other_pos) < 0.5:
                    corner_bottomright = True
                else:
                    corner_bottomleft = True
            # Left
            elif other_pos[0] == pos[0] - 1 and other_pos[1] == pos[1]:
                if edge_random(other_pos, pos) < 0.5:
                    corner_topleft = True
                else:
                    corner_bottomleft = True
            # Right
            elif other_pos[0] == pos[0] + 1 and other_pos[1] == pos[1]:
                if edge_random(pos, other_pos) < 0.5:
                    corner_topright = True
                else:
                    corner_bottomright = True
        return corner_topright, corner_bottomright, corner_bottomleft, corner_topleft

    def _chain_end_process(self, tilemap, pos: tuple, other_pos: tuple) -> tuple:
        topright, bottomright, bottomleft, topleft = \
            self._calc_corners(tilemap, pos, [other_pos])
        if topright:
            bottomleft = True
        elif bottomright:
            topleft = True
        elif topleft:
            bottomright = True
        elif bottomleft:
            topright = True

        return topright, bottomright, bottomleft, topleft

    def single_process(self, tilemap):
        positions: set = tilemap.get_all_terrain(Terrain.CLIFF)
        self.organization.clear()
        groupings: List[Set[Pos]] = []  # of sets
        counter: int = 0
        while positions and counter < 99999:
            pos = positions.pop()
            near_positions: set = flood_fill(tilemap, pos, diagonal=True)
            groupings.append(near_positions)
            positions -= near_positions
            counter += 1
        if counter >= 99999:
            raise RuntimeError("Unexpected infinite loop in cliff flood_fill")

        while groupings:
            group = groupings.pop()
            if not (group & tilemap.terrain_grid_to_update):
                # Don't need to bother updating this one if no intersections
                continue
            longest_path: list = self._find_longest_path(group)

            # Handle the case where the longest path does not include some members of the group
            present = set(longest_path)
            new_group = group - present  # The leftovers become a new group
            if new_group:
                groupings.append(new_group)

            # now that we have longest path, we can fill in according to rules
            for idx, pos in list(enumerate(longest_path))[1:-1]:  # Skip first
                prev_pos = longest_path[idx - 1]              
                next_pos = longest_path[idx + 1]
                topright, bottomright, bottomleft, topleft = \
                    self._calc_corners(tilemap, pos, [prev_pos, next_pos])
                
                self.organization[pos] = (topright, bottomright, bottomleft, topleft)
            # For first and last path
            if len(longest_path) > 1:
                self.organization[longest_path[0]] = self._chain_end_process(tilemap, longest_path[0], longest_path[1])
                self.organization[longest_path[-1]] = self._chain_end_process(tilemap, longest_path[-1], longest_path[-2])
            else:
                self.organization[longest_path[0]] = (True, True, True, True)  # Facing down

    def _determine_index(self, tilemap, pos: Pos) -> Pos:
        corner_topright, corner_bottomright, corner_bottomleft, corner_topleft = self.organization[pos]
        index = 1 * corner_topright + \
            2 * corner_bottomright + \
            4 * corner_bottomleft + \
            8 * corner_topleft
        return index

    def _determine_cliff_vector(self, tilemap, pos: Pos) -> Tuple[bool, bool, bool]:
        """
        Determines chirality of the cliff position
        """
        closest_cliff_marker = list(sorted(tilemap.cliff_markers, key=lambda x: distance(pos, x)))[0]
        x_diff = closest_cliff_marker[0] - (pos[0] + .5)
        y_diff = closest_cliff_marker[1] - (pos[1] + .5)
        angle = math.atan2(y_diff, x_diff)
        if angle < 0:
            angle += 2 * math.pi
        bottom = angle >= math.pi  # vector points up
        right = 0.5 * math.pi <= angle <= 1.5 * math.pi  # vector points left
        # Tells you whether the angle is more horizontal or vertical
        x_stronger = angle < 0.25 * math.pi or angle > 1.75 * math.pi or 0.75 * math.pi < angle < 1.25 * math.pi
        # print("vert", pos, angle, right, bottom, x_stronger)
        return right, bottom, x_stronger

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        index: Pos = self._determine_index(tilemap, pos)
        right, bottom, x_stronger = self._determine_cliff_vector(tilemap, pos)

        use_bottomright = True
        if index in (3, 12):
            use_bottomright = right
        elif index in (5, 7, 13):
            if x_stronger:
                use_bottomright = right
            else:
                use_bottomright = bottom
        elif index in (6, 9):
            use_bottomright = bottom
        elif index in (10, 11, 14):
            if x_stronger:
                use_bottomright = not right
            else:
                use_bottomright = bottom
        if use_bottomright:
            new_coords = [(index, k) for k in range(self.limit[index])]
        else:
            new_coords = [(index, k + self.second_start_px//16) for k in range(self.second_limit[index])]

        coord = random_choice(new_coords, pos)
        return coord
