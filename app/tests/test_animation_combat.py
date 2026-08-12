import unittest
from unittest.mock import MagicMock, patch

from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options
from app.engine.combat import animation_combat


class AnimationCombatInitTests(unittest.TestCase):
    def build_combat(self):
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

    def test_cursor_is_placed_before_the_sprites_take_their_facing(self):
        '''
        The combat_attacker sprite state reads its facing off the cursor, so the
        cursor has to be on the combat's view position first. It used to be moved
        afterwards, which left the attacker facing wherever the cursor happened to
        be -- arbitrary for a combat started by an event
        '''
        combat = self.build_combat()
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


if __name__ == '__main__':
    unittest.main()
