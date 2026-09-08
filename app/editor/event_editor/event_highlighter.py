from __future__ import annotations
from dataclasses import dataclass

import logging
from typing import List

from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from app import dark_theme
from app.data.database.database import DB
from app.data.resources.resources import RESOURCES
from app.events import event_commands, event_validators

@dataclass
class Rule():
    pattern: QRegularExpression
    _format: QTextCharFormat

@dataclass
class LineToFormat():
    start: int
    length: int
    _format: QTextCharFormat

class EventSyntaxRuleHighlighter():
    def __init__(self, window) -> None:
        self.window = window
        theme = dark_theme.get_theme()
        syntax_colors = theme.event_syntax_highlighting()
        function_match = QRegularExpression("^[^;]*")
        function_format = self.create_text_format(syntax_colors.func_color, font_weight=QFont.Bold)

        comment_match = QRegularExpression("#[^\n]*")
        comment_format = self.create_text_format(syntax_colors.comment_color, italic=True)

        self.func_rule = Rule(function_match, function_format)
        self.comment_rule = Rule(comment_match, comment_format)

        self.lint_format = QTextCharFormat()
        self.lint_format.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
        self.lint_format.setUnderlineColor(syntax_colors.error_underline_color)
        self.text_format = self.create_text_format(syntax_colors.text_color)
        self.special_text_format = self.create_text_format(syntax_colors.special_text_color)

    def create_text_format(self, color: QColor, font_weight=None, italic=False):
        text_format = QTextCharFormat()
        text_format.setForeground(color)
        if font_weight:
            text_format.setFontWeight(font_weight)
        text_format.setFontItalic(italic)
        return text_format

    def match_line(self, line: str) -> List[LineToFormat]:
        format_lines: List[LineToFormat] = []

        match_iterator = self.func_rule.pattern.globalMatch(line)
        while match_iterator.hasNext():
            match = match_iterator.next()
            format_lines.append(LineToFormat(match.capturedStart(), match.capturedLength(), self.func_rule._format))

        as_tokens = event_commands.get_command_arguments(line)
        # speak formatting
        command_type = event_commands.determine_command_type(as_tokens[0].string.strip())
        if command_type == event_commands.Speak:
            if len(as_tokens) >= 3:
                dialog_token = as_tokens[2]
                format_lines.append(LineToFormat(dialog_token.index, len(dialog_token.string), self.text_format))
                for idx, char in enumerate(dialog_token.string):
                    if char in '|':
                        format_lines.append(LineToFormat(dialog_token.index + idx, 1, self.special_text_format))

        # error checking
        # error checking happens before brace formatting so that
        # brace formatting can overwrite the error checking
        # because if the user is using braces, they probably know what they
        # are doing (or at least they *should* know what they are doing)
        broken_args = self.validate_tokens(line)
        if broken_args == 'all':
            for token in as_tokens:
                format_lines.append(LineToFormat(token.index, len(token.string), self.lint_format))
        else:
            for idx in broken_args:
                format_lines.append(LineToFormat(as_tokens[idx].index, len(as_tokens[idx].string), self.lint_format))

        # brace formatting
        brace_mode = 0
        special_start = 0
        for idx, char in enumerate(line):
            if char == '{':
                if brace_mode == 0:
                    special_start = idx
                brace_mode += 1
            if char == '}':
                if brace_mode > 0:
                    format_lines.append(LineToFormat(special_start, idx - special_start + 1, self.special_text_format))
                    brace_mode -= 1

        # Comment rule goes last because it must have the highest precedence -- it overwrites everything else
        match_iterator = self.comment_rule.pattern.globalMatch(line)
        while match_iterator.hasNext():
            match = match_iterator.next()
            format_lines.append(LineToFormat(match.capturedStart(), match.capturedLength(), self.comment_rule._format))

        return format_lines

    def validate_tokens(self, line: str) -> str | List[int]:
        try:
            command, error_loc = event_commands.parse_text_to_command(line, strict=True)
            if command:
                parameters, flags = event_commands.parse(command)
                for keyword in command.keywords:
                    if keyword not in parameters:
                        return 'all'
                broken_args = []
                for keyword, value in parameters.items():
                    # if empty and optional keyword, don't need to highlight
                    if not value and keyword in command.optional_keywords:
                        continue
                    validator = command.get_validator_from_keyword(keyword)
                    level = DB.levels.get(self.window.current.level_nid if self.window.current else None)
                    text = event_validators.validate(validator, value, level, DB, RESOURCES)
                    if text is None:
                        broken_args.append(command.get_index_from_keyword(keyword) + 1)
                return broken_args
            elif error_loc:
                return [error_loc + 1]  # Integer that points to the first idx that is broken
            else:
                return [0]  # First arg is broken
        except Exception as e:
            logging.error("Error while validating %s %s", line, e)
            return 'all'


class EventHighlighter(QSyntaxHighlighter):
    def __init__(self, parent, window):
        super().__init__(parent)
        self.window = window
        self.event_syntax_formatter = EventSyntaxRuleHighlighter(self.window)

    def highlightBlock(self, text: str):
        # PyQt aborts the entire process (SIGABRT, no dialog, no chance to save)
        # if an exception escapes a reimplemented virtual like this one.
        # Syntax highlighting is cosmetic -- never let it take the editor down.
        try:
            to_format = self.event_syntax_formatter.match_line(text)
        except Exception:
            logging.exception("Failed to syntax highlight line %s", text)
            return
        for piece_to_format in to_format:
            if piece_to_format.length == 0:
                piece_to_format.length = 1
            self.setFormat(piece_to_format.start, piece_to_format.length, piece_to_format._format)
