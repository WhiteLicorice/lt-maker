import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION

class IconRenameDeleteTests(unittest.TestCase):
    '''
    Renaming an icon in the icon editor and then deleting it removed the icon sheet but left the
    renamed icon on screen until the editor was reopened. The rename set the icon's nid directly,
    so the model's nid-keyed lookup still held it under its old name, and the delete skipped it
    '''
    @classmethod
    def setUpClass(cls):
        import sys
        from PyQt5.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        from unittest.mock import patch
        from app.data.resources.resources import RESOURCES
        from app.editor.icon_editor import icon_model
        from app.editor.icon_editor.icon_model import Icon32Model
        from app.editor.icon_editor.icon_tab import Icon32Database
        # When the loaded database has factions using the icon, deleting it asks for confirmation
        # in a modal dialog. Answer OK, as the reporter did
        dialog_patch = patch.object(icon_model.DeletionDialog, 'inform', return_value=True)
        dialog_patch.start()
        self.addCleanup(dialog_patch.stop)
        RESOURCES.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
        self.tab = Icon32Database(RESOURCES.icons32, "32x32 Icon", Icon32Model)
        self.model = self.tab.full_model

    def test_renamed_icon_is_removed_when_deleted(self):
        from PyQt5.QtCore import Qt
        rows = self.model.rowCount()
        self.model.setData(self.model.index(0), 'Renamed', Qt.EditRole)
        self.assertIs(self.model.sub_data.get('Renamed'), self.model.sub_data[0])

        self.tab.view.delete(self.tab.model.index(0, 0))
        self.assertEqual(self.model.rowCount(), rows - 1)
        self.assertNotIn('Renamed', [icon.nid for icon in self.model.sub_data])

if __name__ == '__main__':
    unittest.main()
