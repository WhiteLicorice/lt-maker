import gc

def settle():
    """
    Collects all the garbage now, while a loading screen is up, then sets
    aside every object still alive, so that later collections leave them out.
    Most of them live as long as the level does or longer (the project's data,
    the level's units and map), and a full collection that looks through them
    all stops the game for tens of milliseconds. Each settle takes back what
    the last one set aside before collecting, so what has died since is
    collected too
    """
    gc.unfreeze()
    gc.collect()
    gc.freeze()

def release():
    """
    Hands back to the garbage collector everything settle set aside. The
    editor runs the engine in its own process, and settle sets aside the
    editor's objects along with the engine's: once the engine returns, the
    engine's are garbage, and the editor's go on living and dying
    """
    gc.unfreeze()
