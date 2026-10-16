import unittest
from unittest.mock import MagicMock, patch

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


class RangeSquareOpeningTests(EngineTestCase):
    def test_squares_grow_out_of_their_bottom_left_corner(self):
        '''
        As on the GBA, 5, 7, 9, 11, 13 and 15 pixels over 6 frames, then whole.
        Here they grew from 10 to 16 pixels out of the top left
        '''
        from app.engine.highlight import HighlightController
        harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        highlight = HighlightController()
        highlight.add_highlights({(2, 3)}, 'move')
        seen = []
        for _ in range(8):
            surf = MagicMock()
            with patch('app.engine.highlight.game') as game:
                game.level.regions = []
                highlight.draw(surf, (0, 0))
            image, pos = surf.blit.call_args[0]
            seen.append((image.get_width(), image.get_height(), pos))
        sizes = [5, 7, 9, 11, 13, 15, 16, 16]
        self.assertEqual([(size, size, (32, 48 + 16 - size)) for size in sizes], seen)


class UnitWalkTests(EngineTestCase):
    def test_a_tile_in_8_frames_2_pixels_a_frame(self):
        '''As on the GBA. Here it was 120 ms, and its steps came out 2 or 3 pixels'''
        from app.engine import config as cf
        from app.engine.movement.unit_path_movement_component import UnitPathMovementComponent
        from app.engine import engine
        self.assertEqual(133, cf.base_config()['unit_speed'])
        harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        eirika = harness.game.get_unit('Eirika')
        self.addCleanup(engine.constants.__setitem__, 'current_time', engine.constants.get('current_time', 0))
        start = engine.constants['current_time'] = 50000
        x, y = eirika.position
        mover = UnitPathMovementComponent(eirika, [(x, y - 1), (x, y)], speed=133)
        mover._last_update = start
        seen = []
        for frame in range(1, 9):
            # The clock counts whole milliseconds, so frames are 16 or 17 of them apart
            engine.constants['current_time'] = start + frame * 16 + frame * 2 // 3
            with patch.object(mover, '_handle_path'):
                mover.update(engine.get_time())
            seen.append(eirika.sprite.offset[1] if frame < 8 else 'there')
        self.assertEqual([-2, -4, -6, -8, -10, -12, -14, 'there'], seen)

    def test_settings_offer_whole_frames(self):
        from app.engine import settings
        speeds = dict((name, values) for name, values, _ in settings.config)['unit_speed']
        self.assertIn(133, speeds)
        self.assertIn(66, speeds)  # The GBA's fast game speed


class StepSoundTests(unittest.TestCase):
    def steps(self, tag: str, frames: int) -> list:
        from app.engine import unit_sound
        unit = MagicMock()
        unit.tags = [tag]
        sound = unit_sound.UnitSound(unit)
        played = []
        with patch.object(unit_sound, 'get_sound_thread') as thread:
            thread.return_value.play_sfx.side_effect = lambda name, volume=1: played.append((frame, name))
            sound.play()
            for frame in range(frames):
                sound.update()
        return played

    def test_cycles_as_long_as_the_gbas(self):
        '''They took a frame more each time round: infantry stepped 8 and then 9 frames apart'''
        self.assertEqual([0, 8, 16, 24, 32], [frame for frame, _ in self.steps('Infantry', 40)])
        self.assertEqual([0, 3, 10, 21, 24, 31], [frame for frame, _ in self.steps('Mounted', 32)])
        self.assertEqual([0, 16, 32], [frame for frame, _ in self.steps('Armor', 40)])
        self.assertEqual([0, 20, 40], [frame for frame, _ in self.steps('Flying', 41)])
        self.assertEqual([0, 20, 40], [frame for frame, _ in self.steps('Mogall', 41)])


if __name__ == '__main__':
    unittest.main()
