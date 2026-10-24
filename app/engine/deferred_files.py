"""
Files that may arrive after the game has started. The browser build
(app/utilities/web_export.py) leaves most of the game's music, sound
effects and combat animation sheets out of the download the page starts with,
and the page fetches them in the background while the game runs, keeping them
apart from the game's own memory. The engine opens such a file through load,
which puts the file in place while it loads it, fetching it there and then if
it has yet to arrive, and takes it out again after. Everywhere else every file
is in place from the start, and load leaves it at that.
"""
import os
import sys
from typing import Callable, TypeVar

Loaded = TypeVar('Loaded')

def load(path: str, loader: Callable[[str], Loaded]) -> Loaded:
    """
    What loader makes of the file at path, which in the browser is in place
    only while loader runs: what it makes (a decoded sound, an image) must not
    read the file later
    """
    loaded = loader(ensure(path))
    if sys.platform == 'emscripten':
        # pygbag's platform module, standing in for the standard library's, reaches the page
        import platform
        platform.window.__ltDeferred.release(_page_path(path), os.path.abspath(path))
    return loaded

def ensure(path: str) -> str:
    """Returns path, once the file there is in place"""
    if sys.platform == 'emscripten' and not os.path.exists(path):
        import platform
        # Why the page could not fetch it, or '' once it is in place
        problem = str(platform.window.__ltDeferred.fetchNow(_page_path(path), os.path.abspath(path)))
        if problem:
            raise FileNotFoundError("Could not fetch %s: %s" % (path, problem))
    return path

def _page_path(path: str) -> str:
    """The page's name for the file at path: its path from main.py's folder, as deferred.json has it"""
    return os.path.relpath(path).replace(os.sep, '/')
