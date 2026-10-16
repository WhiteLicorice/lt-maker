from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, List
if TYPE_CHECKING:
    from app.data.database.database import Database
from app.utilities.data import Data, Prefab
from app.utilities import str_utils


@dataclass
class Tag(Prefab):
    nid: str = None

    def save(self):
        return self.nid

    @classmethod
    def restore(cls, dat):
        return cls(dat)

class TagCatalog(Data[Tag]):
    datatype = Tag
    default_tags = [
        'Lord', 'Boss', 'Required', 'Mounted', 'Flying', 'Armor', 'Dragon',
        'AutoPromote', 'NoAutoPromote', 'Convoy', 'AdjConvoy','Tile', 'Blacklist',
        'ZeroMove', 'Horse', 'SlowMove'
    ]

    def __init__(self, strs: List[str] = None):
        super().__init__()
        for s in self.default_tags:
            self.append(Tag(s))
        if strs is not None:
            for s in strs:
                if s not in self.default_tags:
                    self.append(Tag(s))

    def add_new_default(self, db: Database) -> Tag:
        nid = str_utils.get_next_name("New Tag", self.keys())
        new_tag = Tag(nid)
        self.append(new_tag)
        return new_tag
