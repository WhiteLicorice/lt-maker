import os
from pathlib import Path
import shutil
from typing import List, Optional, Set
from typing_extensions import override

from app.data.resources.base_catalog import ManifestCatalog
from app.data.resources.resource_prefab import WithResources
from app.utilities.data import HasNid, Prefab
from app.utilities.typing import NestedPrimitiveDict

class SongPrefab(HasNid, WithResources, Prefab):
    def __init__(self, nid, full_path=None):
        self.nid = nid
        self.full_path = full_path
        # self.length = None

        # Mutually exclusive. Can't have both start and battle versions
        self.intro_full_path = None
        self.battle_full_path = None

        # Consecutive unique positive int, or 0 (e.g: 0, 0, 0, 0, 1, 2, 3, 4)
        self.soundroom_idx: int = 0
        
        #Name to display in the sound room
        self.display_name = nid

    def set_intro_full_path(self, full_path):
        self.intro_full_path = full_path

    def set_battle_full_path(self, full_path):
        self.battle_full_path = full_path

    def full_save(self):
        return (self.nid, self.intro_full_path, self.battle_full_path, self.soundroom_idx, self.display_name)

    def save(self):
        return (self.nid, True if self.intro_full_path else False, True if self.battle_full_path else False, self.soundroom_idx, self.display_name)

    @override
    def set_full_path(self, path: str) -> None:
        self.full_path = path
        parent_path = Path(path).parent
        if self.battle_full_path:
            self.set_battle_full_path(str(parent_path / (self.nid + '-battle.ogg')))
        if self.intro_full_path:
            self.set_intro_full_path(str(parent_path / (self.nid + '-intro.ogg')))

    @override
    def used_resources(self) -> List[Optional[Path]]:
        paths = [Path(self.full_path)]
        paths.append(Path(self.intro_full_path) if self.intro_full_path else None)
        paths.append(Path(self.battle_full_path) if self.battle_full_path else None)
        return paths

    @classmethod
    def restore(cls, s_tuple):
        self = cls(s_tuple[0])
        self.intro_full_path = s_tuple[1]
        self.battle_full_path = s_tuple[2]
        if len(s_tuple) > 3:
            self.soundroom_idx = s_tuple[3]
        if len(s_tuple) > 4:
            self.display_name = s_tuple[4]
        return self

class MusicCatalog(ManifestCatalog[SongPrefab]):
    filetype = '.ogg'
    manifest = 'music.json'
    title = 'music'
    datatype = SongPrefab

class SFXPrefab(HasNid, WithResources, Prefab):
    def __init__(self, nid, full_path=None, tag=None):
        self.nid = nid
        self.tag = tag
        # self.length = None
        self.full_path = full_path

    @override
    def set_full_path(self, full_path):
        self.full_path = full_path

    @override
    def used_resources(self) -> List[Optional[Path]]:
        return [Path(self.full_path)]

    def save(self):
        return (self.nid, self.tag)

    @classmethod
    def restore(cls, s_tuple):
        self = cls(s_tuple[0], tag=s_tuple[1])
        # if len(s_tuple) > 2:
        #     self.length = s_tuple[2]
        return self

class SFXCatalog(ManifestCatalog[SFXPrefab]):
    manifest = 'sfx.json'
    title = 'sfx'
    filetype = '.ogg'
    datatype = SFXPrefab
