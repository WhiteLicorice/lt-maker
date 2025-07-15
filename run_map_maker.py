import os, sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from app.editor.settings import MainSettingsController

if __name__ == '__main__':
    import logging, traceback
    from app import lt_log
    success = lt_log.create_logger()
    from PyQt5.QtWidgets import QApplication
    from app import dark_theme

    # For High DPI displays
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    ap = QApplication(sys.argv)
    ap.setWindowIcon(QIcon('favicon.ico'))
    settings = MainSettingsController()
    theme = dark_theme.get_theme()
    dark_theme.set(ap, theme)

    from app.map_maker.map_prefab import MapPrefab
    from app.map_maker.editor.map_editor import MapEditor
    
    try:
        sample_tilemap = MapPrefab('sample')
        map_editor = MapEditor(current=sample_tilemap)
        map_editor.show()
        ap.exec_()
    except Exception as e:
        logging.exception(e)
        import time
        time.sleep(0.5)
        traceback.print_exc()
        time.sleep(0.5)
