'''
Import before the first QApplication to run Qt without a screen

The offscreen platform doesn't ask the OS for its fonts. It reads them from Qt's
own lib/fonts folder, which the PyQt5 wheels leave out, and warns
"QFontDatabase: Cannot find font directory" every time it looks. On Windows,
point it at the system fonts instead.

It also warns that it "does not support propagateSizeHints()" whenever a test
shows a widget, which says nothing about the widget, so that one message is
dropped. Every other Qt message still reaches stderr
'''
import os
import sys

from PyQt5.QtCore import qInstallMessageHandler

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
if sys.platform == 'win32':
    os.environ.setdefault('QT_QPA_FONTDIR', os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts'))

IGNORED_MESSAGES = {'This plugin does not support propagateSizeHints()'}

def _message_handler(mode, context, message):
    if message not in IGNORED_MESSAGES:
        print(message, file=sys.stderr)

qInstallMessageHandler(_message_handler)
