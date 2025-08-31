from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class MeasureSeries(BaseModel):
    target: float                                    # valeur cible (mm)
    readings: List[float] = Field(default_factory=list)  # relevés réels (mm)


class Session(BaseModel):
    # Métadonnées
    operator: str
    date: datetime = datetime.now()
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    comparator_ref: Optional[str] = None

    # Paramétrage de campagne
    series_count: int = 0
    measures_per_series: int = 0
    observations: Optional[str] = None

    # Données de mesures
    series: List[MeasureSeries] = Field(default_factory=list)

    def has_measures(self) -> bool:
        return any(len(s.readings) > 0 for s in self.series)

    def total_readings(self) -> int:
        return sum(len(s.readings) for s in self.series)
