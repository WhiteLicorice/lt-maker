import unittest

from app.tests.engine_harness import EngineTestCase


class SlowMoveTests(EngineTestCase):
    def test_new_project_has_the_tag(self):
        from app.data.database.tags import TagCatalog
        self.assertIn('SlowMove', TagCatalog().keys())

    def test_tagged_unit_takes_twice_as_long_to_cross_a_tile(self):
        '''
        On the GBA the armored and the robed classes walk at half the pace of
        the rest. In testing_proj Seth is a Paladin and Eirika a Lord
        '''
        from app.data.database.database import DB
        from app.engine import action
        from app.engine import config as cf
        harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        seth, eirika = harness.game.get_unit('Seth'), harness.game.get_unit('Eirika')
        DB.classes.get(seth.klass).tags.append('SlowMove')
        self.assertIn('SlowMove', seth.tags)

        unit_speed = cf.SETTINGS['unit_speed']
        self.assertEqual(unit_speed * 2, action.Move(seth, (5, 4)).speed)
        self.assertEqual(unit_speed, action.Move(eirika, (5, 5)).speed)

    def test_speed_that_is_asked_for_is_kept(self):
        '''An event that moves a unit at a speed of its own, or the AI skipping ahead'''
        from app.data.database.database import DB
        from app.engine import action
        harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        seth = harness.game.get_unit('Seth')
        DB.classes.get(seth.klass).tags.append('SlowMove')
        self.assertEqual(10, action.Move(seth, (5, 4), speed=10).speed)

    def test_tagged_unit_is_seen_to_walk_at_half_the_pace(self):
        from app.data.database.database import DB
        harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        game = harness.game
        seth = game.get_unit('Seth')

        def frames_to_walk_to(pos):
            harness.select_unit('Seth')
            harness.move_cursor_to(pos)
            harness.press('SELECT', settle=0)
            frames = 0
            while harness.state != 'menu' or game.state.temp_state:
                harness.step()
                frames += 1
                self.assertLess(frames, 600)
            self.assertEqual(pos, seth.position)
            # Back to where he started
            harness.press('BACK')
            harness.run_until_state('move')
            harness.press('BACK')
            harness.run_until_state('free')
            return frames

        start = seth.position
        usual = frames_to_walk_to((8, 5))
        self.assertEqual(start, seth.position)
        DB.classes.get(seth.klass).tags.append('SlowMove')
        slow = frames_to_walk_to((8, 5))
        self.assertGreater(usual, 20)
        self.assertAlmostEqual(usual * 2, slow, delta=6)


if __name__ == '__main__':
    unittest.main()
