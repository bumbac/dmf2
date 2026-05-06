from __future__ import annotations

from .domain import MessageRecord, PlanRecord, ProgressRecord, SummaryRecord
from .repository import Repository


class MemoryService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def append_message(self, record: MessageRecord) -> MessageRecord:
        return self.repository.add_message(record)

    def recent_messages(self, session_id: str, limit: int = 12) -> list[MessageRecord]:
        return self.repository.list_messages(session_id)[-limit:]

    def update_summary(self, session_id: str) -> SummaryRecord:
        messages = self.repository.list_messages(session_id)
        tail = messages[-8:]
        content = "\n".join(f"[{item.role}] {item.content}" for item in tail)
        record = SummaryRecord(session_id=session_id, content=content or "No conversation yet.")
        return self.repository.upsert_summary(record)

    def latest_summary(self, session_id: str) -> SummaryRecord | None:
        return self.repository.latest_summary(session_id)

    def set_plan(self, session_id: str, content: str) -> PlanRecord:
        return self.repository.upsert_plan(PlanRecord(session_id=session_id, content=content))

    def latest_plan(self, session_id: str) -> PlanRecord | None:
        return self.repository.latest_plan(session_id)

    def add_progress(self, record: ProgressRecord) -> ProgressRecord:
        return self.repository.add_progress(record)

    def list_progress(self, session_id: str) -> list[ProgressRecord]:
        return self.repository.list_progress(session_id)
