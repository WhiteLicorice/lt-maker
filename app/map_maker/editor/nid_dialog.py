from PyQt5.QtWidgets import QLineEdit, QVBoxLayout, \
    QDialogButtonBox, QDialog

from app.extensions.custom_gui import PropertyBox, Dialog

class NidDialog(Dialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Tileset Nid")
        self.window = parent

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.new_nid_box = PropertyBox("Tileset Nid", QLineEdit, self)
        self.new_nid_box.edit.setPlaceholderText("Give the tileset a unique nid")
        self.new_nid_box.edit.textChanged.connect(self.text_changed)
        layout.addWidget(self.new_nid_box)

        layout.addWidget(self.buttonbox)
        self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)

    def text_changed(self, text):
        if self.new_nid_box.edit.text():
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)

    @classmethod
    def get(cls, parent=None):
        dialog = cls(parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            return dialog.new_nid_box.edit.text()
        else:
            return None
