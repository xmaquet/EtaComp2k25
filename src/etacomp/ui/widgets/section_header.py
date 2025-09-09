from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QFrame
from PySide6.QtCore import Qt

class SectionHeader(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._label = QLabel(title)
        self._label.setObjectName("SectionHeaderLabel")
        self._label.setAlignment(Qt.AlignVCenter)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setObjectName("SectionHeaderLine")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(10)
        layout.addWidget(self._label)
        layout.addWidget(line, 1)

    def setText(self, text: str):
        self._label.setText(text)
