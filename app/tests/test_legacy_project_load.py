import logging
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.data.database.database import DB
from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
from app.utilities.serialization import rmtree_robust


class LegacyProjectLoadTests(unittest.TestCase):
    """Projects made before a data type existed are still missing its file on disk.
    They must load anyway, with an empty catalog, instead of raising."""

    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.tmp_dir = tempfile.mkdtemp()
        self.proj_dir = Path(self.tmp_dir, 'legacy.ltproj')
        shutil.copytree('default.ltproj', self.proj_dir)

    def tearDown(self):
        logging.disable(logging.NOTSET)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _delete_data(self, key: str):
        as_dir = Path(self.proj_dir, 'game_data', key)
        as_file = Path(self.proj_dir, 'game_data', key + '.json')
        if as_dir.exists():
            rmtree_robust(as_dir)
        if as_file.exists():
            os.remove(as_file)

    def test_missing_credit_data_loads_as_empty(self):
        self._delete_data('credit')
        DB.load(self.proj_dir, CURRENT_SERIALIZATION_VERSION)
        self.assertEqual(len(DB.credit), 0)

    def test_missing_credit_data_is_written_back_out(self):
        self._delete_data('credit')
        DB.load(self.proj_dir, CURRENT_SERIALIZATION_VERSION)
        self.assertTrue(DB.serialize(str(self.proj_dir), as_chunks=True))
        self.assertTrue(Path(self.proj_dir, 'game_data', 'credit').exists())

    def test_missing_required_data_still_raises(self):
        self._delete_data('units')
        with self.assertRaises(FileNotFoundError):
            DB.load(self.proj_dir, CURRENT_SERIALIZATION_VERSION)


class EmptyCreditScreenTests(unittest.TestCase):
    """A project with no credits at all must not crash the credit state."""

    def test_populate_options_with_no_credits(self):
        from app.data.database.credit import CreditCatalog
        from app.engine.credit_state import populate_options
        options, ignore, ordered_credits = populate_options(CreditCatalog())
        self.assertEqual(len(options), 0)
        self.assertEqual(len(ignore), 0)
        self.assertEqual(len(ordered_credits), 0)
