import unittest
from unittest.mock import MagicMock, patch

from app.tests.engine_harness import EngineTestCase
from app.engine import dialog, fonts

# Fits a default width text box with 3 pixels to spare -- but not with the waiting cursor after it
FULL_LINE = "Doesn't look like you've got anything to forge."

class DialogCursorWrapTests(EngineTestCase):
    def setUp(self):
        super().setUp()
        fonts.load_fonts(headless=True)

    def _process(self, text, **kwargs) -> dialog.Dialog:
        with patch.object(dialog.engine, 'create_surface', new=MagicMock()), \
                patch.object(dialog, 'create_base_surf', new=MagicMock()):
            box = dialog.Dialog(text, speaker='Narrator', **kwargs)
            box.warp_speed()
        return box

    def _line_widths(self, box: dialog.Dialog):
        return [box.tagged_text[start:stop].width() for start, stop in box.text_indices]

    def _cursor_right_edge(self, box: dialog.Dialog, line_width: int) -> int:
        return line_width + box.cursor_gap + box.cursor.get_width()

    def test_cursor_moves_last_word_to_next_line(self):
        '''
        Ram 9/29/25: a line that only just fits the box drew the waiting cursor over its border
        '''
        box = self._process(FULL_LINE)
        widths = self._line_widths(box)
        self.assertEqual(len(widths), 2)
        self.assertLessEqual(self._cursor_right_edge(box, widths[-1]), box.text_width)

    def test_cursor_at_mid_text_wait(self):
        box = self._process(FULL_LINE + "{w} Ok.")
        widths = self._line_widths(box)
        # The word before the wait leaves the first line, taking the cursor with it
        self.assertLess(widths[0], box.tagged_text[0:len(FULL_LINE)].width())
        self.assertEqual(len(widths), 2)
        before_wait = box.tagged_text[box.text_indices[1].start:len(FULL_LINE)].width()
        self.assertLessEqual(self._cursor_right_edge(box, before_wait), box.text_width)

    def test_autosized_box_is_built_wide_enough_for_the_cursor(self):
        '''
        Windward 9/24/26: an autosized box sized itself from a balanced split that
        knew nothing about the cursor, so the typing wrap dropped the last word to
        a line of its own and left the rest of the box empty
        '''
        for text in ("All right, back into the fray! Let's go, Franz!",
                     'She seems very...sincere.'):
            with self.subTest(text=text):
                box = self._process(text, autosize=True)
                widths = self._line_widths(box)
                bare = self._line_widths(self._process(text, autosize=True, draw_cursor=False))
                self.assertEqual(len(widths), len(bare))
                self.assertLessEqual(self._cursor_right_edge(box, widths[-1]), box.text_width)

    def test_no_room_reserved_without_cursor(self):
        self.assertEqual(len(self._line_widths(self._process(FULL_LINE, draw_cursor=False))), 1)
        self.assertEqual(len(self._line_widths(self._process(FULL_LINE + "{no_wait}"))), 1)
        # The cursor comes after the break, at the start of the next line
        self.assertEqual(len(self._line_widths(self._process(FULL_LINE + "{br}Ok."))), 2)

if __name__ == '__main__':
    unittest.main()
