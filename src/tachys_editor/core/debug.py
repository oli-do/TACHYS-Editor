from PySide6.QtCore import QObject, Signal
from concurrent.futures import ProcessPoolExecutor, as_completed
from time import time
import os
import threading
import re

from tachys_editor.shared.objects import parser
from tachys_editor.shared.classes import ParserError


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
    signal_progress: Signal = Signal(int)

    def __init__(self):
        super().__init__()
        parser.signal_progress.connect(self.send_progress_update)
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

    def validate_structure(self, start_tag: str, end_tag: str, propagate_positions: bool = False,
                           reverse: bool = False) -> list[dict] | tuple[list[dict], list[dict]]:
        stack = []
        positions = []
        matches = list(re.finditer(f'{start_tag}|{end_tag}', self.text))
        if reverse:
            matches.reverse()

        for match in matches:
            token = match.group()
            start_idx = match.start()
            line_num = self.text[:start_idx].count('\n')
            last_newline = self.text.rfind('\n', 0, start_idx)
            col_num = start_idx + 1 if last_newline == -1 else start_idx - last_newline
            if token in [start_tag, end_tag]:
                positions.append({
                    'line': line_num,
                    'col': col_num - 1,
                    'token': token
                })
            if not reverse:
                if token == start_tag:
                    stack.append(positions[-1])
                elif token == end_tag:
                    if stack:
                        stack.pop()
            else:
                if token == end_tag:
                    stack.append(positions[-1])
                elif token == start_tag:
                    if stack:
                        stack.pop()
        if not propagate_positions:
            return stack
        else:
            return stack, positions

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
                        self.lines_changed_indices = list(range(start + 1, end_idx, -1))
            print('DebugWorker: check lines', self.lines_changed_indices)
            self.errors = [e for e in self.errors if not e.line in self.lines_changed_indices and not e.line > max_index_current_lines]
            futures = [self.debug_executor.submit(debug, self.current_lines[i], i) for i in self.lines_changed_indices if i < len_current_lines]
            threading.Thread(target=self.monitor_futures, args=(futures,), daemon=True).start()

    def send_progress_update(self, percentage: int):
        self.signal_progress.emit(percentage)

    def monitor_futures(self, futures):
        completed = 0
        for future in as_completed(futures):
            error, xml = future.result()
            if error:
                self.errors.append(error)
            if xml:
                index, text = xml[0]
                self.xml_lines[index] = text
            completed += 1
            percentage = round(completed / len(futures) * 50) - 1
            self.send_progress_update(percentage)
        self.on_finished()

    def enable(self):
        self.enabled = True

    def disable(self):
        self.debug_executor.shutdown(wait=False, cancel_futures=True)
        self.enabled = False
        self.is_running = False

    def on_finished(self):
        if self.enabled:
            self.previous_text = self.text
            lines = self.text.splitlines()
            self.errors, xml = parser.validate_line_errors(lines, self.errors)
            self.send_progress_update(99)
            start_time = time()
            self.errors = [error for error in self.errors if not error.id in [4, 5, 6, 8, 9]]
            unclosed_div = self.validate_structure('<D=', '=D>')
            for u in unclosed_div:
                self.errors.append(ParserError('Unexpected EOF div', 4, u['line'], u['col'], u['token'], None, 'Division is missing a closing statement (=D>)'))
            unopened_div = self.validate_structure('<D=', '=D>', reverse=True)
            for u in unopened_div:
                self.errors.append(ParserError('Unexpected EOF div', 4, u['line'], u['col'], u['token'], None, 'Division is missing an opening statement (<D=)'))
            unopened_ab = self.validate_structure('<=', '=>', reverse=True)
            for u in unopened_ab:
                self.errors.append(ParserError('Unexpected EOF ab', 5, u['line'], u['col'], u['token'], None, 'Text block is missing an opening statement (<=)'))
            unclosed_ab, ab_positions = self.validate_structure('<=', '=>', True)
            for u in unclosed_ab:
                self.errors.append(ParserError('Unexpected EOF ab', 5, u['line'], u['col'], u['token'], None, 'Text block is missing a closing statement (=>)'))
            for i in range(len(ab_positions)):
                pos = ab_positions[i]
                token = pos['token']
                line = pos['line']
                column = pos['col']
                if i > 0 and token == '<=':
                    previous = ab_positions[i - 1]
                    if pos['token'] == previous['token']:
                        self.errors.append(ParserError('Semantic Error (Text Block)', 8, line, column, '', None,
                                                       'Text blocks (<= =>) must not be nested inside each other'))

                elif i < len(ab_positions) - 1 and token == '=>':
                    consecutive = ab_positions[i + 1]
                    if pos['token'] == consecutive['token']:
                        self.errors.append(ParserError('Semantic Error (Text Block)', 8, pos['line'], pos['col'], '', None,
                                                       'Text blocks (<= =>) must not be nested inside each other'))
                try:
                    if token == '<=':
                        if lines[line + 1].startswith('<D'):
                            self.errors.append(ParserError('Structural Error', 9, line + 1, 0, '', None,
                                                           'Starting a new division (<D=) is not allowed inside a text block (<= =>)'))
                    if token == '=>':
                        if lines[line - 1].startswith('=D'):
                            self.errors.append(ParserError('Structural Error', 9, line - 1, 0, '', None,
                                                           'End of division (=D>) is not allowed inside a text block (<= =>)'))
                except IndexError:
                    pass
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
        self.send_progress_update(100)

    def set_text(self, text):
        self.text = text

    def set_lines_changed_indices(self, lines):
        self.lines_changed_indices = lines

    def set_previous_text(self, text):
        self.previous_text = text
