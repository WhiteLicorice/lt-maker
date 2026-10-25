from __future__ import annotations
from typing import Any, Dict
import glob, json, os

from dataclasses import dataclass, field

from app.utilities.data import Data
from app.map_maker.terrain import Terrain

@dataclass
class Palette:
    """Framework-agnostic record of where a terrain's tileset images live.
    The qt_renderers and pygame_renderers packages wrap this with their own
    image caches (QtPalette / PygamePalette)."""
    parent: PaletteCollection
    fn: str
    autotile_fn: str = None
    shading_fn: str = None

@dataclass
class PaletteCollection:
    nid: str
    name: str
    author: str
    palette_dir: str
    outdoor: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    palettes: Dict[Terrain, Palette] = field(default_factory=dict)

    def get(self, terrain: Terrain) -> Palette:
        return self.palettes.get(terrain)

    def load_palettes(self):
        self.palettes = {
            # Outdoors
            Terrain.GRASS: Palette(self, os.path.join(self.palette_dir, 'grass.png')),
            Terrain.LIGHT_GRASS: Palette(self, os.path.join(self.palette_dir, 'grass.png')),
            Terrain.NOISY_GRASS: Palette(self, os.path.join(self.palette_dir, 'grass.png')),
            Terrain.SAND: Palette(self, os.path.join(self.palette_dir, 'sand.png')),
            Terrain.ROAD: Palette(self, os.path.join(self.palette_dir, 'road.png')),
            Terrain.RIVER: Palette(self, os.path.join(self.palette_dir, 'river.png'), os.path.join(self.palette_dir, 'river_autotiles.png')),
            Terrain.SEA: Palette(self, os.path.join(self.palette_dir, 'sea.png'), os.path.join(self.palette_dir,  'sea_autotiles.png')),
            Terrain.SPARSE_FOREST: Palette(self, os.path.join(self.palette_dir, 'sparse_forest.png')),
            Terrain.FOREST: Palette(self, os.path.join(self.palette_dir, 'forest.png')),
            Terrain.THICKET: Palette(self, os.path.join(self.palette_dir, 'thicket.png')),
            Terrain.HILL: Palette(self, os.path.join(self.palette_dir, 'hill.png')),
            Terrain.MOUNTAIN: Palette(self, os.path.join(self.palette_dir, 'mountain.png')),
            Terrain.CLIFF: Palette(self, os.path.join(self.palette_dir, 'cliff.png')),
            Terrain.DESERT: Palette(self, os.path.join(self.palette_dir, 'desert.png')),
            Terrain.DESERT_CLIFF: Palette(self, os.path.join(self.palette_dir, 'desert_cliff.png')),
            Terrain.DESERT_ROCK: Palette(self, os.path.join(self.palette_dir, 'desert_rock.png')),
            Terrain.BRIDGEH: Palette(self, os.path.join(self.palette_dir, 'bridge_h.png')),
            Terrain.BRIDGEV: Palette(self, os.path.join(self.palette_dir, 'bridge_v.png')),
            Terrain.CASTLE: Palette(self, os.path.join(self.palette_dir, 'castle.png')),
            Terrain.HOUSE: Palette(self, os.path.join(self.palette_dir, 'house.png')),
            Terrain.RUINS: Palette(self, os.path.join(self.palette_dir, 'ruins.png')),
            # Indoors
            Terrain.VOID: Palette(self, os.path.join(self.palette_dir, 'void.png')),
            Terrain.FLOOR_1: Palette(self, os.path.join(self.palette_dir, 'floor1.png'), shading_fn=os.path.join(self.palette_dir, 'floor1_shading.png')),
            Terrain.FLOOR_2: Palette(self, os.path.join(self.palette_dir, 'floor2.png'), shading_fn=os.path.join(self.palette_dir, 'floor2_shading.png')),
            Terrain.FLOOR_3: Palette(self, os.path.join(self.palette_dir, 'floor3.png'), shading_fn=os.path.join(self.palette_dir, 'floor3_shading.png')),
            Terrain.WALL_TOP: Palette(self, os.path.join(self.palette_dir, 'wall_top.png')),
            Terrain.WALL_BOTTOM: Palette(self, os.path.join(self.palette_dir, 'wall_bottom.png')),
            Terrain.COLUMN: Palette(self, os.path.join(self.palette_dir, 'column.png')),
            Terrain.STAIRS_UPDOWN: Palette(self, os.path.join(self.palette_dir, 'stairs_updown.png')),
            Terrain.STAIRS_LEFT: Palette(self, os.path.join(self.palette_dir, 'stairs_left.png')),
            Terrain.STAIRS_RIGHT: Palette(self, os.path.join(self.palette_dir, 'stairs_right.png')),
            Terrain.STAIRS_CENTER: Palette(self, os.path.join(self.palette_dir, 'stairs_center.png')),
            Terrain.PILLAR: Palette(self, os.path.join(self.palette_dir, 'pillar.png')),
            Terrain.POOL: Palette(self, 
                                    os.path.join(self.palette_dir, 'pool.png'), 
                                    os.path.join(self.palette_dir, 'pool_autotiles.png'), 
                                    shading_fn=os.path.join(self.palette_dir, 'pool_shading.png')),
            Terrain.POOL_BRIDGE: Palette(self, os.path.join(self.palette_dir, 'pool_bridge.png'),
                                         shading_fn=os.path.join(self.palette_dir, 'pool_bridge.png')),
            Terrain.TREASURE: Palette(self, os.path.join(self.palette_dir, 'treasure.png')),
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
