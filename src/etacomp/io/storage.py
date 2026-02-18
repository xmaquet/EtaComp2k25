from __future__ import annotations

from pathlib import Path
import json
from typing import Type, TypeVar, List, Optional

from ..config.paths import get_data_dir
from ..models.comparator import Comparator
from ..models.detenteur import Detenteur
from ..models.banc_etalon import BancEtalon
from ..models.session import Session

T = TypeVar("T", Comparator, Session)


# ---------- helpers génériques ----------
def _subdir_path(subdir: str) -> Path:
    p = get_data_dir() / subdir
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_model(model: T, subdir: str, filename: str) -> Path:
    dest = _subdir_path(subdir) / filename
    dest.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    return dest


def load_model(cls: type[T], subdir: str, filename: str) -> T:
    path = _subdir_path(subdir) / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    return cls.model_validate(data)


# ---------- Comparators ----------
COMPARATORS_DIR = "comparators"


def list_comparator_files() -> List[Path]:
    d = _subdir_path(COMPARATORS_DIR)
    return sorted([p for p in d.glob("*.json") if p.is_file()])


def list_comparators() -> List[Comparator]:
    comps: List[Comparator] = []
    for fp in list_comparator_files():
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            # Le validateur gère la migration (déduction course/graduation/range_type)
            comps.append(Comparator.model_validate(data))
        except Exception:
            # on ignore les fichiers corrompus
            continue
    return comps


def save_comparator(c: Comparator) -> Path:
    base = c.reference.strip().replace(" ", "_")
    return save_model(c, COMPARATORS_DIR, f"{base}.json")


def delete_comparator_by_reference(reference: str) -> bool:
    base = reference.strip().replace(" ", "_")
    fp = _subdir_path(COMPARATORS_DIR) / f"{base}.json"
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
    except Exception:
        return []


def save_detenteurs(detenteurs: List[Detenteur]) -> Path:
    """Sauvegarde la liste des détenteurs."""
    get_data_dir().mkdir(parents=True, exist_ok=True)
    fp = get_data_dir() / DETENTEURS_FILE
    payload = {"detenteurs": [d.model_dump() for d in detenteurs]}
    fp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
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
    except Exception:
        return []


def save_bancs_etalon(bancs: List[BancEtalon]) -> Path:
    """Sauvegarde la liste des bancs étalon."""
    get_data_dir().mkdir(parents=True, exist_ok=True)
    fp = get_data_dir() / BANCS_ETALON_FILE
    payload = {"bancs": [b.model_dump() for b in bancs]}
    fp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
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


def _default_session_filename(s: Session) -> str:
    ref = (s.comparator_ref or "sans_ref").strip().replace(" ", "_")
    dt = s.date.strftime("%Y%m%d_%H%M%S")
    return f"{ref}_{dt}.json"


def list_sessions() -> List[Path]:
    d = _subdir_path(SESSIONS_DIR)
    return sorted(d.glob("*.json"), reverse=True)


def save_session_file(s: Session, filename: Optional[str] = None) -> Path:
    if not s.has_measures():
        raise RuntimeError("La session ne contient aucune mesure.")
    name = filename or _default_session_filename(s)
    return save_model(s, SESSIONS_DIR, name)


def load_session_file(path: Path) -> Session:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Session.model_validate(data)
