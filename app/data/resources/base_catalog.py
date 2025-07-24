import os
from pathlib import Path
import shutil
import filecmp
from typing import List, Set, Type, TypeVar, Union

from app.data.resources.resource_prefab import WithResources
from app.utilities.data import Data, Prefab

import logging

from app.utilities.typing import NID, NestedPrimitiveDict

M = TypeVar('M', bound=Union[WithResources, Prefab])
class ManifestCatalog(Data[M]):
    filetype = '.png'
    manifest = None  # To be implemented
    title = ''  # To be implemented
    datatype: Type[M] = None  # To be implemented

    def load(self, loc, resource_dict: NestedPrimitiveDict):
        for s_dict in resource_dict:
            new_resource: M = self.datatype.restore(s_dict)
            new_resource.set_full_path(os.path.join(loc, new_resource.nid + self.filetype))
            self.append(new_resource)

    def update_nid(self, val: M, nid: NID, set_nid=True):
        used_resources = val.used_resources()
        super().update_nid(val, nid, set_nid)
        if not used_resources:
            return
        val.set_full_path(os.path.join(os.path.dirname(used_resources[0]), val.nid + self.filetype))
        new_resource_paths = val.used_resources()
        for old_resource, new_resource in zip(used_resources, new_resource_paths):
            if old_resource and new_resource and old_resource != new_resource:
                try:
                    self.make_copy(old_resource, new_resource)
                except shutil.SameFileError:
                    os.rename(old_resource, new_resource)

    def save_resources(self, loc):
        for datum in self:
            original_resources = datum.used_resources()
            datum.set_full_path(os.path.join(loc, datum.nid + self.filetype))
            new_resource_locs = datum.used_resources()
            for old_loc, new_loc in zip(original_resources, new_resource_locs):
                if not old_loc:
                    continue
                if os.path.abspath(old_loc) != os.path.abspath(new_loc):
                    try:
                        self.make_copy(old_loc, new_loc)
                    except shutil.SameFileError:  # windows filesystem doesn't distinguish between capitals
                        os.rename(old_loc, new_loc)

    def make_copy(self, old_full_path, new_full_path):
        if os.path.exists(old_full_path):
            if os.path.exists(new_full_path) and filecmp.cmp(old_full_path, new_full_path, shallow=False):
                pass  # Identical files
            else:
                shutil.copy(old_full_path, new_full_path)
        else:
            logging.warning("%s does not exist" % old_full_path)

    def used_resources(self) -> Set[Path]:
        resources = set()
        for datum in self:
            resources |= set(datum.used_resources())
        return {r for r in resources if r}

    def get_unused_files(self, loc: str) -> List[str]:
        unused_files = []
        used_files = self.used_resources()
        # in the format of just the filename (e.g. 'test.png')
        valid_filenames: str = {r.name for r in used_files}
        valid_filenames.add(self.manifest)  # also include the manifest file ('manifest.json') otherwise it would be deleted
        valid_filenames.add(self.manifest.replace('.json', '.category.json'))  # also include the category file ('manifest.category.json') otherwise it would be deleted
        for fn in os.listdir(loc):
            if not Path(fn).suffix: # no filetype indicates directory, don't delete directories
                continue
            if fn not in valid_filenames:
                full_fn = os.path.normpath(os.path.join(loc, fn))
                unused_files.append(full_fn)
        return unused_files

    def clean(self, bad_files: List[str]):
        for fn in bad_files:
            logging.warning("Removing %s..." % fn)
            os.remove(fn)
