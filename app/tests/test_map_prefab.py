import random
import sys
import unittest
from typing import Dict, Tuple
from unittest.mock import patch

import pygame

from app.constants import TILEWIDTH, TILEHEIGHT
from app.utilities import utils
from app.utilities.typing import Pos
import app.map_maker.utilities as map_utils
from app.map_maker.map_prefab import MapPrefab
from app.map_maker.mountain_processing_csp import CSPProcess
from app.map_maker.painter_database import PAINTERS
from app.map_maker.painters.mountain_painter import MountainPainter
from app.map_maker.painters.pool_painter import PoolPainter
from app.map_maker.terrain import Terrain
import app.map_maker.pygame_renderers.draw_tilemap as pygame_draw_tilemap


class FakeThread():
    """Stands in for a NaiveBacktrackingThread/CSPThread. QThread.finished is
    emitted from inside wait(), so that is where the callback is invoked."""
    def __init__(self, on_finished):
        self.on_finished = on_finished
        self.stopped = False

    def stop(self):
        self.stopped = True

    def wait(self):
        self.on_finished()


class MapPrefabResizeTests(unittest.TestCase):
    def setUp(self):
        self.tilemap = MapPrefab('test')
        # 15x10 by default
        self.tilemap.set((0, 0), None, Terrain.SEA)      # autotiled
        self.tilemap.set((1, 0), None, Terrain.MOUNTAIN)  # not autotiled
        self.tilemap.terrain_grid_to_update.clear()

    def test_resize_offsets_terrain(self):
        self.tilemap.resize(15, 12, 0, 2)
        self.assertEqual(self.tilemap.get_terrain((0, 2)), Terrain.SEA)
        self.assertEqual(self.tilemap.get_terrain((1, 2)), Terrain.MOUNTAIN)
        self.assertIsNone(self.tilemap.get_terrain((0, 0)))

    def test_resize_offsets_autotile_set(self):
        """A stale autotile position points draw_tilemap's autotile pass at
        whatever terrain has moved onto it, skipping terrain_grid_to_update
        and asking painters for coords they have not solved yet."""
        self.assertEqual(self.tilemap.autotile_set, {(0, 0)})
        self.tilemap.resize(15, 12, 0, 2)
        self.assertEqual(self.tilemap.autotile_set, {(0, 2)})

    def test_resize_drops_out_of_bounds_positions(self):
        self.tilemap.resize(15, 10, 0, -1)  # shift everything off the top
        self.assertEqual(self.tilemap.terrain_grid, {})
        self.assertEqual(self.tilemap.autotile_set, set())

    def test_resize_offsets_cliff_markers_and_clamps(self):
        self.tilemap.cliff_markers = [(7, 5), (0, 9)]
        self.tilemap.resize(15, 12, 0, 2)
        self.assertEqual(self.tilemap.cliff_markers, [(7, 7), (0, 11)])

    def test_resize_marks_everything_for_update(self):
        self.tilemap.resize(15, 12, 0, 2)
        self.assertEqual(self.tilemap.terrain_grid_to_update, {(0, 2), (1, 2)})


class MountainPainterThreadTests(unittest.TestCase):
    def setUp(self):
        self.painter = MountainPainter()

    def test_cancelled_thread_is_dropped_before_wait(self):
        """A cancelled solve reports positions from before the resize, so the
        finished callback must be able to tell it apart from a real completion.
        It does that by membership in current_threads -- which therefore has to
        be updated before wait() lets the finished signal through."""
        seen = []
        thread = FakeThread(lambda: seen.append(thread in self.painter.current_threads))
        self.painter.current_threads.append(thread)

        self.painter.quit_all_threads()

        self.assertTrue(thread.stopped)
        self.assertEqual(seen, [False])
        self.assertEqual(self.painter.current_threads, [])

    def test_quit_single_thread_is_dropped_before_wait(self):
        seen = []
        thread = FakeThread(lambda: seen.append(thread in self.painter.current_threads))
        self.painter.current_threads.append(thread)

        self.painter._quit_thread(thread)

        self.assertTrue(thread.stopped)
        self.assertEqual(seen, [False])
        self.assertEqual(self.painter.current_threads, [])


class CSPProcessTests(unittest.TestCase):
    def test_group_larger_than_recursion_limit(self):
        """The search goes one level deeper per tile, so a group with more
        tiles than Python's recursion limit must still be solved"""
        painter = MountainPainter()
        painter._initial_process()
        tilemap = MapPrefab('test')
        tilemap.width, tilemap.height = 36, 36
        group = {(x, y) for x in range(2, 34) for y in range(2, 34) if not (x < 5 and y < 5)}
        self.assertGreater(len(group), sys.getrecursionlimit())
        process = CSPProcess(tilemap, painter.mountain_data, painter.noneless_rules, group, gui_processing=False)
        with patch('builtins.print'):
            process.process_group()
        self.assertTrue(process.did_complete)
        self.assertEqual(set(process.organization), group)


def build_mixed_tilemap(size: int = 20) -> MapPrefab:
    """Open sea with sand islands, a river, forests touching the map edge,
    and a pool in an indoor floor -- every autotiled terrain plus the
    painters that work out per-forest state in single_process"""
    grid = {}
    for x in range(size):
        for y in range(size):
            if x < size // 2:
                terrain = Terrain.SAND if 2 <= x <= 3 and 2 <= y <= 4 else Terrain.SEA
            elif x == size // 2 + 1:
                terrain = Terrain.RIVER
            elif x > 3 * size // 4 and y < size // 2 and (x + y) % 5:
                terrain = Terrain.FOREST
            elif y > 3 * size // 4:
                terrain = Terrain.POOL if (x + y) % 4 == 0 else Terrain.FLOOR_1
            else:
                terrain = Terrain.FOREST if (x * y) % 7 == 0 else Terrain.GRASS
            grid[(x, y)] = terrain
    tilemap = MapPrefab('test')
    tilemap.set_new_terrain_grid((size, size), grid)
    return tilemap


def build_pool_grid() -> Tuple[Tuple[int, int], Dict[Pos, Terrain]]:
    """A pool wide enough to have open pool, ringed by floor, with a floor
    tile inside it -- a size and terrain grid for set_new_terrain_grid"""
    grid = {(x, y): Terrain.POOL if 1 <= x <= 14 and 1 <= y <= 14 else Terrain.FLOOR_1
            for x in range(16) for y in range(16)}
    grid[(4, 11)] = Terrain.FLOOR_1
    return (16, 16), grid


def update_at_frame(tilemap: MapPrefab, frame: int):
    # At autotile_fps=1 each autotile frame lasts 16.66 ms
    with patch.object(pygame_draw_tilemap.time, 'time_ns', return_value=(int(frame * 16.66) + 1) * 1_000_000):
        pygame_draw_tilemap.update_tile_grid(tilemap, autotile_fps=1)


def draw_at_frame(tilemap: MapPrefab, frame: int) -> bytes:
    update_at_frame(tilemap, frame)
    return pygame.image.tobytes(pygame_draw_tilemap.simple_draw_tilemap(tilemap), 'RGBA')


def fresh_draw_at_frame(tilemap: MapPrefab, frame: int) -> bytes:
    """Every position drawn from scratch at this frame, with no autotile pass"""
    tilemap.reset_all()
    pygame_draw_tilemap.last_autotile_num = frame
    return draw_at_frame(tilemap, frame)


class DrawTilemapTests(unittest.TestCase):
    def setUp(self):
        pygame_draw_tilemap.last_autotile_num = 0
        self.tilemap = build_mixed_tilemap()
        draw_at_frame(self.tilemap, 0)

    def test_autotile_frame_matches_fresh_draw(self):
        """The autotile pass redraws from the coords cached at the last update,
        so it must land on exactly what a full redraw at that frame gives"""
        for frame in (1, 7, 15):
            incremental = draw_at_frame(self.tilemap, frame)
            self.assertEqual(incremental, fresh_draw_at_frame(self.tilemap, frame), frame)

    def test_edits_then_autotile_frame_match_fresh_draw(self):
        # Coast sea, the middle of a forest, a river turned to grass, and an erase
        self.tilemap.set((9, 9), Terrain.SEA, Terrain.SAND)
        self.tilemap.set((17, 3), self.tilemap.get_terrain((17, 3)), Terrain.FOREST)
        self.tilemap.set((11, 5), Terrain.RIVER, Terrain.GRASS)
        self.tilemap.erase_terrain((0, 0), Terrain.SEA)
        draw_at_frame(self.tilemap, 3)
        incremental = draw_at_frame(self.tilemap, 9)
        self.assertEqual(incremental, fresh_draw_at_frame(self.tilemap, 9))

    def test_land_near_open_sea_then_autotile_frame_match_fresh_draw(self):
        """A bridge does not count as land, so turning one into land changes
        which sea tiles up to 3 tiles away are open sea, though they are
        not adjacent and not flood filled with it"""
        grid = {(x, y): Terrain.SEA for x in range(16) for y in range(16)}
        for x in range(16):
            grid[(x, 8)] = Terrain.BRIDGEH
        self.tilemap.set_new_terrain_grid((16, 16), grid)
        draw_at_frame(self.tilemap, 0)
        self.tilemap.set((8, 8), Terrain.BRIDGEH, Terrain.GRASS)
        draw_at_frame(self.tilemap, 2)
        incremental = draw_at_frame(self.tilemap, 9)
        self.assertEqual(incremental, fresh_draw_at_frame(self.tilemap, 9))

        self.tilemap.erase_terrain((8, 8), Terrain.GRASS)
        draw_at_frame(self.tilemap, 11)
        incremental = draw_at_frame(self.tilemap, 13)
        self.assertEqual(incremental, fresh_draw_at_frame(self.tilemap, 13))

    def test_floor_in_open_pool_then_autotile_frame_match_fresh_draw(self):
        """A floor tile changes which pool tiles up to 2 tiles away are open
        pool, though they are not adjacent and pools are not flood filled"""
        self.tilemap.set_new_terrain_grid(*build_pool_grid())
        draw_at_frame(self.tilemap, 0)
        self.tilemap.set((8, 8), Terrain.POOL, Terrain.FLOOR_1)
        draw_at_frame(self.tilemap, 2)
        incremental = draw_at_frame(self.tilemap, 9)
        self.assertEqual(incremental, fresh_draw_at_frame(self.tilemap, 9))

        self.tilemap.erase_terrain((8, 8), Terrain.FLOOR_1)
        draw_at_frame(self.tilemap, 11)
        incremental = draw_at_frame(self.tilemap, 13)
        self.assertEqual(incremental, fresh_draw_at_frame(self.tilemap, 13))

    def test_set_many_then_autotile_frame_match_fresh_draw(self):
        """set_many flood fills once against the map before and after every
        change, instead of after each one, which must still mark every blob"""
        # Bucket fill the grass and forest region with sea, joining the main sea
        region = {pos for pos, terrain in self.tilemap.terrain_grid.items()
                  if terrain in (Terrain.GRASS, Terrain.FOREST) and pos[0] < 16 and pos[1] < 12}
        self.tilemap.set_many({pos: Terrain.SEA for pos in region})
        draw_at_frame(self.tilemap, 2)
        incremental = draw_at_frame(self.tilemap, 9)
        self.assertEqual(incremental, fresh_draw_at_frame(self.tilemap, 9))

        # Widen the forest in the top right: its bounds change for every tile in it,
        # which must all be marked, not just the ones next to the new forest
        self.tilemap.set_many({(x, y): Terrain.FOREST for x in range(12, 16) for y in range(10)})
        forest = map_utils.flood_fill(self.tilemap, (12, 0))
        self.assertIn((19, 9), forest)
        self.assertLessEqual(forest, self.tilemap.terrain_grid_to_update)
        draw_at_frame(self.tilemap, 4)
        incremental = draw_at_frame(self.tilemap, 6)
        self.assertEqual(incremental, fresh_draw_at_frame(self.tilemap, 6))

        # Stamp a mix of flood filled terrains across sea, river and forest
        stamp = [Terrain.FOREST, Terrain.SEA, Terrain.SAND, Terrain.CLIFF]
        self.tilemap.set_many({(x, y): stamp[(x + y) % len(stamp)] for x in range(6, 19) for y in range(2, 8)})
        draw_at_frame(self.tilemap, 11)
        incremental = draw_at_frame(self.tilemap, 13)
        self.assertEqual(incremental, fresh_draw_at_frame(self.tilemap, 13))

    def test_random_edits_on_sea_match_fresh_draw(self):
        """Sea is not flood filled, so every edit must mark each sea tile
        whose sprite it can change -- the ones up to 3 tiles away"""
        rng = random.Random(0)
        brushes = [Terrain.GRASS, Terrain.SAND, Terrain.SEA, Terrain.RIVER,
                   Terrain.BRIDGEH, Terrain.FOREST, None]
        for step in range(40):
            pos = (rng.randrange(self.tilemap.width), rng.randrange(self.tilemap.height))
            brush = rng.choice(brushes)
            if brush:
                self.tilemap.set(pos, self.tilemap.get_terrain(pos), brush)
            elif self.tilemap.get_terrain(pos):
                self.tilemap.erase_terrain(pos, self.tilemap.get_terrain(pos))
            incremental = draw_at_frame(self.tilemap, step % 16)
            self.assertEqual(incremental, fresh_draw_at_frame(self.tilemap, step % 16), (step, pos, brush))

    def test_autotile_coords_follow_autotile_set(self):
        self.assertEqual(set(self.tilemap.autotile_coords), self.tilemap.autotile_set)
        self.tilemap.set((5, 5), Terrain.SEA, Terrain.GRASS)
        self.tilemap.erase_terrain((6, 6), Terrain.SEA)
        self.assertNotIn((5, 5), self.tilemap.autotile_coords)
        self.assertNotIn((6, 6), self.tilemap.autotile_coords)
        self.tilemap.set((15, 5), Terrain.GRASS, Terrain.SEA)
        draw_at_frame(self.tilemap, 0)
        self.assertEqual(set(self.tilemap.autotile_coords), self.tilemap.autotile_set)


class TileGridChangedTests(unittest.TestCase):
    """The map maker view keeps its own image of the map and draws on it
    again only the tiles in tile_grid_changed, so that must hold every
    position whose tile was set or removed"""
    def setUp(self):
        pygame_draw_tilemap.last_autotile_num = 0
        self.tilemap = build_mixed_tilemap()
        update_at_frame(self.tilemap, 0)
        self.image = pygame_draw_tilemap.simple_draw_tilemap(self.tilemap)
        self.tilemap.tile_grid_changed.clear()

    def assert_image_up_to_date(self, frame: int, msg=None):
        """Brings self.image up to date the way the view does, and checks it against a full draw"""
        update_at_frame(self.tilemap, frame)
        for pos in self.tilemap.tile_grid_changed:
            rect = (pos[0] * TILEWIDTH, pos[1] * TILEHEIGHT, TILEWIDTH, TILEHEIGHT)
            self.image.fill((0, 0, 0, 0), rect)
            if pos in self.tilemap.tile_grid:
                self.image.blit(self.tilemap.tile_grid[pos], rect)
        self.tilemap.tile_grid_changed.clear()
        full_image = pygame_draw_tilemap.simple_draw_tilemap(self.tilemap)
        self.assertEqual(pygame.image.tobytes(self.image, 'RGBA'), pygame.image.tobytes(full_image, 'RGBA'), msg)

    def test_edits_erases_and_autotile_frames(self):
        rng = random.Random(2)
        brushes = [Terrain.GRASS, Terrain.SAND, Terrain.SEA, Terrain.RIVER,
                   Terrain.FOREST, Terrain.POOL, None]
        for step in range(40):
            pos = (rng.randrange(self.tilemap.width), rng.randrange(self.tilemap.height))
            brush = rng.choice(brushes)
            if brush:
                self.tilemap.set(pos, self.tilemap.get_terrain(pos), brush)
            elif self.tilemap.get_terrain(pos):
                self.tilemap.erase_terrain(pos, self.tilemap.get_terrain(pos))
            self.assert_image_up_to_date(step % 16, (step, pos, brush))
        self.tilemap.set_many({(x, y): Terrain.SEA for x in range(12, 18) for y in range(4)})
        self.assert_image_up_to_date(3)

    def test_resize_in_place_and_clear(self):
        # Same size, shifted: every tile moves, and the ones shifted off leave the image
        self.tilemap.resize(self.tilemap.width, self.tilemap.height, 2, -3)
        self.assert_image_up_to_date(5)
        self.tilemap.clear()
        # clear() also shrinks the map, which a view meets by drawing it all again
        self.tilemap.width, self.tilemap.height = 20, 20
        self.assert_image_up_to_date(6)


class SeaPainterTests(unittest.TestCase):
    def test_distance_to_closest_land_is_exact_under_4(self):
        """get_coord only asks whether land is nearer than 2-4 tiles, so the
        windowed search must be exact below 4 and report nothing nearer beyond it"""
        tilemap = build_mixed_tilemap()
        sea_painter = PAINTERS[Terrain.SEA]
        for pos in tilemap.get_all_terrain(Terrain.SEA):
            land = [other for other, terrain in tilemap.terrain_grid.items()
                    if terrain not in (Terrain.SEA, Terrain.BRIDGEV, Terrain.BRIDGEH)]
            brute_force = min(utils.distance(pos, other) for other in land)
            distance = sea_painter._distance_to_closest_land(tilemap, pos)
            if brute_force < 4:
                self.assertEqual(distance, brute_force, pos)
            else:
                self.assertGreaterEqual(distance, 4, pos)


class PoolPainterTests(unittest.TestCase):
    def test_distance_to_closest_nonpool_is_exact_under_3(self):
        """get_coord only asks whether a non-pool tile is nearer than 1-3 tiles,
        so the windowed search must be exact below 3 and report nothing nearer beyond it"""
        tilemap = MapPrefab('test')
        tilemap.set_new_terrain_grid(*build_pool_grid())
        nonpool = [other for other, terrain in tilemap.terrain_grid.items() if terrain != Terrain.POOL]
        for pos in tilemap.get_all_terrain(Terrain.POOL):
            brute_force = min(utils.distance(pos, other) for other in nonpool)
            distance = PoolPainter._distance_to_closest_nonpool(tilemap, pos)
            if brute_force < 3:
                self.assertEqual(distance, brute_force, pos)
            else:
                self.assertGreaterEqual(distance, 3, pos)


if __name__ == '__main__':
    unittest.main()
