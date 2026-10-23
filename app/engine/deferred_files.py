"""
Files that may arrive after the game has started. The browser build
(app/utilities/web_export.py) leaves most of the game's music, sound
effects and combat animation sheets out of the download the page starts with,
and the page fetches them in the background while the game runs. The engine
passes such a file's path through ensure before opening it, which fetches the
file there and then if it has yet to arrive. Everywhere else every file is in
place from the start, and ensure leaves it at that.
"""
import os
import sys

def ensure(path: str) -> str:
    """Returns path, once the file there is in place"""
    if sys.platform == 'emscripten' and not os.path.exists(path):
        # pygbag's platform module, standing in for the standard library's, reaches the page
        import platform
        # Why the page could not fetch it, or '' once it is in place
        problem = str(platform.window.__ltDeferred.fetchNow(os.path.relpath(path).replace(os.sep, '/'), os.path.abspath(path)))
        if problem:
            raise FileNotFoundError("Could not fetch %s: %s" % (path, problem))
    return path
