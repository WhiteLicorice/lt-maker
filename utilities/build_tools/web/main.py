'''
Entry point of the browser build. utilities/build_tools/build_web.py copies it
to main.py beside the engine and the one project it packs, and pygbag runs it
under CPython compiled to WebAssembly (sys.platform == 'emscripten').

The page's address takes options:
    ?level=<nid>            starts that level as the editor's Test Chapter does,
                            instead of the title screen
    ?bench                  times a few kinds of work (bench.py) before starting,
                            to compare one browser or device with another
    ?cprofile=<start>,<n>   splits frames start to start + n between pygame's
                            C functions and Python (bench.CCallTimer)
    ?audio_buffer=<n>       opens the mixer with 128 * 2 ** n frames of buffer,
                            in place of the sound_buffer_size setting (2)
    ?audio_log              logs to the browser's console whether the sound
                            keeps up (AUDIO_LOG_JS)
    ?frame_log              logs to the browser's console each screen refresh
                            the page missed, and what held it up (FRAME_LOG_JS)
    ?touch                  draws the on-screen buttons (page.js) even where
                            the screen isn't a touch screen
    ?integer                shows the game only at whole multiples of its size,
                            with a border, rather than filling the window
    ?report                 sends Python's output, the browser's console and
                            the page's errors to the server it came from, for
                            a phone whose browser can't be inspected
                            (serve.py writes them down)
'''
import asyncio
import json
import os
import sys
import time
import traceback
from pathlib import Path
from urllib.parse import parse_qs

# pygbag fetches the packages that main.py itself imports, and no others
import pygame  # noqa: F401

def page_options() -> dict[str, str]:
    # pygbag's platform module, standing in for the standard library's, reaches the page
    import platform
    query = parse_qs(str(platform.window.location.search).lstrip('?'), keep_blank_values=True)
    return {key: values[0] for key, values in query.items()}

def loaded(step: str):
    """Notes how long after the page was opened a step of loading finished"""
    import platform
    print('LTLOAD %-20s %6.0f ms' % (step, float(platform.window.performance.now())), flush=True)

# Sends what it is given to the server's /report once a second, along with the
# browser's console and the page's errors, starting with what device this is
REPORT_JS = """(() => {
  const pending = [];
  window.__ltReport = (line) => { pending.push(line); };
  const send = () => {
    if (!pending.length) return;
    const body = pending.splice(0).join('\\n');
    fetch('/report', {method: 'POST', body: body, keepalive: true}).catch(() => {});
  };
  setInterval(send, 1000);
  window.addEventListener('pagehide', send);
  for (const level of ['log', 'warn', 'error']) {
    const original = console[level];
    console[level] = function (...args) {
      pending.push('console.' + level + ' ' + args.map(String).join(' '));
      original.apply(console, args);
    };
  }
  window.addEventListener('error', (event) => {
    pending.push('page error: ' + event.message + ' at ' + event.filename + ':' + event.lineno);
  });
  window.addEventListener('unhandledrejection', (event) => {
    pending.push('page error: unhandled rejection ' + event.reason);
  });
  document.addEventListener('visibilitychange', () => { pending.push('page ' + document.visibilityState); });
  pending.push('device ' + navigator.userAgent + '; screen ' + screen.width + 'x' + screen.height +
               ' at ' + devicePixelRatio + 'x; window ' + innerWidth + 'x' + innerHeight +
               '; ' + navigator.hardwareConcurrency + ' cores');
})();"""

class ReportingStream():
    """Passes writes on to the stream it wraps, and each finished line to REPORT_JS"""
    def __init__(self, stream, window):
        self.stream = stream
        self.window = window
        self.partial = ''

    def write(self, text: str) -> int:
        self.partial += text
        *lines, self.partial = self.partial.split('\n')
        for line in lines:
            self.window.eval('__ltReport(%s)' % json.dumps(line))
        return self.stream.write(text)

    def flush(self):
        self.stream.flush()

def start_reporting():
    import platform
    platform.window.eval(REPORT_JS)
    sys.stdout = ReportingStream(sys.stdout, platform.window)
    sys.stderr = ReportingStream(sys.stderr, platform.window)

OPTIONS = page_options()
if 'report' in OPTIONS:
    start_reporting()
loaded('main.py running')
# Read by the driver at import
os.environ['LT_FRAME_STATS'] = '1'

from app.constants import VERSION, WINWIDTH, WINHEIGHT
from app.data.metadata import Metadata
from app.data.resources.resources import RESOURCES
from app.data.database.database import DB
from app.data.serialization.dataclass_serialization import dataclass_from_dict
from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
from app.engine import config as cf
from app.engine import driver
from app.engine import game_state
loaded('engine imported')

def find_project() -> str:
    projects = [name for name in os.listdir('.') if name.endswith('.ltproj')]
    if len(projects) != 1:
        raise ValueError("Expected exactly one .ltproj beside main.py, found %s" % projects)
    return projects[0]

async def run_c_timed(game, start: int, frames: int):
    import bench
    main_loop = driver.MainLoop(game, wait_out_frame=True)
    timer = bench.CCallTimer()
    frame, wall = 0, 0.0
    while True:
        timed = start <= frame < start + frames
        if timed:
            began = time.perf_counter()
            timer.start()
        running = main_loop.run_frame()
        if timed:
            timer.stop()
            wall += time.perf_counter() - began
        if not running:
            break
        frame += 1
        if frame == start + frames:
            timer.report(frames, wall)
        await asyncio.sleep(0)

# Logs to the browser's console, every two seconds, how the sound kept up:
# page.js has SDL fill buffers ahead of time, and any the game's thread held
# up past their time leave a gap of silence (holds)
AUDIO_LOG_JS = """setInterval(() => {
  console.log('LTAUDIO ' + (__ltSound.buffers / 2).toFixed(1) + ' buffers/s of ' + __ltSound.node + ', ' +
              __ltSound.holds + ' holds, ' + __ltSound.silentMs.toFixed(0) + ' ms silent');
  __ltSound.buffers = 0; __ltSound.holds = 0; __ltSound.silentMs = 0;
}, 2000);"""

# Logs to the browser's console each time the page's animation frames, which
# the engine runs in, come more than 20 ms apart: how late the frame's
# callbacks started after its time, how long each of the last frame's took
# (the engine's is the longest), and how long feeding the sound took between
# them (page.js). Every two seconds it sums up
FRAME_LOG_JS = """(() => {
  const request = window.requestAnimationFrame.bind(window);
  let last = null, current = null, frames = 0, missed = 0;
  window.requestAnimationFrame = (callback) => request((stamp) => {
    if (!current || current.stamp !== stamp) {
      last = current;
      current = {stamp: stamp, start: performance.now(), took: [], sound: __ltSound.busyMs};
      frames++;
      if (last && stamp - last.stamp > 20) {
        missed++;
        console.log('LTFRAME ' + (stamp - last.stamp).toFixed(1) + ' ms since the last frame, started ' +
                    (current.start - stamp).toFixed(1) + ' ms late; last frame callbacks ' +
                    last.took.map((ms) => ms.toFixed(1)).join(', ') + ' ms, started ' +
                    (last.start - last.stamp).toFixed(1) + ' ms late; sound since ' +
                    (current.sound - last.sound).toFixed(1) + ' ms (longest ' + __ltSound.longestMs.toFixed(1) + ')');
        __ltSound.longestMs = 0;
      }
    }
    const began = performance.now();
    try { callback(stamp); } finally { current.took.push(performance.now() - began); }
  });
  setInterval(() => {
    console.log('LTFRAME ' + (frames / 2).toFixed(1) + ' frames/s, ' + missed + ' late');
    frames = 0; missed = 0;
  }, 2000);
})();"""

def setup_page():
    """
    Lays out the page, with on-screen buttons on a touch screen or for ?touch.
    The engine draws at the game's own size, and the page scales it up
    """
    import platform
    platform.window.eval(Path('page.js').read_text())
    show_pad = json.loads(str(platform.window.eval(
        'JSON.stringify(__ltSetupPage(%s || matchMedia("(pointer: coarse)").matches, %s, %s))'
        % (json.dumps('touch' in OPTIONS), WINWIDTH / WINHEIGHT, json.dumps('integer' in OPTIONS)))))
    # The files the build left out of the download, from here on
    platform.window.__ltDeferred.start(os.getcwd())
    cf.SETTINGS['screen_size'] = 1
    if show_pad:
        # A touch on the game's screen would press SELECT where it touched; the buttons do instead
        cf.SETTINGS['mouse'] = 0

async def pump_touch_controls():
    """
    Hands the engine the on-screen buttons' presses as presses of the keys
    the player has for those buttons, so it takes them as it does a keyboard
    """
    import platform
    while True:
        for button, down in json.loads(str(platform.window.eval('__ltTouch.take()'))):
            event_type = pygame.KEYDOWN if down else pygame.KEYUP
            pygame.event.post(pygame.event.Event(event_type, key=cf.SETTINGS['key_' + button], mod=0, scancode=0, unicode=''))
        await asyncio.sleep(0)

async def main():
    setup_page()
    print('*** Lex Talionis Engine Version %s on Python %s (%s) ***' % (VERSION, sys.version.split()[0], sys.platform))
    print('Built', Path('built.txt').read_text())
    print('Working directory:', os.getcwd())
    if 'audio_log' in OPTIONS:
        import platform
        platform.window.eval(AUDIO_LOG_JS)
    if 'frame_log' in OPTIONS:
        import platform
        platform.window.eval(FRAME_LOG_JS)
    if 'audio_buffer' in OPTIONS:
        # The mixer's buffer is 128 * 2 ** this many frames
        cf.SETTINGS['sound_buffer_size'] = int(OPTIONS['audio_buffer'])
    if 'bench' in OPTIONS:
        import bench
        pygame.init()
        bench.run()
    project = find_project()
    metadata = dataclass_from_dict(Metadata, json.loads(Path(project, 'metadata.json').read_text()))
    if metadata.has_fatal_errors:
        raise ValueError("Fatal errors detected in game. Aborting launch.")
    os.makedirs('saves', exist_ok=True)
    RESOURCES.load(project, CURRENT_SERIALIZATION_VERSION)
    loaded('resources loaded')
    DB.load(project, CURRENT_SERIALIZATION_VERSION)
    loaded('database loaded')
    title = DB.constants.value('title')
    import platform
    platform.window.__ltSetTitle(title)
    level_nid = OPTIONS.get('level')
    driver.start(title, from_editor=bool(level_nid))
    print('Mixer (frequency, format, channels):', pygame.mixer.get_init())
    loaded('engine started')
    if level_nid:
        game = game_state.start_level(level_nid)
    else:
        game = game_state.start_game()
    loaded('game started')
    asyncio.create_task(pump_touch_controls())
    if 'cprofile' in OPTIONS:
        start, frames = (int(n) for n in OPTIONS['cprofile'].split(','))
        await run_c_timed(game, start, frames)
    else:
        await driver.run_async(game)

try:
    asyncio.run(main())
except Exception:
    traceback.print_exc()
