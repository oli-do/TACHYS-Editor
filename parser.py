from lark import Lark, exceptions
from dataclasses import dataclass
import unicodedata

@dataclass
class ParserError:
    type: str
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

    def error_handler(self, e):
        if isinstance(e, exceptions.UnexpectedCharacters):
            self.errors.append(ParserError(e.__class__.__name__, e.line, e.column, e.char, None))
        elif isinstance(e, exceptions.UnexpectedToken):
            self.errors.append(ParserError(e.__class__.__name__, e.line, e.column, None, e.expected))
        return True

    def parse(self, text):
        if self.print_debug_info:
            print('\n### PARSE ###\n')
            print(f'TEXT\n{text}')
        self.errors = []
        with open('leiden_plus.lark', 'r', encoding='utf-8') as file:
            leiden_grammar = file.read()
        parser = Lark(leiden_grammar, parser='lalr')
        try:
            tree = parser.parse(text, on_error=self.error_handler)
            if self.print_debug_info:
                print(f'TREE\n{tree}')
        except exceptions.UnexpectedCharacters:
            pass
        except exceptions.UnexpectedToken:
            pass
        if self.print_debug_info:
            print(f'ERRORS\n{self.errors}')
