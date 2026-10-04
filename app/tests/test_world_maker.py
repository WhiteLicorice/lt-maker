import unittest

from app.world_maker import themes, terrain_generation
from app.map_maker.terrain import Terrain


def _make_theme(size=(25, 25), **overrides):
    theme = themes.get_theme("Default")
    theme['size'] = size
    theme.update(overrides)
    return theme


def _connected_components(positions):
    """4-connected components over an arbitrary set of positions."""
    remaining = set(positions)
    components = []
    while remaining:
        start = next(iter(remaining))
        stack = [start]
        remaining.discard(start)
        component = {start}
        while stack:
            x, y = stack.pop()
            for adj in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if adj in remaining:
                    remaining.discard(adj)
                    component.add(adj)
                    stack.append(adj)
        components.append(component)
    return components


class WorldMakerPercentileThresholdTests(unittest.TestCase):
    def test_determinism(self):
        theme = _make_theme()
        tm1 = terrain_generation.generate_terrain(theme, 42)
        tm2 = terrain_generation.generate_terrain(theme, 42)
        self.assertEqual(tm1.terrain_grid, tm2.terrain_grid)

    def test_sea_ratio_matches_percent(self):
        theme = _make_theme()
        for seed in range(10):
            tm = terrain_generation.generate_terrain(theme, seed)
            total = tm.width * tm.height
            sea_count = sum(1 for t in tm.terrain_grid.values() if t == Terrain.SEA)
            observed = sea_count / total * 100
            expected = theme['sea_percent'] * 100
            self.assertLessEqual(abs(observed - expected), 2,
                                  "seed %d: sea %.1f%% vs expected %.1f%%" % (seed, observed, expected))

    def test_sea_ratio_tracks_percent_parameter(self):
        low_theme = _make_theme(sea_percent=0.10)
        high_theme = _make_theme(sea_percent=0.60)

        def sea_fraction(theme):
            tm = terrain_generation.generate_terrain(theme, 7)
            total = tm.width * tm.height
            return sum(1 for t in tm.terrain_grid.values() if t == Terrain.SEA) / total

        low_fraction = sea_fraction(low_theme)
        high_fraction = sea_fraction(high_theme)
        self.assertLess(low_fraction, high_fraction)
        self.assertLessEqual(abs(low_fraction - 0.10), 0.05)
        self.assertLessEqual(abs(high_fraction - 0.60), 0.05)


class WorldMakerHillPeakBandTests(unittest.TestCase):
    # Coverage is measured right after band classification (generate_topology), before
    # rivers/cliffs/forests consume NOISY_GRASS/HILL tiles and skew the final ratios.

    def test_highland_coverage_matches_percent(self):
        theme = _make_theme()
        for seed in range(10):
            tm, _, _, _ = terrain_generation.generate_topology(theme, seed)
            land_count = sum(1 for t in tm.terrain_grid.values()
                              if t in (Terrain.NOISY_GRASS, Terrain.HILL, Terrain.MOUNTAIN))
            highland_count = sum(1 for t in tm.terrain_grid.values()
                                  if t in (Terrain.HILL, Terrain.MOUNTAIN))
            observed = highland_count / land_count * 100
            expected = theme['highland_percent'] * 100
            self.assertLessEqual(abs(observed - expected), 3,
                                  "seed %d: highland %.1f%% vs expected %.1f%%" % (seed, observed, expected))

    def test_peak_coverage_matches_percent(self):
        theme = _make_theme()
        for seed in range(10):
            tm, _, _, _ = terrain_generation.generate_topology(theme, seed)
            highland_count = sum(1 for t in tm.terrain_grid.values()
                                  if t in (Terrain.HILL, Terrain.MOUNTAIN))
            mountain_count = sum(1 for t in tm.terrain_grid.values() if t == Terrain.MOUNTAIN)
            if highland_count == 0:
                continue
            observed = mountain_count / highland_count * 100
            expected = theme['peak_percent'] * 100
            self.assertLessEqual(abs(observed - expected), 5,
                                  "seed %d: peak %.1f%% vs expected %.1f%%" % (seed, observed, expected))

    def test_determinism(self):
        theme = _make_theme()
        tm1 = terrain_generation.generate_terrain(theme, 99)
        tm2 = terrain_generation.generate_terrain(theme, 99)
        self.assertEqual(tm1.terrain_grid, tm2.terrain_grid)

    def test_hills_and_mountains_form_ranges_not_blobs(self):
        # Weak automated proxy for "ranges not blobs": components should tend to be
        # larger than a single tile, and at least one map in the sample should show
        # a clearly elongated (ridge-shaped) component.
        theme = _make_theme()
        elongated_seed_count = 0
        for seed in range(10):
            tm = terrain_generation.generate_terrain(theme, seed)
            highland_positions = [pos for pos, t in tm.terrain_grid.items()
                                   if t in (Terrain.HILL, Terrain.MOUNTAIN)]
            components = _connected_components(highland_positions)
            if not components:
                continue
            mean_size = sum(len(c) for c in components) / len(components)
            self.assertGreater(mean_size, 1.5, "seed %d: mean component size %.2f" % (seed, mean_size))

            for component in components:
                xs = [p[0] for p in component]
                ys = [p[1] for p in component]
                w = max(xs) - min(xs) + 1
                h = max(ys) - min(ys) + 1
                aspect = max(w, h) / min(w, h)
                if aspect >= 3:
                    elongated_seed_count += 1
                    break

        self.assertGreaterEqual(elongated_seed_count, 5,
                                 "only %d/10 seeds had an elongated (ridge) component" % elongated_seed_count)

    def test_hills_and_mountains_dont_overwrite_sand_or_sea(self):
        # Band classification must not touch SEA/SAND tiles -- their share of the map
        # should still match sea_percent/sand_percent exactly, regardless of highland_percent.
        theme = _make_theme()
        for seed in range(5):
            tm, _, _, _ = terrain_generation.generate_topology(theme, seed)
            total = tm.width * tm.height
            sea_fraction = sum(1 for t in tm.terrain_grid.values() if t == Terrain.SEA) / total
            sand_fraction = sum(1 for t in tm.terrain_grid.values() if t == Terrain.SAND) / total
            self.assertLessEqual(abs(sea_fraction - theme['sea_percent']), 0.02)
            self.assertLessEqual(abs(sand_fraction - theme['sand_percent']), 0.02)


def _chebyshev(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


class WorldMakerRiverTests(unittest.TestCase):
    def test_determinism(self):
        theme = _make_theme()
        tm1 = terrain_generation.generate_terrain(theme, 3)
        tm2 = terrain_generation.generate_terrain(theme, 3)
        self.assertEqual(tm1.terrain_grid, tm2.terrain_grid)

    def test_disabled_produces_no_rivers(self):
        theme = _make_theme(tiles_per_river_tile=0)
        for seed in range(5):
            tm = terrain_generation.generate_terrain(theme, seed)
            rivers = sum(1 for t in tm.terrain_grid.values() if t == Terrain.RIVER)
            self.assertEqual(rivers, 0, "seed %d produced %d river tiles" % (seed, rivers))

    def test_quota_large_landmasses_have_a_river(self):
        theme = _make_theme()
        tpr = theme['tiles_per_river_tile']
        for seed in range(10):
            tm = terrain_generation.generate_terrain(theme, seed)
            non_sea = [pos for pos, t in tm.terrain_grid.items() if t != Terrain.SEA]
            for component in _connected_components(non_sea):
                if len(component) < tpr:
                    continue
                river_tiles = sum(1 for pos in component
                                  if tm.terrain_grid[pos] == Terrain.RIVER)
                self.assertGreaterEqual(
                    river_tiles, 1,
                    "seed %d: landmass of %d tiles has no river" % (seed, len(component)))

    def test_sources_are_spaced(self):
        theme = _make_theme()
        for seed in range(10):
            tm = terrain_generation.generate_terrain(theme, seed)
            sources = tm.river_sources
            for i in range(len(sources)):
                for j in range(i + 1, len(sources)):
                    self.assertGreater(
                        _chebyshev(sources[i], sources[j]), 2,
                        "seed %d: sources %s and %s too close" % (seed, sources[i], sources[j]))

    def test_every_river_terminates_or_was_erased(self):
        # Kept rivers end at SEA / RIVER / off-map, or ran out of room (deadend/cap) with
        # at least 3 painted tiles; anything shorter is never recorded (erased).
        theme = _make_theme()
        allowed = set(terrain_generation.RiverEnd)
        for seed in range(10):
            tm = terrain_generation.generate_terrain(theme, seed)
            for path, reason in tm.rivers:
                self.assertIn(reason, allowed, "seed %d: unexpected reason %s" % (seed, reason))
                painted = [p for p in path if tm.terrain_grid[p] == Terrain.RIVER]
                self.assertGreaterEqual(len(painted), 3,
                                        "seed %d: kept river shorter than 3 tiles" % seed)

    def test_no_river_runs_through_mountain_or_cliff(self):
        # The walk hard-excludes stepping onto MOUNTAIN/CLIFF, so no path tile past the
        # source is ever one (the source itself may be a mountain, which stays unpainted).
        theme = _make_theme()
        for seed in range(10):
            tm = terrain_generation.generate_terrain(theme, seed)
            for path, _reason in tm.rivers:
                for pos in path[1:]:
                    self.assertNotIn(tm.terrain_grid[pos], (Terrain.MOUNTAIN, Terrain.CLIFF),
                                     "seed %d: river crosses %s" % (seed, tm.terrain_grid[pos]))


if __name__ == '__main__':
    unittest.main()
