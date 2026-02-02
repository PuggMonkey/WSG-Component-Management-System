"""
User domain model.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class User:
    """Represents an engineer/operator using the tool."""

    id: Optional[int]
    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("User name must be a non-empty string.")

    def __str__(self) -> str:
        return f"User(id={self.id}, name='{self.name}')"