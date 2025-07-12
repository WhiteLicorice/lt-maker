from typing import Optional

import os
import json

from PyQt5.QtWidgets import QFrame, QVBoxLayout, \
    QToolBar, QSpinBox, QAction, QMenu, QDockWidget, \
    QActionGroup, QWidget, QMainWindow, QLabel, QSizePolicy, \
    QDesktopWidget, QFileDialog, QHBoxLayout, QMessageBox, \
    QTabWidget
from PyQt5.QtCore import Qt, QDir
from PyQt5.QtGui import QIcon, QImage, QPainter, QColor

from app import dark_theme

from app.constants import TILEWIDTH, TILEHEIGHT, AUTOTILE_FRAMES

from app.extensions.custom_gui import PropertyBox, ComboBox
from app.editor.settings import MainSettingsController

from .resize_dialog import ResizeDialog
from .terrain_painter_menu import TerrainPainterMenu
from .map_editor_view import PaintTool, MapEditorView
from .draw_tilemap import simple_draw_tilemap
from .palette_model import PaletteModel
from .nid_dialog import NidDialog
from .autogenerate_indoor_map import AutogenerateIndoorMap

from app.map_maker.map_prefab import MapPrefab
import app.map_maker.utilities as map_utils
from app.map_maker.palette_collection import PALETTES
from app.map_maker.qt_renderers.renderer_database import RENDERERS
from app.map_maker.terrain import Terrain

class CliffMarkerWidget(QWidget):
    def __init__(self, parent=None, tilemap=None):
        super().__init__(parent)
        self.window = parent
        self.tilemap = tilemap

        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.main_box = PropertyBox("Cliff Markers", ComboBox, self)
        self.main_box.setMaximumWidth(100)
        self.main_box.setMinimumWidth(100)
        for cliff_marker in self.tilemap.cliff_markers:
            self.main_box.edit.addItem("%d, %d" % cliff_marker)
        # self.main_box.edit.activated.connect(self.main_box_activation)

        self.toolbar = QToolBar(self)
        self.toolbar.addAction(self.window.add_cliff_marker_action)
        self.toolbar.addAction(self.window.remove_cliff_marker_action)

        self.layout.addWidget(self.main_box)
        self.layout.addWidget(self.toolbar)

    def set_current(self, current):
        self.tilemap = current
        self.main_box.edit.clear()
        for cliff_marker in self.tilemap.cliff_markers:
            self.main_box.edit.addItem("%d, %d" % cliff_marker)
        self.reset()

    def reset(self):
        self.window.add_cliff_marker_action.setChecked(False)
        self.toggle_remove_button()

    def add_new_marker(self, pos):
        self.reset()
        self.tilemap.cliff_markers.append(pos)
        self.main_box.edit.addItem("%d, %d" % self.tilemap.cliff_markers[-1])
        self.tilemap.reset_all()
        self.toggle_remove_button()

    def toggle_remove_button(self):
        self.window.remove_cliff_marker_action.setEnabled(len(self.tilemap.cliff_markers) > 1)

class MapEditor(QMainWindow):
    title = "LT Map Maker"

    def __init__(self, parent=None, current: Optional[MapPrefab] = None):
        super().__init__(parent)
        self.window = parent
        self.setWindowTitle(self.title)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.settings = MainSettingsController()

        desktop = QDesktopWidget()
        main_screen_size = desktop.availableGeometry(desktop.primaryScreen())
        default_size = int(main_screen_size.width()*0.7), int(main_screen_size.height()*0.7)
        self.resize(*default_size)

        self.current = current
        self.current_map_save_location = None
        self.current_tool = PaintTool.NoTool

        self.outdoor_terrain_painter_menu = TerrainPainterMenu(Terrain.outdoor_terrain(), self)
        self.indoor_terrain_painter_menu = TerrainPainterMenu(Terrain.indoor_terrain(), self)

        self.view = MapEditorView(self)
        self.view.set_current(current)

        self.autotile_fps_box = PropertyBox("Autotile Speed", QSpinBox, self)
        self.autotile_fps_box.edit.setValue(self.current.autotile_fps)
        self.autotile_fps_box.setMaximumWidth(100)
        self.autotile_fps_box.edit.setAlignment(Qt.AlignRight)
        self.autotile_fps_box.edit.valueChanged.connect(self.autotile_fps_changed)

        self.random_seed_box = PropertyBox("RNG Seed", QSpinBox, self)
        self.random_seed_box.edit.setRange(0, 1023)
        self.random_seed_box.edit.setValue(map_utils.get_random_seed())
        self.random_seed_box.setMaximumWidth(100)
        self.random_seed_box.edit.setAlignment(Qt.AlignRight)
        self.random_seed_box.edit.valueChanged.connect(self.random_seed_changed)

        self.setCentralWidget(self.view)

        self.create_actions()
        self.create_menus()
        self.create_toolbar()

        self.cliff_marker_widget = CliffMarkerWidget(self, self.current)

        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.cliff_marker_widget)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)
        self.toolbar.addWidget(self.autotile_fps_box)
        fixed_space = QLabel()
        fixed_space.setFixedWidth(10)
        self.toolbar.addWidget(fixed_space)
        self.toolbar.addWidget(self.random_seed_box)

        # Palette selectors
        self.outdoor_palette_selector = PropertyBox("Palette", ComboBox, self)
        outdoor_palette_model = PaletteModel(PALETTES.outdoor_palettes(), self)
        self.outdoor_palette_selector.edit.setModel(outdoor_palette_model)
        self.outdoor_palette_selector.edit.currentIndexChanged.connect(self.outdoor_palette_changed)

        if self.current.current_outdoor_palette:
            idx = [p.nid for p in PALETTES.outdoor_palettes()].index(self.current.current_outdoor_palette)
            self.outdoor_palette_changed(idx)
        else:
            self.outdoor_palette_changed(0)  # Apply it for the current palette

        self.indoor_palette_selector = PropertyBox("Palette", ComboBox, self)
        indoor_palette_model = PaletteModel(PALETTES.indoor_palettes(), self)
        self.indoor_palette_selector.edit.setModel(indoor_palette_model)
        self.indoor_palette_selector.edit.currentIndexChanged.connect(self.indoor_palette_changed)

        if self.current.current_indoor_palette:
            idx = [p.nid for p in PALETTES.indoor_palettes()].index(self.current.current_indoor_palette)
            self.indoor_palette_changed(idx)
        else:
            self.indoor_palette_changed(0)  # Apply it for the current palette

        self.terrain_tab = QTabWidget(self)

        # Outdoor
        outdoor_frame = QFrame(self)
        outdoor_layout = QVBoxLayout()
        outdoor_frame.setLayout(outdoor_layout)
        outdoor_layout.addWidget(self.outdoor_terrain_painter_menu)
        outdoor_layout.addWidget(self.outdoor_palette_selector)
        self.terrain_tab.addTab(outdoor_frame, "Outdoor Terrain")

        # Indoor
        indoor_frame = QFrame(self)
        indoor_layout = QVBoxLayout()
        indoor_frame.setLayout(indoor_layout)
        indoor_layout.addWidget(self.indoor_terrain_painter_menu)
        indoor_layout.addWidget(self.indoor_palette_selector)
        self.terrain_tab.addTab(indoor_frame, "Indoor Terrain")

        self.terrain_dock = QDockWidget("Terrain", self)
        self.terrain_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.terrain_dock.setWidget(self.terrain_tab)
        self.terrain_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.addDockWidget(Qt.RightDockWidgetArea, self.terrain_dock)

        self.position_bar = QLabel("", self)
        self.position_bar.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.position_bar.setMinimumWidth(100)
        self.statusBar().addPermanentWidget(self.position_bar)

        self.check_brush()

        # Restore Geometry
        geometry = self.settings.component_controller.get_geometry(self._type())
        if geometry:
            self.restoreGeometry(geometry)

        self.view.update_view()

    def terrain_painter_menu(self):
        if self.terrain_tab.currentIndex() == 0:
            return self.outdoor_terrain_painter_menu
        else:
            return self.indoor_terrain_painter_menu

    def palette_selector(self):
        if self.terrain_tab.currentIndex() == 0:
            return self.outdoor_palette_selector
        else:
            return self.indoor_palette_selector

    def create_actions(self):
        theme = dark_theme.get_theme()
        icon_folder = theme.icon_dir()

        paint_group = QActionGroup(self)
        self.brush_action = QAction(QIcon(f"{icon_folder}/brush.png"), "Brush", self, shortcut="B", triggered=self.set_brush)
        self.brush_action.setCheckable(True)
        paint_group.addAction(self.brush_action)
        self.paint_action = QAction(QIcon(f"{icon_folder}/fill.png"), "Fill", self, shortcut="F", triggered=self.set_fill)
        self.paint_action.setCheckable(True)
        paint_group.addAction(self.paint_action)
        self.erase_action = QAction(QIcon(f"{icon_folder}/eraser.png"), "Erase", self, shortcut="E", triggered=self.set_erase)
        self.erase_action.setCheckable(True)
        paint_group.addAction(self.erase_action)
        self.resize_action = QAction(QIcon(f"{icon_folder}/resize.png"), "Resize", self, shortcut="R", triggered=self.resize_map)

        self.export_as_png_action = QAction(QIcon(f"{icon_folder}/export_as_png.png"), "Export Current Image as PNG", self, triggered=self.export_as_png)
        self.export_to_lt_action = QAction(QIcon("favicon.ico"), "Export to LT-maker", self, triggered=self.export_to_lt)

        self.show_gridlines_action = QAction(QIcon(f"{icon_folder}/gridlines.png"), "Show GridLines", self, triggered=self.gridline_toggle)
        self.show_gridlines_action.setCheckable(True)
        self.show_gridlines_action.setChecked(True)

        self.add_cliff_marker_action = QAction(QIcon(f"{icon_folder}/plus.png"), "Add Cliff Marker", self, triggered=self.choose_cliff_marker)
        self.add_cliff_marker_action.setCheckable(True)
        self.remove_cliff_marker_action = QAction(QIcon(f"{icon_folder}/minus.png"), "Remove Cliff Marker", self, triggered=self.remove_cliff_marker)
        self.remove_cliff_marker_action.setEnabled(False)

        self.new_action = QAction("New Map...", self,
                                  shortcut="Ctrl+N", triggered=self.new)
        self.open_action = QAction("Open Map...", self,
                                   shortcut="Ctrl+O", triggered=self.open)
        self.save_action = QAction("Save Map", self,
                                   shortcut="Ctrl+S", triggered=self.save)
        self.save_as_action = QAction(
            "Save Map As...", self, shortcut="Ctrl+Shift+S", triggered=self.save_as)
        self.quit_action = QAction(
            "&Quit", self, shortcut="Ctrl+Q", triggered=self.close)

        self.autogenerate_indoor_map_action = QAction("Autogenerate Indoor Map...", self, triggered=self.autogenerate_indoor_map)
        self.autogenerate_outdoor_map_action = QAction("Autogenerate Outdoor Map...", self, triggered=self.autogenerate_outdoor_map)

        self.about_action = QAction("About", self, triggered=self.about)
        self.help_action = QAction("Help", self, triggered=self.display_help)

        # menu actions
        self.zoom_in_action = QAction(
            QIcon(f"{icon_folder}/zoom_in.png"),
            "Zoom in", self, shortcut="Ctrl++", triggered=self.view.zoom_in)
        self.zoom_out_action = QAction(
            QIcon(f"{icon_folder}/zoom_out.png"),
            "Zoom out", self, shortcut="Ctrl+-", triggered=self.view.zoom_out)

    def create_menus(self):
        self.menuBar().clear()
        file_menu = QMenu("File", self)
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addAction(self.export_as_png_action)
        file_menu.addAction(self.export_to_lt_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        edit_menu = QMenu("Edit", self)
        edit_menu.addAction(self.brush_action)
        edit_menu.addAction(self.paint_action)
        edit_menu.addAction(self.erase_action)
        edit_menu.addAction(self.add_cliff_marker_action)
        edit_menu.addAction(self.remove_cliff_marker_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.show_gridlines_action)
        edit_menu.addAction(self.zoom_in_action)
        edit_menu.addAction(self.zoom_out_action)

        auto_menu = QMenu("Auto", self)
        auto_menu.addAction(self.autogenerate_indoor_map_action)
        auto_menu.addAction(self.autogenerate_outdoor_map_action)

        extra_menu = QMenu("Extra", self)
        extra_menu.addAction(self.about_action)
        extra_menu.addAction(self.help_action)

        self.menuBar().addMenu(file_menu)
        self.menuBar().addMenu(edit_menu)
        self.menuBar().addMenu(auto_menu)
        self.menuBar().addMenu(extra_menu)

    def create_toolbar(self):
        self.toolbar = self.addToolBar("Edit")
        self.toolbar.addAction(self.brush_action)
        self.toolbar.addAction(self.paint_action)
        self.toolbar.addAction(self.erase_action)
        self.toolbar.addAction(self.resize_action)
        self.toolbar.addAction(self.export_as_png_action)
        self.toolbar.addAction(self.show_gridlines_action)
        self.toolbar.setAllowedAreas(Qt.TopToolBarArea)
        self.toolbar.setFloatable(False)
        self.toolbar.setMovable(False)

    def set_title(self):
        if self.current_map_save_location:
            self.setWindowTitle(self.current_map_save_location + " -- " + self.title)
        else:
            self.setWindowTitle(self.title)

    def set_message(self, msg):
        if msg:
            self.statusBar().showMessage(msg)
        else:
            self.statusBar().clearMessage()

    def set_position_bar(self, pos):
        if pos:
            self.position_bar.setText("Position (%d, %d)" % (pos[0], pos[1]))
        else:
            self.position_bar.setText("")

    def void_right_selection(self):
        self.view.right_selection.clear()

    def check_brush(self):
        self.brush_action.setChecked(True)
        self.set_brush(True)

    def set_brush(self, val):
        self.cliff_marker_widget.reset()
        self.current_tool = PaintTool.Brush

    def set_fill(self, val):
        self.cliff_marker_widget.reset()
        self.current_tool = PaintTool.Fill

    def set_erase(self, val):
        self.cliff_marker_widget.reset()
        self.current_tool = PaintTool.Erase

    def choose_cliff_marker(self, checked):
        if checked:
            self.set_cliff_marker()
            self.add_cliff_marker_action.setChecked(True)

    def set_cliff_marker(self):
        self.brush_action.setChecked(False)
        self.paint_action.setChecked(False)
        self.erase_action.setChecked(False)
        self.current_tool = PaintTool.CliffMarker

    def remove_cliff_marker(self):
        if len(self.current.cliff_markers) > 1:
            idx = self.cliff_marker_widget.main_box.edit.currentIndex()
            self.current.cliff_markers.pop(idx)
            self.cliff_marker_widget.main_box.edit.removeItem(idx)
            self.current.reset_all()
        else:
            QMessageBox.warning("Warning", "Cannot remove last cliff marker!")
        self.cliff_marker_widget.toggle_remove_button()

    def set_current(self, current: MapPrefab):
        self.current = current
        self.view.set_current(current)
        self.autotile_fps_box.edit.setValue(current.autotile_fps)
        self.cliff_marker_widget.set_current(current)
        self.view.update_view()

    def resize_map(self):
        ResizeDialog.get_new_size(self.current, self)

    def gridline_toggle(self, val):
        self.view.draw_gridlines = val

    def autotile_fps_changed(self, val):
        self.current.autotile_fps = val

    def random_seed_changed(self, val):
        map_utils.set_random_seed(val)
        print("--- Seed Changed to %d ---" % val)
        self.current.reset_all()

    def indoor_palette_changed(self, idx: int):
        palette = PALETTES.indoor_palettes()[idx]
        self.current.current_indoor_palette = palette.nid
        for terrain, renderer in RENDERERS.items():
            if not terrain.outdoor:
                renderer.set_palette(palette.get(terrain))
        self.current.reset_all()
        self.indoor_terrain_painter_menu.reset()

    def outdoor_palette_changed(self, idx: int):
        palette = PALETTES.outdoor_palettes()[idx]
        self.current.current_outdoor_palette = palette.nid
        for terrain, renderer in RENDERERS.items():
            if terrain.outdoor:
                renderer.set_palette(palette.get(terrain))
        self.current.reset_all()
        self.outdoor_terrain_painter_menu.reset()

    def autogenerate_indoor_map(self):
        AutogenerateIndoorMap.customize(self)

    def autogenerate_outdoor_map(self):
        QMessageBox.information(self, self.title, "Not implemented yet!")

    def export_as_png(self):
        if self.current:
            image = simple_draw_tilemap(self.current)
            starting_path = self.settings.get_last_open_path()
            fn, ok = QFileDialog.getSaveFileName(
                self, "Export Current Image", starting_path,
                "PNG Files (*.png)")
            if fn and ok:
                image.save(fn)
                parent_dir = os.path.split(fn)[0]
                self.settings.set_last_open_path(parent_dir)

    def export_to_lt(self):
        if not self.current:
            QMessageBox.critical(self, self.title, "There is no current map!")
            return

        QMessageBox.warning(self, self.title, "Do not select a .ltproj that's currently open in the LT Editor!\n"
                            "Doing so may cause corruption of your files!")

        image: QImage = simple_draw_tilemap(self.current)

        starting_path = self.settings.get_last_open_path()
        fn = QFileDialog.getExistingDirectory(
            self, "Select LT Project", starting_path)

        if fn:
            parent_dir = os.path.split(fn)[0]
            self.settings.set_last_open_path(parent_dir)

            nid = NidDialog.get(self)
            if not nid:
                return

            loc = os.path.join(fn, 'resources', 'tilesets')
            assert os.path.isdir(loc)
            manifest = os.path.join(loc, 'tilesets.json')
            full_path = os.path.join(loc, nid + '.png')
            autotile_path = os.path.join(loc, nid + '_autotiles.png')
            image.save(full_path)

            s_dict = {}
            s_dict['nid'] = nid
            s_dict['terrain_grid'] = {}

            # Build autotiles
            s_dict['autotiles'] = {}
            all_autotile_positions = []
            for pos in sorted(self.current.terrain_grid):
                # Determine what terrain is in this position
                terrain = self.current.get_terrain(pos)
                if not terrain:
                    continue
                painter = RENDERERS.get(terrain).painter
                if painter.has_autotiles():
                    all_autotile_positions.append((pos, terrain))

            if all_autotile_positions:
                autotile_width = TILEWIDTH * len(all_autotile_positions)
                autotile_height = TILEHEIGHT * AUTOTILE_FRAMES
                autotile_image = QImage(autotile_width, autotile_height, QImage.Format_ARGB32)
                autotile_image.fill(QColor(255, 255, 255, 0))

                qpainter = QPainter(autotile_image)
                for idx, (pos, terrain) in enumerate(all_autotile_positions):
                    str_coord = "%d,%d" % (pos[0], pos[1])
                    s_dict['autotiles'][str_coord] = idx
                    for pidx in range(AUTOTILE_FRAMES):
                        sprite = RENDERERS.get(terrain).determine_sprite(self.current, pos, pidx)
                        qpainter.drawPixmap(idx * TILEWIDTH, pidx * TILEHEIGHT, sprite)
                qpainter.end()
                autotile_image.save(autotile_path)
            # Completed creating autotiles

            # Modify the tileset manifest of the project
            import json
            with open(manifest) as fp:
                data = json.load(fp)
            data.append(s_dict)
            with open(manifest, 'w') as fp:
                json.dump(data, fp, indent=4)

            QMessageBox.information(self, self.title, "Map successfully exported as tileset with nid *%s* to %s" % (nid, fn))

    def update_view(self):
        self.view.update_view()

    def maybe_save(self):
        ret = QMessageBox.warning(self, self.title, "The current map may have been modified.\n"
                                  "Do you want to save your changes?",
                                  QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if ret == QMessageBox.Save:
            return self.save()
        elif ret == QMessageBox.Cancel:
            return False
        return True

    def save(self, new=False):
        if new or not self.current_map_save_location:
            starting_path = self.current_map_save_location or QDir.currentPath()
            fn, ok = QFileDialog.getSaveFileName(self, "Save Map", starting_path,
                                                 "All Files (*)")
            if ok:
                if fn.endswith('.json'):
                    self.current_map_save_location = fn
                else:
                    self.current_map_save_location = fn + '.json'
            else:
                return False
            new = True

        if new:
            if os.path.exists(self.current_map_save_location):
                ret = QMessageBox.warning(self, "Save Map", "The file already exists.\nDo you want to overwrite it?",
                                          QMessageBox.Save | QMessageBox.Cancel)
                if ret == QMessageBox.Save:
                    pass
                else:
                    return False

        # Actually save project
        self.saved_data = self.current.save()
        with open(self.current_map_save_location, 'w') as save_file:
            json.dump(self.saved_data, save_file, indent=4)
        self.set_title()
        return True

    def save_as(self):
        return self.save(True)

    def new(self):
        if not self.maybe_save():
            return False
        new_tilemap_prefab = MapPrefab('sample')
        result = ResizeDialog.get_new_size(new_tilemap_prefab)
        if not result:
            return False
        self.current_map_save_location = None
        self.current = new_tilemap_prefab
        self.current.reset_all()
        self.view.set_current(self.current)
        self.set_title()
        return result

    def open(self):
        if self.maybe_save():
            if self.current_map_save_location:
                starting_path = os.path.join(self.current_map_save_location, '..')
            else:
                starting_path = QDir.currentPath()
            fn, ok = QFileDialog.getOpenFileName(self, "Open Saved Map", starting_path, "JSON Files (*.json)")
            if fn:
                self.current_map_save_location = fn
                self.load()
                self.set_title()
                return True
            else:
                return False
        return False

    def load(self):
        if os.path.exists(self.current_map_save_location):
            with open(self.current_map_save_location) as load_file:
                s_dict = json.load(load_file)
                self.current = MapPrefab.restore(s_dict)

        if self.current.current_indoor_palette:
            idx = PALETTES.indoor_palettes().index(self.current.current_indoor_palette)
            self.indoor_palette_selector.edit.setCurrentIndex(idx)
            self.indoor_palette_changed(idx)
        else:
            self.indoor_palette_changed(0)  # Apply it for the current palette
        if self.current.current_outdoor_palette:
            idx = PALETTES.outdoor_palettes().index(self.current.current_outdoor_palette)
            self.outdoor_palette_selector.edit.setCurrentIndex(idx)
            self.outdoor_palette_changed(idx)
        else:
            self.outdoor_palette_changed(0)  # Apply it for the current palette

        self.set_current(self.current)

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()
        self.save_geometry()

    def about(self):
        QMessageBox.about(self, "About Lex Talionis Map Maker",
                          "<p>This is the <b>Lex Talionis</b> Map Maker.</p>"
                          "<p>Check out <a href='https://lt-maker.readthedocs.io/'>https://lt-maker.readthedocs.io/</a> "
                          "for more information and helpful tutorials.</p>"
                          "<p>This program has been freely distributed under the MIT License.</p>"
                          "<p>Copyright 2014-2025 rainlash.</p>")

    def display_help(self):
        QMessageBox.about(self, "Help for Lex Talionis Map Maker",
                          "<p>Check out <a href='https://lt-maker.readthedocs.io/'>https://lt-maker.readthedocs.io/</a> "
                          "for information and helpful tutorials.</p>"
                          "<p>Or visit the LT community discord at <a href='https://discord.gg/dC6VWGh4sw'>https://discord.gg/dC6VWGh4sw</a> "
                          "for answers to your questions and a helpful community.</p>")

    def _type(self):
        return 'map_maker'

    def save_geometry(self):
        self.settings.component_controller.set_geometry(self._type(), self.saveGeometry())
        # self.settings.component_controller.set_state(self._type(), (self.main_splitter.saveState(), self.right_frame.saveState()))
