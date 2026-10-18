import unittest
from unittest.mock import patch

from app.engine import action, engine, item_funcs
import app.engine.config as cf
from app.events import triggers
from app.tests.engine_harness import EngineTestCase

SHOP_ITEMS = 'Iron_Sword,Steel_Sword,Iron_Lance,Steel_Lance,Iron_Axe,Steel_Axe,Iron_Bow,Fire'


class ShopTests(EngineTestCase):
    '''
    The shop as on the GBA (bmshop.c): every purchase and sale is asked about first, a unit
    with full hands is asked whether to send the item to the convoy, and running out of
    things to sell goes back to Buy or Sell.

    Played in testing_proj level 0, with Eirika at the shop
    '''

    def setUp(self):
        super().setUp()
        # Text appears at once, so a line is done the frame it is shown
        text_speed = patch.dict(cf.SETTINGS, {'text_speed': 0})
        text_speed.start()
        self.addCleanup(text_speed.stop)
        self.harness = self.start_harness()
        self.harness.start_level('0')
        self.harness.run_until_state('free')
        self.game = self.harness.game
        self.unit = self.game.get_unit('Eirika')
        self.game.set_money(10000)

    def give_items(self, nids):
        for item in self.unit.items[:]:
            action.do(action.RemoveItem(self.unit, item))
        for nid in nids:
            item = item_funcs.create_item(self.unit, nid)
            self.game.register_item(item)
            action.do(action.GiveItem(self.unit, item))

    def open_shop(self):
        script = 'shop;Eirika;%s' % SHOP_ITEMS
        self.game.events._add_event_from_script('shop_test', script, triggers.GenericTrigger(self.unit, None, self.unit.position, {}))
        self.harness.run_until_state('shop')
        self.shop = self.game.state.current_state()
        self.harness.step(20)
        while self.shop.state == 'open':
            self.harness.press('SELECT', 4)
        self.assertEqual('choice', self.shop.state)

    def press(self, button):
        '''Taps button, then waits for the shopkeeper to finish talking'''
        self.harness.press(button, 6)
        self.harness.run_until(lambda: self.shop.current_msg.is_done_or_wait(), 300, 'the line said')

    def choose_buy(self):
        self.shop.choice_menu.move_to(0)
        self.press('SELECT')
        self.assertEqual('buy', self.shop.state)

    def choose_sell(self):
        self.shop.choice_menu.move_to(1)
        self.press('SELECT')

    def test_buying_is_asked_about_first(self):
        self.give_items(['Vulnerary'])
        self.open_shop()
        self.choose_buy()
        self.press('SELECT')
        self.assertEqual('buy_confirm', self.shop.state)
        self.assertEqual(10000, self.game.get_money())
        self.assertEqual(['Vulnerary'], [item.nid for item in self.unit.items])

        self.press('SELECT')  # Yes
        self.assertEqual('buy', self.shop.state)
        self.assertEqual(['Vulnerary', 'Iron_Sword'], [item.nid for item in self.unit.items])
        self.assertLess(self.game.get_money(), 10000)

    def test_no_goes_back_to_the_list_without_buying(self):
        self.give_items(['Vulnerary'])
        self.open_shop()
        self.choose_buy()
        self.press('SELECT')
        self.press('RIGHT')  # No
        self.press('SELECT')
        self.assertEqual('buy', self.shop.state)
        self.assertEqual(10000, self.game.get_money())

        self.press('SELECT')
        self.press('BACK')  # Backing out is a No too
        self.assertEqual('buy', self.shop.state)
        self.assertEqual(['Vulnerary'], [item.nid for item in self.unit.items])

    def test_full_hands_are_asked_about_the_convoy(self):
        self.game.game_vars['_convoy'] = True
        self.give_items(['Vulnerary'] * 5)
        self.open_shop()
        self.choose_buy()
        self.press('SELECT')
        self.press('SELECT')  # Yes to the price
        self.assertEqual('convoy_confirm', self.shop.state)
        self.assertEqual(10000, self.game.get_money())
        self.assertTrue(self.shop.confirm_menu.takes_input)  # The hand is on Yes

        self.press('SELECT')  # Yes, send it
        self.assertEqual('buy', self.shop.state)
        self.assertEqual(['Iron_Sword'], [item.nid for item in self.game.party.convoy])
        self.assertEqual(5, len(self.unit.items))

    def test_not_sending_it_to_the_convoy_goes_back_to_buy_or_sell(self):
        self.game.game_vars['_convoy'] = True
        self.give_items(['Vulnerary'] * 5)
        self.open_shop()
        self.choose_buy()
        self.press('SELECT')
        self.press('SELECT')
        self.press('RIGHT')  # No
        self.press('SELECT')
        self.assertEqual('choice', self.shop.state)
        self.assertEqual(10000, self.game.get_money())
        self.assertEqual([], [item.nid for item in self.game.party.convoy])

    def test_full_hands_without_a_convoy(self):
        self.game.game_vars['_convoy'] = False
        self.give_items(['Vulnerary'] * 5)
        self.open_shop()
        self.choose_buy()
        self.press('SELECT')
        self.press('SELECT')
        self.assertEqual('choice', self.shop.state)
        self.assertEqual(10000, self.game.get_money())

    def test_selling_is_asked_about_first(self):
        self.give_items(['Vulnerary', 'Iron_Sword'])
        self.open_shop()
        self.choose_sell()
        self.assertEqual('sell', self.shop.state)
        self.press('SELECT')
        self.assertEqual('sell_confirm', self.shop.state)
        self.assertEqual(2, len(self.unit.items))

        self.press('SELECT')  # Yes
        self.assertEqual('sell', self.shop.state)
        self.assertEqual(['Iron_Sword'], [item.nid for item in self.unit.items])
        self.assertGreater(self.game.get_money(), 10000)

    def test_the_hand_stays_on_the_items_after_selling_the_last_one_in_the_list(self):
        self.give_items(['Vulnerary', 'Iron_Sword'])
        self.open_shop()
        self.choose_sell()
        self.press('DOWN')
        self.press('SELECT')
        self.press('SELECT')
        self.assertEqual('sell', self.shop.state)
        self.assertEqual(0, self.shop.sell_menu.current_index)

    def test_selling_the_last_item_goes_back_to_buy_or_sell(self):
        self.give_items(['Vulnerary'])
        self.open_shop()
        self.choose_sell()
        self.press('SELECT')
        self.press('SELECT')
        self.assertEqual([], self.unit.items)
        self.assertEqual('choice', self.shop.state)

    def test_sell_with_nothing_to_sell_says_so(self):
        self.give_items([])
        self.open_shop()
        self.choose_sell()
        self.assertEqual('choice', self.shop.state)
        self.assertIn('nothing to sell', ''.join(c for c in self.shop.current_msg.text_commands if len(c) == 1))

    def test_a_scrolling_list_takes_no_selection(self):
        self.give_items(['Vulnerary'])
        self.open_shop()
        self.choose_buy()
        for _ in range(3):
            self.press('DOWN')
        # Onto the last row shown: the list scrolls
        self.harness.step(events=[self.harness._key_event(engine.KEYDOWN, 'DOWN')])
        self.harness.step(events=[self.harness._key_event(engine.KEYUP, 'DOWN')])
        self.assertTrue(self.shop.buy_menu.is_scrolling())
        self.harness.step(events=[self.harness._key_event(engine.KEYDOWN, 'SELECT')])
        self.assertEqual('buy', self.shop.state)
        self.harness.step(events=[self.harness._key_event(engine.KEYUP, 'SELECT')])
        self.harness.step(4)
        self.assertFalse(self.shop.buy_menu.is_scrolling())
        self.press('SELECT')
        self.assertEqual('buy_confirm', self.shop.state)


class ShopTextSpeedTests(EngineTestCase):
    '''Shopkeepers talk at twice the speed of other dialog'''

    def frames_to_say(self, d):
        for frame in range(1000):
            if d.is_done_or_wait():
                return frame
            engine.constants['last_time'] = engine.constants['current_time']
            engine.constants['current_time'] += 16
            engine.constants['delta_t'] = 16
            d.update()

    def test_a_shopkeeper_line_takes_half_as_long(self):
        from app.engine import dialog
        from app.engine.general_states import ShopState
        self.start_harness()
        text = 'That is worth 480 gold. Is that acceptable?'
        shop = ShopState.__new__(ShopState)
        shopkeeper = self.frames_to_say(shop.get_dialog(text))
        regular = self.frames_to_say(dialog.Dialog(text))
        self.assertAlmostEqual(regular / 2, shopkeeper, delta=2)


if __name__ == '__main__':
    unittest.main()
