from lark import Lark, exceptions
from dataclasses import dataclass
from itertools import groupby
from operator import itemgetter
import unicodedata

@dataclass
class ParserError:
    type: str
    id: int
    line: int
    column: int
    char: str | None
    expected: set[str] | None

class LeidenParser:
    def __init__(self):
        self.errors: list[ParserError] = []
        self.file_errors: list[ParserError] = []
        self.index: int = 0
        self.print_debug_info: bool = True
        with open('leiden_plus.lark', 'r', encoding='utf-8') as file:
            leiden_grammar = file.read()
        self.grammar = leiden_grammar

    def set_print_debug_info(self, print_debug_info: bool):
        self.print_debug_info = print_debug_info

    def parse_full(self, text, is_debugger=True, on_ambiguity=None):
        text = unicodedata.normalize('NFC', text)
        if self.print_debug_info:
            print('\n### PARSE ###\n')
            print(f'TEXT\n{text}')
        with open('leiden_plus.lark', 'r', encoding='utf-8') as file:
            leiden_grammar = file.read()
        if is_debugger:
            parser = Lark(leiden_grammar, parser='earley', propagate_positions=False, maybe_placeholders=False, ambiguity='resolve', regex=True)
        else:
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

    def validate_line_errors(self, lines):
        """
        Validate line errors by parsing with context.

        This function uses contextual parsing to expand single line parsing in case of apparatus tags spanning multiple
        lines. It deletes reported errors if it detects a multi line apparatus.
        :param lines: text lines
        """
        if not self.errors:
            return
        print('##### parser.validate_line_errors()')
        print('### received errors:', self.errors)
        needs_validation = []
        for error in self.errors:
            if error.id == 0:
                if error.char == '\n' or error.char == '<' or error.char == '>' or error.char == ':' or error.char == '|':
                    needs_validation.append(error.line)
            elif error.id == 2:
                needs_validation.append(error.line)
        print('Needs validation:', needs_validation)
        groups = []
        parser = Lark(self.grammar, parser='earley', start='_leiden_lines', propagate_positions=False,
                      maybe_placeholders=False, ambiguity='resolve', regex=True)
        # idea: match <:.*?$, find next :> in following lines; processing range is start <: to end :> unless end opens
        # another <:.*?$, then keep looking
        for k, g in groupby(enumerate(needs_validation), lambda x: x[1] - x[0]):
            group = list(map(itemgetter(1), g))
            groups.append(group)
        for group in groups:
            if len(group) == 1:
                index = group[0]
                group = [index]
                minus_expansion = [index - x for x in range(1,2)]
                plus_expansion = [index + x for x in range(1,2)]
                for ex in minus_expansion:
                    if ex >= 0:
                        group.append(ex)
                for ex in plus_expansion:
                    if ex < len(lines):
                        group.append(ex)
                group = list(sorted(group))
            line_texts = []
            for index in group:
                line_texts.append(lines[index])
            text = '\n'.join(line_texts)
            print('block text', text, group)
            try:
                parser.parse('\ue747' + text)
                self.errors = [error for error in self.errors if not error.line in group]
                print('### errors final', self.errors)
            except (exceptions.UnexpectedCharacters, exceptions.UnexpectedToken, exceptions.UnexpectedEOF) as e:
                try:
                    line = group[e.line - 1]
                except IndexError:
                    return
                self.errors = [error for error in self.errors if not error.line == line]
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
                    self.errors.append(ParserError(e.__class__.__name__, error_id, line, e.column, char, expected))

    def parse_line(self, lines, line_indices):
        parser = Lark(self.grammar, parser='earley', start='_leiden_line', propagate_positions=False, maybe_placeholders=False, ambiguity='resolve', regex=True)
        for i in line_indices:
            self.errors = [error for error in self.errors if not error.line == i]
            line = lines[i]
            line = unicodedata.normalize('NFC', line)
            try:
                parser.parse('\ue747' + line)
            except exceptions.UnexpectedCharacters as e:
                self.errors.append(ParserError(e.__class__.__name__, 0, i, e.column, e.char, None))
            except exceptions.UnexpectedToken as e:
                self.errors.append(ParserError(e.__class__.__name__, 1, i, e.column, None, e.expected))
            except exceptions.UnexpectedEOF as e:
                self.errors.append(ParserError(e.__class__.__name__, 2, i, e.column, None, None))
        self.validate_line_errors(lines)
        if self.print_debug_info:
            print(f'ERRORS\n{self.errors}')
        return None
