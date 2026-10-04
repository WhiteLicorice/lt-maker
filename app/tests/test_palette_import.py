import os
import unittest

from app.tests import qt_headless  # noqa: F401 -- before any QApplication


class AssignNewColorsTests(unittest.TestCase):
    '''
    Combat animation sheets are stored in palette coordinate space -- each pixel is
    qRgb(0, x, y). A source color the palette never took on survives the conversion
    as literal RGB and is read back as the coord (green, blue), which is what
    produced "Cannot find coord: (104, 56)" for the color (168, 104, 56)
    '''

    def setUp(self) -> None:
        import sys
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication(sys.argv)

        from app.data.resources.combat_palettes import Palette
        import app.editor.utilities as editor_utilities
        self.Palette = Palette
        self.utils = editor_utilities

    def build_palette(self, colors):
        palette = self.Palette('Test')
        palette.assign_colors(colors)
        return palette

    def test_same_count_but_different_colors_still_registers_them(self):
        '''
        The import used to gate on len(image colors) > len(palette), so an image
        with as many colors as the palette contributed none of its own
        '''
        palette = self.build_palette([(i, 0, 0) for i in range(14)])
        image_colors = [(i, 0, 0) for i in range(12)] + [(168, 104, 56), (192, 176, 16)]
        self.assertEqual(14, len(image_colors))
        new_colors = self.utils.assign_new_colors(palette, image_colors)
        self.assertEqual({(6, 1): (168, 104, 56), (7, 1): (192, 176, 16)}, new_colors)

    def test_known_colors_are_not_reassigned(self):
        palette = self.build_palette([(i, 0, 0) for i in range(14)])
        self.assertEqual({}, self.utils.assign_new_colors(palette, [(3, 0, 0), (7, 0, 0)]))

    def test_a_repeated_new_color_only_takes_one_slot(self):
        palette = self.build_palette([(0, 0, 0)])
        new_colors = self.utils.assign_new_colors(palette, [(9, 9, 9), (9, 9, 9)])
        self.assertEqual({(1, 0): (9, 9, 9)}, new_colors)

    def test_unconvertible_colors_are_reported(self):
        from PyQt5.QtGui import QImage, qRgb
        palette = self.build_palette([(0, 0, 0), (168, 104, 56)])
        image = QImage(2, 1, QImage.Format_RGB32)
        image.setPixel(0, 0, qRgb(0, 0, 0))
        image.setPixel(1, 0, qRgb(192, 176, 16))
        convert_dict = self.utils.get_color_conversion(palette)
        self.assertEqual([(192, 176, 16)],
                         self.utils.find_unconvertible_colors(image, convert_dict))

    def test_nothing_reported_when_every_color_converts(self):
        from PyQt5.QtGui import QImage, qRgb
        palette = self.build_palette([(0, 0, 0), (192, 176, 16)])
        image = QImage(2, 1, QImage.Format_RGB32)
        image.setPixel(0, 0, qRgb(0, 0, 0))
        image.setPixel(1, 0, qRgb(192, 176, 16))
        convert_dict = self.utils.get_color_conversion(palette)
        self.assertEqual([], self.utils.find_unconvertible_colors(image, convert_dict))


class SheetsStayInCoordSpaceTests(unittest.TestCase):
    '''
    A sheet pixel is qRgb(0, x, y), naming a palette slot. Any pixel whose red
    channel is set is a literal color instead, and every reader decodes it as the
    coord (green, blue) -- so it renders the same under every palette and the
    palette editor cannot find it
    '''

    # The Eirika Lord sheets carry a raw colorkey from some other route and are
    # deliberately left alone for now
    ANIMATIONS = ('Berserker', 'ArcherFemale2')

    def setUp(self) -> None:
        import sys
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication(sys.argv)

    def sheet_colors(self, path):
        from PyQt5.QtGui import QColor, QImage
        image = QImage(path).convertToFormat(QImage.Format_Indexed8)
        self.assertLess(image.colorCount(), 256, 'too many colors to read exactly')
        return [QColor(c) for c in image.colorTable()]

    def palettes_of(self, nid):
        import glob
        import json
        import os
        with open(os.path.join('default.ltproj', 'resources', 'combat_anims',
                               'combat_anims.json'), encoding='utf-8') as fp:
            anims = json.load(fp)
        anim = next(a for a in anims if a['nid'] == nid)
        sheets = sorted(glob.glob(os.path.join(
            'default.ltproj', 'resources', 'combat_anims', '%s-*.png' % nid)))
        palettes = {}
        for _, palette_nid in anim['palettes']:
            path = os.path.join('default.ltproj', 'resources', 'combat_palettes',
                                'palette_data', '%s.json' % palette_nid)
            with open(path, encoding='utf-8') as fp:
                for stored_nid, colors in json.load(fp):
                    palettes[stored_nid] = {tuple(coord) for coord, _ in colors}
        return sheets, palettes

    def test_every_pixel_names_a_palette_slot(self):
        for nid in self.ANIMATIONS:
            sheets, palettes = self.palettes_of(nid)
            self.assertTrue(sheets)
            for sheet in sheets:
                raw = sorted((c.red(), c.green(), c.blue())
                             for c in self.sheet_colors(sheet) if c.red())
                self.assertEqual([], raw, '%s stores literal colors' % sheet)

    def test_every_coord_used_exists_in_every_palette(self):
        for nid in self.ANIMATIONS:
            sheets, palettes = self.palettes_of(nid)
            self.assertTrue(palettes)
            used = set()
            for sheet in sheets:
                used |= {(c.green(), c.blue()) for c in self.sheet_colors(sheet)}
            for palette_nid, coords in palettes.items():
                self.assertEqual(set(), used - coords,
                                 '%s is missing coords its sheets use' % palette_nid)

if __name__ == '__main__':
    unittest.main()
