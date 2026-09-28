"""
Gamepad bindings for the input manager.

Pads that SDL recognizes as game controllers use the standardized
controller layout (``button:a`` is the bottom face button on every pad),
so their action bindings are user-configurable and stored in config.ini
as comma separated strings, e.g. ``joy_INFO=button:x,axis:triggerright+``.
Their directions are fixed to the D-pad and left stick.

Pads SDL does not recognize fall back to a fixed raw joystick layout.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, Union

import pygame

# How far an axis must be pushed (as a fraction of its range) to count as pressed
AXIS_THRESHOLD = 0.5
# Controller axes report raw SDL values in [-32768, 32767]
CONTROLLER_AXIS_MAX = 32768

REBINDABLE_ACTIONS = ('SELECT', 'BACK', 'INFO', 'AUX', 'START')

CONTROLLER_BUTTONS: dict[str, int] = {
    'a': pygame.CONTROLLER_BUTTON_A,
    'b': pygame.CONTROLLER_BUTTON_B,
    'x': pygame.CONTROLLER_BUTTON_X,
    'y': pygame.CONTROLLER_BUTTON_Y,
    'back': pygame.CONTROLLER_BUTTON_BACK,
    'guide': pygame.CONTROLLER_BUTTON_GUIDE,
    'start': pygame.CONTROLLER_BUTTON_START,
    'leftstick': pygame.CONTROLLER_BUTTON_LEFTSTICK,
    'rightstick': pygame.CONTROLLER_BUTTON_RIGHTSTICK,
    'leftshoulder': pygame.CONTROLLER_BUTTON_LEFTSHOULDER,
    'rightshoulder': pygame.CONTROLLER_BUTTON_RIGHTSHOULDER,
    'dpup': pygame.CONTROLLER_BUTTON_DPAD_UP,
    'dpdown': pygame.CONTROLLER_BUTTON_DPAD_DOWN,
    'dpleft': pygame.CONTROLLER_BUTTON_DPAD_LEFT,
    'dpright': pygame.CONTROLLER_BUTTON_DPAD_RIGHT,
}

CONTROLLER_AXES: dict[str, int] = {
    'leftx': pygame.CONTROLLER_AXIS_LEFTX,
    'lefty': pygame.CONTROLLER_AXIS_LEFTY,
    'rightx': pygame.CONTROLLER_AXIS_RIGHTX,
    'righty': pygame.CONTROLLER_AXIS_RIGHTY,
    'triggerleft': pygame.CONTROLLER_AXIS_TRIGGERLEFT,
    'triggerright': pygame.CONTROLLER_AXIS_TRIGGERRIGHT,
}

BUTTON_DISPLAY_NAMES: dict[str, str] = {
    'a': 'A', 'b': 'B', 'x': 'X', 'y': 'Y',
    'back': 'Back', 'guide': 'Guide', 'start': 'Start',
    'leftstick': 'LS', 'rightstick': 'RS',
    'leftshoulder': 'LB', 'rightshoulder': 'RB',
    'dpup': 'D-Up', 'dpdown': 'D-Down', 'dpleft': 'D-Left', 'dpright': 'D-Right',
}

AXIS_DISPLAY_NAMES: dict[tuple[str, int], str] = {
    ('leftx', -1): 'LS Left', ('leftx', 1): 'LS Right',
    ('lefty', -1): 'LS Up', ('lefty', 1): 'LS Down',
    ('rightx', -1): 'RS Left', ('rightx', 1): 'RS Right',
    ('righty', -1): 'RS Up', ('righty', 1): 'RS Down',
    ('triggerleft', 1): 'LT', ('triggerright', 1): 'RT',
}

class ControllerDevice(Protocol):
    def get_button(self, button: int) -> int: ...
    def get_axis(self, axis: int) -> int: ...

class JoystickDevice(Protocol):
    def get_numbuttons(self) -> int: ...
    def get_button(self, button: int) -> bool: ...
    def get_numhats(self) -> int: ...
    def get_hat(self, hat: int) -> tuple[int, int]: ...
    def get_numaxes(self) -> int: ...
    def get_axis(self, axis: int) -> float: ...

@dataclass(frozen=True)
class ControllerButton:
    name: str

    def is_active(self, controller: ControllerDevice) -> bool:
        return bool(controller.get_button(CONTROLLER_BUTTONS[self.name]))

    def serialize(self) -> str:
        return 'button:%s' % self.name

    def display_name(self) -> str:
        return BUTTON_DISPLAY_NAMES[self.name]

@dataclass(frozen=True)
class ControllerAxis:
    name: str
    sign: int  # 1 or -1: which direction along the axis counts as pressed

    def is_active(self, controller: ControllerDevice) -> bool:
        amount = controller.get_axis(CONTROLLER_AXES[self.name]) / CONTROLLER_AXIS_MAX
        return amount * self.sign > AXIS_THRESHOLD

    def serialize(self) -> str:
        return 'axis:%s%s' % (self.name, '+' if self.sign > 0 else '-')

    def display_name(self) -> str:
        return AXIS_DISPLAY_NAMES[(self.name, self.sign)]

ControllerBinding = Union[ControllerButton, ControllerAxis]

def parse_binding(text: str) -> ControllerBinding:
    kind, _, name = text.strip().partition(':')
    if kind == 'button' and name in CONTROLLER_BUTTONS:
        return ControllerButton(name)
    if kind == 'axis' and name[:-1] in CONTROLLER_AXES and name[-1:] in ('+', '-'):
        return ControllerAxis(name[:-1], 1 if name[-1] == '+' else -1)
    raise ValueError("Unknown controller binding: %s" % text)

def parse_bindings(text: str) -> list[ControllerBinding]:
    return [parse_binding(part) for part in text.split(',')]

def serialize_bindings(bindings: Sequence[ControllerBinding]) -> str:
    return ','.join(binding.serialize() for binding in bindings)

def display_bindings(bindings: Sequence[ControllerBinding]) -> str:
    return ' / '.join(binding.display_name() for binding in bindings)

# Every input the rebind prompt listens for, in priority order when several
# are pressed on the same frame. Guide is left out since the OS often claims it,
# and triggers only travel in the positive direction.
CAPTURE_CANDIDATES: tuple[ControllerBinding, ...] = (
    *(ControllerButton(name) for name in CONTROLLER_BUTTONS if name != 'guide'),
    *(ControllerAxis(name, sign) for name, sign in AXIS_DISPLAY_NAMES),
)

CONTROLLER_DIRECTIONS: dict[str, tuple[ControllerBinding, ...]] = {
    'LEFT': (ControllerButton('dpleft'), ControllerAxis('leftx', -1)),
    'RIGHT': (ControllerButton('dpright'), ControllerAxis('leftx', 1)),
    'UP': (ControllerButton('dpup'), ControllerAxis('lefty', -1)),
    'DOWN': (ControllerButton('dpdown'), ControllerAxis('lefty', 1)),
}

@dataclass(frozen=True)
class JoyButton:
    index: int

    def is_active(self, joystick: JoystickDevice) -> bool:
        return joystick.get_numbuttons() > self.index and bool(joystick.get_button(self.index))

@dataclass(frozen=True)
class JoyHat:
    index: int
    axis: int  # 0 for x, 1 for y
    value: int

    def is_active(self, joystick: JoystickDevice) -> bool:
        return joystick.get_numhats() > self.index and joystick.get_hat(self.index)[self.axis] == self.value

@dataclass(frozen=True)
class JoyAxis:
    index: int
    sign: int

    def is_active(self, joystick: JoystickDevice) -> bool:
        return joystick.get_numaxes() > self.index and joystick.get_axis(self.index) * self.sign > AXIS_THRESHOLD

JoystickBinding = Union[JoyButton, JoyHat, JoyAxis]

# Fixed layout for pads SDL does not recognize, assuming XInput-style indices
RAW_JOYSTICK_BINDINGS: dict[str, tuple[JoystickBinding, ...]] = {
    'SELECT': (JoyButton(0),),  # A
    'BACK': (JoyButton(1),),  # B
    'START': (JoyButton(3), JoyButton(6), JoyButton(7)),  # Y, Select, Start
    'INFO': (JoyButton(2), JoyButton(5), JoyAxis(2, -1)),  # X, RB, R2
    'AUX': (JoyButton(4), JoyAxis(2, 1)),  # LB, L2
    'LEFT': (JoyHat(0, 0, -1), JoyAxis(0, -1)),
    'RIGHT': (JoyHat(0, 0, 1), JoyAxis(0, 1)),
    'UP': (JoyHat(0, 1, 1), JoyAxis(1, -1)),
    'DOWN': (JoyHat(0, 1, -1), JoyAxis(1, 1)),
}
