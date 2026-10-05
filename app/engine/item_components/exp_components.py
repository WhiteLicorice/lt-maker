from app.engine.exp_calculator import ExpCalcType, ExpCalculator

from app.data.database.database import DB

from app.data.database.item_components import ItemComponent, ItemTags
from app.data.database.components import ComponentType

from app.engine import skill_system, action
from app.utilities import utils

def determine_all_defenders(playback: list, attacker) -> set:
    # Returns defenders that were hit
    marks = [mark for mark in playback if mark.nid == 'mark_hit']
    marks += [mark for mark in playback if mark.nid == 'mark_crit']
    marks = [mark for mark in marks if mark.attacker == attacker]
    damage_marks = [mark for mark in playback if mark.nid == 'damage_hit']
    damage_marks = [mark for mark in damage_marks if mark.attacker == attacker and skill_system.check_enemy(attacker, mark.defender)]
    all_defenders = set()
    for mark in marks + damage_marks:
        if 'Tile' in mark.defender.tags:
            continue  # Don't count tiles
        all_defenders.add(mark.defender) 
    return all_defenders

def determine_all_damaged_defenders(playback: list, attacker) -> set:
    # Returns defenders that were hit
    damage_marks = [mark for mark in playback if mark.nid in ('damage_hit', 'damage_crit')]
    damage_marks = [mark for mark in damage_marks if
                    mark.attacker == attacker and
                    skill_system.check_enemy(attacker, mark.defender) and
                    mark.true_damage != 0]
    all_defenders = set()
    for mark in damage_marks:
        if 'Tile' in mark.defender.tags: 
            continue  # Don't count tiles
        all_defenders.add(mark.defender)
    return all_defenders

def determine_all_healed_defenders(playback: list, attacker) -> set:
    healing_marks = [mark for mark in playback if mark.nid == 'heal_hit' and mark.attacker == attacker]
    healing_marks = [mark for mark in healing_marks if 
                     skill_system.check_ally(attacker, mark.defender) and
                     mark.true_damage > 0]
    all_defenders = set()
    for mark in healing_marks:
        if 'Tile' in mark.defender.tags:
            continue  # Don't count tiles
        all_defenders.add(mark.defender)
    return all_defenders

def modify_exp(exp, attacker, defender):
    self_mult = skill_system.exp_multiplier(attacker, defender)
    exp *= self_mult
    if not defender:
        return exp

    enemy_mult = skill_system.enemy_exp_multiplier(defender, attacker)
    exp *= enemy_mult
    if not defender.is_dying:
        return exp
        
    exp *= float(DB.constants.value('kill_multiplier'))
    if 'Boss' in defender.tags and DB.constants.value('exp_formula') != ExpCalcType.CLASSIC.value:
        # CLASSIC exp formula already added boss_bonus in a different way
        exp += int(DB.constants.value('boss_bonus') * self_mult * enemy_mult)
    return exp

class Exp(ItemComponent):
    nid = 'exp'
    desc = "Item gives a fixed integer of EXP each use. Useful for staves like Warp or Rescue."
    tag = ItemTags.EXP

    expose = ComponentType.Int
    value = 15

    def exp(self, playback, unit, item) -> int:
        total_exp = 0
        defenders = determine_all_defenders(playback, unit)
        for defender in defenders:
            exp = self.value
            exp = modify_exp(exp, unit, defender)
            total_exp += exp
        total_exp = utils.clamp(int(total_exp), DB.constants.value('min_exp'), 100)
        return total_exp

class LevelExp(ItemComponent):
    nid = 'level_exp'
    desc = "Gives EXP based on the level difference between attacker and defender. How EXP is normally calculated for weapons. Equation for EXP can be edited in the Constants menu."
    tag = ItemTags.EXP

    def _calc_exp(self, unit, target):
        if DB.constants.value('promote_level_reset'):
            level_diff = target.get_internal_level() - unit.get_internal_level()
        else:
            level_diff = target.level - unit.level
        if DB.constants.value('exp_formula') == ExpCalcType.STANDARD.value:
            return ExpCalculator.standard_curve_calculator(
                level_diff,
                DB.constants.value('exp_offset'),
                DB.constants.value('exp_curve'),
                DB.constants.value('exp_magnitude'))
        elif DB.constants.value('exp_formula') == ExpCalcType.GOMPERTZ.value:
            return ExpCalculator.gompertz_curve_calculator(
                level_diff,
                DB.constants.value('gexp_max'),
                DB.constants.value('gexp_min'),
                DB.constants.value('gexp_slope'),
                DB.constants.value('gexp_intercept'))
        elif DB.constants.value('exp_formula') == ExpCalcType.CLASSIC.value:
            return ExpCalculator.classic_curve_calculator(
                unit,
                target,
                DB.classes.get(unit.klass),
                DB.classes.get(target.klass),
                DB.constants.value('cexp_damage_bonus'),
                DB.constants.value('cexp_kill_bonus'),
                DB.constants.value('boss_bonus'),
                DB.constants.value('cexp_thief_bonus'),
                DB.constants.value('cexp_thief_list'),
                DB.constants.value('cexp_class_bonus_a'),
                DB.constants.value('cexp_class_bonus_a_tier'),
                DB.constants.value('cexp_class_bonus_b'),
                DB.constants.value('cexp_class_bonus_b_tier'),
                DB.constants.value('cexp_class_bonus_b1'),
                DB.constants.value('cexp_class_bonus_b1_list'),
                DB.constants.value('cexp_class_power_1'),
                DB.constants.value('cexp_class_power_1_list'),
                DB.constants.value('cexp_class_power_1_tier'),
                DB.constants.value('cexp_class_power_2'),
                DB.constants.value('cexp_class_power_2_list'),
                DB.constants.value('cexp_class_power_3'),
                DB.constants.value('cexp_class_power_4'),
                DB.constants.value('cexp_class_power_4_tier'),
                DB.constants.value('cexp_mode_coeff'))
        else:
            return 0

    def exp(self, playback, unit, item) -> int:
        total_exp = 0
        defenders = determine_all_damaged_defenders(playback, unit)
        for defender in defenders:
            exp = self._calc_exp(unit, defender)
            exp = modify_exp(exp, unit, defender)
            total_exp += exp
        total_exp = utils.clamp(int(total_exp), DB.constants.value('min_exp'), 100)
        return total_exp

class HealExp(ItemComponent):
    nid = 'heal_exp'
    desc = "Item gives exp to user based on amount of damage healed"
    tag = ItemTags.EXP

    def _calc_exp(self, unit, healing_done):
        if DB.constants.value('promote_level_reset'):
            heal_diff = healing_done - unit.get_internal_level()
        else:
            heal_diff = healing_done - unit.level
        heal_diff += DB.constants.get('heal_offset').value
        exp_gained = DB.constants.get('heal_curve').value * heal_diff
        exp_gained += DB.constants.get('heal_magnitude').value
        exp_gained = max(exp_gained, DB.constants.get('heal_min').value)
        return exp_gained

    def exp(self, playback, unit, item) -> int:
        total_exp = 0
        defenders = determine_all_healed_defenders(playback, unit)
        for defender in defenders:
            healing_done = 0
            for brush in playback:
                if brush.nid == 'heal_hit' and brush.attacker == unit and brush.defender == defender:
                    healing_done += brush.true_damage
            if healing_done <= 0:
                continue
            exp_gained = self._calc_exp(unit, healing_done)
            total_exp += exp_gained
        total_exp = utils.clamp(int(total_exp), 0, 100)
        return total_exp

class Wexp(ItemComponent):
    nid = 'wexp'
    desc = "Item gives a custom number of wexp to user while using"
    tag = ItemTags.EXP

    expose = ComponentType.Int
    value = 2

    def wexp(self, playback, unit, item, target):
        return self.value - 1  # Because 1 will already be given by WeaponComponent

class Fatigue(ItemComponent):
    nid = 'fatigue'
    desc = "If fatigue is enabled, increases the amount of fatigue a user suffers while using this item. Can be negative in order to remove fatigue."
    tag = ItemTags.EXP

    expose = ComponentType.Int
    value = 1

    def end_combat(self, playback, unit, item, target, item2, mode):
        if mode != 'attack':
            return
        marks = [mark for mark in playback if mark.nid.startswith('mark') and mark.attacker is unit and mark.item is item]
        if marks:
            action.do(action.ChangeFatigue(unit, self.value))
