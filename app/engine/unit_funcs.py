from __future__ import annotations

from typing import Dict, List, Optional, Set, TYPE_CHECKING
from app.data.database.database import DB
from app.data.database.difficulty_modes import GrowthOption
from app.engine import item_funcs, skill_system
from app.engine.game_state import game
from app.events import triggers
from app.utilities import utils, static_random

if TYPE_CHECKING:
    from app.data.database.units import UnitPrefab
    from app.engine.objects.region import RegionObject
    from app.engine.objects.skill import SkillObject
    from app.engine.objects.unit import UnitObject

import logging

from app.utilities.typing import NID

def get_leveling_method(unit, custom_method=None) -> str:
    if custom_method:
        method = custom_method.capitalize()
    elif unit.team == 'player':
        method = game.current_mode.growths
    else:
        method = DB.constants.value('enemy_leveling')
        if method == 'Match':
            method = game.current_mode.growths
    return method

def growth_rate(unit: UnitObject, nid: NID) -> int:
    """
    Calculates the growth rate of a unit for a given stat.

    Args:
        unit (UnitObject): The unit for which to calculate the growth rate.
        nid (NID): The NID (Name IDentifier) of the stat.

    Returns:
        int: The calculated growth rate.
    """
    klass = DB.classes.get(unit.klass)
    difficulty_growth_bonus = game.mode.get_growth_bonus(unit, DB)
    growth = unit.growths[nid] + unit.growth_bonus(nid) + klass.growth_bonus.get(nid, 0) + difficulty_growth_bonus.get(nid, 0)
    return growth

def growth_contribution(unit: UnitObject, nid: NID) -> Dict[str, int]:
    """
    Calculates the growth rate of a unit for a given stat and returns it individually as dict elements.

    Args:
        unit (UnitObject): The unit for which to calculate the growth rate.
        nid (NID): The NID (Name IDentifier) of the stat.

    Returns:
        Dict[str, int]: The calculated growth rates
    """
    growth_rates = {}
    klass = DB.classes.get(unit.klass)
    base_growths = unit.growths[nid]
    klass_growths = klass.growth_bonus.get(nid, 0)
    if DB.constants.value('alt_growth_format'):
        growth_rates["Base Value"] = base_growths + klass_growths
    else:
        growth_rates["Base Value"] = base_growths
        if klass_growths != 0:
            growth_rates["Class Bonus"] = klass_growths
    difficulty_growths = game.mode.get_growth_bonus(unit, DB).get(nid, 0)
    if difficulty_growths != 0:
        growth_rates["Difficulty Bonus"] = difficulty_growths
    other_growths = unit.growth_bonus(nid)
    if other_growths != 0:
        growth_rates["Other Bonuses"] = other_growths
    return growth_rates

def base_growth_rate(unit: UnitObject, nid: NID) -> int:
    """
    Calculates the base growth rate of a unit for a given stat.
    Base growth rate can either be unit growths or unit growths + klass growths depending on DB settings.

    Args:
        unit (UnitObject): The unit for which to calculate the base growth rate.
        nid (NID): The NID (Name IDentifier) of the stat.

    Returns:
        int: The calculated base growth rate.
    """
    if DB.constants.value('alt_growth_format'):
        klass = DB.classes.get(unit.klass)
        return unit.growths[nid] + klass.growth_bonus.get(nid, 0)
    else:
        return unit.growths[nid]

def difficulty_growth_rate(unit: UnitObject, nid: NID) -> int:
    """
    Calculates the additional growth rate that comes from the difficulty mode for a unit for a given stat.

    Args:
        unit (UnitObject): The unit for which to calculate the difficulty growth rate.
        nid (NID): The NID (Name IDentifier) of the stat.

    Returns:
        int: The calculated difficulty growth rate.
    """
    difficulty_growth_bonus = game.mode.get_growth_bonus(unit, DB)
    return difficulty_growth_bonus.get(nid, 0)

def _fixed_levelup(unit, level, get_growth_rate=growth_rate) -> dict:
    stat_changes = {nid: 0 for nid in DB.stats.keys()}

    for nid in DB.stats.keys():
        growth = get_growth_rate(unit, nid)
        if growth > 0:
            stat_changes[nid] += growth // 100
            growth %= 100
            growth_inc = (50 + growth * level) % 100
            if growth_inc < growth:
                stat_changes[nid] += 1
        elif growth < 0 and DB.constants.value('negative_growths'):
            stat_changes[nid] -= abs(growth) // 100
            growth = -(abs(growth) % 100)
            growth_inc = (50 + growth * level) % 100
            if growth_inc > 100 - growth or growth_inc == 0:
                stat_changes[nid] -= 1
    return stat_changes

def _random_levelup(unit, level) -> dict:
    rng = static_random.get_levelup(unit.nid, level)
    stat_changes = {nid: 0 for nid in DB.stats.keys()}

    for nid in DB.stats.keys():
        growth = growth_rate(unit, nid)
        counter = 0
        if growth > 0:
            while growth > 0:
                counter += 1 if rng.randint(0, 99) < growth else 0
                growth -= 100
        elif growth < 0 and DB.constants.value('negative_growths'):
            growth = -growth
            while growth > 0:
                counter -= 1 if rng.randint(0, 99) < growth else 0
                growth -= 100
        stat_changes[nid] += counter
    return stat_changes

def _dynamic_levelup(unit, level) -> dict:
    """
    Does not support leveling down 100% because it keeps state
    """
    variance = 10
    rng = static_random.get_levelup(unit.nid, level)
    stat_changes = {nid: 0 for nid in DB.stats.keys()}

    for nid in DB.stats.keys():
        growth = growth_rate(unit, nid)
        if growth > 0:
            free_stat_ups = growth // 100
            stat_changes[nid] += free_stat_ups
            new_growth = growth % 100
            start_growth = new_growth + unit.growth_points[nid]
            if rng.randint(0, 99) < int(start_growth):
                stat_changes[nid] += 1
                unit.growth_points[nid] -= (100 - new_growth) / variance
            else:
                unit.growth_points[nid] += new_growth / variance

        elif growth < 0 and DB.constants.value('negative_growths'):
            growth = -growth
            free_stat_downs = growth // 100
            stat_changes[nid] -= free_stat_downs
            new_growth = growth % 100
            start_growth = new_growth + unit.growth_points[nid]
            if rng.randint(0, 99) < int(start_growth):
                stat_changes[nid] -= 1
                unit.growth_points[nid] -= (100 - new_growth) / variance
            else:
                unit.growth_points[nid] += new_growth / variance

    return stat_changes

def _rd_bexp_levelup(unit, level):
    """
    Negative growth rates are ignored
    Leveling down will not work when any stat is capped
    """
    num_choices = 3
    rng = static_random.get_levelup(unit.nid, level)
    stat_changes = {nid: 0 for nid in DB.stats.keys()}

    growths: list = []
    for stat in DB.stats:
        nid = stat.nid
        growth = growth_rate(unit, nid)
        max_stat = unit.get_stat_cap(nid)
        if unit.stats[nid] < max_stat and unit.growths[nid] != 0:
            growths.append(max(growth, 0))
        else:  # Cannot increase this one at all
            growths.append(0)

    for _ in range(num_choices):
        if sum(growths) <= 0:
            break
        choice_idx = static_random.weighted_choice(growths, rng)
        nid = [stat.nid for stat in DB.stats][choice_idx]
        stat_changes[nid] += 1
        growths[choice_idx] = max(0, growths[choice_idx] - 100)
        max_stat = unit.get_stat_cap(nid)
        if unit.stats[nid] + stat_changes[nid] >= max_stat:
            growths[choice_idx] = 0

    return stat_changes

def get_next_level_up(unit: UnitObject, level: int, custom_method: Optional[str] = None) -> Dict[NID, int]:
    """
    Determines the unit's next level-up stat changes based on its current level and the leveling method.

    If you are using 'Dynamic' leveling method, does modify the state of the unit's growth points.
    Otherwise, this function does not actually change anything about the unit

    Args:
        unit (UnitObject): The unit for which to determine the next level-up stat changes.
        level (int): The current level of the unit.
        custom_method (Optional[str]): A custom leveling method to use. Defaults to None.

    Returns:
        dict (Dict[NID, int]): A dictionary containing the next level-up stat changes for the unit.
    """
    method = get_leveling_method(unit, custom_method)

    stat_changes = {nid: 0 for nid in DB.stats.keys()}
    if method == 'Bexp':
        stat_changes = _rd_bexp_levelup(unit, level)
    elif method == GrowthOption.FIXED:
        stat_changes = _fixed_levelup(unit, level)
    elif method == GrowthOption.RANDOM:
        stat_changes = _random_levelup(unit, level)
    elif method == GrowthOption.DYNAMIC:
        stat_changes = _dynamic_levelup(unit, level)
    else:
        logging.error("Could not find level_up method matching %s", method)

    for nid in DB.stats.keys():
        max_stat = unit.get_stat_cap(nid)
        stat_changes[nid] = utils.clamp(stat_changes[nid], -unit.stats[nid], max_stat - unit.stats[nid])
    return stat_changes

def auto_level(unit: UnitObject, base_level: int, num_levels: int, custom_method: Optional[str] = None) -> Dict[NID, int]:
    """
    Levels up a unit's stats for a specified number of levels. Primarily used for generics.

    This does modify the stats and growth points of the unit. After this runs, it resets 
    the unit's current hp and current mana to their full value.

    Args:
        unit (UnitObject): The unit to level up.
        base_level (int): The base level of the unit.
        num_levels (int): The number of levels to increase or decrease.
        custom_method (Optional[str]): A custom leveling method to use. Defaults to None.

    Returns:
        dict (Dict[NID, int]): A dictionary containing the total stat changes after auto-leveling.
    """
    total_stat_changes = {nid: 0 for nid in DB.stats.keys()}

    if num_levels > 0:
        for i in range(num_levels):
            level = base_level + i
            stat_changes = get_next_level_up(unit, level, custom_method)
            # Add to total
            for nid in total_stat_changes.keys():
                total_stat_changes[nid] += stat_changes[nid]

    elif num_levels < 0:
        ending_level = base_level + num_levels
        for level in reversed(range(ending_level, base_level)):
            stat_changes = get_next_level_up(unit, level, custom_method)
            # Add reversed stat_changes to total
            for nid in total_stat_changes.keys():
                total_stat_changes[nid] -= stat_changes[nid]

    for nid in DB.stats.keys():
        max_stat = unit.get_stat_cap(nid)
        total_stat_changes[nid] = utils.clamp(total_stat_changes[nid], -unit.stats[nid], max_stat - unit.stats[nid])

    for nid in total_stat_changes.keys():
        unit.stats[nid] += total_stat_changes[nid]
    unit.set_hp(1000)  # Go back to full hp
    unit.set_mana(1000)  # Go back to full mana
    return total_stat_changes

def difficulty_auto_level(unit: UnitObject, base_level: int, num_levels: int) -> Dict[NID, int]:
    """
    Levels up a unit's stats for a specified number of levels based on the growth points
    that the current difficulty adds to the unit.

    This does modify the stats and growth points of the unit. After this runs, it resets 
    the unit's current hp and current mana to their full value.

    Args:
        unit (UnitObject): The unit to level up.
        base_level (int): The base level of the unit.
        num_levels (int): The number of levels to increase or decrease.

    Returns:
        dict (Dict[NID, int]): A dictionary containing the total stat changes after auto-leveling.
    """
    total_stat_changes = {nid: 0 for nid in DB.stats.keys()}
    if num_levels > 0:
        for i in range(num_levels):
            stat_changes = _fixed_levelup(unit, base_level + i, difficulty_growth_rate)
            # Add to total
            for nid in total_stat_changes.keys():
                total_stat_changes[nid] += stat_changes[nid]
    # No reason to be less than 0

    for nid in DB.stats.keys():
        max_stat = unit.get_stat_cap(nid)
        total_stat_changes[nid] = utils.clamp(total_stat_changes[nid], -unit.stats[nid], max_stat - unit.stats[nid])

    for nid in total_stat_changes.keys():
        unit.stats[nid] += total_stat_changes[nid]
    unit.set_hp(1000)  # Go back to full hp
    unit.set_mana(1000)  # Go back to full mana
    return total_stat_changes

def apply_stat_changes(unit: UnitObject, stat_changes: Dict[NID, int], increase_current_stats: bool = True) -> None:
    """
    Applies the given stat changes to the unit's stats.

    Args:
        unit (UnitObject): The unit to which the stat changes should be applied.
        stat_changes (Dict[NID, int]): A dictionary containing the stat changes to apply.
        increase_current_stats (bool, optional): Whether to adjusts the unit's current HP and mana if their maximum values increase.
            Defaults to True.

    Notes:
        - Assumes that the stat changes are valid. No checks are done for maximum stats, stat caps, etc.
    """
    old_max_hp = unit.get_max_hp()
    old_max_mana = unit.get_max_mana()

    # Actually apply changes
    for nid, value in stat_changes.items():
        unit.stats[nid] += value

    current_max_hp = unit.get_max_hp()
    current_max_mana = unit.get_max_mana()

    if increase_current_stats:
        if current_max_hp > old_max_hp:
            unit.set_hp(current_max_hp - old_max_hp + unit.get_hp())
        if current_max_mana > old_max_mana:
            unit.set_mana(current_max_mana - old_max_mana + unit.get_mana())
    if unit.get_hp() > current_max_hp:
        unit.set_hp(current_max_hp)
    if unit.get_mana() > current_max_mana:
        unit.set_mana(current_max_mana)

def apply_growth_changes(unit: UnitObject, growth_changes: Dict[NID, int]) -> None:
    """
    Applies the given changes to the unit's growths.

    Args:
        unit (UnitObject): The unit to which the stat changes should be applied.
        growth_changes (Dict[NID, int]): A dictionary containing the stat changes to apply.
    """ 
    for nid, value in growth_changes.items():
        unit.growths[nid] += value

def get_starting_skills(unit: UnitObject, starting_level: Optional[int] = 0) -> List[SkillObject]:
    """
    Retrieves the starting skills for a unit based on its class and level.

    Args:
        unit (UnitObject): The unit for which to retrieve starting skills.
        starting_level (int, optional): The starting level of the unit. Defaults to 0.

    Returns:
        List[SkillObject]: The starting skills of the unit.

    Notes:
        - If `promote_skill_inheritance` constant is enabled, skills from lower-tier classes are also considered (up to 5 tiers back).
        - If `generic_feats` constant is enabled and a learned skill is a 'Feat', a random feat skill is added.

    """
    klass_obj = DB.classes.get(unit.klass)
    current_klass = klass_obj
    all_klasses = [klass_obj]
    if DB.constants.value('promote_skill_inheritance'):
        counter = 5
        while current_klass and current_klass.tier > 1 and counter > 0:
            counter -= 1  # Prevent infinite loops
            if current_klass.promotes_from:
                current_klass = DB.classes.get(current_klass.promotes_from)
                all_klasses.append(current_klass)
            else:
                break
    all_klasses.reverse()

    skills_to_add = []
    feats = DB.skills.get_feats()
    current_skills = [skill.nid for skill in unit.skills]
    for idx, klass in enumerate(all_klasses):
        for learned_skill in klass.learned_skills:
            if (starting_level < learned_skill[0] <= unit.level or klass != klass_obj) and \
                    learned_skill[1] not in current_skills and \
                    learned_skill[1] not in skills_to_add:
                if learned_skill[1] == 'Feat':
                    if DB.constants.value('generic_feats'):
                        my_feats = [feat for feat in feats if feat.nid not in current_skills and feat.nid not in skills_to_add]
                        random_number = static_random.get_growth() % len(my_feats)
                        new_skill = my_feats[random_number]
                        skills_to_add.append(new_skill.nid)
                else:
                    skills_to_add.append(learned_skill[1])

    klass_skills = item_funcs.create_skills(unit, skills_to_add)
    return klass_skills

def get_personal_skills(unit: UnitObject, prefab: UnitPrefab, starting_level: Optional[int] = 0) -> List[SkillObject]:
    """
    Retrieves the personal skills for a unit based on its prefab and level.

    Args:
        unit (UnitObject): The unit for which to retrieve personal skills.
        prefab (UnitPrefab): The unit's prefab which contains information about the unit's personal skills.
        starting_level (int, optional): The starting level of the unit. Defaults to 0.

    Returns:
        List[SkillObject]: A list of SkillObject instances representing the personal skills of the unit.

    Notes:
        - Only skills that the unit has learned at or below its current level are included.
    """
    skills_to_add = []
    current_skills = [skill.nid for skill in unit.skills]
    for learned_skill in prefab.learned_skills:
        if starting_level < learned_skill[0] <= unit.level and learned_skill[1] not in current_skills:
            skills_to_add.append(learned_skill[1])

    personal_skills = item_funcs.create_skills(unit, skills_to_add)
    return personal_skills

def get_global_skills(unit: UnitObject) -> List[SkillObject]:
    """
    Retrieves the global skills for the unit. These are the skills that every unit should have.
    They are used to change your game mechanics globally.

    Args:
        unit (UnitObject): The unit for which to retrieve global skills.

    Returns:
        List[SkillObject]: A list of SkillObject instances representing the global skills.

    Notes:
        - The function retrieves global skills that the unit does not already possess.
    """
    skills_to_add = []
    current_skills = [skill.nid for skill in unit.skills]
    for skill_prefab in DB.skills:
        if skill_prefab.components.get('global') and skill_prefab.nid not in current_skills:
            skills_to_add.append(skill_prefab.nid)

    global_skills = item_funcs.create_skills(unit, skills_to_add)
    return global_skills

def can_unlock(unit: UnitObject, region: RegionObject) -> bool:
    """
    Checks if a unit can unlock a region.

    Args:
        unit (UnitObject): The unit attempting to unlock.
        region (RegionObject): The region to unlock.

    Returns:
        bool: True if the unit can unlock the region, False otherwise.
    """
    from app.engine import item_system, skill_system
    if skill_system.can_unlock(unit, region):
        return True
    for item in item_funcs.get_all_items(unit):
        if item_funcs.available(unit, item) and \
                item_system.can_unlock(unit, item, region):
            return True
    return False

def can_pairup(rescuer: UnitObject, rescuee: UnitObject) -> bool:
    """
    Determines whether a pair-up can occur between a rescuer unit and a rescuee unit.

    Args:
        rescuer (UnitObject): The unit that is attempting to initiate the pair-up.
        rescuee (UnitObject): The unit that is being considered as a potential partner for pair-up.

    Returns:
        bool: True if a pair-up can occur between the rescuer and rescuee units; False otherwise.

    Notes:
        - A pair-up can occur if pair-up mechanics are enabled in the game and attack stance only is not enforced.
        - If player pair-up is restricted, the function checks whether both the rescuer and rescuee units belong to the player's team.
    """
    valid = DB.constants.value('pairup') and not DB.constants.value('attack_stance_only')
    if valid and DB.constants.value('player_pairup_only'):
        valid = rescuer.team == 'player' and rescuee.team == 'player'
    return valid

def check_focus(unit: UnitObject, limit: Optional[int] = 3) -> int:
    """
    Counts the number of allied units within a specified distance from a given unit.

    Args:
        unit (UnitObject): The unit whose surroundings are being checked for allied units.
        limit (int, optional): The maximum distance within which allied units are considered.
            Defaults to 3.

    Returns:
        int: The count of allied units within the specified distance from the given unit.

    Notes:
        - Does not count self as an ally.
    """
    from app.engine import skill_system
    from app.engine.game_state import game
    counter = 0
    if unit.position:
        for other in game.units:
            if other.position and \
                    unit is not other and \
                    skill_system.check_ally(unit, other) and \
                    utils.calculate_distance(unit.position, other.position) <= limit:
                counter += 1
    return counter

def check_flanked(unit: UnitObject) -> bool:
    """
    Checks if the given unit is flanked by enemy units.

    Args:
        unit (UnitObject): The unit to check for flanking.

    Returns:
        bool: True if the unit is flanked by enemy units, False otherwise.

    Notes:
        - If both the up and down adjacent units are enemies or the same is true for
          the left and right adjacent units, the unit is considered flanked.
    """
    from app.engine import skill_system
    from app.engine.game_state import game
    if unit.position:
        up = game.board.get_unit((unit.position[0], unit.position[1] - 1))
        left = game.board.get_unit((unit.position[0] - 1, unit.position[1]))
        right = game.board.get_unit((unit.position[0] + 1, unit.position[1]))
        down = game.board.get_unit((unit.position[0], unit.position[1] + 1))
        if up and down and skill_system.check_enemy(unit, up) and skill_system.check_enemy(unit, down):
            return True
        if left and right and skill_system.check_enemy(unit, left) and skill_system.check_enemy(unit, right):
            return True
    return False

check_flanking = check_flanked

def wait(unit: UnitObject, actively_chosen: bool = False):
    """
    Makes the unit wait, ending its turn.

    Args:
        unit (UnitObject): The unit that will wait.
        actively_chosen (bool, optional): Indicates whether the wait action was actively chosen by the player.
            Defaults to False, which means the unit just automatically waited when it ran out of actions to do (finished a combat, etc.)

    Notes:
        - the function triggers a UnitWait event, indicating that the unit is waiting.
        - If the unit's turn is already finished, the function does nothing.
    """
    from app.engine import action
    if not unit.finished:  # Only wait if we aren't finished
        # To prevent double-waiting
        game.events.trigger(triggers.UnitWait(unit, unit.position, game.get_region_under_pos(unit.position), actively_chosen))
        action.do(action.Wait(unit))
        skill_system.on_wait(unit, actively_chosen)

def usable_wtypes(unit: UnitObject) -> Set[NID]:
    """
    Retrieves the set of weapon types usable by the unit.

    Args:
        unit (UnitObject): The unit for which to determine usable weapon types.

    Returns:
        Set[NID]: A set containing the NIDs of weapon types that the unit can use.

    Notes:
        - The unit's class determines its base weapon proficiency.
        - Usable weapon types include those defined by the unit's class as well as any additional
          types granted by skills or other effects.
    """
    klass = DB.classes.get(unit.klass)
    klass_weapons = klass.wexp_gain
    klass_usable = set([wtype_name for wtype_name, wtype_info in klass_weapons.items() if wtype_info.usable])
    return (klass_usable | skill_system.usable_wtypes(unit)) - skill_system.forbidden_wtypes(unit)

def get_weapon_cap(unit: UnitObject, weapon_type: NID) -> int:
    """
    Retrieves the weapon proficiency cap for a specific weapon type and unit.
    For instance, if the unit can only get up to B rank in a weapon type, will return the WEXP value for B rank.

    Args:
        unit (UnitObject): The unit for which to retrieve the weapon proficiency cap.
        weapon_type (NID): The NID of the weapon type for which to retrieve the cap.

    Returns:
        int: The proficiency cap for the specified weapon type and unit.

    Notes:
        - If no cap is specified for the weapon type, the highest weapon rank requirement from the
          database is used as the cap.
    """
    klass = DB.classes.get(unit.klass)
    wexp_gain = klass.wexp_gain.get(weapon_type, DB.weapons.default(DB))
    cap = wexp_gain.cap
    if cap:
        return cap
    else:
        return DB.weapon_ranks.get_highest_rank().requirement
