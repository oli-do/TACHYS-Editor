import re
from shared import greek_pattern


def format_numerals(text):
    tokens = list(set(text.split()))
    numerals = {"α": 1, "β": 2, "γ": 3, "δ": 4, "ε": 5, "ϛ": 6, "Ϛ": 6, "ϝ": 6, "Ϝ": 6, "ζ": 7, "η": 8, "θ": 9,
                "ι": 10, "κ": 20, "λ": 30, "μ": 40, "ν": 50, "ξ": 60, "ο": 70, "π": 80, "\u03DF": 90, "\u03DE": 90,
                "ρ": 100, "σ": 200, "τ": 300, "υ": 400, "φ": 500, "χ": 600, "ψ": 700, "ω": 800, "\u03e1": 900,
                "\u03e0": 900,
                "͵α": 1000, "͵β": 2000, "͵γ": 3000, "͵δ": 4000, "͵ε": 5000, "͵ϛ": 6000, "͵Ϛ": 6000, "͵ϝ": 6000,
                "͵Ϝ": 6000, "͵ζ": 7000, "͵η": 8000, "͵θ": 9000}
    for token in tokens:
        if '\u0304' in token:
            clean_token = token.replace('\u0304', '')
            value = 0
            skip_iteration = False
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
        self.supralinear_stroke = '[\ue6b7]'

    @staticmethod
    def replace_lunate_sigma(text):
        print(text)
        lines = text.split('\n')
        new_lines = []
        for line in lines:
            words = line.split()
            new_words = []
            for word in words:
                new_word = ''
                for i in range(len(word)):
                    foreshadow = word[i:len(word)]
                    char = word[i]
                    if char == 'ϲ' or char == 'c':
                        if i == len(word) - 1:
                            new_word += 'ς'
                        elif i == 0:
                            new_word += 'σ'
                        else:
                            print(foreshadow)
                            if re.findall(r'[' + greek_pattern + r']+', foreshadow):
                                new_word += 'σ'
                            else:
                                new_word += 'ς'
                    elif char == 'ϲ'.upper() or char == 'c'.upper():
                        new_word += 'Σ'
                    else:
                        new_word += char
                new_words.append(new_word)
            new_line = ' '.join(new_words)
            new_lines.append(new_line)
        return '\n'.join(new_lines)

    def replace_underdots(self, text):
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
        text = re.sub(self.supralinear_stroke, '\u0304', text)
        return text
