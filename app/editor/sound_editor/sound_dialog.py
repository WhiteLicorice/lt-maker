from app.editor.lib.components.validated_line_edit import NidLineEdit
import os

from PyQt5.QtWidgets import QLineEdit, QMessageBox, QVBoxLayout, \
    QFileDialog, QPushButton, QSpinBox

from app.utilities import str_utils
from app.extensions.custom_gui import ComboBox, PropertyBox, Dialog
from app.editor.settings import MainSettingsController

class ModifySFXDialog(Dialog):
    def __init__(self, data, current, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modify SFX")
        self.window = parent
        self._data = data
        self.current = current

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.nid_box = PropertyBox("Name", NidLineEdit, self)
        layout.addWidget(self.nid_box)

        if len(self.current) > 1:
            self.nid_box.edit.setText("Multiple SFX")
            self.nid_box.setEnabled(False)
        else:
            self.nid_box.edit.setText(self.current[0].nid)
            self.nid_box.edit.textChanged.connect(self.nid_changed)
            self.nid_box.edit.editingFinished.connect(self.nid_done_editing)

        self.tag_box = PropertyBox("Tag", QLineEdit, self)
        tags = [d.tag for d in self.current]
        if len(tags) > 1:
            self.tag_box.edit.setText("Multiple Tags")
        else:
            self.tag_box.edit.setText(self.current[0].tag)
        self.tag_box.edit.textChanged.connect(self.tag_changed)
        layout.addWidget(self.tag_box)

        layout.addWidget(self.buttonbox)

    def nid_changed(self, text):
        for d in self.current:
            d.nid = text

    def nid_done_editing(self):
        current = self.current[0]
        # Check validity of nid!
        other_nids = [d.nid for d in self._data.values() if d is not current]
        if current.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning', 'SFX ID %s already in use' % current.nid)
            current.nid = str_utils.get_next_name(current.nid, other_nids)
        self._data.update_nid(current, current.nid)

    def tag_changed(self, text):
        for d in self.current:
            d.tag = text

class ModifyMusicDialog(Dialog):
    """
    Does not allow multi-select
    """
    def __init__(self, data, current, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modify Song")
        self.window = parent
        self._data = data
        self.current = current[0]

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.nid_box = PropertyBox("Name", NidLineEdit, self)
        layout.addWidget(self.nid_box)

        self.nid_box.edit.setText(self.current.nid)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)

        self.choice_box = ComboBox()
        self.choice_box.addItems(["No Variant", "Battle", "Intro"])
        self.choice_box.activated.connect(self.on_choice)

        self.battle_box = PropertyBox("Battle Variant", QLineEdit, self,)
        self.battle_box.edit.setReadOnly(True)
        self.battle_box.edit.setPlaceholderText("No Battle Variant")
        battle_button = QPushButton("...")
        battle_button.setMaximumWidth(40)
        battle_button.clicked.connect(self.load_battle_variant)
        self.battle_box.add_button(battle_button)

        self.intro_box = PropertyBox("Intro Section", QLineEdit, self,)
        self.intro_box.edit.setReadOnly(True)
        self.intro_box.edit.setPlaceholderText("No Intro Section")
        intro_button = QPushButton("...")
        intro_button.setMaximumWidth(40)
        intro_button.clicked.connect(self.load_intro_variant)
        self.intro_box.add_button(intro_button)

        self.battle_box.hide()
        self.intro_box.hide()

        if self.current.battle_full_path:
            self.choice_box.setValue("Battle")
            print(self.current.battle_full_path, flush=True)
            name = os.path.split(self.current.battle_full_path[:-4])[-1]
            self.battle_box.edit.setText("%s" % name)
            self.battle_box.show()
        elif self.current.intro_full_path:
            self.choice_box.setValue("Intro")
            print(self.current.intro_full_path, flush=True)
            name = os.path.split(self.current.intro_full_path[:-4])[-1]
            self.intro_box.edit.setText("%s" % name)
            self.intro_box.show()
        else:
            self.choice_box.setValue("No Variant")

        layout.addWidget(self.choice_box)
        layout.addWidget(self.battle_box)
        layout.addWidget(self.intro_box)

        self.soundroom_box = PropertyBox("Sound Room Number", QSpinBox, self)
        self.soundroom_box.edit.setValue(self.current.soundroom_idx)
        self.soundroom_box.edit.valueChanged.connect(self.soundroom_idx_changed)
        layout.addWidget(self.soundroom_box)
        
        self.display_name_box = PropertyBox("Display Name", QLineEdit, self)
        layout.addWidget(self.display_name_box)

        self.display_name_box.edit.setText(self.current.display_name)
        self.display_name_box.edit.textChanged.connect(self.display_name_changed)

        layout.addWidget(self.buttonbox)

    def on_choice(self):
        choice = self.choice_box.currentText()
        if choice == 'No Variant':
            self.battle_box.hide()
            self.intro_box.hide()
            self.battle_box.edit.setText("")
            self.intro_box.edit.setText("")
            self.current.battle_full_path = None
            self.current.intro_full_path = None
        elif choice == 'Battle':
            self.battle_box.show()
            self.intro_box.hide()
            self.intro_box.edit.setText("")
            self.current.intro_full_path = None
        elif choice == 'Intro':
            self.battle_box.hide()
            self.intro_box.show()
            self.battle_box.edit.setText("")
            self.current.battle_full_path = None

    def nid_changed(self, text):
        self.current.nid = text

    def nid_done_editing(self):
        current = self.current
        # Check validity of nid!
        other_nids = [d.nid for d in self._data.values() if d is not current]
        if current.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning', 'SFX ID %s already in use' % current.nid)
            current.nid = str_utils.get_next_name(current.nid, other_nids)
        self._data.update_nid(current, current.nid)

    def load_battle_variant(self):
        settings = MainSettingsController()
        starting_path = settings.get_last_open_path()
        fn, ok = QFileDialog.getOpenFileName(self.window, "Select Music File", starting_path, "OGG Files (*.ogg);;All FIles (*)")
        if ok:
            if fn.endswith('.ogg'):
                self.current.set_battle_full_path(fn)
                name = os.path.split(fn[:-4])[-1]
                self.battle_box.edit.setText("%s" % name)
                print(self.current.battle_full_path)
            else:
                QMessageBox.critical(self.window, "File Type Error!", "Music must be in OGG format!")
            parent_dir = os.path.split(fn)[0]
            settings.set_last_open_path(parent_dir)

    def load_intro_variant(self):
        settings = MainSettingsController()
        starting_path = settings.get_last_open_path()
        fn, ok = QFileDialog.getOpenFileName(self.window, "Select Music File", starting_path, "OGG Files (*.ogg);;All FIles (*)")
        if ok:
            if fn.endswith('.ogg'):
                self.current.set_intro_full_path(fn)
                name = os.path.split(fn[:-4])[-1]
                self.intro_box.edit.setText("%s" % name)
                print(self.current.intro_full_path)
            else:
                QMessageBox.critical(self.window, "File Type Error!", "Music must be in OGG format!")
            parent_dir = os.path.split(fn)[0]
            settings.set_last_open_path(parent_dir)

    def soundroom_idx_changed(self, text):
        # Sound room index can be consecutive unique positive int, or 0.
        # Example: 0, 0, 0, 0, 1, 2, 3, 4.
        # Setting a song to #0 will hide the song from the sound room.

        old_idx = self.current.soundroom_idx
        new_idx = self.soundroom_box.edit.value()
        if old_idx == new_idx:
            return

        sorted_db = sorted(self._data, key=lambda x: x.soundroom_idx)
        max_idx = sorted_db[-1].soundroom_idx
        if max_idx == 0:    # All songs are hidden
            self.current.soundroom_idx = 1
            return

        soundroom = sorted_db[-max_idx:]    # Filter out hidden songs

        # If we move a hidden song to slot #2, songs from #2 onwards have to be shifted up
        if old_idx == 0:
            for song_prefab in soundroom[new_idx-1:]:
                song_prefab.soundroom_idx += 1

            self.current.soundroom_idx = min(new_idx, max_idx + 1)
            return

        # If we hide song #3, songs from #4 onwards have to be shifted down
        if new_idx == 0:
            for song_prefab in soundroom[old_idx:]:
                song_prefab.soundroom_idx -= 1

        # If we move song #3 to slot #1, songs #1 and #2 have to be shifted up
        elif new_idx < old_idx:
            for song_prefab in soundroom[new_idx-1:old_idx-1]:
                song_prefab.soundroom_idx += 1

        # If we move song #1 to slot #3, songs #2 and #3 have to be shifted down
        else:
            for song_prefab in soundroom[old_idx:new_idx]:
                song_prefab.soundroom_idx -= 1

        self.current.soundroom_idx = min(new_idx, max_idx)
        
    def display_name_changed(self, text):
        self.current.display_name = text
