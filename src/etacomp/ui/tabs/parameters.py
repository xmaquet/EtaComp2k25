from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QComboBox, QLineEdit, QLabel
)

from ...io.serial_manager import serial_manager


class ParametersTab(QWidget):
    """
    Onglet Paramètres :
    - Profil TESA ASCII (parse et envoi)
    (Ajoute ce widget dans ta fenêtre principale si ce n’est pas déjà fait)
    """
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)

        grp_tesa = QGroupBox("TESA ASCII")
        ft = QFormLayout(grp_tesa)

        # ENVOI
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Manuel (opérateur)", "À la demande"])
        self.combo_mode.setToolTip("Mode de déclenchement de la mesure.")

        self.input_trigger = QLineEdit()
        self.input_trigger.setPlaceholderText("Commande (si 'À la demande'), ex: M")
        self.input_trigger.setToolTip("Commande ASCII envoyée pour demander une mesure, si 'À la demande'.")

        self.combo_eol = QComboBox()
        self.combo_eol.addItems(["Aucun", "CR (\\r)", "LF (\\n)", "CRLF (\\r\\n)"])
        self.combo_eol.setCurrentText("CR (\\r)")
        self.combo_eol.setToolTip("Fin de ligne ajoutée à la commande envoyée.")

        # PARSE
        self.combo_decimal = QComboBox()
        self.combo_decimal.addItems(["Point (.)", "Virgule (,)"])
        self.combo_decimal.setToolTip("Caractère décimal attendu dans les nombres reçus.")

        self.input_regex = QLineEdit(r"^\s*[+-]?\d+(?:[.,]\d+)?\s*$")
        self.input_regex.setToolTip("Regex d’extraction de la valeur (conseillée: stricte).")

        ft.addRow("Mode", self.combo_mode)
        ft.addRow("Commande", self.input_trigger)
        ft.addRow("EOL", self.combo_eol)
        ft.addRow("Décimale", self.combo_decimal)
        ft.addRow("Regex", self.input_regex)

        root.addWidget(grp_tesa)
        root.addStretch()

        # Appliquer au SerialManager
        self.combo_mode.currentIndexChanged.connect(lambda _: self._apply_send())
        self.input_trigger.textChanged.connect(lambda _: self._apply_send())
        self.combo_eol.currentIndexChanged.connect(lambda _: self._apply_send())
        self.combo_decimal.currentIndexChanged.connect(lambda _: self._apply_parse())
        self.input_regex.textChanged.connect(lambda _: self._apply_parse())

        self._apply_send()
        self._apply_parse()

    def _apply_send(self):
        serial_manager.set_send_config(
            mode=self.combo_mode.currentText(),
            trigger_text=self.input_trigger.text(),
            eol_mode=self.combo_eol.currentText(),
        )

    def _apply_parse(self):
        serial_manager.set_ascii_config(
            regex_pattern=self.input_regex.text().strip() or r"^\s*[+-]?\d+(?:[.,]\d+)?\s*$",
            decimal_comma=self.combo_decimal.currentText().startswith("Virgule"),
        )
