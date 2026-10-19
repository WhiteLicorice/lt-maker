from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from app.counters import GenericAnimCounter
from app.data.database.units import UnitPrefab
from app.data.resources import map_sprites
from app.engine.game_counters import ANIMATION_COUNTERS

from app.constants import TILEWIDTH, TILEHEIGHT, COLORKEY
from app.engine.objects.unit import UnitObject

from app.data.resources.resources import RESOURCES
from app.data.database.database import DB
from app.data.resources.default_palettes import default_palettes

from app.utilities import utils

from app.engine.sprites import SPRITES
from app.engine.sound import get_sound_thread
from app.engine import engine, image_mods, gui, health_bar, equations
from app.engine import item_funcs, item_system, skill_system, particles, status_heal_effect
import app.engine.config as cf
from app.engine.animations import Animation
from app.engine.game_state import game
from app.utilities.typing import NID, Color3

import logging

# The color map sprites are outlined in, in their blue palette (color 15 on the GBA)
MAP_SPRITE_OUTLINE: Color3 = (64, 56, 56)

def swap_arc_frames(distance: int) -> int:
    """
    How many frames a unit takes to fly `distance` pixels when units are
    reordered on the prep screen: 12 for no distance, 48 for 512 pixels.
    From the GBA games (FE8's PrepUnitSwapProc_Init)
    """
    return 12 + 36 * distance // 512

def swap_arc_offset(start: Tuple[int, int], progress: float) -> Tuple[int, int]:
    """
    Where a unit is, in pixels from its new tile, `progress` (0 to 1) of the
    way through that flight. `start` is where it began, also in pixels from
    its new tile. The unit bows out to the left of its heading, by more the
    farther it flies but never by much more than a tile, so that two units
    trading places circle each other.
    From the GBA games (FE8's PrepUnitSwapProc_MainLoop)
    """
    distance = math.isqrt(start[0] * start[0] + start[1] * start[1])
    bow = math.sin(math.pi * progress) * 0x1000 / (0x1000 + (0x20000 - 0x1000) * distance // 0x200)
    return (start[0] + math.floor(-start[0] * progress) + int(-start[1] * bow),
            start[1] + math.floor(-start[1] * progress) + int(start[0] * bow))

class SingleMapSprite():
    frames: List[engine.Surface] = []
    counter: GenericAnimCounter = None

    @classmethod
    def create_looping_sprite(cls, frames: List[engine.Surface], counter: Any) -> SingleMapSprite:
        """Create a sprite that loops on a (probably) shared counter"""
        sprite = cls()
        sprite.frames = frames
        sprite.counter = counter
        return sprite

    @classmethod
    def create_anim_sprite(cls, frames: List[engine.Surface], frame_timings: List[int]) -> SingleMapSprite:
        """Create an animated sprite that only plays once"""
        sprite = cls()
        sprite.frames = frames
        sprite.counter = GenericAnimCounter.from_frames(frame_timings, loop=False, get_time=engine.get_time)
        return sprite

    def get_frame(self) -> engine.Surface:
        return self.frames[self.counter.count].copy()

    def get_stationary_frame(self) -> engine.Surface:
        return self.frames[0].copy()

class MapSprite():
    def __init__(self, map_sprite: map_sprites.MapSprite, team: NID, palette_override: NID = None):
        self.nid = map_sprite.nid
        self.team = team
        self.palette_override = palette_override
        self.resource = map_sprite
        if not map_sprite.standing_image:
            map_sprite.standing_image = engine.image_load(map_sprite.stand_full_path)
        if not map_sprite.moving_image:
            map_sprite.moving_image = engine.image_load(map_sprite.move_full_path)
        stand, move = self.convert_to_team_colors(map_sprite)
        engine.set_colorkey(stand, COLORKEY, rleaccel=True)
        engine.set_colorkey(move, COLORKEY, rleaccel=True)
        passive_frames = [engine.subsurface(stand, (num*64, 0, 64, 48)) for num in range(3)]
        self.passive = SingleMapSprite.create_looping_sprite(passive_frames, ANIMATION_COUNTERS.passive_sprite_counter)
        if DB.constants.value('autogenerate_grey_map_sprites'):
            gray_frames = [engine.subsurface(stand, (num*64, 0, 64, 48)) for num in range(3)]
            self.gray = SingleMapSprite.create_looping_sprite(self.create_gray(gray_frames), ANIMATION_COUNTERS.passive_sprite_counter)
        else:
            gray_frames = [engine.subsurface(stand, (num*64, 48, 64, 48)) for num in range(3)]
            self.gray = SingleMapSprite.create_looping_sprite(gray_frames, ANIMATION_COUNTERS.passive_sprite_counter)

        down_frames = [engine.subsurface(move, (num*48, 0, 48, 40)) for num in range(4)]
        self.down = SingleMapSprite.create_looping_sprite(down_frames, ANIMATION_COUNTERS.move_sprite_counter)
        self.down_stand = SingleMapSprite.create_anim_sprite([self.down.get_stationary_frame()], [22])
        left_frames = [engine.subsurface(move, (num*48, 40, 48, 40)) for num in range(4)]
        self.left = SingleMapSprite.create_looping_sprite(left_frames, ANIMATION_COUNTERS.move_sprite_counter)
        self.left_stand = SingleMapSprite.create_anim_sprite([self.left.get_stationary_frame()], [22])
        right_frames = [engine.subsurface(move, (num*48, 80, 48, 40)) for num in range(4)]
        self.right = SingleMapSprite.create_looping_sprite(right_frames, ANIMATION_COUNTERS.move_sprite_counter)
        self.right_stand = SingleMapSprite.create_anim_sprite([self.right.get_stationary_frame()], [22])
        up_frames = [engine.subsurface(move, (num*48, 120, 48, 40)) for num in range(4)]
        self.up = SingleMapSprite.create_looping_sprite(up_frames, ANIMATION_COUNTERS.move_sprite_counter)
        self.up_stand = SingleMapSprite.create_anim_sprite([self.up.get_stationary_frame()], [22])

        active_frames = [engine.subsurface(stand, (num*64, 96, 64, 48)) for num in range(3)]
        self.active = SingleMapSprite.create_looping_sprite(active_frames, ANIMATION_COUNTERS.active_sprite_counter)
        self.start_cast = SingleMapSprite.create_anim_sprite(active_frames, [22, 4, 22])
        self.end_cast = SingleMapSprite.create_anim_sprite([frame for frame in reversed(active_frames)], [22, 4, 22])

    def _get_team_palette(self):
        palette_nid = self.palette_override
        palette = RESOURCES.combat_palettes.get(palette_nid)
        if not palette: #If we can't find a valid override palette, default to team colors
            if palette_nid is not None:
                logging.error("Map palette override with nid %s could not be found." % palette_nid)
            team_obj = game.teams.get(self.team)
            palette_nid = team_obj.map_sprite_palette
            palette = RESOURCES.combat_palettes.get(palette_nid)
            if not palette:
                logging.error("Unable to locate map sprite palette with nid %s" % palette_nid)
        return palette

    def convert_to_team_colors(self, map_sprite):
        self.outline_color = MAP_SPRITE_OUTLINE
        if self.team == 'black' and not self.palette_override:
            palette = RESOURCES.combat_palettes.get('map_sprite_black')
            if palette:
                colors: List[Color3] = palette.get_colors()
            else:
                colors: List[Color3] = default_palettes['map_sprite_black']
        elif not game.teams:
            # Currently in Title Screen, havent loaded any games, so game.teams is empty
            return map_sprite.standing_image, map_sprite.moving_image
        else:
            palette = self._get_team_palette()
            if palette:
                colors: List[Color3] = palette.get_colors()
            else:
                colors: List[Color3] = default_palettes['map_sprite_black']

        conversion_dict = {a: b for a, b in zip(default_palettes['map_sprite_blue'], colors)}
        self.outline_color = conversion_dict.get(MAP_SPRITE_OUTLINE, MAP_SPRITE_OUTLINE)
        return image_mods.color_convert(map_sprite.standing_image, conversion_dict), \
            image_mods.color_convert(map_sprite.moving_image, conversion_dict)

    def create_gray(self, imgs):
        """
        Assumes imgs have already been converted to team colors
        """
        palette = RESOURCES.combat_palettes.get('map_sprite_wait')
        if palette:
            colors: List[Color3] = palette.get_colors()
        else:
            colors: List[Color3] = default_palettes['map_sprite_wait']

        # Handle the situation where team is "black"
        if self.team == 'black':
            new_colors: List[Color3] = default_palettes['map_sprite_black']
        elif not game.teams:
            # Currently in Title Screen, havent loaded any games, so game.teams is empty
            new_colors: List[Color3] = default_palettes['map_sprite_blue']
        else:
            current_palette = self._get_team_palette()
            new_colors: List[Color3] = current_palette.get_colors()
        conversion_dict: Dict[Color3, Color3] = {a: b for a, b in zip(new_colors, colors)}
        imgs = [image_mods.color_convert(img, conversion_dict) for img in imgs]
        # for img in imgs:
            # engine.set_colorkey(img, COLORKEY, rleaccel=True)
        return imgs

    def create_image(self, state, stationary=False):
        image: SingleMapSprite = self.__dict__.get(state)  # This is roughly 2x as fast as getattr, but getattr is safer
        return image.get_stationary_frame() if stationary else image.get_frame()

def load_map_sprite(unit: UnitObject | UnitPrefab, team='player'):
    klass = DB.classes.get(unit.klass)
    nid = klass.map_sprite_nid
    variant = skill_system.change_variant(unit) if isinstance(unit, UnitObject) else unit.variant
    if variant:
        nid += variant
    res = RESOURCES.map_sprites.get(nid)
    if not res:  # Try without unit variant
        res = RESOURCES.map_sprites.get(klass.map_sprite_nid)
    if not res:
        return None
    
    palette_override = skill_system.change_map_palette(unit) if isinstance(unit, UnitObject) else None
    if palette_override:
        term = palette_override
    else:
        term = team
    map_sprite = game.map_sprite_registry.get(res.nid + '_' + term)
    if not map_sprite:
        map_sprite = MapSprite(res, team, palette_override)
        game.map_sprite_registry[map_sprite.nid + '_' + term] = map_sprite
    return map_sprite

def load_klass_sprite(klass_nid: NID, team: NID = 'player') -> Optional[MapSprite]:
    klass = DB.classes.get(klass_nid)
    nid = klass.map_sprite_nid
    res = RESOURCES.map_sprites.get(nid)
    if not res:
        return None

    map_sprite = game.map_sprite_registry.get(res.nid + '_' + team)
    if not map_sprite:
        map_sprite = MapSprite(res, team)
        game.map_sprite_registry[map_sprite.nid + '_' + team] = map_sprite
    return map_sprite

class UnitSprite():
    default_transition_time = 450
    cardinal = ['down', 'left', 'right', 'up']

    def __init__(self, unit):
        self.unit = unit
        self.state = 'normal'  # What state the image sprite is in
        self.image_state = 'passive'  # What the image looks like
        self.hover_start = None  # When the cursor came onto the unit
        self.transition_state = 'normal'

        self.transition_counter = 0
        self.transition_time = self.default_transition_time
        # Where a 'swap_arc' began, in pixels from the unit's tile, and how long it takes
        self.swap_arc_start = (0, 0)
        self.swap_arc_time = 0

        self._fake_position = None  # For escape and rescue, etc...
        self._roam_position = None  # For roam
        self.net_position = None
        self.offset = [0, 0]
        # Set by change_state whenever a combat state is entered -- when True the unit
        # neither turns to face its opponent nor jostles towards it
        self.suppress_combat_movement = False

        self.flicker = []
        # When the unit began to show a bad status leaving it
        self.status_heal_start: Optional[int] = None
        # When the unit began to fade away in death
        self.death_fade_start: Optional[int] = None
        self.vibrate = []
        self.vibrate_counter = 0
        self.animations: Dict[NID, Animation] = {}
        self.particles = []
        self.damage_numbers = []

        self.map_sprite = load_map_sprite(self.unit, self.unit.team)

        self.health_bar = health_bar.MapHealthBar(self.unit)

    def set_image_state(self, new_state: str):
        self.image_state = new_state

    @property
    def position(self):
        if self._fake_position:
            return self._fake_position
        elif self._roam_position:
            return self._roam_position
        else:
            return self.unit.position

    def set_roam_position(self, pos):
        self._roam_position = pos

    def get_roam_position(self):
        return self._roam_position

    def load_sprites(self):
        self.map_sprite = load_map_sprite(self.unit, self.unit.team)

    # Normally drawing units is culled to those on the screen
    # Unit sprites matching this will be drawn anyway
    def draw_anyway(self):
        return self.transition_state != 'normal' or self.particles

    def reset(self):
        self.offset = [0, 0]
        ANIMATION_COUNTERS.attack_movement_counter.reset()
        self._roam_position = None

    def get_round_fake_pos(self):
        if self._fake_position:
            return utils.round_pos(self._fake_position)
        elif self._roam_position:
            return utils.round_pos(self._roam_position)
        return None

    def add_animation(self, anim, loop=True, contingent=False):
        if isinstance(anim, str):
            anim = RESOURCES.animations.get(anim)
            if anim:
                anim = Animation(anim, (-16, -16), loop=loop, contingent=contingent)
            else:
                return
        if anim.nid in self.animations:
            return False
        self.animations[anim.nid] = anim
        return True

    def remove_animation(self, animation_nid):
        if animation_nid in self.animations:
            del self.animations[animation_nid]
            return True
        return False

    def begin_flicker(self, total_time, color, direction='add'):
        self.flicker.append((engine.get_time(), total_time, color, direction, False))

    def start_flicker(self, start_time, total_time, color, direction='add', fade_out=False):
        self.flicker.append((engine.get_time() + start_time, total_time, color, direction, fade_out))

    def start_status_heal(self):
        """Shows a bad status leaving the unit, as on the GBA"""
        self.status_heal_start = engine.get_time()

    # As on the GBA (MU_StartDeathFade), a dying unit flashes white and its colors come back
    # over 20 frames, while over 32 it fades away. It is added onto the map below it, out of
    # 16 parts at first and one less every other frame, so it lightens the map as it goes
    death_fade_frames = 32
    death_flash_frames = 20

    def start_death_fade(self):
        self.death_fade_start = engine.get_time()

    def death_fade_image(self, image: engine.Surface, frame: int) -> Optional[engine.Surface]:
        """The dying unit's image on this frame of its fade, to be added onto the map. None once it is gone"""
        strength = (self.death_fade_frames - frame) >> 1
        if strength <= 0:
            return None
        image = image.convert_alpha()
        white = max(0, self.death_flash_frames - frame) / self.death_flash_frames
        if white:
            # From the GBA's white back to its own colors
            engine.fill(image, (int(255 * (1 - white)),) * 3, None, engine.BLEND_RGB_MULT)
            engine.fill(image, (int(248 * white),) * 3, None, engine.BLEND_RGB_ADD)
        # On black, so nothing is added where the unit is not
        faded = engine.create_surface(image.get_size())
        faded.fill((0, 0, 0))
        faded.blit(image, (0, 0))
        engine.fill(faded, (255 * strength // 16,) * 3, None, engine.BLEND_RGB_MULT)
        return faded

    def start_vibrate(self, start_time, total_time):
        self.vibrate.append((engine.get_time() + start_time, total_time))

    def add_warp_anim(self, nid, reverse=False):
        anim = RESOURCES.animations.get('Warp')
        if anim:
            anim_trans = Animation(anim, (-7, -24), reverse=reverse)
            anim_trans.sprite = image_mods.make_translucent(anim_trans.sprite, .33)
            self.animations[nid] = anim_trans
            anim_blend = Animation(anim, (-7, -24), reverse=reverse)
            anim_blend.set_tint(engine.BlendMode.BLEND_RGB_ADD)
            self.animations[nid + '_blend'] = anim_blend

    def add_warp_flowers(self, reverse=False):
        ps = particles.SimpleParticleSystem('warp_flower', particles.WarpFlower, self.unit.position, (-1, -1, -1, -1), 0)
        angle_frac = math.pi / 8
        if self._roam_position:
            pos = self._roam_position
        elif self._fake_position:
            pos = self._fake_position
        elif self.unit.position:
            pos = self.unit.position
        else:
            logging.error("No position for sprite found during add warp flowers!")
            return
        true_pos_x = pos[0] * TILEWIDTH + TILEWIDTH//2
        true_pos_y = pos[1] * TILEHEIGHT + TILEHEIGHT//2
        for idx, speed in enumerate((4.5, )):
            for num in range(0, 16):
                angle = num * angle_frac + (angle_frac / 2 if idx == 0 else 0)
                if reverse:
                    new_particle = particles.ReverseWarpFlower().reset((true_pos_x, true_pos_y), speed, angle)
                else:
                    new_particle = particles.WarpFlower().reset((true_pos_x, true_pos_y), speed, angle)
                ps.particles.append(new_particle)
        self.particles.append(ps)

    def add_swoosh_anim(self, reverse=False):
        anim = RESOURCES.animations.get('Swoosh')
        if anim:
            anim = Animation(anim, (-12, -40), reverse=reverse)
        self.animations['swoosh'] = anim

    def add_damage_number(self, damage: int):
        """
        damage should be positive if its a damage
        and negative if its a heal
        """
        str_damage = str(abs(damage))
        if damage >= 0:
            color = 'small_red'
        else:
            color = 'small_cyan'
        for idx, num in enumerate(str_damage):
            d = gui.DamageNumber(int(num), idx, len(str_damage), self.position, color)
            self.damage_numbers.append(d)

    def set_transition(self, new_state):
        self.transition_state = new_state
        self.transition_counter = self.transition_time  # 400
        if self.state == 'moving':
            # self.change_state('normal')
            self.reset()

        if self.transition_state == 'normal':
            self.offset = [0, 0]
            self._fake_position = None
        elif self.transition_state == 'fake_in':
            self._fake_position = None
            self.change_state('fake_transition_in')
        elif self.transition_state in ('fake_out', 'rescue'):
            self._fake_position = self.unit.position
            self.change_state('fake_transition_out')
        elif self.transition_state == 'fade_in':
            self._fake_position = None
        elif self.transition_state == 'fade_out':
            self._fake_position = self.unit.position
        elif self.transition_state == 'fade_move':
            self._fake_position = self.unit.position
        elif self.transition_state == 'warp_in':
            get_sound_thread().play_sfx('WarpEnd')
            self._fake_position = None
            self.add_warp_anim('warp_in')
            self.add_warp_flowers(reverse=True)
        elif self.transition_state == 'warp_out':
            get_sound_thread().play_sfx('Warp')
            self._fake_position = self.unit.position
            self.add_warp_anim('warp_out')
            self.begin_flicker(self.transition_time, (255, 255, 255))
            self.add_warp_flowers()
        elif self.transition_state == 'warp_move':
            get_sound_thread().play_sfx('Warp')
            self._fake_position = self.unit.position
            self.add_warp_anim('warp_move')
            self.begin_flicker(self.transition_time, (255, 255, 255))
            self.add_warp_flowers()
        elif self.transition_state == 'swoosh_in':
            get_sound_thread().play_sfx('Sword Whoosh')
            self._fake_position = None
            self.add_swoosh_anim()
        elif self.transition_state == 'swoosh_out':
            get_sound_thread().play_sfx('Sword Whoosh')
            self._fake_position = self.unit.position
            self.add_swoosh_anim(reverse=True)
        elif self.transition_state == 'swoosh_move':
            get_sound_thread().play_sfx('Sword Whoosh')
            self._fake_position = self.unit.position
            self.add_swoosh_anim(reverse=True)

    def begin_swap_arc(self, old_pos: Tuple[int, int]):
        """
        Draws the unit flying in an arc from old_pos to the tile it now stands on,
        as units do on the GBA when they are reordered on the prep screen
        """
        self.set_transition('swap_arc')
        self._fake_position = None
        self.swap_arc_start = ((old_pos[0] - self.unit.position[0]) * TILEWIDTH,
                               (old_pos[1] - self.unit.position[1]) * TILEHEIGHT)
        distance = math.isqrt(self.swap_arc_start[0] ** 2 + self.swap_arc_start[1] ** 2)
        self.swap_arc_time = utils.frames2ms(swap_arc_frames(distance))
        self.transition_counter = self.swap_arc_time
        self.offset = list(self.swap_arc_start)

    combat_states = ('combat_attacker', 'combat_anim', 'combat_defender', 'combat_counter')

    def change_state(self, new_state, dir = None, suppress_movement: bool = False):
        self.state = new_state
        if self.state in self.combat_states:
            self.suppress_combat_movement = suppress_movement
        if self.state in ('combat_attacker', 'combat_anim'):
            self.net_position = game.cursor.position[0] - self.unit.position[0], game.cursor.position[1] - self.unit.position[1]
            self.handle_net_position(self.net_position)
            self.reset()
        elif self.state in ('combat_active', 'active'):
            self.set_image_state('active')
        elif self.state == 'combat_defender':
            attacker = game.memory['current_combat'].attacker
            self.net_position = attacker.position[0] - self.unit.position[0], attacker.position[1] - self.unit.position[1]
            self.handle_net_position(self.net_position)
        elif self.state == 'combat_counter':
            attacker = game.memory['current_combat'].defender
            if attacker:
                self.net_position = attacker.position[0] - self.unit.position[0], attacker.position[1] - self.unit.position[1]
            else:
                self.net_position = 0, 0
            self.handle_net_position(self.net_position)
        elif self.state == 'fake_transition_in':
            pos = (self.unit.position[0] + utils.clamp(self.offset[0], -1, 1),
                   self.unit.position[1] + utils.clamp(self.offset[1], -1, 1))
            pos = (pos[0] - self.unit.position[0], pos[1] - self.unit.position[1])
            self.net_position = (-pos[0], -pos[1])
            self.handle_net_position(self.net_position)
        elif self.state == 'fake_transition_out':
            pos = (utils.clamp(self.offset[0], -1, 1),
                   utils.clamp(self.offset[1], -1, 1))
            self.net_position = pos
            self.handle_net_position(self.net_position)
        elif self.state == 'selected':
            # Mounted units face right while selected, everybody else faces down
            self.set_image_state('right' if 'Mounted' in self.unit.tags else 'down')
        elif self.state == 'start_cast':
            self.map_sprite.start_cast.counter.reset()
            self.set_image_state('start_cast')
        elif self.state == 'end_cast':
            self.map_sprite.end_cast.counter.reset()
            self.set_image_state('end_cast')
        elif self.state == 'normal':
            self.set_transition('normal')
        elif self.state == 'moving' and dir in self.cardinal:
            self.set_image_state(dir)
        elif self.state == 'stand_dir' and dir in self.cardinal:
            self.set_image_state(dir + '_stand')

    def handle_net_position(self, pos):
        self.net_position = pos
        if self.suppress_combat_movement and self.state in self.combat_states:
            return  # Hold whatever direction the unit was already facing
        if abs(pos[0]) >= abs(pos[1]):
            if pos[0] > 0:
                self.set_image_state('right')
            elif pos[0] < 0:
                self.set_image_state('left')
            else:
                self.set_image_state('down')  # default
        else:
            if pos[1] < 0:
                self.set_image_state('up')
            else:
                self.set_image_state('down')

    def clear_net_position(self):
        self.net_position = None

    def update(self):
        self.update_state()
        self.update_transition()
        self.health_bar.update()

        # update animations
        self.animations = {k: v for (k, v) in self.animations.items() if not v.update()}

        # update personal particles
        self.particles = [ps for ps in self.particles if not ps.remove_me_flag]
        for particle_system in self.particles:
            particle_system.update()

        # update damage numbers
        self.damage_numbers = [d for d in self.damage_numbers if not d.done]
        for damage_num in self.damage_numbers:
            damage_num.update()

    # As on the GBA, a player unit's hover animation waits for the cursor to rest on it
    # for 5 frames, so that it is not begun for every unit the cursor passes over
    hover_wait = utils.frames2ms(4.5)

    def update_state(self):
        hovered = self.state == 'normal' and game.cursor.draw_state and \
            game.cursor.position == self.unit.position and self.unit.team == 'player'
        if not hovered:
            self.hover_start = None
        elif self.hover_start is None:
            self.hover_start = engine.get_time()

        if self.state == 'normal':
            if self.unit.finished and not self.unit.is_dying:
                self.set_image_state('gray')
            elif DB.constants.value('initiative') and game.initiative.get_current_unit() != self.unit \
                    and not game.is_roam() and self.unit.team == 'player':
                self.set_image_state('gray')
            elif hovered and engine.get_time() - self.hover_start >= self.hover_wait:
                if self.image_state != 'active':
                    # and then it starts from its first frame
                    ANIMATION_COUNTERS.active_sprite_counter.restart()
                self.set_image_state('active')
            elif game.is_roam() and game.get_roam_unit() == self.unit:
                self.set_image_state('passive')
            else:
                self.set_image_state('passive')
        elif self.state == 'combat_anim':
            if self.suppress_combat_movement:
                self.offset = [0, 0]
            else:
                self.offset[0] = utils.clamp(self.net_position[0], -1, 1) * ANIMATION_COUNTERS.attack_movement_counter.value()
                self.offset[1] = utils.clamp(self.net_position[1], -1, 1) * ANIMATION_COUNTERS.attack_movement_counter.value()
        elif self.state == 'chosen':
            pos = self.unit.position or self._fake_position
            test_position = game.cursor.position[0] - pos[0], game.cursor.position[1] - pos[1]
            if test_position != (0, 0):
                self.net_position = test_position
            if self.net_position:
                self.handle_net_position(self.net_position)
            else:
                self.set_image_state('down')
        elif self.state == 'moving':
            # next_position = game.movement.get_next_position(self.unit.nid)
            # if not next_position or not self.unit.position:
            #     self.set_transition('normal')
            #     return
            # self.net_position = (next_position[0] - self.unit.position[0], next_position[1] - self.unit.position[1])
            # last_update = game.movement.get_last_update(self.unit.nid)
            # current_time = engine.get_time()
            # dt = current_time - last_update
            # self.offset[0] = int(TILEWIDTH * dt / max(self.speed, 1) * self.net_position[0])
            # self.offset[1] = int(TILEHEIGHT * dt / max(self.speed, 1) * self.net_position[1])
            # self.handle_net_position(self.net_position)
            pass # Handled in movement system
        elif self.state == 'fake_transition_in':
            if self.offset[0] > 0:
                self.offset[0] -= 2
            elif self.offset[0] < 0:
                self.offset[0] += 2
            if self.offset[1] > 0:
                self.offset[1] -= 2
            elif self.offset[1] < 0:
                self.offset[1] += 2

            if self.offset[0] == 0 and self.offset[1] == 0:
                self.set_transition('normal')
                self.change_state('normal')
        elif self.state == 'fake_transition_out':
            if self.offset[0] > 0:
                self.offset[0] += 2
            elif self.offset[0] < 0:
                self.offset[0] -= 2
            if self.offset[1] > 0:
                self.offset[1] += 2
            elif self.offset[1] < 0:
                self.offset[1] -= 2

            if abs(self.offset[0]) > TILEWIDTH or abs(self.offset[1]) > TILEHEIGHT:
                self.set_transition('normal')
                self.change_state('normal')

    def walk_one_tile(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int], stays: bool):
        """
        As on the GBA (KOIDO), the unit walks one tile at its usual pace, from from_pos
        to to_pos: into a unit that rescues it, out of the one that drops it, or from one
        to another. If it stays, it is on the map at to_pos; otherwise it is gone once there
        """
        from app.engine.movement import movement_funcs
        self.set_transition('walk')
        self.walk_vector = (to_pos[0] - from_pos[0], to_pos[1] - from_pos[1])
        self.walk_stays = stays
        self.walk_start = engine.get_time()
        self.walk_time = movement_funcs.get_default_speed(self.unit)
        self._fake_position = None if stays else from_pos
        self.offset = [-TILEWIDTH * self.walk_vector[0], -TILEHEIGHT * self.walk_vector[1]] if stays else [0, 0]
        self.change_state('moving')
        self.handle_net_position(self.walk_vector)
        self.unit.sound.play()

    def update_walk(self):
        progress = (engine.get_time() - self.walk_start) / max(self.walk_time, 1)
        if progress < 1:
            # Rounded, so at the GBA's pace it steps 2 pixels a frame, as it does on a move
            start = -1 if self.walk_stays else 0
            self.offset = [round(TILEWIDTH * (start + progress) * self.walk_vector[0]),
                           round(TILEHEIGHT * (start + progress) * self.walk_vector[1])]
        else:
            self.unit.sound.stop()
            self.change_state('normal')
            self.set_transition('normal')

    def update_transition(self):
        self.transition_counter -= engine.get_delta()
        if self.transition_state == 'walk':
            self.update_walk()
            return
        if self.transition_state == 'swap_arc':
            if self.transition_counter > 0:
                progress = 1 - self.transition_counter / self.swap_arc_time
                self.offset = list(swap_arc_offset(self.swap_arc_start, progress))
            else:
                self.set_transition('normal')
            return
        if self.transition_counter < 0:
            self.transition_counter = 0
            self._fake_position = None
            if self.transition_state in ('fade_out', 'warp_out', 'swoosh_out', 'fade_in', 'warp_in', 'swoosh_in'):
                self.set_transition('normal')
            elif self.transition_state == 'fade_move':
                self.set_transition('fade_in')
            elif self.transition_state == 'warp_move':
                self.set_transition('warp_in')
            elif self.transition_state == 'swoosh_move':
                self.set_transition('swoosh_in')

    def create_image(self, state, stationary=False):
        stationary = stationary or self.unit.is_dying
        if not self.map_sprite:  # This shouldn't happen, but if it does...
            res = RESOURCES.map_sprites[0]
            self.map_sprite = MapSprite(res, self.unit.team)
        if self.transition_state == 'swoosh_in':
            state = 'down'
        return self.map_sprite.create_image(state, stationary)

    def get_topleft(self, cull_rect):
        if self._fake_position:
            x, y = self._fake_position
        elif self._roam_position:
            x, y = self._roam_position
        elif self.unit.position:
            x, y = self.unit.position
        left = x * TILEWIDTH + self.offset[0] - cull_rect[0]
        top = y * TILEHEIGHT + self.offset[1] - cull_rect[1]
        return left, top

    def draw(self, surf, cull_rect):
        current_time = engine.get_time()
        image = self.create_image(self.image_state)
        left, top = self.get_topleft(cull_rect)

        anim_top = top

        self.vibrate_counter += 1
        for vibrate in self.vibrate[:]:
            starting_time, total_time = vibrate
            if engine.get_time() >= starting_time:
                if engine.get_time() > starting_time + total_time:
                    self.vibrate.remove(vibrate)
                    continue
                left += (2 if self.vibrate_counter % 2 else -2)  # As far as on the GBA

        # Handle transitions
        if self.transition_state in ('fade_out', 'warp_out', 'swoosh_out', 'fade_move', 'warp_move', 'swoosh_move') or self.state in ('fake_transition_out'):
            progress = utils.clamp((self.transition_time - self.transition_counter) / self.transition_time, 0, 1)
            # Distort Vertically
            if self.transition_state in ('swoosh_out', 'swoosh_move'):
                cur_width, cur_height = image.get_width(), image.get_height()
                new_width, new_height = cur_width, int(cur_height * (max(0, progress - 0.4) * 3 + 1))
                extra_height = new_height - cur_height
                image = engine.transform_scale(image, (new_width, new_height))
                top -= extra_height
            image = image_mods.make_translucent(image.convert_alpha(), progress)

        elif self.transition_state in ('fade_in', 'warp_in', 'swoosh_in') or self.state in ('fake_transition_in'):
            progress = utils.clamp((self.transition_time - self.transition_counter) / self.transition_time, 0, 1)
            progress = 1 - progress
            if self.transition_state == 'swoosh_in':
                # Distort Vertically
                cur_width, cur_height = image.get_width(), image.get_height()
                new_width, new_height = cur_width, int(cur_height * (max(0, progress - 0.4) * 3 + 1))
                extra_height = new_height - cur_height
                image = engine.transform_scale(image, (new_width, new_height))
                top -= extra_height
            image = image_mods.make_translucent(image.convert_alpha(), progress)

        # Flickering the unit a specific color, like flash white during a map combat hit
        for flicker in self.flicker[:]:
            starting_time, total_time, color, direction, fade_out = flicker
            if engine.get_time() >= starting_time:
                if engine.get_time() > starting_time + total_time:
                    self.flicker.remove(flicker)
                    continue
                if fade_out:
                    time_passed = engine.get_time() - starting_time
                    color = tuple((total_time - time_passed) * float(c) // total_time for c in color)
                if direction == 'add':
                    image = image_mods.add_tint(image.convert_alpha(), color)
                elif direction == 'sub':
                    image = image_mods.sub_tint(image.convert_alpha(), color)

        if self.status_heal_start is not None:
            # Frames since it began, to the nearest frame
            frame = int((current_time - self.status_heal_start) * 60 / 1000 + 0.5)
            if frame < status_heal_effect.FRAMES:
                image = status_heal_effect.draw(image, frame, self.map_sprite.outline_color)
            else:
                self.status_heal_start = None

        # Color a unit red if they are highlighted by the boundary
        if not self.flicker and self.status_heal_start is None and \
                game.boundary.draw_flag and self.unit.nid in game.boundary.displaying_units:
            image = image_mods.change_color(image.convert_alpha(), (60, 0, 0))

        # Turnwheel tint of unit sprite
        if game.action_log.hovered_unit is self.unit:
            length = 200
            if not (current_time // length) % 2:
                diff = current_time % length
                if diff > length // 2:
                    diff = length - diff
                diff = utils.clamp(255. * diff / length * 2, 0, 255)
                color = (0, int(diff * .5), 0)  # Tint image green at magnitude depending on diff
                image = image_mods.change_color(image.convert_alpha(), color)

        flicker_tints = skill_system.unit_sprite_flicker_tint(self.unit)
        flicker_tints = [image_mods.FlickerTint(*tint) for tint in flicker_tints]
        image = image_mods.draw_flicker_tint(image, current_time, flicker_tints)

        final_alpha = skill_system.unit_sprite_alpha_tint(self.unit)
        if final_alpha != 0.0:
            image = image_mods.make_translucent(image.convert_alpha(), final_alpha)

        # Each image has (self.image.get_width() - 32)//2 pixels on the
        # left and right of it, to handle any off tile spriting
        topleft = left - max(0, (image.get_width() - 16)//2), top - 24

        if DB.constants.value('pairup') and self.unit.traveler:
            partner = game.get_unit(self.unit.traveler)
            partner_state = 'passive' if self.image_state in ('start_cast', 'end_cast') else self.image_state
            partner_image = partner.sprite.create_image(partner_state)
            partner_image = partner_image.convert_alpha()
            surf.blit(partner_image, (topleft[0] + 3, topleft[1] - 3))
            surf.blit(image, (topleft[0] - 3, topleft[1] + 3))
        elif self.death_fade_start is not None:
            # Frames since it began, to the nearest frame
            frame = int((current_time - self.death_fade_start) * 60 / 1000 + 0.5)
            faded = self.death_fade_image(image, frame)
            if faded:
                # It adds onto what is below, so onto the map itself, below the other units (see MapView.draw_units)
                surf.blit(faded, topleft, None, engine.BLEND_RGB_ADD)
        else:
            surf.blit(image, topleft)

        # Draw animations
        valid_anims: list = skill_system.should_draw_anim(self.unit)
        for animation in self.animations.values():
            if not animation.contingent or animation.nid in valid_anims:
                animation.draw(surf, (left, anim_top))

        # Draw personal particles
        for particle_system in self.particles:
            particle_system.draw(surf, cull_rect[0], cull_rect[1])

        # Draw damage numbers
        for damage_num in self.damage_numbers:
            damage_num.draw(surf, (left + 4, anim_top))

        return surf

    def draw_markers(self, surf, cull_rect):
        # Talk Options
        cur_unit = None
        if game.state.current() == 'free':
            cur_unit = game.cursor.get_hover()
        elif game.state.current() in ('move', 'menu', 'item', 'item_child', 'item_discard',
                                      'weapon_choice', 'spell_choice', 'targeting',
                                      'combat_targeting', 'item_targeting'):
            cur_unit = game.cursor.cur_unit
        elif game.state.current() == 'free_roam':
            cur_unit = game.get_roam_unit()
        if not cur_unit:
            return surf

        left, top = self.get_topleft(cull_rect)
        topleft = (left - 2, top - 14)

        frame = (engine.get_time() // 100) % 8
        offset = [0, 0, 0, 1, 2, 2, 2, 1][frame]
        markers = []
        if game.is_roam() and game.state.current() == 'free_roam' and game.state.state[-1].get_closest_unit(must_have_talk=True) and \
                (self.unit.nid, cur_unit.nid) in game.talk_options and (self.unit.nid, cur_unit.nid) not in game.talk_hidden:
            markers.append('talk')
        elif (cur_unit.nid, self.unit.nid) in game.talk_options and (cur_unit.nid, self.unit.nid) not in game.talk_hidden:
            markers.append('talk')
        if (game.is_roam() and game.state.current() == 'free_roam' and
                game.state.state[-1].get_visit_region() and
                game.state.state[-1].roam_unit and
                game.state.state[-1].roam_unit.nid == self.unit.nid):
            markers.append('interact')
        if cur_unit.team == 'player':
            for item in item_funcs.get_all_items(self.unit):
                markers += item_system.target_icon(self.unit, item, cur_unit)
            markers += skill_system.target_icon(cur_unit, self.unit)
        markers = [SPRITES.get('marker_%s' % marker) for marker in markers if marker]
        markers = [_ for _ in markers if _]  # Only include non-None
        if markers:
            icon_frame = (engine.get_time() // 500) % len(markers)
            surf.blit(markers[icon_frame], (topleft[0], topleft[1] + offset))
        return surf

    def check_draw_hp(self) -> bool:
        if game.is_roam() and DB.constants.value('roam_hide_hp'):
            return False
        if self.unit.is_dying or self.unit.dead:
            return False
        if (cf.SETTINGS['hp_map_team'] == 'All') or \
           (cf.SETTINGS['hp_map_team'] == 'Ally' and self.unit.team in DB.teams.allies) or \
           (cf.SETTINGS['hp_map_team'] == 'Enemy' and self.unit.team in DB.teams.enemies):
            if (cf.SETTINGS['hp_map_cull'] == 'All') or \
               (cf.SETTINGS['hp_map_cull'] == 'Wounded' and self.unit.get_hp() < equations.parser.hitpoints(self.unit)):
                return True
        return False

    def draw_hp(self, surf, cull_rect, event=False):
        current_time = engine.get_time()
        left, top = self.get_topleft(cull_rect)

        if not event and self.check_draw_hp():
            self.health_bar.draw(surf, left, top)

        if self.transition_state == 'normal' and not self.unit.is_dying and \
                self.image_state in ('gray', 'passive') and int((current_time%450) // 150) in (1, 2):
            icon = None
            if 'Boss' in self.unit.tags:
                icon = SPRITES.get('boss_icon')
            elif 'Elite' in self.unit.tags:
                icon = SPRITES.get('elite_icon')
            elif 'Protect' in self.unit.tags:
                team_color = game.teams.get(self.unit.team).combat_color
                icon = SPRITES.get('protect_%s_icon' % team_color, 'protect_icon')
            if icon:
                surf.blit(icon, (left - 8, top - 8))

        if self.unit.traveler and self.transition_state == 'normal' and \
                not self.unit.is_dying and not DB.constants.value('pairup'):
            traveler_team = game.get_unit(self.unit.traveler).team
            team_color = game.teams.get(traveler_team).combat_color
            rescue_icon = SPRITES.get('rescue_icon_%s' % team_color, 'rescue_icon_green')
            topleft = (left - 8, top - 8)
            surf.blit(rescue_icon, topleft)

        if DB.constants.value('droppable_icon') and any((i.droppable for i in self.unit.items)):
            droppable_icon = SPRITES.get('droppable_icon')
            topleft = (left - 8, top - 8)
            surf.blit(droppable_icon, topleft)

        return surf
