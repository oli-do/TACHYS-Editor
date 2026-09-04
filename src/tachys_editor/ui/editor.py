import re
from typing import Literal

import pyperclip
import roman
import unicodedata
from PySide6.QtCore import Qt, QSize, QRect, QTimer, Slot
from PySide6.QtGui import QColor, QTextCursor, QPainter, QTextCharFormat, QTextOption, QPalette, QFont
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit, QDialog, QLineEdit, QPushButton, QVBoxLayout, QLabel, QHBoxLayout

from .highlighter import TachysHighlighter
from ..core.debug import DebugWorker
from ..core.format import PasteManager, format_numerals
from ..shared.settings import settings_mgr
from ..shared.objects import parser
from ..shared.grammar import get_lang_chars

added_fmt = QTextCharFormat()
added_fmt.setBackground(QColor("#d4fedd"))
deleted_fmt = QTextCharFormat()
deleted_fmt.setBackground(QColor("#fdd4d4"))
deleted_fmt.setFontStrikeOut(True)
normal_fmt = QTextCharFormat()


class LeftWidget(QWidget):
    def __init__(self, code_editor):
        super().__init__(code_editor)
        self.codeEditor = code_editor

    def sizeHint(self):
        return QSize(self.codeEditor.left_widget_width(), 0)

    def paintEvent(self, event):
        self.codeEditor.left_widget_paint_event(event)


class FindAndReplaceDialog(QDialog):
    def __init__(self, code_editor):
        super().__init__(code_editor)
        self.setWindowTitle('Find and Replace')
        self.setFixedSize(300, 150)
        self.editor = code_editor
        self.find_input = QLineEdit(placeholderText='Find...')
        self.replace_input = QLineEdit(placeholderText='Replace with...')
        self.find_button = QPushButton('Find Next')
        self.replace_button = QPushButton('Replace')
        self.replace_all_button = QPushButton('Replace All')
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Search for:'))
        layout.addWidget(self.find_input)
        layout.addWidget(QLabel('Replace with:'))
        layout.addWidget(self.replace_input)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.find_button)
        button_layout.addWidget(self.replace_button)
        button_layout.addWidget(self.replace_all_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.find_button.clicked.connect(self.find_text)
        self.replace_button.clicked.connect(self.replace_text)
        self.replace_all_button.clicked.connect(self.replace_all)

    def find_text(self):
        text_to_find = self.find_input.text()
        if not text_to_find:
            return
        found = self.editor.find(text_to_find)
        if not found:
            self.editor.moveCursor(QTextCursor.MoveOperation.Start)
            self.editor.find(text_to_find)

    def replace_text(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self.find_input.text():
            cursor.insertText(self.replace_input.text())
            self.find_text()

    def replace_all(self):
        find_text = self.find_input.text()
        replace_text = self.replace_input.text()
        if not find_text:
            return
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        self.editor.moveCursor(QTextCursor.MoveOperation.Start)
        count = 0
        while self.editor.find(find_text):
            self.editor.textCursor().insertText(replace_text)
            count += 1
        cursor.endEditBlock()


class TachysEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.theme = settings_mgr.appearance.theme
        if self.theme == 'Dark':
            palette = self.palette()
            palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
            self.setPalette(palette)
        self.default_font_size = settings_mgr.editor.font_size
        font = QFont(settings_mgr.editor.font)
        font.setPointSize(self.default_font_size)
        self.setFont(font)
        self.line_text = ''
        self.line_break = False
        self.do_debugging = True
        self.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.paste_mgr = PasteManager()
        self.dialog_find_and_replace = FindAndReplaceDialog(self)
        self.original_paste_text = ''
        self.selected_text = ''
        self.left_widget = LeftWidget(self)
        self.blockCountChanged.connect(self.update_left_widget_width)
        self.updateRequest.connect(self.update_left_widget_area)
        self.update_left_widget_width(0)
        self.highlighter = TachysHighlighter(self.document())
        self.debug_worker = DebugWorker()
        self.debug_worker.signal_error_info.connect(self.highlighter.update_error_highlighting)
        self.debug_timer = QTimer()
        self.debug_timer.setSingleShot(True)
        self.debug_timer.timeout.connect(self.start_debugging)
        self.lines_changed = []
        self.document().contentsChange.connect(self.on_contents_change)
        self.cursorPositionChanged.connect(self.on_cursor_position_changed)
        self.current_line_bg_highlight = 0
        self.highlight_current_line()

    def find_and_replace(self):
        self.dialog_find_and_replace.show()

    def paste_greek(self):
        # run operations with clipboard text, e.g. replace lunate sigma or convert whole Leiden input to Leiden+
        cursor = self.textCursor()
        line_text = self.get_current_line_text()
        try:
            line_number = re.findall(r'^\(?[0-9]+', line_text)[0]
            line_number = int(line_number)
        except (IndexError, ValueError):
            line_number = None
        self.original_paste_text = pyperclip.paste()
        clipboard_text = pyperclip.paste()
        clipboard_text = unicodedata.normalize('NFC', clipboard_text)
        clipboard_text = self.paste_mgr.char_level_replacements(clipboard_text)
        clipboard_text = self.paste_mgr.replace_underdots(clipboard_text)
        clipboard_text = self.paste_mgr.replace_supralinear_stroke(clipboard_text)
        clipboard_text = self.paste_mgr.replace_brackets(clipboard_text)
        clipboard_text = self.paste_mgr.replace_supplied_omitted(clipboard_text)
        clipboard_text = self.paste_mgr.delete_edition_line_numbers(clipboard_text)
        clipboard_text = self.paste_mgr.multiline(clipboard_text, line_number)
        pyperclip.copy(clipboard_text)
        cursor.insertText(clipboard_text)
        pyperclip.copy(self.original_paste_text)

    def show_changes(self, line_diff_list: list):
        self.stop_debugging()
        cursor = self.textCursor()
        cursor.beginEditBlock()
        self.clear()
        self.setUpdatesEnabled(False)
        for line in line_diff_list:
            for tag, text in line:
                if tag == 1:
                    cursor.insertText(text, added_fmt)
                elif tag == -1:
                    cursor.insertText(text, deleted_fmt)
                elif tag == 0:
                    cursor.insertText(text, normal_fmt)
            cursor.insertBlock()
        cursor.endEditBlock()
        self.setUpdatesEnabled(True)
        self.setReadOnly(True)

    def on_cursor_position_changed(self):
        self.highlight_current_line()

    def set_language(self, lang: Literal['grc', 'la', 'cop', 'any']):
        parser.set_language(lang)
        self.highlighter.update_error_highlighting([])
        self.highlighter.text = get_lang_chars(lang)
        self.debug_worker.set_language(lang)
        self.lines_changed = [i for i in range(self.blockCount())]

    def on_contents_change(self, position, _, __):
        block = self.document().findBlock(position)
        line = block.blockNumber()
        self.lines_changed.append(line)
        if line == 0:
            text = block.text().strip()
            if text == '<S=.grc':
                self.set_language('grc')
            elif text == '<S=.la':
                self.set_language('la')
            elif text == '<S=.cop':
                self.set_language('cop')
            else:
                self.set_language('any')
        if self.do_debugging:
            self.request_debugging()

    @Slot()
    def highlight_current_line(self):
        cursor = self.textCursor()
        highlight_line = cursor.blockNumber()
        if highlight_line != self.current_line_bg_highlight:
            extra_selections = []
            if not self.isReadOnly():
                selection = QTextEdit.ExtraSelection()
                if self.theme == 'Dark':
                    line_color = QColor.fromRgb(0, 0, 30)
                else:
                    line_color = QColor('#e8f2fe')
                selection.format.setBackground(line_color)
                selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
                selection.cursor = self.textCursor()
                selection.cursor.clearSelection()
                extra_selections.append(selection)
            self.setExtraSelections(extra_selections)
            self.current_line_bg_highlight = highlight_line

    def request_debugging(self):
        self.debug_timer.start(settings_mgr.editor.debug_delay)

    def start_debugging(self):
        if self.debug_worker.is_running:
            if self.lines_changed:
                self.request_debugging()
            return
        self.debug_worker.set_text(self.toPlainText())
        self.debug_worker.set_lines_changed_indices(list(set(self.lines_changed)))
        self.lines_changed = []
        self.debug_worker.run()


    def continue_debugging(self):
        self.do_debugging = True
        self.debug_worker.enable()
        self.highlighter.do_error_highlighting = True
        self.highlighter.rehighlight()
        self.highlighter.do_error_highlighting = False
        self.setReadOnly(False)

    def stop_debugging(self):
        self.do_debugging = False
        self.debug_worker.disable()
        self.highlighter.parser_errors = []
        self.highlighter.do_error_highlighting = False

    def left_widget_width(self):
        digits = len(str(max(1, self.blockCount()))) + 2
        space = self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_left_widget_width(self, _):
        self.setViewportMargins(self.left_widget_width(), 0, 0, 0)

    def update_left_widget_area(self, rect, dy):
        if dy:
            self.left_widget.scroll(0, dy)
        else:
            self.left_widget.update(0, rect.y(), self.left_widget.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_left_widget_width(0)

    def left_widget_paint_event(self, event):
        painter = QPainter(self.left_widget)
        if self.theme == 'Light':
            painter.fillRect(event.rect(), QColor("lightgray"))
        else:
            painter.fillRect(event.rect(), QColor.fromRgb(100, 100, 100))
        first_block = self.firstVisibleBlock()
        current_number = 0
        blocks_to_check = []
        curr = first_block.previous()
        while curr.isValid():
            text = curr.text()
            blocks_to_check.append(text)
            if '<=' in text:
                break
            curr = curr.previous()
        for text in reversed(blocks_to_check):
            if '<=' in text:
                current_number = 0
            if re.match(r'^\(?[0-9]+', text):
                if 'lost.?lin' in text:
                    continue
                current_number += 1
                lines_lost = re.search(r'lost\.([0-9]+)lin', text)
                if lines_lost:
                    current_number += int(lines_lost.group(1)) - 1
        block = first_block
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            text = block.text()
            is_numbered = bool(re.match(r'^\(?[0-9]+', text))
            if '<=' in text:
                current_number = 0
            if is_numbered:
                if not 'lost.?lin' in text:
                    current_number += 1
                    if block.isVisible() and bottom >= event.rect().top():
                        draw_number = f'[{current_number}]'
                        if self.theme == 'Light':
                            painter.setPen(QColor("white"))
                        else:
                            painter.setPen(QColor.fromRgb(170, 170, 170))
                        painter.drawText(0, top, self.left_widget.width(), self.fontMetrics().height(),
                                         Qt.AlignmentFlag.AlignCenter, draw_number)
                    lines_lost = re.search(r'lost\.([0-9]+)lin', text)
                    if lines_lost:
                        current_number += int(lines_lost.group(1)) - 1
            block = block.next()
            top = bottom
            if block.isValid():
                bottom = top + round(self.blockBoundingRect(block).height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        # Hier wird die Geometrie des LeftWidgets fest an den linken Rand gebunden
        self.left_widget.setGeometry(
            QRect(cr.left(), cr.top(), self.left_widget_width(), cr.height())
        )

    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoomIn(1)
            else:
                self.zoomOut(1)
            event.accept()
        else:
            super().wheelEvent(event)

    def get_zoom_level(self):
        current_font_size = self.font().pointSize()
        return current_font_size / self.default_font_size

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            self.line_text = self.get_current_line_text().strip()
            cursor.beginEditBlock()
            try:
                if self.line_text[-1] == '-' and not re.fullmatch(r'--|\$-', self.line_text[-2:]) and cursor.atBlockEnd():
                    self.line_break = True
                    cursor.deletePreviousChar()
            except IndexError:
                self.line_break = False
        elif event.key() == Qt.Key.Key_BracketLeft or event.key() == Qt.Key.Key_ParenLeft or event.key() == Qt.Key.Key_BraceLeft:
            self.selected_text = cursor.selectedText()
        super().keyPressEvent(event)

    def insert_deletion(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            cursor.insertText('〚' + cursor.selectedText() + '〛')
        else:
            cursor.insertText('〚〛')
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, 1)
            self.setTextCursor(cursor)

    def insert_numeral(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            numeral = format_numerals(cursor.selectedText())
            cursor.insertText(numeral)
        else:
            cursor.insertText('<#=#>')
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, 2)
            self.setTextCursor(cursor)

    def insert_underdot(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            replacement = ''
            for char in cursor.selectedText():
                replacement += char + '\u0323'
            cursor.insertText(replacement)
        else:
            cursor.insertText('\u0323')

    def insert_supralinear_stroke(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            if len(text) > 1:
                cursor.insertText('¯' + cursor.selectedText() + '¯')
            else:
                cursor.insertText(text + '\u0304')
        else:
            cursor.insertText('\u0304')

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
        super().keyReleaseEvent(event)

    def get_current_line_text(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        line_text = cursor.selectedText()
        return line_text

    def navigate_to_line(self, line: int):
        block = self.document().findBlockByLineNumber(line)
        cursor = QTextCursor(block)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()