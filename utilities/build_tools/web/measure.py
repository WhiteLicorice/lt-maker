'''
Plays a browser build in headless Edge or Chrome and collects the engine's
LTPERF frame-time lines.

    python utilities/build_tools/web/measure.py <url> <out_dir> [title|level] [--browser msedge|chrome|firefox|webkit] [--cpu-throttle N]

Serve the build first (web/serve.py, or any static server on
build/web/<project>). Needs playwright (pip install playwright==1.64.0).
"title" sits on the title screen; "level" expects a url with ?level=<nid>,
watches its opening events, skips the rest, then idles on the map and moves
the cursor about; a number of seconds just leaves the engine running that long.
--cpu-throttle N slows the page's CPU N times over, as Chrome's DevTools does
to stand in for a phone (Lighthouse takes 4 for a mid-range one); Chromium only.

Python's output goes to the page's xterm.js terminal, not the browser console,
so this reads the terminal's buffer. out_dir gets screenshots, terminal.log
(Python's output) and console.log (the page's JavaScript console)
'''
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

# The engine's default keys (app/engine/config.py)
SELECT, BACK, START = 'x', 'z', 's'

TERMINAL_JS = """() => {
  const t = window.python && window.python.vt && window.python.vt.xterm;
  if (!t || !t.buffer) return [];
  const b = t.buffer.active, lines = [];
  for (let i = 0; i < b.length; i++) { const l = b.getLine(i); if (l) lines.push(l.translateToString(true)); }
  return lines;
}"""

class Terminal():
    '''Follows the page's terminal, which scrolls old lines away'''
    def __init__(self, page, log_path: Path, began: float):
        self.page = page
        self.log = open(log_path, 'w', encoding='utf-8')
        self.began = began
        self.seen: list[str] = []
        self.text = ''

    def drain(self):
        lines = [line for line in self.page.evaluate(TERMINAL_JS) if line.strip()]
        # The new lines are what follows the longest tail of what we saw that the
        # buffer starts with. The last line seen may still have been growing, so it
        # is read again
        settled = self.seen[:-1]
        overlap = 0
        for n in range(min(len(settled), len(lines)), 0, -1):
            if settled[-n:] == lines[:n]:
                overlap = n
                break
        # Unless it has not changed
        if self.seen and overlap == len(settled) and overlap < len(lines) and lines[overlap] == self.seen[-1]:
            overlap += 1
        for line in lines[overlap:]:
            stamped = '%7.1f %s' % (time.time() - self.began, line)
            self.log.write(stamped + '\n')
            self.text += line + '\n'
            if 'LTPERF' in line or 'LTBENCH' in line or 'LTCPROF' in line or 'Error' in line or 'Traceback' in line or 'Lex Talionis' in line:
                print(stamped, flush=True)
        self.log.flush()
        self.seen = lines

def main(args: list[str]):
    def take_option(name: str, default: str) -> str:
        nonlocal args
        if name not in args:
            return default
        at = args.index(name)
        value = args[at + 1]
        args = args[:at] + args[at + 2:]
        return value
    browser_channel = take_option('--browser', 'msedge')
    cpu_throttle = float(take_option('--cpu-throttle', '1'))
    url, out_dir = args[0], Path(args[1])
    scenario = args[2] if len(args) > 2 else 'title'
    out_dir.mkdir(parents=True, exist_ok=True)
    console = open(out_dir / 'console.log', 'w', encoding='utf-8')
    began = time.time()

    with sync_playwright() as p:
        if browser_channel in ('firefox', 'webkit'):
            # Playwright's own builds (playwright install firefox webkit); WebKit is Safari's engine
            browser = getattr(p, browser_channel).launch(headless=True)
        else:
            browser = p.chromium.launch(channel=browser_channel, headless=True,
                                        args=['--autoplay-policy=no-user-gesture-required'])
        page = browser.new_page(viewport={'width': 1280, 'height': 720})
        page.on('console', lambda msg: console.write('%7.1f %s\n' % (time.time() - began, msg.text)))
        page.on('pageerror', lambda err: console.write('%7.1f PAGEERROR %s\n' % (time.time() - began, err)))
        terminal = Terminal(page, out_dir / 'terminal.log', began)
        if cpu_throttle != 1:
            cdp = page.context.new_cdp_session(page)
            cdp.send('Emulation.setCPUThrottlingRate', {'rate': cpu_throttle})
        # ?perf has the engine print its LTPERF lines (main.py)
        page.goto(url + ('&' if '?' in url else '?') + 'perf')

        def wait(seconds: float):
            end = time.time() + seconds
            while time.time() < end:
                page.wait_for_timeout(int(min(0.5, max(0.0, end - time.time())) * 1000))
                terminal.drain()

        def shot(name: str):
            page.screenshot(path=str(out_dir / ('%s.png' % name)))

        def press(key: str, times: int = 1, gap: float = 0.25):
            for _ in range(times):
                page.keyboard.down(key)
                page.wait_for_timeout(80)
                page.keyboard.up(key)
                wait(gap)

        # pygbag waits for a click (user media engagement) before it runs main.py,
        # unless the browser already allows autoplay
        deadline = time.time() + 300
        while time.time() < deadline and 'LTPERF' not in terminal.text:
            info = page.evaluate("() => { const e = document.getElementById('infobox'); return e ? e.innerText : '' }")
            if 'click' in info.lower():
                print('clicking to start after %.1fs' % (time.time() - began), flush=True)
                page.mouse.click(640, 360)
                break
            wait(0.5)
        while time.time() < deadline and 'LTPERF' not in terminal.text:
            wait(0.5)
        print('engine running after %.1fs' % (time.time() - began), flush=True)
        shot('01_started')

        if scenario == 'title':
            wait(20)
            shot('02_title')
            press(START)
            wait(10)
            shot('03_title_menu')
        elif scenario == 'level':
            # Watch the opening events for a while, then skip them until the
            # player has the map
            wait(20)
            shot('02_event')
            for _ in range(30):
                last_report = [line for line in terminal.text.splitlines() if 'LTPERF' in line][-1]
                if 'state=free' in last_report:
                    break
                press(START)
                wait(2)
            print('on the map after %.1fs' % (time.time() - began), flush=True)
            wait(20)
            shot('03_map_idle')
            for key in ('ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp') * 3:
                press(key, 4, gap=0.1)
            shot('04_cursor')
            wait(10)
        else:
            # Leave the engine be, as for a profile
            wait(float(scenario))
        browser.close()
    console.close()

if __name__ == '__main__':
    main(sys.argv[1:])
