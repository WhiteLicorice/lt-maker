import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options
from app.engine.combat import interaction

A = SimpleNamespace(nid='A', sequence_item=False, subitems=[])
B = SimpleNamespace(nid='B', sequence_item=False, subitems=[])

def sequence(*subitems):
    return SimpleNamespace(nid='Sequence', sequence_item=True, subitems=list(subitems))

class MultiTargetEngageTests(unittest.TestCase):
    '''
    The combat solver resolves items[i] against target_positions[i], so engage has to line up one
    item per target. A multi-target sub-item is copied once per extra target, and those copies used
    to go in at the sub-item's index in the original list, which ignored the copies already inserted
    for any earlier multi-target sub-item
    '''
    def pairs(self, main_item, positions):
        captured = {}
        def combat(attacker, main_item, items, target_positions, main_targets, splashes, script, total_rounds):
            captured['pairs'] = [(item.nid, pos) for item, pos in zip(items, target_positions)]
            captured['lengths'] = (len(items), len(target_positions), len(main_targets), len(splashes))
        with patch.object(interaction.item_system, 'splash', lambda unit, item, pos: (pos, [])), \
             patch.object(interaction, 'SimpleCombat', combat), \
             patch.object(interaction, 'game', MagicMock()):
            interaction.engage(SimpleNamespace(nid='Eirika'), positions, main_item, skip=True)
        self.assertEqual(len(set(captured['lengths'])), 1, captured['lengths'])
        return captured['pairs']

    def test_multi_target_item(self):
        self.assertEqual(self.pairs(A, [[(1, 1), (2, 2), (3, 3)]]),
                         [('A', (1, 1)), ('A', (2, 2)), ('A', (3, 3))])

    def test_sequence_multi_target_then_single(self):
        self.assertEqual(self.pairs(sequence(A, B), [[(1, 1), (2, 2)], (3, 3)]),
                         [('A', (1, 1)), ('A', (2, 2)), ('B', (3, 3))])

    def test_sequence_single_then_multi_target(self):
        self.assertEqual(self.pairs(sequence(A, B), [(1, 1), [(3, 3), (4, 4)]]),
                         [('A', (1, 1)), ('B', (3, 3)), ('B', (4, 4))])

    def test_sequence_of_two_multi_target_items(self):
        self.assertEqual(self.pairs(sequence(A, B), [[(1, 1), (2, 2)], [(3, 3), (4, 4)]]),
                         [('A', (1, 1)), ('A', (2, 2)), ('B', (3, 3)), ('B', (4, 4))])

if __name__ == '__main__':
    unittest.main()
