from types import SimpleNamespace
from unittest.mock import patch

from app.data.database.database import DB
from app.engine import dialog, engine, fonts, game_state
from app.engine.dialog_log import DialogLog
from app.tests.engine_harness import EngineTestCase


class DialogSpeakerNameTests(EngineTestCase):
    '''
    A unit speaks under its nid, but the dialog log and the nametag show its name
    '''
    def setUp(self):
        super().setUp()
        fonts.load_fonts(headless=True)
        game_state.game.unit_registry = {}
        DB.units.get('Seth').name = 'Sir Seth'

    def test_unit_not_in_game_shows_its_prefab_name(self):
        self.assertEqual(dialog.speaker_name('Seth'), 'Sir Seth')

    def test_unit_in_game_shows_its_current_name(self):
        game_state.game.unit_registry['Seth'] = SimpleNamespace(nid='Seth', name='Seth the Silver', portrait_nid=None)
        self.assertEqual(dialog.speaker_name('Seth'), 'Seth the Silver')

    def test_other_speakers_show_as_written(self):
        self.assertEqual(dialog.speaker_name('Mysterious Voice'), 'Mysterious Voice')

    def test_dialog_log_shows_name_and_keeps_nid(self):
        log = DialogLog()
        log.append(('Seth', 'Princess!'))
        self.assertEqual(log.ui.entries[-1].name, 'Sir Seth')
        self.assertEqual(log.save(), [('Seth', 'Princess!')])

    def test_nametag_shows_name(self):
        box = dialog.Dialog('Princess!', speaker='Seth')
        box.warp_speed()
        box.state = dialog.DialogState.WAIT
        with patch.object(dialog.Dialog, 'draw_nametag') as draw_nametag:
            box.draw(engine.create_surface((240, 160)))
        draw_nametag.assert_called_once()
        self.assertEqual(draw_nametag.call_args.args[1], 'Sir Seth')
