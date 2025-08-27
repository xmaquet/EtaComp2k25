from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Session(BaseModel):
    operator: str
    date: datetime = datetime.now()
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    comparator_ref: Optional[str] = None
    series_count: int = 0
    measures_per_series: int = 0
    observations: Optional[str] = None
