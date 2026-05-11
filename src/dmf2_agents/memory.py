from __future__ import annotations

from .domain import MessageRecord, PlanRecord, ProgressRecord, SummaryRecord
from .repository import Repository


class MemoryService:
    def __init__(self, repository: Repository):
        self.repository = repository

    async def append_message(self, record: MessageRecord) -> MessageRecord:
        return await self.repository.add_message(record)

    async def recent_messages(self, session_id: str, limit: int = 12) -> list[MessageRecord]:
        return (await self.repository.list_messages(session_id))[-limit:]

    async def update_summary(self, session_id: str) -> SummaryRecord:
        messages = await self.repository.list_messages(session_id)
        tail = messages[-8:]
        content = "\n".join(f"[{item.role}] {item.content}" for item in tail)
        record = SummaryRecord(session_id=session_id, content=content or "No conversation yet.")
        return await self.repository.upsert_summary(record)

    async def latest_summary(self, session_id: str) -> SummaryRecord | None:
        return await self.repository.latest_summary(session_id)

    async def set_plan(self, session_id: str, content: str) -> PlanRecord:
        return await self.repository.upsert_plan(PlanRecord(session_id=session_id, content=content))

    async def latest_plan(self, session_id: str) -> PlanRecord | None:
        return await self.repository.latest_plan(session_id)

    async def add_progress(self, record: ProgressRecord) -> ProgressRecord:
        return await self.repository.add_progress(record)

    async def list_progress(self, session_id: str) -> list[ProgressRecord]:
        return await self.repository.list_progress(session_id)
