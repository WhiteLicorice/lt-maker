import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.engine import action  # noqa: F401 -- avoids a circular import
from app.engine import ai_controller
from app.engine.pathfinding import pathfinding
from app.engine.pathfinding.node import Node
from app.engine.pathfinding.path_system import PathSystem
from app.utilities.grid import BoundedGrid

START = (0, 1)
GOAL = (4, 1)

class SecondaryAIBlockedPathTests(unittest.TestCase):
    """
    An AI whose only way to its target was plugged by an enemy found no path and stood still.
    It should walk as far along that way as it can.
    """
    def build_grid(self, walls):
        width, height = 5, 3
        grid = BoundedGrid((width, height), (0, 0, width - 1, height - 1))
        for x in range(width):
            for y in range(height):
                grid.append(Node(x, y, (x, y) not in walls, 1))
        return grid

    def find_position(self, walls, enemy_positions, movement=5, pass_through=False):
        """
        Returns where the AI at START decides to move to in order to reach GOAL
        """
        unit = MagicMock()
        unit.position = START
        unit.team = 'enemy'
        unit.movement_left = movement
        unit.get_movement.return_value = movement
        enemies = [SimpleNamespace(position=pos) for pos in enemy_positions]

        fake_game = SimpleNamespace(units=[unit] + enemies)
        fake_game.board = SimpleNamespace(
            can_move_through=lambda team, pos: pos not in enemy_positions,
            get_unit=lambda pos: None)
        fake_game.path_system = PathSystem(fake_game)

        ai = ai_controller.SecondaryAI.__new__(ai_controller.SecondaryAI)
        ai.unit = unit
        ai.behaviour = SimpleNamespace(action='Move_to', target='Position', view_range=-4)
        ai.view_range = -4
        ai.widen_flag = False
        ai.all_targets = [GOAL]
        ai.grid = self.build_grid(walls)
        ai.pathfinder = pathfinding.AStar(START, None, ai.grid)
        ai.reset()

        with patch.object(ai_controller, 'game', fake_game), \
                patch.object(ai_controller.skill_system, 'pass_through', return_value=pass_through):
            for _ in range(10):
                done, position = ai.run()
                if done:
                    return position
        self.fail("AI never finished thinking")

    # Only the middle row can be walked on
    CORRIDOR = {(x, y) for x in range(5) for y in (0, 2)}

    def test_open_corridor_is_walked_normally(self):
        self.assertEqual(self.find_position(self.CORRIDOR, set(), movement=3), (3, 1))

    def test_blocked_corridor_is_walked_up_to_the_blocker(self):
        self.assertEqual(self.find_position(self.CORRIDOR, {(3, 1)}), (2, 1))

    def test_never_moves_beyond_the_blocker(self):
        self.assertEqual(self.find_position(self.CORRIDOR, {(2, 1)}, movement=10), (1, 1))

    def test_stops_before_the_first_of_several_blockers(self):
        self.assertEqual(self.find_position(self.CORRIDOR, {(2, 1), (3, 1)}), (1, 1))

    def test_stays_put_when_the_blocker_is_adjacent(self):
        self.assertEqual(self.find_position(self.CORRIDOR, {(1, 1)}), START)

    def test_enemy_on_the_goal_is_walked_up_to(self):
        self.assertEqual(self.find_position(self.CORRIDOR, {GOAL}), (3, 1))

    def test_pass_through_walks_through_an_enemy(self):
        self.assertEqual(self.find_position(self.CORRIDOR, {(2, 1)}, pass_through=True), GOAL)

    def test_pass_through_cannot_stop_on_an_enemy(self):
        self.assertEqual(self.find_position(self.CORRIDOR, {(3, 1)}, movement=3, pass_through=True), (2, 1))

    def test_pass_through_walks_up_to_an_enemy_on_the_goal(self):
        self.assertEqual(self.find_position(self.CORRIDOR, {(2, 1), GOAL}, pass_through=True), (3, 1))

    def test_way_around_the_blocker_is_preferred(self):
        # 6 moves around the enemy to the goal, rather than stopping in front of it
        self.assertEqual(self.find_position(set(), {(2, 1)}, movement=6), GOAL)

    def test_terrain_in_the_way_still_means_no_path(self):
        self.assertIsNone(self.find_position(self.CORRIDOR | {(2, 1)}, set()))

class SecondaryAIWholeMapTests(unittest.TestCase):
    """
    A behaviour that looks at the whole map (view range -4) walks toward its target
    however far off it is. Past 99 tiles, or 99 movement points of path, it used to
    find no target and stand still.
    """
    MOVEMENT = 5

    def find_position(self, length, tile_cost=1, view_range=-4):
        """
        Returns where the AI at the left end of a corridor `length` tiles long
        decides to move to in order to reach its right end
        """
        start, goal = (0, 0), (length - 1, 0)
        grid = BoundedGrid((length, 1), (0, 0, length - 1, 0))
        for x in range(length):
            grid.append(Node(x, 0, True, tile_cost))

        unit = MagicMock()
        unit.position = start
        unit.team = 'enemy'
        unit.ai_group = None
        unit.movement_left = self.MOVEMENT
        unit.get_movement.return_value = self.MOVEMENT

        fake_game = SimpleNamespace(units=[unit])
        fake_game.board = SimpleNamespace(
            can_move_through=lambda team, pos: True,
            get_unit=lambda pos: None)
        fake_game.path_system = PathSystem(fake_game)
        fake_game.ai_group_active = lambda ai_group: False

        ai = ai_controller.SecondaryAI.__new__(ai_controller.SecondaryAI)
        ai.unit = unit
        ai.behaviour = SimpleNamespace(action='Move_to', target='Position', view_range=view_range)
        # As SecondaryAI.__init__ does: the whole map is looked at only after two moves' worth is
        ai.view_range = -3 if view_range == -4 else view_range
        ai.widen_flag = False
        ai.single_move = self.MOVEMENT
        ai.double_move = self.MOVEMENT * 2
        ai.all_targets = [goal]
        ai.grid = grid
        ai.pathfinder = pathfinding.AStar(start, None, ai.grid)
        ai.reset()

        with patch.object(ai_controller, 'game', fake_game),                 patch.object(ai_controller.skill_system, 'pass_through', return_value=False):
            for _ in range(10):
                done, position = ai.run()
                if done:
                    return position
        self.fail("AI never finished thinking")

    def test_a_target_within_two_moves_is_walked_toward(self):
        self.assertEqual(self.find_position(length=9), (5, 0))

    def test_a_target_more_than_99_tiles_off_is_walked_toward(self):
        self.assertEqual(self.find_position(length=300), (5, 0))

    def test_a_path_costing_more_than_99_is_walked(self):
        # 39 tiles of 5 movement each
        self.assertEqual(self.find_position(length=40, tile_cost=5), (1, 0))

    def test_a_view_range_of_two_moves_still_ignores_what_is_farther(self):
        self.assertIsNone(self.find_position(length=300, view_range=-3))

    def test_a_view_range_in_tiles_still_ignores_what_is_farther(self):
        self.assertIsNone(self.find_position(length=300, view_range=20))
        self.assertEqual(self.find_position(length=21, view_range=20), (5, 0))


if __name__ == '__main__':
    unittest.main()
