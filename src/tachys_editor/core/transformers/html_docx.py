import docx.text.paragraph
from docx import Document
from docx.shared import Pt, Cm, Length
from tachys_editor.shared.settings import __version__
from bs4 import BeautifulSoup
from bs4.element import Tag
from pathlib import Path
from PySide6.QtWidgets import QMessageBox


class HTML2Docx:
    def __init__(self, parent=None):
        self.doc = Document()
        self.parent = parent

    @staticmethod
    def format_paragraph(node: Tag, paragraph: docx.text.paragraph.Paragraph):
        for content in node.contents:
            text = content.get_text().replace('\n', '')
            run = paragraph.add_run(text)
            if isinstance(content, Tag):
                if content.name == 'i':
                    run.font.italic = True
                elif content.name == 'b':
                    run.font.bold = True


    def convert(self, html: Path | str, output_path: str):
        self.doc = Document()
        section = self.doc.sections[0]
        usable_width = Length(section.page_width - section.left_margin - section.right_margin)
        if isinstance(html, Path):
            soup = BeautifulSoup(open(html, encoding='utf-8'), 'html.parser')
        else:
            soup = BeautifulSoup(html, 'html.parser')
        style = self.doc.styles['Normal']
        font = style.font
        font.name = 'IFAO-Grec Unicode'
        font.size = Pt(11)
        self.doc.add_paragraph(f'This document has been created with TACHYS Editor v{__version__}.\n')
        text_parts = soup.find_all('div', attrs={'class': 'textpart'})
        if not text_parts:
            text_parts = soup.find_all('table')
        for text_part in text_parts:
            text_part_name = text_part.find_next('h3', attrs={'class': 'textpart'})
            if text_part_name:
                self.doc.add_heading(text_part_name.get_text(strip=True), 1)
            if not text_part.name == 'table':
                table = text_part.find_next('table')
            else:
                table = text_part
            trs = table.find_all('tr')
            num_rows = len(trs)
            num_cells = (max([len(row.find_all('td')) for row in trs]))
            docx_table = self.doc.add_table(num_rows, num_cells)
            docx_table.autofit = False
            for i in range(len(trs)):
                cells = docx_table.rows[i].cells
                tds = trs[i].find_all('td')
                for j in range(len(tds)):
                    paragraph = cells[j].paragraphs[0]
                    self.format_paragraph(tds[j], paragraph)
                    td_classes = tds[j].get('class')
                    if td_classes:
                        if 'lb' in td_classes:
                            cells[j].width = Cm(1.5)
                    else:
                        cells[j].width = Cm(usable_width.cm - 1.5)
                    for paragraph in cells[j].paragraphs:
                        paragraph.paragraph_format.space_before = Pt(0)
                        paragraph.paragraph_format.space_after = Pt(0)
            apparatus = text_part.find_next('p', attrs={'class': 'apparatus'})
            if apparatus:
                app_paragraph = self.doc.add_paragraph()
                run = app_paragraph.add_run('\n\n\n\n' + apparatus.get_text(strip=True))
                run.font.size = Pt(9)

        try:
            self.doc.save(output_path)
            QMessageBox.information(self.parent, 'Success', f'Successfully wrote {output_path}.')
        except PermissionError:
            QMessageBox.warning(self.parent, 'Permission Error', 'Permission Denied. Make sure the .docx file '
                                                                 'you are writing is not opened.')
