from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    id: str
    email: str
    name: str
    created_at: datetime | str
