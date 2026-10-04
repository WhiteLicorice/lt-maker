import unittest

from app.engine import config as cf
from app.tests.engine_harness import EngineTestCase

# testing_proj level 0: Eirika (4, 5) and Seth (4, 4) against the generic
# fighters 101 (9, 6) and 102 (8, 6), with O'Neill guarding (10, 8)
LEVEL = '0'

class EngineHarnessTests(EngineTestCase):
    '''
    The harness plays testing_proj through the real state machine, so these pin
    down that it does: if one fails, every test built on the harness is suspect
    '''

    def setUp(self):
        super().setUp()
        self.harness = self.start_harness()
        self.harness.start_level(LEVEL)
        self.harness.run_until_state('free')

    def test_level_starts_on_the_player_phase(self):
        game = self.harness.game
        self.assertEqual(['free'], game.state.state_names())
        self.assertEqual(1, game.turncount)
        self.assertEqual('player', game.phase.get_current())

    def test_a_unit_moves_and_waits_through_button_presses(self):
        self.harness.wait('Eirika', (5, 5))
        self.harness.run_until_state('free')
        eirika = self.harness.game.get_unit('Eirika')
        self.assertEqual((5, 5), eirika.position)
        self.assertTrue(eirika.finished)

    def test_backing_out_of_the_menu_puts_the_unit_back(self):
        self.harness.move_unit('Eirika', (5, 5))
        self.harness.press('BACK')
        self.harness.run_until_state('move')
        self.harness.press('BACK')
        self.harness.run_until_state('free')
        eirika = self.harness.game.get_unit('Eirika')
        self.assertEqual((4, 5), eirika.position)
        self.assertFalse(eirika.finished)

    def test_combat_plays_out_the_same_every_time(self):
        '''The random seed is pinned, so Seth's Steel Sword always kills 102'''
        self.harness.attack('Seth', (8, 5))
        game = self.harness.game
        self.assertTrue(game.get_unit('102').dead)
        self.assertEqual((8, 5), game.get_unit('Seth').position)
        self.assertTrue(game.get_unit('Seth').finished)

    def test_the_enemy_phase_runs_and_the_turn_comes_back(self):
        # Waiting with both units auto-ends the turn
        self.harness.wait('Eirika', (5, 5))
        self.harness.wait('Seth', (3, 3))
        self.harness.run_until_player_turn(2)
        game = self.harness.game
        # 101 and 102 left their starting tiles to attack Eirika
        self.assertNotEqual((9, 6), game.get_unit('101').position)
        self.assertNotEqual((8, 6), game.get_unit('102').position)
        self.assertLess(game.get_unit('Eirika').get_hp(), game.get_unit('Eirika').get_max_hp())

class EngineTestCaseTests(EngineTestCase):
    def test_settings_are_the_defaults_whatever_the_config_file_says(self):
        self.assertEqual(cf.convert_setting('unit_speed', cf.base_config()['unit_speed']), cf.SETTINGS['unit_speed'])
        self.assertEqual(0, cf.SETTINGS['random_seed'])

    def test_settings_a_test_changes_are_put_back(self):
        self.tearDown()
        before = cf.SETTINGS.copy()
        self.setUp()
        cf.SETTINGS['unit_speed'] = 1
        self.tearDown()
        self.assertEqual(before, cf.SETTINGS)
        self.setUp()

if __name__ == '__main__':
    unittest.main()
