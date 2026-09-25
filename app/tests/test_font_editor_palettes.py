import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


class FontPaletteEditorTests(unittest.TestCase):
    '''
    A font's non-default palettes are defined as an index-for-index recoloring of
    its default palette, and the default palette names the colors that actually
    appear in the sprite sheet. A freshly imported font had neither, so a palette
    added to it came out empty -- no swatches to click, nothing to recolor.
    '''

    @classmethod
    def setUpClass(cls) -> None:
        import sys
        from PyQt5.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.png_path = os.path.join('default.ltproj', 'resources', 'fonts', 'bconvo.png')

    def make_font(self):
        from app.data.resources.fonts import Font
        font = Font(nid='test_font')
        font.set_full_path(self.png_path[:-len('.png')])
        return font

    def test_new_font_seeds_its_default_palette_from_the_sheet(self):
        from app.editor.font_editor.font_model import seed_default_palette
        font = self.make_font()
        self.assertTrue(seed_default_palette(font))
        self.assertEqual(font.default_color, 'default')
        # bconvo.png's glyphs are dark grey with a light grey shadow, in that order
        self.assertEqual(font.palettes['default'][:2],
                         [(40, 40, 40, 255), (184, 184, 184, 255)])

    def test_seeding_leaves_an_existing_default_palette_alone(self):
        from app.editor.font_editor.font_model import seed_default_palette
        font = self.make_font()
        font.default_color = 'black'
        font.palettes['black'] = [(1, 2, 3, 255)]
        self.assertFalse(seed_default_palette(font))
        self.assertEqual(font.palettes, {'black': [(1, 2, 3, 255)]})

    def test_palette_added_to_a_new_font_has_editable_swatches(self):
        from unittest.mock import patch
        from PyQt5.QtWidgets import QPushButton
        from app.editor.font_editor.font_properties import PaletteEditor
        font = self.make_font()
        editor = PaletteEditor()
        editor.set_font(font)
        with patch('app.editor.font_editor.font_properties.QInputDialog.getText',
                   return_value=('red', True)):
            editor._add_palette()
        self.assertTrue(font.palettes['red'])
        self.assertEqual(font.palettes['red'], font.palettes[font.default_color])
        swatches = [editor._edit_swatch_layout.itemAt(i).widget()
                    for i in range(editor._edit_swatch_layout.count())]
        self.assertEqual(len(swatches), len(font.palettes['red']))
        self.assertTrue(all(isinstance(s, QPushButton) for s in swatches))

    def test_default_palette_stays_listed_and_read_only(self):
        from PyQt5.QtWidgets import QPushButton
        from app.editor.font_editor.font_model import seed_default_palette
        from app.editor.font_editor.font_properties import PaletteEditor
        font = self.make_font()
        seed_default_palette(font)
        editor = PaletteEditor()
        editor.set_font(font)
        names = [editor.palette_list.item(i).text() for i in range(editor.palette_list.count())]
        self.assertEqual(names, ['default'])
        swatches = [editor._edit_swatch_layout.itemAt(i).widget()
                    for i in range(editor._edit_swatch_layout.count())]
        self.assertEqual(len(swatches), len(font.palettes['default']))
        self.assertFalse(any(isinstance(s, QPushButton) for s in swatches))

    def test_adding_a_palette_updates_the_default_color_dropdown(self):
        from unittest.mock import patch
        from PyQt5.QtWidgets import QWidget
        from app.data.resources.resources import RESOURCES
        from app.editor.font_editor.font_properties import FontProperties
        window = QWidget()
        window._data = RESOURCES.fonts
        props = FontProperties(window)
        font = self.make_font()
        props.set_current(font)
        with patch('app.editor.font_editor.font_properties.QInputDialog.getText',
                   return_value=('red', True)):
            props.palette_editor._add_palette()
        default_color_names = [props.default_color_box.edit.itemText(i)
                               for i in range(props.default_color_box.edit.count())]
        self.assertIn('red', default_color_names)
        # The palette list selects what it just added, and the preview follows it
        self.assertEqual(props.palette_editor.palette_list.currentItem().text(), 'red')
        self.assertEqual(props.preview_color, 'red')
        self.assertEqual(props.preview_color_label.text(), 'red')

    def test_default_palette_cannot_be_deleted(self):
        from unittest.mock import patch
        from app.editor.font_editor.font_model import seed_default_palette
        from app.editor.font_editor.font_properties import PaletteEditor
        font = self.make_font()
        seed_default_palette(font)
        editor = PaletteEditor()
        editor.set_font(font)
        with patch('app.editor.font_editor.font_properties.QMessageBox.warning'):
            editor._delete_palette()
        self.assertIn('default', font.palettes)

    def test_bmpfont_survives_a_default_color_with_no_palette(self):
        import pygame
        from app.engine.bmpfont import BmpFont
        pygame.init()
        font = self.make_font()
        font.default_color = 'not_a_palette'
        font.palettes['red'] = [(1, 2, 3, 255)]
        bmp_font = BmpFont(font, headless=True)
        self.assertIn('red', bmp_font.surfaces)


if __name__ == '__main__':
    unittest.main()
