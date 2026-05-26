from __future__ import annotations

from textual.widgets import Static

from versa.api.dtos import Readiness, SessionSnapshot
from versa.gather import formatters as fmt_module


class StatsBar(Static):
    def update_snapshot(self, snapshot: SessionSnapshot) -> None:
        self.update(fmt_module.format_header_stats(snapshot))


class ChatView(Static):
    def update_snapshot(self, snapshot: SessionSnapshot) -> None:
        hint = fmt_module.chat_hint(snapshot.readiness)
        body = fmt_module.format_messages(snapshot.messages)
        self.update(f"{hint}\n\n{body}")


class FactsView(Static):
    def update_snapshot(self, snapshot: SessionSnapshot) -> None:
        self.update(fmt_module.format_facts(snapshot.facts))


class SlotsView(Static):
    def update_snapshot(self, snapshot: SessionSnapshot) -> None:
        self.update(fmt_module.format_slot_table(snapshot.slots, snapshot.missing_slot_keys))


class QuestionsView(Static):
    def update_snapshot(self, snapshot: SessionSnapshot) -> None:
        self.update(fmt_module.format_questions(snapshot.open_questions))


class DocumentView(Static):
    def update_snapshot(self, snapshot: SessionSnapshot) -> None:
        self.update(
            fmt_module.format_document(snapshot.active_artifact, snapshot.artifact_status)
        )


class ExportView(Static):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._preview = "Press m for Markdown export, j for JSON export."

    def update_snapshot(self, snapshot: SessionSnapshot) -> None:
        self._snapshot = snapshot
        self.update(
            f"{self._preview}\n\nTask: {snapshot.task_id} | "
            f"Readiness: {fmt_module.readiness_label(snapshot.readiness)}"
        )

    def show_export(self, content: str, export_fmt: str) -> None:
        self.update(fmt_module.format_export_preview(content, export_fmt))
