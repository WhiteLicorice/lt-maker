import os
from pathlib import Path
import shutil
from typing import List, Optional, Set
from typing_extensions import override

from app.data.category import CategorizedCatalog
from app.data.resources.base_catalog import ManifestCatalog
from app.data.resources.resource_prefab import WithResources
from app.utilities.data import Data, Prefab
from app.utilities.typing import NID, NestedPrimitiveDict

class MapSprite(WithResources, Prefab):
    def __init__(self, nid, stand_full_path=None, move_full_path=None):
        self.nid: NID = nid
        self.stand_full_path: Optional[str] = stand_full_path
        self.move_full_path: Optional[str] = move_full_path
        self.standing_image = None
        self.moving_image = None
        self.standing_pixmap = None
        self.moving_pixmap = None
        self.frames = Data()
        self.palettes = []  # Palette name -> Palette nid

    def set_stand_full_path(self, full_path):
        self.stand_full_path = full_path

    def set_move_full_path(self, full_path):
        self.move_full_path = full_path

    def save(self):
        return self.nid

    @override
    def set_full_path(self, path: str) -> None:
        parent_path = Path(path).parent
        self.set_stand_full_path(str(parent_path / (self.nid + '-stand.png')))
        self.set_move_full_path(str(parent_path / (self.nid + '-move.png')))

    @override
    def used_resources(self) -> List[Optional[Path]]:
        return [Path(self.stand_full_path), Path(self.move_full_path)]

    @classmethod
    def restore(cls, s):
        self = cls(s)
        return self

class MapSpriteCatalog(ManifestCatalog[MapSprite], CategorizedCatalog[MapSprite]):
    manifest = 'map_sprites.json'
    title = 'map sprites'
    datatype = MapSprite