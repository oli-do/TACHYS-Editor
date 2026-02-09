import re
from shared import greek_pattern


def format_numerals(text):
    tokens = list(set(text.split()))
    numerals = {"α": 1, "β": 2, "γ": 3, "δ": 4, "ε": 5, "ϛ": 6, "Ϛ": 6, "ϝ": 6, "Ϝ": 6, "ζ": 7, "η": 8, "θ": 9,
                "ι": 10, "κ": 20, "λ": 30, "μ": 40, "ν": 50, "ξ": 60, "ο": 70, "π": 80, "\u03DF": 90, "\u03DE": 90,
                "ρ": 100, "σ": 200, "τ": 300, "υ": 400, "φ": 500, "χ": 600, "ψ": 700, "ω": 800, "\u03e1": 900,
                "\u03e0": 900}
    numerals_thousands = {
                "α": 1000, "β": 2000, "γ": 3000, "δ": 4000, "ε": 5000, "ϛ": 6000, "Ϛ": 6000, "ϝ": 6000,
                "Ϝ": 6000, "ζ": 7000, "η": 8000, "θ": 9000}
    for token in tokens:
        clean_token = token.replace('\u0304', '').replace('͵', '')
        if len(clean_token) > 4:
            return text
        thousands = r'[αβγδεϛϚϝϜζηθ]'
        hundreds = r'[ρστυφχψω\u03e1\u03e0]?'
        tens = r'[ικλμνξοπ\u03DF\u03DE]?'
        ones = r'[αβγδϵϛϚϝϜζηθ]'
        print(thousands + "?" + hundreds + tens + ones, clean_token)
        if not re.fullmatch(thousands + "?" + hundreds + tens + ones, clean_token):
            return text
        value = 0
        skip_iteration = False
        if len(clean_token) > 1 and re.fullmatch(thousands + hundreds + tens + ones, clean_token):
            skip_iteration = True
            value = numerals_thousands[clean_token[0]]
        for i in range(len(clean_token)):
            if skip_iteration:
                skip_iteration = False
                continue
            char = clean_token[i]
            if char == '͵':
                try:
                    char += clean_token[i + 1]
                    skip_iteration = True
                except IndexError:
                    continue
            try:
                value += numerals[char]
            except KeyError:
                break
        if value > 0:
            text = text.replace(token, f'<#{token}={value}#>')
    return text


class PasteManager:
    def __init__(self):
        self.underdot = '[\u0323\ue5ce]'
        self.supralinear_stroke = '[\ue6b7\ue790]'

    @staticmethod
    def replace_lunate_sigma(text):
        print(text)
        lines = text.split('\n')
        new_lines = []
        for line in lines:
            if not re.match(r'.*[ϲcϹC]', line):
                new_lines.append(line)
                continue
            words = line.split()
            new_words = []
            for word in words:
                if not re.match(r'.*[ϲcϹC]', word):
                    new_words.append(word)
                    continue
                new_word = ''
                for i in range(len(word)):
                    char = word[i]
                    if char == 'ϲ' or char == 'c':
                        if i == len(word) - 1:
                            new_word += 'ς'
                        elif i == 0:
                            new_word += 'σ'
                        else:
                            foreshadow = word[i:len(word)]
                            print(foreshadow)
                            if re.findall(r'[' + greek_pattern + r']+', foreshadow):
                                new_word += 'σ'
                            else:
                                new_word += 'ς'
                    elif char == 'Ϲ' or char == 'C':
                        new_word += 'Σ'
                    else:
                        new_word += char
                new_words.append(new_word)
            new_line = ' '.join(new_words)
            new_lines.append(new_line)
        return '\n'.join(new_lines)

    def replace_underdots(self, text):
        if not re.match(self.underdot, text):
            return text
        text = re.sub(r'^' + self.underdot, '$', text)
        text = re.sub(r'([(\[{<])' + self.underdot, r'\1$', text)
        text = re.sub(r' ' + self.underdot, '$', text)
        underdots = re.findall(r'\$+', text)
        underdots = list(set(underdots))
        underdots.sort(reverse=True)
        for dots in underdots:
            num = dots.count('$')
            text = text.replace(dots, f'.{num}')
        print(underdots)
        return text

    def replace_supralinear_stroke(self, text):
        return re.sub(self.supralinear_stroke, '\u0304', text)

    @staticmethod
    def replace_brackets(text):
        if not re.match('\[', text):
            return text
        brackets = set(list(re.findall(r'\[.[^]]+]', text)))
        for bracket in brackets:
            if 'σa' in bracket or 'σ.' in bracket:
                new_bracket = bracket.replace('σa', 'ca.').replace('σ.', 'ca.').replace(' ', '')
                text = text.replace(bracket, new_bracket)
        return text
