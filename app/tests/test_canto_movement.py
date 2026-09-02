import unittest
from unittest.mock import MagicMock


class CantoMovementTests(unittest.TestCase):
    """canto_movement resolves as a MAXIMUM across every component that defines
    it, so a component that is declining to grant canto must abstain from the
    movement value too. Otherwise Canto's remaining movement drowns out Canter's
    fixed range. Bonklestonk 9/15/25 thread."""

    def setUp(self) -> None:
        import app.engine.action  # noqa: F401 - avoids a circular import
        from app.engine.codegen import source_generator
        source_generator.generate_component_system_source()

    def _unit_with(self, components, has_attacked, movement_left, movement=7):
        skill = MagicMock()
        skill.components = components
        for component in components:
            component.ignore_conditional = True
        unit = MagicMock()
        unit.skills = [skill]
        unit.has_attacked = has_attacked
        unit.movement_left = movement_left
        unit.get_movement.return_value = movement
        return unit

    def test_canter_is_not_widened_by_canto(self) -> None:
        from app.engine import skill_system
        from app.engine.skill_components.movement_components import Canto, Canter
        # Attacked without moving first, so Canto's movement_left is still full
        unit = self._unit_with([Canto(), Canter(2)], has_attacked=True, movement_left=7)
        target = MagicMock()
        self.assertTrue(skill_system.has_canto(unit, target))
        self.assertEqual(2, skill_system.canto_movement(unit, target))

    def test_canto_alone_still_grants_remaining_movement(self) -> None:
        from app.engine import skill_system
        from app.engine.skill_components.movement_components import Canto
        unit = self._unit_with([Canto()], has_attacked=False, movement_left=4)
        target = MagicMock()
        self.assertTrue(skill_system.has_canto(unit, target))
        self.assertEqual(4, skill_system.canto_movement(unit, target))

    def test_canto_targeting_self_still_grants_remaining_movement(self) -> None:
        from app.engine import skill_system
        from app.engine.skill_components.movement_components import Canto, Canter
        # `unit is unit2` is Canto's own escape hatch (it attacked itself), so it
        # is genuinely granting canto here and should still contribute
        unit = self._unit_with([Canto(), Canter(2)], has_attacked=True, movement_left=5)
        self.assertEqual(5, skill_system.canto_movement(unit, unit))

    def test_canto_sharp_abstains_once_movement_is_spent(self) -> None:
        from app.engine import skill_system
        from app.engine.skill_components.movement_components import CantoSharp, Canter
        # Attacked and moved, so CantoSharp no longer grants canto
        unit = self._unit_with([CantoSharp(), Canter(2)], has_attacked=True, movement_left=6, movement=7)
        target = MagicMock()
        self.assertEqual(2, skill_system.canto_movement(unit, target))

    def test_canto_plus_still_wins_over_canter(self) -> None:
        from app.engine import skill_system
        from app.engine.skill_components.movement_components import CantoPlus, Canter
        # CantoPlus grants canto unconditionally, so its movement legitimately applies
        unit = self._unit_with([CantoPlus(), Canter(2)], has_attacked=True, movement_left=7)
        target = MagicMock()
        self.assertEqual(7, skill_system.canto_movement(unit, target))


if __name__ == '__main__':
    unittest.main()
