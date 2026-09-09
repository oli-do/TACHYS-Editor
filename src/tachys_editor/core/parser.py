from importlib.resources import files
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Literal

import lark.exceptions

from ..shared.grammar import build_text_rules
from .transformer import LeidenPlusTransformer

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
    """
    Stores Error Information.

    Attributes:
        type: Type or name of the error.
        id: Error ID:
        line: Line number of the error.
        column: Column number of the error.
        char: Affected character.
        expected: Expected set of characters.
        details: Details of the error.

    - id=0: Unexpected Characters
    - id=1: Unexpected Token
    - id=2: Unexpected EOF
    - id=3: XMLError
    - id=4: Unexpected EOF div
    - id=5: Unexpected EOF ab
    - id=6: Unexpected Document Start
    """
    type: str
    id: int
    line: int
    column: int
    char: str | None
    expected: set[str] | None
    details: str = ''

class TachysParser:
    def __init__(self):
        self.errors: list[ParserError] = []
        self.file_errors: list[ParserError] = []
        self.index: int = 0
        self.print_debug_info: bool = True
        with open(grammar_path, 'r', encoding='utf-8') as file:
            leiden_grammar = file.read()
        self.grammar = leiden_grammar
        self.lang = ''
        self.unicode_normalization: Literal['NFC', 'NFD'] = 'NFC'
        self.fast_parser = Lark(self.grammar, parser='earley', start='_leiden_line', propagate_positions=False, ambiguity='resolve', regex=True)
        self.full_parser = Lark(self.grammar, parser='earley', regex=True)
        self.executor = ProcessPoolExecutor(max_workers=3)
        self.transformer = LeidenPlusTransformer()

    def set_language(self, lang: Literal['grc', 'la', 'cop', 'any']):
        if lang == 'la':
            self.set_unicode_normalization('NFD')
        else:
            self.set_unicode_normalization('NFC')
        grammar_lines = self.grammar.splitlines()
        index_text_rule = None
        index_text_char_rule = None
        for i in range(len(grammar_lines)):
            target = grammar_lines[i]
            if target.startswith('TEXT:'):
                index_text_rule = i
            if target.startswith('TEXT_CHAR:'):
                index_text_char_rule = i
        if not index_text_rule or not index_text_char_rule:
            return False
        grammar_lines[index_text_rule], grammar_lines[index_text_char_rule] = build_text_rules(lang)
        self.lang = lang
        self.grammar = '\n'.join(grammar_lines)
        self.fast_parser = Lark(self.grammar, parser='earley', start='_leiden_line', propagate_positions=False,
                                ambiguity='resolve', regex=True)
        self.full_parser = Lark(self.grammar, parser='earley', regex=True)
        self.errors = []
        return True

    def set_unicode_normalization(self, norm: Literal['NFC', 'NFD']):
        self.unicode_normalization = norm

    def set_print_debug_info(self, print_debug_info: bool):
        self.print_debug_info = print_debug_info

    def parse_full(self, text):
        text = unicodedata.normalize(self.unicode_normalization, text)
        if self.print_debug_info:
            print('\n### PARSE ###\n')
            print(f'TEXT\n{text}')
        try:
            tree = self.full_parser.parse(text)
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

    def validate_line_errors(self, lines: list[str], errors: list[ParserError]) -> tuple[list[ParserError], None] | tuple[list[ParserError], list[tuple[int, str]]]:
        """
        Validate line errors by parsing with context.

        This function uses contextual parsing to expand single line parsing in case of tags spanning multiple lines.
        It deletes reported errors if it detects a multi line tag.
        :param lines: text lines
        :param errors: list of ParserErrors
        """
        transformed = []
        if not errors:
            return errors, transformed
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
            return errors, transformed
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
            return errors, transformed
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
                    tree = self.fast_parser.parse('\ue747' + text)
                    errors = [error for error in errors if not error.line in group]
                    if tree:
                        xml = self.transformer.transform(tree)
                        xml_lines = list(filter(None, xml.splitlines()))
                        line_numbers = [n for n in range(start, end + 1)]
                        if len(xml_lines) == len(line_numbers):
                            for i in range(len(xml_lines)):
                                transformed.append((line_numbers[i], xml_lines[i]))
                        else:
                            errors.append(ParserError('IndexError', -1, -1, -1, '', None,
                                                      f'Transformation failed in validate_line_numbers. '
                                                      f'Reason: len(xml_lines) {len(xml_lines)} != '
                                                      f'len(line_numbers) {len(line_numbers)}'))
                except (exceptions.UnexpectedCharacters, exceptions.UnexpectedToken, exceptions.UnexpectedEOF) as e:
                    try:
                        line = group[e.line - 1]
                    except IndexError:
                        return errors, transformed
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
                except lark.exceptions.VisitError as e:
                    errors.append(ParserError(e.__class__.__name__, -1, group[0], -1, None, None, f'{e.__class__} in {self.__class__}: {e}'))
        return errors, transformed

    def parse_line(self, line: str, i: int) -> tuple[ParserError, None] | tuple[ParserError, tuple[int, str]]:
        """
        Parse a single line.
        :param line: Text line to parse.
        :param i: Index of the line to parse.
        :return: ParserError | None if no error.
        """
        line = unicodedata.normalize(self.unicode_normalization, line)
        tree = None
        transformed = None
        try:
            tree = self.fast_parser.parse('\ue747' + line)
            error = None
        except exceptions.UnexpectedCharacters as e:
            error = ParserError(e.__class__.__name__, 0, i, e.column, e.char, None)
        except exceptions.UnexpectedToken as e:
            error = ParserError(e.__class__.__name__, 1, i, e.column, None, e.expected)
        except exceptions.UnexpectedEOF as e:
            error = ParserError(e.__class__.__name__, 2, i, e.column, None, None)
        if tree:
            self.transformer.errors = []
            try:
                xml = self.transformer.transform(tree)
                xml_line = xml.replace('\n', '')
                transformed = [(i, xml_line)]
            except lark.exceptions.VisitError as e:
                return ParserError(e.__class__.__name__, -1, i, -1, None, None, f'{e.__class__} in {self.__class__}: {e}'), None
            if self.transformer.errors:
                error = ParserError('XMLError', 3, i, line.find('§'), None, None)
        return error, transformed
