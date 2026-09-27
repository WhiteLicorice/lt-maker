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
    if talk_state == 0 or talk_state == max_state-1:
        reverse = not reverse
    elif random.randint(1, 10) == 1:  # 10% chance to reverse
        reverse = not reverse

    mt = 2 if random.randint(1, 10) == 1 else 1    # 10% chance to skip a frame
    if reverse:
        next_state = talk_state - mt
    else:
        next_state = talk_state + mt
    next_state = utils.clamp(next_state, 0, max_state-1)

    if next_state == 0:
        next_update = random.randint(50, 100)
    elif next_state == max_state-1:
        next_update = random.randint(70, 160)
    else:
        next_update = random.randint(30, 50)

    return next_state, next_update, reverse

class EventPortrait():
    base_transition_speed = utils.frames2ms(14)
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
        self.transition_speed = self.base_transition_speed * max(speed_mult, 0.001)
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

        # For moving
        self.moving = False
        self.orig_position = None
        self.next_position = None

        # For talking
        self.talk_state = 0
        self.last_talk_update = 0
        self.next_talk_update = 0
        self.reverse = False

        # For blinking
        # Blinking set up
        self.offset_blinking = [x for x in range(-2000, 2000, 125)]
        # 3 frames for each
        self.blink_counter = counters.BlinkCounter(self.portrait.blink_frames,
            [7000 + random.choice(self.offset_blinking), utils.frames2ms(3)])

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

        self.travel_time = self.determine_travel_time(utils.distance(self.next_position, self.orig_position))
        self.travel_time = int(self.travel_time / speed_mult)

    def quick_move(self, position):
        self.position = position

    def determine_travel_time(self, distance):
        counter = 0
        while distance > 0:
            counter += 1
            change = int(round(distance / 8))
            change = utils.clamp(change, 1, 8)
            distance -= change
        return utils.frames2ms(counter)

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
            idx = self.portrait.blink_frames - 1
        elif "HalfCloseEyes" in self.expressions:
            idx = self.portrait.blink_frames // 2 - 1
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
                self.transition_progress = utils.clamp(perc, 0, 1)
                if self.remove:
                    return True

        if self.moving:
            distance = utils.distance(self.next_position, self.position)
            if distance == 0:
                self.position = self.next_position
                self.moving = False
                self.bop_state = False
                # self.bop(num=1, height=1)
            else:
                # The below does not actually contain the CORRECT true-to-GBA algorithm
                # Just a close simple approximation, because I could not determine the GBA algorithm perfectly
                # 15 frames (250 ms) to lerp 24 pixels
                # 30 frames (500 ms) to lerp 120 pixels
                # 45 frames? (750 ms) to lerp 264 pixels
                travel_mag = int(round(distance / 8))
                travel_mag = utils.clamp(travel_mag, 1, 8)
                if travel_mag in (1, 4, 5, 6, 7):
                    self.bop_state = True
                    self.bop_height = 1
                # Multiply by travel speed
                travel_mag = min(self.travel_speed_mult * travel_mag, distance)
                diff_x = self.next_position[0] - self.position[0]
                diff_y = self.next_position[1] - self.position[1]
                angle = math.atan2(diff_y, diff_x)
                updated_position = (self.position[0] + (travel_mag * math.cos(angle)),
                                    self.position[1] + (travel_mag * math.sin(angle)))
                # updated_position = (self.position[0] + (travel_mag * direction), self.position[1])
                self.position = updated_position

        if self.bops_remaining:
            if current_time - self.last_bop > self.bop_time:
                self.last_bop += self.bop_time
                if self.bop_state:
                    self.bops_remaining -= 1
                self.bop_state = not self.bop_state

        return False

    def draw(self, surf):
        image = self.create_image()
        if self.mirror:
            image = engine.flip_horiz(image)

        if self.saturation < 1:
            blackness = 0.5 * (1 - self.saturation)
            image = image_mods.make_black_colorkey(image, blackness)

        if self.transition:
            if self.slide:
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

        surf.blit(image, position)

    def end(self, speed_mult=1, slide: Optional[str] = None):
        self.transition = True
        self.remove = True
        if slide:  # Use the existing slide if not specified
            self.slide = slide
        self.transition_speed = self.base_transition_speed * max(speed_mult, 0.001)
        self.transition_update = engine.get_time()
