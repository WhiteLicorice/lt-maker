import unittest
from unittest.mock import MagicMock

from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options
from app.tests.engine_harness import EngineTestCase


class MenuHandSlideTests(EngineTestCase):
    '''
    On the GBA the menu hand covers half the way left to its item each frame:
    8, 12, 14, 15 of a 16 pixel row. Here it went 4 pixels a frame
    '''

    def setUp(self):
        super().setUp()
        from app.engine import engine
        self.addCleanup(engine.constants.__setitem__, 'current_time', engine.constants.get('current_time', 0))

    def drawn_offsets(self, cursor, frames):
        '''How far from its item the hand is drawn, a frame at a time'''
        from app.engine import engine
        surf = MagicMock()
        offsets = []
        for frame in range(frames):
            engine.constants['current_time'] = 1000 + frame * 17
            cursor.draw(surf, 0, 0)
            offsets.append(surf.blit.call_args[0][1][1] - 3)
        return offsets

    def test_halfway_each_frame(self):
        from app.engine.menus import Cursor
        cursor = Cursor()
        cursor.y_offset_down()
        self.assertEqual([-8, -4, -2, -1, 0, 0], self.drawn_offsets(cursor, 6))
        cursor.y_offset_up()
        self.assertEqual([8, 4, 2, 1, 0, 0], self.drawn_offsets(cursor, 6))

    def test_once_a_frame_however_often_it_is_drawn(self):
        from app.engine import engine
        from app.engine.menus import Cursor
        cursor = Cursor()
        cursor.y_offset_down()
        engine.constants['current_time'] = 5000
        surf = MagicMock()
        cursor.draw(surf, 0, 0)
        cursor.draw(surf, 0, 0)
        self.assertEqual(-8, cursor.y_offset)

    def test_generic_menu_hand_slides_the_same(self):
        from app.engine import engine
        from app.engine.game_menus.menu_components.generic_menu.cursor_hand import CursorHand
        hand = CursorHand()
        hand.y_offset_up()
        seen = []
        for frame in range(5):
            engine.constants['current_time'] = 2000 + frame * 17
            hand.draw(MagicMock(), (0, 0))
            seen.append(hand.y_offset)
        self.assertEqual([8, 4, 2, 1, 0], seen)

    def make_menu(self, count=5, limit=10):
        from app.engine import menus
        menu = menus.Simple.__new__(menus.Simple)
        menu.options = [MagicMock(height=MagicMock(return_value=16)) for _ in range(count)]
        menu.current_index = 0
        menu.scroll = 0
        menu.limit = limit
        menu.cursor = menus.Cursor()
        return menu

    def test_menu_slides_by_how_far_the_rows_are_apart(self):
        menu = self.make_menu()
        menu.move_down()
        self.assertEqual(-16, menu.cursor.y_offset)
        menu.move_up()
        self.assertEqual(16, menu.cursor.y_offset)

    def test_wrapping_around_slides_too(self):
        '''As on the GBA. It used to jump there'''
        menu = self.make_menu()
        menu.move_up()
        self.assertEqual(4, menu.current_index)
        self.assertEqual(-64, menu.cursor.y_offset)
        menu.move_down()
        self.assertEqual(64, menu.cursor.y_offset)

    def test_no_slide_when_the_menu_scrolls_under_it(self):
        menu = self.make_menu(count=10, limit=4)
        for _ in range(3):
            menu.move_down()
        self.assertEqual(1, menu.scroll)
        self.assertEqual(0, menu.cursor.y_offset)


if __name__ == '__main__':
    unittest.main()
