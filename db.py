"""
SQLite database utilities and schema initialisation.

Design goals:
- Reliable: enables foreign keys and uses simple, explicit schema.
- Maintainable: single place for schema and connection behaviour.
"""

from __future__ import annotations

import sqlite3
from typing import Optional


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Creates a SQLite connection with consistent settings.

    - Row factory enabled for dict-like access
    - Foreign keys enabled (off by default in sqlite)
    """
    conn = sqlite3.connect(db_path)
    # Access rows like dicts: row["column_name"].
    conn.row_factory = sqlite3.Row
    # SQLite requires enabling FK enforcement explicitly for reliability.
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Creates tables if they do not already exist."""
    # One executescript keeps schema creation simple and repeatable.
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS components (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL UNIQUE,
            description  TEXT NOT NULL DEFAULT '',
            status       TEXT NOT NULL,
            quantity     INTEGER NOT NULL DEFAULT 0,
            min_quantity INTEGER NOT NULL DEFAULT 0,
            created_at   TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            component_id    INTEGER NOT NULL,
            timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
            user_name       TEXT NOT NULL,
            action          TEXT NOT NULL,
            message         TEXT NOT NULL DEFAULT '',
            status_before   TEXT,
            status_after    TEXT,
            qty_before      INTEGER,
            qty_after       INTEGER,
            FOREIGN KEY(component_id) REFERENCES components(id) ON DELETE CASCADE
        );

        -- Index supports faster log lookups by component and time.
        CREATE INDEX IF NOT EXISTS idx_logs_component_time
            ON logs(component_id, timestamp);
        """
    )
    conn.commit()


def touch_component_updated_at(conn: sqlite3.Connection, component_id: int) -> None:
    """Updates the `updated_at` timestamp for a component."""
    conn.execute(
        "UPDATE components SET updated_at = datetime('now') WHERE id = ?",
        (component_id,),
    )

