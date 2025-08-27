from pydantic import BaseModel, Field
from typing import List, Optional

class Comparator(BaseModel):
    reference: str
    manufacturer: Optional[str] = None
    description: Optional[str] = None
    targets: List[float] = Field(default_factory=list)
