from __future__ import annotations

import os
import tempfile
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QProgressDialog

from app.data.database.database import DB
from app.editor.file_manager.project_file_backend import DEFAULT_PROJECT, ProjectFileBackend
from app.utilities import file_utils, web_export

class WebExporter():
    '''
    Exports the open project as a zip of its browser version, ready to upload
    to itch.io, through app/utilities/web_export.py
    '''
    def __init__(self, proj_file_manager: ProjectFileBackend):
        self.proj_file_manager = proj_file_manager

    def _save(self) -> bool:
        '''
        Saves the project, as the build reads it from disk. The default
        project can't be saved over, so it is built as it is on disk
        '''
        if os.path.basename(self.proj_file_manager.current_proj) == DEFAULT_PROJECT:
            return True
        if not self.proj_file_manager.save():
            QMessageBox.warning(None, "Cannot export project",
                                "Cannot export the project without saving it. Please save the project "
                                "before exporting it.")
            return False
        return True

    def _confirm_game_nid(self) -> bool:
        '''
        The browser keeps a game's saves by its game_nid. On a site that serves
        many games, as itch.io does, two games with the same one share them
        '''
        if DB.constants.value('game_nid') != web_export.DEFAULT_GAME_NID:
            return True
        answer = QMessageBox.question(
            None, "Export for Web",
            "This project's Game Unique Identifier is still the default, %s. Players' browsers keep "
            "each game's saves by it, so on itch.io this game would share its saves with every other "
            "game that kept the default.\n\nYou can change it under Edit > Constants. Export anyway?"
            % web_export.DEFAULT_GAME_NID)
        return answer == QMessageBox.Yes

    def _select_zip_path(self, project: Path) -> str:
        starting_path = project.parent / (project.stem + '_web.zip')
        zip_path, _ = QFileDialog.getSaveFileName(None, "Export for Web", str(starting_path), "Zip files (*.zip)")
        return zip_path

    def export(self):
        if not self._save():
            return
        project = Path(self.proj_file_manager.current_proj)
        try:
            web_export.check(project)
        except ValueError as error:
            QMessageBox.warning(None, "Cannot export project", str(error))
            return
        if not self._confirm_game_nid():
            return
        zip_path = self._select_zip_path(project)
        if not zip_path:
            return

        progress_dialog = QProgressDialog("Exporting %s for the web" % project.name, None, 0, 100)
        progress_dialog.setWindowTitle("Export for Web")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        QApplication.processEvents()

        def progress(done: float):
            # The last step, zipping, is quick
            progress_dialog.setValue(int(done * 95))
            QApplication.processEvents()

        try:
            with tempfile.TemporaryDirectory() as staging:
                web_dir = Path(staging) / 'web'
                web_export.build(project, web_dir, progress)
                web_export.package(web_dir, Path(zip_path))
        except ValueError as error:
            QMessageBox.warning(None, "Cannot export project", str(error))
            return
        finally:
            progress_dialog.close()

        QMessageBox.information(
            None, "Export for Web",
            "Exported to %s\n\nTo publish it on itch.io, set the project's Kind to HTML, upload this zip, "
            "and tick \"This file will be played in the browser\"." % zip_path)
        file_utils.startfile(str(Path(zip_path).parent))
