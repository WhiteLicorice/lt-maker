from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple

from enum import Enum

import bisect
import math
import random
import time

from app.map_maker.terrain import Terrain
from app.map_maker import simplex_noise, utilities

from app.utilities import direction, static_random, utils
from app.utilities.typing import NID, Pos

NOISE_LACUNARITY = 2.0
NOISE_GAIN = 0.5
# Derived seeds -- distinct fields must not correlate, so each gets seed + its own offset.
HILL_SEED_OFFSET = 1
PASS_SEED_OFFSET = 2
LAKE_SEED_OFFSET = 3
DESERT_SEED_OFFSET = 4
# Macro-layout hint grid (Civ's HintedWorld): a coarse block grid of land/water bias is
# blended into the elevation field so the map has guaranteed large-scale structure. Block
# size is fixed; the grid is ceil(width / BLOCK) x ceil(height / BLOCK).
MACRO_BLOCK_SIZE = 5
# Terrains an arid blob converts to DESERT core / SAND skirt. HILL and MOUNTAIN both flatten
# to arid ground exactly like grass (no DESERT_ROCK bands or peaks); RIVER dries up into the
# desert too (deserts run last, so any river crossing the blob is overwritten). Cliffs reskin
# to DESERT_CLIFF; existing sand and open water (SEA) are left untouched.
DESERT_CONVERTIBLE = (Terrain.NOISY_GRASS, Terrain.FOREST, Terrain.SPARSE_FOREST,
                      Terrain.THICKET, Terrain.HILL, Terrain.MOUNTAIN, Terrain.RIVER)
# The pass field modulates mountain-spine width along each ridge; finer than the hill
# field so a low patch cuts *across* a ridge rather than tracking it. 2x -> a pass is
# roughly half a hill wavelength wide (a few tiles at the default frequency).
PASS_FREQUENCY_MULTIPLIER = 2.0
# Exponent on the pass field in the spine score. At 1.0 the hill budget spreads evenly
# between thinning skirts and cutting passes; >1 spends it on carving passes through
# ridges first, keeping skirts mountainous right up to the band edge elsewhere.
PASS_STRENGTH = 2.0

# River source spacing (Chebyshev). Passes 2-3 halve both ranges (Civ's addRivers).
RIVER_SOURCE_MIN_RIVER_RANGE = 4
RIVER_SOURCE_MIN_SEA_RANGE = 2
# Deterministic per-tile jitter modulus. A pure function of (x, y, seed) added to every
# river_value; two rivers approaching the same valley break ties the same way and merge
# instead of running side by side (Civ's getRiverValueAtPlot trick).
RIVER_JITTER = 10
# Terrain -> altitude class for the flow walk. Missing entries (grass/forest family) = 2.
RIVER_ALTITUDE = {
    Terrain.MOUNTAIN: 4, Terrain.CLIFF: 4,
    Terrain.HILL: 3,
    Terrain.SAND: 1,
    Terrain.SEA: 0, Terrain.RIVER: 0,
}
# An off-map tile contributes this to a neighbor sum (Civ's NUM_PLOT_TYPES * 10), so
# river_value spikes near the border and rivers steer away from hugging the edge.
RIVER_OFF_MAP_ALTITUDE = 40
# Terrain a river tile may be painted over; rivers may cut through forest but never
# through mountains/cliffs (hard-excluded during the walk).
RIVER_PAINTABLE = (Terrain.HILL, Terrain.NOISY_GRASS, Terrain.SAND,
                   Terrain.FOREST, Terrain.SPARSE_FOREST, Terrain.THICKET)

class RiverEnd(Enum):
    """How a flow walk terminated. SEA/RIVER/OFFMAP are clean exits and are the only
    reasons a river is painted. DEADEND (ran out of legal moves) and CAP (hit the step
    limit) mean the river never reached water -- it is erased, not painted, because a
    river that stops mid-land or space-fills a flat basin into a wide blob reads as wrong
    in FE (unlike Civ's edge rivers, which may dead-end)."""
    SEA = 'sea'
    RIVER = 'river'
    OFFMAP = 'offmap'
    DEADEND = 'deadend'
    CAP = 'cap'

def derive_octaves(frequency: float) -> int:
    """Octaves whose wavelength falls below ~2 tiles (the tile Nyquist limit)
    add nothing visible, so octave depth follows from frequency."""
    if frequency == 0:
        return 1
    return max(1, math.ceil(math.log2(0.5 / frequency)))

def get_threshold_from_percent(noise_map: Dict[Pos, float], percent: float,
                               width: int, height: int,
                               positions: Optional[Iterable[Pos]] = None) -> float:
    """Value v such that `percent`% of in-bounds tiles have noise < v.
    Mirrors Civ 4's CyFractal.getHeightFromPercent. Only in-bounds tiles
    (0 <= x < width, 0 <= y < height) count; the border ring is excluded.
    `positions`, if given, restricts the percentile pool to that subset
    (e.g. land tiles only) instead of the full width x height grid."""
    if positions is None:
        positions = [(x, y) for x in range(width) for y in range(height)]
    values = sorted(noise_map[pos] for pos in positions)
    if percent <= 0:
        return values[0] - 1.0
    if percent >= 100:
        return values[-1] + 1.0
    index = min(len(values) - 1, int(len(values) * percent / 100))
    return values[index]

def generate_terrain(theme: Dict[NID, Any], seed: int) -> WorldTileMap:
    if seed == -1:  # Random seed
        random.seed(time.time())
        seed = random.randint(0, 999_999)
        print("Random Seed: %d" % seed)
    orig_seed = seed
    while True:
        result = _generate_terrain_process(theme, seed)
        seed += 1  # If that didn't work, try a different seed
        if result:
            break
        if seed > orig_seed + 10:
            return None

    return result

def generate_topology(theme: Dict[NID, Any], seed: int) -> Tuple[WorldTileMap, Dict[Pos, float], float, float]:
    """Elevation classification (SEA/SAND/land) plus hill/peak bands -- everything up to,
    but not including, the terrain-mutating passes (rivers/cliffs/forests). Split out from
    `_generate_terrain_process` so tests can measure band classification in isolation from
    those later passes, which also consume NOISY_GRASS/HILL tiles."""
    tilemap = WorldTileMap(theme, seed)

    # 1. Generate a simplex noise field of the right size and parameters from the theme
    terrain_noise_map: Dict[Pos, float] = simplex_noise.gen_noise_map(
        (tilemap.width + 2, tilemap.height + 2), seed, theme['starting_frequency'],
        1.0, derive_octaves(theme['starting_frequency']), NOISE_LACUNARITY,
        NOISE_GAIN)
    terrain_noise_map = simplex_noise.normalize_noise_map(terrain_noise_map)
    # Move noise map so it's topleft is (-1, -1)
    new_terrain_noise_map = {}
    for pos, value in terrain_noise_map.items():
        new_terrain_noise_map[(pos[0] - 1, pos[1] - 1)] = value
    terrain_noise_map = new_terrain_noise_map

    # 1.25 Blend in the macro-layout hint (guaranteed continents / pangaea / coast). Done
    # *before* the water_border falloff (so both compose, falloff staying an outer multiplier)
    # and before sink-fill + percentile classification (so it only decides *where* sea goes,
    # never how much -- the ratios stay percentile-locked).
    terrain_noise_map = tilemap.apply_macro_layout(terrain_noise_map)

    # Set Water Border
    if theme['water_border']:
        new_terrain_noise_map = {}
        for pos, value in terrain_noise_map.items():
            distance_from_center_x = abs(tilemap.width/2 - pos[0])/(tilemap.width/2)
            distance_from_center_y = abs(tilemap.height/2 - pos[1])/(tilemap.height/2)
            total_distance_from_center = math.sqrt(distance_from_center_x**2 + distance_from_center_y**2)
            if total_distance_from_center < 0.9:
                total_distance_from_center = 0
            new_value = value * utils.clamp(1 - total_distance_from_center, 0, 1)
            new_terrain_noise_map[pos] = new_value
        terrain_noise_map = new_terrain_noise_map

    # 1.5 Fill any sinks with the lowest average of the adjacent tiles
    new_terrain_noise_map = {}
    for pos, value in terrain_noise_map.items():
        adjacent_positions = [adj for adj in direction.get_cardinal_positions(pos) if adj in terrain_noise_map]
        lowest_average = min(terrain_noise_map[adj] for adj in adjacent_positions)
        if value < lowest_average:
            new_terrain_noise_map[pos] = lowest_average
        else:
            new_terrain_noise_map[pos] = value
    terrain_noise_map = new_terrain_noise_map

    # 2. Assign terrain based on the simplex noise field: SEA / SAND / land (NOISY_GRASS)
    sea_threshold, high_elevation_threshold = tilemap.generate_terrain_grid_from_noise(terrain_noise_map)

    # 2.5 Hills and mountains as bands of their own noise fields, decoupled from elevation,
    # so ranges snake across land instead of tracking the elevation blob.
    hill_frequency = theme['hill_frequency']
    hill_noise_map: Dict[Pos, float] = simplex_noise.gen_noise_map(
        (tilemap.width, tilemap.height), seed + HILL_SEED_OFFSET, hill_frequency,
        1.0, derive_octaves(hill_frequency), NOISE_LACUNARITY, NOISE_GAIN)
    hill_noise_map = simplex_noise.normalize_noise_map(hill_noise_map)

    pass_frequency = hill_frequency * PASS_FREQUENCY_MULTIPLIER
    pass_noise_map: Dict[Pos, float] = simplex_noise.gen_noise_map(
        (tilemap.width, tilemap.height), seed + PASS_SEED_OFFSET, pass_frequency,
        1.0, derive_octaves(pass_frequency), NOISE_LACUNARITY, NOISE_GAIN)
    pass_noise_map = simplex_noise.normalize_noise_map(pass_noise_map)

    tilemap.generate_bands_from_noise(hill_noise_map, pass_noise_map)

    return tilemap, terrain_noise_map, sea_threshold, high_elevation_threshold

def _generate_terrain_process(theme: Dict[NID, Any], seed: int) -> Optional[WorldTileMap]:
    tilemap, terrain_noise_map, _sea_threshold, _high_elevation_threshold = generate_topology(theme, seed)

    # 3. Figure out where cliffs go
    tilemap.generate_cliffs_from_noise(terrain_noise_map)

    # 4. Figure out where forests go
    forest_noise_map: Dict[Pos, float] = simplex_noise.gen_noise_map(
        (tilemap.width, tilemap.height), seed, theme['forest_starting_frequency'],
        1.0, derive_octaves(theme['forest_starting_frequency']), NOISE_LACUNARITY,
        NOISE_GAIN)
    forest_noise_map = simplex_noise.normalize_noise_map(forest_noise_map)
    tilemap.generate_forests_from_noise(forest_noise_map)

    # 5. Figure out where lakes go. Independent field (LAKE_SEED_OFFSET) so lakes don't
    # correlate with elevation and pile onto the coastal fringe. Runs *before* rivers so a
    # river can terminate in a lake (river termination already checks SEA).
    lake_noise_map: Dict[Pos, float] = simplex_noise.gen_noise_map(
        (tilemap.width, tilemap.height), seed + LAKE_SEED_OFFSET, theme['lake_frequency'],
        1.0, derive_octaves(theme['lake_frequency']), NOISE_LACUNARITY, NOISE_GAIN)
    lake_noise_map = simplex_noise.normalize_noise_map(lake_noise_map)
    tilemap.generate_lakes_from_noise(lake_noise_map)

    # 6. Figure out where rivers go. Rivers run *after* cliffs, forests, and lakes, matching
    # Civ's order (features last) and letting rivers read the finished altitude field,
    # including forest tiles they may cut through and lakes they may terminate in.
    tilemap.generate_rivers()

    # 7. Figure out where deserts go. Independent field (DESERT_SEED_OFFSET): an arid blob is a
    # DESERT core wrapped in a SAND skirt (like hills/peaks), with DESERT_ROCK scattered on top.
    # Runs *last* so the arid blob overwrites everything under it -- including rivers, which dry
    # up into desert/sand rather than flowing through the sand. A lake (SEA) under the blob
    # survives as an oasis (SEA is not convertible).
    desert_noise_map: Dict[Pos, float] = simplex_noise.gen_noise_map(
        (tilemap.width, tilemap.height), seed + DESERT_SEED_OFFSET, theme['desert_frequency'],
        1.0, derive_octaves(theme['desert_frequency']), NOISE_LACUNARITY, NOISE_GAIN)
    desert_noise_map = simplex_noise.normalize_noise_map(desert_noise_map)
    tilemap.generate_deserts_from_noise(desert_noise_map)

    return tilemap

class WorldTileMap:
    def __init__(self, theme: Dict[NID, Any], seed: int):
        self.random = static_random.LCG(seed)
        self.seed = seed
        self.theme = theme
        self.width, self.height = theme["size"]
        self.terrain_grid: Dict[Pos, Terrain] = {}

    def get_terrain(self, pos: Pos) -> Optional[Terrain]:
        return self.terrain_grid.get(pos, None)

    def check_bounds(self, pos: Pos) -> bool:
        return 0 <= pos[0] < self.width and 0 <= pos[1] < self.height

    def _expand_blocks(self, seeds: List[Pos], target: int, claimed: set,
                       bx: int, by: int, allowed: Optional[set] = None) -> None:
        # Civ's expandContinentBy: grow a landmass by repeatedly picking a random block it
        # already owns, a random cardinal neighbour, and claiming that neighbour if it is
        # unclaimed (and, if `allowed` is given, inside that region -- used to pen each
        # continent into its own half so they stay separate). `claimed` is the shared land
        # set (mutated); `seeds` bootstraps this continent. All choices go through self.random
        # so expansion is deterministic.
        owned: List[Pos] = []
        for s in seeds:
            claimed.add(s)
            owned.append(s)
        guard = 0
        max_guard = bx * by * 50 + 100
        while len(owned) < target and guard < max_guard:
            guard += 1
            block = self.random.choice(owned)
            dx, dy = self.random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            nb = (block[0] + dx, block[1] + dy)
            if not (0 <= nb[0] < bx and 0 <= nb[1] < by):
                continue
            if allowed is not None and nb not in allowed:
                continue
            if nb not in claimed:
                claimed.add(nb)
                owned.append(nb)

    def _macro_hint_blocks(self, layout: str, bx: int, by: int) -> Dict[Pos, float]:
        # Assign each block of the coarse grid a hint value in [0, 1]: land ~0.75, water ~0.15,
        # unassigned ~0.45 (jittered). Which blocks are land/water comes from the layout.
        total = bx * by
        land: set = set()
        water: set = set()
        if layout == 'pangaea':
            # Confine expansion to interior blocks (exclude the outer block ring) so the
            # continent never claims an edge block -- a water block ring surrounds it, and the
            # edge falloff in apply_macro_layout then guarantees a true sea border.
            interior = {(x, y) for x in range(1, bx - 1) for y in range(1, by - 1)}
            if not interior:  # grid too small for an interior ring
                interior = {(bx // 2, by // 2)}
            center = min(interior, key=lambda b: abs(b[0] - bx / 2) + abs(b[1] - by / 2))
            target = min(max(1, round(0.55 * total)), len(interior))
            self._expand_blocks([center], target, land, bx, by, interior)
            water = {(x, y) for x in range(bx) for y in range(by)} - land
        elif layout == 'continents':
            # Reserve the two centre columns as a water gutter and pen each continent into its
            # own interior half (excluding the outer block ring, as pangaea does), so the two
            # landmasses stay separate *and* stay off the map edge. Each fills ~75% of its half.
            lo, hi = (bx - 1) // 2, bx // 2  # two central columns (one when bx is odd)
            left = {(x, y) for x in range(1, lo) for y in range(1, by - 1)}
            right = {(x, y) for x in range(hi + 1, bx - 1) for y in range(1, by - 1)}
            if left:
                seed_a = min(left, key=lambda b: abs(b[0] - lo / 2) + abs(b[1] - by / 2))
                self._expand_blocks([seed_a], max(1, round(0.75 * len(left))), land, bx, by, left)
            if right:
                anchor = (hi + bx) / 2
                seed_b = min(right, key=lambda b: abs(b[0] - anchor) + abs(b[1] - by / 2))
                self._expand_blocks([seed_b], max(1, round(0.75 * len(right))), land, bx, by, right)
            water = {(x, y) for x in range(bx) for y in range(by)} - land
        elif layout == 'coastal':
            edge = self.random.randrange(4)  # 0 top, 1 bottom, 2 left, 3 right
            for x in range(bx):
                for y in range(by):
                    if ((edge == 0 and y < 2) or (edge == 1 and y >= by - 2)
                            or (edge == 2 and x < 2) or (edge == 3 and x >= bx - 2)):
                        water.add((x, y))
                    else:
                        land.add((x, y))

        # Draw the jittered values in a fixed (sorted) block order so the field is deterministic.
        hint: Dict[Pos, float] = {}
        for x in range(bx):
            for y in range(by):
                r = self.random.random()
                if (x, y) in land:
                    hint[(x, y)] = 0.75 + r * 0.15
                elif (x, y) in water:
                    hint[(x, y)] = 0.15 + r * 0.15
                else:
                    hint[(x, y)] = 0.45 + r * 0.10
        return hint

    def apply_macro_layout(self, noise_map: Dict[Pos, float]) -> Dict[Pos, float]:
        # Blend a coarse macro-layout hint into the elevation field. A no-op for 'none'. The
        # block grid is bilinearly upsampled to per-tile resolution (block centres as sample
        # points, clamped at edges) and mixed in at strength hint_weight. Because downstream
        # classification is percentile-based, this only steers *where* land/sea land, not how
        # much of each there is.
        layout = str(self.theme['macro_layout'])
        weight = self.theme['hint_weight']
        if layout == 'none' or weight <= 0:
            return noise_map

        bx = max(1, math.ceil(self.width / MACRO_BLOCK_SIZE))
        by = max(1, math.ceil(self.height / MACRO_BLOCK_SIZE))
        hint = self._macro_hint_blocks(layout, bx, by)

        def sample(x: int, y: int) -> float:
            # Block b covers tiles [b*BLOCK, b*BLOCK+BLOCK-1]; its centre tile is b*BLOCK + BLOCK/2.
            fx = (x - MACRO_BLOCK_SIZE / 2) / MACRO_BLOCK_SIZE
            fy = (y - MACRO_BLOCK_SIZE / 2) / MACRO_BLOCK_SIZE
            x0 = int(utils.clamp(math.floor(fx), 0, bx - 1))
            y0 = int(utils.clamp(math.floor(fy), 0, by - 1))
            x1 = int(utils.clamp(x0 + 1, 0, bx - 1))
            y1 = int(utils.clamp(y0 + 1, 0, by - 1))
            tx = utils.clamp(fx - x0, 0.0, 1.0)
            ty = utils.clamp(fy - y0, 0.0, 1.0)
            top = hint[(x0, y0)] * (1 - tx) + hint[(x1, y0)] * tx
            bot = hint[(x0, y1)] * (1 - tx) + hint[(x1, y1)] * tx
            return top * (1 - ty) + bot * ty

        blended: Dict[Pos, float] = {}
        for pos, value in noise_map.items():
            h = sample(pos[0], pos[1])
            blended[pos] = utils.clamp((1 - weight) * value + weight * h, 0, 1)

        # Enclosed layouts (pangaea, continents) must be surrounded by sea on every side. The
        # interior-block confinement keeps land off the edge blocks, but the ~sea_percent budget
        # alone can't guarantee a full perimeter ring. Force it: drive the outer tile ring to 0
        # (the global minimum, so it is always classified SEA) and ramp back up over MARGIN tiles.
        # Coastal is exempt -- it *wants* land running to three of the four edges.
        if layout in ('pangaea', 'continents'):
            margin = 2
            for pos in blended:
                d = min(pos[0], pos[1], self.width - 1 - pos[0], self.height - 1 - pos[1])
                if d < margin:
                    blended[pos] *= max(0.0, d) / margin

        # Continents also need a guaranteed sea channel between the two halves. The reserved
        # block gutter isn't enough on its own: the edge falloff above consumes sea budget
        # (classification is percentile-locked), so the ~0.15 gutter hint can end up above the
        # sea threshold and the two landmasses bridge. Force the two central columns to 0 so a
        # sea channel always splits the map.
        if layout == 'continents':
            centre = (self.width - 1) / 2
            for pos in blended:
                if abs(pos[0] - centre) < 1.0:
                    blended[pos] = 0.0
        return blended

    def generate_terrain_grid_from_noise(self, noise_map: Dict[Pos, float]) -> Tuple[float, float]:
        # Cumulative percentile thresholds, computed on the final (post-macro-layout,
        # post-water-border, post-sink-fill) field, so ratios are exact for every seed. This field decides only SEA / SAND / land -- hills and
        # mountains are classified separately in generate_bands_from_noise, from the
        # hill field.
        sea_percent = self.theme['sea_percent'] * 100
        sand_percent = self.theme['sand_percent'] * 100

        sea_threshold = get_threshold_from_percent(noise_map, sea_percent, self.width, self.height)
        sand_threshold = get_threshold_from_percent(noise_map, sea_percent + sand_percent, self.width, self.height)

        for x in range(self.width):
            for y in range(self.height):
                value: float = noise_map[(x, y)]
                if value < sea_threshold:
                    terrain = Terrain.SEA
                elif value < sand_threshold:
                    terrain = Terrain.SAND
                else:
                    terrain = Terrain.NOISY_GRASS
                self.terrain_grid[(x, y)] = terrain

        # Stand-in "high ground" bound for the river logic, which still reads the
        # elevation field for now (Phase 3 replaces river source selection entirely).
        high_elevation_threshold = get_threshold_from_percent(
            noise_map, 100 - self.theme['highland_percent'] * 100, self.width, self.height)

        return sea_threshold, high_elevation_threshold

    def generate_bands_from_noise(self, hill_noise_map: Dict[Pos, float], pass_noise_map: Dict[Pos, float]):
        # Hills/mountains form as percentile *bands* of the hill field (a level set of a
        # continuous field is an elongated ridge, not a blob) rather than being thresholded
        # directly -- this is what produces mountain ranges instead of scattered clumps.
        land_positions = [(x, y) for x in range(self.width) for y in range(self.height)
                          if self.get_terrain((x, y)) == Terrain.NOISY_GRASS]
        if not land_positions:
            return

        highland_percent = self.theme['highland_percent'] * 100
        half_width = highland_percent / 4  # two bands, each with two edges

        # Percentile rank of each land tile within the hill field; the bands and the
        # spines inside them are both defined in this space. Centrality is 0 on a
        # band's center line (the ridge crest) and 1 at its edge; tiles outside both
        # bands stay NOISY_GRASS.
        sorted_values = sorted(hill_noise_map[pos] for pos in land_positions)
        total = len(sorted_values)
        centrality: Dict[Pos, float] = {}
        for pos in land_positions:
            percentile = bisect.bisect_left(sorted_values, hill_noise_map[pos]) / total * 100
            for center in (25, 75):
                band_position = abs(percentile - center) / half_width
                if band_position < 1:
                    centrality[pos] = band_position
                    break
        if not centrality:
            return

        # Mountains are the most-central slice of each band, so every range is a
        # mountain spine flanked by hill skirts. The pass field scales spine width
        # along the ridge: where it nears zero the score diverges and the spine
        # pinches off entirely, leaving an all-hill gap -- a mountain pass.
        # Thresholding the score at a percentile over highland tiles keeps mountain
        # coverage at exactly peak_percent regardless of the pass field's distribution.
        score_map = {pos: value / max(pass_noise_map[pos], 1e-9) ** PASS_STRENGTH
                     for pos, value in centrality.items()}
        highland_positions = list(centrality)
        peak_percent = self.theme['peak_percent'] * 100
        peak_threshold = get_threshold_from_percent(score_map, peak_percent, self.width, self.height, highland_positions)

        for pos in highland_positions:
            if score_map[pos] <= peak_threshold:
                self.terrain_grid[pos] = Terrain.MOUNTAIN
            else:
                self.terrain_grid[pos] = Terrain.HILL

    def generate_cliffs_from_noise(self, noise_map: Dict[Pos, float]):
        # Use Sobel Edge Detection to find areas of discontinuity
        gx = [-1, 0, 1,
              -2, 0, 2,
              -1, 0, 1]
        gy = [1, 2, 1,
              0, 0, 0,
              -1, -2, -1]

        def convolve(values: List[float], kernel: List[int]) -> float:
            assert len(values) == len(kernel)
            return sum([(value * k) for value, k in zip(values, kernel)]) ** 2

        def non_max_suppression(gradient_magnitude: List[float], gradient_orientation: List[float]) -> List[float]:
            output = [0] * len(gradient_magnitude)

            # Ignore the border pixels
            for x in range(1, self.width - 1):
                for y in range(1, self.height - 1):
                    # Will be between -pi and pi
                    magnitude: float = gradient_magnitude[y + self.height * x]
                    direction: float = gradient_orientation[y + self.height * x] 
                    direction += math.pi  # Move to be between 0 and 2*pi

                    if (0 <= direction < math.pi / 8) or (15 * math.pi / 8 <= direction <= 2 * math.pi):
                        before_pixel = gradient_magnitude[y + self.height * (x - 1)]
                        after_pixel = gradient_magnitude[y + self.height * (x + 1)]

                    elif (math.pi / 8 <= direction < 3 * math.pi / 8) or (9 * math.pi / 8 <= direction < 11 * math.pi):
                        before_pixel = gradient_magnitude[(y + 1) + self.height * (x - 1)]
                        after_pixel = gradient_magnitude[(y - 1) + self.height * (x + 1)]

                    elif (3 * math.pi / 8 <= direction < 5 * math.pi / 8) or (11 * math.pi / 8 <= direction < 13 * math.pi):
                        before_pixel = gradient_magnitude[(y - 1) + self.height * x]
                        after_pixel = gradient_magnitude[(y + 1) + self.height * x]

                    else:
                        before_pixel = gradient_magnitude[(y - 1) + self.height * (x - 1)]
                        after_pixel = gradient_magnitude[(y + 1) + self.height * (x + 1)]

                    if magnitude >= before_pixel and magnitude >= after_pixel:
                        output[y + self.height * x] = magnitude
            return output

        x_image, y_image = [], []
        # Do the convolution
        for x in range(self.width):
            for y in range(self.height):
                values = [noise_map[(x - 1, y - 1)], noise_map[(x, y - 1)], noise_map[(x + 1, y - 1)],
                          noise_map[(x - 1, y)], noise_map[(x, y)], noise_map[(x + 1, y)],
                          noise_map[(x - 1, y + 1)], noise_map[(x, y + 1)], noise_map[(x + 1, y + 1)]]
                x_image.append(convolve(values, gx))
                y_image.append(convolve(values, gy))
        
        # Now generate a single magnitude for each point
        gradient_magnitude = [math.sqrt(x**2 + y**2) for (x, y) in zip(x_image, y_image)]
        gradient_orientation = [math.atan2(y, x) for (x, y) in zip(x_image, y_image)]
        max_magnitude = max(gradient_magnitude)
        if max_magnitude > 0:
            gradient_magnitude = [_ / max_magnitude for _ in gradient_magnitude]  # Now between 0 and 1
        else:
            gradient_magnitude = [0 for _ in gradient_magnitude]

        for x in range(self.width):
            for y in range(self.height):
                value: float = gradient_magnitude[y + self.height * x]
                if self.get_terrain((x, y)) != Terrain.NOISY_GRASS:
                    continue  # Don't bother if not grass
                
                if value >= (1 - self.theme['cliff_threshold']):
                    self.terrain_grid[(x, y)] = Terrain.CLIFF         

    def generate_forests_from_noise(self, noise_map: Dict[Pos, float]):
        for x in range(self.width):
            for y in range(self.height):
                value: float = noise_map[(x, y)]
                if self.get_terrain((x, y)) != Terrain.NOISY_GRASS:
                    continue  # Don't bother if not grass
                # Clamped noise (normalize_noise_map) can land exactly on value == 1.0,
                # so a bare `>= (1 - 0)` threshold would still fire at 0% chance.
                thick_forest_threshold = (1 - self.theme['thick_forest_threshold'])
                if self.theme['thick_forest_threshold'] > 0 and value >= thick_forest_threshold:
                    self.terrain_grid[(x, y)] = Terrain.THICKET
                elif self.theme['forest_threshold'] > 0 and thick_forest_threshold > value >= (1 - self.theme['forest_threshold']):
                    self.terrain_grid[(x, y)] = Terrain.FOREST

    def generate_lakes_from_noise(self, noise_map: Dict[Pos, float]):
        # Inland water bodies: the low percentile of an independent lake field becomes SEA
        # (lakes *are* SEA terrain -- the autotiler renders inland sea). Blob lakes modeled
        # on Highlands.py's dedicated lake fractal, not Civ's single-tile method.
        lake_percent = self.theme['lake_percent'] * 100
        if lake_percent <= 0:
            return
        # Percentile pool is land only -- include sea and coastal water eats the lake budget.
        land_positions = [(x, y) for x in range(self.width) for y in range(self.height)
                          if self.get_terrain((x, y)) != Terrain.SEA]
        if not land_positions:
            return
        lake_threshold = get_threshold_from_percent(
            noise_map, lake_percent, self.width, self.height, land_positions)
        # Snapshot the *pre-lake* coastline: distance-to-sea is measured against it, so a
        # growing lake blob neither fuses into the coast nor self-blocks (the second lake
        # tile must not measure its distance to the first).
        coastline = {pos for pos, terrain in self.terrain_grid.items()
                     if terrain == Terrain.SEA}
        convertible = (Terrain.NOISY_GRASS, Terrain.SAND, Terrain.FOREST,
                       Terrain.SPARSE_FOREST, Terrain.THICKET, Terrain.HILL)

        def near_coast(pos: Pos) -> bool:
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if (pos[0] + dx, pos[1] + dy) in coastline:
                        return True
            return False

        for pos in land_positions:
            if noise_map[pos] >= lake_threshold:
                continue
            if self.get_terrain(pos) not in convertible:
                continue
            if near_coast(pos):  # keep lakes > Chebyshev 2 from the coast
                continue
            self.terrain_grid[pos] = Terrain.SEA

    def generate_deserts_from_noise(self, noise_map: Dict[Pos, float]):
        # Arid biome as a blob (no latitude axis -- we target one island/small continent, not a
        # globe). Each blob is a DESERT core wrapped in a SAND skirt, the SAND : DESERT relation
        # mirroring HILL : MOUNTAIN: the deepest interior of the blob is true DESERT, everything
        # out to the blob edge is SAND, so DESERT reaches grass/forest only through a sand band.
        # DESERT_ROCK is then sprinkled onto DESERT tiles at random -- never banded (a run of
        # DESERT_ROCK reads badly), so HILL flattens to arid ground rather than becoming rock.
        desert_percent = self.theme['desert_percent'] * 100
        if desert_percent <= 0:
            return
        # Percentile pool is land only, else sea eats the budget.
        land_positions = [(x, y) for x in range(self.width) for y in range(self.height)
                          if self.get_terrain((x, y)) != Terrain.SEA]
        if not land_positions:
            return
        # Arid region = top `desert_percent` of the desert field over land (one/few blobs).
        arid_threshold = get_threshold_from_percent(
            noise_map, 100 - desert_percent, self.width, self.height, land_positions)
        arid_positions = [pos for pos in land_positions if noise_map[pos] >= arid_threshold]
        if not arid_positions:
            return
        # Within the blob, the top `deep_desert_percent` (of the arid pool) is true DESERT core;
        # the rest is SAND skirt. Because noise level sets nest, the core sits blob-interior.
        deep_percent = self.theme['deep_desert_percent'] * 100
        deep_threshold = get_threshold_from_percent(
            noise_map, 100 - deep_percent, self.width, self.height, arid_positions)

        for pos in arid_positions:
            terrain = self.get_terrain(pos)
            if terrain == Terrain.CLIFF:
                self.terrain_grid[pos] = Terrain.DESERT_CLIFF
                continue
            if terrain not in DESERT_CONVERTIBLE:
                continue  # existing SAND / RIVER survive the climate
            if noise_map[pos] >= deep_threshold:
                self.terrain_grid[pos] = Terrain.DESERT
            else:
                self.terrain_grid[pos] = Terrain.SAND

        # Guarantee the SAND skirt: percentile nesting alone leaves a jagged, sometimes
        # one-tile-thin border on small blobs, so a DESERT tile can still abut grass/forest.
        # Erode once -- every DESERT tile 4-adjacent to vegetation is demoted to SAND
        # (computed against the pre-erosion grid, so the survivors provably touch no
        # vegetation). This also thickens the skirt, keeping SAND the common arid tile.
        vegetation = (Terrain.NOISY_GRASS, Terrain.FOREST, Terrain.SPARSE_FOREST, Terrain.THICKET)
        to_sand = []
        for (x, y) in arid_positions:
            if self.get_terrain((x, y)) != Terrain.DESERT:
                continue
            if any(self.get_terrain(n) in vegetation
                   for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))):
                to_sand.append((x, y))
        for pos in to_sand:
            self.terrain_grid[pos] = Terrain.SAND

        # Scatter DESERT_ROCK onto true-desert tiles only, via a deterministic per-tile draw
        # (pure function of position + seed, independent of iteration order and of the river
        # jitter -- distinct offset), so rocks reproduce and never form a band.
        rock_chance = self.theme['desert_rock_chance']
        if rock_chance > 0:
            for pos in arid_positions:
                if self.get_terrain(pos) != Terrain.DESERT:
                    continue
                if utilities.random_random(pos, self.seed, DESERT_SEED_OFFSET) < rock_chance:
                    self.terrain_grid[pos] = Terrain.DESERT_ROCK

    def _identify_landmasses(self) -> Tuple[Dict[Pos, int], Dict[int, int]]:
        """Flood-fill 4-connected non-SEA tiles into landmasses. Returns
        (area_id per tile, size per area)."""
        area_id: Dict[Pos, int] = {}
        area_size: Dict[int, int] = {}
        next_area = 0
        for x in range(self.width):
            for y in range(self.height):
                start = (x, y)
                if start in area_id or self.get_terrain(start) == Terrain.SEA:
                    continue
                stack = [start]
                area_id[start] = next_area
                size = 0
                while stack:
                    cur = stack.pop()
                    size += 1
                    for adj in direction.get_cardinal_positions(cur):
                        if self.check_bounds(adj) and adj not in area_id \
                                and self.get_terrain(adj) != Terrain.SEA:
                            area_id[adj] = next_area
                            stack.append(adj)
                area_size[next_area] = size
                next_area += 1
        return area_id, area_size

    def _altitude_class(self, pos: Pos) -> int:
        return RIVER_ALTITUDE.get(self.get_terrain(pos), 2)

    def _river_value(self, pos: Pos) -> int:
        # altitude of the tile (weighted) + altitudes of its 8 neighbors + deterministic
        # jitter. Rivers greedily descend this field; jitter (a pure function of position
        # and map seed) is what makes two rivers heading into the same valley merge.
        self_alt = self._altitude_class(pos) if self.check_bounds(pos) else 0
        neighbor_total = 0
        neighbors = direction.get_cardinal_positions(pos) + direction.get_diagonal_positions(pos)
        for n in neighbors:
            if self.check_bounds(n):
                neighbor_total += self._altitude_class(n)
            else:
                neighbor_total += RIVER_OFF_MAP_ALTITUDE
        # Deterministic per-tile jitter (0 .. RIVER_JITTER-1), a pure function of position
        # and map seed, so two rivers reaching the same valley break ties identically and
        # merge. random_random hides the coordinate hash in the trusted map_maker util.
        jitter = int(utilities.random_random(pos, self.seed) * RIVER_JITTER)
        return self_alt * 20 + neighbor_total + jitter

    def _do_river(self, source: Pos) -> Tuple[List[Pos], RiverEnd]:
        # Greedy min-river_value descent with Civ's no-U-turn rule. Returns the path
        # (starting at source) and how it ended (see RiverEnd).
        path: List[Pos] = [source]
        path_set = {source}
        first_dir: Optional[direction.Direction] = None
        prev_dir: Optional[direction.Direction] = None
        reason = RiverEnd.DEADEND
        # A river that reaches water does so in O(map dimension) steps. A walk that runs
        # much longer is snaking a flat basin (no gradient to descend, no water to hit);
        # cap it so it bails as CAP -> erased instead of space-filling a wide blob.
        max_steps = 2 * (self.width + self.height)
        for _ in range(max_steps):
            current = path[-1]
            candidates: List[Tuple[Pos, direction.Direction]] = []
            for n in direction.get_cardinal_positions(current):
                step_dir = direction.Direction.determine(current, n)
                if prev_dir is not None and step_dir == direction.Direction.opposite(prev_dir):
                    continue
                if first_dir is not None and step_dir == direction.Direction.opposite(first_dir):
                    continue
                if n in path_set:
                    continue
                if self.check_bounds(n) and self.get_terrain(n) in (Terrain.MOUNTAIN, Terrain.CLIFF):
                    continue
                candidates.append((n, step_dir))
            if not candidates:
                reason = RiverEnd.DEADEND
                break
            best_pos, best_dir = min(candidates, key=lambda c: self._river_value(c[0]))
            if first_dir is None:
                first_dir = best_dir
            prev_dir = best_dir
            if not self.check_bounds(best_pos):
                reason = RiverEnd.OFFMAP
                break
            terrain = self.get_terrain(best_pos)
            if terrain == Terrain.SEA:
                reason = RiverEnd.SEA
                break
            if terrain == Terrain.RIVER:
                reason = RiverEnd.RIVER
                break
            path.append(best_pos)
            path_set.add(best_pos)
        else:
            reason = RiverEnd.CAP
        return path, reason

    def generate_rivers(self):
        # Port of Civ 4's addRivers/doRiver: rivers seeded per landmass with quotas and
        # spacing, then flowed downhill along the altitude field until they hit water or
        # the map edge (or merge into an existing river). Replaces the old strictly-downhill
        # noise walk. self.river_sources / self.rivers are exposed for tests.
        self.river_sources: List[Pos] = []
        self.rivers: List[Tuple[List[Pos], RiverEnd]] = []

        tiles_per_river_tile = self.theme['tiles_per_river_tile']
        if tiles_per_river_tile <= 0:
            return

        area_id, area_size = self._identify_landmasses()
        river_tiles_placed: Dict[int, int] = {area: 0 for area in area_size}
        placed_river_tiles: set = set()

        def under_quota(area: int) -> bool:
            return river_tiles_placed[area] < area_size[area] // tiles_per_river_tile + 1

        def near_sea(pos: Pos, rng: int) -> bool:
            for dx in range(-rng, rng + 1):
                for dy in range(-rng, rng + 1):
                    n = (pos[0] + dx, pos[1] + dy)
                    if self.check_bounds(n) and self.get_terrain(n) == Terrain.SEA:
                        return True
            return False

        def near_river(pos: Pos, rng: int) -> bool:
            for dx in range(-rng, rng + 1):
                for dy in range(-rng, rng + 1):
                    if (pos[0] + dx, pos[1] + dy) in placed_river_tiles:
                        return True
            return False

        for pass_num in range(4):
            # Passes 0-1 place the well-spaced "nice" rivers at full spacing. Passes 2-3
            # are quota backfill: they only fire on landmasses still under quota, and halve
            # both ranges so a river can be squeezed onto a small or cramped landmass that
            # full spacing would leave with no legal source tile at all.
            if pass_num <= 1:
                river_range = RIVER_SOURCE_MIN_RIVER_RANGE
                sea_range = RIVER_SOURCE_MIN_SEA_RANGE
            else:
                river_range = RIVER_SOURCE_MIN_RIVER_RANGE // 2
                sea_range = RIVER_SOURCE_MIN_SEA_RANGE // 2

            for x in range(self.width):
                for y in range(self.height):
                    pos = (x, y)
                    terrain = self.get_terrain(pos)
                    if terrain == Terrain.SEA:
                        continue
                    area = area_id[pos]
                    highland = terrain in (Terrain.HILL, Terrain.MOUNTAIN)

                    if pass_num == 0:
                        candidate = highland
                    elif pass_num == 1:
                        candidate = (not near_sea(pos, RIVER_SOURCE_MIN_SEA_RANGE)
                                     and self.random.randint(0, 7) == 0)
                    elif pass_num == 2:
                        candidate = highland and under_quota(area)
                    else:
                        candidate = under_quota(area)
                    if not candidate:
                        continue

                    # Spacing: keep sources apart and away from the coast. Checked against
                    # every earlier river's tiles (placed within this same pass too), so
                    # rivers spread instead of bunching.
                    if near_sea(pos, sea_range) or near_river(pos, river_range):
                        continue

                    path, reason = self._do_river(pos)
                    if reason not in (RiverEnd.SEA, RiverEnd.RIVER, RiverEnd.OFFMAP):
                        continue  # never reached water -- erase it (no dead-end/blob rivers)
                    paintable = [p for p in path if self.get_terrain(p) in RIVER_PAINTABLE]
                    if len(paintable) < 3:
                        continue  # too short -- erase it
                    for p in paintable:
                        self.terrain_grid[p] = Terrain.RIVER
                    placed_river_tiles.update(path)
                    river_tiles_placed[area] += len(paintable)
                    self.river_sources.append(pos)
                    self.rivers.append((path, reason))
