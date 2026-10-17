import unittest

from app.engine import engine, menus
from app.tests.engine_harness import EngineTestCase


class MenuScrollTests(EngineTestCase):
    '''As on the GBA (ShopUpdateBg2Offset, PrepItemList), a scrolled list slides 4 pixels a frame'''

    def setUp(self):
        super().setUp()
        self.harness = self.start_harness()
        self.surf = engine.create_surface((240, 160))

    def frame(self, menu):
        engine.constants['current_time'] += 16
        menu.draw(self.surf)
        return menu.scroll_offset

    def test_a_choice_slides_one_row_over_four_frames(self):
        menu = menus.Choice(None, ['Option %d' % i for i in range(8)], (40, 20))
        menu.set_limit(5)
        self.frame(menu)
        for _ in range(3):
            menu.move_down(True)
            self.assertEqual(0, self.frame(menu))
        menu.move_down(True)
        self.assertEqual(1, menu.scroll)
        self.assertEqual([12, 8, 4, 0], [self.frame(menu) for _ in range(4)])
        menu.move_up(True)
        menu.move_up(True)
        menu.move_up(True)
        self.assertEqual(0, menu.scroll)
        self.assertEqual([-12, -8, -4, 0], [self.frame(menu) for _ in range(4)])

    def test_a_table_slides_one_row_over_four_frames(self):
        menu = menus.Table(None, ['Option %d' % i for i in range(16)], (4, 2), (40, 20))
        self.frame(menu)
        for _ in range(2):
            menu.move_down(True)
            self.assertEqual(0, self.frame(menu))
        menu.move_down(True)
        self.assertEqual(1, menu.scroll)
        self.assertEqual([12, 8, 4, 0], [self.frame(menu) for _ in range(4)])

    def test_wrapping_round_does_not_slide(self):
        menu = menus.Choice(None, ['Option %d' % i for i in range(8)], (40, 20))
        menu.set_limit(5)
        self.frame(menu)
        menu.move_up(True)
        self.assertEqual(3, menu.scroll)
        self.assertEqual(0, self.frame(menu))
        self.assertFalse(menu.is_scrolling())


if __name__ == '__main__':
    unittest.main()
