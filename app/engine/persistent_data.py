try:
    import cPickle as pickle
except ImportError:
    import pickle
import logging
import os
import time

def _retry_while_in_use(func, *args):
    """Windows refuses to open or replace a file for the moment another process
    has it open or is swapping it (the tests run in parallel, a virus scanner,
    a sync client), so this tries again for up to half a second"""
    for _ in range(50):
        try:
            return func(*args)
        except PermissionError:
            time.sleep(0.01)
    return func(*args)

def _write(location, data):
    """Pickles the data into a file of its own, then swaps that in for the old
    file, so a save that dies part way leaves the old file whole and a reader
    never opens a half-written one. The process id keeps two processes saving
    at once (the tests, run in parallel) out of each other's file"""
    temp_location = '%s.%d.tmp' % (location, os.getpid())
    try:
        with open(temp_location, 'wb') as fp:
            pickle.dump(data, fp)
        _retry_while_in_use(os.replace, temp_location, location)
    finally:
        if os.path.exists(temp_location):
            os.remove(temp_location)

def serialize(location, data):
    logging.info("Saving persistent data to %s", location)
    try:
        _write(location, data)
    except TypeError as e:
        # There's a surface somewhere in the dictionary of things to save...
        print(data)
        print(e)

def _read(location):
    with open(location, 'rb') as fp:
        return pickle.load(fp)

def deserialize(location):
    logging.info("Loading persistent data from %s", location)
    try:
        return _retry_while_in_use(_read, location)
    except FileNotFoundError:
        logging.info("No persistent data file found at %s", location)

def clear(location):
    logging.info("Clearing data in %s", location)
    _write(location, [])
