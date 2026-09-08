import unittest

from app.map_maker.map_prefab import MapPrefab
from app.map_maker.painters.mountain_painter import MountainPainter
from app.map_maker.terrain import Terrain


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


if __name__ == '__main__':
    unittest.main()
