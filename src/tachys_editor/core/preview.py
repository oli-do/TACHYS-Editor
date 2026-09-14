import html

from transformer import EpiDocTransformer, EssentialAttributeMissingException
from bs4 import BeautifulSoup
from bs4 import Tag, NavigableString

apparatus_id = 0
resp = ''

class EpiDoc2HTML(EpiDocTransformer):
    line_name: str = ''
    apparatus_dict: dict[str, list[str]] = {}
    def transform(self, path: str):
        self.text = ''
        self.errors = []
        if self.is_valid_tei(path):
            soup = BeautifulSoup(open(path, 'r', encoding='utf-8'), 'lxml-xml')
            main_div = soup.find('div', attrs={'type': 'edition'})
            if main_div:
                has_lines = main_div.find('lb')
                if has_lines:
                    try:
                        self.text += self.transform_node(main_div)
                    except EssentialAttributeMissingException:
                        return ''
                    apparatus = self.generate_apparatus() if self.apparatus_dict else ''
                    lines = [str(line) for line in self.text.splitlines() if line is not None and str(line).strip()]
                    self.text = '\n'.join(lines) + apparatus
                    html_output = '<!DOCTYPE html><body><div style="font-family:IFAO-Grec Unicode; font-size:11px; width:21cm; height:29.7cm; border:2px solid black; overflow-y:scroll;">' + self.text + '</div></body></html>'
                    return html_output
                else:
                    return ''
            else:
                self.errors.append(f'There is no <div> with @type="edition" in file "{path}".')
                return ''
        else:
            return ''

    def add_to_apparatus(self, text: str):
        if self.line_name in self.apparatus_dict:
            self.apparatus_dict[self.line_name].append(text)
        else:
            self.apparatus_dict[self.line_name] = [text]

    def convert(self, node: Tag) -> str:
        global apparatus_id
        global resp
        name = node.name
        result = []
        for content in node.contents:
            if isinstance(content, Tag):
                result.append(self.transform_node(content))
            elif isinstance(content, NavigableString):
                result.append(str(content))
        output = ''.join(result)
        if name in ['reg', 'corr']:
                self.add_to_apparatus(f'l. {output}')
                return ''
        elif name == 'rdg':
            node_parent = node.parent
            if isinstance(node_parent, Tag):
                app_type = node_parent.attrs['type']
                if app_type == 'alternative':
                    self.add_to_apparatus(f'or {output} {resp}')
                else:
                    self.add_to_apparatus(f'{output} {resp}')
            return ''
        elif name == 'del':
            rend = node.attrs['rend']
            if rend == 'corrected' and node.parent.name == 'subst':
                self.add_to_apparatus(f'<span id="{apparatus_id}">corr. ex {output}</span>')
                return ''
        elif name == 'hi':
            rend = node.attrs['rend']
            if rend == 'supraline' or rend == 'supraline-underline':
                text = node.get_text().strip()
                supraline_text = ''
                for c in text:
                    if c != ' ':
                        supraline_text += c + '\u0305'
                    else:
                        supraline_text += c
                return supraline_text
        return output

    def generate_apparatus(self):
        lines = []
        for key, values in self.apparatus_dict.items():
            result = ''
            result += key + ' '
            result += ' | '.join(values)
            lines.append(result)
        return '<p style="font-size:9px;">' + ' ‖ '.join(lines) + '</p>\n'


    def div(self, node: Tag):
        attrs = node.attrs
        div_type = str(attrs['type'])
        if div_type == 'textpart':
            apparatus = ''
            if self.apparatus_dict:
                apparatus = self.generate_apparatus()
            self.apparatus_dict = {}
            n = str(attrs['n'])
            if 'subtype' in attrs:
                subtype = str(attrs['subtype'])
                return f'{apparatus}<h3>{subtype} {n}</h3>', ''
            else:
                if n == 'v':
                    n = 'verso ↓'
                elif n == 'r':
                    n = 'recto →'
                return f'{apparatus}<h3>{n}</h3>', ''
        else:
            self.unsupported_attribute_value(node, 'type', div_type)
            return '', ''

    @staticmethod
    def ab(node: Tag):
        return '<table>', '</table>'

    def lb(self, node: Tag):
        attrs = node.attrs
        if 'break' in attrs:
            lb_break = '-'
        else:
            lb_break = ''
        try:
            lb_n = str(attrs['n'])
            self.line_name = lb_n
        except KeyError:
            return self.essential_attribute_missing(node, 'n')
        try:
            lb_n = int(lb_n)
            if not lb_n % 5 == 0:
                lb_n = ''
        except ValueError:
            pass
        parent = node.parent.name
        if parent in ['reg', 'orig', 'lem', 'rdg', 'corr', 'sic']:
            new_line = ''
        else:
            new_line = '\n'
        close_tr = '</tr>'
        if parent == 'ab':
            close_tr = ''
        if not 'rend' in attrs:
            return f'{lb_break}{close_tr}{new_line}<tr><td style="padding-right: 30px;">{lb_n}</td><td>', ''
        else:
            rend = attrs['rend']
            if rend == 'indent':
                self.add_to_apparatus('in eisthesis')
                return f'{lb_break}{close_tr}{new_line}<tr><td>{lb_n}</td><td style="padding-left: 30px;">', ''
            elif rend == 'outdent':
                self.add_to_apparatus('in ekthesis')
            elif rend == 'inverse':
                self.add_to_apparatus('inversum')
            elif rend == 'perpendicular':
                self.add_to_apparatus('perpendicular in margin')
            return f'{lb_break}{close_tr}{new_line}<tr><td>{lb_n}</td><td>', ''

    def handShift(self, node: Tag):
        attrs = node.attrs
        if 'cert' in attrs:
            cert_low = '?'
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
            return '<sup>', f'{cert_low}</sup>'
        elif place == 'below':
            return '<sub>', f'{cert_low}</sub>'
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
                return '<u>', f'{cert_low}</u>'
            else:
                self.unsupported_attribute_value(node, 'rend', rend)
                return '', ''
        elif place == 'inline':
            global apparatus_id
            return '', ''
        else:
            self.unsupported_attribute_value(node, 'place', place)
            return '', ''

    def milestone(self, node: Tag):
        try:
            rend = str(node.attrs['rend'])
        except KeyError:
            return self.essential_attribute_missing(node, 'rend')
        new_line = '</tr><tr><td></td><td>'
        if rend == 'box':
            return '', ''
        elif rend == 'paragraphos':
            return f'{new_line}⸏⸏⸏⸏', ''
        elif rend == f'{new_line}horizontal-rule':
            return f'{new_line}⸏⸏⸏⸏⸏⸏⸏⸏', ''
        elif rend == 'wavy-line':
            return f'{new_line}~~~~~~~~', ''
        elif rend == 'diple-obelismene':
            return f'{new_line}⸐⸏⸏⸏', ''
        elif rend == 'coronis':
            return f'{new_line}⸎', ''
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
            return '', ''
        elif rend == 'supraline-underline':
            return '<u>', '</u>'
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
        reason = str(attrs['reason'])
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
            return ''
        try:
            unit = attrs['unit']
        except KeyError:
            return self.essential_attribute_missing(node, 'unit')
        for child in node.children:
            if isinstance(child, Tag):
                if child.name == 'desc' and child.get_text() == 'vestiges':
                    gap_start = 'vestig'
                    node.clear()
        if unit == 'character':
            unit = ''
        else:
            unit = 'lines'
        if 'precision' in attrs:
            precision_low = 'ca '
        else:
            precision_low = ''
        if 'atLeast' in attrs:
            at_least = attrs['atLeast']
            try:
                at_most = attrs['atMost']
            except KeyError:
                return self.essential_attribute_missing(node, 'atMost')
            return f'{gap_start} {at_least}-{at_most} {unit}{gap_end}', ''
        elif 'extent' in attrs:
            return f'{gap_start}.?{unit}{gap_end}', ''
        elif 'quantity' in attrs:
            try:
                quantity = str(attrs['quantity'])
            except KeyError:
                return self.essential_attribute_missing(node, 'quantity')
            if precision_low:
                return f'{gap_start}{precision_low}{quantity}{unit}{gap_end}', ''
            else:
                if not unit:
                    underdots = ['\ue5ce' for _ in range(int(quantity))]
                    quantity = ''.join(underdots)
                return f'{gap_start}{precision_low}{quantity}{unit}{gap_end}', ''
        else:
            return '[', ']'

    @staticmethod
    def certainty(node: Tag):
        return '?', ''

    def supplied(self, node: Tag):
        attrs = node.attrs
        reason = str(attrs['reason'])
        if 'cert' in attrs:
            cert_low = '?'
        else:
            cert_low = ''
        if reason == 'omitted':
            return html.escape('<'), html.escape(f'{cert_low}>')
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
        if rend == 'corrected':
            if node.parent.name == 'subst':
                return '', ''
            else:
                return '<s>', '</s>'
        else:
            return '<s>', '</s>'

    @staticmethod
    def expan(node: Tag):
        return '', ''

    @staticmethod
    def ex(node: Tag):
        if 'cert' in node.attrs:
            cert_low = '?'
        else:
            cert_low = ''
        return '(', f'{cert_low})'

    @staticmethod
    def abbr(node: Tag):
        if 'certainty' in node.attrs:
            certainty = '?'
        else:
            certainty = ''
        return '(|', f'{certainty}|)'

    @staticmethod
    def note(node: Tag):
        return '/*', '*/'

    @staticmethod
    def q(node: Tag):
        return '"', '"'

    @staticmethod
    def choice(node: Tag):
        global apparatus_id
        apparatus_id += 1
        return '', ''

    @staticmethod
    def reg(node: Tag):
        attrs = node.attrs
        if 'cert' in attrs:
            cert_low = '?'
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
        return '', ''

    @staticmethod
    def app(node: Tag):
        global apparatus_id
        apparatus_id += 1
        return '', ''

    @staticmethod
    def lem(node: Tag):
        global resp
        resp = ''
        if 'resp' in node.attrs:
            resp = str(node.attrs['resp'])
        return '', ''

    @staticmethod
    def rdg(node: Tag):
        global resp
        resp = ''
        if 'resp' in node.attrs:
            resp = str(node.attrs['resp'])
        return '', ''

    @staticmethod
    def subst(node: Tag):
        global apparatus_id
        apparatus_id += 1
        return '', ''

    @staticmethod
    def corr(node: Tag):
        if 'cert' in node.attrs:
            cert_low = '?'
        else:
            cert_low = ''
        return '', f'{cert_low}'

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
            value = str(node.attrs['value'])
        else:
            value = ''
        return f'<span title="{value}">{rend}', '</span>'

    @staticmethod
    def g(node: Tag):
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
        return '(', ') '

    @staticmethod
    def foreign(node: Tag):
        lang = node.attrs['xml:lang']
        return f'<span title="{lang}">', f'</span> '

if __name__ == '__main__':
    tr = EpiDoc2HTML()
    html_out = (tr.transform('C:/Users/arnon/Desktop/test.xml'))
    print(html_out)
    with open('C:/Users/arnon/Desktop/test.html', 'w', encoding='utf-8') as f:
        f.write(html_out)
