from PyQt6.QtCore import QRegularExpression, Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication, QPlainTextEdit, QMainWindow, QFontDialog, QMenu
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextCursor, QAction
from typing import Callable
from parser import LeidenParser
from shared import greek_pattern
from addon import PasteManager, format_numerals
import sys
import re
import roman
import pyperclip
import unicodedata


def catch_exceptions(exctype, value, traceback):
    print("An exception occurred:")
    sys.__excepthook__(exctype, value, traceback)
    sys.exit(1)

sys.excepthook = catch_exceptions


class DebugWorker(QThread):
    syntax_errors: pyqtSignal = pyqtSignal(list)

    def __init__(self, parser: LeidenParser):
        super().__init__()
        self.parser = parser
        self.text = ''
        self.previous_text = ''
        self._is_running = True

    def run(self):
        while self._is_running:
            if self.text != self.previous_text:
                self.parser.parse(self.text)
                error_positions = [(error.line, error.column) for error in self.parser.errors]
                self.syntax_errors.emit(error_positions)
                self.previous_text = self.text
            self.msleep(500)

    def set_text(self, text):
        self.text = text

    def stop(self):
        self._is_running = False


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.greek_pattern = greek_pattern
        self.highlighting_rules = []
        self.set_highlighting_rules()
        self.do_error_highlighting = False
        self.parser_errors = []

    def set_highlighting_rules(self):
        # line numbers
        line_format = QTextCharFormat()
        line_format.setForeground(QColor('darkBlue'))
        self.highlighting_rules.append((r'^[0-9]+\.\-?', line_format))
        # default Greek text
        text_format = QTextCharFormat()
        text_format.setForeground(QColor('black'))
        self.highlighting_rules.append((f'[{self.greek_pattern} ]+', text_format))
        # special = symbol, supplied characters + lost characters, deletion
        special_format = QTextCharFormat()
        special_format.setForeground(QColor("green"))
        self.highlighting_rules.append((r'\*[a-zA-Z\-]+\*', special_format))
        self.highlighting_rules.append((r'\[[' + self.greek_pattern + r' \.\-\?0-9]+\]', special_format))
        self.highlighting_rules.append((f'〚[{self.greek_pattern}]+〛', special_format))
        self.highlighting_rules.append((r'\.[0-9\?]+-?[0-9]*', special_format))
        self.highlighting_rules.append((f'<[{self.greek_pattern}]+>', special_format))
        self.highlighting_rules.append((r'\{[' + self.greek_pattern + r']+\}', special_format))
        self.highlighting_rules.append((r'\([' + self.greek_pattern + r']+\)', special_format))
        self.highlighting_rules.append((r'[' + self.greek_pattern + ']\u0323', special_format))
        # div
        div_format = QTextCharFormat()
        div_format.setForeground(QColor("darkBlue"))
        self.highlighting_rules.append((r'<D=.+<=', div_format))
        self.highlighting_rules.append((r'=>=D>', div_format))
        # super_div
        super_div_format = QTextCharFormat()
        super_div_format.setForeground(QColor("purple"))
        self.highlighting_rules.append((r'<D=.[0-9a-z\.]+$', super_div_format))
        self.highlighting_rules.append((r'^=D>$', super_div_format))
        # default language
        def_lang_format = QTextCharFormat()
        def_lang_format.setForeground(QColor("purple"))
        self.highlighting_rules.append((r'<S=\.[a-zA-Z-]+', def_lang_format))

    def highlightBlock(self, text):
        for pattern, formatting in self.highlighting_rules:
            expression = QRegularExpression(pattern)
            match = expression.match(text)
            index = match.capturedStart()
            while index >= 0:
                length = match.capturedLength()
                self.setFormat(index, length, formatting)
                match = expression.match(text, index + length)
                index = match.capturedStart()
        if self.do_error_highlighting:
            for error in self.parser_errors:
                line, column = error
                if self.currentBlock().blockNumber() == line - 1:
                    error_format = QTextCharFormat()
                    error_format.setUnderlineColor(QColor("red"))
                    error_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
                    self.setFormat(column - 1, len(text) - column + 1, error_format)

    def update_error_highlighting(self, error_data):
        self.do_error_highlighting = True
        self.parser_errors = list(error_data)
        self.rehighlight()
        self.do_error_highlighting = False


class MyPlainTextEdit(QPlainTextEdit):
    def __init__(self, suggestions):
        super().__init__()
        self.line_text = ''
        self.suggestions = suggestions
        self.line_break = False
        self.paste_mgr = PasteManager()
        self.selected_text = ''

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            self.line_text = self.get_current_line_text().strip()
            cursor.beginEditBlock()
            if self.line_text[-1] == '-' and not self.line_text[-2:] == '--' and cursor.atBlockEnd():
                self.line_break = True
                cursor.deletePreviousChar()
        elif (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (event.key() == Qt.Key.Key_Period):
            if cursor.hasSelection():
                replacement = ''
                for char in cursor.selectedText():
                    replacement += char + '\u0323'
                cursor.insertText(replacement)
            else:
                cursor.insertText('\u0323')
        elif (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (event.key() == Qt.Key.Key_Minus):
            if cursor.hasSelection():
                cursor.insertText('¯' + cursor.selectedText() + '¯')
            else:
                cursor.insertText('\u0304')
        elif (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (event.key() == Qt.Key.Key_D):
            if cursor.hasSelection():
                cursor.insertText('〚' + cursor.selectedText() + '〛')
            else:
                cursor.insertText('〚〛')
                cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, 1)
                self.setTextCursor(cursor)
        elif (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (event.key() == Qt.Key.Key_0):
            if cursor.hasSelection():
                numeral = format_numerals(cursor.selectedText())
                cursor.insertText(numeral)
            else:
                cursor.insertText('<#=#>')
                cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, 2)
                self.setTextCursor(cursor)
        elif event.key() == Qt.Key.Key_BracketLeft or event.key() == Qt.Key.Key_ParenLeft or event.key() == Qt.Key.Key_BraceLeft:
            self.selected_text = cursor.selectedText()
        elif (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (event.key() == Qt.Key.Key_V):
            # run operations with clipboard text, e.g. replace lunate sigma or convert whole Leiden input to Leiden+
            clipboard_text = pyperclip.paste()
            clipboard_text = unicodedata.normalize('NFC', clipboard_text)
            clipboard_text = self.paste_mgr.replace_lunate_sigma(clipboard_text)
            clipboard_text = self.paste_mgr.replace_underdots(clipboard_text)
            clipboard_text = self.paste_mgr.replace_supralinear_stroke(clipboard_text)
            pyperclip.copy(clipboard_text)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        cursor = self.textCursor()
        if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            line_text = self.line_text
            if re.findall(r'^[0-9]+\.-?', line_text):
                line_number = int(re.findall(r'[0-9]+', line_text)[0])
                if self.line_break:
                    cursor.insertText(f'{line_number + 1}.- ')
                    self.line_break = False
                else:
                    cursor.insertText(f'{line_number + 1}. ')
            elif re.findall(r'=>=D>', line_text):
                try:
                    last_div = re.findall(r'<D=\.[0-9a-z]+\.[a-z]+', self.toPlainText())[-1]
                    div_type = re.findall(r'[a-z]+', last_div)[-1]
                except IndexError:
                    return
                if last_div:
                    try:
                        div_number = int(re.findall(r'[0-9]+', last_div)[0])
                        cursor.insertText(f'<D=.{div_number + 1}.{div_type}<=\n1. \n=>=D>')
                    except IndexError:
                        try:
                            div_roman = re.findall(r'\.[ivxlcdm]+\.', last_div)[0]
                            roman_num = div_roman.replace('.', '')
                            arabic_num = roman.fromRoman(roman_num)
                            arabic_num += 1
                            roman_num = roman.toRoman(arabic_num)
                            cursor.insertText(f'<D=.{roman_num.lower()}.{div_type}<=\n1. \n=>=D>')
                        except IndexError:
                            cursor.insertText(f'<D=.next.{div_type}<=\n1. \n=>=D>')
                else:
                    cursor.insertText(f'<D=.1.fragment<=\n1. \n=>=D>')
                cursor.movePosition(QTextCursor.MoveOperation.Up, QTextCursor.MoveMode.MoveAnchor, 1)
                cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, 3)
                self.setTextCursor(cursor)
            cursor.endEditBlock()
        elif event.key() == Qt.Key.Key_BracketLeft:
            if self.selected_text:
                cursor.insertText(self.selected_text + ']')
                self.selected_text = ''
            elif cursor.atBlockEnd():
                cursor.insertText(']')
                cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, 1)
                self.setTextCursor(cursor)
        elif event.key() == Qt.Key.Key_ParenLeft:
            if self.selected_text:
                cursor.insertText(self.selected_text + ')')
                self.selected_text = ''
            elif cursor.atBlockEnd():
                cursor.insertText(')')
                cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, 1)
                self.setTextCursor(cursor)
        elif event.key() == Qt.Key.Key_BraceLeft:
            if self.selected_text:
                cursor.insertText(self.selected_text + '}')
            elif cursor.atBlockEnd():
                cursor.insertText('}')
                cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, 1)
                self.setTextCursor(cursor)
        super().keyReleaseEvent(event)

    def get_current_line_text(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        line_text = cursor.selectedText()
        return line_text


class LeidenEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialize Window
        screen = app.primaryScreen()
        size = screen.size()
        self.screen_width = size.width()
        self.screen_height = size.height()
        self.width = round(0.75 * self.screen_width)
        self.height = round(0.75 * self.screen_height)
        # Initialize Editor
        self.editor = MyPlainTextEdit(suggestions=[])
        self.setCentralWidget(self.editor)
        self.editor_font = QFont('Cardo')
        self.editor_font.setPointSize(round(0.011 * self.screen_height))
        self.editor.setFont(self.editor_font)
        self.editor.appendPlainText('<S=.grc\n<D=.1.fragment<=\n1. \n=>=D>')
        self.highlighter = PythonHighlighter(self.editor.document())
        self.setWindowTitle("Leiden+ Editor")
        self.resize(self.width, self.height)
        self.init_ui()
        # Background Processes
        self.parser = LeidenParser()
        self.worker = DebugWorker(parser=self.parser)
        self.worker.syntax_errors.connect(self.highlight_errors)
        self.syntax_check_timer = QTimer(self)
        self.syntax_check_timer.timeout.connect(self.push_text_to_worker)
        QTimer.singleShot(2000, self.activate_debugging)


    def highlight_errors(self, error_data):
        self.highlighter.update_error_highlighting(error_data)

    def activate_debugging(self):
        self.worker.start()
        self.syntax_check_timer.start(2000)
        self.push_text_to_worker()

    def push_text_to_worker(self):
        self.worker.set_text(self.editor.toPlainText())

    def init_ui(self):
        self.set_cursor_position(3, 3)
        # Menu Bar
        menubar = self.menuBar()
        # File Menu
        file_menu = menubar.addMenu('File')
        self.add_menu_action(file_menu, 'New\n(Ctrl + N)', self.new_file, 'Ctrl+N')
        self.add_menu_action(file_menu, 'Save\t(Ctrl + S)', self.save_file, 'Ctrl+S')
        # Insert Menu
        insert_menu = menubar.addMenu('Insert')
        submenu_diacriticals = QMenu('Ancient Diacriticals', self)
        self.add_menu_action(submenu_diacriticals, 'Acute', lambda: self.insert_str('´'))
        self.add_menu_action(submenu_diacriticals, 'Asper', lambda: self.insert_str('῾'))
        self.add_menu_action(submenu_diacriticals, 'Circumflex', lambda: self.insert_str('^'))
        self.add_menu_action(submenu_diacriticals, 'Diaresis', lambda: self.insert_str('¨'))
        self.add_menu_action(submenu_diacriticals, 'Grave', lambda: self.insert_str('`'))
        self.add_menu_action(submenu_diacriticals, 'Lenis', lambda: self.insert_str('᾿'))
        insert_menu.addMenu(submenu_diacriticals)
        self.add_menu_action(insert_menu, 'Deletion\t(Ctrl + D)', lambda: self.insert_str('〚〛'))
        self.add_menu_action(insert_menu, 'Numeral\t(Ctrl + 0)', lambda: self.insert_str('<#=#>'))
        self.add_menu_action(insert_menu, 'Paragraphos\t(Ctrl + P])', lambda: self.insert_str('----'), 'Ctrl+P')
        self.add_menu_action(insert_menu, 'Supralinear Stroke\t(Ctrl + [MINUS])', lambda: self.insert_str('\u0304'))
        self.add_menu_action(insert_menu, 'Underdot\t(Ctrl + [PERIOD])', lambda: self.insert_str('\u0323'))

    def add_menu_action(self, menu: QMenu, action_name: str, action_connector: Callable = None, shortcut: str = None):
        action = QAction(action_name, self)
        if shortcut:
            action.setShortcut(shortcut)
        if action_connector:
            action.triggered.connect(action_connector)
        menu.addAction(action)
        return action

    def insert_str(self, string: str):
        cursor = self.editor.textCursor()
        cursor.insertText(string)

    def set_cursor_position(self, line, column):
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, line - 1)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, column)
        self.editor.setTextCursor(cursor)

    def new_file(self):
        self.editor.clear()
        self.editor.appendPlainText('<S=.grc\n<D=.1.fragment<=\n1. \n=>=D>')

    def save_file(self):
        return

    def change_font(self):
        current_font = self.editor.font()
        font, ok = QFontDialog.getFont(current_font, self, "Select Font")
        if ok:
            self.editor.setFont(font)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = LeidenEditor()
    editor.show()
    sys.exit(app.exec())
