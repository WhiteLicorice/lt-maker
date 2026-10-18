import unittest
from unittest.mock import patch

from app.data.resources.resources import RESOURCES
from app.engine import fonts, image_mods
from app.tests.engine_harness import EngineTestCase

class FontColorTests(EngineTestCase):
    '''
    Each font is registered once more for each of its palettes ('text-blue'
    and so on), writing in that color by default. Each palette is recolored
    once per font, and those registrations share the recolored sheets: built
    as fonts of their own, every one recolored every palette over again
    '''

    def load_counting_recolors(self) -> int:
        with patch('app.engine.bmpfont.image_mods.color_convert_alpha', wraps=image_mods.color_convert_alpha) as recolor:
            fonts.load_fonts(headless=True)
        return recolor.call_count

    def test_each_palette_is_recolored_once(self):
        palettes = 0
        for font in RESOURCES.fonts.values():
            if font.palettes.get(font.base_palette_nid):
                palettes += len([nid for nid in font.palettes if nid != font.base_palette_nid])
        self.assertGreater(palettes, 0)
        self.assertEqual(self.load_counting_recolors(), palettes)

    def test_a_color_registration_shares_its_fonts_sheets(self):
        self.load_counting_recolors()
        for font in RESOURCES.fonts.values():
            for color in font.palettes:
                registered = fonts.FONT['%s-%s' % (font.nid, color)]
                self.assertIs(registered.surfaces, fonts.FONT[font.nid].surfaces)
                self.assertEqual(registered.default_color, color)
                self.assertIs(registered.get_base_surf(), fonts.FONT[font.nid].surfaces[color])

    def test_a_color_registration_shares_its_fonts_glyphs(self):
        self.load_counting_recolors()
        for font in RESOURCES.fonts.values():
            c = next(iter(font.font_index.chartable))
            for color in font.palettes:
                registered = fonts.FONT['%s-%s' % (font.nid, color)]
                self.assertIs(registered._get_char_from_surf(c), fonts.FONT[font.nid]._get_char_from_surf(c, color))

if __name__ == '__main__':
    unittest.main()
