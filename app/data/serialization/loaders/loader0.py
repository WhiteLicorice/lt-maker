import logging
import os
from pathlib import Path
from typing import List
from app.data.database import database
from app.data.resources import resources
from app.data.serialization.loaders.loader_base import LoaderBase
from app.utilities.data_order import parse_order_keys_file
from app.utilities.serialization import load_json
from app.utilities.typing import NestedPrimitiveDict

class Loader0(LoaderBase):
    def load_database(self, data_dir: Path) -> NestedPrimitiveDict:
        return _load_as_dict(data_dir)

    def load_resources(self, resource_dir: Path) -> NestedPrimitiveDict:
        as_dict = {}
        for key in resources.Resources.save_data_types:
            if not (resource_dir / key).exists():
                raise FileNotFoundError(f"Resource directory {resource_dir / key} does not exist!\nPlease recover or copy from default.ltproj the missing directory.")
            if key == 'combat_palettes': # special case
                as_dict[key] = _json_load(resource_dir / key, 'palette_data')
            elif key == 'tilemaps': # special case
                as_dict[key] = _json_load(resource_dir / key, 'tilemap_data')
            else:
                as_dict[key] = _load_manifest_or_prefabs(resource_dir, key)
        return as_dict

def _load_manifest_or_prefabs(resource_dir: Path, key: str):
    manifest_path = Path(resource_dir / key, key + '.json')
    if manifest_path.exists():
        return load_json(manifest_path)
    else:
        return _json_load(resource_dir, key)

def _load_as_dict(data_dir: Path) -> NestedPrimitiveDict:
    as_dict = {}
    category_suffix = database.CATEGORY_SUFFIX
    for key in database.Database.save_data_types:
        as_dict[key] = _json_load(data_dir, key)
        if as_dict[key] is None:
            raise FileNotFoundError(f"Data directory {data_dir / key} does not exist!\nPlease recover or copy from default.ltproj the missing directory.")
        # Load any of the categories we need
        if Path(data_dir, key + category_suffix + '.json').exists():
            as_dict[key + category_suffix] = _json_load(data_dir, key + category_suffix)
    return as_dict

def _json_load(data_dir: str, key: str):
    data_path = Path(data_dir, key)
    if data_path.exists(): # data type is a directory, browse within
        data_fnames = os.listdir(data_path)
        ordering = []
        if '.orderkeys' in data_fnames:
            ordering = parse_order_keys_file(Path(data_dir, key, '.orderkeys'))
        data_fnames: List[Path] = [Path(data_dir, key, fname) for fname in data_fnames if fname.endswith('.json')]
        data_fnames = sorted(data_fnames, key=lambda fname: ordering.index(fname.stem) if fname.stem in ordering else 99999)
        full_data = []
        for fname in data_fnames:
            full_data += load_json(fname)
        return full_data
    else:   # data type is a singular file
        save_loc = Path(data_dir, key + '.json')
        if not save_loc.exists():
            logging.warning("%s does not exist!", save_loc)
            return None
        return load_json(save_loc)