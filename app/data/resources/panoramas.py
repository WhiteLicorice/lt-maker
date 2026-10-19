from pathlib import Path
from typing import List, Optional, override

from app.data.resources.base_catalog import ManifestCatalog
from app.data.resources.resource_prefab import WithResources
from app.utilities.data import Prefab

class Panorama(WithResources, Prefab):
    """
    A collection of background images
    """
    def __init__(self, nid, full_path=None, num_frames=0):
        self.nid = nid
        self.full_path = full_path  # Ignores numbers at the end
        self.num_frames = num_frames
        self.images = []
        self.pixmaps = []

        # self.idx = 0

    @override
    def set_full_path(self, full_path):
        self.full_path = full_path

    @override
    def used_resources(self) -> List[Optional[Path]]:
        paths = self.get_all_paths()
        return [Path(path) for path in paths]

    def get_all_paths(self):
        paths = []
        if self.num_frames == 1:
            paths.append(self.full_path)
        else:
            for idx in range(self.num_frames):
                path = self.full_path[:-4] + str(idx) + '.png'
                paths.append(path)
        return paths

    def save(self):
        return (self.nid, self.num_frames)

    @classmethod
    def restore(cls, s_tuple):
        self = cls(s_tuple[0], num_frames=s_tuple[1])
        return self

class PanoramaCatalog(ManifestCatalog[Panorama]):
    manifest = 'panoramas.json'
    title = 'panoramas'
    datatype = Panorama
