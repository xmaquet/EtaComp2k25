from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QComboBox, QLineEdit, QLabel,
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton, QMessageBox
)

from ...io.serial_manager import serial_manager
from ...config.tesa import load_tesa_config, save_tesa_config, DEFAULT_TESA_CONFIG


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

        self.input_regex = QLineEdit(r"^\s*[+-]?\s*(?:\d*[.,]\d+|\d+)\s*$")
        self.input_regex.setToolTip("Regex d’extraction de la valeur (conseillée: stricte).")

        ft.addRow("Mode", self.combo_mode)
        ft.addRow("Commande", self.input_trigger)
        ft.addRow("EOL", self.combo_eol)
        ft.addRow("Décimale", self.combo_decimal)
        ft.addRow("Regex", self.input_regex)

        # ====== Groupe TESA Frame / Decode ======
        grp_frame = QGroupBox("TESA Frame / Decode")
        ff = QFormLayout(grp_frame)

        self.chk_tesa_enable = QCheckBox("Activer lecteur TESA (mode bouton)")
        self.chk_tesa_enable.setToolTip("Active le décodage TESA par silence inter‑octets (120 ms) avec masque 7‑bit et extraction numérique.")
        self.chk_tesa_enable.setChecked(True)
        self.combo_frame_mode = QComboBox(); self.combo_frame_mode.addItems(["silence", "eol"])
        self.spin_silence = QSpinBox(); self.spin_silence.setRange(10, 2000); self.spin_silence.setValue(120); self.spin_silence.setSuffix(" ms")
        self.combo_eol_mode = QComboBox(); self.combo_eol_mode.addItems(["CRLF", "CR", "LF"])
        self.chk_mask7 = QCheckBox("Masque 7-bit");
        self.chk_mask7.setChecked(True)
        self.line_strip = QLineEdit("\\r\\n\\0 ")
        self.line_regex = QLineEdit(r"[-+]?\d+(?:[.,]\d+)?|[-+]?[.,]\d+")
        self.spin_decimals = QSpinBox(); self.spin_decimals.setRange(0, 6); self.spin_decimals.setValue(3)
        self.combo_decimal_disp = QComboBox(); self.combo_decimal_disp.addItems(["dot", "comma"])

        # Bouton rétablir par défaut
        self.btn_tesa_defaults = QPushButton("Rétablir par défaut")

        ff.addRow(self.chk_tesa_enable)
        ff.addRow("frame_mode", self.combo_frame_mode)
        ff.addRow("silence_ms", self.spin_silence)
        ff.addRow("eol", self.combo_eol_mode)
        ff.addRow(self.chk_mask7)
        ff.addRow("strip_chars", self.line_strip)
        ff.addRow("value_regex", self.line_regex)
        ff.addRow("decimals", self.spin_decimals)
        ff.addRow("decimal_display", self.combo_decimal_disp)
        ff.addRow("", self.btn_tesa_defaults)

        root.addWidget(grp_tesa)
        root.addWidget(grp_frame)
        root.addStretch()

        # Appliquer au SerialManager
        self.combo_mode.currentIndexChanged.connect(lambda _: self._apply_send())
        self.input_trigger.textChanged.connect(lambda _: self._apply_send())
        self.combo_eol.currentIndexChanged.connect(lambda _: self._apply_send())
        self.combo_decimal.currentIndexChanged.connect(lambda _: self._apply_parse())
        self.input_regex.textChanged.connect(lambda _: self._apply_parse())
        # TESA reader bindings
        self.chk_tesa_enable.toggled.connect(lambda _: self._apply_tesa_reader())
        self.combo_frame_mode.currentIndexChanged.connect(lambda _: self._apply_tesa_reader())
        self.spin_silence.valueChanged.connect(lambda _: self._apply_tesa_reader())
        self.combo_eol_mode.currentIndexChanged.connect(lambda _: self._apply_tesa_reader())
        self.chk_mask7.toggled.connect(lambda _: self._apply_tesa_reader())
        self.line_strip.textChanged.connect(lambda _: self._apply_tesa_reader())
        self.line_regex.textChanged.connect(lambda _: self._apply_tesa_reader())
        self.spin_decimals.valueChanged.connect(lambda _: self._apply_tesa_reader())
        self.combo_decimal_disp.currentTextChanged.connect(lambda _: self._apply_tesa_reader())
        self.btn_tesa_defaults.clicked.connect(self._restore_tesa_defaults)

        # Charger config TESA depuis disque et appliquer
        self._apply_send()
        self._apply_parse()
        self._load_tesa_config()
        self._apply_tesa_reader()

    def _apply_send(self):
        serial_manager.set_send_config(
            mode=self.combo_mode.currentText(),
            trigger_text=self.input_trigger.text(),
            eol_mode=self.combo_eol.currentText(),
        )

    def _apply_parse(self):
        serial_manager.set_ascii_config(
            regex_pattern=self.input_regex.text().strip() or r"^\s*[+-]?\s*(?:\d*[.,]\d+|\d+)\s*$",
            decimal_comma=self.combo_decimal.currentText().startswith("Virgule"),
        )

    def _apply_tesa_reader(self):
        # Appliquer au moteur
        serial_manager.set_tesa_reader_config(
            enabled=self.chk_tesa_enable.isChecked(),
            frame_mode=self.combo_frame_mode.currentText(),
            silence_ms=int(self.spin_silence.value()),
            eol=self.combo_eol_mode.currentText(),
            mask_7bit=self.chk_mask7.isChecked(),
            strip_chars=self.line_strip.text(),
            value_regex=self.line_regex.text().strip() or r"[-+]?\d+(?:[.,]\d+)?|[-+]?[.,]\d+",
            decimals=int(self.spin_decimals.value()),
            decimal_display=self.combo_decimal_disp.currentText(),
        )
        # Sauvegarder la config
        cfg = {
            "enabled": self.chk_tesa_enable.isChecked(),
            "frame_mode": self.combo_frame_mode.currentText(),
            "silence_ms": int(self.spin_silence.value()),
            "eol": self.combo_eol_mode.currentText(),
            "mask_7bit": self.chk_mask7.isChecked(),
            "strip_chars": self.line_strip.text(),
            "value_regex": self.line_regex.text().strip() or r"[-+]?\d+(?:[.,]\d+)?|[-+]?[.,]\d+",
            "decimals": int(self.spin_decimals.value()),
            "decimal_display": self.combo_decimal_disp.currentText(),
        }
        save_tesa_config(cfg)

    # ----- helpers TESA config -----
    def _load_tesa_config(self):
        cfg = load_tesa_config()
        # Remplir l'UI
        self.chk_tesa_enable.setChecked(bool(cfg.get("enabled", True)))
        self.combo_frame_mode.setCurrentText(str(cfg.get("frame_mode", "silence")))
        self.spin_silence.setValue(int(cfg.get("silence_ms", 120)))
        self.combo_eol_mode.setCurrentText(str(cfg.get("eol", "CRLF")))
        self.chk_mask7.setChecked(bool(cfg.get("mask_7bit", True)))
        self.line_strip.setText(str(cfg.get("strip_chars", "\\r\\n\\0 ")))
        self.line_regex.setText(str(cfg.get("value_regex", r"[-+]?\d+(?:[.,]\d+)?|[-+]?[.,]\d+")))
        self.spin_decimals.setValue(int(cfg.get("decimals", 3)))
        self.combo_decimal_disp.setCurrentText(str(cfg.get("decimal_display", "dot")))

    def _restore_tesa_defaults(self):
        # Revenir sur DEFAULT_TESA_CONFIG
        d = DEFAULT_TESA_CONFIG
        self.chk_tesa_enable.setChecked(bool(d["enabled"]))
        self.combo_frame_mode.setCurrentText(d["frame_mode"])
        self.spin_silence.setValue(int(d["silence_ms"]))
        self.combo_eol_mode.setCurrentText(d["eol"])
        self.chk_mask7.setChecked(bool(d["mask_7bit"]))
        self.line_strip.setText(d["strip_chars"])
        self.line_regex.setText(d["value_regex"])
        self.spin_decimals.setValue(int(d["decimals"]))
        self.combo_decimal_disp.setCurrentText(d["decimal_display"])
        self._apply_tesa_reader()
        QMessageBox.information(self, "TESA ASCII", "Valeurs par défaut rétablies et enregistrées.")
