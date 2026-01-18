from lark import Lark

class LeidenParser:

    def parse(self, text):
        for line in text.splitlines():
            print(line)
            if "=" in line:
                continue
            with open('leiden.lark', 'r', encoding='utf-8') as file:
                leiden_grammar = file.read()
            parser = Lark(leiden_grammar, parser='lalr')
            tree = parser.parse(line)
            print(tree)

if __name__ == '__main__':
    parser = LeidenParser()
    text = "1. abc[def]ghi"
    parser.parse(text)