import logging
import unittest
from unittest.mock import MagicMock, patch, call

import app.editor.lib.csv.csv_data_exporter as csv
from app.tests.engine_harness import EngineTestCase
from app.engine import engine, item_system
from app.engine.combat_calcs import WeaponAdvantage
from app.engine.query_engine import GameQueryEngine
from app.tests.mocks.mock_game import get_mock_game
from app.tests.mocks.mock_object import Object

class QueryEngineTests(unittest.TestCase):
    def setUp(self):
        self.game = get_mock_game()
        self.query_engine = GameQueryEngine(logging.Logger("logger"), self.game)

    def tearDown(self) -> None:
        pass

    def test_resolve_to_unit(self):
        eirika_obj = Object(nid='Eirika', position=(2, 4))

        def mock_get_unit_return(value):
            if value == 'Eirika':
                return eirika_obj
            raise ValueError()
        self.game.get_unit = MagicMock(side_effect=mock_get_unit_return)

        res = self.query_engine._resolve_to_unit('Eirika')
        self.assertEqual(res.position, eirika_obj.position)

        res = self.query_engine._resolve_to_unit(eirika_obj)
        self.assertEqual(res.position, eirika_obj.position)

    def test_resolve_pos(self):
        TEST_POS = (2, 4)
        eirika_obj = Object(nid='Eirika', position=TEST_POS)
        def mock_get_unit_return(value):
            if value == 'Eirika':
                return eirika_obj
            raise ValueError()
        self.game.get_unit = MagicMock(side_effect=mock_get_unit_return)

        res = self.query_engine._resolve_pos((2, 4))
        self.assertEqual(res, TEST_POS)

        res = self.query_engine._resolve_pos('Eirika')
        self.assertEqual(res, TEST_POS)

        res = self.query_engine._resolve_pos(eirika_obj)
        self.assertEqual(res, TEST_POS)

class CheckAdvantageTests(EngineTestCase):
    '''Eirika's Rapier (a sword) against an enemy's Iron Axe'''
    def setUp(self):
        super().setUp()
        harness = self.start_harness()
        self.game = harness.start_level('0')
        harness.run_until_state('free')
        self.eirika = self.game.get_unit('Eirika')
        self.enemy = self.game.get_unit('101')
        self.rapier = self.eirika.get_weapon()
        self.axe = self.enemy.get_weapon()
        self.check_advantage = self.game.query_engine.check_advantage
        self.check_no_triangle = self.game.query_engine.check_no_triangle
        self.check_disadvantage = self.game.query_engine.check_disadvantage

    def drawn_arrow(self) -> str:
        surf = MagicMock()
        with patch.object(engine, 'subsurface', side_effect=lambda sprite, rect: 'up' if rect[1] == 0 else 'down'):
            self.game.ui_view.draw_adv_arrows(surf, self.eirika, self.enemy, self.rapier, self.axe, (0, 0))
        surf.blit.assert_called_once()
        return surf.blit.call_args.args[0]

    def test_advantage_and_disadvantage(self):
        self.assertIs(self.check_advantage(self.eirika, self.enemy, self.rapier, self.axe), True)
        self.assertIs(self.check_no_triangle(self.eirika, self.enemy, self.rapier, self.axe), False)
        self.assertIs(self.check_disadvantage(self.eirika, self.enemy, self.rapier, self.axe), False)

        self.assertIs(self.check_advantage(self.enemy, self.eirika, self.axe, self.rapier), False)
        self.assertIs(self.check_no_triangle(self.enemy, self.eirika, self.axe, self.rapier), False)
        self.assertIs(self.check_disadvantage(self.enemy, self.eirika, self.axe, self.rapier), True)

    def test_units_and_items_by_nid(self):
        self.assertIs(self.check_advantage('Eirika', '101', 'Rapier', 'Iron_Axe'), True)

    def test_neutral_when_the_target_has_no_weapon(self):
        self.assertIs(self.check_advantage(self.eirika, self.enemy, self.rapier, None), False)
        self.assertIs(self.check_no_triangle(self.eirika, self.enemy, self.rapier, None), True)
        self.assertIs(self.check_disadvantage(self.eirika, self.enemy, self.rapier, None), False)

    def test_result_has_no_truth_value(self):
        for member in WeaponAdvantage:
            with self.assertRaises(TypeError):
                bool(member)

    def test_arrow_component_does_not_change_the_query(self):
        with patch.object(item_system, 'show_weapon_disadvantage', return_value=True):
            self.assertIs(self.check_advantage(self.eirika, self.enemy, self.rapier, self.axe), True)

    def test_drawn_arrow_follows_the_weapon_triangle(self):
        self.assertEqual(self.drawn_arrow(), 'up')

    def test_arrow_component_overrides_the_drawn_arrow(self):
        with patch.object(item_system, 'show_weapon_disadvantage', return_value=True):
            self.assertEqual(self.drawn_arrow(), 'down')

if __name__ == '__main__':
    unittest.main()
