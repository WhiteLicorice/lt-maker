import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
from app.engine.game_board import GameBoard
from app.engine.target_system import TargetSystem
from app.engine.objects.unit import UnitObject
from app.engine.pathfinding.path_system import PathSystem
from app.engine.pathfinding.node import Node

from app.utilities.grid import Grid

from app.tests.mocks.mock_game import get_mock_game

class PathSystemTests(unittest.TestCase):
    """
    Tests the path_system functions which help with running pathfinding
    """

    def setUp(self):
        from app.data.database.database import DB
        DB.load('testing_proj.ltproj', CURRENT_SERIALIZATION_VERSION)
        self.game = get_mock_game()
        self.game.target_system = TargetSystem(game=self.game)
        self.path_system = PathSystem(game=self.game)

        tilemap = MagicMock(name='tilemap')
        tilemap.width = 29
        tilemap.height = 29
        self.game.board = GameBoard(tilemap)
        self.game.board.bounds = (0, 0, 28, 28)
        self.game.units = []

        self.player_unit = UnitObject('player')
        self.player_unit.klass = 'Citizen'
        self.player_unit.team = 'player'
        self.player_unit.finished = False
        self.player_unit.position = (1, 1)
        self.player_unit.movement_left = 5

        # Set up a simple grid for use in travel algorithm tests
        width, height = 9, 9
        self.simple_grid = Grid((width, height))
        for x in range(width):
            for y in range(height):
                self.simple_grid.append(Node(x, y, True, 1))

    def test_valid_moves(self):
        with patch('app.engine.equations.parser.movement') as movement_mock, \
             patch('app.engine.objects.unit.UnitObject.movement_left', new_callable=PropertyMock) as movement_left_mock:
            movement_instance = movement_mock.return_value
            movement_instance.method.return_value = 5
            movement_left_mock.return_value = 5

            valid_moves = self.path_system.get_valid_moves(self.player_unit)
            self.assertGreater(len(valid_moves), 0, 'get_valid_moves did not return a valid move')
            self.assertIn((1, 1), valid_moves, 'current position is not valid_moves')

    def test_get_path(self):
        goal = (28, 14)

        # Yes, path is reversed throughout the whole engine
        # path[0] is the end of the unit's path
        # path[-1] is their starting point

        with patch('app.engine.equations.parser.movement') as movement_mock, \
             patch('app.engine.objects.unit.UnitObject.movement_left', new_callable=PropertyMock) as movement_left_mock:
            movement_instance = movement_mock.return_value
            movement_instance.method.return_value = 5
            movement_left_mock.return_value = 5

            # Test AStar
            path = self.path_system.get_path(self.player_unit, goal)
            self.assertGreater(len(path), 0, 'path is empty')
            self.assertEqual(path[0], goal, 'Did not find the end')
            self.assertEqual(path[-1], (1, 1), 'Did not start at the beginning')

            # Test Limit
            path = self.path_system.get_path(self.player_unit, goal, use_limit=self.player_unit.movement_left)
            self.assertEqual(len(path), 0, 'path is not empty')

            # Test ThetaStar
            path = self.path_system.get_path(self.player_unit, goal, free_movement=True)
            self.assertEqual(len(path), 2, 'path is not a perfect diagonal')
            self.assertEqual(path[0], goal, 'Did not find the end')
            self.assertEqual(path[-1], (1, 1), 'Did not start at the beginning')

    def test_check_path(self):
        with patch('app.engine.equations.parser.movement') as movement_mock, \
             patch('app.engine.movement.movement_funcs.get_mcost') as mcost_mock, \
             patch('app.engine.objects.unit.UnitObject.movement_left', new_callable=PropertyMock) as movement_left_mock:
            movement_instance = movement_mock.return_value
            movement_instance.method.return_value = 5
            mcost_mock.return_value = 1
            movement_left_mock.return_value = 5

            good_path = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (2, 3)]
            good_path_valid = self.path_system.check_path(self.player_unit, good_path)
            self.assertEqual(good_path_valid, True)

            # Bad adjacencies
            bad_path = [(0, 0), (1, 1), (2, 1), (2, 2)]
            bad_path_valid = self.path_system.check_path(self.player_unit, bad_path)
            self.assertEqual(bad_path_valid, False, 'Did not catch that not every position in path is adjacent')

            # Too long
            bad_path = [(0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (3, 2), (3, 3), (3, 4)]
            bad_path_valid = self.path_system.check_path(self.player_unit, bad_path)
            self.assertEqual(bad_path_valid, False, 'A too long path was not caught')

    def test_get_path_cost(self):
        with patch('app.engine.movement.movement_funcs.get_mcost') as mcost_mock, \
             patch('app.engine.objects.unit.UnitObject.movement_left', new_callable=PropertyMock) as movement_left_mock:
            mcost_mock.return_value = 1
            movement_left_mock.return_value = 5

            # path is goal-first, start-last; the starting position (path[-1])
            # is not counted, so cost == number of tiles moved onto
            path = [(2, 3), (2, 2), (2, 1), (1, 1)]
            cost = self.path_system.get_path_cost(self.player_unit, path)
            self.assertEqual(cost, 3, 'Path cost should exclude the starting position')

            # An over-budget winding path costs more than the unit's movement
            winding_path = [(3, 1), (3, 2), (3, 3), (2, 3), (1, 3), (1, 2), (1, 1)]
            cost = self.path_system.get_path_cost(self.player_unit, winding_path)
            self.assertGreater(cost, self.player_unit.movement_left,
                               'Winding path should overspend normal movement')

    def test_travel_algorithm(self):
        path = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (2, 3)]
        final_pos = self.path_system.travel_algorithm(path, 3, self.player_unit, self.simple_grid)
        self.assertEqual(final_pos, (1, 1), 'Did not find correct final position')

        orig_position = self.player_unit.position
        final_pos = self.path_system.travel_algorithm([], 3, self.player_unit, self.simple_grid)
        self.assertEqual(final_pos, orig_position, 'Unit should always end up at original position')


class MoveSelectionTests(unittest.TestCase):
    """
    MoveSelection is the single source of truth behind both the move highlights and the
    cursor's movement borders, so its set algebra has to match what MoveState acts on
    """

    def setUp(self):
        from app.engine.movement.move_selection import MoveSelection
        self.MoveSelection = MoveSelection

    def test_normal_is_everything_reachable_without_xcom(self):
        sel = self.MoveSelection(walkable={(1, 1), (1, 2)}, warp={(9, 9)}, xcom={(1, 3)})
        self.assertEqual({(1, 1), (1, 2), (9, 9)}, sel.normal)

    def test_contains_spans_all_three_sets(self):
        sel = self.MoveSelection(walkable={(1, 1)}, warp={(9, 9)}, xcom={(1, 3)})
        self.assertIn((1, 1), sel)
        self.assertIn((9, 9), sel)
        self.assertIn((1, 3), sel)
        self.assertNotIn((5, 5), sel)

    def test_an_empty_selection_is_falsy(self):
        self.assertFalse(self.MoveSelection())
        self.assertTrue(self.MoveSelection(walkable={(1, 1)}))
        self.assertTrue(self.MoveSelection(xcom={(1, 1)}))

    def test_a_warp_tile_the_unit_could_walk_to_is_walked_to(self):
        # The player was shown a path arrow to it, so committing a Warp there would
        # contradict the preview
        sel = self.MoveSelection(walkable={(1, 1), (1, 2)}, warp={(1, 2), (9, 9)})
        self.assertTrue(sel.is_warp((9, 9)))
        self.assertFalse(sel.is_warp((1, 2)))
        self.assertFalse(sel.is_warp((1, 1)))


class GetMoveSelectionTests(unittest.TestCase):
    """
    get_move_selection replaces the move rules that used to be spread over
    highlight.display_highlights (the xcom subtraction and the zero_move clamp),
    MoveState.begin (the has_traded rule) and boundary._add_unit (the clamp again)
    """

    def setUp(self):
        from app.data.database.database import DB
        DB.load('testing_proj.ltproj', CURRENT_SERIALIZATION_VERSION)
        self.game = get_mock_game()
        self.game.target_system = TargetSystem(game=self.game)
        self.game.ai_group_active = lambda ai_group: False
        self.path_system = PathSystem(game=self.game)

        tilemap = MagicMock(name='tilemap')
        tilemap.width = 29
        tilemap.height = 29
        self.game.board = GameBoard(tilemap)
        self.game.board.bounds = (0, 0, 28, 28)
        self.game.units = []

        self.unit = UnitObject('player')
        self.unit.klass = 'Citizen'
        self.unit.team = 'player'
        self.unit.finished = False
        self.unit.position = (10, 10)
        self.unit.movement_left = 3

    def get_selection(self, xcom=0, warp=(), **kwargs):
        """Pins the unit's movement budget, optionally granting xcom movement and warps"""
        with patch('app.engine.equations.parser.movement', return_value=3), \
                patch('app.engine.objects.unit.UnitObject.movement_left',
                      new_callable=PropertyMock, return_value=3), \
                patch('app.engine.objects.unit.UnitObject.get_xcom_movement',
                      return_value=xcom), \
                patch('app.engine.skill_system.witch_warp', return_value=list(warp)):
            return self.path_system.get_move_selection(self.unit, **kwargs)

    def test_walkable_holds_the_units_own_tile(self):
        sel = self.get_selection()
        self.assertIn((10, 10), sel.walkable)
        self.assertIn((10, 10), sel)

    def test_xcom_is_disjoint_from_normal(self):
        sel = self.get_selection(xcom=3)
        self.assertTrue(sel.xcom, 'xcom movement produced no extra tiles to test with')
        self.assertFalse(sel.xcom & sel.normal, 'xcom tiles must not repeat normal ones')

    def test_warp_destinations_are_reachable_but_marked_as_warps(self):
        sel = self.get_selection(warp=[(25, 25)])
        self.assertIn((25, 25), sel.warp)
        self.assertIn((25, 25), sel.normal)
        self.assertTrue(sel.is_warp((25, 25)))
        # and a warp tile is never double-counted as an xcom tile
        self.assertNotIn((25, 25), sel.xcom)

    def test_a_traded_unit_is_offered_no_xcom_movement(self):
        # MoveState always refused xcom for a traded unit; that rule now lives here, so
        # the highlights cannot advertise a move the state would reject
        self.unit._has_traded = True
        sel = self.get_selection(xcom=3)
        self.assertTrue(sel.walkable)
        self.assertEqual(set(), sel.xcom)

    def test_has_traded_covers_a_unit_that_merely_attacked(self):
        '''has_traded is derived: _finished or _has_attacked or _has_traded'''
        self.unit._has_attacked = True
        self.assertTrue(self.unit.has_traded)
        self.assertEqual(set(), self.get_selection(xcom=3).xcom)

    def test_a_finished_unit_gets_an_empty_selection(self):
        self.unit.finished = True
        sel = self.get_selection(xcom=3)
        self.assertFalse(sel)
        self.assertEqual(set(), sel.normal)
        # A cleared selection is what lets the cursor roam the whole map again
        self.assertNotIn((10, 10), sel)

    def test_a_finished_unit_is_not_handed_warp_tiles(self):
        self.unit.finished = True
        self.assertEqual(set(), self.get_selection(warp=[(25, 25)]).warp)

    def test_zero_move_clamps_a_guard_to_its_own_tile(self):
        with patch.object(PathSystem, 'is_zero_move', return_value=True):
            sel = self.get_selection(xcom=3, warp=[(25, 25)], zero_move=True)
        self.assertEqual({(10, 10)}, sel.walkable)
        self.assertEqual(set(), sel.warp)
        self.assertEqual(set(), sel.xcom)

    def test_the_clamp_is_only_applied_when_the_caller_asks(self):
        # The highlights ask only for units the player does not control; the enemy range
        # boundary asks for every unit. The predicate is shared, the decision is not
        with patch.object(PathSystem, 'is_zero_move', return_value=True):
            sel = self.get_selection(zero_move=False)
        self.assertGreater(len(sel.walkable), 1)

    def test_is_zero_move_needs_the_constant_the_ai_and_a_guard(self):
        from app.data.database.database import DB
        guard_ai = MagicMock()
        guard_ai.guard_ai.return_value = True
        with patch.object(DB.constants, 'value', return_value=True), \
                patch.object(DB.ai, 'get', return_value=guard_ai), \
                patch.object(UnitObject, 'get_ai', return_value='Guard'):
            self.assertTrue(self.path_system.is_zero_move(self.unit))

            # An active ai group overrides the guard
            self.game.ai_group_active = lambda ai_group: True
            self.assertFalse(self.path_system.is_zero_move(self.unit))
            self.game.ai_group_active = lambda ai_group: False

            guard_ai.guard_ai.return_value = False
            self.assertFalse(self.path_system.is_zero_move(self.unit))

    def test_is_zero_move_is_off_without_the_constant(self):
        from app.data.database.database import DB
        with patch.object(DB.constants, 'value', return_value=False), \
                patch.object(UnitObject, 'get_ai', return_value='Guard'):
            self.assertFalse(self.path_system.is_zero_move(self.unit))

    def test_is_zero_move_is_off_for_a_unit_with_no_ai(self):
        from app.data.database.database import DB
        with patch.object(DB.constants, 'value', return_value=True), \
                patch.object(UnitObject, 'get_ai', return_value=None):
            self.assertFalse(self.path_system.is_zero_move(self.unit))


if __name__ == '__main__':
    unittest.main()
