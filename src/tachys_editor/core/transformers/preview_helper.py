import html
import bisect
import re
import unicodedata
from bs4.element import Tag

g_type_map: dict = {
        'coronis' : '⸎',
        "asteriskos": "※",
        "antisigma": "ͻ",
        "antisigma-periestigmene": "ͽ",
        "diple": "›",
        "diple-periestigmene": "⸖",
        "obelos": "―",
        "downwards-ancora": "⸔",
        "upwards-ancora": "⸕",
        "dotted-obelos": "⸓",
        "reverse-dotted-obelos": "(PN does not yet support this character)",
        "chi-periestigmenon": "Χ·",
        "diple-obelismene": "⤚",
        "stauros": "†",
        "rho-cross": "⳨",
        "chirho": "☧",
        "dash": "—",
        "filler": {
            "extension": "—",
            "diple": "›"
        },
        "slanting-stroke": "/",
        "backslash": "\\",
        "double-slanting-stroke": "⸗",
        "double-vertical-bar": "‖",
        "long-vertical-bar": "|",
        "swungdash": "~",
        "dot": "•",
        "check": "／",
        "filled-circle": "⦿",
        "apostrophe": "’",
        "diastole": "’",
        "hypodiastole": "⸒",
        "high-punctus": "˙",
        "middot": "·",
        "low-punctus": ".",
        "dipunct": "∶",
        "tripunct": "⋮",
        "tetrapunct": "⁞",
        "parens-punctuation-opening": "(",
        "parens-punctuation-closing": ")",
        "parens-upper-opening": "⎛",
        "parens-middle-opening": "⎜",
        "parens-lower-opening": "⎝",
        "parens-upper-closing": "⎞",
        "parens-middle-closing": "⎟",
        "parens-lower-closing": "⎠",
        "upper-brace-opening": "⎧",
        "center-brace-opening": "⎨",
        "lower-brace-opening": "⎩",
        "x": "☓",
        "xs": "☓☓☓☓☓"
    }

expan_map: dict = {
    "θ": "☉",
    "γι": "",
    "γρ": "",
    "γτ": "",
    "δι": "",
    "ζρ": "",
    "νι": "",
    "ογ": "",
    "πρ": "",
    "χρ": "⳩",
    "ωρ": "",
    "σχι": "ϲ",
    "χαρ": "χαρ/",
    "ημρ": "η",
}

ex_start_map: dict = {
    "ονοματα": "̅",
    "δραχμ": "",
    "σελήν": "",
    "ουραν": "",
    "και": "ϗ",
    "ηλι": "",
}

ex_match_map: dict = {
    "ν": "\u0305"
}

def remove_diacritics_punctuation(text: str):
    normalized = unicodedata.normalize('NFD', text)
    clean_text = "".join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')
    clean_text = re.sub(r'[^\w\s]', '', clean_text)
    return unicodedata.normalize('NFC', clean_text)

def draw_lost_lines_extent_unknown(lines: list[str]):
    lines_raw_text = [html.unescape(re.sub(r'<.*?>|[0-9]+', '', line)) for line in lines]
    lost_lin_indices = []
    text_part_indices = []
    for i in range(len(lines)):
        line = lines[i]
        if 'lost.?lin' in line:
            lost_lin_indices.append(i)
        elif '<h3>' in line:
            text_part_indices.append(i)
    if len(text_part_indices) == 1:
        text_part_indices.append(len(lines_raw_text) - 1)
    for i in lost_lin_indices:
        pos = bisect.bisect_left(text_part_indices, i)
        try:
            text_part_start = text_part_indices[pos - 1]
            text_part_end = text_part_indices[pos]
            while not '<tr>' in lines[text_part_end]:
                text_part_end -= 1
            text_part_char_lengths = [len(remove_diacritics_punctuation(line)) for line in lines_raw_text[text_part_start:text_part_end]]
            max_length = max(text_part_char_lengths)
        except IndexError:
            max_length = 20
        lost_lin_symbol = ''
        lost_lin_symbol += '-' * max_length
        lines[i] = lines[i].replace('lost.?lin', lost_lin_symbol)
    return lines

def draw_gaps(lines: list[str]):
    for i in range(len(lines)):
        lines[i] = lines[i].strip()
        line = lines[i]
        if line.endswith('[ ? ]'):
            lines[i] = line[:-4]
        if line.startswith('[ ? ]'):
            lines[i] = line[4:]
        lines[i] = re.sub(r']( +)\[', r'\1', lines[i])
    return lines

def map_resp_nodes(main_div: Tag):
    resp_nodes = main_div.find_all(None, attrs={'resp': True}, recursive=True)
    resps = []
    for node in resp_nodes:
        if isinstance(node, Tag):
            resp = str(node.attrs['resp'])
            if ',' in resp:
                resp_split = resp.split(',')
                for r in resp_split:
                    resps.append(r.strip())
            else:
                resps.append(resp)
    resps = list(set(resps))
    resps_dict = {}
    final_dict = {}
    for resp in resps:
        if not ' ' in resp:
            resps_dict[resp] = [resp]
    for resp in resps:
        if ' ' in resp:
            basename = resp.split(' ')[0]
            if basename in resps_dict:
                resps_dict[basename].append(resp)
            else:
                resps_dict[basename] = [resp]
    for key, val in resps_dict.items():
        if len(val) == 1:
            final_dict[val[0]] = key[:2]
        else:
            for i in range(len(val)):
                abbr = key[:2]
                if i == 0:
                    final_dict[val[i]] = abbr
                else:
                    final_dict[val[i]] = abbr + f'<sup>{i}</sup>'
    return final_dict

def create_html_output(text: str, resp_map: dict[str, str]):
    resp_map = dict(sorted(resp_map.items(), key=lambda item: item[1]))
    title = '<h2 style="text-align:center;">EDITION</h2>'
    commentary = '<p>This text has been created with TACHYS Editor.</p>\n'
    commentary += f'\n<p>{', '.join([f'{key} [{val}]' for key, val in resp_map.items()])}</p>'
    html_output = (
                      '<!DOCTYPE html><html style="margin:0; padding:0; height:100%; width:100%; ">'
                      '<body style="margin:0; padding:0; height:100%; width:100%; display:grid; place-items:center; background:#f0f0f0;">'
                      '<div style="'
                      'font-family:IFAO-Grec Unicode; '
                      'font-size:11px; '
                      'width:21cm; '
                      'border:2px solid black; '
                      'transform: scale(min(100vw / 21cm, 100vh / 29.7cm)); '
                      'transform-origin: center; '
                      'background: white; '
                      'padding: 2.54cm; '
                      'box-sizing: border-box; '
                      '">') + title + commentary + text + '</div></body></html>'
    return html_output