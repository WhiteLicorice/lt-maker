import unittest
from unittest.mock import MagicMock, patch


class AIStatusPriorityTests(unittest.TestCase):
    """A status item's AI priority must not be zeroed out just because the user
    cannot double. Squid 9/26/25."""

    def setUp(self) -> None:
        import app.engine.action  # noqa: F401 - avoids a circular import
        from app.engine.item_components import hit_components
        self.hit_components = hit_components

    def _priority(self) -> float:
        from app.engine import combat_calcs
        unit = MagicMock()
        unit.skills = []
        target = MagicMock()
        target.skills = []
        target.position = (0, 0)
        item = MagicMock()

        with patch.object(combat_calcs, 'compute_hit', return_value=100), \
             patch.object(combat_calcs, 'outspeed', return_value=0), \
             patch.object(combat_calcs.item_system, 'dynamic_attacks', return_value=0), \
             patch.object(combat_calcs.skill_system, 'dynamic_attacks', return_value=0), \
             patch.object(combat_calcs, 'resolve_weapon', return_value=None), \
             patch.object(self.hit_components.skill_system, 'check_enemy', return_value=True):
            return self.hit_components.ai_status_priority(unit, target, item, (0, 0), 'Poison')

    def test_non_doubling_status_item_still_has_priority(self) -> None:
        # Guaranteed hit, one attack phase, no distance travelled -> 0.5 * 1.0 * 1
        self.assertEqual(0.5, self._priority())


if __name__ == '__main__':
    unittest.main()
