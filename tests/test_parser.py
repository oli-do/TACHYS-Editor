import unittest

from parser import LeidenParser

parser = LeidenParser()
parser.set_print_debug_info(True)
div_start = '<S=.grc\n<D=.1.fragment<=\n'
div_end = '\n=>=D>'


def insert(leiden_text: str):
    return div_start + leiden_text + div_end


def parser_test(text: str):
    parser.parse(text)
    return parser.errors


class TestParser(unittest.TestCase):
    def test_nested_div(self):
        test = '<S=.grc\n<D=.r\n<D=.1.column<=\n1. α\n2.- β' + div_end + '\n<D=.2.column\n<D=.b.fragment<=\n1. ' + div_end + '\n=D>\n=D>'
        self.assertFalse(parser_test(test))

    def test_div(self):
        test = insert('1. ')
        self.assertFalse(parser_test(test))

    def test_line_position(self):
        test_list = [insert('(2, perpendicular) '),
                     insert('(8, inverse) '),
                     insert('(3.-, inverse) '),
                     insert('(12, outdent) '),
                     insert('3,ms. '), insert('3,md. '),
                     insert('1,msup. '),
                     insert('1,minf. '),
                     insert('(8,ms, perpendicular) '),
                     insert('(16,minf, inverse) ')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_vacat(self):
        test_list = [insert('1. vac.?'),
                     insert('1. vac.3'),
                     insert('1. vac.2-5'),
                     insert('1. vac.ca.3'),
                     insert('1. vac.?lin'),
                     insert('1. vac.3lin'),
                     insert('1. vac.2-5lin'),
                     insert('1. vac.ca.3lin')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_insertions_marginalia(self):
        test_list = [insert('1. \\ὅλων/'),
                     insert('1. //<#δ=4#>\\\\'),
                     insert('1. ||left:καὶ||'),
                     insert('1. ||right:καὶ||'),
                     insert('1. ||interlin: ῷ(῾)ν||'),
                     insert('1. <|ν|>'),
                     insert('1. <_οὒτως ἔχει_>'),
                     insert('1. \\Θέων̣?/')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_special_text_formatting(self):
        test_list = [insert('1. ###'),
                     insert('1. ~||β||~tall'),
                     insert('1. |^Ἡρωνείνῳ^|'),
                     insert('1. \\|τα|/'),
                     insert('1. ¯νο.1¯'),
                     insert('1. ¯_εὐτύχει_¯')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_lines_lost(self):
        test_list = [insert('1. lost.7lin'),
                     insert('1. lost.ca.7lin'),
                     insert('1. lost.3-4lin'),
                     insert('1. lost.?lin'),
                     insert('1. lost.?lin(?)')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_illegible(self):
        test_list = [insert('1. .3'),
                     insert('1. .?'),
                     insert('1. ca.23'),
                     insert('1. .43'),
                     insert('1. .9-10'),
                     insert('1. .5lin'),
                     insert('1. ca.20lin'),
                     insert('1. .2-3lin'),]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_vestiges(self):
        test_list = [insert('1. vestig.15lin'),
                     insert('1. vestig.2-3lin'),
                     insert('1. vestig.ca.3lin'),
                     insert('1. vestig.?lin'),
                     insert('1. vestig'),
                     insert('1. vestig.14char'),
                     insert('1. vestig.ca.3char'),
                     insert('1. vestig.15-30char')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_leiden_conventions(self):
        test_list = [insert('1. <ἀπεγραψάμην>'),
                     insert('1. <οὐκ(?)>'),
                     insert('1. ἀπ<ε>γραψάμην'),
                     insert('1. {ὀνόματος}'),
                     insert('1. ὁμο{μο}λογῶ.'),
                     insert('1. 〚τοῖς κορασίοις〛'),
                     insert('1. 〚/ τραπέζης Φρέμει. 〛'),
                     insert('1. 〚X $m4 lost.?lin 〛')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_expansion(self):
        test_list = [insert('1. (στρατηγ(ός))'),
                     insert('1. (Καρ(ανίδι?))'),
                     insert('1. (Καρ(ανίδ ))'),
                     insert('1. ((ἔτους))'),
                     insert('1. (ἔτους(?))'),
                     insert('1. ((ἔτ ))')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_abbreviation(self):
        test_list = [insert('1. (|ομυο|)'),
                     insert('1. (|[.8]χυρι̣ο|)'),
                     insert('1. (|λ(?)|)')]#
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_lost_characters(self):
        test_list = [insert('1. [.8] or [.43]'),
                     insert('1. [ca.5]'),
                     insert('1. [.11-15]'),
                     insert('1. [.?]'),
                     insert('1. [ὁμο]λογῶ'),
                     insert('1. ἡμετέρ[α μήτηρ (?)] [.?]')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_parallel(self):
        test_list = [insert('1. |_Πόσεις_|'),
                     insert('1. _[αβγ]_')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_handshift(self):
        test_list = [insert('1. $m4'),
                     insert('1. $m3(?) α')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_note(self):
        test = insert('1. /*BGU 1,108,r reprinted in WChr 227*/')
        self.assertFalse(parser_test(test))

    def test_quotation(self):
        test = insert('1. " ὁ γὰ̣ρ̣ ἐ̣λ̣εῶ̣ν̣ [πτωχόν] "')
        self.assertFalse(parser_test(test))

    def test_apparatus(self):
        test_list = [insert('1. <:φρόντι[σ]ον|reg|φρόνδει[σ]ο̣ν:>'),
                     insert('1. <:ἀνοίγεται (?)|ἀνοίεται (?)||reg||ἀ̣νύεται:>'),
                     insert('1. <:Ὀχυρυγχίτου|alt|Ὀξυρυγχίτου νομοῦ:>'),
                     insert('1. <:[.?].1αμεν.1ν̣||alt||[ἀπογρα]ψ̣αμένη̣ν̣|[θρε]ψ̣αμένη̣ν̣:>'),
                     insert('1. <:Ὀχυρυγχίτου(?)|alt|Ὀξυρυγχίτου νομοῦ(?):>'),
                     insert('1. <:τοῦ|subst|της:>'),
                     insert('1. <:τοῦ(?)|subst|της(?):>'),
                     insert('1. <:τιμὴν|corr|τμμὴν:>'),
                     insert('1. <:αἱ τοῦ=BL 9.17|ed|Θίτου:>'),
                     insert('1. <:αἱ τοῦ(?)=BL 9.17|ed|Θίτου:>'),
                     insert('1. <:Ἀντωνίνου=N. Gonis, ZPE 166 (2008) 268|ed|Αὐρηλίου:>'),
                     insert('1. <:<#κγ=23#>=BGU 1 p.357|ed|<#κϛ=26#>:>'),
                     insert('1. <:<#κγ=23#>(?)=bgu 1 p.357|ed|<#κϛ=26#>:>'),
                     insert('1. <:τοῦ=PN W.G. Claytor (CPR VI plate 35)|ed|:>')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_numbers(self):
        #
        #
        test_list = [insert('1. <#ιϛ=16#>'),
                     insert('1. <#ιϛ=1/16#>'),
                     insert("1. <#λβ '=1/32#>"),
                     insert("1. <#σ̣ν̣ϛ̣ '=1/256#>"),
                     insert('1. <#.2=#>'),
                     insert('1. <#=4#>'),
                     insert('1. <#=1/8#>'),
                     insert('1. <#ι[ε(?)]=15#>'),]
        for test in test_list:
            self.assertFalse(parser_test(test))
