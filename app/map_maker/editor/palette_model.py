from PyQt5.QtCore import Qt, QAbstractListModel

class PaletteModel(QAbstractListModel):
    def __init__(self, data, window):
        super().__init__(window)
        self._data = data
        self.window = window

    def rowCount(self, parent=None):
        return len(self._data)

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            palette = self._data[index.row()]
            text = "%s (%s)" % (palette.name, palette.author)
            return text
        return None
