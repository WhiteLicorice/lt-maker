import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options
from app.engine.item_components import hit_components
from app.engine.item_components.hit_components import PermanentStatChange

def unit(stat, cap):
    return SimpleNamespace(stats={'STR': stat}, get_stat_cap=lambda stat_nid: cap)

class StatBoosterClampTests(unittest.TestCase):
    '''
    A stat booster used on another unit must clamp against the target's stat cap, not the user's
    '''
    def applied_changes(self, user, target):
        booster = PermanentStatChange([('STR', 5)])
        applied = {}
        def apply_stat_changes(unit, stat_changes):
            applied.update(stat_changes)
        with patch.object(hit_components.action, 'do'), \
             patch.object(hit_components.action, 'ApplyStatChanges', apply_stat_changes), \
             patch.object(hit_components, 'game', MagicMock()):
            booster.on_hit([], [], user, None, target, None, None, 'attack', (0, 0))
            booster.end_combat([], user, None, target, None, 'attack')
        return applied

    def test_clamps_to_target_cap_when_user_cap_is_higher(self):
        self.assertEqual(self.applied_changes(user=unit(10, 40), target=unit(18, 20)), {'STR': 2})

    def test_uses_target_cap_when_user_cap_is_lower(self):
        self.assertEqual(self.applied_changes(user=unit(10, 12), target=unit(10, 20)), {'STR': 5})

if __name__ == '__main__':
    unittest.main()
