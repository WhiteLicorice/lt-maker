from __future__ import annotations

from app.data.database.credit import CreditCatalog
from app.editor.credit_editor.new_credit_properties import NewCreditProperties
from app.editor.new_editor_tab import NewEditorTab

from app.utilities.typing import NID

class NewCreditDatabase(NewEditorTab):
    catalog_type = CreditCatalog
    properties_type = NewCreditProperties

    @property
    def data(self):
        return self._db.credit

    def get_icon(self, unit_nid: NID) -> Optional[QIcon]:
        pass

    def _on_delete(self, nid: NID) -> bool:
        return True

    def _on_nid_changed(self, old_nid: NID, new_nid: NID) -> None:
        pass

    def import_xml(self):
        pass

    def import_csv(self):
        pass

    def create_new(self, nid):
        if self.data.get(nid):
            QMessageBox.warning(self, 'Warning', 'ID %s already in use' % nid)
            return False
        new_obj = self.catalog_type.datatype(nid, nid)
        self.data.append(new_obj)
        return True

# Testing
# Run "python -m app.editor.credit_editor.new_credit_tab" from main directory
if __name__ == '__main__':
    import sys
    from app.data.database.database import DB
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from app.data.resources.resources import RESOURCES
    from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
    DB.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
    RESOURCES.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
    window = NewCreditDatabase(None, DB)
    window.show()
    app.exec_()
