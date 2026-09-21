import os
import unittest
from unittest.mock import MagicMock, patch

import pygame

import app.engine.sprites as sprites
from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options


class SelectedFacingTests(unittest.TestCase):
    def setUp(self):
        # settings.py (pulled in by general_states) reads sprites at module level
        sprites.load_images()
        # phase.py builds surfaces at module level, which needs a display
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        pygame.display.init()
        if not pygame.display.get_surface():
            pygame.display.set_mode((1, 1))

    def build_sprite(self, tags):
        from app.engine.unit_sprite import UnitSprite
        sprite = UnitSprite.__new__(UnitSprite)
        sprite.unit = MagicMock()
        sprite.unit.tags = tags
        sprite.image_state = 'passive'
        return sprite

    def test_mounted_unit_faces_right_while_choosing_a_destination(self):
        sprite = self.build_sprite({'Mounted'})
        sprite.change_state('selected')
        self.assertEqual('right', sprite.image_state)

    def test_unmounted_unit_faces_down_while_choosing_a_destination(self):
        sprite = self.build_sprite({'Armor'})
        sprite.change_state('selected')
        self.assertEqual('down', sprite.image_state)

    def test_move_state_uses_the_move_select_facing(self):
        '''
        The 'selected' sprite state used to face every unit down. Mounted units
        face right instead while the player picks a destination
        '''
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
            from app.engine.movement.move_selection import MoveSelection
            mock_game.path_system.get_move_selection.return_value = MoveSelection()

            move_state.begin()

            cur_unit.sprite.change_state.assert_called_once_with('selected')


if __name__ == '__main__':
    unittest.main()
