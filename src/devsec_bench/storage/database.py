"""SQLite tables remain separate from benchmark domain objects."""

import json
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from devsec_bench.models import Run, ScenarioResult, ToolEvent
from devsec_bench.tools.policies import sanitize


class Base(DeclarativeBase):
    pass


class RunRow(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[str] = mapped_column(String, index=True)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)


class ResultRow(Base):
    __tablename__ = "results"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    scenario: Mapped[str] = mapped_column(String)
    repetition: Mapped[int]
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)


class EventRow(Base):
    __tablename__ = "tool_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    sequence: Mapped[int]
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)


def sanitized_run(run: Run) -> Run:
    def clean(value: Any) -> Any:
        if isinstance(value, str):
            return sanitize(value)
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    return Run.model_validate(clean(run.model_dump(mode="json")))


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{path.resolve().as_posix()}", connect_args={"timeout": 30})
        Base.metadata.create_all(self.engine)

    def save(self, run: Run) -> None:
        run = sanitized_run(run)
        with Session(self.engine) as session, session.begin():
            old = session.get(RunRow, run.id)
            if old:
                results = session.scalars(select(ResultRow).where(ResultRow.run_id == run.id)).all()
                for result in results:
                    for event in session.scalars(select(EventRow).where(EventRow.result_id == result.id)):
                        session.delete(event)
                    session.delete(result)
                old.snapshot = run.model_dump(mode="json", exclude={"results"})
            else:
                session.add(RunRow(id=run.id, timestamp=run.timestamp, snapshot=run.model_dump(mode="json", exclude={"results"})))
            session.flush()
            for result in run.results:
                row = ResultRow(run_id=run.id, scenario=result.scenario, repetition=result.repetition, snapshot=result.model_dump(mode="json", exclude={"events"}))
                session.add(row)
                session.flush()
                for event in result.events:
                    session.add(EventRow(result_id=row.id, sequence=event.sequence, snapshot=event.model_dump(mode="json")))

    def get(self, run_id: str) -> Run:
        with Session(self.engine) as session:
            row = session.get(RunRow, run_id)
            if row is None:
                raise ValueError("Run not found")
            results = []
            for result in session.scalars(select(ResultRow).where(ResultRow.run_id == run_id).order_by(ResultRow.scenario, ResultRow.repetition)):
                events = [ToolEvent.model_validate(event.snapshot) for event in session.scalars(select(EventRow).where(EventRow.result_id == result.id).order_by(EventRow.sequence))]
                results.append(ScenarioResult.model_validate({**result.snapshot, "events": events}))
            return Run.model_validate({**row.snapshot, "results": results})

    def list_runs(self) -> list[Run]:
        with Session(self.engine) as session:
            ids = list(session.scalars(select(RunRow.id).order_by(RunRow.timestamp.desc())))
        return [self.get(run_id) for run_id in ids]

    def latest(self) -> Run:
        with Session(self.engine) as session:
            run_id = session.scalar(select(RunRow.id).order_by(RunRow.timestamp.desc()).limit(1))
        if run_id is None:
            raise ValueError("No benchmark runs; run the reference agent first")
        return self.get(run_id)
