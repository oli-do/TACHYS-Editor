import json
import os
from dataclasses import dataclass, asdict

from appdirs import user_data_dir

app_name = 'TACHYS Editor'
app_author = 'Oliver Donath'
data_dir = user_data_dir(appname=app_name, appauthor=app_author)
tracking_dir = os.path.join(data_dir, 'changes')
config_file_path = os.path.join(data_dir, 'config.json')


@dataclass
class SettingsManager:
    zoom_level: int = 1.0
    last_file: str = ''
    debug_delay: int = 250
    scroll_val: int = 0
    text_cursor_pos: int = 0

    def read_settings(self):
        with open(config_file_path, 'r') as f:
            settings_dict = json.load(f)
        try:
            self.zoom_level = settings_dict['zoom_level']
            self.last_file = settings_dict['last_file']
            self.debug_delay = settings_dict['debug_delay']
            self.scroll_val = settings_dict['scroll_val']
            self.text_cursor_pos = settings_dict['text_cursor_pos']
        except KeyError:
            pass

    def write_settings(self):
        settings_dict = asdict(self)
        print(f'wrote {config_file_path} > {settings_dict}')
        with open(config_file_path, 'w') as f:
            json.dump(settings_dict, f)


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



