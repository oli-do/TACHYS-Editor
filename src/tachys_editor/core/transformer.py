from lark import Transformer, v_args

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

class LeidenPlusTransformer(Transformer):

    # DOCUMENT START
    @v_args(inline=True)
    def default_language(self, lang):
        return f'<div xml:lang="{lang}" type="edition" xml:space="preserve">'

    def file_start(self, children):
        return ''.join(children) + '\n</div>'

    def div(self, children):
        children = list(filter(None, children))
        return ''.join(children)

    def superdiv(self, children):
        children = list(filter(None, children))
        return ''.join(children)

    @v_args(inline=True)
    def div_start(self, n, subtype, corresp):
        if corresp:
            corresp_str = f' corresp="{corresp}"'
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

    # ITEMS
    def items(self, children):
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

    def supraline_underline(self, children):
        return inner_xml('<hi rend="supraline-underline">', children[0], '</hi>')

    def supralinear_stroke(self, children):
        char = children[0]
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
        return f'<hi rend="supraline">{char}</hi>'

    def lines_lost(self, children):
        return inner_xml('<gap reason="lost"', children, '/>')

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
        return f'<foreign xml:lang="{lang}">{text}</foreign>"'

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







