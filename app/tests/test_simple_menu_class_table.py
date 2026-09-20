import os
import unittest

import pygame

from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION

CLASSES = ['Citizen', 'Eirika_Lord', 'Eirika_Great_Lord']

class ClassTableTests(unittest.TestCase):
    '''
    eretein 4/29/25: `table;...;type_class;...` crashed with "expected string or bytes-like
    object, got 'Klass'". A class row was handed to the table as the bare Klass instead of
    the (icon, text, nid) tuple every other row type gets, so the table tried to render the
    Klass itself as text
    '''
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        pygame.display.init()
        if not pygame.display.get_surface():
            pygame.display.set_mode((1, 1))
        from app.data.database.database import DB
        from app.data.resources.resources import RESOURCES
        DB.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
        RESOURCES.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
        from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options
        from app.engine import fonts, sprites
        fonts.load_fonts()
        sprites.load_images()

    def setUp(self):
        from app.engine.game_state import game
        game.map_sprite_registry = {}

    def build_table(self, data):
        from app.engine.game_menus.menu_components.generic_menu.simple_menu_wrapper import SimpleMenuUI
        return SimpleMenuUI(data, 'type_class')

    def test_class_table_draws(self):
        surf = pygame.Surface((240, 160))
        for data in (CLASSES[:], lambda: CLASSES[:]):  # a plain list, and the `expression` flag's callable
            table = self.build_table(data)
            table.update()
            table.draw(surf)

    def test_class_rows_are_icon_name_and_nid(self):
        from app.data.database.database import DB
        from app.engine.graphics.ui_framework.ui_framework import UIComponent
        rows = self.build_table(CLASSES[:]).parse_data(CLASSES + ['Citizen|Farmer'])
        for nid, (icon, text, value) in zip(CLASSES, rows):
            self.assertIsInstance(icon, UIComponent)
            self.assertEqual((text, value), (DB.classes.get(nid).name, nid))
        self.assertEqual(rows[-1][1:], ('Farmer', 'Citizen'))

    def test_class_rows_are_rebuilt_every_update_so_their_sprites_animate(self):
        from unittest.mock import patch
        table = self.build_table(CLASSES[:])
        with patch.object(table.table, 'set_data') as set_data:
            table.update()
            table.update()
        self.assertEqual(set_data.call_count, 2)

if __name__ == '__main__':
    unittest.main()
