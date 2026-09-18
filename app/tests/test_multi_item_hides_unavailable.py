import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pygame

import app.engine.sprites as sprites
from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options

def child(nid, kind, usable):
    return SimpleNamespace(nid=nid, kind=kind, usable=usable, multi_item=None)

def multi_item(hides_unusable):
    return SimpleNamespace(
        nid='Parent', multi_item=True, multi_item_hides_unavailable=True if hides_unusable else None,
        subitems=[child('Lance', 'weapon', True), child('Broken Lance', 'weapon', False),
                  child('Physic', 'spell', True), child('Sealed Physic', 'spell', False)])

class MultiItemHidesUnusableChildrenTests(unittest.TestCase):
    '''
    Multi Item Hides Unusable Children stopped hiding them in the weapon, spell and ability
    multi item menus after cf76061bb, which dropped the availability filter from every menu
    except the item child menu
    '''
    @classmethod
    def setUpClass(cls):
        # settings.py (pulled in by general_states) reads sprites at module level
        sprites.load_images()
        # phase.py builds surfaces at module level, which needs a display
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        pygame.display.init()
        if not pygame.display.get_surface():
            pygame.display.set_mode((1, 1))

    def setUp(self):
        from app.engine import general_states
        self.general_states = general_states
        self.game = SimpleNamespace(memory={}, state=MagicMock(), target_system=MagicMock())
        self.game.target_system.get_valid_targets_recursive_with_availability_check.return_value = True
        self.unit = SimpleNamespace(nid='Eirika')
        for patcher in (
                patch.object(general_states, 'game', self.game),
                patch.object(general_states, 'get_sound_thread', MagicMock()),
                patch.object(general_states.item_funcs, 'is_weapon_recursive', lambda unit, item: item.kind == 'weapon'),
                patch.object(general_states.item_funcs, 'is_spell_recursive', lambda unit, item: item.kind == 'spell'),
                patch.object(general_states.item_funcs, 'available', lambda unit, item: item.usable)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def select_in(self, state_class, parent):
        state = state_class.__new__(state_class)
        state.cur_unit = self.unit
        state.fluid = MagicMock()
        state.fluid.get_directions.return_value = []
        state.menu = MagicMock()
        state.menu.handle_mouse.return_value = False
        state.menu.get_current.return_value = parent
        state.take_input('SELECT')

    def offered(self, memory_key):
        return [item.nid for item in self.game.memory[memory_key]]

    def test_weapon_menu(self):
        self.select_in(self.general_states.WeaponChoiceState, multi_item(hides_unusable=True))
        self.assertEqual(self.offered('valid_weapons'), ['Lance'])

    def test_spell_menu(self):
        self.select_in(self.general_states.SpellChoiceState, multi_item(hides_unusable=True))
        self.assertEqual(self.offered('valid_spells'), ['Physic'])

    def test_ability_multi_item_menu(self):
        self.select_in(self.general_states.AbilityMultiItemChoiceState, multi_item(hides_unusable=True))
        self.assertEqual(self.offered('valid_options'), ['Lance', 'Physic'])

    def test_multi_item_granted_as_an_ability(self):
        menu_state = self.general_states.MenuState.__new__(self.general_states.MenuState)
        menu_state.cur_unit = self.unit
        menu_state.extra_abilities = {'_uncategorized': {'Parent': multi_item(hides_unusable=True)}}
        menu_state._handle_extra_ability_selection('Parent')
        self.assertEqual(self.offered('valid_options'), ['Lance', 'Physic'])

    def test_unusable_children_stay_without_the_component(self):
        self.select_in(self.general_states.WeaponChoiceState, multi_item(hides_unusable=False))
        self.assertEqual(self.offered('valid_weapons'), ['Lance', 'Broken Lance'])
        self.select_in(self.general_states.AbilityMultiItemChoiceState, multi_item(hides_unusable=False))
        self.assertEqual(self.offered('valid_options'), ['Lance', 'Broken Lance', 'Physic', 'Sealed Physic'])

if __name__ == '__main__':
    unittest.main()
