import unittest
from unittest.mock import MagicMock, patch

from app.engine.movement.move_selection import MoveSelection
from app.tests.engine_harness import EngineTestCase


class MoveSelectionLifecycleTests(EngineTestCase):
    '''
    "Am I choosing a destination?" used to be encoded implicitly, as highlights['move']
    being non-empty -- hover wrote the separate light set, which check_in_move ignored,
    and the blanket remove_highlights() calls cleaned it up. Now the cursor holds a
    MoveSelection instead, so it has to be armed and cleared on exactly the same beats or
    the cursor keeps clamping to a stale movement border.

    Played in testing_proj level 0: Eirika (4, 5) and Seth (4, 4) against the
    fighters 101 (9, 6) and 102 (8, 6). Seth is a Paladin, with Canto
    '''

    def setUp(self):
        super().setUp()
        self.harness = self.start_harness()
        self.harness.start_level('0')
        self.harness.run_until_state('free')
        self.cursor = self.harness.game.cursor
        self.highlights = self.harness.game.highlight.highlights

    def test_move_state_arms_the_cursor_with_the_selection_it_judges_against(self):
        self.harness.select_unit('Eirika')
        move_state = self.harness.game.state.current_state()
        # The same object, not a copy -- one truth for the border and for SELECT
        self.assertIs(move_state.move_selection, self.cursor.move_selection)
        self.assertIn((5, 5), self.cursor.move_selection)

    def test_the_highlights_are_drawn_from_the_selection(self):
        self.harness.select_unit('Eirika')
        self.assertEqual(self.cursor.move_selection.normal, self.highlights['move'])
        # Eirika can reach the fighters, so her attack range is drawn around the moves
        self.assertTrue(self.highlights['attack'])

    def test_a_traded_unit_is_armed_too_even_though_it_skips_the_attack_preview(self):
        # Trading without moving, then backing out, sends a unit with canto back to move
        self.harness.move_unit('Seth', (4, 4))
        self.harness.choose('Trade')
        self.harness.run_until_state('targeting')
        self.harness.press('SELECT')
        self.harness.run_until_state('trade')
        # Pick up Seth's first item and hand it over
        self.harness.press('SELECT')
        self.harness.press('SELECT')
        self.harness.press('BACK')
        self.harness.run_until_state('menu')
        self.harness.press('BACK')
        self.harness.run_until_state('move')

        self.assertTrue(self.harness.game.get_unit('Seth').has_traded)
        self.assertIs(self.harness.game.state.current_state().move_selection, self.cursor.move_selection)
        self.assertEqual(self.cursor.move_selection.normal, self.highlights['move'])
        # Only the moves are drawn; no attack or spell ranges for a unit that has acted
        self.assertEqual(set(), self.highlights['attack'])
        self.assertEqual(set(), self.highlights['spell'])

    def test_backing_out_of_the_move_clears_the_cursor(self):
        self.harness.select_unit('Eirika')
        self.harness.press('BACK')
        self.harness.run_until_state('free')
        self.assertFalse(self.cursor.move_selection)
        self.assertEqual(set(), self.highlights['move'])

    def test_waiting_clears_the_cursor(self):
        self.harness.wait('Eirika', (5, 5))
        self.harness.run_until_state('free')
        self.assertFalse(self.cursor.move_selection)
        self.assertEqual(set(), self.highlights['move'])

    def test_hovering_a_unit_never_arms_the_cursor(self):
        '''
        Hover draws the light move highlights for any unit under the cursor. It must not
        make the cursor think the player is choosing a destination -- that used to be
        guaranteed by hover writing 'possible_move' rather than 'move'
        '''
        self.harness.move_cursor_to((8, 6))
        self.harness.step()
        self.assertFalse(self.cursor.move_selection, 'hover armed the cursor with a movement border')
        # It does light up the move tiles, in the light set
        self.assertTrue(self.highlights['possible_move'])
        self.assertEqual(set(), self.highlights['move'])


class LevelCursorMoveSelectionTests(EngineTestCase):
    def build_cursor(self):
        from app.engine.level_cursor import LevelCursor

        cursor = LevelCursor.__new__(LevelCursor)
        cursor.move_selection = MoveSelection()
        cursor._last_valid_position = None
        cursor._display_arrows = False
        cursor.arrows = []
        return cursor

    def test_remove_arrows_clears_the_selection(self):
        cursor = self.build_cursor()
        cursor.move_selection = MoveSelection(walkable={(1, 1)}, xcom={(1, 4)})
        cursor._last_valid_position = (1, 1)
        cursor._display_arrows = True

        cursor.remove_arrows()

        self.assertFalse(cursor.move_selection)
        self.assertIsNone(cursor._last_valid_position)
        self.assertFalse(cursor._display_arrows)

    def test_a_cleared_cursor_treats_every_tile_as_out_of_bounds_for_clamping(self):
        # This is what frees the cursor to roam the map outside of move selection
        cursor = self.build_cursor()
        self.assertNotIn((1, 1), cursor.move_selection)
        self.assertNotIn((0, 0), cursor.move_selection)

    def test_hover_asks_for_the_zero_move_clamp_only_for_units_the_player_does_not_control(self):
        from app.engine import highlight

        controller = highlight.HighlightController()
        for team, expected in (('player', False), ('enemy', True)):
            hover_unit = MagicMock()
            hover_unit.team = team
            hover_unit.skills = []
            with patch.object(highlight, 'game') as mock_game:
                mock_game.cursor.get_hover.return_value = hover_unit
                mock_game.path_system.get_move_selection.return_value = MoveSelection()
                mock_game.target_system.get_all_attackable_positions_spells.return_value = set()
                mock_game.target_system.get_all_attackable_positions_weapons.return_value = set()

                controller.handle_hover()

                mock_game.path_system.get_move_selection.assert_called_once_with(
                    hover_unit, zero_move=expected)


if __name__ == '__main__':
    unittest.main()
