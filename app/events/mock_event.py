from enum import Enum
from typing import List

from app.data.database.database import DB

from app.engine import engine, game_state
from app.events import speak_style, event_commands
from app.events.event import Event
from app.engine.sprites import SPRITES
from app.engine.text_evaluator import TextEvaluator
from app.events.event_processor import EventProcessor
from app.events.event_prefab import EventPrefab
from app.events.event_version import EventVersion
from app.events.python_eventing.python_event_processor import PythonEventProcessor

from app.utilities.typing import NID

class IfStatementStrategy(Enum):
    ALWAYS_TRUE = 1
    ALWAYS_FALSE = 2
    EVALUATE = 3  # Actually evaluate the condition (needs local_args context)

class MockGame():
    """
    Mock game object that stores the speak styles, so they work even though the rest of the game isn't present
    """
    def __init__(self):
        self.speak_styles = speak_style.SpeakStyleLibrary()
        self.movement = None
        self.action_log = None
        self.camera = None

class MockEvent(Event):
    # These are the only commands that will be processed by this event
    available = {"finish", "wait", "end_skip", "music", "music_clear",
                 "sound", "stop_sound", "add_portrait", "multi_add_portrait",
                 "remove_portrait", "multi_remove_portrait", "remove_all_portraits",
                 "move_portrait", "mirror_portrait", "bop_portrait",
                 "expression", "speak_style", "speak", "unhold",
                 "transition", "change_background", "table",
                 "remove_table", "draw_overlay_sprite", "narrate",
                 "remove_overlay_sprite", "location_card", "credits",
                 "ending", "paired_ending", "pop_dialog", "unpause", 
                 "screen_shake", "toggle_narration_mode"}

    def __init__(self, nid, event_prefab: EventPrefab, command_idx=0, if_statement_strategy=IfStatementStrategy.ALWAYS_TRUE,
                 local_args=None):
        self._transition_speed = 250
        self._transition_color = (0, 0, 0)

        self.nid = nid
        self.command_queue: List[event_commands.EventCommand] = []

        self.background = None
        self.bg_black = SPRITES.get('bg_black').copy()
        self.game = MockGame()

        self._generic_setup()

        # local_args carries the trigger context (e.g. support_rank_nid, unit1,
        # unit2) so conditional commands can be evaluated under EVALUATE. unit1/
        # unit2/position must be passed positionally too: check_pair() closes
        # over those params, not over local_args.
        local_args = local_args or {}
        # Use the process-global GameState. It's not a real playthrough, but it's
        # the same object `evaluate.evaluate` falls back on for {e:} expressions,
        # so {v:}/{d:}/{f:} resolve against the same world instead of silently
        # returning "??".
        self.text_evaluator = TextEvaluator(self.logger, game_state.game,
                                            unit=local_args.get('unit1'),
                                            unit2=local_args.get('unit2'),
                                            position=local_args.get('position'),
                                            local_args=local_args)
        if event_prefab.version() != EventVersion.EVENT:
            self.processor = MockPythonEventProcessor('Mock', event_prefab.source)
        else:
            self.processor = MockEventProcessor('Mock', event_prefab.source, self.text_evaluator, if_statement_strategy, command_idx)

        # Runs the `on_startup` trigger event commands before running the main MockEvent (to load speak_style)
        startup_event_prefabs = DB.events.get('on_startup', None)
        for startup in startup_event_prefabs:
            for line in startup.source.split('\n'):
                self.queue_command(line)

    def update(self):
        # update all internal updates, remove the ones that are finished
        self.should_update = {name: to_update for name, to_update in self.should_update.items() if not to_update(self.do_skip)}

        self._update_state(dialog_log=False)
        self._update_transition()

    def draw(self, surf):
        # Necessary to clear out content from the previous frame
        if not self.background:
            engine.blit_center(surf, self.bg_black)
        surf = super().draw(surf)
        return surf

    def run_command(self, command: event_commands.EventCommand):
        # Only certain commands will be processed
        if command.nid in self.available:
            super().run_command(command)

    def _get_unit(self, text):
        return None

class MockEventProcessor(EventProcessor):
    def __init__(self, nid: NID, script: str, text_evaluator: TextEvaluator, 
                 if_statement_strategy=IfStatementStrategy.ALWAYS_TRUE,
                 command_pointer: int = 0):
        super().__init__(nid, script, text_evaluator)
        self.if_statement_strategy = if_statement_strategy
        self.command_pointer = command_pointer

    def _get_truth(self, command: event_commands.EventCommand) -> bool:
        if self.if_statement_strategy == IfStatementStrategy.EVALUATE:
            # Real evaluation against the trigger context (text_evaluator's
            # local_args). Used by the Support Room so a single support event
            # that branches on support_rank_nid plays the chosen rank.
            return super()._get_truth(command)
        truth = self.if_statement_strategy == IfStatementStrategy.ALWAYS_TRUE
        self.logger.info("Result: %s" % truth)
        return truth

class MockPythonEventProcessor(PythonEventProcessor):
    def __init__(self, nid: NID, source: str, command_pointer: int = 0):
        super().__init__(nid, source, None)
