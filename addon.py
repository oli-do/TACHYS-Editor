import re
from shared import greek_pattern

class PasteManager:

    @staticmethod
    def replace_lunate_sigma(text):
        words = text.split()
        new_words = []
        for word in words:
            new_word = ''
            for i in range(len(word)):
                foreshadow = word[i:len(word)]
                char = word[i]
                if char == 'ϲ':
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
                else:
                    new_word += char
            new_words.append(new_word)
        line = ' '.join(new_words)
        return line

    @staticmethod
    def replace_underdots(text):
        text = re.sub(r' \u0323', '$', text)
        text = re.sub(r'^\u0323', '$', text)
        underdots = re.findall(r'\$+', text)
        for dots in underdots:
            num = dots.count('$')
            text = text.replace(dots, f'.{num}')
        return text
