from __future__ import annotations

import json
from typing import Literal

from versa.models.state import Assumption, Fact, FactStatus, TaskState, ToolResult
from versa.reducer import active_facts, find_active_fact

ArtifactKind = Literal["code", "sql", "plan", "answer", "patch", "document"]


def _format_lines(lines: list[str]) -> str:
    return "(none)" if not lines else "\n".join(lines)


def format_facts(facts: list[Fact]) -> str:
    return _format_lines(
        [f"- [{f.kind.value}] {f.key} = {json.dumps(f.value)}" for f in facts]
    )


def format_tool_results(results: list[ToolResult]) -> str:
    return _format_lines([f"- {tr.tool_name}: {tr.output_summary}" for tr in results])


def format_open_assumptions(assumptions: list[Assumption]) -> str:
    open_ones = [a for a in assumptions if a.status == "open"]
    return _format_lines(
        [f"- {a.key} = {json.dumps(a.value)} ({a.reason})" for a in open_ones]
    )


def build_solver_context(state: TaskState, verification_failures: list[str] | None = None) -> str:
    facts = active_facts(state)
    verified_tools = [tr for tr in state.tool_results if tr.verified]

    failure_block = ""
    if verification_failures:
        bullets = "\n".join(f"- {f}" for f in verification_failures)
        failure_block = f"""
The current candidate failed these checks:
{bullets}
Regenerate from authoritative state only.
"""

    return f"""You are solving from a clean authoritative task state.

Authoritative user-stated facts:
{format_facts(facts)}

Verified tool results:
{format_tool_results(verified_tools)}

Open assumptions (not authoritative until user confirms):
{format_open_assumptions(state.assumptions)}
{failure_block}
Rules:
- Use only the authoritative facts and verified tool results.
- Do not rely on previous assistant drafts.
- Do not invent missing requirements.
- If the state is insufficient, ask one concise clarification.
- Produce the smallest complete answer satisfying the state.
"""


def build_coding_solver_context(
    state: TaskState,
    verification_failures: list[str] | None = None,
) -> str:
    base = build_solver_context(state, verification_failures)
    objective = find_active_fact(state, "objective")
    if objective and objective.value in {"edit_repository", "write_patch"}:
        return base + """
You are editing a repository.

Use only:
- active user requirements
- verified repository observations
- test failures listed above

Do not rely on previous assistant patches.
Do not preserve previous implementation choices unless verified or explicitly requested.
Generate a minimal patch satisfying the active state.
"""
    objective = find_active_fact(state, "objective")
    if objective and objective.value == "write_requirements_doc":
        return base + build_document_solver_suffix()
    return base


def build_document_solver_suffix() -> str:
    return """
Produce a requirements specification document in Markdown.

Required sections (include only if the corresponding fact exists):
# Overview
# Target Users
# Functional Requirements
# Non-Functional Requirements
# Constraints
# Success Criteria
# Open Questions

Rules:
- Use only authoritative facts and verified tool results above.
- Do not rely on previous assistant drafts.
- Do not invent missing requirements.
- Bullet-list array values.
- If open assumptions remain unresolved, list them under Open Questions.
"""


def classify_artifact_kind(state: TaskState) -> ArtifactKind:
    objective = find_active_fact(state, "objective")
    if not objective:
        return "answer"

    value = objective.value
    if value == "write_patch":
        return "patch"
    if value in {"write_python_function", "edit_repository"}:
        return "code"
    if value == "write_sql_query":
        return "sql"
    if value in {"plan_task", "break_down_task"}:
        return "plan"
    if value == "write_requirements_doc":
        return "document"
    return "answer"


def build_extractor_prompt(state: TaskState, user_text: str) -> str:
    return f"""Extract only information explicitly stated by the user in the latest message.

You may use the current TaskState to resolve references, but you must not treat
prior assistant messages as facts.

Return JSON matching the TurnDelta schema.

Rules:
- Every fact must include a verbatim evidence_quote from the latest user message.
- Do not infer unstated requirements.
- If the user corrects or contradicts a previous fact, emit a supersede or reject patch.
- If the user confirms or rejects an assistant assumption, update that assumption.
- If something is ambiguous, do not guess; emit a question in new_questions_for_user.

Current authoritative facts:
{format_facts(active_facts(state))}

Open assumptions:
{format_open_assumptions(state.assumptions)}

Latest user message:
\"\"\"
{user_text}
\"\"\"
"""
