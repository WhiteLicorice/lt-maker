'''
Background work for the engine. The browser build (sys.platform 'emscripten')
cannot start threads, so there the work runs to completion where it starts
'''
import sys
import threading
from typing import Callable, Protocol

CAN_START_THREADS = sys.platform != 'emscripten'

class Work(Protocol):
    def join(self) -> None: ...
    def is_alive(self) -> bool: ...

class FinishedWork():
    '''Work that already ran to completion when it was started'''
    def join(self) -> None:
        pass

    def is_alive(self) -> bool:
        return False

def start(target: Callable, args: tuple = ()) -> Work:
    if not CAN_START_THREADS:
        target(*args)
        return FinishedWork()
    thread = threading.Thread(target=target, args=args)
    thread.start()
    return thread
