from typing import (Optional, Tuple, Type,
                    TypeVar)
from typing_extensions import Protocol

from app.data.database.components import Component
from app.utilities.data import Data
from app.utilities.typing import NID

class HasComponents(Protocol):
    nid: NID
    name: str
    desc: str
    components: Data[Component]
    icon_nid: Optional[NID]
    icon_index: Tuple[int, int]

T = TypeVar('T', bound=HasComponents)