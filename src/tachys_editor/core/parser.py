from importlib.resources import files
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed

import unicodedata
from lark import Lark, exceptions


grammar_path = str(files('tachys_editor.resources').joinpath('leiden_plus.lark'))


def find_multiline_pairs(lines: list[str], opening: str, closing: str = None):
    stack = []
    pairs = []
    len_opening = len(opening)
    if closing:
        len_closing = len(closing)
        for line_num, text in enumerate(lines, 0):
            i = 0
            while i < len(text):
                index_opening = text.find(opening, i)
                index_closing = text.find(closing, i)
                if index_opening != -1 and (index_closing == -1 or index_opening < index_closing):
                    stack.append(line_num)
                    i = index_opening + len_opening
                elif index_closing != -1:
                    if stack:
                        start_line = stack.pop()
                        if start_line != line_num:
                            pairs.append((start_line, line_num))
                    i = index_closing + len_closing
                else:
                    break
    else:
        for line_num, text in enumerate(lines, 0):
            i = 0
            while i < len(text):
                index_opening = text.find(opening, i)
                if index_opening == -1:
                    break
                if not stack:
                    stack.append(line_num)
                else:
                    start_line = stack.pop()
                    if start_line != line_num:
                        pairs.append((start_line, line_num))
                i = index_opening + len_opening
    return pairs


@dataclass
class ParserError:
    type: str
    id: int
    line: int
    column: int
    char: str | None
    expected: set[str] | None

class TachysParser:
    def __init__(self):
        self.errors: list[ParserError] = []
        self.file_errors: list[ParserError] = []
        self.index: int = 0
        self.print_debug_info: bool = True
        with open(grammar_path, 'r', encoding='utf-8') as file:
            leiden_grammar = file.read()
        self.grammar = leiden_grammar
        self.fast_parser = Lark(self.grammar, parser='earley', start='_leiden_line', propagate_positions=False, maybe_placeholders=False, ambiguity='resolve', regex=True)
        self.executor = ProcessPoolExecutor(max_workers=3)

    def set_print_debug_info(self, print_debug_info: bool):
        self.print_debug_info = print_debug_info

    def parse_full(self, text):
        text = unicodedata.normalize('NFC', text)
        if self.print_debug_info:
            print('\n### PARSE ###\n')
            print(f'TEXT\n{text}')
        with open(grammar_path, 'r', encoding='utf-8') as file:
            leiden_grammar = file.read()
        parser = Lark(leiden_grammar, parser='earley', regex=True)
        try:
            tree = parser.parse(text)
            if self.print_debug_info:
                print(f'TREE\n{tree}')
            self.errors = []
            return tree
        except exceptions.UnexpectedCharacters as e:
            self.file_errors.append(ParserError(e.__class__.__name__, 0, e.line, e.column, e.char, None))
        except exceptions.UnexpectedToken as e:
            self.file_errors.append(ParserError(e.__class__.__name__, 1, e.line, e.column, None, e.expected))
        except exceptions.UnexpectedEOF as e:
            if e.line == -1:
                line = len(text.split('\n'))
            else:
                line = e.line
            self.file_errors.append(ParserError(e.__class__.__name__, 2, line, e.column, None, None))
        if self.print_debug_info:
            print(f'FILE ERRORS\n{self.file_errors}')
        return None

    def validate_line_errors(self, lines: list[str], errors: list[ParserError]):
        """
        Validate line errors by parsing with context.

        This function uses contextual parsing to expand single line parsing in case of tags spanning multiple lines.
        It deletes reported errors if it detects a multi line tag.
        :param lines: text lines
        :param errors: list of ParserErrors
        """
        if not errors:
            return errors
        needs_validation = []
        validate = ['\n', '<', '>', ':', '|', '(', ')']
        for error in errors:
            if error.id == 0:
                char = error.char
                if char in validate:
                    needs_validation.append(error.line)
            elif error.id == 2:
                needs_validation.append(error.line)
        if not needs_validation:
            return errors
        pairs = []
        multiline_tags = [('<:', ':>'), ('(', ')'), ('"', None)]
        futures = [self.executor.submit(find_multiline_pairs, lines, o, c) for o, c in multiline_tags]
        for future in as_completed(futures):
            result = future.result()
            if result:
                pairs += future.result()
        pairs = sorted(pairs)
        if pairs:
            merged = [list(pairs[0])]
        else:
            return errors
        for current_start, current_end in pairs[1:]:
            last_start, last_end = merged[-1]
            if current_start == last_end:
                merged[-1][1] = current_end
            else:
                merged.append([current_start, current_end])
        for pair in merged:
            start = pair[0]
            end = pair[1]
            parse = False
            group = [i for i in range(start, end + 1)]
            for error_line in needs_validation:
                if error_line in group:
                    parse = True
                    break
            if parse:
                text = '\n'.join(lines[start:end + 1])
                try:
                    self.fast_parser.parse('\ue747' + text)
                    errors = [error for error in errors if not error.line in group]
                except (exceptions.UnexpectedCharacters, exceptions.UnexpectedToken, exceptions.UnexpectedEOF) as e:
                    try:
                        line = group[e.line - 1]
                    except IndexError:
                        return errors
                    errors = [error for error in errors if not error.line == line]
                    if line >= 0:
                        error_name = e.__class__.__name__
                        if error_name == 'UnexpectedCharacters':
                            error_id = 0
                            char = e.char
                            expected = None
                        elif error_name == 'UnexpectedToken':
                            error_id = 1
                            char = None
                            expected = e.expected
                        else:
                            error_id = 2
                            char = None
                            expected = None
                        errors.append(ParserError(e.__class__.__name__, error_id, line, e.column, char, expected))
        return errors

    def parse_line(self, line: str, i: int) -> ParserError | None:
        """
        Parse a single line.
        :param line: Text line to parse.
        :param i: Index of the line to parse.
        :return: ParserError | None if no error.
        """
        line = unicodedata.normalize('NFC', line)
        try:
            self.fast_parser.parse('\ue747' + line)
            error = None
        except exceptions.UnexpectedCharacters as e:
            error = ParserError(e.__class__.__name__, 0, i, e.column, e.char, None)
        except exceptions.UnexpectedToken as e:
            error = ParserError(e.__class__.__name__, 1, i, e.column, None, e.expected)
        except exceptions.UnexpectedEOF as e:
            error = ParserError(e.__class__.__name__, 2, i, e.column, None, None)
        return error
