import unittest
from unittest.mock import MagicMock, patch


class SecondaryAIPriorityTests(unittest.TestCase):
    """SecondaryAI decides whether to walk toward a target. It used to probe for
    the single hardcoded `status_on_hit` component, so any other item that
    declares an ai_priority was worth nothing out of range. Eon 10/25/25."""

    def setUp(self) -> None:
        import app.engine.action  # noqa: F401 - avoids a circular import
        from app.engine import ai_controller
        self.ai_controller = ai_controller

    def _terms(self, custom_priority):
        ai_controller = self.ai_controller
        ai = MagicMock()
        ai.unit.position = (0, 0)
        enemy = MagicMock()
        enemy.get_hp.return_value = 20
        # An item that applies a status but is not the `status_on_hit` component
        item = MagicMock()
        item.status_on_hit = None

        parser = MagicMock()
        parser.hitpoints.return_value = 20
        with patch.object(ai_controller.equations, 'parser', parser), \
             patch.object(ai_controller.item_funcs, 'get_all_items', return_value=[item]), \
             patch.object(ai_controller.item_funcs, 'available', return_value=True), \
             patch.object(ai_controller.item_system, 'is_weapon', return_value=False), \
             patch.object(ai_controller.item_system, 'is_spell', return_value=False), \
             patch.object(ai_controller.item_system, 'ai_priority', return_value=custom_priority):
            return ai_controller.SecondaryAI.default_priority(ai, enemy)

    def test_custom_ai_priority_is_pursued(self) -> None:
        # weakness_term is 0 at full health; damage term 0, status term is the hook's value
        self.assertEqual([(0, 15), (0.8, 10), (0.0, 15)], self._terms(0.8))

    def test_no_ai_priority_hook_is_still_ignored(self) -> None:
        # No component defines the hook and the item deals no damage -> not worth walking to
        self.assertEqual([], self._terms(None))

    def test_negative_ai_priority_is_clamped_and_ignored(self) -> None:
        # e.g. the no_ai component, which returns -1
        self.assertEqual([], self._terms(-1))


if __name__ == '__main__':
    unittest.main()
