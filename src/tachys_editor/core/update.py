import requests
import sys
import os
from packaging import version
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import QMessageBox, QProgressDialog, QFileDialog
from tachys_editor.shared.settings import __version__


class UpdateWorker(QThread):
    finished = Signal(str)
    progress = Signal(int)

    def __init__(self, download_url: str, update_version: str, directory: str, filename: str):
        super().__init__()
        self.download_url = download_url
        self.update_version = update_version
        self.filename = filename
        self.directory = directory

    def run(self):
        path = os.path.join(self.directory, self.update_version)
        os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, self.filename)
        try:
            headers = {'User-Agent': 'TACHYS-Editor'}
            r = requests.get(self.download_url, stream=True, headers=headers, timeout=30)
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            self.progress.emit(percent)
            self.finished.emit("Success")
        except Exception as e:
            self.finished.emit(f"Error: {str(e)}")


class Updater:
    def __init__(self, parent=None):
        self.progress_dialog = None
        self.update_worker: UpdateWorker | None = None
        self.download_directory: str = ''
        self.asset_name: str = ''
        self.parent = parent

    @Slot(int)
    def update_progress_dialog(self, percentage: int):
        if self.progress_dialog and self.progress_dialog.isVisible():
            self.progress_dialog.setValue(percentage)

    def start_update(self):
        self.progress_dialog = QProgressDialog(labelText='Please wait while the update is being downloaded...', minimum=0, maximum=100)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint |
                                            Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.progress_dialog.setWindowTitle('Downloading')
        self.progress_dialog.show()
        self.update_worker.start()

    @Slot(str)
    def on_finished(self, status: str):
        if self.progress_dialog:
            self.progress_dialog.close()
        msg = QMessageBox()
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        if status == "Success":
            downloaded_file = os.path.normpath(os.path.join(self.download_directory, self.asset_name))
            msg.information(self.parent, 'Download complete', f'The latest version of TACHYS Editor has been '
                                                       f'successfully downloaded to {downloaded_file}.')
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        else:
            msg.warning(self.parent, 'Download failed', 'The download of the latest version of TACHYS Editor '
                                                 'failed. Download it manually from '
                                                 '<a href="https://github.com/oli-do/TACHYS-Editor/releases/latest">GitHub</a>.')
            msg.exec()

    def get_asset_name(self) -> str:
        platform_map = {
            'win32': 'TACHYS-Editor-Windows.zip',
            'darwin': 'TACHYS-Editor-macOS.tar.gz',
            'linux': 'TACHYS-Editor-Linux.tar.gz'
        }
        asset_name = platform_map.get(sys.platform)
        if not asset_name:
            raise RuntimeError(f"Unsupported platform: {sys.platform}")
        self.asset_name = asset_name
        return asset_name

    def check_for_update(self):
        url = "https://api.github.com/repos/oli-do/TACHYS-Editor/releases/latest"
        try:
            r = requests.get(url, timeout=10, headers={'User-Agent': 'TACHYS-Editor-Updater'})
            if r.ok:
                data = r.json()
                online_version = data.get("tag_name", "").lstrip("v")
                assets = data.get('assets', [])
                asset_name = self.get_asset_name()
                download_url = next((a['browser_download_url'] for a in assets if a.get('name') == asset_name), None)
                if not download_url:
                    raise RuntimeError(f"No download url found for {asset_name}")
                if version.parse(online_version) > version.parse(__version__):
                    msg = QMessageBox(self.parent)
                    msg.setWindowTitle('New version available')
                    msg.setText(f'TACHYS Editor has been updated to v{online_version}. \n\n'
                                'Would you like to download the latest version now? '
                                'You will still be able to use the editor in the meantime.')
                    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if msg.exec() == QMessageBox.StandardButton.Yes:
                        file_dialog = QFileDialog()
                        file_dialog.setWindowTitle('Select the download directory')
                        self.download_directory = file_dialog.getExistingDirectory()
                        if self.download_directory:
                            self.update_worker = UpdateWorker(download_url, online_version, self.download_directory, asset_name)
                            self.update_worker.progress.connect(self.update_progress_dialog)
                            self.update_worker.finished.connect(self.on_finished)
                            self.start_update()
        except Exception as e:
            print(f'Update check failed: {e}')
