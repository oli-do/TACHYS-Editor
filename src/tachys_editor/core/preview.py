import html
import webbrowser
import unicodedata
import re
from transformer import EpiDocTransformer, EssentialAttributeMissingException
from bs4 import BeautifulSoup
from bs4 import Tag, NavigableString

class EpiDoc2HTML(EpiDocTransformer):
    line_name: str = ''
    apparatus_dict: dict[str, list[dict[str, str]]] = {}
    g_type_map: dict = {
        'coronis' : '⸎',
        "asteriskos": "※",
        "antisigma": "ͻ",
        "antisigma-periestigmene": "ͽ",
        "diple": "›",
        "diple-periestigmene": "⸖",
        "obelos": "―",
        "downwards-ancora": "⸔",
        "upwards-ancora": "⸕",
        "dotted-obelos": "⸓",
        "reverse-dotted-obelos": "(PN does not yet support this character)",
        "chi-periestigmenon": "Χ·",
        "diple-obelismene": "⤚",
        "stauros": "†",
        "rho-cross": "⳨",
        "chirho": "☧",
        "dash": "—",
        "filler": {
            "extension": "—",
            "diple": "›"
        },
        "slanting-stroke": "/",
        "backslash": "\\",
        "double-slanting-stroke": "⸗",
        "double-vertical-bar": "‖",
        "long-vertical-bar": "|",
        "swungdash": "~",
        "dot": "•",
        "check": "／",
        "filled-circle": "⦿",
        "apostrophe": "’",
        "diastole": "’",
        "hypodiastole": "⸒",
        "high-punctus": "˙",
        "middot": "·",
        "low-punctus": ".",
        "dipunct": "∶",
        "tripunct": "⋮",
        "tetrapunct": "⁞",
        "parens-punctuation-opening": "(",
        "parens-punctuation-closing": ")",
        "parens-upper-opening": "⎛",
        "parens-middle-opening": "⎜",
        "parens-lower-opening": "⎝",
        "parens-upper-closing": "⎞",
        "parens-middle-closing": "⎟",
        "parens-lower-closing": "⎠",
        "upper-brace-opening": "⎧",
        "center-brace-opening": "⎨",
        "lower-brace-opening": "⎩",
        "x": "☓",
        "xs": "☓☓☓☓☓"
    }

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
                    title = '<h2 style="text-align:center;">TITLE</h2>'
                    commentary = '<p>This text has been created with TACHYS Editor.</p>\n'
                    html_output = (
                                      '<!DOCTYPE html><html style="margin:0; padding:0; height:100%; width:100%; ">'
                                      '<body style="margin:0; padding:0; height:100%; width:100%; display:grid; place-items:center; background:#f0f0f0;">'
                                      '<div style="'
                                      'font-family:IFAO-Grec Unicode; '
                                      'font-size:11px; '
                                      'width:21cm; '
                                      'border:2px solid black; '
                                      'transform: scale(min(100vw / 21cm, 100vh / 29.7cm)); '
                                      'transform-origin: center; '
                                      'background: white; '
                                      'padding: 2.54cm; '
                                      'box-sizing: border-box; '
                                      '">') + title + commentary + self.text + '</div></body></html>'
                    return html_output
                else:
                    return ''
            else:
                self.errors.append(f'There is no <div> with @type="edition" in file "{path}".')
                return ''
        else:
            return ''

    def add_to_apparatus(self, text: str, origin: Tag | str):
        if isinstance(origin, Tag):
            origin = self.transform_node(origin)
        origin = self.remove_diacritics_punctuation(origin)
        if self.line_name in self.apparatus_dict:
            self.apparatus_dict[self.line_name].append({origin: text})
        else:
            self.apparatus_dict[self.line_name] = [{origin: text}]

    def get_word_context(self, node: Tag) -> dict[str, str]:
        prefix = ""
        curr = node.previous_sibling
        while curr:
            text = self.transform_node(curr) if isinstance(curr, Tag) else str(curr)
            prefix = text + prefix
            if ' ' in text and isinstance(curr, NavigableString):
                break
            curr = curr.previous_sibling
        inside = node.get_text()
        suffix = ""
        curr = node.next_sibling
        while curr:
            text = self.transform_node(curr) if isinstance(curr, Tag) else str(curr)
            suffix += text
            if ' ' in text and isinstance(curr, NavigableString):
                break
            curr = curr.next_sibling

        suffix = re.sub(r'<.*?>', '', suffix)
        prefix = re.sub(r'<.*?>', '', prefix)
        if prefix.endswith((' ', ' |')):
            prefix = ''
        if suffix.startswith((' ', '| ')):
            suffix = ''
        prefix = re.sub('.*\n\n', '', prefix)
        suffix = re.sub('\n\n.*', '', suffix)
        prefix = prefix.replace('\n', '').replace('-', '|')
        suffix = suffix.replace('\n', '').replace('-', '|')
        prefix = prefix.split(' ')[-1]
        suffix = suffix.split(' ')[0]

        return {
            "line": self.line_name,
            "prefix": prefix,
            "inside": inside,
            "suffix": suffix,
            "full_word": f"{prefix}{inside}{suffix}",
        }

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
            result = f'{start}{self.convert(node)}{end}'
            return result
        else:
            return f'{start}{end}'

    def convert(self, node: Tag, ignore_app: bool = True) -> str:
        name = node.name
        if ignore_app:
            if name in ['corr', 'reg', 'rdg']:
                return ''
        result = []
        for content in node.contents:
            if isinstance(content, Tag):
                result.append(self.transform_node(content))
            elif isinstance(content, NavigableString):
                result.append(str(content))
        output = ''.join(result)
        if name == 'hi':
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
            results = []
            last_origin = 'last_origin'
            index = 0
            for val in values:
                origin, text = list(val.items())[0]
                if origin == last_origin:
                    results.append(':')
                    results.append(text)
                else:
                    if index > 0:
                        results.append('|')
                    else:
                        results.append(key)
                    results.append(text)
                index += 1
                last_origin = origin
            lines.append(' '.join(results))
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
                self.add_to_apparatus('in eisthesis', '')
                return f'{lb_break}{close_tr}{new_line}<tr><td>{lb_n}</td><td style="padding-left: 30px;">', ''
            elif rend == 'outdent':
                self.add_to_apparatus('in ekthesis', '')
            elif rend == 'inverse':
                self.add_to_apparatus('inversum', '')
            elif rend == 'perpendicular':
                self.add_to_apparatus('perpendicular in margin', '')
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

    @staticmethod
    def remove_diacritics_punctuation(text: str):
        normalized = unicodedata.normalize('NFD', text)
        clean_text = "".join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')
        clean_text = re.sub(r'[^\w\s]', '', clean_text)
        return unicodedata.normalize('NFC', clean_text)

    def hi_diacritical(self, node: Tag, rend: str):
        context = self.get_word_context(node)
        prefix = self.remove_diacritics_punctuation(context['prefix'])
        suffix = self.remove_diacritics_punctuation(context['suffix'])
        origin = context['full_word']
        parent = node.parent.name
        text = self.remove_diacritics_punctuation(node.text)
        hi_children = [hi.attrs['rend'] for hi in node.children if isinstance(hi, Tag) and hi.name == 'hi']
        map_diacriticals = {'acute': '´', 'grave': '`'}
        try:
            additional_diacritics = ''.join([map_diacriticals[str(child)] for child in hi_children])
        except KeyError:
            return '', ''
        if rend == 'diaeresis':
            if not parent == 'hi':
                self.add_to_apparatus(f'{prefix}{text}\u0308{suffix} Pap.', origin)
                return '', ''
            else:
                return '', ''
        elif rend == 'asper':
            if not parent == 'hi':
                if hi_children:
                    self.add_to_apparatus(f'{prefix}{text}\u1F01{additional_diacritics}{suffix} Pap.', origin)
                    return '', ''
                else:
                    self.add_to_apparatus(f'{prefix}{text}\u1F01{suffix} Pap.', origin)
                    return '', ''
            else:
                return '', ''
        elif rend == 'acute':
            if not parent == 'hi':
                self.add_to_apparatus(f'{prefix}{text}\u0301{suffix} Pap.', origin)
                return '', ''
            else:
                return '', ''
        elif rend == 'grave':
            if not parent == 'hi':
                self.add_to_apparatus(f'{prefix}{text}\u1f70{suffix} Pap.', origin)
                return '', ''
            else:
                return '', ''
        elif rend == 'circumflex':
            self.add_to_apparatus(f'{prefix}{text}\u0342{suffix} Pap.', origin)
            return '', ''
        elif rend == 'lenis':
            if not parent == 'hi':
                if hi_children:
                    self.add_to_apparatus(f'{prefix}{text}\u0313{additional_diacritics}{suffix} Pap.', origin)
                    return '', ''
                else:
                    self.add_to_apparatus(f'{prefix}{text}\u0313{suffix} Pap.', origin)
                    return '', ''
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
                return '〚', '〛'
        else:
            return '〚', '〛'

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

    def choice(self, node: Tag):
        self.add_to_apparatus(self.create_apparatus_text(node), str(node))
        return '', ''

    @staticmethod
    def reg(node: Tag):
        return '', ''

    @staticmethod
    def orig(node: Tag):
        return '', ''

    def app(self, node: Tag):
        self.add_to_apparatus(self.create_apparatus_text(node), str(node))
        return '', ''

    @staticmethod
    def lem(node: Tag):
        return '', ''

    @staticmethod
    def rdg(node: Tag):
        return '', ''

    def create_apparatus_text(self, node: Tag, results=None):
        if results is None:
            results = []
        print('create_apparatus_text', node, results)
        name = node.name
        attrs = node.attrs
        tags = [content for content in node.contents if isinstance(content, Tag)]
        navigable_strings = [content for content in node.contents if isinstance(content, NavigableString)]
        parent = node.parent
        parent_attrs = parent.attrs if isinstance(parent, Tag) else {}
        app_type = parent_attrs['type'] if 'type' in parent_attrs else ''
        resp = str(attrs['resp']).strip().replace(',', '') if 'resp' in node.attrs else ''
        place = attrs['place'] if 'place' in attrs else ''
        separator = ' : '
        if name == 'add' and place == 'inline':
            if navigable_strings:
                results.append(f'{self.convert(node, False)} corr. ex')
            else:
                for tag in tags:
                    self.create_apparatus_text(tag, results)
                results.append('corr. ex')
        elif name == 'del':
            if navigable_strings:
                results.append(self.convert(node, False))
            else:
                for tag in tags:
                    self.create_apparatus_text(tag, results)
        elif name == 'lem':
            if app_type == 'alternative':
                if navigable_strings:
                    results.append(self.convert(node, False))
                else:
                    for tag in tags:
                        self.create_apparatus_text(tag, results)
            elif app_type == 'editorial':
                if resp:
                    if navigable_strings:
                        results.append(f'{self.convert(node, False)} {resp}')
                    else:
                        for tag in tags:
                            self.create_apparatus_text(tag, results)
                        results.append(resp)
        elif name == 'rdg':
            if app_type == 'alternative':
                if navigable_strings:
                    results.append(f'vel{' ' + self.convert(node, False) if navigable_strings else ''}')
                else:
                    results.append('vel')
                    for tag in tags:
                        self.create_apparatus_text(tag, results)
            elif app_type == 'editorial':
                if results:
                    results.append(separator)
                if navigable_strings:
                    results.append(f'{self.convert(node, False)} {resp}')
                else:
                    for tag in tags:
                        self.create_apparatus_text(tag, results)
                    results.append(resp)
        elif name == 'reg' or name == 'corr':
            if navigable_strings:
                results.append(f'l.{' ' + self.convert(node, False)}')
            else:
                for tag in tags:
                    self.create_apparatus_text(tag, results)
                results.insert(0, 'l.')
        elif name in ['orig', 'sic']:
            return ''
        elif name in ['app', 'choice', 'subst']:
            for tag in tags:
                self.create_apparatus_text(tag, results)
        else:
            results.append(self.convert(node, False))
        results = list(filter(None, results))
        return ' '.join(results)

    def subst(self, node: Tag):
        self.add_to_apparatus(self.create_apparatus_text(node), str(node))
        return '', ''

    @staticmethod
    def corr(node: Tag):
        return '', ''

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

    def g(self, node: Tag):
        context = self.get_word_context(node)
        prefix = context['prefix']
        prefix = self.remove_diacritics_punctuation(prefix)
        suffix = context['suffix']
        suffix = self.remove_diacritics_punctuation(suffix)
        g_type = str(node.attrs['type'])
        description = g_type.replace('-', ' ')
        if g_type in self.g_type_map:
            app_symbol = self.g_type_map[g_type]
            text_symbol = app_symbol
        else:
            app_symbol = f'*'
            text_symbol = '*'
        if g_type in ['apostrophe', 'chi-periestigmenon', 'high-punctus', 'middot', 'low-punctus']:
            text_symbol = ''
            description = 'punxit'
        parent = node.parent.name
        if parent == 'unclear':
            unclear = '?'
        else:
            unclear = ''
        if 'rend' in node.attrs:
            rend = node.attrs['rend']
            if isinstance(app_symbol, dict):
                if rend in app_symbol:
                    app_symbol = app_symbol[rend]
                    text_symbol = app_symbol
        if description == 'punxit':
            self.add_to_apparatus(f'{prefix}{app_symbol}{suffix} Pap.', '')
        else:
            self.add_to_apparatus(f'{description} post {prefix} Pap.', '')
        return f'{text_symbol}{unclear}', ''

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
    # print(tr.create_apparatus_entry(BeautifulSoup(open('C:/Users/arnon/Desktop/new 1.xml', 'r', encoding='utf-8'), 'lxml-xml')))
    html_out = tr.transform('C:/Users/arnon/Desktop/test.xml')
    file_path = 'C:/Users/arnon/Desktop/test.html'
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_out)
    webbrowser.open(file_path)
