from app.utilities import utils

from app.data.database.database import DB

from app.data.database.item_components import ItemComponent, ItemTags
from app.data.database.components import ComponentType

from app.engine import action, combat_calcs, equations, banner
from app.engine import item_system, skill_system, item_funcs
from app.engine.game_state import game
from app.engine.combat import playback as pb
from app.engine.movement import movement_funcs

class PermanentStatChange(ItemComponent):
    nid = 'permanent_stat_change'
    desc = "Using this item permanently changes the stats of the target in the specified ways. The target and user are often the same unit (think of normal FE stat boosters)."
    tag = ItemTags.SPECIAL

    expose = (ComponentType.Dict, ComponentType.Stat)

    _hit_count = 0

    def _target_restrict(self, defender):
        for stat, inc in self.value:
            if inc <= 0 or defender.stats[stat] < defender.get_stat_cap(stat):
                return True
        return False

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # Ignore's splash
        defender = game.board.get_unit(def_pos)
        if not defender:
            return True
        return self._target_restrict(defender)

    def simple_target_restrict(self, unit, item):
        return self._target_restrict(unit)

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        self._hit_count += 1
        playback.append(pb.StatHit(unit, item, target))

    def end_combat(self, playback, unit, item, target, item2, mode):
        if self._hit_count > 0:
            stat_changes = {k: v*self._hit_count for (k, v) in self.value}
            # clamp stat changes
            stat_changes = {k: utils.clamp(v, -target.stats[k], unit.get_stat_cap(k) - target.stats[k]) for k, v in stat_changes.items()}
            action.do(action.ApplyStatChanges(target, stat_changes))
            if any(v != 0 for v in stat_changes.values()):
                game.memory['stat_changes'] = stat_changes
                game.exp_instance.append((target, 0, None, 'stat_booster'))
                game.state.change('exp')
        self._hit_count = 0

class PermanentGrowthChange(ItemComponent):
    nid = 'permanent_growth_change'
    desc = "Using this item permanently changes the growth values of the target in the specified ways."
    tag = ItemTags.SPECIAL

    expose = (ComponentType.Dict, ComponentType.Stat)

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        growth_changes = {k: v for (k, v) in self.value}
        actions.append(action.ApplyGrowthChanges(target, growth_changes))
        playback.append(pb.StatHit(unit, item, target))

class WexpChange(ItemComponent):
    nid = 'wexp_change'
    desc = "Using this item permanently changes the WEXP of the target. Can specify individual amounts for different weapon types. Useful for Arms Scroll."
    tag = ItemTags.SPECIAL

    expose = (ComponentType.Dict, ComponentType.WeaponType)

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        wexp_changes = {k: v for (k, v) in self.value}
        for weapon_type, wexp_change in wexp_changes.items():
            actions.append(action.AddWexp(target, weapon_type, wexp_change))

class FatigueOnHit(ItemComponent):
    nid = 'fatigue_on_hit'
    desc = "If fatigue is enabled, increases the amount of fatigue a target suffers when hit by this item. Can be negative in order to remove fatigue."
    tag = ItemTags.SPECIAL

    expose = ComponentType.Int
    value = 1

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        actions.append(action.ChangeFatigue(target, self.value))

def ai_status_priority(unit, target, item, move, status_nid) -> float:
    if target and status_nid not in [skill.nid for skill in target.skills]:
        accuracy_term = utils.clamp(combat_calcs.compute_hit(unit, target, item, target.get_weapon(), "attack", (0, 0))/100., 0, 1)
        num_attacks = combat_calcs.outspeed(unit, target, item, target.get_weapon(), "attack", (0, 0))
        accuracy_term *= num_attacks
        # Tries to maximize distance from target
        distance_term = 0.01 * utils.calculate_distance(move, target.position)
        if skill_system.check_enemy(unit, target):
            return 0.5 * accuracy_term + distance_term
        else:
            return -0.5 * accuracy_term
    return 0

class StatusOnHit(ItemComponent):
    nid = 'status_on_hit'
    desc = "Target gains the specified status on hit. Applies instantly, potentially causing values to change mid-combat."
    tag = ItemTags.SPECIAL

    expose = ComponentType.Skill  # Nid

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        act = action.AddSkill(target, self.value, unit)
        actions.append(act)
        playback.append(pb.StatusHit(unit, item, target, self.value))

    def ai_priority(self, unit, item, target, move):
        # Do I add a new status to the target
        return ai_status_priority(unit, target, item, move, self.value)


class SelfStatusOnHit(ItemComponent):
    nid = 'self_status_on_hit'
    desc = "User gains the specified status on hit. Applies instantly, potentially causing values to change mid-combat."
    tag = ItemTags.SPECIAL

    expose = ComponentType.Skill  # Nid

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        act = action.AddSkill(unit, self.value, unit)
        actions.append(act)
        playback.append(pb.StatusHit(unit, item, unit, self.value))

    def ai_priority(self, unit, item, target, move):
        # Do I add a new status to the target
        return ai_status_priority(unit, unit, item, move, self.value)

class StatusesOnHit(ItemComponent):
    nid = 'statuses_on_hit'
    desc = "Item gives statuses to target when it hits"
    tag = ItemTags.SPECIAL
    author = 'BigMood'

    expose = (ComponentType.List, ComponentType.Skill)  # Nid

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        for status_nid in self.value:
            act = action.AddSkill(target, status_nid, unit)
            actions.append(act)
        playback.append(pb.StatusHit(unit, item, target, self.value))

    def ai_priority(self, unit, item, target, move):
        # Do I add a new status to the target
        total = 0
        for status_nid in self.value:
            total += ai_status_priority(unit, target, item, move, status_nid)
        return total

class StatusAfterCombatOnHit(StatusOnHit):
    nid = 'status_after_combat_on_hit'
    desc = "If the target is hit they gain the specified status at the end of combat. Prevents changes being applied mid-combat."
    tag = ItemTags.SPECIAL

    expose = ComponentType.Skill  # Nid

    _did_hit = set()

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        self._did_hit.add(target)

    def end_combat(self, playback, unit, item, target, item2, mode):
        for target in self._did_hit:
            act = action.AddSkill(target, self.value, unit)
            action.do(act)
        self._did_hit.clear()

    def ai_priority(self, unit, item, target, move):
        # Do I add a new status to the target
        return ai_status_priority(unit, target, item, move, self.value)

class Shove(ItemComponent):
    nid = 'shove'
    desc = "Item shoves target on hit"
    tag = ItemTags.SPECIAL

    expose = ComponentType.Int
    value = 1

    def _check_shove(self, unit_to_move, anchor_pos, magnitude):
        offset_x = utils.clamp(unit_to_move.position[0] - anchor_pos[0], -1, 1)
        offset_y = utils.clamp(unit_to_move.position[1] - anchor_pos[1], -1, 1)
        new_position = (unit_to_move.position[0] + offset_x * magnitude,
                        unit_to_move.position[1] + offset_y * magnitude)

        mcost = movement_funcs.get_mcost(unit_to_move, new_position)
        if game.board.check_bounds(new_position) and \
                not game.board.get_unit(new_position) and \
                mcost <= unit_to_move.get_movement():
            return new_position
        return False

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        if not skill_system.ignore_forced_movement(target):
            new_position = self._check_shove(target, unit.position, self.value)
            if new_position:
                actions.append(action.ForcedMovement(target, new_position))
                playback.append(pb.ShoveHit(unit, item, target))

class ShoveOnEndCombat(Shove):
    nid = 'shove_on_end_combat'
    desc = "Item shoves target at the end of combat"
    tag = ItemTags.SPECIAL

    expose = ComponentType.Int
    value = 1

    def end_combat(self, playback, unit, item, target, item2, mode):
        if not skill_system.ignore_forced_movement(target) and mode:
            new_position = self._check_shove(target, unit.position, self.value)
            if new_position:
                action.do(action.ForcedMovement(target, new_position))

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        pass

class ShoveTargetRestrict(Shove):
    nid = 'shove_target_restrict'
    desc = "Works the same as shove but will not allow the item to be selected if the action cannot be performed."
    tag = ItemTags.SPECIAL

    expose = ComponentType.Int
    value = 1

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        defender = game.board.get_unit(def_pos)
        if defender and self._check_shove(defender, unit.position, self.value) and \
                not skill_system.ignore_forced_movement(defender):
            return True
        for s_pos in splash:
            s = game.board.get_unit(s_pos)
            if self._check_shove(s, unit.position, self.value) and \
                    not skill_system.ignore_forced_movement(s):
                return True
        return False

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        pass

    def end_combat(self, playback, unit, item, target, item2, mode):
        pass

class Swap(ItemComponent):
    nid = 'swap'
    desc = "Item swaps user with target on hit"
    tag = ItemTags.SPECIAL

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        if not skill_system.ignore_forced_movement(unit) and not skill_system.ignore_forced_movement(target):
            actions.append(action.Swap(unit, target))
            playback.append(pb.SwapHit(unit, item, target))

class SwapOnEndCombat(ItemComponent):
    nid = 'swap_on_end_combat'
    desc = "Item swaps user with target after initiated combat"
    tag = ItemTags.SPECIAL

    def end_combat(self, playback, unit, item, target, item2, mode):
        if target and not skill_system.ignore_forced_movement(unit) and \
                not skill_system.ignore_forced_movement(target) and \
                mode == 'attack':
            action.do(action.Swap(unit, target))

class Pivot(ItemComponent):
    nid = 'pivot'
    desc = "User moves to other side of target on hit."
    tag = ItemTags.SPECIAL
    author = "Lord Tweed"

    expose = ComponentType.Int
    value = 1

    def _check_pivot(self, unit_to_move, anchor_pos, magnitude):
        offset_x = utils.clamp(unit_to_move.position[0] - anchor_pos[0], -1, 1)
        offset_y = utils.clamp(unit_to_move.position[1] - anchor_pos[1], -1, 1)
        new_position = (anchor_pos[0] + offset_x * -magnitude,
                        anchor_pos[1] + offset_y * -magnitude)

        mcost = movement_funcs.get_mcost(unit_to_move, new_position)
        if game.board.check_bounds(new_position) and \
                not game.board.get_unit(new_position) and \
                mcost <= unit_to_move.get_movement():
            return new_position
        return False

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        if not skill_system.ignore_forced_movement(unit):
            new_position = self._check_pivot(unit, target.position, self.value)
            if new_position:
                actions.append(action.ForcedMovement(unit, new_position))
                playback.append(pb.ShoveHit(unit, item, target))


class PivotTargetRestrict(Pivot):
    nid = 'pivot_target_restrict'
    desc = "Suppresses the Pivot command when it would be invalid."
    tag = ItemTags.SPECIAL
    author = "Lord Tweed"

    expose = ComponentType.Int
    value = 1

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        defender = game.board.get_unit(def_pos)
        if defender and self._check_pivot(unit, defender.position, self.value) and \
                not skill_system.ignore_forced_movement(unit):
            return True
        for s_pos in splash:
            s = game.board.get_unit(s_pos)
            if self._check_pivot(unit, s.position, self.value) and \
                    not skill_system.ignore_forced_movement(unit):
                return True
        return False

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        pass

    def end_combat(self, playback, unit, item, target, item2, mode):
        pass

class DrawBack(ItemComponent):
    nid = 'draw_back'
    desc = "Item moves both user and target back on hit."
    tag = ItemTags.SPECIAL
    author = "Lord Tweed"

    expose = ComponentType.Int
    value = 1

    def _check_draw_back(self, target, user, magnitude):
        offset_x = utils.clamp(target.position[0] - user.position[0], -1, 1)
        offset_y = utils.clamp(target.position[1] - user.position[1], -1, 1)
        new_position_user = (user.position[0] - offset_x * magnitude,
                             user.position[1] - offset_y * magnitude)
        new_position_target = (target.position[0] - offset_x * magnitude,
                               target.position[1] - offset_y * magnitude)

        mcost_user = movement_funcs.get_mcost(user, new_position_user)
        mcost_target = movement_funcs.get_mcost(target, new_position_target)

        if game.board.check_bounds(new_position_user) and \
                not game.board.get_unit(new_position_user) and \
                mcost_user <= user.get_movement() and mcost_target <= target.get_movement():
            return new_position_user, new_position_target
        return None, None

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        if not skill_system.ignore_forced_movement(target):
            new_position_user, new_position_target = self._check_draw_back(target, unit, self.value)
            if new_position_user and new_position_target:
                actions.append(action.ForcedMovement(unit, new_position_user))
                playback.append(pb.ShoveHit(unit, item, unit))
                actions.append(action.ForcedMovement(target, new_position_target))
                playback.append(pb.ShoveHit(unit, item, target))


class DrawBackTargetRestrict(DrawBack):
    nid = 'draw_back_target_restrict'
    desc = "Suppresses the Draw Back command when it would be invalid."
    tag = ItemTags.SPECIAL
    author = "Lord Tweed"

    expose = ComponentType.Int
    value = 1

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        defender = game.board.get_unit(def_pos)
        if defender:
            positions = [result for result in self._check_draw_back(defender, unit, self.value)]
            if all(positions) and not skill_system.ignore_forced_movement(defender):
                return True
        for s_pos in splash:
            s = game.board.get_unit(s_pos)
            if not s:
                continue
            splash_positions = [result for result in self._check_draw_back(s, unit, self.value)]
            if all(splash_positions) and not skill_system.ignore_forced_movement(s):
                return True
        return False

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        pass

    def end_combat(self, playback, unit, item, target, item2, mode):
        pass

class Steal(ItemComponent):
    nid = 'steal'
    desc = "Steal any unequipped item from target on hit"
    tag = ItemTags.SPECIAL

    _did_steal = False

    def init(self, item):
        item.data['target_item'] = None

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # Unit has item that can be stolen
        attack = equations.parser.steal_atk(unit)
        defender = game.board.get_unit(def_pos)
        defense = equations.parser.steal_def(defender)
        if attack >= defense:
            for def_item in defender.items:
                if self.item_restrict(unit, item, defender, def_item):
                    return True
        return False

    def valid_targets(self, unit, item):
        positions = set()
        for other in game.units:
            if other.position and skill_system.check_enemy(unit, other):
                for def_item in other.items:
                    if self.item_restrict(unit, item, other, def_item):
                        positions.add(other.position)
                        break
        return positions

    def targets_items(self, unit, item) -> bool:
        return True

    def item_restrict(self, unit, item, defender, def_item) -> bool:
        if item_system.unstealable(defender, def_item):
            return False
        if item_funcs.inventory_full(unit, def_item):
            return False
        if def_item is defender.get_weapon():
            return False
        return True

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        target_item = item.data.get('target_item')
        if target_item:
            actions.append(action.RemoveItem(target, target_item))
            actions.append(action.DropItem(unit, target_item))
            if unit.team != 'player':
                actions.append(action.MakeItemDroppable(unit, target_item))
            actions.append(action.UpdateRecords('steal', (unit.nid, target.nid, target_item.nid)))
            self._did_steal = True

    def end_combat(self, playback, unit, item, target, item2, mode):
        if self._did_steal:
            target_item = item.data.get('target_item')
            game.alerts.append(banner.StoleItem(unit, target_item))
            game.state.change('alert')
        item.data['target_item'] = None
        self._did_steal = False

    def ai_priority(self, unit, item, target, move):
        if target:
            steal_term = 0.075
            enemy_positions = utils.average_pos({other.position for other in game.units if other.position and skill_system.check_enemy(unit, other)})
            distance_term = utils.calculate_distance(move, enemy_positions)
            return steal_term + 0.01 * distance_term
        return 0

class GBASteal(Steal):
    nid = 'gba_steal'
    desc = "Steal any non-weapon, non-spell from target on hit"
    tag = ItemTags.SPECIAL

    def item_restrict(self, unit, item, defender, def_item) -> bool:
        if item_system.unstealable(defender, def_item):
            return False
        if item_funcs.inventory_full(unit, def_item):
            return False
        if item_system.is_weapon(defender, def_item) or item_system.is_spell(defender, def_item):
            return False
        return True

class EventBeforeHit(ItemComponent):
    nid = 'event_on_hit'
    desc = "The selected event plays before a hit, if the unit will hit with this item. The event is triggered with args (unit1=attacking unit, unit2=target, item=item, position=attacking unit's position, target_pos=position of target, mode='attack' or 'defense', attack_info=a tuple containing which attack this is as the first element, and which subattack this is as the second element)"
    tag = ItemTags.SPECIAL

    expose = ComponentType.Event

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        event_prefab = DB.events.get_from_nid(self.value)
        if event_prefab:
            local_args = {'target_pos': target_pos, 'mode': mode, 'attack_info': attack_info, 'item': item}
            game.events.trigger_specific_event(event_prefab.nid, unit, target, unit.position, local_args)

class EventAfterCombatOnHit(ItemComponent):
    nid = 'event_after_combat_on_hit'
    desc = "The selected event plays at the end of combat so long as an attack in combat hit."
    tag = ItemTags.SPECIAL

    expose = ComponentType.Event

    _did_hit = False

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        self._did_hit = True
        self.target_pos = target_pos

    def end_combat(self, playback, unit, item, target, item2, mode):
        if self._did_hit and target:
            event_prefab = DB.events.get_from_nid(self.value)
            if event_prefab:
                local_args = {'target_pos': self.target_pos, 'item': item, 'item2': item2, 'mode': mode}
                game.events.trigger_specific_event(event_prefab.nid, unit, target, unit.position, local_args)
        self._did_hit = False

class EventAfterCombatEvenMiss(ItemComponent):
    nid = 'event_after_combat_even_miss'
    desc = "The selected event plays at the end of combat."
    tag = ItemTags.SPECIAL

    expose = ComponentType.Event

    def end_combat(self, playback, unit, item, target, item2, mode):
        event_prefab = DB.events.get_from_nid(self.value)
        if event_prefab:
            local_args = {'item': item, 'item2': item2, 'mode': mode}
            game.events.trigger_specific_event(event_prefab.nid, unit, target, unit.position, local_args)
