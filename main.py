from PySide6.QtCore import QRegularExpression, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QMainWindow, QMenu, QMessageBox, QFileDialog
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextCursor, QAction
from typing import Callable
from parser import LeidenParser
from transformer import LeidenTransformer
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
    syntax_errors: Signal = Signal(list)

    def __init__(self, parser: LeidenParser):
        super().__init__()
        self.parser = parser
        self.text = ''
        self.previous_text = ''
        self._is_running = True

    def run(self):
        while self._is_running:
            if self.text != self.previous_text:
                current_lines = self.text.split('\n')
                previous_lines = self.previous_text.split('\n')
                lines_changed_indices = []
                for i in range(len(current_lines)):
                    try:
                        if current_lines[i] != previous_lines[i]:
                            lines_changed_indices.append(i)
                    except IndexError:
                        lines_changed_indices.append(i)
                self.parser.parse_line(self.text, lines_changed_indices)
                if not self.parser.errors:
                    self.parser.parse_full(self.text)
                error_info = [(error.id, error.line, error.column) for error in self.parser.errors]
                self.syntax_errors.emit(error_info)
                self.previous_text = self.text
            self.msleep(1000)

    def set_text(self, text):
        self.text = text

    def stop(self):
        self._is_running = False


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.text = '[ ’͵;,·˙\u037e-\u03ce\u03da-\u03e4\u1f00-\u1fb0\u1fb2-\u1fb8\u1fba-\u1fd0\u1fd2-\u1fd8\u1fda-\u1fe0\u1fe2-\u1fe8\u1fea-\u1ffe\u0300-\u0301\u0313-\u0314\u0340-\u0345]'
        self.highlighting_rules = []
        self.set_highlighting_rules()
        self.do_error_highlighting = False
        self.parser_errors = []

    def set_highlighting_rules(self):
        # marked up text
        markup_format = QTextCharFormat()
        markup_format.setForeground(QColor("green"))
        self.highlighting_rules.append((r'\[' + self.text + r'+\]', markup_format))
        self.highlighting_rules.append((f'〚[^〛]+〛', markup_format))
        self.highlighting_rules.append((f'<[^>]+>', markup_format))
        self.highlighting_rules.append((f'<:.*?:>', markup_format))
        self.highlighting_rules.append((r'\{[^}]+\}', markup_format))
        self.highlighting_rules.append((r'\(.*?\)', markup_format))
        self.highlighting_rules.append((r'\\[^\/]+\/', markup_format))
        self.highlighting_rules.append((r'~[^l]+ll', markup_format))
        self.highlighting_rules.append((r'~[^~]+~', markup_format))
        self.highlighting_rules.append((r'/[^\/]+\/', markup_format))
        self.highlighting_rules.append((r'\|.*?\|', markup_format))
        self.highlighting_rules.append((r'\|\|.*?\|\|', markup_format))
        self.highlighting_rules.append((r'¯[^¯]+¯', markup_format))
        self.highlighting_rules.append((r'_[^_]_', markup_format))
        self.highlighting_rules.append((self.text + '\u0323', markup_format))
        self.highlighting_rules.append((self.text + '\u0304|[ᾱᾹῑῙῡῩ]', markup_format))
        # special format
        special_format = QTextCharFormat()
        special_format.setForeground(QColor("blue"))
        self.highlighting_rules.append((r'\$.[^ ]+ ', special_format))
        self.highlighting_rules.append((r'#[a-zA-Z0-9][^ ]+ ', special_format))
        self.highlighting_rules.append((r'###', special_format))
        self.highlighting_rules.append((r'--------', special_format))
        self.highlighting_rules.append((r'----', special_format))
        self.highlighting_rules.append((r'~~~~~~~~', special_format))
        self.highlighting_rules.append((r'>---', special_format))
        self.highlighting_rules.append((r'-\$\$-', special_format))
        self.highlighting_rules.append((r'(ca)?\.[0-9\?]+-?[0-9]*', special_format))
        self.highlighting_rules.append((r'vac\.(ca\.)?[0-9\?]+-?[0-9]*(lin)?', special_format))
        self.highlighting_rules.append((r'lost\.[0-9\?]+-?[0-9]*(lin)?', special_format))
        self.highlighting_rules.append((r'vestig\.[0-9\?]+-?[0-9]*(lin)?', special_format))
        self.highlighting_rules.append((r'\*.+\*', special_format))
        self.highlighting_rules.append((r'=[a-zA-Z, \-:]+', special_format))
        self.highlighting_rules.append((r'=[0-9]+', special_format))
        # keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("darkMagenta"))
        self.highlighting_rules.append((r'ed|reg|subst|alt|corr', keyword_format))
        self.highlighting_rules.append((r'\|', keyword_format))
        self.highlighting_rules.append((r'<:|:>', keyword_format))
        self.highlighting_rules.append((r'<|>', keyword_format))
        self.highlighting_rules.append((r'{|}', keyword_format))
        self.highlighting_rules.append((r'〚|〛', keyword_format))
        self.highlighting_rules.append((r'\[|\]', keyword_format))
        self.highlighting_rules.append((r'\(|\)', keyword_format))
        self.highlighting_rules.append((r'\(?\?\)?', keyword_format))
        self.highlighting_rules.append((r'(left|right|interlin):', keyword_format))
        self.highlighting_rules.append((r'\^|_|#|\\|\/', keyword_format))
        self.highlighting_rules.append((r'¨| ῾|´| ᾿|`', keyword_format))
        # overwrite diacriticals
        self.highlighting_rules.append((r'\((^|¨| ῾|´| ᾿|`)\)', special_format))
        # line numbers
        line_format = QTextCharFormat()
        line_format.setForeground(QColor('darkBlue'))
        self.highlighting_rules.append((r'^[0-9]+\.\-?', line_format))
        self.highlighting_rules.append((r'^\([0-9]+\-?.+\)', line_format))
        self.highlighting_rules.append((r'^[0-9]+\-?,.+\.', line_format))
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
                error_id, line, column = error
                if self.currentBlock().blockNumber() == line - 1:
                    error_format = QTextCharFormat()
                    error_format.setUnderlineColor(QColor("red"))
                    error_format.setForeground(QColor("red"))
                    error_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
                    index = column - 1
                    if error_id == 0:
                        format_count = len(text) - index
                    elif error_id == 1:
                        format_count = len(text) - index
                    elif error_id == 2:
                        column = 2
                        format_count = len(text)
                    else:
                        break
                    self.setFormat(column - 2, format_count + 1, error_format)

    def update_error_highlighting(self, error_data):
        self.do_error_highlighting = True
        self.parser_errors = list(error_data)
        self.rehighlight()
        self.do_error_highlighting = False


class MyPlainTextEdit(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.line_text = ''
        self.line_break = False
        self.paste_mgr = PasteManager()
        self.original_paste_text = ''
        self.selected_text = ''

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            self.line_text = self.get_current_line_text().strip()
            cursor.beginEditBlock()
            if self.line_text[-1] == '-' and not re.fullmatch(r'--|\$-', self.line_text[-2:]) and cursor.atBlockEnd():
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
                text = cursor.selectedText()
                if len(text) > 1:
                    cursor.insertText('¯' + cursor.selectedText() + '¯')
                else:
                    cursor.insertText(text + '\u0304')
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
            line_text = self.get_current_line_text()
            try:
                line_number = re.findall(r'^\(?[0-9]+', line_text)[0]
                line_number = int(line_number)
            except (IndexError, ValueError):
                line_number = None
            self.original_paste_text = pyperclip.paste()
            clipboard_text = pyperclip.paste()
            clipboard_text = unicodedata.normalize('NFC', clipboard_text)
            clipboard_text = self.paste_mgr.replace_lunate_sigma(clipboard_text)
            clipboard_text = self.paste_mgr.replace_underdots(clipboard_text)
            clipboard_text = self.paste_mgr.replace_supralinear_stroke(clipboard_text)
            clipboard_text = self.paste_mgr.replace_brackets(clipboard_text)
            if '\n' in clipboard_text and line_number:
                newline_count = str(clipboard_text).count('\n')
                for i in range(newline_count):
                    clipboard_text = re.sub('\n', f'§{line_number+i+1}. ', clipboard_text, 1)
                clipboard_text = clipboard_text.replace('§', '\n')
            pyperclip.copy(clipboard_text)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        cursor = self.textCursor()
        if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            line_text = self.line_text
            if re.findall(r'^\(?[0-9]+', line_text):
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
        elif (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (event.key() == Qt.Key.Key_V):
            pyperclip.copy(self.original_paste_text)
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
        self.editor = MyPlainTextEdit()
        self.setCentralWidget(self.editor)
        self.editor_font = QFont('Cardo')
        self.editor_font.setPointSize(round(0.011 * self.screen_height))
        self.editor.setFont(self.editor_font)
        self.editor.appendPlainText('<S=.grc\n<D=.1.fragment<=\n1. \n=>=D>')
        self.highlighter = PythonHighlighter(self.editor.document())
        self.setWindowTitle("Leiden+ Editor - New File")
        self.resize(self.width, self.height)
        self.file_dialog = QFileDialog()
        self.msg = QMessageBox()
        self.file_path = ''
        self.init_ui()
        # Background Processes
        self.parser = LeidenParser()
        self.transformer = LeidenTransformer()
        self.worker = DebugWorker(parser=self.parser)
        self.worker.syntax_errors.connect(self.highlight_errors)
        self.syntax_check_timer = QTimer(self)
        self.syntax_check_timer.timeout.connect(self.push_text_to_worker)
        QTimer.singleShot(2000, self.activate_debugging)


    def highlight_errors(self, error_data):
        self.highlighter.update_error_highlighting(error_data)

    def activate_debugging(self):
        self.worker.start()
        self.syntax_check_timer.start(500)
        self.push_text_to_worker()

    def push_text_to_worker(self):
        self.worker.set_text(self.editor.toPlainText())

    def init_ui(self):
        self.set_cursor_position(3, 3)
        # Menu Bar
        menubar = self.menuBar()
        # File Menu
        file_menu = menubar.addMenu('File')
        self.add_menu_action(file_menu, 'New', self.new_file, 'Ctrl+N')
        self.add_menu_action(file_menu, 'Open', self.open_file, 'Ctrl+O')
        self.add_menu_action(file_menu, 'Save', lambda: self.save_file(False), 'Ctrl+S')
        self.add_menu_action(file_menu, 'Save As', lambda: self.save_file(True), 'Ctrl+Alt+S')
        self.add_menu_action(file_menu, 'Export to XML', self.export_to_xml, 'Ctrl+E')
        # Insert Menu
        insert_menu = menubar.addMenu('Insert')
        submenu_diacriticals = QMenu('Ancient Diacriticals', self)
        self.add_menu_action(submenu_diacriticals, 'Acute', lambda: self.insert_str('´'))
        self.add_menu_action(submenu_diacriticals, 'Asper', lambda: self.insert_str(' ῾'))
        self.add_menu_action(submenu_diacriticals, 'Circumflex', lambda: self.insert_str('^'))
        self.add_menu_action(submenu_diacriticals, 'Diaresis', lambda: self.insert_str('¨'))
        self.add_menu_action(submenu_diacriticals, 'Grave', lambda: self.insert_str('`'))
        self.add_menu_action(submenu_diacriticals, 'Lenis', lambda: self.insert_str(' ᾿'))
        insert_menu.addMenu(submenu_diacriticals)
        submenu_apparatus = QMenu('Apparatus', self)
        self.add_menu_action(submenu_apparatus, 'Alternate Reading', lambda: self.insert_str('<:{text}|alt|:>'))
        self.add_menu_action(submenu_apparatus, 'Alternate Reading (multiple)', lambda: self.insert_str('<:{text}||alt||α|β:>'))
        self.add_menu_action(submenu_apparatus, 'Editorial Correction', lambda: self.insert_str('<:{text}|ed|:>'))
        self.add_menu_action(submenu_apparatus, 'Editorial Correction (multiple)', lambda: self.insert_str('<:{text}||ed||α|β:>'))
        self.add_menu_action(submenu_apparatus, 'Orthographic Regularization', lambda: self.insert_str('<:|reg|{text}:>'))
        self.add_menu_action(submenu_apparatus, 'Orthographic Regularization (multiple)', lambda: self.insert_str('<:α|β||reg||{text}:>'))
        self.add_menu_action(submenu_apparatus, 'Scribal Correction', lambda: self.insert_str('<:{text}|subst|:>'))
        self.add_menu_action(submenu_apparatus, 'Spelling Correction', lambda: self.insert_str('<:|corr|{text}:>'))
        insert_menu.addMenu(submenu_apparatus)
        self.add_menu_action(insert_menu, 'Deletion\tCtrl+D', lambda: self.insert_str('〚〛'))
        self.add_menu_action(insert_menu, 'Numeral\tCtrl+0', lambda: self.insert_str('<#=#>'))
        self.add_menu_action(insert_menu, 'Numeral Tick', lambda: self.insert_str(" '"))
        self.add_menu_action(insert_menu, 'Paragraphos', lambda: self.insert_str('----'), 'Ctrl+P')
        self.add_menu_action(insert_menu, 'Supralinear Stroke\tCtrl+[MINUS]', lambda: self.insert_str('\u0304'))
        self.add_menu_action(insert_menu, 'Underdot\tCtrl +[PERIOD]', lambda: self.insert_str('\u0323'))

    def export_to_xml(self):
        text = self.editor.toPlainText()
        tree = self.parser.parse_full(text)
        if tree:
            xml = self.transformer.transform(tree)
            self.msg.setWindowTitle('Preview')
            self.msg.setInformativeText('Click "Show Details" to inspect transformer results. File export not yet implemented.')
            self.msg.setDetailedText(xml)
            self.msg.setVisible(True)
        else:
            self.msg.warning(self, 'Export Error', 'There are unhandled errors in the Leiden+ code.')

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
        text = cursor.selectedText()
        if not text:
            text = ''
        string = string.format(text=text)
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
        self.setWindowTitle(f'Leiden+ Editor - New File')
        self.set_cursor_position(3, 3)
        self.file_path = ''

    def open_file(self):
        path, _ = self.file_dialog.getOpenFileName(filter='*.leiden')
        if path:
            with open(path, 'r', encoding='utf-8') as file:
                text = file.read()
            self.editor.setPlainText(text)
            self.setWindowTitle(f'Leiden+ Editor - {path}')
            self.file_path = path

    def save_file(self, show_dialog):
        if show_dialog:
            path, _ = self.file_dialog.getSaveFileName(filter='*.leiden')
        else:
            path = self.file_path
        if path:
            with open(path, 'w', encoding='utf-8') as file:
                file.write(self.editor.toPlainText())
                self.file_path = path
                self.setWindowTitle(f'Leiden+ Editor - {path}')
        return

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = LeidenEditor()
    editor.show()
    sys.exit(app.exec())
