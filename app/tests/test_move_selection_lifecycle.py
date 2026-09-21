import os
import unittest
from unittest.mock import MagicMock, patch

import pygame

import app.engine.sprites as sprites
from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options


class MoveSelectionLifecycleTests(unittest.TestCase):
    '''
    "Am I choosing a destination?" used to be encoded implicitly, as highlights['move']
    being non-empty -- hover wrote the separate light set, which check_in_move ignored,
    and the blanket remove_highlights() calls cleaned it up. Now the cursor holds a
    MoveSelection instead, so it has to be armed and cleared on exactly the same beats or
    the cursor keeps clamping to a stale movement border
    '''

    def setUp(self):
        # settings.py (pulled in by general_states) reads sprites at module level
        sprites.load_images()
        # phase.py builds surfaces at module level, which needs a display
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        pygame.display.init()
        if not pygame.display.get_surface():
            pygame.display.set_mode((1, 1))

        from app.engine.movement.move_selection import MoveSelection
        self.MoveSelection = MoveSelection

    def begin_move_state(self, selection, **unit_attrs):
        '''Runs MoveState.begin against a mocked game, and reports the state and cursor'''
        from app.engine import general_states

        move_state = general_states.MoveState.__new__(general_states.MoveState)
        with patch.object(general_states, 'game') as mock_game, \
                patch.object(general_states, 'phase'):
            cur_unit = mock_game.cursor.cur_unit
            cur_unit.is_dying = False
            cur_unit.dead = False
            cur_unit.position = (1, 1)
            cur_unit.previous_position = (1, 1)
            cur_unit.traveler = None
            cur_unit.has_traded = False
            cur_unit.has_attacked = False
            for key, value in unit_attrs.items():
                setattr(cur_unit, key, value)
            mock_game.path_system.get_move_selection.return_value = selection

            move_state.begin()
            return move_state, mock_game

    def test_move_state_arms_the_cursor_with_the_selection_it_judges_against(self):
        selection = self.MoveSelection(walkable={(1, 1), (1, 2)})
        move_state, mock_game = self.begin_move_state(selection)
        # The same object, not a copy -- one truth for the border and for SELECT
        self.assertIs(selection, move_state.move_selection)
        self.assertIs(selection, mock_game.cursor.move_selection)

    def test_a_traded_unit_is_armed_too_even_though_it_skips_the_attack_preview(self):
        selection = self.MoveSelection(walkable={(1, 1), (1, 2)})
        move_state, mock_game = self.begin_move_state(selection, has_traded=True)
        self.assertIs(selection, mock_game.cursor.move_selection)
        # Only the moves are drawn; no attack or spell ranges for a unit that has acted
        mock_game.highlight.display_moves.assert_called_once_with(selection.normal, light=False)
        mock_game.highlight.display_highlights.assert_not_called()

    def test_the_highlights_are_drawn_from_the_selection_rather_than_recomputing_it(self):
        selection = self.MoveSelection(walkable={(1, 1)}, xcom={(1, 4)})
        _, mock_game = self.begin_move_state(selection)
        mock_game.highlight.display_highlights.assert_called_once_with(
            mock_game.cursor.cur_unit, selection)

    def test_move_state_end_clears_the_cursor(self):
        from app.engine import general_states

        move_state = general_states.MoveState.__new__(general_states.MoveState)
        with patch.object(general_states, 'game') as mock_game:
            move_state.end()
            mock_game.cursor.remove_arrows.assert_called_once()
            mock_game.highlight.remove_highlights.assert_called_once()

    def build_cursor(self):
        from app.engine.level_cursor import LevelCursor

        cursor = LevelCursor.__new__(LevelCursor)
        cursor.move_selection = self.MoveSelection()
        cursor._last_valid_position = None
        cursor._display_arrows = False
        cursor.arrows = []
        return cursor

    def test_remove_arrows_clears_the_selection(self):
        cursor = self.build_cursor()
        cursor.move_selection = self.MoveSelection(walkable={(1, 1)}, xcom={(1, 4)})
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

    def test_hovering_a_unit_never_arms_the_cursor(self):
        '''
        Hover draws the light move highlights for any unit under the cursor. It must not
        make the cursor think the player is choosing a destination -- that used to be
        guaranteed by hover writing 'possible_move' rather than 'move'
        '''
        from app.engine import highlight

        controller = highlight.HighlightController()
        hover_unit = MagicMock()
        hover_unit.team = 'enemy'
        hover_unit.skills = []

        with patch.object(highlight, 'game') as mock_game:
            mock_game.cursor.get_hover.return_value = hover_unit
            mock_game.cursor.move_selection = self.MoveSelection()
            mock_game.path_system.get_move_selection.return_value = \
                self.MoveSelection(walkable={(5, 5)})
            mock_game.target_system.get_all_attackable_positions_spells.return_value = set()
            mock_game.target_system.get_all_attackable_positions_weapons.return_value = set()

            controller.handle_hover()

            self.assertFalse(mock_game.cursor.move_selection,
                             'hover armed the cursor with a movement border')
            # It does light up the move tiles, in the light set
            self.assertEqual({(5, 5)}, controller.highlights['possible_move'])
            self.assertEqual(set(), controller.highlights['move'])

    def test_hover_asks_for_the_zero_move_clamp_only_for_units_the_player_does_not_control(self):
        from app.engine import highlight

        controller = highlight.HighlightController()
        for team, expected in (('player', False), ('enemy', True)):
            hover_unit = MagicMock()
            hover_unit.team = team
            hover_unit.skills = []
            with patch.object(highlight, 'game') as mock_game:
                mock_game.cursor.get_hover.return_value = hover_unit
                mock_game.path_system.get_move_selection.return_value = self.MoveSelection()
                mock_game.target_system.get_all_attackable_positions_spells.return_value = set()
                mock_game.target_system.get_all_attackable_positions_weapons.return_value = set()

                controller.handle_hover()

                mock_game.path_system.get_move_selection.assert_called_once_with(
                    hover_unit, zero_move=expected)


if __name__ == '__main__':
    unittest.main()
