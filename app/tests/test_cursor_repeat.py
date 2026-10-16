import unittest
from unittest.mock import MagicMock, patch

from app.tests.engine_harness import EngineTestCase


class CursorRepeatTests(EngineTestCase):
    def test_held_direction_repeats_as_on_the_gba(self):
        '''
        The GBA games move the cursor on the frame a direction is pressed, again
        12 frames later if it is still held, and every 4 frames after that
        '''
        from app.engine import engine, fluid_scroll
        from app.engine.cursor import BaseCursor

        held = MagicMock()
        held.is_pressed.side_effect = lambda button: button == 'RIGHT'
        # The map cursor's, and the one a menu gets when it asks for nothing else
        for fluid in (BaseCursor().fluid, fluid_scroll.FluidScroll()):
            # The clock counts whole milliseconds, so a frame is 16 or 17 of them
            for frame_ms in (16, 1000 / 60, 17):
                fluid.reset_on_change_state()
                moved_on = []
                with patch.object(fluid_scroll, 'get_input_manager', return_value=held):
                    for frame in range(30):
                        engine.constants['current_time'] = 1000 + int(frame * frame_ms)
                        held.just_pressed.side_effect = lambda button: button == 'RIGHT' and frame == 0
                        fluid.update()
                        if fluid.get_directions():
                            moved_on.append(frame)
                self.assertEqual([0, 12, 16, 20, 24, 28], moved_on, frame_ms)

    def test_holding_b_moves_every_2_frames_from_the_first(self):
        '''On the GBA there is no wait before the second move. Here it was 6 frames'''
        from app.engine import engine, fluid_scroll

        held = MagicMock()
        held.is_pressed.side_effect = lambda button: button == 'RIGHT'
        fluid = fluid_scroll.FluidScroll()
        for frame_ms in (16, 1000 / 60, 17):
            fluid.reset_on_change_state()
            moved_on = []
            with patch.object(fluid_scroll, 'get_input_manager', return_value=held):
                for frame in range(12):
                    engine.constants['current_time'] = 1000 + int(frame * frame_ms)
                    held.just_pressed.side_effect = lambda button: button == 'RIGHT' and frame == 0
                    fluid.update()
                    if fluid.get_directions(double_speed=True):
                        moved_on.append(frame)
            self.assertEqual([0, 2, 4, 6, 8, 10], moved_on, frame_ms)


if __name__ == '__main__':
    unittest.main()
