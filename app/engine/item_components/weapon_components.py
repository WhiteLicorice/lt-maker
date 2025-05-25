from app.utilities import utils
from app.data.database.database import DB
from app.data.database.difficulty_modes import RNGOption

from app.data.database.item_components import ItemComponent, ItemTags
from app.data.database.components import ComponentType

from app.engine import action, combat_calcs, equations, item_system, skill_system, unit_funcs
from app.engine.game_state import game
from app.engine.combat import playback as pb

class WeaponType(ItemComponent):
    nid = 'weapon_type'
    desc = "The type of weapon that the wielder must be able to use in order to attack with this item."
    tag = ItemTags.WEAPON

    expose = ComponentType.WeaponType

    def weapon_type(self, unit, item):
        return self.value

    def available(self, unit, item) -> bool:
        klass = DB.classes.get(unit.klass)
        wexp_gain = klass.wexp_gain.get(self.value)
        if wexp_gain:
            klass_usable = self.value in unit_funcs.usable_wtypes(unit)
            return unit.wexp[self.value] > 0 and klass_usable
        return False

class WeaponRank(ItemComponent):
    nid = 'weapon_rank'
    desc = "Item has a weapon rank and can only be used by units with high enough rank"
    requires = ['weapon_type']
    tag = ItemTags.WEAPON

    expose = ComponentType.WeaponRank

    def weapon_rank(self, unit, item):
        return self.value

    def available(self, unit, item):
        required_wexp = DB.weapon_ranks.get(self.value).requirement
        weapon_type = item_system.weapon_type(unit, item)
        if weapon_type:
            return unit.wexp.get(weapon_type) >= required_wexp
        else:  # If no weapon type, then always available
            return True

class Magic(ItemComponent):
    nid = 'magic'
    desc = 'Makes Item use magic damage formula'
    tag = ItemTags.WEAPON

    def damage_formula(self, unit, item):
        return 'MAGIC_DAMAGE'

    def resist_formula(self, unit, item):
        return 'MAGIC_DEFENSE'

class MagicAtRange(ItemComponent):
    nid = 'magic_at_range'
    desc = 'Makes Item use magic damage formula at range'
    tag = ItemTags.WEAPON

    def dynamic_damage(self, unit, item, target, item2, mode, attack_info, base_value) -> int:
        running_damage = 0
        if unit.position and target and target.position:
            dist = utils.calculate_distance(unit.position, target.position)
            if dist > 1:
                normal_damage = equations.parser.get('DAMAGE', unit)
                new_damage = equations.parser.get('MAGIC_DAMAGE', unit)
                normal_resist = equations.parser.get('DEFENSE', target)
                new_resist = equations.parser.get('MAGIC_DEFENSE', target)
                running_damage -= normal_damage
                running_damage += new_damage
                running_damage += normal_resist
                running_damage -= new_resist
        return running_damage

class Hit(ItemComponent):
    nid = 'hit'
    desc = "Item has a chance to hit. If left off, item will always hit."
    tag = ItemTags.WEAPON

    expose = ComponentType.Int
    value = 75

    def hit(self, unit, item):
        return self.value

class Damage(ItemComponent):
    nid = 'damage'
    desc = "Item does damage on hit"
    tag = ItemTags.WEAPON

    expose = ComponentType.Int
    value = 0

    def damage(self, unit, item):
        return self.value

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # Restricts target based on whether any unit is an enemy
        defender = game.board.get_unit(def_pos)
        if defender and skill_system.check_enemy(unit, defender):
            return True
        for s_pos in splash:
            s = game.board.get_unit(s_pos)
            if s and skill_system.check_enemy(unit, s):
                return True
        return False

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        playback_nids = [brush.nid for brush in playback]
        if 'attacker_partner_phase' in playback_nids or 'defender_partner_phase' in playback_nids:
            damage = combat_calcs.compute_assist_damage(unit, target, item, target.get_weapon(), mode, attack_info)
        else:
            damage = combat_calcs.compute_damage(unit, target, item, target.get_weapon(), mode, attack_info)

        # Reduce damage if in Grandmaster Mode
        if game.rng_mode == RNGOption.GRANDMASTER:
            hit = utils.clamp(combat_calcs.compute_hit(unit, target, item, target.get_weapon(), mode, attack_info), 0, 100)
            damage = int(damage * float(hit) / 100)

        true_damage = min(damage, target.get_hp())
        actions.append(action.ChangeHP(target, -damage))

        # For animation
        playback.append(pb.DamageHit(unit, item, target, damage, true_damage))
        if damage == 0:
            playback.append(pb.HitSound('No Damage'))
            playback.append(pb.HitAnim('MapNoDamage', target))

    def on_glancing_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        playback_nids = [brush.nid for brush in playback]
        if 'attacker_partner_phase' in playback_nids or 'defender_partner_phase' in playback_nids:
            damage = combat_calcs.compute_assist_damage(unit, target, item, target.get_weapon(), mode, attack_info)
        else:
            damage = combat_calcs.compute_damage(unit, target, item, target.get_weapon(), mode, attack_info)

        # Reduce damage if in Grandmaster Mode
        if game.rng_mode == RNGOption.GRANDMASTER:
            hit = utils.clamp(combat_calcs.compute_hit(unit, target, item, target.get_weapon(), mode, attack_info), 0, 100)
            damage = int(damage * float(hit) / 100)

        damage //= 2  # Because glancing hit

        true_damage = min(damage, target.get_hp())
        actions.append(action.ChangeHP(target, -damage))

        # For animation
        playback.append(pb.DamageHit(unit, item, target, damage, true_damage))
        if damage == 0:
            playback.append(pb.HitAnim('MapNoDamage', target))
        else:
            playback.append(pb.HitAnim('MapGlancingHit', target))

    def on_crit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        playback_nids = [brush.nid for brush in playback]
        if 'attacker_partner_phase' in playback_nids or 'defender_partner_phase' in playback_nids:
            damage = combat_calcs.compute_assist_damage(unit, target, item, target.get_weapon(), mode, attack_info, crit=True)
        else:
            damage = combat_calcs.compute_damage(unit, target, item, target.get_weapon(), mode, attack_info, crit=True)

        # Reduce damage if in Grandmaster Mode (although crit doesn't make much sense with Grandmaster mode)
        if game.rng_mode == RNGOption.GRANDMASTER:
            hit = utils.clamp(combat_calcs.compute_hit(unit, target, item, target.get_weapon(), mode, attack_info), 0, 100)
            damage = int(damage * float(hit) / 100)

        true_damage = min(damage, target.get_hp())
        actions.append(action.ChangeHP(target, -damage))

        playback.append(pb.DamageCrit(unit, item, target, damage, true_damage))
        if damage == 0:
            playback.append(pb.HitSound('No Damage'))
            playback.append(pb.HitAnim('MapNoDamage', target))

class Crit(ItemComponent):
    nid = 'crit'
    desc = "Item has a chance to crit. If left off, item cannot crit."
    tag = ItemTags.WEAPON

    expose = ComponentType.Int
    value = 0

    def crit(self, unit, item):
        return self.value

class Weight(ItemComponent):
    nid = 'weight'
    desc = "Lowers attack speed. At first, subtracted from the CONSTITUTION equation. If negative, subtracts from overall attack speed."
    tag = ItemTags.WEAPON

    expose = ComponentType.Int
    value = 0

    def modify_attack_speed(self, unit, item):
        return -1 * max(0, self.value - equations.parser.constitution(unit))

    def modify_defense_speed(self, unit, item):
        return -1 * max(0, self.value - equations.parser.constitution(unit))

    def modify_avoid(self, unit, item):
        return -2 * max(0, self.value - equations.parser.constitution(unit))

class Unwieldy(ItemComponent):
    nid = 'Unwieldy'
    desc = "Item lowers unit's defense by X"
    tag = ItemTags.WEAPON

    expose = ComponentType.Int
    value = 0

    def modify_resist(self, unit, item):
        return -1 * self.value

class StatChange(ItemComponent):
    nid = 'stat_change'
    desc = "A list of stats that correspond to integers. When equipped, stats are changed by that amount."
    tag = ItemTags.WEAPON

    expose = (ComponentType.Dict, ComponentType.Stat)
    value = []

    def stat_change(self, unit):
        return {stat[0]: stat[1] for stat in self.value}

class CannotDS(ItemComponent):
    nid = 'exempt_from_dual_strike'
    desc = 'Disallows the item\'s wielder from having or being a dual strike partner while equipped'
    tag = ItemTags.WEAPON

    author = 'KD'

    def cannot_be_dual_strike_partner(self, unit, item):
        return True

    def cannot_have_dual_strike_partner(self, unit, item):
        return True

class NoEquip(ItemComponent):
    nid = 'no_equip'
    desc = 'Prevents the item from being equipped even when being used as a weapon, similar to Spell behavior.'
    tag = ItemTags.WEAPON

    def equippable(self, unit, item):
        return False