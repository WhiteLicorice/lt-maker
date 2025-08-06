from app.editor.lib.components.validated_line_edit import NidLineEdit
from functools import partial

from app.data.database.database import DB
from app.editor import timer
from app.editor.custom_widgets import PartyBox, UnitBox
from app.editor.sound_editor import sound_tab
from app.editor.tag_widget import TagDialog
from app.editor.tile_editor import tile_tab
from app.editor.unit_editor import new_unit_tab
from app.extensions.custom_gui import (PropertyBox, PropertyCheckBox, QHLine,
                                       SimpleDialog)
from app.extensions.multi_select_combo_box import MultiSelectComboBox
from app.utilities import str_utils
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QCheckBox, QLabel, QLineEdit, QMessageBox,
                             QPushButton, QVBoxLayout, QWidget, QDialog)


class MusicDialog(SimpleDialog):
    def __init__(self, current):
        super().__init__()
        self.setWindowTitle("Level Music")
        self.current = current

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.boxes = {}
        for key in DB.music_keys:
            title = key.replace('_', ' ').title()
            box = PropertyBox(title, QLineEdit, self)
            box.edit.setReadOnly(True)
            box.add_button(QPushButton('...'))
            box.button.setMaximumWidth(40)
            box.button.clicked.connect(
                partial(self.access_music_resources, key))
            box.delete_button = QPushButton('X')
            box.bottom_section.addWidget(box.delete_button)
            box.delete_button.setMaximumWidth(30)
            box.delete_button.clicked.connect(
                partial(self.delete_music_resource, key))

            layout.addWidget(box)
            self.boxes[key] = box

        self.set_current(self.current)
        self.setMinimumWidth(300)

    def set_current(self, current):
        self.current = current
        for key, value in self.current.music.items():
            if key in self.boxes and value:
                self.boxes[key].edit.setText(value)

    def access_music_resources(self, key):
        res, ok = sound_tab.get_music()
        if ok and res:
            nid = res[0].nid
            self.current.music[key] = nid
            self.boxes[key].edit.setText(nid)

    def delete_music_resource(self, key):
        self.current.music[key] = None
        self.boxes[key].edit.setText('')

class PropertiesMenu(QWidget):
    def __init__(self, state_manager):
        super().__init__()

        self.state_manager = state_manager

        self.setStyleSheet("font: 10pt;")

        form = QVBoxLayout(self)
        form.setAlignment(Qt.AlignTop)

        self.nid_box = PropertyBox("Level ID", NidLineEdit, self)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)
        form.addWidget(self.nid_box)

        self.title_box = PropertyBox("Level Title", QLineEdit, self)
        self.title_box.edit.textChanged.connect(self.title_changed)
        form.addWidget(self.title_box)

        # Records
        self.record_box = PropertyCheckBox("Display in Records?", QCheckBox, self)
        self.record_box.setToolTip("You might want to turn this off if this level is not a main story level that should be viewed in the Records screen.")
        self.record_box.edit.setChecked(True)
        self.record_box.edit.stateChanged.connect(self.record_changed)
        form.addWidget(self.record_box)

        self.party_box = PartyBox(self)
        self.party_box.edit.activated.connect(self.party_changed)
        form.addWidget(self.party_box)

        self.music_button = QPushButton("Edit Level's Music...", self)
        self.music_button.clicked.connect(self.edit_music)
        form.addWidget(self.music_button)

        self.currently_playing = None
        self.currently_playing_label = QLabel("")
        form.addWidget(self.currently_playing_label)

        form.addWidget(QHLine())

        self.quick_display = PropertyBox("Objective Display", QLineEdit, self)
        self.quick_display.edit.editingFinished.connect(
            lambda: self.set_objective('simple'))
        form.addWidget(self.quick_display)

        self.win_condition = PropertyBox("Win Condition", QLineEdit, self)
        self.win_condition.edit.editingFinished.connect(
            lambda: self.set_objective('win'))
        form.addWidget(self.win_condition)

        self.loss_condition = PropertyBox("Loss Condition", QLineEdit, self)
        self.loss_condition.edit.editingFinished.connect(
            lambda: self.set_objective('loss'))
        form.addWidget(self.loss_condition)

        form.addWidget(QHLine())

        self.map_box = QPushButton("Select Tilemap...")
        self.map_box.clicked.connect(self.select_tilemap)
        form.addWidget(self.map_box)

        self.bg_box = QPushButton("Select background tilemap...")
        self.bg_box.clicked.connect(self.select_bg_tilemap)
        form.addWidget(self.bg_box)

        # overworld stuff
        self.overworld_box = PropertyCheckBox("Go to overworld after?", QCheckBox, self)
        self.overworld_box.edit.stateChanged.connect(self.overworld_box_changed)
        form.addWidget(self.overworld_box)
        self.overworld_box.hide()

        # Tag stuff
        self.tag_box = PropertyBox(_("Level Tags"), MultiSelectComboBox, self)
        self.tag_box.edit.setPlaceholderText(_("No tag"))
        self.tag_box.edit.addItems(DB.tags.keys())
        self.tag_box.edit.updated.connect(self.tags_changed)
        form.addWidget(self.tag_box)

        self.tag_box.add_button(QPushButton('...'))
        self.tag_box.button.setMaximumWidth(40)
        self.tag_box.button.clicked.connect(self.access_tags)

        # Free roam stuff
        self.free_roam_box = PropertyCheckBox("Free Roam?", QCheckBox, self)
        self.free_roam_box.edit.stateChanged.connect(self.free_roam_changed)
        form.addWidget(self.free_roam_box)

        self.unit_box = UnitBox(self, button=True, title="Roaming Unit")
        self.unit_box.edit.activated.connect(self.unit_changed)
        self.unit_box.button.clicked.connect(self.access_units)
        form.addWidget(self.unit_box)

        self.set_current(self.state_manager.state.selected_level)
        self.state_manager.subscribe_to_key(
            PropertiesMenu.__name__, 'selected_level', self.set_current)

        timer.get_timer().tick_elapsed.connect(self.tick)

    def tick(self):
        if DB.constants.value('overworld'):
            self.overworld_box.show()
        else:
            self.overworld_box.hide()
        self.party_box.model.layoutChanged.emit()

    def set_current(self, level_nid):
        self.current = DB.levels.get(level_nid)
        current = self.current
        if not current:
            return
        self.title_box.edit.setText(current.name)
        self.nid_box.edit.setText(current.nid)
        self.record_box.edit.setChecked(bool(current.should_record))
        if current.party in DB.parties:
            idx = DB.parties.index(current.party)
            self.party_box.edit.setCurrentIndex(idx)
            self.party_changed()
        else:
            self.party_box.edit.setCurrentIndex(0)
            self.party_changed()

        tags = current.tags.copy()
        self.tag_box.edit.clear()
        self.tag_box.edit.addItems(DB.tags.keys())
        self.tag_box.edit.setCurrentTexts(tags)

        # Handle roaming
        if DB.units:
            self.unit_box.model._data = DB.units
            self.unit_box.model.layoutChanged.emit()
        if current.roam_unit:
            self.unit_box.edit.setValue(current.roam_unit)
        elif DB.units:
            self.unit_box.edit.setValue(DB.units[0].nid)
        self.free_roam_box.edit.setChecked(bool(current.roam))
        if bool(current.roam):
            self.unit_box.show()
        else:
            self.unit_box.hide()

        self.quick_display.edit.setText(current.objective['simple'])
        self.win_condition.edit.setText(current.objective['win'])
        self.loss_condition.edit.setText(current.objective['loss'])
        self.overworld_box.edit.setChecked(bool(current.go_to_overworld))

    def nid_changed(self, text):
        self.current.nid = text
        self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def nid_done_editing(self):
        other_nids = [
            level.nid for level in DB.levels if level is not self.current]
        if self.current.nid in other_nids:
            QMessageBox.warning(
                self, 'Warning', 'Level ID %s already in use' % self.current.nid)
            self.current.nid = str_utils.get_next_int(
                self.current.nid, other_nids)
        self.on_nid_changed(DB.levels.find_key(
            self.current), self.current.nid)
        DB.levels.update_nid(self.current, self.current.nid)
        self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def on_nid_changed(self, old_nid, new_nid):
        for event in DB.events:
            if event.level_nid == old_nid:
                event.level_nid = new_nid

    def title_changed(self, text):
        self.current.name = text
        self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def record_changed(self, state):
        self.current.should_record = bool(state)

    def party_changed(self):
        idx = self.party_box.edit.currentIndex()
        if idx >= 0:
            party = DB.parties[idx]
            self.current.party = party.nid

    def edit_music(self):
        dlg = MusicDialog(self.current)
        dlg.exec_()

    def set_objective(self, key):
        if key == 'simple':
            self.current.objective[key] = self.quick_display.edit.text()
        elif key == 'win':
            self.current.objective[key] = self.win_condition.edit.text()
        elif key == 'loss':
            self.current.objective[key] = self.loss_condition.edit.text()

    def check_positions(self, tilemap):
        # Tilemap is the tilemap itself, not a nid
        # Reset the positions of units who are now off the side of the map
        for unit in self.current.units:
            if unit.starting_position:
                if unit.starting_position[0] >= tilemap.width or unit.starting_position[1] >= tilemap.height:
                    unit.starting_position = None
        # Reset any illegal positions for groups
        for group in self.current.unit_groups:
            group.positions = {k: v for k, v in group.positions.items() if v[0] < tilemap.width and v[1] < tilemap.height}

    def select_tilemap(self):
        res, ok = tile_tab.get_tilemaps()
        if ok and res:
            nid = res.nid
            self.current.tilemap = nid
            self.check_positions(res)
            self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def select_bg_tilemap(self):
        res, ok = tile_tab.get_tilemaps()
        if ok and res:
            nid = res.nid
            self.current.bg_tilemap = nid
            self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def access_units(self):
        unit, ok = new_unit_tab.get(self.current.roam_unit)
        if unit and ok:
            self.current.roam_unit = unit.nid
            self.unit_box.edit.setValue(self.current.roam_unit)

    def free_roam_changed(self, state):
        self.current.roam = bool(state)
        if self.current.roam:
            self.unit_box.show()
            self.current.roam_unit = self.unit_box.edit.currentText()
            # self.unit_changed() - This line seems only to cause issues due to it reseting the roam_unit in line 265. Functionality appears to work correctly with it removed
        else:
            self.unit_box.hide()

    def overworld_box_changed(self, state):
        self.current.go_to_overworld = bool(state)

    def unit_changed(self):
        self.current.roam_unit = self.unit_box.edit.currentText()
        self.unit_box.edit.setValue(self.current.roam_unit)

    def access_tags(self):
        dlg = TagDialog.create(self)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            self.tag_box.edit.clear()
            self.tag_box.edit.addItems(DB.tags.keys())
            self.tag_box.edit.setCurrentTexts(self.current.tags)
        else:
            pass

    def tags_changed(self):
        self.current.tags = self.tag_box.edit.currentText()
