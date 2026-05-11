from __future__ import annotations

import asyncio

from sqlalchemy import desc, select

from .domain import ArtifactRecord, EventRecord, MessageRecord, PlanRecord, ProgressRecord, SessionRecord, SummaryRecord
from .storage import ArtifactTable, Database, EventTable, MessageTable, PlanTable, ProgressTable, SessionTable, SummaryTable


class Repository:
    def __init__(self, database: Database):
        self.database = database

    async def create_session(self, record: SessionRecord) -> SessionRecord:
        def operation() -> SessionRecord:
            with self.database.session() as db:
                db.add(SessionTable(**record.model_dump()))
            return record

        return await asyncio.to_thread(operation)

    async def update_session_status(self, session_id: str, status: str) -> None:
        def operation() -> None:
            with self.database.session() as db:
                row = db.get(SessionTable, session_id)
                if row is None:
                    return
                row.status = status

        await asyncio.to_thread(operation)

    async def get_session(self, session_id: str) -> SessionRecord | None:
        def operation() -> SessionRecord | None:
            with self.database.session() as db:
                row = db.get(SessionTable, session_id)
                if row is None:
                    return None
                return SessionRecord.model_validate(row, from_attributes=True)

        return await asyncio.to_thread(operation)

    async def list_sessions(self) -> list[SessionRecord]:
        def operation() -> list[SessionRecord]:
            with self.database.session() as db:
                rows = db.execute(select(SessionTable).order_by(SessionTable.created_at.asc())).scalars()
                return [SessionRecord.model_validate(row, from_attributes=True) for row in rows]

        return await asyncio.to_thread(operation)

    async def list_child_sessions(self, parent_session_id: str) -> list[SessionRecord]:
        def operation() -> list[SessionRecord]:
            with self.database.session() as db:
                rows = db.execute(
                    select(SessionTable)
                    .where(SessionTable.parent_session_id == parent_session_id)
                    .order_by(SessionTable.created_at.asc())
                ).scalars()
                return [SessionRecord.model_validate(row, from_attributes=True) for row in rows]

        return await asyncio.to_thread(operation)

    async def add_message(self, record: MessageRecord) -> MessageRecord:
        def operation() -> MessageRecord:
            with self.database.session() as db:
                db.add(MessageTable(**record.model_dump()))
            return record

        return await asyncio.to_thread(operation)

    async def list_messages(self, session_id: str) -> list[MessageRecord]:
        def operation() -> list[MessageRecord]:
            with self.database.session() as db:
                rows = db.execute(
                    select(MessageTable).where(MessageTable.session_id == session_id).order_by(MessageTable.created_at.asc())
                ).scalars()
                return [MessageRecord.model_validate(row, from_attributes=True) for row in rows]

        return await asyncio.to_thread(operation)

    async def upsert_summary(self, record: SummaryRecord) -> SummaryRecord:
        def operation() -> SummaryRecord:
            with self.database.session() as db:
                db.add(SummaryTable(**record.model_dump()))
            return record

        return await asyncio.to_thread(operation)

    async def latest_summary(self, session_id: str) -> SummaryRecord | None:
        def operation() -> SummaryRecord | None:
            with self.database.session() as db:
                row = db.execute(
                    select(SummaryTable).where(SummaryTable.session_id == session_id).order_by(desc(SummaryTable.created_at)).limit(1)
                ).scalar_one_or_none()
                if row is None:
                    return None
                return SummaryRecord.model_validate(row, from_attributes=True)

        return await asyncio.to_thread(operation)

    async def upsert_plan(self, record: PlanRecord) -> PlanRecord:
        def operation() -> PlanRecord:
            with self.database.session() as db:
                db.add(PlanTable(**record.model_dump()))
            return record

        return await asyncio.to_thread(operation)

    async def latest_plan(self, session_id: str) -> PlanRecord | None:
        def operation() -> PlanRecord | None:
            with self.database.session() as db:
                row = db.execute(
                    select(PlanTable).where(PlanTable.session_id == session_id).order_by(desc(PlanTable.created_at)).limit(1)
                ).scalar_one_or_none()
                if row is None:
                    return None
                return PlanRecord.model_validate(row, from_attributes=True)

        return await asyncio.to_thread(operation)

    async def add_progress(self, record: ProgressRecord) -> ProgressRecord:
        def operation() -> ProgressRecord:
            with self.database.session() as db:
                db.add(ProgressTable(**record.model_dump()))
            return record

        return await asyncio.to_thread(operation)

    async def list_progress(self, session_id: str) -> list[ProgressRecord]:
        def operation() -> list[ProgressRecord]:
            with self.database.session() as db:
                rows = db.execute(
                    select(ProgressTable).where(ProgressTable.session_id == session_id).order_by(ProgressTable.created_at.asc())
                ).scalars()
                return [ProgressRecord.model_validate(row, from_attributes=True) for row in rows]

        return await asyncio.to_thread(operation)

    async def add_artifact(self, record: ArtifactRecord) -> ArtifactRecord:
        def operation() -> ArtifactRecord:
            with self.database.session() as db:
                existing = db.execute(
                    select(ArtifactTable)
                    .where(ArtifactTable.session_id == record.session_id)
                    .where(ArtifactTable.kind == record.kind)
                    .order_by(desc(ArtifactTable.version))
                    .limit(1)
                ).scalar_one_or_none()
                payload = record.model_dump()
                if existing is not None:
                    payload["version"] = existing.version + 1
                    record.version = payload["version"]
                payload["storage_kind"] = record.storage_kind
                payload["file_path"] = record.file_path
                db.add(ArtifactTable(**payload))
            return record

        return await asyncio.to_thread(operation)

    async def list_artifacts(self, session_id: str) -> list[ArtifactRecord]:
        def operation() -> list[ArtifactRecord]:
            with self.database.session() as db:
                rows = db.execute(
                    select(ArtifactTable).where(ArtifactTable.session_id == session_id).order_by(ArtifactTable.created_at.asc())
                ).scalars()
                return [ArtifactRecord.model_validate(row, from_attributes=True) for row in rows]

        return await asyncio.to_thread(operation)

    async def update_artifact(self, record: ArtifactRecord) -> ArtifactRecord:
        def operation() -> ArtifactRecord:
            with self.database.session() as db:
                row = db.get(ArtifactTable, record.id)
                if row is None:
                    raise ValueError(f"unknown artifact: {record.id}")
                row.session_id = record.session_id
                row.stage_id = record.stage_id
                row.author_agent = record.author_agent
                row.kind = record.kind
                row.title = record.title
                row.content = record.content
                row.storage_kind = record.storage_kind
                row.file_path = record.file_path
                row.version = record.version
                row.created_at = record.created_at
            return record

        return await asyncio.to_thread(operation)

    async def add_event(self, record: EventRecord) -> EventRecord:
        def operation() -> EventRecord:
            with self.database.session() as db:
                db.add(EventTable(**record.model_dump()))
            return record

        return await asyncio.to_thread(operation)

    async def list_events(self, session_id: str) -> list[EventRecord]:
        def operation() -> list[EventRecord]:
            with self.database.session() as db:
                rows = db.execute(
                    select(EventTable).where(EventTable.session_id == session_id).order_by(EventTable.created_at.asc())
                ).scalars()
                return [EventRecord.model_validate(row, from_attributes=True) for row in rows]

        return await asyncio.to_thread(operation)
