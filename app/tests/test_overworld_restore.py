import os
import unittest
from unittest.mock import MagicMock


class StaleOverworldSaveTests(unittest.TestCase):
    '''
    A save records overworlds by nid and remembers a menu option per node, but the
    project can be edited after the save is made. Loading has to survive an
    overworld that was renamed or deleted, and nodes that were added since
    '''

    @classmethod
    def setUpClass(cls) -> None:
        # The overworld builds its tilemap surface up front, which needs a display
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        import pygame
        pygame.display.init()
        if not pygame.display.get_surface():
            pygame.display.set_mode((1, 1))

        from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
        from app.data.resources.resources import RESOURCES
        from app.data.database.database import DB
        RESOURCES.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
        DB.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
        cls.DB = DB

    def build_game(self):
        game = MagicMock()
        game.parties = {}
        game.unit_registry = {}
        return game

    def saved_overworld(self):
        from app.engine.objects.overworld.overworld import OverworldObject
        prefab = self.DB.overworlds[0]
        overworld = OverworldObject.from_prefab(prefab, {}, {})
        return prefab, overworld.save()

    def test_an_overworld_missing_from_the_database_is_skipped(self):
        from app.engine.objects.overworld.overworld import OverworldObject
        _, s_dict = self.saved_overworld()
        s_dict['prefab_nid'] = 'renamed_since_the_save'
        with self.assertLogs(level='ERROR') as logged:
            self.assertIsNone(OverworldObject.restore(s_dict, self.build_game()))
        self.assertIn('renamed_since_the_save', str(logged.output))

    def test_a_present_overworld_still_restores(self):
        from app.engine.objects.overworld.overworld import OverworldObject
        prefab, s_dict = self.saved_overworld()
        restored = OverworldObject.restore(s_dict, self.build_game())
        self.assertIsNotNone(restored)
        self.assertEqual(prefab.nid, restored.nid)

    def test_a_node_added_after_the_save_keeps_its_prefab_settings(self):
        from app.engine.objects.overworld.overworld import OverworldObject
        prefab, s_dict = self.saved_overworld()
        node = prefab.overworld_nodes[0]
        # The save predates this node, so it holds no entry for it
        s_dict['enabled_menu_options'].pop(node.nid, None)
        s_dict['visible_menu_options'].pop(node.nid, None)

        restored = OverworldObject.restore(s_dict, self.build_game())
        self.assertIn(node.nid, restored.enabled_menu_options)
        self.assertIn(node.nid, restored.visible_menu_options)
        for option in node.menu_options:
            self.assertEqual(option.enabled, restored.enabled_menu_options[node.nid][option.nid])
            self.assertEqual(option.visible, restored.visible_menu_options[node.nid][option.nid])

    def test_a_node_deleted_after_the_save_is_not_resurrected(self):
        from app.engine.objects.overworld.overworld import OverworldObject
        _, s_dict = self.saved_overworld()
        s_dict['enabled_menu_options']['node_that_no_longer_exists'] = {'Battle': True}

        restored = OverworldObject.restore(s_dict, self.build_game())
        self.assertNotIn('node_that_no_longer_exists', restored.enabled_menu_options)

class MenuOptionMergeTests(unittest.TestCase):
    '''
    The sample overworld carries no node menu options, so the merge itself is
    exercised directly
    '''

    def merge(self, from_prefab, saved):
        from app.engine.objects.overworld.overworld import OverworldObject
        return OverworldObject._restore_menu_options(from_prefab, saved)

    def test_a_saved_setting_wins_over_the_prefab(self):
        merged = self.merge({'town': {'Battle': True}}, {'town': {'Battle': False}})
        self.assertEqual({'town': {'Battle': False}}, merged)

    def test_a_node_added_since_the_save_keeps_the_prefab_setting(self):
        merged = self.merge({'town': {'Battle': True}, 'new_node': {'Shop': True}},
                            {'town': {'Battle': False}})
        self.assertEqual({'town': {'Battle': False}, 'new_node': {'Shop': True}}, merged)

    def test_an_option_added_since_the_save_keeps_the_prefab_setting(self):
        merged = self.merge({'town': {'Battle': True, 'Shop': True}},
                            {'town': {'Battle': False}})
        self.assertEqual({'town': {'Battle': False, 'Shop': True}}, merged)

    def test_a_node_deleted_since_the_save_stays_deleted(self):
        merged = self.merge({'town': {'Battle': True}}, {'gone': {'Battle': False}})
        self.assertEqual({'town': {'Battle': True}}, merged)

    def test_an_option_deleted_since_the_save_stays_deleted(self):
        merged = self.merge({'town': {'Battle': True}},
                            {'town': {'Battle': False, 'Gone': True}})
        self.assertEqual({'town': {'Battle': False}}, merged)


if __name__ == '__main__':
    unittest.main()
