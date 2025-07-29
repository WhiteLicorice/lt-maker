from typing import List, Tuple

from app.constants import TILEHEIGHT, TILEWIDTH, WINHEIGHT, WINWIDTH
from app.data.database.database import DB
from app.engine import action, background, banner, base_surf
from app.engine import config as cf
from app.engine import (convoy_funcs, engine, gui, image_mods,
                        item_funcs, item_system, menus, text_funcs,
                        trade, skill_system)
from app.engine.fluid_scroll import FluidScroll
from app.engine.fonts import FONT
from app.engine.game_state import game
from app.engine.prep import PrepMainState, setup_units
from app.engine.sound import get_sound_thread
from app.engine.sprites import SPRITES
from app.engine.state import MapState, State
from app.events import triggers

import math

class PrepGBAMainState(State):
    name = 'prep_gba_main'
    bg = None
    menu = None

    def populate_options(self) -> Tuple[List[str], List[str], List[str], List[str]]:
        """
        return (options, ignore, events, info_descs), which should all be the same size
        """
        options = ['Pick Units', 'Items', 'Support', 'Check Map', 'Save']
        ignore = [True, False, True, False, False]
        events = [None] * len(options)
        info_descs = [text_funcs.translate("prep_gba_%s_desc" % option.replace(' ', '_').lower()) 
                        for option in options]

        # Don't manage units if there's nobody in the party!
        if game.get_units_in_party():
            if game.level_vars.get('_prep_pick'):
                ignore[0] = False
            if game.game_vars.get('_supports'):
                ignore[2] = False

        additional_options = game.game_vars.get('_prep_additional_options', [])
        additional_ignore = [not enabled for enabled in game.game_vars.get('_prep_options_enabled', [])]
        additional_events = game.game_vars.get('_prep_options_events', [])
        additional_descs = game.game_vars.get('_prep_options_info_descs', [])

        options = options[:-1] + additional_options + [options[-1]]
        ignore = ignore[:-1] + additional_ignore + [ignore[-1]]
        events = events[:-1] + additional_events + [events[-1]]
        info_descs = info_descs[:-1] + additional_descs + [info_descs[-1]]

        return options, ignore, events, info_descs

    def create_button_surfs(self):
        sprite = SPRITES.get('buttons')
        b_size = [(37, 9), (18, 13)]
        buttons = [sprite.subsurface(0, 165, *b_size[0]), sprite.subsurface(0, 82, *b_size[1])]

        font = FONT['text']
        commands = ['Fight!', 'Menu']
        commands = [text_funcs.translate(c) for c in commands]

        surfs = []
        for i in range(len(buttons)):
            pad_top = (16 - b_size[i][1]) // 2 + 1
            pad_left = b_size[i][0] + 4

            size = (pad_left + font.width(commands[i]) + 4, 16)
            surf = engine.create_surface(size, transparent=True)

            surf.blit(buttons[i], (0, pad_top))
            font.blit(commands[i], surf, (pad_left, 0))

            surfs.append(surf)
        return surfs

    def start(self):
        self.fluid = FluidScroll()

        prep_music = game.game_vars.get('_prep_music')
        if prep_music:
            get_sound_thread().fade_in(prep_music)

        options, ignore, events_on_options, info_descs = self.populate_options()
        self.events_on_option_select = events_on_options

        self.menu = menus.PrepGBA(options, info_descs, *game.memory.get('prep_gba_disp'))
        self.menu.set_ignore(ignore)

        self.button_surfs = self.create_button_surfs()

        self.bg = background.create_background('rune_background')
        game.memory['prep_bg'] = self.bg

        self.last_update = 0

        setup_units()
        game.state.change('transition_in')
        game.events.trigger(triggers.OnPrepStart())
        return 'repeat'

    def begin(self):
        self.fluid.reset_on_change_state()
        prep_music = game.game_vars.get('_prep_music')
        if prep_music:
            get_sound_thread().fade_in(prep_music)
        self.button_pressed = None

    def take_input(self, event):
        if self.last_update > 0:
            return

        self.button_pressed = event

        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            if self.menu.move_down(first_push):
                get_sound_thread().play_sfx('Select 6')
        elif 'UP' in directions:
            if self.menu.move_up(first_push):
                get_sound_thread().play_sfx('Select 6')

        elif event == 'SELECT':
            get_sound_thread().play_sfx('Select 1')
            selection = self.menu.get_current()
            if selection == 'Pick Units':
                game.memory['next_state'] = 'prep_pick_units'
                game.state.change('transition_to')
            elif selection == 'Items':
                game.memory['next_state'] = 'prep_manage'
                game.state.change('transition_to')
            elif selection == 'Support':
                game.memory['base_bg'] = self.bg
                game.memory['next_state'] = 'base_supports'
                game.state.change('transition_to')
            elif selection == 'Check Map':
                game.memory['next_state'] = 'prep_gba_map'
                game.state.change('transition_to')
            elif selection == 'Save':
                game.memory['save_kind'] = 'prep'
                game.memory['next_state'] = 'in_chapter_save'
                game.state.change('transition_to')
            else:
                option_index = self.menu.get_current_index()
                if self.events_on_option_select[option_index]:
                    event_to_trigger = self.events_on_option_select[option_index]
                    valid_events = DB.events.get_by_nid_or_name(event_to_trigger, game.level.nid)
                    for event_prefab in valid_events:
                        game.events.trigger_specific_event(event_prefab.nid)

        elif event == 'BACK':
            self.last_update = engine.get_time()

        elif event == 'START':
            if game.level_vars.get('_minimum_deployment', 0) > 0:
                if sum(bool(unit.position) for unit in game.get_units_in_party()) \
                        >= min(game.level_vars['_minimum_deployment'], len(game.get_units_in_party())):
                    get_sound_thread().play_sfx('Select 1')
                    self.last_update = engine.get_time()
                else:
                    get_sound_thread().play_sfx('Select 4')
                    if game.level_vars['_minimum_deployment'] == 1:
                        alert = banner.Custom("Must select at least 1 unit!")
                    else:
                        alert = banner.Custom("Must select at least %d units!" % game.level_vars['_minimum_deployment'])
                    game.alerts.append(alert)
                    game.state.change('alert')
            elif any(unit.position for unit in game.get_units_in_party()):
                get_sound_thread().play_sfx('Select 1')
                self.last_update = engine.get_time()
            else:
                get_sound_thread().play_sfx('Select 4')
                alert = banner.Custom("Must select at least one unit!")
                game.alerts.append(alert)
                game.state.change('alert')

    def update(self):
        self.menu.update()
        if self.last_update:
            if self.button_pressed == 'START' and engine.get_time() - self.last_update > 800:
                game.state.change('transition_pop')

            elif self.button_pressed == 'BACK' and engine.get_time() - self.last_update > 300:
                game.memory['next_state'] = 'prep_gba_map'
                game.state.change('transition_to')
                self.last_update = 0

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        self.menu.draw(surf)

        disp = self.button_surfs.copy()
        if self.last_update > 0:
            if self.button_pressed == 'START':
                idx = 0
            elif self.button_pressed == 'BACK':
                idx = 1
            else:
                return surf

            interval = 300   # ms
            progress = engine.get_time() % (interval*2)  # Between 0 and 600
            white = math.sin(progress / interval * math.pi)  # Returns between -1 and 1
            # Rescale to be between 0 and 1
            white = (white + 1) / 2
            
            disp[idx] = image_mods.make_white(disp[idx], white)

        for idx in range(len(disp)):
            surf.blit(disp[idx], (16 + 80 * idx, WINHEIGHT - 18))

        return surf    

class PrepGBAMapState(PrepMainState):
    name = 'prep_gba_map'

    def populate_options(self) -> Tuple[List[str], List[str], List[str]]:
        """return (options, ignore, events), which should all be the same size
        """
        options = ['Formation', 'Options', 'Save', 'Fight']
        if cf.SETTINGS['debug']:
            options.insert(0, 'Debug')
        ignore = [False for option in options]
        events = [None for option in options]
        return options, ignore, events

    def start(self):
        self._prep_start()

    def take_input(self, event):
        super().take_input(event)

        if self.fade_out:
            return

        if event == 'BACK':
            get_sound_thread().play_sfx('Select 4')
            game.state.change('transition_pop')

    def update(self):
        if self.fade_out:
            if engine.get_time() - self.last_update > 300:
                game.state.back()
                game.state.back()
        elif self.menu:
            self.menu.update()
