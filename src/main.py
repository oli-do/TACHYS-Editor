import sys
import os
import traceback
import datetime

from PySide6.QtWidgets import QApplication, QStyleFactory

from tachys_editor.ui.window import TachysEditorWindow
from multiprocessing import freeze_support
from tachys_editor.shared.settings import data_dir, settings_mgr

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
    freeze_support()
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    screen = QApplication.primaryScreen()
    size = screen.size()
    screen_width = size.width()
    screen_height = size.height()
    width = round(0.75 * screen_width)
    height = round(0.75 * screen_height)
    default_ui_font_size = round(0.009 * screen_height)
    settings_mgr.appearance.default_ui_font_size = default_ui_font_size
    if settings_mgr.appearance.ui_font_size == -1:
        settings_mgr.appearance.ui_font_size = default_ui_font_size
    font = app.font()
    font.setPointSize(settings_mgr.appearance.ui_font_size)
    app.setFont(font)
    window = TachysEditorWindow(screen_height)
    window.resize(width, height)
    window.show()
    sys.exit(app.exec())
