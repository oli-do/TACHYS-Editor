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
            self.errors.append(ParserError(e.__class__.__name__, e.line, e.column, e.char, None))
        elif isinstance(e, exceptions.UnexpectedToken):
            self.errors.append(ParserError(e.__class__.__name__, e.line, e.column, None, e.expected))
        return True

    def parse(self, text):
        self.errors = []
        with open('leiden.lark', 'r', encoding='utf-8') as file:
            leiden_grammar = file.read()
        parser = Lark(leiden_grammar, parser='lalr')
        try:
            parser.parse(text, on_error=self.error_handler)
        except exceptions.UnexpectedCharacters:
            pass
        except exceptions.UnexpectedToken:
            pass

if __name__ == '__main__':
    parser = LeidenParser()
    parser.parse('''
<S=.grc
<D=.1.fragment<=
1. 
=>=D>
    ''')
