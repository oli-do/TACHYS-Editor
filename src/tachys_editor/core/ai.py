from importlib.resources import files
import joblib
import unicodedata
import regex

regs_model = str(files('tachys_editor.resources.models').joinpath('predict_regs.joblib'))

class AIManager:
    def __init__(self):
        self.regs_pipeline = joblib.load(regs_model)

    @staticmethod
    def normalize(text):
        normalized_text = unicodedata.normalize('NFD', text)
        stripped = "".join(c for c in normalized_text if unicodedata.category(c) != 'Mn')
        nfc_text = unicodedata.normalize('NFC', stripped)
        return ''.join(regex.findall(r'[Α-Ωα-ω]', nfc_text))

    def predict_reg(self, word: str):
        normalized_word = self.normalize(word)
        print('execute prediction', type(self.regs_pipeline), normalized_word)
        prediction = self.regs_pipeline.predict([self.normalize(normalized_word)])
        if prediction:
            return prediction[0]
        return ''