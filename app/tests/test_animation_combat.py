import unittest
from unittest.mock import MagicMock, patch

from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options
from app.engine.combat import animation_combat


def build_combat():
    combat = animation_combat.AnimationCombat.__new__(animation_combat.AnimationCombat)
    combat.state = 'init'
    combat.last_update = 0
    combat._skip = True
    combat.playback = []
    combat.view_pos = (5, 5)
    combat.attacker = MagicMock()
    combat.defender = MagicMock()
    combat.start_combat = MagicMock()
    combat._set_stats = MagicMock()
    # Only reached at the tail of update(), well after the part under test
    combat.left_hp_bar = MagicMock()
    combat.right_hp_bar = MagicMock()
    combat.update_anims = MagicMock()
    return combat


class AnimationCombatInitTests(unittest.TestCase):
    def test_cursor_is_placed_before_the_sprites_take_their_facing(self):
        '''
        The combat_attacker sprite state reads its facing off the cursor, so the
        cursor has to be on the combat's view position first. It used to be moved
        afterwards, which left the attacker facing wherever the cursor happened to
        be -- arbitrary for a combat started by an event
        '''
        combat = build_combat()
        calls = []
        combat.attacker.sprite.change_state.side_effect = \
            lambda state: calls.append(('attacker sprite', state))
        combat.defender.sprite.change_state.side_effect = \
            lambda state: calls.append(('defender sprite', state))

        with patch.object(animation_combat, 'game') as mock_game:
            mock_game.cursor.set_pos.side_effect = lambda pos: calls.append(('cursor', pos))
            combat.update()

        self.assertEqual(('cursor', (5, 5)), calls[0])
        self.assertIn(('attacker sprite', 'combat_attacker'), calls)
        self.assertIn(('defender sprite', 'combat_defender'), calls)


class AnimationCombatTargetCursorTests(unittest.TestCase):
    '''
    On the GBA the cursor is put on what the AI is about to strike, for 46
    frames, and on nothing the player strikes. Here it was on every target, for 24
    '''

    def cursor_frames(self, ai_combat, held=(), skip=False):
        '''Whether the red cursor is up, a frame at 60 a second, until the screen begins to fade in'''
        from app.engine import engine
        from app.engine.combat import simple_combat
        self.addCleanup(engine.constants.__setitem__, 'current_time', engine.constants.get('current_time', 0))
        combat = build_combat()
        combat._skip = skip
        combat.ai_combat = ai_combat
        cursor = {'shown': False}
        frames = []
        with patch.object(animation_combat, 'game') as mock_game, \
                patch.object(simple_combat, 'get_input_manager') as mock_input:
            mock_game.cursor.combat_show.side_effect = lambda: cursor.update(shown=True)
            mock_game.cursor.hide.side_effect = lambda: cursor.update(shown=False)
            mock_input.return_value.is_pressed.side_effect = lambda button: button in held
            for frame in range(200):
                engine.constants['current_time'] = 10000 + frame * 1000 // 60
                combat.update()
                if combat.state == 'fade_in':
                    break
                frames.append(cursor['shown'])
        self.assertEqual('fade_in', combat.state)
        self.assertFalse(cursor['shown'])
        return frames

    def test_cursor_is_on_the_target_before_the_ai_strikes(self):
        frames = self.cursor_frames(ai_combat=True)
        # The frame the camera is sent off on, and the 46 after it
        self.assertIn(len(frames), (47, 48))
        self.assertTrue(all(frames))

    def test_holding_a_button_cuts_it_short(self):
        for button in ('SELECT', 'START'):
            self.assertLess(len(self.cursor_frames(ai_combat=True, held=(button,))), 3, button)
        # But not any button
        self.assertGreater(len(self.cursor_frames(ai_combat=True, held=('BACK',))), 40)

    def test_player_is_not_shown_the_target_they_chose(self):
        frames = self.cursor_frames(ai_combat=False)
        self.assertEqual([False], frames)

    def test_nothing_shown_for_a_combat_that_is_skipped(self):
        frames = self.cursor_frames(ai_combat=True, skip=True)
        self.assertEqual([False], frames)


if __name__ == '__main__':
    unittest.main()
