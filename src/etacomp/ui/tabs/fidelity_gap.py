from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QComboBox, QPushButton, QHBoxLayout, QLabel

class FidelityGapTab(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)

        # 1) Contexte
        g_ctx = QGroupBox("Contexte")
        f1 = QFormLayout(g_ctx)
        self.combo_comparator = QComboBox()
        self.combo_comparator.addItem("(sélectionner)")
        f1.addRow("Comparateur", self.combo_comparator)

        # 2) Données (placeholder)
        g_data = QGroupBox("Séries de mesures (placeholder)")
        v2 = QVBoxLayout(g_data)
        v2.addWidget(QLabel("Ici viendront : import/saisie des séries, stats intra-série, écart type, etc."))

        # 3) Actions
        bar = QHBoxLayout()
        self.btn_compute = QPushButton("Calculer")
        self.btn_clear = QPushButton("Effacer")
        bar.addStretch()
        bar.addWidget(self.btn_clear)
        bar.addWidget(self.btn_compute)

        root.addWidget(g_ctx)
        root.addWidget(g_data)
        root.addLayout(bar)
        root.addStretch()
