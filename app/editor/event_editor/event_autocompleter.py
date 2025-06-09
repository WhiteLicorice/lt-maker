from __future__ import annotations
from collections import Counter
from enum import Enum

import re
from dataclasses import dataclass
from difflib import SequenceMatcher as SM
from typing import List, Optional, Type

from PyQt5.QtCore import (QAbstractListModel, QLocale, QModelIndex, QSize, Qt,
                          pyqtSignal)
from PyQt5.QtWidgets import (QCompleter, QStyledItemDelegate,
                             QStyleOptionViewItem)
from PyQt5.QtGui import QPalette, QColor
from app import dark_theme

from app.data.database.database import DB
from app.data.resources.resources import RESOURCES
from app.editor.settings import MainSettingsController
from app.events import event_commands, event_validators
from app.events.event_version import EventVersion
from app.events.event_structs import ParseMode
from app.events.python_eventing.swscomp.swscompv1 import SWSCompilerV1
from app.utilities.typing import NID

class CompletionType(Enum):
    GENERIC = 0      # completions that are just any words that appear in document
    NORMAL = 1       # completions that are valid args
    FLAG = 2         # completions that are flags
    SPECIAL = 3      # completions that are special args (e.g. `{unit}``)

@dataclass
class CompletionToInsert():
    text: str                   # text to insert
    position: int               # location to insert at
    replace: int                # chars to delete before insertion (e.g. for autocompleting half a word)

@dataclass
class CompletionEntry():
    name: str                   # what the completion actually shows
    match_text: str             # what the completer matches against
    value: str                  # what the completer inserts
    ctype: CompletionType       # what kind of completion this is

@dataclass
class CompletionLocation():
    word_to_complete: str       # word to complete
    word_to_match: str          # word to match with. can differ from above (e.g. completing `"Eir` but only matching with `Eir`)
    index: int                  # index of the word to complete

COMPLETION_DATA_ROLE = 100

def _fuzzy_match(text: str, completion: CompletionEntry) -> float:
    start_bonus = 0.5 if completion.match_text.startswith(text) else 0
    return SM(None, text.lower(), completion.match_text).ratio() + start_bonus

class EventScriptCompleter(QCompleter):
    insertText = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = MainSettingsController()
        self.setFilterMode(Qt.MatchContains)
        self.activated[QModelIndex].connect(self.do_complete)
        self.completion_location: Optional[CompletionLocation] = None
        self.version = EventVersion.EVENT

    def _get_word_under_cursor(self, source: str, cursor_idx: int) -> str:
        right = cursor_idx
        left = right - 1
        while left > 0 and re.match(r'[a-zA-Z0-9_]', source[left]):
            left -= 1
        while right < len(source) and re.match(r'[a-zA-Z0-9_]', source[right]):
            right += 1
        return source[left:right].strip()

    def generate_generic_completions(self, source: str, cursor_idx: int) -> List[CompletionEntry]:
        """Generates generic completions from all strings in the document.
        Not used for events, since that's a restricted language without variables"""
        if self.version == EventVersion.EVENT:
            return []
        else:
            word_under_cursor = self._get_word_under_cursor(source, cursor_idx)
            return generate_generic_completions(source, word_under_cursor)

    def set_version(self, version: EventVersion):
        self.version = version

    def do_complete(self, completion_index: QModelIndex):
        completion: CompletionEntry = completion_index.data(COMPLETION_DATA_ROLE)
        self.insertText.emit([CompletionToInsert(completion.value, self.completion_location.index, len(self.completion_location.word_to_complete))])
        if not completion.value.endswith('='):
            self.popup().hide()

    def handleKeyPressEvent(self, event) -> bool:
        # If completer is up, Tab/Enter can auto-complete
        if event.key() == self.settings.get_autocomplete_button(Qt.Key_Tab):
            if self.popup().isVisible() and len(self.popup().selectedIndexes()) > 0:
                choice = self.popup().selectedIndexes()[0]
                self.do_complete(choice)
                return True  # should not enter a tab
        elif event.key() == Qt.Key_Backspace:
            self.popup().hide()
        elif event.key() == Qt.Key_Escape:
            self.popup().hide()
        return False

    def setTextToComplete(self, line: str, cursor_idx: int, level_nid: NID, source: str):
        completions = generate_completions(source, line, level_nid, self.version)
        generic_completions = self.generate_generic_completions(source, cursor_idx)
        completions += generic_completions
        if not completions:
            self.setModel(self.ESInternalModel([], self))
            return
        self.completion_location = get_arg_info(line, cursor_idx, self.version)
        if not self.completion_location:
            return
        # sort completions based on similarity
        completions = sorted(completions, key=lambda compl: _fuzzy_match(self.completion_location.word_to_match, compl), reverse=True)
        self.setModel(self.ESInternalModel(completions, self))
        self.popup().setItemDelegate(self.ESInternalDelegate(self))
        self.setCompletionPrefix(self.completion_location.word_to_match.lower())
        self.popup().setCurrentIndex(self.completionModel().index(0, 0))
        return True

    class ESInternalDelegate(QStyledItemDelegate):
        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self.settings = MainSettingsController()
            theme = dark_theme.get_theme()
            self.syntax_colors = theme.event_syntax_highlighting()
            self.python_colors = theme.python_syntax_highlighting()

        def displayText(self, value: CompletionEntry, locale: QLocale) -> str:
            return value.name

        def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
            completion: CompletionEntry = index.data(COMPLETION_DATA_ROLE)
            return QSize(len(completion.name) * 8 + 8, 20)

        def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
            super().initStyleOption(option, index)
            option.font.setFamily(self.settings.get_code_font())
            option.font.setBold(True)
            completion: CompletionEntry = index.data(COMPLETION_DATA_ROLE)

            def set_text_color(color: QColor):
                option.palette.setBrush(QPalette.ColorRole.Text, color)
                option.palette.setBrush(QPalette.ColorRole.HighlightedText, color)

            if completion.ctype == CompletionType.SPECIAL:
                set_text_color(self.syntax_colors.special_text_color)
            elif completion.ctype == CompletionType.FLAG:
                set_text_color(self.python_colors.flag)
            elif completion.ctype == CompletionType.GENERIC:
                option.font.setBold(False)

    class ESInternalModel(QAbstractListModel):
        def __init__(self, data: List[CompletionEntry], parent: EventScriptCompleter):
            super().__init__(parent)
            self._data = data

        def rowCount(self, parent=None) -> int:
            return len(self._data)

        def data(self, index: QModelIndex, role: int):
            if not index.isValid():
                return None
            # completer uses this field to match against
            elif role == Qt.ItemDataRole.EditRole:
                return self._data[index.row()].match_text.lower()
            # what the completer ultimately returns
            elif role == COMPLETION_DATA_ROLE:
                return self._data[index.row()]
            # delegate uses this to decide what to display
            elif role == Qt.ItemDataRole.DisplayRole:
                return self._data[index.row()]
            else:
                return None

def generate_completions(source: str, line: str, level_nid: NID, version: EventVersion) -> List[CompletionEntry]:
    if version == EventVersion.EVENT:
        return generate_event_completions(source, line, level_nid)
    elif version == EventVersion.PYEV1:
        return generate_pyev1_completions(line, level_nid)
    return []

def generate_event_completions(source: str, line: str, level_nid: NID) -> List[CompletionEntry]:
    as_tokens = event_commands.parse_event_line(line)
    arg = as_tokens.tokens[-1]

    def create_completion(nid, name):
        nid_or_name = nid
        if name and nid != name:
            nid_or_name = "%s (%s)" % (name, nid)
        return CompletionEntry(nid_or_name, nid_or_name, nid, CompletionType.NORMAL)

    if as_tokens.mode() == ParseMode.COMMAND:
        commands = event_validators.EventFunction().valid_entries()
        completions = [create_completion(nid, name) for name, nid in commands]
        return completions

    # Else not ParseMode.COMMAND
    command_t = event_commands.get_all_event_commands(EventVersion.EVENT).get(as_tokens.command(), None)
    # First argument is not a valid command...
    if not command_t:
        return []

    completions = []
    if as_tokens.mode() == ParseMode.ARGS:
        arg_name = get_arg_name(command_t, arg, len(as_tokens.tokens) - 2)
        arg_validator = event_validators.get(command_t.get_validator_from_keyword(arg_name))
        if arg_validator:
            valids = arg_validator(DB, RESOURCES).valid_entries(level_nid, arg)
            completions = [create_completion(nid, name) for name, nid in valids]
        if arg_validator.include_generic_completions:
            generic_completions = generate_generic_completions(source, arg)
        else:
            generic_completions = []
        flag_cmpls = []
        if arg_name in command_t.optional_keywords:
            # add flags when we're done with required
            flags = command_t().flags
            flag_key = "FLAG(%s)"
            flag_cmpls = [CompletionEntry(flag_key % flag, flag, flag, CompletionType.FLAG) for flag in flags]
        return completions + generic_completions + flag_cmpls

    elif as_tokens.mode() == ParseMode.FLAGS:
        flags = command_t().flags
        flag_key = "FLAG(%s)"
        completions = [CompletionEntry(flag_key % flag, flag, flag, CompletionType.FLAG) for flag in flags]
        return completions
    return []

def generate_pyev1_completions(line: str, level_nid: NID) -> List[CompletionEntry]:
    as_tokens = SWSCompilerV1.parse_line(line)
    if not as_tokens:
        return []
    arg = as_tokens.tokens[-1]

    def create_completion(nid, name, is_command: bool = False, ctype: CompletionType = CompletionType.NORMAL):
        nid_or_name = nid
        if name and nid != name:
            nid_or_name = "%s (%s)" % (name, nid)
        if not is_command:
            nid = '"%s"' % nid
        return CompletionEntry(nid_or_name, nid_or_name, nid, ctype)

    if as_tokens.mode() == ParseMode.COMMAND:
        commands = event_commands.get_all_event_commands(EventVersion.PYEV1).keys()
        completions = [create_completion(name, name, True) for name in commands]
        return completions

    command_t = event_commands.get_all_event_commands(EventVersion.PYEV1).get(as_tokens.command(), None)
    if not command_t:
        return []

    if as_tokens.mode() == ParseMode.ARGS:
        arg_name = get_arg_name(command_t, arg, len(as_tokens.tokens) - 2)
        arg_validator = event_validators.get(command_t.get_validator_from_keyword(arg_name))
        completions = []
        if arg_validator:
            valids = arg_validator(DB, RESOURCES).valid_entries(level_nid, arg)
            completions += [create_completion(nid, name) for name, nid in valids]
        # add positional args only if we're likely searching for them
        if not as_tokens.tokens[-1] or as_tokens.tokens[-1].isalpha():
            for kwd in command_t.optional_keywords:
                completions += [create_completion(kwd + '=', kwd + '=', True, CompletionType.SPECIAL)]
        return completions
    elif as_tokens.mode() == ParseMode.FLAGS:
        flags = command_t().flags
        flag_key = "FLAG(%s)"
        completions = [CompletionEntry(flag_key % flag, flag, flag, CompletionType.FLAG) for flag in flags]
        return completions

def generate_generic_completions(source: str, word_under_cursor: str) -> List[CompletionEntry]:
    if len(word_under_cursor) < 2:
        return []
    all_compl = source.replace('\n', ' ').replace(';', ' ').split()
    all_compl = [t for t in all_compl if re.match('^[A-Za-z_]+$', t) and len(t) > 3]
    all_compl = Counter(all_compl)
    all_compl[word_under_cursor] -= 1
    return [CompletionEntry(trim_arg_text(key), trim_arg_text(key), trim_arg_text(key), CompletionType.GENERIC) for key in all_compl.keys() if all_compl[key] > 0]

def get_arg_info(line: str, end_idx: int, version: EventVersion) -> CompletionLocation:
    """Returns the arg at the end of line, as well as its starting index in the document"""
    as_tokens = None
    if version == EventVersion.EVENT:
        as_tokens = event_commands.parse_event_line(line)
        full_arg = as_tokens.tokens[-1]
        arg_to_match = trim_arg_match(full_arg)
        arg_to_replace = trim_arg_text(full_arg)
        return CompletionLocation(arg_to_replace, arg_to_match, end_idx - len(arg_to_replace))
    elif version == EventVersion.PYEV1:
        as_tokens = SWSCompilerV1.parse_line(line)
        if not as_tokens:  # normal line, not a python eventing line
            arg_to_replace = trim_arg_match(line)
            return CompletionLocation(arg_to_replace, arg_to_replace, end_idx - len(arg_to_replace))
        full_arg = as_tokens.tokens[-1]
        arg_to_match = trim_arg_match(full_arg)
        arg_to_replace = trim_arg_text_python(full_arg)
        return CompletionLocation(arg_to_replace, arg_to_match, end_idx - len(arg_to_replace))
    else:
        raise Exception("Unknown event version")

def get_arg_name(command_t: Type[event_commands.EventCommand], arg_text: str, arg_idx: int) -> Optional[str]:
    # is this a keyword arg?
    if '=' in arg_text:
        maybe_keyword, _ = arg_text.split('=', 1)
        if command_t.get_validator_from_keyword(maybe_keyword):
            return maybe_keyword

    # not a keyword arg
    if not arg_idx < len(command_t.get_keywords()):
        return None
    return command_t.get_keyword_from_index(arg_idx)

def trim_arg_match(arg_text: str) -> str:
    return re.split('[^a-zA-Z0-9_ ]', arg_text)[-1]

def trim_arg_text(arg_text: str) -> str:
    return re.split('[^a-zA-Z0-9_ "\'\{]', arg_text)[-1]

def trim_arg_text_python(arg_text: str) -> str:
    return re.split('[^a-zA-Z0-9_ "\']', arg_text)[-1]
