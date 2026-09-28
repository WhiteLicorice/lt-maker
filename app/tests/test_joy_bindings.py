import unittest

from app.engine import config as cf
from app.engine import engine
from app.engine import joy_bindings
from app.engine.input_manager import InputManager
from app.engine.joy_bindings import ControllerAxis, ControllerButton, JoyAxis, JoyButton, JoyHat


class FakeController():
    def __init__(self):
        self.buttons: set[int] = set()
        self.axes: dict[int, int] = {}

    def get_button(self, button: int) -> int:
        return int(button in self.buttons)

    def get_axis(self, axis: int) -> int:
        return self.axes.get(axis, 0)

class FakeJoystick():
    def __init__(self, num_buttons: int = 8, num_hats: int = 1, num_axes: int = 6):
        self.num_buttons = num_buttons
        self.num_hats = num_hats
        self.num_axes = num_axes
        self.buttons: set[int] = set()
        self.hats: dict[int, tuple[int, int]] = {}
        self.axes: dict[int, float] = {}

    def get_numbuttons(self) -> int:
        return self.num_buttons

    def get_button(self, button: int) -> bool:
        return button in self.buttons

    def get_numhats(self) -> int:
        return self.num_hats

    def get_hat(self, hat: int) -> tuple[int, int]:
        return self.hats.get(hat, (0, 0))

    def get_numaxes(self) -> int:
        return self.num_axes

    def get_axis(self, axis: int) -> float:
        return self.axes.get(axis, 0.)


class JoyBindingParseTests(unittest.TestCase):
    def test_parse_button_and_axis(self):
        self.assertEqual(joy_bindings.parse_binding('button:a'), ControllerButton('a'))
        self.assertEqual(joy_bindings.parse_binding('axis:triggerright+'), ControllerAxis('triggerright', 1))
        self.assertEqual(joy_bindings.parse_binding('axis:leftx-'), ControllerAxis('leftx', -1))

    def test_round_trip(self):
        text = 'button:x,button:rightshoulder,axis:triggerright+,axis:righty-'
        self.assertEqual(joy_bindings.serialize_bindings(joy_bindings.parse_bindings(text)), text)

    def test_malformed_bindings_raise(self):
        for text in ('', 'button:z', 'axis:leftx', 'axis:nope+', 'hat:0:up', 'a'):
            with self.assertRaises(ValueError, msg=text):
                joy_bindings.parse_bindings(text)

    def test_default_config_bindings_parse(self):
        defaults = cf.base_config()
        for action in joy_bindings.REBINDABLE_ACTIONS:
            joy_bindings.parse_bindings(defaults['joy_' + action])


class JoyBindingActiveTests(unittest.TestCase):
    def test_controller_axis_threshold(self):
        pad = FakeController()
        binding = ControllerAxis('lefty', -1)
        pad.axes[joy_bindings.CONTROLLER_AXES['lefty']] = -10000  # Under half
        self.assertFalse(binding.is_active(pad))
        pad.axes[joy_bindings.CONTROLLER_AXES['lefty']] = -30000
        self.assertTrue(binding.is_active(pad))
        # The other direction doesn't count
        pad.axes[joy_bindings.CONTROLLER_AXES['lefty']] = 30000
        self.assertFalse(binding.is_active(pad))

    def test_raw_bindings_ignore_missing_inputs(self):
        joystick = FakeJoystick(num_buttons=2, num_hats=0, num_axes=0)
        self.assertFalse(JoyButton(5).is_active(joystick))
        self.assertFalse(JoyHat(0, 1, 1).is_active(joystick))
        self.assertFalse(JoyAxis(2, 1).is_active(joystick))

    def test_raw_hat(self):
        joystick = FakeJoystick()
        joystick.hats[0] = (0, 1)
        self.assertTrue(JoyHat(0, 1, 1).is_active(joystick))
        self.assertFalse(JoyHat(0, 1, -1).is_active(joystick))
        self.assertFalse(JoyHat(0, 0, 1).is_active(joystick))


class InputManagerGamepadTests(unittest.TestCase):
    def setUp(self):
        self.old_settings = {k: v for k, v in cf.SETTINGS.items() if k.startswith(('joy_', 'key_'))}
        defaults = cf.base_config()
        for action in joy_bindings.REBINDABLE_ACTIONS:
            cf.SETTINGS['joy_' + action] = defaults['joy_' + action]
        self.manager = InputManager()
        self.pad = FakeController()
        self.manager.controllers = [self.pad]
        self.manager.joysticks = []

    def tearDown(self):
        cf.SETTINGS.update(self.old_settings)

    def poll(self):
        self.manager.key_up_events.clear()
        self.manager.key_down_events.clear()
        self.manager.handle_gamepads()

    def test_press_and_release_edges(self):
        self.pad.buttons.add(joy_bindings.CONTROLLER_BUTTONS['a'])
        self.poll()
        self.assertEqual(self.manager.key_down_events, ['SELECT'])
        self.assertTrue(self.manager.is_pressed('SELECT'))
        # Holding does not fire again
        self.poll()
        self.assertEqual(self.manager.key_down_events, [])
        self.pad.buttons.clear()
        self.poll()
        self.assertEqual(self.manager.key_up_events, ['SELECT'])
        self.assertFalse(self.manager.is_pressed('SELECT'))

    def test_action_held_until_all_its_bindings_release(self):
        x = joy_bindings.CONTROLLER_BUTTONS['x']
        rightshoulder = joy_bindings.CONTROLLER_BUTTONS['rightshoulder']
        self.pad.buttons.update({x, rightshoulder})
        self.poll()
        self.assertEqual(self.manager.key_down_events, ['INFO'])
        self.pad.buttons.discard(x)
        self.poll()
        self.assertTrue(self.manager.is_pressed('INFO'))
        self.assertEqual(self.manager.key_up_events, [])

    def test_rebinding_takes_effect_on_update(self):
        cf.SETTINGS['joy_SELECT'] = 'button:y'
        self.manager.update_joy_map()
        self.pad.buttons.add(joy_bindings.CONTROLLER_BUTTONS['a'])
        self.poll()
        self.assertNotIn('SELECT', self.manager.key_down_events)
        self.pad.buttons.add(joy_bindings.CONTROLLER_BUTTONS['y'])
        self.poll()
        self.assertIn('SELECT', self.manager.key_down_events)

    def test_left_stick_moves(self):
        self.pad.axes[joy_bindings.CONTROLLER_AXES['leftx']] = 32767
        self.poll()
        self.assertEqual(self.manager.key_down_events, ['RIGHT'])

    def test_unplugging_releases_held_buttons(self):
        self.pad.buttons.add(joy_bindings.CONTROLLER_BUTTONS['b'])
        self.poll()
        self.manager.controllers = []
        self.poll()
        self.assertEqual(self.manager.key_up_events, ['BACK'])

    def capture(self) -> bool:
        self.manager.key_down_events.clear()
        return self.manager.capture_controller_input()

    def test_capture_ignores_inputs_held_when_prompt_opened(self):
        a = joy_bindings.CONTROLLER_BUTTONS['a']
        # A opened the prompt and is still held
        self.pad.buttons.add(a)
        self.poll()
        self.manager.start_joymap_capture('SELECT')
        self.assertFalse(self.capture())
        self.pad.buttons.clear()
        self.assertFalse(self.capture())
        # Pressed again, it counts
        self.pad.buttons.add(a)
        self.assertTrue(self.capture())
        self.assertEqual(self.manager.captured_binding, ControllerButton('a'))

    def test_capture_unbound_input(self):
        self.manager.start_joymap_capture('SELECT')
        self.pad.axes[joy_bindings.CONTROLLER_AXES['righty']] = -30000
        self.assertTrue(self.capture())
        self.assertEqual(self.manager.captured_binding, ControllerAxis('righty', -1))

    def test_sole_binding_of_another_action_fires_it(self):
        self.manager.start_joymap_capture('SELECT')
        self.pad.buttons.add(joy_bindings.CONTROLLER_BUTTONS['b'])
        self.assertFalse(self.capture())
        self.assertEqual(self.manager.key_down_events, ['BACK'])

    def test_takes_binding_from_action_with_several(self):
        self.manager.start_joymap_capture('SELECT')
        self.pad.buttons.add(joy_bindings.CONTROLLER_BUTTONS['leftshoulder'])
        self.assertTrue(self.capture())
        self.manager.rebind_controller('SELECT', self.manager.captured_binding)
        self.assertEqual(cf.SETTINGS['joy_SELECT'], 'button:leftshoulder')
        self.assertEqual(cf.SETTINGS['joy_AUX'], 'axis:triggerleft+')

    def test_captured_input_does_not_fire_under_new_binding(self):
        self.manager.start_joymap_capture('SELECT')
        rightstick = joy_bindings.CONTROLLER_BUTTONS['rightstick']
        self.pad.buttons.add(rightstick)
        self.assertTrue(self.capture())
        self.manager.rebind_controller('SELECT', self.manager.captured_binding)
        self.manager.stop_joymap_capture()
        # Still held on the next frame
        self.poll()
        self.assertEqual(self.manager.key_down_events, [])
        self.assertTrue(self.manager.is_pressed('SELECT'))

    def test_directions_cannot_be_captured(self):
        self.manager.start_joymap_capture('SELECT')
        self.pad.buttons.add(joy_bindings.CONTROLLER_BUTTONS['dpup'])
        self.assertFalse(self.capture())
        self.assertEqual(self.manager.key_down_events, ['UP'])

    def test_reset_restores_default_bindings(self):
        cf.SETTINGS['joy_BACK'] = 'button:y'
        cf.reset_settings(['joy_BACK'])
        self.assertEqual(cf.SETTINGS['joy_BACK'], cf.base_config()['joy_BACK'])

    def test_button_name_follows_last_device(self):
        self.manager.last_input_device = 'keyboard'
        cf.SETTINGS['key_INFO'] = cf.convert_setting('key_INFO', 'K_c')
        self.manager.update_key_map()
        self.assertEqual(self.manager.get_button_name('INFO'), 'c')
        self.pad.buttons.add(joy_bindings.CONTROLLER_BUTTONS['b'])
        self.poll()
        self.assertEqual(self.manager.last_input_device, 'controller')
        # First of X / RB / RT
        self.assertEqual(self.manager.get_button_name('INFO'), 'X')

    def test_raw_joystick_uses_keyboard_names(self):
        joystick = FakeJoystick()
        self.manager.joysticks = [joystick]
        joystick.buttons.add(0)
        self.poll()
        self.assertEqual(self.manager.last_input_device, 'joystick')
        self.assertEqual(self.manager.get_button_name('SELECT'),
                         engine.get_key_name(cf.SETTINGS['key_SELECT']))

    def test_raw_joystick_fallback(self):
        joystick = FakeJoystick()
        self.manager.joysticks = [joystick]
        joystick.axes[2] = -0.9  # R2 on XInput-style pads
        self.poll()
        self.assertEqual(self.manager.key_down_events, ['INFO'])


if __name__ == '__main__':
    unittest.main()
