from lark import Transformer, v_args

def inner_xml(start: str, children: list[str], end: str):
    children = list(filter(None, children))
    xml = start + ''.join(children) + end
    return xml

class LeidenTransformer(Transformer):

    # DOCUMENT START
    @v_args(inline=True)
    def default_language(self, lang):
        print(f'default_language: {lang}')
        return f'<div xml:lang="{lang}" type="edition" xml:space="preserve">'

    def file_start(self, children):
        return ''.join(children) + '\n</div>'

    def div(self, children):
        print(f'div: {children}')
        children = list(filter(None, children))
        return ''.join(children)

    def superdiv(self, children):
        print(f'superdiv: {children}')
        children = list(filter(None, children))
        return ''.join(children)

    @v_args(inline=True)
    def div_start(self, n, subtype, corresp):
        print(f'div_start: {n}, {subtype}, {corresp}')
        if corresp:
            corresp_str = f' corresp="{corresp}"'
        else:
            corresp_str = ''
        if n == 'r' or n == 'v':
           subtype_str = ''
        else:
           subtype_str = f' subtype="{subtype}"'
        xml = f'<div n="{n}"{subtype_str} type="textpart"{corresp_str}>'
        print('div_start XML:', xml)
        return f'<div n="{n}"{subtype_str} type="textpart"{corresp_str}>'

    def TEXTBLOCK_OPEN(self, _):
        xml = '<ab>'
        print('TEXTBLOCK_OPEN XML:', xml)
        return xml

    def TEXTBLOCK_CLOSE(self, _):
        xml = '</ab>'
        print('TEXTBLOCK_OPEN XML:', xml)
        return xml

    def DIV_CLOSE(self, _):
        xml = '</div>'
        print('DIV_CLOSE XML:', xml)
        return xml

    def NEWLINE(self, _):
        return '\n'

    # ITEMS
    @v_args(inline=True)
    def text(self, text):
        print(f'text: {text}')
        return text

    @v_args(inline=True)
    def text_space(self, space):
        print(f'text_space: {space}')
        return space

    @v_args(inline=True)
    def line(self, _, number, lb, __):
        print(f'line: {number}, {lb}')
        if lb:
            lb_str = f' break="no"'
        else:
            lb_str = ''
        xml = f'\n<lb n="{number}"{lb_str}/>'
        print('line XML:', xml)
        return xml

    @v_args(inline=True)
    def line_formatted(self, n, n2, lb, rend):
        print(f'line_formatted: n={n}, n2={n2}, lb={lb}, rend={rend}')
        if lb:
            lb_str = f' break="no"'
        else:
            lb_str = ''
        xml = f'\n<lb n="{n+n2}"{lb_str} rend="{rend}"/>'
        print('line_formatted XML:', xml)
        return xml

    @v_args(inline=True)
    def line_rend(self, n, lb, rend):
        print(f'line_rend: n={n}, lb={lb}, rend={rend}')
        if lb:
            lb_str = f' break="no"'
        else:
            lb_str = ''
        xml = f'\n<lb n="{n}"{lb_str} rend="{rend}"/>'
        print('line_rend XML:', xml)
        return xml

    @v_args(inline=True)
    def line_margin(self, n, n2, lb):
        print(f'line_margin: n={n}, n2={n2}, lb={lb}')
        if lb:
            lb_str = f' break="no"'
        else:
            lb_str = ''
        xml = f'\n<lb n="{n+n2}"{lb_str}/>'
        print('line_margin XML:', xml)
        return xml

    def EXTENT_UNKNOWN(self, _):
        xml = ' extent="unknown"'
        print('UNKNOWN XML:', xml)
        return xml

    def CERT_LOW(self, _):
        xml = ' cert="low"'
        print('CERT_LOW XML:', xml)
        return xml

    def CERTAINTY_MATCH(self, _):
        xml = '<certainty match=".." locus="value"/>'
        print('CERTAINTY_MATCH XML:', xml)
        return xml

    @v_args(inline=True)
    def range(self, at_least, at_most):
        xml = f' atLeast="{at_least}" atMost="{at_most}"'
        print('RANGE XML:', xml)
        return xml

    @v_args(inline=True)
    def QUANTITY(self, quantity):
        xml = f' quantity={quantity}'
        print('QUANTITY XML:', xml)
        return xml

    @v_args(inline=True)
    def LIN(self, _):
        xml = ' unit="line"'
        print(f'LINE XML:', xml)
        return xml

    @v_args(inline=True)
    def QUANTITY(self, quantity):
        xml = f' quantity="{quantity}"'
        print(f'QUANTITY XML:', xml)
        return xml

    def vacat(self, children):
        if not children[2]:
            return inner_xml('<space', children, ' unit="character"/>')
        else:
            return inner_xml('<space', children, '/>')

    def add_above(self, children):
        return inner_xml('<add place="above">', children, '</add>')

    def add_below(self, children):
        return inner_xml('<add place="below">', children, '</add>')

    def add_left(self, children):
        return inner_xml('<add place="left">', children, '</add>')

    def add_right(self, children):
        return inner_xml('<add place="right">', children, '</add>')

    def add_interlin(self, children):
        return inner_xml('<add place="interlinear">', children, '</add>')

    def add_sling(self, children):
        return inner_xml('<add rend="sling" place="margin">', children, '</add>')

    def add_underline(self, children):
        return inner_xml('<add rend="underline" place="margin">', children, '</add>')

    def box(self, _):
        return '<milestone rend="box" unit="undefined"/>'

    def tall(self, children):
        return inner_xml('<hi rend="tall">', children, '</hi>')

    def superscripted(self, children):
        return inner_xml('<hi rend="superscript">', children, '</hi>')

    def subscripted(self, children):
        return inner_xml('<hi rend="subscript">', children, '</hi>')

    def supraline(self, children):
        return inner_xml('<hi rend="supraline">', children, '</hi>')

    def supraline_underline(self, children):
        return inner_xml('<hi rend="supraline-underline">', children, '</hi>')

    def supralinear_stroke(self, children):
        print('supralinear_stroke:', children)
