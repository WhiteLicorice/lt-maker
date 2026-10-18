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
    ?audio_log              logs to the browser's console whether the audio
                            callback keeps up (AUDIO_LOG_JS)
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

OPTIONS = page_options()
# Read by the driver at import
os.environ['LT_FRAME_STATS'] = '1'

from app.constants import VERSION
from app.data.metadata import Metadata
from app.data.resources.resources import RESOURCES
from app.data.database.database import DB
from app.data.serialization.dataclass_serialization import dataclass_from_dict
from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
from app.engine import config as cf
from app.engine import driver
from app.engine import game_state

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

# Logs to the browser's console, every two seconds, whether SDL's audio
# callback keeps up. It runs on the page's main thread through a
# ScriptProcessorNode, so anything that holds the thread past one buffer
# (10.7 ms of 512 frames at 48 kHz) drops sound
AUDIO_LOG_JS = """(() => {
  const create = AudioContext.prototype.createScriptProcessor;
  AudioContext.prototype.createScriptProcessor = function (size, inputs, outputs) {
    const node = create.call(this, size, inputs, outputs);
    const context = this;
    let handler = null, calls = 0, late = 0, worst = 1e9, longestGap = 0, last = null;
    console.log('LTAUDIO context ' + context.sampleRate + ' Hz, buffer ' + node.bufferSize + ' frames (' +
                (node.bufferSize / context.sampleRate * 1000).toFixed(1) + ' ms)');
    Object.defineProperty(node, 'onaudioprocess', {
      get() { return handler; },
      set(callback) {
        handler = callback;
        node.addEventListener('audioprocess', (event) => {
          const now = performance.now();
          if (last !== null) longestGap = Math.max(longestGap, now - last);
          last = now;
          handler(event);
          const lead = (event.playbackTime - context.currentTime) * 1000;
          calls++; worst = Math.min(worst, lead); if (lead < 0) late++;
        });
      },
    });
    setInterval(() => {
      console.log('LTAUDIO ' + (calls / 2).toFixed(1) + ' callbacks/s, ' + late + ' late, closest ' +
                  worst.toFixed(1) + ' ms before due, longest gap ' + longestGap.toFixed(1) + ' ms');
      calls = 0; late = 0; worst = 1e9; longestGap = 0;
    }, 2000);
    return node;
  };
})();"""

async def main():
    print('*** Lex Talionis Engine Version %s on Python %s (%s) ***' % (VERSION, sys.version.split()[0], sys.platform))
    print('Working directory:', os.getcwd())
    if 'audio_log' in OPTIONS:
        import platform
        platform.window.eval(AUDIO_LOG_JS)
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
    DB.load(project, CURRENT_SERIALIZATION_VERSION)
    title = DB.constants.value('title')
    level_nid = OPTIONS.get('level')
    driver.start(title, from_editor=bool(level_nid))
    print('Mixer (frequency, format, channels):', pygame.mixer.get_init())
    if level_nid:
        game = game_state.start_level(level_nid)
    else:
        game = game_state.start_game()
    if 'cprofile' in OPTIONS:
        start, frames = (int(n) for n in OPTIONS['cprofile'].split(','))
        await run_c_timed(game, start, frames)
    else:
        await driver.run_async(game)

try:
    asyncio.run(main())
except Exception:
    traceback.print_exc()
