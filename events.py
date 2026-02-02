"""
The CLI + service layer publish events when interesting state changes occur.
"""

from dataclasses import dataclass
from typing import Any, Callable, DefaultDict
from collections import defaultdict

@dataclass(frozen=True)
class Event:
    """Base event type."""
    name: str
    payload: dict[str, Any]


class EventBus:
    """Simple synchronous pub/sub event bus."""

    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, list[Callable[[Event], None]]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        # Registers a handler for a specific event name.
        if not isinstance(event_name, str) or not event_name.strip():
            raise ValueError("event_name must be a non-empty string.")
        self._subscribers[event_name].append(handler)

    def publish(self, event: Event) -> None:
        # Synchronous publish keeps behaviour deterministic for a prototype.
        for handler in list(self._subscribers.get(event.name, [])):
            handler(event)

