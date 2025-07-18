from app.engine.objects.unit import UnitObject
from app.data.database.skill_components import SkillComponent, SkillTags
from app.data.database.components import ComponentType

from app.engine import action
from app.engine.game_state import game

class DeathTether(SkillComponent):
    nid = 'death_tether'
    desc = "Remove all skills in the game that I initiated on my death"
    tag = SkillTags.ADVANCED

    def on_death(self, unit):
        for other_unit in game.units:
            for skill in other_unit.skills:
                if skill.initiator_nid == unit.nid:
                    action.do(action.RemoveSkill(other_unit, skill))

class Oversplash(SkillComponent):
    nid = 'oversplash'
    desc = "Grants unit +X area of effect for regular and blast items"
    tag = SkillTags.ADVANCED

    expose = ComponentType.Int
    value = 1

    def empower_splash(self, unit):
        return self.value

    def alternate_splash(self, unit):
        from app.engine.item_components.aoe_components import BlastAOE
        return BlastAOE(0)

class EnemyOversplash(Oversplash):
    nid = 'enemy_oversplash'
    desc = "Grants unit +X area of effect for regular and blast items that only affects enemies"

    def alternate_splash(self, unit):
        from app.engine.item_components.aoe_components import EnemyBlastAOE
        return EnemyBlastAOE(0)

class SmartOversplash(Oversplash):
    nid = 'smart_oversplash'
    desc = """
        Grants unit +X area of effect for regular and blast items. If the main target is an enemy, then splash will only affect enemies. 
        The same holds true for allies.
        """

    def alternate_splash(self, unit):
        from app.engine.item_components.aoe_components import SmartBlastAOE
        return SmartBlastAOE(0)

class EmpowerHeal(SkillComponent):
    nid = 'empower_heal'
    desc = "Gives +X extra healing"
    tag = SkillTags.ADVANCED

    expose = ComponentType.String

    def empower_heal(self, unit, target):
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, target, unit.position, local_args={'skill': self.skill}))
        except:
            print("Couldn't evaluate %s conditional" % self.value)
            return 0

class EmpowerHealReceived(SkillComponent):
    nid = 'empower_heal_received'
    desc = "Gives +X extra healing received"
    tag = SkillTags.ADVANCED

    expose = ComponentType.String

    def empower_heal_received(self, target, unit):
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, target, unit, local_args={'skill': self.skill}))
        except:
            print("Couldn't evaluate %s conditional" % self.value)
            return 0

class ManaOnHit(SkillComponent):
    nid = 'mana_on_hit'
    desc = 'Gives +X mana on hit'
    tag = SkillTags.ADVANCED
    author = 'BigMood'

    expose = ComponentType.Int

    def mana(self, playback, unit, item, target):
        mark_playbacks = [p for p in playback if p.nid in ('mark_hit', 'mark_crit')]

        if target and any(p.defender == target for p in mark_playbacks):
            return self.value
        return 0

class ManaOnKill(SkillComponent):
    nid = 'mana_on_kill'
    desc = 'Gives +X mana on kill'
    tag = SkillTags.ADVANCED

    expose = ComponentType.Int

    def mana(self, playback, unit, item, target):
        if target and target.is_dying:
            return self.value
        return 0


class EventAfterInitiatedCombat(SkillComponent):
    nid = 'event_after_initiated_combat'
    desc = 'calls event after combat initated by user'
    tag = SkillTags.ADVANCED

    expose = ComponentType.Event
    value = ''

    def end_combat(self, playback, unit: UnitObject, item, target: UnitObject, item2, mode):
        if mode == 'attack':
            game.events.trigger_specific_event(self.value, unit, target, unit.position, {'item': item, 'item2': item2, 'mode': mode})

class Nihil(SkillComponent):
    nid = 'nihil'
    desc = "Takes a list of skills as its value. If a skill from this list is present on `target`, then *this* skill does not work."
    tag = SkillTags.CUSTOM
    author = 'Eretein/rainlash'

    expose = (ComponentType.List, ComponentType.Skill)
    value = []

    ignore_conditional = True
    _condition = True

    def pre_combat(self, playback, unit, item, target, item2, mode):
        all_target_nihils = set(self.value)
        for skill in target.skills:
            if skill.nid in all_target_nihils:
                self._condition = False
                return
        self._condition = True

    def post_combat_unconditional(self, playback, unit, item, target, item2, mode):
        game.on_alter_game_state()
        self._condition = True

    def condition(self, unit, item):
        return self._condition

    def test_on(self, playback, unit, item, target, item2, mode):
        game.on_alter_game_state()
        self.pre_combat(playback, unit, item, target, item2, mode)

    def test_off(self, playback, unit, item, target, item2, mode):
        game.on_alter_game_state()
        self._condition = True