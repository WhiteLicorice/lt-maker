from __future__ import annotations

from typing import Optional

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox

from app.data.database.lore import LoreCatalog
from app.editor.lore_editor.new_lore_properties import NewLoreProperties
from app.editor.new_editor_tab import NewEditorTab

from app.utilities.typing import NID

class NewLoreDatabase(NewEditorTab):
    catalog_type = LoreCatalog
    properties_type = NewLoreProperties
    allow_copy_and_paste = True
    icon_size = 16

    @property
    def data(self):
        return self._db.lore

    def get_icon(self, lore_nid: NID) -> Optional[QIcon]:
        return None

    def get_search_text(self, nid: NID) -> str:
        lore = self.data.get(nid)
        return '\n'.join([nid, lore.name, lore.title, lore.category])

    def create_new(self, nid):
        if self.data.get(nid):
            QMessageBox.warning(self, 'Warning', 'ID %s already in use' % nid)
            return False
        new_lore = self.catalog_type.datatype(nid, nid, nid)
        self.data.append(new_lore)
        return True

    def _on_nid_changed(self, old_nid: NID, new_nid: NID):
        pass

    def _on_delete(self, nid: NID) -> bool:
        return True

# Testing
# Run "python -m app.editor.lore_editor.new_lore_tab" from main directory
if __name__ == '__main__':
    import sys
    from app.data.database.database import DB
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from app.data.resources.resources import RESOURCES
    from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
    DB.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
    RESOURCES.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
    window = NewLoreDatabase(None, DB)
    window.show()
    app.exec_()
