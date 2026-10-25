import unittest
from unittest.mock import patch

from app.engine import action
from app.tests.engine_harness import EngineTestCase

class AIEquipLoggingTests(EngineTestCase):
    '''The AI tries each of its unit's items by equipping it, and equips the first again afterwards'''

    def test_the_enemy_phase_equips_nothing_already_equipped(self):
        '''Each unit tried, and equipped again, the weapon it already had equipped, filling the action log'''
        harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')

        already_equipped = []
        equip_item_init = action.EquipItem.__init__
        def record(equip, unit, item):
            already_equipped.append(unit.has_equipped(item))
            equip_item_init(equip, unit, item)
        with patch.object(action.EquipItem, '__init__', record):
            harness.end_turn()
            harness.run_until_player_turn(2)

        self.assertNotIn(True, already_equipped)

    def test_has_equipped_is_when_equip_does_nothing(self):
        harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        unit = harness.game.get_unit('Eirika')
        weapon = unit.get_weapon()
        self.assertTrue(unit.has_equipped(weapon))
        with patch('app.engine.item_system.on_equip_item') as on_equip_item:
            unit.equip(weapon)
        on_equip_item.assert_not_called()

if __name__ == '__main__':
    unittest.main()
