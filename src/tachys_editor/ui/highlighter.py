from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor


class TachysHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.text = '[ ’͵;,·˙\u037e-\u03ce\u03da-\u03e4\u1f00-\u1fb0\u1fb2-\u1fb8\u1fba-\u1fd0\u1fd2-\u1fd8\u1fda-\u1fe0\u1fe2-\u1fe8\u1fea-\u1ffe\u0300-\u0301\u0313-\u0314\u0340-\u0345]'
        self.highlighting_rules = []
        self.do_error_highlighting = False
        self.parser_errors = []
        self.markup_format = QTextCharFormat()
        self.markup_format.setForeground(QColor("green"))
        self.unclear_format = QTextCharFormat()
        self.unclear_format.setForeground(QColor("darkGreen"))
        self.special_format = QTextCharFormat()
        self.special_format.setForeground(QColor("blue"))
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("darkMagenta"))
        self.line_format = QTextCharFormat()
        self.line_format.setForeground(QColor('darkBlue'))
        self.div_format = QTextCharFormat()
        self.div_format.setForeground(QColor("darkBlue"))
        self.super_div_format = QTextCharFormat()
        self.super_div_format.setForeground(QColor("purple"))
        self.def_lang_Format = QTextCharFormat()
        self.def_lang_Format.setForeground(QColor("purple"))
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(QColor("red"))
        self.error_format.setForeground(QColor("red"))
        self.error_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        self.set_highlighting_rules()
        self.compiled_rules = [(QRegularExpression(pattern), formatting) for pattern, formatting in self.highlighting_rules]
        self.error_map = {}

    def set_highlighting_rules(self):
        # marked up text
        self.highlighting_rules.append((r'\[.*?\]', self.markup_format))
        self.highlighting_rules.append((r'〚[^〛]+〛', self.markup_format))
        self.highlighting_rules.append((r'<[^>]+>', self.markup_format))
        self.highlighting_rules.append((r'<:.*?:>', self.markup_format))
        self.highlighting_rules.append((r'\{[^}]+\}', self.markup_format))
        self.highlighting_rules.append((r'\((?:[^()]|\([^()]*\))*\)', self.markup_format))
        self.highlighting_rules.append((r'\\[^\/]+\/', self.markup_format))
        self.highlighting_rules.append((r'~[^l]+ll', self.markup_format))
        self.highlighting_rules.append((r'~[^~]+~', self.markup_format))
        self.highlighting_rules.append((r'/[^\/]+\/', self.markup_format))
        self.highlighting_rules.append((r'\|.*?\|', self.markup_format))
        self.highlighting_rules.append((r'\|\|.*?\|\|', self.markup_format))
        self.highlighting_rules.append((r'¯[^¯]+¯', self.markup_format))
        self.highlighting_rules.append((r'_[^_]_', self.markup_format))
        # unclear
        self.highlighting_rules.append((self.text + '\u0323', self.unclear_format))
        self.highlighting_rules.append((self.text + '\u0304|[ᾱᾹῑῙῡῩ]', self.unclear_format))
        # special format
        self.highlighting_rules.append((r'\$.[^ ]+ ', self.special_format))
        self.highlighting_rules.append((r'#[a-zA-Z0-9][^ ]+ ', self.special_format))
        self.highlighting_rules.append((r'###', self.special_format))
        self.highlighting_rules.append((r'-\$\$-', self.special_format))
        self.highlighting_rules.append((r'\*.*?\*', self.special_format))
        resp = QRegularExpression(r'=[ \-.:,()\p{L}0-9]+')
        self.highlighting_rules.append((resp, self.special_format))
        self.highlighting_rules.append((r'=[0-9]+(/[0-9]+)?', self.special_format))
        # keywords
        self.highlighting_rules.append((r'\|(ed|reg|subst|alt|corr)\|', self.keyword_format))
        self.highlighting_rules.append((r'\|', self.keyword_format))
        self.highlighting_rules.append((r'<:|:>', self.keyword_format))
        self.highlighting_rules.append((r'<|>', self.keyword_format))
        self.highlighting_rules.append((r'{|}', self.keyword_format))
        self.highlighting_rules.append((r'〚|〛', self.keyword_format))
        self.highlighting_rules.append((r'\[|\]', self.keyword_format))
        self.highlighting_rules.append((r'\(|\)', self.keyword_format))
        self.highlighting_rules.append((r'\(?\?\)?', self.keyword_format))
        self.highlighting_rules.append((r'(left|right|interlin):', self.keyword_format))
        self.highlighting_rules.append((r'\^|_|#|\\|\/', self.keyword_format))
        self.highlighting_rules.append((r'¨| ῾|´| ᾿|`', self.keyword_format))
        # overwrite diacriticals
        self.highlighting_rules.append((r'\((^|¨| ῾|´| ᾿|`)\)', self.special_format))
        # overwrite .?
        self.highlighting_rules.append((r'(ca)?\.[0-9\?]+-?[0-9]*', self.special_format))
        self.highlighting_rules.append((r'vac\.(ca\.)?[0-9\?]+-?[0-9]*(lin)?', self.special_format))
        self.highlighting_rules.append((r'lost\.[0-9\?]+-?[0-9]*(lin)', self.special_format))
        self.highlighting_rules.append((r'vestig\.[0-9\?]+-?[0-9]*(lin)?', self.special_format))
        # one-line symbols
        self.highlighting_rules.append((r'--------', self.special_format))
        self.highlighting_rules.append((r'----', self.special_format))
        self.highlighting_rules.append((r'~~~~~~~~', self.special_format))
        self.highlighting_rules.append((r'>---', self.special_format))
        # line numbers
        self.highlighting_rules.append((r'[0-9a-z]+\.\- ', self.line_format))
        self.highlighting_rules.append((r'^[0-9a-z]+\.\-?', self.line_format))
        self.highlighting_rules.append((r'^[0-9a-z]+/[0-9a-z]+\.\-?', self.line_format))
        self.highlighting_rules.append((r'^\([0-9a-z]+\-?.*?\)', self.line_format))
        self.highlighting_rules.append((r'^[0-9a-z]+\-?,.*?\.', self.line_format))
        # div
        self.highlighting_rules.append((r'<D=.+<=', self.div_format))
        self.highlighting_rules.append((r'=>=D>', self.div_format))
        # super_div
        self.highlighting_rules.append((r'<D=.[0-9a-z\.]+$', self.super_div_format))
        self.highlighting_rules.append((r'^=D>$', self.super_div_format))
        # default language
        self.highlighting_rules.append((r'<S=\.[a-zA-Z-]+', self.def_lang_Format))

    def highlightBlock(self, text):
        for expression, formatting in self.compiled_rules:
            match = expression.globalMatch(text)  # globalMatch is faster for loops
            while match.hasNext():
                m = match.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), formatting)
        if self.do_error_highlighting:
            line_num = self.currentBlock().blockNumber()
            if line_num in self.error_map:
                for error_id, column, _ in self.error_map[line_num]:
                    index = column - 1
                    if error_id == 0:
                        format_count = len(text) - index
                    elif error_id == 1:
                        format_count = len(text) - index
                    elif error_id == 2:
                        column = 2
                        format_count = len(text)
                    else:
                        break
                    self.setFormat(column - 2, format_count + 1, self.error_format)

    def update_error_highlighting(self, error_data):
        print(f'Highlighter: highlight errors {error_data}')
        self.do_error_highlighting = True
        self.error_map = {}
        for error_id, line, column, char in error_data:
            if line not in self.error_map:
                self.error_map[line] = []
            self.error_map[line].append((error_id, column, char))
        self.rehighlight()
        self.do_error_highlighting = False