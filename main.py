from PySide6.QtWidgets import QApplication
import sys
from ui.window import LeidenEditorWindow


def catch_exceptions(exctype, value, traceback):
    print("An exception occurred:")
    sys.__excepthook__(exctype, value, traceback)
    sys.exit(1)

sys.excepthook = catch_exceptions


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = LeidenEditorWindow()
    editor.show()
    sys.exit(app.exec())
