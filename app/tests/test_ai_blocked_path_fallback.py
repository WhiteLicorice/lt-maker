from unittest.mock import patch

from app.data.database.ai import AIBehaviour, AIPrefab
from app.data.database.database import DB
from app.engine import action, skill_system
from app.engine.objects.region import RegionObject
from app.events.regions import RegionType
from app.tests.engine_harness import EngineTestCase
from app.utilities import utils

# testing_proj level 0: Eirika (4, 5) and Seth (4, 4) against the generic
# fighters 101 (9, 6) and 102 (8, 6), with O'Neill guarding (10, 8)
LEVEL = '0'
THRONE = 'Throne'

MOVE_TO_THRONE = ('Move_to', 'Event', -4, THRONE)
ATTACK_IN_RANGE = ('Attack', 'Enemy', -2)

class AIBlockedPathFallbackTests(EngineTestCase):
    '''
    A behaviour whose path is blocked by an enemy walks the unit as far along
    that path as it can. That is a last resort: an AI that moves to a throne
    and then attacks anyone in range attacks the enemy sitting on the throne,
    rather than walking up to it and stopping
    '''

    def setUp(self):
        super().setUp()
        self.harness = self.start_harness()
        self.game = self.harness.start_level(LEVEL)
        self.harness.run_until_state('free')
        self.unit = self.game.get_unit('102')
        self.eirika = self.game.get_unit('Eirika')
        self.ai = AIPrefab('Test AI', 20)
        DB.ai.append(self.ai)
        self.unit.ai = self.ai.nid

    def place_throne(self, pos):
        region = RegionObject(THRONE, RegionType.EVENT, pos, sub_nid=THRONE)
        action.do(action.AddRegion(region))

    def think(self, *behaviours):
        '''
        Has the fighter 102 decide what to do with an AI made of behaviours
        '''
        self.ai.behaviours = [AIBehaviour(*behaviour) for behaviour in behaviours]

        controller = self.game.ai
        controller.load_unit(self.unit)
        for _ in range(100):
            if controller.think():
                return controller
        self.fail("AI never finished thinking")

    def test_attacks_the_enemy_on_the_throne(self):
        self.place_throne(self.eirika.position)
        controller = self.think(MOVE_TO_THRONE, ATTACK_IN_RANGE)
        self.assertEqual(controller.goal_target, self.eirika.position)
        self.assertIsNotNone(controller.goal_item)
        self.assertTrue(controller.did_something)

    def test_attacks_the_enemy_on_a_position(self):
        controller = self.think(('Move_to', 'Position', -4, self.eirika.position), ATTACK_IN_RANGE)
        self.assertEqual(controller.goal_target, self.eirika.position)
        self.assertIsNotNone(controller.goal_item)

    def test_unit_that_passes_through_enemies_attacks_the_enemy_on_the_throne(self):
        patcher = patch.object(skill_system, 'pass_through', return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.place_throne(self.eirika.position)
        controller = self.think(MOVE_TO_THRONE, ATTACK_IN_RANGE)
        self.assertEqual(controller.goal_target, self.eirika.position)
        self.assertIsNotNone(controller.goal_item)

    def test_walks_up_to_an_ally_on_a_position(self):
        ally = self.game.get_unit('101')
        controller = self.think(('Move_to', 'Position', -4, ally.position), ATTACK_IN_RANGE)
        self.assertIsNone(controller.goal_target)
        self.assertEqual(controller.goal_position, self.unit.position)
        self.assertFalse(controller.did_something)

    def test_walks_towards_the_throne_when_no_other_behaviour_succeeds(self):
        self.place_throne(self.eirika.position)
        controller = self.think(MOVE_TO_THRONE)
        self.assertIsNone(controller.goal_target)
        self.assertLess(
            utils.calculate_distance(controller.goal_position, self.eirika.position),
            utils.calculate_distance(self.unit.position, self.eirika.position))
        self.assertTrue(controller.did_something)

    def test_first_blocked_behaviour_is_the_one_walked_towards(self):
        self.place_throne(self.eirika.position)
        towards_throne = self.think(MOVE_TO_THRONE).goal_position
        controller = self.think(MOVE_TO_THRONE, ('Move_to', 'Event', -4, 'No Such Region'))
        self.assertIsNotNone(towards_throne)
        self.assertEqual(controller.goal_position, towards_throne)

    def test_open_throne_is_moved_to_before_attacking(self):
        throne = (7, 5)
        self.place_throne(throne)
        controller = self.think(MOVE_TO_THRONE, ATTACK_IN_RANGE)
        self.assertEqual(controller.goal_position, throne)
        self.assertIsNone(controller.goal_target)
