from appdirs import user_data_dir
import os
import json
from dataclasses import dataclass, asdict


app_name = 'Leiden Editor'
app_author = 'Oliver Donath'
data_dir = user_data_dir(appname=app_name, appauthor=app_author)
tracking_dir = os.path.join(data_dir, 'changes')
config_file_path = os.path.join(data_dir, 'config.json')


@dataclass
class SettingsManager:
    zoom_level: int = 1.0
    last_file: str = ''

    def read_settings(self):
        with open(config_file_path, 'r') as f:
            settings_dict = json.load(f)
        self.zoom_level = settings_dict['zoom_level']
        self.last_file = settings_dict['last_file']

    def write_settings(self):
        settings_dict = asdict(self)
        print(settings_dict)
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



