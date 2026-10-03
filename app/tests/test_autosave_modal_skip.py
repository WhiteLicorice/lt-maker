import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


class AutosaveWaitsForModalDialogTests(unittest.TestCase):
    '''
    Autosave shows a modal progress dialog. Firing it while another modal dialog is open
    (e.g. Load Unit while placing units) stacked two modal dialogs, reported to freeze the
    editor on macOS. Autosave now waits until no modal dialog is open
    '''

    def setUp(self):
        from app.editor.file_manager import project_file_backend
        self.module = project_file_backend
        self.backend = project_file_backend.ProjectFileBackend.__new__(project_file_backend.ProjectFileBackend)
        self.backend._autosave_waiting = False
        self.backend.autosave = MagicMock()
        self.modal = None
        self.retries = []
        for patcher in (
                patch.object(project_file_backend.QApplication, 'activeModalWidget', lambda: self.modal),
                patch.object(project_file_backend.QTimer, 'singleShot', lambda ms, func: self.retries.append(func))):
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_retries(self):
        retries, self.retries = self.retries, []
        for retry in retries:
            retry()

    def test_saves_right_away_when_no_dialog_is_open(self):
        self.backend.attempt_autosave()
        self.backend.autosave.assert_called_once()
        self.assertEqual(self.retries, [])

    def test_waits_while_a_dialog_is_open_then_saves_once_it_closes(self):
        self.modal = object()
        self.backend.attempt_autosave()
        self.backend.autosave.assert_not_called()

        self.run_retries()  # Dialog still open
        self.backend.autosave.assert_not_called()

        self.modal = None
        self.run_retries()
        self.backend.autosave.assert_called_once()
        self.assertEqual(self.retries, [])

    def test_timer_firing_again_while_waiting_does_not_start_a_second_wait(self):
        self.modal = object()
        self.backend.attempt_autosave()
        self.backend.attempt_autosave()
        self.assertEqual(len(self.retries), 1)

        self.modal = None
        self.run_retries()
        self.backend.autosave.assert_called_once()


if __name__ == '__main__':
    unittest.main()
