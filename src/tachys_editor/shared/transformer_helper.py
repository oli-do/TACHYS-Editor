from lxml import etree
from importlib.resources import files
from pathlib import Path

schema_path = str(files('tachys_editor.resources').joinpath('tei-epidoc.rng'))
schema = etree.parse(schema_path)
rng = etree.RelaxNG(schema)


class EssentialAttributeMissingException(Exception):
    """
    Exception raised when a core attribute which is essential for the conversion to Leiden+ is missing.
    """
    def __init__(self, message):
        super().__init__(message)


def validate_epidoc_tei(xml: str | Path) -> tuple[bool, etree.Element] | tuple[bool, list[str]]:
    """
    Checks if XML is valid EpiDoc TEI.
    :param xml: XML input as str or Path to an XML file
    :return: (True, root element) if the XML is valid; (False, list of errors) if not.
    """
    errors = []
    try:
        if isinstance(xml, Path):
            xml_doc = etree.parse(xml)
        else:
            root = etree.fromstring(xml.encode('utf-8'))
            xml_doc = etree.ElementTree(root)
    except etree.XMLSyntaxError as e:
        line = e.position[0] - 1
        try:
            if isinstance(xml, str):
                errors.append(f'XML Syntax Error in "{xml.splitlines()[line]}": {e}')
            else:
                with open(str(xml), 'r', encoding='utf-8') as f:
                    text = f.read()
                    errors.append(f'XML Syntax Error in "{text.splitlines()[line]}": {e}')
        except IndexError:
            errors.append(f'XML Syntax Error: {e}')
        return False, errors
    if rng.validate(xml_doc) is not None:
        return True, xml_doc.getroot()
    else:
        for error in rng.error_log:
            errors.append(f'Invalid EpiDoc XML: {error.message}')
        return False, errors


def inner_xml(start: str, children: list[str], end: str):
    children = list(filter(None, children))
    xml = start + ''.join(children) + end
    return xml


def lem_rdg(children, tag: str):
    items = ''.join(children[0])
    certainty = children[1]
    resp = children[2]
    if not certainty:
        certainty = ''
    if resp:
        resp = f' resp="{resp}"'
    else:
        resp = ''
    return f'<{tag}{resp}>{items}{certainty}</{tag}>'