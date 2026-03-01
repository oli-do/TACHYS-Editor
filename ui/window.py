from os.path import basename
from pathlib import Path
import pickle
from PySide6.QtGui import QFont, QTextCursor, QAction, QTextCharFormat
from PySide6.QtWidgets import QMainWindow, QMenu, QMessageBox, QFileDialog, QApplication
from typing import Callable
from core.parser import LeidenParser
from core.change_tracker import ChangeTracker
from ui.editor import LeidenEditor
from core.transformer import LeidenTransformer

tracking_directory = 'changes'


class LeidenEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.parser = LeidenParser()
        self.transformer = LeidenTransformer()
        self.tracker = ChangeTracker(tracking_directory)
        # Settings
        self.saving_enabled = True
        self.imported_change_log = None
        self.original_text = ''
        # Initialize Window
        screen = QApplication.primaryScreen()
        size = screen.size()
        self.screen_width = size.width()
        self.screen_height = size.height()
        self.width = round(0.75 * self.screen_width)
        self.height = round(0.75 * self.screen_height)
        window_font = self.font()
        window_font.setPointSize((round(0.01 * self.screen_height)))
        self.setFont(window_font)
        # Initialize Editor
        self.editor = LeidenEditor()
        self.setCentralWidget(self.editor)
        self.editor_font = QFont('Cardo')
        self.editor_font.setPointSize(round(0.013 * self.screen_height))
        self.editor.setFont(self.editor_font)
        self.resize(self.width, self.height)
        self.file_dialog = QFileDialog()
        self.msg = QMessageBox()
        self.file_path = ''
        # Menus
        self.menubar = self.menuBar()
        self.init_ui()
        self.action_track_changes = self.get_menu_action(self.menubar, 'Track Changes')
        self.action_view_changes = self.get_menu_action(self.menubar, 'View Changes')
        # New File
        self.new_file()

    def get_menu_action(self, parent, action_name: str):
        for action in parent.actions():
            if action.text() == action_name:
                return action
            if action.menu():
                result = self.get_menu_action(action.menu(), action_name)
                if result:
                    return result
        return None

    @staticmethod
    def set_checked_no_signal(action, checked: bool):
        action.blockSignals(True)
        action.setChecked(checked)
        action.blockSignals(False)

    def init_ui(self):
        self.set_cursor_position(3, 3)
        # File Menu
        file_menu = self.menubar.addMenu('File')
        self.add_menu_action(file_menu, 'New', self.new_file, 'Ctrl+N')
        self.add_menu_action(file_menu, 'Open', lambda: self.open_file(), 'Ctrl+O')
        self.add_menu_action(file_menu, 'Save', lambda: self.save_file(False, self.create_leiden_file()), 'Ctrl+S')
        self.add_menu_action(file_menu, 'Save As', lambda: self.save_file(True, self.create_leiden_file()), 'Ctrl+Alt+S')
        self.add_menu_action(file_menu, 'Export to XML', self.export_to_xml, 'Ctrl+E')
        self.add_menu_action(file_menu, 'Export to TXT', self.export_to_txt, 'Ctrl+Alt+E')
        # Insert Menu
        insert_menu = self.menubar.addMenu('Insert')
        submenu_diacriticals = QMenu('Ancient Diacriticals', self)
        self.add_menu_action(submenu_diacriticals, 'Acute', lambda: self.insert_str('(´)'))
        self.add_menu_action(submenu_diacriticals, 'Asper', lambda: self.insert_str('( ῾)'))
        self.add_menu_action(submenu_diacriticals, 'Circumflex', lambda: self.insert_str('(^)'))
        self.add_menu_action(submenu_diacriticals, 'Diaresis', lambda: self.insert_str('(¨)'))
        self.add_menu_action(submenu_diacriticals, 'Grave', lambda: self.insert_str('(`)'))
        self.add_menu_action(submenu_diacriticals, 'Lenis', lambda: self.insert_str('( ᾿)'))
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
        # Changes Menu
        changes_menu = self.menubar.addMenu('Changes')
        changes_menu.setToolTipsVisible(True)
        track_changes_action = self.add_menu_action(changes_menu, 'Track Changes', lambda checked: self.start_tracking(checked), tooltip='Sets your current Leiden+ text as a reference and tracks changes')
        track_changes_action.setCheckable(True)
        import_change_log_action = self.add_menu_action(changes_menu, 'Import Change Log', lambda checked: self.import_change_log(checked), tooltip='Import an external change log')
        import_change_log_action.setCheckable(True)
        view_changes_action = self.add_menu_action(changes_menu, 'View Changes', lambda checked: self.view_changes(checked), tooltip='Shows changes, prioritizes imported change logs')
        view_changes_action.setCheckable(True)
        self.add_menu_action(changes_menu, 'Export Change Log', self.export_change_log, tooltip='Export your changes to a file')

    def start_tracking(self, checked):
        if checked:
            if not self.file_path:
                if not self.save_file(True, self.create_leiden_file()):
                    self.set_checked_no_signal(self.action_track_changes, False)
                    return
            self.tracker.active = True
            self.tracker.write_changes(basename(self.file_path), self.editor.toPlainText())
            self.tracker.commit_changes()
        else:
            msg = QMessageBox.warning(self, 'Reset Change Tracking', 'Be aware that this action will fully reset your change tracking!', buttons=QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            if msg == QMessageBox.StandardButton.Ok:
                self.tracker.active = False
            else:
                self.set_checked_no_signal(self.action_track_changes, True)

    def export_change_log(self):
        if self.tracker.active and self.saving_enabled:
            self.save_file(False, self.create_leiden_file())
            path, _ = self.file_dialog.getSaveFileName(filter='*.leiden_changelog *.txt')
            if path:
                suffix = Path(path).suffix
                with open(path, 'wb') as f:
                    if suffix == '.leiden_changelog':
                        pickle.dump(self.tracker.parse_word_diff(basename(self.file_path)), f)
                    else:
                        self.tracker.write_change_log(path, basename(self.file_path))

    def import_change_log(self, checked):
        if checked:
            path, _ = self.file_dialog.getOpenFileName(filter='*.leiden_changelog')
            if path:
                with open(path, 'rb') as f:
                    self.imported_change_log = pickle.load(f)
            else:
                self.get_menu_action(self.menubar, 'Import Change Log').setChecked(False)
        else:
            self.imported_change_log = None

    def view_changes(self, checked):
        scrollbar = self.editor.verticalScrollBar()
        scroll_position = scrollbar.value()
        if checked:
            if self.tracker.active or self.imported_change_log:
                if self.file_path:
                    self.original_text = ''
                    self.save_file(False, self.create_leiden_file())
                else:
                    self.original_text = self.editor.toPlainText()
                self.saving_enabled = False
                if not self.imported_change_log:
                    diffs = self.tracker.parse_word_diff(basename(self.file_path))
                else:
                    diffs = self.imported_change_log
                self.editor.show_changes(diffs)
            else:
                self.action_view_changes.setChecked(False)
        else:
            self.editor.setCurrentCharFormat(QTextCharFormat())
            if self.file_path:
                self.open_file(self.file_path)
                self.editor.continue_debugging()
                self.saving_enabled = True
            else:
                self.editor.setPlainText(self.original_text)
                self.editor.continue_debugging()
        scrollbar.setValue(scroll_position)

    def export_to_txt(self):
        text = self.editor.toPlainText()
        self.save_file(True, text, '*.txt')

    def export_to_xml(self):
        text = self.editor.toPlainText()
        tree = self.parser.parse_full(text)
        if tree:
            xml = self.transformer.transform(tree)
            self.save_file(True, xml, '*.xml')
        else:
            self.msg.warning(self, 'Export Error', 'There are unhandled errors in the Leiden+ code.')

    def add_menu_action(self, menu: QMenu, action_name: str, action_connector: Callable = None, shortcut: str = None, tooltip: str = None):
        action = QAction(action_name, self)
        if shortcut:
            action.setShortcut(shortcut)
        if action_connector:
            action.triggered.connect(action_connector)
        if tooltip:
            action.setToolTip(tooltip)
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

    def reset(self):
        self.editor.clear()
        self.tracker.active = False
        self.set_checked_no_signal(self.action_track_changes, False)
        self.saving_enabled = True
        self.set_checked_no_signal(self.action_view_changes, False)
        self.editor.setReadOnly(False)

    def new_file(self):
        self.reset()
        self.editor.appendPlainText('<S=.grc\n<D=.1.fragment<=\n1. \n=>=D>')
        self.setWindowTitle(f'Leiden+ Editor - New File')
        self.set_cursor_position(3, 3)
        self.file_path = ''

    def open_file(self, path=None):
        if not path:
            path, _ = self.file_dialog.getOpenFileName(filter='*.leiden *.txt')
        if path:
            self.reset()
            with open(path, 'r', encoding='utf-8') as file:
                file_content = file.read()
            data = file_content.split('\ue747')
            if data[0] == '0.1.0':
                settings = data[1].split(';')
                if len(settings) >= 1:
                    if bool(settings[0]):
                        if self.tracker.request_active(basename(path)):
                            self.set_checked_no_signal(self.action_track_changes, True)
                        else:
                            self.set_checked_no_signal(self.action_track_changes, False)
                text = data[2]
            else:
                self.tracker.request_active(basename(path))
                text = file_content
            self.editor.setPlainText(text)
            self.editor.start_debugging()
            self.setWindowTitle(f'Leiden+ Editor - {path}')
            self.file_path = path

    def create_leiden_file(self):
        splitter = '\ue747'
        # 1st line: file version
        text = '0.1.0' + splitter
        # 2nd line: settings (split by semicolon)
        if self.tracker.active:
            text += '1;'
        else:
            text += '0;'
        # 3rd line: text
        text += splitter + self.editor.toPlainText()
        return text

    def save_file(self, show_dialog, text_to_write: str, file_filter='*.leiden'):
        if not self.saving_enabled:
            QMessageBox.warning(self, 'Saving Disabled', 'Due to the current viewing mode, saving is disabled.')
            return False
        if show_dialog or not self.file_path:
            path, _ = self.file_dialog.getSaveFileName(filter=file_filter)
        elif file_filter == '*.leiden':
            path = self.file_path
        else:
            return False
        if path:
            with open(path, 'w', encoding='utf-8') as file:
                file.write(text_to_write)
            if file_filter == '*.leiden':
                self.file_path = path
                self.setWindowTitle(f'Leiden+ Editor - {path}')
                if self.tracker.active:
                    self.tracker.write_changes(basename(self.file_path), self.editor.toPlainText())
            return True
        else:
            return False