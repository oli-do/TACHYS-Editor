from PySide6.QtCore import QObject, Signal
from concurrent.futures import ProcessPoolExecutor, as_completed, wait, ALL_COMPLETED
import os
import threading


from .parser import TachysParser, ParserError
parser = TachysParser()


def debug(line: str, i: int):
    return parser.parse_line(line, i)

def debug_full(text, previous_text):
    if text != previous_text:
        parser.parse_full(text)
        error_info = [(error.id, error.line, error.column) for error in parser.errors]
        return error_info
    else:
        return None


def find_text_changes(current_line, previous_lines, index):
    try:
        previous_line = previous_lines[index]
    except IndexError:
        return index
    if current_line != previous_line:
        return index
    else:
        return None


class DebugWorker(QObject):
    signal_error_info: Signal = Signal(list)

    def __init__(self):
        super().__init__()
        self.text = ''
        self.previous_text = ''
        self.is_running = False
        self.enabled = True
        self.debug_executor = ProcessPoolExecutor(max_workers=os.cpu_count() - 1)
        self.analyzer = ProcessPoolExecutor(max_workers=os.cpu_count() - 1)
        self.previous_error_info = []
        self.errors: list[ParserError] = []

    def run(self):
        if self.enabled and not self.is_running:
            self.is_running = True
            current_lines = self.text.splitlines()
            previous_lines = self.previous_text.splitlines()
            lines_changed_indices = []
            futures = [self.analyzer.submit(find_text_changes, current_lines[i], previous_lines, i) for i in range(len(current_lines))]
            for future in as_completed(futures):
                if future.result():
                    lines_changed_indices.append(future.result())
            if len(current_lines) != len(previous_lines):
                change_cause = lines_changed_indices[0] - 1
                if change_cause > 0:
                    lines_changed_indices.append(change_cause)
            self.errors = [e for e in self.errors if not e.line in lines_changed_indices]
            futures = [self.debug_executor.submit(debug, current_lines[i], i) for i in lines_changed_indices]
            threading.Thread(target=self.monitor_futures, args=(futures,), daemon=True).start()


    def monitor_futures(self, futures):
        wait(futures, return_when=ALL_COMPLETED)
        self.on_finished(futures)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def on_finished(self, futures):
        if self.enabled:
            for future in futures:
                if future.result():
                    self.errors.append(future.result())
            self.previous_text = self.text
            self.errors = parser.validate_line_errors(self.text.splitlines(), self.errors)
            error_info = [(error.id, error.line, error.column, error.char) for error in self.errors]
            if error_info:
                self.previous_error_info = error_info
                self.signal_error_info.emit(error_info)
        self.is_running = False

    def set_text(self, text):
        self.text = text

