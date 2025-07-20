from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Optional

from app.utilities.typing import NID

if TYPE_CHECKING:
    from app.events.event import Event


class PythonProxy:
    """Used to proxy late bound local arguments in an Event object for use in #pyev1."""
    def __init__(self, name: str, event_nid: NID):
        self._name = name
        self._nid = event_nid
        # For lazy initialization.
        self._event: Optional[Event] = None

    def _resolve(self):
        """Check if the target has already been set somewhere else, in the event's attributes."""
        # Lazily rebuild the event pointer during runtime so we avoid race conditions when unpickling.
        if not self._event:
            self._event = PythonProxy._rebuild_event_pointer(self._nid)
        target = getattr(self._event, self._name, None)
        if target is None:
            logging.info(f"name {self._name!r} is not defined")
        return target

    def __getattr__(self, attr):
        return getattr(self._resolve(), attr)

    def __eq__(self, other):
        return self._resolve() == other
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __bool__(self):
        return bool(self._resolve())

    def __repr__(self):
        return repr(self._resolve())
    
    def __reduce__(self):
        # On save: pickle self._name and self._nid - safe because these are strings
        # On load: create a new PythonProxy object with self._name & self._nid as constructor args.
        return (PythonProxy, (self._name, self._nid))
    
    @staticmethod
    def _rebuild_event_pointer(nid: NID) -> Event:
        """
            Takes an event NID and finds the matching Event instance
            in the current game state. This is slow, but necessary,
            to avoid standing issues with pickling an Event object.
            The Event object is lazily cached during runtime to alleviate pain.
        """
        from app.engine.game_state import game
        for ev in game.events.all_events:
            if ev.nid == nid:
                return ev
        # Ugh some schmuck is inevitably gonna do something stupid like this somehow so we have to account for it?
        # But this normally shouldn't happen...
        logging.error(f"Event with {nid} not found in the game registry. Perhaps you deleted an event then loaded a bad save?")
        return game.events.all_events[0]
