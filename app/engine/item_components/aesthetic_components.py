from app.engine.fonts import NORMAL_FONT_COLORS
from app.data.database.item_components import ItemComponent, ItemTags
from app.data.database.components import ComponentType

from app.engine.combat import playback as pb
from app.engine import engine, image_mods, item_funcs, skill_system

from app.utilities import utils
from app.constants import TILEWIDTH, TILEHEIGHT

import math

import logging

def get_target_position(target, target_pos, mode):
    #Return the position of the tile we are targeting.  Splash needs a special case, because for splash attacks target_pos will always give the main target's position.
    if mode == 'splash' and target:
        return target.position
    else:
        return target_pos       

class NeverUseBattleAnimation(ItemComponent):
    nid = 'never_use_battle_animation'
    desc = "Item will never use a battle animation even if otherwise available"
    tag = ItemTags.AESTHETIC

    def force_map_anim(self, unit, item):
        return True

class MapHitAddBlend(ItemComponent):
    nid = 'map_hit_add_blend'
    desc = "Changes the color that appears on the unit when hit -- Use to make brighter"
    tag = ItemTags.AESTHETIC

    expose = ComponentType.Color3
    value = (255, 255, 255)

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        playback.append(pb.UnitTintAdd(target, self.value))

class MapHitSubBlend(ItemComponent):
    nid = 'map_hit_sub_blend'
    desc = "Changes the color that appears on the unit when hit -- Use to make darker"
    tag = ItemTags.AESTHETIC

    expose = ComponentType.Color3
    value = (0, 0, 0)

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        playback.append(pb.UnitTintSub(target, self.value))

class MapHitSFX(ItemComponent):
    nid = 'map_hit_sfx'
    desc = "When the target is hit by this item the selected sound is played."
    tag = ItemTags.AESTHETIC

    expose = ComponentType.Sound
    value = 'Attack Hit 1'

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        playback.append(pb.HitSound(self.value))

class MapCastSFX(ItemComponent):
    nid = 'map_cast_sfx'
    desc = "When item is used the selected sound is played."
    tag = ItemTags.AESTHETIC

    expose = ComponentType.Sound
    value = 'Attack Hit 1'

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        playback.append(pb.CastSound(self.value))

    def on_miss(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        playback.append(pb.CastSound(self.value))

class MapCastAnim(ItemComponent):
    nid = 'map_cast_anim'
    desc = "Adds a specific animation effect on the target's tile when the item is used. Relevant in map combat situations."
    tag = ItemTags.AESTHETIC

    expose = ComponentType.MapAnimation

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        playback.append(pb.CastAnim(self.value))

    def on_miss(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        playback.append(pb.CastAnim(self.value))

class MapTargetCastAnim(ItemComponent):
    nid = 'map_target_cast_anim'
    desc = "Adds a specific animation effect on all units in AoE when the item is used. Relevant in map combat situations."
    tag = ItemTags.AESTHETIC

    expose = ComponentType.MapAnimation

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        if target:
            playback.append(pb.TargetCastAnim(self.value, get_target_position(target, target_pos, mode)))

    def on_miss(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        if target:
            playback.append(pb.TargetCastAnim(self.value, get_target_position(target, target_pos, mode)))
            
class ProjectileSpellAnim(ItemComponent):
    nid = 'projectile_spell_anim'
    desc = """Adds an animation which moves from the user to the target when the item is used. Relevant in map combat situations.
    anim: The animation to be used.
    speed: How quickly the animation will move (Must be a positive integer).
    loop: Whether the animation should loop while moving.
    rotate: Whether the animation should rotate to face the target.  If used, make sure your animation png is initially facing right and centered on the rotation point.
    """
    tag = ItemTags.AESTHETIC

    expose = ComponentType.NewMultipleOptions
    options = {
        'anim': ComponentType.String,
        'speed': ComponentType.Int,
        'loop': ComponentType.Bool,
        'rotate': ComponentType.Bool
    }

    def __init__(self, value=None):
        self.value = {
            'anim': None,
            'speed': 1,
            'loop': False,
            'rotate': False
        }
        if value:
            self.value.update(value)
            
    def _create_projectile(self, unit_pos, target_pos):
        u_pos = ((unit_pos[0] * TILEWIDTH + TILEWIDTH // 2), (unit_pos[1] * TILEHEIGHT + TILEHEIGHT // 2)) #Centered unit position in pixels
        t_pos = (target_pos[0] * TILEWIDTH + TILEWIDTH // 2, target_pos[1] * TILEHEIGHT + TILEHEIGHT // 2) #Centered target pos
        delta = utils.tuple_sub(t_pos, u_pos)
        distance = utils.magnitude(delta)
        direction = utils.normalize(delta)
        speed = max(self.value['speed'], 1) #Speed should be a positive integer.
        theta = math.atan2(-direction[1], direction[0]) if self.value['rotate'] else 0
        vel = utils.tmult(direction, speed)
        anim = self._generate_anim(self.value['anim'], unit_pos, vel, distance / speed, self.value['loop'], theta)
        return anim
        
    def _generate_anim(self, val, pos, vel, dur, loop, rot):
        return pb.SpellCastAnim(val, pos, vel, dur, loop, rot)
        
    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        if unit.position != get_target_position(target, target_pos, mode):
            playback.append(self._create_projectile(unit.position, get_target_position(target, target_pos, mode)))

    def on_miss(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        if unit.position != get_target_position(target, target_pos, mode):
            playback.append(self._create_projectile(unit.position, get_target_position(target, target_pos, mode)))
        
class SequentialProjectileAnim(ProjectileSpellAnim):
    nid = 'sequential_projectile_anim'
    desc = """Adds an animation which moves between targets in order when the item is used. Relevant in map combat situations.
    Intended for scenarios in which there is a clearly designated order to targets, such as multi-target items.
    anim: The animation to be used.
    speed: How quickly the animation will move (Must be a positive integer).
    loop: Whether the animation should loop while moving.
    rotate: Whether the animation should rotate to face the target.  If used, make sure your animation png is initially facing right and centered on the rotation point.
    """
    tag = ItemTags.AESTHETIC
    
    def __init__(self, value = None):
        self.prev_targ_pos = None
        self.current_attack = (0,0) #This records which attack/sub-attack we're currently on.  Later, if it differs from what is indicated in attack info, we'll reset prev_targ
        super().__init__(value)
        
    def _generate_anim(self, val, pos, vel, dur, loop, rot):
        return pb.SequentialAnim(val, pos, vel, dur, loop, rot)
        
    def _handle_sequence_anim(self, unit, item, target_pos, playback, attack_info):
        if self.prev_targ_pos is None or self.current_attack != attack_info: #First target, animation goes from attacker to target
            self.current_attack = attack_info
            if target_pos != unit.position: #In case unit is also the first target, don't spawn a projectile that has nowhere to go
                playback.append(self._create_projectile(unit.position, target_pos))
        else:
            if target_pos != self.prev_targ_pos: #In case we select same target multiple times consecutively, don't spawn a projectile that has nowhere to go 
                playback.append(self._create_projectile(self.prev_targ_pos, target_pos))
        self.prev_targ_pos = target_pos
                
    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        self._handle_sequence_anim(unit, item, get_target_position(target, target_pos, mode), playback, attack_info)

    def on_miss(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        self._handle_sequence_anim(unit, item, get_target_position(target, target_pos, mode), playback, attack_info)
        
    def end_combat(self, playback, unit, item, target, item2, mode):
        self.prev_targ_pos = None
        self.current_attack = (0, 0)
            
class WaitOnMapAnim(ItemComponent):
    nid = 'wait_on_map_anim'
    desc = "Wait for all map cast animations to complete before proceeding with map combat."
    tag = ItemTags.AESTHETIC

    def wait_on_map_anim(self, unit, item):
        return True

class MapCastPose(ItemComponent):
    nid = 'map_cast_pose'
    desc = "Forces map animation to use the active pose for combat. (Think GBA map staff animations, item use animations)"
    tag = ItemTags.AESTHETIC

    def map_cast_pose(self, unit, item):
        return True

class BattleHitTint(ItemComponent):
    nid = 'battle_hit_tint'
    desc = "When this item hits in a combat animation, the target's battle animation stays tinted this color until the combat ends. Useful for effects like petrify, where a spell's own Tint Enemy command would wear off before the combat does."
    tag = ItemTags.AESTHETIC

    expose = ComponentType.Color3
    value = (0, 0, 0)

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        playback.append(pb.BattleAnimTint(target, self.value))

class BattleCastAnim(ItemComponent):
    nid = 'battle_cast_anim'
    desc = "Adds a specific animation effect when the item is used. This does not change the battle animation used, think instead of the spell's effect."
    tag = ItemTags.AESTHETIC

    expose = ComponentType.EffectAnimation

    def effect_animation(self, unit, item):
        return self.value

class BattleAnimationMusic(ItemComponent):
    nid = 'battle_animation_music'
    desc = "Uses custom battle music"
    tag = ItemTags.AESTHETIC

    expose = ComponentType.Music
    value = None

    def battle_music(self, unit, item, target, item2, mode):
        return self.value

class NoMapHPDisplay(ItemComponent):
    nid = 'no_map_hp_display'
    desc = "Item does not show full map hp display when used"
    tag = ItemTags.BASE

    def no_map_hp_display(self, unit, item):
        return True

class NoMapHitFlash(ItemComponent):
    nid = 'no_map_hit_flash'
    desc = "Targets do not flash white (or the color chosen by a Map Hit Add/Sub Blend component) when hit in map combat. Also suppresses the critical hit flash."
    tag = ItemTags.AESTHETIC

    def no_map_hit_flash(self, unit, item):
        return True

class NoMapHitSFX(ItemComponent):
    nid = 'no_map_hit_sfx'
    desc = "No sound effect is played when a target is hit or missed in map combat. Sounds from a Map Cast SFX component still play."
    tag = ItemTags.AESTHETIC

    def no_map_hit_sfx(self, unit, item):
        return True

class NoMapCombatMovement(ItemComponent):
    nid = 'no_map_combat_movement'
    desc = "Combatants do not turn to face one another or jostle towards one another during map combat. Also suppresses the critical hit vibration."
    tag = ItemTags.AESTHETIC

    def no_map_combat_movement(self, unit, item):
        return True

class NoMapDamageNumbers(ItemComponent):
    nid = 'no_map_damage_numbers'
    desc = "No floating damage, healing, or critical damage numbers appear over targets in map combat."
    tag = ItemTags.AESTHETIC

    def no_map_damage_numbers(self, unit, item):
        return True

class NoMapCombatFX(ItemComponent):
    nid = 'no_map_combat_fx'
    desc = ("Suppresses every default map combat flourish at once -- the hp display, the hit flash, "
            "the hit sound effect, the combatants' facing and jostle, and the floating damage numbers. "
            "Equivalent to adding No Map HP Display, No Map Hit Flash, No Map Hit SFX, "
            "No Map Combat Movement, and No Map Damage Numbers together.")
    tag = ItemTags.AESTHETIC

    def no_map_hp_display(self, unit, item):
        return True

    def no_map_hit_flash(self, unit, item):
        return True

    def no_map_hit_sfx(self, unit, item):
        return True

    def no_map_combat_movement(self, unit, item):
        return True

    def no_map_damage_numbers(self, unit, item):
        return True

class PreCombatEffect(ItemComponent):
    nid = 'pre_combat_effect'
    desc = "Item plays a combat effect right before combat."
    tag = ItemTags.AESTHETIC

    expose = ComponentType.EffectAnimation

    def combat_effect(self, unit, item, target, item2, mode):
        return self.value

class OnHitEffect(ItemComponent):
    nid = 'on_hit_effect'
    desc = "Item plays an on-hit effect."
    tag = ItemTags.AESTHETIC
    
    author = 'Eretein'

    expose = ComponentType.EffectAnimation

    def on_hit_effect(self, unit, item, target, item2, mode):
        return self.value

class Warning(ItemComponent):
    nid = 'warning'
    desc = "A yellow exclamation mark appears above the wielder's head. Often used for killing weapons."
    tag = ItemTags.AESTHETIC

    def target_icon(self, unit, item, target) -> str:
        return 'warning' if item_funcs.available(unit, item) and skill_system.check_enemy(target, unit) else None

class EvalWarning(ItemComponent):
    nid = 'eval_warning'
    desc = "A red exclamation mark appears above the wielder’s head if the selected unit matches the evaluated string. Often used for effective weapons."
    tag = ItemTags.AESTHETIC

    expose = ComponentType.String
    value = 'True'

    def target_icon(self, unit, item, target) -> bool:
        from app.engine import evaluate
        if not skill_system.check_enemy(target, unit):
            return None
        try:
            val = evaluate.evaluate(self.value, unit, target, unit.position, {'item': item})
            if bool(val):
                return 'danger'
        except Exception as e:
            logging.error("Could not evaluate %s (%s)" % (self.value, e))
        return None

class ItemIconFlash(ItemComponent):
    nid = 'item_icon_flash'
    desc = "During combat preview, item will flash if target's item meets condition"
    tag = ItemTags.AESTHETIC

    expose = ComponentType.String
    value = 'True'

    def item_icon_mod(self, unit, item, target, item2, sprite):
        from app.engine import evaluate
        try:
            val = evaluate.evaluate(self.value, unit, target, unit.position, {'item': item, 'item2': item})
        except Exception as e:
            print("Could not evaluate %s (%s)" % (self.value, e))
            return sprite
        if val:
            sprite = image_mods.make_white(sprite.convert_alpha(), abs(250 - engine.get_time() % 500)/250)
        return sprite
        
class HoverDescription(ItemComponent):
    nid = 'hover_description'
    desc = "Replaces the item's help text when the item is hovered over in the items menu."
    tag = ItemTags.AESTHETIC

    expose = ComponentType.String
    value = ''

    def hover_description(self, unit, item):
        return self.value

class TargetingPennant(ItemComponent):
    nid = 'targeting_pennant'
    desc = "Scrolls this text along the bottom of the screen while the player chooses a target for the item. Ex: Select a character to restore HP to. On a sequence item, it is shown for each subitem that has none of its own."
    tag = ItemTags.AESTHETIC

    expose = ComponentType.String
    value = ''

    def targeting_pennant(self, unit, item):
        return self.value

class ShowAdvantageArrow(ItemComponent):
    nid = 'show_advantage_arrow'
    desc = 'Shows the advantage arrow in combat.'
    tag = ItemTags.AESTHETIC
    
    author = 'Eretein'
    
    def show_weapon_advantage(self, unit, item, target, item2):
        return True
    
class ShowDisadvantageArrow(ItemComponent):
    nid = 'show_disadvantage_arrow'
    desc = 'Shows the disadvantage arrow in combat.'
    tag = ItemTags.AESTHETIC
    
    author = 'Eretein'
    
    def show_weapon_disadvantage(self, unit, item, target, item2):
        return True

class SpecialArticle(ItemComponent):
    nid = 'special_article'
    desc = 'Causes the article in the banner to be this string'
    tag = ItemTags.AESTHETIC

    expose = ComponentType.String
    value = ''