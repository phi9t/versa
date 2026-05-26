from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Input, TabbedContent, TabPane
from textual.worker import get_current_worker

from versa.api.dtos import Readiness, SessionSnapshot
from versa.gather.session import GatherSession
from versa.gather.tabs import GATHER_TAB_ORDER, GatherTab, TAB_LABELS
from versa.gather.tui.widgets import (
    ChatView,
    DocumentView,
    ExportView,
    FactsView,
    QuestionsView,
    SlotsView,
    StatsBar,
)
from versa.llm.codex_cli import CodexExecError

if TYPE_CHECKING:
    pass


class GatherApp(App):
    """Terminal requirements gatherer using the same controller as the web UI."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #stats-bar {
        height: 1;
        background: $surface;
        color: $text;
        padding: 0 1;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 1 1;
    }

    .view-panel {
        height: 100%;
        overflow-y: auto;
        border: solid $primary;
    }

    #message-input {
        dock: bottom;
        margin: 0 1 1 1;
    }

    #error-banner {
        dock: bottom;
        height: auto;
        max-height: 3;
        background: $error;
        color: $text;
        padding: 0 1;
        display: none;
    }

    #error-banner.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+e", "export_md", "Export MD"),
        Binding("1", "tab_chat", "Chat", show=False),
        Binding("2", "tab_facts", "Facts", show=False),
        Binding("3", "tab_slots", "Slots", show=False),
        Binding("4", "tab_questions", "Questions", show=False),
        Binding("5", "tab_document", "Document", show=False),
        Binding("6", "tab_export", "Export", show=False),
    ]

    def __init__(self, session: GatherSession, task_id: str) -> None:
        super().__init__()
        self.session = session
        self.task_id = task_id
        self.snapshot: SessionSnapshot | None = None
        self._pending = False
        self._views: dict[GatherTab, object] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield StatsBar(id="stats-bar")
        with TabbedContent():
            for tab in GATHER_TAB_ORDER:
                with TabPane(TAB_LABELS[tab], id=f"pane-{tab.value}"):
                    view = self._make_view(tab)
                    view.add_class("view-panel")
                    self._views[tab] = view
                    yield view
        yield Input(
            placeholder="Describe a requirement or answer a clarification...",
            id="message-input",
        )
        yield Footer()

    def _make_view(self, tab: GatherTab):
        if tab == GatherTab.CHAT:
            return ChatView()
        if tab == GatherTab.FACTS:
            return FactsView()
        if tab == GatherTab.SLOTS:
            return SlotsView()
        if tab == GatherTab.QUESTIONS:
            return QuestionsView()
        if tab == GatherTab.DOCUMENT:
            return DocumentView()
        return ExportView()

    async def on_mount(self) -> None:
        self.title = f"Versa Gather — {self.task_id}"
        self.sub_title = "Requirements gathering TUI"
        await self._reload_snapshot()

    async def _reload_snapshot(self) -> None:
        self.snapshot = await self.session.load(self.task_id)
        self._refresh_views()
        if self.snapshot.readiness == Readiness.SYNTHESIZED:
            self._activate_tab(GatherTab.DOCUMENT)

    def _refresh_views(self) -> None:
        if self.snapshot is None:
            return
        self.query_one("#stats-bar", StatsBar).update_snapshot(self.snapshot)
        for tab, view in self._views.items():
            if hasattr(view, "update_snapshot"):
                view.update_snapshot(self.snapshot)

    def _set_pending(self, pending: bool) -> None:
        self._pending = pending
        input_widget = self.query_one("#message-input", Input)
        input_widget.disabled = pending

    def _activate_tab(self, tab: GatherTab) -> None:
        tabbed = self.query_one(TabbedContent)
        tabbed.active = f"pane-{tab.value}"

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text or self._pending:
            return
        event.input.value = ""
        self.run_worker(self._send_turn(text), exclusive=True)

    async def _send_turn(self, text: str) -> None:
        worker = get_current_worker()
        self._set_pending(True)
        try:
            response = await self.session.send(self.task_id, text)
            if worker.is_cancelled:
                return
            self.snapshot = response.snapshot
            self._refresh_views()
            if self.snapshot.readiness == Readiness.SYNTHESIZED:
                self._activate_tab(GatherTab.DOCUMENT)
        except (CodexExecError, ValidationError) as exc:
            self.notify(str(exc), severity="error", timeout=8)
        finally:
            self._set_pending(False)

    def action_tab_chat(self) -> None:
        self._activate_tab(GatherTab.CHAT)

    def action_tab_facts(self) -> None:
        self._activate_tab(GatherTab.FACTS)

    def action_tab_slots(self) -> None:
        self._activate_tab(GatherTab.SLOTS)

    def action_tab_questions(self) -> None:
        self._activate_tab(GatherTab.QUESTIONS)

    def action_tab_document(self) -> None:
        self._activate_tab(GatherTab.DOCUMENT)

    def action_tab_export(self) -> None:
        self._activate_tab(GatherTab.EXPORT)

    async def action_export_md(self) -> None:
        await self._load_export("md")

    async def on_key(self, event) -> None:
        tabbed = self.query_one(TabbedContent)
        active = tabbed.active or ""
        if not active.endswith("export"):
            return
        if event.key == "m":
            await self._load_export("md")
            event.prevent_default()
        elif event.key == "j":
            await self._load_export("json")
            event.prevent_default()

    async def _load_export(self, fmt: str) -> None:
        try:
            export = await self.session.export(self.task_id, fmt)  # type: ignore[arg-type]
        except Exception as exc:
            self.notify(str(exc), severity="error", timeout=8)
            return
        export_view = self._views[GatherTab.EXPORT]
        if isinstance(export_view, ExportView):
            export_view.show_export(export.content, fmt)
        self._activate_tab(GatherTab.EXPORT)
        self.notify(f"Loaded {fmt.upper()} export", timeout=3)


def run_gather_app(session: GatherSession, task_id: str) -> None:
    GatherApp(session, task_id).run()
