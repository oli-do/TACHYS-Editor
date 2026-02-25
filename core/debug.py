from PySide6.QtCore import QObject, Signal
from concurrent.futures import ProcessPoolExecutor
import re

from core.parser import LeidenParser
parser = LeidenParser()


def debug(text, previous_text):
    if text != previous_text:
        current_lines = text.split('\n')
        previous_lines = previous_text.split('\n')
        lines_changed_indices = []
        for i in range(len(current_lines)):
            current_line = current_lines[i]
            try:
                if current_line != previous_lines[i]:
                    lines_changed_indices.append(i)
            except IndexError:
                lines_changed_indices.append(i)
        parser.parse_line(current_lines, lines_changed_indices)
        error_info = [(error.id, error.line, error.column) for error in parser.errors]
        for error in error_info:
            index = error[1]
            if index < len(current_lines):
                if re.findall(r'^\(?[0-9]+\.-|^[0-9]+,[a-z]+\.-', current_lines[index]):
                    return debug_full(text, previous_text)
        return error_info
    else:
        return None

def debug_full(text, previous_text):
    if text != previous_text:
        parser.parse_full(text)
        error_info = [(error.id, error.line, error.column) for error in parser.errors]
        return error_info
    else:
        return None


class DebugWorker(QObject):
    syntax_errors: Signal = Signal(list)

    def __init__(self):
        super().__init__()
        self.text = ''
        self.visible_lines = []
        self.previous_text = ''
        self.is_running = False
        self.enabled = True
        self.executor = ProcessPoolExecutor(max_workers=1)

    def run(self):
        if self.enabled:
            self.is_running = True
            future = self.executor.submit(debug, self.text, self.previous_text)
            future.add_done_callback(self.on_finished)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def on_finished(self, future):
        self.is_running = False
        if self.enabled:
            result = future.result()
            if result is not None:
                self.previous_text = self.text
                self.syntax_errors.emit(result)

    def set_text(self, text):
        self.text = text

    def set_visible_lines(self, visible_lines):
        self.visible_lines = visible_lines
