import random

from app.data.database.skill_components import SkillComponent, SkillTags
from app.data.database.components import ComponentType

from app.engine import equations, action, skill_system
from app.engine.game_state import game
from app.engine.combat import playback as pb
from app.utilities import static_random
from app.utilities.enums import Strike
from app.engine.source_type import SourceType

class Aura(SkillComponent):
    nid = 'aura'
    desc = "Skill has an aura that gives off child skill"
    tag = SkillTags.STATUS
    paired_with = ('aura_range', 'aura_target')

    expose = ComponentType.Skill

class AuraRange(SkillComponent):
    nid = 'aura_range'
    desc = "Set range of skill's aura"
    tag = SkillTags.STATUS
    paired_with = ('aura', 'aura_target')

    expose = ComponentType.Int
    value = 3

class AuraTarget(SkillComponent):
    nid = 'aura_target'
    desc = "Set target of skill's aura (set to 'ally', 'enemy', or 'unit')"
    tag = SkillTags.STATUS
    paired_with = ('aura', 'aura_range')

    # expose = ComponentType.String
    expose = (ComponentType.MultipleChoice, ('ally', 'enemy', 'unit'))
    value = 'unit'

class AuraShow(SkillComponent):
    nid = 'show_aura'
    desc = 'Aura will always show with this color on the map'
    tag = SkillTags.STATUS
    paired_with = ('aura', 'aura_range', 'aura_target')

    expose = ComponentType.Color3
    value = (128, 0, 0)

class HideAura(SkillComponent):
    nid = 'hide_aura'
    desc = 'Aura\'s highlight will never appear on the map'
    tag = SkillTags.STATUS
    paired_with = ('aura', 'aura_range', 'aura_target')
    
class AuraShape(SkillComponent):
    nid = 'aura_shape'
    desc = """Aura affects tiles in a specified shape around the user. 
    The pattern will be extended according to the aura's range.
    Set an aura range of 1 to use the drawn pattern with no extension."""
    tag = SkillTags.STATUS
    expose = ComponentType.Shape
    value = []
    
    def get_shape(self, unit, skill):
        value_list = set()
        coords = self.value
        for i in range(1, skill.aura_range.value + 1):
            for coord in coords:
                value_list.add((unit.position[0] + i * coord[0], unit.position[1] + i * coord[1]))
        return value_list
        
    def get_max_shape_range(self, skill):
        if len(self.value) > 0:
            return max([abs(pos[0]) + abs(pos[1]) for pos in self.value]) * skill.aura_range.value
        else:
            return 0

class PairUpBonus(SkillComponent):
    nid = 'pairup_bonus'
    desc = "Grants a child skill to lead units while in guard stance."
    tag = SkillTags.STATUS

    expose = ComponentType.Skill

    def on_pairup(self, unit, leader):
        action.do(action.AddSkill(leader, self.value, source=unit.nid, source_type=SourceType.TRAVELER))

    def on_separate(self, unit, leader):
        if self.value in [skill.nid for skill in leader.skills]:
            action.do(action.RemoveSkill(leader, self.value, source=unit.nid, source_type=SourceType.TRAVELER))

class Regeneration(SkillComponent):
    nid = 'regeneration'
    desc = "Unit restores %% of HP at beginning of turn"
    tag = SkillTags.STATUS

    expose = ComponentType.Float
    value = 0.2

    def on_upkeep(self, actions, playback, unit):
        max_hp = equations.parser.hitpoints(unit)
        if unit.get_hp() < max_hp:
            hp_change = int(max_hp * self.value)
            actions.append(action.ChangeHP(unit, hp_change))
            # Playback
            playback.append(pb.HitSound('MapHeal'))
            playback.append(pb.DamageNumbers(unit, -hp_change))
            if hp_change >= 30:
                name = 'MapBigHealTrans'
            elif hp_change >= 15:
                name = 'MapMediumHealTrans'
            else:
                name = 'MapSmallHealTrans'
            playback.append(pb.CastAnim(name))

class ManaRegeneration(SkillComponent):
    nid = 'mana_regeneration'
    desc = "Unit restores X mana at beginning of turn"
    tag = SkillTags.STATUS

    expose = ComponentType.Int

    def on_upkeep(self, actions, playback, unit):
        actions.append(action.ChangeMana(unit, self.value))

class UpkeepDamage(SkillComponent):
    nid = 'upkeep_damage'
    desc = "Unit takes damage at upkeep"
    tag = SkillTags.STATUS

    expose = ComponentType.Int
    value = 5

    def _playback_processing(self, playback, unit, hp_change):
        # Playback
        if hp_change < 0:
            playback.append(pb.HitSound('Attack Hit ' + str(random.randint(1, 5))))
            playback.append(pb.UnitTintAdd(unit, (255, 255, 255)))
            playback.append(pb.DamageNumbers(unit, self.value))
        elif hp_change > 0:
            playback.append(pb.HitSound('MapHeal'))
            if hp_change >= 30:
                name = 'MapBigHealTrans'
            elif hp_change >= 15:
                name = 'MapMediumHealTrans'
            else:
                name = 'MapSmallHealTrans'
            playback.append(pb.CastAnim(name))
            playback.append(pb.DamageNumbers(unit, self.value))

    def on_upkeep(self, actions, playback, unit):
        hp_change = -self.value
        actions.append(action.ChangeHP(unit, hp_change))
        actions.append(action.TriggerCharge(unit, self.skill))
        self._playback_processing(playback, unit, hp_change)
        skill_system.after_take_strike(actions, playback, unit, None, None, None, 'defense', (0, 0), Strike.HIT)

class EndstepDamage(UpkeepDamage):
    nid = 'endstep_damage'
    desc = "Unit takes damage at endstep"
    tag = SkillTags.STATUS

    expose = ComponentType.Int
    value = 5

    def on_upkeep(self, actions, playback, unit):
        pass

    def on_endstep(self, actions, playback, unit):
        hp_change = -self.value
        actions.append(action.ChangeHP(unit, hp_change))
        actions.append(action.TriggerCharge(unit, self.skill))
        self._playback_processing(playback, unit, hp_change)
        skill_system.after_take_strike(actions, playback, unit, None, None, None, 'defense', (0, 0), Strike.HIT)

class GBAPoison(SkillComponent):
    nid = 'gba_poison'
    desc = "Unit takes random amount of damage up to num"
    tag = SkillTags.STATUS

    expose = ComponentType.Int
    value = 5

    def on_upkeep(self, actions, playback, unit):
        old_random_state = static_random.get_combat_random_state()
        hp_loss = -static_random.get_randint(1, self.value)
        new_random_state = static_random.get_combat_random_state()
        actions.append(action.RecordRandomState(old_random_state, new_random_state))
        actions.append(action.ChangeHP(unit, hp_loss))

class ResistStatus(SkillComponent):
    nid = 'resist_status'
    desc = "Unit is only affected by new statuses for a turn"
    tag = SkillTags.STATUS

    def before_gain_skill(self, unit, other_skill):
        if other_skill.time or other_skill.end_time or other_skill.combined_time:
            if skill_system.condition(self.skill, unit):
                action.do(action.SetObjData(other_skill, 'turns', min(other_skill.data['turns'], 1)))

class ImmuneStatus(SkillComponent):
    nid = 'immune_status'
    desc = "Unit does not receive negative statuses and is not affected by existing negative statuses"
    tag = SkillTags.STATUS

    def has_immune(self, unit) -> bool:
        return True

    def after_gain_skill(self, unit, other_skill):
        if other_skill.negative and skill_system.condition(self.skill, unit):
            action.do(action.RemoveSkill(unit, other_skill))

class ReflectStatus(SkillComponent):
    nid = 'reflect_status'
    desc = "Unit reflects statuses back to initiator"
    tag = SkillTags.STATUS

    def after_gain_skill(self, unit, other_skill):
        if other_skill.initiator_nid and skill_system.condition(self.skill, unit):
            other_unit = game.get_unit(other_skill.initiator_nid)
            if other_unit:
                # Create a copy of other skill
                action.do(action.AddSkill(other_unit, other_skill.nid))
