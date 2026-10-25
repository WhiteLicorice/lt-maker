import xml.etree.ElementTree as ET

from app.utilities import str_utils, utils
from app.data.database.database import DB
from app.data.database import skills

from app.data.database.components import ComponentData, ComponentType

import app.engine.skill_component_access as SCA

import logging

def get_from_xml(parent_dir: str, xml_fn: str) -> list:
    skill_xml = ET.parse(xml_fn)
    skill_list = []
    for skill in skill_xml.getroot().findall('status'):
        try:
            new_skill = load_skill(skill)
            skill_list.append(new_skill)
        except Exception as e:
            logging.warning("Skill %s Import Error: %s" % (skill.find('id').text, e))
    return skill_list

def load_skill(skill):
    nids = DB.skills.keys()
    nid = str_utils.get_next_name(skill.find('id').text, nids)
    name = skill.get('name')
    desc = skill.find('desc').text
    icon_nid = 'Skills'
    icon_index = skill.find('image_index').text.split(',')
    icon_index = (int(icon_index[0]), int(icon_index[1]))

    components = skill.find('components').text.split(',') if skill.find('components').text else []
    final_components = ComponentData()
    for component in components:
        if component in ('aura_child', 'affects_movement'):
            # Not needed
            pass

        elif component == 'hp_percentage':
            perc = int(skill.find(component).text)
            if perc > 0:
                comp = SCA.get_component('regeneration')
                comp.value = perc/100.
                final_components.append(comp)
            else:
                logging.warning("%s: Could not determine value for component %s" % (nid, 'hp_percentage'))

        elif component == 'upkeep_animation':
            comp = SCA.get_component('upkeep_animation')
            val = skill.find(component).text.split(',')[0]
            comp.value = val
            final_components.append(comp)

        elif component == 'always_animation':
            comp = SCA.get_component('unit_anim')
            val = skill.find(component).text.split(',')[0]
            comp.value = val
            final_components.append(comp)

        elif component == 'unit_tint':
            comp = SCA.get_component('unit_flickering_tint')
            value = skill.find(component).text.split(',')
            comp.value = tuple([utils.clamp(int(v), 0, 255) for v in value[:3]])
            final_components.append(comp)

        elif component == 'no_weapons':
            comp = SCA.get_component('cannot_use_items')
            final_components.append(comp)

        elif component == 'no_magic_weapons':
            comp = SCA.get_component('cannot_use_magic_items')
            final_components.append(comp)

        elif component == 'un_selectable':
            comp = SCA.get_component('unselectable')
            final_components.append(comp)

        elif component == 'ephemeral':
            comp = SCA.get_component('event_on_remove')
            final_components.append(comp)
            logging.warning("%s: Attach an event that kills {unit} to this component" % nid)

        elif component == 'reflect':
            comp = SCA.get_component('reflect_status')
            final_components.append(comp)

        elif component in ('gain_status_after_kill', 'gain_status_after_attack', 'gain_status_after_active_kill'):
            comp = component.replace('status', 'skill')
            comp = SCA.get_component(comp)
            comp.value = skill.find(component).text
            final_components.append(comp)

        elif component == 'lost_on_endchapter':
            comp = SCA.get_component('lost_on_end_chapter')
            final_components.append(comp)

        elif component in ('lost_on_interact', 'lost_on_attack'):
            comp = SCA.get_component('lost_on_end_combat')
            final_components.append(comp)

        elif component == 'evasion':
            comp = SCA.get_component('dynamic_avoid')
            comp.value = "1000 if mode == 'splash' else 0"
            final_components.append(comp)

        elif component == 'buy_value_mod':
            comp = SCA.get_component('change_buy_price')
            value = float(skill.find(component).text)
            comp.value = value
            final_components.append(comp)

        elif component in ('mt', 'resist', 'hit', 'avoid', 'crit', 'crit_avoid', 'attackspeed'):
            comp = component.replace('mt', 'damage')
            val = skill.find(component).text
            if str_utils.is_int(val):
                comp = SCA.get_component(comp)
                if comp:
                    comp.value = int(val)
                    final_components.append(comp)
                else:
                    logging.warning("%s: Could not determine correct component for %s" % (nid, component))
            else:
                comp = comp.replace('hit', 'accuracy').replace('crit', 'crit_accuracy')
                comp = SCA.get_component('dynamic_%s' % comp)
                if comp:
                    comp.value = val
                    final_components.append(comp)
                else:
                    logging.warning("%s: Could not determine correct component for %s" % (nid, component))

        elif component.startswith('conditional'):
            value = skill.find(component).text
            num, cond = value.split(';')
            comp = component.replace('conditional', 'dynamic')
            comp = comp.replace('mt', 'damage')
            comp = comp.replace('hit', 'accuracy')
            comp = SCA.get_component(comp)
            if comp:
                comp.value = '%s if (%s) else 0' % (num, cond)
                final_components.append(comp)
            else:
                logging.warning("%s: Could not determine correponding component for %s" % component)
            logging.warning("%s: Combat components not guaranteed to work the same!" % nid)

        elif component == 'stat_halve':
            comp = SCA.get_component('stat_multiplier')
            logging.warning("%s: Could not determine value for component %s" % (nid, component))
            final_components.append(comp)

        elif component == 'savior':
            comp = SCA.get_component('ignore_rescue_penalty')
            final_components.append(comp)

        elif component == 'pass_through':
            comp = SCA.get_component('pass')
            final_components.append(comp)

        elif component in ('fleet_of_foot', 'flying'):
            comp = SCA.get_component('movement_type')
            logging.warning("%s: Could not determine value for component %s" % (nid, component))
            final_components.append(comp)

        elif component == 'shrug_off':
            comp = SCA.get_component('resist_status')
            final_components.append(comp)

        elif component == 'immune':
            comp = SCA.get_component('immune_status')
            final_components.append(comp)

        elif component == 'def_double':
            comp = SCA.get_component('can_double_on_defense')
            final_components.append(comp)

        elif component == 'no_exp':
            comp = SCA.get_component('enemy_exp_multiplier')
            comp.value = 0.
            final_components.append(comp)

        elif component == 'upkeep_damage':
            val = skill.find('upkeep_damage').text
            if ',' in val or not str_utils.is_int(val):
                logging.warning("%s: Could not determine value for component %s" % (nid, component))
            else:
                comp = SCA.get_component('upkeep_damage')
                comp.value = int(val)
                final_components.append(comp)

        elif component == 'activated_item':
            val = skill.find('activated_item').text
            comp = SCA.get_component('ability')
            comp.value = val
            final_components.append(comp)
            logging.warning("%s: Conversion of activated item not perfect" % nid)

        elif component == 'status_after_battle':
            val = skill.find('status_after_battle').text
            comp = SCA.get_component('give_status_after_combat')
            comp.value = val
            final_components.append(comp)

        elif component == 'tether':
            comp = SCA.get_component('death_tether')
            comp.value = val
            final_components.append(comp)

        elif skill.find(component) is not None:
            comp = SCA.get_component(component)
            if comp:
                try:
                    value = skill.find(component).text
                    if comp.expose == ComponentType.Int:
                        value = int(value)
                    elif comp.expose == ComponentType.Float:
                        value = float(value)
                    elif comp.expose == ComponentType.Color3 or comp.expose == ComponentType.Color4:
                        value = [utils.clamp(int(c), 0, 255) for c in value.split(',')]
                    elif isinstance(comp.expose, tuple):
                        logging.warning("%s: Could not determine value for component %s" % (nid, component))
                        value = []
                    comp.value = value
                except Exception as e:
                    logging.warning("%s: Could not determine value for component %s" % (nid, component))
                final_components.append(comp)
            else:
                logging.warning("%s: Could not determine corresponding LT maker component for %s" % (nid, component))
        else:
            comp = SCA.get_component(component)
            if comp:
                final_components.append(comp)
            else:
                logging.warning("%s: Could not determine corresponding LT maker component for %s" % (nid, component))

    new_skill = skills.SkillPrefab(nid, name, desc, icon_nid, icon_index, final_components)
    return new_skill
