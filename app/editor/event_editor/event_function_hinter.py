from __future__ import annotations

from functools import lru_cache
from typing import Protocol, Type
from app.editor.event_editor.event_autocompleter import get_arg_name
from app.editor.settings.main_settings_controller import MainSettingsController


from app.editor.settings.preference_definitions import Preference
from app.events import event_commands, event_validators
from app.events.event_version import EventVersion
from app.events.event_structs import ParseMode
from app.events.python_eventing.swscomp.swscompv1 import SWSCompilerV1

class IFunctionHinter(Protocol):
    @staticmethod
    def generate_hint_for_line(line: str) -> str: pass

class EventScriptFunctionHinter():
    @staticmethod
    @lru_cache(16)
    def _generate_hint_for_command(command: Type[event_commands.EventCommand], param: str) -> str:
        command = command()
        args = []
        args.append(command.nid)
        curr_keyword = None
        for idx, keyword in enumerate(command.get_keywords()):
            if command.keyword_types:
                keyword_type = command.keyword_types[idx]
                hint_str = "%s=%s" % (keyword, keyword_type)
                if keyword == param:
                    hint_str = "<b>%s</b>" % hint_str
                    curr_keyword = keyword_type
                args.append(hint_str)
            else:
                hint_str = keyword
                if keyword == param:
                    hint_str = "<b>%s</b>" % hint_str
                    curr_keyword = keyword
                args.append(hint_str)
        if command.flags:
            hint_str = 'FLAGS'
            if param == 'FLAGS':
                hint_str = "<b>%s</b>" % hint_str
                curr_keyword = 'FLAGS'
            args.append(hint_str)
        hint_cmd_str = ';\u200b'.join(args)
        hint_cmd_str = '<div class="command_text">' + hint_cmd_str + '</div>'

        hint_desc = ''
        if curr_keyword == 'FLAGS':
            hint_desc = 'Must be one of: %s' % ', '.join(command.flags)
        else:
            validator = event_validators.get(curr_keyword)
            if validator:
                hint_desc = '<div class="desc_text">' + validator().desc + '</div>'

        settings = MainSettingsController()
        style = """
            <style>
                .command_text {font-family: '%s', %s, monospace;}
                .desc_text {font-family: Arial, Helvetica, sans-serif;}
            </style>
        """ % (settings.get_preference(Preference.CODE_FONT), settings.get_preference(Preference.CODE_FONT))


        hint_text = style + hint_cmd_str + '<hr>' + hint_desc
        return hint_text

    @staticmethod
    def generate_hint_for_line(line: str):
        if not line:
            return None
        as_tokens = event_commands.parse_event_line(line)
        if as_tokens.mode() in (ParseMode.COMMAND, ParseMode.EOL):
            return None

        arg = as_tokens.tokens[-1]
        command = as_tokens.command()
        command_t = event_commands.get_all_event_commands(EventVersion.EVENT).get(command, None)
        if not command_t:
            return None
        if as_tokens.mode() == ParseMode.FLAGS:
            return EventScriptFunctionHinter._generate_hint_for_command(command_t, 'FLAGS')
        else:
            param = get_arg_name(command_t, arg, len(as_tokens.tokens) - 2)
            return EventScriptFunctionHinter._generate_hint_for_command(command_t, param or 'FLAGS')

class PythonFunctionHinter():
    @staticmethod
    @lru_cache(16)
    def _generate_hint_for_command(command: Type[event_commands.EventCommand], param: str) -> str:
        command = command()
        args = []
        args.append(command.nid)
        curr_keyword = None
        for idx, keyword in enumerate(command.get_keywords()):
            if command.keyword_types:
                keyword_type = command.keyword_types[idx]
                hint_str = "%s=%s" % (keyword, keyword_type)
                if keyword == param:
                    hint_str = "<b>%s</b>" % hint_str
                    curr_keyword = keyword_type
                args.append(hint_str)
            else:
                hint_str = keyword
                if keyword == param:
                    hint_str = "<b>%s</b>" % hint_str
                    curr_keyword = keyword
                args.append(hint_str)
        if command.flags:
            hint_str = 'FLAGS'
            if param == 'FLAGS':
                hint_str = "<b>%s</b>" % hint_str
                curr_keyword = 'FLAGS'
            args.append(hint_str)
        hint_cmd_str = ' \u200b'.join(args)
        hint_cmd_str = '<div class="command_text">' + hint_cmd_str + '</div>'

        hint_desc = ''
        if curr_keyword == 'FLAGS':
            hint_desc = 'Must be one of: %s' % ', '.join(command.flags)
        else:
            validator = event_validators.get(curr_keyword)
            if validator:
                hint_desc = '<div class="desc_text">' + validator().desc + '</div>'

        settings = MainSettingsController()
        style = """
            <style>
                .command_text {font-family: '%s', %s, monospace;}
                .desc_text {font-family: Arial, Helvetica, sans-serif;}
            </style>
        """ % (settings.get_preference(Preference.CODE_FONT), settings.get_preference(Preference.CODE_FONT))


        hint_text = style + hint_cmd_str + '<hr>' + hint_desc
        return hint_text

    @staticmethod
    def generate_hint_for_line(line: str):
        if not line:
            return None
        as_tokens = SWSCompilerV1.parse_line(line)
        if not as_tokens:
            return None
        if as_tokens.mode() in (ParseMode.COMMAND, ParseMode.EOL):
            return None

        arg = as_tokens.tokens[-1]
        command = as_tokens.command()
        command_t = event_commands.get_all_event_commands(EventVersion.PYEV1).get(command, None)
        if not command_t:
            return None
        if as_tokens.mode() == ParseMode.FLAGS:
            return PythonFunctionHinter._generate_hint_for_command(command_t, 'FLAGS')
        else:
            param = get_arg_name(command_t, arg, len(as_tokens.tokens) - 2)
            return PythonFunctionHinter._generate_hint_for_command(command_t, param or 'FLAGS')
