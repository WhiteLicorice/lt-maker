from app.editor.skill_list_widget import SkillListWidget
from PyQt5.QtWidgets import QPushButton, QLineEdit, QComboBox, \
    QWidget, QStyledItemDelegate, QDialog, QSpinBox, \
    QVBoxLayout, QHBoxLayout, QMessageBox, QApplication, QCheckBox
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon, QBrush, QColor, QFontMetrics
from app.events.event_prefab import EventInspectorEngine

from app.utilities import str_utils
from app.utilities.data import Data
from app.data.database.level_units import GenericUnit, UniqueUnit
from app.data.database.ai_groups import AIGroup
from app.data.database.database import DB

from app.editor import timer

from app.extensions.custom_gui import PropertyBox, ComboBox, Dialog, RightClickListView
from app.editor.base_database_gui import DragDropCollectionModel
from app.editor.custom_widgets import CustomQtRoles, UnitBox, ClassBox, \
    TeamBox, FactionBox, AIBox, ObjBox, RoamAIBox
from app.editor.map_sprite_editor import map_sprite_model
from app.editor.item_editor import item_model
from app.editor.unit_editor import new_unit_tab
from app.editor.faction_editor import faction_model
from app.editor.stat_widget import StatAverageDialog, GenericStatAveragesModel
from app.editor.item_list_widget import ItemListWidget
from app.editor.lib.components.validated_line_edit import NidLineEdit
from app.events.event_commands import ChangeRoaming


class UnitPainterMenu(QWidget):
    def __init__(self, state_manager, map_view):
        super().__init__()
        self.map_view = map_view
        self.state_manager = state_manager

        self.current_level = DB.levels.get(
            self.state_manager.state.selected_level)
        if self.current_level:
            self._data = self.current_level.units
        else:
            self._data = Data()

        grid = QVBoxLayout()
        self.setLayout(grid)

        def duplicate_func(model, index):
            return isinstance(model._data[index.row()], GenericUnit)

        self.view = RightClickListView(
            (None, duplicate_func, None), parent=self)
        self.view.currentChanged = self.on_item_changed
        self.view.doubleClicked.connect(self.on_double_click)

        self.model = AllUnitModel(self._data, self)
        self.view.setModel(self.model)
        self.view.setIconSize(QSize(32, 32))
        self.inventory_delegate = InventoryDelegate(self._data)
        self.view.setItemDelegate(self.inventory_delegate)

        grid.addWidget(self.view)

        self.create_button = QPushButton("Create Generic Unit...")
        self.create_button.clicked.connect(self.create_generic)
        grid.addWidget(self.create_button)
        self.load_button = QPushButton("Load Unit...")
        self.load_button.clicked.connect(self.load_unit)
        grid.addWidget(self.load_button)

        self.last_touched_generic = None

        # self.display = self
        self.display = None
        self.state_manager.subscribe_to_key(
            UnitPainterMenu.__name__, 'selected_level', self.set_current_level)
        timer.get_timer().tick_elapsed.connect(self.tick)

    def on_visibility_changed(self, state):
        pass

    def tick(self):
        self.model.layoutChanged.emit()

    def set_current_level(self, level_nid):
        level = DB.levels.get(level_nid)
        self.current_level = level
        self._data = self.current_level.units
        self.model._data = self._data
        self.model.update()
        self.inventory_delegate._data = self._data

    def select(self, idx):
        index = self.model.index(idx)
        self.view.setCurrentIndex(index)

    def deselect(self):
        self.view.clearSelection()

    def on_item_changed(self, curr, prev):
        # idx = int(idx)
        if self._data:
            unit = self._data[curr.row()]
            if unit.starting_position:
                self.map_view.center_on_pos(unit.starting_position)

    def get_current(self):
        for index in self.view.selectionModel().selectedIndexes():
            idx = index.row()
            if len(self._data) > 0 and idx < len(self._data):
                return self._data[idx]
        return None

    def create_generic(self, example=None):
        if not example:
            example = self.last_touched_generic
        created_unit, ok = GenericUnitDialog.get_unit(self, example)
        if ok:
            self.last_touched_generic = created_unit
            self._data.append(created_unit)
            self.model.update()
            # Select the unit
            idx = self._data.index(created_unit.nid)
            index = self.model.index(idx)
            self.view.setCurrentIndex(index)
            self.state_manager.change_and_broadcast('ui_refresh_signal', None)
            return created_unit
        return None

    def load_unit(self):
        unit, ok = LoadUnitDialog.get_unit(self)
        if ok:
            if unit.nid in self._data:
                QMessageBox.critical(
                    self, "Error!", "%s already present in level!" % unit.nid)
            else:
                self._data.append(unit)
                self.model.update()
                # Select the unit
                idx = self._data.index(unit.nid)
                index = self.model.index(idx)
                self.view.setCurrentIndex(index)
                self.state_manager.change_and_broadcast(
                    'ui_refresh_signal', None)
                return unit
        return None

    def on_double_click(self, index):
        idx = index.row()
        unit = self._data[idx]
        if unit.generic:
            serialized_unit = unit.save()
            unit, ok = GenericUnitDialog.get_unit(self, unit=unit)
            if ok:
                pass
            else:
                # Restore the old unit
                unit = GenericUnit.restore(serialized_unit)
                self._data.pop(idx)
                self._data.insert(idx, unit)
        else:  # Unique unit
            old_unit_nid = unit.nid
            old_unit_team = unit.team
            old_unit_ai = unit.ai
            old_unit_roam_ai = unit.roam_ai
            old_unit_ai_group = unit.ai_group
            edited_unit, ok = LoadUnitDialog.get_unit(self, unit)
            if ok:
                pass
            else:
                unit.nid = old_unit_nid
                unit.prefab = DB.units.get(unit.nid)
                unit.team = old_unit_team
                unit.ai = old_unit_ai
                unit.roam_ai = old_unit_roam_ai
                unit.ai_group = old_unit_ai_group


class LevelUnitModel(DragDropCollectionModel):
    allow_delete_last_obj = True

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self._data):
            return None
        if role == Qt.DisplayRole:
            unit = self._data[index.row()]
            text = str(unit.nid)
            group = ''
            if unit.ai_group:
                group = '-' + str(unit.ai_group)
            if isinstance(unit, GenericUnit):
                text += ' (' + str(unit.ai) + group + ' Lv ' + str(unit.level) + ')'
            else:
                text += ' (' + str(unit.ai) + group + ')'
            return text
        elif role == Qt.DecorationRole:
            unit = self._data[index.row()]
            # Don't draw any units which have been deleted in editor
            if not unit.generic and unit.nid not in DB.units:
                return None
            klass_nid = unit.klass
            num = timer.get_timer().passive_counter.count
            klass = DB.classes.get(klass_nid)
            if self.window.view:
                active = self.window.view.selectionModel().isSelected(index)
            else:
                active = False
            pixmap = map_sprite_model.get_map_sprite_icon(klass.map_sprite_nid, num, active, unit.team, unit.variant)
            if pixmap:
                return QIcon(pixmap)
            else:
                return None
        elif role == Qt.ForegroundRole:
            unit = self._data[index.row()]
            if unit.starting_position:
                return QBrush(QApplication.palette().text().color())
            elif any(u.starting_traveler == unit.nid for u in self._data):
                return QBrush(QColor("cyan"))
            else:
                return QBrush(QColor("red"))
        elif role == CustomQtRoles.UnderlyingDataRole:
            return self._data[index.row()]
        return None

class AllUnitModel(LevelUnitModel):
    def delete(self, idx):
        # check to make sure nothing else is using me!!
        unit = self._data[idx]
        current_level = self.window.current_level
        for unit_group in current_level.unit_groups:
            unit_group.remove(unit.nid)
        for u in self._data:
            if u.starting_traveler == unit.nid:
                u.starting_traveler = None

        # Just delete unit from any groups the unit is a part of
        super().delete(idx)

    def new(self, idx):
        if len(self._data):
            unit = self._data[idx]
            if unit.generic:
                ok = self.window.create_generic(unit)
            else:
                ok = self.window.load_unit()
        else:
            ok = self.window.load_unit()
        if ok:
            self._data.move_index(len(self._data) - 1, idx + 1)
            self.layoutChanged.emit()

    def duplicate(self, idx):
        obj = self._data[idx]
        if obj.generic:
            new_nid = str_utils.get_next_generic_nid(
                obj.nid, self._data.keys())
            serialized_obj = obj.save()
            new_obj = GenericUnit.restore(serialized_obj)
            new_obj.nid = new_nid
            new_obj.starting_position = None
            self._data.insert(idx + 1, new_obj)
            self.layoutChanged.emit()
        else:
            QMessageBox.critical(self.window, "Error!",
                                 "Cannot duplicate unique unit!")


class InventoryDelegate(QStyledItemDelegate):
    def __init__(self, data, parent=None):
        super().__init__()
        self._data = data
        self.window = parent

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        unit = self._data[index.row()]
        if isinstance(unit, str):  # It is a nid
            unit = self.window.current_level.units.get(unit)
        if not unit:
            return None
        # Don't draw any units which have been deleted in editor
        if not unit.generic and unit.nid not in DB.units:
            return None

        # Draw faction, if applicable
        rect = option.rect
        faction = DB.factions.get(unit.faction)
        if faction:
            pixmap = faction_model.get_pixmap(faction)
            if pixmap:
                pixmap = pixmap.scaled(24, 24, Qt.KeepAspectRatio)
            group = ''
            if unit.ai_group:
                group = '-' + str(unit.ai_group)
            text = str(unit.nid) + ' (' + str(unit.ai) + group + ' Lv ' + str(unit.level) + ')'
            font = QApplication.font()
            fm = QFontMetrics(font)
            left = rect.left() + 48 + fm.width(text)
            if pixmap:
                painter.drawImage(left, rect.center().y() - 24//2 + 2, pixmap.toImage())

        items = unit.starting_items
        for idx, item in enumerate(items):
            item_nid, droppable = item
            item = DB.items.get(item_nid)
            if item:
                pixmap = item_model.get_pixmap(item)
                if not pixmap:
                    continue
                left = rect.right() - ((idx + 1) * 16)
                top = rect.center().y() - 8
                if droppable:
                    green = QColor("Green")
                    green.setAlpha(80)
                    painter.setBrush(QBrush(green))
                    painter.drawRect(
                        left, top, pixmap.width(), pixmap.height())
                painter.drawImage(left, top, pixmap.toImage())

def valid_partners(units, unit) -> list:
    if not unit.starting_position:  # Don't bother for units not on map
        return []
    # Must be same team and not on the board and not a traveler unless your my traveler
    partners = {u.starting_traveler for u in units}
    return [u for u in units if
            u.team == unit.team
            and not u.starting_position
            and (unit.starting_traveler == u.nid
                 or u.nid not in partners)]

def build_traveler_box(self):
    self.traveler_box = ObjBox("Paired With", AllUnitModel, valid_partners(self.window.current_level.units, self.current), self)
    self.traveler_box.edit.setIconSize(QSize(32, 32))
    self.traveler_box.edit.view().setUniformItemSizes(True)
    if self.current.starting_traveler:
        partners = valid_partners(self.window.current_level.units, self.current)
        idx = [u.nid for u in partners].index(self.current.starting_traveler)
        self.traveler_box.edit.setCurrentIndex(idx)
    self.traveler_box.edit.activated.connect(self.traveler_changed)
    self.traveler_box.setEnabled(False)
    self.traveler_button = QCheckBox()
    if self.current.starting_traveler:
        self.traveler_button.setChecked(True)
        self.traveler_box.setEnabled(True)
    else:
        self.traveler_button.setChecked(False)
    self.traveler_button.stateChanged.connect(self.traveler_check)
    traveler_layout = QHBoxLayout()
    traveler_layout.addWidget(self.traveler_button)
    traveler_layout.addWidget(self.traveler_box)
    return traveler_layout

class LoadUnitDialog(Dialog):
    def __init__(self, parent=None, current=None):
        super().__init__(parent)
        self.setWindowTitle("Load Unit")
        self.window = parent
        self.view = None

        self.event_inspector: EventInspectorEngine = DB.events.inspector

        layout = QVBoxLayout()
        self.setLayout(layout)

        if current:
            self.current = current
            self.is_new_unit = False
        else:
            assert len(DB.units) > 0 and len(DB.ai) > 0
            nid = DB.units[0].nid
            self.current = UniqueUnit(nid, 'player', DB.ai[0].nid)
            self.is_new_unit = True

        self.unit_box = UnitBox(self, button=True)
        self.unit_box.edit.setValue(self.current.nid)
        self.unit_box.edit.currentIndexChanged.connect(self.unit_changed)
        self.unit_box.button.clicked.connect(self.access_units)
        layout.addWidget(self.unit_box)

        self.team_box = TeamBox(self)
        self.team_box.edit.setValue(self.current.team)
        self.team_box.edit.activated.connect(self.team_changed)
        layout.addWidget(self.team_box)

        self.ai_box = AIBox(self)
        self.ai_box.edit.setValue(self.current.ai)
        self.ai_box.edit.activated.connect(self.ai_changed)

        self.ai_group_box = PropertyBox("AI Group", ComboBox, self)
        self.ai_group_box.setToolTip("Units which share an AI Group will try to attack together.")
        self.ai_group_box.edit.setEditable(True)
        self.ai_group_box.edit.setInsertPolicy(QComboBox.InsertAlphabetically)
        self.ai_group_box.edit.addItems(sorted(self.window.current_level.ai_groups.keys()))
        if self.current.ai_group:
            self.ai_group_box.edit.setValue(self.current.ai_group)
        else:
            self.ai_group_box.edit.clearEditText()
        self.ai_group_box.edit.currentTextChanged.connect(self.ai_group_changed)
        # self.ai_group_box.edit.activated.connect(self.ai_group_changed)  # Shared with ai_group_threshold below

        self.ai_group_threshold_box = PropertyBox("Threshold", QSpinBox, self)
        self.ai_group_threshold_box.setToolTip("How many units need to be capable of attacking an enemy for group activation.")
        self.ai_group_threshold_box.edit.setRange(1, 99)
        if self.current.ai_group:
            ai_group = self.window.current_level.ai_groups.get(self.current.ai_group)
            self.ai_group_threshold_box.edit.setValue(ai_group.trigger_threshold)
        else:
            self.ai_group_threshold_box.edit.setValue(1)
        # self.ai_group_threshold_box.edit.valueChanged.connect(self.ai_group_changed)  # Shared with ai_group above

        ai_layout = QHBoxLayout()
        ai_layout.addWidget(self.ai_box)

        self.roam_ai_box = RoamAIBox(self)
        self.roam_ai_box.edit.setValue(self.current.roam_ai)
        self.roam_ai_box.edit.activated.connect(self.roam_ai_changed)
        self.roam_ai_box.hide()

        if self.event_inspector.find_all_calls_of_command(ChangeRoaming(), self.window.current_level.nid) or self.window.current_level.roam:
            self.roam_ai_box.show()
            ai_layout.addWidget(self.roam_ai_box)

        ai_layout.addWidget(self.ai_group_box)
        ai_layout.addWidget(self.ai_group_threshold_box)
        layout.addLayout(ai_layout)

        traveler_layout = build_traveler_box(self)
        layout.addLayout(traveler_layout)
        if DB.constants.value('pairup') and valid_partners(self.window.current_level.units, self.current):
            self.traveler_box.show()
            self.traveler_button.show()
        else:
            self.traveler_box.hide()
            self.traveler_button.hide()

        layout.addWidget(self.buttonbox)

    def team_changed(self, val):
        self.current.team = self.team_box.edit.currentText()

    def unit_changed(self, index):
        self.nid_changed(DB.units[index].nid)

    def ai_changed(self, val):
        self.current.ai = self.ai_box.edit.currentText()

    def ai_group_changed(self, text):
        """
        # Remember to set the value of the ai threshold box when we switch ai groups
        # if it's an already existing ai group
        """
        ai_group = self.ai_group_box.edit.currentText()
        if ai_group in self.window.current_level.ai_groups:
            threshold = self.window.current_level.ai_groups.get(ai_group).trigger_threshold
            self.ai_group_threshold_box.edit.setValue(threshold)

    def check_ai_group(self):
        ai_group = self.ai_group_box.edit.currentText()
        threshold = int(self.ai_group_threshold_box.edit.value())
        if ai_group in self.window.current_level.ai_groups:
            self.window.current_level.ai_groups.get(ai_group).trigger_threshold = threshold
        else:
            self.window.current_level.ai_groups.append(AIGroup(ai_group, threshold))
        self.current.ai_group = ai_group

    def traveler_check(self, val):
        if bool(val):
            self.traveler_box.setEnabled(True)
            partners = valid_partners(self.window.current_level.units, self.current)
            idx = self.traveler_box.edit.currentIndex()
            text = partners[idx].nid
            self.current.starting_traveler = text
        else:
            self.traveler_box.setEnabled(False)
            self.current.starting_traveler = None

    def traveler_changed(self, idx):
        partners = valid_partners(self.window.current_level.units, self.current)
        text = partners[idx].nid
        self.current.starting_traveler = text

    def roam_ai_changed(self, val):
        self.current.roam_ai = self.roam_ai_box.edit.currentText()

    def access_units(self):
        unit, ok = new_unit_tab.get(self.current.nid)
        if ok:
            self.unit_box.edit.setValue(unit.nid)

    def nid_changed(self, nid):
        # Don't bother if already identical
        if nid == self.current.nid:
            return

        # If nid already in level
        if nid in self.window.current_level.units.keys():
            self.unit_box.edit.setValue(self.current.nid)
            QMessageBox.warning(self.window, 'Warning',
                                'Unit ID %s already in use' % nid)
            return

        old_nid = self.current.nid
        self.current.nid = nid
        self.current.prefab = DB.units.get(nid)

        if not self.is_new_unit:
            # Swap level units
            self.window.current_level.units.update_nid(self.current, self.current.nid)
            # Swap level unit groups
            for unit_group in self.window.current_level.unit_groups:
                unit_group.swap(old_nid, self.current.nid)
            # Swap travelers
            for unit in self.window.current_level.units:
                if old_nid and unit.starting_traveler == old_nid:
                    unit.starting_traveler = self.current.nid

    # def set_current(self, current):
    #     self.current = current
    #     self.current.nid = self.
    #     self.current.team = self.team_box.edit.currentText()
    #     self.current.ai = self.ai_box.edit.currentText()

    @classmethod
    def get_unit(cls, parent, unit=None):
        dialog = cls(parent, unit)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            dialog.check_ai_group()
            unit = dialog.current
            return unit, True
        else:
            return None, False


class GenericUnitDialog(Dialog):
    def __init__(self, parent=None, example=None, unit=None):
        super().__init__(parent)
        self.setWindowTitle("Create Generic Unit")
        self.window = parent

        self.event_inspector = EventInspectorEngine(DB.events)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.averages_dialog = None
        self.view = None

        self._data = self.window._data
        if unit:
            self.current = unit
        elif example:
            new_nid = str_utils.get_next_generic_nid(
                example.nid, self._data.keys())
            self.current = GenericUnit(
                new_nid, example.variant, example.level, example.klass, example.faction,
                example.starting_items, example.starting_skills, example.team, example.ai)
        else:
            new_nid = str_utils.get_next_generic_nid("101", self._data.keys())
            assert len(DB.classes) > 0 and len(DB.factions) > 0 and len(
                DB.items) > 0 and len(DB.ai) > 0
            self.current = GenericUnit(
                new_nid, None, 1, DB.classes[0].nid, DB.factions[0].nid,
                [(DB.items[0].nid, False)], [], 'player', DB.ai[0].nid)

        self.nid_box = PropertyBox("Unique ID", NidLineEdit, self)
        self.nid_box.edit.setPlaceholderText("Unique ID")
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)
        layout.addWidget(self.nid_box)

        self.team_box = TeamBox(self)
        self.team_box.edit.activated.connect(self.team_changed)
        layout.addWidget(self.team_box)

        self.class_box = ClassBox(self)
        self.class_box.edit.currentIndexChanged.connect(self.class_changed)
        self.class_box.model.display_team = self.current.team
        layout.addWidget(self.class_box)

        self.level_box = PropertyBox("Level", QSpinBox, self)
        self.level_box.edit.setRange(1, 255)
        self.level_box.edit.setAlignment(Qt.AlignRight)
        self.level_box.edit.valueChanged.connect(self.level_changed)
        self.level_box.add_button(QPushButton("..."))
        self.level_box.button.clicked.connect(self.display_averages)
        self.level_box.button.setMaximumWidth(40)

        self.variant_box = PropertyBox("Animation Variant", QLineEdit, self)
        self.variant_box.edit.setPlaceholderText("No Variant")
        self.variant_box.edit.textChanged.connect(self.variant_changed)

        mini_layout = QHBoxLayout()
        mini_layout.addWidget(self.variant_box)
        mini_layout.addWidget(self.level_box)
        layout.addLayout(mini_layout)

        self.faction_box = FactionBox(self)
        self.faction_box.edit.currentIndexChanged.connect(self.faction_changed)
        layout.addWidget(self.faction_box)

        self.ai_box = AIBox(self)
        self.ai_box.edit.activated.connect(self.ai_changed)

        self.ai_group_box = PropertyBox("AI Group", ComboBox, self)
        self.ai_group_box.setToolTip("Units which share an AI Group will try to attack together.")
        self.ai_group_box.edit.setEditable(True)
        self.ai_group_box.edit.setInsertPolicy(QComboBox.InsertAlphabetically)
        self.ai_group_box.edit.addItems(sorted(self.window.current_level.ai_groups.keys()))
        self.ai_group_box.edit.currentTextChanged.connect(self.ai_group_changed)

        self.ai_group_threshold_box = PropertyBox("Threshold", QSpinBox, self)
        self.ai_group_threshold_box.setToolTip("How many units need to be capable of attacking an enemy for group activation.")
        self.ai_group_threshold_box.edit.setRange(1, 99)

        ai_layout = QHBoxLayout()
        ai_layout.addWidget(self.ai_box)

        self.roam_ai_box = RoamAIBox(self)
        self.roam_ai_box.edit.activated.connect(self.roam_ai_changed)
        self.roam_ai_box.hide()

        if self.event_inspector.find_all_calls_of_command(ChangeRoaming(), self.window.current_level.nid) or self.window.current_level.roam:
            self.roam_ai_box.show()
            ai_layout.addWidget(self.roam_ai_box)

        ai_layout.addWidget(self.ai_group_box)
        ai_layout.addWidget(self.ai_group_threshold_box)
        layout.addLayout(ai_layout)

        traveler_layout = build_traveler_box(self)
        layout.addLayout(traveler_layout)
        if DB.constants.value('pairup') and valid_partners(self.window.current_level.units, self.current):
            self.traveler_box.show()
            self.traveler_button.show()
        else:
            self.traveler_box.hide()
            self.traveler_button.hide()

        self.item_widget = ItemListWidget("Items", self)
        self.item_widget.items_updated.connect(self.items_changed)
        layout.addWidget(self.item_widget)

        self.skill_widget = SkillListWidget("Skills", self)
        self.skill_widget.skills_updated.connect(self.skills_changed)
        # self.item_widget.setMaximumHeight(200)
        layout.addWidget(self.skill_widget)

        layout.addWidget(self.buttonbox)

        self.set_current(self.current)

        timer.get_timer().tick_elapsed.connect(self.tick)

    def tick(self):
        self.class_box.model.dataChanged.emit(self.class_box.model.index(
            0), self.class_box.model.index(self.class_box.model.rowCount()))

    def nid_changed(self, text):
        if self.current:
            self.current.nid = text

    def nid_done_editing(self):
        if not self.current:
            return
        # Check validity of nid!
        other_nids = [d.nid for d in self._data.values()
                      if d is not self.current]
        other_nids += DB.units.keys()  # Can't use these either
        if not self.current.nid or self.current.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning',
                                'Unit ID %s already in use' % self.current.nid)
            new_nid = str_utils.get_next_generic_nid("101", other_nids)
            self.current.nid = new_nid
        # Find old nid
        old_nid = self._data.find_key(self.current)
        # Swap level units
        self._data.update_nid(self.current, self.current.nid)
        # Swap level unit groups
        for unit_group in self.window.current_level.unit_groups:
            unit_group.swap(old_nid, self.current.nid)
        # Swap travelers
        for unit in self.window.current_level.units:
            if old_nid and unit.starting_traveler == old_nid:
                unit.starting_traveler = self.current.nid

    def team_changed(self, val):
        self.current.team = self.team_box.edit.currentText()
        self.class_box.model.display_team = self.current.team
        self.class_box.model.layoutChanged.emit()  # Force color change

    def class_changed(self, index):
        self.current.klass = self.class_box.edit.currentText()
        self.level_box.edit.setMaximum(
            DB.classes.get(self.current.klass).max_level)
        # self.check_color()
        if self.averages_dialog:
            self.averages_dialog.update()

    def level_changed(self, val):
        self.current.level = val
        if self.averages_dialog:
            self.averages_dialog.set_current(self.current)
            self.averages_dialog.update()

    def variant_changed(self, text):
        self.current.variant = text

    def faction_changed(self, index):
        faction_nid = self.faction_box.edit.currentText()
        self.current.faction = faction_nid

    def ai_changed(self, val):
        self.current.ai = self.ai_box.edit.currentText()

    def ai_group_changed(self, text):
        """
        # Remember to set the value of the ai threshold box when we switched ai groups
        # if it's an already existing ai group
        """
        ai_group = self.ai_group_box.edit.currentText()
        if ai_group in self.window.current_level.ai_groups:
            threshold = self.window.current_level.ai_groups.get(ai_group).trigger_threshold
            self.ai_group_threshold_box.edit.setValue(threshold)

    def check_ai_group(self):
        ai_group = self.ai_group_box.edit.currentText()
        threshold = int(self.ai_group_threshold_box.edit.value())
        if ai_group in self.window.current_level.ai_groups:
            self.window.current_level.ai_groups.get(ai_group).trigger_threshold = threshold
        else:
            self.window.current_level.ai_groups.append(AIGroup(ai_group, threshold))
        self.current.ai_group = ai_group

    def roam_ai_changed(self, val):
        self.current.roam_ai = self.roam_ai_box.edit.currentText()

    def traveler_check(self, val):
        if bool(val):
            self.traveler_box.setEnabled(True)
            partners = valid_partners(self.window.current_level.units, self.current)
            idx = self.traveler_box.edit.currentIndex()
            text = partners[idx].nid
            self.current.starting_traveler = text
        else:
            self.traveler_box.setEnabled(False)
            self.current.starting_traveler = None

    def traveler_changed(self, idx):
        partners = valid_partners(self.window.current_level.units, self.current)
        text = partners[idx].nid
        self.current.starting_traveler = text

    # def check_color(self):
    #     # See which ones can actually be wielded
    #     color_list = []
    #     for item_nid, droppable in self.current.starting_items:
    #         item = DB.items.get(item_nid)
    #         if droppable:
    #             color_list.append(Qt.darkGreen)
    #         elif not can_wield(self.current, item, prefab=False):
    #             color_list.append(Qt.red)
    #         else:
    #             color_list.append(Qt.black)
    #     self.item_widget.set_color(color_list)

    def items_changed(self):
        self.current.starting_items = self.item_widget.get_items()
        # self.check_color()

    def skills_changed(self):
        self.current.starting_skills = self.skill_widget.get_skills()

    def display_averages(self):
        # Modeless dialog
        if not self.averages_dialog:
            self.averages_dialog = StatAverageDialog(
                self.current, "Generic", GenericStatAveragesModel, self)
        self.averages_dialog.show()
        self.averages_dialog.raise_()
        self.averages_dialog.activateWindow()

    def close_averages(self):
        if self.averages_dialog:
            self.averages_dialog.done(0)
            self.averages_dialog = None

    def set_current(self, current):
        self.current = current
        self.nid_box.edit.setText(current.nid)
        self.team_box.edit.setValue(current.team)
        self.level_box.edit.setValue(current.level)
        self.class_box.edit.setValue(current.klass)
        if current.variant:
            self.variant_box.edit.setText(current.variant)
        else:
            self.variant_box.edit.clear()
        self.faction_box.edit.setValue(current.faction)
        self.ai_box.edit.setValue(current.ai)
        self.roam_ai_box.edit.setValue(current.roam_ai)
        if current.ai_group:
            self.ai_group_box.edit.setValue(current.ai_group)
            ai_group = self.window.current_level.ai_groups.get(current.ai_group)
            self.ai_group_threshold_box.edit.setValue(ai_group.trigger_threshold)
        else:
            self.ai_group_box.edit.clearEditText()
            self.ai_group_threshold_box.edit.setValue(1)
        if current.starting_traveler:
            self.traveler_button.setChecked(True)
            self.traveler_box.edit.setValue(current.starting_traveler)
        else:
            self.traveler_button.setChecked(False)
            self.traveler_box.edit.clear()
        self.item_widget.set_current(current.starting_items)
        self.skill_widget.set_current(current.starting_skills)
        if self.averages_dialog:
            self.averages_dialog.set_current(current)

    @classmethod
    def get_unit(cls, parent, last_touched_generic=None, unit=None):
        dialog = cls(parent, last_touched_generic, unit)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            dialog.check_ai_group()
            unit = dialog.current
            return unit, True
        else:
            return None, False

    def hideEvent(self, event):
        self.close_averages()
