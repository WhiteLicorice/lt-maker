import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.tests import engine_harness  # noqa: F401 -- imports the state modules while the sprites are loaded
from app.engine import general_states

class FakeUnit():
    def __init__(self, nid: str, ai: str, distance: int):
        self.nid = nid
        self.ai = ai
        self.distance = distance

    def get_ai(self) -> str:
        return self.ai

class AIUnitOrderTests(unittest.TestCase):
    '''AIState.first_to_act: which AI unit acts next'''

    def setUp(self):
        self.measured = []
        priorities = {'high': SimpleNamespace(priority=2), 'low': SimpleNamespace(priority=1)}
        def distance(unit):
            self.measured.append(unit.nid)
            return unit.distance
        for patcher in (patch.object(general_states.DB.ai, 'get', side_effect=priorities.get),
                        patch.object(general_states.game, 'target_system', SimpleNamespace(distance_to_closest_enemy=distance))):
            patcher.start()
            self.addCleanup(patcher.stop)

    def first(self, *units: FakeUnit) -> str:
        return general_states.AIState.first_to_act(list(units)).nid

    def test_higher_priority_acts_first_however_far(self):
        self.assertEqual('far', self.first(FakeUnit('near', 'low', 1), FakeUnit('far', 'high', 9)))

    def test_closest_to_an_enemy_acts_first_within_a_priority(self):
        self.assertEqual('near', self.first(FakeUnit('far', 'high', 9), FakeUnit('near', 'high', 1)))

    def test_no_enemy_at_all_counts_as_closest(self):
        '''distance_to_closest_enemy is -1 when there are no enemies'''
        self.assertEqual('none', self.first(FakeUnit('near', 'high', 1), FakeUnit('none', 'high', -1)))

    def test_a_tie_goes_to_the_first(self):
        self.assertEqual('a', self.first(FakeUnit('a', 'high', 3), FakeUnit('b', 'high', 3)))
        self.assertEqual('b', self.first(FakeUnit('b', 'high', 3), FakeUnit('a', 'high', 3)))

    def test_only_the_highest_priority_is_measured(self):
        self.first(FakeUnit('low1', 'low', 1), FakeUnit('high', 'high', 5), FakeUnit('low2', 'low', 2))
        self.assertEqual(['high'], self.measured)

if __name__ == '__main__':
    unittest.main()
