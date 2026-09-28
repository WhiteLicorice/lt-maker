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

class MultiTargetDoublingTests(unittest.TestCase):
    '''
    A multi-target combat has no single defender. The attacker should still double,
    striking each target for as many phases as it gets against that target,
    and never striking a target that has already died
    '''
    def run_combat(self, defenders, phases_vs, lethal=(), multiattacks=1):
        """phases_vs: attacker's number of phases against each unit (by nid).
        lethal: nids of units that die on the first strike they take.
        Returns the nids struck, in order"""
        attacker = Unit(nid='Eirika', hp=20, strike_partner=None)
        item = SimpleNamespace(nid='Multi')
        strikes = []

        def process(actions, playback, atk, defender, def_pos, item, def_item, mode, attack_info, assist=False):
            strikes.append(defender.nid)
            if defender.nid in lethal:
                defender.hp = 0

        def compute_attack_phases(unit, target, item, def_item, mode, attack_info):
            return phases_vs[target.nid] if target else 1

        db = MagicMock()
        db.constants.value.return_value = False
        with patch.object(solver_module, 'DB', db), \
             patch.object(solver_module, 'skill_system', MagicMock(ignore_dying_in_combat=lambda unit: False)), \
             patch.object(solver_module, 'resolve_weapon', lambda unit: None), \
             patch.object(solver_module.item_funcs, 'available', lambda unit, item: True), \
             patch.object(solver_module.combat_calcs, 'compute_attack_phases', compute_attack_phases), \
             patch.object(solver_module.combat_calcs, 'compute_multiattacks', lambda *args: multiattacks):
            all_defenders = list(set(defenders))
            defender = all_defenders[0] if len(all_defenders) == 1 else None
            solver = CombatPhaseSolver(attacker, item, [item] * len(defenders), defenders,
                                       [[] for _ in defenders], [(i, 0) for i in range(len(defenders))],
                                       defender, None)
            solver.process = process
            while solver.get_state():
                solver.do()
                solver.setup_next_state()
        return strikes

    def test_doubles_every_target(self):
        a, b = Unit(nid='A', hp=20), Unit(nid='B', hp=20)
        self.assertEqual(self.run_combat([a, b], {'A': 2, 'B': 2}), ['A', 'B', 'A', 'B'])

    def test_doubles_only_the_targets_it_outspeeds(self):
        a, b = Unit(nid='A', hp=20), Unit(nid='B', hp=20)
        self.assertEqual(self.run_combat([a, b], {'A': 1, 'B': 2}), ['A', 'B', 'B'])

    def test_no_doubling(self):
        a, b = Unit(nid='A', hp=20), Unit(nid='B', hp=20)
        self.assertEqual(self.run_combat([a, b], {'A': 1, 'B': 1}), ['A', 'B'])

    def test_brave_strikes_each_target_twice_per_phase(self):
        a, b = Unit(nid='A', hp=20), Unit(nid='B', hp=20)
        self.assertEqual(self.run_combat([a, b], {'A': 1, 'B': 1}, multiattacks=2), ['A', 'B', 'A', 'B'])

    def test_dead_target_is_not_struck_again(self):
        a, b = Unit(nid='A', hp=20), Unit(nid='B', hp=20)
        self.assertEqual(self.run_combat([a, b], {'A': 2, 'B': 2}, lethal=('A',)), ['A', 'B', 'B'])

    def test_combat_ends_when_every_target_is_dead(self):
        a, b = Unit(nid='A', hp=20), Unit(nid='B', hp=20)
        self.assertEqual(self.run_combat([a, b], {'A': 2, 'B': 2}, lethal=('A', 'B')), ['A', 'B'])

    def test_same_target_twice_is_not_struck_after_death(self):
        a = Unit(nid='A', hp=20)
        self.assertEqual(self.run_combat([a, a], {'A': 1}, lethal=('A',)), ['A'])

if __name__ == '__main__':
    unittest.main()
