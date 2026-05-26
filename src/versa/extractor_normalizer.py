from __future__ import annotations

import json
import re

from versa.models.delta import FactPatch, TurnDelta
from versa.models.state import FactKind, TaskState
from versa.policy import infer_required_slots_for_objective
from versa.reducer import active_fact_keys, find_active_fact

_CANONICAL_OBJECTIVES = frozenset(
    {
        "write_requirements_doc",
        "write_python_function",
        "write_sql_query",
        "write_patch",
        "edit_repository",
        "plan_task",
        "break_down_task",
    }
)

_REQUIREMENTS_PATTERNS = (
    "write_requirements_doc",
    "requirements specification document",
    "gather requirements",
    "collect requirements",
    "requirements doc",
    "requirements for",
)

_PYTHON_FUNCTION_PATTERNS = (
    "python function",
    "write a function",
    "write function",
)

_SQL_PATTERNS = (
    ("sql", "query"),
)

_SCOPE_ALIASES = frozenset(
    {
        "project",
        "subject",
        "product",
        "system",
        "application",
        "task",
        "description",
        "summary",
        "overview",
    }
)

_NO_AUTO_FILL_SLOTS = frozenset({"synthesis_requested", "objective"})


def normalize_turn_delta(
    state: TaskState,
    delta: TurnDelta,
    user_text: str,
    *,
    default_objective: str | None = None,
) -> TurnDelta:
    """Apply deterministic fixes so policy sees canonical facts when intent is clear."""
    delta = delta.model_copy(deep=True)
    explicit = _parse_use_slot_message(user_text)
    if explicit is not None:
        delta.fact_patches = [
            patch for patch in delta.fact_patches if patch.key != explicit.key
        ]
        delta.fact_patches.append(explicit)

    _fix_miskeyed_objective_patches(delta, user_text)
    _fix_noncanonical_objective_values(delta, user_text)
    _coalesce_scope_aliases(delta, user_text)

    if find_active_fact(state, "objective") or _has_objective_patch(delta):
        pass
    else:
        inferred = _infer_objective(user_text)
        if inferred is None and default_objective in _CANONICAL_OBJECTIVES:
            inferred = (default_objective, user_text.strip()[:120] or default_objective)
        if inferred is not None:
            value, quote = inferred
            delta.fact_patches.append(
                FactPatch(
                    op="add",
                    kind=FactKind.OBJECTIVE,
                    key="objective",
                    value=value,
                    evidence_quote=quote,
                )
            )

    _fill_missing_slot_answer(state, delta, user_text, explicit)
    delta.new_questions_for_user = []
    return delta


def _has_objective_patch(delta: TurnDelta) -> bool:
    return any(patch.key == "objective" for patch in delta.fact_patches)


def _parse_use_slot_message(user_text: str) -> FactPatch | None:
    match = re.match(r"use\s+(\w+):\s*(.+)", user_text.strip(), re.I | re.S)
    if not match:
        return None
    key, raw_value = match.group(1), match.group(2).strip()
    value: object = raw_value
    if raw_value.startswith("["):
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
    elif raw_value.lower() in {"true", "false"}:
        value = raw_value.lower() == "true"

    kind = FactKind.REQUIREMENT
    if key in {"constraints", "non_functional_requirements"}:
        kind = FactKind.CONSTRAINT
    if key == "synthesis_requested":
        kind = FactKind.DECISION
        value = True
    if key == "objective":
        kind = FactKind.OBJECTIVE

    return FactPatch(
        op="add",
        kind=kind,
        key=key,
        value=value,
        evidence_quote=match.group(0),
    )


def _fix_miskeyed_objective_patches(delta: TurnDelta, user_text: str) -> None:
    for patch in delta.fact_patches:
        if patch.key == "objective":
            if patch.value in _CANONICAL_OBJECTIVES:
                patch.kind = FactKind.OBJECTIVE
            elif patch.kind == FactKind.OBJECTIVE:
                canonical = _canonicalize_objective_value(str(patch.value), user_text)
                if canonical:
                    patch.value = canonical
            continue

        if patch.kind != FactKind.OBJECTIVE:
            continue

        patch.key = "objective"
        if patch.value in _CANONICAL_OBJECTIVES:
            continue
        canonical = _canonicalize_objective_value(str(patch.value), user_text)
        if canonical:
            patch.value = canonical


def _fix_noncanonical_objective_values(delta: TurnDelta, user_text: str) -> None:
    for patch in delta.fact_patches:
        if patch.key != "objective":
            continue
        if patch.value in _CANONICAL_OBJECTIVES:
            continue
        canonical = _canonicalize_objective_value(str(patch.value), user_text)
        if canonical:
            patch.value = canonical
            continue
        if default := _infer_objective(user_text):
            patch.value = default[0]


def _coalesce_scope_aliases(delta: TurnDelta, user_text: str) -> None:
    if any(patch.key == "scope" for patch in delta.fact_patches):
        return
    alias_patches = [patch for patch in delta.fact_patches if patch.key in _SCOPE_ALIASES]
    if not alias_patches:
        return
    primary = alias_patches[0]
    delta.fact_patches = [patch for patch in delta.fact_patches if patch.key not in _SCOPE_ALIASES]
    delta.fact_patches.append(
        FactPatch(
            op="add",
            kind=FactKind.REQUIREMENT,
            key="scope",
            value=primary.value,
            evidence_quote=primary.evidence_quote,
        )
    )


def _fill_missing_slot_answer(
    state: TaskState,
    delta: TurnDelta,
    user_text: str,
    explicit: FactPatch | None,
) -> None:
    objective = _effective_objective(state, delta)
    if objective != "write_requirements_doc":
        return

    text = user_text.strip()
    if not text or "proceed with synthesis" in text.lower():
        return
    if _infer_objective(user_text) is not None:
        return

    pending_keys = active_fact_keys(state) | {
        patch.key for patch in delta.fact_patches if patch.op in {"add", "update", "supersede"}
    }
    missing = _missing_requirements_slots(objective, pending_keys)
    if not missing:
        return

    first_missing = missing[0]
    if first_missing in _NO_AUTO_FILL_SLOTS:
        return
    if any(patch.key == first_missing for patch in delta.fact_patches):
        return
    if explicit is not None and explicit.key != first_missing:
        return

    kind = FactKind.REQUIREMENT
    if first_missing in {"constraints", "non_functional_requirements"}:
        kind = FactKind.CONSTRAINT

    delta.fact_patches.append(
        FactPatch(
            op="add",
            kind=kind,
            key=first_missing,
            value=text,
            evidence_quote=text[:120],
        )
    )


def _missing_requirements_slots(objective: str, pending_keys: set[str]) -> list[str]:
    if objective == "write_requirements_doc":
        return [slot for slot in infer_required_slots_for_objective(objective) if slot not in pending_keys]
    return []


def _effective_objective(state: TaskState, delta: TurnDelta) -> str | None:
    for patch in delta.fact_patches:
        if patch.key == "objective" and patch.value in _CANONICAL_OBJECTIVES:
            return str(patch.value)
    active = find_active_fact(state, "objective")
    if active and active.value in _CANONICAL_OBJECTIVES:
        return str(active.value)
    return None


def _canonicalize_objective_value(raw: str, user_text: str) -> str | None:
    lowered = raw.lower()
    if lowered in _CANONICAL_OBJECTIVES:
        return lowered
    if "requirement" in lowered:
        return "write_requirements_doc"
    inferred = _infer_objective(user_text)
    return inferred[0] if inferred else None


def _infer_objective(user_text: str) -> tuple[str, str] | None:
    lower = user_text.lower().strip()
    if not lower:
        return None

    for pattern in _REQUIREMENTS_PATTERNS:
        if pattern in lower:
            return _quote_match(user_text, pattern, "write_requirements_doc")

    for pattern in _PYTHON_FUNCTION_PATTERNS:
        if pattern in lower:
            return _quote_match(user_text, pattern, "write_python_function")

    if re.search(r"write\s+(?:a\s+)?(?:python\s+)?function", lower):
        match = re.search(r"write\s+(?:a\s+)?(?:python\s+)?function", user_text, re.I)
        quote = match.group(0) if match else user_text.strip()[:120]
        return ("write_python_function", quote)

    for a, b in _SQL_PATTERNS:
        if a in lower and b in lower:
            return _quote_match(user_text, a, "write_sql_query")

    return None


def _quote_match(user_text: str, pattern: str, objective: str) -> tuple[str, str]:
    idx = user_text.lower().find(pattern)
    if idx >= 0:
        return (objective, user_text[idx : idx + len(pattern)])
    return (objective, user_text.strip()[:120])
