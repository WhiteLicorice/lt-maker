import unittest

from app.tests.engine_harness import EngineTestCase


class StaleForecastTests(EngineTestCase):
    '''
    Choosing a target leaves the battle forecast up through the combat. Targeting
    for a spell afterwards must not slide it out when backed out of, since the
    unit it showed may have died since
    '''

    def setUp(self):
        super().setUp()
        harness = self.harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')

    def test_backing_out_of_spell_targeting_after_a_kill(self):
        harness, game = self.harness, self.harness.game
        harness.move_unit('Seth', (8, 5))
        harness.choose('Attack')
        harness.run_until_state('weapon_choice')
        harness.press('SELECT')
        harness.run_until_state('combat_targeting')
        harness.run_until(lambda: game.ui_view.attack_info_slide.state == 'shown',
                          description='battle forecast up')
        defender = game.ui_view.attack_info_args[2]
        harness.press('SELECT')
        harness.run_until_state('free', max_frames=3000)
        self.assertIsNone(defender.position, 'Seth kills it')
        # Eirika, next to the other soldier, targets it
        eirika = game.get_unit('Eirika')
        game.leave(eirika)
        game.arrive(eirika, (9, 5))
        game.cursor.cur_unit = eirika
        game.memory['item'] = eirika.get_weapon()
        game.memory['ability'] = 'Spells'
        game.state.change('combat_targeting')
        harness.run_until_state('combat_targeting')
        harness.press('BACK')
        harness.run_until(lambda: harness.state != 'combat_targeting', description='targeting left')


if __name__ == '__main__':
    unittest.main()
