import unittest
from unittest.mock import patch

from app.engine import combat_calcs, ui_view
from app.engine import config as cf
from app.engine.combat.utils import resolve_weapon
from app.tests.engine_harness import EngineTestCase

# testing_proj level 0: Seth (4, 4) against the generic fighter 102 (8, 6)
LEVEL = '0'

class ForecastAttackSpeedTests(EngineTestCase):
    '''
    The Detailed combat forecast has an AS row. It should show each unit's own
    attack speed, not how much faster that unit is than the other one
    '''

    def setUp(self):
        super().setUp()
        self.harness = self.start_harness()
        self.game = self.harness.start_level(LEVEL)
        self.harness.run_until_state('free')
        self.seth = self.game.get_unit('Seth')
        self.fighter = self.game.get_unit('102')
        self.weapon = self.seth.get_weapon()
        self.def_weapon = resolve_weapon(self.fighter)

    def attack_speeds(self) -> tuple[int, int]:
        return (combat_calcs.compute_attack_speed(self.seth, self.fighter, self.weapon, self.def_weapon, 'attack', (0, 0)),
                combat_calcs.compute_attack_speed(self.fighter, self.seth, self.def_weapon, self.weapon, 'defense', (0, 0)))

    def test_each_unit_gets_its_own_attack_speed(self):
        seth_speed, fighter_speed = self.attack_speeds()
        self.assertEqual(combat_calcs.attack_speed(self.seth, self.weapon), seth_speed)
        self.assertEqual(combat_calcs.attack_speed(self.fighter, self.def_weapon), fighter_speed)
        # Seth is much faster than a fighter, so the two could only add up to zero
        # if each one were the difference between them
        self.assertNotEqual(0, seth_speed + fighter_speed)

    def test_true_speed_is_attack_speed_less_the_targets_defense_speed(self):
        seth_speed, fighter_speed = self.attack_speeds()
        self.assertEqual(
            seth_speed - combat_calcs.defense_speed(self.fighter, self.def_weapon, self.weapon),
            combat_calcs.compute_true_speed(self.seth, self.fighter, self.weapon, self.def_weapon, 'attack', (0, 0)))
        self.assertEqual(
            fighter_speed - combat_calcs.defense_speed(self.seth, self.weapon, self.def_weapon),
            combat_calcs.compute_true_speed(self.fighter, self.seth, self.def_weapon, self.weapon, 'defense', (0, 0)))

    def test_detailed_forecast_draws_each_units_attack_speed(self):
        cf.SETTINGS['forecast'] = 'Detailed'
        font = ui_view.FONT['text-blue']
        with patch.object(font, 'blit_right', wraps=font.blit_right) as blit_right:
            self.game.ui_view.create_attack_info(self.seth, self.weapon, self.fighter)
        drawn = {call.args[2]: call.args[0] for call in blit_right.call_args_list}
        # AS is the last row of numbers: the attacker's column is at x = 88, the defender's at x = 44
        last_row = max(y for x, y in drawn)
        seth_speed, fighter_speed = self.attack_speeds()
        self.assertEqual(str(seth_speed), drawn[(88, last_row)])
        self.assertEqual(str(fighter_speed), drawn[(44, last_row)])

if __name__ == '__main__':
    unittest.main()
