from __future__ import annotations
import functools

import json
import logging
import os
from pathlib import Path
import shutil
from datetime import datetime
import traceback
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PyQt5.QtCore import QDir, Qt
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QProgressDialog, QVBoxLayout, QLabel, QDialogButtonBox, QCheckBox

from app.constants import VERSION
from app.data.database.database import DB, Database
from app.data.resources.resources import RESOURCES, Resources
from app.data.serialization.dataclass_serialization import dataclass_from_dict
from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
from app.data.validation.db_validation import DBChecker
from app.editor import timer
from app.editor.error_viewer import show_error_report
from app.extensions.message_box import show_warning_message
from app.utilities.file_manager import FileManager
from app.data.metadata import Metadata
from app.editor.file_manager.project_initializer import ProjectInitializer
from app.editor.lib.csv import csv_data_exporter, text_data_exporter
from app.editor.recent_project_dialog import choose_recent_project
from app.editor.settings import MainSettingsController
from app.extensions.custom_gui import SimpleDialog
from app.utilities import exceptions
import app.utilities.platformdirs as appdirs

if TYPE_CHECKING:
    from app.editor.main_editor import MainEditor


RESERVED_PROJECT_PATHS = ("default.ltproj", 'autosave.ltproj', 'autosave', 'default')
DEFAULT_PROJECT = "default.ltproj"

class FatalErrorDialog(SimpleDialog):
    def __init__(self, main_window_reference: MainEditor, on_accept_do_not_show_callback):
        super().__init__()
        self.setWindowTitle("Validation Errors Detected")
        self.main_window_ref = main_window_reference

        layout = QVBoxLayout()
        self.setLayout(layout)

        message_label = QLabel('Fatal errors detected in game. Please fix all errors detected.'
                               '<br><br>Error report can be viewed in the <a href="#view_errors"><span style=" text-decoration: underline; color:#7777ff;">Error Viewer</span></a>')
        message_label.linkActivated.connect(self.open_error_viewer)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)

        self.on_accept_do_not_show_callback = on_accept_do_not_show_callback
        self.do_not_show_again = QCheckBox("Don't show for several minutes")

        layout.addWidget(message_label)
        layout.addWidget(self.do_not_show_again)
        layout.addWidget(button_box)
        self.setMinimumWidth(300)

    def accept(self):
        self.on_accept_do_not_show_callback(self.do_not_show_again.isChecked())
        self.close()

    def open_error_viewer(self):
        self.main_window_ref._error_window_ref = show_error_report()
        self.close()

class ProjectFileBackend():
    def __init__(self, parent, app_state_manager):
        self.parent = parent
        self.app_state_manager = app_state_manager
        self.settings = MainSettingsController()
        self.current_proj = self.settings.get_current_project()
        self.file_manager = FileManager(self.current_proj)
        self.is_saving = False
        try:
            self.metadata: Metadata = dataclass_from_dict(Metadata, self.file_manager.load_json(Path('metadata.json')))
        except Exception:
            self.metadata = Metadata()

        self.save_progress = QProgressDialog(
            "Saving project to %s" % self.current_proj, None, 0, 100, self.parent)
        self.save_progress.setAutoClose(True)
        self.save_progress.setWindowTitle("Saving Project")
        self.save_progress.setWindowModality(Qt.WindowModal)
        self.save_progress.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.save_progress.reset()

        project_nid = DB.constants.value('game_nid').replace(' ', '_')
        autosave_path = os.path.abspath('autosave_%s.ltproj' % project_nid)
        self.autosave_progress = QProgressDialog(
            "Autosaving project to %s" % autosave_path, None, 0, 100, self.parent)
        self.autosave_progress.setAutoClose(True)
        self.autosave_progress.setWindowTitle("Autosaving Project")
        self.autosave_progress.setWindowModality(Qt.WindowModal)
        self.autosave_progress.setWindowFlag(
            Qt.WindowContextHelpButtonHint, False)
        self.autosave_progress.reset()

        timer.get_timer().autosave_timer.timeout.connect(self.autosave)

        self._do_not_show_fatal_errors = False
        timer.get_timer().autosave_timer.timeout.connect(self.refresh_do_not_show)

    def refresh_do_not_show(self):
        self._do_not_show_fatal_errors = False

    def display_fatal_errors(self):
        if self._do_not_show_fatal_errors:
            return
        def set_do_not_show_again(do_not_show_again):
            if self._do_not_show_fatal_errors:
                return
            self._do_not_show_fatal_errors = do_not_show_again
        dlg = FatalErrorDialog(self.parent, set_do_not_show_again)
        dlg.exec_()

    def maybe_save(self):
        # if not self.undo_stack.isClean():
        if True:  # For now, since undo stack is not being used
            ret = QMessageBox.warning(self.parent, "Main Editor", "The current project may have been modified.\n"
                                      "Do you want to save your changes?",
                                      QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if ret == QMessageBox.Save:
                return self.save()
            elif ret == QMessageBox.Cancel:
                return False
        return True

    def save_mutex(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # If we're currently saving, we don't want to save again! So gate operations in the save mutex!
            if not self.is_saving:
                # If we're saving the game, we want to ensure autosave doesn't show up and mess with our stuff! Stop it.
                timer.get_timer().autosave_timer.stop()
                self.is_saving = True

                # ... Then, actually save.
                result = func(self, *args, **kwargs)
                self.is_saving = False

                # ... Then start it again! Problem solved! (except this resets the timer, but close enough)
                timer.get_timer().autosave_timer.start()
                return result
        return wrapper

    @save_mutex
    def save(self, new:bool=False, as_chunks:Optional[bool]=None) -> bool:
        # make sure no errors in DB exist
        # if we make a mistake in validation,
        # we should allow the save so
        # the user can make a game
        try:
            checker = DBChecker(DB, RESOURCES)
            checker.repair()
            any_errors = checker.validate_for_errors()
            has_fatal_errors = bool(any_errors)
        except Exception as e:
            QMessageBox.warning(self.parent, "Validation warning", "Validation failed with error. Please send this message to the devs.\nYour save will continue as normal.\nException:\n" + traceback.format_exc())
            has_fatal_errors = False

        # Returns whether we successfully saved
        # check if we're editing default, if so, prompt to save as
        if new or not self.current_proj or os.path.basename(self.current_proj) == DEFAULT_PROJECT:
            if os.path.basename(self.current_proj) == DEFAULT_PROJECT:
                starting_path = appdirs.user_documents_dir()
            else:
                starting_path = Path(self.current_proj or QDir.currentPath()).parent
            fn, ok = QFileDialog.getSaveFileName(self.parent, "Save Project", str(starting_path),
                                                 "All Files (*)")
            if ok:
                # Make sure you can't save as "autosave" or "default"
                if os.path.split(fn)[-1] in RESERVED_PROJECT_PATHS:
                    QMessageBox.critical(
                        self.parent, "Save Error", "You cannot save project as <b>%s</b> or <b>autosave.ltproj</b>!\nChoose another name." % DEFAULT_PROJECT)
                    return False
                if fn.endswith('.ltproj'):
                    self.current_proj = fn
                else:
                    self.current_proj = fn + '.ltproj'
                self.settings.set_current_project(self.current_proj)
            else:
                return False
            new = True

        if new:
            if os.path.exists(self.current_proj):
                ret = QMessageBox.warning(self.parent, "Save Project", "The file already exists.\nDo you want to overwrite it?",
                                          QMessageBox.Save | QMessageBox.Cancel)
                if ret == QMessageBox.Save:
                    pass
                else:
                    return False

        # Make directory for saving if it doesn't already exist
        if not new and self.settings.get_should_make_backup_save():
            # we will copy the existing save (whichever is more recent)
            # as a backup
            self.tmp_proj = self.current_proj + '.lttmp'
            self.save_progress.setLabelText(
                "Making backup to %s" % self.tmp_proj)
            self.save_progress.setValue(1)
            if os.path.exists(self.tmp_proj):
                shutil.rmtree(self.tmp_proj)

            most_recent_path = self.current_proj
            shutil.move(most_recent_path, self.tmp_proj)
        self.save_progress.setLabelText(
            "Saving project to %s" % self.current_proj)
        self.save_progress.setValue(10)

        # Actually save project
        def display_error(section: str):
            self.save_progress.setValue(100)
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Critical)
            error_msg.setText("Editor was unable to save your project's %s. \nFree up memory in your hard drive or try saving somewhere else, \notherwise progress will be lost when the editor is closed. \nFor more detailed logs, please click View Logs in the Extra menu.\n\n" % section)
            error_msg.setWindowTitle("Serialization Error")
            error_msg.exec_()

        success = RESOURCES.save(self.current_proj, progress=self.save_progress)
        if not success:
            display_error("resources")
            return False
        self.save_progress.setValue(75)
        
        if as_chunks is None:
            as_chunks = self.settings.get_should_save_as_chunks()

        success = DB.serialize(self.current_proj, as_chunks=as_chunks)
        if not success:
            display_error("database")
            return False
        self.save_progress.setValue(85)

        # Save metadata
        self.save_metadata(self.current_proj, has_fatal_errors, as_chunks)
        self.save_progress.setValue(87)
        if not new and self.settings.get_should_make_backup_save():
            # we have fully saved the current project.
            # first, delete the .json files that don't appear in the new project
            for old_dir, dirs, files in os.walk(self.tmp_proj):
                new_dir = old_dir.replace(self.tmp_proj, self.current_proj)
                for f in files:
                    if f.endswith('.json'):
                        old_file = os.path.join(old_dir, f)
                        new_file = os.path.join(new_dir, f)
                        if not os.path.exists(new_file):
                            os.remove(old_file)
            # then replace the files in the original backup folder and rename it back
            for src_dir, dirs, files in os.walk(self.current_proj):
                dst_dir = src_dir.replace(self.current_proj, self.tmp_proj)
                for f in files:
                    src_file = os.path.join(src_dir, f)
                    dst_file = os.path.join(dst_dir, f)
                    if os.path.exists(dst_file + '.bak'):
                        os.remove(dst_file)
                    os.rename(src_file, dst_file + '.bak')
                    if os.path.exists(dst_file):
                        os.remove(dst_file)
                    os.rename(dst_file + '.bak', dst_file)
            if os.path.isdir(self.current_proj):
                shutil.rmtree(self.current_proj)
            os.rename(self.tmp_proj, self.current_proj)
        self.save_progress.setValue(100)

        self.settings.append_or_bump_project(DB.constants.value('title') or os.path.basename(self.current_proj), self.current_proj)

        if has_fatal_errors:
            self.display_fatal_errors()

        return True

    def new(self):
        if not self.maybe_save():
            return False
        project_initializer = ProjectInitializer()
        result = project_initializer.full_create_new_project()
        if result:
            _, _, path = result
            self.current_proj = path
            self.settings.set_current_project(path)
        self.load()
        return result

    def open(self) -> bool:
        if self.maybe_save():
            # Go up one directory when starting
            fn = choose_recent_project(load_only=True)
            if fn:
                if not fn.endswith('.ltproj'):
                    QMessageBox.warning(self.parent, "Incorrect directory type",
                                        "%s is not an .ltproj." % fn)
                    return False
                self.current_proj = fn
                self.settings.set_current_project(self.current_proj)
                logging.info("Opening project %s" % self.current_proj)
                self.load()
                return True
            else:
                return False
        return False

    def auto_open(self, project_path: Optional[str] = None):
        path = project_path or self.settings.get_current_project()
        logging.info("Auto Open: %s" % path)
        if path and os.path.exists(path):
            try:
                self.current_proj = path
                self.settings.set_current_project(self.current_proj)
                self.load()
                return True
            except exceptions.CustomComponentsException as e:
                logging.exception(e)
                logging.error("Failed to load project at %s due to syntax error. Likely there's a problem in your Custom Components file, located at %s. See error above." % (
                    path, RESOURCES.get_custom_components_path()))
                QMessageBox.warning(self.parent, "Load of project failed",
                                    "Failed to load project at %s due to syntax error. Likely there's a problem in your Custom Components file, located at %s. Exception:\n%s." % (path, RESOURCES.get_custom_components_path(), e))
                return False
            except Exception as e:
                logging.exception(e)
                logging.warning(
                    "Failed to load project at %s.", path)
                show_warning_message("Project load failed", "Failed to load project at %s" % path, detailed_text=str(e))
                return False
        logging.warning(
            "path %s not found. Falling back to %s" % (path, DEFAULT_PROJECT))
        QMessageBox.warning(self.parent, "Load of project failed",
                            "Failed to load project at %s - path doesn't exist" % path)
        return False

    def load(self):
        if os.path.exists(self.current_proj):
            curr_proj_path = Path(self.current_proj)
            self.file_manager = FileManager(curr_proj_path)
            try:
                self.metadata = dataclass_from_dict(Metadata, self.file_manager.load_json(Path('metadata.json')))
            except Exception:
                self.metadata = Metadata()
            RESOURCES.load(self.current_proj, CURRENT_SERIALIZATION_VERSION)
            DB.load(curr_proj_path, self.metadata.serialization_version)
            self.settings.append_or_bump_project(
                DB.constants.value('title') or os.path.basename(self.current_proj), self.current_proj)

    @save_mutex
    def autosave(self):
        project_nid = DB.constants.value('game_nid').replace(' ', '_')
        autosave_path = os.path.abspath('autosave_%s.ltproj' % project_nid)
        self.autosave_progress.setLabelText(
            "Autosaving project to %s" % autosave_path)
        autosave_dir = os.path.abspath(autosave_path)
        # Make directory for saving if it doesn't already exist
        if not os.path.isdir(autosave_dir):
            os.mkdir(autosave_dir)
        self.autosave_progress.setValue(1)

        try:
            self.parent.status_bar.showMessage(
                'Autosaving project to %s...' % autosave_dir)
        except Exception:
            pass

        # Actually save project
        logging.info("Autosaving project to %s..." % autosave_dir)
        RESOURCES.autosave(self.current_proj, autosave_dir,
                           self.autosave_progress)
        self.autosave_progress.setValue(75)
        DB.serialize(autosave_dir, as_chunks=self.settings.get_should_save_as_chunks())
        self.autosave_progress.setValue(99)

        # Save metadata
        self.save_metadata(autosave_dir, self.metadata.has_fatal_errors, self.settings.get_should_save_as_chunks())

        try:
            self.parent.status_bar.showMessage(
                'Autosave to %s complete!' % autosave_dir)
        except Exception:
            pass
        self.autosave_progress.setValue(100)

    def save_metadata(self, save_dir: Path, has_fatal_errors: bool, as_chunks: bool) -> None:
        updated_metadata: dict[str, Any] = {
            'date': str(datetime.now()),
            'engine_version': VERSION,
            # always uses the current version to save. this is only required to select the deserializer on the load side
            'serialization_version': CURRENT_SERIALIZATION_VERSION, 
            'project': DB.constants.get('game_nid').value,
            'has_fatal_errors': has_fatal_errors,
            'as_chunks': as_chunks
        }
        
        # static to serialized
        serialized_metadata = self.metadata.update(updated_metadata)
        
        metadata_loc = os.path.join(save_dir, 'metadata.json')
        with open(metadata_loc, 'w') as serialize_file:
            json.dump(serialized_metadata, serialize_file, indent=4)

    def get_unused_files(self) -> Dict[str, List[str]]:
        return RESOURCES.get_unused_files(self.current_proj)

    def clean(self, unused_files: Dict[str, List[str]]):
        RESOURCES.clean(unused_files)

    def dump_csv(self, db: Database):
        starting_path = self.current_proj or QDir.currentPath()
        fn = QFileDialog.getExistingDirectory(
            self.parent, "Choose dump location", starting_path)
        if fn:
            csv_direc = fn
            for ttype, tstr in csv_data_exporter.dump_as_csv(db, RESOURCES):
                with open(os.path.join(csv_direc, ttype + '.csv'), 'w') as f:
                    f.write(tstr)
        else:
            return False

    def dump_script(self, db: Database, single_block=True):
        starting_path = self.current_proj or QDir.currentPath()
        fn = QFileDialog.getExistingDirectory(
            self.parent, "Choose dump location", starting_path)
        if fn:
            script_direc = os.path.join(fn, 'script')
            if not os.path.exists(script_direc):
                os.mkdir(script_direc)
            else:
                shutil.rmtree(script_direc)
                os.mkdir(script_direc)
            if single_block:
                with open(os.path.join(script_direc, "script.txt"), 'w') as f:
                    for level_nid, event_dict in text_data_exporter.dump_script(db.events, db.levels).items():
                        for event_nid, event_script in event_dict.items():
                            f.write(event_script + "\n")
            else:
                for level_nid, event_dict in text_data_exporter.dump_script(db.events, db.levels).items():
                    level_direc = os.path.join(script_direc, level_nid)
                    if not os.path.exists(level_direc):
                        os.mkdir(level_direc)
                    else:
                        shutil.rmtree(level_direc)
                        os.mkdir(level_direc)
                    for event_nid, event_script in event_dict.items():
                        with open(os.path.join(level_direc, event_nid + '.txt'), 'w') as f:
                            f.write(event_script)
        else:
            return False
