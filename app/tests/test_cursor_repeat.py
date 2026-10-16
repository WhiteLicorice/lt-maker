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


class MoveBorderTests(EngineTestCase):
    '''
    As on the GBA, a held direction does not take the cursor off the edge of where the
    unit can move, however long it is held. Here it went on after a pause
    '''

    def moves(self, pressed_on_frames: set, frames: int = 120) -> list:
        '''
        Holds RIGHT at the right edge of where the unit can move, pressing it anew on
        pressed_on_frames. The frames on which the cursor was let move
        '''
        from app.engine import engine, fluid_scroll, level_cursor
        from app.engine.movement.move_selection import MoveSelection
        cursor = level_cursor.LevelCursor.__new__(level_cursor.LevelCursor)
        cursor.fluid = fluid_scroll.FluidScroll()
        cursor.speed_state = False
        cursor.position = (2, 2)
        cursor.move_selection = MoveSelection(walkable={(1, 2), (2, 2)})
        cursor._handle_move = MagicMock()
        held = MagicMock()
        held.is_pressed.side_effect = lambda button: button == 'RIGHT'
        moved_on = []
        with patch.object(fluid_scroll, 'get_input_manager', return_value=held), \
                patch.object(level_cursor, 'get_input_manager', return_value=held):
            for frame in range(frames):
                engine.constants['current_time'] = 1000 + frame * 1000 // 60
                held.just_pressed.side_effect = lambda button: button == 'RIGHT' and frame in pressed_on_frames
                cursor.take_input()
                if cursor._handle_move.call_args[0][0]:
                    moved_on.append(frame)
        return moved_on

    def test_held_direction_stops_at_the_edge(self):
        self.assertEqual([], self.moves(pressed_on_frames=set()))

    def test_pressing_again_goes_on(self):
        self.assertEqual([0, 60], self.moves(pressed_on_frames={0, 60}))



class CursorGlideTests(EngineTestCase):
    def glide(self, speed: int) -> list:
        '''Where the cursor is drawn, a frame at a time, from the frame it is moved a tile right'''
        from app.engine import engine
        from app.engine.cursor import BaseCursor
        self.addCleanup(engine.constants.__setitem__, 'current_time', engine.constants.get('current_time', 0))
        cursor = BaseCursor()
        cursor._transition_speed = speed
        seen = []
        for frame in range(6):
            # The clock counts whole milliseconds, so frames are 16 or 17 of them apart
            engine.constants['current_time'] = 5000 + frame * 16 + frame * 2 // 3
            if frame == 0:
                cursor.move(1, 0, sound=False)
            cursor.update_offset()
            seen.append(round(cursor.position[0] * 16 - cursor.offset_x))
        return seen

    def test_first_step_on_the_frame_it_is_moved(self):
        '''As on the GBA, 4 pixels a frame from then. Here it began a frame later'''
        self.assertEqual([4, 8, 12, 16, 16, 16], self.glide(1))

    def test_holding_b_8_pixels_a_frame(self):
        self.assertEqual([8, 16, 16, 16, 16, 16], self.glide(2))


if __name__ == '__main__':
    unittest.main()
