import requests
import sys
import os
from packaging import version
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (QMessageBox, QProgressDialog, QFileDialog, QDialog, QVBoxLayout, QTextBrowser, QLabel,
                               QDialogButtonBox, QFrame)
from tachys_editor.shared.settings import __version__
from tachys_editor.shared.objects import session


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
        path = self.directory
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
        if isinstance(self.update_worker, UpdateWorker):
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
            msg.information(self.parent, 'Download Complete',
                            f'The latest version of TACHYS Editor has been successfully downloaded to:\n'
                            f'{downloaded_file}\n\nYou can extract the archive to your preferred directory. Please '
                            f'ensure that TACHYS Editor is not running if you decide to overwrite existing files.')
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        else:
            msg.warning(self.parent, 'Download failed',
                        'The download of the latest version of TACHYS Editor failed. Download it manually from '
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

    def show_update_notice(self, new_version: str, release_notes: str):
        dialog = QDialog(self.parent)
        dialog.setWindowTitle('New Version Available')
        dialog.resize(450, 450)
        layout = QVBoxLayout(dialog)
        label = QLabel(f'TACHYS Editor has been updated to v{new_version}.')
        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(True)
        browser.setMarkdown(release_notes)
        splitter = QFrame()
        splitter.setFrameShape(QFrame.Shape.HLine)
        splitter.setFrameShadow(QFrame.Shadow.Sunken)
        label_question = QLabel('Would you like to download the latest version now? '
                                'You will still be able to use the editor in the meantime.')
        layout.addWidget(label)
        layout.addWidget(browser)
        layout.addWidget(splitter)
        layout.addWidget(label_question)
        buttons = QDialogButtonBox(parent=dialog)
        buttons.addButton(QDialogButtonBox.StandardButton.Yes)
        buttons.addButton(QDialogButtonBox.StandardButton.No)
        buttons.button(QDialogButtonBox.StandardButton.Yes).setText("Download Now")
        buttons.button(QDialogButtonBox.StandardButton.No).setText("Later")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        return dialog.exec()

    def check_for_update(self, notice_if_latest: bool = False, display_errors: bool = False):
        url = "https://api.github.com/repos/oli-do/TACHYS-Editor/releases/latest"
        try:
            r = session.get(url, timeout=(0.1, 0.1), headers={'User-Agent': 'TACHYS-Editor-Updater'})
            r.raise_for_status()
        except requests.exceptions.RequestException:
            if display_errors:
                QMessageBox.critical(self.parent, 'HTTP Request Failed',
                                     f'Could not retrieve information from GitHub.')
            return
        if r.ok:
            data = r.json()
            release_notes = data.get('body')
            online_version = data.get("tag_name", "").lstrip("v")
            assets = data.get('assets', [])
            asset_name = self.get_asset_name()
            download_url: str = next((a['browser_download_url'] for a in assets if a.get('name') == asset_name), '')
            if not download_url:
                raise RuntimeError(f"No download url found for {asset_name}")
            if version.parse(online_version) > version.parse(__version__):
                if self.show_update_notice(online_version, release_notes) == QDialog.DialogCode.Accepted:
                    file_dialog = QFileDialog()
                    file_dialog.setWindowTitle('Select the download directory')
                    self.download_directory = file_dialog.getExistingDirectory()
                    if self.download_directory:
                        self.update_worker = UpdateWorker(download_url, online_version, self.download_directory, asset_name)
                        self.update_worker.progress.connect(self.update_progress_dialog)
                        self.update_worker.finished.connect(self.on_finished)
                        self.start_update()
            else:
                if notice_if_latest:
                    msg = QMessageBox(self.parent)
                    msg.setWindowTitle('No Updates Available')
                    msg.setText('Currently, there are no updates available. You are running the latest version of '
                                'TACHYS Editor.')
                    msg.exec()
