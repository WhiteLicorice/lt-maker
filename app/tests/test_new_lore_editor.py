import os
import shutil
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


class NewLoreEditorTests(unittest.TestCase):
    '''
    The Lore editor uses the tree-style editor, so lore can be sorted into folders
    '''

    @classmethod
    def setUpClass(cls) -> None:
        import sys
        from app.editor.editor_locale import init_locale
        init_locale()
        from PyQt5.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self) -> None:
        from app.data.category import Categories
        from app.data.database.database import Database
        from app.data.database.lore import Lore
        from app.editor.lore_editor.new_lore_tab import NewLoreDatabase
        self.db = Database()
        # A catalog only gets its categories when a project is loaded
        self.db.lore.categories = Categories()
        self.db.lore.append(Lore('Eirika', 'Eirika', 'Princess of Renais', 'Character', 'A princess'))
        self.db.lore.append(Lore('Weapons', 'Weapons', 'The Weapon Triangle', 'Guide', 'Swords beat axes'))
        self.tab = NewLoreDatabase.create(db=self.db)

    def test_lists_every_lore(self):
        entries, categories = self.tab.tree_list.get_list_and_category_structure()
        self.assertEqual(entries, ['Eirika', 'Weapons'])
        self.assertEqual(categories, {})

    def test_selecting_a_lore_shows_it(self):
        self.tab.on_select('Weapons')
        props = self.tab.right_frame
        self.assertTrue(props.isEnabled())
        self.assertEqual(props.nid_box.edit.text(), 'Weapons')
        self.assertEqual(props.long_name_box.edit.text(), 'The Weapon Triangle')
        self.assertEqual(props.category_box.edit.text(), 'Guide')
        self.assertEqual(props.desc_box.edit.toPlainText(), 'Swords beat axes')

    def test_nothing_selected_disables_the_properties(self):
        self.assertFalse(self.tab.right_frame.isEnabled())

    def test_editing_fields_changes_the_lore(self):
        self.tab.on_select('Eirika')
        props = self.tab.right_frame
        props.long_name_box.edit.setText('Queen of Renais')
        props.category_box.edit.setText('Royalty')
        props.desc_box.edit.setText('A queen')
        lore = self.db.lore.get('Eirika')
        self.assertEqual((lore.title, lore.category, lore.text), ('Queen of Renais', 'Royalty', 'A queen'))

    def test_new_lore_is_named_after_its_nid(self):
        self.assertTrue(self.tab.create_new('Renais'))
        lore = self.db.lore.get('Renais')
        self.assertEqual((lore.name, lore.title, lore.category), ('Renais', 'Renais', 'Character'))

    def test_changing_nid_renames_matching_names_and_rekeys(self):
        self.tab.create_new('Renais')
        self.tab.reset()
        self.tab.on_select('Renais')
        props = self.tab.right_frame
        props.nid_box.edit.setText('Grado')
        props.nid_done_editing()
        self.assertIsNone(self.db.lore.get('Renais'))
        lore = self.db.lore.get('Grado')
        self.assertEqual((lore.name, lore.title), ('Grado', 'Grado'))

    def test_changing_nid_to_one_in_use_is_refused(self):
        from unittest.mock import patch
        from app.editor import new_editor_tab
        self.tab.on_select('Eirika')
        props = self.tab.right_frame
        props.nid_box.edit.setText('Weapons')
        with patch.object(new_editor_tab.QMessageBox, 'warning'):
            props.nid_done_editing()
        self.assertEqual(self.db.lore.get('Eirika').nid, 'Eirika')
        self.assertEqual(props.nid_box.edit.text(), 'Eirika')

    def test_duplicate_and_delete(self):
        self.assertTrue(self.tab.duplicate('Eirika', 'Eirika2'))
        self.assertEqual(self.db.lore.get('Eirika2').title, 'Princess of Renais')
        self.assertTrue(self.tab.delete_from_db('Eirika2'))
        self.assertIsNone(self.db.lore.get('Eirika2'))

    def test_search_matches_names_and_category(self):
        text = self.tab.get_search_text('Weapons')
        for part in ('Weapons', 'The Weapon Triangle', 'Guide'):
            self.assertIn(part, text)

    def test_list_is_compact_since_lore_has_no_icons(self):
        from PyQt5.QtCore import QSize
        from app.data.category import Categories
        self.db.lore.categories = Categories.load({'Eirika': 'People'})
        self.tab.categories = self.db.lore.categories
        self.tab.reset()
        tree = self.tab.tree_list.tree_widget
        self.assertEqual(tree.iconSize(), QSize(16, 16))
        folder = tree.topLevelItem(0)
        self.assertEqual(folder.text(0), 'People')
        for item in (folder, folder.child(0)):
            self.assertEqual(item.icon(0).availableSizes(), [QSize(16, 16)])
            self.assertLess(tree.itemDelegate().sizeHint(tree.viewOptions(), tree.indexFromItem(item)).height(), 32)

    def test_other_editors_keep_their_large_icons(self):
        from PyQt5.QtCore import QSize
        from app.editor.lib.components.nested_list import LTNestedList
        tree = LTNestedList(None, ['A']).tree_widget
        self.assertEqual(tree.iconSize(), QSize(32, 32))
        item = tree.topLevelItem(0)
        self.assertEqual(tree.itemDelegate().sizeHint(tree.viewOptions(), tree.indexFromItem(item)).height(), 32)

    def test_folders_survive_a_save_and_load(self):
        from app.data.category import Categories
        from app.data.database.database import DB
        from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
        tmp = os.path.join(tempfile.mkdtemp(), 'copy.ltproj')
        self.addCleanup(shutil.rmtree, os.path.dirname(tmp))
        shutil.copytree('default.ltproj', tmp)
        DB.load(tmp, CURRENT_SERIALIZATION_VERSION)
        self.addCleanup(DB.load, 'default.ltproj', CURRENT_SERIALIZATION_VERSION)
        # A project saved before lore had folders loads with none
        self.assertEqual(DB.lore.categories, {})

        tab = type(self.tab).create(db=DB)
        nid = DB.lore[0].nid
        tab.resort_db(list(DB.lore.keys()), Categories.load({nid: 'People/Renais'}))
        DB.serialize(tmp)
        DB.load(tmp, CURRENT_SERIALIZATION_VERSION)
        self.assertEqual(DB.lore.categories, {nid: ['People', 'Renais']})


if __name__ == '__main__':
    unittest.main()
