import unittest

from app.tests import qt_headless  # noqa: F401 -- before any QApplication


class ReturnDoesNotCloseTheDialogTests(unittest.TestCase):
    '''
    QLineEdit ignores Return so the surrounding dialog can act on it, and the
    editor dialogs carry an Ok button in their button box. Renaming something and
    pressing Enter therefore committed the rename and accepted the dialog at once,
    closing the window
    '''

    @classmethod
    def setUpClass(cls) -> None:
        import sys
        from app.editor.editor_locale import init_locale
        init_locale()
        from PyQt5.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def build_dialog(self, edit_class):
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

        class Dialog(QDialog):
            def __init__(self):
                super().__init__()
                self.accepted_count = 0
                layout = QVBoxLayout(self)
                self.edit = edit_class()
                layout.addWidget(self.edit)
                box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel |
                                       QDialogButtonBox.Apply, Qt.Horizontal, self)
                box.accepted.connect(self.accept)
                layout.addWidget(box)

            def accept(self):
                self.accepted_count += 1
                super().accept()

        dialog = Dialog()
        dialog.show()
        dialog.edit.setFocus()
        return dialog

    def press(self, widget, key, text=''):
        from PyQt5.QtCore import QEvent, Qt
        from PyQt5.QtGui import QKeyEvent
        self.app.sendEvent(widget, QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier, text))
        self.app.sendEvent(widget, QKeyEvent(QEvent.KeyRelease, key, Qt.NoModifier, text))

    def edit_classes(self):
        from app.editor.lib.components.validated_line_edit import (NidLineEdit,
                                                                   NoParentheticalLineEdit)
        return (NidLineEdit, NoParentheticalLineEdit)

    def test_return_leaves_the_dialog_open(self):
        from PyQt5.QtCore import Qt
        for edit_class in self.edit_classes():
            for key, name in ((Qt.Key_Return, 'Return'), (Qt.Key_Enter, 'Enter')):
                with self.subTest(edit=edit_class.__name__, key=name):
                    dialog = self.build_dialog(edit_class)
                    dialog.edit.setText('Renamed')
                    self.press(dialog.edit, key)
                    self.assertEqual(0, dialog.accepted_count)
                    self.assertTrue(dialog.isVisible())
                    dialog.close()

    def test_return_still_finishes_the_edit(self):
        from PyQt5.QtCore import Qt
        for edit_class in self.edit_classes():
            with self.subTest(edit=edit_class.__name__):
                dialog = self.build_dialog(edit_class)
                emitted = []
                dialog.edit.returnPressed.connect(lambda: emitted.append('returnPressed'))
                dialog.edit.editingFinished.connect(lambda: emitted.append('editingFinished'))
                dialog.edit.setText('Renamed')
                self.press(dialog.edit, Qt.Key_Return)
                self.assertIn('returnPressed', emitted)
                self.assertIn('editingFinished', emitted)
                dialog.close()

    def test_other_keys_are_unaffected(self):
        from PyQt5.QtCore import Qt
        dialog = self.build_dialog(self.edit_classes()[0])
        self.press(dialog.edit, Qt.Key_A, 'a')
        self.assertEqual('a', dialog.edit.text())
        dialog.close()


if __name__ == '__main__':
    unittest.main()
