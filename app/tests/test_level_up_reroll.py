import unittest
from unittest.mock import patch

from app.tests.engine_harness import EngineTestCase


class EmptyLevelUpRerollTests(EngineTestCase):
    '''
    The GBA games roll an empty level up again: up to twice over, a stat at a
    time, stopping at the first stat to come up. Here every stat grows 5% of the
    time, so that most levels are empty
    '''
    growth = 5

    def setUp(self):
        super().setUp()
        from app.engine import unit_funcs
        patcher = patch.object(unit_funcs, 'growth_rate', return_value=self.growth)
        patcher.start()
        self.addCleanup(patcher.stop)
        harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        self.unit = harness.game.get_unit('Eirika')

    def level_up(self, level, method='Random', **kwargs):
        from app.engine import unit_funcs
        return unit_funcs.get_next_level_up(self.unit, level, method, **kwargs)

    def expected(self, level):
        '''What the GBA's rule gives for the level, from the unit's own rolls'''
        from app.data.database.database import DB
        from app.utilities import static_random
        rng = static_random.get_levelup(self.unit.nid, level)
        stats = list(DB.stats.keys())
        changes = {nid: 1 if rng.randint(0, 99) < self.growth else 0 for nid in stats}
        if not any(changes.values()):
            for _ in range(2):
                for nid in stats:
                    if rng.randint(0, 99) < self.growth:
                        changes[nid] = 1
                        return changes
        return changes

    def test_off_unless_the_constant_is_set(self):
        from app.data.database.database import DB
        self.assertFalse(DB.constants.value('reroll_empty_level_ups'))
        empty_levels = [level for level in range(1, 60) if not any(self.level_up(level).values())]
        self.assertGreater(len(empty_levels), 20)

    def test_empty_level_is_rolled_again(self):
        from app.data.database.database import DB
        empty_levels = [level for level in range(1, 60) if not any(self.level_up(level).values())]
        DB.constants.get('reroll_empty_level_ups').set_value(True)
        self.addCleanup(DB.constants.get('reroll_empty_level_ups').set_value, False)

        saved = 0
        for level in range(1, 60):
            changes = self.level_up(level)
            self.assertEqual(self.expected(level), changes, level)
            if level in empty_levels and any(changes.values()):
                # Only the first stat to come up is raised
                self.assertEqual(1, sum(changes.values()), level)
                saved += 1
        self.assertGreater(saved, 5)
        # And two more passes of 5% rolls still leave some levels empty
        self.assertLess(saved, len(empty_levels))

    def test_dynamic_growths_are_rolled_again_too(self):
        '''
        A dynamic level up can be empty as well. The second rolls are against the
        growth rates alone, and leave the unit's growth points as the first left them
        '''
        from app.data.database.database import DB

        def level_ups():
            '''Levels 1 to 59 from the same start, with the growth points each left'''
            self.unit.growth_points = {nid: 0 for nid in DB.stats.keys()}
            results = []
            for level in range(1, 60):
                changes = self.level_up(level, 'Dynamic')
                results.append((changes, dict(self.unit.growth_points)))
            return results

        without = level_ups()
        empty_levels = [idx for idx, (changes, _) in enumerate(without) if not any(changes.values())]
        self.assertGreater(len(empty_levels), 5)
        DB.constants.get('reroll_empty_level_ups').set_value(True)
        self.addCleanup(DB.constants.get('reroll_empty_level_ups').set_value, False)
        rolled_again = level_ups()

        saved = 0
        for idx, ((before, points_before), (after, points_after)) in enumerate(zip(without, rolled_again)):
            self.assertEqual(points_before, points_after, idx)
            if idx in empty_levels:
                self.assertIn(sum(after.values()), (0, 1), idx)
                saved += sum(after.values())
            else:
                self.assertEqual(before, after, idx)
        self.assertGreater(saved, 0)

    def test_levels_a_unit_is_given_are_not_rolled_again(self):
        '''As on the GBA, where a generic unit's levels come from a rule of their own'''
        from app.data.database.database import DB
        empty_levels = [level for level in range(1, 60) if not any(self.level_up(level).values())]
        DB.constants.get('reroll_empty_level_ups').set_value(True)
        self.addCleanup(DB.constants.get('reroll_empty_level_ups').set_value, False)
        for level in empty_levels:
            self.assertFalse(any(self.level_up(level, reroll_empty=False).values()), level)


if __name__ == '__main__':
    unittest.main()
