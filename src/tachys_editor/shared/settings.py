import json
import os
from dataclasses import dataclass, asdict, field, fields, is_dataclass
from tkinter import Tk, font
from appdirs import user_data_dir
from PySide6.QtWidgets import QApplication

app_name = 'TACHYS Editor'
app_author = 'Oliver Donath'
data_dir = user_data_dir(appname=app_name, appauthor=app_author)
tracking_dir = os.path.join(data_dir, 'changes')
config_file_path = os.path.join(data_dir, 'config.json')
root = Tk()
root.withdraw()
font_families = font.families()
if 'IFAO-Grec Unicode' in font_families:
    default_font: str = 'IFAO-Grec Unicode'
elif 'Brill' in font_families:
    default_font: str = 'Brill'
elif 'Cardo' in font_families:
    default_font: str = 'Cardo'
elif 'Segoe UI' in font_families:
    default_font: str = 'Segoe UI'
elif 'Noto Sans' in font_families:
    default_font: str = 'Noto Sans'
elif 'Noto Serif' in font_families:
    default_font: str = 'Noto Serif'
else:
    default_font: str = ''
screen = QApplication.primaryScreen()
size = screen.size()
screen_width = size.width()
screen_height = size.height()
window_width = round(0.75 * screen_width)
window_height = round(0.75 * screen_height)
default_ui_font_size = round(0.009 * screen_height)
default_editor_font_size = round(0.013 * screen_height)


@dataclass
class GeneralSettings:
    auto_save_on_exit: bool = field(default=True)
    last_dir_in_: str = field(default='')
    last_dir_out_: str = field(default='')
    feature_track_changes_: bool = field(default=False)

@dataclass
class AppearanceSettings:
    window_style: str = field(default='Fusion')
    theme: str = field(default='auto')
    ui_font_size: int = field(default=default_ui_font_size)

@dataclass
class EditorShortcuts:
    zoom_in: str = field(default='Ctrl++')
    zoom_out: str = field(default='Ctrl+-')
    intelliPaste: str = field(default='Ctrl+Shift+V')
    deletion: str = field(default='Ctrl+D')
    numeral: str = field(default='Ctrl+0')
    paragraphos: str = field(default='Ctrl+P')
    forked_paragraphos: str = field(default='Ctrl+Shift+P')
    supralinear_stroke: str = field(default='Ctrl+L')
    supralinear_stroke_alt: str = field(default='Ctrl+Shift+L')
    handshift: str = field(default='Ctrl+H')
    underdot: str = field(default='Ctrl+U')
    orthographic_regularization: str = field(default='Ctrl+R')

@dataclass
class EditorSettings:
    font: str = field(default=default_font)
    font_size: int = field(default=default_editor_font_size)
    default_language: str = field(default='grc')
    zoom_level_: float = field(default=1.0)
    last_file_: str = field(default='')
    debug_delay: int = field(default=150)
    scroll_val_: int = field(default=0)
    text_cursor_pos_: int = field(default=0)
    shortcuts: EditorShortcuts = field(default_factory=EditorShortcuts)


@dataclass
class SettingsManager:
    general: GeneralSettings = field(default_factory=lambda: GeneralSettings())
    editor: EditorSettings = field(default_factory=lambda: EditorSettings())
    appearance: AppearanceSettings = field(default_factory=lambda: AppearanceSettings())

    def read_settings(self):
        with open(config_file_path, 'r') as f:
            settings_dict = json.load(f)
        try:
            self.load_settings(self, settings_dict)
        except KeyError:
            pass

    def load_settings(self, target, settings_dict: dict):
        for f in fields(target):
            if f.name not in settings_dict:
                print(f'SettingsManager: Expected field {f.name} in config.json')
                continue
            value = getattr(target, f.name)
            new_value = settings_dict[f.name]
            if (is_dataclass(value) or is_dataclass(f.type)) and value is not None:
                if isinstance(new_value, dict):
                    self.load_settings(value, new_value)
            else:
                setattr(target, f.name, new_value)

    def reset_user_settings(self, target=None):
        if target is None:
            target = self
        for f in fields(target):
            value = getattr(target, f.name)
            if is_dataclass(value) and value is not None:
                self.reset_user_settings(value)
            else:
                if not f.name.endswith('_'):
                    setattr(target, f.name, f.default)

    def write_settings(self):
        settings_dict = asdict(self)
        print(f'wrote {config_file_path} > {settings_dict}')
        with open(config_file_path, 'w') as f:
            json.dump(settings_dict, f, indent=4)


def make_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


make_dir(data_dir)
make_dir(tracking_dir)
settings_mgr = SettingsManager()
if not os.path.exists(config_file_path):
    settings_mgr.write_settings()
else:
    settings_mgr.read_settings()



