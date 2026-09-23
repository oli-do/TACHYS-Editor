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

g_types = ['*diple-obelismene*', '*filled-circle*', '*unintelligible*', '*long-vertical-bar*',
           '*antisigma-periestigmene*', '*dotted-obelos*', '*upper-brace-opening*',
           '*parens-punctuation-closing*', '*backslash*', '*apostrophe*', '*diple*',
           '*reverse-dotted-obelos*', '*dash*', '*rho-cross*', '*slanting-stroke*',
           '*center-brace-closing*', '*obelos*', '*upwards-ancora*', '*parens-deletion-opening*',
           '*chirho*', '*double-vertical-bar*', '*chirho?*', '*low-punctus*', '*double-slanting-stroke*',
           '*x*', '*tachygraphic-marks*', '*filler(diple)*', '*tetrapunct*', '*middot*',
           '*lower-brace-closing*', '*parens-upper-opening*', '*parens-punctuation-opening*',
           '*downwards-ancora*', '*lower-brace-opening*', '*hypodiastole*', '*diple-periestigmene*',
           '*high-punctus*', '*dipunct*', '*guide-dot*', '*diastole*', '*xs*', '*center-brace-opening*',
           '*asteriskos*', '*dot*', '*swungdash*', '*undefined*', '*asteriskos?*',
           '*parens-deletion-closing*', '*paraphe*', '*filler(extension)*', '*stauros*',
           '*parens-upper-closing*', '*chi-periestigmenon*', '*check*', '*parens-middle-closing*',
           '*magical-symbol*', '*parens-lower-closing*', '*parens-lower-opening*', '*charakteres*',
           '*parens-middle-opening*', '*tripunct*', '*upper-brace-closing*', '*antisigma*', '*monogram*']
g_types = list(sorted(g_types))