"""
Component domain model.

This file defines the core data + validation rules for a tracked component.
"""

from dataclasses import dataclass, field
from typing import Optional

from user import User


@dataclass
class Component:
    """
    Represents a physical/electronic component being tracked.

    Fields are kept simple so they map cleanly to SQLite columns.
    """

    # Keeping statuses as a small fixed set simplifies validation and reporting.
    allowed_statuses = ("active", "idle", "defected", "retired")

    id: Optional[int]
    name: str
    description: str = ""
    status: str = "idle"
    quantity: int = 0
    min_quantity: int = 0
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Protects service/repository layers from bad data.
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Component name must be a non-empty string.")
        if self.status not in self.allowed_statuses:
            raise ValueError(
                f"Invalid status '{self.status}'. Allowed: {', '.join(self.allowed_statuses)}"
            )
        if not isinstance(self.quantity, int) or self.quantity < 0:
            raise ValueError("Quantity must be an integer >= 0.")
        if not isinstance(self.min_quantity, int) or self.min_quantity < 0:
            raise ValueError("min_quantity must be an integer >= 0.")

    def add_note(self, note: str) -> None:
        """Adds an operational note."""
        if not isinstance(note, str) or not note.strip():
            raise ValueError("Note must be a non-empty string.")
        self.notes.append(note.strip())

    def update_status(self, user: User, new_status: str) -> None:
        """Updates the component status (validation only; persistence handled elsewhere)."""
        _ = user  # kept for audit/logging parity in service layer
        if new_status not in self.allowed_statuses:
            raise ValueError(
                f"Invalid status '{new_status}'. Allowed: {', '.join(self.allowed_statuses)}"
            )
        self.status = new_status

    def adjust_quantity(self, user: User, delta: int) -> None:
        """Adjusts quantity by delta, can be positive or 
        negative but resulting value cannot go below zero."""
        _ = user  # kept for audit/logging parity in service layer
        if not isinstance(delta, int):
            raise ValueError("Quantity delta must be an integer.")
        new_qty = self.quantity + delta
        if new_qty < 0:
            raise ValueError("Quantity cannot go below 0.")
        self.quantity = new_qty

    def requires_replenishment(self) -> bool:
        """True when quantity is at/below the replenishment threshold."""
        return self.quantity <= self.min_quantity