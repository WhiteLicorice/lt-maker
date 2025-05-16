from __future__ import annotations

from app.data.database.skill_components import SkillComponent, SkillTags
from app.data.database.components import ComponentType

from app.utilities import utils
from app.utilities.enums import Strike
from app.engine import action, item_system, skill_system
from app.engine.game_state import game
from app.engine.combat import playback as pb

import logging


class Miracle(SkillComponent):
    nid = 'miracle'
    desc = "Unit will not die after combat, but will instead be resurrected with 1 hp"
    tag = SkillTags.COMBAT2

    def cleanup_combat(self, playback, unit, item, target, item2, mode):
        if unit.get_hp() <= 0:
            action.do(action.SetHP(unit, 1))
            game.death.miracle(unit)
            action.do(action.TriggerCharge(unit, self.skill))


class TrueMiracle(SkillComponent):
    nid = 'TrueMiracle'
    desc = "Unit cannot go beneath 1hp"
    tag = SkillTags.COMBAT2

    def after_take_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        did_something = False
        for act in reversed(actions):
            if isinstance(act, action.ChangeHP) and -act.num >= act.old_hp and act.unit == unit:
                act.num = -act.old_hp + 1
                did_something = True
                playback.append(pb.DefenseHitProc(unit, self.skill))

        if did_something:
            actions.append(action.TriggerCharge(unit, self.skill))


class IgnoreDamage(SkillComponent):
    nid = 'ignore_damage'
    desc = "Unit will ignore all damage"
    tag = SkillTags.COMBAT2

    def after_take_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        # Remove any acts that reduce my HP!
        did_something = False
        for act in reversed(actions):
            if isinstance(act, action.ChangeHP) and act.num < 0 and act.unit == unit:
                actions.remove(act)
                did_something = True

        if did_something:
            actions.append(action.TriggerCharge(unit, self.skill))


class LiveToServe(SkillComponent):
    nid = 'live_to_serve'
    desc = r"Unit will be healed X% of amount healed"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Float
    value = 1.0

    def after_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        total_amount_healed = 0
        playbacks = [p for p in playback if p.nid ==
                     'heal_hit' and p.attacker is unit and p.defender is not unit]
        for p in playbacks:
            total_amount_healed += p.damage

        amount = int(total_amount_healed * self.value)
        if amount > 0:
            true_heal = min(amount, unit.get_max_hp() - unit.get_hp())
            playback.append(pb.HealHit(unit, item, unit, true_heal, true_heal))
            actions.append(action.ChangeHP(unit, amount))
            actions.append(action.TriggerCharge(unit, self.skill))


class Lifetaker(SkillComponent):
    nid = 'lifetaker'
    desc = r"Heal % of total HP after a kill"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Float
    value = 0.5

    def end_combat(self, playback, unit, item, target, item2, mode):
        playbacks = [p for p in playback if p.nid in (
            'mark_hit', 'mark_crit') and p.attacker is unit and p.defender is not unit and p.defender.is_dying]
        unique_units = {p.defender for p in playbacks}
        num_playbacks = len(unique_units)
        if num_playbacks > 0:
            amount = max(2, int(unit.get_max_hp() *
                                self.value * num_playbacks))
            if amount > 0:
                true_heal = min(amount, unit.get_max_hp() - unit.get_hp())
                playback.append(pb.HealHit(
                    unit, item, unit, true_heal, true_heal))
                action.do(action.ChangeHP(unit, amount))
                action.do(action.TriggerCharge(unit, self.skill))


class Lifelink(SkillComponent):
    nid = 'lifelink'
    desc = "Heals user %% of damage dealt"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Float
    value = 0.5

    def after_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        total_damage_dealt = 0
        playbacks = [p for p in playback if p.nid in (
            'damage_hit', 'damage_crit') and p.attacker == unit]
        for p in playbacks:
            total_damage_dealt += p.true_damage

        damage = utils.clamp(total_damage_dealt, 0, target.get_hp())
        true_damage = int(damage * self.value)
        actions.append(action.ChangeHP(unit, true_damage))

        playback.append(pb.HealHit(unit, item, unit, true_damage, true_damage))

        actions.append(action.TriggerCharge(unit, self.skill))


class AllyLifelink(SkillComponent):
    nid = 'ally_lifelink'
    desc = "Heals adjacent allies %% of damage dealt"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Float
    value = 0.5

    def after_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        total_damage_dealt = 0
        playbacks = [p for p in playback if p.nid in (
            'damage_hit', 'damage_crit') and p.attacker == unit]
        for p in playbacks:
            total_damage_dealt += p.true_damage

        damage = utils.clamp(total_damage_dealt, 0, target.get_hp())
        true_damage = int(damage * self.value)
        if true_damage > 0 and unit.position:
            adj_positions = game.target_system.get_adjacent_positions(unit.position)
            did_happen = False
            for adj_pos in adj_positions:
                other = game.board.get_unit(adj_pos)
                if other and skill_system.check_ally(other, unit):
                    actions.append(action.ChangeHP(other, true_damage))
                    playback.append(pb.HealHit(
                        unit, item, other, true_damage, true_damage))
                    did_happen = True

            if did_happen:
                actions.append(action.TriggerCharge(unit, self.skill))


class Armsthrift(SkillComponent):
    nid = 'armsthrift'
    desc = 'Restores uses on hit.'
    tag = SkillTags.COMBAT2

    expose = ComponentType.Int
    value = 1

    _did_something = False

    def _after_strike(self, actions, unit, item):
        if item_system.unrepairable(unit, item):
            return  # Don't restore for unrepairable items
        # Handles Uses
        if item.data.get('uses', None) and item.data.get('starting_uses', None):
            curr_uses = item.data.get('uses')
            max_uses = item.data.get('starting_uses')
            actions.append(action.SetObjData(
                item, 'uses', min(curr_uses + self.value - 1, max_uses)))
        # Handles Chapter Uses
        if item.data.get('c_uses', None) and item.data.get('starting_c_uses', None):
            curr_uses = item.data.get('c_uses')
            max_uses = item.data.get('starting_c_uses')
            actions.append(action.SetObjData(
                item, 'c_uses', min(curr_uses + self.value - 1, max_uses)))

    def _post_combat(self, unit, item):
        if item_system.unrepairable(unit, item):
            return  # Don't restore for unrepairable items
        # Handles Uses
        if item.data.get('uses', None) and item.data.get('starting_uses', None):
            curr_uses = item.data.get('uses')
            max_uses = item.data.get('starting_uses')
            # No -1 for post combat since action.do has already happened
            action.do(action.SetObjData(item, 'uses', min(
                curr_uses + self.value, max_uses)))
        # Handles Chapter Uses
        if item.data.get('c_uses', None) and item.data.get('starting_c_uses', None):
            curr_uses = item.data.get('c_uses')
            max_uses = item.data.get('starting_c_uses')
            action.do(action.SetObjData(item, 'c_uses',
                                        min(curr_uses + self.value, max_uses)))

    def after_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        if not item:
            return

        if item.parent_item:
            self.after_strike(actions, playback, unit,
                              item.parent_item, target, item2, mode, attack_info, strike)
        if strike != Strike.MISS or (item.uses_options and item.uses_options.lose_uses_on_miss()):
            self._did_something = True
            self._after_strike(actions, unit, item)

    def post_combat(self, playback, unit, item, target, item2, mode):
        # handles one loss per combat + armsthift interaction
        if not item:
            return

        if self._did_something:
            if item.parent_item:
                self.post_combat(
                    playback, unit, item.parent_item, target, item2, mode)
            if (item.uses_options and item.uses_options.one_loss_per_combat()):
                self._post_combat(unit, item)

        self._did_something = False


class LimitMaximumRange(SkillComponent):
    nid = 'limit_maximum_range'
    desc = "limits unit's maximum allowed range"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Int
    value = 1

    def limit_maximum_range(self, unit, item):
        return self.value


class ModifyMaximumRange(SkillComponent):
    nid = 'modify_maximum_range'
    desc = "modifies unit's maximum allowed range"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Int
    value = 1

    def modify_maximum_range(self, unit, item):
        return self.value


class ModifyMinimumRange(SkillComponent):
    nid = 'modify_minimum_range'
    desc = "modifies unit's minimum allowed range"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Int
    value = 1

    def modify_minimum_range(self, unit, item):
        return self.value


class EvalMaximumRange(SkillComponent):
    nid = 'eval_max_range'
    desc = "Gives +X range to the maximum solved using evaluate"
    tag = SkillTags.COMBAT2

    expose = ComponentType.String

    def modify_maximum_range(self, unit, item):
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, local_args={'item': item}))
        except:
            logging.error("Couldn't evaluate %s conditional" % self.value)
        return 0

    def has_dynamic_range(sellf, unit):
        return True


class EvalMinimumRange(SkillComponent):
    nid = 'eval_min_range'
    desc = "Adds +X range to the minimum solved using evaluate"
    tag = SkillTags.COMBAT2

    expose = ComponentType.String

    def modify_minimum_range(self, unit, item):
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, local_args={'item': item}))
        except:
            logging.error("Couldn't evaluate %s conditional" % self.value)
        return 0

    def has_dynamic_range(sellf, unit):
        return True


class CannotDouble(SkillComponent):
    nid = 'cannot_double'
    desc = "Unit cannot double"
    tag = SkillTags.COMBAT2

    def no_double(self, unit):
        return True


class CanDoubleOnDefense(SkillComponent):
    nid = 'can_double_on_defense'
    desc = "Unit can double while defending (extraneous if set to True in constants)"
    tag = SkillTags.COMBAT2

    def def_double(self, unit):
        return True

class Vantage(SkillComponent):
    nid = 'vantage'
    desc = "Unit will attack first even while defending"
    tag = SkillTags.COMBAT2

    def vantage(self, unit):
        return True


class Desperation(SkillComponent):
    nid = 'desperation'
    desc = "Unit will attack as much as possible when given the opportunity"
    tag = SkillTags.COMBAT2

    def desperation(self, unit):
        return True


class GuaranteedCrit(SkillComponent):
    nid = 'guaranteed_crit'
    desc = "Unit will always crit even if crit constant is turned off"
    tag = SkillTags.COMBAT2

    def crit_anyway(self, unit):
        return True


class DistantCounter(SkillComponent):
    nid = 'distant_counter'
    desc = "Unit has infinite range when defending"
    tag = SkillTags.COMBAT2

    def distant_counter(self, unit):
        return True


class CloseCounter(SkillComponent):
    nid = 'close_counter'
    desc = "Unit can retaliate against adjacent foes even if otherwise unable to"
    tag = SkillTags.COMBAT2

    def close_counter(self, unit):
        return True
        
class CannotCounter(SkillComponent):
    nid = 'cannot_counter'
    desc = "Unit cannot retaliate in combat"
    tag = SkillTags.COMBAT2

    def can_counter(self, unit):
        return False


class Cleave(SkillComponent):
    nid = 'Cleave'
    desc = "Grants unit the ability to cleave with all their non-splash attacks"
    tag = SkillTags.COMBAT2

    def alternate_splash(self, unit):
        from app.engine.item_components.aoe_components import EnemyCleaveAOE
        return EnemyCleaveAOE()


class GiveStatusAfterCombat(SkillComponent):
    nid = 'give_status_after_combat'
    desc = "Gives a status to target enemy after combat"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Skill

    def end_combat(self, playback, unit, item, target, item2, mode):
        from app.engine import skill_system
        if target and skill_system.check_enemy(unit, target):
            action.do(action.AddSkill(target, self.value, unit))
            action.do(action.TriggerCharge(unit, self.skill))


class GiveAllyStatusAfterCombat(SkillComponent):
    nid = 'give_ally_status_after_combat'
    desc = "Gives a status to target ally after combat"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Skill

    def end_combat(self, playback, unit, item, target, item2, mode):
        from app.engine import skill_system
        if target and skill_system.check_ally(unit, target):
            action.do(action.AddSkill(target, self.value, unit))
            action.do(action.TriggerCharge(unit, self.skill))


class GiveStatusAfterAttack(SkillComponent):
    nid = 'give_status_after_attack'
    desc = "Gives a status to target after attacking the target"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Skill

    def end_combat(self, playback, unit, item, target, item2, mode):
        mark_playbacks = [p for p in playback if p.nid in (
            'mark_miss', 'mark_hit', 'mark_crit')]
        if target and any(p.attacker is unit and (p.main_attacker is unit or p.attacker is p.main_attacker.strike_partner)
                          for p in mark_playbacks):  # Unit is overall attacker
            action.do(action.AddSkill(target, self.value, unit))
            action.do(action.TriggerCharge(unit, self.skill))


class GiveStatusAfterCombatOnHit(SkillComponent):
    nid = 'give_status_after_combat_on_hit'
    desc = "Gives a status to target after combat assuming you hit the target"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Skill

    def end_combat(self, playback, unit, item, target, item2, mode):
        mark_playbacks = [p for p in playback if p.nid in (
            'mark_hit', 'mark_crit')]
        if target and any(p.attacker is unit and (p.main_attacker is unit or p.attacker is p.main_attacker.strike_partner)
                          for p in mark_playbacks):  # Unit is overall attacker
            action.do(action.AddSkill(target, self.value, unit))
            action.do(action.TriggerCharge(unit, self.skill))


class GiveStatusAfterHit(SkillComponent):
    nid = 'give_status_after_hit'
    desc = "Gives a status to target after hitting them"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Skill

    def after_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        mark_playbacks = [p for p in playback if p.nid in (
            'mark_hit', 'mark_crit')]

        if target and any(p.attacker == unit for p in mark_playbacks):
            actions.append(action.AddSkill(target, self.value, unit))
            actions.append(action.TriggerCharge(unit, self.skill))


class SkillBeforeCombat(SkillComponent):
    nid = 'skill_before_combat'
    desc = 'Grants a skill before combat'
    tag = SkillTags.COMBAT2

    expose = ComponentType.NewMultipleOptions

    options = {
        "skill": ComponentType.Skill,
        "recipient": (ComponentType.MultipleChoice, ("self", "target", "both")),
        "allegiance": (ComponentType.MultipleChoice, ("ally", "enemy", "both")),
    }

    def __init__(self, value=None):
        self.value = {
            "skill": None,
            "recipient": "target",
            "allegiance": "enemy"
        }
        if value:
            self.value.update(value)

    def get_skill_nid(self):
        return self.value['skill']

    def _resolve_targets(self, unit, target) -> list:
        recipient = self.value['recipient']
        allegiance = self.value['allegiance']
        if recipient == 'self':
            return [unit]
        if recipient == 'target':
            if not target:
                return []
            is_ally = skill_system.check_ally(unit, target)
            if allegiance == 'enemy' and is_ally:
                return []
            if allegiance == 'ally' and not is_ally:
                return []
            return [target]
        return [unit, target]

    def start_combat(self, playback, unit, item, target, item2, mode):
        skill_nid = self.get_skill_nid()
        if not skill_nid:
            return
        targets = self._resolve_targets(unit, target)
        for skill_gainer in targets:
            action.do(action.AddSkill(skill_gainer, skill_nid))
        if targets:
            action.do(action.TriggerCharge(unit, self.skill))


class GainSkillAfterKill(SkillComponent):
    nid = 'gain_skill_after_kill'
    desc = "Gives a skill to user after a kill"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Skill

    def end_combat(self, playback, unit, item, target, item2, mode):
        if target and target.get_hp() <= 0:
            action.do(action.AddSkill(unit, self.value))
            action.do(action.TriggerCharge(unit, self.skill))


class GainSkillAfterCombat(SkillComponent):
    nid = 'gain_skill_after_combat'
    desc = "Gives a skill to user after any combat"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Skill

    def end_combat(self, playback, unit, item, target, item2, mode):
        action.do(action.AddSkill(unit, self.value))
        action.do(action.TriggerCharge(unit, self.skill))


class GainSkillAfterAttacking(SkillComponent):
    nid = 'gain_skill_after_attack'
    desc = "Gives a skill to user after an attack"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Skill

    def end_combat(self, playback, unit, item, target, item2, mode):
        mark_playbacks = [p for p in playback if p.nid in (
            'mark_miss', 'mark_hit', 'mark_crit')]
        # Unit is overall attacker
        if any(p.attacker is unit and p.main_attacker is unit for p in mark_playbacks):
            action.do(action.AddSkill(unit, self.value))
            action.do(action.TriggerCharge(unit, self.skill))


class GainSkillAfterActiveKill(SkillComponent):
    nid = 'gain_skill_after_active_kill'
    desc = "Gives a skill after a kill on personal phase"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Skill

    def end_combat(self, playback, unit, item, target, item2, mode):
        mark_playbacks = [p for p in playback if p.nid in (
            'mark_miss', 'mark_hit', 'mark_crit')]
        if target and target.get_hp() <= 0 and any(p.main_attacker is unit for p in mark_playbacks):  # Unit is overall attacker
            action.do(action.AddSkill(unit, self.value))
            action.do(action.TriggerCharge(unit, self.skill))


class GainSkillAfterTakeMiss(SkillComponent):
    nid = 'gain_skill_after_take_miss'
    desc = "Gain a skill immediately after an enemy misses you"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Skill

    def after_take_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        if strike == Strike.MISS:
            actions.append(action.AddSkill(unit, self.value, unit))
            actions.append(action.TriggerCharge(unit, self.skill))


class GainSkillAfterTakeDamage(SkillComponent):
    nid = 'gain_skill_after_take_damage'
    desc = "Gain a skill immediately after an enemy damages you"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Skill

    def after_take_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        for act in actions:
            if isinstance(act, action.ChangeHP) and act.num < 0 and act.unit == unit:
                actions.append(action.AddSkill(unit, self.value, unit))
                actions.append(action.TriggerCharge(unit, self.skill))
                return


class DelayInitiativeOrder(SkillComponent):
    nid = 'delay_initiative_order'
    desc = "Delays the target's next turn by X after hit. Cannot activate when unit is defending."
    tag = SkillTags.COMBAT2

    expose = ComponentType.Int
    value = 1
    author = "KD"

    def after_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        mark_playbacks = [p for p in playback if p.nid in (
            'mark_hit', 'mark_crit')]
        if target and target.get_hp() >= 0 and any(p.attacker is unit and p.main_attacker is unit for p in mark_playbacks):  # Unit is overall attacker
            actions.append(action.MoveInInitiative(target, self.value))
            actions.append(action.TriggerCharge(unit, self.skill))


class Recoil(SkillComponent):
    nid = 'recoil'
    desc = "Unit takes non-lethal damage after combat with an enemy"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Int
    value = 0
    author = 'Lord_Tweed'

    def end_combat(self, playback, unit, item, target, item2, mode):
        if target and skill_system.check_enemy(unit, target):
            end_health = unit.get_hp() - self.value
            action.do(action.SetHP(unit, max(1, end_health)))
            action.do(action.TriggerCharge(unit, self.skill))


class PostCombatDamage(SkillComponent):
    nid = 'post_combat_damage'
    desc = "Target takes non-lethal flat damage after combat"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Int
    value = 0
    author = 'Lord_Tweed'

    def end_combat(self, playback, unit, item, target, item2, mode):
        if target and skill_system.check_enemy(unit, target):
            end_health = target.get_hp() - self.value
            action.do(action.SetHP(target, max(1, end_health)))
            action.do(action.TriggerCharge(unit, self.skill))


class PostCombatDamagePercent(SkillComponent):
    nid = 'post_combat_damage_percent'
    desc = "Target takes non-lethal MaxHP percent damage after combat"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Float
    value = 0.2
    author = 'Lord_Tweed'

    def end_combat(self, playback, unit, item, target, item2, mode):
        if target and skill_system.check_enemy(unit, target):
            end_health = int(target.get_hp() -
                             (target.get_max_hp() * self.value))
            action.do(action.SetHP(target, max(1, end_health)))
            action.do(action.TriggerCharge(unit, self.skill))


class PostCombatSplash(SkillComponent):
    nid = 'post_combat_splash'
    desc = "Deals flat damage to enemies in a range defined by the PostCombatSplashAOE component"
    tag = SkillTags.COMBAT2
    paired_with = ('post_combat_splash_aoe', )

    expose = ComponentType.Int
    value = 0
    author = 'Lord_Tweed'

    def post_combat_damage(self) -> int:
        return self.value


class PostCombatSplashAOE(SkillComponent):
    nid = 'post_combat_splash_aoe'
    desc = 'Defines the range for PostCombatSplash damage to hit.'
    tag = SkillTags.COMBAT2
    paired_with = ('post_combat_splash', )

    expose = ComponentType.Int
    value = 0
    author = 'Lord_Tweed'

    def end_combat(self, playback, unit, item, target, item2, mode):
        if target and skill_system.check_enemy(unit, target):
            r = set(range(self.value+1))
            locations = game.target_system.get_shell(
                {target.position}, r, game.board.bounds)
            damage = get_pc_damage(unit, self.skill)
            if damage > 0:
                for loc in locations:
                    target2 = game.board.get_unit(loc)
                    if target2 and target2 is not target and skill_system.check_enemy(unit, target2):
                        end_health = target2.get_hp() - damage
                        action.do(action.SetHP(target2, max(1, end_health)))


def get_pc_damage(unit, skill) -> int:
    for component in skill.components:
        if component.defines('post_combat_damage'):
            return component.post_combat_damage()
    return 0  # 0 is default


class AllBrave(SkillComponent):
    nid = 'all_brave'
    desc = "All items multi-attack"
    tag = SkillTags.COMBAT2
    author = 'BigMood'

    def dynamic_multiattacks(self, unit, item, target, item2, mode, attack_info, base_value):
        return 1

class DevilAxeGBA(SkillComponent):
    nid = 'devil_axe_gba'
    desc = "Make attacks backfire: Deal 0 damage to the defender and deal full damage to the attacker instead."
    tag = SkillTags.COMBAT2

    expose = (ComponentType.MultipleChoice, ["Affect attacks done by %s" % i for i in ('unit', 'enemy')])
    value = "Affect attacks done by %s" % 'unit'

    def _make_attacks_backfire(self, actions, playback, unit, attacker, defender, item):
        for act in reversed(actions):
            if isinstance(act, action.ChangeHP) and act.num < 0 and act.unit == defender:
                actions.remove(act)

        total_damage_dealt = 0
        playbacks = [p for p in playback if p.nid in (
            'damage_hit', 'damage_crit') and p.defender == defender]
        for p in playbacks:
            total_damage_dealt += p.damage
            p.defender = attacker

        damage = -utils.clamp(total_damage_dealt, 0, attacker.get_hp())

        actions.append(action.ChangeHP(attacker, damage))
        actions.append(action.TriggerCharge(unit, self.skill))

    def after_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        if self.value == "Affect attacks done by %s" % 'unit':
            self._make_attacks_backfire(actions, playback, unit, unit, target, item)

    def after_take_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        if self.value == "Affect attacks done by %s" % 'enemy':
            self._make_attacks_backfire(actions, playback, unit, target, unit, item2)