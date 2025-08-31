from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QLabel, QPushButton, QHBoxLayout

class FinalizationTab(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)

        g_summary = QGroupBox("Synthèse (placeholder)")
        v1 = QVBoxLayout(g_summary)
        v1.addWidget(QLabel("Ici viendront : récapitulatif des sessions, stats clés, conformité, traçabilité."))

        g_report = QGroupBox("Rapport (placeholder)")
        v2 = QVBoxLayout(g_report)
        v2.addWidget(QLabel("Bouton pour générer un rapport (PDF/HTML) + choix du template."))

        bar = QHBoxLayout()
        self.btn_export_pdf = QPushButton("Exporter PDF")
        self.btn_export_html = QPushButton("Exporter HTML")
        bar.addStretch()
        bar.addWidget(self.btn_export_html)
        bar.addWidget(self.btn_export_pdf)

        root.addWidget(g_summary)
        root.addWidget(g_report)
        root.addLayout(bar)
        root.addStretch()
