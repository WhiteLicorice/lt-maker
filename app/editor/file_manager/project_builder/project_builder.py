from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path
from typing import Callable, List

from PyQt5.QtCore import QDir, QEventLoop, QProcess, Qt
from PyQt5.QtWidgets import (QApplication, QFileDialog, QMessageBox,
                             QProgressDialog)

from app.data.database.database import DB
from app.editor.file_manager.project_file_backend import DEFAULT_PROJECT, ProjectFileBackend
from app.engine import config as cf
from app.utilities import file_utils
from app.utilities.file_manager import FileManager

# Steps PyInstaller (and engine.spec) log while building the engine, with
# the progress each one marks, spaced by how far into a build it comes
ENGINE_BUILD_MILESTONES = [
    ("Analyzing base_library.zip", 3),
    ("Running Analysis", 21),
    ("Processing module hooks", 42),
    ("Looking for dynamic libraries", 43),
    ("Building PYZ", 68),
    ("Building EXE", 71),
    ("Building COLLECT", 75),
    ("Copying game files", 77),
]
ENGINE_BUILT_PROGRESS = 90

class PyInstallerRun():
    """PyInstaller running in the background under the editor's own
    interpreter, not whichever pyinstaller is first on PATH, which can
    belong to an older Python and bundle that Python's stdlib"""
    def __init__(self, args: List[str], on_line: Callable[[str], None]):
        self.lines: List[str] = []
        self.on_line = on_line
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_lines)
        self.process.start(sys.executable, ['-m', 'PyInstaller'] + args)

    def _read_lines(self):
        while self.process.canReadLine():
            line = bytes(self.process.readLine()).decode(errors='replace').rstrip()
            self.lines.append(line)
            self.on_line(line)

    def running(self) -> bool:
        return self.process.state() != QProcess.NotRunning

    def succeeded(self) -> bool:
        return self.process.error() == QProcess.UnknownError and self.process.exitCode() == 0

def wait_for(runs: List[PyInstallerRun]):
    """Keeps the editor's event loop going until every run has stopped"""
    loop = QEventLoop()
    def check_done(*args):
        if not any(run.running() for run in runs):
            loop.quit()
    for run in runs:
        run.process.finished.connect(check_done)
        run.process.errorOccurred.connect(check_done)
    if any(run.running() for run in runs):
        loop.exec_()

def icon_path(current_proj: Path, curr_plat: file_utils.Pltfm) -> Path:
    """Returns the icon path for a project. Pltfm is presently unused,
    because I'm not sure the icon best practices for other operating systems,
    but I expect we may end up using different files per OS.
    """
    project_icon_path = current_proj / 'resources' / 'system' / 'favicon.ico'
    if os.path.exists(project_icon_path):
        return project_icon_path
    return Path('favicon.ico')

class LTProjectBuilder():
    def __init__(self, proj_file_manager: ProjectFileBackend):
        self.proj_file_manager = proj_file_manager
        self.progress_dialog = None

    def validate(self, current_proj: Path) -> bool:
        if not file_utils.Pltfm.windows():
            QMessageBox.warning(None, "Build not supported on this platform",
                                "Project building currently only works on Windows. "
                                "The build tooling produces a Windows executable whose "
                                "launcher wrapper collides with the game folder on Linux/Mac.\n\n"
                                "To share your project, distribute the .ltproj alongside the "
                                "engine source, or build on a Windows machine.")
            return False
        current_proj_basename = os.path.basename(current_proj)
        if(current_proj_basename) == DEFAULT_PROJECT:
            QMessageBox.warning(None, "Cannot build default project",
                                "Cannot build with default project! Please make a new project "
                                "before attempting to build.")
            return False
        # since it's not default, force a save. if save fails, we can't build.
        if not self.proj_file_manager.save(new=False, as_chunks=False):
            QMessageBox.warning(None, "Cannot build project",
                                "Cannot build project without saving! Please save the project "
                                "before attempting to build.")
            return False
        if self.proj_file_manager.metadata.has_fatal_errors:
            QMessageBox.warning(None, "Cannot build project",
                                "Cannot build project with fatal errors! Please fix the errors "
                                "before attempting to build.")
            return False
        return True

    def _select_build_path(self, current_proj: Path) -> Path:
        starting_path = Path(current_proj or QDir.currentPath()).parent
        starting_path = Path(starting_path) / (os.path.basename(current_proj) + '_build_' + time.strftime("%Y%m%d-%H%M%S"))
        output_dir, _ = QFileDialog.getSaveFileName(None, "Choose build location", str(starting_path),
                                            "All Files (*)")
        return output_dir

    def _start_game_build(self, current_proj: Path, output_dir: Path, path_to_icon: Path) -> PyInstallerRun:
        # quirk of engine.spec
        project_path_without_extension = str(current_proj).replace(".ltproj", '')
        args = ['--distpath', str(output_dir / 'dist'), '--workpath', str(output_dir / 'build'),
                '-y', './utilities/build_tools/engine.spec',
                '--', project_path_without_extension, str(path_to_icon)]
        return PyInstallerRun(args, self._on_game_build_line)

    def _on_game_build_line(self, line: str):
        for milestone, progress in ENGINE_BUILD_MILESTONES:
            if milestone in line and progress > self.progress_dialog.value():
                self.progress_dialog.setValue(progress)
        _, info, message = line.partition(' INFO: ')
        if info:
            self.progress_dialog.setLabelText(message[:80])

    def _start_executable_wrapper_build(self, current_proj: Path, output_dir: Path, path_to_icon: Path) -> PyInstallerRun:
        project_name = current_proj.name.replace('.ltproj', '')
        dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
        work_dir = output_dir / 'build'
        os.makedirs(work_dir, exist_ok=True)
        tmp_run_exe_fname = work_dir / ('%s.py' % project_name)
        with open(dir_path / 'run_exe_base.txt') as base:
            text = base.read()
            text = text.replace('__PROJECT_NAME__', project_name)
            with open(tmp_run_exe_fname, 'w') as out:
                out.write(text)

        args = ['--onefile', '--noconsole', '--noupx',
                '--distpath', str(output_dir / 'dist'), '--workpath', str(work_dir / 'launcher'),
                '--specpath', str(work_dir), '--icon', os.path.abspath(path_to_icon),
                str(tmp_run_exe_fname)]
        return PyInstallerRun(args, lambda line: None)

    def _report_failure(self, run: PyInstallerRun):
        error = QMessageBox()
        error.setIcon(QMessageBox.Critical)
        error.setWindowTitle("Build failed")
        error.setText("Building the project failed:\n\n" + '\n'.join(run.lines[-10:]))
        error.setDetailedText('\n'.join(run.lines))
        error.exec_()

    def _preload_config(self, current_proj: Path, output_dir: Path):
        project_name = current_proj.name.replace('.ltproj', '')
        config = cf.base_config()
        config['debug'] = 0

        fman = FileManager(output_dir / 'dist' / project_name)
        cf.save_config(config, fman.get_path('saves/config.ini'))

    def build(self, current_proj: str):
        curr_proj_path: Path = Path(current_proj)
        if not self.validate(curr_proj_path):
            return

        output_dir = self._select_build_path(current_proj)
        if not output_dir:
            return
        self.progress_dialog = QProgressDialog(
                "Building project", None, 0, 100)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setWindowTitle("Building Project")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.progress_dialog.hide()
        self.progress_dialog.setValue(1)
        self.progress_dialog.show()
        QApplication.processEvents()

        curr_plat = file_utils.Pltfm.current_platform()
        icon = icon_path(Path(current_proj), curr_plat)
        # The launcher is small and independent, so it builds alongside the game
        runs = [self._start_game_build(curr_proj_path, Path(output_dir), icon),
                self._start_executable_wrapper_build(curr_proj_path, Path(output_dir), icon)]
        wait_for(runs)
        for run in runs:
            if not run.succeeded():
                self.progress_dialog.close()
                self._report_failure(run)
                self.proj_file_manager.save()
                return
        self.progress_dialog.setValue(ENGINE_BUILT_PROGRESS)
        self._preload_config(curr_proj_path, Path(output_dir))
        shutil.rmtree(output_dir + "/build")
        self.progress_dialog.setValue(100)
        
        # just save again to restore state
        # and leave project data seemingly untouched after auto-unchunking
        # for git users who can see diffs after building
        self.proj_file_manager.save()

        # finally, for ease of use, open the folder for the user
        file_utils.startfile(f"{output_dir}/dist")