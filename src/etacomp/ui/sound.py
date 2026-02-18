from __future__ import annotations

import math
import wave
import struct
from pathlib import Path

from ..config.paths import get_data_dir


def _beep_path() -> Path:
    return get_data_dir() / "assets" / "beep.wav"


def ensure_beep_wav(freq_hz: float = 880.0, duration_ms: int = 80, volume: float = 0.4) -> Path:
    """
    Crée un petit wav mono si absent (~80 ms, sinusoïde).
    """
    path = _beep_path()
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    n_samples = int(sample_rate * (duration_ms / 1000.0))
    amplitude = int(max(0.0, min(1.0, volume)) * 32767)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        for i in range(n_samples):
            t = i / sample_rate
            val = int(amplitude * math.sin(2.0 * math.pi * freq_hz * t))
            wf.writeframes(struct.pack("<h", val))
    return path


def play_beep() -> None:
    """
    Joue le beep (wav). Sur Windows utilise winsound pour éviter dépendances Qt multimédia.
    """
    try:
        path = ensure_beep_wav()
        try:
            import winsound  # type: ignore
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception:
            pass
        # Fallback: beep basique
        try:
            from PySide6.QtGui import QGuiApplication
            QGuiApplication.beep()
        except Exception:
            pass
    except Exception:
        # Silencieux en cas d'échec
        pass

