from typing import Set, Tuple
from app.data.database.skill_components import SkillComponent, SkillTags
from app.data.database.components import ComponentType

from app.engine import equations, action
from app.engine.game_state import game
from app.engine.movement import movement_funcs
from app.engine.objects.unit import UnitObject

import logging

class Canto(SkillComponent):
    nid = 'canto'
    desc = "Unit can move again after certain actions"
    tag = SkillTags.MOVEMENT

    def canto_movement(self, unit, unit2) -> int:
        return unit.movement_left

    def has_canto(self, unit, unit2) -> bool:
        """
        Can move again if hasn't attacked or attacked self
        """
        return not unit.has_attacked or unit is unit2

class CantoPlus(SkillComponent):
    nid = 'canto_plus'
    desc = "Unit can move again even after attacking"
    tag = SkillTags.MOVEMENT

    def canto_movement(self, unit, unit2) -> int:
        return unit.movement_left

    def has_canto(self, unit, unit2) -> bool:
        return True

class CantoSharp(SkillComponent):
    nid = 'canto_sharp'
    desc = "Unit can move and attack in either order"
    tag = SkillTags.MOVEMENT

    def canto_movement(self, unit, unit2) -> int:
        return unit.movement_left

    def has_canto(self, unit, unit2) -> bool:
        return not unit.has_attacked or unit.movement_left >= equations.parser.movement(unit)

class Canter(SkillComponent):
    nid = 'canter'
    desc = "Unit can move a specified number of spaces after any action"
    tag = SkillTags.MOVEMENT

    expose = ComponentType.Int
    value = 2

    def canto_movement(self, unit, unit2) -> int:
        return self.value

    def has_canto(self, unit, unit2) -> bool:
        """
        Can move again after any action, has exactly the number of movement that was determined in the component
        """
        return True

class MovementType(SkillComponent):
    nid = 'movement_type'
    desc = "Unit will have a non-default movement type"
    tag = SkillTags.MOVEMENT

    expose = ComponentType.MovementType

    def movement_type(self, unit):
        return self.value

class Pass(SkillComponent):
    nid = 'pass'
    desc = "Unit can move through enemies"
    tag = SkillTags.MOVEMENT

    def pass_through(self, unit):
        return True

class IgnoreTerrain(SkillComponent):
    nid = 'ignore_terrain'
    desc = "Unit will not be affected by terrain"
    tag = SkillTags.MOVEMENT

    def ignore_terrain(self, unit):
        return True

    def ignore_region_status(self, unit):
        return True

class IgnoreRescuePenalty(SkillComponent):
    nid = 'ignore_rescue_penalty'
    desc = "Unit will ignore the rescue penalty"
    tag = SkillTags.MOVEMENT

    def ignore_rescue_penalty(self, unit):
        return True

class Grounded(SkillComponent):
    nid = 'grounded'
    desc = "Unit cannot be forcibly moved"
    tag = SkillTags.MOVEMENT

    def ignore_forced_movement(self, unit):
        return True

class NoAttackAfterMove(SkillComponent):
    nid = 'no_attack_after_move'
    desc = 'Unit can either move or attack, but not both'
    tag = SkillTags.MOVEMENT

    def no_attack_after_move(self, unit):
        return True

class WitchWarp(SkillComponent):
    nid = 'witch_warp'
    desc = 'Unit can warp to any ally'
    tag = SkillTags.MOVEMENT

    def witch_warp(self, unit: UnitObject) -> Set[Tuple[int, int]]:
        warp_spots = set()
        for ally in game.get_all_units():
            if ally.team == unit.team and ally.position and game.board.check_bounds(ally.position):
                pos = ally.position
                up = (pos[0], pos[1] - 1)
                down = (pos[0], pos[1] + 1)
                left = (pos[0] - 1, pos[1])
                right = (pos[0] + 1, pos[1])
                for point in [up, down, left, right]:
                    if game.board.check_bounds(point) and movement_funcs.check_weakly_traversable(unit, point) and not game.board.get_unit(point):
                        warp_spots.add(point)
        return warp_spots

class SpecificWitchWarp(SkillComponent):
    nid = 'specific_witch_warp'
    desc = "Allows unit to witch warp to the given units"
    tag = SkillTags.MOVEMENT

    expose = (ComponentType.List, ComponentType.Unit)

    def witch_warp(self, unit: UnitObject) -> list:
        positions = []
        for val in self.value:
            u = game.get_unit(val)
            if u and u.position:
                partner_pos = u.position
            else:
                continue
            if partner_pos:
                positions += [
                    pos for pos in game.target_system.get_adjacent_positions(partner_pos)
                    if movement_funcs.check_weakly_traversable(unit, pos) and
                    not game.board.get_unit(pos)
                ]
        return positions

class WitchWarpExpression(SkillComponent):
    nid = 'witch_warp_expression'
    desc = "Allows unit to witch warp to the units that satisfy the expression"
    tag = SkillTags.MOVEMENT

    expose = ComponentType.String
    value = 'True'

    def witch_warp(self, unit) -> list:
        from app.engine import evaluate
        positions = []
        for target in game.units:
            if target.position:
                try:
                    if evaluate.evaluate(self.value, target, unit, target.position):
                        positions += [
                            pos for pos in game.target_system.get_adjacent_positions(target.position)
                            if movement_funcs.check_weakly_traversable(unit, pos) and
                            not game.board.get_unit(pos)
                        ]
                except Exception as e:
                    logging.error("Could not evaluate %s (%s)", self.value, e)
                    return positions
        return positions

class Galeforce(SkillComponent):
    nid = 'galeforce'
    desc = "After killing an enemy on player phase, unit can move again."
    tag = SkillTags.MOVEMENT

    def end_combat(self, playback, unit, item, target, item2, mode):
        mark_playbacks = [p for p in playback if p.nid in ('mark_miss', 'mark_hit', 'mark_crit')]
        if target and target.get_hp() <= 0 and \
                any(p.main_attacker is unit for p in mark_playbacks):  # Unit is overall attacker
            action.do(action.Reset(unit))
            action.do(action.TriggerCharge(unit, self.skill))

class ModernGaleforce(SkillComponent):
    nid = 'modern_galeforce'
    desc = "After killing an enemy on player phase, unit can move again. Allows `on_wait` event triggers and post-combat reposition skills that wrap `Canto` & variants to run before the unit is refreshed."
    tag = SkillTags.MOVEMENT
    
    author = 'Eretein'
    
    _should_refresh: bool = False

    def end_combat(self, playback, unit, item, target, item2, mode):
        mark_playbacks = [p for p in playback if p.nid in ('mark_miss', 'mark_hit', 'mark_crit')]
        if target and target.get_hp() <= 0 and \
                any(p.main_attacker is unit for p in mark_playbacks):  # Unit is overall attacker
            self._should_refresh = True
    
    def on_wait(self, unit, actively_chosen):
        if self._should_refresh:
            action.do(action.Reset(unit))
            action.do(action.TriggerCharge(unit, self.skill))
            self._should_refresh = False
        