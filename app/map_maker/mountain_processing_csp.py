"""
CSP-based mountain group solver.

The solver MountainPainter uses for mountain groups of 12+ tiles (smaller
groups still use NaiveBacktrackingProcess). It replaced an exact-cover /
dancing-links solver (AlgorithmXProcess), whose encoding ballooned to thousands
of "invalid-coord" secondary columns and whose cover/uncover cost dominated --
and which failed to terminate on some shapes. Same problem: assign each
mountain tile in a connected group a tile-coord so that (a) its border edges
match the group boundary and (b) every adjacent pair is compatible per
mountain_data.

A direct CSP keeps one small domain per tile (<= number of mountain tiles) and
maintains arc consistency (AC-3) during search, so it barely backtracks and
proves unsatisfiable shapes in milliseconds instead of spinning forever.

NOT wave-function-collapse: variable order is MRV and *value* selection is
weighted-random by partner counts (the same signal NaiveBacktrackingProcess
uses), so the tile-frequency distribution is preserved rather than collapsing
to WFC's chaotic min-entropy output.

Interface (the mountain-process protocol MountainPainter drives):
  __init__(tilemap, mountain_data, noneless_rules, group, gui_processing, waiting_callback)
  process_group(); attrs organization, did_complete, broke_out; stop().
"""
from typing import Callable, Dict, List, Optional, Set, Tuple
from collections import deque
import random

from app.utilities.typing import Pos

_OPPOSITE = {'right': 'left', 'left': 'right', 'up': 'down', 'down': 'up'}

class CSPProcess:
    # Value-selection bias against "index 15" tiles -- tiles that allow a
    # border (None) in all four directions. They connect to almost anything, so
    # partner-count weighting over-picks them and maps look washed out. This
    # scales their selection weight down (they stay in the domain, so they're
    # still chosen when genuinely the only option). 1.0 = no bias; smaller =
    # rarer. Tune to taste.
    index15_weight_scale: float = 0.01

    # Value-selection bias against repeating the tile directly above/below the
    # current cell, so vertical runs of identical tiles are unlikely. Applied
    # multiplicatively like index15_weight_scale; non-removing, so a forced
    # repeat still happens. 1.0 = no bias; smaller = stronger avoidance.
    vertical_repeat_scale: float = 0.1

    def __init__(self, tilemap, mountain_data, noneless_rules,
                 group: Set[Pos], gui_processing: bool = True,
                 waiting_callback: Optional[Callable] = None):
        self.tilemap = tilemap
        self.mountain_data = mountain_data
        self.noneless_rules = noneless_rules
        self.group: Set[Pos] = group
        self.gui_processing = gui_processing
        self.waiting_callback = waiting_callback

        # Sort top-left to bottom-right
        self.to_process = sorted(self.group, key=lambda x: (x[0] + x[1], x[0]))
        self.organization: Dict[Pos, Pos] = {}

        self.did_complete = False
        self.broke_out = False

        # Precomputed compatibility sets per coord (keys only, None already
        # stripped in noneless_rules). RIGHT[c] = coords allowed to the right
        # of c, etc.
        self._right: Dict[Pos, Set[Pos]] = {}
        self._left: Dict[Pos, Set[Pos]] = {}
        self._up: Dict[Pos, Set[Pos]] = {}
        self._down: Dict[Pos, Set[Pos]] = {}
        for coord, rules in self.noneless_rules.items():
            self._right[coord] = set(rules['right'].keys())
            self._left[coord] = set(rules['left'].keys())
            self._up[coord] = set(rules['up'].keys())
            self._down[coord] = set(rules['down'].keys())

        # "Index 15" tiles: None allowed in every direction (detected on the raw
        # rules, since a direction can carry both None and real partners).
        self._index15: Set[Pos] = {
            coord for coord, rules in self.mountain_data.items()
            if None in rules['up'] and None in rules['down']
            and None in rules['left'] and None in rules['right']}

        self.counter = 0
        self.step_limit = int(2e6)

    def stop(self):
        self.broke_out = True

    # ------------------------------------------------------------------ solve
    def process_group(self):
        print("--- Process CSP Group --- %d" % id(self))
        self.did_complete = False
        self.broke_out = False
        self.organization.clear()
        self.counter = 0

        positions = self.to_process
        domains: Dict[Pos, List[Pos]] = {pos: list(self.find_valid_coords(pos)) for pos in positions}
        domains = {pos: set(v) for pos, v in domains.items()}

        # Neighbors that live inside the group, with the direction FROM this
        # tile TO the neighbor. Used for forward checking.
        neighbors: Dict[Pos, List[Tuple[Pos, str]]] = {}
        group = self.group
        for pos in positions:
            x, y = pos
            nb = []
            if (x + 1, y) in group:
                nb.append(((x + 1, y), 'right'))
            if (x - 1, y) in group:
                nb.append(((x - 1, y), 'left'))
            if (x, y + 1) in group:
                nb.append(((x, y + 1), 'down'))
            if (x, y - 1) in group:
                nb.append(((x, y - 1), 'up'))
            neighbors[pos] = nb
        self._neighbors = neighbors

        assignment: Dict[Pos, Pos] = {}
        unassigned: Set[Pos] = set(positions)

        # Make the whole network arc-consistent up front, then maintain it
        # incrementally during search (MAC). Forward-checking alone only looks
        # one hop and thrashes; AC-3 propagates constraints transitively so
        # dead-ends surface far earlier and the search barely backtracks.
        if not self._ac3(list(self._all_arcs(positions)), domains, trail=[]):
            print("CSP: unsatisfiable after initial AC-3", flush=True)
            return

        ok = self._search(unassigned, domains, assignment)
        if self.broke_out:
            return
        if ok:
            self.organization.update(assignment)
            self.did_complete = True
            print("CSP solution found in %d steps" % self.counter, flush=True)
        else:
            print("CSP: no valid solution (%d steps)" % self.counter, flush=True)

    def _allowed(self, val: Pos, direction: str) -> Set[Pos]:
        # Coords allowed for a neighbor lying `direction` of a tile assigned val.
        if direction == 'right':
            return self._right[val]
        if direction == 'left':
            return self._left[val]
        if direction == 'down':
            return self._down[val]
        return self._up[val]

    def _select_var(self, unassigned: Set[Pos], domains) -> Pos:
        # Minimum-remaining-values; deterministic tie-break by position.
        best = None
        best_size = 1 << 30
        for pos in unassigned:
            s = len(domains[pos])
            if s < best_size or (s == best_size and (best is None or pos < best)):
                best_size = s
                best = pos
        return best

    def _order_values(self, pos: Pos, domains, assignment) -> List[Pos]:
        # Order this cell's candidate coords by a weighted-random draw: each
        # coord's weight is 1 + how strongly already-assigned neighbors want it
        # (partner counts), scaled down for index-15 tiles so they stop
        # dominating. Uses Efraimidis-Spirakis keys (key = u ** (1/weight)) for
        # a proper weighted random permutation with float weights; iterating
        # sorted(coords) keeps the RNG draw order deterministic.
        md = self.mountain_data
        x, y = pos
        west = assignment.get((x - 1, y))
        north = assignment.get((x, y - 1))
        east = assignment.get((x + 1, y))
        south = assignment.get((x, y + 1))
        rng = random.Random(self.tilemap.seed + x * 1024 ** 2 + y * 1024)
        scale = self.index15_weight_scale
        vrepeat = self.vertical_repeat_scale
        index15 = self._index15
        keyed: List[Tuple[float, Pos]] = []
        for c in sorted(domains[pos]):
            w = 1.0
            if west is not None:
                w += md[west]['right'].get(c, 0)
            if north is not None:
                w += md[north]['down'].get(c, 0)
            if east is not None:
                w += md[c]['right'].get(east, 0)
            if south is not None:
                w += md[c]['down'].get(south, 0)
            if c in index15:
                w *= scale
            # Disfavor repeating the tile directly above/below so columns don't
            # stack identical tiles. Non-removing: a forced repeat still wins.
            if c == north or c == south:
                w *= vrepeat
            if w < 1e-9:
                w = 1e-9
            keyed.append((rng.random() ** (1.0 / w), c))
        keyed.sort(reverse=True)
        return [c for _, c in keyed]

    def _all_arcs(self, positions):
        for pos in positions:
            for npos, direction in self._neighbors[pos]:
                # arc (npos, pos): revise npos against pos, direction from npos
                yield (npos, pos, _OPPOSITE[direction])

    def _revise(self, xi: Pos, xj: Pos, direction: str, domains, trail) -> bool:
        # Remove from domain[xi] every value with no support in domain[xj].
        # `direction` is from xi toward xj; a value a at xi is supported iff
        # some coord that may sit `direction` of a is still in domain[xj].
        dj = domains[xj]
        di = domains[xi]
        removed = None
        for a in di:
            if not (self._allowed(a, direction) & dj):
                if removed is None:
                    removed = []
                removed.append(a)
        if removed:
            for a in removed:
                di.discard(a)
            trail.append((xi, set(removed)))
            return True
        return False

    def _ac3(self, arcs, domains, trail) -> bool:
        # arcs: iterable of (xi, xj, direction_xi_to_xj). Returns False if a
        # domain wiped out (caller undoes trail).
        queue = deque(arcs)
        neighbors = self._neighbors
        while queue:
            xi, xj, direction = queue.popleft()
            if self._revise(xi, xj, direction, domains, trail):
                if not domains[xi]:
                    return False
                for xk, dir_ik in neighbors[xi]:
                    if xk == xj:
                        continue
                    queue.append((xk, xi, _OPPOSITE[dir_ik]))
        return True

    def _search(self, unassigned: Set[Pos], domains, assignment) -> bool:
        # Depth-first search, one level per tile. The levels are kept on an
        # explicit stack, since a group can have more tiles than Python's
        # recursion limit. Each level is [pos, values left to try at pos,
        # trail of the value assigned to pos (None while unassigned)].
        stack: List[list] = []
        while True:
            if self.broke_out:
                return False
            self.counter += 1
            if self.counter > self.step_limit:
                # Safety valve for a pathological / undetected-unsat instance;
                # also the path by which stop() takes effect.
                self.broke_out = True
                return False
            if not unassigned:
                return True

            pos = self._select_var(unassigned, domains)
            unassigned.discard(pos)
            stack.append([pos, iter(self._order_values(pos, domains, assignment)), None])

            # Assign the next value that keeps the network arc-consistent,
            # backtracking up the stack while a level runs out of values
            while stack:
                level = stack[-1]
                pos, values, trail = level
                if trail is not None:
                    self._unassign(pos, trail, domains, assignment)
                    level[2] = None
                for val in values:
                    trail = self._assign(pos, val, domains, assignment)
                    if trail is not None:
                        level[2] = trail
                        break
                if level[2] is not None:
                    break
                unassigned.add(pos)
                stack.pop()
            if not stack:
                return False

    def _assign(self, pos: Pos, val: Pos, domains, assignment) -> Optional[list]:
        # Returns the trail of domain removals, or None (with nothing changed)
        # if the assignment wipes out a domain
        assignment[pos] = val
        trail = []
        # Collapse pos to {val}, recording the removal, then re-establish
        # arc consistency across the network from pos outward.
        di = domains[pos]
        removed_self = di - {val}
        if removed_self:
            di.difference_update(removed_self)
            trail.append((pos, removed_self))
        arcs = [(npos, pos, _OPPOSITE[d]) for npos, d in self._neighbors[pos]
                if npos not in assignment]
        if self._ac3(arcs, domains, trail):
            return trail
        self._unassign(pos, trail, domains, assignment)
        return None

    def _unassign(self, pos: Pos, trail: list, domains, assignment):
        for p, r in trail:
            domains[p] |= r
        del assignment[pos]

    # ------------------------------------------------------- domain / border
    # Border/domain rules: a tile's edge toward the group boundary must allow a
    # non-mountain (None) neighbor; interior cells exclude fully-generic tiles.
    def find_valid_coords(self, pos) -> list:
        north, east, south, west = self.get_cardinal_terrain(pos)
        north_edge = not north
        south_edge = not south
        east_edge = not east
        west_edge = not west
        valid_coords = \
            [coord for coord, rules in self.mountain_data.items() if
             ((north_edge and None in rules['up']) or (not north_edge and self.noneless_rules[coord]['up'])) and
             ((south_edge and None in rules['down']) or (not south_edge and self.noneless_rules[coord]['down'])) and
             ((east_edge and None in rules['right']) or (not east_edge and self.noneless_rules[coord]['right'])) and
             ((west_edge and None in rules['left']) or (not west_edge and self.noneless_rules[coord]['left']))]
        orig_valid_coords = valid_coords[:]
        if not north_edge and not south_edge and not east_edge and not west_edge:
            valid_coords = \
                [coord for coord in valid_coords if
                 None not in self.mountain_data[coord]['up'] or
                 None not in self.mountain_data[coord]['down'] or
                 None not in self.mountain_data[coord]['left'] or
                 None not in self.mountain_data[coord]['right']]
        if not valid_coords:
            valid_coords = orig_valid_coords
        return valid_coords

    def get_cardinal_terrain(self, pos: Pos) -> Tuple[bool, bool, bool, bool]:
        north = pos[1] == 0 or self.get_terrain((pos[0], pos[1] - 1))
        east = pos[0] + 1 == self.tilemap.width or self.get_terrain((pos[0] + 1, pos[1]))
        south = pos[1] + 1 == self.tilemap.height or self.get_terrain((pos[0], pos[1] + 1))
        west = pos[0] == 0 or self.get_terrain((pos[0] - 1, pos[1]))
        return north, east, south, west

    def get_terrain(self, pos: Pos) -> bool:
        return pos in self.group
