import unittest
import unicodedata

from src.tachys_editor.core.parser import TachysParser

parser = TachysParser()
parser.set_print_debug_info(True)
div_start = '<S=.grc\n<D=.1.fragment<=\n'
div_end = '\n=>=D>'


def insert(leiden_text: str):
    return div_start + leiden_text + div_end


def parser_test(text: str):
    parser.parse_full(text)
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
                     insert('1. ||interlin: ῷ( ῾)ν||'),
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
                     insert('1. .2-3lin')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_vestiges(self):
        test_list = [insert('1. vestig.15lin'),
                     insert('1. vestig.2-3lin'),
                     insert('1. vestig.ca.3lin'),
                     insert('1. vestig.?lin'),
                     insert('1. vestig.?'),
                     insert('1. vestig.14'),
                     insert('1. vestig.ca.3'),
                     insert('1. vestig.15-30')]
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
                     insert('1. ((ἔτους?))'),
                     insert('1. ((ἔτ ))')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_abbreviation(self):
        test_list = [insert('1. (|ομυο|)'),
                     insert('1. (|[.8]χυρι̣ο|)'),
                     insert('1. (|λ(?)|)')]  #
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
        test_list = [insert('1. <#ιϛ=16#>'),
                     insert('1. <#ιϛ=1/16#>'),
                     insert("1. <#λβ '=1/32#>"),
                     insert("1. <#σ̣ν̣ϛ̣ '=1/256#>"),
                     insert('1. <#.2=#>'),
                     insert('1. <#=4#>'),
                     insert('1. <#=1/8#>'),
                     insert('1. <#ι[ε(?)]=15#>'), ]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_diacriticals(self):
        test_list = [insert('1. υ ἱ(¨)οῦ'),
                     insert('1.  ὧ( ῾)'),
                     insert('1.  ὃ(´)'),
                     insert('1.  ὑ(^)'),
                     insert('1.  Ἀ( ᾿)'),
                     insert('1.  ἵ( ῾´)'),
                     insert('1.  .1(¨)'),
                     insert('1.  [.1](´)')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_special_characters(self):
        test_list = [insert('1. \n----\n2. '),
                     insert('1. \n--------\n2. '),
                     insert('1. \n~~~~~~~~\n2. '),
                     insert('1. \n>---\n2. '),
                     insert('1. \n-$$-\n2. '),
                     insert('1. *slanting-stroke*'),
                     insert('1. *check?*'),
                     insert('1. *chirho*'),
                     insert('1. *filler(extension)*'),
                     insert('1. *filler(extension)?*'),
                     insert('1. *s-etous*'),
                     insert('1. *parens-punctuation-opening* *parens-punctuation-closing*'),
                     insert('1. #seal ')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_non_default_language(self):
        test_list = [insert('1. ~|γενήσεται|~grc'),
                     insert('1. ~|comes|~la')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_omitted_language(self):
        test_list = [insert('1. (Lang: Demotic 1 lines)'),
                     insert('1. (Lang: Coptic ? lines)'),
                     insert('1. (Lang: Demotic 2 char)'),
                     insert('1. (Lang: Demotic ? char)')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_untranscribed(self):
        test_list = [insert('1. (Lines: 19 non transcribed)'),
                     insert('1. (Lines: ? non transcribed)'),
                     insert('1. (Lines: 1-3 non transcribed)'),
                     insert('1. (Lines: ca.7 non transcribed)'),
                     insert('1. (Chars: ? non transcribed)'),
                     insert('1. (Chars: 1 non transcribed)'),
                     insert('1. (Chars: 1-2 non transcribed)'),
                     insert('1. (Chars: ca.18 non transcribed)')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_common_issues(self):
        test_list = [insert('1. .3[.4]'),
                     insert('1. [.?]<:[ὤλεσ]ε̣ν̣|ed|.3[.0-1]η̣ν=Baplu:> ἀ̣λ̣κή·'),
                     insert('1. β̣̄'),
                     insert('1.  ι̣(¨)')]
        for test in test_list:
            self.assertFalse(parser_test(test))

    def test_dclp_63087(self):
        test = '''<S=.grc
<D=.r
<D=.i.column<=
1. [.?]ε̣ρ̣ λιξ
2. [.?]ρ.1 μων
3. [.?]ερ λοις
4. [.?]υ [.0-1]υς
5. [.?] τρων
6. [.?] τα
=>=D>
<D=.ii.column<=
1. Κη φεύς
2. κισ σός
3. Κό δρος
4. κύ κνος
5. κω [.?]
=>=D>
=D>
<D=.v<=
1. τρὶς <:λύσιος|alt|λυστος:> ἔτι ἢ λυθεν[.?]
=>=D>'''
        test = unicodedata.normalize('NFC', test)
        self.assertFalse(parser_test(test))

    def test_dclp_61605(self):
        test = '''<S=.grc
<D=.1.column.#FR15021<=
1. lost.?lin 
1. [.?] [κα]τ̣ὰ π̣έ̣λ̣[λας]
2. [.?] [ἄγγε]α δεύει̣
3. [.?] [οὐδέ] ποτε Ζεὺς
4. [.?] [φα]εινώ
5. [.?] [φράζετο] θ̣υμῶι
6. [.?] [ὁμοίωσις <#[.2]=#>]
7. [.?] [βεβ]ήκει
8. [.?] [κε]ρ̣α̣ΐζ̣ων
9. [.?]<:[ὤλεσ]ε̣ν̣|ed|.3[.0-1]η̣ν=Baplu:> ἀ̣λ̣κή· 
10. [.?] [με]μ̣αώς.
11. [.?] [ἆλτο] χ̣αμᾶζε.
12. [.?] [δηρινθ]ή̣την
13. [.?] [ἐλ]άφοιο
14. [.?] [μά]χεσθον·
15. [.?] [μήστωρες] ἀ̣ϋτῆς
16. [.?] [φαίδι]μος Ἕκτωρ
17. [.?] [νηλέϊ χ]α̣λκῶι
18. [.?] [οὐχ]ὶ μεθίει·
19. [.?] [οἱ δ]ὲ δὴ ἄλλοι
20. [.?] [κρατερὴν] ὑσμίνην
21. [.?] [ἀλλ]ή̣λοισιν
22. [.?] [πελεμιζέμ]εν ὕλην
23. [.?] [κρ]άνειαν
24. [.?] [τανυήκεα]ς ὄζους
25. [.?] [ἀγνυμ]ε̣νάων
26. [.?] [θορό]ντες
=>=D>
<D=.2.column.#FR15021<=
1. lost.?lin
1. [Ἕκτω]ρ̣ δ’ [ὡς εἶδεν]
2. [ἂψ ἀν]αχ̣α[ζόμενον]
3. ἀ̣γ̣χ̣ί̣μολόν [ῥά οἱ ἦλθε]
4. νείατον εἰς κεν̣[εῶνα]
5. δούπησεν δὲ π̣[εσών]
-$$-
6. ὡς δ’ ὅτε σῦν ἀκ̣[άμαντα]
7. ὥι τ’ ὄρεος κορυφ̣[ῆισι]
8. πίδακος ἀμφ’ ὀλί̣[γης]
9. π̣ολ̣[λ]ὰ δέ τ̣’ ἀ̣σθ[μαίνοντα]
10. ὣ{ς} πολέας̣ [π]εφ̣ν̣[όντα]
11. [Ἕκ]τωρ Π̣ρ[ια]μ̣ίδ̣[ης]
12. [κα]ί οἱ ἐπευχόμε[νος]
13. ὁμοίωσι̣ς̣ [<#[.2]=#>]
14. οὐδ’ ἔλαθ’ Ἀτρέος υ[ἱὸν]
15. [Π]ά̣τροκλος Τρώ[εσσι]
16. β̣ῆ δὲ διὰ προμάχ̣[ων]
-$$-
17. ||left:*diple*|| ἀμφὶ δ’ ἄρ̣’ αὐτῶι βαῖν̣’ [ὥς τις]
18. πρωτοτόκος κι̣ν̣[υρή]
19. ὣς 〚κ〛\π/ερὶ Πατρόκλω̣[ι βαῖνε]
20. πρόσ{σ}θε δέ οἱ <:δόρυ|corr|κόρυ:> [.?]
21. ὁμοίωσ[ις] [<#[.2]=#>]
22. τ̣ὸ̣ν δὲ μέγ’ ὀχθή[σας]
23. Ζεῦ πάτερ, οὐ μὲν κ[αλὸν]
-$$-
24. οὐτ’ οὖν πορδάλιο[ς]
25. οὔτε συὸς κάπρου ὀ [λοόφρονος]
26. θυμὸς ἐνὶ στήθεσσ̣[ι]
27. ὅσσον Πάνθου υἷ̣[ες]
=>=D>'''
        test = unicodedata.normalize('NFC', test)
        self.assertFalse(parser_test(test))

    def test_dclp_60716(self):
        test = '''<S=.grc
<D=.i.column<=
1. lost.?lin 
1. [.?]α̣ι̣
2. [.?].1
3. [.?]ει̣τ
4. [.?].1ε̣
5. [.?].1
6. [.?]σ̣
7. [.?]ωι
8. [.?]ε̣
9. [.?]ο̣η̣[.1]αι
10. [.?]υ̣δαλ̣
11. [.?].1χων
12. [.?]φην̣ο̣
13. [.?].2ι̣ο̣ς
14. [.?].1ο.2
15. [.?].1ε̣.1ο̣ι̣.2ε̣ν̣
16. [.?].1ε̣α̣ν
17. [.?].1[.?].1[.?]
17. lost.?lin
=>=D>
<D=.ii.column<=
18. κ̣αὶ̣ τ̣ὴν ἐπιτ̣ο̣λ̣ὴν .1[.?]
19. τ̣ηρο̣ῦντας αὐτ̣[ο]ὺ̣ς ε.1[.?]
20. .3[.1]την τοῦ γε̣[ί]τ̣ονο̣[ς] [.?]
21. Ἀ̣ρ̣ι̣σ̣τ̣ά̣ρ̣χου δε̣[.1]<:.1ο̣τ̣ε̣υ̣|alt|.1ο̣γ̣ε̣υ̣[.?]:>[.?]
22. φησαν̣τ̣ο̣.1δ̣[.1]ο.1[.2].2[.?]
23. καὶ θεα̣σαμε̣[.?]
24. πολλὰ δεσω[.?]
25. .3[.1].1σμ̣ον.1[.?]
26. μηδεν̣δ̣ε̣δ[.?]
27. μηδὲ διορ̣θω̣[.?]
28. τεπου.2ας ρ.1[.?]
29. τὸ <:κ̣είμ̣ε̣ν̣ο̣\\ν̣/|subst|κ̣είμ̣ε̣ν̣ο̣ς̣:> .1[.?]
30. καὶ̣ <:δύν[α]σθ̣α̣ι̣|alt|δύν[ε]σθ̣α̣ι̣(?):> .1[.?]
31. σαι ἀκού̣ω̣ν ὁ Ἀρ[ίσταρχος (?)] [.?]
----
32. μὲν ο̣ὖ̣ν̣ ἡ̣μῖν̣ λ̣ο̣[.?]
33. σται βιω̣τ̣ι̣κῶν .1[.?]
34. ν̣ασ̣θα̣ι̣ δ̣ι̣ορθ̣ω̣[.?]
35. .4-5<:δι̣.2σκα̣ι̣ει̣.1|alt|δι̣ω̣σκα̣ι̣ει̣.1:>[.?]
36. π̣ρ̣ὸ̣ς̣ τ̣ὸ̣ν̣ βίον <:γ̣ι̣.1|alt|π̣.1:>[.?]
37. λ̣ο̣σ̣α̣.4[.1].4[.?]
38. Ὀ̣δ̣υσσ̣ε̣ῖ̣ κ̣α̣ὶ̣ γ̣ὰρ .2[.?] [κα]
39.- τ̣αβὰς τ̣[ὸ]ν̣ μὲν <:ε̣.1[.?]|ed|Ἐ̣λ̣[πήνορα] [.?]=Coles:>
40. ἄ̣λ̣λ̣ους̣ τ̣ι̣ν̣ὰς καὶ̣ .1[.?]
41. τ̣ο̣ι̣.1[.1] Πλο̣[ύτ]ω̣να .1[.?]
42. [.?].1[.?]
42. lost.?lin
=>=D>'''
        self.assertFalse(parser_test(test))

    def test_dclp_60890(self):
        test = '''<S=.grc
<D=.i.column.#FR15007<= 
1. [μάρτυρ]ο̣ι̣ ὦ̣σ’ ο̣ἳ̣ ἔ̣[ν]ερθε θεοὶ Κρόνον ἀμ̣φὶς ἐ̣[όντες]
2. [ca.5] μ̣οὶ δ ώ(´)σ̣ε̣[ι]ν̣ Χαρίτων μίαν̣ ὁπλ̣οτ̣εράω̣[ν]
3. [ca.8] [ἧ]ς̣ τ’ α̣[ὐτὸ]ς̣ ἐέλδομ̣αι̣ ἤματα πάντα
4. [ca.9] [ἀπί]θ̣η̣[σ]ε θεὰ λ̣ευκώλενος Ἥ̣ρη,
5. [ca.9] [κ]έ̣λ̣[ευ]ε̣ν̣ θεοὺς̣ δ’*apostrophe* ὀν ό(´)μην̣εν ἅπ̣αν̣[τας]
6. [ca.4] [ὑποταρταρίο]υ̣ς̣ ο̣ἳ̣ Τ̣ιτ̣ ῆ(^)νες καλ έ(´)οντ[α]ι.
7. [ca.10] ὄ̣μο̣σ έ(´)ν τ̣ε τελεύτησ έ(´)ν τε τὸν  ὅ(´)ρκο[ν]
8. [τὼ] β̣ή̣[την Λήμ]νου τε καὶ Ἴμβρου ἄσ̣τ̣υ̣ λιπόντε̣
9. [ἠέ]ρα ἑ̣σ̣σ̣α̣[μέ]ν̣ω̣ ῥ ί(´)μφα πρ ή(´)σσοντ̣ε̣ κ̣έ̣λ̣ευθον
10. Ἴδ̣η̣ν̣ δὲ ἱ̣κ̣έσθ̣[η]ν <:<:πολυπίδακα|reg|πολυπεί\\*high-punctus*δ*high-punctus*/ακα:>|subst|πολυπείρακα:> μητέρα θηρ̣ῶ̣ν̣
11. Λ έ(´)κτό̣ν, ὅ̣θι π̣ρ̣ῶτον λιπέτην ἅλα τὼ δ’ [ἐ]πὶ χέ̣ρσο[υ]
12. βήτη̣ν, ἀκροτ̣ ά(´)την̣ τε ποδ ῶ(^)ν ὕπεσείε[το] ὕλη·*high-punctus*
13. ἔνθ’*apostrophe* Ὕπνος μὲν ἔμιμν̣ε̣ π̣ά̣ρος Δ̣ι̣ὸς ὄ̣[σ]σ̣ε ἰδ έ(´)σθα̣[ι]
14. εἰς ἐ̣λ̣ά̣τ̣η̣ν ἀνα̣β ὰ(^)ς π ὲ(`)ριμ ή(´)κετον ἣ̣ τ ό(´)[τ’] [ca.5]
15. μ̣α̣κροτά̣τ̣η π̣ε̣φυ υ(¨)ῖα̣ δ̣ι̣’ ἠ έ(´)ρο̣ς αἰθ έ(´)ρ’ ἵκ̣[ανεν]
16. ἔ̣ν̣θ’*apostrophe*  ἧ(^)στ’*apostrophe*  ὄ(´)ζοισιν <:πεπ̣υ̣\κ/ασμ έ(´)νο̣ς̣|subst|πεπ̣υ̣.1ασμένο̣ς̣:> ε̣ἰ̣λ̣ατ[ίνοισιν]
17. [ὄρν]ι̣θι λιγυρ  ῇ(^) ἐναλ ί(´)γκ̣[ι]ο̣ς \\.3/ ἥν τ’ ἐν ὄρ̣εσσι
18. [χαλ]κ ί(´)δα κικλή[σ]κουσι [θεοί] ἄνδρε̣ς̣ δ̣ὲ̣ κ̣ύμ̣[ινδιν]
19. Ἥρ̣η̣ δὲ κραιπν ῶ(^)ς προσε̣[βήσατο] [ca.13]
20. Ἴδ̣ης ὑψηλῆς·*high-punctus* ἴδε \δὲ/ νεφε̣[ληγερέτα] [ca.4]
21. ὡς δ’ ἴδεν ὥς μιν ἔρω[ς] [ca.13]
22. οἷ̣[ο]ν̣ <: ὅ(´)\\[τ]ε/|subst|ὅθι:> πρ ώ(´)τιστο[ν] [ca.21] 
23. εἰς εὐν ὴ(^)ν φοιτ .1(´).1[ca.21]
24. σ[τῆ] δ’ αὐτῆς̣ π̣ρ̣οπ̣ά̣[ροιθεν] [ca.20]
25. Ἥρη̣ π ῇ(^) μ̣ε̣μ̣α̣[υῖα][ca.21]
26. ἵ̣π̣[ποι] δ̣’ [ca.30] 
27. [τ̣]ὸ̣[ν δὲ] δ̣ολ̣[ο]φ̣ρ̣ο̣[νέουσα] [ca.17] 
28. [ἔρχομ]α̣ι ὀ[ψομένη] [ca.22] 
29. [Ὠκεα]ν̣ ό(´)[ν] [τε] [ca.25] 
=>=D>'''
        self.assertFalse(parser_test(test))
