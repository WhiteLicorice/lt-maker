from __future__  import annotations
# Helper global object for map sprite animations
from typing import Callable, List, Union

from app.constants import FRAMERATE


class generic3counter():
    def __init__(self, first_time=440, second_time=50, third_time=None):
        self.count = 0
        self.last_update = 0
        self.lastcount = 1
        self.first_time = int(first_time)
        self.second_time = int(second_time)
        self.third_time = self.first_time if third_time is None else int(third_time)

    def update(self, current_time):
        if self.count == 1 and current_time - self.last_update > self.second_time:
            self.increment()
            self.last_update = current_time
            return True
        elif self.count == 0 and current_time - self.last_update > self.first_time:
            self.increment()
            self.last_update = current_time
            return True
        elif self.count == 2 and current_time - self.last_update > self.third_time:
            self.increment()
            self.last_update = current_time
            return True
        return False

    def increment(self):
        if self.count == 0:
            self.count = 1
            self.lastcount = 0
        elif self.count == 2:
            self.count = 1
            self.lastcount = 2
        else:
            if self.lastcount == 0:
                self.count = 2
                self.lastcount = 1
            elif self.lastcount == 2:
                self.count = 0
                self.lastcount = 1

    def reset(self):
        self.count = 0
        self.last_update = 0
        self.lastcount = 1

class GenericAnimCounter():
    _count: int
    _values: List[int]
    _loop: bool = True
    _frame_duration = FRAMERATE
    _last_update = 0                    # should be divisible evenly by _frame_duration
    _get_time: Callable[[], int] = None # source of current time

    def __init__(self, values: List[int], loop: bool = True, frame_duration: int = FRAMERATE, get_time: Callable[[], int] = None):
        self._count = 0
        self._values = values
        self._loop = loop
        self._frame_duration = frame_duration
        self._get_time = get_time

    def get(self):
        self.sync()
        return self._values[self._count]

    def sync(self):
        if not self._get_time:
            return
        current_time = self._get_time()
        dt = current_time - self._last_update
        if dt >= self._frame_duration:
            frames_elapsed = int(dt // self._frame_duration)
            self._last_update = int((current_time // self._frame_duration) * self._frame_duration)
            self._update(frames_elapsed)

    def _update(self, steps):
        if self._loop:
            self._count = (self._count + steps) % len(self._values)
        else:
            if self._count < len(self._values) - 1:
                self._count = min(self._count + steps, len(self._values) - 1)

    def reset(self):
        self._count = 0
        if self._loop or not self._get_time:
            self._last_update = 0
        else:
            self._last_update = self._get_time()

    @staticmethod
    def from_frames(frames: List[int], loop: bool = True, frame_duration: int = FRAMERATE, get_time: Callable[[], int] = None) -> GenericAnimCounter:
        """
        Create a GenericAnimCounter from a list of persisted frames.
        For example, [20, 10, 30] would create a counter that returns 0 for 20 frames, 1 for 10 frames, and 2 for 30 frames.
        """
        frames_as_count = []
        for i, frame in enumerate(frames):
            frames_as_count.extend([i] * frame)
        return GenericAnimCounter(frames_as_count, loop, frame_duration=frame_duration, get_time=get_time)

    @staticmethod
    def from_frames_back_and_forth(frames: List[int], loop: bool = True, frame_duration: int = FRAMERATE, get_time: Callable[[], int] = None) -> GenericAnimCounter:
        """
        Create a GenericAnimCounter from a list of persisted frames. Will loop backwards rather than resetting to the start.
        For example, [20, 10, 30] would create a counter that returns 0 for 20 frames, 1 for 10 frames, 2 for 30 frames, 1 for 10 frames, then 0 for 20 frames again, etc.
        """
        frames_as_count = []
        for i, frame in enumerate(frames):
            frames_as_count.extend([i] * frame)
        if(len(frames) > 2):
            for i, frame in enumerate(reversed(frames[1:-1])):
                frames_as_count.extend([len(frames) - i - 2] * frame)
        return GenericAnimCounter(frames_as_count, loop, frame_duration=frame_duration, get_time=get_time)

    @property
    def count(self):
        """stupid compatability getter, replace this with all haste"""
        return self.get()


class movement_counter():
    def __init__(self):
        self.count = 0
        self.movement = [0, 1, 2, 3, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 4, 3, 2, 1]
        self.started = False

    def value(self):
        return self.movement[self.count]

    def update(self, current_time):
        if self.started:
            self.count += 1
            if self.count >= len(self.movement):
                self.count = 0
                self.started = False

    def reset(self):
        self.started = True
        self.count = 0

class arrow_counter():
    def __init__(self, offset=0):
        self.arrow_counter = offset
        self.arrow_anim = [0, 1, 2, 3, 4, 5]
        self.increment = []

    def update(self):
        if self.increment:
            self.arrow_counter += self.increment.pop()
        else:
            self.arrow_counter += 0.125
        if self.arrow_counter >= len(self.arrow_anim):
            self.arrow_counter = 0

    def get(self):
        return self.arrow_anim[int(self.arrow_counter)]

    def pulse(self):
        self.increment = [1, 1, 1, 1, 1, 1, 1, 1, .5, .5, .5, .5, .25, .25, .25]

class BlinkCounter():
    def __init__(self, max_count: int = 2, update_times: List[int] = [440, 50]):
        self.count = 0
        self.max_count = max_count
        self.last_update = 0
        self.reverse = False

        self.update_times = update_times
        for i in range(max_count+1 - len(update_times)):
            update_times.append(update_times[-1])

    def update(self, current_time):
        if current_time - self.last_update > self.update_times[self.count]:
            self.count += -1 if self.reverse else 1
            if self.count == 0 or self.count == self.max_count:
                self.reverse = not self.reverse
            self.last_update = current_time
            return True
        return False

    def reset(self):
        self.count = 0
        self.last_update = 0
        self.reverse = False

    def get_blink_index(self):
        return self.max_count - self.count

    def is_open_eyes(self):
        return self.count == 0
