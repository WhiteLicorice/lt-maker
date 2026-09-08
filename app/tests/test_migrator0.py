import logging
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import pygame

from app.data.serialization.migrators.migrator0 import Migrator0

OLD_PORTRAIT_SIZE = (128, 112)


def _pixels(path: Path) -> bytes:
    """Raw pixel bytes of an image on disk, so comparisons don't depend on
    how the PNG itself happened to get encoded."""
    surf = pygame.image.load(str(path))
    return pygame.image.tobytes(surf, 'RGB')


class Migrator0PortraitTests(unittest.TestCase):
    """Migrating a portrait twice destroys it -- the second pass reads the new
    layout as if it were the old one. The 'old_portraits' back-up is what makes
    that recoverable, so it must survive a migration that gets re-run."""

    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.tmp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.tmp_dir, 'resources')
        self.portraits_dir = Path(self.data_dir, 'portraits')
        self.backup_dir = Path(self.data_dir, 'old_portraits')
        os.makedirs(self.portraits_dir)

        # A pre-migration portrait, with every region the migrator reads given a
        # distinct color so a wrong read is visible in the pixels
        surf = pygame.Surface(OLD_PORTRAIT_SIZE)
        surf.fill((10, 20, 30))
        surf.fill((200, 0, 0), (0, 0, 96, 80))      # face
        surf.fill((0, 200, 0), (96, 48, 32, 32))    # blink
        surf.fill((0, 0, 200), (0, 80, 128, 32))    # mouth
        surf.fill((200, 200, 0), (96, 16, 32, 32))  # minimug
        pygame.image.save(surf, str(Path(self.portraits_dir, 'test_portrait.png')))

        self.pristine = _pixels(Path(self.portraits_dir, 'test_portrait.png'))

    def tearDown(self):
        logging.disable(logging.NOTSET)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _migrate(self):
        resource_dict = {'portraits': [{'nid': 'test_portrait', 'info_offset': 0}]}
        return Migrator0().migrate_resources(resource_dict, self.data_dir)

    def test_first_migration_backs_up_the_original(self):
        self._migrate()
        self.assertTrue(self.backup_dir.exists())
        self.assertEqual(_pixels(Path(self.backup_dir, 'test_portrait.png')), self.pristine)
        # And the portrait itself was actually migrated
        self.assertNotEqual(_pixels(Path(self.portraits_dir, 'test_portrait.png')), self.pristine)

    def test_rerunning_migration_does_not_clobber_the_backup(self):
        self._migrate()
        migrated_once = _pixels(Path(self.portraits_dir, 'test_portrait.png'))

        # The project failed to load after the first migration, so the version on
        # disk was never bumped and we get asked to migrate the same folder again
        self._migrate()

        self.assertEqual(_pixels(Path(self.backup_dir, 'test_portrait.png')), self.pristine,
                         "Re-running the migration overwrote the pristine back-up")
        self.assertEqual(_pixels(Path(self.portraits_dir, 'test_portrait.png')), migrated_once,
                         "Portrait was migrated twice instead of being rolled back first")

    def test_migration_is_idempotent_across_many_failed_attempts(self):
        self._migrate()
        migrated_once = _pixels(Path(self.portraits_dir, 'test_portrait.png'))
        for _ in range(3):
            self._migrate()
        self.assertEqual(_pixels(Path(self.portraits_dir, 'test_portrait.png')), migrated_once)
        self.assertEqual(_pixels(Path(self.backup_dir, 'test_portrait.png')), self.pristine)

    def test_failed_migration_rolls_the_portrait_back(self):
        resource_dict = {'portraits': [{'nid': 'does_not_exist', 'info_offset': 0}]}
        with self.assertRaises(Exception):
            Migrator0().migrate_resources(resource_dict, self.data_dir)
        self.assertEqual(_pixels(Path(self.portraits_dir, 'test_portrait.png')), self.pristine)
