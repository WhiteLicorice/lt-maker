import unittest
from unittest.mock import MagicMock, Mock, patch, call
from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
from app.engine.objects.item import ItemObject
from app.engine.game_board import GameBoard
from app.engine.target_system import TargetSystem
from app.engine.objects.unit import UnitObject
from app.engine.action import AddSkill, RemoveSkill, Action
from app.engine.source_type import SourceType

class FakeResetUnitVars:
    def __init__(self, unit):
        return

    def do(self):
        return

    def reverse(self):
        return

    def execute(self):
        return

class AddRemoveSkillTests(unittest.TestCase):
    def setUp(self):
        from app.data.database.database import DB
        DB.load('testing_proj.ltproj', CURRENT_SERIALIZATION_VERSION)
        self.test_unit = UnitObject('player')
        self.test_skill = MagicMock()
        self.test_skill.nid = 'Potatomancy'
        self.test_skill.stack = None
        self.test_skill_stack = MagicMock()
        self.test_skill_stack.nid = 'Spud_Stack'
        self.test_skill_stack.stack = MagicMock()
        self.test_skill_stack.stack.value = 3
        self.patchers = [
            patch('app.engine.action.ResetUnitVars', FakeResetUnitVars),
        ]
        for patcher in self.patchers:
            patcher.start()
        pass

    def tearDown(self):
        pass

    def test_add_removable_skill(self):
        '''
        You can add a skill to a unit under normal circumstances
        '''
        with unittest.mock.patch('app.engine.action.ResetUnitVars', FakeResetUnitVars) as plz_work:
            AddSkill(self.test_unit, self.test_skill).do()
            AddSkill(self.test_unit, 'Rescue').do()

            self.assertIn('Potatomancy', [s.nid for s in self.test_unit.all_skills])
            self.assertIn('Rescue', [s.nid for s in self.test_unit.all_skills])

    def test_remove_removable_skill(self):
        '''
        You can remove a skill from a unit under normal circumstances
        '''
        with unittest.mock.patch('app.engine.action.ResetUnitVars', FakeResetUnitVars) as plz_work:
            AddSkill(self.test_unit, self.test_skill).do()
            self.assertIn('Potatomancy', [s.nid for s in self.test_unit.all_skills])
            RemoveSkill(self.test_unit, self.test_skill).do()
            self.assertNotIn('Potatomancy', [s.nid for s in self.test_unit.all_skills])

            AddSkill(self.test_unit, self.test_skill).do()
            self.assertIn('Potatomancy', [s.nid for s in self.test_unit.all_skills])
            RemoveSkill(self.test_unit, 'Potatomancy', source='Bollocks', source_type=SourceType.KLASS).do()
            self.assertNotIn('Potatomancy', [s.nid for s in self.test_unit.all_skills])

    def test_add_remove_unremovable_skill(self):
        '''
        You can remove a unremovable skill from a unit only via the introducing effect, matching both NID and type
        '''
        with unittest.mock.patch('app.engine.action.ResetUnitVars', FakeResetUnitVars) as plz_work:
            AddSkill(self.test_unit, self.test_skill, source='Idaho', source_type=SourceType.TERRAIN).do()
            self.assertIn('Potatomancy', [s.nid for s in self.test_unit.all_skills])

            RemoveSkill(self.test_unit, 'Potatomancy').do()
            self.assertIn('Potatomancy', [s.nid for s in self.test_unit.all_skills])

            RemoveSkill(self.test_unit, 'Potatomancy', source='Idaho', source_type=SourceType.REGION).do()
            self.assertIn('Potatomancy', [s.nid for s in self.test_unit.all_skills])

            RemoveSkill(self.test_unit, 'Potatomancy', source='Bombay', source_type=SourceType.TERRAIN).do()
            self.assertIn('Potatomancy', [s.nid for s in self.test_unit.all_skills])

            RemoveSkill(self.test_unit, 'Potatomancy', source='Idaho', source_type=SourceType.TERRAIN).do()
            self.assertNotIn('Potatomancy', [s.nid for s in self.test_unit.all_skills])

    def test_displace_displaceable_skill(self):
        '''
        Adding a new copy of a skill displaces the existing one
        '''
        with unittest.mock.patch('app.engine.action.ResetUnitVars', FakeResetUnitVars) as plz_work:
            test_skill_dup = MagicMock()
            test_skill_dup.nid = 'Rescue'
            test_skill_dup.stack = None

            AddSkill(self.test_unit, test_skill_dup).do()
            self.assertIn(test_skill_dup, self.test_unit.all_skills)

            AddSkill(self.test_unit, 'Rescue').do()
            self.assertNotIn(test_skill_dup, self.test_unit.all_skills)
            self.assertIn('Rescue', [s.nid for s in self.test_unit.all_skills])

    def test_displace_undisplaceable_skill(self):
        '''
        You can remove a unremovable skill from a unit only via the introducing effect, matching both NID and type
        '''
        with unittest.mock.patch('app.engine.action.ResetUnitVars', FakeResetUnitVars) as plz_work:
            AddSkill(self.test_unit, self.test_skill, source='Idaho', source_type=SourceType.TERRAIN).do()
            self.assertIn(self.test_skill, self.test_unit.all_skills)

            test_skill_dup = MagicMock()
            test_skill_dup.nid = 'Potatomancy'
            test_skill_dup.stack = None
            AddSkill(self.test_unit, test_skill_dup).do()
            self.assertIn(self.test_skill, self.test_unit.all_skills)
            self.assertNotIn(test_skill_dup, self.test_unit.all_skills)

            AddSkill(self.test_unit, test_skill_dup, source='Bungus_Blade', source_type=SourceType.ITEM).do()
            self.assertIn(self.test_skill, self.test_unit.all_skills)
            self.assertIn(test_skill_dup, self.test_unit.all_skills)

    def test_displace_stacks(self):
        '''
        Adding a new copy of a stack skill displaces the oldest existing displaceable copy
        '''
        with unittest.mock.patch('app.engine.action.ResetUnitVars', FakeResetUnitVars) as plz_work:
            AddSkill(self.test_unit, self.test_skill_stack, source='Magmancer', source_type=SourceType.KLASS).do()

            test_skill_stack2 = MagicMock()
            test_skill_stack2.nid = 'Spud_Stack'
            test_skill_stack2.stack = MagicMock()
            test_skill_stack2.stack.value = 3
            AddSkill(self.test_unit, test_skill_stack2).do()

            test_skill_stack3 = MagicMock()
            test_skill_stack3.nid = 'Spud_Stack'
            test_skill_stack3.stack = MagicMock()
            test_skill_stack3.stack.value = 3
            AddSkill(self.test_unit, test_skill_stack3).do()
            self.assertIn(self.test_skill_stack, self.test_unit.all_skills)
            self.assertIn(test_skill_stack2, self.test_unit.all_skills)
            self.assertIn(test_skill_stack3, self.test_unit.all_skills)

            test_skill_stack4 = MagicMock()
            test_skill_stack4.nid = 'Spud_Stack'
            test_skill_stack4.stack = MagicMock()
            test_skill_stack4.stack.value = 3
            AddSkill(self.test_unit, test_skill_stack4).do()
            self.assertIn(self.test_skill_stack, self.test_unit.all_skills)
            self.assertNotIn(test_skill_stack2, self.test_unit.all_skills)
            self.assertIn(test_skill_stack3, self.test_unit.all_skills)
            self.assertIn(test_skill_stack4, self.test_unit.all_skills)

    def test_remove_stacks(self):
        '''
        Removing a stack skill removes all removable copies (including hidden ones), or the oldest removable copy for single count
        '''
        with unittest.mock.patch('app.engine.action.ResetUnitVars', FakeResetUnitVars) as plz_work:
            AddSkill(self.test_unit, self.test_skill_stack, source='Fart_Aura', source_type=SourceType.AURA).do()

            test_skill_stack2 = MagicMock()
            test_skill_stack2.nid = 'Spud_Stack'
            test_skill_stack2.stack = MagicMock()
            test_skill_stack2.stack.value = 3
            AddSkill(self.test_unit, test_skill_stack2, source='Magmancer', source_type=SourceType.KLASS).do()

            test_skill_stack3 = MagicMock()
            test_skill_stack3.nid = 'Spud_Stack'
            test_skill_stack3.stack = MagicMock()
            test_skill_stack3.stack.value = 3
            AddSkill(self.test_unit, test_skill_stack3, source='Magmancer', source_type=SourceType.KLASS).do()

            test_skill_stack4 = MagicMock()
            test_skill_stack4.nid = 'Spud_Stack'
            test_skill_stack4.stack = MagicMock()
            test_skill_stack4.stack.value = 3
            AddSkill(self.test_unit, test_skill_stack4, source='Ophie', source_type=SourceType.PERSONAL).do()

            test_skill_stack5 = MagicMock()
            test_skill_stack5.nid = 'Spud_Stack'
            test_skill_stack5.stack = MagicMock()
            test_skill_stack5.stack.value = 3
            AddSkill(self.test_unit, test_skill_stack5, source='Magmancer', source_type=SourceType.KLASS).do()
            self.assertIn(self.test_skill_stack, self.test_unit.all_skills)
            self.assertIn(test_skill_stack2, self.test_unit.all_skills)
            self.assertIn(test_skill_stack3, self.test_unit.all_skills)
            self.assertIn(test_skill_stack4, self.test_unit.all_skills)
            self.assertIn(test_skill_stack5, self.test_unit.all_skills)

            RemoveSkill(self.test_unit, 'Spud_Stack', count=1).do()
            self.assertIn(self.test_skill_stack, self.test_unit.all_skills)
            self.assertNotIn(test_skill_stack2, self.test_unit.all_skills)
            self.assertIn(test_skill_stack3, self.test_unit.all_skills)
            self.assertIn(test_skill_stack4, self.test_unit.all_skills)
            self.assertIn(test_skill_stack5, self.test_unit.all_skills)

            RemoveSkill(self.test_unit, 'Spud_Stack').do()
            self.assertIn(self.test_skill_stack, self.test_unit.all_skills)
            self.assertNotIn(test_skill_stack2, self.test_unit.all_skills)
            self.assertNotIn(test_skill_stack3, self.test_unit.all_skills)
            self.assertNotIn(test_skill_stack4, self.test_unit.all_skills)
            self.assertNotIn(test_skill_stack5, self.test_unit.all_skills)
    def test_remove_all_auras_strips_orphaned_child(self):
        '''
        An aura child applied to a unit must be removable when the unit leaves
        the map even if board bookkeeping has no record of it. This is the
        "permanent aura skill" bug: AURA skills are non-removable except via
        their exact source, so a board desync would otherwise orphan them.
        '''
        from app.engine import aura_funcs
        with unittest.mock.patch('app.engine.action.ResetUnitVars', FakeResetUnitVars):
            aura_child = MagicMock()
            aura_child.nid = 'Aura_Child'
            aura_child.stack = None
            # Applied as an aura whose parent skill instance has uid 999
            self.test_unit.add_skill(aura_child, source=999, source_type=SourceType.AURA)
            self.assertIn(aura_child, self.test_unit.all_skills)

            # No board entry exists for this child anywhere. The old board-driven
            # teardown would miss it; remove_all_auras must still strip it.
            aura_funcs.remove_all_auras(self.test_unit, test=True)
            self.assertNotIn(aura_child, self.test_unit.all_skills)

    def test_remove_all_auras_leaves_other_sources(self):
        '''
        remove_all_auras must only remove AURA-sourced skills, leaving skills
        from every other source (class, personal, terrain, ...) untouched.
        '''
        from app.engine import aura_funcs
        with unittest.mock.patch('app.engine.action.ResetUnitVars', FakeResetUnitVars):
            aura_child = MagicMock()
            aura_child.nid = 'Aura_Child'
            aura_child.stack = None
            self.test_unit.add_skill(aura_child, source=999, source_type=SourceType.AURA)

            klass_skill = MagicMock()
            klass_skill.nid = 'Class_Skill'
            klass_skill.stack = None
            self.test_unit.add_skill(klass_skill, source='Knight', source_type=SourceType.KLASS)

            aura_funcs.remove_all_auras(self.test_unit, test=True)
            self.assertNotIn(aura_child, self.test_unit.all_skills)
            self.assertIn(klass_skill, self.test_unit.all_skills)

    def _add_rescue_skill(self, traveler_nid):
        AddSkill(self.test_unit, 'Rescue', source=traveler_nid, source_type=SourceType.TRAVELER).do()
        self.assertIn('Rescue', [s.nid for s in self.test_unit.all_skills])

    def test_separate_removes_rescue_skill(self):
        '''
        Separating from a *rescued* traveler must take the Rescue skill off the
        carrier. TRAVELER skills are only removable via their exact source, so a
        Separate that clears unit.traveler without removing the skill leaves an
        orphan that can never be removed again (the captured-unit Rescue bug).
        '''
        from app.engine.action import Separate
        with unittest.mock.patch('app.engine.action.ResetUnitVars', FakeResetUnitVars), \
                unittest.mock.patch('app.engine.action.Wait', FakeResetUnitVars), \
                unittest.mock.patch('app.engine.action.skill_system', new=MagicMock()), \
                unittest.mock.patch('app.engine.action.game', new=MagicMock()):
            droppee = MagicMock()
            droppee.nid = 'Traveler'
            self.test_unit.traveler = droppee.nid
            self._add_rescue_skill(droppee.nid)

            Separate(self.test_unit, droppee, None, with_wait=False).do()

            self.assertIsNone(self.test_unit.traveler)
            self.assertNotIn('Rescue', [s.nid for s in self.test_unit.all_skills])

    def test_drop_removes_rescue_skill_when_executed(self):
        '''
        Drop.execute() (used by the turnwheel and by end of chapter cleanup) must
        remove the Rescue skill too, not just Drop.do().
        '''
        from app.engine.action import Drop
        with unittest.mock.patch('app.engine.action.ResetUnitVars', FakeResetUnitVars), \
                unittest.mock.patch('app.engine.action.skill_system', new=MagicMock()), \
                unittest.mock.patch('app.engine.action.game', new=MagicMock()):
            droppee = MagicMock()
            droppee.nid = 'Traveler'
            self.test_unit.traveler = droppee.nid
            self._add_rescue_skill(droppee.nid)

            Drop(self.test_unit, droppee, (1, 1)).execute()

            self.assertIsNone(self.test_unit.traveler)
            self.assertNotIn('Rescue', [s.nid for s in self.test_unit.all_skills])


if __name__ == '__main__':
    unittest.main()