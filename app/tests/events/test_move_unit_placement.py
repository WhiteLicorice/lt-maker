from app.events import event_functions
from app.events.event import Event
from app.events.event_prefab import EventPrefab
from app.events.triggers import GenericTrigger
from app.tests.engine_harness import EngineTestCase

# testing_proj level 0: Eirika (4, 5) and Seth (4, 4)
LEVEL = '0'

class MoveUnitPlacementTests(EngineTestCase):
    '''
    move_unit onto a tile someone already stands on, with each placement rule
    '''

    def setUp(self):
        super().setUp()
        self.harness = self.start_harness()
        self.game = self.harness.start_level(LEVEL)
        self.harness.run_until_state('free')
        self.eirika = self.game.get_unit('Eirika')
        self.seth = self.game.get_unit('Seth')
        self.event = Event(EventPrefab('test_move_unit'), GenericTrigger(), game=self.game)

    def move_eirika_onto_seth(self, placement):
        event_functions.move_unit(self.event, 'Eirika', '4,4', 'immediate', placement)

    def test_push_moves_the_occupant_off_the_tile(self):
        self.move_eirika_onto_seth('push')
        self.assertEqual(self.eirika.position, (4, 4))
        self.assertNotEqual(self.seth.position, (4, 4))
        self.assertIs(self.game.board.get_unit((4, 4)), self.eirika)
        self.assertIs(self.game.board.get_unit(self.seth.position), self.seth)

    def test_stack_leaves_the_occupant_in_place(self):
        self.move_eirika_onto_seth('stack')
        self.assertEqual(self.eirika.position, (4, 4))
        self.assertEqual(self.seth.position, (4, 4))

    def test_giveup_moves_no_one(self):
        self.move_eirika_onto_seth('giveup')
        self.assertEqual(self.eirika.position, (4, 5))
        self.assertEqual(self.seth.position, (4, 4))
