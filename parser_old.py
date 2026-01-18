import re
from dataclasses import dataclass

@dataclass
class ParserError:
    line: int
    characters: str
    description: str


class LeidenParser:
    def __init__(self):
        self.text = ''
        self.errors = []
        self.greek_input = "ΌΏΎΊΉᾲᾀᾁᾂᾃᾅᾇέάΐήώίόύϝϛϋϊᾄᾆᾳᾴᾷαβγδεζηθικλμνξοπρστυφχψωἀἄἂἆἁἅἃἇάὰᾶἐἔἒἑἕἓὲέἠἤἢἦἡἥἣἧὴήᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἰἴἲἶἱἵἳἷὶίῐῑῒΐῖῗὀὄὂὁὅὃὸόὐὑὒὓὔὕὖὗὺῦύῠῡῢΰῧὠὤὢὦὡὥὣὧώὼᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷῤῥἈἌἊἎἉἍἋἏᾺΆᾼᾈᾉᾊᾋᾌᾍᾎᾏἘἜἚἙἝἛῈΈἨἬἪἮἩἭἫἯῊΉῌᾘᾙᾚᾛᾜᾝᾞᾟἸἼἺἾἹἽἻἿΊῚῘῙὈὌὊὉὍὋΌῸὙὝὛὟΎῪῨῩὨὬὪὮὩὭὫὯΏῺῼᾨᾩᾪᾫᾬᾭᾮᾯῬςϲϹ"


    def parse(self):
        if not self.text:
            return ''
        self.errors = []
        lines = self.text.split('\n')
        for i in range(len(lines)):
            line = lines[i]
            line = line.strip()
            if '<S=' in line:
                print(self.parse_language(line, i))
            elif re.match(r'^[0-9]+\.-? ', line):
                print(self.parse_text_line(line, i))
        print(self.errors)

    def parse_language(self, line: str, index: int):
        dot_language_abbr = re.findall(r'\.[a-zA-Z\-]+', line)
        if dot_language_abbr:
            lang = dot_language_abbr[0].replace('.', '')
            return f'<div xml:lang="{lang}" type="edition" xml:space="preserve">'
        else:
            self.errors.append(ParserError(index, line, 'Language abbreviation not found.'))
            return ''

    def parse_text_line(self, line: str, index: int):
        tokens = line.split()
        xml_line = ''
        for i in range(len(tokens)):
            token = tokens[i]
            if re.match(r'[0-9]+\.', token):
                xml_line += self.line_details(token, index)
            elif '[' in token:
                xml_line += self.letters_lost(token, index)
            elif 'vac.' in token:
                xml_line += self.vacat(token, index)
            elif '(' in token:
                xml_line += self.expansion(token, index)
            elif '\\' in token or '//' in token or '||' in token or '<|' in token or '<_' in token:
                xml_line += self.add(token, index)
            elif '¯' in token:
                return f'<hi rend="supraline">{token.replace('¯', '')}</hi>'
            elif 'lost.' in token:
                xml_line += self.lines_lost(token, index)
            elif re.match(r'(ca)?\.', token):
                xml_line += self.illegible(token, index)
            elif 'vestig' in token:
                xml_line += self.vestiges(token, index)
            elif '<' in token:
                xml_line += self.supplied_omitted(token, index)
            elif '{' in token:
                xml_line += self.surplus(token, index)
            elif '〚' in token:
                xml_line += self.deletion(token, index)
            else:
                xml_line += token
        return xml_line

    def letters_lost(self, token: str, index: int):
        brackets = re.findall(r'\[.*?]', token)
        outer_text = list(filter(None, re.split(r'\[.*?]', token)))
        for bracket in brackets:
            print(bracket)
            if re.match(r'\[(ca)?\.[0-9?]+]', bracket) or re.match(r'\[.[0-9]+-[0-9]+]', bracket):
                nums = re.findall(r'[0-9?]+', bracket)
                if len(nums) == 2:
                    try:
                        if int(nums[0]) > int(nums[1]) or int(nums[0]) == int(nums[1]):
                            self.errors.append(ParserError(index, token, 'Invalid @atLeast and @atMost: @atLeast must be smaller than @atMost.'))
                            return ''
                    except ValueError:
                        self.errors.append(ParserError(index, token, 'Unknown error in letters lost.'))
                    token = token.replace(bracket, f'<gap reason="lost" atLeast="{nums[0]}" atMost="{nums[1]}" unit="character"/>')
                elif len(nums) > 2 or len(nums) == 0:
                    self.errors.append(ParserError(index, '', 'Invalid number of attributes for letters lost.'))
                else:
                    if nums[0] == '?':
                        attribute = 'extent'
                        num = 'unknown'
                    else:
                        try:
                            _ = int(nums[0])
                        except ValueError:
                            self.errors.append(ParserError(index, token, 'Invalid @quantity for letters lost.'))
                        attribute = 'quantity'
                        num = nums[0]
                    token = token.replace(bracket, f'<gap reason="lost" {attribute}="{num}" unit="character"/>')
            elif re.match(r'\[.*?]', bracket):
                token = token.replace(bracket, f'<supplied reason="lost">{bracket.replace('[', '').replace(']', '')}</supplied>')
        for text in outer_text:
            replacement = self.parse_text_line(text, index)
            token = token.replace(text, replacement)
        return token

    def expansion(self, token, index):
        open = token.count('(')
        close = token.count(')')
        if not open == close:
            self.errors.append(ParserError(index, token, 'Incorrect number of brackets in expansion.'))
            return ''
        if '|' in token:
            match = re.search(r'\(\|(.+)\|\)', token)
            if not match:
                self.errors.append(ParserError(index, token, 'Invalid expansion.'))
                return ''
            if '(?)' in token:
                return f'<abbr>{match.group(1).replace('(?)', '')}<certainty locus="name" match=".."/></abbr>'
            else:
                return f'<abbr>{match.group(1)}</abbr>'
        expansion = '<expan>'
        token = token.strip('(')
        token = token.strip(')')
        parts = token.split(')')
        for part in parts:
            splitted_part = part.split('(')
            if len(splitted_part) == 2:
                expan = self.parse_text_line(splitted_part[0], index)
                ex = self.parse_text_line(splitted_part[1], index)
                if '?' in ex:
                    cert = ' cert="low"'
                else:
                    cert = ''
                expansion += f'{expan}<ex{cert}>{ex}</ex>'
            else:
                ex = splitted_part[0], index
                if '?' in ex:
                    cert = ' cert="low"'
                else:
                    cert = ''
                expansion += f'<ex{cert}>{ex}</ex>'
                break
        expansion += f'</expan>'
        return expansion

    def surplus(self, token, index):
        matches = re.search(r'(.*)\{(.+)}(.*)', token)
        if matches:
            return f'{matches.group(1)}<surplus>{matches.group(2)}</surplus>{matches.group(3)}'
        else:
            self.errors.append(ParserError(index, token, 'Empty Leiden braces.'))
            return ''

    def deletion(self, token, index):
        matches = re.search(r'(.*)〚(.+)〛(.*)', token)
        if matches:
            return f'{matches.group(1)}<del rend="erasure">{matches.group(2)}</del>{matches.group(3)}'
        else:
            self.errors.append(ParserError(index, token, 'Empty Leiden double square braces.'))
            return ''

    def supplied_omitted(self, token, index):
        cert = ''
        if '(?)' in token:
            cert = ' cert="low"'
            token = token.replace('(?)', '')
        matches = re.search(r'(.*)<(.+)>(.*)', token)
        if matches:
            return f'{matches.group(1)}<supplied reason="omitted"{cert}>{matches.group(2)}</supplied>{matches.group(3)}'
        else:
            self.errors.append(ParserError(index, token, 'Empty angled brackets.'))
            return ''

    def vestiges(self, token, index):
        if token == 'vestig':
            return '<gap reason="illegible" extent="unknown" unit="character"><desc>vestiges</desc></gap>'
        elif token == 'vestig.?lin':
            return '<gap reason="illegible" extent="unknown" unit="line"/>'
        if not re.match(r'vestig\.[0-9]+(lin|char)', token) and not re.match(r'vestig\.[0-9]+-[0-9]+(lin|char)', token) and not re.match(r'vestig\.ca\.[0-9]+(lin|char)', token):
            self.errors.append(ParserError(index, token, 'Invalid syntax for vestiges.'))
            return ''
        if 'lin' in token:
            unit = 'line'
        else:
            unit = 'character'
        nums = re.findall(r'[0-9]+', token)
        if len(nums) == 2:
            try:
                if int(nums[0]) > int(nums[1]) or int(nums[0]) == int(nums[1]):
                    self.errors.append(ParserError(index, token, 'Invalid @atLeast and @atMost: @atLeast must be smaller than @atMost.'))
                    return ''
            except ValueError:
                self.errors.append(ParserError(index, token, 'Unknown error in vestiges.'))
            return f'<gap reason="illegible" atLeast="{nums[0]}" atMost="{nums[1]}" unit="character"><desc>vestiges</desc></gap>'
        elif len(nums) > 2 or len(nums) == 0:
            self.errors.append(ParserError(index, token, 'Invalid number of attributes for vestiges.'))
            return ''
        else:
            if 'ca' in token:
                precision = ' precision="low"'
            else:
                precision = ''
            try:
                _ = int(nums[0])
            except ValueError:
                self.errors.append(ParserError(index, token, '@quantity must be a number.'))
            return f'<gap reason="illegible" quantity="{nums[0]}" unit="{unit}"{precision}><desc>vestiges</desc></gap>'

    def illegible(self, token, index):
        if not re.match(r'\.[0-9]+(lin)?', token) and not re.match(r'\.[0-9]+-[0-9]+(lin)?', token) and not re.match(r'ca\.[0-9]+(lin)?', token):
            self.errors.append(ParserError(index, token, 'Invalid syntax for illegible.'))
            return ''
        if 'lin' in token:
            unit = 'line'
        else:
            unit = 'character'
        nums = re.findall(r'[0-9]+', token)
        if len(nums) == 2:
            try:
                if int(nums[0]) > int(nums[1]) or int(nums[0]) == int(nums[1]):
                    self.errors.append(ParserError(index, token, 'Invalid @atLeast and @atMost: @atLeast must be smaller than @atMost.'))
                    return ''
            except ValueError:
                self.errors.append(ParserError(index, token, 'Unknown error in lines lost.'))
            return f'<gap reason="illegible" atLeast="{nums[0]}" atMost="{nums[1]}" unit="character"/>'
        elif len(nums) > 2 or len(nums) == 0:
            self.errors.append(ParserError(index, token, 'Invalid number of attributes for lines lost.'))
            return ''
        else:
            if 'ca' in token:
                precision = ' precision="low"'
            else:
                precision = ''
            try:
                _ = int(nums[0])
            except ValueError:
                self.errors.append(ParserError(index, token, '@quantity must be a number.'))
            return f'<gap reason="illegible" quantity="{nums[0]}" unit="{unit}"{precision}/>'

    def lines_lost(self, token: str, index: int):
        if not re.match(r'lost\.[0-9]+lin', token) and not re.match(r'lost\.ca\.[0-9]+]lin', token) and not re.match(
                r'lost\.[0-9]+-[0-9]+lin', token) and not token == 'lost.?lin' and not token == 'lost.?lin(?)':
            self.errors.append(ParserError(index, token, 'Invalid syntax for lines lost.'))
            return ''
        if '.ca.' in token:
            precision = ' precision="low"'
        else:
            precision = ''
        nums = re.findall(r'[0-9?]+', token)
        if len(nums) == 2:
            if nums[0] == nums[1] == '?':
                return '<gap reason="lost" extent="unknown" unit="line"><certainty match=".." locus="name"/></gap>'
            try:
                if int(nums[0]) > int(nums[1]) or int(nums[0]) == int(nums[1]):
                    self.errors.append(ParserError(index, token, 'Invalid @atLeast and @atMost: @atLeast must be smaller than @atMost.'))
                    return ''
            except ValueError:
                self.errors.append(ParserError(index, token, 'Unknown error in lines lost.'))
            return f'<gap reason="lost" atLeast="{nums[0]}" atMost="{nums[1]}" unit="line"/>'
        elif len(nums) > 2 or len(nums) == 0:
            self.errors.append(ParserError(index, '', 'Invalid number of attributes for lines lost.'))
            return ''
        else:
            if nums[0] == '?':
                attribute = 'extent'
                num = 'unknown'
            else:
                try:
                    _ = int(nums[0])
                except ValueError:
                    self.errors.append(ParserError(index, token, 'Invalid @quantity for lines lost.'))
                    return ''
                attribute = 'quantity'
                num = nums[0]
            return f'<gap reason="lost" {attribute}="{num}" unit="line"{precision}"/>'

    def add(self, token: str, index: int):
        rend = ''
        if '||' in token:
            place = re.findall(r'\|\|[a-z]+:', token)
            if not place:
                self.errors.append(ParserError(index, token, 'Missing place definition in add.'))
                return ''
            else:
                place = place[0].replace('|', '').replace(':', '')
                text = token.replace('|', '').replace(':', '').replace(place, '').strip()
                if not text:
                    self.errors.append(ParserError(index, token, 'Missing text in add.'))
                    return ''
                if place == 'interlin':
                    place = 'interlinear'
        elif '\\' in token:
            place = 'above'
            text = token.replace('\\', '').replace('/', '')
        elif '//' in token:
            place = 'below'
            text = token.replace('//', '').replace('\\\\', '')
        elif '<|' in token:
            rend = ' rend="sling"'
            place = 'margin'
            text = token.replace('<|', '').replace('|>', '')
        elif '<_' in token:
            rend = ' rend="underline"'
            place = 'margin'
            text = token.replace('<_', '').replace('_>', '')
        else:
            self.errors.append(ParserError(index, token, 'Unknown add syntax.'))
            return ''
        return f'<add{rend} place="{place}">{text}</add>'

    @staticmethod
    def line_details(token: str, index: int):
        line_no = re.findall(r'[0-9]+', token)[0]
        lb = f'<lb n="{line_no}"'
        if '-' in token:
            lb += ' break="no"'
        lb += '/>'
        return lb

    def vacat(self, token: str, index: int):
        if 'lin' in token:
            unit = 'line'
        else:
            unit = 'character'
        if '-' in token:
            nums = re.findall(r'[0-9]+', token)
            if len(nums) == 2:
                at_least = nums[0]
                at_most = nums[1]
            else:
                self.errors.append(ParserError(index, token, 'Invalid range of vacat.'))
                return ''
            return f'<space atLeast="{at_least}" atMost="{at_most}" unit="{unit}"/>'
        else:
            num = re.findall(r'[0-9?]+', token)[0]
            if num == '?':
                num = 'unknown'
                argument = 'extent'
            else:
                try:
                    _ = int(num)
                except ValueError:
                    self.errors.append(ParserError(index, token, 'Invalid quantity or extent of vacat.'))
                    return ''
                argument = 'quantity'
            if '.ca.' in token:
                precision = ' precision="low"'
            else:
                precision = ''
            return f'<space {argument}="{num}" unit="{unit}"{precision}/>'
