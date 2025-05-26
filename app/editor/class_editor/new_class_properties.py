from app.editor.lib.components.database_delegate import UnitFieldDelegate
from app.extensions.key_value_delegate import KeyValueDoubleListModel
from PyQt5.QtWidgets import QWidget, QGridLayout, QLineEdit, \
    QMessageBox, QSpinBox, QHBoxLayout, QPushButton, QDialog, QSplitter, \
    QVBoxLayout, QLabel, QTextEdit, QSizePolicy
from PyQt5.QtGui import QFontMetrics, QIcon
from PyQt5.QtCore import Qt

from app import dark_theme

from app.data.resources.resources import RESOURCES
from app.data.database.database import DB

from app.extensions.custom_gui import PropertyBox, ComboBox, QHLine
from app.extensions.list_widgets import AppendMultiListWidget, MultiDictWidget
from app.extensions.list_models import ReverseDoubleListModel
from app.extensions.multi_select_combo_box import MultiSelectComboBox

from app.editor.settings import MainSettingsController

from app.editor.tag_widget import TagDialog
from app.editor.stat_widget import StatListWidget, StatAverageDialog, ClassStatAveragesModel
from app.editor.weapon_editor.weapon_rank import WexpGainDelegate, WexpGainMultiAttrModel
from app.editor.learned_skill_delegate import LearnedSkillDelegate
from app.editor.icons import ItemIcon80, MapSpriteBox
from app.editor.lib.components.validated_line_edit import NidLineEdit
from app.editor.component_editor_properties import T

from app.editor.class_editor import class_model
from app.editor.map_sprite_editor import map_sprite_tab
from app.editor.combat_animation_editor import combat_animation_tab

from app.editor import timer

from app.utilities import str_utils
from app.utilities.typing import NID

from typing import (Callable, Optional)

class NewClassProperties(QWidget):
    title = "Class"

    def __init__(self, parent, current: Optional[T] = None,
                 attempt_change_nid: Optional[Callable[[NID, NID], bool]] = None,
                 on_icon_change: Optional[Callable] = None):
        super().__init__(parent)
        self.window = parent

        self.current: Optional[T] = current
        self.cached_nid: Optional[NID] = self.current.nid if self.current else None
        self.attempt_change_nid = attempt_change_nid
        self.on_icon_change = on_icon_change

        self.settings = MainSettingsController()
        theme = dark_theme.get_theme()
        icon_folder = theme.icon_dir()

        self.current = current

        top_section = QHBoxLayout()

        main_section = QGridLayout()

        self.icon_edit = ItemIcon80(self)
        main_section.addWidget(self.icon_edit, 0, 0, 2, 2, Qt.AlignHCenter)

        self.nid_box = PropertyBox(_("Unique ID"), NidLineEdit, self)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)
        main_section.addWidget(self.nid_box, 0, 2)

        self.name_box = PropertyBox(_("Display Name"), QLineEdit, self)

        self.name_box.edit.textChanged.connect(self.name_changed)
        main_section.addWidget(self.name_box, 1, 2)

        self.desc_box = PropertyBox(_("Description"), QTextEdit, self)
        self.desc_box.edit.textChanged.connect(self.desc_changed)
        font_height = QFontMetrics(self.desc_box.edit.font())
        self.desc_box.edit.setFixedHeight(font_height.lineSpacing() * 3 + 20)
        main_section.addWidget(self.desc_box, 2, 0, 1, 2)

        self.movement_box = PropertyBox(_("Movement Type"), ComboBox, self)
        self.movement_box.edit.addItems(DB.mcost.unit_types)
        self.movement_box.edit.currentIndexChanged.connect(self.movement_changed)
        main_section.addWidget(self.movement_box, 2, 2)

        self.tier_box = PropertyBox(_("Tier"), QSpinBox, self)
        self.tier_box.edit.setRange(0, 5)
        self.tier_box.edit.setAlignment(Qt.AlignRight)
        self.tier_box.edit.valueChanged.connect(self.tier_changed)
        main_section.addWidget(self.tier_box, 3, 0)

        self.promotes_from_box = PropertyBox(_("Promotes From"), ComboBox, self)
        self.promotes_from_box.edit.addItems([_("None")] + DB.classes.keys())
        self.promotes_from_box.edit.activated.connect(self.promotes_from_changed)
        main_section.addWidget(self.promotes_from_box, 3, 1)

        self.max_level_box = PropertyBox(_("Max Level"), QSpinBox, self)
        self.max_level_box.edit.setRange(1, 255)
        self.max_level_box.edit.setAlignment(Qt.AlignRight)
        self.max_level_box.edit.valueChanged.connect(self.max_level_changed)
        main_section.addWidget(self.max_level_box, 3, 2)

        tag_section = QHBoxLayout()

        self.turns_into_box = PropertyBox(_("Turns Into"), MultiSelectComboBox, self)
        self.turns_into_box.edit.setPlaceholderText(_("Promotion Options..."))
        self.turns_into_box.edit.addItems(DB.classes.keys())
        self.turns_into_box.edit.updated.connect(self.turns_into_changed)
        tag_section.addWidget(self.turns_into_box)

        self.tag_box = PropertyBox(_("Tags"), MultiSelectComboBox, self)
        self.tag_box.edit.setPlaceholderText(_("No tag"))
        self.tag_box.edit.addItems(DB.tags.keys())
        self.tag_box.edit.updated.connect(self.tags_changed)
        tag_section.addWidget(self.tag_box)

        self.tag_box.add_button(QPushButton('...'))
        self.tag_box.button.setMaximumWidth(40)
        self.tag_box.button.clicked.connect(self.access_tags)

        stat_section = QGridLayout()

        self.class_stat_widget = StatListWidget(self.current, _("Stats"), parent=self)
        self.class_stat_widget.button.clicked.connect(self.display_averages)
        self.class_stat_widget.model.dataChanged.connect(self.stat_list_model_data_changed)
        self.averages_dialog = None
        stat_section.addWidget(self.class_stat_widget, 1, 0, 1, 2)

        weapon_section = QHBoxLayout()

        attrs = ("usable", "nid", "wexp_gain", "cap")
        default_weapons = {weapon_nid: DB.weapons.default(DB) for weapon_nid in DB.weapons.keys()}
        self.wexp_gain_widget = MultiDictWidget(
            default_weapons, "Weapon Experience",
            attrs, WexpGainDelegate, self, model=WexpGainMultiAttrModel)
        self.wexp_gain_widget.model.checked_columns = {0}  # Add checked column
        weapon_section.addWidget(self.wexp_gain_widget)

        skill_section = QHBoxLayout()
        attrs = ("level", "skill_nid")
        self.class_skill_widget = AppendMultiListWidget([], _("Class Skills"), attrs, LearnedSkillDelegate, self, model=ReverseDoubleListModel)
        skill_section.addWidget(self.class_skill_widget)

        field_section = QHBoxLayout()
        attrs = ("field", "value")
        self.field_widget = AppendMultiListWidget([], "Class Fields", attrs, UnitFieldDelegate, self, model=KeyValueDoubleListModel)
        field_section.addWidget(self.field_widget)

        self.map_sprite_box = MapSpriteBox()
        self.map_sprite_box.sourceChanged.connect(self.select_map_sprite)

        self.combat_anim_label = QLabel()
        self.combat_anim_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.combat_anim_box = QPushButton(_("Choose Combat Animation..."))
        self.combat_anim_box.clicked.connect(self.select_combat_anim)
        self.combat_anim_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.combat_anim_auto_box = QPushButton()
        self.combat_anim_auto_box.setIcon(QIcon(f"{icon_folder}/autoassign.png"))
        self.combat_anim_auto_box.setMaximumWidth(32)
        self.combat_anim_auto_box.setToolTip(_("Auto-assign combat animation with the same unique ID"))
        self.combat_anim_auto_box.clicked.connect(self.autoselect_combat_anim)
        self.combat_anim_auto_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        total_section = QVBoxLayout()
        total_section.addLayout(top_section)
        total_section.addLayout(main_section)
        total_section.addLayout(tag_section)
        total_section.addWidget(QHLine())
        total_section.addLayout(stat_section)
        total_widget = QWidget()
        total_widget.setLayout(total_section)

        right_section = QVBoxLayout()
        right_section.addLayout(weapon_section)
        right_section.addWidget(QHLine())
        right_section.addLayout(skill_section)
        right_section.addLayout(field_section)
        right_section.addWidget(self.map_sprite_box)

        combat_anim_section = QHBoxLayout()
        combat_anim_section.addWidget(self.combat_anim_label)
        combat_anim_section.addWidget(self.combat_anim_box)
        combat_anim_section.addWidget(self.combat_anim_auto_box)
        right_section.addLayout(combat_anim_section)
        right_widget = QWidget()
        right_widget.setLayout(right_section)

        self.splitter = QSplitter(self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(total_widget)
        self.splitter.addWidget(right_widget)
        self.splitter.setStyleSheet("QSplitter::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eee, stop:1 #ccc); border: 1px solid #777; width: 13px; margin-top: 2px; margin-bottom: 2px; border-radius: 4px;}")

        final_section = QHBoxLayout()
        self.setLayout(final_section)
        final_section.addWidget(self.splitter)

        self.set_current(self.current)

        # final_section = QHBoxLayout()
        # self.setLayout(final_section)
        # final_section.addLayout(total_section)
        # final_section.addWidget(QVLine())
        # final_section.addLayout(right_section)

        timer.get_timer().tick_elapsed.connect(self.tick)

    def tick(self):
        self.on_icon_change()

    def on_icon_changed(self, nid):
        if self.current:
            self.current.icon_nid = nid
            if self.on_icon_change:
                self.on_icon_change()

    def nid_changed(self, text):
        if self.current:
            # Also change name if they are identical
            if self.current.name == self.current.nid.replace('_', ' '):
                self.name_box.edit.setText(text.replace('_', ' '))
            self.current.nid = text

    def nid_done_editing(self):
        if self.current and self.cached_nid:
            self.nid_box.edit.blockSignals(True)  # message box causes focus loss which double triggers nid_done_editing
            # Check validity of nid!
            if self.attempt_change_nid and self.attempt_change_nid(self.cached_nid, self.current.nid):
                self.cached_nid = self.current.nid
            else:
                self.current.nid = self.cached_nid
                self.nid_box.edit.setText(self.cached_nid)
            self.nid_box.edit.blockSignals(False)

    def name_changed(self, text):
        self.current.name = text

    def desc_changed(self, text=None):
        self.current.desc = self.desc_box.edit.toPlainText()
        # self.current.desc = text

    def tier_changed(self, val):
        self.current.tier = val

    def promotes_from_changed(self):
        p = self.promotes_from_box.edit.currentText()
        if p == "None":
            self.current.promotes_from = None
        else:
            self.current.promotes_from = p

    def movement_changed(self, index):
        self.current.movement_group = self.movement_box.edit.currentText()

    def max_level_changed(self, val):
        self.current.max_level = val

    def turns_into_changed(self):
        self.current.turns_into = self.turns_into_box.edit.currentText()

    def tags_changed(self):
        self.current.tags = self.tag_box.edit.currentText()

    def access_tags(self):
        dlg = TagDialog.create(self)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            self.tag_box.edit.clear()
            self.tag_box.edit.addItems(DB.tags.keys())
            self.tag_box.edit.setCurrentTexts(self.current.tags)
        else:
            pass

    # def access_stats(self):
    #     dlg = StatTypeDialog.create()
    #     result = dlg.exec_()
    #     if result == QDialog.Accepted:
    #         self.class_stat_widget.update_stats()
    #     else:
    #         pass

    def display_averages(self):
        if not self.current:
            return
        # Modeless dialog
        if not self.averages_dialog:
            self.averages_dialog = StatAverageDialog(self.current, "Class", ClassStatAveragesModel, self)
        self.averages_dialog.show()
        self.averages_dialog.raise_()
        self.averages_dialog.activateWindow()

    def close_averages(self):
        if self.averages_dialog:
            self.averages_dialog.done(0)
            self.averages_dialog = None

    def stat_list_model_data_changed(self, index1, index2):
        if self.averages_dialog:
            self.averages_dialog.update()

    def select_map_sprite(self, nid):
        self.current.map_sprite_nid = nid
        self.on_icon_change()

    def select_combat_anim(self):
        res, ok = combat_animation_tab.get_animations()
        if res and ok:
            nid = res.nid
            self.current.combat_anim_nid = nid
            pix = class_model.get_combat_anim_icon(self.current)
            if pix:
                self.combat_anim_label.setPixmap(pix)
        else:  # Use to clear the combat animation -- since this can be reasonable
            self.current.combat_anim_nid = None
            self.combat_anim_label.clear()

    def autoselect_combat_anim(self):
        nid = self.current.nid
        res = RESOURCES.combat_anims.get(nid)
        if res:
            nid = res.nid
            self.current.combat_anim_nid = nid
            pix = class_model.get_combat_anim_icon(self.current)
            if pix:
                self.combat_anim_label.setPixmap(pix)

    def set_current(self, current):
        if not current:
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            self.current = current
            self.cached_nid = current.nid
            self.nid_box.edit.setText(current.nid)
            self.name_box.edit.setText(current.name)
            self.desc_box.edit.setText(current.desc)
            self.tier_box.edit.setValue(current.tier)
            self.max_level_box.edit.setValue(current.max_level)
            self.movement_box.edit.setValue(current.movement_group)
            # Reset promotes from box
            self.promotes_from_box.edit.clear()
            self.promotes_from_box.edit.addItems(["None"] + DB.classes.keys())
            if current.promotes_from:
                self.promotes_from_box.edit.setValue(current.promotes_from)
            else:
                self.promotes_from_box.edit.setValue("None")
            # Need to make copies because otherwise ResetSelection calls
            # self.tag_box.updated which resets the current.tags
            turns_into = current.turns_into[:]
            tags = current.tags[:]
            self.turns_into_box.edit.clear()
            self.turns_into_box.edit.addItems(DB.classes.keys())
            self.turns_into_box.edit.setCurrentTexts(turns_into)
            self.tag_box.edit.clear()
            self.tag_box.edit.addItems(DB.tags.keys())
            self.tag_box.edit.setCurrentTexts(tags)

            self.class_stat_widget.update_stats()
            self.class_stat_widget.set_new_obj(current)
            if self.averages_dialog:
                self.averages_dialog.set_current(current)

            self.class_skill_widget.set_current(current.learned_skills)
            default_weapons = {weapon_nid: DB.weapons.default(DB) for weapon_nid in DB.weapons.keys()}
            default_weapons.update(current.wexp_gain)
            current.wexp_gain = default_weapons
            self.wexp_gain_widget.set_current(current.wexp_gain)
            self.field_widget.set_current(current.fields)

            self.icon_edit.set_current(current.icon_nid, current.icon_index)
            self.map_sprite_box.set_current(current, current.map_sprite_nid)
            pix = class_model.get_combat_anim_icon(self.current)
            if pix:
                self.combat_anim_label.setPixmap(pix)
            else:
                self.combat_anim_label.clear()

    def hideEvent(self, event):
        self.close_averages()
