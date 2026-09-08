from app.data.database.skill_components import SkillComponent, SkillTags
from app.data.database.components import ComponentType

from app.engine import equations, action, item_funcs, item_system
from app.engine.game_state import game

# status plugins
class Unselectable(SkillComponent):
    nid = 'unselectable'
    desc = "Unit cannot be selected"
    tag = SkillTags.BASE

    def can_select(self, unit) -> bool:
        return False

class CannotUseItems(SkillComponent):
    nid = 'cannot_use_items'
    desc = "Unit cannot use or equip any items"
    tag = SkillTags.BASE

    def available(self, unit, item) -> bool:
        return False

class CannotUseMagicItems(SkillComponent):
    nid = 'cannot_use_magic_items'
    desc = "Unit cannot use or equip magic items"
    tag = SkillTags.BASE

    def available(self, unit, item) -> bool:
        return not item_funcs.is_magic(unit, item)

class CannotTrade(SkillComponent):
    nid = 'cannot_trade'
    desc = "Unit cannot select Trade or be traded with"
    tag = SkillTags.BASE

    def no_trade(self, unit) -> bool:
        return True
        
class CannotAccessConvoy(SkillComponent):
    nid = 'cannot_access_convoy'
    desc = "Unit cannot access the convoy from the map.  Useful for generics and summons."
    tag = SkillTags.BASE

    def no_convoy(self, unit) -> bool:
        return True

class AdditionalAccessories(SkillComponent):
    nid = 'additional_accessories'
    desc = "Unit can hold additional accessories rather than regular items"
    tag = SkillTags.BASE

    expose = ComponentType.Int
    value = 2

    def num_items_offset(self, unit) -> int:
        return -1 * self.value

    def num_accessories_offset(self, unit) -> int:
        return self.value

class IgnoreAlliances(SkillComponent):
    nid = 'ignore_alliances'
    desc = "Unit will treat all units as enemies"
    tag = SkillTags.BASE

    def check_ally(self, unit1, unit2) -> bool:
        return unit1 is unit2

    def check_enemy(self, unit1, unit2) -> bool:
        return unit1 is not unit2

class ChangeAI(SkillComponent):
    nid = 'change_ai'
    desc = "Unit's AI is forcibly changed"
    tag = SkillTags.BASE

    expose = ComponentType.AI

    def change_ai(self, unit):
        return self.value

class ChangeBuyPrice(SkillComponent):
    nid = 'change_buy_price'
    desc = "Unit's buy price for items is changed"
    tag = SkillTags.BASE

    expose = ComponentType.Float

    def modify_buy_price(self, unit, item):
        return self.value

class ExpMultiplier(SkillComponent):
    nid = 'exp_multiplier'
    desc = "Unit receives a multiplier on exp gained"
    tag = SkillTags.BASE

    expose = ComponentType.Float

    def exp_multiplier(self, unit1, unit2):
        return self.value

class EnemyExpMultiplier(SkillComponent):
    nid = 'enemy_exp_multiplier'
    desc = "Unit gives a multiplier to the exp gained by others in combat"
    tag = SkillTags.BASE

    expose = ComponentType.Float

    def enemy_exp_multiplier(self, unit1, unit2):
        return self.value

class WexpMultiplier(SkillComponent):
    nid = 'wexp_multiplier'
    desc = "Unit receives a multiplier on wexp gained"
    tag = SkillTags.BASE

    expose = ComponentType.Float

    def wexp_multiplier(self, unit1, unit2):
        return self.value

class CanUseWeaponType(SkillComponent):
    nid = 'wexp_usable_skill'
    desc = 'Unit can use this weapon type, regardless of class'
    tag = SkillTags.BASE

    expose = ComponentType.WeaponType

    def usable_wtypes(self, unit):
        return self.value

class CannotUseWeaponType(SkillComponent):
    nid = 'wexp_unusable_skill'
    desc = 'Unit cannot use this weapon type, regardless of class'
    tag = SkillTags.BASE

    expose = ComponentType.WeaponType

    def forbidden_wtypes(self, unit):
        return self.value

class EnemyWexpMultiplier(SkillComponent):
    nid = 'enemy_wexp_multiplier'
    desc = "Unit gives a multiplier to the wexp gained by others in combat"
    tag = SkillTags.BASE

    expose = ComponentType.Float

    def enemy_wexp_multiplier(self, unit1, unit2):
        return self.value

class Locktouch(SkillComponent):
    nid = 'locktouch'
    desc = "Unit is able to unlock automatically"
    tag = SkillTags.BASE

    def can_unlock(self, unit, region):
        return True

class SightRangeBonus(SkillComponent):
    nid = 'sight_range_bonus'
    desc = "Unit gains a bonus to sight range"
    tag = SkillTags.BASE

    expose = ComponentType.Int
    value = 3

    def sight_range(self, unit):
        return self.value

class DecreasingSightRangeBonus(SkillComponent):
    nid = 'decreasing_sight_range_bonus'
    desc = "Unit gains a bonus to sight range that decreases by 1 each turn"
    tag = SkillTags.BASE

    expose = ComponentType.Int
    value = 3

    def init(self, skill):
        self.skill.data['torch_counter'] = 0

    def sight_range(self, unit):
        return max(0, self.value - self.skill.data['torch_counter'])

    def on_upkeep(self, actions, playback, unit):
        val = self.skill.data['torch_counter'] + 1
        action.do(action.UpdateFogOfWar(unit))
        action.do(action.SetObjData(self.skill, 'torch_counter', val))
        action.do(action.UpdateFogOfWar(unit))

class IgnoreFatigue(SkillComponent):
    nid = 'ignore_fatigue'
    desc = "Unit cannot gain fatigue"
    tag = SkillTags.BASE

    def ignore_fatigue(self, unit):
        return True

class SkillTag(SkillComponent):
    nid = 'skill_tags'
    desc = 'attach arbitrary tags to items. Useful for conditionals.'
    tag = SkillTags.BASE

    expose = (ComponentType.List, ComponentType.Tag)
    value = []
