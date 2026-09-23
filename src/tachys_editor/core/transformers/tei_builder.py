from bs4 import BeautifulSoup
from tachys_editor.shared.transformer_helper import inner_xml

class TEIBuilder:
    default_tei_header = """<teiHeader>
        <fileDesc>
            <titleStmt>
                <title></title>
            </titleStmt>
            <publicationStmt>
                <authority>TACHYS Editor</authority>
            </publicationStmt>
            <sourceDesc>
                <msDesc>
                    <msIdentifier>
                    </msIdentifier>
                </msDesc>
            </sourceDesc>
        </fileDesc>
    </teiHeader>"""

    intro = """<?xml version="1.0" encoding="UTF-8"?>
<?xml-model href="https://epidoc.stoa.org/schema/8.23/tei-epidoc.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>"""

    commentary = """<div type="commentary" subtype="frontmatter" xml:space="preserve">
                        <p>
                            This text has been digitally edited with TACHYS Editor.
                        </p>
</div>"""

    def build_placeholder(self, inner_body: str):
        body = inner_xml('<body>', [inner_body], '</body>')
        text = inner_xml('<text>', [body], '</text>')
        tei = inner_xml(f'{self.intro}\n<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="en">', [self.commentary, self.default_tei_header, text], '</TEI>')
        return tei

    def build_from_origin(self, inner_body: str, xml_origin: str):
        soup = BeautifulSoup(open(xml_origin, 'r', encoding='utf-8'), 'lxml-xml')
        body = soup.find('body')
        new_body = inner_xml('<body>', [inner_body], '</body>')
        if body:
            body.replace_with(BeautifulSoup(new_body, 'lxml-xml'))
            return str(soup)
        else:
            return self.build_placeholder(inner_body)