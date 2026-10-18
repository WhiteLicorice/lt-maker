'''
Records what a browser build sends to the speakers, to find why its audio stutters.

    python utilities/build_tools/web/audio_probe.py <url> <out_dir> [seconds] [--browser msedge|chrome] [--unlimited-fps]

--unlimited-fps lifts the browser's frame-rate cap, as a monitor faster than
60 Hz does to requestAnimationFrame.

SDL plays sound in the browser through a ScriptProcessorNode, whose callback
runs on the page's main thread, between the engine's frames. This wraps that
callback to note when each one ran and how close to its deadline, and records
its output. out_dir gets audio.wav (what was played) and audio_timing.txt
'''
import json
import struct
import sys
import time
import wave
from pathlib import Path

from playwright.sync_api import sync_playwright

WRAP_SCRIPT_PROCESSOR = """(() => {
  const log = window.__ltAudio = {calls: [], samples: [[], []], rate: 0, size: 0, channels: 0};
  for (const Context of [window.AudioContext, window.webkitAudioContext]) {
    if (!Context) continue;
    const create = Context.prototype.createScriptProcessor;
    Context.prototype.createScriptProcessor = function (size, inputs, outputs) {
      const node = create.call(this, size, inputs, outputs);
      const context = this;
      log.rate = context.sampleRate; log.size = node.bufferSize; log.channels = outputs;
      let handler = null;
      Object.defineProperty(node, 'onaudioprocess', {
        get() { return handler; },
        set(callback) {
          handler = callback;
          node.addEventListener('audioprocess', (event) => {
            const began = performance.now();
            handler(event);
            // How long before this buffer is due to play the callback finished, in ms
            const lead = (event.playbackTime - context.currentTime) * 1000;
            log.calls.push([began, performance.now() - began, lead]);
            for (let c = 0; c < Math.min(2, event.outputBuffer.numberOfChannels); c++) {
              log.samples[c].push(Array.from(event.outputBuffer.getChannelData(c)));
            }
          });
        },
      });
      return node;
    };
  }
})();"""

def write_wav(path: Path, channels: list[list[list[float]]], rate: int):
    left = [s for block in channels[0] for s in block]
    right = [s for block in channels[1] for s in block] if channels[1] else left
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(rate)
        frames = bytearray()
        for l, r in zip(left, right):
            frames += struct.pack('<hh', int(max(-1, min(1, l)) * 32767), int(max(-1, min(1, r)) * 32767))
        out.writeframes(bytes(frames))

def main(args: list[str]):
    channel = 'msedge'
    launch_args = ['--autoplay-policy=no-user-gesture-required']
    if '--unlimited-fps' in args:
        args.remove('--unlimited-fps')
        launch_args += ['--disable-gpu-vsync', '--disable-frame-rate-limit']
    if '--browser' in args:
        at = args.index('--browser')
        channel = args[at + 1]
        args = args[:at] + args[at + 2:]
    url, out_dir = args[0], Path(args[1])
    seconds = float(args[2]) if len(args) > 2 else 20
    out_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=channel, headless=True, args=launch_args)
        page = browser.new_page(viewport={'width': 1280, 'height': 720})
        page.add_init_script(WRAP_SCRIPT_PROCESSOR)
        page.goto(url)
        # Until the engine has been running a while, then clear what loading did
        deadline = time.time() + 120
        while time.time() < deadline and not page.evaluate('window.__ltAudio && window.__ltAudio.calls.length > 200'):
            info = page.evaluate("() => { const e = document.getElementById('infobox'); return e ? e.innerText : '' }")
            if 'click' in info.lower():
                page.mouse.click(640, 360)
            page.wait_for_timeout(500)
        page.wait_for_timeout(8000)
        page.evaluate('() => { window.__ltAudio.calls = []; window.__ltAudio.samples = [[], []]; }')
        page.wait_for_timeout(int(seconds * 1000))
        log = page.evaluate('() => window.__ltAudio')
        browser.close()

    calls = log['calls']
    budget = log['size'] / log['rate'] * 1000
    gaps = [b[0] - a[0] for a, b in zip(calls, calls[1:])]
    late = [c for c in calls if c[2] < 0]
    lines = [
        'context %d Hz, ScriptProcessor buffer %d frames (%.1f ms), %d output channels' % (log['rate'], log['size'], budget, log['channels']),
        '%d callbacks in %.0f s (%.1f a second, %.1f needed)' % (len(calls), seconds, len(calls) / seconds, 1000 / budget),
        'callback run time: mean %.2f ms, max %.2f ms' % (sum(c[1] for c in calls) / len(calls), max(c[1] for c in calls)),
        'gap between callbacks: max %.1f ms; %d gaps longer than two buffers' % (max(gaps), sum(1 for g in gaps if g > 2 * budget)),
        'finished after the buffer was due: %d of %d (%.1f%%), worst %.1f ms late' % (
            len(late), len(calls), 100 * len(late) / len(calls), -min(c[2] for c in calls)),
    ]
    (out_dir / 'audio_timing.txt').write_text('\n'.join(lines) + '\n' + json.dumps(calls[:2000]))
    print('\n'.join(lines))
    write_wav(out_dir / 'audio.wav', log['samples'], log['rate'])
    print('wrote', out_dir / 'audio.wav')

if __name__ == '__main__':
    main(sys.argv[1:])
