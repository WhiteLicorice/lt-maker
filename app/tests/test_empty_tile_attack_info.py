import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options
from app.engine.combat import solver as solver_module
from app.engine.combat.solver import CombatPhaseSolver

class Unit(SimpleNamespace):
    __hash__ = object.__hash__

    def get_hp(self):
        return self.hp

class EmptyTileAttackInfoTests(unittest.TestCase):
    '''
    A strike on an empty tile still runs the item's on_hit.
    It should be told which attack it is, the same as a strike on a unit
    '''
    def run_combat(self, phases):
        """Returns the (mode, attack_info) each on_hit was called with, in order"""
        attacker = Unit(nid='Eirika', hp=20, strike_partner=None)
        item = SimpleNamespace(nid='Torch')
        hits = []

        def on_hit(actions, playback, unit, item, target, item2, target_pos, mode, attack_info, first_item):
            hits.append((mode, attack_info))

        db = MagicMock()
        db.constants.value.return_value = False
        with patch.object(solver_module, 'DB', db), \
             patch.object(solver_module, 'skill_system', MagicMock(ignore_dying_in_combat=lambda unit: False)), \
             patch.object(solver_module, 'resolve_weapon', lambda unit: None), \
             patch.object(solver_module.item_funcs, 'available', lambda unit, item: True), \
             patch.object(solver_module.item_system, 'on_hit', on_hit), \
             patch.object(solver_module.combat_calcs, 'compute_attack_phases', lambda *args: phases), \
             patch.object(solver_module.combat_calcs, 'compute_multiattacks', lambda *args: 1):
            solver = CombatPhaseSolver(attacker, item, [item], [None], [[]], [(3, 3)], None, None)
            while solver.get_state():
                solver.do()
                solver.setup_next_state()
        return hits

    def test_single_strike(self):
        self.assertEqual(self.run_combat(phases=1), [('attack', (0, 0))])

    def test_follow_up_strike_knows_it_is_the_second_attack(self):
        self.assertEqual(self.run_combat(phases=2), [('attack', (0, 0)), ('attack', (1, 0))])

if __name__ == '__main__':
    unittest.main()
