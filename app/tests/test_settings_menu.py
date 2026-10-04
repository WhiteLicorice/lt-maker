import unittest

from app.tests.engine_harness import EngineTestCase


class SettingsMenuTests(EngineTestCase):
    def setUp(self) -> None:
        # Importing settings reads sprites at module level, which EngineTestCase loads
        super().setUp()
        from app.engine import config as cf, settings, settings_menu
        self.cf = cf
        config_options = [(c[0], c[1]) for c in settings.config]
        self.menu = settings_menu.Config(None, config_options, 'menu_bg_base', settings.config_icons)
        self.menu.move_to([c[0] for c in settings.config].index('sound_volume'))

    def test_move_reports_whether_the_value_changed(self):
        '''
        The settings menu only plays its scroll sound when these report a change.
        They used to return None, so nothing beeped when adjusting an option
        '''
        self.cf.SETTINGS['sound_volume'] = 0
        self.assertTrue(self.menu.move_right())
        self.assertTrue(self.menu.move_left())
        # Already at the ends of the slider, so nothing changes
        self.assertFalse(self.menu.move_left())
        self.cf.SETTINGS['sound_volume'] = 1
        self.assertFalse(self.menu.move_right())


class FakePad():
    def __init__(self):
        self.calls = []

    def rumble(self, low_frequency, high_frequency, duration):
        self.calls.append('rumble')
        return True

    def stop_rumble(self):
        self.calls.append('stop')


class RumbleOptionTests(EngineTestCase):
    def setUp(self) -> None:
        super().setUp()
        from app.engine import config as cf, settings, settings_menu
        from app.engine.input_manager import get_input_manager
        self.cf = cf
        self.input_manager = get_input_manager()
        self.old_pads = self.input_manager.controllers, self.input_manager.joysticks
        self.pad = FakePad()
        self.input_manager.controllers, self.input_manager.joysticks = [self.pad], []

        self.state = settings.SettingsMenuState('settings_menu')
        self.state.tab = 'config'
        self.state.keyboard_menu = self.state.controller_menu = None
        config_options = [(c[0], c[1]) for c in settings.config]
        self.state.config_menu = settings_menu.Config(None, config_options, 'menu_bg_base', settings.config_icons)
        self.state.config_menu.move_to([c[0] for c in settings.config].index('rumble'))

    def tearDown(self) -> None:
        self.input_manager.controllers, self.input_manager.joysticks = self.old_pads
        super().tearDown()

    def toggle(self, move: str):
        if getattr(self.state.config_menu, move)():
            self.state.apply_option_change()

    def test_turning_rumble_off_stops_it_and_on_starts_it(self):
        self.cf.SETTINGS['rumble'] = 1
        self.toggle('move_next')
        self.assertEqual(self.cf.SETTINGS['rumble'], 0)
        self.assertEqual(self.pad.calls, ['stop'])
        self.toggle('move_next')
        self.assertEqual(self.cf.SETTINGS['rumble'], 1)
        self.assertEqual(self.pad.calls, ['stop', 'rumble'])

    def test_no_rumble_when_value_does_not_change(self):
        self.cf.SETTINGS['rumble'] = 1
        self.toggle('move_left')  # Already on
        self.assertEqual(self.pad.calls, [])

    def test_rumble_does_nothing_when_off(self):
        self.cf.SETTINGS['rumble'] = 0
        self.input_manager.rumble(0.5, 0.5, 250)
        self.assertEqual(self.pad.calls, [])


if __name__ == '__main__':
    unittest.main()
