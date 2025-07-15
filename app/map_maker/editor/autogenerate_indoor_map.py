from typing import Any, Dict, Tuple

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QDoubleSpinBox, \
    QDialog, QGroupBox, QFormLayout, QSpinBox, \
    QCheckBox, QVBoxLayout, QLabel, QWidget, \
    QPushButton, QHBoxLayout, QMessageBox, QScrollArea

from app.utilities.typing import NID

from app.extensions.custom_gui import ComboBox, QHLine, PropertyBox
from app.editor.settings import MainSettingsController


from .map_terrain_model import MapTerrainModel
from app.map_maker.terrain import Terrain

from app.dungeon_maker import themes
from app.dungeon_maker import terrain_generation

class AutogenerateIndoorMap(QDialog):
    def __init__(self, current: Dict[NID, Any], parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.window = parent
        self.setWindowTitle("Autogenerate Indoor Map")

        self.tilemap = parent.current

        self.settings = MainSettingsController()

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.current: Dict[NID, Any] = current  # Set of custom theme parameters

        self.previous_theme = self.settings.component_controller.get_state(self.__class__.__name__)
        if self.previous_theme:
            self.previous_theme['floor_lower'] = Terrain((self.previous_theme['floor_lower'], False))
            self.previous_theme['floor_upper'] = Terrain((self.previous_theme['floor_upper'], False))

        self.theme_preset_combobox = ComboBox(self)
        self.theme_presets = list(themes.theme_presets.keys())
        self.theme_preset_combobox.addItems(self.theme_presets)
        self.theme_preset_combobox.currentIndexChanged.connect(self.theme_preset_changed)
        self.layout.addWidget(self.theme_preset_combobox)

        h_line = QHLine()
        self.layout.addWidget(h_line)

        form_widget = QWidget(self)
        form_layout = QFormLayout(form_widget)
        form_widget.setLayout(form_layout)

        scroll_area = QScrollArea(self)
        scroll_area.setWidget(form_widget)
        scroll_area.setWidgetResizable(True)
        self.layout.addWidget(scroll_area)
        self.setMaximumWidth(350)
        self.resize(350, 800)

        self.boxes = {}
        for theme_parameter in themes.theme_parameters:
            if theme_parameter._type == Tuple[int, int]:
                editor, x_widget, y_widget = self._create_2d_editor(theme_parameter.name, theme_parameter.value)
                self.boxes[theme_parameter.nid] = (x_widget, y_widget)
            elif theme_parameter._type == float:
                editor = QDoubleSpinBox(self)
                editor.setAlignment(Qt.AlignRight)
                editor.setRange(0, 100)
                editor.setDecimals(1)
                editor.setSingleStep(5)
                editor.setSuffix(" %")
                editor.setValue(theme_parameter.value * 100)
                self.boxes[theme_parameter.nid] = editor
            elif theme_parameter._type == int:
                editor = QSpinBox(self)
                editor.setAlignment(Qt.AlignRight)
                editor.setRange(0, 999)
                editor.setValue(theme_parameter.value)
                self.boxes[theme_parameter.nid] = editor
            elif theme_parameter._type == bool:
                editor = QCheckBox(self)
                editor.setStyleSheet("margin-left:50%; margin-right:50%;")
                editor.setChecked(bool(theme_parameter.value))
                self.boxes[theme_parameter.nid] = editor
            elif theme_parameter._type == Terrain:
                editor = ComboBox(self)
                model = MapTerrainModel(Terrain.get_all_floor(), self)
                editor.setModel(model)
                editor.setIconSize(QSize(32, 32))
                idx = Terrain.get_all_floor().index(theme_parameter.value)
                editor.setCurrentIndex(idx)
                self.boxes[theme_parameter.nid] = editor

            editor.setToolTip(theme_parameter.desc)
            name_label = QLabel(theme_parameter.name)
            name_label.setToolTip(theme_parameter.desc)
            form_layout.addRow(name_label, editor)

        generate_layout = QHBoxLayout()
        generate_button = QPushButton("Generate")
        generate_button.clicked.connect(self.generate)
        self.random_seed_box = PropertyBox("Seed", QSpinBox, self)
        self.random_seed_box.edit.setRange(-1, 1023)
        self.random_seed_box.edit.setValue(0)
        self.random_seed_box.setMaximumWidth(60)
        self.random_seed_box.edit.setAlignment(Qt.AlignRight)
        self.random_seed_box.setToolTip("Seed utilized to generate a unique map. Set to -1 for a random seed each time.")
        generate_layout.addWidget(generate_button)
        generate_layout.addWidget(self.random_seed_box)
        self.layout.addLayout(generate_layout)

        if self.previous_theme:
            self.theme_presets.append("Previous")
            self.theme_preset_combobox.addItem("Previous")
            self.theme_preset_combobox.setValue("Previous")

    def _create_2d_editor(self, title: str, value: Tuple[int, int]):
        size_section = QGroupBox(self)
        size_layout = QFormLayout()
        x_box = QSpinBox()
        x_box.setAlignment(Qt.AlignRight)
        x_box.setMaximumWidth(60)
        x_box.setValue(value[0])
        x_box.setRange(1, 255)
        size_layout.addRow("X:", x_box)
        y_box = QSpinBox()
        y_box.setAlignment(Qt.AlignRight)
        y_box.setMaximumWidth(60)
        y_box.setValue(value[1])
        y_box.setRange(1, 255)
        size_layout.addRow("Y:", y_box)
        size_section.setLayout(size_layout)
        return (size_section, x_box, y_box)

    def theme_preset_changed(self, idx: int):
        """
        Called when the user selects a new theme preset
        Overwrites the current value of every selection made so far
        """
        chosen_preset_nid = self.theme_presets[idx]
        if chosen_preset_nid == "Previous":
            chosen_preset = self.previous_theme
        else:
            chosen_preset = themes.get_theme(chosen_preset_nid)
            
        for nid, value in chosen_preset.items():
            editor = self.boxes[nid]
            if isinstance(editor, tuple):
                x_editor, y_editor = editor
                x_editor.setValue(value[0])
                y_editor.setValue(value[1])
            elif isinstance(editor, QCheckBox):
                editor.setChecked(bool(value))
            elif isinstance(editor, QDoubleSpinBox):
                editor.setValue(value * 100)
            elif isinstance(editor, ComboBox):
                idx = Terrain.get_all_floor().index(value)
                editor.setCurrentIndex(idx)
            else:
                editor.setValue(value)

    def get_parameters(self) -> Dict[NID, Any]:
        """
        Get the current set of parameters the user has chosen
        using this dialog
        """
        theme_parameters = {}
        for nid, editor in self.boxes.items():
            if isinstance(editor, tuple):
                x_editor, y_editor = editor
                x = x_editor.value()
                y = y_editor.value()
                value = (x, y)
            elif isinstance(editor, QCheckBox):
                value = bool(editor.isChecked())
            elif isinstance(editor, QDoubleSpinBox):
                value = editor.value() / 100.0
            elif isinstance(editor, QSpinBox):
                value = editor.value()
            elif isinstance(editor, ComboBox):
                idx = editor.currentIndex()
                value = Terrain.get_all_floor()[idx]
            else:
                value = editor.getValue()
            theme_parameters[nid] = value
        return theme_parameters

    def generate(self):
        theme = self.get_parameters()
        dungeon_tilemap = terrain_generation.generate_terrain(theme, self.random_seed_box.edit.value())
        if dungeon_tilemap:
            # Update the current with the dungeon tilemap values
            self.tilemap.set_new_terrain_grid(
                (dungeon_tilemap.width, dungeon_tilemap.height), dungeon_tilemap.terrain_grid)
        else:
            QMessageBox.information(self, "Map Generation Failed", "Unable to generate a map. Check your connectivity rules!")

    @classmethod
    def customize(cls, parent=None):
        default_theme_parameters = themes.get_default_theme()
        dialog = cls(default_theme_parameters, parent)
        dialog.show()
        dialog.raise_()
        # dialog.exec_()
        # Set previous

    def closeEvent(self, event):
        super().closeEvent(event)
        current_theme = self.get_parameters()
        current_theme['floor_lower'] = current_theme['floor_lower'].value
        current_theme['floor_upper'] = current_theme['floor_upper'].value
        self.settings.component_controller.set_state(self.__class__.__name__, current_theme)
