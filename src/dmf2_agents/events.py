from __future__ import annotations

import asyncio
from collections.abc import Callable

from .domain import EventRecord
from .repository import Repository


class EventBus:
    def __init__(self, repository: Repository):
        self.repository = repository
        self._subscribers: list[Callable[[EventRecord], None]] = []

    def subscribe(self, callback: Callable[[EventRecord], None]) -> None:
        self._subscribers.append(callback)

    async def publish(self, event: EventRecord) -> EventRecord:
        await self.repository.add_event(event)
        for callback in self._subscribers:
            await asyncio.to_thread(callback, event)
        return event
