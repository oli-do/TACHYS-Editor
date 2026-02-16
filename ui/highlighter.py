from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
from PySide6.QtCore import QRegularExpression

class LeidenHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.text = '[ ’͵;,·˙\u037e-\u03ce\u03da-\u03e4\u1f00-\u1fb0\u1fb2-\u1fb8\u1fba-\u1fd0\u1fd2-\u1fd8\u1fda-\u1fe0\u1fe2-\u1fe8\u1fea-\u1ffe\u0300-\u0301\u0313-\u0314\u0340-\u0345]'
        self.highlighting_rules = []
        self.set_highlighting_rules()
        self.do_error_highlighting = False
        self.parser_errors = []

    def set_highlighting_rules(self):
        # marked up text
        markup_format = QTextCharFormat()
        markup_format.setForeground(QColor("green"))
        self.highlighting_rules.append((r'\[' + self.text + r'+\]', markup_format))
        self.highlighting_rules.append((f'〚[^〛]+〛', markup_format))
        self.highlighting_rules.append((f'<[^>]+>', markup_format))
        self.highlighting_rules.append((f'<:.*?:>', markup_format))
        self.highlighting_rules.append((r'\{[^}]+\}', markup_format))
        self.highlighting_rules.append((r'\([^()]*(\([^()]*\)[^()]*)*\)', markup_format))
        self.highlighting_rules.append((r'\\[^\/]+\/', markup_format))
        self.highlighting_rules.append((r'~[^l]+ll', markup_format))
        self.highlighting_rules.append((r'~[^~]+~', markup_format))
        self.highlighting_rules.append((r'/[^\/]+\/', markup_format))
        self.highlighting_rules.append((r'\|.*?\|', markup_format))
        self.highlighting_rules.append((r'\|\|.*?\|\|', markup_format))
        self.highlighting_rules.append((r'¯[^¯]+¯', markup_format))
        self.highlighting_rules.append((r'_[^_]_', markup_format))
        self.highlighting_rules.append((self.text + '\u0323', markup_format))
        self.highlighting_rules.append((self.text + '\u0304|[ᾱᾹῑῙῡῩ]', markup_format))
        # special format
        special_format = QTextCharFormat()
        special_format.setForeground(QColor("blue"))
        self.highlighting_rules.append((r'\$.[^ ]+ ', special_format))
        self.highlighting_rules.append((r'#[a-zA-Z0-9][^ ]+ ', special_format))
        self.highlighting_rules.append((r'###', special_format))
        self.highlighting_rules.append((r'-\$\$-', special_format))
        self.highlighting_rules.append((r'\*.+\*', special_format))
        self.highlighting_rules.append((r'=[a-zA-Z, \-:]+', special_format))
        self.highlighting_rules.append((r'=[0-9]+', special_format))
        # keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("darkMagenta"))
        self.highlighting_rules.append((r'ed|reg|subst|alt|corr', keyword_format))
        self.highlighting_rules.append((r'\|', keyword_format))
        self.highlighting_rules.append((r'<:|:>', keyword_format))
        self.highlighting_rules.append((r'<|>', keyword_format))
        self.highlighting_rules.append((r'{|}', keyword_format))
        self.highlighting_rules.append((r'〚|〛', keyword_format))
        self.highlighting_rules.append((r'\[|\]', keyword_format))
        self.highlighting_rules.append((r'\(|\)', keyword_format))
        self.highlighting_rules.append((r'\(?\?\)?', keyword_format))
        self.highlighting_rules.append((r'(left|right|interlin):', keyword_format))
        self.highlighting_rules.append((r'\^|_|#|\\|\/', keyword_format))
        self.highlighting_rules.append((r'¨| ῾|´| ᾿|`', keyword_format))
        # overwrite diacriticals
        self.highlighting_rules.append((r'\((^|¨| ῾|´| ᾿|`)\)', special_format))
        # overwrite .?
        self.highlighting_rules.append((r'(ca)?\.[0-9\?]+-?[0-9]*', special_format))
        self.highlighting_rules.append((r'vac\.(ca\.)?[0-9\?]+-?[0-9]*(lin)?', special_format))
        self.highlighting_rules.append((r'lost\.[0-9\?]+-?[0-9]*(lin)?', special_format))
        self.highlighting_rules.append((r'vestig\.[0-9\?]+-?[0-9]*(lin)?', special_format))
        # one-line symbols
        self.highlighting_rules.append((r'--------', special_format))
        self.highlighting_rules.append((r'----', special_format))
        self.highlighting_rules.append((r'~~~~~~~~', special_format))
        self.highlighting_rules.append((r'>---', special_format))
        # line numbers
        line_format = QTextCharFormat()
        line_format.setForeground(QColor('darkBlue'))
        self.highlighting_rules.append((r'^[0-9]+\.\-?', line_format))
        self.highlighting_rules.append((r'^\([0-9]+\-?.+\)', line_format))
        self.highlighting_rules.append((r'^[0-9]+\-?,.+\.', line_format))
        # div
        div_format = QTextCharFormat()
        div_format.setForeground(QColor("darkBlue"))
        self.highlighting_rules.append((r'<D=.+<=', div_format))
        self.highlighting_rules.append((r'=>=D>', div_format))
        # super_div
        super_div_format = QTextCharFormat()
        super_div_format.setForeground(QColor("purple"))
        self.highlighting_rules.append((r'<D=.[0-9a-z\.]+$', super_div_format))
        self.highlighting_rules.append((r'^=D>$', super_div_format))
        # default language
        def_lang_format = QTextCharFormat()
        def_lang_format.setForeground(QColor("purple"))
        self.highlighting_rules.append((r'<S=\.[a-zA-Z-]+', def_lang_format))

    def highlightBlock(self, text):
        for pattern, formatting in self.highlighting_rules:
            expression = QRegularExpression(pattern)
            match = expression.match(text)
            index = match.capturedStart()
            while index >= 0:
                length = match.capturedLength()
                self.setFormat(index, length, formatting)
                match = expression.match(text, index + length)
                index = match.capturedStart()
        if self.do_error_highlighting:
            for error in self.parser_errors:
                error_id, line, column = error
                if self.currentBlock().blockNumber() == line - 1:
                    error_format = QTextCharFormat()
                    error_format.setUnderlineColor(QColor("red"))
                    error_format.setForeground(QColor("red"))
                    error_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
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
                    self.setFormat(column - 2, format_count + 1, error_format)

    def update_error_highlighting(self, error_data):
        self.do_error_highlighting = True
        self.parser_errors = list(error_data)
        self.rehighlight()
        self.do_error_highlighting = False