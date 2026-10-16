import itertools
import unittest
from unittest.mock import MagicMock, patch

from app.tests.engine_harness import EngineTestCase


def frame_time(start: int, frame: int) -> int:
    '''The clock on that frame at 60 frames a second, a clock of whole milliseconds'''
    return start + frame * 1000 // 60


class PortraitTestCase(EngineTestCase):
    start = 100000

    def setUp(self):
        super().setUp()
        from app.engine import engine
        self.addCleanup(engine.constants.__setitem__, 'current_time', engine.constants.get('current_time', 0))
        self.set_frame(0)

    def set_frame(self, frame: int):
        from app.engine import engine
        engine.constants['current_time'] = frame_time(self.start, frame)

    def make_portrait(self, position=(0, 0), **kwargs):
        from app.data.resources.resources import RESOURCES
        from app.events.event_portrait import EventPortrait
        prefab = next(p for p in RESOURCES.portraits if p.blink_frames == 2)
        return EventPortrait(prefab, position, 0, **kwargs)

    def run_frames(self, portrait, frames: int, read):
        '''Updates the portrait a frame at a time, from frame 1. Returns what read gives each frame'''
        rows = []
        for frame in range(1, frames + 1):
            self.set_frame(frame)
            portrait.update()
            rows.append(read(portrait))
        return rows


class PortraitMoveTests(PortraitTestCase):
    '''
    On the GBA a face moves in 16 frames, or 32 if it has more than 24 pixels to
    go, fast at first and slowing to a stop, and sinks a pixel on the way.
    Here it was an approximation of that
    '''

    def move(self, distance: int, speed_mult=1):
        portrait = self.make_portrait()
        portrait.move((distance, 0), speed_mult)
        rows = [(portrait.position[0], portrait.move_dip)]
        rows += self.run_frames(portrait, 40, lambda p: (p.position[0], p.move_dip))
        return portrait, rows

    def test_long_move(self):
        from app.utilities import utils
        portrait, rows = self.move(96)
        self.assertEqual(utils.frames2ms(32), portrait.travel_time)
        xs = [x for x, _ in rows]
        # Frame 0 is where it was, and it is there by the last of its 32 frames
        self.assertEqual(0, xs[0])
        self.assertEqual(96, xs[31])
        self.assertEqual({96}, set(xs[31:]))
        # 96 - 31 * 31 * 96 // 1024, and halfway there by a quarter of the time
        self.assertEqual(6, xs[1])
        self.assertEqual(72, xs[16])
        steps = [b - a for a, b in zip(xs, xs[1:32])]
        self.assertTrue(all(step >= 0 for step in steps))
        self.assertGreater(steps[0], steps[-1])
        # Down a pixel from frame 4 to 15 and from frame 20 to the end
        dips = [dip for _, dip in rows]
        expected = [1 if 4 <= frame < 16 or 20 <= frame < 32 else 0 for frame in range(len(dips))]
        self.assertEqual(expected, dips)
        self.assertFalse(portrait.moving)

    def test_short_move(self):
        portrait, rows = self.move(24)
        xs = [x for x, _ in rows]
        self.assertEqual(0, xs[0])
        self.assertEqual(24, xs[15])
        # 24 - 4 * 4 * 24 // 256: the last frames round to where it is going
        self.assertEqual(23, xs[12])
        self.assertEqual(24, xs[13])
        # Down a pixel for its second half
        dips = [dip for _, dip in rows]
        self.assertEqual([1 if 8 <= frame < 16 else 0 for frame in range(len(dips))], dips)

    def test_moves_to_the_left_too(self):
        portrait = self.make_portrait(position=(120, 0))
        portrait.move((24, 0))
        xs = self.run_frames(portrait, 40, lambda p: p.position[0])
        self.assertEqual(24, xs[-1])
        self.assertTrue(all(b <= a for a, b in zip(xs, xs[1:])))

    def test_speed_mult_shortens_it(self):
        from app.utilities import utils
        portrait, rows = self.move(96, speed_mult=2)
        self.assertEqual(utils.frames2ms(16), portrait.travel_time)
        self.assertEqual(96, rows[15][0])


class PortraitFadeTests(PortraitTestCase):
    def test_fades_in_over_12_frames(self):
        portrait = self.make_portrait(transition=True)
        shown = self.run_frames(portrait, 20, lambda p: p.transition)
        # On the GBA a face fades in from black over 12 frames. Here it took 14
        self.assertEqual(12, sum(shown))

    def test_fades_out_as_it_did(self):
        portrait = self.make_portrait()
        portrait.end()
        done = self.run_frames(portrait, 20, lambda p: p.transition)
        self.assertEqual(14, sum(done))


class AddPortraitTests(PortraitTestCase):
    '''On the GBA a scene waits 8 frames for a face to appear before going on, though it is still fading in'''

    def frames_waited(self, speed_mult=1.0, flags=None):
        from app.data.resources.resources import RESOURCES
        from app.events import event_functions
        prefab = next(p for p in RESOURCES.portraits if p.blink_frames == 2)
        event = MagicMock(portraits={}, priority_counter=0, do_skip=False, wait_time=0, state='processing')
        event._get_portrait.return_value = (prefab, prefab.nid)
        self.assertTrue(event_functions.add_portrait(event, prefab.nid, (0, 0), speed_mult=speed_mult, flags=flags))
        if event.state != 'waiting':
            return 0
        frame = 0
        while True:
            frame += 1
            self.set_frame(frame)
            # As Event.update checks it
            if frame_time(self.start, frame) > event.wait_time:
                return frame

    def test_waits_8_frames(self):
        self.assertEqual(8, self.frames_waited())

    def test_speed_mult_shortens_it(self):
        self.assertEqual(4, self.frames_waited(speed_mult=2))

    def test_no_block_does_not_wait(self):
        self.assertEqual(0, self.frames_waited(flags={'no_block'}))


class PortraitBlinkTests(PortraitTestCase):
    def eyes(self, portrait):
        counter = portrait.blink_counter
        return 'open' if counter.is_open_eyes() else 'shut' if counter.get_blink_index() == 0 else 'half'

    def blinks(self, make, update, read):
        '''Steps of open, half shut and shut eyes over 200 frames, with waits of 50, 40, then 1000 frames'''
        from app import counters
        from app.utilities import utils
        waits = iter([utils.frames2ms(n - 0.5) for n in (50, 40, 1000)])
        with patch.object(counters, 'blink_wait', lambda: next(waits)):
            portrait = make()
            rows = []
            for frame in range(1, 201):
                self.set_frame(frame)
                update(portrait)
                rows.append(read(portrait))
        return [(eyes, len(list(frames))) for eyes, frames in itertools.groupby(rows)]

    # Open for its first wait, then half shut, shut, half shut for 3 frames
    # each, then open for the next wait, which was drawn again
    gba_blinks = [('open', 49), ('half', 3), ('shut', 3), ('half', 3), ('open', 40),
                  ('half', 3), ('shut', 3), ('half', 3)]

    def test_blink_is_three_frames_a_step(self):
        steps = self.blinks(self.make_portrait, lambda p: p.update(), self.eyes)
        self.assertEqual(self.gba_blinks, steps[:8])

    def test_info_menu_portrait_blinks_the_same(self):
        from app.data.resources.resources import RESOURCES
        from app.engine.info_menu.info_menu_portrait import InfoMenuPortrait
        prefab = next(p for p in RESOURCES.portraits if p.blink_frames == 2)
        steps = self.blinks(lambda: InfoMenuPortrait(prefab, should_blink=True), lambda p: p.update(), self.eyes)
        self.assertEqual(self.gba_blinks, steps[:8])

    def test_waits_are_those_of_the_gba(self):
        from app import counters
        from app.utilities import utils
        with patch.object(counters.random, 'randint', side_effect=[30, 541]) as randint:
            self.assertEqual(utils.frames2ms(32.5), counters.blink_wait())
            self.assertEqual(utils.frames2ms(543.5), counters.blink_wait())
        randint.assert_called_with(30, 541)

    def test_does_not_blink_as_it_appears(self):
        portrait = self.make_portrait(transition=True)
        rows = self.run_frames(portrait, 29, self.eyes)
        self.assertEqual({'open'}, set(rows))


class MouthTests(PortraitTestCase):
    def test_mouth_opens_and_shuts_a_frame_at_a_time(self):
        from app.events.event_portrait import update_talk
        state, reverse, seen = 0, False, []
        for _ in range(9):
            state, _, reverse = update_talk(state, 3, reverse)
            seen.append(state)
        self.assertEqual([1, 2, 1, 0, 1, 2, 1, 0, 1], seen)

    def test_each_frame_is_held_one_to_eight_frames(self):
        from app.events import event_portrait
        holds = [1, 8, 3, 5, 2]
        portrait = self.make_portrait()
        with patch.object(event_portrait.random, 'randint', side_effect=holds + [1] * 50) as randint:
            portrait.start_talking()
            rows = self.run_frames(portrait, 30, lambda p: p.talk_state)
        randint.assert_called_with(1, 8)
        steps = [(state, len(list(frames))) for state, frames in itertools.groupby(rows)]
        self.assertEqual([(1, 1), (2, 8), (1, 3), (0, 5), (1, 2)], steps[:5])

    def test_shut_once_done_talking(self):
        portrait = self.make_portrait()
        portrait.start_talking()
        self.run_frames(portrait, 10, lambda p: p.talk_state)
        portrait.stop_talking()
        self.assertEqual([0], self.run_frames(portrait, 1, lambda p: p.talk_state))


class LineScrollTests(EngineTestCase):
    def test_lines_move_up_a_pixel_a_frame(self):
        from app.engine import dialog, fonts
        fonts.load_fonts(headless=True)
        with patch.object(dialog.engine, 'create_surface', new=MagicMock()), \
                patch.object(dialog, 'create_base_surf', new=MagicMock()):
            box = dialog.Dialog('One line.', speaker='Narrator')
        box.state = dialog.DialogState.NEW_LINE
        box.y_offset = 16
        frames = 0
        while box.state == dialog.DialogState.NEW_LINE:
            box.update()
            frames += 1
            self.assertLess(frames, 40)
        # 16 frames for a line of 16 pixels, as on the GBA. Here it took 8
        self.assertEqual(16, frames)


if __name__ == '__main__':
    unittest.main()
