from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget,
    QVBoxLayout, QFormLayout, QCheckBox, QComboBox, QScrollArea,
    QSpinBox, QDialogButtonBox, QLabel, QKeySequenceEdit, QMessageBox, QStyleFactory
)
from ..shared.settings import settings_mgr, font_families
from dataclasses import fields

class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.resize(600, 500)
        self.registered_elements = []
        self.restart_required = False
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_general_tab(), "General")
        self.tabs.addTab(self._create_appearance_tab(), "Appearance")
        self.tabs.addTab(self._create_editor_tab(), "Editor")
        main_layout.addWidget(self.tabs)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Reset
        )
        self.button_box.accepted.connect(self.accept_settings)
        self.button_box.rejected.connect(self.reject)
        reset_button = self.button_box.button(QDialogButtonBox.StandardButton.Reset)
        reset_button.clicked.connect(self.reset)
        main_layout.addWidget(self.button_box)

    def _create_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QFormLayout(tab)

        self.autosave_check = QCheckBox("Enable auto-save on exit")
        self.autosave_check.setChecked(settings_mgr.general.auto_save_on_exit)
        self.register(self.autosave_check, settings_mgr.general, 'auto_save_on_exit')

        layout.addRow("Auto-Save:", self.autosave_check)
        return tab

    def _create_appearance_tab(self) -> QWidget:
        tab = QWidget()
        layout = QFormLayout(tab)

        self.window_style_combo = QComboBox()
        self.window_style_combo.addItems(QStyleFactory.keys())
        self.window_style_combo.setCurrentText(settings_mgr.appearance.window_style)
        self.window_style_combo.currentTextChanged.connect(self.set_restart_required_true)
        self.register(self.window_style_combo, settings_mgr.appearance, 'window_style')

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Auto', 'Light', 'Dark'])
        self.theme_combo.setCurrentText(settings_mgr.appearance.theme)
        self.theme_combo.currentTextChanged.connect(self.set_restart_required_true)
        self.register(self.theme_combo, settings_mgr.appearance, 'theme')

        self.ui_font_size_spin = QSpinBox()
        self.ui_font_size_spin.setValue(settings_mgr.appearance.ui_font_size)
        self.ui_font_size_spin.setRange(8, 18)
        self.ui_font_size_spin.valueChanged.connect(self.set_restart_required_true)
        self.register(self.ui_font_size_spin, settings_mgr.appearance, 'ui_font_size')

        layout.addRow("Window Style:", self.window_style_combo)
        layout.addRow("Theme:", self.theme_combo)
        layout.addRow("UI Font Size:", self.ui_font_size_spin)
        return tab

    def _create_editor_tab(self) -> QWidget:
        tab = QWidget()
        layout = QFormLayout(tab)

        self.font_combo = QComboBox()
        self.font_combo.addItems(list(font_families))
        self.font_combo.setCurrentText(settings_mgr.editor.font)
        self.font_combo.currentTextChanged.connect(self.set_restart_required_true)
        self.register(self.font_combo, settings_mgr.editor, 'font')

        self.default_language_combo = QComboBox()
        self.default_language_combo.addItems(['grc', 'la', 'cop', 'ar', 'egy-Egyd', 'grc-Latn', 'la-Grek', 'cop-Grek'])
        self.default_language_combo.setCurrentText(settings_mgr.editor.default_language)
        self.register(self.default_language_combo, settings_mgr.editor, 'default_language')

        self.debug_delay_spin = QSpinBox()
        self.debug_delay_spin.setRange(100, 1000)
        self.debug_delay_spin.setValue(settings_mgr.editor.debug_delay)
        self.debug_delay_spin.setSuffix(' ms')
        self.debug_delay_spin.setToolTip('How long the debugger is delayed after the user has stopped typing.')
        self.register(self.debug_delay_spin, settings_mgr.editor, 'debug_delay')

        scroll_shortcuts = QScrollArea()
        scroll_shortcuts.setWidgetResizable(True)
        container_widget = QWidget()
        scroll_shortcuts_layout = QFormLayout(container_widget)
        for f in fields(settings_mgr.editor.shortcuts):
            name = f.name
            display_name = name.replace('_', ' ')
            display_name = display_name.title()
            label = QLabel(display_name)
            sequence_edit = QKeySequenceEdit()
            sequence_edit.setKeySequence(getattr(settings_mgr.editor.shortcuts, f.name))
            sequence_edit.keySequenceChanged.connect(self.set_restart_required_true)
            self.register(sequence_edit, settings_mgr.editor.shortcuts, f.name)
            scroll_shortcuts_layout.addRow(label, sequence_edit)
        scroll_shortcuts.setWidget(container_widget)

        layout.addRow('Font:', self.font_combo)
        layout.addRow('Default Language:', self.default_language_combo)
        layout.addRow("Debug Delay:", self.debug_delay_spin)
        layout.addRow('Shortcuts:', scroll_shortcuts)
        return tab

    def set_restart_required_true(self):
        if not self.restart_required:
            self.restart_required = True

    def register(self, ui_element, target, attribute: str):
        self.registered_elements.append((ui_element, target, attribute))

    def save_settings(self):
        """Write current UI state to persistent storage."""
        for element in self.registered_elements:
            ui_element, target, attr = element
            if isinstance(ui_element, QSpinBox):
                setattr(target, attr, ui_element.value())
            elif isinstance(ui_element, QComboBox):
                setattr(target, attr, ui_element.currentText())
            elif isinstance(ui_element, QCheckBox):
                setattr(target, attr, ui_element.isChecked())
            elif isinstance(ui_element, QKeySequenceEdit):
                setattr(target, attr, ui_element.keySequence().toString())
            else:
                print(f'{type(ui_element)} is not yet supported.')
        settings_mgr.write_settings()
        if self.restart_required:
            QMessageBox().information(self, "Application Restart Required",
                                    "A restart may be required to apply some settings.")

    def update_ui_values(self):
        for element in self.registered_elements:
            ui_element, target, attr = element
            if isinstance(ui_element, QSpinBox):
                ui_element.setValue(getattr(target, attr))
            elif isinstance(ui_element, QComboBox):
                ui_element.setCurrentText(getattr(target, attr))
            elif isinstance(ui_element, QCheckBox):
                ui_element.setChecked(getattr(target, attr))
            elif isinstance(ui_element, QKeySequenceEdit):
                ui_element.setKeySequence(getattr(target, attr))
            else:
                print(f'update_ui_values: {type(ui_element)} is not yet supported.')

    def reset(self):
        settings_mgr.reset_user_settings()
        settings_mgr.write_settings()
        self.update_ui_values()

    def accept_settings(self):
        """Called when pressing 'OK'."""
        self.save_settings()
        self.accept()