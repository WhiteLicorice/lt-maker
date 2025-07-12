from typing import List

from PyQt5.QtWidgets import QGridLayout, QListView, \
    QWidget
from PyQt5.QtCore import QSize

from app.map_maker.editor.map_terrain_model import MapTerrainModel
from app.map_maker.terrain import Terrain

class TerrainPainterMenu(QWidget):
    def __init__(self, terrain: List[Terrain], parent=None):
        super().__init__(parent)
        self.terrain_list = terrain
        self.map_editor = parent

        grid = QGridLayout()
        self.setLayout(grid)

        self.list_view = QListView(self)

        self.model = MapTerrainModel(self.terrain_list, self)
        self.list_view.setModel(self.model)
        self.list_view.setIconSize(QSize(32, 32))
        self.list_view.setMaximumWidth(300)

        grid.addWidget(self.list_view, 3, 0, 1, 2)

    def on_visibility_changed(self, state):
        pass

    def reset(self):
        self.model.layoutChanged.emit()

    def set_current_terrain(self, terrain: Terrain):
        idx = self.model.index(self.terrain_list.index(terrain))
        self.list_view.setCurrentIndex(idx)

    def get_current_terrain(self) -> Terrain:
        index = self.list_view.currentIndex()
        terrain = self.terrain_list[index.row()]
        return terrain
