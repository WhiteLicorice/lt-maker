from app.constants import WINWIDTH, WINHEIGHT

from app.engine import config as cf
from app.engine.sprites import SPRITES
from app.engine.fonts import FONT
from app.engine.sound import get_sound_thread
from app.engine.input_manager import get_input_manager
from app.engine.state import State
from app.engine import engine, background, banner, menus, settings_menu, base_surf, text_funcs, joy_bindings
from app.engine.game_state import game
from app.engine.fluid_scroll import FluidScroll

controls = {'key_SELECT': engine.subsurface(SPRITES.get('buttons'), (0, 66, 14, 13)),
            'key_BACK': engine.subsurface(SPRITES.get('buttons'), (0, 82, 14, 13)),
            'key_INFO': engine.subsurface(SPRITES.get('buttons'), (1, 149, 16, 9)),
            'key_AUX': engine.subsurface(SPRITES.get('buttons'), (1, 133, 16, 9)),
            'key_START': engine.subsurface(SPRITES.get('buttons'), (0, 165, 33, 9)),
            'key_LEFT': engine.subsurface(SPRITES.get('buttons'), (1, 4, 13, 12)),
            'key_RIGHT': engine.subsurface(SPRITES.get('buttons'), (1, 19, 13, 12)),
            'key_DOWN': engine.subsurface(SPRITES.get('buttons'), (1, 34, 12, 13)),
            'key_UP': engine.subsurface(SPRITES.get('buttons'), (1, 50, 12, 13))}
control_order = ('key_SELECT', 'key_BACK', 'key_INFO', 'key_AUX', 'key_LEFT', 'key_RIGHT', 'key_UP', 'key_DOWN', 'key_START')

config = [('animation', ['Always', 'Your Turn', 'Combat Only', 'Never'], 0),
          ('screen_size', [1, 2, 3, 4, 5, 6], 18),
          ('display_fps', bool, 2),
          ('battle_bg', bool, 17),
          ('unit_speed', list(reversed(range(15, 180, 15))), 1),
          ('text_speed', cf.text_speed_options, 2),
          # ('cursor_speed', list(reversed(range(32, 160, 16))), 8),
          ('mouse', bool, 19),
          ('show_terrain', bool, 7),
          ('forecast', ['Strategic', 'Detailed', 'Off'], 10),
          ('show_objective', bool, 6),
          ('autocursor', bool, 13),
          ('hp_map_team', ['All', 'Ally', 'Enemy'], 10),
          ('hp_map_cull', ['None', 'Wounded', 'All'], 10),
          ('music_volume', [0, 0.01, 0.02, 0.03, 0.0625, 0.125, 0.25, 0.5, 1], 15),
          ('sound_volume', [0, 0.01, 0.02, 0.03, 0.0625, 0.125, 0.25, 0.5, 1], 16),
          ('talk_boop', bool, 16),
          ('show_bounds', bool, 7),
          ('grid_opacity', [int(255 * x / 10.0) for x in range(11)], 7),
          ('autoend_turn', bool, 14),
          ('confirm_end', bool, 14),
          ('display_hints', bool, 3),
          ('rumble', bool, 15)]

config_icons = [engine.subsurface(SPRITES.get('settings_icons'), (0, c[2] * 16, 16, 16)) for c in config]

joy_control_order = tuple('joy_' + action for action in joy_bindings.REBINDABLE_ACTIONS)
joy_fixed_controls = [('Move', 'D-Pad / L-Stick')]
joy_fixed_icons = [engine.subsurface(SPRITES.get('buttons'), (0, 192, 16, 16))]  # D-pad

tabs = ('config', 'keyboard', 'controller')
tab_names = {'config': 'Config', 'keyboard': 'Keyboard', 'controller': 'Controller'}

# The controls tabs show fewer rows than config to make room
# for the reset button beneath them
CONTROLS_LIMIT = 5
RESET_BUTTON_RECT = (64, 120, 112, 24)

def in_rect(position, rect) -> bool:
    x, y, width, height = rect
    return x <= position[0] <= x + width and y <= position[1] <= y + height

class SettingsMenuState(State):
    name = 'settings_menu'
    in_level = False
    header_width = 76

    def start(self):
        self.fluid = FluidScroll(128)
        self.bg = background.create_background('settings_background')
        self.tab = 'config'
        # top_menu, menu, reset_button, reset_confirm, get_input
        self.state = 'top_menu'

        config_options = [(c[0], c[1]) for c in config]
        self.config_menu = settings_menu.Config(None, config_options, 'menu_bg_base', config_icons)
        self.config_menu.takes_input = False

        keyboard_icons = [controls[c] for c in control_order]
        self.keyboard_menu = settings_menu.Controls(None, control_order, 'menu_bg_base', keyboard_icons)
        self.keyboard_menu.set_limit(CONTROLS_LIMIT)
        self.keyboard_menu.takes_input = False

        joy_icons = [controls['key_' + action] for action in joy_bindings.REBINDABLE_ACTIONS]
        self.controller_menu = settings_menu.JoyControls(
            None, joy_control_order, 'menu_bg_base', joy_icons, joy_fixed_controls, joy_fixed_icons)
        self.controller_menu.set_limit(CONTROLS_LIMIT)
        self.controller_menu.takes_input = False

        self.top_cursor = menus.Cursor()
        self.reset_cursor = menus.Cursor()

        self.confirm_menu = menus.Choice(None, ['Yes', 'No'], 'center', None)  # Clear background
        self.confirm_menu.set_horizontal(True)
        header = text_funcs.translate('Reset controls to defaults?')
        width = sum(option.width() + 8 for option in self.confirm_menu.options) + 16
        header_width = FONT['text'].width(header) + 8
        self.confirm_bg = base_surf.create_base_surf(max(width, header_width), 40)
        FONT['text'].blit(header, self.confirm_bg, (self.confirm_bg.get_width()//2 - header_width//2 + 4, 4))

        game.state.change('transition_in')
        return 'repeat'

    def begin(self):
        self.fluid.reset_on_change_state()

    @property
    def current_menu(self):
        return {'config': self.config_menu,
                'keyboard': self.keyboard_menu,
                'controller': self.controller_menu}[self.tab]

    def get_tab_center(self, tab) -> int:
        return WINWIDTH * (2 * tabs.index(tab) + 1) // (2 * len(tabs))

    def get_tab_rect(self, tab):
        return (self.get_tab_center(tab) - self.header_width//2, 4, self.header_width, 24)

    def handle_mouse(self):
        mouse_position = get_input_manager().get_mouse_position()
        if not mouse_position:
            return
        for tab in tabs:
            if in_rect(mouse_position, self.get_tab_rect(tab)):
                self.current_menu.takes_input = False
                self.tab = tab
                self.state = 'top_menu'
                return
        if self.tab != 'config' and in_rect(mouse_position, RESET_BUTTON_RECT):
            self.current_menu.takes_input = False
            self.state = 'reset_button'
            return
        current_idxs, current_option_rects = self.current_menu.get_rects()
        for idx, option_rect in zip(current_idxs, current_option_rects):
            if in_rect(mouse_position, option_rect) and not self.current_menu.options[idx].ignore:
                self.state = 'menu'
                self.current_menu.takes_input = True
                self.current_menu.move_to(idx)
                return

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        if self.state == 'get_input':
            if event == 'BACK':
                get_sound_thread().play_sfx('Select 4')
                self.end_get_input()
            elif event == 'NEW':
                get_sound_thread().play_sfx('Select 1')
                selection = self.current_menu.get_current()
                if self.tab == 'keyboard':
                    cf.SETTINGS[selection] = get_input_manager().unavailable_button
                    get_input_manager().update_key_map()
                else:
                    get_input_manager().rebind_controller(selection[len('joy_'):], get_input_manager().captured_binding)
                self.end_get_input()
            elif event:
                get_sound_thread().play_sfx('Select 4')
                self.end_get_input()
                self.alert('Invalid Choice!')

        elif self.state == 'reset_confirm':
            self.confirm_menu.handle_mouse()
            if event == 'RIGHT':
                if self.confirm_menu.move_down():
                    get_sound_thread().play_sfx('Select 6')
            elif event == 'LEFT':
                if self.confirm_menu.move_up():
                    get_sound_thread().play_sfx('Select 6')
            elif event == 'BACK':
                get_sound_thread().play_sfx('Select 4')
                self.state = 'reset_button'
            elif event == 'SELECT':
                if self.confirm_menu.get_current() == 'Yes':
                    get_sound_thread().play_sfx('Select 1')
                    self.reset_current_tab()
                else:
                    get_sound_thread().play_sfx('Select 4')
                self.state = 'reset_button'

        elif self.state == 'top_menu':
            self.handle_mouse()
            idx = tabs.index(self.tab)
            if event == 'DOWN' or event == 'SELECT':
                get_sound_thread().play_sfx('Select 6')
                self.state = 'menu'
                self.current_menu.takes_input = True
            elif event == 'LEFT':
                if idx > 0:
                    get_sound_thread().play_sfx('Select 6')
                    self.tab = tabs[idx - 1]
            elif event == 'RIGHT':
                if idx < len(tabs) - 1:
                    get_sound_thread().play_sfx('Select 6')
                    self.tab = tabs[idx + 1]
            elif event == 'BACK':
                self.back()

        elif self.state == 'reset_button':
            self.handle_mouse()
            if event == 'UP':
                get_sound_thread().play_sfx('Select 6')
                self.state = 'menu'
                self.current_menu.takes_input = True
            elif event == 'SELECT':
                get_sound_thread().play_sfx('Select 1')
                self.confirm_menu.set_selection('No')
                self.state = 'reset_confirm'
            elif event == 'BACK':
                self.back()

        else:
            self.handle_mouse()
            if 'DOWN' in directions:
                at_last_row = self.current_menu.get_current_option() is self.current_menu.get_last_option()
                if self.tab != 'config' and at_last_row:
                    if first_push:
                        get_sound_thread().play_sfx('Select 6')
                        self.current_menu.takes_input = False
                        self.state = 'reset_button'
                elif self.current_menu.move_down(first_push):
                    get_sound_thread().play_sfx('Select 6')
            elif 'UP' in directions:
                if self.current_menu.get_current_index() <= 0:
                    self.current_menu.takes_input = False
                    self.state = 'top_menu'
                    get_sound_thread().play_sfx('Select 6')
                else:
                    if self.current_menu.move_up(first_push):
                        get_sound_thread().play_sfx('Select 6')
            elif 'LEFT' in directions:
                did_change = self.current_menu.move_left()
                if did_change:
                    self.apply_option_change()
                    get_sound_thread().play_sfx('Select 6')
            elif 'RIGHT' in directions:
                did_change = self.current_menu.move_right()
                if did_change:
                    self.apply_option_change()
                    get_sound_thread().play_sfx('Select 6')

            elif event == 'BACK':
                self.back()

            elif event == 'SELECT':
                if self.tab == 'keyboard':
                    get_sound_thread().play_sfx('Select 1')
                    self.state = 'get_input'
                    get_input_manager().set_change_keymap(True)
                elif self.tab == 'controller':
                    if get_input_manager().controllers:
                        get_sound_thread().play_sfx('Select 1')
                        self.state = 'get_input'
                        get_input_manager().start_joymap_capture(self.current_menu.get_current()[len('joy_'):])
                    else:
                        get_sound_thread().play_sfx('Select 4')
                        self.alert('No controller detected!')
                else:
                    if self.current_menu.move_next():
                        self.apply_option_change()
                    get_sound_thread().play_sfx('Select 6')

    def alert(self, text):
        game.alerts.append(banner.Custom(text_funcs.translate(text)))
        game.state.change('alert')

    def end_get_input(self):
        self.state = 'menu'
        get_input_manager().set_change_keymap(False)
        get_input_manager().stop_joymap_capture()

    def reset_current_tab(self):
        if self.tab == 'keyboard':
            cf.reset_settings(control_order)
            get_input_manager().update_key_map()
        else:
            cf.reset_settings(joy_control_order)
            get_input_manager().update_joy_map()

    def apply_option_change(self):
        name = self.current_menu.get_current_option().name
        if name in ('music_volume', 'sound_volume'):
            self.update_sound()
        elif name == 'rumble':
            self.update_rumble()

    def back(self):
        get_sound_thread().play_sfx('Select 4')
        cf.save_settings()
        self.update_sound()
        # if game.cursor is not None:
        #     game.cursor.fluid.update_speed(cf.SETTINGS['cursor_speed'])
        game.state.change('transition_pop')

    def update_sound(self):
        get_sound_thread().set_music_volume(cf.SETTINGS['music_volume'])
        get_sound_thread().set_sfx_volume(cf.SETTINGS['sound_volume'])

    def update_rumble(self):
        if cf.SETTINGS['rumble']:
            # Lets the player feel that rumble is on
            get_input_manager().rumble(0.5, 0.5, 250)
        else:
            get_input_manager().stop_rumble()

    def update(self):
        self.current_menu.update()
        self.top_cursor.update()
        self.reset_cursor.update()
        if self.state == 'reset_confirm':
            self.confirm_menu.update()

    def draw_top_menu(self, surf):
        bg = base_surf.create_base_surf(self.header_width, 24, 'menu_bg_clear')
        for tab in tabs:
            x, y, _, _ = self.get_tab_rect(tab)
            surf.blit(bg, (x, y))
            center = self.get_tab_center(tab)
            name = text_funcs.translate(tab_names[tab])
            font = FONT['text-yellow'] if tab == self.tab else FONT['text-grey']
            font.blit_center(name, surf, (center, 8))
            if tab == self.tab and self.state == 'top_menu':
                self.top_cursor.draw(surf, center - font.width(name)//2 - 5, 8)

    def draw_reset_button(self, surf):
        x, y, width, height = RESET_BUTTON_RECT
        surf.blit(base_surf.create_base_surf(width, height, 'menu_bg_green'), (x, y))
        text = text_funcs.translate('Reset to Defaults')
        focused = self.state in ('reset_button', 'reset_confirm')
        font = FONT['text-yellow'] if focused else FONT['text']
        font.blit_center(text, surf, (x + width//2, y + 4))
        if focused:
            self.reset_cursor.draw(surf, x + width//2 - font.width(text)//2 - 5, y + 4)

    def draw_confirm(self, surf):
        surf.blit(self.confirm_bg, (WINWIDTH//2 - self.confirm_bg.get_width()//2, WINHEIGHT//2 - 28))
        self.confirm_menu.draw(surf)

    def draw_info_banner(self, surf):
        height = 16
        bg = base_surf.create_base_surf(WINWIDTH + 16, height, 'menu_bg_clear')
        surf.blit(bg, (-8, WINHEIGHT - height))
        if self.state in ('reset_button', 'reset_confirm'):
            text = 'Restore the default bindings.'
        elif self.state == 'get_input':
            if self.tab == 'keyboard':
                text = 'get_input_desc'
            else:
                text = 'Press a new button (or BACK to quit)'
        elif self.tab == 'config':
            if self.state == 'top_menu':
                text = 'config_desc'
            else:
                idx = self.config_menu.get_current_index()
                text = config[idx][0] + '_desc'
        elif self.tab == 'keyboard':
            text = 'keymap_desc'
        else:
            text = 'Change controller bindings.'
        text = text_funcs.translate(text)
        FONT['text'].blit_center(text, surf, (WINWIDTH//2, WINHEIGHT - height))

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        else:
            # settings menu shouldn't be transparent
            surf.blit(SPRITES.get('bg_black'), (0, 0))

        self.draw_top_menu(surf)
        if self.state == 'get_input':
            self.current_menu.draw(surf, True)
        else:
            self.current_menu.draw(surf)
        if self.tab != 'config':
            self.draw_reset_button(surf)
        self.draw_info_banner(surf)
        if self.state == 'reset_confirm':
            self.draw_confirm(surf)

        return surf

    def finish(self):
        # Just to make sure!
        get_input_manager().set_change_keymap(False)
        get_input_manager().stop_joymap_capture()
