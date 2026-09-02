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
        widget.new_category(None, None)
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
        # The 'Eirika' entry sits at the root, so findItems reaches it before the
        # nested 'Eirika' folder -- the order in which the folder wins the icon.
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


if __name__ == '__main__':
    unittest.main()
