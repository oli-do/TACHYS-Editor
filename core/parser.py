from lark import Lark, exceptions
from dataclasses import dataclass
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

    def parse_line(self, lines, line_indices):
        with open('leiden_plus.lark', 'r', encoding='utf-8') as file:
            leiden_grammar = file.read()
        leiden_grammar = leiden_grammar.replace('_LINE_START: NEWLINE', '_LINE_START: "!"')
        parser = Lark(leiden_grammar, parser='earley', start='_leiden_line', propagate_positions=False, maybe_placeholders=False, ambiguity='resolve', regex=True)
        for i in line_indices:
            for error in self.errors:
                if error.line == i + 1:
                    self.errors.remove(error)
            line = lines[i]
            line = unicodedata.normalize('NFC', line)
            try:
                parser.parse('!' + line)
            except exceptions.UnexpectedCharacters as e:
                self.errors.append(ParserError(e.__class__.__name__, 0, i + 1, e.column, e.char, None))
            except exceptions.UnexpectedToken as e:
                self.errors.append(ParserError(e.__class__.__name__, 1, i + 1, e.column, None, e.expected))
            except exceptions.UnexpectedEOF as e:
                self.errors.append(ParserError(e.__class__.__name__, 2, i + 1, e.column, None, None))
        if self.print_debug_info:
            print(f'ERRORS\n{self.errors}')
        return None
