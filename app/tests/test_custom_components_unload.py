import os
import shutil
import tempfile
import unittest


class CustomComponentUnloadTests(unittest.TestCase):
    '''
    Custom components are executed under the fixed module name 'custom_components'.
    The classes they define stay registered as subclasses of ItemComponent and
    SkillComponent for as long as anything references them, so switching projects
    has to drop the previous project's or two projects' components share the pool
    and duplicate each other's nids
    '''

    @classmethod
    def setUpClass(cls) -> None:
        from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
        cls.version = CURRENT_SERIALIZATION_VERSION
        cls.copy_dir = tempfile.mkdtemp()
        cls.copied_project = os.path.join(cls.copy_dir, 'copied.ltproj')
        shutil.copytree('default.ltproj', cls.copied_project)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.copy_dir, ignore_errors=True)
        # Leave the singletons on the project the rest of the suite expects
        cls().load('testing_proj.ltproj')

    def load(self, path):
        from app.data.resources.resources import RESOURCES
        from app.data.database.database import DB
        from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
        RESOURCES.load(path, CURRENT_SERIALIZATION_VERSION)
        DB.load(path, CURRENT_SERIALIZATION_VERSION)

    def count(self, nid):
        from app.data.database.item_components import ItemComponent
        from app.data.database.skill_components import SkillComponent
        from app.engine import item_component_access, skill_component_access
        from app.utilities.class_utils import recursive_subclasses
        # Populate the caches the way the editor does
        item_component_access.get_item_components()
        skill_component_access.get_skill_components()
        return (sum(1 for c in recursive_subclasses(ItemComponent) if getattr(c, 'nid', None) == nid),
                sum(1 for c in recursive_subclasses(SkillComponent) if getattr(c, 'nid', None) == nid))

    def test_the_same_project_at_a_new_path_does_not_duplicate_components(self):
        # default.ltproj is the sample project that ships custom components
        self.load('default.ltproj')
        self.assertEqual((1, 1), self.count('do_nothing'))
        self.load(self.copied_project)
        self.assertEqual((1, 1), self.count('do_nothing'))

    def test_switching_to_a_project_without_custom_components_unregisters_them(self):
        self.load('default.ltproj')
        self.assertEqual((1, 1), self.count('do_nothing'))
        self.load('testing_proj.ltproj')
        self.assertEqual((0, 0), self.count('do_nothing'))


if __name__ == '__main__':
    unittest.main()
