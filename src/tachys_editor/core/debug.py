from PySide6.QtCore import QObject, Signal
from concurrent.futures import ProcessPoolExecutor, wait, ALL_COMPLETED
from time import time
import os
import threading

from typing import Literal

from .parser import ParserError
from ..shared.objects import parser


def debug(line: str, i: int):
    return parser.parse_line(line, i)

def debug_full(text, previous_text):
    if text != previous_text:
        parser.parse_full(text)
        error_info = [(error.id, error.line, error.column) for error in parser.errors]
        return error_info
    else:
        return None


def _init_worker(lang: Literal['grc', 'la']):
    parser.set_language(lang)


class DebugWorker(QObject):
    signal_error_info: Signal = Signal(list)

    def __init__(self):
        super().__init__()
        self.text = ''
        self.previous_text = ''
        self.is_running = False
        self.enabled = True
        self.debug_executor = ProcessPoolExecutor(max_workers=os.cpu_count() - 1)
        self.previous_error_info = []
        self.errors: list[ParserError] = []
        self.lines_changed_indices: list[int] = []
        self.debug_start_time = 0
        self.lang: str = ''

    def set_language(self, lang):
        if lang != self.lang:
            self.lang = lang
            self.debug_executor.shutdown(wait=False, cancel_futures=True)
            self.debug_executor = ProcessPoolExecutor(
                max_workers=os.cpu_count() - 1,
                initializer=_init_worker,
                initargs=(lang,)
            )
            self.errors = []

    def run(self):
        if self.enabled and not self.is_running:
            self.debug_start_time = time()
            self.is_running = True
            current_lines = self.text.splitlines()
            len_current_lines = len(current_lines)
            max_index_current_lines = len(current_lines) - 1
            previous_lines = self.previous_text.splitlines()
            len_previous_lines = len(previous_lines)
            if len_current_lines != len_previous_lines:
                if self.previous_text == '':
                    self.lines_changed_indices = range(len_current_lines)
                else:
                    num_lines_changed = abs(len_previous_lines - len_current_lines)
                    start = self.lines_changed_indices[0]
                    self.lines_changed_indices = []
                    for i in range(start, start + num_lines_changed + 1):
                            if i < len_current_lines:
                                self.lines_changed_indices.append(i)
            print('DebugWorker: check lines', self.lines_changed_indices)
            self.errors = [e for e in self.errors if not e.line in self.lines_changed_indices and not e.line > max_index_current_lines]
            futures = [self.debug_executor.submit(debug, current_lines[i], i) for i in self.lines_changed_indices]
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
        debug_time = (time() - self.debug_start_time) * 1000
        print(f'DebugWorker: took {debug_time} ms')
        self.is_running = False

    def set_text(self, text):
        self.text = text

    def set_lines_changed_indices(self, lines):
        self.lines_changed_indices = lines

    def set_previous_text(self, text):
        self.previous_text = text
