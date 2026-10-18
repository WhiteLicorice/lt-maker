import unittest
from unittest.mock import patch

from app.engine import engine, menus
from app.tests.engine_harness import EngineTestCase


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
            if menu in self.convoy.menus.values():
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


if __name__ == '__main__':
    unittest.main()
