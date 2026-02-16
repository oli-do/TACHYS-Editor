from PySide6.QtCore import Qt, QSize, QRect, QTimer
from PySide6.QtWidgets import QPlainTextEdit, QWidget
from PySide6.QtGui import QColor, QTextCursor, QPainter
from core.format import PasteManager, format_numerals
from core.debug import DebugWorker
from core.parser import LeidenParser
import unicodedata
import roman
import re
import pyperclip
from ui.highlighter import LeidenHighlighter


class LeftWidget(QWidget):
    def __init__(self, code_editor):
        super().__init__(code_editor)
        self.codeEditor = code_editor

    def sizeHint(self):
        return QSize(self.codeEditor.left_widget_width(), 0)

    def paintEvent(self, event):
        self.codeEditor.left_widget_paint_event(event)

class LeidenEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.line_text = ''
        self.line_break = False
        self.paste_mgr = PasteManager()
        self.original_paste_text = ''
        self.selected_text = ''
        self.left_widget = LeftWidget(self)
        self.blockCountChanged.connect(self.update_left_widget_width)
        self.updateRequest.connect(self.update_left_widget_area)
        self.update_left_widget_width(0)
        self.highlighter = LeidenHighlighter(self.document())
        self.parser = LeidenParser()
        self.debug_worker = DebugWorker()
        self.debug_worker.syntax_errors.connect(self.highlighter.update_error_highlighting)
        self.debug_timer = QTimer()
        self.debug_timer.setSingleShot(True)
        self.debug_timer.timeout.connect(self.start_debugging)
        self.textChanged.connect(self.on_text_change)

    def on_text_change(self):
        self.debug_timer.start(600)

    def start_debugging(self):
        if self.debug_worker.is_running:
            self.debug_timer.start(100)
            return
        self.debug_worker.set_text(self.toPlainText())
        visible_lines = []
        block = self.firstVisibleBlock()
        while block.isValid():
            if block.isVisible():
                visible_lines.append(block.blockNumber())
            block = block.next()
        self.debug_worker.set_visible_lines(visible_lines)
        self.debug_worker.run()

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
        painter.fillRect(event.rect(), QColor("lightgray"))
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
                current_number += 1
        block = first_block
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            text = block.text()
            is_numbered = bool(re.match(r'^\(?[0-9]+', text))
            if '<=' in text:
                current_number = 0
            if is_numbered:
                current_number += 1
                if block.isVisible() and bottom >= event.rect().top():
                    draw_number = f'[{current_number}]'
                    painter.setPen(QColor("white"))
                    painter.drawText(0, top, self.left_widget.width(), self.fontMetrics().height(),
                                     Qt.AlignmentFlag.AlignCenter, draw_number)
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