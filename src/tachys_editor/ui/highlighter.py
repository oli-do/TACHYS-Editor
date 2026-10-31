from PySide6.QtCore import QRegularExpression, Slot
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor

from tachys_editor.shared.settings import settings_mgr


def set_color(color: str):
    theme = settings_mgr.appearance.theme
    if theme == 'Dark':
        if color == 'red':
            return 'red'
        if color == 'blue':
            return QColor('cyan')
        elif color == 'darkBlue':
            return QColor('cyan')
        elif 'dark' in color:
            return color.replace('dark', '')
        elif color == 'darkOrange':
            return QColor('yellow').lighter()
        else:
            color = QColor(color)
            new_color = color.lighter(300)
        return new_color.name()
    else:
        if color == 'darkYellow':
            return QColor('yellow').darker(180).name()
        return color


class TachysHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.text = r'[\p{L}]'
        self.highlighting_rules = []
        self.do_error_highlighting = False
        self.parser_errors = []
        self.markup_format = QTextCharFormat()
        self.markup_format.setForeground(QColor(set_color('green')))
        self.unclear_format = QTextCharFormat()
        self.unclear_format.setForeground(QColor(set_color('darkGreen')))
        self.special_format = QTextCharFormat()
        self.special_format.setForeground(QColor(set_color("blue")))
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(set_color("darkMagenta")))
        self.line_format = QTextCharFormat()
        self.line_format.setForeground(QColor(set_color('darkBlue')))
        self.div_format = QTextCharFormat()
        self.div_format.setForeground(QColor(set_color("darkBlue")))
        self.super_div_format = QTextCharFormat()
        self.super_div_format.setForeground(QColor(set_color("purple")))
        self.def_lang_Format = QTextCharFormat()
        self.def_lang_Format.setForeground(QColor(set_color("purple")))
        self.xml_format = QTextCharFormat()
        self.xml_format.setForeground(QColor(set_color("darkOrange")))
        self.xml_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.DotLine)
        self.xml_attr_format = QTextCharFormat()
        self.xml_attr_format.setForeground(QColor(set_color('darkYellow')))
        self.xml_attr_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.DotLine)
        self.xml_attr_format.setUnderlineColor(set_color("darkOrange"))
        self.xml_value_format = QTextCharFormat()
        self.xml_value_format.setForeground(QColor(set_color("darkGreen")))
        self.xml_value_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.DotLine)
        self.xml_value_format.setUnderlineColor(set_color("darkOrange"))
        self.xml_text_format = QTextCharFormat()
        self.xml_text_format.setForeground(QColor(set_color("darkYellow")))
        self.xml_text_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.DotLine)
        self.xml_text_format.setUnderlineColor(set_color("darkOrange"))
        self.xml_value_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.DotLine)
        self.xml_value_format.setUnderlineColor(set_color("darkOrange"))
        self.xml_section_regex = QRegularExpression(r'§([^§]+)§')
        self.xml_tag_regex = QRegularExpression(r'</?([\w:-]+)')
        self.xml_attr_regex = QRegularExpression(r'([\w:-]+)=("[^"]*"|\'[^\']*\')')
        self.xml_text_regex = QRegularExpression(r'>([^<]+)<')
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(QColor(set_color("red")))
        self.error_format.setForeground(QColor(set_color("red")))
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
            match = expression.globalMatch(text)
            while match.hasNext():
                m = match.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), formatting)
        if '§' in text:
            xml_matches = self.xml_section_regex.globalMatch(text)
            while xml_matches.hasNext():
                m = xml_matches.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), self.xml_format)
                content_start = m.capturedStart(1)
                content_text = m.captured(1)

                # Highlight Tag Names
                tag_matches = self.xml_tag_regex.globalMatch(content_text)
                while tag_matches.hasNext():
                    tm = tag_matches.next()
                    self.setFormat(content_start + tm.capturedStart(1), tm.capturedLength(1), self.xml_format)

                # Highlight Attributes
                attr_matches = self.xml_attr_regex.globalMatch(content_text)
                while attr_matches.hasNext():
                    am = attr_matches.next()
                    self.setFormat(content_start + am.capturedStart(1), am.capturedLength(1), self.xml_attr_format)
                    self.setFormat(content_start + am.capturedStart(2), am.capturedLength(2), self.xml_value_format)

                # Highlight Inner Text
                text_matches = self.xml_text_regex.globalMatch(content_text)
                while text_matches.hasNext():
                    tm = text_matches.next()
                    self.setFormat(content_start + tm.capturedStart(1), tm.capturedLength(1), self.xml_text_format)
        if self.do_error_highlighting:
            line_num = self.currentBlock().blockNumber()
            if line_num in self.error_map:
                for error_id, column, _ in self.error_map[line_num]:
                    index = column - 1
                    start = column - 2
                    if error_id == 0:
                        format_count = len(text) - index
                    elif error_id == 1:
                        format_count = len(text) - index
                    elif error_id == 2:
                        start = 0
                        format_count = len(text)
                    elif error_id in [3, 4, 5, 6, 7]:
                        format_count = len(text) - index
                        start = column
                    else:
                        break
                    self.setFormat(start, format_count + 1, self.error_format)

    @Slot(list)
    def update_error_highlighting(self, error_data):
        print(f'Highlighter: highlight errors {error_data}')
        self.do_error_highlighting = True
        previous_error_lines = list(self.error_map.keys())
        self.error_map = {}
        if error_data:
            for error_id, line, column, char, _ in error_data:
                if line not in self.error_map:
                    self.error_map[line] = []
                self.error_map[line].append((error_id, column, char))
        doc = self.document()
        for line_num in list(self.error_map.keys()) + previous_error_lines:
            block = doc.findBlockByNumber(line_num)
            if block.isValid():
                self.rehighlightBlock(block)