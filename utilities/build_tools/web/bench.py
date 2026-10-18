'''
A quick measure of how fast this interpreter runs the kinds of work a frame does,
so one machine or browser can be compared with another. The browser build runs
it for ?bench in the page's address; natively,
python utilities/build_tools/web/bench.py
'''
import collections
import sys
import time
from typing import Callable

import pygame

class CCallTimer():
    '''
    Totals the time spent in each C function (pygame's blits and the like) while
    running, through sys.setprofile: the browser's Python has no cProfile.
    Whatever a frame spends outside them is Python
    '''
    def __init__(self):
        self.totals: dict[str, float] = collections.defaultdict(float)
        self.counts: collections.Counter = collections.Counter()
        # Blit time by the line that called it
        self.blit_sites: dict[str, float] = collections.defaultdict(float)
        self.blit_site_counts: collections.Counter = collections.Counter()
        self._stack: list[tuple[str, str, float]] = []

    def _hook(self, frame, event, arg):
        if event == 'c_call':
            name = getattr(arg, '__qualname__', repr(arg))
            site = '%s:%d %s' % (frame.f_code.co_filename.rsplit('/', 1)[-1], frame.f_lineno, frame.f_code.co_name)
            self._stack.append((name, site, time.perf_counter()))
        elif event in ('c_return', 'c_exception') and self._stack:
            name, site, began = self._stack.pop()
            elapsed = time.perf_counter() - began
            self.totals[name] += elapsed
            self.counts[name] += 1
            if name == 'Surface.blit':
                self.blit_sites[site] += elapsed
                self.blit_site_counts[site] += 1

    def start(self):
        sys.setprofile(self._hook)

    def stop(self):
        sys.setprofile(None)

    def report(self, frames: int, wall_seconds: float):
        tick = self.totals.pop('Clock.tick', 0.0)
        in_c = sum(self.totals.values())
        per_frame = lambda seconds: seconds * 1000 / frames
        print('LTCPROF %d frames: %.2f ms a frame, %.2f waiting in Clock.tick, %.2f in other C calls, %.2f in Python'
              % (frames, per_frame(wall_seconds), per_frame(tick), per_frame(in_c), per_frame(wall_seconds - tick - in_c)), flush=True)
        for name, seconds in sorted(self.totals.items(), key=lambda item: -item[1])[:12]:
            print('LTCPROF   %-40s %6.2f ms a frame, %6.1f calls a frame' % (name, per_frame(seconds), self.counts[name] / frames), flush=True)
        print('LTCPROF blits by caller:', flush=True)
        for site, seconds in sorted(self.blit_sites.items(), key=lambda item: -item[1])[:15]:
            print('LTCPROF   %-60s %6.2f ms a frame, %5.1f calls a frame' % (site, per_frame(seconds), self.blit_site_counts[site] / frames), flush=True)

def _time(work: Callable[[], None], repeat: int = 5) -> float:
    '''Best of repeat runs, in ms'''
    best = None
    for _ in range(repeat):
        start = time.perf_counter()
        work()
        elapsed = (time.perf_counter() - start) * 1000
        best = elapsed if best is None else min(best, elapsed)
    return best

def _python_loop():
    total = 0
    for i in range(200_000):
        total += i % 7
    return total

def _python_calls():
    class Unit():
        def __init__(self, hp):
            self.hp = hp

        def get_hp(self):
            return self.hp
    units = [Unit(i) for i in range(100)]
    return sum(unit.get_hp() for _ in range(500) for unit in units)

def _python_dicts():
    table = {('tile', x, y): x * y for x in range(60) for y in range(40)}
    return sum(table[('tile', x % 60, x % 40)] for x in range(100_000))

def run() -> dict[str, float]:
    screen = pygame.Surface((240, 160))
    tile = pygame.Surface((16, 16), pygame.SRCALPHA)
    tile.fill((200, 100, 50, 128))
    opaque = pygame.Surface((16, 16))
    # A full screen image half see-through, as a portrait or a window is
    big = pygame.Surface((240, 160), pygame.SRCALPHA)
    big.fill((200, 100, 50, 255), (0, 0, 240, 80))
    big_opaque = pygame.Surface((240, 160))
    big_opaque.fill((200, 100, 50))
    big_colorkey = pygame.Surface((240, 160))
    big_colorkey.fill((200, 100, 50), (0, 0, 240, 80))
    big_colorkey.set_colorkey((0, 0, 0))
    big_colorkey_rle = big_colorkey.copy()
    big_colorkey_rle.set_colorkey((0, 0, 0), pygame.RLEACCEL)
    big_premul = big.premul_alpha()

    def blit_alpha():
        for _ in range(2000):
            screen.blit(tile, (32, 32))

    def blit_opaque():
        for _ in range(2000):
            screen.blit(opaque, (32, 32))

    def blit_full(source: pygame.Surface, flags: int = 0):
        def work():
            for _ in range(200):
                screen.blit(source, (0, 0), special_flags=flags)
        return work

    def scale_up():
        for _ in range(20):
            pygame.transform.scale(screen, (720, 480))

    results = {
        'python_loop_200k': _time(_python_loop),
        'python_calls_50k': _time(_python_calls),
        'python_dict_100k': _time(_python_dicts),
        'blit_16px_alpha_2000': _time(blit_alpha),
        'blit_16px_opaque_2000': _time(blit_opaque),
        'blit_240x160_alpha_200': _time(blit_full(big)),
        'blit_240x160_premultiplied_200': _time(blit_full(big_premul, pygame.BLEND_PREMULTIPLIED)),
        'blit_240x160_opaque_200': _time(blit_full(big_opaque)),
        'blit_240x160_colorkey_200': _time(blit_full(big_colorkey)),
        'blit_240x160_colorkey_rle_200': _time(blit_full(big_colorkey_rle)),
        'scale_240x160_to_3x_20': _time(scale_up),
    }
    # Whether Clock.tick holds the thread for the rest of the frame
    clock = pygame.time.Clock()
    clock.tick(60)
    results['clock_tick_60_x10'] = _time(lambda: [clock.tick(60) for _ in range(10)], repeat=1)
    for name, ms in results.items():
        print('LTBENCH %s %.2f ms' % (name, ms), flush=True)
    return results

if __name__ == '__main__':
    pygame.init()
    run()
