import re
from shared import greek_pattern

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
