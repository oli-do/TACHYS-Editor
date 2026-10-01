import html
import regex
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CustomOptionDropdown(QPushButton):
    """Dropdown button that opens a popup container with further options."""
    valueChanged = Signal()

    def __init__(self, category: str, parent=None):
        super().__init__("Options ▾", parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.popup = QFrame(self, Qt.WindowType.Popup)
        self.popup.setObjectName("optionsPopup")
        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setSpacing(6)
        popup_layout.setContentsMargins(10, 10, 10, 10)
        self.chk_uncertain = QCheckBox("Uncertain (?)")
        self.custom_input = QLineEdit()
        if category == 'Editorial Correction':
            self.custom_input.setPlaceholderText("Editor / Source")
        elif category == 'Orthographic Regularization':
            self.custom_input.setPlaceholderText("Language")
        else:
            self.custom_input.setVisible(False)
        popup_layout.addWidget(self.chk_uncertain)
        popup_layout.addWidget(self.custom_input)
        self.chk_uncertain.stateChanged.connect(self._on_internal_change)
        self.custom_input.textChanged.connect(self._on_internal_change)
        self.clicked.connect(self.toggle_popup)

    def toggle_popup(self):
        if self.popup.isVisible():
            self.popup.hide()
        else:
            pos = self.mapToGlobal(self.rect().bottomLeft())
            self.popup.move(pos)
            self.popup.setMinimumWidth(max(self.width(), 180))
            self.popup.show()

    def get_value(self) -> str:
        parts = []
        if self.chk_uncertain.isChecked():
            parts.append('(?)')
        custom_text = self.custom_input.text().strip()
        if custom_text:
            parts.append('=' + custom_text)
        return " ".join(parts)

    def _on_internal_change(self):
        val = self.get_value()
        self.setText(f"{val} ▾" if val else "Options ▾")
        self.valueChanged.emit()


class ApparatusCreatorDialog(QDialog):
    CATEGORIES = {
        "Orthographic Regularization": {
            "tag": "reg",
            "desc": "Used for syntax corrections as well as non-classical or phonetical spellings.",
            "left_placeholder": "Regularization",
            "right_placeholder": "Original Text",
            "expandable_side": "left",
        },
        "Editorial Correction": {
            "tag": "ed",
            "desc": "Used when readings from previous editions are corrected in the current edition.",
            "left_placeholder": "Preferred Editorial Reading",
            "right_placeholder": "Corrected Editorial Reading",
            "expandable_side": "right",
        },
        "Alternate Reading": {
            "tag": "alt",
            "desc": "Used when multiple readings are proposed by the current edition.",
            "left_placeholder": "Preferred Reading",
            "right_placeholder": "Alternative Reading",
            "expandable_side": "right",
        },
        "Scribal Correction": {
            "tag": "subst",
            "desc": "Used when text has been corrected in-line by a scribe.",
            "left_placeholder": "Scribal Correction",
            "right_placeholder": "Original Reading",
            "expandable_side": None,
        },
        "Spelling Correction": {
            "tag": "corr",
            "desc": "Used when the scribe misspelled a word. (Use Regularization for phonetical causes).",
            "left_placeholder": "Corrected Spelling",
            "right_placeholder": "Scribal Error",
            "expandable_side": None,
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apparatus Creator")
        self.resize(680, 520)
        self.setMinimumWidth(580)
        self.left_inputs: list[tuple[QLineEdit, CustomOptionDropdown]] = []
        self.right_inputs: list[tuple[QLineEdit, CustomOptionDropdown]] = []
        self.left_ph: str = ""
        self.right_ph: str = ""
        self.category: str = ""
        self._init_ui()
        self._apply_styles()
        self.on_category_changed(self.combo_apparatus.currentText())

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # category
        form_group = QGroupBox("Apparatus Configuration")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)
        self.combo_apparatus = QComboBox()
        self.combo_apparatus.addItems(list(self.CATEGORIES.keys()))
        self.combo_apparatus.currentTextChanged.connect(self.on_category_changed)
        self.category_description = QLabel()
        self.category_description.setWordWrap(True)
        self.category_description.setStyleSheet("color: #666666; font-style: italic;")

        # Containers for dynamic rows
        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(6)
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(6)

        # Buttons
        self.add_left_btn = QPushButton("+ Add")
        self.add_left_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_left_btn.clicked.connect(self.on_add_left_clicked)
        self.add_right_btn = QPushButton("+ Add")
        self.add_right_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_right_btn.clicked.connect(self.on_add_right_clicked)
        left_box = QVBoxLayout()
        left_box.setSpacing(6)
        left_box.addWidget(self.left_container)
        left_box.addWidget(self.add_left_btn)
        right_box = QVBoxLayout()
        right_box.setSpacing(6)
        right_box.addWidget(self.right_container)
        right_box.addWidget(self.add_right_btn)
        form_layout.addRow("Category:", self.combo_apparatus)
        form_layout.addRow("Description:", self.category_description)
        form_layout.addRow("Left Side:", left_box)
        form_layout.addRow("Right Side:", right_box)
        main_layout.addWidget(form_group)

        # Leiden+ Preview
        preview_group = QGroupBox("Leiden+ Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(12, 16, 12, 16)
        self.lp_label = QLabel("<:|reg|:>")
        self.lp_label.setObjectName("previewLabel")
        self.lp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lp_label.setWordWrap(True)
        mono_font = QFont("IFAO-Grec Unicode")
        mono_font.setPointSize(16)
        self.lp_label.setFont(mono_font)
        preview_layout.addWidget(self.lp_label)
        main_layout.addWidget(preview_group)

        # Dialog Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Insert")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        main_layout.addWidget(button_box)

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 12px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 4px;
                color: #333333;
            }
            QLineEdit, QComboBox, QPushButton {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 6px 10px;
                background-color: #FFFFFF;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #0066CC;
            }
            QFrame#optionsPopup {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
            }
            QLabel#previewLabel {
                background-color: #2B2B2B;
                color: #A9B7C6;
                border-radius: 6px;
                padding: 12px;
            }
            QPushButton#removeBtn {
                background-color: #FFF0F0;
                color: #CC0000;
                border: 1px solid #FFCCCC;
                border-radius: 4px;
                font-weight: bold;
                padding: 4px 8px;
            }
            QPushButton#removeBtn:hover {
                background-color: #FFCCCC;
            }
        """)

    def _clear_layout(
        self, layout: QVBoxLayout, target_list: list[tuple[QLineEdit, CustomOptionDropdown]]
    ):
        """Clear all child widgets from a layout and reset its tracking list."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        target_list.clear()

    def add_reading_field(
        self,
        side: str,
        placeholder: str = "",
        removable: bool = False,
    ):
        """Add a QLineEdit + CustomOptionDropdown row."""
        layout = self.left_layout if side == "left" else self.right_layout
        target_list = self.left_inputs if side == "left" else self.right_inputs
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.textChanged.connect(self.update_preview)
        options_dropdown = CustomOptionDropdown(self.category)
        options_dropdown.valueChanged.connect(self.update_preview)
        row_layout.addWidget(line_edit, stretch=3)
        row_layout.addWidget(options_dropdown, stretch=1)
        item_tuple = (line_edit, options_dropdown)
        target_list.append(item_tuple)
        if removable:
            remove_btn = QPushButton("✕")
            remove_btn.setObjectName("removeBtn")
            remove_btn.setToolTip("Remove")
            remove_btn.setFixedWidth(28)
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            def remove_row():
                target_list.remove(item_tuple)
                row_widget.deleteLater()
                self.update_preview()

            remove_btn.clicked.connect(remove_row)
            row_layout.addWidget(remove_btn)

        layout.addWidget(row_widget)
        self.update_preview()

    def on_category_changed(self, category_name: str):
        self.category = category_name
        data = self.CATEGORIES.get(category_name)
        if not data:
            return
        self.category_description.setText(data["desc"])
        self._clear_layout(self.left_layout, self.left_inputs)
        self._clear_layout(self.right_layout, self.right_inputs)
        self.left_ph = data.get("left_placeholder", "Left Reading")
        self.add_reading_field("left", placeholder=self.left_ph)
        self.right_ph = data.get("right_placeholder", "Right Reading")
        self.add_reading_field("right", placeholder=self.right_ph)
        expandable_side = data.get("expandable_side")
        self.add_left_btn.setVisible(expandable_side == "left")
        self.add_right_btn.setVisible(expandable_side == "right")

    def on_add_left_clicked(self):
        count = len(self.left_inputs) + 1
        self.add_reading_field("left", placeholder=f"{self.left_ph} {count}", removable=True)

    def on_add_right_clicked(self):
        count = len(self.right_inputs) + 1
        self.add_reading_field("right", placeholder=f"{self.right_ph} {count}", removable=True)

    def _format_span(self, text: str, color: str) -> str:
        escaped_text = html.escape(text)
        return f'<span style="color: {color};">{escaped_text}</span>'

    def _get_row_preview_html(self, line_edit: QLineEdit, options_dropdown: CustomOptionDropdown) -> str:
        raw_text = line_edit.text().strip()
        mod = options_dropdown.get_value()
        if not raw_text:
            return ""
        text_color = QColor("green").lighter(300).name()
        mod_color = QColor("cyan").name()
        uncertain_color = QColor("purple").lighter(200).name()

        text_html = self._format_span(raw_text, text_color)
        if mod:
            mod_html = regex.sub(r'(\(\?\))', self._format_span(r'\1', uncertain_color), mod)
            mod_html = regex.sub(r'(\=[ \-.:,()\p{L}0-9]+)', self._format_span(r'\1', mod_color), mod_html)
            return f"{text_html}{mod_html}"
        return text_html

    def update_preview(self):
        category_name = self.combo_apparatus.currentText()
        data = self.CATEGORIES.get(category_name, {})
        tag = data.get("tag", "reg")

        left_vals = [self._get_row_preview_html(le, dd) for le, dd in self.left_inputs if le.text().strip()]
        right_vals = [self._get_row_preview_html(le, dd) for le, dd in self.right_inputs if le.text().strip()]

        purple_color = QColor("purple").lighter(300).name()
        left_text = f"{self._format_span('|', purple_color)}".join(left_vals)
        right_text = f"{self._format_span('|', purple_color)}".join(right_vals)

        if len(self.left_inputs) > 1 or len(self.right_inputs) > 1:
            content = f"{left_text}{self._format_span(f'||{tag}||', purple_color)}{right_text}"
        else:
            content = f"{left_text}{self._format_span(f'|{tag}|', purple_color)}{right_text}"

        self.lp_label.setText(
            f"{self._format_span('<:', purple_color)}{content}{self._format_span(':>', purple_color)}"
        )

    def get_raw_text(self):
        formatted_text = self.lp_label.text()
        text = regex.sub(r'<.*?>', '', formatted_text)
        return html.unescape(text)