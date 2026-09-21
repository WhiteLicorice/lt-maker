from __future__ import annotations

from dataclasses import dataclass, field
from typing import Set

from app.utilities.typing import Pos

@dataclass(frozen=True)
class MoveSelection:
    """Where a unit may move right now.

    The move highlights and the cursor's movement borders key off this, so
    what the player is shown and what the player is allowed to do cannot drift apart.

    walkable: reachable by spending normal movement, on foot
    warp: teleport destinations (witch warp), reachable regardless of movement cost
    xcom: reachable only by also spending xcom movement
    """
    walkable: Set[Pos] = field(default_factory=set)
    warp: Set[Pos] = field(default_factory=set)
    xcom: Set[Pos] = field(default_factory=set)

    @property
    def normal(self) -> Set[Pos]:
        """Everything reachable without dipping into xcom movement."""
        return self.walkable | self.warp

    def __contains__(self, position: Pos) -> bool:
        return position in self.walkable or position in self.warp or position in self.xcom

    def __bool__(self) -> bool:
        return bool(self.walkable or self.warp or self.xcom)

    def is_warp(self, position: Pos) -> bool:
        """Whether arriving here means teleporting rather than walking.

        A warp destination the unit could also have walked to is walked to -- the unit
        keeps the ordinary move so the path arrow it was just shown is what it follows.
        """
        return position in self.warp and position not in self.walkable
