import os
import tempfile

import pygame

from app import sprites as sprite_registry
from app.constants import WINHEIGHT, WINWIDTH
from app.engine import dialog, sprites
from app.sprites import SPRITES
from app.tests.engine_harness import EngineTestCase

CUSTOM_COLOR = (12, 200, 34, 255)

class CustomEndingSpriteTests(EngineTestCase):
    '''
    endings_display / paired_endings_display ignored a project's custom_sprites
    folder. The editor imports dialog.py before any project is loaded, and the
    ending classes read their background when the module was imported, so they
    kept the stock sprite however many projects were loaded afterwards
    '''
    def setUp(self):
        super().setUp()
        self.start_harness()  # fonts
        self.addCleanup(sprites.load_images)
        self.addCleanup(sprite_registry.reset)

    def load_custom_sprite(self, name: str):
        custom_sprites = tempfile.TemporaryDirectory()
        self.addCleanup(custom_sprites.cleanup)
        surf = pygame.Surface((WINWIDTH, WINHEIGHT), pygame.SRCALPHA)
        surf.fill(CUSTOM_COLOR)
        pygame.image.save(surf, os.path.join(custom_sprites.name, name + '.png'))
        # What RESOURCES.load and driver.start do for a project's custom_sprites
        sprite_registry.load_sprites(custom_sprites.name)
        sprites.load_images()

    def test_ending_uses_custom_sprite(self):
        self.load_custom_sprite('endings_display')
        portrait = pygame.Surface((8, 8), pygame.SRCALPHA)
        ending = dialog.Ending(portrait, 'Title', 'Text', None)
        self.assertEqual(tuple(ending.bg.get_at((0, 0))), CUSTOM_COLOR)

    def test_paired_ending_uses_custom_sprite(self):
        self.load_custom_sprite('paired_endings_display')
        portrait = pygame.Surface((8, 8), pygame.SRCALPHA)
        ending = dialog.PairedEnding(portrait, portrait, 'Left', 'Right', 'Text', None, None)
        self.assertEqual(tuple(ending.bg.get_at((0, 0))), CUSTOM_COLOR)

    def test_stock_sprite_without_custom(self):
        portrait = pygame.Surface((8, 8), pygame.SRCALPHA)
        ending = dialog.Ending(portrait, 'Title', 'Text', None)
        self.assertEqual(ending.bg.get_at((0, 0)), SPRITES.get('endings_display').get_at((0, 0)))
