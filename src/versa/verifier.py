from __future__ import annotations

import ast

from versa.models.state import Artifact, ArtifactStatus, TaskState, Verification
from versa.policy import REQUIREMENTS_DOC_SLOTS
from versa.reducer import active_facts, find_active_fact


async def verify_artifact(artifact: Artifact, state: TaskState) -> Verification:
    if artifact.kind == "code":
        return await run_code_tests(artifact, state)
    if artifact.kind == "sql":
        return await run_sql_checks(artifact, state)
    if artifact.kind == "patch":
        return await run_static_and_unit_checks(artifact, state)
    if artifact.kind == "document":
        return await verify_requirements_document(artifact, state)
    return await llm_judge_against_state(artifact, state)


async def run_code_tests(artifact: Artifact, state: TaskState) -> Verification:
    checks: list[str] = []
    failures: list[str] = []

    content = artifact.content.strip()
    checks.append("non_empty")
    if not content:
        failures.append("Artifact content is empty")
        return _verification(artifact, checks, failures)

    checks.append("python_syntax")
    try:
        ast.parse(content)
    except SyntaxError as exc:
        failures.append(f"Python syntax error: {exc}")
        return _verification(artifact, checks, failures)

    function_name_fact = find_active_fact(state, "function_name")
    if function_name_fact:
        checks.append("function_name_present")
        name = str(function_name_fact.value)
        if f"def {name}" not in content:
            failures.append(f"Expected function `def {name}` in generated code")

    examples = find_active_fact(state, "examples_or_tests")
    if examples and isinstance(examples.value, list):
        checks.append("docstring_examples")
        for example in examples.value:
            if str(example) not in content:
                failures.append(f"Missing referenced example/test: {example}")

    return _verification(artifact, checks, failures)


async def run_sql_checks(artifact: Artifact, state: TaskState) -> Verification:
    checks = ["non_empty", "select_present"]
    failures: list[str] = []
    raw = artifact.content.strip()
    content_upper = raw.upper()

    if not raw:
        failures.append("SQL artifact is empty")
    elif "SELECT" not in content_upper:
        failures.append("SQL must contain a SELECT statement")

    schema = find_active_fact(state, "schema")
    if schema and isinstance(schema.value, dict):
        checks.append("tables_referenced")
        for table in schema.value.get("tables", []):
            if str(table).upper() not in content_upper:
                failures.append(f"Expected reference to table `{table}`")

    return _verification(artifact, checks, failures)


async def run_static_and_unit_checks(artifact: Artifact, _state: TaskState) -> Verification:
    checks = ["non_empty"]
    failures: list[str] = []
    if not artifact.content.strip():
        failures.append("Patch content is empty")
    return _verification(artifact, checks, failures)


_DOCUMENT_HEADINGS = {
    "scope": "# overview",
    "target_users": "# target users",
    "functional_requirements": "# functional requirements",
    "non_functional_requirements": "# non-functional requirements",
    "constraints": "# constraints",
    "success_criteria": "# success criteria",
}


async def verify_requirements_document(artifact: Artifact, state: TaskState) -> Verification:
    checks = ["non_empty", "sections_for_facts", "grounded"]
    failures: list[str] = []
    content = artifact.content.strip()
    content_lower = content.lower()

    if not content:
        failures.append("Document artifact is empty")
        return _verification(artifact, checks, failures)

    active = active_facts(state)
    content_slots = [slot for slot in REQUIREMENTS_DOC_SLOTS if slot != "synthesis_requested"]

    for fact in active:
        if fact.key not in content_slots:
            continue
        heading = _DOCUMENT_HEADINGS.get(fact.key)
        if heading and heading not in content_lower:
            failures.append(f"Missing section heading for `{fact.key}`")

    if active:
        grounded = any(
            fact.key.lower() in content_lower or str(fact.value).lower() in content_lower
            for fact in active
            if fact.key != "synthesis_requested"
        )
        if not grounded:
            failures.append("Document does not appear grounded in active facts")

    blocking_questions = [q for q in state.open_questions if q.blocks_progress]
    if blocking_questions and "# open questions" not in content_lower:
        failures.append("Blocking open questions exist but document lacks Open Questions section")

    return _verification(artifact, checks, failures)


async def llm_judge_against_state(artifact: Artifact, state: TaskState) -> Verification:
    """Rubric check: artifact must reference at least one active fact key or value."""
    checks = ["grounded_in_active_facts"]
    failures: list[str] = []

    active = active_facts(state)
    if not active:
        return _verification(artifact, checks, failures)

    content_lower = artifact.content.lower()
    grounded = any(
        f.key.lower() in content_lower or str(f.value).lower() in content_lower
        for f in active
    )
    if not grounded and len(artifact.content) > 200:
        failures.append("Artifact does not appear grounded in active facts")

    return _verification(artifact, checks, failures)


def _verification(artifact: Artifact, checks: list[str], failures: list[str]) -> Verification:
    return Verification(
        artifact_id=artifact.id,
        passed=len(failures) == 0,
        checks=checks,
        failures=failures,
    )


def commit_artifact(
    state: TaskState,
    artifact: Artifact,
    verification: Verification,
) -> tuple[TaskState, Artifact]:
    state = state.model_copy(deep=True)
    artifact.verification_ids.append(verification.id)
    artifact.status = (
        ArtifactStatus.VERIFIED if verification.passed else ArtifactStatus.FAILED
    )

    if verification.passed:
        state.active_artifact_id = artifact.id

    state.version += 1
    return state, artifact
