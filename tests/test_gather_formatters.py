from __future__ import annotations

from versa.api.dtos import FactView, MessageView, Readiness, SessionSnapshot, SlotStatus
from versa.gather import formatters


def _snapshot(**overrides) -> SessionSnapshot:
    base = SessionSnapshot(
        task_id="demo",
        version=1,
        objective="write_requirements_doc",
        facts=[],
        messages=[],
        open_questions=[],
        slots=[
            SlotStatus(key="scope", label="Project scope", filled=False),
            SlotStatus(key="target_users", label="Target users", filled=True, value_preview="devs"),
        ],
        missing_slot_keys=["scope"],
        readiness=Readiness.GATHERING,
        active_artifact=None,
        artifact_status="none",
    )
    return base.model_copy(update=overrides)


def test_readiness_label():
    assert formatters.readiness_label(Readiness.GATHERING) == "Gathering"
    assert formatters.readiness_label(Readiness.READY_TO_SYNTHESIZE) == "Ready to synthesize"
    assert formatters.readiness_label(Readiness.SYNTHESIZED) == "Synthesized"


def test_format_header_stats():
    text = formatters.format_header_stats(_snapshot())
    assert "Gathering" in text
    assert "Slots: 1/2" in text
    assert "Facts: 0" in text


def test_format_slot_table_shows_missing():
    text = formatters.format_slot_table(
        _snapshot().slots,
        _snapshot().missing_slot_keys,
    )
    assert "Still missing: scope" in text
    assert "○ Project scope" in text or "Project scope (scope)" in text


def test_format_facts_and_messages():
    facts = [
        FactView(
            id="f1",
            kind="requirement",
            key="scope",
            value="demo",
            evidence_quote="demo scope",
            message_id="m1",
        )
    ]
    messages = [
        MessageView(id="m1", role="user", content="hello", created_at="2026-01-01T00:00:00Z")
    ]
    assert "scope = demo" in formatters.format_facts(facts)
    assert "user> hello" in formatters.format_messages(messages)


def test_chat_hint_changes_with_readiness():
    assert "Proceed with synthesis" in formatters.chat_hint(Readiness.READY_TO_SYNTHESIZE)
    assert "plain language" in formatters.chat_hint(Readiness.GATHERING)
