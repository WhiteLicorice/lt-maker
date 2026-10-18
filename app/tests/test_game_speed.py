import unittest

import pygame

from app.data.database.database import DB
from app.engine import config as cf
from app.engine import driver, engine
from app.engine.input_manager import get_input_manager
from app.tests.engine_harness import EngineTestCase

class GameSpeedTests(EngineTestCase):
    '''The SPEED button (Tab, or the right stick on a pad) steps the game through x1 to x4'''

    def press(self, *buttons: str):
        '''Presses and releases buttons together. What the frame's state got as its event'''
        inp = get_input_manager()
        event = inp.process_input([pygame.event.Event(engine.KEYDOWN, key=cf.SETTINGS['key_' + button]) for button in buttons])
        self.speed = driver.update_game_speed(inp, self.speed)
        inp.process_input([pygame.event.Event(engine.KEYUP, key=cf.SETTINGS['key_' + button]) for button in buttons])
        return event

    def setUp(self):
        super().setUp()
        self.speed = 1

    def test_steps_through_x1_to_x4_and_back(self):
        speeds = []
        for _ in range(5):
            self.press('SPEED')
            speeds.append(self.speed)
        self.assertEqual([2, 3, 4, 1, 2], speeds)

    def test_stays_at_x1_if_the_game_does_not_allow_it(self):
        constant = DB.constants.get('speed_up')
        self.addCleanup(setattr, constant, 'value', constant.value)
        constant.value = False
        self.press('SPEED')
        self.assertEqual(1, self.speed)

    def test_never_an_event_for_a_state(self):
        self.assertIsNone(self.press('SPEED'))
        self.assertEqual('SELECT', self.press('SPEED', 'SELECT'))
        self.assertEqual('RIGHT', self.press('RIGHT', 'SPEED'))

class PlanUpdatesTests(unittest.TestCase):
    '''How many updates a frame of real time gets'''

    def run_frames(self, frame_times: list, update_ms: float = 1, game_speed: int = 1) -> list:
        '''The updates each frame ran, for frames that took frame_times of real time'''
        behind = engine.FRAME_MS  # As driver.run starts
        updates = []
        for frame_ms in frame_times:
            num_updates, behind = driver.plan_updates(behind, update_ms, game_speed)
            updates.append(num_updates)
            behind += frame_ms
        return updates

    def test_one_update_a_frame_on_time(self):
        self.assertEqual([1] * 60, self.run_frames([16, 17, 17] * 20))

    def test_catches_up_after_a_slow_frame(self):
        self.assertEqual([1, 1, 2, 1, 1], self.run_frames([17, 34, 17, 17, 17]))

    def test_catches_up_at_most_one_frame(self):
        # A long hitch is dropped rather than run as a burst of updates
        self.assertEqual([1, 1, 2, 2, 1, 1], self.run_frames([17, 500, 17, 17, 17, 17]))

    def test_no_catching_up_if_two_updates_do_not_fit_a_frame(self):
        self.assertEqual([1, 1, 1, 1], self.run_frames([17, 34, 34, 34], update_ms=10))

    def test_sped_up_runs_that_many_updates_and_never_catches_up(self):
        self.assertEqual([4, 4, 4], self.run_frames([17, 100, 17], update_ms=30, game_speed=4))

if __name__ == '__main__':
    unittest.main()
