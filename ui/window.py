from PySide6.QtGui import QFont, QTextCursor, QAction, Qt
from PySide6.QtWidgets import QMainWindow, QMenu, QMessageBox, QFileDialog, QApplication
from typing import Callable
from core.parser import LeidenParser
from ui.editor import LeidenEditor
from core.transformer import LeidenTransformer


class LeidenEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialize Window
        screen = QApplication.primaryScreen()
        size = screen.size()
        self.screen_width = size.width()
        self.screen_height = size.height()
        self.width = round(0.75 * self.screen_width)
        self.height = round(0.75 * self.screen_height)
        # Initialize Editor
        self.editor = LeidenEditor()
        self.setCentralWidget(self.editor)
        self.editor_font = QFont('Cardo')
        self.editor_font.setPointSize(round(0.011 * self.screen_height))
        self.editor.setFont(self.editor_font)
        self.editor.appendPlainText('<S=.grc\n<D=.1.fragment<=\n1. \n=>=D>')
        self.setWindowTitle("Leiden+ Editor - New File")
        self.resize(self.width, self.height)
        self.file_dialog = QFileDialog()
        self.msg = QMessageBox()
        self.file_path = ''
        self.init_ui()
        # Parser and Transformer
        self.parser = LeidenParser()
        self.transformer = LeidenTransformer()

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
        tree = self.parser.parse_full(text, False)
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
            self.editor.start_debugging()
            self.setWindowTitle(f'Leiden+ Editor - {path}')
            self.file_path = path

    def save_file(self, show_dialog):
        if show_dialog or not self.file_path:
            path, _ = self.file_dialog.getSaveFileName(filter='*.leiden')
        else:
            path = self.file_path
        if path:
            with open(path, 'w', encoding='utf-8') as file:
                file.write(self.editor.toPlainText())
                self.file_path = path
                self.setWindowTitle(f'Leiden+ Editor - {path}')
        return