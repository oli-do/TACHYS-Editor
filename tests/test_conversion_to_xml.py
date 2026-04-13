import unittest
import unicodedata

from src.tachys_editor.core.parser import TachysParser
from src.tachys_editor.core.transformer import LeidenPlusTransformer

class TestXMLConversion(unittest.TestCase):
    def setUp(self):
        self.parser = TachysParser()
        self.transformer = LeidenPlusTransformer()
        self.maxDiff = None

    def test_dclp_61605(self):
            leiden_input = '''<S=.grc
<D=.1.column.#FR15021<=
1. lost.?lin
1. [.?] [κα]τ̣ὰ π̣έ̣λ̣[λας]
2. [.?] [ἄγγε]α δεύει̣
3. [.?] [οὐδέ] ποτε Ζεὺς
4. [.?] [φα]εινώ
5. [.?] [φράζετο] θ̣υμῶι
6. [.?] [ὁμοίωσις <#[.2]=#>]
7. [.?] [βεβ]ήκει
8. [.?] [κε]ρ̣α̣ΐ̣ζ̣ων
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
25. οὔτε συὸς κάπρου ὀ̣[λοόφρονος]
26. θυμὸς ἐνὶ στήθεσσ̣[ι]
27. ὅσσον Πάνθου υἷ̣[ες]
=>=D>'''
            expected = '''<div xml:lang="grc" type="edition" xml:space="preserve">
<div n="1" subtype="column" type="textpart" corresp="#FR15021"><ab>
<lb n="1"/><gap reason="lost" extent="unknown" unit="line"/>
<lb n="1"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">κα</supplied><unclear>τ</unclear>ὰ <unclear>πέλ</unclear><supplied reason="lost">λας</supplied>
<lb n="2"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">ἄγγε</supplied>α δεύε<unclear>ι</unclear>
<lb n="3"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">οὐδέ</supplied> ποτε Ζεὺς
<lb n="4"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">φα</supplied>εινώ
<lb n="5"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">φράζετο</supplied> <unclear>θ</unclear>υμῶι
<lb n="6"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">ὁμοίωσις <num><gap reason="lost" quantity="2" unit="character"/></num></supplied>
<lb n="7"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">βεβ</supplied>ήκει
<lb n="8"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">κε</supplied><unclear>ραΐζ</unclear>ων
<lb n="9"/><gap reason="lost" extent="unknown" unit="character"/><app type="editorial"><lem><supplied reason="lost">ὤλεσ</supplied><unclear>εν</unclear></lem><rdg resp="Baplu"><gap reason="illegible" quantity="3" unit="character"/><gap reason="lost" atLeast="0" atMost="1" unit="character"/><unclear>η</unclear>ν</rdg></app> <unclear>ἀλ</unclear>κή· 
<lb n="10"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">με</supplied><unclear>μ</unclear>αώς.
<lb n="11"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">ἆλτο</supplied> <unclear>χ</unclear>αμᾶζε.
<lb n="12"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">δηρινθ</supplied><unclear>ή</unclear>την
<lb n="13"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">ἐλ</supplied>άφοιο
<lb n="14"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">μά</supplied>χεσθον·
<lb n="15"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">μήστωρες</supplied> <unclear>ἀ</unclear>ϋτῆς
<lb n="16"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">φαίδι</supplied>μος Ἕκτωρ
<lb n="17"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">νηλέϊ χ</supplied><unclear>α</unclear>λκῶι
<lb n="18"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">οὐχ</supplied>ὶ μεθίει·
<lb n="19"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">οἱ δ</supplied>ὲ δὴ ἄλλοι
<lb n="20"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">κρατερὴν</supplied> ὑσμίνην
<lb n="21"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">ἀλλ</supplied><unclear>ή</unclear>λοισιν
<lb n="22"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">πελεμιζέμ</supplied>εν ὕλην
<lb n="23"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">κρ</supplied>άνειαν
<lb n="24"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">τανυήκεα</supplied>ς ὄζους
<lb n="25"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">ἀγνυμ</supplied><unclear>ε</unclear>νάων
<lb n="26"/><gap reason="lost" extent="unknown" unit="character"/> <supplied reason="lost">θορό</supplied>ντες
</ab></div>
<div n="2" subtype="column" type="textpart" corresp="#FR15021"><ab>
<lb n="1"/><gap reason="lost" extent="unknown" unit="line"/>
<lb n="1"/><supplied reason="lost">Ἕκτω</supplied><unclear>ρ</unclear> δ’ <supplied reason="lost">ὡς εἶδεν</supplied>
<lb n="2"/><supplied reason="lost">ἂψ ἀν</supplied>α<unclear>χ</unclear>α<supplied reason="lost">ζόμενον</supplied>
<lb n="3"/><unclear>ἀγχί</unclear>μολόν<supplied reason="lost"> ῥά οἱ ἦλθε</supplied>
<lb n="4"/>νείατον εἰς κε<unclear>ν</unclear><supplied reason="lost">εῶνα</supplied>
<lb n="5"/>δούπησεν δὲ <unclear>π</unclear><supplied reason="lost">εσών</supplied>
<milestone rend="coronis" unit="undefined"/>
<lb n="6"/>ὡς δ’ ὅτε σῦν ἀ<unclear>κ</unclear><supplied reason="lost">άμαντα</supplied>
<lb n="7"/>ὥι τ’ ὄρεος κορυ<unclear>φ</unclear><supplied reason="lost">ῆισι</supplied>
<lb n="8"/>πίδακος ἀμφ’ ὀλ<unclear>ί</unclear><supplied reason="lost">γης</supplied>
<lb n="9"/><unclear>π</unclear>ο<unclear>λ</unclear><supplied reason="lost">λ</supplied>ὰ δέ <unclear>τ</unclear>’ <unclear>ἀ</unclear>σθ<supplied reason="lost">μαίνοντα</supplied>
<lb n="10"/>ὣ<surplus>ς</surplus> πολέα<unclear>ς</unclear> <supplied reason="lost">π</supplied>ε<unclear>φν</unclear><supplied reason="lost">όντα</supplied>
<lb n="11"/><supplied reason="lost">Ἕκ</supplied>τωρ <unclear>Π</unclear>ρ<supplied reason="lost">ια</supplied><unclear>μ</unclear>ί<unclear>δ</unclear><supplied reason="lost">ης</supplied>
<lb n="12"/><supplied reason="lost">κα</supplied>ί οἱ ἐπευχόμε<supplied reason="lost">νος</supplied>
<lb n="13"/>ὁμοίωσ<unclear>ις</unclear> <supplied reason="lost"><num><gap reason="lost" quantity="2" unit="character"/></num></supplied>
<lb n="14"/>οὐδ’ ἔλαθ’ ᾿Ατρέος υ<supplied reason="lost">ἱὸν</supplied>
<lb n="15"/><supplied reason="lost">Π</supplied><unclear>ά</unclear>τροκλος Τρώ<supplied reason="lost">εσσι</supplied>
<lb n="16"/><unclear>β</unclear>ῆ δὲ διὰ πρoμά<unclear>χ</unclear><supplied reason="lost">ων</supplied>
<milestone rend="coronis" unit="undefined"/>
<lb n="17"/><add place="left"><g type="diple"/></add> ἀμφὶ δ’ ἄ<unclear>ρ</unclear>’ αὐτῶι βαῖ<unclear>ν</unclear>’ <supplied reason="lost">ὥς τις</supplied>
<lb n="18"/>πρωτοτόκος κ<unclear>ιν</unclear><supplied reason="lost">υρή</supplied>
<lb n="19"/>ὣς <del rend="erasure">κ</del><add place="above">π</add>ερὶ Πατρόκλ<unclear>ω</unclear><supplied reason="lost">ι βαῖνε</supplied>
<lb n="20"/>πρόσ<surplus>σ</surplus>θε δέ οἱ <choice><corr>δόρυ</corr><sic>κόρυ</sic></choice> <gap reason="lost" extent="unknown" unit="character"/>
<lb n="21"/>ὁμοίωσ<supplied reason="lost">ις</supplied> <supplied reason="lost"><num><gap reason="lost" quantity="2" unit="character"/></num></supplied>
<lb n="22"/><unclear>τὸ</unclear>ν δὲ μέγ’ ὀχθή<supplied reason="lost">σας</supplied>
<lb n="23"/>Ζεῦ πάτερ, οὐ μὲν κ<supplied reason="lost">αλὸν</supplied>
<milestone rend="coronis" unit="undefined"/>
<lb n="24"/>οὐτ’ οὖν πορδάλιο<supplied reason="lost">ς</supplied>
<lb n="25"/>οὔτε συὸς κάπρου <unclear>ὀ</unclear><supplied reason="lost">λοόφρονος</supplied>
<lb n="26"/>θυμὸς ἐνὶ στήθεσ<unclear>σ</unclear><supplied reason="lost">ι</supplied>
<lb n="27"/>ὅσσον Πάνθου υ<unclear>ἷ</unclear><supplied reason="lost">ες</supplied>
</ab></div>
</div>'''
            leiden_input = unicodedata.normalize('NFC', leiden_input)
            expected = unicodedata.normalize('NFC', expected)
            tree = self.parser.parse_full(leiden_input)
            xml = self.transformer.transform(tree)
            xml = unicodedata.normalize('NFC', xml)
            self.assertEqual(xml, expected)