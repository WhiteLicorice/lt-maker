from typing import Optional
from app.data.database.item_components import ItemComponent, ItemTags
from app.data.database.components import ComponentType

from app.utilities import utils
from app.engine import action, combat_calcs, item_funcs, image_mods, engine, item_system, skill_system
from app.engine.combat import playback as pb
from app.engine.source_type import SourceType

class EffectiveDamage(ItemComponent):
    nid = 'effective_damage'
    desc = 'If this item is effective against an enemy, its damage value will be multiplied and increased'
    tag = ItemTags.EXTRA

    expose = ComponentType.NewMultipleOptions

    options = {
        'effective_tags': (ComponentType.List, ComponentType.Tag),
        'effective_multiplier': ComponentType.Float,
        'effective_bonus_damage': ComponentType.Int,
        'show_effectiveness_flash': ComponentType.Bool,
        'weapon_effectiveness_multiplied': ComponentType.Bool,
    }

    def __init__(self, value=None):
        self.value = {
            'effective_tags': [],
            'effective_multiplier': 3,
            'effective_bonus_damage': 0,
            'show_effectiveness_flash': True,
            'weapon_effectiveness_multiplied': True,
        }
        if value:
            self.value.update(value)

    @property
    def tags(self):
        return self.value['effective_tags']

    @property
    def multiplier(self):
        return self.value['effective_multiplier']

    @property
    def bonus_damage(self):
        return self.value['effective_bonus_damage']

    @property
    def show_flash(self):
        return self.value['show_effectiveness_flash']

    @property
    def weapon_effectiveness_multiplied(self):
        return self.value['weapon_effectiveness_multiplied']

    def _check_effective(self, target):
        if self._check_negate(target):
            return False
        return any(tag in target.tags for tag in self.tags)

    def _check_negate(self, target) -> bool:
        # Returns whether it DOES negate the effectiveness
        # Still need to check negation (Fili Shield, etc.)
        if any(skill.negate for skill in target.skills if skill_system.condition(skill, target)):
            return True
        for skill in target.skills:
            # Do the tags match?
            if skill.negate_tags and skill.negate_tags.value and \
                    skill_system.condition(skill, target) and \
                    any(tag in self.tags for tag in skill.negate_tags.value):
                return True
        # No negation, so proceed with effective damage
        return False

    def item_icon_mod(self, unit, item, target, item2, sprite):
        if self.show_flash:
            if self._check_effective(target):
                sprite = image_mods.make_white(sprite.convert_alpha(), abs(250 - engine.get_time() % 500)/250)
        return sprite

    def target_icon(self, unit, item, target) -> Optional[str]:
        if item_funcs.available(unit, item) and skill_system.check_enemy(target, unit):
            if self._check_effective(target):
                return 'danger'
        return None

    def dynamic_damage(self, unit, item, target, item2, mode, attack_info, base_value) -> int:
        if self._check_effective(target):
            might = item_system.damage(unit, item) or 0
            if self.weapon_effectiveness_multiplied:
                adv = combat_calcs.compute_advantage(unit, target, item, item2)
                disadv = combat_calcs.compute_advantage(unit, target, item, item2, False)
                if adv:
                    might += int(adv.damage)
                if disadv:
                    might += int(disadv.damage)
            return int((self.multiplier - 1.0) * might + self.bonus_damage)
        return 0

class Brave(ItemComponent):
    nid = 'brave'
    desc = "Weapon has the brave property, doubling its attacks."
    tag = ItemTags.EXTRA

    def dynamic_multiattacks(self, unit, item, target, item2, mode, attack_info, base_value):
        return 1

class BraveOnAttack(ItemComponent):
    nid = 'brave_on_attack'
    desc = "The weapon is only brave when making an attack, and acts as a normal weapon when being attacked."
    tag = ItemTags.EXTRA

    def dynamic_multiattacks(self, unit, item, target, item2, mode, attack_info, base_value):
        return 1 if mode == 'attack' else 0

class Lifelink(ItemComponent):
    nid = 'lifelink'
    desc = "The unit heals this percentage of damage dealt to an enemy on hit. Chosen value should be between 0 and 1."
    # requires = ['damage']
    tag = ItemTags.EXTRA

    expose = ComponentType.Float
    value = 0.5

    def after_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        total_damage_dealt = 0
        playbacks = [p for p in playback if p.nid in ('damage_hit', 'damage_crit') and p.attacker == unit]
        for p in playbacks:
            total_damage_dealt += p.true_damage

        damage = utils.clamp(total_damage_dealt, 0, target.get_hp())
        true_damage = int(damage * self.value)
        actions.append(action.ChangeHP(unit, true_damage))

        playback.append(pb.HealHit(unit, item, unit, true_damage, true_damage))

class DamageOnMiss(ItemComponent):
    nid = 'damage_on_miss'
    desc = "Item deals a percentage of it's normal damage on a miss."
    tag = ItemTags.EXTRA

    expose = ComponentType.Float
    value = 0.5

    def on_miss(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        damage = combat_calcs.compute_damage(unit, target, item, target.get_weapon(), mode, attack_info)
        damage = int(damage * self.value)

        true_damage = min(damage, target.get_hp())
        actions.append(action.ChangeHP(target, -damage))

        # For animation
        playback.append(pb.DamageHit(unit, item, target, damage, true_damage))
        if true_damage == 0:
            playback.append(pb.HitSound('No Damage'))
            playback.append(pb.HitAnim('MapNoDamage', target))

class Eclipse(ItemComponent):
    nid = 'eclipse'
    desc = "Target loses half current HP on hit"
    tag = ItemTags.EXTRA

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        true_damage = damage = target.get_hp()//2
        actions.append(action.ChangeHP(target, -damage))

        # For animation
        playback.append(pb.DamageHit(unit, item, target, damage, true_damage))
        if true_damage == 0:
            playback.append(pb.HitSound('No Damage'))
            playback.append(pb.HitAnim('MapNoDamage', target))

class EclipseFE7(ItemComponent):
    nid = 'eclipse_fe7'
    desc = "Reduces target's HP to 1"
    tag = ItemTags.EXTRA

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        true_damage = damage = target.get_hp() - 1
        actions.append(action.ChangeHP(target, -damage))

        # For animation
        playback.append(pb.DamageHit(unit, item, target, damage, true_damage))
        if true_damage == 0:
            playback.append(pb.HitSound('No Damage'))
            playback.append(pb.HitAnim('MapNoDamage', target))

class NoDouble(ItemComponent):
    nid = 'no_double'
    desc = "Item cannot double"
    tag = ItemTags.EXTRA

    def can_double(self, unit, item):
        return False

class CannotCounter(ItemComponent):
    nid = 'cannot_counter'
    desc = "Item cannot counter"
    tag = ItemTags.EXTRA

    def can_counter(self, unit, item):
        return False

class CannotBeCountered(ItemComponent):
    nid = 'cannot_be_countered'
    desc = "Item cannot be countered"
    tag = ItemTags.EXTRA

    def can_be_countered(self, unit, item):
        return False

class IgnoreWeaponAdvantage(ItemComponent):
    nid = 'ignore_weapon_advantage'
    desc = "Any weapon advantage relationships defined in the weapon types editor are ignored by this item."
    tag = ItemTags.EXTRA

    def ignore_weapon_advantage(self, unit, item):
        return True

class Reaver(ItemComponent):
    nid = 'reaver'
    desc = "Weapon advantage relationships defined in the weapon types editor are doubled and reversed against this weapon. If two reaver weapons are in combat with each other weapon advantage works as normal. Identical to a custom_triangle_multiplier of -2.0."
    tag = ItemTags.EXTRA

    def modify_weapon_triangle(self, unit, item):
        return -2.0

class DoubleTriangle(ItemComponent):
    nid = 'double_triangle'
    desc = "The effects of weapon advantage relationships are doubled by this item. Identical to a custom_triangle_multiplier of 2.0."
    tag = ItemTags.EXTRA

    def modify_weapon_triangle(self, unit, item):
        return 2.0

class CustomTriangleMultiplier(ItemComponent):
    nid = 'custom_triangle_multiplier'
    desc = "Weapon advantage effects are multiplied by the provided value."
    tag = ItemTags.EXTRA

    expose = ComponentType.Float
    value = 1.0

    def modify_weapon_triangle(self, unit, item):
        return self.value

class WeaponTriangleOverride(ItemComponent):
    nid = 'weapon_triangle_override'
    desc = "The item is considered as this weapon type when solving for weapon triangle advantage/disadvantage."
    tag = ItemTags.EXTRA
    
    author = 'Eretein'
    
    expose = ComponentType.WeaponType

    def weapon_triangle_override(self, unit, item):
        return self.value

class StatusOnEquip(ItemComponent):
    nid = 'status_on_equip'
    desc = "A unit with this item equipped will receive the specified status."
    tag = ItemTags.EXTRA

    expose = ComponentType.Skill  # Nid

    def on_equip_item(self, unit, item):
        act = action.AddSkill(unit, self.value, source=item.uid, source_type=SourceType.ITEM)
        action.do(act)

    def on_unequip_item(self, unit, item):
        action.do(action.RemoveSkill(unit, self.value, count=1, source=item.uid, source_type=SourceType.ITEM))

class MultiStatusOnEquip(ItemComponent):
    nid = 'multi_status_on_equip'
    desc = "Item gives these statuses while equipped"
    tag = ItemTags.EXTRA

    expose = (ComponentType.List, ComponentType.Skill)  # Nid

    def on_equip_item(self, unit, item):
        for skl in self.value:
            act = action.AddSkill(unit, skl, source=item.uid, source_type=SourceType.ITEM)
            action.do(act)

    def on_unequip_item(self, unit, item):
        for skl in self.value:
            action.do(action.RemoveSkill(unit, skl, count=1, source=item.uid, source_type=SourceType.ITEM))

class StatusOnHold(ItemComponent):
    nid = 'status_on_hold'
    desc = "Item gives status while in unit's inventory"
    tag = ItemTags.EXTRA

    expose = ComponentType.Skill  # Nid

    def on_add_item(self, unit, item):
        action.do(action.AddSkill(unit, self.value, source=item.uid, source_type=SourceType.ITEM))

    def on_remove_item(self, unit, item):
        action.do(action.RemoveSkill(unit, self.value, count=1, source=item.uid, source_type=SourceType.ITEM))

class MultiStatusOnHold(ItemComponent):
    nid = 'multi_status_on_hold'
    desc = "Item gives these statuses while in unit's inventory"
    tag = ItemTags.EXTRA

    expose = (ComponentType.List, ComponentType.Skill)  # Nid

    def on_add_item(self, unit, item):
        for skl in self.value:
            act = action.AddSkill(unit, skl, source=item.uid, source_type=SourceType.ITEM)
            action.do(act)

    def on_remove_item(self, unit, item):
        for skl in self.value:
            action.do(action.RemoveSkill(unit, skl, count=1, source=item.uid, source_type=SourceType.ITEM))

class GainManaAfterCombat(ItemComponent):
    nid = 'gain_mana_after_combat'
    desc = "Takes a string that will be evaluated by python. At the end of combat the string is evaluated if the item was used and the result is translated into mana gained by the unit. If you want a flat gain of X mana, enter X, where X is an integer."
    tag = ItemTags.EXTRA
    author = 'KD'

    expose = ComponentType.String

    def end_combat(self, playback, unit, item, target, item2, mode):
        from app.engine import evaluate
        try:
            mana_gain = int(evaluate.evaluate(self.value, unit, target, position=unit.position))
            action.do(action.ChangeMana(unit, mana_gain))
        except Exception as e:
            print("Could not evaluate %s (%s)" % (self.value, e))
            return True