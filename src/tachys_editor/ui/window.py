import json
import os
import uuid
from os.path import basename
from pathlib import Path
from typing import Callable

from PySide6.QtGui import QFont, QTextCursor, QAction, QTextCharFormat
from PySide6.QtWidgets import QMainWindow, QMenu, QMessageBox, QFileDialog, QApplication
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

from .editor import TachysEditor
from ..core.change_tracker import ChangeTracker
from ..core.parser import TachysParser
from ..core.transformer import LeidenPlusTransformer
from ..core.ai import AIManager
from ..shared.settings import tracking_dir, settings_mgr, app_name

from importlib.resources import files
documentation_path = str(files('tachys_editor.resources').joinpath('leiden_plus_documentation.html'))


class TachysEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.webview = QWebEngineView()
        self.parser = TachysParser()
        self.transformer = LeidenPlusTransformer()
        self.tracker = ChangeTracker(tracking_dir)
        self.ai_mgr = AIManager()
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
        self.editor = TachysEditor()
        self.setCentralWidget(self.editor)
        self.editor.default_font_size = (round(0.013 * self.screen_height))
        self.editor_font = QFont('Cardo')
        self.editor_font.setPointSize(self.editor.default_font_size * settings_mgr.zoom_level)
        self.editor.setFont(self.editor_font)
        self.resize(self.width, self.height)
        self.file_dialog = QFileDialog()
        self.msg = QMessageBox()
        self.file_path = ''
        self.file_id = None
        # Menus
        self.menubar = self.menuBar()
        self.init_ui()
        self.action_track_changes = self.get_menu_action(self.menubar, 'Track Changes')
        self.action_view_changes = self.get_menu_action(self.menubar, 'View Changes')
        # New File
        if settings_mgr.last_file:
            self.open_file(settings_mgr.last_file)
        else:
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
        # Edit Menu
        edit_menu = self.menubar.addMenu('Edit')
        edit_menu.setToolTipsVisible(True)
        self.add_menu_action(edit_menu, 'Undo\tCtrl+Z', self.editor.undo)
        self.add_menu_action(edit_menu, 'Redo\tCtrl+Y', self.editor.redo)
        QMenu.addSeparator(edit_menu)
        self.add_menu_action(edit_menu, 'Cut\tCtrl+X', self.editor.cut)
        self.add_menu_action(edit_menu, 'Copy\tCtrl+C', self.editor.copy)
        self.add_menu_action(edit_menu, 'Paste\tCtrl+V', self.editor.paste)
        self.add_menu_action(edit_menu, 'IntelliPaste\tCtrl+Alt+V', self.editor.paste_greek, tooltip='Intelligent Pasting featuring automatic conversions for Greek text')
        QMenu.addSeparator(edit_menu)
        self.add_menu_action(edit_menu, 'Find and Replace\tCtrl+F', self.editor.find_and_replace)
        # Insert Menu
        insert_menu = self.menubar.addMenu('Insert')
        submenu_diacriticals = QMenu('Ancient Diacriticals', self)
        self.add_menu_action(submenu_diacriticals, 'Acute', lambda: self.insert_str(' {text}(´)'))
        self.add_menu_action(submenu_diacriticals, 'Asper', lambda: self.insert_str(' {text}( ῾)'))
        self.add_menu_action(submenu_diacriticals, 'Circumflex', lambda: self.insert_str(' {text}(^)'))
        self.add_menu_action(submenu_diacriticals, 'Diaresis', lambda: self.insert_str(' {text}(¨)'))
        self.add_menu_action(submenu_diacriticals, 'Grave', lambda: self.insert_str(' {text}(`)'))
        self.add_menu_action(submenu_diacriticals, 'Lenis', lambda: self.insert_str(' {text}( ᾿)'))
        insert_menu.addMenu(submenu_diacriticals)
        submenu_apparatus = QMenu('Apparatus', self)
        self.add_menu_action(submenu_apparatus, 'Alternate Reading', lambda: self.insert_str('<:{text}|alt|:>'))
        self.add_menu_action(submenu_apparatus, 'Alternate Reading (multiple)', lambda: self.insert_str('<:{text}||alt||α|β:>'))
        self.add_menu_action(submenu_apparatus, 'Editorial Correction', lambda: self.insert_str('<:{text}|ed|:>'))
        self.add_menu_action(submenu_apparatus, 'Editorial Correction (multiple)', lambda: self.insert_str('<:{text}||ed||α|β:>'))
        self.add_menu_action(submenu_apparatus, 'Orthographic Regularization', lambda: self.insert_str('', 'reg'))
        self.add_menu_action(submenu_apparatus, 'Orthographic Regularization (multiple)', lambda: self.insert_str('<:α|β||reg||{text}:>'))
        self.add_menu_action(submenu_apparatus, 'Scribal Correction', lambda: self.insert_str('<:{text}|subst|:>'))
        self.add_menu_action(submenu_apparatus, 'Spelling Correction', lambda: self.insert_str('<:|corr|{text}:>'))
        insert_menu.addMenu(submenu_apparatus)
        submenu_supplied_parallel = QMenu('Supplied Parallel', self)
        self.add_menu_action(submenu_supplied_parallel, 'reason="undefined"', lambda: self.insert_str('|_{text}_|'))
        self.add_menu_action(submenu_supplied_parallel, 'reason="lost"', lambda: self.insert_str('_[{text}]_'))
        insert_menu.addMenu(submenu_supplied_parallel)
        submenu_num_characters = QMenu('Numerical Characters', self)
        self.add_menu_action(submenu_num_characters, '1/2', lambda: self.insert_str('𐅵'))
        self.add_menu_action(submenu_num_characters, '2/3', lambda: self.insert_str('𐅷'))
        self.add_menu_action(submenu_num_characters, '3/4', lambda: self.insert_str('𐅸'))
        self.add_menu_action(submenu_num_characters, 'Stigma (small)', lambda: self.insert_str('ϛ'))
        self.add_menu_action(submenu_num_characters, 'Stigma (capital)', lambda: self.insert_str('Ϛ'))
        self.add_menu_action(submenu_num_characters, 'Koppa (small)', lambda: self.insert_str('ϙ'))
        self.add_menu_action(submenu_num_characters, 'Sampi (small)', lambda: self.insert_str('ϡ'))
        self.add_menu_action(submenu_num_characters, "Numeral Tick", lambda: self.insert_str(" '"))
        insert_menu.addMenu(submenu_num_characters)
        submenu_langs = QMenu('Non-default Language', self)
        self.add_menu_action(submenu_langs, 'Arabic', lambda: self.insert_str('~|{text}|~ar '))
        self.add_menu_action(submenu_langs, 'Coptic', lambda: self.insert_str('~|{text}|~cop '))
        self.add_menu_action(submenu_langs, 'Demotic', lambda: self.insert_str('~|{text}|~egy-Egyd '))
        self.add_menu_action(submenu_langs, 'Greek', lambda: self.insert_str('~|{text}|~grc '))
        self.add_menu_action(submenu_langs, 'Latin', lambda: self.insert_str('~|{text}|~la '))
        QMenu.addSeparator(submenu_langs)
        self.add_menu_action(submenu_langs, 'Greek in Latin script', lambda: self.insert_str('~|{text}|~grc-Latn '))
        self.add_menu_action(submenu_langs, 'Latin in Greek script', lambda: self.insert_str('~|{text}|~la-Grek '))
        self.add_menu_action(submenu_langs, 'Coptic in Greek script', lambda: self.insert_str('~|{text}|~cop-Grek '))
        insert_menu.addMenu(submenu_langs)
        QMenu.addSeparator(insert_menu)
        self.add_menu_action(insert_menu, 'Deletion\tCtrl+D', lambda: self.insert_str('〚〛'))
        self.add_menu_action(insert_menu, 'Numeral\tCtrl+0', lambda: self.insert_str('<#=#>'))
        self.add_menu_action(insert_menu, 'Paragraphos\tCtrl+P', lambda: self.insert_str('----'), 'Ctrl+P')
        self.add_menu_action(insert_menu, 'Forked Paragraphos\tCtrl+Alt+P', lambda: self.insert_str('>---'), 'Ctrl+Alt+P')
        self.add_menu_action(insert_menu, 'Supralinear Stroke\tCtrl+L', lambda: self.insert_str('\u0304'))
        self.add_menu_action(insert_menu, 'Supralinear Stroke alt.\tCtrl+Alt+L', lambda: self.insert_str('¯'), 'Ctrl+Alt+L')
        self.add_menu_action(insert_menu, 'Handshift\tCtrl+H', lambda: self.insert_str('$m2 '),'Ctrl+H')
        self.add_menu_action(insert_menu, 'Underdot\tCtrl+U', lambda: self.insert_str('\u0323'))
        # View Menu
        view_menu = self.menuBar().addMenu('View')
        submenu_zoom = QMenu('Zoom')
        submenu_zoom.setToolTipsVisible(True)
        self.add_menu_action(submenu_zoom, 'Zoom In', self.editor.zoomIn, 'Ctrl++', tooltip='Alternatively: Ctrl+Mousewheel Up')
        self.add_menu_action(submenu_zoom, 'Zoom Out', self.editor.zoomOut, 'Ctrl+-', tooltip='Alternatively: Ctrl+Mousewheel Down')
        view_menu.addMenu(submenu_zoom)
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
        self.add_menu_action(changes_menu, 'Reset Git', self.reset_git, tooltip='Resets all tracked files')
        help_menu = self.menubar.addMenu('Help')
        self.add_menu_action(help_menu, 'Leiden+ Documentation', lambda: self.show_in_web('Leiden+ Documentation', documentation_path, True))
        self.add_menu_action(help_menu, 'Sigla, Special Characters, Scribal Punctuation, Glyphs', lambda: self.show_in_web('Sigla, Special Characters, Scribal Punctuation & Glyphs', 'https://github.com/papyri/site-docs/blob/master/gtypes.md'))
        self.menubar.addMenu(help_menu)

    def show_in_web(self, window_name, url, local=False):
        self.webview.setWindowTitle(window_name)
        if not local:
            self.webview.load(QUrl(url))
        else:
            self.webview.load(QUrl.fromLocalFile(url))
        self.webview.show()

    def get_tracked_file_name(self):
        return str(self.file_id) + '_' + basename(self.file_path)

    def reset_git(self):
        msg = QMessageBox.warning(self, 'Reset Git',
                                  'Be aware that this action will fully reset your change tracking for all files!',
                                  buttons=QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        if msg == QMessageBox.StandardButton.Ok:
            if self.tracker.active:
                self.set_checked_no_signal(self.action_track_changes, False)
            self.tracker.reset_git()
            return True
        else:
            return False

    def start_tracking(self, checked):
        if checked:
            if not self.file_path:
                if not self.save_file(True, self.create_leiden_file()):
                    self.set_checked_no_signal(self.action_track_changes, False)
                    return
            self.tracker.active = True
            self.tracker.write_changes(self.get_tracked_file_name(), self.editor.toPlainText())
            self.tracker.commit_changes(self.get_tracked_file_name())
        else:
            msg = QMessageBox.warning(self, 'Reset Change Tracking', 'Be aware that this action will fully reset your change tracking for this file!', buttons=QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            if msg == QMessageBox.StandardButton.Ok:
                self.tracker.stop_tracking(self.get_tracked_file_name())
                self.set_checked_no_signal(self.action_track_changes, False)
            else:
                self.set_checked_no_signal(self.action_track_changes, True)

    def export_change_log(self):
        if self.tracker.active and self.saving_enabled:
            self.save_file(False, self.create_leiden_file())
            path, _ = self.file_dialog.getSaveFileName(filter='*.leiden_changelog.json *.txt')
            if path:
                suffixes = Path(path).suffixes
                with open(path, 'w', encoding='utf-8') as f:
                    if suffixes[0] == '.leiden_changelog':
                        json.dump(self.tracker.parse_word_diff(self.get_tracked_file_name()), f)
                    else:
                        self.tracker.write_change_log(path, self.get_tracked_file_name())

    def import_change_log(self, checked):
        if checked:
            path, _ = self.file_dialog.getOpenFileName(filter='*.leiden_changelog.json')
            if path:
                with open(path, 'r', encoding='utf-8') as f:
                    self.imported_change_log = json.load(f)['diffs']
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
                    diffs = self.tracker.parse_word_diff(self.get_tracked_file_name())['diffs']
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

    def insert_str(self, string: str, sender: str = ''):
        cursor = self.editor.textCursor()
        text = cursor.selectedText()
        prediction = ''
        if not text:
            text = ''
        if not sender:
            string = string.format(text=text)
        elif sender == 'reg':
            prediction = self.ai_mgr.predict_reg(text)
            string = f'<:{prediction}|reg|{text}:>'
        cursor.insertText(string)
        if sender == 'reg':
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, len(text) + 8)
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            self.editor.setTextCursor(cursor)


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
        self.editor.debug_worker.set_previous_text('')
        self.editor.setReadOnly(False)

    def set_new_file_id(self):
        self.file_id = uuid.uuid4()
        print('FILE ID: ', self.file_id)

    def new_file(self):
        self.reset()
        self.editor.appendPlainText('<S=.grc\n<D=.1.fragment<=\n1. \n=>=D>')
        self.set_window_title('New File')
        self.set_cursor_position(3, 3)
        self.file_path = ''
        settings_mgr.last_file = ''
        self.set_new_file_id()

    def open_file(self, path=None):
        if not path:
            path, _ = self.file_dialog.getOpenFileName(filter='*.leiden *.txt')
        if os.path.exists(path):
            self.reset()
            with open(path, 'r', encoding='utf-8') as file:
                file_content = file.read()
            self.file_path = path
            data = file_content.split('\ue747')
            if data[0] == '0.1.0':
                file_settings = data[1].split(';')
                if len(file_settings) >= 1:
                    self.file_id = file_settings[0]
                    if self.tracker.request_active(self.get_tracked_file_name()):
                        self.set_checked_no_signal(self.action_track_changes, True)
                    else:
                        self.set_checked_no_signal(self.action_track_changes, False)
                text = data[2]
            else:
                self.tracker.request_active(self.get_tracked_file_name())
                text = file_content
            self.editor.setPlainText(text)
            self.editor.start_debugging()
            self.set_window_title(path)
            if path == settings_mgr.last_file:
                cursor = self.editor.textCursor()
                cursor.setPosition(settings_mgr.text_cursor_pos)
                self.editor.setTextCursor(cursor)
            self.editor.verticalScrollBar().setValue(settings_mgr.scroll_val)
        else:
            self.new_file()

    def create_leiden_file(self):
        splitter = '\ue747'
        # file version
        text = '0.1.0' + splitter
        # file config (split by semicolon: file_id)
        text += str(self.file_id) + ';'
        # text
        text += splitter + self.editor.toPlainText()
        return text

    def set_window_title(self, path=None):
        if not path:
            self.setWindowTitle(app_name)
        else:
            self.setWindowTitle(f'{app_name} - {path}')

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
                self.set_window_title(path)
                if self.tracker.active:
                    self.tracker.write_changes(self.get_tracked_file_name(), self.editor.toPlainText())
            return True
        else:
            return False

    def update_settings(self):
        settings_mgr.zoom_level = self.editor.get_zoom_level()
        settings_mgr.last_file = self.file_path
        settings_mgr.scroll_val = self.editor.verticalScrollBar().value()
        settings_mgr.text_cursor_pos = self.editor.textCursor().position()
        settings_mgr.write_settings()

    def closeEvent(self, event):
        self.update_settings()
        if self.file_path.endswith('.leiden'):
            self.save_file(False, self.create_leiden_file())