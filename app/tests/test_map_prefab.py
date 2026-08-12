import unittest

from app.map_maker.map_prefab import MapPrefab
from app.map_maker.terrain import Terrain


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


if __name__ == '__main__':
    unittest.main()
