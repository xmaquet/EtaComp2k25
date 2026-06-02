from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Type, TypeVar, List, Optional

from ..config.paths import get_data_dir
from ..models.comparator import Comparator
from ..models.detenteur import Detenteur
from ..models.banc_etalon import BancEtalon
from ..models.session import Session
from .atomic_write import atomic_write
from .safe_filename import sanitize_filename

logger = logging.getLogger(__name__)

T = TypeVar("T", Comparator, Session)


# ---------- helpers génériques ----------
def _subdir_path(subdir: str) -> Path:
    p = get_data_dir() / subdir
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_model(model: T, subdir: str, filename: str) -> Path:
    dest = _subdir_path(subdir) / filename
    atomic_write(dest, model.model_dump_json(indent=2))
    return dest


def load_model(cls: type[T], subdir: str, filename: str) -> T:
    path = _subdir_path(subdir) / filename
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(data)
    except Exception as exc:
        logger.error("Fichier illisible %s : %s", path, exc)
        raise ValueError(f"Fichier invalide ou corrompu : {path.name}") from exc


# ---------- Comparators ----------
COMPARATORS_DIR = "comparators"


def _comparator_filename(reference: str) -> str:
    return f"{sanitize_filename(reference)}.json"


def list_comparator_files() -> List[Path]:
    d = _subdir_path(COMPARATORS_DIR)
    return sorted([p for p in d.glob("*.json") if p.is_file()])


def list_comparators() -> List[Comparator]:
    comps: List[Comparator] = []
    for fp in list_comparator_files():
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            comps.append(Comparator.model_validate(data))
        except Exception as exc:
            logger.warning("Comparateur ignoré (%s) : %s", fp.name, exc)
            continue
    return comps


def save_comparator(c: Comparator) -> Path:
    return save_model(c, COMPARATORS_DIR, _comparator_filename(c.reference))


def delete_comparator_by_reference(reference: str) -> bool:
    fp = _subdir_path(COMPARATORS_DIR) / _comparator_filename(reference)
    if fp.exists():
        fp.unlink()
        return True
    return False


def upsert_comparator(c: Comparator) -> Path:
    return save_comparator(c)


# ---------- Détenteurs ----------
DETENTEURS_FILE = "detenteurs.json"


def list_detenteurs() -> List[Detenteur]:
    """Charge la liste des détenteurs depuis le fichier JSON."""
    fp = get_data_dir() / DETENTEURS_FILE
    if not fp.exists():
        return []
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        items = data.get("detenteurs", data) if isinstance(data, dict) else data
        return [Detenteur.model_validate(d) for d in items]
    except Exception as exc:
        logger.warning("Fichier détenteurs illisible : %s", exc)
        return []


def save_detenteurs(detenteurs: List[Detenteur]) -> Path:
    """Sauvegarde la liste des détenteurs."""
    get_data_dir().mkdir(parents=True, exist_ok=True)
    fp = get_data_dir() / DETENTEURS_FILE
    payload = {"detenteurs": [d.model_dump() for d in detenteurs]}
    atomic_write(fp, json.dumps(payload, indent=2))
    return fp


def add_detenteur(d: Detenteur) -> Path:
    """Ajoute un détenteur (écrase si code_es existe déjà)."""
    lst = list_detenteurs()
    lst = [x for x in lst if x.code_es.strip().upper() != d.code_es.strip().upper()]
    lst.append(d)
    return save_detenteurs(lst)


def delete_detenteur_by_code(code_es: str) -> bool:
    """Supprime le détenteur ayant le code ES donné."""
    code = code_es.strip().upper()
    lst = [x for x in list_detenteurs() if x.code_es.strip().upper() != code]
    if len(lst) == len(list_detenteurs()):
        return False
    save_detenteurs(lst)
    return True


# ---------- Bancs étalon ----------
BANCS_ETALON_FILE = "bancs_etalon.json"


def list_bancs_etalon() -> List[BancEtalon]:
    """Charge la liste des bancs étalon."""
    fp = get_data_dir() / BANCS_ETALON_FILE
    if not fp.exists():
        return []
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        items = data.get("bancs", data) if isinstance(data, dict) else data
        return [BancEtalon.model_validate(d) for d in items]
    except Exception as exc:
        logger.warning("Fichier bancs étalon illisible : %s", exc)
        return []


def save_bancs_etalon(bancs: List[BancEtalon]) -> Path:
    """Sauvegarde la liste des bancs étalon."""
    get_data_dir().mkdir(parents=True, exist_ok=True)
    fp = get_data_dir() / BANCS_ETALON_FILE
    payload = {"bancs": [b.model_dump() for b in bancs]}
    atomic_write(fp, json.dumps(payload, indent=2))
    return fp


def get_default_banc_etalon() -> Optional[BancEtalon]:
    """Retourne le banc étalon marqué par défaut (pour export PDF)."""
    for b in list_bancs_etalon():
        if b.is_default:
            return b
    return None


def list_bancs_etalon_for_session() -> List[BancEtalon]:
    """Retourne les bancs étalon sauf le défaut (pour l'onglet Session)."""
    return [b for b in list_bancs_etalon() if not b.is_default]


# ---------- Sessions ----------
SESSIONS_DIR = "sessions"
AUTOSAVE_DIR = "autosave"
AUTOSAVE_FILENAME = "autosave_session.json"


def _default_session_filename(s: Session) -> str:
    ref = sanitize_filename(s.comparator_ref or "sans_ref")
    dt = s.date.strftime("%Y%m%d_%H%M%S")
    return f"{ref}_{dt}.json"


def list_sessions() -> List[Path]:
    d = _subdir_path(SESSIONS_DIR)
    return sorted(d.glob("*.json"), reverse=True)


def save_autosave_session(s: Session) -> Optional[Path]:
    """Sauvegarde automatique silencieuse (issue #14)."""
    if not s.has_measures():
        return None
    from ..core.session_adapter import sync_comparator_snapshot

    sync_comparator_snapshot(s)
    return save_model(s, AUTOSAVE_DIR, AUTOSAVE_FILENAME)


def save_session_file(s: Session, filename: Optional[str] = None) -> Path:
    if not s.has_measures():
        raise RuntimeError("La session ne contient aucune mesure.")
    name = filename or _default_session_filename(s)
    return save_model(s, SESSIONS_DIR, name)


def load_session_file(path: Path) -> Session:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Session.model_validate(data)
    except Exception as exc:
        logger.error("Session illisible %s : %s", path, exc)
        raise ValueError(f"Fichier session invalide ou corrompu : {path.name}") from exc
