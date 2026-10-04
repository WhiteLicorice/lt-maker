import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.tests import qt_headless  # noqa: F401 -- before any QApplication

GREEN = (168, 208, 160)   # the frames' transparent background, which becomes LT's colorkey
DARK = (40, 40, 40)
BLUE = (88, 96, 144)

SCRIPT = """/// - Mode 1
3 p- Lance-0.png
3 p- Lance-1.png
/// - Mode 5
3 p- Lance-0.png
/// - End
"""

def write_frame(path, draw):
    from PIL import Image
    image = Image.new('P', (248, 160), 0)
    image.putpalette(list(GREEN) + list(DARK) + list(BLUE) + [0, 0, 0] * 253)
    draw(image)
    for y in range(3):  # palette column, as GBA frames ship it
        for x in range(240, 248):
            image.putpixel((x, y), y)
    image.save(path)

def fill(image, left, top, width, height, index):
    for x in range(left, left + width):
        for y in range(top, top + height):
            image.putpixel((x, y), index)

def ordinary_frame(image):
    fill(image, 100, 60, 20, 30, 2)

def critical_backdrop_frame(image):
    # Dark across the top rows, leaving the name window corners clear, like Heathcliff's critical
    fill(image, 0, 0, 240, 100, 1)
    fill(image, 0, 8, 56, 16, 0)
    fill(image, 184, 8, 56, 16, 0)
    fill(image, 100, 60, 20, 30, 2)

class GBAScriptImportCropTests(unittest.TestCase):
    '''
    Heathcliff 7/28/25: importing a GBA animation cut off the top rows of any frame whose
    top left pixel is artwork. The importer measured each frame without saying what its
    background was, so get_bbox guessed from that pixel -- here the dark backdrop -- and
    trimmed the dark rows across the top as if they were empty
    '''
    @classmethod
    def setUpClass(cls):
        import sys
        from PyQt5.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        write_frame(os.path.join(self.folder, 'Lance-0.png'), ordinary_frame)
        write_frame(os.path.join(self.folder, 'Lance-1.png'), critical_backdrop_frame)
        self.script = os.path.join(self.folder, 'Lance.txt')
        with open(self.script, 'w') as fp:
            fp.write(SCRIPT)

    def import_lance(self):
        from app.data.resources import combat_anims
        from app.data.resources.resources import RESOURCES
        from app.editor.combat_animation_editor import combat_animation_imports
        from app.editor.file_manager.project_file_backend import DEFAULT_PROJECT

        palettes_before = set(RESOURCES.combat_palettes.keys())
        def remove_new_palettes():
            for nid in set(RESOURCES.combat_palettes.keys()) - palettes_before:
                RESOURCES.combat_palettes.remove_key(nid)
        self.addCleanup(remove_new_palettes)

        # Point the "current project" at the default one, so the import writes nothing to disk
        settings = MagicMock()
        settings.get_current_project.return_value = os.path.join(self.folder, DEFAULT_PROJECT)
        current = combat_anims.CombatAnimation('Test')
        with patch.object(combat_animation_imports, 'MainSettingsController', return_value=settings):
            combat_animation_imports.import_from_gba(current, self.script)
        return current.weapon_anims.get('Lance')

    def test_frame_with_artwork_in_its_top_left_keeps_its_top_rows(self):
        frame = self.import_lance().frames.get('Lance-1')
        self.assertEqual(frame.offset, (0, 0))
        self.assertEqual((frame.pixmap.width(), frame.pixmap.height()), (240, 100))

    def test_ordinary_frame_is_trimmed_to_its_artwork(self):
        frame = self.import_lance().frames.get('Lance-0')
        self.assertEqual(frame.offset, (100, 60))
        self.assertEqual((frame.pixmap.width(), frame.pixmap.height()), (20, 30))

if __name__ == '__main__':
    unittest.main()
