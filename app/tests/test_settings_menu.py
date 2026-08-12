import unittest


class SettingsMenuTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.engine import sprites
        # An earlier test may have reset the sprite dict without reloading the
        # images, and importing settings reads sprites at module level
        sprites.load_images()
        from app.engine import config as cf, settings, settings_menu
        self.cf = cf
        self.old_value = cf.SETTINGS['sound_volume']
        config_options = [(c[0], c[1]) for c in settings.config]
        self.menu = settings_menu.Config(None, config_options, 'menu_bg_base', settings.config_icons)
        self.menu.move_to([c[0] for c in settings.config].index('sound_volume'))

    def tearDown(self) -> None:
        self.cf.SETTINGS['sound_volume'] = self.old_value

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


if __name__ == '__main__':
    unittest.main()
