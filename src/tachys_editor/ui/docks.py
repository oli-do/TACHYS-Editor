from PySide6.QtCore import Qt, Slot
from .editor import TachysEditor
from PySide6.QtWidgets import QDockWidget, QListWidget, QListWidgetItem, QWidget, QVBoxLayout
from typing import Literal


class BottomDock(QDockWidget):
    def __init__(self, editor: TachysEditor):
        super().__init__()
        self.editor = editor
        self.setWindowTitle('Checking for syntax problems...')
        self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.list_widget = QListWidget(self)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.has_active_problems = True
        container = QWidget(self)
        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        container.setLayout(layout)
        self.setWidget(container)

    def add_problem(self, symbol: Literal['⛔', '⚠️', '🚫'],  line: int, description: str):
        text = f'{symbol} {description} :{line + 1}'
        list_widget_item = QListWidgetItem(text)
        list_widget_item.setData(Qt.ItemDataRole.UserRole, line)
        self.list_widget.addItem(list_widget_item)

    def on_item_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.editor.navigate_to_line(data)

    def reset(self):
        self.setWindowTitle('Checking for syntax problems...')
        self.list_widget.clear()
        self.has_active_problems = True

    @Slot(list)
    def on_problems_received(self, problems: list[tuple[int, int, int, str, str]]):
        self.setWindowTitle(f'Problems ({len(problems)})')
        if problems:
            self.list_widget.clear()
            self.has_active_problems = True
            if not self.isVisible():
                self.show()
        else:
            if self.has_active_problems:
                if not self.isVisible():
                    self.show()
                self.list_widget.clear()
                self.list_widget.addItem(QListWidgetItem('✅ Found no problems.'))
                self.has_active_problems = False
        for problem in problems:
            problem_id = problem[0]
            line = problem[1]
            symbol: Literal['⛔', '⚠️', '🚫']
            if problem_id == 0:
                char = problem[3]
                desc = f'Unexpected Characters. One or more characters are not allowed here, including "{char}"'
                symbol = '🚫'
            elif problem_id == 1:
                desc = ' Unexpected Expression. A Leiden+ expression is not allowed here'
                symbol = '⛔'
            elif problem_id == 2:
                desc = 'Incomplete Syntax. Check for any unclosed expressions or a missing space character'
                symbol = '⚠️'
            elif problem_id == 3:
                desc = f'Incorrect XML. Make sure to follow the EpiDoc guidelines.'
                symbol = '⛔'
            else:
                text = problem[4].replace('\n', ' ')
                desc = f'Unexpected Error. {text}'
                symbol = '⛔'
            self.add_problem(symbol, line, desc)


