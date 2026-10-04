import unittest
from typing import Callable

from app.data.database.database import DB
from app.data.resources.resources import RESOURCES
from app.engine.stale_save import StaleSaveError
from app.tests.engine_harness import EngineHarness, EngineTestCase, diff_saves

# testing_proj level 0: Eirika (4, 5) and Seth (4, 4) against the generic
# fighters 101 (9, 6) and 102 (8, 6), with O'Neill guarding (10, 8)
LEVEL = '0'

def play_first_combat(harness: EngineHarness):
    '''Seth kills 102, which leaves a dead unit, a used weapon and exp behind'''
    harness.start_level(LEVEL)
    harness.run_until_state('free')
    harness.attack('Seth', (8, 5))

def finish_turn_1(harness: EngineHarness):
    '''Eirika waits, the enemy phase plays out, and the player gets turn 2'''
    harness.wait('Eirika', (7, 5))
    harness.run_until_player_turn(2)

class SaveRoundTripTests(EngineTestCase):
    '''
    A save loaded straight back must save the same again. Anything the save
    drops, or that load rebuilds differently, shows up as a path into the save
    '''

    def setUp(self):
        super().setUp()
        self.harness = self.start_harness()

    def assertRoundTrips(self):
        before, after = self.harness.round_trip()
        self.assertEqual([], diff_saves(before, after))

    def test_round_trip_at_level_start(self):
        '''
        GameState.load runs UpdateFogOfWar for every unit on the map, marking
        the tiles around each one as previously visited, so the units the level
        starts with must have done the same in level_setup, before moving
        '''
        self.harness.start_level(LEVEL)
        self.harness.run_until_state('free')
        self.assertRoundTrips()

    def test_round_trip_after_the_enemy_phase(self):
        play_first_combat(self.harness)
        finish_turn_1(self.harness)
        self.assertRoundTrips()

    def test_loading_twice_is_the_same_as_loading_once(self):
        play_first_combat(self.harness)
        self.harness.round_trip()
        self.assertRoundTrips()

    def test_a_loaded_game_plays_out_the_same(self):
        '''
        Loading partway through changes nothing about what happens next. This
        catches state a save leaves out entirely, which a round trip can't see
        '''
        play_first_combat(self.harness)
        finish_turn_1(self.harness)
        straight_through, _ = self.harness.game.save()

        play_first_combat(self.harness)
        self.harness.round_trip()
        finish_turn_1(self.harness)
        with_a_load, _ = self.harness.game.save()

        for s_dict in (straight_through, with_a_load):
            # Counts frames, and the cursor walks a different route after a load
            del s_dict['playtime']
            # FreeState.begin marks the end of an action group every time it
            # begins, and it begins again on load
            del s_dict['action_log']
        self.assertEqual([], diff_saves(straight_through, with_a_load))

def rename(catalog_name: str, nid: str, resources: bool = False) -> Callable[[], None]:
    '''What renaming nid in the editor looks like to a save made before'''
    def change():
        catalog = getattr(RESOURCES if resources else DB, catalog_name)
        catalog.update_nid(catalog.get(nid), nid + '_renamed')
    return change

class StaleSaveTests(EngineTestCase):
    '''
    A save outlives the shape of the project that made it: a developer saves,
    renames something in the editor, and loads that save. Where the game can
    do without the old name it loads the save and carries on; where it can't,
    it refuses with a StaleSaveError naming what's missing.

    Each test loads the same save, made after Seth's first combat, into a
    project with one thing renamed
    '''
    _save = None

    def setUp(self):
        super().setUp()
        self.harness = self.start_harness()
        if StaleSaveTests._save is None:
            play_first_combat(self.harness)
            StaleSaveTests._save, _ = self.harness.game.save()
            # Back to a fresh project and game for the test itself
            super().setUp()

    def assertLoadsAndPlaysOn(self, change_project: Callable[[], None]):
        change_project()
        self.harness.load(StaleSaveTests._save)
        self.harness.run_until_state('free')
        finish_turn_1(self.harness)

    def test_renamed_item(self):
        '''Seth swung his Steel Sword before the save'''
        self.assertLoadsAndPlaysOn(rename('items', 'Steel_Sword'))

    def test_renamed_class_skill(self):
        self.assertLoadsAndPlaysOn(rename('skills', 'Canto'))

    def test_renamed_personal_skill(self):
        self.assertLoadsAndPlaysOn(rename('skills', 'Inspiration'))

    def test_renamed_unit(self):
        self.assertLoadsAndPlaysOn(rename('units', 'Seth'))

    def test_renamed_party(self):
        self.assertLoadsAndPlaysOn(rename('parties', 'Eirika'))

    def test_renamed_team(self):
        self.assertLoadsAndPlaysOn(rename('teams', 'enemy2'))

    def test_renamed_difficulty_mode(self):
        self.assertLoadsAndPlaysOn(rename('difficulty_modes', 'Normal'))

    def test_renamed_level(self):
        self.assertLoadsAndPlaysOn(rename('levels', LEVEL))

    def test_renamed_affinity(self):
        self.assertLoadsAndPlaysOn(rename('affinities', 'Anima'))

    def test_removed_factions(self):
        self.assertLoadsAndPlaysOn(lambda: DB.factions.clear())

    def assertRefusesToLoad(self, change_project: Callable[[], None], message: str):
        '''
        Some things a save can't do without. Loading it anyway used to crash
        far from the cause, so it stops at the load and says what's missing
        '''
        change_project()
        with self.assertRaisesRegex(StaleSaveError, message):
            self.harness.load(StaleSaveTests._save)

    def test_renamed_player_class(self):
        '''Used to crash drawing the map: UnitObject has no attribute sprite'''
        self.assertRefusesToLoad(rename('classes', 'Paladin'),
                                 "Unit 'Seth' has class 'Paladin', but no class with that nid was found in the database")

    def test_renamed_enemy_class(self):
        '''Used to crash as the units arrived: no attribute 'movement_group' '''
        klass = DB.levels.get(LEVEL).units.get('101').klass
        self.assertRefusesToLoad(rename('classes', klass), "has class '%s', but no class with that nid" % klass)

    def test_renamed_ai(self):
        '''Used to crash as the units arrived: no attribute 'guard_ai' '''
        self.assertRefusesToLoad(rename('ai', 'Attack'), "has AI 'Attack', but no AI with that nid")

    def test_renamed_weapon_type(self):
        '''Used to crash when the enemy AI weighed attacking Seth: no attribute 'advantage' '''
        self.assertRefusesToLoad(rename('weapons', 'Sword'), "weapon type 'Sword', but no weapon type with that nid")

    def test_renamed_tilemap(self):
        '''Used to crash restoring the level: no attribute 'nid' '''
        self.assertRefusesToLoad(rename('tilemaps', 'Prologue', resources=True),
                                 "has tilemap 'Prologue', but no tilemap with that nid")

if __name__ == '__main__':
    unittest.main()
