from typing import Dict, List, Optional, Set, Callable
import functools

try:
    import cPickle as pickle
except ImportError:
    import pickle

from PyQt5.QtCore import QThread

from app.utilities.typing import Pos

from app.map_maker.utilities import random_choice, flood_fill
from app.map_maker.terrain import Terrain
from app.map_maker.painter_utils import Painter
from app.map_maker.mountain_processing_threads \
    import NaiveBacktrackingThread, AlgorithmXThread

class MountainPainter(Painter):
    terrain_like = (Terrain.MOUNTAIN, )
    base_coord = (8, 13)
    organization = {}
    current_threads = []  # Keeps track of the currently running threads
    mountain_process_finished: Callable = None
    mountain_processing: Callable = None

    def __init__(self, base_coord: Optional[Pos] = None):
        super().__init__(base_coord)
        self._initial_process()

    @property
    def check_flood_fill(self):
        return True

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        coord = self.organization[pos]
        if coord == (12, 6):
            coord = random_choice([(12, 6), (11, 6)], pos)
        elif coord == (13, 3):
            coord = random_choice([(13, 3), (12, 4), (12, 5)], pos)
        return coord

    def _initial_process(self):
        self.quit_all_threads()
        data_loc = 'app/map_maker/mountain_data_generation/mountain_data.p'
        with open(data_loc, 'rb') as fp:
            self.mountain_data = pickle.load(fp)
        self.border_dict: Dict[Pos, int] = {}  # Coord: Index (0-15)
        self.index_dict: Dict[int, Set[Pos]] = {i: set() for i in range(16)}  # Index: Coord 
        self.noneless_rules = {}

        for coord, rules in self.mountain_data.items():
            north_edge = None in rules['up']
            south_edge = None in rules['down']
            east_edge = None in rules['right']
            west_edge = None in rules['left']
            index = 1 * north_edge + 2 * east_edge + 4 * south_edge + 8 * west_edge
            self.border_dict[coord] = index
            self.index_dict[index].add(coord)
            # Keep track of the rules when None is not present as well
            noneless_rules = {}
            noneless_rules['up'] = {k: v for k, v in rules['up'].items() if k is not None}
            noneless_rules['down'] = {k: v for k, v in rules['down'].items() if k is not None}
            noneless_rules['left'] = {k: v for k, v in rules['left'].items() if k is not None}
            noneless_rules['right'] = {k: v for k, v in rules['right'].items() if k is not None}
            self.noneless_rules[coord] = noneless_rules

        for index, coord in self.index_dict.items():
            print(index, sorted(coord))

    def single_process(self, tilemap):
        positions: Set[Pos] = tilemap.get_all_terrain(Terrain.MOUNTAIN)
        self.organization.clear()
        groupings: List[Set[Pos]] = []  # of sets
        counter: int = 0
        limit: int = int(1e6)
        while positions and counter < limit:
            pos = positions.pop()
            near_positions: Set[Pos] = flood_fill(tilemap, pos)
            groupings.append(near_positions)
            for near_pos in near_positions:
                positions.discard(near_pos)
            counter += 1
        if counter >= limit:
            raise RuntimeError("Unexpected infinite loop in mountain flood_fill")

        while groupings:
            group = groupings.pop()
            if not (group & tilemap.terrain_grid_to_update):
                # Don't need to bother updating this one if no intersections
                continue

            # Quit out of threads that are already operating on this group
            for thread in self.current_threads[:]:
                if thread.group & group:
                    self._quit_thread(thread)
            # Now we can process this group
            self._process_group(tilemap, group)

    def _process_group(self, tilemap, group: Set[Pos]):
        # Just fill it up with generic pieces
        self._generic_fill(group)

        # But then, start the thread
        if len(group) < 12:
            thread = NaiveBacktrackingThread(tilemap, self.mountain_data, self.noneless_rules, group)
        else:
            thread = AlgorithmXThread(tilemap, self.mountain_data, self.noneless_rules, group)
        thread.finished.connect(functools.partial(self.mountain_process_finished, thread, tilemap))
        thread.waiting.connect(functools.partial(self.mountain_processing, thread, tilemap))
        self.current_threads.append(thread)
        thread.start(QThread.LowPriority)

    def _generic_fill(self, group: Set[Pos]):
        for pos in group:
            valid_coords = self.index_dict[15]
            valid_coord = random_choice(list(valid_coords), pos)
            self.organization[pos] = valid_coord

    def _quit_thread(self, thread: QThread):
        thread.stop()
        thread.wait()
        if thread in self.current_threads:
            self.current_threads.remove(thread)

    def quit_all_threads(self):
        for thread in self.current_threads:
            thread.stop()
            thread.wait()
        self.current_threads.clear()
