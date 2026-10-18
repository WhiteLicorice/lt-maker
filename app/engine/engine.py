import sys
from typing import Tuple, TypeAlias
from enum import Enum

import pygame
import pygame.image
import pygame.time
try:
    from pygame._sdl2 import controller
except ImportError:
    # The browser build of pygame-ce has no game controller module, so there
    # every pad is a raw joystick
    controller = None

from app.constants import WINWIDTH, WINHEIGHT, FPS
from app.engine import config as cf
from app.utilities import utils

import logging

constants = {'current_time': 0,
             'last_time': 0,
             'input_time': 0,
             'delta_t': 0,
             'standalone': True,
             'running': True}

fast_quit = False

# === engine functions ===
def init():
    pygame.mixer.pre_init(44100, -16, 2, 128 * 2**cf.SETTINGS['sound_buffer_size'])
    pygame.init()
    pygame.font.init()
    # pygame.init does not start the game controller subsystem
    if controller:
        controller.init()
    logging.info("Engine Init Completed")

def simple_init():
    pygame.init()

def set_icon(icon):
    pygame.display.set_icon(icon)

def set_title(text):
    pygame.display.set_caption(text)

def build_display(size):
    try:
        if cf.SETTINGS['fullscreen']:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            return pygame.display.set_mode(size, pygame.RESIZABLE)
    except pygame.error as e:
        logging.exception(e)
        logging.error(
            "Display creation failed. Falling back to windowed resizable mode."
        )
        return pygame.display.set_mode(size, pygame.RESIZABLE)
    
def get_screen_size():
    return pygame.display.get_surface().get_size()

def push_display(surf, size, new_surf):
    win_w, win_h = size
    base_w, base_h = surf.get_size()

    # Calculate current aspect ratio
    scale = min(win_w / base_w, win_h / base_h)

    # Calculate new size with scale factor
    new_w = int(base_w * scale)
    new_h = int(base_h * scale)

    scaled_surf = pygame.transform.scale(surf, (new_w, new_h))

    # Center view
    x = (win_w - new_w) // 2
    y = (win_h - new_h) // 2

    # Render scaled surface
    new_surf.blit(scaled_surf, (x, y))

def update_display():
    pygame.display.update()

def remove_display():
    pygame.display.quit()

def terminate(crash=False):
    on_end(crash)
    # A rumble with no duration keeps going after the game closes
    stop_rumble()
    if pygame.mixer.get_init():
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    pygame.quit()
    if constants['standalone']:
        sys.exit()

def on_end(crash=False):
    cf.save_settings()

# === timing functions ===
# Game time moves on one frame each update, however long the computer took
# over it, so everything timed in milliseconds keeps pace with everything
# counted in frames. driver.MainLoop decides how many updates a frame of real time gets
FRAME_MS = 1000 / FPS
_frames = 0

def update_time(held_buttons_too: bool = True):
    # All measured in milliseconds. Whole milliseconds, a frame of 16 or 17
    global _frames
    _frames += 1
    constants['last_time'] = constants['current_time']
    constants['delta_t'] = round(_frames * FRAME_MS) - round((_frames - 1) * FRAME_MS)
    constants['current_time'] += constants['delta_t']
    if held_buttons_too:
        constants['input_time'] += constants['delta_t']

def get_time() -> int:
    return constants['current_time']

def get_input_time() -> int:
    """
    The clock held buttons repeat by. Game time, but for the updates a sped-up
    game runs on top of one a frame, so a held button repeats on the same frames
    at any game speed
    """
    return constants['input_time']

def get_last_time():
    return constants['last_time']

def get_true_time():
    return pygame.time.get_ticks()

def get_delta():
    return constants['delta_t']

# === drawing functions ===
BLEND_RGB_ADD = pygame.BLEND_RGB_ADD
BLEND_RGB_SUB = pygame.BLEND_RGB_SUB
BLEND_RGB_MULT = pygame.BLEND_RGB_MULT
BLEND_RGB_MIN = pygame.BLEND_RGB_MIN
BLEND_RGBA_ADD = pygame.BLEND_RGBA_ADD
BLEND_RGBA_SUB = pygame.BLEND_RGBA_SUB
BLEND_RGBA_MULT = pygame.BLEND_RGBA_MULT

class BlendMode(Enum):
    NONE = 0
    BLEND_RGB_ADD = 1
    BLEND_RGB_SUB = 2
    BLEND_RGB_MULT = 3

    @staticmethod
    def convert(blendmode):
        if blendmode == BlendMode.BLEND_RGB_ADD:
            return pygame.BLEND_RGB_ADD
        elif blendmode == BlendMode.BLEND_RGB_SUB:
            return pygame.BLEND_RGB_SUB
        elif blendmode == BlendMode.BLEND_RGB_MULT:
            return pygame.BLEND_RGB_MULT
        return 0

Surface: TypeAlias = pygame.Surface

def blit(dest, source, pos=(0, 0), mask=None, blend=0):
    dest.blit(source, pos, mask, blend)

def blit_center(dest, source, pos=(WINWIDTH//2, WINHEIGHT//2), mask=None, blend=0):
    x = pos[0] - source.get_width()//2
    y = pos[1] - source.get_height()//2
    dest.blit(source, (x, y), mask, blend)

def create_surface(size, transparent=False) -> pygame.Surface:
    if transparent:
        surf = pygame.Surface(size, pygame.SRCALPHA, 32)
        surf = surf.convert_alpha()
    else:
        surf = pygame.Surface(size)
        surf = surf.convert()
    return surf

def create_simple_surface(size) -> pygame.Surface:
    return pygame.Surface(size)

def copy_surface(surf):
    return surf.copy()

def save_surface(surf, fn):
    pygame.image.save(surf, fn)

_empty_surf: Surface = None
def empty_surf() -> Surface:
    global _empty_surf
    if not _empty_surf:
        _empty_surf = create_surface((0, 0), True)
    return _empty_surf

def bound_subsurface(surf_size: Tuple[int, int], rect: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    surf_width, surf_height = surf_size
    lx, ly, width, height = rect
    rx = lx + width
    ry = ly + height
    # sanity clamp
    lx = utils.clamp(lx, 0, surf_width)
    ly = utils.clamp(ly, 0, surf_height)
    rx = utils.clamp(rx, 0, surf_width)
    ry = utils.clamp(ry, 0, surf_height)
    if rx < lx:
        rx, lx = lx, rx
    if ry < ly:
        ry, ly = ly, ry
    return lx, ly, rx - lx, ry - ly

def subsurface(surf: Surface, rect: Tuple[int, int, int, int]) -> Surface:
    rect = bound_subsurface(surf.get_size(), rect)
    _, _, twidth, theight = rect
    if twidth == 0 or theight == 0:
        return empty_surf()
    return surf.subsurface(rect)

def blit_layer_view(dest: Surface, layer: Surface, content: pygame.Rect, view: Tuple[int, int, int, int]):
    """
    Blits the part of a map-sized layer that the view (the camera's rect on the
    map) shows onto dest, but only where the layer has anything drawn: content
    is layer.get_bounding_rect(), taken when the layer was drawn. A
    see-through layer costs as much to blit as it is large, however little is
    in it, and in the browser a full screen of per-pixel alpha takes most of a
    millisecond
    """
    shown = content.clip(pygame.Rect(view))
    if shown.width and shown.height:
        dest.blit(layer, (shown.x - view[0], shown.y - view[1]), shown)

def image_load(fn, convert=False, convert_alpha=False):
    image = pygame.image.load(fn)
    if convert:
        image = image.convert()
    elif convert_alpha:
        image = image.convert_alpha()
    return image

def surf_to_raw(surf: pygame.Surface, format: str) -> str:
    """Converts a given surface into a raw byte representation.

    Args:
        surf (pygame.Surface): surf to convert
        format (str): any valid format string (https://www.pygame.org/docs/ref/image.html#pygame.image.tobytes)

    Returns:
        str: raw byte buffer version of surf
    """
    return pygame.image.tobytes(surf, format)

def raw_to_surf(raw_bytes: str, size: Tuple[int, int], format: str) -> pygame.Surface:
    """converts a raw image string into a surface.

    Args:
        raw_bytes (str): raw data
        size (Tuple[int, int]): size of surface to be created
        format (str): the format string that was used to encode the raw data
            (https://www.pygame.org/docs/ref/image.html#pygame.image.tobytes)

    Returns:
        pygame.Surface: the surface consisting of the raw image
    """
    return pygame.image.frombytes(raw_bytes, size, format)

def fill(surf, color, mask=None, blend=0):
    surf.fill(color, mask, blend)

def set_alpha(surf, alpha, rleaccel=False):
    if rleaccel:
        surf.set_alpha(alpha, pygame.RLEACCEL)
    else:
        surf.set_alpha(alpha)

def set_colorkey(surf, color, rleaccel=True):
    if rleaccel:
        surf.set_colorkey(color, pygame.RLEACCEL)
    else:
        surf.set_colorkey(color)

def make_pixel_array(surf):
    return pygame.PixelArray(surf)

def draw_line(surf, color, start, end, width=1):
    return pygame.draw.line(surf, color, start, end, width)

# === transform functions ===
def flip_horiz(surf):
    return pygame.transform.flip(surf, 1, 0)

def flip_vert(surf):
    return pygame.transform.flip(surf, 0, 1)

def transform_scale(surf, scale):
    return pygame.transform.scale(surf, scale)

def transform_rotate(surf, degrees):
    return pygame.transform.rotate(surf, degrees)

# === event functions ===
def get_key_name(key_code):
    return pygame.key.name(key_code)

key_map = {"enter": pygame.K_RETURN,
           "tab": pygame.K_TAB,
           "backspace": pygame.K_BACKSPACE,
           "pageup": pygame.K_PAGEUP,
           "f12": pygame.K_F12,
           "`": pygame.K_BACKQUOTE,
           "1": pygame.K_1,
           "2": pygame.K_2,
           "3": pygame.K_3,
           "4": pygame.K_4,
           "5": pygame.K_5,
           }

events = []

def clear_events():
    """
    Forgets the frame's events, for the updates a sped-up game runs after the
    first, so a key typed once is read once. The list get_events gave keeps them
    """
    global events
    events = []

def get_events():
    global events, fast_quit
    events.clear()
    if fast_quit:
        fast_quit = False  # Reset so this doesn't persist
        terminate()
        return pygame.QUIT
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            terminate()
            return pygame.QUIT
        if event.type == pygame.KEYDOWN and cf.SETTINGS['debug']:
            if event.key == pygame.K_ESCAPE:
                terminate()
                return pygame.QUIT
        events.append(event)
    return events

# === controls functions ===
QUIT = pygame.QUIT
KEYUP = pygame.KEYUP
KEYDOWN = pygame.KEYDOWN
MOUSEBUTTONDOWN = pygame.MOUSEBUTTONDOWN
MOUSEBUTTONUP = pygame.MOUSEBUTTONUP
MOUSEMOTION = pygame.MOUSEMOTION
JOYDEVICEADDED = pygame.JOYDEVICEADDED
JOYDEVICEREMOVED = pygame.JOYDEVICEREMOVED

def get_pressed():
    return pygame.key.get_pressed()

def get_gamepads() -> tuple[list['controller.Controller'], list[pygame.joystick.JoystickType]]:
    """
    Returns every connected pad, split into those SDL recognizes as
    game controllers and raw joysticks it does not.
    """
    controllers, joysticks = [], []
    if not pygame.joystick.get_init() or (controller and not controller.get_init()):
        return controllers, joysticks
    for idx in range(pygame.joystick.get_count()):
        if controller and controller.is_controller(idx):
            controllers.append(controller.Controller(idx))
        else:
            joystick = pygame.joystick.Joystick(idx)
            joystick.init()
            joysticks.append(joystick)
    return controllers, joysticks

def stop_rumble():
    controllers, joysticks = get_gamepads()
    for pad in controllers + joysticks:
        pad.stop_rumble()

def get_mouse_pos():
    return pygame.mouse.get_pos()

def get_mouse_focus():
    return pygame.mouse.get_focused()

# === loop functions ===
DISPLAYSURF: Surface = None

def get_screensize(init=False):
    global DISPLAYSURF
    if not DISPLAYSURF or init:
        return (WINWIDTH * min(cf.SETTINGS['screen_size'], 5), WINHEIGHT * min(cf.SETTINGS['screen_size'], 5))
    return (DISPLAYSURF.get_width(), DISPLAYSURF.get_height())

class Clock():
    def __init__(self) -> None:
        self.clock = pygame.time.Clock()

    def tick(self) -> int:
        return self.clock.tick(FPS)

    def measure(self) -> int:
        """Milliseconds since the last call, as tick, without waiting for the frame's time to be up"""
        return self.clock.tick()

# === System Messages

SYSTEM_FONT_SIZE = 14
def get_system_font():
    return pygame.font.Font(None, SYSTEM_FONT_SIZE)

def write_system_msg(surf, msg: str):
    """Writes a message to the screen.
    Use asterisks like **this** in order
    to emphasize a word.
    """
    fill(surf, (0, 0, 0))
    width = surf.get_width()
    font = get_system_font()
    x = 0
    y = 0
    lines = msg.splitlines()
    emphasis = False
    for line in lines:
        for word in line.split(' '):
            tmp = word
            if word.startswith('**'):
                emphasis = True
            tmp = word.strip('*')
            tmp += ' '
            wwidth = font.size(tmp)[0]
            if x + wwidth > width:
                x = 0
                y += SYSTEM_FONT_SIZE
            color = (0, 255, 0) if emphasis else (255, 255, 255) # green for emphasis
            wsurf = font.render(tmp, True, color)
            surf.blit(wsurf, (x, y))
            x += wwidth
            if word.endswith('**'):
                emphasis = False
        y += SYSTEM_FONT_SIZE
        x = 0
    return surf
