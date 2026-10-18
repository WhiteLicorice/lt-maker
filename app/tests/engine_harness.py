'''
Shared fixtures for engine tests

EngineTestCase gives every test the same clean starting point, whatever ran
before it in the suite: the headless SDL drivers, a display, freshly loaded
sprites, the default engine settings rather than the developer's own config,
and a freshly loaded project. Tests that use it can't pass or fail on what an
earlier test left behind in the global singletons.

EngineHarness drives the real engine one frame at a time, the way driver.run
does, but with a fake clock and scripted button presses. A test can play a
level through the real state machine instead of mocking the states:

    class MyTests(EngineTestCase):
        def test_something(self):
            harness = self.start_harness()
            harness.start_level('0')
            harness.run_until_state('free')
            harness.select_unit('Eirika')
            harness.move_cursor_to((5, 5))
            harness.press('SELECT')
            harness.run_until_state('menu')
            harness.choose('Wait')

Each frame goes through the same InputManager.process_input and
game.state.update calls as driver.run, so what a test presses is what a player
presses. move_unit / wait / attack / run_until_player_turn wrap the common
sequences.
'''
from __future__ import annotations

import os
import pickle
import unittest
from typing import Callable, Optional
from unittest.mock import patch

import pygame

from app.constants import FPS, WINHEIGHT, WINWIDTH
from app.data.database.database import DB
from app.data.resources.resources import RESOURCES
from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
from app.engine import action  # noqa: F401 -- import first, avoids a circular import, see test_menu_options
from app.engine import config as cf
from app.engine import engine, game_state, save
from app.engine import sprites
from app.engine.game_state import GameState
from app.engine.input_manager import get_input_manager
from app.engine.objects.item import ItemObject
from app.engine.objects.skill import SkillObject
from app.engine.sound import get_sound_thread
from app.engine.state_machine import StateMachine
from app.utilities.typing import NID, Pos

FRAME_MS = 1000 // FPS
# ItemObject.next_uid and SkillObject.next_uid in a fresh engine
FIRST_UID = 100

# Pinned so a test plays out the same on every machine. The rest of the
# settings come from config.base_config(), never the developer's config file
HARNESS_SETTINGS = {
    'random_seed': 0,
    # The cursor moves only for the keys a test presses
    'mouse': 0,
    # Map combat, which is quicker to step through than battle animations
    'animation': 'Never',
}

def _init_display():
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
    pygame.display.init()
    if not pygame.display.get_surface():
        pygame.display.set_mode((WINWIDTH, WINHEIGHT))

# Many engine modules read sprites into class or module attributes when first
# imported (menus.Trade.trade_name_surf, settings.config_icons, ...). A test
# that runs RESOURCES.load without reloading the sprites leaves them unloaded,
# and any state module first imported after that holds None for good. Test
# discovery imports this module before any test runs, while the sprites are
# loaded, so import every state module now. Some build surfaces at import,
# which needs a display
_init_display()
sprites.load_images()
StateMachine().load_states()
# One of the modules that needs the display to be imported
from app.engine.phase import PhaseIn  # noqa: E402

class EngineTestCase(unittest.TestCase):
    '''
    Resets the engine's global state before each test, and restores the
    settings after it. Set `project` to choose which project gets loaded
    '''
    project = 'testing_proj.ltproj'

    def setUp(self):
        _init_display()

        RESOURCES.load(self.project, CURRENT_SERIALIZATION_VERSION)
        DB.load(self.project, CURRENT_SERIALIZATION_VERSION)
        # RESOURCES.load resets the sprite dict to unloaded sprites (to pick up
        # the project's custom ones), and several engine modules read sprites
        # at import time, so images must be loaded after it
        sprites.load_images()

        self._old_settings = cf.SETTINGS.copy()
        cf.SETTINGS.clear()
        cf.SETTINGS.update({k: cf.convert_setting(k, v) for k, v in cf.base_config().items()})
        cf.SETTINGS.update(HARNESS_SETTINGS)
        get_input_manager().update()
        get_input_manager().reset_keys_pressed()

        game_state.game.clear()

    def tearDown(self):
        cf.SETTINGS.clear()
        cf.SETTINGS.update(self._old_settings)
        get_input_manager().update()

    def start_harness(self) -> EngineHarness:
        harness = EngineHarness()
        self.addCleanup(harness.close)
        return harness

_engine_started = False

def _start_engine():
    '''
    The parts of driver.start a headless test needs, done once per process.
    Fonts need a display mode, so this comes after EngineTestCase.setUp
    '''
    global _engine_started
    if not _engine_started:
        engine.init()
        from app.engine import fonts
        fonts.load_fonts()
        _engine_started = True
    from app.engine import battle_animation
    from app.engine.game_counters import ANIMATION_COUNTERS
    ANIMATION_COUNTERS.reset()
    battle_animation.battle_anim_registry.clear()

class EngineHarness():
    '''
    Runs the engine frame by frame with a fake clock. Exceptions from a state
    propagate straight to the test instead of reaching driver.run's crash screen.
    Get one from EngineTestCase.start_harness, which closes it after the test
    '''

    def __init__(self):
        _start_engine()
        self.surf = engine.create_surface((WINWIDTH, WINHEIGHT))
        self.input = get_input_manager()
        self.frame = 0
        # The engine reads the clock through engine.get_time; the AI also
        # checks get_true_time to spread its thinking across frames
        self._true_time_patch = patch.object(engine, 'get_true_time', engine.get_time)
        self._true_time_patch.start()
        # A phase starts as it does in the game, but its banner is over at once.
        # The banner plays for 87 frames at every change of phase, and drawing it
        # was a third of the time the tests that play a level took
        self._phase_banner_patch = patch.object(PhaseIn, 'update', return_value=True)
        self._phase_banner_patch.start()

    def close(self):
        self._true_time_patch.stop()
        self._phase_banner_patch.stop()

    @property
    def game(self) -> GameState:
        return game_state.game

    # === Starting ===
    def start_level(self, level_nid: NID) -> GameState:
        '''
        Test Chapter: what the editor does to play one level. Uids start over
        as in a fresh engine, so two runs of the same level match uid for uid
        '''
        ItemObject.next_uid = SkillObject.next_uid = FIRST_UID
        return game_state.start_level(level_nid)

    def load(self, s_dict: dict):
        '''
        Loads a save as the title screen's Load Game does (TitleLoadState),
        from a pickled copy, since a save on disk is a pickle
        '''
        game = self.game
        game.state.clear()
        game.state.process_temp_state()
        game.build_new()
        game.load(pickle.loads(pickle.dumps(s_dict)))
        save.set_next_uids(game)

    def round_trip(self) -> tuple[dict, dict]:
        '''Saves, loads that save, and saves again. Returns both saves'''
        before, _ = self.game.save()
        self.load(before)
        after, _ = self.game.save()
        return before, after

    # === Running ===
    def step(self, frames: int = 1, events: Optional[list] = None):
        '''Runs frames of driver.run's loop. events go to the first frame only'''
        for _ in range(frames):
            engine.constants['last_time'] = engine.constants['current_time']
            engine.constants['current_time'] += FRAME_MS
            engine.constants['input_time'] += FRAME_MS
            engine.constants['delta_t'] = FRAME_MS

            raw_events = events or []
            events = None
            event = self.input.process_input(raw_events)
            self.surf, repeat = self.game.state.update(event, self.surf)
            while repeat:
                self.surf, repeat = self.game.state.update([], self.surf)
            get_sound_thread().update(raw_events)

            self.game.playtime += FRAME_MS
            self.frame += 1

    def run_until(self, condition: Callable[[], bool], max_frames: int = 600, description: str = 'condition'):
        for _ in range(max_frames):
            if condition():
                return
            self.step()
        if not condition():
            raise AssertionError('%s not reached in %d frames; state stack is %s'
                                 % (description, max_frames, self.game.state.state_names()))

    def run_until_state(self, state_name: str, max_frames: int = 600):
        '''Runs until state_name is on top of the stack and nothing is waiting to change it'''
        self.run_until(lambda: self.state == state_name and not self.game.state.temp_state,
                       max_frames, "state '%s'" % state_name)

    @property
    def state(self) -> Optional[str]:
        return self.game.state.current()

    # === Input ===
    def _key_event(self, kind: int, button: str):
        return pygame.event.Event(kind, key=cf.SETTINGS['key_' + button])

    def press(self, button: str, settle: int = 1):
        '''Taps button: down on one frame, up on the next, then settle more frames'''
        self.step(events=[self._key_event(engine.KEYDOWN, button)])
        self.step(events=[self._key_event(engine.KEYUP, button)])
        self.step(settle)

    def move_cursor_to(self, pos: Pos, max_presses: int = 64):
        '''Taps the arrow keys until the cursor is on pos'''
        cursor = self.game.cursor
        for _ in range(max_presses):
            if cursor.position == tuple(pos):
                return
            x, y = cursor.position
            if x != pos[0]:
                self.press('RIGHT' if pos[0] > x else 'LEFT')
            else:
                self.press('DOWN' if pos[1] > y else 'UP')
            # Let the cursor finish sliding before the next tap
            self.run_until(lambda: cursor.offset_x == 0 and cursor.offset_y == 0, 60, 'cursor at rest')
        if cursor.position != tuple(pos):
            raise AssertionError('Cursor stuck at %s on the way to %s' % (cursor.position, pos))

    def select_unit(self, unit_nid: NID):
        '''From the free state, picks up a unit: its move preview comes up'''
        self.move_cursor_to(self.game.get_unit(unit_nid).position)
        self.press('SELECT')
        self.run_until_state('move')

    def choose(self, option, max_presses: int = 32):
        '''
        In the menu on top of the stack, moves down to the option whose value
        is option and selects it
        '''
        menu = self.game.state.current_state().menu
        for _ in range(max_presses):
            if menu.get_current() == option:
                self.press('SELECT')
                return
            self.press('DOWN')
        raise AssertionError('No option %r in %s' % (option, [opt.get() for opt in menu.options]))

    # === Turns ===
    def move_unit(self, unit_nid: NID, pos: Pos):
        '''Moves a unit to pos and stops at its action menu'''
        self.select_unit(unit_nid)
        self.move_cursor_to(pos)
        self.press('SELECT')
        self.run_until_state('menu')

    def wait(self, unit_nid: NID, pos: Pos):
        self.move_unit(unit_nid, pos)
        self.choose('Wait')

    def attack(self, unit_nid: NID, pos: Pos, max_frames: int = 3000):
        '''Moves a unit to pos and attacks the first target with its first weapon'''
        self.move_unit(unit_nid, pos)
        self.choose('Attack')
        self.run_until_state('weapon_choice')
        self.press('SELECT')
        self.run_until_state('combat_targeting')
        self.press('SELECT')
        self.run_until_state('free', max_frames)

    def end_turn(self):
        '''From the free state, ends the player's turn as End in the option menu does'''
        self.game.state.change('turn_change')
        self.game.state.change('status_endstep')
        self.game.state.change('ai')

    def run_until_player_turn(self, turn: int, max_frames: int = 6000):
        '''Runs through the other phases until the player can act on turn'''
        self.run_until(lambda: self.game.turncount == turn and self.state == 'free' and not self.game.state.temp_state,
                       max_frames, 'player phase of turn %d' % turn)

def diff_saves(before, after, path: str = '') -> list[str]:
    '''
    Every place two saves (or any nest of dicts, lists, tuples and sets)
    disagree, as a path into them and the two values
    '''
    if isinstance(before, dict) and isinstance(after, dict):
        differences = []
        for key in list(before) + [k for k in after if k not in before]:
            sub_path = '%s/%s' % (path, key)
            if key not in after:
                differences.append('%s: only before' % sub_path)
            elif key not in before:
                differences.append('%s: only after' % sub_path)
            else:
                differences += diff_saves(before[key], after[key], sub_path)
        return differences
    if isinstance(before, (list, tuple)) and isinstance(after, (list, tuple)) and len(before) == len(after):
        differences = []
        for idx, (b, a) in enumerate(zip(before, after)):
            differences += diff_saves(b, a, '%s/%d' % (path, idx))
        return differences
    if before != after:
        return ['%s: %r != %r' % (path or '/', before, after)]
    return []
