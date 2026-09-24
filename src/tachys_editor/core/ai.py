from importlib.resources import files
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QFont
import joblib
import unicodedata
import numpy as np
from tachys_editor.shared.settings import settings_mgr

regs_model = str(files('tachys_editor.resources.models').joinpath('predict_regs.joblib'))

class AIManager:
    def __init__(self):
        self.regs_pipeline = joblib.load(regs_model)
        self.context_menu = QMenu()

    @staticmethod
    def normalize(text):
        normalized_text = unicodedata.normalize('NFD', text)
        stripped = "".join(c for c in normalized_text if unicodedata.category(c) != 'Mn')
        nfc_text = unicodedata.normalize('NFC', stripped)
        return nfc_text

    def predict_reg(self, word: str, context_menu_position):
        self.context_menu.clear()
        font_size = settings_mgr.appearance.ui_font_size + 2
        self.context_menu.setFont(QFont(settings_mgr.editor.font, font_size))
        normalized_word = self.normalize(word)
        print(normalized_word)
        probabilities = self.regs_pipeline.predict_proba([normalized_word])[0]
        all_classes = self.regs_pipeline.named_steps['kneighborsclassifier'].classes_
        top_indices = np.argsort(probabilities)[::-1][:10]
        results = []
        for idx in top_indices:
            prob = probabilities[idx]
            if prob > 0.01:
                option = str(all_classes[idx])
                self.context_menu.addAction(f'<:{option}|reg|{word}:>')
                results.append(option)
        predicted_reg = ''
        if results:
            if len(results) > 1:
                choice = self.context_menu.exec(context_menu_position)
                if choice:
                    return choice.text()
            else:
                predicted_reg = results[0]
        return f'<:{predicted_reg}|reg|{word}:>'