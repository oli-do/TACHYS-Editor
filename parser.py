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

    def error_handler(self, e):
        if isinstance(e, exceptions.UnexpectedCharacters):
            self.errors.append(ParserError(e.__class__.__name__, e.line, e.column, e.char, None))
        elif isinstance(e, exceptions.UnexpectedToken):
            self.errors.append(ParserError(e.__class__.__name__, e.line, e.column, None, e.expected))
        return True

    def parse(self, text):
        text = unicodedata.normalize('NFD', text)
        print('\n### PARSE ###')
        self.errors = []
        with open('leiden_plus.lark', 'r', encoding='utf-8') as file:
            leiden_grammar = file.read()
        parser = Lark(leiden_grammar, parser='lalr')
        try:
            tree = parser.parse(text, on_error=self.error_handler)
            print(f'TREE\n{tree}')
        except exceptions.UnexpectedCharacters:
            pass
        except exceptions.UnexpectedToken:
            pass
        print(f'ERRORS\n{self.errors}')
