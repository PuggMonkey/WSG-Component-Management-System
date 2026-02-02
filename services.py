"""
Service layer
"""

import sqlite3

from typing import Optional

from component import Component
from events import Event, EventBus
from user import User
import repositories as repo


class ComponentService:
    def __init__(self, conn: sqlite3.Connection, event_bus: EventBus) -> None:
        # Service owns the connection and coordinates repository operations + events.
        self._conn = conn
        self._events = event_bus

    def add_component(self, user: User, component: Component) -> int:
        # Business rule: component names must be unique (enforced both here and by DB UNIQUE).
        if repo.get_component_by_name(self._conn, component.name) is not None:
            raise ValueError(f"A component named '{component.name}' already exists.")

        try:
            # Transaction: create component + write log as one unit of work.
            component_id = repo.create_component(self._conn, component)
            repo.add_log(
                self._conn,
                component_id=component_id,
                user_name=user.name,
                action="CREATE_COMPONENT",
                message=f"Created component '{component.name}'.",
                status_after=component.status,
                qty_after=component.quantity,
            )
            self._conn.commit()
        except sqlite3.Error as e:
            # Roll back on any DB error to avoid partial writes.
            self._conn.rollback()
            raise RuntimeError(f"Database error while creating component: {e}") from e

        # Event-driven behaviour: notify subscribers if stock is already low at creation.
        if component.quantity <= component.min_quantity:
            self._events.publish(
                Event(
                    name="LOW_STOCK",
                    payload={"component_id": component_id, "name": component.name, "quantity": component.quantity},
                )
            )
        return component_id

    def update_status(self, user: User, component_id: int, new_status: str, message: str = "") -> None:
        """Updates status and records before/after in the log."""
        self.update_status_with_audit(user, component_id, new_status, message)

    def update_status_with_audit(self, user: User, component_id: int, new_status: str, message: str = "") -> None:
        """Same as update_status, but stores before/after in the log."""
        # Load current state first so we can log before/after for auditability.
        before = repo.get_component(self._conn, component_id)
        if before is None:
            raise ValueError(f"Component id {component_id} not found.")

        # Validation
        # Use the domain model to validate the status value consistently.
        _tmp = Component(
            id=before.id,
            name=before.name,
            description=before.description,
            status=before.status,
            quantity=before.quantity,
            min_quantity=before.min_quantity,
        )
        _tmp.update_status(user, new_status)

        try:
            # Transaction: update persisted state + write a log entry.
            repo.update_component_status(self._conn, component_id, new_status)
            repo.add_log(
                self._conn,
                component_id=component_id,
                user_name=user.name,
                action="UPDATE_STATUS",
                message=message.strip(),
                status_before=before.status,
                status_after=new_status,
            )
            self._conn.commit()
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Database error while updating status: {e}") from e

    def adjust_quantity(self, user: User, component_id: int, delta: int, message: str = "") -> None:
        # Load state so we can validate and also log before/after quantity.
        before = repo.get_component(self._conn, component_id)
        if before is None:
            raise ValueError(f"Component id {component_id} not found.")

        # Validation via domain model
        # Ensures we never persist negative stock levels.
        before.adjust_quantity(user, delta)
        after_qty = before.quantity

        try:
            # Transaction: persist new quantity + log entry.
            repo.update_component_quantity(self._conn, component_id, after_qty)
            repo.add_log(
                self._conn,
                component_id=component_id,
                user_name=user.name,
                action="ADJUST_QUANTITY",
                message=message.strip(),
                qty_before=after_qty - delta,
                qty_after=after_qty,
            )
            self._conn.commit()
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Database error while adjusting quantity: {e}") from e

        # Publish event after commit so handlers don't react to uncommitted state.
        comp = repo.get_component(self._conn, component_id)
        if comp is not None and comp.requires_replenishment():
            # Event consumers (e.g., CLI) can decide how to display/handle the alert.
            self._events.publish(
                Event(
                    name="LOW_STOCK",
                    payload={"component_id": comp.id, "name": comp.name, "quantity": comp.quantity},
                )
            )

    def set_min_quantity(self, user: User, component_id: int, min_quantity: int, message: str = "") -> None:
        # Simple guard: threshold must be a non-negative integer.
        if not isinstance(min_quantity, int) or min_quantity < 0:
            raise ValueError("min_quantity must be an integer >= 0.")

        before = repo.get_component(self._conn, component_id)
        if before is None:
            raise ValueError(f"Component id {component_id} not found.")

        try:
            # Transaction: update threshold + log entry.
            repo.update_component_min_quantity(self._conn, component_id, min_quantity)
            repo.add_log(
                self._conn,
                component_id=component_id,
                user_name=user.name,
                action="SET_MIN_QUANTITY",
                message=(message.strip() or f"min_quantity {before.min_quantity} -> {min_quantity}"),
                qty_before=None,
                qty_after=None,
            )
            self._conn.commit()
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Database error while setting min quantity: {e}") from e

        comp = repo.get_component(self._conn, component_id)
        if comp is not None and comp.requires_replenishment():
            # If a threshold change makes a component "low stock", notify via event.
            self._events.publish(
                Event(
                    name="LOW_STOCK",
                    payload={"component_id": comp.id, "name": comp.name, "quantity": comp.quantity},
                )
            )

    def get_component(self, component_id: int) -> Optional[Component]:
        return repo.get_component(self._conn, component_id)

    def list_components(self) -> list[Component]:
        return repo.list_components(self._conn)

    def list_low_stock(self) -> list[Component]:
        return repo.list_low_stock(self._conn)

    def list_logs(self, component_id: Optional[int] = None, limit: int = 50):
        return repo.list_logs(self._conn, component_id=component_id, limit=limit)

