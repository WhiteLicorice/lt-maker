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
        # A recorded river reached water: it ends at SEA / RIVER / off-map. Dead-end and
        # capped walks never reach water and are erased (not painted, not recorded), so
        # they must not appear in tm.rivers. Kept rivers also paint at least 3 tiles.
        theme = _make_theme()
        clean = {terrain_generation.RiverEnd.SEA, terrain_generation.RiverEnd.RIVER,
                 terrain_generation.RiverEnd.OFFMAP}
        for seed in range(10):
            tm = terrain_generation.generate_terrain(theme, seed)
            for path, reason in tm.rivers:
                self.assertIn(reason, clean, "seed %d: kept river with reason %s" % (seed, reason))
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

    def test_lakes_exist_when_enabled_and_none_when_disabled(self):
        # Lakes on for most seeds at 8%; exactly zero SEA gained when disabled.
        on = _make_theme(lake_percent=0.08)
        off = _make_theme(lake_percent=0.0)
        seeds_with_lakes = 0
        for seed in range(10):
            base = {p for p, t in terrain_generation.generate_terrain(off, seed).terrain_grid.items()
                    if t == Terrain.SEA}
            lit = {p for p, t in terrain_generation.generate_terrain(on, seed).terrain_grid.items()
                   if t == Terrain.SEA}
            self.assertTrue(base <= lit, "seed %d: disabling lakes must only remove SEA" % seed)
            if lit - base:
                seeds_with_lakes += 1
        self.assertGreaterEqual(seeds_with_lakes, 8,
                                "lakes appeared on only %d/10 seeds" % seeds_with_lakes)

    def test_no_lake_within_chebyshev_2_of_coastline(self):
        # Lake tiles (SEA gained vs the lakes-disabled run) must sit > Chebyshev 2 from the
        # pre-lake coastline, so they never fuse into the coast.
        on = _make_theme(lake_percent=0.08)
        off = _make_theme(lake_percent=0.0)
        for seed in range(10):
            base = {p for p, t in terrain_generation.generate_terrain(off, seed).terrain_grid.items()
                    if t == Terrain.SEA}
            lit = {p for p, t in terrain_generation.generate_terrain(on, seed).terrain_grid.items()
                   if t == Terrain.SEA}
            for (lx, ly) in lit - base:
                for (sx, sy) in base:
                    self.assertGreater(max(abs(lx - sx), abs(ly - sy)), 2,
                                       "seed %d: lake at (%d,%d) hugs coast" % (seed, lx, ly))

    def test_deserts_are_a_noop_when_disabled(self):
        off = _make_theme(desert_percent=0.0)
        for seed in range(10):
            g = terrain_generation.generate_terrain(off, seed).terrain_grid
            for t in g.values():
                self.assertNotIn(t, (Terrain.DESERT, Terrain.DESERT_ROCK, Terrain.DESERT_CLIFF),
                                 "seed %d: desert tile appeared with deserts disabled" % seed)

    def test_desert_sand_skirt_outweighs_desert_core(self):
        # SAND is the common arid tile, true DESERT only the rare core. The pass must add more
        # SAND than DESERT. (DESERT_ROCK is excluded: it is mostly replaced mountains, a
        # separate feature from the sand-skirt / desert-core relationship.)
        on = _make_theme(desert_percent=0.15)
        off = _make_theme(desert_percent=0.0)
        for seed in range(10):
            g_on = terrain_generation.generate_terrain(on, seed).terrain_grid
            g_off = terrain_generation.generate_terrain(off, seed).terrain_grid
            sand_on = {p for p, t in g_on.items() if t == Terrain.SAND}
            sand_off = {p for p, t in g_off.items() if t == Terrain.SAND}
            sand_gained = len(sand_on - sand_off)
            core = sum(1 for t in g_on.values() if t == Terrain.DESERT)
            if core == 0:
                continue  # no arid land this seed
            self.assertGreater(sand_gained, core,
                               "seed %d: sand skirt %d not > desert core %d" % (seed, sand_gained, core))

    def test_desert_never_directly_touches_vegetation(self):
        # True DESERT reaches grass/forest only through the SAND skirt: no DESERT tile is
        # 4-adjacent to vegetation (erosion guarantees this). Checking DESERT alone keeps the
        # invariant crisp; scattered DESERT_ROCK sits on interior desert, not the eroded edge.
        on = _make_theme(desert_percent=0.15)
        veg = (Terrain.NOISY_GRASS, Terrain.FOREST, Terrain.SPARSE_FOREST, Terrain.THICKET)
        for seed in range(10):
            g = terrain_generation.generate_terrain(on, seed).terrain_grid
            core = [p for p, t in g.items() if t == Terrain.DESERT]
            if not core:
                continue
            violations = 0
            for (x, y) in core:
                for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if g.get(n) in veg:
                        violations += 1
                        break
            self.assertLessEqual(violations, max(1, len(core) // 20),
                                 "seed %d: %d/%d desert tiles touch vegetation" % (seed, violations, len(core)))

    def test_desert_rocks_are_sparse_and_on_desert(self):
        # DESERT_ROCK is only the scatter on flat desert (mountains flatten to DESERT/SAND,
        # they do not become rock). It must stay a small minority of the desert region.
        on = _make_theme(desert_percent=0.15, desert_rock_chance=0.06)
        saw_rock = False
        for seed in range(10):
            g = terrain_generation.generate_terrain(on, seed).terrain_grid
            rocks = sum(1 for t in g.values() if t == Terrain.DESERT_ROCK)
            region = sum(1 for t in g.values() if t in (Terrain.DESERT, Terrain.DESERT_ROCK))
            if region == 0:
                continue
            saw_rock = saw_rock or rocks > 0
            self.assertLess(rocks, region * 0.25,
                            "seed %d: rocks %d not sparse vs region %d" % (seed, rocks, region))
        self.assertTrue(saw_rock, "no desert rocks scattered across 10 seeds")

    def test_desert_replaces_mountains_in_the_blob(self):
        # Mountains inside an arid blob flatten to DESERT/SAND like hills, so enabling deserts
        # strictly reduces the mountain count on at least some seeds (a blob covering a peak).
        on = _make_theme(desert_percent=0.20)
        off = _make_theme(desert_percent=0.0)
        reduced = False
        for seed in range(10):
            mtn_on = sum(1 for t in terrain_generation.generate_terrain(on, seed).terrain_grid.values()
                         if t == Terrain.MOUNTAIN)
            mtn_off = sum(1 for t in terrain_generation.generate_terrain(off, seed).terrain_grid.values()
                          if t == Terrain.MOUNTAIN)
            self.assertLessEqual(mtn_on, mtn_off, "seed %d: deserts added mountains" % seed)
            reduced = reduced or mtn_on < mtn_off
        self.assertTrue(reduced, "deserts never replaced a mountain across 10 seeds")

    def test_deserts_are_deterministic(self):
        on = _make_theme(desert_percent=0.15)
        for seed in range(5):
            a = terrain_generation.generate_terrain(on, seed).terrain_grid
            b = terrain_generation.generate_terrain(on, seed).terrain_grid
            self.assertEqual(a, b, "seed %d: desert generation not deterministic" % seed)

    def test_pangaea_is_one_landmass(self):
        # A pangaea layout must collapse the land into a single dominant continent.
        theme = _make_theme(size=(30, 30), macro_layout='pangaea')
        for seed in range(10):
            g = terrain_generation.generate_terrain(theme, seed).terrain_grid
            land = {p for p, t in g.items() if t != Terrain.SEA}
            if not land:
                continue
            largest = max(len(c) for c in _connected_components(land))
            self.assertGreaterEqual(largest, 0.85 * len(land),
                                    "seed %d: largest landmass %d/%d < 85%%" % (seed, largest, len(land)))

    def test_enclosed_layouts_are_surrounded_by_sea(self):
        # Pangaea and continents must be islands: no land on the outer tile ring, any seed.
        for layout in ('pangaea', 'continents'):
            theme = _make_theme(size=(40, 24), macro_layout=layout)
            for seed in range(10):
                g = terrain_generation.generate_terrain(theme, seed).terrain_grid
                w, h = 40, 24
                ring = [(x, y) for x in range(w) for y in range(h)
                        if x in (0, w - 1) or y in (0, h - 1)]
                land = [p for p in ring if g[p] != Terrain.SEA]
                self.assertEqual(land, [], "%s seed %d: %d land tiles on border ring"
                                 % (layout, seed, len(land)))

    def test_continents_makes_multiple_landmasses(self):
        # Continents should usually yield two separate sizable landmasses (noise can bridge
        # them on some seeds -- require it on most, not all).
        theme = _make_theme(size=(40, 28), macro_layout='continents')
        good = 0
        for seed in range(10):
            g = terrain_generation.generate_terrain(theme, seed).terrain_grid
            land = {p for p, t in g.items() if t != Terrain.SEA}
            big = [c for c in _connected_components(land) if len(c) >= 20]
            if len(big) >= 2:
                good += 1
        self.assertGreaterEqual(good, 7, "only %d/10 seeds had 2+ landmasses" % good)

    def test_none_layout_is_a_noop(self):
        # With no macro layout, the hint weight must not touch the output at all.
        a = _make_theme(macro_layout='none', hint_weight=0.55)
        b = _make_theme(macro_layout='none', hint_weight=0.0)
        for seed in range(5):
            ga = terrain_generation.generate_terrain(a, seed).terrain_grid
            gb = terrain_generation.generate_terrain(b, seed).terrain_grid
            self.assertEqual(ga, gb, "seed %d: 'none' layout was not a no-op" % seed)

    def test_macro_layout_is_deterministic(self):
        for layout in ('pangaea', 'continents', 'coastal'):
            theme = _make_theme(size=(30, 24), macro_layout=layout)
            for seed in range(4):
                a = terrain_generation.generate_terrain(theme, seed).terrain_grid
                b = terrain_generation.generate_terrain(theme, seed).terrain_grid
                self.assertEqual(a, b, "%s seed %d: not deterministic" % (layout, seed))


if __name__ == '__main__':
    unittest.main()
