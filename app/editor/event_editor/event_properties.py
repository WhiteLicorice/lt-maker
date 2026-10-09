from __future__ import annotations
from typing import Optional

from enum import Enum
import functools
import logging
import math
import os
import re

from PyQt5.QtCore import QRect, QSize, QSortFilterProxyModel, Qt, pyqtSignal
from PyQt5.QtGui import (QFont, QFontMetrics, QIcon, QPainter, QPalette,
                         QTextCursor)
from PyQt5.QtWidgets import (QAbstractItemView, QAction, QApplication,
                             QCheckBox, QCompleter, QDialog, QFrame,
                             QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                             QLineEdit, QListView, QMenu, QMessageBox,
                             QPlainTextEdit, QPushButton, QSizePolicy,
                             QSpinBox, QSplitter, QStyle, QStyledItemDelegate,
                             QTextEdit, QToolBar, QVBoxLayout, QWidget)
from app.editor.event_editor.commands_dialog import ShowCommandsDialog
from app.editor.event_editor.event_function_hinter import EventScriptFunctionHinter, PythonFunctionHinter
from app.editor.event_editor.event_text_editor import EventTextEditor

import app.editor.game_actions.game_actions as GAME_ACTIONS
from app import dark_theme
from app.data.database.database import DB
from app.data.database.levels import LevelPrefab
from app.data.resources.resources import RESOURCES
from app.editor import table_model, timer
from app.editor.base_database_gui import CollectionModel
from app.editor.custom_widgets import TilemapBox
from app.editor.event_editor import event_autocompleter, find_and_replace
from app.editor.event_editor.event_highlighter import EventHighlighter
from app.editor.event_editor.py_syntax import PythonHighlighter
from app.editor.lib.components.validated_line_edit import \
    NoParentheticalLineEdit
from app.editor.map_view import SimpleMapView
from app.editor.settings import MainSettingsController
from app.editor.settings.preference_definitions import Preference
from app.events import event_commands, event_validators
from app.events.event_prefab import EventPrefab
from app.events.event_version import EventVersion
from app.events.mock_event import IfStatementStrategy
from app.events.regions import RegionType
from app.events.triggers import ALL_TRIGGERS
from app.extensions.custom_gui import (ComboBox, PropertyBox, PropertyCheckBox,
                                       QHLine, TableView)
from app.extensions.markdown2 import Markdown
from app.utilities import str_utils

from app.editor.code_line_edit import CodeLineEdit

class EventCollection(QWidget):
    def __init__(self, deletion_criteria, collection_model, parent,
                 button_text="Create %s", view_type=TableView):
        super().__init__(parent)
        self.window = parent
        self.database_editor = self.window.window
        self.main_editor = self.database_editor.window
        current_level_nid = self.main_editor.app_state_manager.state.selected_level
        self.current_level = DB.levels.get(current_level_nid)

        self._data = self.window._data
        self.title = self.window.title

        self.settings = MainSettingsController()

        self.display = None
        grid = QGridLayout()
        self.setLayout(grid)

        self.level_filter_box = PropertyBox("Level Filter", ComboBox, self)
        self.level_filter_box.edit.addItem("All")
        self.level_filter_box.edit.addItem("Global")
        self.level_filter_box.edit.addItems(DB.levels.keys())
        self.level_filter_box.edit.currentIndexChanged.connect(self.filter_changed)

        self.event_name_filter_box = PropertyBox("Filter by name", QLineEdit, self)
        self.event_name_filter_box.edit.textChanged.connect(self.filter_changed)

        self.model = collection_model(self._data, self)
        self.name_filtered_model = table_model.ProxyModel()
        self.name_filtered_model.setSourceModel(self.model)
        self.level_filtered_model = table_model.ProxyModel()
        self.level_filtered_model.setSourceModel(self.name_filtered_model)
        self.view: TableView = view_type(self)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setModel(self.level_filtered_model)
        # self.view.setModel(self.model)
        self.view.setSortingEnabled(True)
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        # sort is stored as (col, dir)
        # see leaveEvent
        sort = self.settings.component_controller.get_sort(self.__class__.__name__)
        if sort:
            self.view.sortByColumn(sort[0], sort[1])
        # self.view.clicked.connect(self.on_single_click)
        # Remove edit on double click
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # self.view.currentChanged = self.on_item_changed
        self.view.selectionModel().selectionChanged.connect(self.on_item_changed)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        self.button = QPushButton(button_text % self.title)
        self.button.clicked.connect(self.create_new_event)

        self.create_actions()
        self.create_toolbar()
        grid.addWidget(self.toolbar, 0, 0, Qt.AlignLeft)
        grid.addWidget(self.event_name_filter_box, 0, 1, Qt.AlignRight)
        grid.addWidget(self.level_filter_box, 0, 2, Qt.AlignRight)
        grid.addWidget(self.view, 1, 0, 1, 3)
        grid.addWidget(self.button, 2, 0, 1, 3)

        # Reopen on the event that was open when the editor last closed
        self.last_event: Optional[EventPrefab] = None
        last = self.settings.component_controller.get_property(self.__class__.__name__, 'last_event')
        if last and self.settings.get_preference(Preference.EVENT_REOPEN_LAST):
            project, event_nid, level_filter = last
            if project == self.settings.get_current_project():
                self.last_event = DB.events.get_from_nid(event_nid)
        if self.last_event:
            if level_filter != "All":
                level_filter = self.last_event.level_nid or "Global"
            self.level_filter_box.edit.setValue(level_filter)
        elif self.current_level:
            self.level_filter_box.edit.setValue(self.current_level.nid)
        else:
            self.level_filter_box.edit.setValue("All")

    def create_actions(self):
        theme = dark_theme.get_theme()
        icon_folder = theme.icon_dir()

        self.new_action = QAction(QIcon(f"{icon_folder}/file-plus.png"), "New Event", triggered=self.new)
        self.new_action.setShortcut("Ctrl+N")
        self.duplicate_action = QAction(QIcon(f"{icon_folder}/duplicate.png"), "Duplicate Event", triggered=self.duplicate)
        self.duplicate_action.setShortcut("Ctrl+D")
        self.delete_action = QAction(QIcon(f"{icon_folder}/x-circle.png"), "Delete Event", triggered=self.delete)
        self.delete_action.setShortcut("Del")
        self._set_enabled(False)

    def _set_enabled(self, val: bool):
        if self.display:
            self.display.setEnabled(val)
        self.delete_action.setEnabled(val)
        self.duplicate_action.setEnabled(val)

    def create_toolbar(self):
        self.toolbar = QToolBar(self)
        self.toolbar.addAction(self.new_action)
        self.toolbar.addAction(self.duplicate_action)
        self.toolbar.addAction(self.delete_action)

    def delete(self):
        self.window.right_frame.name_done_editing()  # Necessary for handling deletion right after you change the name if you don't click off
        current_index = self.view.currentIndex()
        model_index = self.name_filtered_model.mapToSource(self.level_filtered_model.mapToSource(current_index))
        row = current_index.row()
        self.model.delete(model_index)

        if self.level_filtered_model.rowCount() > 0:
            if row >= self.level_filtered_model.rowCount():
                new_index = self.level_filtered_model.index(row - 1, 0)
            else:
                new_index = self.level_filtered_model.index(row, 0)
            self.view.setCurrentIndex(new_index)
            self.set_current_index(new_index)
        else:
            self._set_enabled(False)

    def new(self):
        """
        # Identical to regular create new event
        # since it will just be sorted anyway
        """
        self.create_new_event()

    def duplicate(self):
        current_index = self.view.currentIndex()
        model_index = self.name_filtered_model.mapToSource(self.level_filtered_model.mapToSource(current_index))
        new_index = self.model.duplicate(model_index)
        if new_index:
            name_index = self.name_filtered_model.mapFromSource(new_index)
            new_proxy_index = self.level_filtered_model.mapFromSource(name_index)

            self.view.setCurrentIndex(new_proxy_index)
            self.set_current_index(new_proxy_index)

    def _get_level_nid(self) -> str:
        if self.level_filter_box.edit.currentText() == 'All':
            level_nid = None
        elif self.level_filter_box.edit.currentText() == 'Global':
            level_nid = None
        else:
            level_nid = self.level_filter_box.edit.currentText()
        return level_nid

    def create_new_event(self):
        level_nid = self._get_level_nid()

        self.model.layoutAboutToBeChanged.emit()
        output = self.model.create_new(level_nid)
        self.model.layoutChanged.emit()
        if not output:
            return

        last_index = self.model.index(self.model.rowCount() - 1, 0)

        proxy_last_index = self.level_filtered_model.mapFromSource(self.name_filtered_model.mapFromSource(last_index))
        self.view.setCurrentIndex(proxy_last_index)
        self.set_current_index(proxy_last_index)

        self._set_enabled(True)

    def on_item_changed(self, curr, prev):
        if self._data:
            if curr.indexes():
                index = curr.indexes()[0]
                correct_index = self.name_filtered_model.mapToSource(self.level_filtered_model.mapToSource(index))
                row = correct_index.row()
            else:
                return
            # new_data = curr.internalPointer()  # Internal pointer is way too powerful
            # if not new_data:
            new_data = self._data[row]
            if self.display:
                self.display.set_current(new_data)
                self.display.setEnabled(True)

    def set_current_index(self, index):
        correct_index = self.name_filtered_model.mapToSource(self.level_filtered_model.mapToSource(index))
        row = correct_index.row()
        new_data = self._data[row]
        if self.display:
            self.display.set_current(new_data)
            self.display.setEnabled(True)

    def set_display(self, disp):
        self.display = disp
        if self.last_event:
            source_index = self.model.index(self._data.index(self.last_event.nid), 0)
            index = self.level_filtered_model.mapFromSource(self.name_filtered_model.mapFromSource(source_index))
            self.view.setCurrentIndex(index)
            self.view.scrollTo(index, QAbstractItemView.PositionAtCenter)
        else:
            first_index = self.level_filtered_model.index(0, 0)
            self.view.setCurrentIndex(first_index)

        self.display.setEnabled(False)
        if self.level_filtered_model.rowCount() > 0:
            self.display.setEnabled(True)

    def filter_changed(self, idx):
        level = self.level_filter_box.edit.currentText()
        name = self.event_name_filter_box.edit.text()

        if level == 'All':
            level = ""
        if not name:
            name = ""

        if not name:
            self.name_filtered_model.setFilterFixedString("")
        else:
            self.name_filtered_model.setFilterRegularExpression('(?i){}'.format(name))

        self.view.selectionModel().selectionChanged.disconnect(self.on_item_changed)
        self.level_filtered_model.setFilterKeyColumn(1)
        if not level:
            self.level_filtered_model.setFilterFixedString("")
        else:
            search = "^" + re.escape(level) + "$"
            self.level_filtered_model.setFilterRegularExpression(search)
        self.view.selectionModel().selectionChanged.connect(self.on_item_changed)
        # Determine if we should reselect something
        if level and self.display:
            # current_index = self.view.currentIndex()
            # real_index = self.level_filtered_model.mapToSource(current_index)
            # obj = self._data[real_index.row()]
            obj = self.display.current
            if obj and ((level != "Global" and level != obj.level_nid) or (level == "Global" and obj.level_nid)):
                # Change selection only if we need to!
                first_index = self.level_filtered_model.index(0, 0)
                self.view.setCurrentIndex(first_index)
                self.set_current_index(first_index)
        elif self.display and not self.display.current:
            # Change selection only if we need to!
            first_index = self.level_filtered_model.index(0, 0)
            self.view.setCurrentIndex(first_index)
            self.set_current_index(first_index)

        self.update_list()

        if self.level_filtered_model.rowCount() > 0:
            self._set_enabled(True)
        else:
            self._set_enabled(False)


    def update_list(self):
        # self.model.layoutChanged.emit()
        # self.level_filtered_model.invalidate()
        self.level_filtered_model.layoutChanged.emit()

    def leaveEvent(self, event) -> None:
        sort_dir = self.view.horizontalHeader().sortIndicatorOrder()
        sort_col = self.view.horizontalHeader().sortIndicatorSection()
        self.settings.component_controller.set_sort(self.__class__.__name__, (sort_col, sort_dir))
        return super().leaveEvent(event)

    def hideEvent(self, event) -> None:
        # Saved on close rather than on selection, so that renaming
        # the open event doesn't leave a stale nid behind
        current = self.display.current if self.display else None
        project = self.settings.get_current_project()
        if current and current.nid and project:
            self.settings.component_controller.set_property(
                self.__class__.__name__, 'last_event',
                [project, current.nid, self.level_filter_box.edit.currentText()])
        return super().hideEvent(event)

class EventProperties(QWidget):
    def __init__(self, parent, current=None):
        super().__init__(parent)
        self.window = parent
        self._data = self.window._data

        self.settings = MainSettingsController()
        self.current = current
        self.version = None

        self.text_box = EventTextEditor(self)
        self.text_box.textChanged.connect(self.text_changed)
        self.find_and_replace_window = find_and_replace.Find(self)

        self.find_action = QAction("Find...", self, shortcut="Ctrl+F", triggered=self.show_find_and_replace)
        self.replace_action = QAction("Replace...", self, shortcut="Ctrl+H", triggered=self.show_find_and_replace)
        self.replace_all_action = QAction("Replace all...", self, shortcut="Ctrl+Shift+H", triggered=self.show_find_and_replace)
        self.addAction(self.find_action)
        self.addAction(self.replace_action)
        self.addAction(self.replace_all_action)

        # Text setup
        self.cursor = self.text_box.textCursor()
        self.code_font = QFont()
        self.code_font.setFamily(self.settings.get_preference(Preference.CODE_FONT))
        self.code_font.setFixedPitch(True)
        self.code_font.setPointSize(10)
        self.text_box.setFont(self.code_font)
        self.highlighter = EventHighlighter(self.text_box.document(), self)

        main_section = QVBoxLayout()
        self.setLayout(main_section)
        main_section.addWidget(self.text_box)

        left_frame = self.window.left_frame
        self.level_filter_box = left_frame.level_filter_box
        grid = left_frame.layout()

        self.name_box = PropertyBox("Name", NoParentheticalLineEdit, self)
        self.name_box.edit.textChanged.connect(self.name_changed)
        self.name_box.edit.editingFinished.connect(self.name_done_editing)

        self.trigger_box = PropertyBox("Trigger", ComboBox, self)
        items = self.get_trigger_items("Global")
        self.trigger_box.edit.addItems(items)
        self.trigger_box.edit.activated.connect(self.trigger_changed)

        self.level_nid_box = PropertyBox("Level", ComboBox, self)
        self.level_nid_box.edit.addItem("Global")
        self.level_nid_box.edit.addItems(DB.levels.keys())
        self.level_nid_box.edit.currentIndexChanged.connect(self.level_nid_changed)

        self.condition_box = PropertyBox("Condition", CodeLineEdit, self)
        self.condition_box.edit.setPlaceholderText("Condition required for event to fire")
        self.condition_box.edit.textChanged.connect(lambda: self.condition_changed(self.condition_box.edit.toPlainText()))

        self.only_once_box = PropertyCheckBox("Trigger only once?", QCheckBox, self)
        self.only_once_box.edit.stateChanged.connect(self.only_once_changed)

        self.priority_box = PropertyBox("Priority", QSpinBox, self)
        self.priority_box.edit.setRange(0, 99)
        self.priority_box.edit.setAlignment(Qt.AlignRight)
        self.priority_box.setToolTip("Higher Priority happens first")
        self.priority_box.edit.valueChanged.connect(self.priority_changed)

        grid.addWidget(QHLine(), 3, 0, 1, 3)
        grid.addWidget(self.name_box, 4, 0, 1, 3)
        grid.addWidget(self.level_nid_box, 5, 0, 1, 3)
        trigger_layout = QHBoxLayout()
        self.trigger_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        trigger_layout.addWidget(self.trigger_box)
        trigger_layout.addWidget(self.priority_box, alignment=Qt.AlignRight)
        grid.addLayout(trigger_layout, 6, 0, 1, 3)
        grid.addWidget(self.condition_box, 7, 0, 1, 3)
        grid.addWidget(self.only_once_box, 8, 0, 1, 3, Qt.AlignLeft)

        bottom_section = QHBoxLayout()
        main_section.addLayout(bottom_section)

        self.show_map_dialog = None
        self.show_map_button = QPushButton("Show Map")
        self.show_map_button.clicked.connect(self.show_map)
        bottom_section.addWidget(self.show_map_button)

        self.show_commands_dialog = None
        self.show_commands_button = QPushButton("Show Commands")
        self.show_commands_button.clicked.connect(self.show_commands)
        bottom_section.addWidget(self.show_commands_button)

        self.test_event_button = QPushButton("Test Event")
        test_menu = QMenu("Test", self)
        test_menu.addAction(QAction("with If Statements always True", self, triggered=functools.partial(self.test_event, IfStatementStrategy.ALWAYS_TRUE)))
        test_menu.addAction(QAction("with If Statements always False", self, triggered=functools.partial(self.test_event, IfStatementStrategy.ALWAYS_FALSE)))
        self.test_event_button.setMenu(test_menu)
        bottom_section.addWidget(self.test_event_button)

        self.test_python_event_button = QPushButton("Test Python Event")
        self.test_python_event_button.clicked.connect(self.test_python_event)
        bottom_section.addWidget(self.test_python_event_button)
        self.set_test_event_button_visible()

    def setEnabled(self, val):
        super().setEnabled(val)
        # Need to also set these, since they are considered
        # part of the left frame by Qt
        self.name_box.setEnabled(val)
        self.level_nid_box.setEnabled(val)
        self.trigger_box.setEnabled(val)
        self.condition_box.setEnabled(val)
        self.only_once_box.setEnabled(val)

    def get_trigger_items(self, level_nid: str) -> list:
        all_items = ["None"]
        all_custom_triggers = set()
        for level in DB.levels:
            if level_nid == 'Global' or level_nid == level.nid:
                for region in level.regions:
                    if region.region_type == RegionType.EVENT:
                        all_custom_triggers.add(region.sub_nid)
        all_items += list(all_custom_triggers)
        all_items += [trigger.nid for trigger in ALL_TRIGGERS]
        return all_items

    def insert_text(self, text):
        self.text_box.insertPlainText(text)

    def insert_text_with_newline(self, text):
        self.cursor.movePosition(QTextCursor.NextBlock)
        self.text_box.insertPlainText(text)

    def show_map(self):
        # Modeless dialog
        if not self.show_map_dialog:
            current_level: Optional[LevelPrefab] = DB.levels.get(self.current.level_nid)
            self.show_map_dialog = ShowMapDialog(current_level, self)
        self.show_map_dialog.setAttribute(Qt.WA_ShowWithoutActivating, True)
        # self.show_map_dialog.setWindowFlags(self.show_map_dialog.windowFlags() | Qt.WindowDoesNotAcceptFocus)
        self.show_map_dialog.show()
        self.show_map_dialog.raise_()
        # self.show_map_dialog.activateWindow()

    def close_map(self):
        if self.show_map_dialog:
            self.show_map_dialog.done(0)
            self.show_map_dialog = None

    def show_commands(self):
        # Modeless dialog
        # if not self.show_commands_dialog:
        self.show_commands_dialog = ShowCommandsDialog(self, self.current.version() == EventVersion.PYEV1)
        # self.show_commands_dialog.setAttribute(Qt.WA_ShowWithoutActivating, True)
        # self.show_commands_dialog.setWindowFlags(self.show_commands_dialog.windowFlags() | Qt.WindowDoesNotAcceptFocus)
        self.show_commands_dialog.show()
        self.show_commands_dialog.raise_()
        # self.show_commands_dialog.activateWindow()

    def close_commands(self):
        if self.show_commands_dialog:
            self.show_commands_dialog.done(0)
            self.show_commands_dialog = None

    def show_find_and_replace(self):
        if not self.find_and_replace_window:
            self.find_and_replace_window = find_and_replace.Find(self)
        self.find_and_replace_window.show()
        self.find_and_replace_window.raise_()

    def close_find_and_replace(self):
        if self.find_and_replace_window:
            self.find_and_replace_window.done(0)
            self.find_and_replace_window = None

    def test_event(self, strategy):
        if self.current:
            # If not debug_point_line_number default to 0 (the start)
            command_pointer = (self.text_box.debug_point_line_number or 1) - 1
            timer.get_timer().stop()
            GAME_ACTIONS.test_event(self.current, command_pointer, strategy)
            timer.get_timer().start()

    def test_python_event(self):
        if self.current:
            command_pointer = 0
            timer.get_timer().stop()
            GAME_ACTIONS.test_event(self.current, command_pointer)
            timer.get_timer().start()

    def name_changed(self, text):
        self.current.name = text
        self.window.update_list()

    def name_done_editing(self):
        # Check validity of nid!
        other_nids = [d.nid for d in self._data.values() if d is not self.current]
        other_names = [d.name for d in self._data.values() if d is not self.current and d.level_nid == self.current.level_nid]
        if self.current.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning', 'Event ID %s already in use' % self.current.nid)
            self.current.name = str_utils.get_next_name(self.current.name, other_names)
            self.name_box.edit.setText(self.current.name)
        self._data.update_nid(self.current, self.current.nid, set_nid=False)
        self.window.update_list()

    def trigger_changed(self, idx):
        cur_val = self.trigger_box.edit.currentText()
        if cur_val == 'None':
            self.current.trigger = None
        elif cur_val in [trigger.nid for trigger in ALL_TRIGGERS]:
            self.current.trigger = cur_val
        else:
            self.current.trigger = cur_val
        self.window.update_list()

    def level_nid_changed(self, idx):
        if idx == 0:
            self.current.level_nid = None
            self.name_done_editing()
            if self.level_filter_box.edit.currentText() != "All":
                self.level_filter_box.edit.setValue("Global")
        else:
            self.current.level_nid = DB.levels[idx - 1].nid
            self.name_done_editing()
            if self.level_filter_box.edit.currentText() != "All":
                self.level_filter_box.edit.setValue(self.current.level_nid)

        # Update trigger box to match current level
        self.trigger_box.edit.clear()
        if idx == 0:
            self.trigger_box.edit.addItems(self.get_trigger_items("Global"))
        else:
            self.trigger_box.edit.addItems(self.get_trigger_items(self.current.level_nid))
        self.trigger_box.edit.setValue(self.current.trigger)
        self.window.update_list()

    def condition_changed(self, text):
        self.current.condition = text

    def only_once_changed(self, state):
        self.current.only_once = bool(state)

    def priority_changed(self, value):
        self.current.priority = value

    def text_changed(self):
        self.current.source = self.text_box.document().toRawText()
        # reset cached event info
        DB.events.inspector.clear_cache(self.current.nid)
        self.set_editor_language(self.current.version())
        self.set_test_event_button_visible()

    def set_test_event_button_visible(self):
        if self.current and self.current.version() != EventVersion.EVENT:
            self.test_event_button.hide()
            self.test_python_event_button.show()
        else:
            self.test_event_button.show()
            self.test_python_event_button.hide()

    def set_editor_language(self, version: EventVersion):
        if version == self.version:
            return
        self.version = version
        self.text_box.set_completer_version(self.version)
        if version != EventVersion.EVENT:
            self.highlighter = PythonHighlighter(self.text_box.document())
            self.text_box.set_function_hinter(PythonFunctionHinter)
        else:
            self.highlighter = EventHighlighter(self.text_box.document(), self)
            self.text_box.set_function_hinter(EventScriptFunctionHinter)

    def set_current(self, current: EventPrefab):
        self.current = current
        self.name_box.edit.setText(current.name)
        # self.trigger_box.edit.clear()
        if current.level_nid is not None:
            self.level_nid_box.edit.setValue(current.level_nid)
            # self.trigger_box.edit.addItems(self.get_trigger_items(current.level_nid))
        else:
            self.level_nid_box.edit.setValue('Global')
            # self.trigger_box.edit.addItems(self.get_trigger_items("Global"))
        if current.trigger:
            self.trigger_box.edit.setValue(current.trigger)
        else:
            self.trigger_box.edit.setValue("None")
        self.condition_box.edit.setPlainText(current.condition)
        self.only_once_box.edit.setChecked(bool(current.only_once))
        self.priority_box.edit.setValue(current.priority)

        if self.current.version() == EventVersion.EVENT:
            if not self.current.source:
                self.current.source = '\n'.join([str(cmd) for cmd in self.current.commands])
            self.text_box.setPlainText(self.current.source)
            self.set_editor_language(self.current.version())
        else:
            self.text_box.setPlainText(self.current.source)
            self.set_editor_language(self.current.version())
        self.set_test_event_button_visible()
        # Reset red dot
        self.text_box.debug_point_line_number = None

    def hideEvent(self, event):
        self.close_map()
        self.close_commands()
        self.close_find_and_replace()

class ShowMapDialog(QDialog):
    def __init__(self, current_level: Optional[LevelPrefab], parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowTitle("Level Map View")
        self.window = parent
        self.current_level = current_level

        self.map_selector = TilemapBox(self)
        self.map_selector.edit.activated.connect(self.select_current)
        if self.current_level and self.current_level.tilemap:
            self.map_selector.edit.setCurrentIndex(self.map_selector.edit.findText(self.current_level.tilemap))
        else:
            self.map_selector.edit.setCurrentIndex(0)

        self.map_view = SimpleMapView(self)
        self.map_view.position_clicked.connect(self.position_clicked)
        self.map_view.position_moved.connect(self.position_moved)
        self.map_view.position_right_clicked_float.connect(self.position_right_clicked_float)
        if self.current_level:
            self.map_view.set_current_level(self.current_level)
        else:
            tilemap_nid = self.map_selector.edit.currentText()
            tilemap = RESOURCES.tilemaps.get(tilemap_nid)
            if tilemap:
                self.map_view.set_current_map(tilemap)

        self.position_edit = QLineEdit(self)
        self.position_edit.setAlignment(Qt.AlignRight)
        self.position_edit.setReadOnly(True)

        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.map_selector)
        layout.addWidget(self.map_view)
        layout.addWidget(self.position_edit, Qt.AlignRight)

        timer.get_timer().tick_elapsed.connect(self.map_view.update_view)

    def select_current(self):
        tilemap_nid = self.map_selector.edit.currentText()
        if self.current_level and tilemap_nid == self.current_level.tilemap:
            self.map_view.set_current_level(self.current_level)
        else:
            tilemap = RESOURCES.tilemaps.get(tilemap_nid)
            if tilemap:
                self.map_view.set_current_map(tilemap)

    def position_clicked(self, x, y):
        self.window.insert_text("%d,%d" % (x, y))

    def position_right_clicked_float(self, x: float, y: float):
        self.window.insert_text("%0.1f,%0.1f" % (x, y))

    def position_moved(self, x, y):
        if x >= 0 and y >= 0:
            if not self.current_level:
                self.position_edit.setText("%d,%d" % (x, y))
                return
            unit_name = None
            for unit in self.current_level.units:
                if unit.starting_position and unit.starting_position[0] == x and unit.starting_position[1] == y:
                    unit_name = unit.nid
                    break
            if unit_name:
                self.position_edit.setText("%s: %d,%d" % (unit_name, x, y))
            else:
                self.position_edit.setText("%d,%d" % (x, y))
        else:
            self.position_edit.setText("")

    def update(self):
        self.map_view.update_view()

    def set_current(self, current: Optional[LevelPrefab]):
        self.current_level = current
        if self.current_level:
            self.map_view.set_current_level(self.current_level)
            tilemap = RESOURCES.tilemaps.get(self.current_level.tilemap)
            if tilemap:
                self.map_view.set_current_map(tilemap)

    def closeEvent(self, event):
        self.window.show_map_dialog = None
