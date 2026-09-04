import sys
import os
import traceback
import datetime
from PySide6.QtCore import Qt
from multiprocessing import freeze_support

freeze_support()

from PySide6.QtWidgets import QApplication, QStyleFactory

app = QApplication(sys.argv)

from tachys_editor.shared.settings import data_dir, settings_mgr
from tachys_editor.ui.window import TachysEditorWindow

crash_log_file = os.path.join(data_dir, 'crashlog.txt')


def catch_exceptions(exception_type, value, tb):
    error_msg = "".join(traceback.format_exception(exception_type, value, tb))
    if crash_log_file:
        with open(crash_log_file, 'a') as f:
            f.write(f'\n[{datetime.datetime.now()}]: {error_msg}')
    print(error_msg)
    sys.exit(1)

sys.excepthook = catch_exceptions


if __name__ == "__main__":
    app.setStyle(QStyleFactory.create(settings_mgr.appearance.window_style))
    theme = settings_mgr.appearance.theme
    if theme == 'Dark':
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    elif theme == 'Light':
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    else:
        settings_mgr.appearance.theme = app.styleHints().colorScheme().name
    font = app.font()
    font.setPointSize(settings_mgr.appearance.ui_font_size)
    app.setFont(font)
    window = TachysEditorWindow()
    window.show()
    sys.exit(app.exec())
