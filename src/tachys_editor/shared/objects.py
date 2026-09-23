from PySide6.QtWidgets import QSplashScreen
from PySide6.QtGui import QPixmap, QFont, QIcon
from tachys_editor.core.parser import TachysParser
from tachys_editor.shared.settings import settings_mgr
from importlib.resources import files

splash_path = str(files('tachys_editor.resources').joinpath('splash.png'))
icon_path = str(files('tachys_editor.resources').joinpath('logo.ico'))

parser = TachysParser()
icon = QIcon(icon_path)
splash = QSplashScreen(QPixmap(splash_path))
splash_font = QFont('Arial', settings_mgr.appearance.ui_font_size)
splash.setFont(splash_font)