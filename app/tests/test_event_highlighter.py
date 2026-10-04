import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.tests import qt_headless  # noqa: F401 -- before any QApplication


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
        # Validation looks up the level the window is editing; no event is open
        return self.EventHighlighter(self.edit.document(), SimpleNamespace(current=None))

    def test_exception_in_match_line_does_not_escape(self):
        highlighter = self._build()
        with patch.object(self.EventSyntaxRuleHighlighter, 'match_line',
                          side_effect=ValueError('boom')), \
                self.assertLogs(level='ERROR') as logs:
            highlighter.highlightBlock('speak;Eirika;Hello, world')
        self.assertIn('Failed to syntax highlight line', logs.output[0])

    def test_normal_line_still_formats(self):
        highlighter = self._build()
        formatted = []
        with patch.object(self.EventHighlighter, 'setFormat',
                          side_effect=lambda *args: formatted.append(args)), \
                self.assertNoLogs(level='ERROR'):
            highlighter.highlightBlock('speak;Eirika;Hello, world')
        self.assertTrue(formatted)



class DialogCommandHighlightTests(unittest.TestCase):
    '''
    In dialog text, dialog commands like {w} and line breaks (|) stand out in the
    special text color. Python events used to color the whole line of dialog
    the plain text color
    '''

    def setUp(self) -> None:
        import sys
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication(sys.argv)
        from app import dark_theme
        style = dark_theme.get_theme().event_syntax_highlighting()
        self.text_color = style.text_color
        self.special_color = style.special_text_color

    def colors(self, highlighter_type, script, line_no):
        """Map each character of the given line to its highlighted foreground color"""
        from PyQt5.QtWidgets import QPlainTextEdit
        self.edit = QPlainTextEdit()
        self.edit.setPlainText(script)
        self.highlighter = highlighter_type(self.edit.document())
        self.highlighter.rehighlight()
        block = self.edit.document().findBlockByNumber(line_no)
        colors = {}
        for fmt_range in block.layout().formats():
            for i in range(fmt_range.start, fmt_range.start + fmt_range.length):
                colors[i] = fmt_range.format.foreground().color()
        return block.text(), colors

    def assert_dialog_colors(self, line, colors, dialog):
        start = line.index(dialog)
        for i, char in enumerate(dialog):
            in_command = dialog.index('{') <= i <= dialog.index('}')
            expected = self.special_color if in_command or char == '|' else self.text_color
            self.assertEqual(expected, colors.get(start + i), (dialog, i, char))

    def test_python_event_speak(self):
        from app.editor.event_editor.py_syntax import PythonHighlighter
        line, colors = self.colors(PythonHighlighter, '#pyev1\n$speak Eirika "Hi {w}there|friend"', 1)
        self.assert_dialog_colors(line, colors, '"Hi {w}there|friend"')

    def test_python_event_say(self):
        from app.editor.event_editor.py_syntax import PythonHighlighter
        line, colors = self.colors(PythonHighlighter, '#pyev1\n$say Eirika "Hi {w}there|friend"', 1)
        self.assert_dialog_colors(line, colors, '"Hi {w}there|friend"')

    def test_python_braces_outside_dialog_keep_python_colors(self):
        from app.editor.event_editor.py_syntax import PythonHighlighter
        line, colors = self.colors(PythonHighlighter, '#pyev1\nx = {1: 2}', 1)
        self.assertNotEqual(self.special_color, colors.get(line.index('{')))

    def test_event_speak(self):
        from app.editor.event_editor.event_highlighter import EventHighlighter
        line, colors = self.colors(lambda doc: EventHighlighter(doc, SimpleNamespace(current=None)), 'speak;Eirika;Hi {w}there|friend', 0)
        self.assert_dialog_colors(line, colors, 'Hi {w}there|friend')


class BraceSpansTests(unittest.TestCase):
    def test_spans(self):
        from app.editor.event_editor.event_highlighter import brace_spans
        self.assertEqual([(3, 3)], brace_spans('Hi {w}'))
        # Nested: the outermost group is covered in full
        self.assertEqual([(0, 5), (0, 10), (0, 11)], brace_spans('{a{b}c {d}}'))
        self.assertEqual([], brace_spans('no {close'))
        self.assertEqual([(4, 3)], brace_spans('} x {w}'))

if __name__ == '__main__':
    unittest.main()
