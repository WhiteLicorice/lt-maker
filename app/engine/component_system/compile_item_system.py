from __future__ import annotations
from typing import Dict
from app.engine.codegen.codegen_utils import get_codegen_header
from app.engine.component_system.utils import HookInfo, ARG_TYPE_MAP, ResolvePolicy

ITEM_HOOKS: Dict[str, HookInfo] = {
    # default false, return false if any component returns false
    'is_weapon':                                       HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'is_spell':                                        HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'is_accessory':                                    HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'equippable':                                      HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'can_counter':                                     HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'can_be_countered':                                HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'can_double':                                      HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'can_use':                                         HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'can_use_in_base':                                 HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    # 'locked':                                          HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'unstealable':                                     HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'allow_same_target':                               HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'allow_less_than_max_targets':                     HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'ignore_weapon_advantage':                         HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'unrepairable':                                    HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'unsplashable':                                    HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'targets_items':                                   HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'menu_after_combat':                               HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'transforms':                                      HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'no_attack_after_move':                            HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'no_map_hp_display':                               HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'cannot_be_dual_strike_partner':                   HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'cannot_have_dual_strike_partner':                 HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'can_attack_after_combat':                         HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'simple_target_restrict':                          HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'force_map_anim':                                  HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'map_cast_pose':                                   HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'ignore_line_of_sight':                            HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    'ignore_fog_of_war':                               HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_FALSE),
    # default true, return false if any component returns false
    'alerts_when_broken':                              HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_TRUE, inherits_parent=True),
    'tradeable':                                       HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_TRUE),                                       
    'storeable':                                       HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_TRUE),
    'discardable':                                     HookInfo(['unit', 'item'], ResolvePolicy.ALL_DEFAULT_TRUE),
    # returns latest value defined by a component, or default value if not defined
    'damage_formula':                                  HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'resist_formula':                                  HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'accuracy_formula':                                HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'avoid_formula':                                   HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'crit_accuracy_formula':                           HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'crit_avoid_formula':                              HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'attack_speed_formula':                            HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'defense_speed_formula':                           HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'damage_formula_override':                         HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'resist_formula_override':                         HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'accuracy_formula_override':                       HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'avoid_formula_override':                          HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'crit_accuracy_formula_override':                  HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'crit_avoid_formula_override':                     HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'attack_speed_formula_override':                   HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'defense_speed_formula_override':                  HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'full_price':                                      HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'buy_price':                                       HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'sell_price':                                      HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'special_sort':                                    HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'num_targets':                                     HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'minimum_range':                                   HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'maximum_range':                                   HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'weapon_type':                                     HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'weapon_triangle_override':                        HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'weapon_rank':                                     HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'damage':                                          HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'hit':                                             HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'crit':                                            HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'effect_animation':                                HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    'text_color':                                      HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE, has_default_value=True),
    # returns set of all defined values
    'target_icon':                                     HookInfo(['unit', 'item', 'target'], ResolvePolicy.UNION),
    # returns sum of all defined values
    'wexp':                                            HookInfo(['playbacks', 'unit', 'item', 'target'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_damage':                                   HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_resist':                                   HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_accuracy':                                 HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_avoid':                                    HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_crit_accuracy':                            HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_crit_damage':                              HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_crit_avoid':                               HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_attack_speed':                             HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_defense_speed':                            HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_ACCUM),
    'modify_weapon_triangle':                          HookInfo(['unit', 'item'], ResolvePolicy.NUMERIC_MULTIPLY, has_default_value=True),
    'dynamic_damage':                                  HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_accuracy':                                HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_crit_accuracy':                           HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_attack_speed':                            HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_attacks':                                 HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    'dynamic_multiattacks':                            HookInfo(['unit', 'item', 'target', 'item2', 'mode', 'attack_info', 'base_value'], ResolvePolicy.NUMERIC_ACCUM),
    # aesthetic components that return a value
    'hover_description':                               HookInfo(['unit', 'item'], ResolvePolicy.UNIQUE),
    'show_weapon_advantage':                           HookInfo(['unit', 'item', 'target', 'item2'], ResolvePolicy.UNIQUE),
    'show_weapon_disadvantage':                        HookInfo(['unit', 'item', 'target', 'item2'], ResolvePolicy.UNIQUE),
    'battle_music':                                    HookInfo(['unit', 'item', 'target', 'item2', 'mode'], ResolvePolicy.UNIQUE),
    'combat_effect':                                   HookInfo(['unit', 'item', 'target', 'item2', 'mode'], ResolvePolicy.UNIQUE),
    'on_hit_effect':                                   HookInfo(['unit', 'item', 'target', 'item2', 'mode'], ResolvePolicy.UNIQUE),
    # events do not return, but are the only item components currently inherited from parents
    'on_end_chapter':                                  HookInfo(['unit', 'item'], ResolvePolicy.NO_RETURN, inherits_parent=True),
    'reverse_use':                                     HookInfo(['unit', 'item'], ResolvePolicy.NO_RETURN, inherits_parent=True),
    'on_equip_item':                                   HookInfo(['unit', 'item'], ResolvePolicy.NO_RETURN, inherits_parent=True),
    'on_unequip_item':                                 HookInfo(['unit', 'item'], ResolvePolicy.NO_RETURN, inherits_parent=True),
    'on_add_item':                                     HookInfo(['unit', 'item'], ResolvePolicy.NO_RETURN, inherits_parent=True),
    'on_remove_item':                                  HookInfo(['unit', 'item'], ResolvePolicy.NO_RETURN, inherits_parent=True),
    'on_upkeep':                                       HookInfo(['actions', 'playback', 'unit', 'item'], ResolvePolicy.NO_RETURN, inherits_parent=True),
    'on_endstep':                                      HookInfo(['actions', 'playback', 'unit', 'item'], ResolvePolicy.NO_RETURN, inherits_parent=True),
    'start_combat':                                    HookInfo(['playback', 'unit', 'item', 'target', 'item2', 'mode'], ResolvePolicy.NO_RETURN, inherits_parent=True),
    'end_combat':                                      HookInfo(['playback', 'unit', 'item', 'target', 'item2', 'mode'], ResolvePolicy.NO_RETURN, inherits_parent=True),
}

def generate_item_hook_str(hook_name: str, hook_info: HookInfo):
    args = hook_info.args
    if not 'unit' in args or not 'item' in args:
        raise ValueError("Expected 'unit' and 'item' in args for hook %s" % hook_name)
    func_signature = ['{arg}: {type}'.format(arg=arg, type=ARG_TYPE_MAP.get(arg, "Any")) for arg in args]

    default_handling = "return result"
    inheritance_handling = ""
    if hook_info.has_default_value:
        default_handling = "return result if values else Defaults.{hook_name}({args})".format(hook_name=hook_name, args=', '.join(args))
    if hook_info.inherits_parent:
        inheritance_handling = """
            if item.parent_item:
                orig_item = item
                item = item.parent_item
                for component in item.components:
                    if component.defines('{hook_name}'):
                        values.append(component.{hook_name}({args}))
                item = orig_item
""".format(hook_name=hook_name, args=', '.join(args))

    func_text = """
def {hook_name}({func_signature}):
    all_components = get_all_components(unit, item)
    values = []
    for component in all_components:
        if component.defines('{hook_name}'):
            values.append(component.{hook_name}({args}))
{inheritance_handling}
    result = utils.{policy_resolution}(values)
    {default_handling}
""".format(hook_name=hook_name,
           func_signature=', '.join(func_signature),
           args=', '.join(args),
           policy_resolution=hook_info.policy.value,
           default_handling=default_handling,
           inheritance_handling=inheritance_handling)
    return func_text

def compile_item_system():
    import os
    dir_path = os.path.dirname(os.path.realpath(__file__))
    compiled_item_system = open(os.path.join(dir_path, '..', 'item_system.py'), 'w')
    item_system_base = open(os.path.join(dir_path, 'item_system_base.py'), 'r')

    # write warning msg
    compiled_item_system.writelines(get_codegen_header())

    # copy item system base
    for line in item_system_base.readlines():
        compiled_item_system.write(line)

    for hook_name, hook_info in ITEM_HOOKS.items():
        func = generate_item_hook_str(hook_name, hook_info)
        compiled_item_system.write(func)

    compiled_item_system.close()
    item_system_base.close()