import unittest
from unittest.mock import patch

from app.engine import action, engine, menus
from app.engine.sound import get_sound_thread
from app.tests.engine_harness import EngineTestCase


class PrepPickUnitsSoundTests(EngineTestCase):
    '''
    The sounds of Pick Units, as on the GBA (PrepUnit_HandlePressA, ProcPrepUnit_Idle).
    testing_proj has no prep screen, so Pick Units is entered by hand over the Prologue,
    with a formation region round Eirika (4, 5) and Seth (4, 4)
    '''

    def setUp(self):
        super().setUp()
        from app.engine.objects.region import RegionObject
        from app.events.regions import RegionType
        self.harness = self.start_harness()
        self.harness.start_level('0')
        self.harness.run_until_state('free')
        self.game = self.harness.game
        action.AddRegion(RegionObject('formation_test', RegionType.FORMATION, (3, 3), (3, 3))).do()
        self.played = []
        sfx = patch.object(type(get_sound_thread()), 'play_sfx', lambda s, sound, *a, **k: self.played.append(sound))
        sfx.start()
        self.addCleanup(sfx.stop)
        self.game.state.change('prep_pick_units')
        self.harness.run_until_state('prep_pick_units')
        self.state = self.game.state.current_state()
        # It fades in first
        self.harness.run_until(lambda: hasattr(self.state, 'menu'), 60, 'Pick Units started')
        self.harness.run_until_state('prep_pick_units')

    def press(self, button):
        self.played.clear()
        self.harness.press(button)
        return list(self.played)

    def unit_at_hand(self):
        return self.state.menu.get_current()

    def test_sending_a_unit_back_is_the_cancel_sound_and_picking_it_the_select_sound(self):
        unit = self.unit_at_hand()
        self.assertTrue(unit.position)
        self.assertEqual(['Select 4'], self.press('SELECT'))
        self.assertIsNone(unit.position)
        self.assertEqual(['Select 1'], self.press('SELECT'))
        self.assertTrue(unit.position)

    def test_picking_a_unit_when_every_slot_is_taken_is_the_miss_sound(self):
        unit = self.unit_at_hand()
        self.press('SELECT')
        on_map = [u for u in self.game.get_units_in_party() if u.position]
        self.game.level_vars['_prep_slots'] = len(on_map)
        self.assertEqual(['Error'], self.press('SELECT'))
        self.assertIsNone(unit.position)

    def test_a_unit_outside_the_formation_is_the_miss_sound(self):
        unit = self.unit_at_hand()
        action.do(action.Teleport(unit, (0, 0)))
        self.assertEqual(['Error'], self.press('SELECT'))
        self.assertEqual((0, 0), unit.position)

    def test_the_grid_does_not_wrap_at_its_edges(self):
        self.assertFalse(self.state.menu.wrap_rows)

    def test_the_hand_is_silent_when_it_cannot_move(self):
        self.state.menu.move_to(0)
        self.assertEqual([], self.press('LEFT'))
        self.assertEqual(['Select 5'], self.press('RIGHT'))


class UnitGridEdgeTests(unittest.TestCase):
    '''As on the GBA (PrepItemScreen_DpadKeyHandler, ProcPrepUnit_Idle), a unit grid's hand stops at its edges'''

    def grid(self, wrap_rows):
        menu = menus.Table(None, ['Unit %d' % i for i in range(7)], (4, 3), (6, 0))
        menu.wrap_rows = wrap_rows
        return menu

    def test_right_stops_at_the_end_of_a_row(self):
        menu = self.grid(False)
        menu.move_to(2)
        self.assertFalse(menu.move_right())
        self.assertEqual(2, menu.current_index)
        # The last row is short: the hand stops at its last unit
        menu.move_to(6)
        self.assertFalse(menu.move_right())
        self.assertEqual(6, menu.current_index)

    def test_left_stops_at_the_start_of_a_row(self):
        menu = self.grid(False)
        menu.move_to(3)
        self.assertFalse(menu.move_left())
        self.assertEqual(3, menu.current_index)
        menu.move_to(0)
        self.assertFalse(menu.move_left())
        self.assertEqual(0, menu.current_index)

    def test_within_a_row_the_hand_still_moves(self):
        menu = self.grid(False)
        menu.move_to(4)
        self.assertTrue(menu.move_right())
        self.assertEqual(5, menu.current_index)
        self.assertTrue(menu.move_left())
        self.assertEqual(4, menu.current_index)

    def test_other_tables_still_go_round_to_the_next_row(self):
        menu = self.grid(True)
        menu.move_to(2)
        self.assertTrue(menu.move_right())
        self.assertEqual(3, menu.current_index)
        self.assertTrue(menu.move_left())
        self.assertEqual(2, menu.current_index)


class ConvoyPageSlideTests(EngineTestCase):
    '''As on the GBA (PrepItemSupply_SwitchPageLeft/Right), a new page of the convoy slides in'''

    def setUp(self):
        super().setUp()
        self.harness = self.start_harness()
        self.harness.start_level('0')
        self.harness.run_until_state('free')
        self.unit = self.harness.game.get_unit('Eirika')
        self.convoy = menus.Convoy(self.unit, (124, 40))
        self.surf = engine.create_surface((240, 160))
        self.drawn = []
        real_draw = menus.Choice.draw

        def draw(menu, surf):
            if menu in self.convoy.menus.values() or menu.disp_value:
                self.drawn.append((menu, menu.rows_x_offset))
            return real_draw(menu, surf)
        p = patch.object(menus.Choice, 'draw', draw)
        p.start()
        self.addCleanup(p.stop)

    def frames(self, count):
        out = []
        for _ in range(count):
            engine.constants['current_time'] += 16
            self.drawn.clear()
            self.convoy.draw(self.surf)
            out.append(self.drawn[0])
        return out

    def test_the_next_page_slides_in_from_the_right(self):
        self.convoy.move_right()  # From the unit's items onto the first page: no slide
        self.assertFalse(self.convoy.is_sliding())
        first = self.convoy.get_menu()
        self.convoy.move_right()
        second = self.convoy.get_menu()
        self.assertTrue(self.convoy.is_sliding())
        self.assertEqual([(first, -42), (first, -72), (first, -90),
                          (second, 96), (second, 54), (second, 24), (second, 6), (second, 0)],
                         self.frames(8))
        self.assertFalse(self.convoy.is_sliding())

    def test_the_page_before_slides_in_from_the_left(self):
        self.convoy.move_right()
        self.convoy.move_right()
        self.frames(8)
        second = self.convoy.get_menu()
        self.convoy.move_left()
        first = self.convoy.get_menu()
        self.assertEqual([(second, 42), (second, 72), (second, 90),
                          (first, -96), (first, -54), (first, -24), (first, -6), (first, 0)],
                         self.frames(8))

    def test_the_market_pages_slide_too(self):
        self.convoy = menus.Market(self.unit, None, (76, 40), disp_value='sell')
        first = self.convoy.get_menu()
        self.convoy.move_right()
        second = self.convoy.get_menu()
        self.assertTrue(self.convoy.is_sliding())
        self.assertEqual([(first, -42), (first, -72), (first, -90),
                          (second, 96), (second, 54), (second, 24), (second, 6), (second, 0)],
                         self.frames(8))


if __name__ == '__main__':
    unittest.main()
