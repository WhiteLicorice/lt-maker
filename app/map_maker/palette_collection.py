from typing import Any, Dict
import glob, json, os

from dataclasses import dataclass, field

from app.utilities.data import Data
from app.map_maker.terrain import Terrain
from app.map_maker.qt_renderers.qt_palette import QtPalette

@dataclass
class PaletteCollection:
    nid: str
    name: str
    author: str
    palette_dir: str
    outdoor: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    palettes: Dict[Terrain, QtPalette] = field(default_factory=dict)

    def get(self, terrain: Terrain) -> QtPalette:
        return self.palettes.get(terrain)

    def load_palettes(self):
        self.palettes = {
            # Outdoors
            Terrain.GRASS: QtPalette(self, os.path.join(self.palette_dir, 'grass.png')),
            Terrain.LIGHT_GRASS: QtPalette(self, os.path.join(self.palette_dir, 'grass.png')),
            Terrain.NOISY_GRASS: QtPalette(self, os.path.join(self.palette_dir, 'grass.png')),
            Terrain.SAND: QtPalette(self, os.path.join(self.palette_dir, 'sand.png')),
            Terrain.ROAD: QtPalette(self, os.path.join(self.palette_dir, 'road.png')),
            Terrain.RIVER: QtPalette(self, os.path.join(self.palette_dir, 'river.png'), os.path.join(self.palette_dir, 'river_autotiles.png')),
            Terrain.SEA: QtPalette(self, os.path.join(self.palette_dir, 'sea.png'), os.path.join(self.palette_dir,  'sea_autotiles.png')),
            Terrain.SPARSE_FOREST: QtPalette(self, os.path.join(self.palette_dir, 'sparse_forest.png')),
            Terrain.FOREST: QtPalette(self, os.path.join(self.palette_dir, 'forest.png')),
            Terrain.THICKET: QtPalette(self, os.path.join(self.palette_dir, 'thicket.png')),
            Terrain.HILL: QtPalette(self, os.path.join(self.palette_dir, 'hill.png')),
            Terrain.MOUNTAIN: QtPalette(self, os.path.join(self.palette_dir, 'mountain.png')),
            Terrain.CLIFF: QtPalette(self, os.path.join(self.palette_dir, 'cliff.png')),
            Terrain.BRIDGEH: QtPalette(self, os.path.join(self.palette_dir, 'bridge_h.png')),
            Terrain.BRIDGEV: QtPalette(self, os.path.join(self.palette_dir, 'bridge_v.png')),
            Terrain.CASTLE: QtPalette(self, os.path.join(self.palette_dir, 'castle.png')),
            Terrain.HOUSE: QtPalette(self, os.path.join(self.palette_dir, 'house.png')),
            Terrain.RUINS: QtPalette(self, os.path.join(self.palette_dir, 'ruins.png')),
            # Indoors
            Terrain.VOID: QtPalette(self, os.path.join(self.palette_dir, 'void.png')),
            Terrain.FLOOR_1: QtPalette(self, os.path.join(self.palette_dir, 'floor1.png'), shading_fn=os.path.join(self.palette_dir, 'floor1_shading.png')),
            Terrain.FLOOR_2: QtPalette(self, os.path.join(self.palette_dir, 'floor2.png'), shading_fn=os.path.join(self.palette_dir, 'floor2_shading.png')),
            Terrain.FLOOR_3: QtPalette(self, os.path.join(self.palette_dir, 'floor3.png'), shading_fn=os.path.join(self.palette_dir, 'floor3_shading.png')),
            Terrain.WALL_TOP: QtPalette(self, os.path.join(self.palette_dir, 'wall_top.png')),
            Terrain.WALL_BOTTOM: QtPalette(self, os.path.join(self.palette_dir, 'wall_bottom.png')),
            Terrain.COLUMN: QtPalette(self, os.path.join(self.palette_dir, 'column.png')),
            Terrain.STAIRS_UPDOWN: QtPalette(self, os.path.join(self.palette_dir, 'stairs_updown.png')),
            Terrain.STAIRS_LEFT: QtPalette(self, os.path.join(self.palette_dir, 'stairs_left.png')),
            Terrain.STAIRS_RIGHT: QtPalette(self, os.path.join(self.palette_dir, 'stairs_right.png')),
            Terrain.STAIRS_CENTER: QtPalette(self, os.path.join(self.palette_dir, 'stairs_center.png')),
            Terrain.PILLAR: QtPalette(self, os.path.join(self.palette_dir, 'pillar.png')),
            Terrain.POOL: QtPalette(self, 
                                    os.path.join(self.palette_dir, 'pool.png'), 
                                    os.path.join(self.palette_dir, 'pool_autotiles.png'), 
                                    shading_fn=os.path.join(self.palette_dir, 'pool_shading.png')),
            Terrain.POOL_BRIDGE: QtPalette(self, os.path.join(self.palette_dir, 'pool_bridge.png')),
            Terrain.TREASURE: QtPalette(self, os.path.join(self.palette_dir, 'treasure.png')),
        }

class MapMakerPaletteCatalog(Data[PaletteCollection]):
    datatype = PaletteCollection

    def outdoor_palettes(self) -> Data[PaletteCollection]:
        return Data([p for p in self.values() if p.outdoor])

    def indoor_palettes(self) -> Data[PaletteCollection]:
        return Data([p for p in self.values() if not p.outdoor])

def load_all_palettes():
    valid_palette_folders = glob.glob('app/map_maker/palettes/*')
    for fn in valid_palette_folders:
        metadata_path = os.path.join(fn, 'metadata.json')
        if os.path.isdir(fn) and os.path.exists(metadata_path):
            # Read metadata
            with open(metadata_path) as fp:
                metadata = json.load(fp)
                new_palette = PaletteCollection(
                    metadata['name'], 
                    metadata['name'], 
                    metadata['author'], 
                    fn, 
                    metadata.get('outdoor', True),
                    metadata
                )
                new_palette.load_palettes()
                PALETTES.append(new_palette)

PALETTES = MapMakerPaletteCatalog()
load_all_palettes()
