import sys

from PySide6.QtWidgets import QApplication

from tachys_editor.ui.window import TachysEditorWindow


def catch_exceptions(exctype, value, traceback):
    print("An exception occurred:")
    sys.__excepthook__(exctype, value, traceback)
    sys.exit(1)

sys.excepthook = catch_exceptions


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TachysEditorWindow()
    window.show()
    sys.exit(app.exec())
