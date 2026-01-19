from lark import Lark, exceptions
from dataclasses import dataclass

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
            self.errors.append(ParserError(e.__class__.__name__, self.index, e.column, e.char, None))
        elif isinstance(e, exceptions.UnexpectedToken):
            self.errors.append(ParserError(e.__class__.__name__, self.index, e.column, None, e.expected))
        else:
            return False
        return True

    def parse(self, text):
        lines = text.splitlines()
        for i in range(len(lines)):
            self.index = i
            line = lines[i]
            print(line)
            if "=" in line:
                continue
            with open('leiden.lark', 'r', encoding='utf-8') as file:
                leiden_grammar = file.read()

                parser = Lark(leiden_grammar, parser='lalr')
            try:
                tree = parser.parse(line, on_error=self.error_handler)
            except exceptions.UnexpectedCharacters:
                pass
            except exceptions.UnexpectedToken:
                pass
