from PySide6.QtCore import QObject, Signal
from concurrent.futures import ProcessPoolExecutor, wait, ALL_COMPLETED
from time import time
import os
import threading
import re

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


def _init_worker(lang: str):
    parser.set_language(lang)


class DebugWorker(QObject):
    signal_error_info: Signal = Signal(list)

    def __init__(self):
        super().__init__()
        self.text = ''
        self.current_lines = []
        self.previous_text = ''
        self.is_running = False
        self.enabled = True
        self.debug_executor = ProcessPoolExecutor(max_workers=os.cpu_count() - 1)
        self.errors: list[ParserError] = []
        self.lines_changed_indices: list[int] = []
        self.debug_start_time = 0
        self.lang: str = ''
        self.xml_lines = {}

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

    def validate_structure(self, start_tag: str, end_tag: str):
        stack = []
        for match in re.finditer(f'{start_tag}|{end_tag}', self.text):
            token = match.group()
            start_idx = match.start()
            line_num = self.text[:start_idx].count('\n')
            last_newline = self.text.rfind('\n', 0, start_idx)
            col_num = start_idx + 1 if last_newline == -1 else start_idx - last_newline
            if token == start_tag:
                stack.append({
                    'line': line_num,
                    'col': col_num - 1,
                    'token': token
                })
            elif token == end_tag:
                if stack:
                    stack.pop()
        return stack

    def run(self):
        if self.enabled and not self.is_running:
            self.debug_start_time = time()
            self.is_running = True
            self.current_lines = self.text.splitlines()
            len_current_lines = len(self.current_lines)
            max_index_current_lines = len(self.current_lines) - 1
            previous_lines = self.previous_text.splitlines()
            len_previous_lines = len(previous_lines)
            if len_current_lines != len_previous_lines:
                if not self.previous_text:
                    self.lines_changed_indices = list(range(len_current_lines))
                else:
                    delta = len_current_lines - len_previous_lines
                    start = self.lines_changed_indices[0] if self.lines_changed_indices else 0
                    if delta > 0:
                        for k in sorted((k for k in self.xml_lines if k > start), reverse=True):
                            self.xml_lines[k + delta] = self.xml_lines.pop(k)
                        end_idx = min(start + delta + 1, len_current_lines)
                        self.lines_changed_indices = list(range(start, end_idx))
                    else:
                        for k in sorted(k for k in self.xml_lines if k > start):
                            val = self.xml_lines.pop(k)
                            if k + delta >= 0:
                                self.xml_lines[k + delta] = val
                        self.xml_lines = {k: v for k, v in self.xml_lines.items() if k < len_current_lines}
                        end_idx = max(start + delta - 1, -1)
                        self.lines_changed_indices = list(range(start, end_idx, -1))
            print('DebugWorker: check lines', self.lines_changed_indices)
            self.errors = [e for e in self.errors if not e.line in self.lines_changed_indices and not e.line > max_index_current_lines]
            futures = [self.debug_executor.submit(debug, self.current_lines[i], i) for i in self.lines_changed_indices if i < len_current_lines]
            threading.Thread(target=self.monitor_futures, args=(futures,), daemon=True).start()


    def monitor_futures(self, futures):
        wait(futures, return_when=ALL_COMPLETED)
        self.on_finished(futures)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.debug_executor.shutdown(wait=False, cancel_futures=True)
        self.enabled = False
        self.is_running = False

    def on_finished(self, futures):
        if self.enabled:
            for future in futures:
                if future.result():
                    error, xml = future.result()
                    if error:
                        self.errors.append(error)
                    if xml:
                        index, text = xml[0]
                        self.xml_lines[index] = text
            self.previous_text = self.text
            self.errors, xml = parser.validate_line_errors(self.text.splitlines(), self.errors)
            start_time = time()
            self.errors = [error for error in self.errors if not error.id in [4, 5, 6]]
            unclosed_div = self.validate_structure('<D=', '=D>')
            for u in unclosed_div:
                self.errors.append(ParserError('Unexpected EOF div', 4, u['line'], u['col'], u['token'], None, ''))
            unclosed_ab = self.validate_structure('<=', '=>')
            for u in unclosed_ab:
                self.errors.append(ParserError('Unexpected EOF ab', 5, u['line'], u['col'], u['token'], None, ''))
            if not self.current_lines[0].startswith('<S='):
                self.errors.append(ParserError('Unexpected Document Start', 6, 0, 0, '', None, ''))
            print('DebugWorker: structural integrity check took', (time() - start_time) * 1000, 'ms')
            error_info = [(error.id, error.line, error.column, error.char, error.details) for error in self.errors]
            self.signal_error_info.emit(error_info)
            if xml:
                for line_tuple in xml:
                    index, text = line_tuple
                    self.xml_lines[index] = text
        debug_time = (time() - self.debug_start_time) * 1000
        print(f'DebugWorker: took {debug_time} ms')
        self.is_running = False

    def set_text(self, text):
        self.text = text

    def set_lines_changed_indices(self, lines):
        self.lines_changed_indices = lines

    def set_previous_text(self, text):
        self.previous_text = text
