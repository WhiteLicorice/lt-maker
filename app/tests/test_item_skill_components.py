import unittest
from typing import Any, Callable, List
from unittest.mock import MagicMock, patch

from app.data.database.item_components import ItemComponent
from app.data.database.skill_components import SkillComponent
from app.engine.codegen import source_generator
from app.engine.item_components.base_components import ItemTag, Spell, Weapon
from app.engine.item_components.advanced_components import MultiTarget
from app.engine.item_components.exp_components import Wexp
from app.engine.item_components.weapon_components import Damage, Hit, Crit
from app.engine.item_components.extra_components import CustomTriangleMultiplier
from app.engine.objects.item import ItemObject
from app.engine.objects.skill import SkillObject
from app.engine.objects.unit import UnitObject
from app.engine.skill_components.base_components import CanUseWeaponType, CannotUseWeaponType, ChangeAI, ChangeBuyPrice, IgnoreAlliances, Locktouch, SkillTag
from app.engine.skill_components.combat_components import DamageMultiplier
from app.engine.skill_components.combat2_components import Vantage
from app.engine.skill_components.dynamic_components import DynamicDamage
from app.engine.skill_components.aesthetic_components import BattleAnimMusic, UnitFlickeringTint
from app.utilities.data import Data


class ItemSkillComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        source_generator.generate_component_system_source()

    def tearDown(self) -> None:
        pass

    def test_item_components(self) -> None:
        # Test that all item components have
        # unique nids
        item_components = ItemComponent.__subclasses__()
        nids = {component.nid for component in item_components}
        for component in item_components:
            nid = component.nid
            self.assertIn(nid, nids)
            nids.remove(nid)

    def test_skill_components(self) -> None:
        # Test that all skill components have
        # unique nids
        skill_components = SkillComponent.__subclasses__()
        nids = {component.nid for component in skill_components}
        for component in skill_components:
            nid = component.nid
            self.assertIn(nid, nids)
            nids.remove(nid)

    def _test_skill_hook_with_components(self, components: List[SkillComponent], call_hook: Callable[[UnitObject], Any], expected_result: Any) -> None:
        mock_skill = MagicMock()
        mock_skill.components = components
        mock_unit = MagicMock()
        mock_unit.skills = [mock_skill]
        mock_unit.ai = 'Pursue'
        mock_unit.team = 'player'
        self.assertEqual(expected_result, call_hook(mock_unit))

    def test_skill_hooks_set_union_behavior(self) -> None:
        from app.engine import skill_system
        self._test_skill_hook_with_components([], lambda unit: skill_system.usable_wtypes(unit), set())
        self._test_skill_hook_with_components([CanUseWeaponType(None), CanUseWeaponType("Sword"), CanUseWeaponType("Lance")], lambda unit: skill_system.usable_wtypes(unit), set(["Sword", "Lance"]))
        self._test_skill_hook_with_components([CanUseWeaponType("Sword"), CanUseWeaponType("Lance"), CanUseWeaponType("Lance")], lambda unit: skill_system.usable_wtypes(unit), set(["Sword", "Lance"]))

    def test_combat_condition_invalidates_cache_after_publishing(self) -> None:
        # Regression: CombatCondition.pre_combat must invalidate the ltcache AFTER it
        # publishes self._condition. Evaluating its condition string routes back through
        # item_override -> condition(), re-caching the old _condition under the freshly
        # altered cache state; without a trailing invalidation that stale value sticks and
        # the override (e.g. Weapon Triangle) fails to apply for the first hit.
        from app.engine import skill_system
        from app.engine.utils import ltcache
        from app.engine.skill_components.conditional_components import CombatCondition
        import app.engine.skill_components.conditional_components as cc

        ltcache.init()

        comp = CombatCondition()
        comp._condition = False
        skill = MagicMock()
        skill.components = [comp]
        comp.skill = skill
        unit = MagicMock()
        unit.equipped_weapon = None

        # Forecast phase: condition is False and gets cached
        self.assertFalse(skill_system.condition(skill, unit))

        fake_game = MagicMock()
        fake_game.on_alter_game_state.side_effect = ltcache.alter_state

        # Stand in for a condition string that, while evaluating, reads condition() again
        # (as weapon_type/weapon_triangle_override do via item_override) - re-caching the
        # still-False value - before pre_combat sets _condition = True.
        def fake_evaluate(*args, **kwargs):
            skill_system.condition(skill, unit)
            return True

        with patch.object(cc, 'game', fake_game), \
                patch('app.engine.evaluate.evaluate', side_effect=fake_evaluate):
            comp.pre_combat(None, unit, None, None, None, 'attack')

        self.assertTrue(comp._condition)
        self.assertTrue(skill_system.condition(skill, unit),
                        "condition() returned a stale cached value after pre_combat")

    def test_skill_hooks_all_false_priority(self) -> None:
        from app.engine import skill_system
        self._test_skill_hook_with_components([], lambda unit: skill_system.vantage(unit), False)
        self._test_skill_hook_with_components([Vantage()], lambda unit: skill_system.vantage(unit), True)
        mock_component = MagicMock()
        mock_component.vantage = MagicMock(return_value=False)
        self._test_skill_hook_with_components([Vantage(), mock_component], lambda unit: skill_system.vantage(unit), False)

    def test_skill_hooks_all_true_priority(self) -> None:
        from app.engine import skill_system
        mock_component_1 = MagicMock()
        mock_component_1.available = MagicMock(return_value=False)
        mock_component_2 = MagicMock()
        mock_component_2.available = MagicMock(return_value=True)
        mock_arg = MagicMock()
        self._test_skill_hook_with_components([], lambda unit: skill_system.available(unit, mock_arg), True)
        self._test_skill_hook_with_components([mock_component_1], lambda unit: skill_system.available(unit, mock_arg), False)
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.available(unit, mock_arg), False)

    def test_skill_hooks_any_false_priority(self) -> None:
        from app.engine import skill_system
        mock_arg = MagicMock()
        mock_component = MagicMock()
        mock_component.can_unlock = MagicMock(return_value=False)
        self._test_skill_hook_with_components([], lambda unit: skill_system.can_unlock(unit, mock_arg), False)
        self._test_skill_hook_with_components([Locktouch()], lambda unit: skill_system.can_unlock(unit, mock_arg), True)
        self._test_skill_hook_with_components([Locktouch(), mock_component], lambda unit: skill_system.can_unlock(unit, mock_arg), True)

    def test_skill_hooks_unique_default(self) -> None:
        from app.engine import skill_system
        self._test_skill_hook_with_components([], lambda unit: skill_system.change_ai(unit), 'Pursue')
        self._test_skill_hook_with_components([ChangeAI('Guard'), ChangeAI('Defend')], lambda unit: skill_system.change_ai(unit), 'Defend')
        self._test_skill_hook_with_components([ChangeAI('Defend'), ChangeAI('Guard')], lambda unit: skill_system.change_ai(unit), 'Guard')

    def test_skill_hooks_unique_default_item(self) -> None:
        from app.engine import skill_system
        mock_item = MagicMock()
        self._test_skill_hook_with_components([], lambda unit: skill_system.modify_buy_price(unit, mock_item), 1.0)
        self._test_skill_hook_with_components([ChangeBuyPrice(2.0), ChangeBuyPrice(0.5)], lambda unit: skill_system.modify_buy_price(unit, mock_item), 0.5)
        self._test_skill_hook_with_components([ChangeBuyPrice(0.5), ChangeBuyPrice(2.0)], lambda unit: skill_system.modify_buy_price(unit, mock_item), 2.0)

    def test_skill_hooks_accumulate_item(self) -> None:
        from app.engine import skill_system
        mock_item = MagicMock()
        mock_component_1 = MagicMock()
        mock_component_1.modify_damage = MagicMock(return_value=1)
        mock_component_2 = MagicMock()
        mock_component_2.modify_damage = MagicMock(return_value=2)
        self._test_skill_hook_with_components([], lambda unit: skill_system.modify_damage(unit, mock_item), 0)
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.modify_damage(unit, mock_item), 3)
        self._test_skill_hook_with_components([mock_component_2, mock_component_1], lambda unit: skill_system.modify_damage(unit, mock_item), 3)

    def test_skill_hooks_accumulate(self) -> None:
        from app.engine import skill_system
        mock_item = MagicMock()
        mock_target = MagicMock()
        mock_info = MagicMock()
        self._test_skill_hook_with_components([], lambda unit: skill_system.dynamic_damage(unit, mock_item, mock_target, mock_item, 'attack', mock_info, 1), 0)
        self._test_skill_hook_with_components([DynamicDamage("1"), DynamicDamage("2")], lambda unit: skill_system.dynamic_damage(unit, mock_item, mock_target, mock_item, 'attack', mock_info, 1), 3)
        self._test_skill_hook_with_components([DynamicDamage("2"), DynamicDamage("1")], lambda unit: skill_system.dynamic_damage(unit, mock_item, mock_target, mock_item, 'attack', mock_info, 1), 3)

    def test_skill_hooks_multiply(self) -> None:
        from app.engine import skill_system
        mock_item = MagicMock()
        mock_target = MagicMock()
        mock_info = MagicMock()
        mock_mode = MagicMock()
        self._test_skill_hook_with_components([], lambda unit: skill_system.damage_multiplier(unit, mock_item, mock_target, mock_item, mock_mode, mock_info, 0), 1)
        self._test_skill_hook_with_components([DamageMultiplier(3.0), DamageMultiplier(1.5)], lambda unit: skill_system.damage_multiplier(unit, mock_item, mock_target, mock_item, mock_mode, mock_info, 0), 4.5)
        self._test_skill_hook_with_components([DamageMultiplier(-2), DamageMultiplier(1.5)], lambda unit: skill_system.damage_multiplier(unit, mock_item, mock_target, mock_item, mock_mode, mock_info, 0), -3)

    def test_skill_hooks_unique_default_target(self) -> None:
        from app.engine import skill_system
        mock_target = MagicMock()
        mock_target.team = 'other'
        self._test_skill_hook_with_components([], lambda unit: skill_system.check_ally(unit, mock_target), True)
        self._test_skill_hook_with_components([IgnoreAlliances()], lambda unit: skill_system.check_ally(unit, mock_target), False)

    def test_skill_hooks_unique_no_default(self) -> None:
        from app.engine import skill_system
        mock_playback = MagicMock()
        mock_item = MagicMock()
        mock_target = MagicMock()
        mock_mode = MagicMock()
        self._test_skill_hook_with_components([], lambda unit: skill_system.battle_music(mock_playback, unit, mock_item, mock_target, mock_item, mock_mode), None)
        self._test_skill_hook_with_components([BattleAnimMusic('FillerBong'), BattleAnimMusic('FillerSong')], lambda unit: skill_system.battle_music(mock_playback, unit, mock_item, mock_target, mock_item, mock_mode), 'FillerSong')

    def test_skill_hooks_unique_event(self) -> None:
        from app.engine import skill_system
        self._test_skill_hook_with_components([], lambda unit: skill_system.on_death(unit), None)
        mock_component_1 = MagicMock()
        mock_component_1.on_death = MagicMock()
        mock_component_1.on_add_item = MagicMock()
        mock_component_1.start_combat = MagicMock()
        mock_component_1.start_sub_combat = MagicMock()
        mock_component_1.after_strike = MagicMock()
        mock_component_1.on_upkeep = MagicMock(('Fail', 'Fail'))
        mock_component_1.on_add_item = MagicMock()
        mock_component_2 = MagicMock()
        mock_component_2.on_death = MagicMock()
        mock_component_2.on_add_item = MagicMock()
        mock_component_2.start_combat = MagicMock()
        mock_component_2.start_sub_combat = MagicMock()
        mock_component_2.after_strike = MagicMock()
        mock_component_2.on_upkeep = MagicMock(return_value=('Test', 'Test'))
        mock_component_2.on_add_item = MagicMock()
        mock_component_3 = MagicMock()
        mock_component_3.start_combat = MagicMock()
        mock_component_3.start_combat_unconditional = MagicMock()
        mock_component_3.condition = MagicMock(return_value=False)
        mock_component_3.ignore_conditional = None
        mock_arg = MagicMock()
        mock_item_arg = ItemObject("test", "Test", "Test")
        mock_unit_arg = UnitObject("test")
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.on_death(unit), None)
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.on_add_item(unit, mock_item_arg), None)
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.on_upkeep(mock_arg, mock_arg, unit), None)
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.start_sub_combat(mock_arg, mock_arg, unit, mock_item_arg, mock_unit_arg, mock_item_arg, mock_arg, mock_arg), None)
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.after_strike(mock_arg, mock_arg, unit, mock_item_arg, mock_unit_arg, mock_item_arg, mock_arg, mock_arg, mock_arg), None)
        # has unconditional
        self._test_skill_hook_with_components([mock_component_1, mock_component_2, mock_component_3], lambda unit: skill_system.start_combat(mock_arg, unit, mock_item_arg, mock_unit_arg, mock_item_arg, mock_arg), None)
        self.assertTrue(mock_component_1.on_death.called)
        self.assertTrue(mock_component_2.on_death.called)
        self.assertTrue(mock_component_1.on_add_item.called)
        self.assertTrue(mock_component_2.on_add_item.called)
        self.assertTrue(mock_component_1.start_combat.called)
        self.assertTrue(mock_component_2.start_combat.called)
        self.assertTrue(mock_component_1.start_sub_combat.called)
        self.assertTrue(mock_component_2.start_sub_combat.called)
        self.assertTrue(mock_component_1.after_strike.called)
        self.assertTrue(mock_component_2.after_strike.called)
        # unconditional tests
        self.assertFalse(mock_component_3.start_combat.called)
        self.assertTrue(mock_component_3.start_combat_unconditional.called)

    def test_skill_unconditionals(self) -> None:
        from app.engine import skill_system
        mock_arg = MagicMock()
        mock_on_end_chapter = MagicMock()
        mock_on_end_chapter_skill = MagicMock()
        mock_on_upkeep = MagicMock()
        mock_on_endstep = MagicMock()
        mock_start_combat = MagicMock()
        mock_cleanup_combat = MagicMock()
        mock_end_combat = MagicMock()
        mock_pre_combat = MagicMock()
        mock_post_combat = MagicMock()
        mock_test_on = MagicMock()
        mock_test_off = MagicMock()
        mock_on_end_chapter.on_end_chapter_unconditional = MagicMock(return_value=1)
        mock_on_upkeep.on_upkeep_unconditional = MagicMock(return_value=1)
        mock_on_endstep.on_endstep_unconditional = MagicMock(return_value=1)
        mock_start_combat.start_combat_unconditional = MagicMock(return_value=1)
        mock_cleanup_combat.cleanup_combat_unconditional = MagicMock(return_value=1)
        mock_end_combat.end_combat_unconditional = MagicMock(return_value=1)
        mock_pre_combat.pre_combat_unconditional = MagicMock(return_value=1)
        mock_post_combat.post_combat_unconditional = MagicMock(return_value=1)
        mock_test_on.test_on_unconditional = MagicMock(return_value=1)
        mock_test_off.test_off_unconditional = MagicMock(return_value=1)
        mock_on_end_chapter.condition = MagicMock(return_value=False)
        mock_on_upkeep.condition = MagicMock(return_value=False)
        mock_on_endstep.condition = MagicMock(return_value=False)
        mock_start_combat.condition = MagicMock(return_value=False)
        mock_cleanup_combat.condition = MagicMock(return_value=False)
        mock_end_combat.condition = MagicMock(return_value=False)
        mock_pre_combat.condition = MagicMock(return_value=False)
        mock_post_combat.condition = MagicMock(return_value=False)
        mock_test_on.condition = MagicMock(return_value=False)
        mock_test_off.condition = MagicMock(return_value=False)
        mock_on_end_chapter_skill.components = [mock_on_end_chapter]
        self._test_skill_hook_with_components([mock_on_end_chapter], lambda unit: skill_system.on_end_chapter(unit, mock_on_end_chapter_skill), None)
        self._test_skill_hook_with_components([mock_on_upkeep], lambda unit: skill_system.on_upkeep(mock_arg, mock_arg, unit), None)
        self._test_skill_hook_with_components([mock_on_endstep], lambda unit: skill_system.on_endstep(mock_arg, mock_arg, unit), None)
        self._test_skill_hook_with_components([mock_start_combat], lambda unit: skill_system.start_combat(mock_arg, unit, mock_arg, mock_arg, mock_arg, mock_arg), None)
        self._test_skill_hook_with_components([mock_cleanup_combat], lambda unit: skill_system.cleanup_combat(mock_arg, unit, mock_arg, mock_arg, mock_arg, mock_arg), None)
        self._test_skill_hook_with_components([mock_end_combat], lambda unit: skill_system.end_combat(mock_arg, unit, mock_arg, mock_arg, mock_arg, mock_arg), None)
        self._test_skill_hook_with_components([mock_pre_combat], lambda unit: skill_system.pre_combat(mock_arg, unit, mock_arg, mock_arg, mock_arg, mock_arg), None)
        self._test_skill_hook_with_components([mock_post_combat], lambda unit: skill_system.post_combat(mock_arg, unit, mock_arg, mock_arg, mock_arg, mock_arg), None)
        self._test_skill_hook_with_components([mock_test_on], lambda unit: skill_system.test_on(mock_arg, unit, mock_arg, mock_arg, mock_arg, mock_arg), None)
        self._test_skill_hook_with_components([mock_test_off], lambda unit: skill_system.test_off(mock_arg, unit, mock_arg, mock_arg, mock_arg, mock_arg), None)
        self.assertTrue(mock_on_end_chapter.on_end_chapter_unconditional.called)
        self.assertTrue(mock_on_upkeep.on_upkeep_unconditional.called)
        self.assertTrue(mock_on_endstep.on_endstep_unconditional.called)
        self.assertTrue(mock_start_combat.start_combat_unconditional.called)
        self.assertTrue(mock_cleanup_combat.cleanup_combat_unconditional.called)
        self.assertTrue(mock_end_combat.end_combat_unconditional.called)
        self.assertTrue(mock_pre_combat.pre_combat_unconditional.called)
        self.assertTrue(mock_post_combat.post_combat_unconditional.called)
        self.assertTrue(mock_test_on.test_on_unconditional.called)
        self.assertTrue(mock_test_off.test_off_unconditional.called)

    def _test_item_hook_with_components(self, components: List[ItemComponent], call_hook: Callable[[UnitObject, ItemObject], Any], expected_result: Any) -> None:
        mock_item = MagicMock()
        mock_item.components = components
        mock_unit = MagicMock()
        self.assertEqual(expected_result, call_hook(mock_unit, mock_item))

    def _test_item_hook_with_item(self, mock_item: Any, call_hook: Callable[[UnitObject, ItemObject], Any], expected_result: Any) -> None:
        mock_unit = MagicMock()
        self.assertEqual(expected_result, call_hook(mock_unit, mock_item))

    def test_item_hooks_weapon_resolution_logic(self) -> None:
        from app.engine import item_system
        # is_weapon
        self._test_item_hook_with_components([Weapon()], lambda unit, item: item_system.is_weapon(unit, item), True)
        self._test_item_hook_with_components([Spell()], lambda unit, item: item_system.is_weapon(unit, item), False)
        self._test_item_hook_with_components([Spell(), Weapon()], lambda unit, item: item_system.is_weapon(unit, item), False)
        self._test_item_hook_with_components([], lambda unit, item: item_system.is_weapon(unit, item), False)

    def test_item_hooks_all_false_priority(self) -> None:
        from app.engine import item_system
        self._test_item_hook_with_components([], lambda unit, item: item_system.is_weapon(unit, item), False)
        self._test_item_hook_with_components([Weapon()], lambda unit, item: item_system.is_weapon(unit, item), True)
        mock_component = MagicMock()
        mock_component.is_weapon = MagicMock(return_value=False)
        self._test_item_hook_with_components([Weapon(), mock_component], lambda unit, item: item_system.is_weapon(unit, item), False)

    def test_item_hooks_unique_default(self) -> None:
        from app.engine import item_system
        self._test_item_hook_with_components([], lambda unit, item: item_system.num_targets(unit, item), 1)
        self._test_item_hook_with_components([MultiTarget(2)], lambda unit, item: item_system.num_targets(unit, item), 2)
        self._test_item_hook_with_components([MultiTarget(2), MultiTarget(3)], lambda unit, item: item_system.num_targets(unit, item), 3)

    def test_item_hooks_union(self) -> None:
        from app.engine import item_system
        target = MagicMock()
        mock_component_1 = MagicMock()
        mock_component_1.target_icon = MagicMock(return_value='warning')
        mock_component_2 = MagicMock()
        mock_component_2.target_icon = MagicMock(return_value='money')
        self._test_item_hook_with_components([], lambda unit, item: item_system.target_icon(unit, item, target), set())
        self._test_item_hook_with_components([mock_component_1, mock_component_1], lambda unit, item: item_system.target_icon(unit, item, target), set(['warning']))
        self._test_item_hook_with_components([mock_component_1, mock_component_2], lambda unit, item: item_system.target_icon(unit, item, target), set(['warning', 'money']))

    def test_item_hooks_accum(self) -> None:
        from app.engine import item_system
        mock_arg = MagicMock()
        self._test_item_hook_with_components([], lambda unit, item: item_system.wexp(mock_arg, unit, item, mock_arg), 0)
        self._test_item_hook_with_components([Wexp(2)], lambda unit, item: item_system.wexp(mock_arg, unit, item, mock_arg), 1)
        self._test_item_hook_with_components([Wexp(2), Wexp(3)], lambda unit, item: item_system.wexp(mock_arg, unit, item, mock_arg), 3)

    def test_item_hooks_no_return(self) -> None:
        from app.engine import item_system
        mock_arg = MagicMock()
        mock_item = MagicMock()
        mock_parent = MagicMock()
        mock_component_1 = MagicMock()
        mock_component_1.on_end_chapter = MagicMock(return_value=None)
        mock_component_1.on_upkeep = MagicMock(return_value=None)
        mock_component_1.start_combat = MagicMock(return_value=None)
        mock_component_1.battle_music = MagicMock(return_value=None)
        mock_component_2 = MagicMock()
        mock_component_2.on_end_chapter = MagicMock(return_value=None)
        mock_component_2.on_upkeep = MagicMock(return_value=None)
        mock_component_2.start_combat = MagicMock(return_value=None)
        mock_component_2.battle_music = MagicMock(return_value=None)
        mock_item.components = [mock_component_1]
        mock_parent.components = [mock_component_2]
        mock_item.parent_item = mock_parent
        self.assertEqual(None, item_system.on_end_chapter(mock_arg, mock_item))
        self.assertEqual(None, item_system.on_upkeep(mock_arg, mock_arg, mock_arg, mock_item))
        self.assertEqual(None, item_system.start_combat(mock_arg, mock_arg, mock_item, mock_arg, mock_arg, mock_arg))
        self.assertEqual(None, item_system.battle_music(mock_arg, mock_item, mock_arg, mock_arg, mock_arg))
        self.assertTrue(mock_component_1.on_end_chapter.called)
        self.assertTrue(mock_component_2.on_end_chapter.called)
        self.assertTrue(mock_component_1.on_upkeep.called)
        self.assertTrue(mock_component_2.on_upkeep.called)
        self.assertTrue(mock_component_1.start_combat.called)
        self.assertTrue(mock_component_2.start_combat.called)
        self.assertTrue(mock_component_1.battle_music.called)
        self.assertFalse(mock_component_2.battle_music.called)

    @patch('app.engine.skill_system')
    def test_item_override(self, test_patch: Any) -> None:
        from app.engine import item_system
        mock_unit = MagicMock()
        test_patch.item_override = MagicMock(return_value = [Damage(4), Hit(90), CustomTriangleMultiplier(2)])
        mock_item = MagicMock()
        mock_item.components = [Damage(10), Crit(25), CustomTriangleMultiplier(2)]
        self.assertEqual(4, item_system.damage(mock_unit, mock_item))
        self.assertEqual(90, item_system.hit(mock_unit, mock_item))
        self.assertEqual(25, item_system.crit(mock_unit, mock_item))
        self.assertEqual(4, item_system.modify_weapon_triangle(mock_unit, mock_item))

    def test_object_merge_policy(self) -> None:
        from app.engine.component_system.utils import object_merge
        from app.engine.game_menus.uses_display_config import UsesDisplayConfig

        mock_unit = MagicMock()
        mock_item = MagicMock()

        func_a = lambda u, i: 'a'
        func_b = lambda u, i: 'b'
        func_c = lambda u, i: 'c'
        func_d = lambda u, i: 'd'

        config_1 = UsesDisplayConfig(func_a, '/', func_b, func_c, mock_unit, mock_item)
        config_2 = UsesDisplayConfig(None, '-', None, func_d, mock_unit, mock_item)

        # empty list returns None
        self.assertIsNone(object_merge([]))

        # single item returns itself
        self.assertIs(object_merge([config_1]), config_1)

        # right side overrides non-None fields; None fields fall back to left
        result = object_merge([config_1, config_2])
        self.assertIs(result.get_curr_uses, func_a)   # config_2 is None -> keep config_1's
        self.assertEqual(result.delim, '-')            # config_2 overrides
        self.assertIs(result.get_max_uses, func_b)     # config_2 is None -> keep config_1's
        self.assertIs(result.get_uses_color, func_d)   # config_2 overrides
        self.assertIs(result.unit, mock_unit)
        self.assertIs(result.item, mock_item)

    def test_item_tags(self) -> None:
        mock_item = ItemObject("test", "Test", "Test", None, (0, 0), Data([ItemTag(['weapon'])]))
        self.assertTrue('weapon' in mock_item.tags)
        no_tag_item = ItemObject("test", "Test", "Test", None, (0, 0), Data())
        self.assertFalse('weapon' in no_tag_item.tags)

    def test_skill_tags(self) -> None:
        mock_skill = SkillObject("test", "Test", "Test", None, (0, 0), Data([SkillTag(['skill'])]))
        self.assertTrue('skill' in mock_skill.tags)
        no_tag_skill = SkillObject("test", "Test", "Test", None, (0, 0), Data())
        self.assertFalse('skill' in no_tag_skill.tags)

    def test_shove_on_end_combat_shoves_splash_targets(self) -> None:
        '''
        With a splash component there may be no main defender at all (spell blast
        returns None as the main target), so the units to shove can only be found
        from the on_hit calls -- not from cleanup_combat's `target` argument.
        '''
        from app.engine.item_components import hit_components
        component = hit_components.ShoveOnEndCombat(1)

        unit = MagicMock()
        unit.position = (0, 0)
        near = MagicMock()
        near.position = (1, 0)
        far = MagicMock()
        far.position = (2, 0)

        playback: List[Any] = []
        with patch.object(hit_components, 'action') as mock_action, \
                patch.object(hit_components, 'skill_system') as mock_skill_system, \
                patch.object(hit_components, 'game') as mock_game:
            mock_skill_system.ignore_forced_movement.return_value = False
            mock_game.query_engine.check_shove.side_effect = \
                lambda target, anchor_pos, magnitude: (target.position[0] + magnitude, target.position[1])

            for target in (near, far):
                component.on_hit([], [], unit, None, target, None, target.position, 'attack', None)
            # No main defender -- every unit hit was a splash target
            component.cleanup_combat(playback, unit, None, None, None, 'attack')

            # Farthest target shoved first, so the near unit doesn't stop short against it
            self.assertEqual([((far, (3, 0)),), ((near, (2, 0)),)],
                             [(c.args,) for c in mock_action.ForcedMovement.call_args_list])
        self.assertEqual(2, len(playback))
        # Targets are not carried over into the next combat
        self.assertFalse(component._did_hit)

if __name__ == '__main__':
    unittest.main()
