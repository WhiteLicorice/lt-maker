import logging
import unittest

import app.engine.item_component_access as ICA
import app.engine.skill_component_access as SCA
from app.data.database.components import ComponentType
from app.data.database.database import DB
from app.data.resources.resources import RESOURCES
from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
from app.data.validation.db_validation import DBChecker
from app.events.event_prefab import EventPrefab
from app.events.regions import Region, RegionType

# testing_proj validates clean, so anything reported below was put there by the test.
# Level 0 is on the 15x10 tilemap Prologue: the unique units Eirika (4, 5) and
# Seth (4, 4), and the generic unit 101 (9, 6)
LEVEL = '0'
UNIT = 'Eirika'
ITEM = 'Iron_Sword'
SKILL = 'Steal'
MISSING = 'Nothing_By_This_Name'


class ValidationTestCase(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        DB.load('testing_proj.ltproj', CURRENT_SERIALIZATION_VERSION)
        RESOURCES.load('testing_proj.ltproj', CURRENT_SERIALIZATION_VERSION)
        self.level = DB.levels.get(LEVEL)

    def errors(self) -> list:
        return [str(error) for error in DBChecker(DB, RESOURCES).validate_for_errors()]

    def warnings(self) -> list:
        return [str(warning) for warning in DBChecker(DB, RESOURCES).validate_for_warnings()]

    def assert_one(self, reports: list, *mentions: str):
        '''Exactly one thing was reported, and it names everything in mentions'''
        self.assertEqual(1, len(reports), reports)
        for text in mentions:
            self.assertIn(text, reports[0])

    def level_unit(self, nid):
        return self.level.units.get(nid)


class CleanProjectTests(ValidationTestCase):
    def test_a_sound_project_has_nothing_to_report(self):
        self.assertEqual([], self.errors())
        self.assertEqual([], self.warnings())

    def test_an_error_is_reported_as_an_error_and_a_warning_as_a_warning(self):
        DB.units.get(UNIT).klass = MISSING
        self.level.objective['win'] = ''
        self.assertTrue(self.errors()[0].startswith('ERROR'))
        self.assertTrue(self.warnings()[0].startswith('WARNING'))
        self.assertEqual(1, len(self.errors()))
        self.assertEqual(1, len(self.warnings()))


class UnitValidationTests(ValidationTestCase):
    def test_a_unit_of_a_class_that_does_not_exist(self):
        DB.units.get(UNIT).klass = MISSING
        self.assert_one(self.errors(), UNIT, 'Class', MISSING)

    def test_a_unit_starting_with_an_item_that_does_not_exist(self):
        DB.units.get(UNIT).starting_items.append([MISSING, False])
        self.assert_one(self.errors(), UNIT, 'Starting Items', MISSING)

    def test_a_unit_learning_a_skill_that_does_not_exist(self):
        DB.units.get(UNIT).learned_skills.append([5, MISSING])
        self.assert_one(self.errors(), UNIT, 'Learned Skills', MISSING)

    def test_a_unit_with_an_alternate_class_that_does_not_exist(self):
        DB.units.get(UNIT).alternate_classes = [MISSING]
        self.assert_one(self.errors(), UNIT, 'Alternate Classes', MISSING)

    def test_every_missing_thing_on_a_unit_is_reported(self):
        unit = DB.units.get(UNIT)
        unit.klass = MISSING
        unit.starting_items.append([MISSING, False])
        self.assertEqual(2, len(self.errors()))


class LevelValidationTests(ValidationTestCase):
    def test_a_level_on_a_tilemap_that_does_not_exist(self):
        self.level.tilemap = MISSING
        self.assert_one(self.errors(), LEVEL, 'tilemap', MISSING)

    def test_a_level_with_no_tilemap_at_all_is_allowed(self):
        self.level.tilemap = None
        self.assertEqual([], self.errors())

    def test_a_level_with_a_background_tilemap_that_does_not_exist(self):
        self.level.bg_tilemap = MISSING
        self.assert_one(self.errors(), LEVEL, 'bg_tilemap', MISSING)

    def test_a_level_for_a_party_that_does_not_exist(self):
        self.level.party = MISSING
        self.assert_one(self.errors(), LEVEL, 'party', MISSING)

    def test_a_level_playing_music_that_does_not_exist(self):
        self.level.music['player_phase'] = MISSING
        self.assert_one(self.errors(), LEVEL, 'player_phase', MISSING)

    def test_a_level_playing_music_that_does_exist(self):
        self.level.music['player_phase'] = RESOURCES.music.keys()[0]
        self.assertEqual([], self.errors())

    def test_a_roam_level_needs_its_roam_unit(self):
        self.level.roam = True
        self.level.roam_unit = None
        self.assert_one(self.errors(), LEVEL, 'roam_unit')

    def test_a_level_that_is_not_a_roam_level_needs_no_roam_unit(self):
        self.level.roam = False
        self.level.roam_unit = None
        self.assertEqual([], self.errors())

    def test_a_level_with_an_objective_left_empty_is_a_warning(self):
        self.level.objective['loss'] = ''
        self.assertEqual([], self.errors())
        self.assert_one(self.warnings(), LEVEL, 'objective:loss')


class LevelUnitValidationTests(ValidationTestCase):
    def test_a_unit_with_an_ai_that_does_not_exist(self):
        self.level_unit(UNIT).ai = MISSING
        self.assert_one(self.errors(), LEVEL, UNIT, 'AI', MISSING)

    def test_a_unit_with_a_roam_ai_that_does_not_exist(self):
        self.level_unit(UNIT).roam_ai = MISSING
        self.assert_one(self.errors(), LEVEL, UNIT, 'Roam AI', MISSING)

    def test_a_unit_placed_off_the_map(self):
        self.level_unit(UNIT).starting_position = (15, 5)
        self.assert_one(self.errors(), LEVEL, UNIT, 'out of bounds')

    def test_a_unit_placed_on_the_last_tile_of_the_map(self):
        self.level_unit(UNIT).starting_position = (14, 9)
        self.assertEqual([], self.errors())

    def test_a_generic_unit_carrying_an_item_that_does_not_exist(self):
        self.level_unit('101').starting_items.append([MISSING, False])
        self.assert_one(self.errors(), LEVEL, '101', 'Items', MISSING)

    def test_a_generic_unit_with_a_skill_that_does_not_exist(self):
        self.level_unit('101').starting_skills.append(MISSING)
        self.assert_one(self.errors(), LEVEL, '101', 'Skills', MISSING)


class TravelerValidationTests(ValidationTestCase):
    '''A unit can start the level carrying another, which then has no position of its own'''

    def test_a_unit_carrying_one_that_waits_off_the_map(self):
        self.level_unit('Seth').starting_position = None
        self.level_unit(UNIT).starting_traveler = 'Seth'
        self.assertEqual([], self.errors())

    def test_a_unit_carrying_one_that_is_not_in_the_level(self):
        self.level_unit(UNIT).starting_traveler = MISSING
        self.assert_one(self.errors(), UNIT, MISSING, 'not loaded into level')

    def test_a_unit_carrying_itself(self):
        self.level_unit(UNIT).starting_traveler = UNIT
        self.assert_one(self.errors(), UNIT, 'its own traveler')

    def test_a_unit_carrying_one_that_also_stands_on_the_map(self):
        self.level_unit(UNIT).starting_traveler = 'Seth'
        self.assert_one(self.errors(), UNIT, 'Seth', 'already has position')

    def test_two_units_carrying_the_same_one(self):
        self.level_unit('Seth').starting_position = None
        self.level_unit(UNIT).starting_traveler = 'Seth'
        self.level_unit('101').starting_traveler = 'Seth'
        errors = self.errors()
        self.assertEqual(2, len(errors), errors)
        for error in errors:
            self.assertIn('identical traveler Seth', error)


class RegionValidationTests(ValidationTestCase):
    def add_region(self, position, size=(1, 1)) -> Region:
        region = Region('Trap')
        region.region_type = RegionType.EVENT
        region.position = position
        region.size = list(size)
        self.level.regions.append(region)
        return region

    def test_a_region_inside_the_map(self):
        self.add_region((13, 8), size=(2, 2))
        self.assertEqual([], self.warnings())

    def test_a_region_running_off_the_edge_of_the_map_is_a_warning(self):
        self.add_region((13, 8), size=(3, 2))
        self.assertEqual([], self.errors())
        self.assert_one(self.warnings(), LEVEL, 'Trap', 'bounds')

    def test_a_region_starting_before_the_map_is_a_warning(self):
        self.add_region((-1, 0))
        self.assert_one(self.warnings(), LEVEL, 'Trap', 'bounds')

    def test_a_region_with_no_position_is_allowed(self):
        self.add_region(None)
        self.assertEqual([], self.warnings())

    def test_a_region_in_a_level_with_no_tilemap_is_a_warning(self):
        self.add_region((0, 0))
        self.level.tilemap = None
        self.assert_one(self.warnings(), LEVEL, 'Trap', 'no tilemap')


class ComponentValidationTests(ValidationTestCase):
    '''An item's or skill's components may name other things in the project'''

    def give_item(self, component_nid, value):
        DB.items.get(ITEM).components.append(ICA.restore_component((component_nid, value)))

    def give_skill(self, component_nid, value):
        DB.skills.get(SKILL).components.append(SCA.restore_component((component_nid, value)))

    def test_an_item_component_naming_a_skill_that_does_not_exist(self):
        self.give_item('status_on_hit', MISSING)
        self.assert_one(self.errors(), ITEM, 'status_on_hit', MISSING)

    def test_an_item_component_naming_a_skill_that_exists(self):
        self.give_item('status_on_hit', SKILL)
        self.assertEqual([], self.errors())

    def test_a_list_component_reports_each_missing_entry(self):
        tag = DB.tags.keys()[0]
        self.give_item('item_tags', [tag, MISSING, 'Another_Missing_One'])
        errors = self.errors()
        self.assertEqual(2, len(errors), errors)
        self.assertIn(MISSING, errors[0])
        self.assertIn('Another_Missing_One', errors[1])

    def test_a_dict_component_checks_its_keys(self):
        stat = DB.stats.keys()[0]
        self.give_item('stat_change', [[stat, 2], [MISSING, 3]])
        self.assert_one(self.errors(), ITEM, 'stat_change', MISSING)

    def test_a_float_dict_component_checks_its_keys(self):
        stat = DB.stats.keys()[0]
        self.give_skill('stat_multiplier', [[stat, 1.5], [MISSING, 2.0]])
        self.assert_one(self.errors(), SKILL, 'stat_multiplier', MISSING)

    def test_a_string_dict_component_checks_its_keys(self):
        stat = DB.stats.keys()[0]
        self.give_skill('stat_change_expression', [[stat, '2'], [MISSING, '3']])
        self.assert_one(self.errors(), SKILL, 'stat_change_expression', MISSING)

    def test_a_choice_component_set_to_something_that_is_not_a_choice(self):
        self.give_skill('devil_axe_gba', 'Affect nothing at all')
        self.assert_one(self.errors(), SKILL, 'devil_axe_gba', 'Affect nothing at all')

    def test_a_choice_component_set_to_one_of_its_choices(self):
        self.give_skill('devil_axe_gba', 'Affect attacks done by enemy')
        self.assertEqual([], self.errors())

    def test_a_component_with_several_fields_checks_each_of_them(self):
        self.give_skill('skill_before_combat', {'skill': MISSING, 'recipient': 'nobody', 'allegiance': 'ally'})
        errors = self.errors()
        self.assertEqual(2, len(errors), errors)
        self.assertTrue(any(MISSING in error for error in errors))
        self.assertTrue(any('nobody' in error for error in errors))

    def test_a_list_inside_a_component_with_several_fields_is_checked(self):
        self.give_item('effective_damage', {'effective_tags': [MISSING]})
        self.assert_one(self.errors(), ITEM, 'effective_damage', MISSING)

    def test_a_deprecated_component_is_a_warning(self):
        self.give_skill('galeforce', None)
        self.assertEqual([], self.errors())
        self.assert_one(self.warnings(), SKILL, 'galeforce', 'Deprecated')

    def test_every_type_a_component_can_hold_is_one_the_validator_knows(self):
        # A type missing from the validator's table is a crash, not a report, the
        # first time a project uses a component of that type
        checker = DBChecker(DB, RESOURCES)
        for component in ICA.get_item_components().values() + SCA.get_skill_components().values():
            for held in self.types_held(component):
                self.assertIn(held, checker.dve._vmap, component.nid)

    def types_held(self, component) -> list:
        '''The types of the values a component holds, with containers opened up'''
        if not component.expose:
            return []
        if component.expose == ComponentType.NewMultipleOptions:
            exposed = list(component.options.values())
        else:
            exposed = [component.expose]
        held = []
        for expose in exposed:
            if not isinstance(expose, tuple):
                held.append(expose)
            elif expose[0] != ComponentType.MultipleChoice:
                held.append(expose[1])
        return held


class EventValidationTests(ValidationTestCase):
    '''Only events written in Python are checked'''

    def add_event(self, *lines):
        event = EventPrefab('Checked')
        event.source = '\n'.join(lines)
        DB.events.append(event)

    def test_a_python_event_using_commands_that_exist(self):
        self.add_event('#pyev1', '$wait 100')
        self.assertEqual([], self.errors())

    def test_a_python_event_that_is_not_valid_python(self):
        self.add_event('#pyev1', 'if True', '    $wait 100')
        self.assertEqual(1, len(self.errors()))

    def test_a_python_event_calling_a_command_that_does_not_exist(self):
        self.add_event('#pyev1', '$not_a_real_command 100')
        self.assertEqual(1, len(self.errors()))

    def test_an_event_in_the_plain_event_language_is_not_checked(self):
        self.add_event('not_a_real_command;100')
        self.assertEqual([], self.errors())


if __name__ == '__main__':
    unittest.main()
