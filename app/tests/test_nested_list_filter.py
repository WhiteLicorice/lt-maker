import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


class SiblingNamespaceTests(unittest.TestCase):
    '''
    Folders and entries share one namespace per parent, the way a directory and a
    file do. _treeify used to key a node's children by the bare nid, so a folder
    and an entry beside each other silently overwrote one another -- taking the
    whole overwritten subtree with them
    '''

    def setUp(self) -> None:
        import sys
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication(sys.argv)

        from app.editor.lib.components.nested_list import LTNestedList, IsCategoryRole
        self.LTNestedList = LTNestedList
        self.IsCategoryRole = IsCategoryRole

    def children_of_root(self, widget):
        root = widget.tree_widget.invisibleRootItem()
        return [(root.child(i).text(0), bool(root.child(i).data(0, self.IsCategoryRole)))
                for i in range(root.childCount())]

    def test_a_folder_beside_its_namesake_entry_survives(self):
        # The 'Eirika' folder holds Seth, and an unrelated entry is also called 'Eirika'
        widget = self.LTNestedList(None, list_entries=['Eirika', 'Seth'],
                                   list_categories={'Seth': ['Eirika']})
        self.assertEqual([('Eirika', False), ('Eirika', True)], self.children_of_root(widget))
        self.assertEqual((['Eirika', 'Seth'], {'Seth': ['Eirika']}),
                         widget.get_list_and_category_structure())

    def test_new_folder_does_not_take_an_entrys_name(self):
        widget = self.LTNestedList(None, list_entries=['New Category'], list_categories={})
        widget.new_category(None)
        names = [name for name, is_category in self.children_of_root(widget) if is_category]
        self.assertNotIn('New Category', names)


class FilterIgnoresFoldersTests(unittest.TestCase):
    '''
    A folder is allowed to carry the same name as an entry. The search results
    used to take their icons from every match, folders included, so the folder's
    icon landed on the entry's row -- the folder looked like it was in the
    results, and clicking it selected the entry instead
    '''

    def setUp(self) -> None:
        import sys
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication(sys.argv)

        from app.editor.lib.components.nested_list import LTNestedList
        self.LTNestedList = LTNestedList

    def build(self, list_entries, list_categories):
        from PyQt5.QtGui import QColor, QIcon, QPixmap

        def get_icon(nid):
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(255, 0, 0))
            return QIcon(pixmap)

        return self.LTNestedList(None, list_entries=list_entries,
                                 list_categories=list_categories,
                                 get_icon=get_icon)

    def folder_holds_its_namesake(self):
        return self.build(['Eirika', 'Seth'], {'Eirika': ['Eirika']})

    def folder_follows_its_namesake(self):
        # The 'Eirika' entry sits at the root, ahead of the nested 'Eirika' folder.
        # The folder cannot be a sibling of the entry: _treeify keys a node's
        # children by nid, so same-named siblings overwrite each other
        return self.build(['Eirika', 'Seth'], {'Seth': ['Chapter 1', 'Eirika']})

    def search(self, widget, text):
        widget.on_filter_changed(text)
        return [widget.search_list.item(i).text() for i in range(widget.search_list.count())]

    def assert_result_keeps_the_entrys_icon(self, widget):
        self.assertEqual(['Eirika'], self.search(widget, 'Eirika'))
        entry = widget.find_item_by_nid('Eirika')
        # The QImages have to outlive the comparison, so hold them in names
        expected = entry.icon(0).pixmap(32, 32).toImage()
        actual = widget.search_list.item(0).icon().pixmap(32, 32).toImage()
        self.assertEqual(expected, actual)

    def test_entry_keeps_its_icon_when_the_folder_holds_it(self):
        self.assert_result_keeps_the_entrys_icon(self.folder_holds_its_namesake())

    def test_entry_keeps_its_icon_when_the_folder_comes_later(self):
        self.assert_result_keeps_the_entrys_icon(self.folder_follows_its_namesake())

    def test_builds_without_a_get_foreground(self):
        '''get_foreground is documented as optional, and no tab actually supplies one'''
        widget = self.LTNestedList(None, list_entries=['Eirika'], list_categories={})
        self.assertEqual(1, widget.tree_widget.invisibleRootItem().childCount())

    def test_folder_alone_is_not_a_result(self):
        from PyQt5.QtGui import QIcon
        widget = self.LTNestedList(None, list_entries=['Seth'],
                                   list_categories={'Seth': ['Knights']},
                                   get_icon=lambda nid: QIcon())
        self.assertEqual([], self.search(widget, 'Knights'))


class SearchTextTests(unittest.TestCase):
    '''
    The search box matches whatever text the owning tab supplies for an entry, so an item
    or skill can be found by its name, description, components, or component values
    '''

    def setUp(self) -> None:
        import sys
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication(sys.argv)

        from app.editor.lib.components.nested_list import LTNestedList
        self.LTNestedList = LTNestedList

    def search(self, widget, text):
        widget.on_filter_changed(text)
        return [widget.search_list.item(i).text() for i in range(widget.search_list.count())]

    def test_defaults_to_matching_the_nid(self):
        widget = self.LTNestedList(None, list_entries=['Iron Sword', 'Steel Sword', 'Vulnerary'],
                                   list_categories={'Steel Sword': ['Swords']})
        self.assertEqual(['Iron Sword', 'Steel Sword'], self.search(widget, 'sword'))

    def test_matches_the_supplied_search_text(self):
        search_text = {'Iron Sword': 'Iron Sword\nweapon', 'Nosferatu': 'Nosferatu\nlifelink\n0.5',
                       'Vulnerary': 'Vulnerary\nheal'}
        widget = self.LTNestedList(None, list_entries=list(search_text),
                                   list_categories={'Nosferatu': ['Tomes']},
                                   get_search_text=search_text.get)
        self.assertEqual(['Nosferatu'], self.search(widget, 'LIFELINK'))
        self.assertEqual(['Iron Sword', 'Vulnerary'], self.search(widget, 'ea'))

    def test_component_search_text(self):
        from types import SimpleNamespace
        from app.editor.component_editor_properties import component_search_text
        skill = SimpleNamespace(nid='Hex', name='Hex Aura', desc='Lowers enemy avoid.',
                                components=[SimpleNamespace(nid='aura', name='Aura', value='Hex_Child'),
                                            SimpleNamespace(nid='combat_condition', name='Combat Condition',
                                                            value="unit.team == 'player'"),
                                            SimpleNamespace(nid='hidden', name='Hidden', value=None)])
        text = component_search_text(skill)
        for snippet in ('Hex Aura', 'enemy avoid', 'aura', 'Hex_Child', "unit.team == 'player'", 'hidden',
                        'Combat Condition'):
            self.assertIn(snippet, text)
        self.assertNotIn('None', text)


class InsertionRowTests(unittest.TestCase):
    '''
    An item's row comes from its own parent via indexOfChild, not from a QModelIndex
    the view handed over. That is what lets a filtered search result -- which has no
    index into the tree -- drive the same insertions as the tree itself
    '''

    def setUp(self) -> None:
        import sys
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication(sys.argv)

        from app.editor.lib.components.nested_list import LTNestedList
        self.LTNestedList = LTNestedList

    def build(self):
        return self.LTNestedList(None,
                                 list_entries=['Eirika', 'Seth', 'Franz', 'Gilliam', 'Vanessa'],
                                 list_categories={'Franz': ['Knights'], 'Gilliam': ['Knights']},
                                 attempt_new=lambda nid: True)

    def test_row_matches_the_views_own_index(self):
        widget = self.build()
        for nid in ['Eirika', 'Seth', 'Franz', 'Gilliam', 'Vanessa']:
            item = widget.find_item_by_nid(nid)
            self.assertEqual(widget.tree_widget.indexFromItem(item).row(),
                             widget._row_of(item), nid)

    def test_new_entry_lands_after_the_selected_one(self):
        widget = self.build()
        widget.new(widget.find_item_by_nid('Seth'))
        entries, _ = widget.get_list_and_category_structure()
        self.assertEqual(['Eirika', 'Seth', 'new', 'Franz', 'Gilliam', 'Vanessa'], entries)

    def test_new_entry_inside_a_folder_stays_in_it(self):
        widget = self.build()
        widget.new(widget.find_item_by_nid('Franz'))
        entries, categories = widget.get_list_and_category_structure()
        self.assertEqual(['Eirika', 'Seth', 'Franz', 'new', 'Gilliam', 'Vanessa'], entries)
        self.assertEqual(['Knights'], categories.get('new'))

    def test_new_entry_with_nothing_selected_goes_to_the_end(self):
        widget = self.build()
        widget.new(None)
        entries, categories = widget.get_list_and_category_structure()
        self.assertEqual('new', entries[-1])
        self.assertIsNone(categories.get('new'))

    def test_new_folder_on_an_entry_joins_that_entrys_folder(self):
        from app.editor.lib.components.nested_list import IsCategoryRole
        widget = self.build()
        widget.new_category(widget.find_item_by_nid('Franz'))
        knights = widget.find_item_by_nid('Franz').parent()
        names = [knights.child(i).text(0) for i in range(knights.childCount())
                 if knights.child(i).data(0, IsCategoryRole)]
        self.assertEqual(['New Category'], names)

    def test_delete_selects_the_neighbor_that_took_its_row(self):
        widget = self.build()
        widget.attempt_delete = lambda nid: True
        widget.delete(widget.find_item_by_nid('Seth'))
        entries, _ = widget.get_list_and_category_structure()
        self.assertEqual(['Eirika', 'Franz', 'Gilliam', 'Vanessa'], entries)
        # Seth's row is now the Knights folder, which is a category, so nothing is selected
        self.assertIsNone(widget.get_selected_nid())

    def test_delete_the_last_entry_in_a_folder_selects_the_one_before_it(self):
        widget = self.build()
        widget.attempt_delete = lambda nid: True
        widget.delete(widget.find_item_by_nid('Gilliam'))
        self.assertEqual('Franz', widget.get_selected_nid())

    def test_delete_the_last_entry_at_the_root_falls_back_a_row(self):
        widget = self.build()
        widget.attempt_delete = lambda nid: True
        widget.delete(widget.find_item_by_nid('Vanessa'))
        root = widget.tree_widget.invisibleRootItem()
        # The row Vanessa held is gone, so selection falls back to the last remaining
        # root child -- here the Knights folder, which reports no selected nid
        self.assertTrue(root.child(root.childCount() - 1).isSelected())
        self.assertEqual('Knights', root.child(root.childCount() - 1).text(0))


class SearchResultActionsTests(unittest.TestCase):
    '''
    The search results are a separate QListWidget, so they used to carry no context
    menu at all -- searching for an entry meant losing the ability to duplicate or
    delete it. Every action routes through the real tree item behind the result, which
    is what keeps a duplicate beside its original instead of at the end of the list
    '''

    def setUp(self) -> None:
        import sys
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication(sys.argv)

        from app.editor.lib.components.nested_list import LTNestedList
        self.LTNestedList = LTNestedList
        self.deleted = []
        self.duplicated = []

    def build(self):
        # Franz and Gilliam live in a folder; the duplicate has to stay in there with them
        widget = self.LTNestedList(
            None,
            list_entries=['Eirika', 'Seth', 'Franz', 'Gilliam', 'Vanessa'],
            list_categories={'Franz': ['Knights'], 'Gilliam': ['Knights']},
            allow_rename=True, allow_duplicate=True,
            on_begin_rename_item=lambda item, on_begin=True: None,
            attempt_delete=lambda nid: (self.deleted.append(nid), True)[1],
            attempt_duplicate=lambda nid, new_nid: (self.duplicated.append((nid, new_nid)), True)[1],
            attempt_rename=lambda old_nid, new_nid: True)
        return widget

    def results(self, widget):
        return [widget.search_list.item(i).text() for i in range(widget.search_list.count())]

    def search_for(self, widget, text):
        widget.search_box.setText(text)
        return self.results(widget)

    def item_of(self, widget, nid):
        return widget.find_item_by_nid(nid)

    def test_duplicate_from_search_lands_beside_its_original(self):
        widget = self.build()
        self.assertEqual(['Franz'], self.search_for(widget, 'Franz'))
        widget.duplicate_from_search(self.item_of(widget, 'Franz'))
        entries, categories = widget.get_list_and_category_structure()
        # Immediately after Franz, not appended to the end of the list
        self.assertEqual(['Eirika', 'Seth', 'Franz', 'Franz_1', 'Gilliam', 'Vanessa'], entries)
        # and inside the same folder
        self.assertEqual(['Knights'], categories.get('Franz_1'))
        self.assertEqual([('Franz', 'Franz_1')], self.duplicated)

    def test_duplicate_from_search_appears_in_the_results_and_is_selected(self):
        widget = self.build()
        self.search_for(widget, 'Franz')
        widget.duplicate_from_search(self.item_of(widget, 'Franz'))
        self.assertEqual(['Franz', 'Franz_1'], self.results(widget))
        self.assertEqual('Franz_1', widget.search_list.currentItem().text())

    def test_duplicate_from_a_root_level_result(self):
        widget = self.build()
        self.search_for(widget, 'Seth')
        widget.duplicate_from_search(self.item_of(widget, 'Seth'))
        entries, categories = widget.get_list_and_category_structure()
        self.assertEqual(['Eirika', 'Seth', 'Seth_1', 'Franz', 'Gilliam', 'Vanessa'], entries)
        self.assertIsNone(categories.get('Seth_1'))

    def test_delete_from_search_drops_it_from_the_tree_and_the_results(self):
        widget = self.build()
        self.assertEqual(['Franz'], self.search_for(widget, 'Franz'))
        widget.delete_from_search(self.item_of(widget, 'Franz'))
        entries, _ = widget.get_list_and_category_structure()
        self.assertEqual(['Eirika', 'Seth', 'Gilliam', 'Vanessa'], entries)
        self.assertEqual(['Franz'], self.deleted)
        self.assertEqual([], self.results(widget))

    def test_delete_key_in_the_results_deletes_that_entry(self):
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QKeyEvent
        widget = self.build()
        self.search_for(widget, 'Franz')
        widget.search_list.setCurrentRow(0)
        widget.keyPressEvent(QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier))
        self.assertEqual(['Franz'], self.deleted)
        self.assertEqual([], self.results(widget))

    def test_rename_from_search_drops_the_filter_first(self):
        widget = self.build()
        self.search_for(widget, 'Franz')
        self.assertTrue(widget.tree_widget.isHidden())
        widget.rename_from_search(self.item_of(widget, 'Franz'))
        # An editor opened on the hidden tree would be invisible and would strand the
        # tree in EditingState, so the filter has to go before the rename begins
        self.assertEqual('', widget.search_box.text())
        self.assertFalse(widget.tree_widget.isHidden())
        self.assertTrue(widget.search_list.isHidden())

    def menu_actions_for(self, widget, nid):
        '''Builds the results' context menu with QMenu stubbed, and reports its labels'''
        from app.editor.lib.components import nested_list

        class FakeMenu:
            def __init__(self, parent=None):
                self.labels = []

            def addAction(self, action):
                self.labels.append(action.text())

            def popup(self, pos):
                pass

        built = []
        real_menu = nested_list.QMenu
        nested_list.QMenu = lambda parent=None: built.append(FakeMenu()) or built[-1]
        try:
            item = widget.search_list.item([i for i in range(widget.search_list.count())
                                           if widget.search_list.item(i).text() == nid][0])
            widget.searchMenuRequested(widget.search_list.visualItemRect(item).center())
        finally:
            nested_list.QMenu = real_menu
        return built[0].labels if built else []

    def test_results_offer_duplicate_delete_rename(self):
        widget = self.build()
        self.search_for(widget, 'Franz')
        self.assertEqual(['Duplicate', 'Delete', 'Rename'], self.menu_actions_for(widget, 'Franz'))

    def test_results_menu_respects_the_widgets_permissions(self):
        widget = self.LTNestedList(None, list_entries=['Eirika'], list_categories={},
                                   allow_rename=False, allow_duplicate=False,
                                   attempt_delete=lambda nid: True)
        widget.search_box.setText('Eirika')
        self.assertEqual(['Delete'], self.menu_actions_for(widget, 'Eirika'))

    def test_right_click_on_empty_space_does_nothing(self):
        from PyQt5.QtCore import QPoint
        widget = self.build()
        self.search_for(widget, 'Franz')
        widget.searchMenuRequested(QPoint(0, 10000))  # below the last row


if __name__ == '__main__':
    unittest.main()
