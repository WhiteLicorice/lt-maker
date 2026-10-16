import unittest

from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options
from app.tests import engine_harness
from app.tests.engine_harness import EngineTestCase


class SideWindowTests(EngineTestCase):
    '''
    The unit, terrain and goal windows on the map, as on the GBA: they slide in and out
    a tile at a time, and change sides by sliding out and in again
    '''

    def setUp(self):
        super().setUp()
        self.harness = self.start_harness()
        self.harness.start_level('0')
        self.harness.run_until_state('free')
        self.ui = self.harness.game.ui_view
        self.addCleanup(setattr, engine_harness, 'FRAME_MS', engine_harness.FRAME_MS)

    def frames(self, count: int) -> list:
        '''How much of each window shows, a frame at a time: (unit, terrain, goal)'''
        seen = []
        for frame in range(count):
            engine_harness.FRAME_MS = 16 if frame % 3 == 2 else 17
            self.harness.step()
            seen.append((self.ui.unit_slide.shown, self.ui.tile_slide.shown, self.ui.obj_slide.shown))
        return seen

    def test_middle_column_counts_as_the_left(self):
        game = self.harness.game
        middle = int(game.camera.get_x()) + 7
        game.cursor.set_pos((middle, 5))
        self.assertFalse(self.ui.get_cursor_right())
        game.cursor.set_pos((middle + 1, 5))
        self.assertTrue(self.ui.get_cursor_right())

    def put_away_and_back(self) -> list:
        '''Picks Eirika up and puts her down again. How much of each window shows from then'''
        from app.engine import engine
        self.harness.select_unit('Eirika')
        self.harness.step(5)
        seen = []
        for kind in (engine.KEYDOWN, engine.KEYUP):
            self.harness.step(events=[self.harness._key_event(kind, 'BACK')])
            seen.append((self.ui.unit_slide.shown, self.ui.tile_slide.shown, self.ui.obj_slide.shown))
        return seen + self.frames(8)

    def test_windows_slide_in_a_tile_at_a_time(self):
        from app.engine import ui_view
        seen = self.put_away_and_back()
        for idx, table in enumerate((ui_view.UNIT_WINDOW_IN, ui_view.TERRAIN_WINDOW_IN, ui_view.GOAL_WINDOW_IN)):
            shown = [row[idx] for row in seen]
            start = next(i for i, value in enumerate(shown) if value)
            self.assertEqual(list(table) + [1], shown[start:start + len(table) + 1])

    def test_off_a_unit_the_unit_window_slides_out(self):
        from app.engine import ui_view
        eirika = self.harness.game.get_unit('Eirika')
        self.harness.move_cursor_to(eirika.position)
        self.harness.step(10)
        empty = next((x, eirika.position[1]) for x in range(eirika.position[0] + 1, 15)
                     if not self.harness.game.board.get_unit((x, eirika.position[1])))
        self.harness.game.cursor.set_pos(empty)
        seen = self.frames(4)
        self.assertEqual(list(ui_view.UNIT_WINDOW_OUT) + [0], [unit for unit, _, _ in seen])

    def test_terrain_window_changes_sides_by_sliding_out_and_in(self):
        from app.engine import ui_view
        game = self.harness.game
        game.cursor.set_pos((int(game.camera.get_x()) + 2, 6))
        self.harness.step(10)
        self.assertFalse(self.ui.tile_info_left)
        game.cursor.set_pos((int(game.camera.get_x()) + 12, 6))
        seen = self.frames(7)
        self.assertEqual(list(ui_view.TERRAIN_WINDOW_OUT) + list(ui_view.TERRAIN_WINDOW_IN) + [1],
                         [tile for _, tile, _ in seen])
        self.assertTrue(self.ui.tile_info_left)

    def test_gone_at_once_when_the_cursor_is_put_away(self):
        '''Picking a unit up, as on the GBA'''
        self.harness.move_cursor_to(self.harness.game.get_unit('Eirika').position)
        self.harness.step(10)
        self.harness.press('SELECT', settle=0)
        self.assertEqual([('hidden', 0)] * 3, [(slide.state, slide.shown) for slide in
                                                (self.ui.unit_slide, self.ui.tile_slide, self.ui.obj_slide)])


if __name__ == '__main__':
    unittest.main()
