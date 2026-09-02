import re
from PyQt5.QtWidgets import QPushButton, QLineEdit
from PyQt5.QtCore import QSize, Qt, QRegExp
from PyQt5.QtGui import QRegExpValidator

# Custom Widgets
from app.utilities.data import Data
from app.data.database.database import DB

from app.extensions.custom_gui import PropertyBox, ComboBox

class BetterRegExpValidator(QRegExpValidator):
  def fixup(self, a0: str) -> str:
    return re.sub("[^A-Za-z0-9_]", '_', a0)

class CommitsOnReturn(QLineEdit):
  """A line edit where Return finishes the edit and goes no further.

  QLineEdit ignores Return so the surrounding dialog can act on it, and these
  edits sit in dialogs whose button box carries an Ok button. Return would
  therefore commit the field and accept the dialog in one keystroke, closing the
  window out from under someone who was only renaming something.
  """
  def keyPressEvent(self, event) -> None:
    super().keyPressEvent(event)  # still emits returnPressed and editingFinished
    if event.key() in (Qt.Key_Return, Qt.Key_Enter):
      event.accept()

class NidLineEdit(CommitsOnReturn):
  """For strict limiting on NID forms. Alphanumerics and underscore only.
  """
  def __init__(self, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    reg_ex = QRegExp(r"[A-Za-z0-9_]*")
    input_validator = BetterRegExpValidator(reg_ex, self)
    self.setValidator(input_validator)

class NoParentheticalLineEdit(CommitsOnReturn):
  """Less limiting. Allows periods and spaces, but no parentheses.

  Also doesn't allow semicolons.
  """
  def __init__(self, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    reg_ex = QRegExp(r"[^\(\);]*")
    input_validator = QRegExpValidator(reg_ex, self)
    self.setValidator(input_validator)