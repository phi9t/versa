from __future__ import annotations

import json

from versa.api.dtos import FactView, MessageView, Readiness, SessionSnapshot, SlotStatus


def readiness_label(readiness: Readiness) -> str:
    if readiness == Readiness.GATHERING:
        return "Gathering"
    if readiness == Readiness.READY_TO_SYNTHESIZE:
        return "Ready to synthesize"
    return "Synthesized"


def chat_hint(readiness: Readiness) -> str:
    if readiness == Readiness.READY_TO_SYNTHESIZE:
        return 'All content slots filled. Say "Proceed with synthesis" when ready.'
    return (
        "Answer the assistant's question in plain language — "
        "or use Use scope: your answer for a specific slot."
    )


def format_header_stats(snapshot: SessionSnapshot) -> str:
    filled = sum(1 for slot in snapshot.slots if slot.filled)
    total = len(snapshot.slots)
    return (
        f"Readiness: {readiness_label(snapshot.readiness)} | "
        f"Slots: {filled}/{total} | Facts: {len(snapshot.facts)}"
    )


def format_slot_table(slots: list[SlotStatus], missing_slot_keys: list[str]) -> str:
    filled = sum(1 for slot in slots if slot.filled)
    lines = [f"{filled}/{len(slots)} slots filled", ""]
    for slot in slots:
        mark = "✓" if slot.filled else "○"
        line = f"{mark} {slot.label} ({slot.key})"
        if slot.value_preview:
            line += f": {slot.value_preview}"
        lines.append(line)
    if missing_slot_keys:
        lines.append("")
        lines.append(f"Still missing: {', '.join(missing_slot_keys)}")
    if all(slot.filled for slot in slots) and slots:
        lines.insert(1, "Ready to synthesize — send \"Proceed with synthesis\" in Chat.")
        lines.insert(2, "")
    return "\n".join(lines)


def format_facts(facts: list[FactView]) -> str:
    if not facts:
        return "No facts yet."
    lines: list[str] = []
    for fact in facts:
        value = json.dumps(fact.value) if not isinstance(fact.value, str) else fact.value
        lines.append(f"[{fact.kind}] {fact.key} = {value}")
        lines.append(f"  evidence: {fact.evidence_quote}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_messages(messages: list[MessageView]) -> str:
    if not messages:
        return "No messages yet. Start gathering requirements."
    lines: list[str] = []
    for message in messages:
        lines.append(f"{message.role}> {message.content}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_questions(open_questions: list[str]) -> str:
    if not open_questions:
        return "No blocking questions."
    return "\n".join(f"• {question}" for question in open_questions)


def format_document(active_artifact: str | None, artifact_status: str | None) -> str:
    if active_artifact:
        return active_artifact
    if artifact_status == "draft":
        return "Document draft exists but is not verified yet."
    if artifact_status == "failed":
        return "Last synthesis attempt failed verification."
    return "No verified document yet."


def format_export_preview(content: str, fmt: str) -> str:
    header = f"--- export ({fmt}) ---"
    return f"{header}\n{content}"
