from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import List

from PyQt5.QtCore import QDir, Qt
from PyQt5.QtWidgets import (QApplication, QFileDialog, QMessageBox,
                             QProgressDialog)

from app.data.database.database import DB
from app.editor.file_manager.project_file_backend import DEFAULT_PROJECT, ProjectFileBackend
from app.engine import config as cf
from app.utilities import file_utils
from app.utilities.file_manager import FileManager

def execute(cmd: str):
    args = shlex.split(cmd)
    popen = subprocess.Popen(args, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

PROGRESS_SENTINEL = "__PROGRESS_SENTINEL_STR__"

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

    def _build_game(self, current_proj: Path, dist_cmd: str, work_cmd: str, path_to_icon: Path):
        kwargs: List[str] = []
        kwargs.append(dist_cmd)
        kwargs.append(work_cmd)
        spec_cmd = "-y ./utilities/build_tools/engine.spec"
        kwargs.append(spec_cmd)
        kwargstr = ' '.join(kwargs)
        # quirk of engine.spec
        project_path_without_extension = str(current_proj).replace(".ltproj", '')

        engine_build_cmd = f'pyinstaller {kwargstr} -- "{project_path_without_extension}" "{PROGRESS_SENTINEL}" "{path_to_icon}"'
        for line in execute(engine_build_cmd):
            if PROGRESS_SENTINEL in line:
                progress = int(line.replace(PROGRESS_SENTINEL, ""))
                self.progress_dialog.setValue(progress)

    def _build_executable_wrapper(self, current_proj: Path, dist_cmd: str, work_cmd: str, path_to_icon: Path):
        project_name = current_proj.name.replace('.ltproj', '')
        dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
        tmp_run_exe_fname = '%s.py' % project_name
        with open(dir_path / 'run_exe_base.txt') as base:
            text = base.read()
            text = text.replace('__PROJECT_NAME__', project_name)
            with open(tmp_run_exe_fname, 'w') as out:
                out.write(text)

        exe_kwargs: List[str] = []
        exe_kwargs.append(dist_cmd)
        exe_kwargs.append(work_cmd)
        icon_cmd = '--icon="%s"' % path_to_icon
        exe_kwargs.append(icon_cmd)

        exe_kwargstr = ' '.join(exe_kwargs)
        executable_build_cmd = f'pyinstaller --onefile --noconsole {exe_kwargstr} "{tmp_run_exe_fname}"'
        subprocess.check_call(executable_build_cmd, shell=True)
        os.remove(tmp_run_exe_fname)
        os.remove(project_name + '.spec')

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
        dist_cmd = '--distpath "%s/dist"' % output_dir
        work_cmd = '--workpath "%s/build"' % output_dir
        icon = icon_path(Path(current_proj), curr_plat)
        self._build_game(curr_proj_path, dist_cmd, work_cmd, icon)
        self.progress_dialog.setValue(80)
        self._build_executable_wrapper(curr_proj_path, dist_cmd, work_cmd, icon)
        self._preload_config(curr_proj_path, Path(output_dir))
        shutil.rmtree(output_dir + "/build")
        self.progress_dialog.setValue(100)
        
        # just save again to restore state
        # and leave project data seemingly untouched after auto-unchunking
        # for git users who can see diffs after building
        self.proj_file_manager.save()

        # finally, for ease of use, open the folder for the user
        file_utils.startfile(f"{output_dir}/dist")