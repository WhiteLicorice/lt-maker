from app.data.database.skill_components import SkillComponent, SkillTags
from app.data.database.components import ComponentType

from app.engine import action
from app.utilities import utils

class BuildCharge(SkillComponent):
    nid = 'build_charge'
    desc = "Skill starts each chapter with 0 charges. Skill will only be active while the there are *value* or more charges. Upon use of skill, charges are reset to 0. Often used with Combat Arts."
    tag = SkillTags.CHARGE

    expose = ComponentType.Int
    value = 10

    ignore_conditional = True

    def init(self, skill):
        self.skill.data['charge'] = 0
        self.skill.data['total_charge'] = self.value

    def condition(self, unit, item):
        return self.skill.data['charge'] >= self.skill.data['total_charge']

    def on_end_chapter(self, unit, skill):
        self.skill.data['charge'] = 0

    def trigger_charge(self, unit, skill):
        action.do(action.SetObjData(self.skill, 'charge', 0))

    def text(self) -> str:
        return str(self.skill.data['charge'])

    def cooldown(self):
        if self.skill.data.get('total_charge'):
            return self.skill.data['charge'] / self.skill.data['total_charge']
        else:
            return 1

class DrainCharge(SkillComponent):
    nid = 'drain_charge'
    desc = "Skill starts each chapter with the number of charges you set here. Every use of the skill will reduce the number of charges by 1. Skill is active while the number of charges is greater than 0. Often used with Combat Arts."
    tag = SkillTags.CHARGE

    expose = ComponentType.Int
    value = 1

    ignore_conditional = True

    def init(self, skill):
        self.skill.data['charge'] = self.value
        self.skill.data['total_charge'] = self.value

    def condition(self, unit, item):
        return self.skill.data['charge'] > 0

    def on_end_chapter(self, unit, skill):
        self.skill.data['charge'] = self.skill.data['total_charge']

    def trigger_charge(self, unit, skill):
        new_value = self.skill.data['charge'] - 1
        action.do(action.SetObjData(self.skill, 'charge', new_value))

    def text(self) -> str:
        return str(self.skill.data['charge'])

    def cooldown(self):
        return self.skill.data['charge'] / self.skill.data['total_charge']

class ChargesPerTurn(DrainCharge):
    nid = 'charges_per_turn'
    desc = "Skill starts each turn with the number of charges you set here. Every use of the skill will reduce the number of charges by 1. Skill is active while the number of charges is greater than 0."
    tag = SkillTags.CHARGE

    expose = ComponentType.Int
    value = 1

    ignore_conditional = True

    def on_endstep(self, actions, playback, unit):
        value = self.skill.data['total_charge']
        action.do(action.SetObjData(self.skill, 'charge', value))

class UpkeepChargeIncrease(SkillComponent):
    nid = 'upkeep_charge_increase'
    desc = "Increases charge of skill by the *value* set here each upkeep. Usually used in conjunction with `Build Charge` skill component. Will not go below 0 or above `total_charge`"
    tag = SkillTags.CHARGE

    expose = ComponentType.Int
    value = 5

    ignore_conditional = True

    def on_upkeep(self, actions, playback, unit):
        new_value = self.skill.data['charge'] + self.value
        new_value = utils.clamp(new_value, 0, self.skill.data['total_charge'])
        action.do(action.SetObjData(self.skill, 'charge', new_value))

def get_marks(playback, unit, item):
    from app.data.database.database import DB
    marks = [mark for mark in playback if mark.nid == 'mark_hit']
    marks += [mark for mark in playback if mark.nid == 'mark_crit']
    if DB.constants.value('miss_wexp'):
        marks += [mark for mark in playback if mark.nid == 'mark_miss']
    marks = [mark for mark in marks if mark.attacker == unit and mark.defender != unit and mark.item == item]
    return marks

class CombatChargeIncrease(SkillComponent):
    nid = 'combat_charge_increase'
    desc = "Increases charge of skill by the *value* set here each combat. Usually used in conjunction with `Build Charge` skill component."
    tag = SkillTags.CHARGE

    expose = ComponentType.Int
    value = 5

    ignore_conditional = True

    def end_combat(self, playback, unit, item, target, item2, mode):
        marks = get_marks(playback, unit, item)
        if not self.skill.data.get('active') and marks:
            new_value = self.skill.data['charge'] + self.value
            new_value = min(new_value, self.skill.data['total_charge'])
            action.do(action.SetObjData(self.skill, 'charge', new_value))

class CombatChargeIncreaseByStat(SkillComponent):
    nid = 'combat_charge_increase_by_stat'
    desc = "Increases charge of skill by the *value* set here each combat. Usually used in conjunction with `Build Charge` skill component."
    tag = SkillTags.CHARGE

    expose = ComponentType.Stat
    value = 'SKL'

    ignore_conditional = True

    def end_combat(self, playback, unit, item, target, item2, mode):
        marks = get_marks(playback, unit, item)
        if not self.skill.data.get('active') and marks:
            new_value = self.skill.data['charge'] + unit.stats[self.value] + unit.stat_bonus(self.value)
            new_value = min(new_value, self.skill.data['total_charge'])
            action.do(action.SetObjData(self.skill, 'charge', new_value))

class GainMana(SkillComponent):
    nid = 'gain_mana'
    desc = "Gain mana at the beginning of each combat with a target."
    tag = SkillTags.CHARGE
    author = 'KD'

    expose = ComponentType.String

    def start_combat(self, playback, unit, item, target, item2, mode):
        from app.engine import evaluate
        try:
            if target:
                mana_gain = int(evaluate.evaluate(self.value, unit, target, position=unit.position, local_args={'item': item, 'skill': self.skill}))
                action.do(action.ChangeMana(unit, mana_gain))
        except Exception as e:
            print("Could not evaluate %s (%s)" % (self.value, e))
            return True

class CostMana(SkillComponent):
    nid = 'cost_mana'
    desc = "Skill reduces Mana with each use. Unit must have >=X Mana to use the skill."
    tag = SkillTags.CHARGE
    author = 'KD'

    expose = ComponentType.Int
    value = 2

    ignore_conditional = True

    def condition(self, unit, item):
        return unit.current_mana >= self.value

    def start_combat(self, playback, unit, item, target, item2, mode):
        if self.skill.data.get('active'):
            action.do(action.ChangeMana(unit, -self.value))

class CheckMana(SkillComponent):
    nid = 'check_mana'
    desc = "Unit must have X or more Mana to use this skill. Does not subtract Mana on use."
    tag = SkillTags.CHARGE
    author = 'KD'

    expose = ComponentType.Int
    value = 2

    ignore_conditional = True

    def condition(self, unit, item):
        return unit.current_mana >= self.value
