import unittest
from unittest.mock import MagicMock, patch


class MenuOptionListTests(unittest.TestCase):
    """The base/prep/set_custom_options event commands build parallel lists
    (options, enabled, events). The consumer states splice all three into the
    menu's option/ignore/event lists, so a length mismatch silently shifts the
    ignore list and disables the final option (menus.Choice.set_ignore treats
    a missing index as ignored)."""

    def setUp(self):
        self.event = MagicMock()
        self.event._resolve_nid = lambda nid: nid

    def get_game_var(self, action_mock, nid):
        for call in action_mock.SetGameVar.call_args_list:
            if call.args[0] == nid:
                return call.args[1]
        raise AssertionError('%s was never set' % nid)

    def test_base_blank_enabled_leaves_all_options_enabled(self):
        from app.events import event_functions
        with patch.object(event_functions, 'action') as action_mock:
            event_functions.base(self.event, 'Panorama', None, ['Resupply'], None, ['MARKETSTART'], set())
        # One entry per option, and none of them disabled
        self.assertEqual(self.get_game_var(action_mock, '_base_options_disabled'), [False])

    def test_base_partial_enabled_list_is_padded_to_option_count(self):
        from app.events import event_functions
        with patch.object(event_functions, 'action') as action_mock:
            event_functions.base(self.event, 'Panorama', None, ['A', 'B', 'C'], [False], ['E1'], set())
        self.assertEqual(self.get_game_var(action_mock, '_base_options_disabled'), [True, False, False])
        self.assertEqual(self.get_game_var(action_mock, '_base_options_events'), ['E1', None, None])
        self.assertEqual(self.get_game_var(action_mock, '_base_additional_options'), ['A', 'B', 'C'])

    def test_prep_blank_enabled_leaves_all_options_enabled(self):
        from app.events import event_functions
        with patch.object(event_functions, 'action') as action_mock:
            event_functions.prep(self.event, False, None, ['A', 'B'], None, ['E1'], None, set())
        self.assertEqual(self.get_game_var(action_mock, '_prep_options_enabled'), [True, True])
        self.assertEqual(self.get_game_var(action_mock, '_prep_options_events'), ['E1', None])
        self.assertEqual(self.get_game_var(action_mock, '_prep_options_info_descs'), ['', ''])

    def test_set_custom_options_blank_enabled_leaves_all_options_enabled(self):
        from app.events import event_functions
        with patch.object(event_functions, 'action') as action_mock:
            event_functions.set_custom_options(self.event, ['A', 'B'], None, None, ['E1'], set())
        self.assertEqual(self.get_game_var(action_mock, '_custom_options_disabled'), [False, False])
        self.assertEqual(self.get_game_var(action_mock, '_custom_options_events'), ['E1', None])

    def test_set_custom_options_descriptions_without_events(self):
        from app.events import event_functions
        with patch.object(event_functions, 'action') as action_mock:
            event_functions.set_custom_options(self.event, ['A', 'B'], None, ['descA', 'descB'], None, set())
        self.assertEqual(self.get_game_var(action_mock, '_custom_info_desc'), ['descA', 'descB'])


if __name__ == '__main__':
    unittest.main()
