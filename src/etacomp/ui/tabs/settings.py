from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox
from ...ui.themes import load_theme_qss
from ...config import defaults
from PySide6.QtWidgets import QApplication

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Thème de l'interface"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        self.theme_combo.setCurrentText(defaults.DEFAULT_THEME)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        layout.addWidget(self.theme_combo)

    def on_theme_changed(self, theme: str):
        qss = load_theme_qss(theme)
        QApplication.instance().setStyleSheet(qss)
