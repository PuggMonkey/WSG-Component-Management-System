"""
Repository layer 

Keeps SQL isolated from the CLI/service logic to improve maintainability.
"""

import sqlite3
from typing import Optional

from component import Component


def create_component(conn: sqlite3.Connection, component: Component) -> int:
    # Parameterised query prevents SQL injection and avoids manual quoting/escaping.
    cur = conn.execute(
        """
        INSERT INTO components (name, description, status, quantity, min_quantity)
        VALUES (?, ?, ?, ?, ?)
        """,
        (component.name, component.description, component.status, component.quantity, component.min_quantity),
    )
    # SQLite should always provide a rowid for INSERTs into rowid tables.
    if cur.lastrowid is None:
        raise RuntimeError("Failed to create component: no rowid returned.")
    return int(cur.lastrowid)


def get_component(conn: sqlite3.Connection, component_id: int) -> Optional[Component]:
    # Read a single component by its unique integer id.
    row = conn.execute(
        "SELECT id, name, description, status, quantity, min_quantity FROM components WHERE id = ?",
        (component_id,),
    ).fetchone()
    if row is None:
        return None
    return Component(
        id=int(row["id"]),
        name=str(row["name"]),
        description=str(row["description"]),
        status=str(row["status"]),
        quantity=int(row["quantity"]),
        min_quantity=int(row["min_quantity"]),
    )


def get_component_by_name(conn: sqlite3.Connection, name: str) -> Optional[Component]:
    # Name is unique in the schema; this is used to prevent duplicates on creation.
    row = conn.execute(
        "SELECT id, name, description, status, quantity, min_quantity FROM components WHERE name = ?",
        (name,),
    ).fetchone()
    if row is None:
        return None
    return Component(
        id=int(row["id"]),
        name=str(row["name"]),
        description=str(row["description"]),
        status=str(row["status"]),
        quantity=int(row["quantity"]),
        min_quantity=int(row["min_quantity"]),
    )


def list_components(conn: sqlite3.Connection) -> list[Component]:
    # Return all components in a consistent, human-friendly order (name A-Z).
    rows = conn.execute(
        "SELECT id, name, description, status, quantity, min_quantity FROM components ORDER BY name ASC"
    ).fetchall()
    return [
        Component(
            id=int(r["id"]),
            name=str(r["name"]),
            description=str(r["description"]),
            status=str(r["status"]),
            quantity=int(r["quantity"]),
            min_quantity=int(r["min_quantity"]),
        )
        for r in rows
    ]


def update_component_status(conn: sqlite3.Connection, component_id: int, new_status: str) -> None:
    # Keep `updated_at` in sync whenever the persisted state changes.
    conn.execute(
        "UPDATE components SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (new_status, component_id),
    )


def update_component_quantity(conn: sqlite3.Connection, component_id: int, new_quantity: int) -> None:
    # Quantity updates are performed in the service layer after validation.
    conn.execute(
        "UPDATE components SET quantity = ?, updated_at = datetime('now') WHERE id = ?",
        (new_quantity, component_id),
    )


def update_component_min_quantity(conn: sqlite3.Connection, component_id: int, min_quantity: int) -> None:
    # Threshold changes can affect replenishment status (service layer publishes events).
    conn.execute(
        "UPDATE components SET min_quantity = ?, updated_at = datetime('now') WHERE id = ?",
        (min_quantity, component_id),
    )


def add_log(
    conn: sqlite3.Connection,
    component_id: int,
    user_name: str,
    action: str,
    message: str = "",
    *,
    status_before: Optional[str] = None,
    status_after: Optional[str] = None,
    qty_before: Optional[int] = None,
    qty_after: Optional[int] = None,
) -> int:
    # Logs provide an audit trail of operational changes and user actions.
    cur = conn.execute(
        """
        INSERT INTO logs (component_id, user_name, action, message, status_before, status_after, qty_before, qty_after)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (component_id, user_name, action, message, status_before, status_after, qty_before, qty_after),
    )
    if cur.lastrowid is None:
        raise RuntimeError("Failed to create log entry: no rowid returned.")
    return int(cur.lastrowid)


def list_logs(conn: sqlite3.Connection, component_id: Optional[int] = None, limit: int = 50) -> list[sqlite3.Row]:
    # Fetch most-recent-first logs for either a specific component or for all components.
    if component_id is None:
        return conn.execute(
            """
            SELECT id, component_id, timestamp, user_name, action, message, status_before, status_after, qty_before, qty_after
            FROM logs
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return conn.execute(
        """
        SELECT id, component_id, timestamp, user_name, action, message, status_before, status_after, qty_before, qty_after
        FROM logs
        WHERE component_id = ?
        ORDER BY timestamp DESC, id DESC
        LIMIT ?
        """,
        (component_id, limit),
    ).fetchall()


def list_low_stock(conn: sqlite3.Connection) -> list[Component]:
    # Stock is considered low when quantity <= min_quantity.
    rows = conn.execute(
        """
        SELECT id, name, description, status, quantity, min_quantity
        FROM components
        WHERE quantity <= min_quantity
        ORDER BY (min_quantity - quantity) DESC, name ASC
        """
    ).fetchall()
    return [
        Component(
            id=int(r["id"]),
            name=str(r["name"]),
            description=str(r["description"]),
            status=str(r["status"]),
            quantity=int(r["quantity"]),
            min_quantity=int(r["min_quantity"]),
        )
        for r in rows
    ]

