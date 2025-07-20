from app.data.database.database import DB
from app.data.database.skill_components import SkillComponent, SkillTags
from app.data.database.components import ComponentType
from app.engine import equations

import logging

class StatChange(SkillComponent):
    nid = 'stat_change'
    desc = "Gives stat bonuses"
    tag = SkillTags.COMBAT

    expose = (ComponentType.Dict, ComponentType.Stat)
    value = []

    def stat_change(self, unit=None):
        return {stat[0]: stat[1] for stat in self.value}

    def tile_def(self):
        total_value = 0
        for stat_nid, stat_value in self.value:
            if stat_nid == 'DEF':
                total_value += stat_value
        return total_value

class StatChangeExpression(SkillComponent):
    nid = 'stat_change_expression'
    desc = "Gives stat bonuses based on expression"
    tag = SkillTags.COMBAT

    expose = (ComponentType.StringDict, ComponentType.Stat)
    value = []

    def stat_change(self, unit=None):
        from app.engine import evaluate
        try:
            return {stat[0]: int(evaluate.evaluate(stat[1], unit)) for stat in self.value}
        except Exception as e:
            logging.error("Couldn't evaluate conditional for skill %s: [%s], %s", self.skill.nid, str(self.value), e)
        return {stat[0]: 0 for stat in self.value}

class StatMultiplier(SkillComponent):
    nid = 'stat_multiplier'
    desc = "Gives stat bonuses"
    tag = SkillTags.COMBAT

    expose = (ComponentType.FloatDict, ComponentType.Stat)
    value = []

    def stat_change(self, unit):
        return {stat[0]: int((stat[1]-1)*unit.stats[stat[0]]) for stat in self.value}

class SubtleStatChange(SkillComponent):
    nid = 'subtle_stat_change'
    desc = "Gives stat bonuses that appear as regular stat increases within in-game ui"
    tag = SkillTags.COMBAT

    expose = (ComponentType.Dict, ComponentType.Stat)
    value = []

    def stat_change(self, unit=None):
        return {stat[0]: stat[1] for stat in self.value}

    def subtle_stat_change(self, unit=None):
        return {stat[0]: stat[1] for stat in self.value}

class GrowthChange(SkillComponent):
    nid = 'growth_change'
    desc = "Gives growth rate % bonuses"
    tag = SkillTags.COMBAT

    expose = (ComponentType.Dict, ComponentType.Stat)
    value = []

    def growth_change(self, unit):
        return {stat[0]: stat[1] for stat in self.value}

class EquationGrowthChange(SkillComponent):
    nid = 'equation_growth_change'
    desc = "Gives growth rate % bonuses equal to chosen equation"
    tag = SkillTags.COMBAT

    expose = ComponentType.Equation

    def growth_change(self, unit):
        value = equations.parser.get(self.value, unit)
        return {stat_nid: value for stat_nid in DB.stats.keys()}

class Damage(SkillComponent):
    nid = 'damage'
    desc = "Gives +X damage"
    tag = SkillTags.COMBAT

    expose = ComponentType.Int
    value = 3

    def modify_damage(self, unit, item):
        return self.value

class EvalDamage(SkillComponent):
    nid = 'eval_damage'
    desc = "Gives +X damage solved using evaluate"
    tag = SkillTags.COMBAT

    expose = ComponentType.String

    def modify_damage(self, unit, item):
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, local_args={'item': item, 'skill': self.skill}))
        except Exception as e:
            logging.error("Couldn't evaluate %s conditional (%s)", self.value, e)
        return 0

class Resist(SkillComponent):
    nid = 'resist'
    desc = "Gives +X damage resist"
    tag = SkillTags.COMBAT

    expose = ComponentType.Int
    value = 2

    def modify_resist(self, unit, item):
        return self.value

class Hit(SkillComponent):
    nid = 'hit'
    desc = "Gives +X accuracy"
    tag = SkillTags.COMBAT

    expose = ComponentType.Int
    value = 15

    def modify_accuracy(self, unit, item):
        return self.value

class EvalHit(SkillComponent):
    nid = 'eval_hit'
    desc = "Gives +X accuracy solved using evaluate"
    tag = SkillTags.COMBAT

    expose = ComponentType.String

    def modify_accuracy(self, unit, item):
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, local_args={'item': item, 'skill': self.skill}))
        except Exception as e:
            logging.error("Couldn't evaluate %s conditional (%s)", self.value, e)
        return 0

class Avoid(SkillComponent):
    nid = 'avoid'
    desc = "Gives +X avoid"
    tag = SkillTags.COMBAT

    expose = ComponentType.Int
    value = 20

    def modify_avoid(self, unit, item):
        return self.value

    def tile_avoid(self):
        return self.value
        
class EvalAvoid(SkillComponent):
    nid = 'eval_avoid'
    desc = "Gives +X avoid solved using evaluate"
    tag = SkillTags.COMBAT

    expose = ComponentType.String

    def modify_avoid(self, unit, item):
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, local_args={'item': item, 'skill': self.skill}))
        except Exception as e:
            logging.error("Couldn't evaluate %s conditional (%s)", self.value, e)
        return 0

class Crit(SkillComponent):
    nid = 'crit'
    desc = "Gives +X crit"
    tag = SkillTags.COMBAT

    expose = ComponentType.Int
    value = 30

    def modify_crit_accuracy(self, unit, item):
        return self.value

class EvalCrit(SkillComponent):
    nid = 'eval_crit'
    desc = "Gives +X crit solved using evaluate"
    tag = SkillTags.COMBAT

    expose = ComponentType.String

    def modify_crit_accuracy(self, unit, item):
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, local_args={'item': item, 'skill': self.skill}))
        except Exception as e:
            logging.error("Couldn't evaluate %s conditional (%s)", self.value, e)
        return 0

class CritAvoid(SkillComponent):
    nid = 'crit_avoid'
    desc = "Gives +X crit avoid"
    tag = SkillTags.COMBAT

    expose = ComponentType.Int
    value = 10

    def modify_crit_avoid(self, unit, item):
        return self.value

class AttackSpeed(SkillComponent):
    nid = 'attack_speed'
    desc = "Gives +X attack speed"
    tag = SkillTags.COMBAT

    expose = ComponentType.Int
    value = 4

    def modify_attack_speed(self, unit, item):
        return self.value

class DefenseSpeed(SkillComponent):
    nid = 'defense_speed'
    desc = "Gives +X defense speed"
    tag = SkillTags.COMBAT

    expose = ComponentType.Int
    value = 4

    def modify_defense_speed(self, unit, item):
        return self.value

class DamageMultiplier(SkillComponent):
    nid = 'damage_multiplier'
    desc = "Multiplies damage given by a fraction"
    tag = SkillTags.COMBAT

    expose = ComponentType.Float
    value = 0.5

    def damage_multiplier(self, unit, item, target, item2, mode, attack_info, base_value):
        return self.value

class DynamicDamageMultiplier(SkillComponent):
    nid = 'dynamic_damage_multiplier'
    desc = "Multiplies damage given by a fraction"
    tag = SkillTags.COMBAT

    expose = ComponentType.String

    def damage_multiplier(self, unit, item, target, item2, mode, attack_info, base_value):
        from app.engine import evaluate
        try:
            local_args = {'item': item, 'item2': item2, 'mode': mode, 'skill': self.skill, 'attack_info': attack_info, 'base_value': base_value}
            return float(evaluate.evaluate(self.value, unit, target, unit.position, local_args))
        except Exception:
            print("Couldn't evaluate %s conditional" % self.value)
            return 1

class ResistMultiplier(SkillComponent):
    nid = 'resist_multiplier'
    desc = "Multiplies damage taken by a fraction"
    tag = SkillTags.COMBAT

    expose = ComponentType.Float
    value = 0.5

    def resist_multiplier(self, unit, item, target, item2, mode, attack_info, base_value):
        return self.value

class PCC(SkillComponent):
    nid = 'pcc'
    desc = "Multiplies crit chance by a stat on second strike"
    tag = SkillTags.COMBAT

    expose = ComponentType.Stat

    def crit_multiplier(self, unit, item, target, item2, mode, attack_info, base_value):
        return unit.get_stat(self.value) if attack_info[0] > 0 else 1


class PCCStatic(SkillComponent):
    nid = 'pcc_static'
    desc = "Multiplies crit chance by a fixed value on second strike"
    tag = SkillTags.COMBAT
    author = 'BigMood'

    expose = ComponentType.Float
    value = 1

    def crit_multiplier(self, unit, item, target, item2, mode, attack_info, base_value):
        return self.value if attack_info[0] > 0 else 1

class ResistFollowUp(SkillComponent):
    nid = 'resist_follow_up'
    desc = "Multiplies damage taken by a fraction after the first strike"
    tag = SkillTags.COMBAT

    expose = ComponentType.Float
    value = 0.5

    def resist_multiplier(self, unit, item, target, item2, mode, attack_info, base_value):
        return self.value if attack_info[0] > 0 else 1
