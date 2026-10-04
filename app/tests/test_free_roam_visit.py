import unittest
from functools import partial
from types import SimpleNamespace
from unittest.mock import patch

from app.tests.engine_harness import EngineTestCase
from app.engine.game_state import GameState
from app.engine.objects.region import RegionObject
from app.events.regions import RegionType

VILLAGE = (3, 4)

def destroy_region() -> RegionObject:
    return RegionObject('Destroy', RegionType.EVENT, VILLAGE, [1, 1], 'Destroy',
                        condition="unit.team == 'enemy'")

def visit_region() -> RegionObject:
    return RegionObject('Visit', RegionType.EVENT, VILLAGE, [1, 1], 'Visit', condition='True')

class FreeRoamVisitRegionTests(EngineTestCase):
    def _visit_region(self, *regions, position=VILLAGE):
        from app.engine.roam import free_roam_state
        roam_unit = SimpleNamespace(nid='Eirika', team='player', position=position)
        level = SimpleNamespace(regions={region.nid: region for region in regions})
        fake_game = SimpleNamespace(level=level)
        # The real lookup, minus its cache, so region queries behave exactly as in game
        fake_game.get_region_under_pos = partial(GameState.get_region_under_pos.__wrapped__, fake_game)
        with patch.object(free_roam_state, 'game', fake_game):
            return free_roam_state.FreeRoamState.get_visit_region(SimpleNamespace(roam_unit=roam_unit))

    def test_visit_region_listed_after_destroy_region(self):
        '''
        Silvio 7/26/25: only the first event region on the tile was checked, so a destroy
        region listed before a village's visit region made the village unvisitable in free roam
        '''
        visit = visit_region()
        self.assertIs(self._visit_region(destroy_region(), visit), visit)

    def test_visit_region_listed_before_destroy_region(self):
        visit = visit_region()
        self.assertIs(self._visit_region(visit, destroy_region()), visit)

    def test_no_region_whose_condition_passes(self):
        self.assertIsNone(self._visit_region(destroy_region()))

    def test_ignores_other_region_types_and_tiles(self):
        formation = RegionObject('Formation', RegionType.FORMATION, VILLAGE, [1, 1])
        elsewhere = RegionObject('Elsewhere', RegionType.EVENT, (0, 0), [1, 1], 'Visit')
        self.assertIsNone(self._visit_region(formation, elsewhere))

if __name__ == '__main__':
    unittest.main()
