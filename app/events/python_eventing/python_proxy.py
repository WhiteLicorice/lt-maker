from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

class PythonProxy:
    def __init__(self, name: str, getter: Callable[[], Any]):
        self._name = name
        self._getter = getter

    def _resolve(self):
        """Check if the target has already been set somewhere else."""
        target = self._getter()
        if target is None:
            raise NameError(f"name {self._name!r} is not defined")
        return target

    def __getattr__(self, attr):
        return getattr(self._resolve(), attr)

    def __eq__(self, other):
        return self._resolve() == other
    
    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return repr(self._resolve())