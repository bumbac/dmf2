from __future__ import annotations

from collections.abc import Callable

from .domain import EventRecord
from .repository import Repository


class EventBus:
    def __init__(self, repository: Repository):
        self.repository = repository
        self._subscribers: list[Callable[[EventRecord], None]] = []

    def subscribe(self, callback: Callable[[EventRecord], None]) -> None:
        self._subscribers.append(callback)

    def publish(self, event: EventRecord) -> EventRecord:
        self.repository.add_event(event)
        for callback in self._subscribers:
            callback(event)
        return event
