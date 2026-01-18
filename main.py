from PyQt5.QtCore import QRegExp, Qt
from PyQt5.QtWidgets import QApplication, QPlainTextEdit, QMainWindow, QAction, QFontDialog, QDesktopWidget, \
    QMessageBox, QListWidget
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextCursor
from parser import LeidenParser
import sys
import re


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.greek_pattern = '\u0370-\u03FF\u1F00-\u1FFF\u0300-\u036F'
        self.highlighting_rules = []
        div_format = QTextCharFormat()
        div_format.setForeground(QColor("blue"))
        self.highlighting_rules.append((r'<D=.+<=', div_format))
        self.highlighting_rules.append((r'=>=D>', div_format))
        s_format = QTextCharFormat()
        s_format.setForeground(QColor('green'))
        self.highlighting_rules.append((f'[{self.greek_pattern}]+', s_format))
        super_div_format = QTextCharFormat()
        super_div_format.setForeground(QColor("purple"))
        self.highlighting_rules.append((r'<D=.[0-9a-z\.]+$', super_div_format))
        self.highlighting_rules.append((r'^=D>$', super_div_format))
        special_format = QTextCharFormat()
        special_format.setForeground(QColor("orange"))
        self.highlighting_rules.append((r'\*[a-z\-]+\*', special_format))
        self.highlighting_rules.append((r'\[[a-z\.\-\?0-9]+\]', special_format))
        self.highlighting_rules.append((r'[\[\]]', special_format))

    def highlightBlock(self, text):
        for pattern, formatting in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, formatting)
                index = expression.indexIn(text, index + length)


class MyPlainTextEdit(QPlainTextEdit):
    def __init__(self, suggestions):
        super().__init__()
        self.line_text = ''
        self.parser = LeidenParser()
        self.suggestions = suggestions

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            self.line_text = self.get_current_line_text()
            self.parser.parse(self.toPlainText())
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            line_text = self.line_text
            if re.findall(r'^[0-9]+\. ', line_text):
                line_number = int(re.findall(r'[0-9]+', line_text)[0])
                cursor = self.textCursor()
                cursor.insertText(f'{line_number + 1}. ')
            elif re.findall(r'=>=D>', line_text):
                cursor = self.textCursor()
                last_div = re.findall(r'<D=\.[0-9a-z]+\.[a-z]+', self.toPlainText())[-1]
                div_type = re.findall(r'[a-z]+', last_div)[-1]
                if last_div:
                    try:
                        div_number = int(re.findall(r'[0-9]+', last_div)[0])
                        cursor.insertText(f'<D=.{div_number + 1}.{div_type}<=\n1. \n=>=D>')
                    except IndexError:
                        cursor.insertText(f'<D=.next.{div_type}<=\n1. \n=>=D>')
                else:
                    cursor.insertText(f'<D=.1.fragment<=\n1. \n=>=D>')
                cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor, 1)
                self.setTextCursor(cursor)
        super().keyReleaseEvent(event)

    def get_current_line_text(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.LineUnderCursor)
        line_text = cursor.selectedText()
        return line_text


class CodeEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        screen = QDesktopWidget().screenGeometry()
        self.screen_width = round(0.75 * screen.width())
        self.screen_height = round(0.75 * screen.height())
        self.editor = MyPlainTextEdit(suggestions=['apple', 'apricot', 'banana'])
        self.setCentralWidget(self.editor)
        self.editor_font = QFont('IFAOGrecUnicode')
        self.editor_font.setPointSize(round(0.01 * self.screen_height))
        self.menu_font = QFont()
        self.menu_font.setPointSize(round(0.0075 * self.screen_height))
        self.editor.setFont(self.editor_font)
        self.editor.appendPlainText('<S=.grc\n<D=.1.fragment<=\n1. \n=>=D>')
        self.highlighter = PythonHighlighter(self.editor.document())
        self.setWindowTitle("Leiden+ Editor")
        self.resize(self.screen_width, self.screen_height)
        self.init_ui()

    def init_ui(self):
        self.set_cursor_position(3, 3)
        # Create a menu bar
        menubar = self.menuBar()
        menubar.setFont(self.menu_font)
        # Create a File menu and add actions
        file_menu = menubar.addMenu('File')
        new_action = QAction('New', self)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)

    def set_cursor_position(self, line, column):
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, line - 1)
        cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, column)
        self.editor.setTextCursor(cursor)

    def new_file(self):
        QMessageBox.information(self, 'New File', 'New file action triggered.')
        self.editor.clear()
        self.editor.appendPlainText('<S=.grc\n<D=.1.fragment<=\n1. \n=>=D>')

    def change_font(self):
        current_font = self.editor.font()
        font, ok = QFontDialog.getFont(current_font, self, "Select Font")
        if ok:
            self.editor.setFont(font)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = CodeEditor()
    editor.show()
    sys.exit(app.exec_())
