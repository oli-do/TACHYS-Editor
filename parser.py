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
        self.index: int = 0
        self.print_debug_info: bool = True

    def set_print_debug_info(self, print_debug_info: bool):
        self.print_debug_info = print_debug_info

    def parse_full(self, text):
        text = unicodedata.normalize('NFC', text)
        if self.print_debug_info:
            print('\n### PARSE ###\n')
            print(f'TEXT\n{text}')
        self.errors = []
        with open('leiden_plus.lark', 'r', encoding='utf-8') as file:
            leiden_grammar = file.read()
        parser = Lark(leiden_grammar, parser='earley')
        try:
            tree = parser.parse(text)
            if self.print_debug_info:
                print(f'TREE\n{tree}')
            return tree
        except exceptions.UnexpectedCharacters as e:
            self.errors.append(ParserError(e.__class__.__name__, 0, e.line, e.column, e.char, None))
        except exceptions.UnexpectedToken as e:
            self.errors.append(ParserError(e.__class__.__name__, 1, e.line, e.column, None, e.expected))
        except exceptions.UnexpectedEOF as e:
            if e.line == -1:
                line = len(text.split('\n'))
            else:
                line = e.line
            self.errors.append(ParserError(e.__class__.__name__, 2, line, e.column, None, None))
        if self.print_debug_info:
            print(f'ERRORS\n{self.errors}')
        return None

    def parse_line(self, text, line_indices):
        text = unicodedata.normalize('NFC', text)
        lines = text.split('\n')
        with open('leiden_plus.lark', 'r', encoding='utf-8') as file:
            leiden_grammar = file.read()
        leiden_grammar = leiden_grammar.replace('_LINE_START: NEWLINE', '_LINE_START: "!"')
        parser = Lark(leiden_grammar, parser='earley', start='leiden_line')
        self.errors = []
        for i in line_indices:
            try:
                print(lines[i])
                parser.parse('!' + lines[i])
            except exceptions.UnexpectedCharacters as e:
                self.errors.append(ParserError(e.__class__.__name__, 0, i + 1, e.column, e.char, None))
            except exceptions.UnexpectedToken as e:
                self.errors.append(ParserError(e.__class__.__name__, 1, i + 1, e.column, None, e.expected))
            except exceptions.UnexpectedEOF as e:
                self.errors.append(ParserError(e.__class__.__name__, 2, i + 1, e.column, None, None))
        if self.print_debug_info:
            print(f'ERRORS\n{self.errors}')
        return None
