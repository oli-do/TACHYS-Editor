import sys
import os
import traceback
import datetime

from PySide6.QtWidgets import QApplication

from tachys_editor.ui.window import TachysEditorWindow
from multiprocessing import freeze_support
from tachys_editor.shared.settings import data_dir

crash_log_file = os.path.join(data_dir, 'crashlog.txt')


def catch_exceptions(exception_type, value, tb):
    error_msg = "".join(traceback.format_exception(exception_type, value, tb))
    with open(crash_log_file, 'a') as f:
        f.write(f'\n[{datetime.datetime.now()}]: {error_msg}')
    sys.exit(1)

sys.excepthook = catch_exceptions


if __name__ == "__main__":
    freeze_support()
    app = QApplication(sys.argv)
    window = TachysEditorWindow()
    window.show()
    sys.exit(app.exec())
