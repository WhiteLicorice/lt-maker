from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from app.data.serialization.dataclass_serialization import dataclass_from_dict

@dataclass
class Metadata():
    date: str = ""
    engine_version: str = ""
    serialization_version: int = 0
    project: str = ""
    has_fatal_errors: bool = False
    as_chunks: bool = False

    def save(self) -> dict[str, Any]:
        return asdict(self)
    
    def update(self, updates:dict[str, Any]) -> dict[str, Any]:
        base = self.save()
        base.update(updates)
        return base
        
    def restore(self, d: dict[str, Any]) -> None:
        if not d:
            return
        restored = dataclass_from_dict(self.__class__, d)
        self.__dict__ = restored.__dict__