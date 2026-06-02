"""Logique partagée de matching par intervalles de course (semi-ouverts)."""

from __future__ import annotations

from typing import List, Protocol, TypeVar

EPS = 1e-6


def feq(a: float, b: float, eps: float = EPS) -> bool:
    return abs(a - b) <= eps


class _CourseRule(Protocol):
    graduation: float
    course_min: float | None
    course_max: float | None


R = TypeVar("R", bound=_CourseRule)


def match_course_group_strict(rules_same_grad: List[R], course: float, eps: float = EPS) -> List[R]:
    """
    Intervalles par graduation :
    - première règle : [course_min, course_max] inclusif ;
    - suivantes : (course_min, course_max] (min exclusif, max inclusif).
    """
    rules_sorted = sorted(rules_same_grad, key=lambda r: (r.course_max, r.course_min))
    matches: List[R] = []
    for i, r in enumerate(rules_sorted):
        cmin = r.course_min if r.course_min is not None else float("-inf")
        cmax = r.course_max if r.course_max is not None else float("inf")
        if i == 0:
            if cmin - eps <= course <= cmax + eps:
                matches.append(r)
        else:
            if course > cmin + eps and course <= cmax + eps:
                matches.append(r)
    return matches


def detect_course_overlaps(rules_same_grad: List[R], eps: float = EPS) -> bool:
    """True si deux intervalles de même graduation se chevauchent."""
    lst_sorted = sorted(rules_same_grad, key=lambda r: (r.course_max, r.course_min))
    for i in range(len(lst_sorted) - 1):
        prev = lst_sorted[i]
        nxt = lst_sorted[i + 1]
        if nxt.course_min is None or prev.course_max is None:
            continue
        if nxt.course_min < prev.course_max - eps:
            return True
    return False
