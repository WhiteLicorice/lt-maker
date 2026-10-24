import asyncio
import logging
import math
import os
import collections
from datetime import datetime
import time
from app import lt_log
from app.data.database.database import DB
from app.utilities import file_utils, utils

from app.constants import WINWIDTH, WINHEIGHT, VERSION, FPS
from app.engine import engine
from app.engine.utils import garbage

import app.engine.config as cf

_profile = "LT_PROFILE" in os.environ
_default_profile_threshold = 0
_profile_threshold = _default_profile_threshold
if "LT_PROFILE_THRESHOLD" in os.environ:
    try:
        _profile_threshold = float(os.environ["LT_PROFILE_THRESHOLD"])
    except ValueError:
        _profile = False
        print(f'could not parse {os.environ["LT_PROFILE_THRESHOLD"]} as float')
# Prints a summary of frame times every FRAME_STATS_WINDOW frames
_frame_stats = "LT_FRAME_STATS" in os.environ
FRAME_STATS_WINDOW = 120

def start(title, from_editor=False):
    if from_editor:
        engine.constants['standalone'] = False
    engine.init()
    icon = engine.image_load('favicon.ico')
    engine.set_icon(icon)

    # Hack to get icon to show up in windows
    try:
        import ctypes
        myappid = u'rainlash.lextalionis.ltmaker.current' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        print("Maybe not Windows? (but that's OK)")

    engine.DISPLAYSURF = engine.build_display(engine.get_screensize(True))

    # After the display is built, to convert the images to its pixel format
    from app.engine import sprites
    sprites.load_images()

    from app.engine import game_counters
    # Reset the animation counters for a new engine start
    # otherwise, the animation counters would be at a large number instead of 0
    # if you already started the engine this session
    game_counters.ANIMATION_COUNTERS.reset()

    from app.engine import battle_animation
    # Clear out old battle animations that we might have tested with earlier,
    # because they could have changed.
    battle_animation.battle_anim_registry.clear()

    # must happen after pygame.display.set_mode
    # is called in engine.build_display
    from app.engine import fonts
    fonts.load_fonts()

    # The project's data is loaded by now, and lasts the whole session
    garbage.settle()

    engine.update_time()
    engine.set_title(title + ' - v' + VERSION)
    print("Version: %s" % VERSION)

screenshot = False
def save_screenshot(raw_events: list, surf):
    global screenshot
    for e in raw_events:
        if e.type == engine.KEYDOWN and e.key == engine.key_map['`']:
            screenshot = True
            if not os.path.isdir('screenshots'):
                os.mkdir('screenshots')
        elif e.type == engine.KEYUP and e.key == engine.key_map['`']:
            screenshot = False
        elif e.type == engine.KEYDOWN and e.key == engine.key_map['f12']:
            if not os.path.isdir('screenshots'):
                os.mkdir('screenshots')
            current_time = str(datetime.now()).replace(' ', '_').replace(':', '.')
            engine.save_surface(surf, 'screenshots/LT_%s.png' % current_time)
    if screenshot:
        current_time = str(datetime.now()).replace(' ', '_').replace(':', '.')
        engine.save_surface(surf, 'screenshots/LT_%s.bmp' % current_time)

def draw_fps(surf, fps_records):
    from app.engine.fonts import FONT
    total_time = sum(fps_records)
    if total_time > 0:
        num_frames = len(fps_records)
        fps = int(num_frames / (total_time / 1000))
        max_frame = max(fps_records)
        min_fps = 1000 // max_frame
    else:  # On the very first frame, can't figure out what the FPS is yet.
        fps, min_fps = "--", "--"

    FONT['small-white'].blit(str(fps), surf, (surf.get_width() - 20, 0))
    FONT['small-white'].blit(str(min_fps), surf, (surf.get_width() - 20, 12))

def draw_soft_reset(surf, remaining_time: int):
    from app.engine.fonts import FONT
    FONT['chapter-yellow'].blit(str(remaining_time), surf, (surf.get_width()//2 - 4, surf.get_height()//2 - 4))

# Updates a frame may run to catch up when the last frame took too long, so the
# game keeps its speed down to 30 frames a second. Each update draws as well, so
# a frame catches up only when that many updates fit in a frame. If updating is
# what takes too long, more updates only make each frame slower still
MAX_CATCH_UP = 2
MAX_GAME_SPEED = 4

def update_game_speed(inp, game_speed: int) -> int:
    """The SPEED button steps the game's speed through x1 to x4, if the game allows it"""
    if not DB.constants.value('speed_up'):
        return 1
    if inp.just_pressed('SPEED'):
        return game_speed % MAX_GAME_SPEED + 1
    return game_speed

def plan_updates(behind: float, update_ms: float, game_speed: int) -> tuple[int, float]:
    """
    How many updates this frame runs, given the real time not yet run as game
    time and how long one update took last frame, and the time still behind after
    them. Sped up, the game runs that many updates a frame and never catches up,
    so a computer that cannot keep up runs it as fast as it can instead
    """
    if game_speed > 1:
        return game_speed, 0
    max_updates = MAX_CATCH_UP if update_ms * MAX_CATCH_UP <= engine.FRAME_MS else 1
    num_updates = utils.clamp(int(behind // engine.FRAME_MS), 1, max_updates)
    behind = utils.clamp(behind - num_updates * engine.FRAME_MS, -engine.FRAME_MS, engine.FRAME_MS)
    return num_updates, behind

def draw_game_speed(surf, game_speed: int):
    from app.engine.fonts import FONT
    FONT['small-white'].blit('x%d' % game_speed, surf, (2, 0))

def check_soft_reset(game, inp) -> bool:
    return game.state.current() != 'title_start' and \
        inp.is_pressed('SELECT') and inp.is_pressed('BACK') and \
        inp.is_pressed('START')

class MainLoop():
    """
    The engine's main loop, one frame per call to run_frame. The desktop runs
    frames back to back (run); the browser build must hand control back to the
    page after every frame (run_async)
    """
    SOFT_RESET_TIME = 3  # seconds

    def __init__(self, game, wait_out_frame: bool):
        """wait_out_frame: whether run_frame holds the thread until the frame's
        time is up, holding the engine to FPS. Otherwise the caller paces it"""
        from app.engine.sound import get_sound_thread
        from app.engine.game_counters import ANIMATION_COUNTERS
        from app.engine.input_manager import get_input_manager

        self.game = game
        self.wait_out_frame = wait_out_frame
        ANIMATION_COUNTERS.reset()

        get_sound_thread().reset()
        get_sound_thread().set_music_volume(cf.SETTINGS['music_volume'])
        get_sound_thread().set_sfx_volume(cf.SETTINGS['sound_volume'])

        self.surf = engine.create_surface((WINWIDTH, WINHEIGHT))
        self.clock = engine.Clock()
        self.fps_records = collections.deque(maxlen=FPS)
        self.inp = get_input_manager()

        self._error_mode = False
        self._error_msg = ''
        self._soft_reset_start_time: int = None  # UTC time.time()

        self.game_speed = 1
        # Real time not yet run as game time, in milliseconds. Below zero when the
        # game is ahead of the clock. It starts a frame behind, for the first frame's
        # update, which runs before any time has been measured
        self.behind = engine.FRAME_MS
        # How long one update took last frame, in milliseconds
        self.update_ms = 0

        # For LT_FRAME_STATS: each frame's milliseconds updating and presenting
        self._stats_update_ms: list[float] = []
        self._stats_present_ms: list[float] = []
        self._stats_start = time.perf_counter()

    def run_frame(self) -> bool:
        """Runs one frame. Returns False once the player quits"""
        from app.engine.sound import get_sound_thread
        game, inp = self.game, self.inp

        start = time.perf_counter_ns()

        raw_events = engine.get_events()

        if raw_events == engine.QUIT:
            return False

        event = inp.process_input(raw_events)

        self.game_speed = update_game_speed(inp, self.game_speed)
        num_updates, self.behind = plan_updates(self.behind, self.update_ms, self.game_speed)

        # Handle soft reset
        if check_soft_reset(game, inp):
            # Set the start time if not already set
            if not self._soft_reset_start_time:
                self._soft_reset_start_time = time.time()
            if time.time() - self.SOFT_RESET_TIME >= self._soft_reset_start_time:
                self._soft_reset_start_time = None
                self._error_mode = False
                game.memory.clear()
                # Drop the stack instead of stacking the title screen on top of it,
                # and apply that here rather than through update(). Updating runs the
                # state underneath one last time, and its transitions queue up behind
                # ours: a move finishing mid-reset calls back() and pops the title
                # straight off again, leaving the game running with memory wiped,
                # while a clear() takes the title with it and empties the stack.
                game.state.clear()
                game.state.change('title_start')
                game.state.process_temp_state()
                return True
        else:
            self._soft_reset_start_time = None

        # game loop. catch and log any errors in this loop.
        if self._error_mode:
            self.surf = engine.write_system_msg(self.surf, self._error_msg)
            if inp.is_pressed('SELECT') or inp.is_pressed('BACK'):
                log_file = lt_log.get_log_fname()
                if log_file:
                    file_utils.startfile(log_file)
        else:
            try:
                updates_start = time.perf_counter()
                for update in range(num_updates):
                    engine.update_time(held_buttons_too=self.game_speed == 1 or update == 0)
                    # The frame's presses go to its first update only
                    if update > 0:
                        inp.clear_events()
                        engine.clear_events()
                        event = None
                    self.surf, repeat = game.state.update(event, self.surf)
                    while repeat:  # Let's the game traverse through state chains
                        # print("Repeating States:\t", game.state.state)
                        self.surf, repeat = game.state.update([], self.surf)
                    # print("States:\t\t\t", game.state.state)
                self.update_ms = (time.perf_counter() - updates_start) * 1000 / num_updates

                if cf.SETTINGS['display_fps']:
                    draw_fps(self.surf, self.fps_records)
                if self.game_speed > 1:
                    draw_game_speed(self.surf, self.game_speed)
                if self._soft_reset_start_time:
                    draw_soft_reset(self.surf, math.ceil(self.SOFT_RESET_TIME - (time.time() - self._soft_reset_start_time)))
            except Exception as e:
                logging.exception("Game crashed with exception.")
                log_file_loc = lt_log.get_log_dir() or ''
                self._error_msg = "Game crashed with exception:\n%s\nPlease press either the **SELECT** or **BACK** keys to open the log file. Please send the contents of the log file to the game developer to resolve this issue.\nLogs can be found in **%s**" % (str(e).strip(), str(log_file_loc))
                self._error_mode = True
                # If we're in editor/debug mode, just throw the error normally
                if cf.SETTINGS['debug']:
                    raise e

        get_sound_thread().update(raw_events)
        updated = time.perf_counter_ns()

        engine.push_display(self.surf, engine.get_screensize(), engine.DISPLAYSURF)

        save_screenshot(raw_events, self.surf)

        engine.update_display()

        end = time.perf_counter_ns()
        ms_elapsed = (end - start) / 1e6
        if _profile and ms_elapsed > _profile_threshold:
            if _profile_threshold != _default_profile_threshold:
                print(f"Engine took longer than {_profile_threshold}ms: {ms_elapsed}", flush=True)
            else:
                print(f"Engine took: {ms_elapsed}", flush=True)

        if _frame_stats:
            self._record_frame_stats((updated - start) / 1e6, (end - updated) / 1e6)

        frame_ms = self.clock.tick() if self.wait_out_frame else self.clock.measure()
        self.fps_records.append(frame_ms)
        game.playtime += frame_ms
        self.behind += frame_ms
        return True

    def _record_frame_stats(self, update_ms: float, present_ms: float):
        self._stats_update_ms.append(update_ms)
        self._stats_present_ms.append(present_ms)
        if len(self._stats_update_ms) < FRAME_STATS_WINDOW:
            return
        now = time.perf_counter()
        fps = len(self._stats_update_ms) / (now - self._stats_start)
        update, present = sorted(self._stats_update_ms), sorted(self._stats_present_ms)
        p95 = int(len(update) * 0.95)
        print("LTPERF state=%s fps=%.1f update_mean=%.2f update_p95=%.2f update_max=%.1f present_mean=%.2f present_max=%.1f" %
              (self.game.state.current(), fps, sum(update) / len(update), update[p95], update[-1],
               sum(present) / len(present), present[-1]), flush=True)
        self._stats_update_ms.clear()
        self._stats_present_ms.clear()
        self._stats_start = now

def run(game):
    main_loop = MainLoop(game, wait_out_frame=True)
    while main_loop.run_frame():
        pass

# How much sooner than its time run_async starts a frame, rather than wait a
# whole screen refresh more for it
FRAME_EARLY_MS = 3

async def run_async(game):
    """
    The browser steps the page's Python once a screen refresh, each await of
    asyncio.sleep(0) handing the thread back until the next. Sound plays from
    callbacks on that same thread, so waiting out the frame in Clock.tick, as
    run does, starves them and the sound breaks up. Instead this holds the
    engine to FPS by yielding refreshes until each frame is due
    """
    main_loop = MainLoop(game, wait_out_frame=False)
    frame_ms = 1000 / FPS
    next_frame = time.perf_counter() * 1000
    while main_loop.run_frame():
        next_frame += frame_ms
        await asyncio.sleep(0)
        while time.perf_counter() * 1000 < next_frame - FRAME_EARLY_MS:
            await asyncio.sleep(0)
        # After a frame slower than its time, or the page hidden, count on from now
        # instead of rushing frames to catch up
        next_frame = max(next_frame, time.perf_counter() * 1000 - frame_ms)

def run_in_isolation(obj):
    """
    Requires that the object has
    1) take_input function that takes in the event
    2) update function
    3) draw function that returns the surface to be drawn
    """
    from app.engine.sound import get_sound_thread
    from app.engine.input_manager import get_input_manager

    get_sound_thread().reset()
    get_sound_thread().set_music_volume(cf.SETTINGS['music_volume'])
    get_sound_thread().set_sfx_volume(cf.SETTINGS['sound_volume'])

    surf = engine.create_surface((WINWIDTH, WINHEIGHT))
    clock = engine.Clock()
    while True:
        engine.update_time()

        raw_events = engine.get_events()
        if raw_events == engine.QUIT:
            break
        event = get_input_manager().process_input(raw_events)

        obj.take_input(event)
        obj.update()
        surf = obj.draw(surf)

        get_sound_thread().update(raw_events)

        engine.push_display(surf, engine.get_screensize(), engine.DISPLAYSURF)
        save_screenshot(raw_events, surf)

        engine.update_display()
        clock.tick()

def run_combat(mock_combat):
    run_in_isolation(mock_combat)

def run_event(event):
    run_in_isolation(event)
