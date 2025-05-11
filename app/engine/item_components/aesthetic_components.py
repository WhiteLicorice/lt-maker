from app.engine.fonts import NORMAL_FONT_COLORS
from app.data.database.item_components import ItemComponent, ItemTags
from app.data.database.components import ComponentType

from app.engine.combat import playback as pb
from app.engine import engine, image_mods, item_funcs, skill_system

import logging

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
            playback.append(pb.TargetCastAnim(self.value, target.position))

    def on_miss(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        if target:
            playback.append(pb.TargetCastAnim(self.value, target.position))

class MapCastPose(ItemComponent):
    nid = 'map_cast_pose'
    desc = "Forces map animation to use the active pose for combat. (Think GBA map staff animations, item use animations)"
    tag = ItemTags.AESTHETIC

    def map_cast_pose(self, unit, item):
        return True

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
