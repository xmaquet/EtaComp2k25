from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QComboBox, QSpinBox, QLabel, QHBoxLayout, QPushButton

class CalibrationCurveTab(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)

        # 1) Modèle
        g_model = QGroupBox("Modèle de courbe")
        f1 = QFormLayout(g_model)
        self.combo_comparator = QComboBox()
        self.combo_comparator.addItem("(sélectionner)")
        self.combo_model = QComboBox()
        self.combo_model.addItems(["Linéaire", "Polynôme (ordre n)"])
        self.spin_order = QSpinBox()
        self.spin_order.setRange(1, 6)
        self.spin_order.setValue(2)
        f1.addRow("Comparateur", self.combo_comparator)
        f1.addRow("Type", self.combo_model)
        f1.addRow("Ordre", self.spin_order)

        # 2) Données & rendu (placeholder)
        g_plot = QGroupBox("Points & courbe (placeholder)")
        v2 = QVBoxLayout(g_plot)
        v2.addWidget(QLabel("Ici viendront : points mesurés, ajustement, résidus, et un graphe Matplotlib."))

        # 3) Actions
        bar = QHBoxLayout()
        self.btn_fit = QPushButton("Ajuster la courbe")
        self.btn_export = QPushButton("Exporter les coefficients")
        bar.addStretch()
        bar.addWidget(self.btn_export)
        bar.addWidget(self.btn_fit)

        root.addWidget(g_model)
        root.addWidget(g_plot)
        root.addLayout(bar)
        root.addStretch()
