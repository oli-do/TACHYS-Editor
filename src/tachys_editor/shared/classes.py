from dataclasses import dataclass

@dataclass
class ParserError:
    """
    Stores Error Information.

    Attributes:
        type: Type or name of the error.
        id: Error ID
        line: Line number of the error.
        column: Column number of the error.
        char: Affected character.
        expected: Expected set of characters.
        details: Details of the error.

    - id=0: Unexpected Characters
    - id=1: Unexpected Token
    - id=2: Unexpected EOF
    - id=3: XML Error
    - id=4: Unexpected EOF div
    - id=5: Unexpected EOF ab
    - id=6: Unexpected Document Start
    - id=7: Semantic Error
    """
    type: str
    id: int
    line: int
    column: int
    char: str | None = None
    expected: set[str] | None = None
    details: str = ''