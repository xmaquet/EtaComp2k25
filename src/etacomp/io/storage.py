from pathlib import Path
import json
from typing import Type, TypeVar, List, Optional, Iterable

from ..config.paths import get_data_dir
from ..models.comparator import Comparator
from ..models.session import Session

T = TypeVar("T", Comparator, Session)


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
            comps.append(Comparator.model_validate(data))
        except Exception:
            # on ignore les fichiers corrompus
            continue
    return comps


def save_comparator(c: Comparator) -> Path:
    return save_model(c, COMPARATORS_DIR, c.filename)


def delete_comparator_by_reference(reference: str) -> bool:
    base = reference.strip().replace(" ", "_")
    fp = _subdir_path(COMPARATORS_DIR) / f"{base}.json"
    if fp.exists():
        fp.unlink()
        return True
    return False


def upsert_comparator(c: Comparator) -> Path:
    """Ajoute ou remplace un comparateur."""
    return save_comparator(c)


# ---------- Sessions ----------
SESSIONS_DIR = "sessions"


def save_session(s: Session, filename: Optional[str] = None) -> Path:
    if filename is None:
        base = s.operator.strip().replace(" ", "_")
        filename = f"{base}_{s.date.strftime('%Y%m%d_%H%M%S')}.json"
    return save_model(s, SESSIONS_DIR, filename)
