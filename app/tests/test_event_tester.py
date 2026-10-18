from unittest.mock import patch

from app.tests import qt_headless  # noqa: F401  (must precede any Qt import)

from app.editor.game_actions import game_actions
from app.engine import driver, game_state
from app.events.event_prefab import EventPrefab
from app.tests.engine_harness import EngineTestCase


class EventTesterTests(EngineTestCase):
    def test_event_tester_ignores_vars_of_previous_launch(self):
        # A test play earlier in the same editor session leaves its vars behind
        game_state.game.build_new()
        game_state.game.game_vars['left_over'] = True
        game_state.game.level_vars['left_over_level'] = True

        prefab = EventPrefab('Test')
        prefab.source = 'speak;Eirika;{v:left_over}'
        seen = {}

        def run_event(mock_event):
            seen['game_vars'] = dict(game_state.game.game_vars)
            seen['level_vars'] = dict(game_state.game.level_vars)
            seen['text'] = mock_event.text_evaluator._evaluate_all('{v:left_over}')

        with patch.object(driver, 'start'), patch.object(driver, 'run_event', side_effect=run_event):
            game_actions.test_event(prefab)

        self.assertNotIn('left_over', seen['game_vars'])
        self.assertNotIn('left_over_level', seen['level_vars'])
        self.assertNotEqual(seen['text'], 'True')
