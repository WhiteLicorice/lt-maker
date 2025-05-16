from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from PyQt5 import QtCore
from PyQt5.QtCore import QSize, QItemSelection
from PyQt5.QtGui import QFont, QIcon, QImage, QPainter, QPixmap
from PyQt5.QtWidgets import (QAction, QMenu, QPushButton, QStyledItemDelegate,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
                             QWidget)

from app.data.category import Categories
from app.utilities import str_utils
from app.utilities.typing import NID


def create_tree_entry(nid: NID, icon: QIcon, is_category: bool) -> QTreeWidgetItem:
    new_item = QTreeWidgetItem()
    new_item.setText(0, nid)
    new_item.setIcon(0, icon)
    new_item.setData(0, IsCategoryRole, is_category)
    if not is_category:
        new_item.setFlags(new_item.flags() & ~QtCore.Qt.ItemIsDropEnabled)
    else:
        new_item.setFlags(new_item.flags() | QtCore.Qt.ItemIsEditable)
    return new_item

def create_empty_icon(w: int, h: int):
    pixmap = QPixmap(QSize(w, h))
    pixmap.fill(QtCore.Qt.transparent)
    return QIcon(pixmap)

def create_folder_icon(contents_icon: Optional[QIcon]) -> QIcon:
    folder_sprite = QPixmap(QImage('resources/editor_folder.png')).scaled(32, 32)
    if contents_icon:
        contents_pixmap = contents_icon.pixmap(QSize(16, 16))
        painter = QPainter(folder_sprite)
        painter.drawPixmap(8, 8, contents_pixmap)
        painter.end()
    icon = QIcon(folder_sprite)
    return icon

IsCategoryRole = 100

class NestedListStyleDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # decide here if item should be bold and set font weight to bold if needed
        if index.data(IsCategoryRole):
            option.font.setWeight(QFont.Bold)
        QStyledItemDelegate.paint(self, painter, option, index)

    def sizeHint(self, option, index) -> QtCore.QSize:
        osize = super().sizeHint(option, index)
        osize.setHeight(32)
        return osize

class LTNestedList(QWidget):
    """A nested list widget with category implementation. Provides numerous callback hooks to allow flexible usage.

    Args:
        on_click_item (function(nid)): Callback is called with a whenever any leaf node is selected, with the selected NID as param. Will not trigger on category click.
        on_rearrange_items (function(List[NID], Categories)): Callback is called whenever the data of the NestedList changes, with the flattened order
                                            of all entries (i.e. no categories), as well as a dictionary mapping each entry to its parent categories as params. Intended to be used
                                            to sync sort order and category naming between DB and the NestedList.
        attempt_delete (function(nid) -> bool): Callback is called with the NID of the item to be deleted. Callback is expected to handle deletion from the DB.
                                            If callback returns True, implies that deletion was successful and the NestedList will also delete its own entry.
        attempt_duplicate (function(nid_to_dup, new_nid) -> bool): Callback is called with the nid of the original item, and the new nid that it will create.
                                            Callback is expected to handle DB duplication. If callback returns True, implies that duplication was successful and
                                            the NestedList will also insert a duplicate into itself.
        attempt_new (function(new_nid) -> bool): Callback is called with the new nid to create. Callback is expected to handle initialization in the DB.
                                            If callback returns True, implies insertion was successful and the NestedList will insert a new entry.
    """
    def __init__(self, parent=None,
                 list_entries: Optional[List[NID]]=None,
                 list_categories: Optional[Categories]=None,
                 get_icon: Optional[Callable[[NID], Optional[QIcon]]]=None,
                 on_click_item: Optional[Callable[[Optional[NID]], None]]=None,
                 on_rearrange_items: Optional[Callable[[List[NID], Categories], None]]=None,
                 attempt_delete: Optional[Callable[[NID], bool]]=None,
                 attempt_new: Optional[Callable[[NID], bool]]=None,
                 attempt_duplicate: Optional[Callable[[NID, NID], bool]]=None,
                 ) -> None:
        super().__init__(parent)
        self.get_icon = get_icon or (lambda nid: create_empty_icon(32, 32))
        self.on_click_item = on_click_item
        self.on_rearrange_items = on_rearrange_items
        self.attempt_delete = attempt_delete
        self.attempt_new = attempt_new
        self.attempt_duplicate = attempt_duplicate

        layout = QVBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText('Filter by keyword, or by "nid"')
        self.search_box.textChanged.connect(self.on_filter_changed)
        layout.addWidget(self.search_box)

        self.search_list = QListWidget()
        layout.addWidget(self.search_list)
        self.search_list.itemClicked.connect(self.on_filter_list_click)
        self.search_list.hide()

        self.tree_widget = QTreeWidget()
        self.build_tree_widget(self.tree_widget, list_entries, list_categories)
        layout.addWidget(self.tree_widget)

        self.new_item_button = QPushButton("Create New")
        self.new_item_button.clicked.connect(lambda: self.new(self.tree_widget.selectedIndexes()[0] if self.tree_widget.selectedIndexes() else None,
                                             self.tree_widget.selectedItems()[0] if self.tree_widget.selectedItems() else None))
        layout.addWidget(self.new_item_button)
        self.setLayout(layout)

        # used to keep track of which category we just dragged an item out of
        self.disturbed_category = None

    def on_click(self, e):
        self.tree_widget.originalMousePressEvent(e)
        item = self.tree_widget.itemAt(e.pos())
        if item:
            while item.parent():
                item = item.parent()
        self.disturbed_category = item

    def on_filter_list_click(self, e):
        item_nid = e.text()
        tree_item = self.find_item_by_nid(item_nid)
        if tree_item:
            self.select_item(tree_item)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            if self.tree_widget.selectedIndexes():
                self.delete(self.tree_widget.selectedIndexes()[0], self.tree_widget.selectedItems()[0])

    def customMenuRequested(self, pos):
        item = self.tree_widget.itemAt(pos)
        index = self.tree_widget.indexAt(pos)
        menu = QMenu(self)
        new_action = QAction("New", self, triggered=lambda: self.new(index, item))
        menu.addAction(new_action)
        new_category = QAction("New Folder", self, triggered=lambda:self.new_category(index, item))
        menu.addAction(new_category)
        if item:
            is_category = item.data(0, IsCategoryRole)
            if not is_category:
                duplicate_action = QAction("Duplicate", self, triggered=lambda: self.duplicate(index, item))
                menu.addAction(duplicate_action)
            if self.can_delete(index, item):
                delete_action = QAction("Delete", self, triggered=lambda: self.delete(index, item))
                menu.addAction(delete_action)
            if is_category:
                rename_action = QAction("Rename", self, triggered=lambda: self.rename_category(item))
                menu.addAction(rename_action)
        menu.popup(self.tree_widget.viewport().mapToGlobal(pos))

    def reset(self, list_entries: Optional[List[NID]], list_categories: Optional[Categories]):
        previous_selected_item_nid = self.get_selected_nid()
        self.tree_widget.clear()
        self._build_tree_widget_in_place(list_entries, list_categories, self.tree_widget.invisibleRootItem())
        self.regenerate_icons(initial_generation=True)
        should_select = self.find_item_by_nid(previous_selected_item_nid)
        if should_select:
            self.select_item(should_select)

    def build_tree_widget(self, tree_widget: QTreeWidget, list_entries: Optional[List[NID]], list_categories: Optional[Categories]):
        self._build_tree_widget_in_place(list_entries, list_categories, tree_widget.invisibleRootItem())
        self.regenerate_icons(initial_generation=True)
        tree_widget.setItemDelegate(NestedListStyleDelegate(self))
        tree_widget.setUniformRowHeights(True)
        tree_widget.setDragDropMode(QTreeWidget.InternalMove)
        tree_widget.setHeaderHidden(True)
        tree_widget.setIconSize(QSize(32, 32))
        tree_widget.originalDropEvent = tree_widget.dropEvent
        tree_widget.dropEvent = self.on_drag_drop
        tree_widget.originalMousePressEvent = tree_widget.mousePressEvent
        tree_widget.mousePressEvent = self.on_click
        tree_widget.customContextMenuRequested.connect(self.customMenuRequested)
        tree_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tree_widget.itemChanged.connect(self.data_changed)
        tree_widget.selectionModel().selectionChanged.connect(self.on_tree_item_selected)

    def on_filter_changed(self, text: str):
        if text:
            filtered_items = self.tree_widget.findItems(text, QtCore.Qt.MatchContains | QtCore.Qt.MatchRecursive)
            items = set([item.text(0) for item in filtered_items if not item.data(0, IsCategoryRole)])
            item_icons = {item.text(0): item.icon(0) for item in filtered_items}
            self.search_list.clear()
            for item_nid in items:
                item_widget = QListWidgetItem(item_icons[item_nid], item_nid)
                self.search_list.addItem(item_widget)
            self.tree_widget.hide()
            self.search_list.show()
        else:
            self.search_list.hide()
            self.tree_widget.show()

    def update_nid(self, old_nid: NID, new_nid: NID):
        """Since this is a list that should reflect db changes,
        it needs to update if the nid is updated in the db via other means.
        """
        old_item = self.find_item_by_nid(old_nid)
        if not old_item:
            raise ValueError("Fatal: old_nid '%s' not found in tree" % old_nid)
        old_item.setText(0, new_nid)

    def new(self, index, item: Optional[QTreeWidgetItem]):
        list_entries, _ = self.get_list_and_category_structure()
        nids = list_entries
        new_nid = str_utils.get_next_name("new", nids)
        if self.attempt_new and self.attempt_new(new_nid):
            closest_category = self._determine_category_parent(item)
            new_item = create_tree_entry(new_nid, create_empty_icon(32, 32), False)
            row = self._determine_insertion_row(index, item)
            closest_category.insertChild(row, new_item)
            self.select_item(new_item)
            self.data_changed(new_item)

    def new_category(self, index, item: Optional[QTreeWidgetItem]):
        existing_categories = set()
        closest_category = self._determine_category_parent(item)
        for i in range(closest_category.childCount()):
            entry = closest_category.child(i)
            if entry.data(0, IsCategoryRole):
                existing_categories.add(entry.data(0, 0))
        new_category_name = str_utils.get_next_name("New Category", existing_categories)
        new_category = create_tree_entry(new_category_name, create_empty_icon(32, 32), True)
        row = self._determine_insertion_row(index, item)
        closest_category.insertChild(row, new_category)
        self.regenerate_icons(new_category)

    def duplicate(self, index, item: QTreeWidgetItem):
        list_entries, _ = self.get_list_and_category_structure()
        nids = list_entries
        nid = item.data(0, 2)
        new_nid = str_utils.get_next_name(nid, nids)
        is_category = item.data(0, IsCategoryRole)
        if not is_category: # duping categories doesn't make sense, lol
            if self.attempt_duplicate and self.attempt_duplicate(nid, new_nid):
                closest_category = self._determine_category_parent(item)
                new_item = create_tree_entry(new_nid, item.icon(0), False)
                row = self._determine_insertion_row(index, item)
                closest_category.insertChild(row, new_item)
                self.select_item(new_item)
                self.data_changed(new_item)

    def rename_category(self, item: QTreeWidgetItem):
        self.tree_widget.editItem(item)

    def can_delete(self, index, item: QTreeWidgetItem):
        if not index or not item:
            return False
        is_category = item.data(0, IsCategoryRole)
        if is_category and not item.childCount(): # is an empty category
            return True
        if not is_category: # is a normal item
            return True
        return False

    def delete(self, index, item: QTreeWidgetItem):
        nid = item.data(0, 2)
        actually_delete = False
        if self.can_delete(index, item):
            if item.data(0, IsCategoryRole):
                actually_delete = True
            elif self.attempt_delete and self.attempt_delete(nid):
                actually_delete = True
        if actually_delete:
            parent = item.parent() or self.tree_widget.invisibleRootItem()
            parent.removeChild(item)
            index_of_item_before = min(index.row(), parent.childCount() - 1)
            self.select_item(parent.child(index_of_item_before))

    def is_editor_open(self) -> bool:
        if not self.tree_widget.selectedItems():
            return False
        selected_item = self.tree_widget.selectedItems()[0]
        if self.tree_widget.isPersistentEditorOpen(selected_item):
            return True
        else:
            return False

    def get_selected_nid(self) -> Optional[NID]:
        if not self.tree_widget.selectedItems():
            return None
        selected_item = self.tree_widget.selectedItems()[0]
        if selected_item.data(0, IsCategoryRole):
            return None
        return selected_item.data(0, 0)

    def select_item(self, item: Optional[QTreeWidgetItem | NID]):
        if isinstance(item, NID):
            item = self.find_item_by_nid(item)
        if item:
            self.tree_widget.selectionModel().clearSelection()
            item.setSelected(True)
            self.tree_widget.scrollToItem(item)
        else:
            if self.on_click_item:
                self.on_click_item(None)

    def on_tree_item_selected(self, selection: Optional[QItemSelection]):
        if not self.on_click_item:
            return
        if not selection or not selection.indexes():
            self.on_click_item(None)
            return
        nid = selection.indexes()[0].data()
        is_category = selection.indexes()[0].data(IsCategoryRole)
        if not is_category:
            self.on_click_item(nid)
        elif is_category:
            self.on_click_item(None)

    def on_drag_drop(self, event):
        self.tree_widget.originalDropEvent(event)
        if self.disturbed_category:
            self.data_changed(self.disturbed_category)
        target_item = self.tree_widget.itemAt(event.pos())
        if target_item:
            self.data_changed(target_item)
            self.select_item(target_item)

    def data_changed(self, item: Optional[QTreeWidgetItem], column=None):
        list_entries, list_categories = self.get_list_and_category_structure()
        if self.on_rearrange_items:
            self.on_rearrange_items(list_entries, list_categories)
        self.regenerate_icons(item, False)

    def find_item_by_nid(self, nid) -> Optional[QTreeWidgetItem]:
        list_entries, list_categories = self.get_list_and_category_structure()
        found_item = None
        if nid is not None and nid in list_entries:
            categories = list_categories.get(nid, [])
            parent = self.tree_widget.invisibleRootItem()
            for category in categories:
                for i in range(parent.childCount()):
                    child = parent.child(i)
                    if child.data(0, IsCategoryRole) and child.data(0, 0) == category:
                        parent = child
                        break
            # parent now contains the path/to/node
            found_item = None
            for i in range(parent.childCount()):
                child = parent.child(i)
                if not child.data(0, IsCategoryRole) and child.data(0, 0) == nid:
                    found_item = child
                    break
        return found_item

    def regenerate_icons(self, root: Optional[QTreeWidgetItem]=None, initial_generation=False):
        """sets the icons for every entry. repeated calls will update category icons.
        initial call will also update the item-level icons.
        """
        if self.is_editor_open():
            return
        if not root:
            root = self.tree_widget.invisibleRootItem()
        while root.parent():
            root = root.parent()
        def recurse_get_icon(node: QTreeWidgetItem) -> Optional[QIcon]:
            if not node.data(0, IsCategoryRole) and not node == self.tree_widget.invisibleRootItem(): # is an item
                if initial_generation: # if initial, create icons before returning them
                    icon = self.get_icon(node.data(0, 0)) or create_empty_icon(32, 32)
                    node.setIcon(0, icon)
                return node.icon(0)
            else: # is a category, fish for child icons
                icon = None
                for i in range(node.childCount()):
                    child = node.child(i)
                    if not icon:
                        icon = recurse_get_icon(child)
                    else:
                        recurse_get_icon(child)
                node.setIcon(0, create_folder_icon(icon) or create_empty_icon(32, 32))
                return icon
        self.tree_widget.blockSignals(True)
        recurse_get_icon(root)
        self.tree_widget.blockSignals(False)

    def get_list_and_category_structure(self) -> Tuple[List[NID], Categories]:
        item_list = []
        item_categories = Categories()
        def recurse(root: QTreeWidgetItem, parent_categories: List[str]):
            child_count = root.childCount()
            categories = parent_categories[:]
            if not root.data(0, IsCategoryRole) and not child_count: # item
                item_nid = root.text(0)
                item_list.append(item_nid)
                if parent_categories:
                    item_categories[item_nid] = parent_categories
                return
            else: # category
                category_nid = root.text(0)
                if category_nid:
                    categories.append(category_nid)
                for row in range(child_count):
                    child = root.child(row)
                    recurse(child, categories[:])
        recurse(self.tree_widget.invisibleRootItem(), [])

        return (item_list, item_categories)

    def _determine_insertion_row(self, index, item: Optional[QTreeWidgetItem]) -> int:
        if not item or not index: # clicked on empty space - add to end of top level
            return self.tree_widget.invisibleRootItem().childCount()
        if item.data(0, IsCategoryRole): # clicked on a category - add to bottom of category
            return item.childCount()
        else: # clicked on an item - add immediately after item
            return index.row() + 1

    def _determine_category_parent(self, item: Optional[QTreeWidgetItem]) -> QTreeWidgetItem:
        """determines the closest category to the clicked item.
        useful for handling right-click context, for example:
            if we right click on a folder, we want to insert into the folder
            if we right click on an entry, we want to insert into the folder containing the entry
        """
        if not item:
            return self.tree_widget.invisibleRootItem()
        if item.data(0, IsCategoryRole):
            return item
        elif item.parent():
            return item.parent()
        else:
            return self.tree_widget.invisibleRootItem()

    @dataclass
    class ListNode():
        nid: NID
        is_category: bool = False
        children: Dict[NID, LTNestedList.ListNode] = field(default_factory=dict)

    def _build_tree_widget_in_place(self, list_entries: Optional[List[NID]],
                                   list_categories: Optional[Categories],
                                   parent: QTreeWidgetItem):
        """straightforward algorithm that first transforms `list_entries` and `list_categories` into a tree dictionary structure,
        then uses that structure to recursively populate the parent
        """
        list_entries = list_entries or []
        list_categories = list_categories or Categories()
        def _treeify(list_entries: List[NID], list_categories: Categories) -> LTNestedList.ListNode:
            root = LTNestedList.ListNode('root', True)
            for nid in list_entries:
                curr_node = root
                item_categories = list_categories.get(nid, None)
                if item_categories:
                    for category in item_categories:
                        new_node = LTNestedList.ListNode(category, True)
                        if category not in curr_node.children:
                            curr_node.children[category] = new_node
                        curr_node = curr_node.children[category]
                list_item = LTNestedList.ListNode(nid)
                curr_node.children[nid] = list_item
            return root
        def _build_tree_widget(root: LTNestedList.ListNode, parent: QTreeWidgetItem):
            for node in root.children.values():
                item = create_tree_entry(node.nid, create_empty_icon(32, 32), node.is_category)
                parent.addChild(item)
                if(node.is_category):
                    _build_tree_widget(node, item)
        list_as_tree = _treeify(list_entries, list_categories)
        _build_tree_widget(list_as_tree, parent)
