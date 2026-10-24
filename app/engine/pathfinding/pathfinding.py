import heapq
import math
from typing import Callable, Dict, List, Optional, Set, Tuple

from app.engine import bresenham_line_algorithm

from app.engine.pathfinding.node import Node
from app.utilities.grid import BoundedGrid
from app.utilities.typing import Pos

class Djikstra:
    """
    Finds every position reachable from start_pos for at most a given cost.
    It keeps the costs it finds to itself, leaving the grid's nodes as they
    were, so a search needs no reset of the grid first
    """
    __slots__ = ['grid', 'start_pos']

    def __init__(self, start_pos: Pos, grid: BoundedGrid[Node]):
        self.grid: BoundedGrid[Node] = grid
        self.start_pos: Pos = start_pos

    def process(self, can_move_through: Callable[[Pos], bool],
                movement_left: float) -> Set[Pos]:
        left, top, right, bottom = self.grid.bounds
        # The cheapest cost found so far to reach each position
        costs: Dict[Pos, float] = {self.start_pos: 0}
        closed: Set[Pos] = set()
        # A position whose cost goes down is pushed again. Its older, costlier
        # entry comes off the heap after the position is closed, and is skipped
        open_heap: List[Tuple[float, Pos]] = [(0, self.start_pos)]
        while open_heap:
            g, pos = heapq.heappop(open_heap)
            # Entries come off in order of cost, so the first one too far ends it
            if g > movement_left:
                break
            if pos in closed:
                continue
            closed.add(pos)
            x, y = pos
            for adj in ((x, y + 1), (x + 1, y), (x - 1, y), (x, y - 1)):
                if left <= adj[0] <= right and top <= adj[1] <= bottom and adj not in closed:
                    node = self.grid.get(adj)
                    if node.reachable and can_move_through(adj):
                        adj_g = g + node.cost
                        if adj_g < costs.get(adj, math.inf):
                            costs[adj] = adj_g
                            heapq.heappush(open_heap, (adj_g, adj))
        return closed

class AStar:
    def __init__(self, start_pos: Pos, goal_pos: Optional[Pos], grid: BoundedGrid[Node]):
        self.grid = grid
        self.start_pos = start_pos
        self.goal_pos = goal_pos

        self.start_node: Node = self.grid.get(start_pos)
        self.end_node: Node = self.grid.get(goal_pos) if goal_pos else None
        self.adj_end: List[Node] = self._get_adj_nodes(self.end_node) if self.end_node else None

        self.reset()

    def _reset_grid(self):
        for node in self.grid.cells():
            node.reset()

    def reset(self):
        self.open: List[Node] = []
        heapq.heapify(self.open)
        # The nodes waiting in the open queue, so that asking whether one is
        # there does not mean reading through the whole queue
        self.in_open: Set[Node] = set()
        self.closed: Set[Node] = set()
        self._reset_grid()

    def set_goal_pos(self, goal_pos: Pos):
        self.goal_pos = goal_pos
        self.end_node = self.grid.get(goal_pos)
        self.adj_end = self._get_adj_nodes(self.end_node)

    def _get_simple_heuristic(self, node: Node) -> float:
        """
        Compute the heuristic for this node
        h is the approximate distance between this node and the goal node
        """
        dx1 = node.x - self.end_node.x
        dy1 = node.y - self.end_node.y
        h = abs(dx1) + abs(dy1)
        return h

    def _get_heuristic(self, node: Node) -> float:
        """
        Compute the heuristic for this node
        h is the approximate distance between this node and the goal node
        """
        # Get main heuristic
        dx1 = node.x - self.end_node.x
        dy1 = node.y - self.end_node.y
        h = abs(dx1) + abs(dy1)
        # Are we going in direction of goal?
        # Slight nudge in direction that lies along path from start to end
        dx2 = self.start_node.x - self.end_node.x
        dy2 = self.start_node.y - self.end_node.y
        cross = abs(dx1 * dy2 - dx2 * dy1)
        return h + cross * .001

    def _get_adj_nodes(self, node: Node) -> List[Node]:
        return self._get_manhattan_adj_nodes(node)

    def _get_manhattan_adj_nodes(self, node: Node) -> List[Node]:
        nodes: List[Node] = []
        for adj in [(node.x, node.y + 1), (node.x + 1, node.y), 
                    (node.x - 1, node.y), (node.x, node.y - 1)]:
            if self.grid.check_bounds(adj):
                nodes.append(self.grid.get(adj))
        return nodes

    def _update_node(self, adj: Node, node: Node):
        # h is approximate distance between this node and the goal
        # g is true distance between this node and the starting position
        # f is simply them added together
        adj.g = node.g + adj.cost
        adj.h = self._get_heuristic(adj)
        adj.parent = node
        adj.f = adj.h + adj.g
        adj.true_f = self._get_simple_heuristic(adj) + adj.g

    def _return_path(self, node: Node) -> List[Pos]:
        path = []
        while node:
            path.append((node.x, node.y))
            node = node.parent
        return path

    def process(self, can_move_through: Callable[[Pos], bool],
                adj_good_enough: bool = False, limit: float = None,
                max_movement_limit: int = 999) -> List[Pos]:
        """
        Args:
            can_move_through (Callable): Expects a callback function that takes in a position 
                and returns whether an enemy unit is standing in that position, which means we can't move through it.
            adj_good_enough (bool, optional): If set, moving adjacent to the goal position also counts as meeting its goal.
            limit (float, optional): If set, return the best answer once we've evaluated all paths that cost <= this cost limit
            max_movement_limit (int, optional): Defaults to 999. Treat as impassable all nodes with cost > this limit.
        """
        # Add starting node to open queue
        heapq.heappush(self.open, (self.start_node.f, self.start_node))
        self.in_open.add(self.start_node)
        while self.open:
            f, node = heapq.heappop(self.open)
            self.in_open.discard(node)
            # Make sure we don't process the node twice
            self.closed.add(node)
            # If this node is past the limit, just return None
            # Uses f, not g, because g will cut off if first greedy path fails
            # f only cuts off if all nodes are bad
            if limit is not None and node.true_f > limit:
                return []
            # if ending node, display found path
            if node is self.end_node or (adj_good_enough and node in self.adj_end):
                return self._return_path(node)
            # get adjacent nodes for node
            adj_nodes = self._get_adj_nodes(node)
            for adj in adj_nodes:
                if adj.reachable and adj not in self.closed:
                    if can_move_through((adj.x, adj.y)) and adj.cost <= max_movement_limit:
                        if adj in self.in_open:
                            # if adj node in open list, check if current path
                            # is better than the one previously found for this adj node
                            if adj.g > node.g + adj.cost:
                                self._update_node(adj, node)
                                heapq.heappush(self.open, (adj.f, adj))
                        else:
                            self._update_node(adj, node)
                            heapq.heappush(self.open, (adj.f, adj))
                            self.in_open.add(adj)
                    else:  # Is blocked
                        pass
        return []

class ThetaStar(AStar):
    """
    # Just a slight modification to AStar that enables better straight line
    # pathing because we can skip nodes
    """
    def _update_node(self, adj: Node, node: Node):
        # h is approximate distance between this node and the goal
        # g is true distance between this node and the starting position
        # f is simply them added together
        # If line of sight is valid, we can just use the parent
        # of the current node rather than the current node
        if node.parent and self._line_of_sight(node.parent, adj):
            adj.g = node.parent.g + adj.cost
            adj.parent = node.parent
        else:
            adj.g = node.g + adj.cost
            adj.parent = node
        adj.h = self._get_heuristic(adj)
        adj.f = adj.h + adj.g
        adj.true_f = self._get_simple_heuristic(adj) + adj.g

    def _line_of_sight(self, node1: Node, node2: Node) -> bool:
        def cannot_move_through(pos: Tuple[int, int]) -> bool:
            node = self.grid.get(pos)
            return not node.reachable

        pos1 = node1.x, node1.y
        pos2 = node2.x, node2.y
        valid = bresenham_line_algorithm.get_line(pos1, pos2, cannot_move_through)
        return valid
