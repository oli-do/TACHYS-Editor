import html
import unicodedata
import difflib
from pathlib import Path

import re
from tachys_editor.core.transformers.xml_transformer import EpiDocTransformer
from tachys_editor.shared.transformer_helper import EssentialAttributeMissingException
from tachys_editor.core.transformers.preview_helper import (g_type_map, expan_map, ex_start_map, ex_match_map,
                            draw_lost_lines_extent_unknown, draw_gaps, combine_div_name, draw_hyphens,
                            create_html_output, map_resp_nodes, remove_diacritics_punctuation)
from tachys_editor.shared.transformer_helper import validate_epidoc_tei
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString

class EpiDoc2HTML(EpiDocTransformer):

    def __init__(self):
        super().__init__()
        self.line_name: str = ''
        self.apparatus_dict: dict[str, list[dict[str, str]]] = {}
        self.ex_start_map = dict(sorted(ex_start_map.items(), key=lambda x: len(x[0]), reverse=True))
        self.resp_map: dict = {}
        self.is_searching_word_context = False
        self.previous_lb_num = -1

    def reset(self):
        self.text = ''
        self.errors = []
        self.line_name: str = ''
        self.apparatus_dict = {}
        self.resp_map: dict = {}
        self.is_searching_word_context = False
        self.previous_lb_num = -1

    def transform(self, xml: Path | str):
        self.reset()
        success, info = validate_epidoc_tei(xml)
        if success:
            if isinstance(xml, Path):
                soup = BeautifulSoup(open(xml, 'r', encoding='utf-8'), 'lxml-xml')
            else:
                soup = BeautifulSoup(xml, 'lxml-xml')
            main_div = soup.find('div', attrs={'type': 'edition'})
            if main_div:
                has_lines = main_div.find_all('lb')
                if has_lines:
                    self.resp_map = map_resp_nodes(main_div)
                    try:
                        self.text += self.transform_node(main_div)
                    except EssentialAttributeMissingException:
                        return ''
                    apparatus = self.generate_apparatus() if self.apparatus_dict else ''
                    lines = [str(line) for line in self.text.splitlines() if line is not None and str(line).strip()]
                    lines = draw_lost_lines_extent_unknown(lines)
                    lines = draw_gaps(lines)
                    lines = draw_hyphens(lines, has_lines)
                    self.text = '\n'.join(lines) + apparatus
                    html_output = create_html_output(self.text, self.resp_map)
                    return html_output
                else:
                    return ''
            else:
                self.errors.append(f'There is no <div> with @type="edition" in "{xml}".')
                return ''
        else:
            self.errors = info
            return ''

    def add_to_apparatus(self, text: str, origin: Tag | str):
        if isinstance(origin, Tag):
            origin = self.transform_node(origin)
        origin = remove_diacritics_punctuation(origin)
        if self.line_name in self.apparatus_dict:
            self.apparatus_dict[self.line_name].append({origin: text})
        else:
            self.apparatus_dict[self.line_name] = [{origin: text}]

    def get_word_context(self, node: Tag) -> dict[str, str]:
        if not self.is_searching_word_context:
            self.is_searching_word_context = True
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
            prefix = re.sub(r'[0-9]+', '', prefix)
            suffix = re.sub(r'[0-9]+', '', suffix)
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
            self.is_searching_word_context = False
        else:
            prefix = ''
            inside = ''
            suffix = ''

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
        parent_name = node.parent.name if isinstance(node.parent, Tag) else ''
        if ignore_app:
            if name in ['corr', 'reg', 'rdg'] or (name == 'del' and parent_name == 'subst'):
                return ''
        result = []
        for content in node.contents:
            if isinstance(content, Tag):
                result.append(self.transform_node(content))
            elif isinstance(content, NavigableString):
                result.append(str(content))
        output = ''.join(result)
        if parent_name == 'hi':
            rend = node.parent.attrs['rend']
            if rend == 'supraline' or rend == 'supraline-underline':
                supraline_text = ''
                for text in result:
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
            last_text = ''
            index = 0
            for val in values:
                origin, text = list(val.items())[0]
                if origin == last_origin:
                    if last_text.endswith('Pap.') and text.endswith('Pap.'):
                        last_text = unicodedata.normalize('NFD', last_text)
                        text = unicodedata.normalize('NFD', text)
                        sm = difflib.SequenceMatcher(None, last_text, text)
                        merged = []
                        for tag, i1, i2, j1, j2 in sm.get_opcodes():
                            if tag == "equal":
                                merged.append(last_text[i1:i2])
                            elif tag in ("replace", "insert", "delete"):
                                merged.append(last_text[i1:i2] + text[j1:j2])
                        results[-1] = unicodedata.normalize("NFC", "".join(merged))
                    else:
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
                last_text = text
            lines.append(' '.join(results))
        return '<p style="font-size:9px;">' + ' ‖ '.join(lines) + '</p>\n'


    def div(self, node: Tag):
        attrs = node.attrs
        div_type = str(attrs['type'])
        has_div_children = bool([child for child in node.children if isinstance(child, Tag) and child.name == 'div'])
        if has_div_children:
            return '', ''
        else:
            name = combine_div_name(node)
            style_opening = '<br/><hr/><br/><h3>'
            style_closing = '</h3>'
        if div_type == 'textpart':
            apparatus = ''
            if self.apparatus_dict:
                apparatus = self.generate_apparatus()
            self.apparatus_dict = {}
            return f'{apparatus}{style_opening}{name}{style_closing}', ''
        elif div_type == 'edition':
            return '', ''
        else:
            self.unsupported_attribute_value(node, 'type', div_type)
            return '', ''

    @staticmethod
    def ab(node: Tag):
        return '<table>', '</table>'

    def lb(self, node: Tag):
        attrs = node.attrs
        try:
            lb_n = str(attrs['n'])
            self.line_name = lb_n
        except KeyError:
            return self.essential_attribute_missing(node, 'n')
        try:
            keep_lb = False
            lb_num = int(lb_n)
            if self.previous_lb_num == -1 or lb_num == self.previous_lb_num:
                self.previous_lb_num = lb_num - 1
            if not abs(lb_num - self.previous_lb_num) == 1:
                keep_lb = True
            if not lb_num % 5 == 0 and not keep_lb:
                lb_n = ''
            sibling = node.next_sibling
            if isinstance(sibling, Tag):
                if sibling.name == 'gap':
                    if 'extent' in sibling.attrs:
                        if sibling.attrs['unit'] == 'line':
                            lb_n = ''
            self.previous_lb_num = lb_num
        except ValueError:
            pass
        parent = node.parent.name
        if parent in ['reg', 'orig', 'lem']:
            new_line = ''
        else:
            new_line = '\n'
        if parent in ['del', 'rdg', 'corr', 'reg']:
            return '|', ''
        close_tr = '</tr>'
        if parent == 'ab':
            close_tr = ''
        if not 'rend' in attrs:
            return f'{close_tr}{new_line}<tr><td class="lb" style="padding-right: 30px;">{lb_n}</td><td>', ''
        else:
            rend = attrs['rend']
            if rend == 'indent':
                self.add_to_apparatus('in eisthesis', '')
                return f'{close_tr}{new_line}<tr><td class="lb">{lb_n}</td><td style="padding-left: 30px;">', ''
            elif rend == 'outdent':
                self.add_to_apparatus('in ekthesis', '')
            elif rend == 'inverse':
                self.add_to_apparatus('inversum', '')
            elif rend == 'perpendicular':
                self.add_to_apparatus('perpendicular in margin', '')
            return f'{close_tr}{new_line}<tr><td class="lb">{lb_n}</td><td>', ''

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
        return f'<i>{new.title()}{cert_low}</i> ', ''

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
            unit = ' lines'
        if 'precision' in attrs:
            precision_low = ' c.'
        else:
            precision_low = ''
        if 'atLeast' in node.attrs:
            at_least = str(attrs['atLeast'])
            try:
                at_most = str(attrs['atMost'])
            except KeyError:
                return self.essential_attribute_missing(node, 'atMost')
            description = f'vac. {at_least}-{at_most}{unit}'
            try:
                quantity = round((int(at_least) + int(at_most)) / 2)
                in_text = ''
                in_text += '&nbsp;' * int(quantity)
                self.add_to_apparatus(description, str(node))
                return in_text, ''
            except ValueError:
                return f'<i>{description}</i>', ''
        elif 'extent' in attrs:
            return f'<i> vacat </i>', ''
        else:
            try:
                quantity = str(attrs['quantity'])
            except KeyError:
                return self.essential_attribute_missing(node, 'quantity')
            description = f'vac.{precision_low}{quantity}{unit}'
            self.add_to_apparatus(description, str(node))
            if not unit:
                in_text = ''
                in_text += '&nbsp;' * int(quantity)
                return f'{in_text}', ''
            else:
                return f'<i>{description}</i>', ''

    def add(self, node: Tag):
        attrs = node.attrs
        text = self.convert(node)
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
            return '/', f'{cert_low}\\'
        elif place == 'left':
            self.add_to_apparatus(f'in marg. sin. {text}{cert_low}', str(node))
            return '', ''
        elif place == 'right':
            self.add_to_apparatus(f'in marg. dext. {text}{cert_low}', str(node))
            return '', ''
        elif place == 'interlinear':
            self.add_to_apparatus(f'supra l. {text}{cert_low}', str(node))
            return '', ''
        elif place == 'margin':
            try:
                rend = str(attrs['rend'])
            except KeyError:
                return self.essential_attribute_missing(node, 'rend')
            if rend == 'sling':
                return '', ''
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

    def hi_diacritical(self, node: Tag, rend: str):
        context = self.get_word_context(node)
        prefix = remove_diacritics_punctuation(context['prefix'])
        suffix = remove_diacritics_punctuation(context['suffix'])
        origin = context['full_word']
        parent = node.parent.name
        text = remove_diacritics_punctuation(node.text)
        hi_children = [hi.attrs['rend'] for hi in node.children if isinstance(hi, Tag) and hi.name == 'hi']
        map_diacriticals = {'acute': '´', 'grave': '`'}
        try:
            additional_diacritics = ''.join([map_diacriticals[str(child)] for child in hi_children])
        except KeyError:
            return '', ''
        if rend == 'diaeresis':
            if not parent == 'hi':
                if not self.is_searching_word_context:
                    self.add_to_apparatus(f'{prefix}{text}\u0308{suffix} Pap.', origin)
                return '', ''
            else:
                return '', ''
        elif rend == 'asper':
            if not parent == 'hi':
                if hi_children:
                    if not self.is_searching_word_context:
                        self.add_to_apparatus(f'{prefix}{text}\u1F01{additional_diacritics}{suffix} Pap.', origin)
                    return '', ''
                else:
                    if not self.is_searching_word_context:
                        self.add_to_apparatus(f'{prefix}{text}\u1F01{suffix} Pap.', origin)
                    return '', ''
            else:
                return '', ''
        elif rend == 'acute':
            if not parent == 'hi':
                if not self.is_searching_word_context:
                    self.add_to_apparatus(f'{prefix}{text}\u0301{suffix} Pap.', origin)
                return '', ''
            else:
                return '', ''
        elif rend == 'grave':
            if not parent == 'hi':
                if not self.is_searching_word_context:
                    self.add_to_apparatus(f'{prefix}{text}\u1f70{suffix} Pap.', origin)
                return '', ''
            else:
                return '', ''
        elif rend == 'circumflex':
            if not self.is_searching_word_context:
                self.add_to_apparatus(f'{prefix}{text}\u0342{suffix} Pap.', origin)
            return '', ''
        elif rend == 'lenis':
            if not parent == 'hi':
                if hi_children:
                    if not self.is_searching_word_context:
                        self.add_to_apparatus(f'{prefix}{text}\u0313{additional_diacritics}{suffix} Pap.', origin)
                    return '', ''
                else:
                    if not self.is_searching_word_context:
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
        _, unit, precision_low, quantity = self.extract_gap_attributes(node)
        if not unit:
            unit = 'character'
        unit = ' ' + unit
        desc = node.find_next('desc')
        desc_text = desc.get_text()
        desc.clear(decompose=True)
        try:
            if int(quantity) > 1:
                unit += 's'
        except ValueError:
            unit += 's'
        if 'character' in unit:
            self.add_to_apparatus(f'om. {quantity}{unit} of {desc_text} text', str(node))
            return '', ''
        else:
            return f'<i>(om. {quantity}{unit} of {desc_text} text)</i>', ''

    @staticmethod
    def desc(node: Tag):
        return '', ''

    def extract_gap_attributes(self, node: Tag):
        attrs = node.attrs
        reason = str(attrs['reason'])
        try:
            unit = attrs['unit']
            if unit != 'line':
                unit = ''
        except KeyError:
            return self.essential_attribute_missing(node, 'unit')
        if 'precision' in attrs:
            precision_low = ' c.'
        else:
            precision_low = ''
        if 'atLeast' in attrs:
            at_least = attrs['atLeast']
            try:
                at_most = attrs['atMost']
            except KeyError:
                return self.essential_attribute_missing(node, 'atMost')
            quantity = f'{at_least}-{at_most}'
        elif 'extent' in attrs:
            quantity = '?'
        elif 'quantity' in attrs:
            try:
                quantity = str(attrs['quantity'])
            except KeyError:
                return self.essential_attribute_missing(node, 'quantity')
        else:
            quantity = ''
        return reason, unit, precision_low, quantity

    def gap(self, node: Tag):
        reason, unit, precision_low, quantity = self.extract_gap_attributes(node)
        if reason == 'lost':
            gap_start = '['
            gap_end = ']'
            status = 'missing'
        elif reason == 'illegible':
            gap_start = ''
            gap_end = ''
            status = 'illegible'
        elif reason == 'ellipsis':
            return self.gap_ellipsis(node)
        else:
            self.unsupported_attribute_value(node, 'reason', reason)
            return '', ''
        if quantity:
            if '-' in quantity:
                if unit:
                    return f'<i>({quantity} lines {status})</i>', ''
                else:
                    if reason == 'lost':
                        return f'{gap_start} {quantity} {unit}{gap_end}', ''
                    else:
                        q_split = quantity.split('-')
                        at_least = int(q_split[0])
                        at_most = int(q_split[1])
                        underdots = '\ue5ce' * at_most
                        underdots = underdots[:at_least] + '(' + underdots[at_least:] + ')'
                        return f'{underdots}', ''
            elif quantity == '?':
                if unit:
                    return 'lost.?lin', ''
                else:
                   return f'{gap_start} ? {gap_end}', ''
            else:
                if not unit:
                    if precision_low:
                        return f'{gap_start}{precision_low}{quantity} {gap_end}', ''
                    else:
                        underdots = ''
                        underdots += '\ue5ce' * int(quantity)
                        return f'{gap_start}{underdots}{gap_end}', ''
                else:
                    if int(quantity) > 1:
                        unit += 's'
                    if precision_low:
                        return f'<i>({precision_low} {quantity} {unit} {status})</i>', ''
                    else:
                        return f'<i>({quantity} {unit} {status})</i>', ''
        else:
            return '[', ']'

    @staticmethod
    def certainty(node: Tag):
        return '?', ''

    def supplied(self, node: Tag):
        attrs = node.attrs
        reason = str(attrs['reason'])
        if 'cert' in attrs:
            cert_low = '(?)'
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

    def expan(self, node: Tag):
        text = ''
        for content in node.contents:
            if isinstance(content, NavigableString):
                text += content
            elif isinstance(content, Tag) and not content.name in ['expan', 'ex']:
                text += self.convert(content)
        if text:
            text = remove_diacritics_punctuation(text)
            if text in expan_map:
                self.add_to_apparatus(f'{expan_map[text]} Pap.', str(node))
                node.clear()
        return '', ''

    def ex(self, node: Tag):
        if 'cert' in node.attrs:
            cert_low = '?'
        else:
            cert_low = ''
        text = ''
        for content in node.contents:
            if isinstance(content, NavigableString):
                text += content
        if text:
            text = remove_diacritics_punctuation(text)
            parent = node.find_parent('expan')
            parent_has_navigable_strings = bool([content for content in parent.contents if isinstance(content, NavigableString)])
            if not parent_has_navigable_strings:
                for key, value in self.ex_start_map.items():
                    if text.startswith(key):
                        self.add_to_apparatus(f'{value} Pap.', str(node))
            else:
                if text in ex_match_map:
                    context = self.get_word_context(node)
                    prefix = context["prefix"]
                    suffix = context["suffix"]
                    print(prefix, suffix)
                    if not self.is_searching_word_context:
                        self.add_to_apparatus(f'{prefix}{ex_match_map[text]}{suffix} Pap.', str(node))
        node.clear()
        return '(', f'{text}{cert_low})'

    @staticmethod
    def abbr(node: Tag):
        return '', f'( )'

    @staticmethod
    def note(node: Tag):
        return '<i>(', ')</i> '

    @staticmethod
    def q(node: Tag):
        return '"', '"'

    def choice(self, node: Tag):
        parent_app = [parent for parent in node.parents if isinstance(parent, Tag) and parent.name in ['app', 'subst']]
        if not parent_app:
            self.add_to_apparatus(self.create_apparatus_text(node), str(node))
        return '', ''

    @staticmethod
    def reg(node: Tag):
        return '', ''

    @staticmethod
    def orig(node: Tag):
        return '', ''

    def app(self, node: Tag):
        parent_app = [parent for parent in node.parents if isinstance(parent, Tag) and parent.name in ['subst', 'choice']]
        if not parent_app:
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
        name = node.name
        attrs = node.attrs
        tags = [content for content in node.contents if isinstance(content, Tag)]
        navigable_strings = [content for content in node.contents if isinstance(content, NavigableString)]
        parent = node.parent
        parent_attrs = parent.attrs if isinstance(parent, Tag) else {}
        app_type = parent_attrs['type'] if 'type' in parent_attrs else ''
        resp = str(attrs['resp']).strip() if 'resp' in node.attrs else ''
        resp_abbr = ''
        if resp:
            resps = []
            for current_resp in resp.split(','):
                current_resp = current_resp.strip()
                resps.append(self.resp_map[current_resp])
            resp_abbr = ' '.join(resps)
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
                if resp_abbr:
                    if navigable_strings:
                        results.append(f'{self.convert(node, False)} {resp_abbr}')
                    else:
                        for tag in tags:
                            self.create_apparatus_text(tag, results)
                        results.append(resp_abbr)
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
                    results.append(f'{self.convert(node, False)} {resp_abbr}')
                else:
                    for tag in tags:
                        self.create_apparatus_text(tag, results)
                    results.append(resp_abbr)
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
        parent_app = [parent for parent in node.parents if isinstance(parent, Tag) and parent.name in ['app', 'choice']]
        if not parent_app:
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
            rend = "'"
        else:
            rend = ""
        if 'value' in node.attrs:
            value = str(node.attrs['value'])
        else:
            value = ''
        return f'<span title="{value}">', f'{rend}</span>'

    def g(self, node: Tag):
        context = self.get_word_context(node)
        origin = context['full_word']
        prefix = context['prefix']
        prefix = remove_diacritics_punctuation(prefix)
        suffix = context['suffix']
        suffix = remove_diacritics_punctuation(suffix)
        g_type = str(node.attrs['type'])
        description = g_type.replace('-', ' ')
        if g_type in g_type_map:
            app_symbol = g_type_map[g_type]
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
            if not self.is_searching_word_context:
                self.add_to_apparatus(f'{prefix}{app_symbol}{suffix} Pap.', origin)
        else:
            if prefix:
                if not self.is_searching_word_context:
                    self.add_to_apparatus(f'{description} post {prefix} Pap.', origin)
            else:
                if not self.is_searching_word_context:
                    self.add_to_apparatus(f'{description} Pap.', origin)
        return f'{text_symbol}{unclear}', ''

    @staticmethod
    def figure(node: Tag):
        return '', ''

    @staticmethod
    def figDesc(node: Tag):
        return '<i>(', ')</i> '

    @staticmethod
    def foreign(node: Tag):
        lang = node.attrs['xml:lang']
        return f'<span title="{lang}">', f'</span> '