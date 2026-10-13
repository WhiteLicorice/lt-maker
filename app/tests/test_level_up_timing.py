import itertools
import unittest

from app.tests import engine_harness
from app.tests.engine_harness import EngineTestCase


class LevelUpSteps():
    def level_up(self):
        '''
        Eirika gains a level on the map, at 60 frames a second. Returns how many
        frames each step took, in order, as (step of the exp state, step of the
        level up screen, frames)
        '''
        harness = self.start_harness()
        harness.start_level('0')
        game = harness.game
        harness.run_until(lambda: game.get_unit('Eirika') is not None, 60, 'Eirika loaded')
        unit = game.get_unit('Eirika')
        game.exp_instance.append((unit, 100 - unit.exp, None, 'init'))
        game.state.change('exp')

        self.addCleanup(setattr, engine_harness, 'FRAME_MS', engine_harness.FRAME_MS)
        steps = []
        for frame in range(3000):
            # A frame is 16 or 17 ms on a clock of whole milliseconds
            engine_harness.FRAME_MS = 16 if frame % 3 == 2 else 17
            harness.step()
            if harness.state != 'exp':
                if steps:
                    break
                continue
            exp_state = game.state.state[-1]
            machine = getattr(exp_state, 'state', None)
            step = machine.get_state() if machine and machine.state else None
            screen = getattr(getattr(exp_state, 'level_up_screen', None), 'state', None)
            steps.append((step, screen))
        return [(step, screen, len(list(frames))) for (step, screen), frames in itertools.groupby(steps)]


class LevelUpTimingTests(LevelUpSteps, EngineTestCase):
    # Its level up banner is timed in frames, as the GBA's is
    project = 'default.ltproj'

    def test_banner_plays_for_as_long_as_it_is_drawn_to(self):
        '''
        The banner was advanced twice a frame, once to see whether it was over
        and once more before it was drawn, and was gone in half its time
        '''
        from app.data.resources.resources import RESOURCES
        banner = RESOURCES.animations.get('LevelUpMap')
        self.assertTrue(banner.use_frame_time)
        frames = sum(banner.frame_times)
        steps = self.level_up()
        self.assertEqual([frames], [length for step, _, length in steps if step == 'level_up'])

    def test_stats_go_up_twenty_frames_apart(self):
        '''As on the GBA: the level, then each stat that went up'''
        steps = self.level_up()
        waits = [idx for idx, (_, screen, _) in enumerate(steps) if screen in ('first_spark', 'spark_wait')]
        self.assertGreater(len(waits), 1)
        for idx in waits:
            self.assertEqual('get_next_spark', steps[idx + 1][1])
            self.assertEqual(20, steps[idx][2] + steps[idx + 1][2])

    def test_screen_leaves_as_fast_as_it_comes(self):
        '''It left in 31 frames, most of them after it was off the screen. The GBA's is gone in 9'''
        steps = self.level_up()
        self.assertEqual([10], [length for _, screen, length in steps if screen == 'scroll_in'])
        self.assertEqual([10], [length for _, screen, length in steps if screen == 'scroll_out'])


class MillisecondBannerTests(LevelUpSteps, EngineTestCase):
    # Its level up banner is timed in milliseconds
    project = 'testing_proj.ltproj'

    def test_banner_starts_when_it_is_first_shown(self):
        '''
        The banner was made while the exp bar was still closing, 12 frames before
        it was shown, and one timed in milliseconds was that far in by then
        '''
        from app.data.resources.resources import RESOURCES
        banner = RESOURCES.animations.get('LevelUpMap')
        self.assertFalse(banner.use_frame_time)
        frames = banner.num_frames * banner.speed * 60 / 1000
        steps = self.level_up()
        shown = [length for step, _, length in steps if step == 'level_up']
        self.assertEqual(1, len(shown))
        self.assertAlmostEqual(frames, shown[0], delta=2)


if __name__ == '__main__':
    unittest.main()
