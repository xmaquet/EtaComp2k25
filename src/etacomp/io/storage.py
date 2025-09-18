from __future__ import annotations

from pathlib import Path
import json
from typing import Type, TypeVar, List, Optional

from ..config.paths import get_data_dir
from ..models.comparator import Comparator
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


# ---------- Sessions ----------
SESSIONS_DIR = "sessions"


def _default_session_filename(s: Session) -> str:
    who = (s.operator or "op").strip().replace(" ", "_")
    dt = s.date.strftime("%Y%m%d_%H%M%S")
    return f"{who}_{dt}.json"


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
