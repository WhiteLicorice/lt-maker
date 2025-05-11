from __future__ import annotations
from typing import Any, Dict
from app.engine.codegen.codegen_utils import get_codegen_header
from app.engine.component_system.utils import ARG_TYPE_MAP, HookInfo, ResolvePolicy

SKILL_HOOKS: Dict[str, HookInfo] = {
    # true priority (set to False if result is False in any component, True if not defined)
    'available':                            HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_TRUE),
    'can_counter':                          HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_TRUE),
    # false priority (set to False if result is False in any component, False if not defined)
    'pass_through':                         HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'vantage':                              HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'desperation':                          HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'ignore_terrain':                       HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'crit_anyway':                          HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'ignore_region_status':                 HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'no_double':                            HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'def_double':                           HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'ignore_rescue_penalty':                HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'ignore_forced_movement':               HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'distant_counter':                      HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'ignore_fatigue':                       HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'no_attack_after_move':                 HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'has_dynamic_range':                    HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'disvantage':                           HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'close_counter':                        HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'attack_stance_double':                 HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'show_skill_icon':                      HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'hide_skill_icon':                      HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'ignore_dying_in_combat':               HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'no_trade':                             HookInfo(['unit'], ResolvePolicy.ALL_DEFAULT_FALSE),
    # false priority, true if any (set to True if result is True in any component, False if not defined)
    'can_unlock':                           HookInfo(['unit', 'region'], ResolvePolicy.ANY_DEFAULT_FALSE),
    'has_canto':                            HookInfo(['unit', 'target'], ResolvePolicy.ANY_DEFAULT_FALSE),
    'has_immune':                           HookInfo(['unit'], ResolvePolicy.ANY_DEFAULT_FALSE),
    # exclusive (returns last component value, returns None if not defined)
    'alternate_splash':                     HookInfo(['unit'], ResolvePolicy.UNIQUE),
    # exclusive (returns last component value, has default value if not defined)
    'can_select':                           HookInfo(['unit'], ResolvePolicy.UNIQUE, has_default_value=True),
    'movement_type':                        HookInfo(['unit'], ResolvePolicy.UNIQUE, has_default_value=True),
    'num_items_offset':                     HookInfo(['unit'], ResolvePolicy.UNIQUE, has_default_value=True),
    'num_accessories_offset':               HookInfo(['unit'], ResolvePolicy.UNIQUE, has_default_value=True),
    'change_variant':                       HookInfo(['unit'], ResolvePolicy.UNIQUE, has_default_value=True),
    'change_animation':                     HookInfo(['unit'], ResolvePolicy.UNIQUE, has_default_value=True),
    'change_ai':                            HookInfo(['unit'], ResolvePolicy.UNIQUE, has_default_value=True),
    'change_roam_ai':                       HookInfo(['unit'], ResolvePolicy.UNIQUE, has_default_value=True),
    'witch_warp':                           HookInfo(['unit'], ResolvePolicy.UNIQUE, has_default_value=True, is_cached=True),
    # numeric accum (adds together all values. 0 if no values are defined)
    'sight_range':                          HookInfo(['unit'], ResolvePolicy.NUMERIC_ACCUM, has_default_value=True),
    # formula (as exclusive)
    'damage_formula':                       HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'resist_formula':                       HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'accuracy_formula':                     HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'avoid_formula':                        HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'crit_accuracy_formula':                HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'crit_avoid_formula':                   HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'attack_speed_formula':                 HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'defense_speed_formula':                HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'critical_multiplier_formula':          HookInfo(['unit'], ResolvePolicy.UNIQUE, has_default_value=True),
    'critical_addition_formula':            HookInfo(['unit'], ResolvePolicy.UNIQUE, has_default_value=True),
    'thracia_critical_multiplier_formula':  HookInfo(['unit'], ResolvePolicy.UNIQUE, has_default_value=True),
    # formula_overrides (as exclusive)
    'damage_formula_override':              HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'resist_formula_override':              HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'accuracy_formula_override':            HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'avoid_formula_override':               HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'crit_accuracy_formula_override':       HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'crit_avoid_formula_override':          HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'attack_speed_formula_override':        HookInfo(['unit'], ResolvePolicy.UNIQUE),
    'defense_speed_formula_override':       HookInfo(['unit'], ResolvePolicy.UNIQUE),
    # item modifiers (as exclusive)
    'modify_buy_price':                     HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'modify_sell_price':                    HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'limit_maximum_range':                  HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    # targeted (as exclusive)
    'check_ally':                           HookInfo(['unit', 'target'], ResolvePolicy.UNIQUE, has_default_value=True),
    'check_enemy':                          HookInfo(['unit', 'target'], ResolvePolicy.UNIQUE, has_default_value=True),
    'can_trade':                            HookInfo(['unit', 'target'], ResolvePolicy.UNIQUE, has_default_value=True),
    'exp_multiplier':                       HookInfo(['unit', 'target'], ResolvePolicy.UNIQUE, has_default_value=True),
    'enemy_exp_multiplier':                 HookInfo(['unit', 'target'], ResolvePolicy.UNIQUE, has_default_value=True),
    'wexp_multiplier':                      HookInfo(['unit', 'target'], ResolvePolicy.UNIQUE, has_default_value=True),
    'enemy_wexp_multiplier':                HookInfo(['unit', 'target'], ResolvePolicy.UNIQUE, has_default_value=True),
    'canto_movement':                       HookInfo(['unit', 'target'], ResolvePolicy.MAXIMUM, has_default_value=False),
    # item numeric modifiers (sums component values, default 0 if not defined)
    'empower_splash':                       HookInfo(['unit'], ResolvePolicy.NUMERIC_ACCUM),
    'empower_heal':                         HookInfo(['unit', 'target'], ResolvePolicy.NUMERIC_ACCUM),
    'empower_heal_received':                HookInfo(['unit', 'target'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_damage':                        HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_resist':                        HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_accuracy':                      HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_avoid':                         HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_crit_accuracy':                 HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_crit_avoid':                    HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_crit_damage':                   HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_attack_speed':                  HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_defense_speed':                 HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_maximum_range':                 HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_minimum_range':                 HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),

    # dynamic numeric modifiers (as item numberic modifiers)
    'dynamic_damage':                       HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_resist':                       HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_accuracy':                     HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_avoid':                        HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_crit_accuracy':                HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_crit_avoid':                   HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_attack_speed':                 HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_defense_speed':                HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_attacks':                      HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_multiattacks':                 HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    # mana (as item numeric modifiers)
    'mana':                                 HookInfo(['playback', 'unit', 'item', 'target'], ResolvePolicy.NUMERIC_ACCUM),
    # multipliers (takes product of component values, default 1 if not defined)
    'damage_multiplier':                    HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_MULTIPLY),
    'resist_multiplier':                    HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_MULTIPLY),
    'crit_multiplier':                      HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_MULTIPLY),
    # aesthetic combat (returns last component value, None if not defined)
    'battle_music':                         HookInfo(['playback', 'unit', 'item', 'target', 'item2', 'mode'], ResolvePolicy.UNIQUE),
    # events (runs all components, does not return anything)
    'on_death':                             HookInfo(['unit'], ResolvePolicy.NO_RETURN),
    # item events
    'on_add_item':                          HookInfo(['unit', 'item'], ResolvePolicy.NO_RETURN),
    'on_remove_item':                       HookInfo(['unit', 'item'], ResolvePolicy.NO_RETURN),
    'on_equip_item':                        HookInfo(['unit', 'item'], ResolvePolicy.NO_RETURN),
    'on_unequip_item':                      HookInfo(['unit', 'item'], ResolvePolicy.NO_RETURN),
    # sub-combat events
    'start_sub_combat':                     HookInfo(['actions', 'playback', 'unit', 'item', 'target', 'item2', 'mode', 'attack_info'], ResolvePolicy.NO_RETURN, has_unconditional=True),
    'end_sub_combat':                       HookInfo(['actions', 'playback', 'unit', 'item', 'target', 'item2', 'mode', 'attack_info'], ResolvePolicy.NO_RETURN, has_unconditional=True),
    # after strike events
    'after_strike':                         HookInfo(['actions', 'playback', 'unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'strike'], ResolvePolicy.NO_RETURN),
    'after_take_strike':                    HookInfo(['actions', 'playback', 'unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'strike'], ResolvePolicy.NO_RETURN),
    # phase events
    'on_upkeep':                            HookInfo(['actions', 'playback', 'unit'], ResolvePolicy.NO_RETURN, has_unconditional=True),
    'on_endstep':                           HookInfo(['actions', 'playback', 'unit'], ResolvePolicy.NO_RETURN, has_unconditional=True),
    # combat events (as events but has unconditional variants)
    'start_combat':                         HookInfo(['playback', 'unit', 'item', 'target', 'item2', 'mode'], ResolvePolicy.NO_RETURN, has_unconditional=True),
    'cleanup_combat':                       HookInfo(['playback', 'unit', 'item', 'target', 'item2', 'mode'], ResolvePolicy.NO_RETURN, has_unconditional=True),
    'end_combat':                           HookInfo(['playback', 'unit', 'item', 'target', 'item2', 'mode'], ResolvePolicy.NO_RETURN, has_unconditional=True),
    'pre_combat':                           HookInfo(['playback', 'unit', 'item', 'target', 'item2', 'mode'], ResolvePolicy.NO_RETURN, has_unconditional=True),
    'post_combat':                          HookInfo(['playback', 'unit', 'item', 'target', 'item2', 'mode'], ResolvePolicy.NO_RETURN, has_unconditional=True),
    'test_on':                              HookInfo(['playback', 'unit', 'item', 'target', 'item2', 'mode'], ResolvePolicy.NO_RETURN, has_unconditional=True),
    'test_off':                             HookInfo(['playback', 'unit', 'item', 'target', 'item2', 'mode'], ResolvePolicy.NO_RETURN, has_unconditional=True),
    # list hooks (returns a list of all hook return values)
    # union hooks (returns a set containing every unique hook return)
    'usable_wtypes':                        HookInfo(['unit'], ResolvePolicy.UNION),
    'forbidden_wtypes':                     HookInfo(['unit'], ResolvePolicy.UNION),
    'target_icon':                          HookInfo(['unit', 'icon_unit'], ResolvePolicy.UNION),
}

def generate_skill_hook_str(hook_name: str, hook_info: HookInfo):
    args = hook_info.args
    if not 'unit' in args:
        raise ValueError("Expected 'unit' in args for hook %s" % hook_name)
    func_signature = ['{arg}: {type}'.format(arg=arg, type=ARG_TYPE_MAP.get(arg, "Any")) for arg in args]

    conditional_check = "condition(skill, unit)" if 'item' not in args else 'condition(skill, unit, item)'
    default_handling = "return result"
    unconditional_handling = ""
    cache_handling = ""
    if hook_info.has_default_value:
        default_handling = "return result if values else Defaults.{hook_name}({args})".format(hook_name=hook_name, args=', '.join(args))
    if hook_info.has_unconditional:
        unconditional_handling = """
            if component.defines('{hook_name}_unconditional'):
                values.append(component.{hook_name}_unconditional({args}))
""".format(hook_name=hook_name, args=', '.join(args))
    if hook_info.is_cached:
        cache_handling = """
@ltcached"""

    func_text = """{cache_handling}
def {hook_name}({func_signature}):
    values = []
    for skill in unit.skills[:]:
        for component in skill.components:
            if component.defines('{hook_name}'):
                if component.ignore_conditional or {conditional_check}:
                    values.append(component.{hook_name}({args}))
{unconditional_handling}
    result = utils.{policy_resolution}(values)
    {default_handling}
""".format(hook_name=hook_name,
           func_signature=', '.join(func_signature),
           conditional_check=conditional_check,
           args=', '.join(args),
           policy_resolution=hook_info.policy.value,
           default_handling=default_handling,
           unconditional_handling=unconditional_handling,
           cache_handling=cache_handling)

    return func_text

def compile_skill_system():
    import os
    dir_path = os.path.dirname(os.path.realpath(__file__))
    compiled_skill_system = open(os.path.join(
        dir_path, '..', 'skill_system.py'), 'w')
    skill_system_base = open(os.path.join(
        dir_path, 'skill_system_base.py'), 'r')

    # write warning msg
    compiled_skill_system.writelines(get_codegen_header())

    # copy skill system base
    for line in skill_system_base.readlines():
        compiled_skill_system.write(line)

    for hook_name, hook_info in SKILL_HOOKS.items():
        func = generate_skill_hook_str(hook_name, hook_info)
        compiled_skill_system.write(func)

    skill_system_base.close()
    compiled_skill_system.close()
