import os
import shutil
import sys
import tempfile
import unittest

from app.tests import qt_headless  # noqa: F401 -- before any QApplication

from PyQt5.QtGui import QImage, qRgb
from PyQt5.QtWidgets import QApplication

from app.constants import COLORKEY
from app.data.resources import combat_anims, combat_palettes
from app.data.resources.resources import RESOURCES
from app.editor.combat_animation_editor import combat_animation_imports


class LegacyAnimImportPaletteTests(unittest.TestCase):
    '''
    A legacy export writes one sheet per palette. The frames must be cut from a sheet
    and converted with that same sheet's palette, whatever order the sheets are found in
    '''

    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.tmp = tempfile.mkdtemp()
        self.blue = combat_palettes.Palette('TestLegacy_GenericBlue')
        self.blue.colors = {(0, 0): COLORKEY, (1, 0): (40, 80, 200), (2, 0): (16, 16, 16)}
        # "Ewan" sorts before "GenericBlue", so a sheet chosen by glob order is the wrong one
        self.ewan = combat_palettes.Palette('TestLegacy_Ewan')
        self.ewan.colors = {(0, 0): COLORKEY, (1, 0): (200, 120, 40), (2, 0): (16, 16, 16)}
        for palette in (self.blue, self.ewan):
            RESOURCES.combat_palettes.append(palette)
        self.anim = combat_anims.CombatAnimation('TestLegacy')
        self.anim.palettes = [['GenericBlue', self.blue.nid], ['Ewan', self.ewan.nid]]

    def tearDown(self) -> None:
        for palette in (self.blue, self.ewan):
            RESOURCES.combat_palettes.remove_key(palette.nid)
        shutil.rmtree(self.tmp)

    def write_export(self):
        for palette_name, palette in (('GenericBlue', self.blue), ('Ewan', self.ewan)):
            image = QImage(2, 1, QImage.Format_RGB32)
            image.setPixel(0, 0, qRgb(*palette.colors[(1, 0)]))
            image.setPixel(1, 0, qRgb(*palette.colors[(2, 0)]))
            image.save(os.path.join(self.tmp, 'TestLegacy-Sword-%s.png' % palette_name))
        with open(os.path.join(self.tmp, 'TestLegacy-Sword-Index.txt'), 'w') as fp:
            fp.write('F0;0,0;2,1;0,0\n')
        script_fn = os.path.join(self.tmp, 'TestLegacy-Sword-Script.txt')
        with open(script_fn, 'w') as fp:
            fp.write('pose;Stand\nframe;1;F0\n')
        return script_fn

    def test_frames_convert_to_palette_coords(self):
        combat_animation_imports.import_from_legacy(self.anim, self.write_export())
        frame = self.anim.weapon_anims.get('Sword').frames.get('F0')
        image = frame.pixmap.toImage()
        self.assertEqual(qRgb(0, 1, 0), image.pixel(0, 0))
        self.assertEqual(qRgb(0, 2, 0), image.pixel(1, 0))

    def test_no_colors_added_to_palettes(self):
        combat_animation_imports.import_from_legacy(self.anim, self.write_export())
        self.assertEqual(3, len(self.blue.colors))
        self.assertEqual(3, len(self.ewan.colors))


if __name__ == '__main__':
    unittest.main()
