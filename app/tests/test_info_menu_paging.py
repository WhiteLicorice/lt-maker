import unittest

from app.engine import engine
from app.tests.engine_harness import EngineTestCase

# testing_proj level 0: Eirika starts on (4, 5)
LEVEL = '0'

class InfoMenuPagingTests(EngineTestCase):
    '''
    In FE8 (StatScreen_OnIdle) a held direction turns the page by the usual key
    repeat: on the press, 12 frames later, then every 4. The 13 frame page turn
    blocks input and swallows the repeats that land during it, so the next turn
    starts on frame 16: 3 still frames after each turn. Here the info menu
    repeated every 200 ms, so pages turned one straight after another
    '''

    def setUp(self):
        super().setUp()
        self.harness = self.start_harness()
        self.harness.start_level(LEVEL)
        self.harness.run_until_state('free')
        self.harness.move_cursor_to((4, 5))
        self.harness.press('INFO')
        self.harness.run_until_state('info_menu')

    def turns_started_holding(self, button: str, frames: int) -> list:
        '''The frames, counted from the press, on which a page began to turn'''
        harness = self.harness
        menu = harness.game.state.current_state()
        started_on = []
        turning = False
        for frame in range(frames):
            events = [harness._key_event(engine.KEYDOWN, button)] if frame == 0 else None
            harness.step(events=events)
            if menu.next_state is not None and not turning:
                started_on.append(frame)
            turning = menu.next_state is not None
        harness.step(events=[harness._key_event(engine.KEYUP, button)])
        return started_on

    def test_held_right_turns_a_page_every_16_frames(self):
        self.assertEqual([0, 16, 32, 48], self.turns_started_holding('RIGHT', 60))

    def test_held_left_too(self):
        self.assertEqual([0, 16, 32, 48], self.turns_started_holding('LEFT', 60))

if __name__ == '__main__':
    unittest.main()
