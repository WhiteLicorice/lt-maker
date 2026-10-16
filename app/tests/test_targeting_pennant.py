import unittest
from unittest.mock import patch

from app.tests.engine_harness import EngineTestCase


class TargetingPennantTests(EngineTestCase):
    '''
    The GBA games scroll a line of help along the bottom of the screen while the
    player picks a target for a staff: "Select a character to restore HP to."
    The targeting_pennant item component gives an item such a line
    '''
    hint = 'Select a character to restore HP to.'

    def setUp(self):
        super().setUp()
        harness = self.harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        self.seth = harness.game.get_unit('Seth')

    def give_hint(self, item, text=None):
        from app.engine.item_components.aesthetic_components import TargetingPennant
        item.components.append(TargetingPennant(value=text or self.hint))

    def target(self):
        '''Seth goes to (8, 5) and picks his first weapon to attack with. Returns the targeting state'''
        harness = self.harness
        harness.move_unit('Seth', (8, 5))
        harness.choose('Attack')
        harness.run_until_state('weapon_choice')
        harness.press('SELECT')
        harness.run_until_state('combat_targeting')
        return harness.game.state.current_state()

    def test_item_with_the_component_shows_its_text(self):
        self.give_hint(self.seth.get_weapon())
        state = self.target()
        self.assertEqual(self.seth.get_weapon(), state.item)
        self.assertEqual(self.hint, state.pennant.text)

    def test_nothing_shown_for_an_item_without_it(self):
        state = self.target()
        self.assertIsNone(state.pennant)

    def test_text_is_translated(self):
        from app.engine import text_funcs
        self.give_hint(self.seth.get_weapon(), 'heal_hint')
        with patch.object(text_funcs, 'translate', lambda text: {'heal_hint': 'Soigner qui ?'}.get(text, text)):
            state = self.target()
        self.assertEqual('Soigner qui ?', state.pennant.text)

    def test_subitem_without_one_shows_the_sequence_items(self):
        state = self.target()
        subitem, parent = self.seth.items[0], self.seth.items[1]
        state.item, state.parent_item = subitem, parent
        self.assertIsNone(state.build_pennant())
        self.give_hint(parent, 'Select character to warp.')
        self.assertEqual('Select character to warp.', state.build_pennant().text)
        # A subitem's own comes first
        self.give_hint(subitem, 'Select warp point.')
        self.assertEqual('Select warp point.', state.build_pennant().text)

    def test_item_that_can_stop_short_of_its_targets_says_how(self):
        from app.engine import general_states
        state = self.target()
        with patch.object(general_states.item_system, 'num_targets', return_value=2), \
                patch.object(general_states.item_system, 'allow_less_than_max_targets', return_value=True):
            self.assertEqual('Press START to confirm targets.', state.build_pennant().text)
            # Unless the item has a line of its own
            self.give_hint(state.item)
            self.assertEqual(self.hint, state.build_pennant().text)


if __name__ == '__main__':
    unittest.main()
