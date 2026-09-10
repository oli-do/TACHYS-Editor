from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from lark import Transformer, v_args
from lxml import etree
from importlib.resources import files


schema_path = str(files('tachys_editor.resources').joinpath('tei-epidoc.rng'))
schema = etree.parse(schema_path)
rng = etree.RelaxNG(schema)
ns = {'tei': 'http://www.tei-c.org/ns/1.0'}


def inner_xml(start: str, children: list[str], end: str):
    children = list(filter(None, children))
    xml = start + ''.join(children) + end
    return xml

def lem_rdg(children, tag: str):
    items = ''.join(children[0])
    certainty = children[1]
    resp = children[2]
    if not certainty:
        certainty = ''
    if resp:
        resp = f' resp="{resp}"'
    else:
        resp = ''
    return f'<{tag}{resp}>{items}{certainty}</{tag}>'


class TEIBuilder:
    default_tei_header = """<teiHeader>
        <fileDesc>
            <titleStmt>
                <title></title>
            </titleStmt>
            <publicationStmt>
                <authority>TACHYS Editor</authority>
            </publicationStmt>
            <sourceDesc>
                <msDesc>
                    <msIdentifier>
                    </msIdentifier>
                </msDesc>
            </sourceDesc>
        </fileDesc>
    </teiHeader>"""

    intro = """<?xml version="1.0" encoding="UTF-8"?>
<?xml-model href="https://epidoc.stoa.org/schema/8.23/tei-epidoc.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>"""

    commentary = """<div type="commentary" subtype="frontmatter" xml:space="preserve">
                        <p>
                            This text has been digitally edited with TACHYS Editor.
                        </p>
</div>"""

    def build_placeholder(self, inner_body: str):
        body = inner_xml('<body>', [inner_body], '</body>')
        text = inner_xml('<text>', [body], '</text>')
        tei = inner_xml(f'{self.intro}\n<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="en">', [self.commentary, self.default_tei_header, text], '</TEI>')
        return tei

    def build_from_origin(self, inner_body: str, xml_origin: str):
        soup = BeautifulSoup(open(xml_origin, 'r', encoding='utf-8'), 'lxml-xml')
        body = soup.find('body')
        new_body = inner_xml('<body>', [inner_body], '</body>')
        if body:
            body.replace_with(BeautifulSoup(new_body, 'lxml-xml'))
            return str(soup)
        else:
            return self.build_placeholder(inner_body)


class LeidenPlusTransformer(Transformer):
    tei_builder = TEIBuilder()
    errors = []

    # DOCUMENT START
    @v_args(inline=True)
    def default_language(self, lang):
        return f'<div xml:lang="{lang}" type="edition" xml:space="preserve">'

    def file_start(self, children):
        return ''.join(children) + '\n</div>'

    def div(self, children):
        children = list(filter(None, children))
        div_text = ''.join(children)
        div_text = div_text.replace('</unclear><unclear>', '')
        return div_text

    def superdiv(self, children):
        children = list(filter(None, children))
        return ''.join(children)

    @v_args(inline=True)
    def div_start(self, n, subtype, corresp):
        if corresp:
            corresp_str = f' corresp="#{corresp}"'
        else:
            corresp_str = ''
        if n == 'r' or n == 'v':
           subtype_str = ''
        else:
           subtype_str = f' subtype="{subtype}"'
        xml = f'\n<div n="{n}"{subtype_str} type="textpart"{corresp_str}>'
        return xml

    def TEXTBLOCK_OPEN(self, _):
        xml = '<ab>'
        return xml

    def TEXTBLOCK_CLOSE(self, _):
        xml = '\n</ab>'
        return xml

    def DIV_CLOSE(self, _):
        xml = '</div>'
        return xml

    def _leiden_line(self, children):
        if isinstance(children[0], list):
            items = children[0]
        else:
            items = children
        items = list(filter(None, items))
        return ''.join(items)

    # ITEMS
    def items(self, children):
        return children

    def app_items(self, children):
        return children

    @v_args(inline=True)
    def TEXT(self, text):
        return text

    def text(self, children):
        return ''.join(children)

    @v_args(inline=True)
    def text_space(self, space):
        return space

    @v_args(inline=True)
    def text_full_stop(self, full_stop):
        return full_stop

    @v_args(inline=True)
    def line(self, number, lb):
        if lb:
            lb_str = f' break="no"'
        else:
            lb_str = ''
        xml = f'\n<lb n="{number}"{lb_str}/>'
        return xml

    @v_args(inline=True)
    def line_double(self, number, number2, lb):
        if lb:
            lb_str = f' break="no"'
        else:
            lb_str = ''
        xml = f'\n<lb n="{number}/{number2}"{lb_str}/>'
        return xml

    @v_args(inline=True)
    def line_break_app(self, number):
        xml = f'<lb n="{number}" break="no"/>'
        return xml

    @v_args(inline=True)
    def line_formatted(self, n, n2, lb, rend):
        if lb:
            lb_str = f' break="no"'
        else:
            lb_str = ''
        xml = f'\n<lb n="{n+n2}"{lb_str} rend="{rend}"/>'
        return xml

    @v_args(inline=True)
    def line_rend(self, n, lb, rend):
        if lb:
            lb_str = f' break="no"'
        else:
            lb_str = ''
        xml = f'\n<lb n="{n}"{lb_str} rend="{rend}"/>'
        return xml

    @v_args(inline=True)
    def line_margin(self, n, n2, lb):
        if lb:
            lb_str = f' break="no"'
        else:
            lb_str = ''
        xml = f'\n<lb n="{n+n2}"{lb_str}/>'
        return xml

    def EXTENT_UNKNOWN(self, _):
        xml = ' extent="unknown"'
        return xml

    def CERT_LOW(self, _):
        xml = ' cert="low"'
        return xml

    def CERTAINTY_MATCH(self, _):
        xml = '<certainty match=".." locus="value"/>'
        return xml

    @v_args(inline=True)
    def range(self, at_least, at_most):
        xml = f' atLeast="{at_least}" atMost="{at_most}"'
        return xml

    @v_args(inline=True)
    def QUANTITY(self, quantity):
        xml = f' quantity="{quantity}"'
        return xml

    @v_args(inline=True)
    def LIN(self, _):
        xml = ' unit="line"'
        return xml

    @v_args(inline=True)
    def CIRCA(self, _):
        xml = f' precision="low"'
        return xml

    def vacat(self, children):
        if not children[2]:
            return inner_xml('<space', children, ' unit="character"/>')
        else:
            return inner_xml('<space', children, '/>')

    def add_above(self, children):
        return inner_xml('<add place="above">', children[0], '</add>')

    def add_below(self, children):
        return inner_xml('<add place="below">', children[0], '</add>')

    def add_left(self, children):
        return inner_xml('<add place="left">', children[0], '</add>')

    def add_right(self, children):
        return inner_xml('<add place="right">', children[0], '</add>')

    def add_interlin(self, children):
        return inner_xml('<add place="interlinear">', children[0], '</add>')

    def add_sling(self, children):
        return inner_xml('<add rend="sling" place="margin">', children[0], '</add>')

    def add_underline(self, children):
        return inner_xml('<add rend="underline" place="margin">', children[0], '</add>')

    def box(self, _):
        return '<milestone rend="box" unit="undefined"/>'

    def tall(self, children):
        return inner_xml('<hi rend="tall">', children[0], '</hi>')

    def superscripted(self, children):
        return inner_xml('<hi rend="superscript">', children[0], '</hi>')

    def subscripted(self, children):
        return inner_xml('<hi rend="subscript">', children[0], '</hi>')

    def supraline(self, children):
        return inner_xml('<hi rend="supraline">', children[0], '</hi>')

    def underline(self, children):
        return inner_xml('<hi rend="underline">', children[0], '</hi>')

    def supraline_underline(self, children):
        return inner_xml('<hi rend="supraline-underline">', children[0], '</hi>')

    def supralinear_stroke(self, children):
        char = children[0]
        underdot = children[1]
        if char.type == 'SUPRA_ALPHA_SMALL':
            char = 'α'
        elif char.type == 'SUPRA_ALPHA_CAPITAL':
            char = 'Α'
        elif char.type == 'SUPRA_IOTA_SMALL':
            char = 'ι'
        elif char.type == 'SUPRA_IOTA_CAPITAL':
            char = 'Ι'
        elif char.type == 'SUPRA_YPSILON_SMALL':
            char = 'υ'
        elif char.type == 'SUPRA_YPSILON_CAPITAL':
            char = 'Υ'
        if underdot:
            char = f'<unclear>{char}</unclear>'
        return f'<hi rend="supraline">{char}</hi>'

    @v_args(inline=True)
    def lines_lost(self, precision, quantity, unit, cert_match):
        return inner_xml('<gap reason="lost"', [precision, quantity, unit], '/>') + str(cert_match)

    def illegible(self, children):
        precision = children[0]
        quantity_extent = children[1]
        unit = children[2]
        if not unit:
            unit = ' unit="character"'
        if precision == '.':
            precision = ''
        return f'<gap reason="illegible"{quantity_extent}{unit}{precision}/>'

    def vestiges(self, children):
        precision = children[0]
        quantity_extent = children[1]
        unit = children[2]
        if not unit:
            unit = ' unit="character"'
        if isinstance(precision, str):
            return f'<gap reason="illegible"{quantity_extent}{unit}{precision}><desc>vestiges</desc></gap>'
        else:
            return f'<gap reason="illegible"{quantity_extent}{unit}><desc>vestiges</desc></gap>'

    def REND_TICK(self, _):
        return f' rend="tick"'

    def ancient_number(self, children):
        rend_tick = children[1]
        value = children[2]
        if value:
            value = f' value="{value}"'
        else:
            value = ''
        if not rend_tick:
            rend_tick = ''
        return inner_xml(f'<num{value}{rend_tick}>', children[0], '</num>')

    @v_args(inline=True)
    def ancient_number_no_text(self, value):
        return f'<num value="{value}"/>'

    def omitted(self, children):
        cert_low = children[1]
        if not cert_low:
            cert_low = ''
        return inner_xml(f'<supplied reason="omitted"{cert_low}>', children[0], '</supplied>')

    def surplus(self, children):
        certainty_match = children[1]
        if not certainty_match:
            certainty_match = ''
        return inner_xml('<surplus>', children[0], f'{certainty_match}</surplus>')

    def SLASHES(self, _):
        return ' rend="slashes"'

    def CROSS_STROKES(self, _):
        return ' rend="cross-strokes"'

    def deletion(self, children):
        rend = children[0]
        if not rend:
            rend = ' rend="erasure"'
        return inner_xml(f'<del{rend}>', children[1], '</del>')

    def deletion_corr(self, children):
        return inner_xml('<del rend="corrected">', children[0], '</del>')

    def abbreviation(self, children):
        certainty_match = children[1]
        if not certainty_match:
            certainty_match = ''
        return inner_xml(f'<abbr>', children[0], f'{certainty_match}</abbr>')

    def OR(self, _):
        return ' or '

    def gap_lost(self, children):
        precision = children[0]
        quantity_extent = children[1]
        or_gap_lost = children[2]
        gap_lost = children[3]
        if not or_gap_lost:
            or_gap_lost = ''
            gap_lost = ''
        if precision == '.':
            precision = ''
        return f'<gap reason="lost"{quantity_extent} unit="character"{precision}/>{or_gap_lost}{gap_lost}'

    def supplied_lost(self, children):
        cert_low = children[1]
        if not cert_low:
            cert_low = ''
        return inner_xml(f'<supplied reason="lost"{cert_low}>', children[0], '</supplied>')

    def parallel(self, children):
        cert_low = children[1]
        if not cert_low:
            cert_low = ''
        return inner_xml(f'<supplied evidence="parallel" reason="undefined"{cert_low}>', children[0], '</supplied>')

    def parallel_lost(self, children):
        cert_low = children[1]
        if not cert_low:
            cert_low = ''
        return inner_xml(f'<supplied evidence="parallel" reason="lost"{cert_low}>', children[0], '</supplied>')

    def unclear(self, children):
        return inner_xml('<unclear>', children, '</unclear>')

    @v_args(inline=True)
    def non_default_language(self, text, lang):
        return f'<foreign xml:lang="{lang}">{text}</foreign>'

    def CHAR(self, _):
        return ' unit="character"'

    def omitted_language(self, children):
        lang = children[0]
        precision = children[1]
        quantity_extent = children[2]
        unit = children[3]
        if not precision:
            precision = ''
        return f'<gap reason="ellipsis"{quantity_extent}{unit}{precision}><desc>{lang}</desc></gap>'

    def ex(self, children):
        cert_low = children[1]
        if not cert_low:
            cert_low = ''
        return inner_xml(f'<ex{cert_low}>', children[0], '</ex>')

    def expansion(self, children):
        return inner_xml('<expan>', children, '</expan>')

    def lem(self, children):
        return lem_rdg(children, 'lem')

    def rdg(self, children):
        return lem_rdg(children, 'rdg')

    def app_ed(self, children):
        ed_1 = children[0]
        ed_2 = children[1]
        if not ed_2:
            return f'<app type="editorial">{ed_1}<rdg/></app>'
        else:
            return inner_xml(f'<app type="editorial">', children, '</app>')

    def app_ed_multi(self, children):
        return inner_xml(f'<app type="editorial">', children, '</app>')

    def reg(self, children):
        items = ''.join(children[0])
        cert_low = children[1]
        if not cert_low:
            cert_low = ''
        lang = children[2]
        if lang:
            lang = f' xml:lang="{lang}"'
        else:
            lang = ''
        return f'<reg{lang}{cert_low}>{items}</reg>'

    def app_element_cl(self, children):
        items = ''.join(children[0])
        cert_low = children[1]
        if not cert_low:
            cert_low = ''
        return f'{cert_low}>{items}'

    def app_element_cm(self, children):
        items = ''.join(children[0])
        certainty_match = children[1]
        if not certainty_match:
            certainty_match = ''
        return f'{items}{certainty_match}'

    def app_reg(self, children):
        reg = children[0]
        orig = f'<orig>{children[1]}</orig>'
        return f'<choice>{reg}{orig}</choice>'

    def app_reg_multi(self, children):
        reg = ''.join(children[0:-1])
        orig = f'<orig>{children[-1]}</orig>'
        return f'<choice>{reg}{orig}</choice>'

    def app_corr(self, children):
        corr = f'<corr{children[0]}</corr>'
        sic = f'<sic>{children[1]}</sic>'
        return f'<choice>{corr}{sic}</choice>'

    def app_subst(self, children):
        add = f'<add place="inline">{children[0]}</add>'
        deletion = f'<del rend="corrected">{children[1]}</del>'
        return f'<subst>{add}{deletion}</subst>'

    def app_alt(self, children):
        lem = children[0]
        rdg = children[1]
        return f'<app type="alternative">{lem}{rdg}</app>'

    def app_alt_multi(self, children):
        lem = children[0]
        rdg = ''.join(children[1:])
        return f'<app type="alternative">{lem}{rdg}</app>'

    @v_args(inline=True)
    def symbol(self, type, rend, unclear):
        if rend:
            rend = f' rend="{rend}"'
        else:
            rend = ''
        g = f'<g{rend} type="{type}"/>'
        if unclear:
            return f'<unclear>{g}</unclear>'
        else:
            return g

    @v_args(inline=True)
    def drawing(self, description):
        return f'<figure><figDesc>{description}</figDesc></figure>'

    @v_args(inline=True)
    def handshift(self, name, cert_low):
        if not cert_low:
            cert_low = ''
        return f'<handShift new="{name}"{cert_low}/>'

    @v_args(inline=True)
    def note(self, text):
        return f'<note xml:lang="en">{text}</note>'

    def quotation(self, children):
        return inner_xml(f'<q>', children[1], '</q>')

    def diacritical(self, children):
        rend = str(children[0].type).lower()
        return f'<hi rend="{rend}">'

    def diacritical_element(self, children):
        item = children[0]
        his = children[1:]
        end_his = ''
        for _ in his:
            end_his += '</hi>'
        return ''.join(his) + item + end_his

    def paragraphos(self, _):
        return '\n<milestone rend="paragraphos" unit="undefined"/>'

    def horizontal_rule(self, _):
        return '\n<milestone rend="horizontal-rule" unit="undefined"/>'

    def wavy_line(self, _):
        return '\n<milestone rend="wavy-line" unit="undefined"/>'

    def diple_obelismene(self, _):
        return '\n<milestone rend="diple-obelismene" unit="undefined"/>'

    def coronis(self, _):
        return '\n<milestone rend="coronis" unit="undefined"/>'

    @v_args(inline=True)
    def lines_untranscribed(self, precision_low, quantity_extent):
        if not precision_low:
            precision_low = ''
        return f'<gap reason="ellipsis"{quantity_extent} unit="line"{precision_low}><desc>non transcribed</desc></gap>'

    @v_args(inline=True)
    def characters_untranscribed(self, precision_low, quantity_extent):
        if not precision_low:
            precision_low = ''
        return f'<gap reason="ellipsis"{quantity_extent} unit="character"{precision_low}><desc>non transcribed</desc></gap>'

    def is_valid_tei(self, xml: str):
        self.errors = []
        try:
            root = etree.fromstring(xml.encode('utf-8'))
            xml_doc = etree.ElementTree(root)
        except etree.XMLSyntaxError as e:
            try:
                line = e.position[0] - 1
                self.errors.append(f'XML Syntax Error in "{xml.splitlines()[line]}": {e}')
            except IndexError:
                self.errors.append(f'XML Syntax Error: {e}')
            return None
        if rng.validate(xml_doc) is not None:
            return root
        else:
            for error in rng.error_log:
                self.errors.append(f'Invalid EpiDoc XML: {error.message}')
            return None

    def XML_TAG(self, children):
        return ''.join(children)

    def hybrid_xml(self, children):
        items = list(filter(None, children))
        xml_text = ''.join(items)
        print('xml_text', xml_text)
        placeholder = self.tei_builder.build_placeholder(f'<div n="1" subtype="fragment" type="textpart"><ab>{xml_text}</ab></div>')
        root = self.is_valid_tei(placeholder)
        if root is not None:
            ab = root.xpath('//tei:ab', namespaces=ns)[0]
            first_element = ab[0]
            tag = etree.QName(first_element.tag).localname
            if tag == 'lb' or tag == 'milestone':
                return '\n' + xml_text
            else:
                return xml_text
        else:
            return ''


class EssentialAttributeMissingException(Exception):
    """
    Exception raised when a core attribute which is essential for the conversion to Leiden+ is missing.
    """
    def __init__(self, message):
        super().__init__(message)


class EpiDocTransformer:
    def __init__(self):
        self.text = ''
        self.errors = []

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
                    lines = [line for line in self.text.splitlines() if line is not None and str(line).strip()]
                    self.text = '\n'.join(lines)
                    self.text = self.text.replace('=>=D>=D>', '=>=D>\n=D>')
                    return self.text
                else:
                    return '<S=.grc\n<D=.1.fragment<=\n1. \n=>=D>'
            else:
                self.errors.append(f'There is no <div> with @type="edition" in file "{path}".')
                return ''
        else:
            return ''

    def is_valid_tei(self, path: str):
        self.errors = []
        try:
            xml_doc = etree.parse(path)
        except etree.XMLSyntaxError as e:
            self.errors.append(f'XML Syntax Error: {e}')
            return False
        if rng.validate(xml_doc):
            return True
        else:
            for error in rng.error_log:
                self.errors.append(f'Invalid EpiDoc XML: {error.message}')
            return False

    def unsupported_attribute_value(self, node: Tag, attribute_name: str, attribute_value: str):
        self.errors.append(f'Unsupported attribute value: @{attribute_name}="{attribute_value}" in node {str(node)}.')

    def unsupported_attribute(self, node: Tag):
        self.errors.append(f'Unsupported attribute: node {str(node)}.')

    def essential_attribute_missing(self, node: Tag, attribute_name: str):
        msg = f'Essential attribute @{attribute_name} is missing in <{node.name}>, node {node}.'
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
        div_type = attrs['type']
        if div_type == 'edition':
            try:
                lang = attrs['xml:lang']
            except KeyError:
                return self.essential_attribute_missing(node, 'xml:lang')
            return f'<S=.{lang}\n', ''
        elif div_type == 'textpart':
            n = attrs['n']
            if 'subtype' in attrs:
                subtype = '.' + attrs['subtype']
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
            place = attrs['place']
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
                rend = attrs['rend']
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
            rend = node.attrs['rend']
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
            additional_diacritics = ''.join([map_diacriticals[child] for child in hi_children])
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
            rend = node.attrs['rend']
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
        reason = attrs['reason']
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
            return f'{gap_start}.?{unit}{gap_end}', ''
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
        reason = attrs['reason']
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
            rend = node.attrs['rend']
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

    @staticmethod
    def expan(node: Tag):
        return '(', ')'

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
            certainty = '(?)'
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
        return '<:', ':>'

    @staticmethod
    def reg(node: Tag):
        attrs = node.attrs
        if 'cert' in attrs:
            cert_low = '(?)'
        else:
            cert_low = ''
        if 'xml:lang' in attrs:
            xml_lang = '=' + attrs['xml:lang']
        else:
            xml_lang = ''
        sibling = node.next_sibling
        if sibling is None:
            return '', f'{cert_low}{xml_lang}'
        else:
            if sibling.name == 'reg':
                return '', f'{cert_low}{xml_lang}|'
            else:
                return '', f'{cert_low}{xml_lang}'

    @staticmethod
    def orig(node: Tag):
        regs = [sibling for sibling in node.previous_siblings if isinstance(sibling, Tag) and sibling.name == 'reg']
        if len(regs) == 1:
            return '|reg|', ''
        else:
            return '||reg||', ''

    @staticmethod
    def app(node: Tag):
        return '<:', ':>'

    @staticmethod
    def lem(node: Tag):
        if 'resp' in node.attrs:
            resp = '=' + node.attrs['resp']
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
            resp = '=' + node.attrs['resp']
        else:
            resp = ''
        sibling = node.next_sibling
        if sibling is None:
            return '', f'{resp}'
        else:
            if sibling.name == 'rdg':
                return '', f'{resp}|'
            else:
                return '', f'{resp}'

    @staticmethod
    def subst(node: Tag):
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
            value = '=' + node.attrs['value']
        else:
            value = '='
        return '<#', f'{rend}{value}#>'

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
        return '#', ' '

    @staticmethod
    def foreign(node: Tag):
        lang = node.attrs['xml:lang']
        return '~|', f'|~{lang} '
