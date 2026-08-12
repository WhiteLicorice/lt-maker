import unittest
from unittest.mock import MagicMock, patch
from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
import app.engine.dialog

from app.events.speak_style import SpeakStyle, SpeakStyleLibrary

class CsvExporterTests(unittest.TestCase):
    def setUp(self):
        from app.data.resources.resources import RESOURCES
        from app.engine import fonts
        RESOURCES.load('testing_proj.ltproj', CURRENT_SERIALIZATION_VERSION)
        fonts.load_fonts(headless=True)
        self.db = SpeakStyleLibrary()

    def tearDown(self) -> None:
        pass

    def test_speak_style_matches_dialog_args(self):
        with patch('app.engine.dialog.engine', new=MagicMock()):
            with patch('app.engine.dialog.create_base_surf', new=lambda *args: None):
                full_style = SpeakStyle('a', 'b', (1, 2), 25, 5.0, 'blue', 'text', 'some_bg', 3, True, 'tail', 2.5, 'None', set('FLAG1'))
                # should not throw
                app.engine.dialog.Dialog.from_style(full_style, 'testing text', None, 11)

    def _speak(self, *args, **kwargs) -> dict:
        '''Runs the speak event function and returns the kwargs it built the Dialog with'''
        from app.events import event_functions
        from app.events.event import Event

        fake_event = MagicMock()
        fake_event.game.speak_styles = SpeakStyleLibrary()
        fake_event.portraits = {}
        fake_event.do_skip = False
        fake_event.text_boxes = []
        fake_event._get_unit.return_value = None
        fake_event._resolve_speak_style = \
            lambda *styles: Event._resolve_speak_style(fake_event, *styles)

        with patch.object(event_functions.dialog, 'Dialog') as mock_dialog:
            event_functions.speak(fake_event, *args, **kwargs)
        return mock_dialog.call_args.kwargs

    def test_speak_uses_draw_cursor_of_style(self):
        '''
        A style that hides the dialog cursor must keep it hidden. speak() used to
        default its own draw_cursor to True, which then overrode the style's False
        '''
        # cinematic is a built in style with draw_cursor=False
        self.assertFalse(self._speak('Eirika', 'text', style_nid='cinematic')['draw_cursor'])
        self.assertFalse(self._speak('cinematic', 'text')['draw_cursor'])
        # ...but the cursor is still on by default, and still explicitly settable
        self.assertTrue(self._speak('Eirika', 'text')['draw_cursor'])
        self.assertTrue(self._speak('Eirika', 'text', style_nid='cinematic', draw_cursor=True)['draw_cursor'])
        self.assertFalse(self._speak('Eirika', 'text', draw_cursor=False)['draw_cursor'])

if __name__ == '__main__':
    unittest.main()
