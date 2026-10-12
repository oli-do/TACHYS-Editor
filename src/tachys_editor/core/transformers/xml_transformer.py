from pathlib import Path
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from tachys_editor.shared.transformer_helper import validate_epidoc_tei, EssentialAttributeMissingException
from lxml import etree

class EpiDocTransformer:
    def __init__(self):
        self.text = ''
        self.errors = []

    def transform(self, xml: Path | str):
        self.text = ''
        self.errors = []
        success, info = validate_epidoc_tei(xml)
        if success:
            if isinstance(xml, Path):
                with open(xml, "r", encoding="utf-8") as f:
                    xml_content = f.read()
                soup = BeautifulSoup(xml_content, "lxml-xml")
                lxml_root = etree.fromstring(xml_content.encode("utf-8"))
                lxml_elements = list(lxml_root.iter())
                bs_elements = list(soup.find_all(True))
                for bs_tag, lxml_el in zip(bs_elements, lxml_elements):
                    bs_tag.sourceline = lxml_el.sourceline
            else:
                soup = BeautifulSoup(xml, 'lxml-xml')
            main_div = soup.find('div', attrs={'type': 'edition'})
            if main_div:
                has_lines = main_div.find('lb')
                if has_lines:
                    try:
                        self.text += self.transform_node(main_div)
                    except EssentialAttributeMissingException:
                        return ''
                    lines = [str(line) for line in self.text.splitlines() if line is not None and str(line).strip()]
                    self.text = '\n'.join(lines)
                    self.text = self.text.replace('=>=D>=D>', '=>=D>\n=D>')
                    return self.text
                else:
                    return '<S=.grc\n<D=.1.fragment<=\n1. \n=>=D>'
            else:
                self.errors.append(f'There is no <div> with @type="edition" in "{xml}".')
                return ''
        else:
            self.errors = info
            return ''

    def unsupported_attribute_value(self, node: Tag, attribute_name: str, attribute_value: str):
        node_copy = node.copy_self()
        line = f' line {node.sourceline},' if node.sourceline else ''
        self.errors.append(f'Unsupported attribute value: @{attribute_name}="{attribute_value}" in{line} '
                           f'node {str(node_copy)}.')

    def unsupported_attribute(self, node: Tag):
        node_copy = node.copy_self()
        line = f' line {node.sourceline},' if node.sourceline else ''
        self.errors.append(f'Unsupported attribute:{line} node {str(node_copy)}.')

    def essential_attribute_missing(self, node: Tag, attribute_name: str):
        node_copy = node.copy_self()
        line = f' line {node.sourceline},' if node.sourceline else ''
        msg = (f'Essential attribute @{attribute_name} is missing in{line} '
               f'node {node_copy}.')
        self.errors.append(msg)
        raise EssentialAttributeMissingException(msg)

    def convert(self, node: Tag) -> str:
        result = []
        for content in node.contents:
            if isinstance(content, Tag):
                result.append(self.transform_node(content))
            elif isinstance(content, NavigableString):
                result.append(str(content))
        return "".join(result)


    def transform_node(self, node: Tag):
        contents = node.contents
        name = node.name
        start, end = f'<{node.name}>', f'</{node.name}>'
        if name == 'del':
            name = 'deletion'
        if hasattr(self, name):
            function = getattr(self, name)
            if name == 'unclear':
                return function(node)
            start, end = function(node)
        if contents:
            return f'{start}{self.convert(node)}{end}'
        else:
            return f'{start}{end}'

    def div(self, node: Tag):
        attrs = node.attrs
        div_type = str(attrs['type'])
        if div_type == 'edition':
            try:
                lang = attrs['xml:lang']
            except KeyError:
                return self.essential_attribute_missing(node, 'xml:lang')
            return f'<S=.{lang}\n', ''
        elif div_type == 'textpart':
            n = attrs['n']
            if 'subtype' in attrs:
                subtype = '.' + str(attrs['subtype'])
            else:
                subtype = ''
            return f'\n<D=.{n}{subtype}', '=D>'
        else:
            self.unsupported_attribute_value(node, 'type', div_type)
            return '', ''

    @staticmethod
    def ab(node: Tag):
        return '<=', '\n=>'

    def lb(self, node: Tag):
        attrs = node.attrs
        try:
            lb_n = attrs['n']
        except KeyError:
            return self.essential_attribute_missing(node, 'n')
        parent = node.parent.name
        if parent in ['reg', 'orig', 'lem', 'rdg', 'corr', 'sic']:
            new_line = ''
        else:
            new_line = '\n'
        if 'break' in attrs:
            lb_break = '-'
        else:
            lb_break = ''
        if not 'rend' in attrs:
            return f'{new_line}{lb_n}.{lb_break} ', ''
        else:
            rend = attrs['rend']
            if lb_break:
                lb_break = '.-'
            return f'{new_line}({lb_n}{lb_break}, {rend}) ', ''

    def handShift(self, node: Tag):
        attrs = node.attrs
        if 'cert' in attrs:
            cert_low = '(?)'
        else:
            cert_low = ''
        try:
            new = attrs['new']
        except KeyError:
            return self.essential_attribute_missing(node, 'new')
        return f'${new}{cert_low} ', ''

    @staticmethod
    def unclear(node: Tag):
        text = node.get_text().strip()
        unclear_text = ''
        for c in text:
            unclear_text += c + '\u0323'
        return unclear_text

    def space(self, node: Tag):
        attrs = node.attrs
        try:
            unit = attrs['unit']
        except KeyError:
            return self.essential_attribute_missing(node, 'unit')
        if unit == 'character':
            unit = ''
        else:
            unit = 'lin'
        if 'precision' in attrs:
            precision_low = 'ca.'
        else:
            precision_low = ''
        if 'atLeast' in node.attrs:
            at_least = attrs['atLeast']
            try:
                at_most = attrs['atMost']
            except KeyError:
                return self.essential_attribute_missing(node, 'atMost')
            return f'vac.{at_least}-{at_most}{unit}', ''
        elif 'extent' in attrs:
            return f'vac.?{unit}', ''
        else:
            try:
                quantity = attrs['quantity']
            except KeyError:
                return self.essential_attribute_missing(node, 'quantity')
            return f'vac.{precision_low}{quantity}{unit}', ''

    def add(self, node: Tag):
        attrs = node.attrs
        try:
            place = str(attrs['place'])
        except KeyError:
            return self.essential_attribute_missing(node, 'place')
        if 'cert' in attrs:
            cert_low = '?'
        else:
            cert_low = ''
        if place == 'above':
            return '\\', f'{cert_low}/'
        elif place == 'below':
            return '//', f'{cert_low}\\\\'
        elif place == 'left':
            return '||left:', f'{cert_low}||'
        elif place == 'right':
            return '||right:', f'{cert_low}||'
        elif place == 'interlinear':
            return '||interlin:', f'{cert_low}||'
        elif place == 'margin':
            try:
                rend = str(attrs['rend'])
            except KeyError:
                return self.essential_attribute_missing(node, 'rend')
            if rend == 'sling':
                return '<|', f'{cert_low}|>'
            elif rend == 'underline':
                return '<_', f'{cert_low}_>'
            else:
                self.unsupported_attribute_value(node, 'rend', rend)
                return '', ''
        elif place == 'inline':
            return '', '|subst|'
        else:
            self.unsupported_attribute_value(node, 'place', place)
            return '', ''

    def milestone(self, node: Tag):
        try:
            rend = str(node.attrs['rend'])
        except KeyError:
            return self.essential_attribute_missing(node, 'rend')
        if rend == 'box':
            return '### ', ''
        elif rend == 'paragraphos':
            return '----', ''
        elif rend == 'horizontal-rule':
            return '--------', ''
        elif rend == 'wavy-line':
            return '~~~~~~~~', ''
        elif rend == 'diple-obelismene':
            return '>---', ''
        elif rend == 'coronis':
            return '-$$-', ''
        else:
            self.unsupported_attribute_value(node, 'rend', rend)
            return '', ''

    def hi_diacritical(self, node: Tag, rend: str):
        parent = node.parent.name
        hi_children = [hi.attrs['rend'] for hi in node.children if isinstance(hi, Tag) and hi.name == 'hi']
        map_diacriticals = {'acute': '´', 'grave': '`'}
        try:
            additional_diacritics = ''.join([map_diacriticals[str(child)] for child in hi_children])
        except KeyError:
            return '', ''
        if rend == 'diaeresis':
            if not parent == 'hi':
                return ' ', '(¨)'
            else:
                return '', ''
        elif rend == 'asper':
            if not parent == 'hi':
                if hi_children:
                    return ' ', '( ῾' + additional_diacritics + ')'
                else:
                    return ' ', '( ῾)'
            else:
                return '', ''
        elif rend == 'acute':
            if not parent == 'hi':
                return ' ', '(´)'
            else:
                return '', ''
        elif rend == 'grave':
            if not parent == 'hi':
                return ' ', '(`)'
            else:
                return '', ''
        elif rend == 'circumflex':
            return ' ', '(^)'
        elif rend == 'lenis':
            if not parent == 'hi':
                if hi_children:
                    return ' ', '( ᾿' + additional_diacritics + ')'
                else:
                    return ' ', '( ᾿)'
            else:
                return '', ''
        else:
            self.unsupported_attribute_value(node, 'rend', rend)
            return '', ''

    def hi(self, node: Tag):
        try:
            rend = str(node.attrs['rend'])
        except KeyError:
            return self.essential_attribute_missing(node, 'rend')
        text = node.get_text()
        if rend == 'tall':
            return '~||', '||~tall'
        elif rend == 'superscript':
            return '|^', '^|'
        elif rend == 'subscript':
            return '\\|', '|/'
        elif rend == 'supraline':
            if len(text) > 1:
                return '¯', '¯'
            else:
                return '', '\u0304'
        elif rend == 'supraline-underline':
            return '¯_', '_¯'
        elif rend == 'underline':
            return '_', '_'
        elif rend in ['diaeresis', 'asper', 'acute', 'grave', 'circumflex', 'lenis']:
            return self.hi_diacritical(node, rend)
        else:
            self.unsupported_attribute_value(node, 'rend', rend)
            return '', ''

    def gap_ellipsis(self, node: Tag):
        attrs = node.attrs
        try:
            unit = attrs['unit']
        except KeyError:
            return self.essential_attribute_missing(node, 'unit')
        desc = node.find('desc')
        desc_text = desc.get_text()
        intro = 'Lang'
        if unit == 'line':
            unit = 'lines'
        else:
            unit = 'char'
        if desc_text == 'non transcribed':
            if unit == 'line':
                intro = 'Lines'
            else:
                intro = 'Chars'
            unit = 'non transcribed'
        if 'precision' in attrs:
            precision_low = 'ca.'
        else:
            precision_low = ''
        if 'atLeast' in attrs:
            at_least = attrs['atLeast']
            try:
                at_most = attrs['atMost']
            except KeyError:
                return self.essential_attribute_missing(node, 'atMost')
            return f'({intro}: ', f'{at_least}-{at_most} {unit})'
        elif 'extent' in attrs:
            return f'({intro}: ', f'? {unit})'
        elif 'quantity' in attrs:
            try:
                quantity = attrs['quantity']
            except KeyError:
                return self.essential_attribute_missing(node, 'quantity')
            return f'({intro}: ', f'{precision_low}{quantity} {unit})'
        else:
            self.unsupported_attribute(node)
            return '', ''

    @staticmethod
    def desc(node: Tag):
        return '', ''

    def gap(self, node: Tag):
        attrs = node.attrs
        try:
            reason = str(attrs['reason'])
        except KeyError:
            return self.essential_attribute_missing(node, 'reason')
        if reason == 'lost':
            gap_start = '['
            gap_end = ']'
        elif reason == 'illegible':
            gap_start = ''
            gap_end = ''
        elif reason == 'ellipsis':
            return self.gap_ellipsis(node)
        else:
            self.unsupported_attribute_value(node, 'reason', reason)
            return '', ''
        try:
            unit = attrs['unit']
        except KeyError:
            return self.essential_attribute_missing(node, 'unit')
        for child in node.children:
            if isinstance(child, Tag):
                if child.name == 'desc' and child.get_text() == 'vestiges':
                    gap_start = 'vestig'
                    gap_end = ''
                    node.clear()
        if unit == 'character':
            unit = ''
        if 'precision' in attrs:
            precision_low = 'ca.'
        else:
            precision_low = ''
        if 'atLeast' in attrs:
            at_least = attrs['atLeast']
            try:
                at_most = attrs['atMost']
            except KeyError:
                return self.essential_attribute_missing(node, 'atMost')
            return f'{gap_start}.{at_least}-{at_most}{unit}{gap_end}', ''
        elif 'extent' in attrs:
            if not unit:
                return f'{gap_start}.?{unit}{gap_end}', ''
            else:
                return f'lost.?lin', ''
        elif 'quantity' in attrs:
            try:
                quantity = attrs['quantity']
            except KeyError:
                return self.essential_attribute_missing(node, 'quantity')
            return f'{gap_start}.{precision_low}{quantity}{unit}{gap_end}', ''
        else:
            return '[', ']'

    @staticmethod
    def certainty(node: Tag):
        return '(?)', ''

    def supplied(self, node: Tag):
        attrs = node.attrs
        reason = str(attrs['reason'])
        if 'cert' in attrs:
            cert_low = '(?)'
        else:
            cert_low = ''
        if reason == 'omitted':
            return '<', f'{cert_low}>'
        elif reason == 'lost':
            if not 'evidence' in attrs:
                return '[', f'{cert_low}]'
            else:
                return '_[', f'{cert_low}]_'
        elif reason == 'undefined':
            return '[', f'{cert_low}]'
        elif reason == 'lost':
            return '[', f'{cert_low}]'
        else:
            self.unsupported_attribute_value(node, 'reason', reason)
            return '', ''

    @staticmethod
    def surplus(node: Tag):
        return '{', '}'

    def deletion(self, node: Tag):
        try:
            rend = str(node.attrs['rend'])
        except KeyError:
            return self.essential_attribute_missing(node, 'rend')
        if rend == 'erasure':
            return '〚', '〛'
        elif rend == 'slashes':
            return '〚/ ', '〛'
        elif rend == 'cross-strokes':
            return '〚X ', '〛'
        elif rend == 'corrected':
            if node.parent.name == 'subst':
                return '', ''
            else:
                return '[[', ']]'
        else:
            self.unsupported_attribute_value(node, 'rend', rend)
            return '', ''

    def expan(self, node: Tag):
        return '(', ')'

    def ex(self, node: Tag):
        if 'cert' in node.attrs:
            cert_low = '?'
        else:
            cert_low = ''
        return '(', f'{cert_low})'

    @staticmethod
    def abbr(node: Tag):
        return '(|', '|)'

    @staticmethod
    def note(node: Tag):
        return '/*', '*/'

    @staticmethod
    def q(node: Tag):
        return '"', '"'

    def choice(self, node: Tag):
        return '<:', ':>'

    @staticmethod
    def reg(node: Tag):
        attrs = node.attrs
        if 'cert' in attrs:
            cert_low = '(?)'
        else:
            cert_low = ''
        if 'xml:lang' in attrs:
            xml_lang = '=' + str(attrs['xml:lang'])
        else:
            xml_lang = ''
        sibling = node.next_sibling
        if sibling is None:
            return '', f'{cert_low}{xml_lang}'
        elif isinstance(sibling, Tag):
            if sibling.name == 'reg':
                return '', f'{cert_low}{xml_lang}|'
            else:
                return '', f'{cert_low}{xml_lang}'
        else:
            return '', f'{cert_low}{xml_lang}'

    @staticmethod
    def orig(node: Tag):
        regs = [sibling for sibling in node.previous_siblings if isinstance(sibling, Tag) and sibling.name == 'reg']
        if len(regs) == 1:
            return '|reg|', ''
        else:
            return '||reg||', ''

    def app(self, node: Tag):
        return '<:', ':>'

    @staticmethod
    def lem(node: Tag):
        if 'resp' in node.attrs:
            resp = '=' + str(node.attrs['resp'])
        else:
            resp = ''
        parent = node.parent
        app_type = parent.attrs['type']
        rdgs = [sibling for sibling in node.next_siblings if isinstance(sibling, Tag) and sibling.name == 'rdg']
        if len(rdgs) == 0:
            return '', ''
        if app_type == 'editorial':
            if len(rdgs) == 1:
                return '', f'{resp}|ed|'
            else:
                return '', f'{resp}||ed||'
        else:
            if len(rdgs) == 1:
                return '', '|alt|'
            else:
                return '', '||alt||'

    @staticmethod
    def rdg(node: Tag):
        if 'resp' in node.attrs:
            resp = '=' + str(node.attrs['resp'])
        else:
            resp = ''
        sibling = node.next_sibling
        if sibling is None:
            return '', f'{resp}'
        elif isinstance(sibling, Tag):
            if sibling.name == 'rdg':
                return '', f'{resp}|'
            else:
                return '', f'{resp}'
        else:
            return '', f'{resp}'

    def subst(self, node: Tag):
        return '<:', ':>'

    @staticmethod
    def corr(node: Tag):
        if 'cert' in node.attrs:
            cert_low = '(?)'
        else:
            cert_low = ''
        return '', f'{cert_low}|corr|'

    @staticmethod
    def sic(node: Tag):
        return '', ''

    @staticmethod
    def num(node: Tag):
        if 'rend' in node.attrs:
            rend = " '"
        else:
            rend = ""
        if 'value' in node.attrs:
            value = '=' + str(node.attrs['value'])
        else:
            value = '='
        return '<#', f'{rend}{value}#>'

    def g(self, node: Tag):
        g_type = node.attrs['type']
        parent = node.parent.name
        if parent == 'unclear':
            unclear = '?'
        else:
            unclear = ''
        if 'rend' in node.attrs:
            rend = node.attrs['rend']
            return f'*{g_type}({rend}){unclear}*', ''
        else:
            return f'*{g_type}{unclear}*', ''

    @staticmethod
    def figure(node: Tag):
        return '', ''

    @staticmethod
    def figDesc(node: Tag):
        return '#', ' '

    @staticmethod
    def foreign(node: Tag):
        lang = node.attrs['xml:lang']
        return '~|', f'|~{lang} '