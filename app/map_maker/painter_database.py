from app.map_maker.terrain import Terrain
from app.map_maker.painter_utils import Painter
from app.map_maker.painters import (
    GrassPainter, 
    LightGrassPainter,
    NoisyGrassPainter,
    SandPainter,
    WangEdge8Painter,
    RiverPainter,
    SeaPainter,
    ForestPainter,
    RandomPainter,
    Random8Painter,
    HillPainter,
    MountainPainter,
    CliffPainter,
    WangEdge16Painter,
    CastlePainter,
    HousePainter,
    RuinsPainter,
    FloorPainter,
    WallTopPainter,
    WallBottomPainter,
    ColumnPainter,
    StairsUpDownPainter,
    StairsLeftPainter,
    StairsRightPainter,
    PoolPainter,
    PoolBridgePainter,
)

PAINTERS = {}

# Outdoor
PAINTERS[Terrain.GRASS] = GrassPainter()
PAINTERS[Terrain.LIGHT_GRASS] = LightGrassPainter()
PAINTERS[Terrain.NOISY_GRASS] = NoisyGrassPainter()
PAINTERS[Terrain.SAND] = SandPainter()
PAINTERS[Terrain.ROAD] = WangEdge8Painter()
PAINTERS[Terrain.ROAD].terrain_like = \
   (Terrain.ROAD, Terrain.SAND, Terrain.BRIDGEH, Terrain.BRIDGEV,
    Terrain.HOUSE, Terrain.CASTLE,
    Terrain.FLOOR_1, Terrain.FLOOR_2, Terrain.FLOOR_3,
    Terrain.STAIRS_LEFT, Terrain.STAIRS_RIGHT, Terrain.STAIRS_UPDOWN
    )
PAINTERS[Terrain.ROAD].base_coord = (15, 0)
PAINTERS[Terrain.RIVER] = RiverPainter()
PAINTERS[Terrain.SEA] = SeaPainter()
PAINTERS[Terrain.SPARSE_FOREST] = RandomPainter()
PAINTERS[Terrain.SPARSE_FOREST].data = [(0, 0), (0, 1), (0, 2)]
PAINTERS[Terrain.FOREST] = ForestPainter()
PAINTERS[Terrain.THICKET] = Random8Painter()
PAINTERS[Terrain.THICKET].data = [
   (x, y) for x in range(3) for y in range(3)
]
PAINTERS[Terrain.HILL] = HillPainter()
PAINTERS[Terrain.MOUNTAIN] = MountainPainter()
PAINTERS[Terrain.CLIFF] = CliffPainter()
PAINTERS[Terrain.BRIDGEH] = WangEdge16Painter()
PAINTERS[Terrain.BRIDGEH].terrain_like = (Terrain.BRIDGEH, )
PAINTERS[Terrain.BRIDGEV] = WangEdge16Painter()
PAINTERS[Terrain.BRIDGEV].terrain_like = (Terrain.BRIDGEV, )
PAINTERS[Terrain.CASTLE] = CastlePainter()
PAINTERS[Terrain.HOUSE] = HousePainter()
PAINTERS[Terrain.RUINS] = RuinsPainter()

# Indoor
PAINTERS[Terrain.VOID] = Painter()
PAINTERS[Terrain.WALL_TOP] = WallTopPainter()
PAINTERS[Terrain.WALL_BOTTOM] = WallBottomPainter()
PAINTERS[Terrain.COLUMN] = ColumnPainter()
PAINTERS[Terrain.FLOOR_1] = FloorPainter()
PAINTERS[Terrain.FLOOR_2] = FloorPainter()
PAINTERS[Terrain.FLOOR_3] = FloorPainter()
PAINTERS[Terrain.STAIRS_UPDOWN] = StairsUpDownPainter()
PAINTERS[Terrain.STAIRS_LEFT] = StairsLeftPainter()
PAINTERS[Terrain.STAIRS_RIGHT] = StairsRightPainter()
PAINTERS[Terrain.STAIRS_CENTER] = RandomPainter()
PAINTERS[Terrain.STAIRS_CENTER].data = [(0, 0), (1, 0)]
PAINTERS[Terrain.PILLAR] = Painter()
PAINTERS[Terrain.POOL] = PoolPainter()
PAINTERS[Terrain.POOL_BRIDGE] = PoolBridgePainter()
PAINTERS[Terrain.TREASURE] = Painter()
