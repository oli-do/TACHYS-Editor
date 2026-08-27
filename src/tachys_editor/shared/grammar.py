from typing import Literal


allowed_punctuation = '’͵;,·˙'

# Ancient Greek
__combining_diacritical_marks_grc = '\u0300-\u0301\u0306-\u0308\u0313-\u0314\u0340-\u0345'
__greek_extensions = '\u1f00-\u1fb0\u1fb2-\u1fb8\u1fba-\u1fd0\u1fd2-\u1fd8\u1fda-\u1fe0\u1fe2-\u1fe8\u1fea-\u1ffe'
__greek_and_coptic_grc = '\u037e-\u03ce\u03d8-\u03e1'
__ancient_greek_numerals = '\U00010140-\U0001018E'
greek_text = __combining_diacritical_marks_grc + __greek_extensions + __greek_and_coptic_grc + __ancient_greek_numerals

# Latin
latin_text = 'A-Ia-iK-Vk-vXYxy'

# Coptic
__coptic = '\u2c80-\u2cff'
__greek_and_coptic_cop = '\u03e2-\u03ef'
__coptic_numerals = '\U000102E0-\U000102FB'
__combining_diacritical_marks_cop = '\u0300-\u0308\u035E'
coptic_text = __coptic + __greek_and_coptic_cop + __coptic_numerals + __combining_diacritical_marks_cop


def get_lang_chars(lang: Literal['grc', 'la', 'cop', 'any']):
    if lang == 'grc':
        lang_chars = greek_text
    elif lang == 'la':
        lang_chars = latin_text
    elif lang == 'cop':
        lang_chars = coptic_text
    elif lang == 'any':
        lang_chars = r'\p{L}'
    return lang_chars


def build_text_rules(lang: Literal['grc', 'la', 'cop', 'any']):
    lang_chars = get_lang_chars(lang)
    text_rule = f'TEXT: /[' + allowed_punctuation + lang_chars + ']+(?![\u0323\u0304])/'
    text_char_rule = 'TEXT_CHAR: /[' + lang_chars + ']/'
    return text_rule, text_char_rule

