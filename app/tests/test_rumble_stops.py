import unittest
from unittest.mock import patch

from app.tests.engine_harness import EngineTestCase
from app.engine import engine, title_screen
from app.engine import config as cf
from app.engine.game_state import game
from app.engine.input_manager import get_input_manager
from app.events.event import Event
from app.events.event_prefab import EventPrefab
from app.events.triggers import GenericTrigger


class FakePad():
    def __init__(self):
        self.calls = []

    def rumble(self, low_frequency, high_frequency, duration):
        self.calls.append(('rumble', duration))
        return True

    def stop_rumble(self):
        self.calls.append('stop')


class RumbleStopsTests(EngineTestCase):
    """
    A `rumble` event command with no duration lasts until `rumble_end`.
    If the event never reaches one, the pad must not keep rumbling
    once the event is over or the player leaves the game
    """
    def setUp(self) -> None:
        super().setUp()
        cf.SETTINGS['rumble'] = 1
        self.input_manager = get_input_manager()
        self.old_pads = self.input_manager.controllers, self.input_manager.joysticks
        self.pad = FakePad()
        self.input_manager.controllers, self.input_manager.joysticks = [self.pad], []

    def tearDown(self) -> None:
        self.input_manager.controllers, self.input_manager.joysticks = self.old_pads
        super().tearDown()

    def run_event(self, script: list[str]):
        prefab = EventPrefab('test_rumble')
        prefab.source = '\n'.join(script)
        event = Event(prefab, GenericTrigger(), game=game)
        while event.state != 'complete':
            event.update()

    def test_endless_rumble_stops_when_its_event_ends(self):
        self.run_event(['rumble;0'])
        self.assertEqual(self.pad.calls, [('rumble', 0), 'stop'])

    def test_endless_rumble_stops_when_its_event_finishes_early(self):
        self.run_event(['rumble;0', 'finish', 'rumble_end'])
        self.assertEqual(self.pad.calls, [('rumble', 0), 'stop'])

    def test_timed_rumble_outlasts_its_event(self):
        self.run_event(['rumble;500'])
        self.assertEqual(self.pad.calls, [('rumble', 500)])

    def test_timed_rumble_replacing_an_endless_one_outlasts_its_event(self):
        self.run_event(['rumble;0', 'rumble;500'])
        self.assertEqual(self.pad.calls, [('rumble', 0), ('rumble', 500)])

    def test_rumble_end_is_not_repeated_when_its_event_ends(self):
        self.run_event(['rumble;0', 'rumble_end'])
        self.assertEqual(self.pad.calls, [('rumble', 0), 'stop'])

    def test_closing_the_game_stops_rumble(self):
        controller, joystick = FakePad(), FakePad()
        with patch.object(engine, 'get_gamepads', return_value=([controller], [joystick])), \
                patch.object(engine, 'on_end'), \
                patch.object(engine.pygame, 'quit'), \
                patch.object(engine.pygame.mixer, 'get_init', return_value=False), \
                patch.dict(engine.constants, {'standalone': False}):
            engine.terminate()
        self.assertEqual(controller.calls, ['stop'])
        self.assertEqual(joystick.calls, ['stop'])

    def test_returning_to_title_stops_rumble(self):
        title_screen.TitleStartState('title_start').start()
        self.assertEqual(self.pad.calls, ['stop'])


if __name__ == '__main__':
    unittest.main()
