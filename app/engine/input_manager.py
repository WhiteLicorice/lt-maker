from __future__ import annotations

from typing import Sequence

from app.constants import WINWIDTH, WINHEIGHT
from app.engine import engine
from app.engine import config as cf
from app.engine import joy_bindings

class InputManager():
    def __init__(self):
        self.refresh_gamepads()

        self.buttons = ('UP', 'DOWN', 'LEFT', 'RIGHT', 'SELECT', 'BACK', 'INFO', 'AUX', 'START', 'SPEED')
        self.directions = ('UP', 'DOWN', 'LEFT', 'RIGHT')
        self.toggle_buttons = ('SELECT', 'BACK', 'INFO', 'AUX', 'START')  # These buttons cause state to change
        # SPEED changes how fast the whole game runs (see driver.run), so it is
        # never an event for a state

        self.update_key_map()

        # Build and down button checker
        self.keys_pressed = {}
        self.joys_pressed = {}
        self.reset_keys_pressed()

        self.update_joy_map()

        self.key_up_events = []
        self.key_down_events = []
        self.change_keymap_mode = False
        self.current_mouse_position = None

        self.unavailable_button = None

        # Controller rebinding: the action being rebound, if any. Inputs held
        # when the prompt opened must be released and pressed again to count
        self.capture_action: str | None = None

        # Which kind of device last pressed a button: keyboard, controller or joystick.
        # Button prompts name the button on this device
        self.last_input_device = 'keyboard'
        self.capture_baseline: set[joy_bindings.ControllerBinding] = set()
        self.captured_binding: joy_bindings.ControllerBinding | None = None

    def refresh_gamepads(self):
        self.controllers, self.joysticks = engine.get_gamepads()
        for pad in self.controllers:
            print("Game Controller: %s" % pad.name)
        for pad in self.joysticks:
            print("Joystick: %s" % pad.get_name())

    def rumble(self, low_frequency: float, high_frequency: float, duration: int):
        """
        Rumbles every connected pad for duration ms, or until stop_rumble if 0.
        low_frequency drives the heavy motor and high_frequency the light one,
        each from 0 to 1. Does nothing if the player turned rumble off
        """
        if not cf.SETTINGS['rumble']:
            return
        for pad in self.controllers + self.joysticks:
            pad.rumble(low_frequency, high_frequency, duration)

    def stop_rumble(self):
        for pad in self.controllers + self.joysticks:
            pad.stop_rumble()

    def set_change_keymap(self, val):
        self.change_keymap_mode = val

    def start_joymap_capture(self, action: str):
        self.capture_action = action
        self.capture_baseline = self.get_active_capture_inputs()

    def stop_joymap_capture(self):
        self.capture_action = None
        # Absorb whatever is still held (like the button just captured)
        # so it doesn't fire under its new binding next frame
        for button in self.buttons:
            self.joys_pressed[button] = self.is_gamepad_pushed(button)

    def rebind_controller(self, action: str, binding: joy_bindings.ControllerBinding):
        """
        Makes binding the only controller input for action,
        taking it away from any other action that had it
        """
        for other in joy_bindings.REBINDABLE_ACTIONS:
            bindings = joy_bindings.parse_bindings(cf.SETTINGS['joy_' + other])
            if other != action and binding in bindings:
                bindings.remove(binding)
                cf.SETTINGS['joy_' + other] = joy_bindings.serialize_bindings(bindings)
        cf.SETTINGS['joy_' + action] = binding.serialize()
        self.update_joy_map()

    def reset_keys_pressed(self):
        for button in self.buttons:
            self.keys_pressed[button] = False
            self.joys_pressed[button] = False

    def is_pressed(self, button):
        return self.keys_pressed[button] or self.joys_pressed[button]

    def just_pressed(self, button):
        return button in self.key_down_events
    
    def directional_input_pressed(self):
        directional_inputs = ('UP', 'DOWN', 'LEFT', 'RIGHT')
        return any([input_pressed for input_pressed in directional_inputs if self.is_pressed(input_pressed)])

    def _raw_to_game_coords(self, raw_pos: tuple[int, int]) -> tuple[int, int]:
        """Unifies conversion of raw OS pixel coordinates to game coordinates,
        accounting for letterbox scaling and offset introduced by
        modifications to `engine.push_display`.
        """
        win_w, win_h = engine.get_screen_size()
        base_w, base_h = WINWIDTH, WINHEIGHT

        scale = min(win_w / base_w, win_h / base_h)
        offset_x = (win_w - int(base_w * scale)) // 2
        offset_y = (win_h - int(base_h * scale)) // 2

        mx = max(0, min(base_w - 1, int((raw_pos[0] - offset_x) / scale)))
        my = max(0, min(base_h - 1, int((raw_pos[1] - offset_y) / scale)))
        return mx, my

    def get_mouse_position(self) -> tuple[int, int] | None:
        if self.current_mouse_position:
            return self._raw_to_game_coords(self.current_mouse_position)
        return None

    def get_real_mouse_position(self) -> tuple[int, int] | None:
        """
        Works whether or not mouse has been moved recently.
        """
        if not cf.SETTINGS['mouse']:
            return None
        mouse_pos = engine.get_mouse_pos()
        if not mouse_pos or not engine.get_mouse_focus():
            return None
        return self._raw_to_game_coords(mouse_pos)

    def get_mouse_pos_with_scaled_surf(self) -> tuple[int, int] | None:
        """
        Return mouse coordinates mapped to the game surface.
        """
        mouse_pos = engine.get_mouse_pos()
        if not mouse_pos or not engine.get_mouse_focus():
            return None
        return self._raw_to_game_coords(mouse_pos)

    def update(self):
        self.update_key_map()
        self.update_joy_map()

    def update_key_map(self):
        self.key_map = {}
        self.key_map['UP'] = cf.SETTINGS['key_UP']
        self.key_map['LEFT'] = cf.SETTINGS['key_LEFT']
        self.key_map['RIGHT'] = cf.SETTINGS['key_RIGHT']
        self.key_map['DOWN'] = cf.SETTINGS['key_DOWN']
        self.key_map['SELECT'] = cf.SETTINGS['key_SELECT']
        self.key_map['START'] = cf.SETTINGS['key_START']
        self.key_map['BACK'] = cf.SETTINGS['key_BACK']
        self.key_map['AUX'] = cf.SETTINGS['key_AUX']
        self.key_map['INFO'] = cf.SETTINGS['key_INFO']
        self.key_map['SPEED'] = cf.SETTINGS['key_SPEED']

        self.map_keys = {v: k for k, v in self.key_map.items()}

    def update_joy_map(self):
        self.controller_map: dict[str, Sequence[joy_bindings.ControllerBinding]] = {}
        for button in joy_bindings.REBINDABLE_ACTIONS:
            self.controller_map[button] = joy_bindings.parse_bindings(cf.SETTINGS['joy_' + button])
        self.controller_map.update(joy_bindings.CONTROLLER_DIRECTIONS)

    def clear_events(self):
        """Forgets the buttons just pressed and released. Held buttons stay held"""
        self.key_up_events.clear()
        self.key_down_events.clear()

    def process_input(self, events):
        self.clear_events()

        # Check keyboard
        for event in events:
            if event.type == engine.KEYUP or event.type == engine.KEYDOWN:
                button = self.map_keys.get(event.key)
                key_up = event.type == engine.KEYUP

                if button:
                    # Update keys pressed
                    self.keys_pressed[button] = not key_up
                    if key_up:
                        self.key_up_events.append(button)
                    else:
                        self.key_down_events.append(button)
                        self.last_input_device = 'keyboard'
                elif self.change_keymap_mode and event.type == engine.KEYDOWN:
                    self.unavailable_button = event.key
                    return 'NEW'

        # Check mouse
        if not self.change_keymap_mode and not self.capture_action and cf.SETTINGS['mouse']:
            self.current_mouse_position = None
            for event in events:
                if event.type == engine.MOUSEBUTTONDOWN:
                    lmb = event.button == 1
                    if lmb:
                        self.key_down_events.append('SELECT')
                    rmb = event.button == 3
                    if rmb:
                        self.key_down_events.append('BACK')
                    mmb = event.button == 2
                    if mmb:
                        self.key_down_events.append('INFO')
                    wheel_up = event.button == 4
                    wheel_down = event.button == 5
                    if wheel_up:
                        self.key_down_events.append('UP')
                    else:
                        self.key_up_events.append('UP')
                    if wheel_down:
                        self.key_down_events.append('DOWN')
                    else:
                        self.key_up_events.append('DOWN')
                    position = event.pos
                    self.current_mouse_position = position
                elif event.type == engine.MOUSEMOTION:
                    position = event.pos
                    self.current_mouse_position = position

        # Check game pads
        # SDL also reports every already-connected pad as added when it
        # starts, which covers re-opening the engine from the editor
        if any(event.type in (engine.JOYDEVICEADDED, engine.JOYDEVICEREMOVED) for event in events):
            self.refresh_gamepads()

        if self.capture_action:
            if self.capture_controller_input():
                return 'NEW'
        else:
            # Still read pads while rebinding a key, so a pad can back out
            self.handle_gamepads()

        # Return the correct event for this frame
        # Gives priority to later inputs
        # Remove reversed to give priority to earlier inputs
        for button in reversed(self.key_down_events):
            if button in self.toggle_buttons:
                return button
        # If only arrow keys pressed, return last one pressed
        for button in reversed(self.key_down_events):
            if button in self.directions:
                return button

    def is_controller_pushed(self, button: str) -> bool:
        return any(binding.is_active(pad)
                   for pad in self.controllers
                   for binding in self.controller_map[button])

    def is_joystick_pushed(self, button: str) -> bool:
        return any(binding.is_active(pad)
                   for pad in self.joysticks
                   for binding in joy_bindings.RAW_JOYSTICK_BINDINGS[button])

    def is_gamepad_pushed(self, button: str) -> bool:
        return self.is_controller_pushed(button) or self.is_joystick_pushed(button)

    def handle_gamepads(self):
        for button in self.buttons:
            controller_pushed = self.is_controller_pushed(button)
            pushed = controller_pushed or self.is_joystick_pushed(button)
            if pushed != self.joys_pressed[button]:
                self.joys_pressed[button] = pushed
                if pushed:
                    self.key_down_events.append(button)
                    self.last_input_device = 'controller' if controller_pushed else 'joystick'
                else:
                    self.key_up_events.append(button)

    def get_button_name(self, button: str) -> str:
        """
        Name of the input for button on the device last used. Raw joysticks
        have no standard button names, so they get the keyboard's
        """
        if self.last_input_device == 'controller':
            # Only the first binding, since prompts have little room
            return self.controller_map[button][0].display_name()
        return engine.get_key_name(self.key_map[button])

    def get_active_capture_inputs(self) -> set[joy_bindings.ControllerBinding]:
        return {binding for pad in self.controllers
                for binding in joy_bindings.CAPTURE_CANDIDATES if binding.is_active(pad)}

    def capture_controller_input(self) -> bool:
        """
        Returns True and sets captured_binding if a new controller input
        was pressed that can be moved to capture_action: one that is unbound,
        already capture_action's, or one of several bound to another action.
        Otherwise the input fires the action it is bound to, like an already
        bound key does in keymap mode.
        """
        active = self.get_active_capture_inputs()
        self.capture_baseline &= active
        new_inputs = active - self.capture_baseline
        if not new_inputs:
            return False
        binding = next(b for b in joy_bindings.CAPTURE_CANDIDATES if b in new_inputs)
        self.capture_baseline.add(binding)
        for button, bindings in self.controller_map.items():
            if binding in bindings:
                rebindable = button in joy_bindings.REBINDABLE_ACTIONS
                if not rebindable or (button != self.capture_action and len(bindings) == 1):
                    self.key_down_events.append(button)
                    return False
        self.captured_binding = binding
        return True

INPUT: InputManager = None
def get_input_manager() -> InputManager:
    global INPUT
    if not INPUT:
        INPUT = InputManager()
    return INPUT
