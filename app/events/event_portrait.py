from __future__ import annotations

import math
import random
from typing import Optional, Tuple

from app.utilities.typing import Point
from app.data.resources.portraits import PortraitPrefab

from app import counters
from app.utilities import utils
from app.constants import COLORKEY

from app.engine import engine, image_mods

def update_talk(talk_state: int, max_state: int, reverse: bool = True) -> Tuple[int, int, bool]:
    """
    The mouth's next frame while talking, how long to hold it, and whether it is closing.
    As on the GBA: shut to open and back again a frame at a time, each held 1 to 8 frames at random
    """
    if talk_state <= 0:
        reverse = False
    elif talk_state >= max_state - 1:
        reverse = True
    next_state = talk_state - 1 if reverse else talk_state + 1
    next_state = utils.clamp(next_state, 0, max(max_state - 1, 0))
    # Half a frame short, since the time is checked once a frame
    next_update = utils.frames2ms(random.randint(1, 8) - 0.5)
    return next_state, next_update, reverse

def move_frames(distance: float) -> int:
    """On the GBA a face moves in 16 frames, or 32 if it has more than 24 pixels to go"""
    return 32 if distance > 24 else 16

def ease_out(start: float, end: float, frame: int, total: int) -> int:
    """Where a moving face is on that frame: fast at first, slowing to a stop, as on the GBA"""
    left = total - frame
    return int(end - math.trunc(left * left * (end - start) / (total * total)))

class EventPortrait():
    base_transition_speed = utils.frames2ms(14)
    # A face fades in from black over 12 frames on the GBA
    fade_in_time = utils.frames2ms(12)
    # but the scene only waits 8 frames for it before going on.
    # Half a frame short, since the time is checked once a frame
    appear_wait = utils.frames2ms(7.5)
    travel_time = utils.frames2ms(15)
    bop_time = utils.frames2ms(8)
    saturation_time = utils.frames2ms(10)
    travel_speed_mult = 1

    def __init__(self, portrait: PortraitPrefab, position: Point, priority,
                 transition=False, slide=None, mirror=False, name='', expressions=None,
                 speed_mult=1):
        self.portrait = portrait
        if not self.portrait.image:
            self.portrait.image = engine.image_load(self.portrait.full_path)
        self.width = self.portrait.image.get_width()
        self.height = self.portrait.image.get_height()
        self.portrait.image = self.portrait.image.convert()
        engine.set_colorkey(self.portrait.image, COLORKEY, rleaccel=True)
        self.position = position
        self.priority = priority
        self.transition = transition
        self.transition_speed = self.fade_in_time * max(speed_mult, 0.001)
        self.transition_update = engine.get_time()
        self.slide = slide
        self.mirror = mirror
        self.name = name
        self.expressions = expressions or set()

        self.transition_progress = 0
        self.main_portrait = engine.subsurface(self.portrait.image, self.portrait.get_face_frame())
        self.chibi = engine.subsurface(self.portrait.image, self.portrait.get_minimug())

        self.talk_on = False
        self.remove = False

        # The portrait this one is fading in over the top of, while it is crossfading
        self.outgoing: Optional[EventPortrait] = None

        # For moving
        self.moving = False
        self.orig_position = None
        self.next_position = None
        self.move_start = 0
        self.move_frames = 0
        self.move_long = False
        self.move_dip = 0  # Pixels the face sinks by while it moves

        # For talking
        self.talk_state = 0
        self.last_talk_update = 0
        self.next_talk_update = 0
        self.reverse = False

        # For blinking
        self.blink_counter = counters.FaceBlinkCounter(self.portrait.blink_frames, engine.get_time())

        # For bop
        self.bops_remaining = 0
        self.bop_state = False
        self.bop_height = 2
        self.last_bop = None

        # For saturation
        self.saturation = 1.
        self.saturation_direction = 0

    def get_size(self):
        return self.portrait.face_size

    def get_width(self):
        return self.portrait.face_size[0]

    def get_height(self):
        return self.portrait.face_size[1]

    def set_expression(self, expression_list):
        self.expressions = set(expression_list)

    def saturate(self):
        self.saturation_direction = 1

    def desaturate(self):
        self.saturation_direction = -1

    def crossfade_from(self, outgoing: EventPortrait):
        self.outgoing = outgoing
        self.transition = True
        self.transition_update = engine.get_time()

    def bop(self, num: int = 2, height: int = 2, speed: int = utils.frames2ms(8)):
        self.bop_time = speed
        self.bops_remaining = num
        self.bop_state = False
        self.bop_height = height
        self.last_bop = engine.get_time()

    def move(self, position, speed_mult=1):
        self.orig_position = self.position
        self.next_position = position
        self.moving = True
        self.travel_speed_mult = max(0.001, speed_mult)

        distance = max(abs(position[0] - self.position[0]), abs(position[1] - self.position[1]))
        self.move_long = move_frames(distance) > 16
        self.move_frames = max(1, int(round(move_frames(distance) / self.travel_speed_mult)))
        self.move_start = engine.get_time()
        self.move_dip = 0
        self.travel_time = utils.frames2ms(self.move_frames)

    def copy_movement(self, other: EventPortrait):
        """Carries on with the move another portrait is in the middle of"""
        for attr in ('moving', 'orig_position', 'next_position', 'travel_speed_mult', 'move_start',
                     'move_frames', 'move_long', 'move_dip', 'travel_time'):
            setattr(self, attr, getattr(other, attr))

    def quick_move(self, position):
        self.position = position

    def update_move(self, current_time):
        # Frames since the move began, to the nearest frame
        frame = int((current_time - self.move_start) * 60 / 1000 + 0.5)
        total = self.move_frames
        if frame >= total:
            self.position = self.next_position
            self.moving = False
            self.move_dip = 0
            return
        self.position = tuple(ease_out(start, end, frame, total)
                              for start, end in zip(self.orig_position, self.next_position))
        # It sinks a pixel on the way, as on the GBA: twice on a long move, once on a short
        if self.move_long:
            self.move_dip = 1 if total // 8 <= frame < total // 2 or total * 5 // 8 <= frame else 0
        else:
            self.move_dip = 1 if total // 2 <= frame else 0

    def start_talking(self):
        self.talk_on = True

    def stop_talking(self):
        self.talk_on = False

    def update_talk(self, current_time):
        # update mouth
        if self.talk_on and current_time - self.last_talk_update > self.next_talk_update:
            self.last_talk_update = current_time
            self.talk_state, self.next_talk_update, self.reverse = \
                update_talk(self.talk_state, self.portrait.mouth_frames, self.reverse)
        if not self.talk_on:
            self.talk_state = 0
            self.reverse = False

    def create_image(self):
        main_image = self.main_portrait.copy()
        # For smile image
        if "OpenMouth" in self.expressions:
            idx = self.portrait.mouth_frames-1
        else:
            idx = self.talk_state
            for expression in self.expressions:
                if expression.startswith('MouthFrame'):
                    # `expression` should be a str of format 'MouthFrameX' where X is a non-negative integer,
                    #  so get X using string slice at 10th index `expression[10:]`
                    idx = int(expression[10:])
                    break
        mouth_image = engine.subsurface(self.portrait.image,
            self.portrait.get_mouth_frame(idx, smile="Smile" in self.expressions))

        # For blink image.
        blink_image: Optional[engine.Surface] = None
        idx = None
        if "CloseEyes" in self.expressions:
            idx = 0
        elif "HalfCloseEyes" in self.expressions:
            idx = self.portrait.blink_frames // 2
        elif "OpenEyes" in self.expressions:
            idx = None
        else:
            if not self.blink_counter.is_open_eyes():
                idx = self.blink_counter.get_blink_index()
            for expression in self.expressions:
                if expression.startswith('BlinkFrame'):
                    # `expression` should be a str of format 'BlinkFrameX' where X is a non-negative integer,
                    #  so get X using string slice at 10th index `expression[10:]`
                    idx = int(expression[10:])
                    break
        if idx is not None:
            blink_image = engine.subsurface(self.portrait.image, self.portrait.get_blink_frame(idx))
        
        # For wink image.
        wink_image: Optional[engine.Surface] = None
        left_wink = None
        if "LeftWink" in self.expressions or "FarWink" in self.expressions:
            left_wink = True
        elif "RightWink" in self.expressions or "NearWink" in self.expressions:
            left_wink = False
        if left_wink is not None:
            wink_image = engine.subsurface(self.portrait.image, self.portrait.get_wink(left_wink))

        # Piece together image
        if blink_image:
            main_image.blit(blink_image, self.portrait.get_blink_coord())
            
        if wink_image:
            main_image.blit(wink_image, self.portrait.get_wink_coord(left_wink))
            
        main_image.blit(mouth_image, self.portrait.get_mouth_coord())
        
        return main_image

    def update(self) -> bool:
        current_time = engine.get_time()
        delta_time = engine.get_delta()
        self.update_talk(current_time)
        self.blink_counter.update(current_time)

        if self.saturation_direction != 0:
            self.saturation += self.saturation_direction * delta_time / self.saturation_time
            self.saturation = utils.clamp(self.saturation, 0, 1)
            # If reached one of the two extremes
            if self.saturation == 0 or self.saturation == 1:
                self.saturation_direction = 0

        if self.transition:
            # 14 frames for unit face to appear
            perc = (current_time - self.transition_update) / self.transition_speed
            if self.remove:
                perc = 1 - perc
            self.transition_progress = perc
            if perc > 1 or perc < 0:
                self.transition = False
                self.outgoing = None
                self.transition_progress = utils.clamp(perc, 0, 1)
                if self.remove:
                    return True

        if self.moving:
            self.update_move(current_time)

        if self.bops_remaining:
            if current_time - self.last_bop > self.bop_time:
                self.last_bop += self.bop_time
                if self.bop_state:
                    self.bops_remaining -= 1
                self.bop_state = not self.bop_state

        return False

    def get_image(self):
        """The portrait as it appears once it has finished transitioning"""
        image = self.create_image()
        if self.mirror:
            image = engine.flip_horiz(image)

        if self.saturation < 1:
            blackness = 0.5 * (1 - self.saturation)
            image = image_mods.make_black_colorkey(image, blackness)
        return image

    def draw(self, surf):
        image = self.get_image()

        if self.transition:
            if self.outgoing:
                image = image_mods.make_translucent(image.convert_alpha(), 1 - self.transition_progress)
            elif self.slide:
                image = image_mods.make_translucent(image.convert_alpha(), 1 - self.transition_progress)
            else:
                image = image_mods.make_black_colorkey(image, 1 - self.transition_progress)

        position = self.position

        slide_length = 24
        if self.slide == 'right':
            position = position[0] + slide_length - int(slide_length * self.transition_progress), self.position[1]
        elif self.slide == 'left':
            position = position[0] - slide_length + int(slide_length * self.transition_progress), self.position[1]

        if self.bop_state:
            position = position[0], position[1] + self.bop_height
        position = position[0], position[1] + self.move_dip

        if self.outgoing:
            surf.blit(self.outgoing.get_image(), position)
        surf.blit(image, position)

    def end(self, speed_mult=1, slide: Optional[str] = None):
        self.outgoing = None
        self.transition = True
        self.remove = True
        if slide:  # Use the existing slide if not specified
            self.slide = slide
        self.transition_speed = self.base_transition_speed * max(speed_mult, 0.001)
        self.transition_update = engine.get_time()
