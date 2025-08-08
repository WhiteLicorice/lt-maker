from dataclasses import dataclass
from enum import Enum
import re
from typing import Callable, List, Dict, Tuple

from app.constants import WINHEIGHT, WINWIDTH
from app.engine import config as cf
from app.events import event_portrait, screen_positions
from app.engine import engine, image_mods, text_funcs
from app.engine.base_surf import create_base_surf
from app.engine.fonts import FONT
from app.engine.game_state import game
from app.engine.graphics.ingame_ui.ui_funcs import calc_align
from app.engine.graphics.text.tagged_text import TaggedText
from app.engine.graphics.text.text_renderer import (
    MATCH_CAPTURE_TAG_RE,
    render_text,
    text_width,
)
from app.engine.graphics.text.styled_text_parser import parse_styled_text
from app.engine.sound import get_sound_thread
from app.engine.sprites import SPRITES
from app.events.speak_style import SpeakStyle
from app.utilities import utils
from app.utilities.enums import Alignments, HAlignment

from app.utilities.str_utils import SHIFT_NEWLINE

MATCH_DIALOG_COMMAND_RE = re.compile("(\{[^\{]*?\})")


def process_dialog_shorthand(text: str) -> str:
    if not text:
        return text
    # special char: this is a unicode single-line break.
    # basically equivalent to {br}
    # the first char shouldn't be one of these
    if text[0] == SHIFT_NEWLINE:
        text = text[1:]
    text = text.replace(SHIFT_NEWLINE, "{sub_break}")  # sub break to distinguish it
    text = text.replace("\n", "{br}")
    text = text.replace("|", "{w}{br}")
    text = text.replace("{semicolon}", ";")
    text = text.replace("{lt}", "<").replace("{gt}", ">")
    text = text.replace("{lcb}", "{").replace("{rcb}", "}")
    return text


class DialogState(Enum):
    PROCESS = "process"  # Normal display of characters one at a time
    TRANSITION_IN = "transition_in"  # Dialog is fading in
    PAUSE = "pause"  # Pause processing for some amount of time
    PAUSE_BEFORE_WAIT = "pause_before_wait"  # Pause processing before we wait for user input, so that user input cannot skip too quickly
    WAIT = "wait"  # Wait for user input
    DONE = "done"  # Dialog has nothing else to do and can be removed
    NEW_LINE = "new_line"  # Pause while we move to a new line
    COMMAND_PAUSE = "command_pause"  # Pause caused by a {p} command


class Dialog:
    solo_flag = False
    cursor_offset = [0] * 20 + [1] * 2 + [2] * 8 + [1] * 2
    transition_speed = utils.frames2ms(10)
    pause_before_wait_time = utils.frames2ms(9)
    pause_time = utils.frames2ms(3)
    attempt_split: bool = True  # Whether we attempt to split big chunks across multiple lines

    @dataclass
    class TextIndex:
        start: int
        stop: int

        def __iter__(self):
            return iter(self.to_tuple())

        def to_tuple(self):
            return (self.start, self.stop)

    def __init__(self,
                 text,
                 portrait=None,
                 background=None,
                 position=None,
                 width=None,
                 speaker=None,
                 style_nid=None,
                 autosize=False,
                 speed: float = 1.0,
                 font_color="black",
                 font_type="convo",
                 num_lines=2,
                 draw_cursor=True,
                 message_tail="message_bg_tail",
                 transparency=0.05,
                 name_tag_bg="name_tag",
                 boop_sound=None,
                 flags=None):
        self.cursor = SPRITES.get("waiting_cursor")
        flags = flags or set()

        self.plain_text = text
        self.portrait = portrait
        self.speaker = speaker
        self.style_nid = style_nid
        self.font_type = font_type
        self.font_color = font_color or "black"
        self.autosize = autosize
        self.speed = speed if speed is not None else 1.0
        self.starting_speed = self.speed
        self.boop_sound = boop_sound
        self.num_lines = num_lines
        self.draw_cursor_flag = draw_cursor
        self.font = FONT[self.font_type]
        if "{sub_break}" in self.plain_text:
            self.attempt_split = False

        self._state = DialogState.TRANSITION_IN

        self.no_wait = False

        # A "plain_text" string consists of text, commands ("{}"), and tags ("<>").
        # This text is immediately broken down into individual characters (including the tags) except
        # for the commands present (they are left intact).
        # These "text_commands" are then parsed a single element at a time during update
        # based on the drawing speed of the text box and added to "text_indices".
        # This is needed to ensure that text commands are performed at the correct time.
        self.text_commands = self.format_text(self.plain_text)

        # The plain text is also parsed into TaggedText during initialization.
        # Commands are discarded and tags are parsed into the fields of the TaggedText.
        self.tagged_text = self.parse_plain_text(self.plain_text)
        # During update, "text_commands" is parsed and generates "text_indices".
        # These "text_indices" are basically the starting and stopping indexes of substrings
        # within TaggedText that should render on each line of a text box during dalog.
        # It will be used during draw state to slice out the corresponding tagged text substring to render.
        # This also allows correct handling for discarding whitespace characters that happens during update.
        self.text_indices: List[self.TextIndex] = []
        # This caches tagged texts so we can reuse a TaggedText object when drawing
        self.tagged_text_cache: Dict[Tuple[int, int], TaggedText] = {}

        # Size
        if width:
            self.width = width
            if self.width % 8:
                self.width += 8 - self.width % 8
            self.text_width = max(8, self.width - 16)
            self.determine_height()
        elif self.portrait or self.autosize:
            self.determine_size()
        else:
            self.text_width, self.text_height = (WINWIDTH - 24, self.num_lines * 16)
            self.width, self.height = self.text_width + 16, self.text_height + 16

        # Position
        if position:
            if isinstance(position, Alignments):
                pos_x, pos_y = calc_align((self.width, self.height), position)
            else:
                pos_x = position[0]
                pos_y = position[1]
        elif self.portrait:
            # If very big, just hard set to 4 pixels from the left
            if self.width >= WINWIDTH - 8:
                pos_x = 4
            else:
                desired_center = self.determine_desired_center(self.portrait)
                pos_x = utils.clamp(desired_center - self.width // 2, 8,
                                    WINWIDTH - 8 - self.width)
                if pos_x % 8 != 0:
                    pos_x += 4
                if pos_x == 0:
                    pos_x = 4
            pos_y = (WINHEIGHT - self.height -
                     event_portrait.EventPortrait.main_portrait_coords[3] - 4)
        else:
            pos_x = 4
            pos_y = WINHEIGHT - self.height - 4
        self.position = pos_x, pos_y

        self.background = None
        self.tail = None
        self.dialog_transparency = transparency

        if background and background not in ("None", "clear"):
            self.background = self.make_background(background)
        else:
            self.background = engine.create_surface((self.width, self.height), True)
        if message_tail and message_tail != "None":
            self.tail = SPRITES.get(message_tail)

        self.name_tag_surf = create_base_surf(64, 16, name_tag_bg)

        # For drawing
        self.cursor_offset_index = 0
        self.text_index = 0
        self.total_num_updates = 0
        self.y_offset = 0  # How much to move lines (for when a new line is spawned)

        self.should_move_mouth = "no_talk" not in flags
        self.should_speak_sound = "no_sound" not in flags

        # For state transitions
        self.transition_progress = 0
        self.last_update = engine.get_time()

        self.hold = "hold" in flags

        # For sound
        self.last_sound_update = 0

        if "no_popup" in flags:
            self.last_update = engine.get_time() - 10000

    @classmethod
    def from_style(cls, style: SpeakStyle, text, portrait=None, width=None):
        style_as_dict = style.as_dict()
        if width:
            style_as_dict["width"] = width
        self = cls(text, portrait=portrait, autosize=False, **style_as_dict)
        return self

    @property
    def state(self) -> DialogState:
        return self._state

    @state.setter
    def state(self, value: DialogState):
        self._state = value

    def reformat(self):
        """Call this if you change font type or font color"""
        # reparse and clear cache
        self.tagged_text = self.parse_plain_text(self.plain_text)
        self.tagged_text_cache: Dict[Tuple[int, int], TaggedText] = {}

    def format_text(self, text):
        text = process_dialog_shorthand(text)
        if text.endswith("{no_wait}"):
            text = text[:-len("{no_wait}")]
            self.no_wait = True
        elif not text.endswith("{w}"):
            text += "{w}"
        processed_text: List[str] = []
        # obligatory regex explanation: turns "A line.{w} With some <red>text</>."
        # into "A line.{w} With some text."
        text_without_tags = re.sub(MATCH_CAPTURE_TAG_RE, "", text)
        # obligatory regex explanation: turns "A line.{w} With some <red>text</>."
        # into ["A line.", "{w}", " With some ", "<red>", "text", "</>", "."]
        # and then decomposes the non-command/tag elements into individual chars.
        text_split_by_commands: List[str] = re.split(MATCH_DIALOG_COMMAND_RE,
                                                     text_without_tags)
        for block in text_split_by_commands:
            if block.startswith("{") and block.endswith("}"):  # command (e.g. "{br}")
                processed_text.append(block)
            else:  # normal char str (e.g. "hello")
                processed_text += list(block)
        return processed_text

    def parse_plain_text(self, plain_text):
        text = process_dialog_shorthand(plain_text)
        # obligatory regex explanation:
        # turns plain text line "A line.{w}With some <red>text</>."
        # into display text line "A line.With some <red>text</>."
        display_text = re.sub(MATCH_DIALOG_COMMAND_RE, "", text)
        # parse display text line into tagged text
        tagged_text = parse_styled_text(display_text, self.font_type, self.font_color)
        return tagged_text

    def determine_desired_center(self, portrait):
        x = portrait.position[0] + portrait.get_width() // 2
        return screen_positions.get_desired_center(x)

    def determine_width(self):
        width = 0
        current_line = ""
        preceded_by_wait: bool = False
        waiting_cursor = False
        for command in self.text_commands:
            if command in ("{br}", "{break}", "{clear}", "{sub_break}"):
                if not preceded_by_wait or not self.attempt_split:
                    # Force it to be only one line
                    split_lines = self.get_lines_from_block(current_line, 1)
                else:
                    split_lines = self.get_lines_from_block(current_line)
                current_width = text_funcs.get_max_width(self.font_type,
                                                         split_lines)
                width = max(width, current_width)
                if len(split_lines) == 1:
                    waiting_cursor = True
                current_line = ""
                preceded_by_wait = False
            elif command in ("{w}", "{wait}"):
                preceded_by_wait = True
            elif command.startswith("{"):
                pass
            else:
                current_line += command
        if current_line:
            if self.attempt_split:
                split_lines = self.get_lines_from_block(current_line)
            else:
                split_lines = self.get_lines_from_block(current_line, 1)
            current_width = text_funcs.get_max_width(self.font_type, split_lines)
            width = max(width, current_width)
            if len(split_lines) == 1:
                waiting_cursor = True
        if waiting_cursor:
            if len(split_lines) == 1:
                width += utils.clamp(current_width - width + 16, 0, 16)
        return width

    def determine_height(self):
        self.text_height = self.font.height * self.num_lines
        self.text_height = max(self.text_height, 16)
        self.height = self.text_height + 16

    def determine_size(self):
        self.text_width = self.determine_width()
        self.text_width = utils.clamp(self.text_width, 48, WINWIDTH - 32)
        self.width = self.text_width + 24 - self.text_width % 8
        if self.width <= WINWIDTH - 16:
            self.width += 8
        self.determine_height()

    def make_background(self, background):
        surf = create_base_surf(self.width, self.height, background)
        return surf

    def get_lines_from_block(self, block, force_lines=None):
        if force_lines:
            num_lines = force_lines
        else:
            num_lines = self.num_lines
            if len(block) <= 24:
                num_lines = 1
        lines = text_funcs.split(self.font_type, block, num_lines, WINWIDTH - 16)
        return lines

    def _increment_text_indices(self):
        self.text_indices[-1].stop += 1  # increment the end of text index

    def _add_text_indices(self, whitespace: bool):
        if self.text_indices:
            self.text_indices.append(
                self.TextIndex(self.text_indices[-1].stop, self.text_indices[-1].stop))
            if whitespace:
                self.text_indices[-1].start += 1
                self.text_indices[-1].stop += 1
        else:
            self.text_indices.append(self.TextIndex(0, 0))

    def _next_line(self, whitespace=False):
        """handle state in preparation to transition to next dialog line

        Args:
            whitespace (bool, optional): whitespace is used to handle the case where
            a line gets separated into two by the size of the textbox and the extra
            space between the text lines gets discarded. Defaults to False.
        """
        # Don't do this for the first line
        if len(self.text_indices) > self.num_lines - 1:
            self.state = DialogState.NEW_LINE
            self.y_offset = 16
        else:
            self.state = DialogState.PROCESS
        self._add_text_indices(whitespace)

    def _done_processing(self):
        return self.text_index >= len(self.text_commands)

    def _next_char(self, sound=True):
        if self._done_processing():
            self.pause_before_wait()
            return

        if self.portrait:
            self.portrait.stop_talking()  # We will turn this back on if we reach a spoken character

        command = self.text_commands[self.text_index]
        if command in ("{br}", "{break}", "{sub_break}"):
            self._next_line()
        elif command == "{w}" or command == "{wait}":
            self.pause_before_wait()
        elif command == "{clear}":
            last_index = self.text_indices[-1].stop
            self.text_indices.clear()
            self.text_indices.append(self.TextIndex(last_index, last_index))
        elif command == "{p}":
            self.command_pause()
        elif command == "{tgm}":
            self.should_move_mouth = not self.should_move_mouth
        elif command == "{tgs}":
            self.should_speak_sound = not self.should_speak_sound
        elif command == "{max_speed}":
            self.speed = 0
        elif command == "{starting_speed}":
            self.speed = self.starting_speed
        elif re.fullmatch(r"\{speed:(\d+(?:\.\d+)?)\}", command):
            val = float(command[7:-1])  # Slice out the number part directly
            self.speed = int(val) if val.is_integer() else val
        elif command == " ":  # Check to see if we should move to next line
            next_word = self._get_next_word(self.text_index)
            start, stop = self.text_indices[-1]
            stop += len(next_word) + 1
            next_width = self.tagged_text[start:stop].width()
            if next_width > self.text_width:
                # move to next line and discard ' '
                self._next_line(True)
            else:
                self._increment_text_indices()
                if self.should_move_mouth and self.portrait:
                    self.portrait.start_talking()
                if sound:
                    self.play_talk_boop(self.boop_sound)
        elif command in (".", ",", ";", "!", "?"):
            self._increment_text_indices()
            self.pause()
        else:
            self._increment_text_indices()
            if self.should_move_mouth and self.portrait:
                self.portrait.start_talking()
            if sound:
                self.play_talk_boop(self.boop_sound)
        self.text_index += 1

    def _get_next_word(self, text_index):
        word = ""
        for letter in self.text_commands[self.text_index + 1:]:
            if letter == " ":
                break
            elif len(letter) > 1:  # Command
                if letter.startswith("{"):
                    break
                elif letter.startswith("<"):
                    # continue
                    word += letter
            else:
                word += letter
        return word

    def is_complete(self) -> bool:
        """
        Should no longer be drawn
        """
        return self.state == DialogState.DONE and not self.hold

    def is_done(self) -> bool:
        """
        Can move onto processing other commands
        """
        return self.state == DialogState.DONE

    def is_done_or_wait(self) -> bool:
        return self.state in (DialogState.DONE, DialogState.WAIT)

    def is_paused(self) -> bool:
        """
        Waiting for the event to finish processing it's {p} command
        """
        return self.state == DialogState.COMMAND_PAUSE

    def pause(self):
        if self.portrait:
            self.portrait.stop_talking()
        self.state = DialogState.PAUSE
        self.last_update = engine.get_time()

    def pause_before_wait(self):
        if self.portrait:
            self.portrait.stop_talking()
        self.state = DialogState.PAUSE_BEFORE_WAIT
        self.last_update = engine.get_time()

    def command_pause(self):
        if self.portrait:
            self.portrait.stop_talking()
        self.state = DialogState.COMMAND_PAUSE

    def command_unpause(self):
        if self.state == DialogState.COMMAND_PAUSE:
            self.state = DialogState.PROCESS

    def start_processing(self):
        if self.state == DialogState.TRANSITION_IN:
            self.state = DialogState.PROCESS
            self._next_line()

    def hurry_up(self):
        if self.state == DialogState.PROCESS:
            while self.state == DialogState.PROCESS:
                self._next_char(sound=False)
                # Skip pauses because we want maximum velocity of speech
                if self.state == DialogState.PAUSE:
                    self.state = DialogState.PROCESS
        elif self.state == DialogState.WAIT:
            if self._done_processing():
                self.state = DialogState.DONE
            else:
                self.state = DialogState.PROCESS

    def play_talk_boop(self, boop=None):
        if (cf.SETTINGS["talk_boop"]
                and engine.get_true_time() - self.last_sound_update > 32
                and self.should_speak_sound):
            self.last_sound_update = engine.get_true_time()
            if boop:
                get_sound_thread().play_sfx(boop)

    def update(self):
        current_time = engine.get_time()

        if self.state == DialogState.TRANSITION_IN:
            perc = (current_time - self.last_update) / self.transition_speed
            self.transition_progress = utils.clamp(perc, 0, 1)
            if self.transition_progress == 1:
                self._next_line()

        elif self.state == DialogState.PROCESS:
            if (cf.SETTINGS["text_speed"] * self.speed) > 0:
                num_updates = engine.get_delta() / (float(cf.SETTINGS["text_speed"]) *
                                                    self.speed)
                self.total_num_updates += num_updates
                while self.total_num_updates >= 1 and self.state == DialogState.PROCESS:
                    self.total_num_updates -= 1
                    self._next_char(sound=self.total_num_updates < 2)
                    if self.state != DialogState.PROCESS:
                        self.total_num_updates = 0
            else:
                while (self.state == DialogState.PROCESS
                       and (cf.SETTINGS["text_speed"] * self.speed) == 0):
                    self._next_char(sound=False)
                    # Skip regular pauses because we want MAXIMUM VELOCITY of characters
                    if self.state == DialogState.PAUSE:
                        self.state = DialogState.PROCESS
                self.play_talk_boop(self.boop_sound)

        elif self.state == DialogState.PAUSE_BEFORE_WAIT:
            if current_time - self.last_update > self.pause_before_wait_time:
                if self.no_wait:
                    self.state = DialogState.DONE
                else:
                    self.state = DialogState.WAIT

        elif self.state == DialogState.PAUSE:  # Regular pause for periods
            if current_time - self.last_update > self.pause_time:
                self.state = DialogState.PROCESS

        elif self.state == DialogState.NEW_LINE:
            # Update y_offset
            self.y_offset = max(0, self.y_offset - 2)
            if self.y_offset == 0:
                self.state = DialogState.PROCESS

        self.cursor_offset_index = (self.cursor_offset_index + 1) % len(
            self.cursor_offset)
        return True

    def warp_speed(self):
        """
        # Process the whole dialog and ignore all non-done states
        # We just want to get to the end
        # Essentially a simplified version of update()
        """
        self.start_processing()
        while self.state != DialogState.DONE:
            if self.state == DialogState.PROCESS:
                while self.state == DialogState.PROCESS:
                    self._next_char(sound=False)
                    # Skip pauses because we want MAXIMUM VELOCITY of characters
                    if self.state in (DialogState.PAUSE, DialogState.COMMAND_PAUSE):
                        self.state = DialogState.PROCESS

            elif self.state == DialogState.PAUSE_BEFORE_WAIT:
                self.state = DialogState.WAIT

            elif self.state == DialogState.WAIT:
                if self._done_processing():
                    self.state = DialogState.DONE
                else:
                    self.state = DialogState.PROCESS

            elif self.state in (DialogState.PAUSE, DialogState.COMMAND_PAUSE):
                self.state = DialogState.PROCESS

            elif self.state == DialogState.NEW_LINE:
                self.y_offset = 0
                self.state = DialogState.PROCESS
        return True

    def draw_text(self, surf):
        end_x_pos, end_y_pos = 0, 0
        text_surf = engine.create_surface((self.text_width, self.text_height),
                                          transparent=True)

        # update state of tagged_text
        self.tagged_text.update_effects()

        # Draw line that's disappearing
        if self.y_offset and len(self.text_indices) > self.num_lines:
            x_pos = 0
            y_pos = -16 + self.y_offset
            start, stop = self.text_indices[-self.num_lines - 1]
            # if it's not cached already at this point it's probably never going to be
            if (start, stop) in self.tagged_text_cache:
                tagged_text = self.tagged_text_cache[(start, stop)]
            else:
                tagged_text = self.tagged_text[start:stop]
            tagged_text.draw(text_surf, (x_pos, y_pos))

        display_indices = self.text_indices[-self.num_lines:]
        for idx, indices in enumerate(display_indices):
            x_pos = 0
            y_pos = 16 * idx
            if len(self.text_indices) > self.num_lines:
                y_set = y_pos + self.y_offset
            else:
                y_set = y_pos
            start, stop = indices
            # check cache
            if (start, stop) in self.tagged_text_cache:
                tagged_text = self.tagged_text_cache[(start, stop)]
            else:
                tagged_text = self.tagged_text[start:stop]
                tagged_text.set_caching_if_recommended()
                self.tagged_text_cache[(start, stop)] = tagged_text
            tagged_text.draw(text_surf, (x_pos, y_set))
            x_pos += tagged_text.width()

            end_x_pos = self.position[0] + 8 + x_pos
            end_y_pos = self.position[1] + 8 + y_pos

        surf.blit(text_surf, (self.position[0] + 8, self.position[1] + 8))
        return end_x_pos, end_y_pos

    def draw_tail(self, surf, portrait: event_portrait.EventPortrait):
        portrait_x = portrait.position[0] + portrait.get_width() // 2
        portrait_y = portrait.position[1] + portrait.get_height() // 2
        mirror_x = portrait_x < WINWIDTH // 2
        mirror_y = self.position[1] > portrait_y
        if mirror_x:
            tail_surf = engine.flip_horiz(self.tail)
        else:
            tail_surf = self.tail
        if mirror_y:
            tail_surf = engine.flip_vert(tail_surf)
            y_pos = self.position[1] - tail_surf.get_height() + 2
        else:
            y_pos = self.position[1] + self.background.get_height() - 2
        x_pos = portrait_x + 20 if mirror_x else portrait_x - 36
        # If we wouldn't actually be on the dialog box
        if x_pos > self.background.get_width() + self.position[0] - 24:
            x_pos = self.position[0] + self.background.get_width() - 24
        elif x_pos < self.position[0] + 8:
            x_pos = self.position[0] + 8

        tail_surf = image_mods.make_translucent(tail_surf, self.dialog_transparency)
        surf.blit(tail_surf, (x_pos, y_pos))

    def draw_nametag(self, surf, name):
        if self.position[1] < 10:  # if it would get cut off
            y_pos = self.position[1] + self.height - 6
        else:
            y_pos = self.position[1] - 10
        x_pos = self.position[0] - 4
        if x_pos < 0:
            x_pos = self.position[0] + 16
        name_tag_surf = self.name_tag_surf.copy()
        self.font.blit_center(name, name_tag_surf,
                              (name_tag_surf.get_width() // 2,
                               name_tag_surf.get_height() // 2 - self.font.height // 2),
                              self.font_color)
        surf.blit(name_tag_surf, (x_pos, y_pos))
        return surf

    def draw(self, surf: engine.Surface) -> engine.Surface:
        if self.background:
            if self.state == DialogState.TRANSITION_IN:
                # bg = image_mods.resize(self.background, (1, .5 + self.transition_progress/2.))
                new_width = max(
                    1,
                    self.background.get_width() - 10 +
                    int(10 * self.transition_progress))
                new_height = max(
                    1,
                    self.background.get_height() - 10 +
                    int(10 * self.transition_progress))
                bg = engine.transform_scale(self.background, (new_width, new_height))
                bg = image_mods.make_translucent(
                    bg, self.dialog_transparency + (0.75 - self.dialog_transparency) *
                    (1 - self.transition_progress))
                surf.blit(bg, (self.position[0],
                               self.position[1] + self.height - bg.get_height()))
            else:
                bg = image_mods.make_translucent(self.background,
                                                 self.dialog_transparency)
                surf.blit(bg, self.position)

        if self.state != DialogState.TRANSITION_IN:
            # Draw message tail
            if self.portrait and self.tail:
                self.draw_tail(surf, self.portrait)
            # Draw nametag
            if not self.portrait and self.speaker and self.speaker != "Narrator":
                self.draw_nametag(surf, self.speaker)
            # Draw text
            end_pos = self.draw_text(surf)

            if self.state == DialogState.WAIT and self.draw_cursor_flag:
                cursor_pos = (
                    4 + end_pos[0],
                    6 + end_pos[1] + self.cursor_offset[self.cursor_offset_index],
                )
                surf.blit(self.cursor, cursor_pos)

        return surf


class DynamicDialogWrapper:

    def __init__(self,
                 text_func: Callable[[], str],
                 portrait=None,
                 background=None,
                 position=None,
                 width=None,
                 speaker=None,
                 style_nid=None,
                 autosize=False,
                 speed: float = 1.0,
                 font_color="black",
                 font_type="convo",
                 num_lines=2,
                 draw_cursor=True,
                 message_tail="message_bg_tail",
                 transparency: float = 0.05,
                 name_tag_bg="name_tag",
                 flags=None) -> None:
        # eval trick
        self.resolve_text_func: Callable[[], str] = text_func
        self.resolved_text = process_dialog_shorthand(self.resolve_text_func()).replace(
            "{w}", "")
        # dialog props
        self.portrait = portrait
        self.background = background
        self.position = position
        self.width = width
        self.speaker = speaker
        self.style_nid = style_nid
        self.autosize = autosize
        self.speed = speed
        self.font_color = font_color
        self.font_type = font_type
        self.num_lines = num_lines
        self.draw_cursor = draw_cursor
        self.message_tail = message_tail
        self.transparency = transparency
        self.name_tag_bg = name_tag_bg
        self.flags = flags

        self.dialog = Dialog(self.resolved_text, portrait, background, position, width,
                             speaker, style_nid, autosize, speed, font_color, font_type,
                             num_lines, draw_cursor, message_tail, transparency,
                             name_tag_bg, flags)

    def update(self):
        new_text = process_dialog_shorthand(self.resolve_text_func()).replace("{w}", "")
        if new_text != self.resolved_text:
            self.resolved_text = new_text
            self.dialog = Dialog(self.resolved_text, self.portrait, self.background,
                                 self.position, self.width, self.speaker,
                                 self.style_nid, self.autosize, self.speed,
                                 self.font_color, self.font_type, self.num_lines,
                                 self.draw_cursor, self.message_tail, self.transparency,
                                 self.name_tag_bg, self.flags)
            self.dialog.last_update = engine.get_time() - 10000
        return self.dialog.update()

    def draw(self, surf) -> engine.Surface:
        self.dialog.draw(surf)
        return surf


class LocationCard:
    exist_time = 2000
    transition_speed = 166  # 10 frames

    def __init__(self, text, background="menu_bg_brown"):
        self.plain_text = text
        self.font = FONT["text"]
        self.font_name = "text"

        self.text_lines = self.format_text(text)
        self.determine_size()
        self.position = (10, 1)

        if background:
            self.background = self.make_background(background)
        else:
            self.background = engine.create_surface((self.width, self.height),
                                                    transparent=True)

        # For transition
        self.transition = "start"
        self.transition_progress = 0
        self.transition_update = engine.get_time()
        self.start_time = engine.get_time()

    def format_text(self, text):
        return [text]

    def determine_size(self):
        self.width = text_funcs.get_max_width(self.font_name, self.text_lines) + 16
        self.height = len(self.text_lines) * self.font.height + 8

    def make_background(self, background):
        surf = create_base_surf(self.width, self.height, background)
        return surf

    def update(self):
        current_time = engine.get_time()

        if self.transition:
            perc = (current_time - self.transition_update) / self.transition_speed
            self.transition_progress = utils.clamp(perc, 0, 1)
            if self.transition_progress == 1:
                if self.transition == "end":
                    return False
                self.transition = False

        if not self.transition and current_time - self.start_time > self.exist_time:
            self.transition_update = current_time
            self.transition = "end"
            self.transition_progress = 0

        return True

    def draw(self, surf):
        bg = self.background.copy()
        # Draw text
        for idx, line in enumerate(self.text_lines):
            self.font.blit_center(line, bg,
                                  (bg.get_width() // 2, idx * self.font.height + 4))

        if self.transition == "start":
            # when the location would enter, it's transparency changes from
            # 1.0 (100% transprenct) to .1 (Which is 90% opaque).
            transparency = 1.0 - (0.9 * self.transition_progress)
            bg = image_mods.make_translucent(bg, transparency)
        elif self.transition == "end":
            # When the location card would leave, it's transparency changes
            # from .1 (90% opaque) to 1.0 (100% transparency)
            transparency = 0.1 + (self.transition_progress * 0.9)
            bg = image_mods.make_translucent(bg, transparency)
        else:
            bg = image_mods.make_translucent(bg, 0.1)
        surf.blit(bg, self.position)

        return surf


class Credits:
    speed = 0.02

    def __init__(self, title, text, wait_flag=False, center_flag=True):
        self.title = title
        self.text = text
        self.title_font = FONT["credit_title"]
        self.title_font_name = "credit_title"
        self.font = FONT["credit"]
        self.font_name = "credit"

        self.center_flag = center_flag
        self.wait_flag = wait_flag
        self.waiting = False

        self.make_surf()

        self.position = [0, WINHEIGHT]

        self.pause_update = engine.get_time()
        self.has_paused = False
        self.start_update = engine.get_time()

    def make_surf(self):
        index = 0
        self.parsed_text = []
        for line in self.text:
            x_bound = WINWIDTH - 12 if self.center_flag else WINWIDTH - 88
            lines = text_funcs.line_wrap(self.font_name, line, x_bound)
            for li in lines:
                if self.center_flag:
                    x_pos = WINWIDTH // 2 - text_width(self.font_name, li) // 2
                else:
                    x_pos = 88
                y_pos = self.font.height * index + self.title_font.height
                index += 1
                self.parsed_text.append((li, index, (x_pos, y_pos)))

        self.num_lines = index

        size = (WINWIDTH, self.title_font.height + self.font.height * self.num_lines)
        self.surf = engine.create_surface(size, transparent=True)

        title_pos_x = 32
        self.title_font.blit(self.title, self.surf, (title_pos_x, 0))

        for text, index, pos in self.parsed_text:
            self.font.blit(text, self.surf, pos)

    def wait_time(self) -> int:
        time = int((self.num_lines + 2) * self.font.height * 50)
        if self.wait_flag:
            time += int(self.pause_time() * 2.1)
        return time

    def pause_time(self) -> int:
        return int((self.num_lines + 1) * 1000)

    def update(self):
        current_time = engine.get_time()

        if not self.waiting or current_time - self.pause_update > self.pause_time():
            self.waiting = False
            ms_passed = current_time - self.start_update
            if self.has_paused:
                ms_passed -= self.pause_time()
            self.position[1] = WINHEIGHT - (ms_passed * self.speed)
            # Should we pause?
            if (self.wait_flag and WINHEIGHT // 2 - self.surf.get_height() // 2
                    >= self.position[1]):
                self.waiting = True
                self.wait_flag = False
                self.pause_update = current_time
                self.has_paused = True
        return True

    def draw(self, surf):
        surf.blit(self.surf, self.position)
        return surf


class Ending:
    """
    Contains a dialog
    """

    solo_flag = True
    wait_time = 5000
    background = SPRITES.get("endings_display")

    def __init__(self, portrait, title, text, unit, wait_for_input: bool = False):
        self.portrait = portrait
        self.title = title
        self.plain_text = text
        self.speaker = None  # Unused attribute to match Dialog
        self.unit = unit
        self.wait_for_input = wait_for_input
        self.font = FONT["text"]
        self.font_name = "text"

        self.build_dialog()

        self.make_background()
        self.x_position = WINWIDTH

        self.wait_update = 0

    def build_dialog(self):
        self.dialog = Dialog(self.plain_text, num_lines=5, draw_cursor=self.wait_for_input)
        self.dialog.position = (8, 40)
        self.dialog.text_width = WINWIDTH - 32
        self.dialog.width = self.dialog.text_width + 16
        self.dialog.font = FONT["text"]
        self.dialog.font_type = "text"
        self.dialog.font_color = "white"
        self.dialog.reformat()

    def make_background(self):
        size = WINWIDTH, WINHEIGHT
        self.bg = engine.create_surface(size, transparent=True)
        self.bg.blit(self.background, (0, 0))
        self.bg.blit(self.portrait, (136, 57))

        title_pos_x = 68 - text_width(self.font_name, self.title) // 2
        self.font.blit(self.title, self.bg, (title_pos_x, 24))

        # Stats
        if self.unit:
            kills = game.records.get_kills(self.unit.nid)
            damage = game.records.get_damage(self.unit.nid)
            healing = game.records.get_heal(self.unit.nid)

            FONT["text-yellow"].blit(text_funcs.translate("K"), self.bg, (136, 8))
            FONT["text-yellow"].blit(text_funcs.translate("D"), self.bg, (168, 8))
            FONT["text-yellow"].blit(text_funcs.translate("H"), self.bg, (200, 8))
            FONT["text-blue"].blit(str(kills), self.bg, (144, 8))
            dam = str(damage)
            if damage >= 1000:
                dam = dam[:-3] + "." + dam[-3] + "k"
            heal = str(healing)
            if healing >= 1000:
                heal = heal[:-3] + "." + heal[-3] + "k"
            FONT["text-blue"].blit(dam, self.bg, (176, 8))
            FONT["text-blue"].blit(heal, self.bg, (208, 8))

        return self.bg

    def is_complete(self) -> bool:
        """
        Should stop being drawn
        """
        return False

    def is_done(self) -> bool:
        return self.dialog.is_done()

    def is_done_or_wait(self) -> bool:
        return self.dialog.is_done_or_wait()

    def is_paused(self) -> bool:
        return self.dialog.is_paused()

    def hurry_up(self):
        self.dialog.hurry_up()

    def update(self):
        current_time = engine.get_time()

        # Move in
        if self.x_position > 0:
            self.x_position -= 8
            self.x_position = max(0, self.x_position)
        else:
            self.dialog.update()

        # Only wait for so long
        if self.wait_update:
            if current_time - self.wait_update > self.wait_time:
                self.dialog.state = DialogState.DONE
        elif self.wait_for_input and self.is_done():
            self.wait_update = current_time
        elif not self.wait_for_input and self.is_done_or_wait():
            self.wait_update = current_time

        return False

    def draw(self, surf):
        bg = self.bg.copy()
        self.dialog.draw(bg)
        surf.blit(bg, (self.x_position, 0))


class PairedEnding(Ending):
    """
    Contains a dialog
    """

    background = SPRITES.get("paired_endings_display")

    def __init__(self, left_portrait, right_portrait, left_title, right_title, text,
                 left_unit, right_unit, wait_for_input: bool = False):
        self.left_portrait = left_portrait
        self.right_portrait = right_portrait
        self.left_title = left_title
        self.right_title = right_title
        self.plain_text = text
        self.speaker = None  # Unused attribute to match Dialog
        self.left_unit = left_unit  # Used in stats
        self.right_unit = right_unit
        self.wait_for_input = wait_for_input
        self.font_name = "text"

        self.build_dialog()

        self.make_background()
        self.x_position = WINWIDTH

        self.wait_update = 0

    def make_background(self):
        size = WINWIDTH, WINHEIGHT
        self.bg = engine.create_surface(size, transparent=True)
        self.bg.blit(self.background, (0, 0))
        self.bg.blit(self.left_portrait, (8, 49))
        self.bg.blit(self.right_portrait, (136, 49))

        render_text(self.bg, [self.font_name], [self.left_title], [None], (68, 24),
                    align=HAlignment.CENTER)
        render_text(self.bg, [self.font_name], [self.right_title], [None],
                    (WINWIDTH - 68, WINHEIGHT - 24),
                    align=HAlignment.CENTER)

        # Stats
        if self.left_unit:
            kills = game.records.get_kills(self.left_unit.nid)
            damage = game.records.get_damage(self.left_unit.nid)
            healing = game.records.get_heal(self.left_unit.nid)

            FONT["text-yellow"].blit(text_funcs.translate("K"), self.bg, (136, 8))
            FONT["text-yellow"].blit(text_funcs.translate("D"), self.bg, (168, 8))
            FONT["text-yellow"].blit(text_funcs.translate("H"), self.bg, (200, 8))
            FONT["text-blue"].blit(str(kills), self.bg, (144, 8))
            dam = str(damage)
            if damage >= 1000:
                dam = dam[:-3] + "." + dam[-3] + "k"
            heal = str(healing)
            if healing >= 1000:
                heal = heal[:-3] + "." + heal[-3] + "k"
            FONT["text-blue"].blit(dam, self.bg, (176, 8))
            FONT["text-blue"].blit(heal, self.bg, (208, 8))

        if self.right_unit:
            kills = game.records.get_kills(self.right_unit.nid)
            damage = game.records.get_damage(self.right_unit.nid)
            healing = game.records.get_heal(self.right_unit.nid)

            FONT["text-yellow"].blit(text_funcs.translate("K"), self.bg,
                                     (8, WINHEIGHT - 23))
            FONT["text-yellow"].blit(text_funcs.translate("D"), self.bg,
                                     (40, WINHEIGHT - 23))
            FONT["text-yellow"].blit(text_funcs.translate("H"), self.bg,
                                     (72, WINHEIGHT - 23))
            FONT["text-blue"].blit(str(kills), self.bg, (16, WINHEIGHT - 23))
            dam = str(damage)
            if damage >= 1000:
                dam = dam[:-3] + "." + dam[-3] + "k"
            heal = str(healing)
            if healing >= 1000:
                heal = heal[:-3] + "." + heal[-3] + "k"
            FONT["text-blue"].blit(dam, self.bg, (48, WINHEIGHT - 23))
            FONT["text-blue"].blit(heal, self.bg, (80, WINHEIGHT - 23))

        return self.bg
