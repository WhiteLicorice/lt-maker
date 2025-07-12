from typing import List

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from PyQt5.QtCore import QAbstractListModel

from app.map_maker.qt_renderers.renderer_database import RENDERERS
from app.map_maker.terrain import Terrain

class MapTerrainModel(QAbstractListModel):
    def __init__(self, data: List[Terrain], window):
        super().__init__(window)
        self._data = data

    def rowCount(self, parent=None):
        return len(self._data)

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            terrain = self._data[index.row()]
            text = terrain.value
            return text
        elif role == Qt.DecorationRole:
            terrain = self._data[index.row()]
            pix = RENDERERS[terrain].get_display_pixmap()
            return QIcon(pix.scaled(32, 32))
        return None
