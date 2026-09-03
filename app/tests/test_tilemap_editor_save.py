import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

MARKER = 'TEST_MARKER_TERRAIN'


class TilemapEditorSaveTests(unittest.TestCase):
    '''
    The Save button in the tilemap editor has to leave the project on disk holding
    the edits. The resource dialog that owns the tilemap editor restores itself on
    Cancel by reloading the project from disk, so a save that misses the disk -- or
    hits the wrong project -- silently throws away every map edit the moment the
    user backs out of that dialog instead of hitting OK.
    '''

    @classmethod
    def setUpClass(cls) -> None:
        import sys
        from app.editor.editor_locale import init_locale
        init_locale()
        from PyQt5.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self) -> None:
        from app.data.database.database import DB
        from app.data.resources.resources import RESOURCES
        from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION

        self.tmp_dir = tempfile.mkdtemp()
        self.proj = os.path.join(self.tmp_dir, 'save_test.ltproj')
        shutil.copytree('default.ltproj', self.proj)

        DB.load(self.proj, CURRENT_SERIALIZATION_VERSION)
        RESOURCES.load(self.proj, CURRENT_SERIALIZATION_VERSION)
        self.version = CURRENT_SERIALIZATION_VERSION

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def make_editor(self, proj_dir):
        """A tilemap editor on the first tilemap, pointed at proj_dir."""
        from app.data.resources.resources import RESOURCES
        from app.editor.tilemap_editor import MapEditor

        editor = MapEditor(None, RESOURCES.tilemaps[0])
        patcher = patch.object(
            type(editor.settings), 'get_current_project', return_value=proj_dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        return editor

    def terrain_on_disk(self):
        """What the project on disk says the first tilemap's origin terrain is.

        This is what the owning resource dialog's Cancel would restore.
        """
        from app.data.resources.resources import RESOURCES
        RESOURCES.load(self.proj, self.version)
        return RESOURCES.tilemaps[0].layers[0].terrain_grid.get((0, 0))

    @patch('app.editor.tilemap_editor.QMessageBox')
    def test_save_survives_cancelling_the_resource_dialog(self, _message_box):
        editor = self.make_editor(self.proj)
        editor.current.layers[0].terrain_grid[(0, 0)] = MARKER

        editor.save_current()

        self.assertEqual(self.terrain_on_disk(), MARKER)

    @patch('app.editor.tilemap_editor.QMessageBox')
    def test_save_then_cancel_in_the_tilemap_editor_keeps_the_save(self, _message_box):
        editor = self.make_editor(self.proj)
        editor.current.layers[0].terrain_grid[(0, 0)] = MARKER

        editor.save_current()
        # Backing out of the tilemap editor rewinds to its snapshot, which the
        # save should have advanced -- otherwise Save then Cancel loses the work.
        editor.restore()

        self.assertEqual(editor.current.layers[0].terrain_grid.get((0, 0)), MARKER)

    @patch('app.editor.tilemap_editor.QMessageBox')
    def test_save_goes_to_the_current_project_not_a_stale_one(self, _message_box):
        from app.data.database.database import DB

        # What a Save As leaves behind if nothing resyncs it
        stale = os.path.join(self.tmp_dir, 'stale.ltproj')
        shutil.copytree(self.proj, stale)
        DB.current_proj_dir = stale

        editor = self.make_editor(self.proj)
        editor.current.layers[0].terrain_grid[(0, 0)] = MARKER
        editor.save_current()

        self.assertEqual(self.terrain_on_disk(), MARKER)

    @patch('app.editor.tilemap_editor.QMessageBox')
    def test_save_refuses_to_write_to_the_default_project(self, message_box):
        editor = self.make_editor('some/path/default.ltproj')
        editor.current.layers[0].terrain_grid[(0, 0)] = MARKER

        editor.save_current()

        self.assertNotEqual(self.terrain_on_disk(), MARKER)
        message_box.warning.assert_called_once()


if __name__ == '__main__':
    unittest.main()
