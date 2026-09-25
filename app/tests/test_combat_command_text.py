import unittest

from app.data.resources import combat_commands


class CombatCommandTextRoundTripTests(unittest.TestCase):
    """generate_text writes the legacy script format that parse_text reads back in"""

    def round_trip(self, text):
        command = combat_commands.parse_text(text)
        return combat_commands.parse_text(combat_commands.generate_text(command))

    def test_color_survives_round_trip(self):
        command = self.round_trip('enemy_tint;8;248,248,248')
        self.assertEqual(command.nid, 'enemy_tint')
        self.assertEqual(command.value, (8, (248, 248, 248)))

    def test_rgba_color_survives_round_trip(self):
        command = self.round_trip('screen_blend_with_fade_out;15;65;255,255,255,255')
        self.assertEqual(command.value, (15, 65, (255, 255, 255, 255)))

    def test_two_colors_survive_round_trip(self):
        command = self.round_trip('parent_tint_blend;75;32,80,8,255;128,160,40,255')
        self.assertEqual(command.value, (75, (32, 80, 8, 255), (128, 160, 40, 255)))


if __name__ == '__main__':
    unittest.main()
