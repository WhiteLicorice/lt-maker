import unittest
from unittest.mock import MagicMock, patch

from app.data.resources import combat_commands
from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options
from app.engine import battle_animation
from app.engine.battle_animation import BattleAnimation

class CombatRumbleCommandTests(unittest.TestCase):
    '''
    A combat animation script can rumble the player's controller,
    the same way it can shake the screen
    '''
    def run_command(self, text):
        """Returns the calls made to the input manager's rumble by the script line"""
        anim = BattleAnimation.__new__(BattleAnimation)
        anim.owner = MagicMock()
        input_manager = MagicMock()
        with patch.object(battle_animation, 'get_input_manager', lambda: input_manager):
            anim.run_command(combat_commands.parse_text(text))
        # Rumbling is not something the combat itself needs to know about
        anim.owner.assert_not_called()
        return input_manager.rumble.call_args_list

    def test_light_rumble(self):
        (call,) = self.run_command('rumble')
        self.assertEqual(call.args, (0.5, 0.5, 150))

    def test_heavy_rumble(self):
        (call,) = self.run_command('rumble_2')
        self.assertEqual(call.args, (1, 1, 500))

    def test_screen_shake_does_not_rumble(self):
        anim = BattleAnimation.__new__(BattleAnimation)
        anim.owner = MagicMock()
        input_manager = MagicMock()
        with patch.object(battle_animation, 'get_input_manager', lambda: input_manager):
            anim.run_command(combat_commands.parse_text('screen_shake'))
        input_manager.rumble.assert_not_called()

    def test_commands_survive_a_save_and_load(self):
        for nid in ('rumble', 'rumble_2'):
            command = combat_commands.parse_text(nid)
            self.assertEqual(combat_commands.generate_text(command), nid)

if __name__ == '__main__':
    unittest.main()
