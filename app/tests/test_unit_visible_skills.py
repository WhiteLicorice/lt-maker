import unittest
from unittest.mock import MagicMock

from app.data.database.database import DB
from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
from app.engine.objects.unit import UnitObject

def make_skill(nid: str) -> MagicMock:
    skill = MagicMock()
    skill.nid = nid
    skill.uid = nid
    skill.stack = None
    return skill

class UnitVisibleSkillsTests(unittest.TestCase):
    '''UnitObject.skills is worked out once, and again only after the skills change'''

    def setUp(self):
        DB.load('testing_proj.ltproj', CURRENT_SERIALIZATION_VERSION)
        self.unit = UnitObject('player')

    def test_a_unit_without_skills_works_them_out_once(self):
        '''An empty list read as no answer, so a unit without skills worked them out on every read'''
        self.assertEqual([], self.unit.skills)
        self.assertIs(self.unit.skills, self.unit.skills)

    def test_skills_are_worked_out_again_after_a_change(self):
        first = make_skill('First')
        self.unit.add_skill(first)
        self.assertEqual([first], self.unit.skills)
        second = make_skill('Second')
        self.unit.add_skill(second)
        self.assertEqual([first, second], self.unit.skills)
        self.unit.remove_skill(first, None)
        self.assertEqual([second], self.unit.skills)

    def test_a_list_already_read_keeps_its_skills(self):
        '''Changing the skills emptied the list skills had handed out, ending a loop over it early'''
        first = make_skill('First')
        self.unit.add_skill(first)
        read = self.unit.skills
        self.unit.add_skill(make_skill('Second'))
        self.assertEqual([first], read)

if __name__ == '__main__':
    unittest.main()
