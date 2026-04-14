from importlib.resources import files
from dataclasses import dataclass

import unicodedata
from lark import Lark, exceptions


grammar_path = str(files('tachys_editor.resources').joinpath('leiden_plus.lark'))


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

    @staticmethod
    def find_multiline_pairs(lines, opening: str, closing: str):
        stack = []
        pairs = []
        len_opening = len(opening)
        len_closing = len(closing)
        for line_num, text in enumerate(lines, 0):
            if not opening in text and not closing in text:
                continue
            i = 0
            while i < len(text):
                if text[i:i + len_opening] == opening:
                    stack.append({'line': line_num, 'pos': i})
                    i += len_opening
                elif text[i:i + len_closing] == closing:
                    if stack:
                        opening_tag = stack.pop()
                        pairs.append((opening_tag['line'], line_num))
                    i += len_closing
                else:
                    i += 1
        return pairs

    def validate_line_errors(self, lines: list[str], errors: list[ParserError]):
        """
        Validate line errors by parsing with context.

        This function uses contextual parsing to expand single line parsing in case of apparatus tags spanning multiple
        lines. It deletes reported errors if it detects a multi line apparatus.
        :param lines: text lines
        :param errors: list of ParserErrors
        """
        if not errors:
            return errors
        needs_validation = []
        for error in errors:
            if error.id == 0:
                char = error.char
                if char == '\n' or char == '<' or char == '>' or char == ':' or char == '|' or char == '(' or char == ')':
                    needs_validation.append(error.line)
            elif error.id == 2:
                needs_validation.append(error.line)
        if not needs_validation:
            return errors
        pairs = self.find_multiline_pairs(lines, '<:', ':>')
        pairs += self.find_multiline_pairs(lines, '(', ')')
        stack = []
        for line_num, text in enumerate(lines, 0):
            if not '"' in text:
                continue
            i = 0
            while i < len(text):
                if text[i:i + 1] == '"':
                    if not stack:
                        stack.append({'line': line_num, 'pos': i})
                    else:
                        opening_tag = stack.pop()
                        pairs.append((opening_tag['line'], line_num))
                i += 1
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
            if start != end:
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
