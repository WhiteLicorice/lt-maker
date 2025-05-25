from PyQt5.QtCore import Qt

from app.data.database.database import DB
from app.editor.base_database_gui import DragDropCollectionModel

class CreditModel(DragDropCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            credit = self._data[index.row()]
            text = credit.nid
            return text
        return None

    def create_new(self):
        new_credit = DB.credit.create_new(DB)
        return new_credit

    def on_nid_changed(self, old_value, new_value):
        pass
