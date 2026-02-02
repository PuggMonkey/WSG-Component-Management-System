"""
Command-line interface (CLI) for the prototype.

This module intentionally uses structured constructs (loops/selection) and
demonstrates event-driven behaviour via EventBus subscriptions.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from component import Component
from db import get_connection, init_db
from events import Event, EventBus
from services import ComponentService
from user import User


def _prompt_non_empty(prompt: str) -> str:
    # Keep prompting until user provides a non-empty string.
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Input cannot be empty. Please try again.")


def _prompt_int(prompt: str, *, min_value: Optional[int] = None, default: Optional[int] = None) -> int:
    # Keep prompting until user provides a valid integer (with optional min constraint).
    while True:
        raw = input(prompt).strip()
        if raw == "" and default is not None:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a valid whole number (integer).")
            continue

        if min_value is not None and value < min_value:
            print(f"Please enter a value >= {min_value}.")
            continue

        return value


def _print_component(c: Component) -> None:
    # Utility function for listing components.
    low_flag = "YES" if c.requires_replenishment() else "NO"
    print(
        f"- id={c.id} | name={c.name} | status={c.status} | qty={c.quantity} | "
        f"min={c.min_quantity} | replenish={low_flag}"
    )


def _handle_low_stock(event: Event) -> None:
    # UI prints alerts, but service layer stays UI-agnostic.
    name = event.payload.get("name", "<unknown>")
    qty = event.payload.get("quantity", "<unknown>")
    component_id = event.payload.get("component_id", "<unknown>")
    print(f"\n[ALERT] LOW STOCK: component id={component_id} '{name}' has quantity={qty}\n")


def run(db_path: str = "wsg_components.db") -> None:
    print("WSG Component Tracking & Logging Tool (Prototype)")
    print("------------------------------------------------")

    user_name = _prompt_non_empty("Enter your name (for audit logging): ")
    user = User(id=None, name=user_name)

    bus = EventBus()
    
    # Subscribe UI handler to low-stock events.
    bus.subscribe("LOW_STOCK", _handle_low_stock)

    conn = get_connection(db_path)
    # Ensure schema exists before the user can interact.
    init_db(conn)
    service = ComponentService(conn, bus)

    try:
        while True:
            # Main menu loop + selection-based dispatch.
            print("\nMenu:")
            print(" 1) List components")
            print(" 2) Add component")
            print(" 3) Update component status")
            print(" 4) Adjust quantity (+/-)")
            print(" 5) Set replenishment threshold (min quantity)")
            print(" 6) View logs for a component")
            print(" 7) View recent logs (all components)")
            print(" 8) List components requiring replenishment")
            print(" 9) Exit")

            choice = _prompt_int("Choose an option: ", min_value=1)

            if choice == 1:
                # Read-only listing.
                components = service.list_components()
                if not components:
                    print("No components found.")
                else:
                    for c in components:
                        _print_component(c)

            elif choice == 2:
                # Prompt for a new component.
                name = _prompt_non_empty("Component name: ")
                description = input("Description (optional): ").strip()
                status = input("Status (active/idle/defected/retired) [idle]: ").strip() or "idle"
                quantity = _prompt_int("Quantity (>= 0): ", min_value=0)
                min_qty = _prompt_int("Min quantity threshold (>= 0): ", min_value=0)

                # Create and add the component.
                comp = Component(
                    id=None,
                    name=name,
                    description=description,
                    status=status,
                    quantity=quantity,
                    min_quantity=min_qty,
                )

                try:
                    new_id = service.add_component(user, comp)
                    print(f"Created component id={new_id}.")
                except (ValueError, RuntimeError) as e:
                    print(f"Error: {e}")

            elif choice == 3:
                # Status update + audit log.
                component_id = _prompt_int("Component id: ", min_value=1)
                new_status = _prompt_non_empty("New status (active/idle/defected/retired): ")
                message = input("Log message (optional): ").strip()
                try:
                    service.update_status(user, component_id, new_status, message)
                    print("Status updated.")
                except (ValueError, RuntimeError) as e:
                    print(f"Error: {e}")

            elif choice == 4:
                # Quantity adjustment can be positive (restock) or negative (consume).
                component_id = _prompt_int("Component id: ", min_value=1)
                delta = _prompt_int("Delta (e.g., 5 or -2): ")
                message = input("Log message (optional): ").strip()
                try:
                    service.adjust_quantity(user, component_id, delta, message)
                    print("Quantity updated.")
                except (ValueError, RuntimeError) as e:
                    print(f"Error: {e}")

            elif choice == 5:
                # Update replenishment threshold (min quantity).
                component_id = _prompt_int("Component id: ", min_value=1)
                min_qty = _prompt_int("New min quantity (>= 0): ", min_value=0)
                message = input("Log message (optional): ").strip()
                try:
                    service.set_min_quantity(user, component_id, min_qty, message)
                    print("Min quantity updated.")
                except (ValueError, RuntimeError) as e:
                    print(f"Error: {e}")

            elif choice == 6:
                # Component-specific logs support operational traceability.
                component_id = _prompt_int("Component id: ", min_value=1)
                limit = _prompt_int("How many log entries? [50]: ", min_value=1, default=50)
                rows = service.list_logs(component_id=component_id, limit=limit)
                if not rows:
                    print("No logs found for that component.")
                else:
                    for r in rows:
                        print(
                            f"- {r['timestamp']} | user={r['user_name']} | action={r['action']} | "
                            f"msg={r['message']}"
                        )

            elif choice == 7:
                # Global logs show recent activity across the system.
                limit = _prompt_int("How many log entries? [50]: ", min_value=1, default=50)
                rows = service.list_logs(component_id=None, limit=limit)
                if not rows:
                    print("No logs found.")
                else:
                    for r in rows:
                        print(
                            f"- {r['timestamp']} | component_id={r['component_id']} | user={r['user_name']} | "
                            f"action={r['action']} | msg={r['message']}"
                        )

            elif choice == 8:
                # List components requiring replenishment.
                low = service.list_low_stock()
                if not low:
                    print("No components currently require replenishment.")
                else:
                    print("Components requiring replenishment:")
                    for c in low:
                        _print_component(c)

            elif choice == 9:
                # Exit the program cleanly.
                print("Goodbye.")
                return

            else:
                print("Invalid choice. Please try again.")

    except KeyboardInterrupt:
        print("\nExiting...")
    except sqlite3.Error as e:
        print(f"Fatal database error: {e}")
    finally:
        conn.close()

