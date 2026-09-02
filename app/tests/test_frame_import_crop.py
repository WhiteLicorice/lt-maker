import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

BACKGROUND = (168, 208, 160)   # the repo's transparent green, not LT's colorkey


class ImportedFrameCropTests(unittest.TestCase):
    '''
    A GBA format frame is 240 wide plus an 8 pixel column on the right holding the
    palette. That column is not the background color, so measuring the bounding box
    before removing it stretches the frame across to the palette and sweeps up all
    the background in between -- which renders as a solid rectangle in game. A 480
    wide frame is two frames side by side, the second drawn under the unit
    '''

    @classmethod
    def setUpClass(cls) -> None:
        import sys
        from PyQt5.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def build_frame(self, width, blob=(116, 54, 71, 55), palette_strip=True,
                    second_blob=None):
        from PyQt5.QtGui import QColor, QImage, QPixmap
        image = QImage(width, 160, QImage.Format_RGB32)
        image.fill(QColor(*BACKGROUND))
        for rect in (blob, second_blob):
            if not rect:
                continue
            bx, by, bw, bh = rect
            for x in range(bx, bx + bw):
                for y in range(by, by + bh):
                    image.setPixelColor(x, y, QColor(88, 96, 144))
        if palette_strip:
            # 14 palette entries parked in the extra column, as the repo art ships them
            for idx in range(14):
                for x in range(width - 8, width):
                    image.setPixelColor(x, idx, QColor(40 + idx * 8, 40, 40))
        return QPixmap.fromImage(image)

    def crop(self, *args, **kwargs):
        from app.editor.combat_animation_editor.animation_import_utils import \
            crop_imported_frames
        return crop_imported_frames('Bael_000', self.build_frame(*args, **kwargs))

    def test_the_palette_column_is_not_treated_as_artwork(self):
        blob = (116, 54, 71, 55)
        frames = self.crop(248, blob)
        self.assertEqual(1, len(frames))
        nid, cropped, rect = frames[0]
        self.assertEqual('Bael_000', nid)
        self.assertEqual(blob, rect)
        self.assertEqual((blob[2], blob[3]), (cropped.width(), cropped.height()))

    def test_a_frame_without_a_palette_column_is_unchanged(self):
        blob = (116, 54, 71, 55)
        nid, cropped, rect = self.crop(240, blob, palette_strip=False)[0]
        self.assertEqual(blob, rect)
        self.assertEqual((blob[2], blob[3]), (cropped.width(), cropped.height()))

    def test_a_double_width_frame_becomes_two_frames(self):
        left = (20, 54, 40, 55)
        right = (300, 54, 71, 55)
        frames = self.crop(488, left, second_blob=right)
        self.assertEqual(['Bael_000', 'Bael_000_under'], [f[0] for f in frames])
        self.assertEqual(left, frames[0][2])
        # The under half is measured within its own 240 wide space
        self.assertEqual((right[0] - 240, right[1], right[2], right[3]), frames[1][2])

    def test_an_empty_under_half_is_not_imported(self):
        frames = self.crop(488, (20, 54, 40, 55))
        self.assertEqual(['Bael_000'], [f[0] for f in frames])

    def test_measuring_before_cropping_is_what_went_wrong(self):
        '''Documents the trap: the raw bounding box reaches the palette column'''
        import app.editor.utilities as editor_utilities
        raw = self.build_frame(248)
        x, y, width, height = editor_utilities.get_bbox(raw.toImage())
        self.assertEqual(248, x + width)
        self.assertEqual(0, y)


if __name__ == '__main__':
    unittest.main()
