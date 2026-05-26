from __future__ import annotations

import json
from typing import Any

from versa.models.state import Fact, OpenQuestion, TaskState
from versa.policy import REQUIREMENTS_DOC_SLOTS
from versa.reducer import active_facts, find_active_fact


SECTION_ORDER: list[tuple[str, str]] = [
    ("scope", "# Overview"),
    ("target_users", "# Target Users"),
    ("functional_requirements", "# Functional Requirements"),
    ("non_functional_requirements", "# Non-Functional Requirements"),
    ("constraints", "# Constraints"),
    ("success_criteria", "# Success Criteria"),
]


def _format_value(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value)
    if isinstance(value, dict):
        return json.dumps(value, indent=2)
    return str(value)


def _fact_by_key(facts: list[Fact], key: str) -> Fact | None:
    for fact in facts:
        if fact.key == key:
            return fact
    return None


def _open_questions_section(questions: list[OpenQuestion]) -> str:
    blocking = [q.question for q in questions if q.blocks_progress]
    if not blocking:
        return ""
    lines = ["# Open Questions", ""]
    lines.extend(f"- {question}" for question in blocking)
    return "\n".join(lines)


def render_requirements_markdown(state: TaskState) -> str:
    """Render authoritative facts as markdown without calling an LLM."""
    facts = active_facts(state)
    sections: list[str] = []

    objective = find_active_fact(state, "objective")
    if objective:
        sections.append("# Requirements Document")
        sections.append("")
        sections.append(f"**Objective:** {objective.value}")
        sections.append("")

    for key, heading in SECTION_ORDER:
        fact = _fact_by_key(facts, key)
        if not fact:
            continue
        sections.append(heading)
        sections.append("")
        sections.append(_format_value(fact.value))
        sections.append("")

    other_facts = [
        fact
        for fact in facts
        if fact.key not in {slot for slot, _ in SECTION_ORDER}
        and fact.key != "objective"
        and fact.key != "synthesis_requested"
    ]
    if other_facts:
        sections.append("# Additional Facts")
        sections.append("")
        for fact in other_facts:
            sections.append(f"## {fact.key}")
            sections.append("")
            sections.append(_format_value(fact.value))
            if fact.source.quote:
                sections.append("")
                sections.append(f"> Evidence: {fact.source.quote}")
            sections.append("")

    open_questions = _open_questions_section(state.open_questions)
    if open_questions:
        sections.append(open_questions)
        sections.append("")

    if not sections:
        return "# Requirements Document\n\nNo requirements captured yet."

    return "\n".join(sections).strip() + "\n"


def content_slot_keys() -> list[str]:
    return [slot for slot in REQUIREMENTS_DOC_SLOTS if slot != "synthesis_requested"]
