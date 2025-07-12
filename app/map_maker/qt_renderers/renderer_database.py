from app.map_maker.terrain import Terrain
from app.map_maker.qt_renderers import (
    SimpleRenderer,
    SimpleRenderer8,
    SeaRenderer,
    DisplayRenderer8,
    LimitRenderer8,
    LimitRenderer16,
    CliffRenderer,
    MountainRenderer,
    SimpleShadingRenderer,
    PoolShadingRenderer,
    FloorShadingRenderer,
)
from app.map_maker.palette_collection import PALETTES
from app.map_maker.painter_database import PAINTERS

RENDERERS = {}

# Outdoor
RENDERERS[Terrain.GRASS] = \
    SimpleRenderer8(PAINTERS[Terrain.GRASS], 
                    PALETTES.outdoor_palettes()[0].get(Terrain.GRASS))
RENDERERS[Terrain.LIGHT_GRASS] = \
    LimitRenderer8(PAINTERS[Terrain.LIGHT_GRASS], 
                   PALETTES.outdoor_palettes()[0].get(Terrain.LIGHT_GRASS))
RENDERERS[Terrain.NOISY_GRASS] = \
    LimitRenderer8(PAINTERS[Terrain.NOISY_GRASS], 
                   PALETTES.outdoor_palettes()[0].get(Terrain.NOISY_GRASS))
RENDERERS[Terrain.SAND] = \
    LimitRenderer8(PAINTERS[Terrain.SAND],
                   PALETTES.outdoor_palettes()[0].get(Terrain.SAND))
RENDERERS[Terrain.ROAD] = \
    LimitRenderer8(PAINTERS[Terrain.ROAD],
                   PALETTES.outdoor_palettes()[0].get(Terrain.ROAD))
RENDERERS[Terrain.RIVER] = \
    LimitRenderer8(PAINTERS[Terrain.RIVER],
                   PALETTES.outdoor_palettes()[0].get(Terrain.RIVER))
RENDERERS[Terrain.SEA] = \
    SeaRenderer(PAINTERS[Terrain.SEA],
                PALETTES.outdoor_palettes()[0].get(Terrain.SEA))
RENDERERS[Terrain.SPARSE_FOREST] = \
    SimpleRenderer(PAINTERS[Terrain.SPARSE_FOREST],
                   PALETTES.outdoor_palettes()[0].get(Terrain.SPARSE_FOREST))
RENDERERS[Terrain.FOREST] = \
    DisplayRenderer8(PAINTERS[Terrain.FOREST],
                     PALETTES.outdoor_palettes()[0].get(Terrain.FOREST))
RENDERERS[Terrain.THICKET] = \
    DisplayRenderer8(PAINTERS[Terrain.THICKET],
                     PALETTES.outdoor_palettes()[0].get(Terrain.THICKET))
RENDERERS[Terrain.HILL] = \
    SimpleRenderer(PAINTERS[Terrain.HILL],
                   PALETTES.outdoor_palettes()[0].get(Terrain.HILL))
RENDERERS[Terrain.MOUNTAIN] = \
    MountainRenderer(PAINTERS[Terrain.MOUNTAIN],
                     PALETTES.outdoor_palettes()[0].get(Terrain.MOUNTAIN))
RENDERERS[Terrain.CLIFF] = \
    CliffRenderer(PAINTERS[Terrain.CLIFF],
                  PALETTES.outdoor_palettes()[0].get(Terrain.CLIFF))
RENDERERS[Terrain.BRIDGEH] = \
    LimitRenderer16(PAINTERS[Terrain.BRIDGEH],
                    PALETTES.outdoor_palettes()[0].get(Terrain.BRIDGEH))
RENDERERS[Terrain.BRIDGEV] = \
    LimitRenderer16(PAINTERS[Terrain.BRIDGEV],
                    PALETTES.outdoor_palettes()[0].get(Terrain.BRIDGEV))
RENDERERS[Terrain.CASTLE] = \
    SimpleRenderer(PAINTERS[Terrain.CASTLE],
                   PALETTES.outdoor_palettes()[0].get(Terrain.CASTLE))
RENDERERS[Terrain.RUINS] = \
    SimpleRenderer(PAINTERS[Terrain.RUINS],
                   PALETTES.outdoor_palettes()[0].get(Terrain.RUINS))
RENDERERS[Terrain.HOUSE] = \
    SimpleRenderer(PAINTERS[Terrain.HOUSE],
                   PALETTES.outdoor_palettes()[0].get(Terrain.HOUSE))

# Indoors
RENDERERS[Terrain.VOID] = \
    SimpleRenderer(PAINTERS[Terrain.VOID],
                   PALETTES.indoor_palettes()[0].get(Terrain.VOID))
RENDERERS[Terrain.FLOOR_1] = \
    FloorShadingRenderer('floor1',
                         PALETTES.indoor_palettes()[0].get(Terrain.FLOOR_1))
RENDERERS[Terrain.FLOOR_2] = \
    FloorShadingRenderer('floor2',
                         PALETTES.indoor_palettes()[0].get(Terrain.FLOOR_2))
RENDERERS[Terrain.FLOOR_3] = \
    FloorShadingRenderer('floor3',
                         PALETTES.indoor_palettes()[0].get(Terrain.FLOOR_3))
RENDERERS[Terrain.WALL_TOP] = \
    LimitRenderer16(PAINTERS[Terrain.WALL_TOP],
                    PALETTES.indoor_palettes()[0].get(Terrain.WALL_TOP))
RENDERERS[Terrain.WALL_BOTTOM] = \
    SimpleRenderer(PAINTERS[Terrain.WALL_BOTTOM],
                   PALETTES.indoor_palettes()[0].get(Terrain.WALL_BOTTOM))
RENDERERS[Terrain.COLUMN] = \
    SimpleRenderer(PAINTERS[Terrain.COLUMN],
                   PALETTES.indoor_palettes()[0].get(Terrain.COLUMN))
RENDERERS[Terrain.STAIRS_UPDOWN] = \
    SimpleRenderer(PAINTERS[Terrain.STAIRS_UPDOWN],
                   PALETTES.indoor_palettes()[0].get(Terrain.STAIRS_UPDOWN))
RENDERERS[Terrain.STAIRS_LEFT] = \
    SimpleRenderer(PAINTERS[Terrain.STAIRS_LEFT],
                   PALETTES.indoor_palettes()[0].get(Terrain.STAIRS_LEFT))
RENDERERS[Terrain.STAIRS_RIGHT] = \
    SimpleRenderer(PAINTERS[Terrain.STAIRS_RIGHT],
                   PALETTES.indoor_palettes()[0].get(Terrain.STAIRS_RIGHT))
RENDERERS[Terrain.STAIRS_CENTER] = \
    SimpleRenderer(PAINTERS[Terrain.STAIRS_CENTER],
                   PALETTES.indoor_palettes()[0].get(Terrain.STAIRS_CENTER))
RENDERERS[Terrain.PILLAR] = \
    SimpleRenderer(PAINTERS[Terrain.PILLAR],
                   PALETTES.indoor_palettes()[0].get(Terrain.PILLAR))
RENDERERS[Terrain.POOL] = \
    PoolShadingRenderer(PAINTERS[Terrain.POOL],
                        PALETTES.indoor_palettes()[0].get(Terrain.POOL))
RENDERERS[Terrain.POOL_BRIDGE] = \
    SimpleShadingRenderer(PAINTERS[Terrain.POOL_BRIDGE],
                          PALETTES.indoor_palettes()[0].get(Terrain.POOL_BRIDGE))
RENDERERS[Terrain.TREASURE] = \
    SimpleRenderer(PAINTERS[Terrain.TREASURE],
                   PALETTES.indoor_palettes()[0].get(Terrain.TREASURE))