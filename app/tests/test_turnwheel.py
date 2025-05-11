import unittest

from app.engine import action
from app.engine.turnwheel import ActionLog

class TurnwheelTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_action_groups(self):
        # Null Case
        no_action_groups = ActionLog.get_action_groups([], 0)
        self.assertEqual(0, len(no_action_groups))

        # Simple Case w/ Extra
        actions = [
            action.MarkActionGroupStart("Eirika", "free"),
            action.Action(),  # Mock
            action.MarkActionGroupEnd("free"),
            action.Action(),  # Mock
        ]
        action_groups = ActionLog.get_action_groups(actions, 0)
        self.assertEqual(2, len(action_groups))
        self.assertTrue(type(action_groups[0]) == ActionLog.Move)
        self.assertEqual(0, action_groups[0].begin)
        self.assertEqual(2, action_groups[0].end)
        self.assertTrue(type(action_groups[1]) == ActionLog.Extra)
        self.assertEqual(3, action_groups[1].last_move_index)
        self.assertEqual(3, action_groups[1].action_index)

        # Case with 2 mark action begins and ends
        actions = [
            action.MarkActionGroupStart("Eirika", "free"),
            action.Action(),  # Mock
            action.Action(),  # Mock
            action.Action(),  # Mock
            action.MarkActionGroupEnd("free"),
            action.Action(),  # Mock
            action.MarkActionGroupStart("Franz", "free"),
            action.Action(),  # Mock
            action.Action(),  # Mock
            action.MarkActionGroupEnd("free"),
        ]
        action_groups = ActionLog.get_action_groups(actions, 0)
        self.assertEqual(2, len(action_groups))
        self.assertTrue(type(action_groups[0]) == ActionLog.Move)
        self.assertEqual(0, action_groups[0].begin)
        self.assertEqual(4, action_groups[0].end)
        self.assertTrue(type(action_groups[1]) == ActionLog.Move)
        self.assertEqual(6, action_groups[1].begin)
        self.assertEqual(9, action_groups[1].end)

        # Case with MarkPhase
        # Case with 2 mark action begins and ends and a mark phase
        actions = [
            action.MarkActionGroupStart("102", "ai"),
            action.Action(),  # Mock
            action.MarkActionGroupEnd("ai"),
            action.MarkPhase('player'),
            action.MarkActionGroupStart("Eirika", "free"),
            action.Action(),  # Mock
            action.MarkActionGroupEnd("free"),
        ]
        action_groups = ActionLog.get_action_groups(actions, 0)
        self.assertEqual(3, len(action_groups))
        self.assertTrue(type(action_groups[0]) == ActionLog.Move)
        self.assertEqual(0, action_groups[0].begin)
        self.assertEqual(2, action_groups[0].end)
        self.assertTrue(type(action_groups[1]) == ActionLog.Phase)
        self.assertEqual(3, action_groups[1].action_index)
        self.assertTrue(type(action_groups[2]) == ActionLog.Move)
        self.assertEqual(4, action_groups[2].begin)
        self.assertEqual(6, action_groups[2].end)

        # Case with nonzero first free action
        actions = [
            action.MarkActionGroupStart("Eirika", "free"),
            action.Action(),  # Mock
            action.Action(),  # Mock
            action.Action(),  # Mock
            action.MarkActionGroupEnd("free"),
            action.Action(),  # Mock
            action.MarkActionGroupStart("Franz", "free"),
            action.Action(),  # Mock
            action.Action(),  # Mock
            action.MarkActionGroupEnd("free"),
        ]
        action_groups = ActionLog.get_action_groups(actions, 6)
        self.assertEqual(1, len(action_groups))
        self.assertTrue(type(action_groups[0]) == ActionLog.Move)
        self.assertEqual(6, action_groups[0].begin)
        self.assertEqual(9, action_groups[0].end)
