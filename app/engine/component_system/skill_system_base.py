from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from app.engine.component_system import utils
from app.engine.utils.ltcache import ltcached

if TYPE_CHECKING:
    from app.engine.objects.item import ItemObject
    from app.engine.objects.unit import UnitObject

class Defaults():
    @staticmethod
    def can_select(unit) -> bool:
        return unit.team == 'player'

    @staticmethod
    def check_ally(unit1, unit2) -> bool:
        from app.data.database.database import DB
        if unit1 is unit2:
            return True
        elif unit2.team in DB.teams.get_allies(unit1.team):
            return True
        else:
            return unit2.team == unit1.team
        return False

    @staticmethod
    def check_enemy(unit1, unit2) -> bool:
        from app.data.database.database import DB
        if unit2.team in DB.teams.get_allies(unit1.team):
            return False
        else:
            return unit2.team != unit1.team
        return True

    @staticmethod
    def can_trade(unit1, unit2) -> bool:
        return unit1.team == unit2.team and check_ally(unit1, unit2) and not no_trade(unit1) and not no_trade(unit2)

    @staticmethod
    def num_items_offset(unit) -> int:
        return 0

    @staticmethod
    def num_accessories_offset(unit) -> int:
        return 0

    @staticmethod
    def witch_warp(unit) -> list:
        return []

    @staticmethod
    def exp_multiplier(unit1, unit2) -> float:
        return 1.0

    @staticmethod
    def enemy_exp_multiplier(unit1, unit2) -> float:
        return 1.0

    @staticmethod
    def wexp_multiplier(unit1, unit2) -> float:
        return 1.0

    @staticmethod
    def enemy_wexp_multiplier(unit1, unit2) -> float:
        return 1.0

    @staticmethod
    def change_variant(unit) -> str:
        return unit.variant

    @staticmethod
    def change_animation(unit) -> str:
        return None

    @staticmethod
    def change_ai(unit) -> str:
        return unit.ai

    @staticmethod
    def change_roam_ai(unit) -> str:
        return unit.roam_ai

    @staticmethod
    def has_canto(unit1, target) -> bool:
        return False

    @staticmethod
    def empower_heal(unit1, unit2) -> int:
        return 0

    @staticmethod
    def empower_heal_received(unit2, unit1) -> int:
        return 0

    @staticmethod
    def limit_maximum_range(unit, item) -> int:
        return 1000

    @staticmethod
    def movement_type(unit):
        return None

    @staticmethod
    def sight_range(unit):
        return 0

    @staticmethod
    def xcom_movement(unit):
        return 0

    @staticmethod
    def empower_splash(unit):
        return 0

    @staticmethod
    def modify_buy_price(unit, item) -> float:
        return 1.0

    @staticmethod
    def modify_sell_price(unit, item) -> float:
        return 1.0

    @staticmethod
    def damage_formula(unit) -> str:
        return 'DAMAGE'

    @staticmethod
    def resist_formula(unit) -> str:
        return 'DEFENSE'

    @staticmethod
    def accuracy_formula(unit) -> str:
        return 'HIT'

    @staticmethod
    def avoid_formula(unit) -> str:
        return 'AVOID'

    @staticmethod
    def crit_accuracy_formula(unit) -> str:
        return 'CRIT_HIT'

    @staticmethod
    def crit_avoid_formula(unit) -> str:
        return 'CRIT_AVOID'

    @staticmethod
    def attack_speed_formula(unit) -> str:
        return 'ATTACK_SPEED'

    @staticmethod
    def defense_speed_formula(unit) -> str:
        return 'DEFENSE_SPEED'

    @staticmethod
    def critical_multiplier_formula(unit) -> str:
        return 'CRIT_MULT'

    @staticmethod
    def critical_addition_formula(unit) -> str:
        return 'CRIT_ADD'

    @staticmethod
    def thracia_critical_multiplier_formula(unit) -> str:
        return 'THRACIA_CRIT'

@ltcached
def condition(skill, unit: UnitObject, item=None) -> bool:
    # print('Checking condition for', skill, unit, item)
    if not item:
        item = unit.equipped_weapon
    for component in skill.components:
        if component.defines('condition'):
            if not component.condition(unit, item):
                return False
    return True

def is_grey(skill, unit) -> bool:
    return (not condition(skill, unit) and skill.grey_if_inactive)

def hidden(skill, unit) -> bool:
    return skill.hidden or skill.is_terrain or (skill.hidden_if_inactive and not condition(skill, unit))

def stat_change(unit, stat_nid) -> int:
    bonus = 0
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('stat_change'):
                d = component.stat_change(unit)
                d_bonus = d.get(stat_nid, 0)
                if d_bonus == 0:
                    continue
                # Why did we write the component condition check after the evaluation of the bonus?
                # Was there a good reason?
                if component.ignore_conditional or condition(skill, unit):
                    bonus += d_bonus
    return bonus

def subtle_stat_change(unit, stat_nid) -> int:
    bonus = 0
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('subtle_stat_change'):
                d = component.subtle_stat_change(unit)
                d_bonus = d.get(stat_nid, 0)
                if d_bonus == 0:
                    continue
                if component.ignore_conditional or condition(skill, unit):
                    bonus += d_bonus
    return bonus

def stat_change_contribution(unit, stat_nid) -> dict:
    contribution = {}
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('stat_change') and not component.defines('subtle_stat_change'):
                if component.ignore_conditional or condition(skill, unit):
                    d = component.stat_change(unit)
                    val = d.get(stat_nid, 0)
                    if val != 0:
                        if skill.name in contribution:
                            contribution[skill.name] += val
                        else:
                            contribution[skill.name] = val
    return contribution

def growth_change(unit, stat_nid) -> int:
    bonus = 0
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('growth_change'):
                if component.ignore_conditional or condition(skill, unit):
                    d = component.growth_change(unit)
                    bonus += d.get(stat_nid, 0)
    return bonus

def unit_sprite_flicker_tint(unit) -> list:
    flicker = []
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('unit_sprite_flicker_tint'):
                if component.ignore_conditional or condition(skill, unit):
                    d = component.unit_sprite_flicker_tint(unit, skill)
                    flicker.append(d)
    return flicker

def should_draw_anim(unit) -> list:
    avail = []
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('should_draw_anim'):
                if component.ignore_conditional or condition(skill, unit):
                    d = component.should_draw_anim(unit, skill)
                    avail.append(d)
    return avail

def additional_tags(unit) -> set:
    new_tags = set()
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('additional_tags'):
                if component.ignore_conditional or condition(skill, unit):
                    new_tags = new_tags | set(component.additional_tags(unit, skill))
    return new_tags

def before_crit(actions, playback, attacker, item, defender, item2, mode, attack_info) -> bool:
    for skill in attacker.skills:
        for component in skill.components:
            if component.defines('before_crit'):
                component.before_crit(actions, playback, attacker, item, defender, item2, mode, attack_info)

def on_end_chapter(unit, skill):
    for component in skill.components:
        if component.defines('on_end_chapter'):
            if component.ignore_conditional or condition(skill, unit):
                component.on_end_chapter(unit, skill)
        if component.defines('on_end_chapter_unconditional'):
            component.on_end_chapter_unconditional(unit, skill)

def init(skill):
    """
    Initializes any data on the parent skill if necessary
    """
    for component in skill.components:
        if component.defines('init'):
            component.init(skill)

def before_add(unit, skill):
    for component in skill.components:
        if component.defines('before_add'):
            component.before_add(unit, skill)
    for other_skill in unit.skills:
        for component in other_skill.components:
            if component.defines('before_gain_skill'):
                component.before_gain_skill(unit, skill)

def after_add(unit, skill):
    for component in skill.components:
        if component.defines('after_add'):
            component.after_add(unit, skill)
    for other_skill in unit.skills:
        for component in other_skill.components:
            if component.defines('after_gain_skill'):
                component.after_gain_skill(unit, skill)

def before_remove(unit, skill):
    for component in skill.components:
        if component.defines('before_remove'):
            component.before_remove(unit, skill)

def after_remove(unit, skill):
    for component in skill.components:
        if component.defines('after_remove'):
            component.after_remove(unit, skill)

def after_add_from_restore(unit, skill):
    for component in skill.components:
        if component.defines('after_add_from_restore'):
            component.after_add_from_restore(unit, skill)

def before_true_remove(unit, skill):
    """
    This does not intrinsically interact with the turnwheel
    It only fires when the skill is actually removed for the first time
    Not on execute or reverse
    """
    for component in skill.components:
        if component.defines('before_true_remove'):
            component.before_true_remove(unit, skill)

def after_true_remove(unit, skill):
    """
    This does not intrinsically interact with the turnwheel
    It only fires when the skill is actually removed for the first time
    Not on execute or reverse
    """
    for component in skill.components:
        if component.defines('after_true_remove'):
            component.after_true_remove(unit, skill)

def get_text(skill) -> str:
    for component in skill.components:
        if component.defines('text'):
            return component.text()
    return None

def get_cooldown(skill) -> float:
    for component in skill.components:
        if component.defines('cooldown'):
            return component.cooldown()
    return None

def get_hide_skill_icon(unit, skill) -> bool:
    # Check if we should be hiding this skill
    for component in skill.components:
        if component.defines('hide_skill_icon') and \
                component.hide_skill_icon(unit):
            return True
    return False

def get_show_skill_icon(unit, skill) -> bool:
    for component in skill.components:
        if component.defines('show_skill_icon') and \
                (component.ignore_conditional or condition(skill, unit)) and \
                component.show_skill_icon(unit):
            return True
    return False
    
def get_shape(unit, skill) -> set[tuple]:
    #Get a set of all tiles this skill should affect
    for component in skill.components:
        if component.defines('get_shape'):
            return component.get_shape(unit, skill)
    return None
    
def get_max_shape_range(skill) -> int:
    #Get the maximum manhattan distance to tiles skill affects
    for component in skill.components:
        if component.defines('get_max_shape_range'):
            return component.get_max_shape_range(skill)
    return None
    
def trigger_charge(unit, skill):
    for component in skill.components:
        if component.defines('trigger_charge'):
            component.trigger_charge(unit, skill)
    return None

def get_extra_abilities(unit: UnitObject, categorized: bool = False):
    """Returns a dict of extra ability names to corresponding skill item.

    Args:
        unit (UnitObject): Unit extra ability belong to.
        categorized (bool, optional): Whether to categorize extra abilities. Defaults to False.

    Returns:
        ExtraAbilityDict | CategorizedExtraAbilityDict: A dict that defines extra abilities,
        or a dict with category names defined by a MenuCategory component that map to extra
        abilities that belong in that category.
    """
    abilities = defaultdict(dict) if categorized else {}
    for skill in unit.skills:
        ability_comps = [] # keep behavior from previous implementation
        category = None
        for component in skill.components:
            if component.defines('extra_ability'):
                if component.ignore_conditional or condition(skill, unit):
                    new_item = component.extra_ability(unit)
                    ability_name = new_item.name
                    ability_comps.append((ability_name, new_item))
            if component.defines('menu_category'):
                category = component.menu_category()
        if ability_comps:
            for ability_name, new_item in ability_comps:
                category = '_uncategorized' if category is None else category
                if categorized:
                    abilities[category][ability_name] = new_item
                else:
                    abilities[ability_name] = new_item

    return abilities

def ai_priority_multiplier(unit) -> float:
    ai_priority_multiplier = 1
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('ai_priority_multiplier'):
                if component.ignore_conditional or condition(skill, unit):
                    ai_priority_multiplier *= component.ai_priority_multiplier(unit)
    return ai_priority_multiplier

def get_combat_arts(unit: UnitObject, categorized: bool = False):
    """Returns a dict of combat art names to corresponding skill and weapons.

    Args:
        unit (UnitObject): Unit combat arts belong to.
        categorized (bool, optional): Whether to categorize combat arts. Defaults to False.

    Returns:
        CombatArtDict | CategorizedCombatArtDict: A dict that defines combat arts, or a dict
        with category names defined by a MenuCategory component that map to combat arts that
        belong in that category.
    """
    from app.engine import action, item_funcs
    from app.engine.game_state import game
    combat_arts = defaultdict(dict) if categorized else {}
    unit_skills = unit.skills[:]
    for skill in unit_skills:
        if not condition(skill, unit):
            continue
        combat_art = None
        combat_art_weapons = [item for item in item_funcs.get_all_items(unit) if item_funcs.available(unit, item)]
        category = None
        for component in skill.components:
            if component.defines('combat_art'):
                combat_art = component.combat_art(unit)
            if component.defines('weapon_filter'):
                combat_art_weapons = \
                    [item for item in combat_art_weapons if component.weapon_filter(unit, item)]
            if component.defines('menu_category'):
                category = component.menu_category()

        if combat_art and combat_art_weapons:
            good_weapons = []
            # Check which of the good weapons meet the range requirements
            for weapon in combat_art_weapons:
                # activate_combat_art(unit, skill)
                act = action.AddSkill(unit, skill.combat_art.value)
                act.do()
                targets = game.target_system.get_valid_targets(unit, weapon)
                act.reverse()
                # deactivate_combat_art(unit, skill)
                if targets:
                    good_weapons.append(weapon)

            if good_weapons:
                category = '_uncategorized' if category is None else category
                if categorized:
                    combat_arts[category][skill.name] = (skill, good_weapons)
                else:
                    combat_arts[skill.name] = (skill, good_weapons)

    return combat_arts

def activate_combat_art(unit, skill):
    for component in skill.components:
        if component.defines('on_activation'):
            component.on_activation(unit)

def deactivate_combat_art(unit, skill):
    for component in skill.components:
        if component.defines('on_deactivation'):
            component.on_deactivation(unit)

def deactivate_all_combat_arts(unit):
    for skill in unit.skills:
        deactivate_combat_art(unit, skill)

def on_pairup(unit, leader):
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('on_pairup'):
                component.on_pairup(unit, leader)

def on_separate(unit, leader):
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('on_separate'):
                component.on_separate(unit, leader)

item_override_recursion_stack = set()
def item_override(unit, item: ItemObject):
    all_override_components = []
    components_so_far = set()
    if not unit or not item:
        return all_override_components
    for skill in reversed(unit.skills):
        for component in skill.components:
            if component.nid == 'item_override':
                # Conditions for item overrides might rely on e.g.
                # what item is equipped, which would itself
                # make an item override call on the same skill.
                # Therefore, we simply assume - probably safely -
                # that the skill cannot influence its own condition.
                if skill.nid not in item_override_recursion_stack:
                    item_override_recursion_stack.add(skill.nid)
                    if condition(skill, unit):
                        new_override_components = list(component.get_components(unit))
                        new_override_components = [comp for comp in new_override_components if comp.nid not in components_so_far]
                        components_so_far |= set([comp.nid for comp in new_override_components])
                        all_override_components += new_override_components
                    item_override_recursion_stack.remove(skill.nid)
                break
    return all_override_components
