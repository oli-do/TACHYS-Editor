import json
import os
from dataclasses import dataclass, asdict, field, fields, is_dataclass
from tkinter import Tk, font
from appdirs import user_data_dir

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


@dataclass
class GeneralSettings:
    auto_save_on_exit: bool
    last_dir_in: str
    last_dir_out: str

@dataclass
class AppearanceSettings:
    default_ui_font_size: int
    ui_font_size: int
    editor_font_size: int

@dataclass
class EditorShortcuts:
    zoom_in: str = 'Ctrl++'
    zoom_out: str = 'Ctrl+-'
    intelliPaste: str = 'Ctrl+Shift+V'
    deletion: str = 'Ctrl+D'
    numeral: str = 'Ctrl+0'
    paragraphos: str = 'Ctrl+P'
    forked_paragraphos: str = 'Ctrl+Shift+P'
    supralinear_stroke: str = 'Ctrl+L'
    supralinear_stroke_alt: str = 'Ctrl+Shift+L'
    handshift: str = 'Ctrl+H'
    underdot: str = 'Ctrl+U'

@dataclass
class EditorSettings:
    font: str
    default_language: str
    zoom_level: float
    last_file: str
    debug_delay: int
    scroll_val: int
    text_cursor_pos: int
    shortcuts: EditorShortcuts = field(default_factory=EditorShortcuts)


@dataclass
class SettingsManager:
    general: GeneralSettings = field(default_factory=lambda: GeneralSettings(True, '', ''))
    editor: EditorSettings = field(default_factory=lambda: EditorSettings(default_font, 'grc', 1.0, '', 250, 0, 0))
    appearance: AppearanceSettings = field(default_factory=lambda: AppearanceSettings(-1, -1, -1))

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



