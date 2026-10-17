from __future__ import annotations

import logging
from typing import Optional

from app.data.database.components import ComponentType
from app.data.database.database import DB
from app.data.database.item_components import ItemComponent, ItemTags
from app.engine import (action, combat_calcs, equations, image_mods, item_system,
                        skill_system)
from app.engine.game_counters import ANIMATION_COUNTERS
from app.engine.combat import playback as pb
from app.engine.game_state import game
from app.utilities import utils
from app.engine.item_components.utility_components import Heal


class EvalTargetRestrict(ItemComponent):
    nid = 'eval_target_restrict'
    desc = "Use this to restrict what units can be targeted"
    tag = ItemTags.DEPRECATED

    expose = ComponentType.String
    value = 'True'

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        from app.engine import evaluate
        try:
            target = game.board.get_unit(def_pos)
            if target and evaluate.evaluate(self.value, target, position=def_pos):
                return True
            for s_pos in splash:
                target = game.board.get_unit(s_pos)
                if evaluate.evaluate(self.value, target, position=s_pos):
                    return True
        except Exception as e:
            logging.error("Could not evaluate %s (%s)", self.value, e)
            return True
        return False

    def simple_target_restrict(self, unit, item):
        from app.engine import evaluate
        try:
            if evaluate.evaluate(self.value, unit):
                return True
        except Exception as e:
            print("Could not evaluate %s (%s)" % (self.value, e))
            return True
        return False

class EventOnUse(ItemComponent):
    nid = 'event_on_use'
    desc = 'Item calls an event on use, before any effects are played'
    tag = ItemTags.DEPRECATED

    expose = ComponentType.Event

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        event_prefab = DB.events.get_from_nid(self.value)
        if event_prefab:
            local_args = {'target_pos': target_pos, 'mode': mode, 'attack_info': attack_info, 'item': item}
            game.events.trigger_specific_event(event_prefab.nid, unit, target, unit.position, local_args)

class EventAfterUse(ItemComponent):
    nid = 'event_after_use'
    desc = 'Item calls an event after use'
    tag = ItemTags.DEPRECATED

    expose = ComponentType.Event

    _target_pos = None

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        self._target_pos = target_pos

    def end_combat(self, playback, unit, item, target, item2, mode):
        event_prefab = DB.events.get_from_nid(self.value)
        if event_prefab:
            local_args = {'target_pos': self._target_pos, 'item': item, 'item2': item2, 'mode': mode}
            game.events.trigger_specific_event(event_prefab.nid, unit, target, unit.position, local_args)
        self._target_pos = None

class EventAfterCombat(ItemComponent):
    nid = 'event_after_combat'
    desc = "The selected event plays at the end of combat so long as an attack in combat hit."
    tag = ItemTags.DEPRECATED

    expose = ComponentType.Event

    _did_hit = False

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        self._did_hit = True
        self.target_pos = target_pos

    def end_combat(self, playback, unit, item, target, item2, mode):
        if self._did_hit and target:
            event_prefab = DB.events.get_from_nid(self.value)
            if event_prefab:
                local_args = {'target_pos': self.target_pos, 'item': item, 'item2': item2, 'mode': mode}
                game.events.trigger_specific_event(event_prefab.nid, unit, target, unit.position, local_args)
        self._did_hit = False

class Effective(ItemComponent):
    nid = 'effective'
    desc = 'If this item is effective against an enemy its damage value will be increased by the integer chosen here instead. This is not a multiplier, but an addition.'
    # requires = ['damage']
    paired_with = ('effective_tag',)
    tag = ItemTags.DEPRECATED

    expose = ComponentType.Int
    value = 0

    def init(self, item):
        item.data['effective'] = self.value

class EffectiveMultiplier(ItemComponent):
    nid = 'effective_multiplier'
    desc = 'If this item is effective against an enemy its might will be multiplied by this value and added to total damage.'
    # requires = ['damage']
    paired_with = ('effective_tag',)
    tag = ItemTags.DEPRECATED

    expose = ComponentType.Float
    value = 1

    def init(self, item):
        item.data['effective_multiplier'] = self.value

class EffectiveIcon(ItemComponent):
    nid = 'effective_icon'
    desc = "Shows the effective icon when appropriate."
    tag = ItemTags.DEPRECATED

    expose = (ComponentType.List, ComponentType.Tag)
    value = []

    def _check_negate(self, target) -> bool:
        # Returns whether it DOES negate the effectiveness
        # Still need to check negation (Fili Shield, etc.)
        if any(skill.negate for skill in target.skills):
            return True
        for skill in target.skills:
            # Do the tags match?
            if skill.negate_tags and skill.negate_tags.value and \
                    any(tag in self.value for tag in skill.negate_tags.value):
                return True
        # No negation, so proceed with effective damage
        return False

    def item_icon_mod(self, unit, item, target, item2, sprite):
        if any(tag in target.tags for tag in self.value):
            if self._check_negate(target):
                return sprite
            sprite = image_mods.flash_effective(sprite.convert_alpha(), ANIMATION_COUNTERS.forecast_counter.count)
        return sprite

    def target_icon(self, unit, item, target) -> bool:
        if not skill_system.check_enemy(target, unit):
            return None
        if self._check_negate(target):
            return None
        if any(tag in target.tags for tag in self.value):
            return 'danger'
        return None

class EffectiveTag(EffectiveIcon):
    nid = 'effective_tag'
    desc = "Item will be considered effective if the targeted enemy has any of the tags listed in this component."
    # requires = ['damage']
    tag = ItemTags.DEPRECATED

    expose = (ComponentType.List, ComponentType.Tag)
    value = []

    def dynamic_damage(self, unit, item, target, item2, mode, attack_info, base_value) -> int:
        if any(tag in target.tags for tag in self.value):
            if self._check_negate(target):
                return 0
            if item.data.get('effective_multiplier') is not None:
                might = item_system.damage(unit, item)
                if might is None:
                    return 0
                return int((item.data.get('effective_multiplier') - 1) * might)
            return item.data.get('effective', 0)
        return 0

class MagicHeal(Heal):
    nid = 'magic_heal'
    desc = "Heals the target for the specified integer + the HEAL equation defined in the equations editor. Will act oddly if no HEAL equation is defined."
    tag = ItemTags.DEPRECATED

    def _get_heal_amount(self, unit, target):
        empower_heal = skill_system.empower_heal(unit, target)
        empower_heal_received = skill_system.empower_heal_received(target, unit)
        return self.value + equations.parser.heal(unit) + empower_heal + empower_heal_received

class TextColor(ItemComponent):
    nid = 'text_color'
    desc = 'Special color for item text.'
    tag = ItemTags.DEPRECATED

    expose = (ComponentType.MultipleChoice, ['white'])
    value = 'white'

    def text_color(self, unit, item):
        if self.value not in ['white']:
            return 'white'
        return self.value
