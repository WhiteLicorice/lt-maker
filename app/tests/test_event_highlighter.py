import os
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


class HighlightBlockNeverRaisesTests(unittest.TestCase):
    '''
    highlightBlock() is a reimplemented Qt virtual. PyQt aborts the whole
    process (SIGABRT -- no dialog, no chance to save the event) when an
    exception escapes one, so a bad line must degrade to unhighlighted text
    rather than take the editor down with it.
    '''

    def setUp(self) -> None:
        import sys
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication(sys.argv)

        from app.editor.event_editor.event_highlighter import EventSyntaxRuleHighlighter, EventHighlighter
        self.EventSyntaxRuleHighlighter = EventSyntaxRuleHighlighter
        self.EventHighlighter = EventHighlighter

    def _build(self):
        from PyQt5.QtWidgets import QPlainTextEdit
        self.edit = QPlainTextEdit()
        return self.EventHighlighter(self.edit.document(), None)

    def test_exception_in_match_line_does_not_escape(self):
        highlighter = self._build()
        with patch.object(self.EventSyntaxRuleHighlighter, 'match_line',
                          side_effect=ValueError('boom')):
            highlighter.highlightBlock('speak;Eirika;Hello, world')

    def test_normal_line_still_formats(self):
        highlighter = self._build()
        formatted = []
        with patch.object(self.EventHighlighter, 'setFormat',
                          side_effect=lambda *args: formatted.append(args)):
            highlighter.highlightBlock('speak;Eirika;Hello, world')
        self.assertTrue(formatted)


if __name__ == '__main__':
    unittest.main()
