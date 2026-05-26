from __future__ import annotations

from enum import Enum

from versa.models.state import OpenQuestion, TaskState
from versa.reducer import active_fact_keys, find_active_fact


class NextAction(str, Enum):
    ASK_CLARIFICATION = "ask_clarification"
    GENERATE_CANDIDATE = "generate_candidate"
    FINALIZE_VERIFIED_ARTIFACT = "finalize_verified_artifact"


REQUIREMENTS_DOC_SLOTS = [
    "scope",
    "target_users",
    "functional_requirements",
    "non_functional_requirements",
    "constraints",
    "success_criteria",
    "synthesis_requested",
]

SLOT_LABELS: dict[str, str] = {
    "scope": "Project scope",
    "target_users": "Target users",
    "functional_requirements": "Functional requirements",
    "non_functional_requirements": "Non-functional requirements",
    "constraints": "Constraints",
    "success_criteria": "Success criteria",
    "synthesis_requested": "Synthesis approved",
}

SLOT_CLARIFICATIONS: dict[str, str] = {
    "objective": "What kind of task is this?",
    "scope": "What are you building? Describe the project scope.",
    "target_users": "Who are the target users?",
    "functional_requirements": "What are the functional requirements?",
    "non_functional_requirements": "What are the non-functional requirements (performance, reliability, etc.)?",
    "constraints": "What constraints should the solution respect?",
    "success_criteria": "How will you measure success?",
    "synthesis_requested": 'Say "Proceed with synthesis" when you are ready for the requirements document.',
    "function_name": "What should the function be named?",
    "input_format": "What are the inputs?",
    "output_format": "What should the function return?",
    "edge_cases": "What edge cases should be handled?",
    "examples_or_tests": "Do you have examples or tests to include?",
}


def clarification_for_slot(slot_key: str) -> str:
    return SLOT_CLARIFICATIONS.get(
        slot_key,
        f"I need one more detail: {SLOT_LABELS.get(slot_key, slot_key.replace('_', ' '))}.",
    )


def infer_required_slots(state: TaskState) -> list[str]:
    objective = find_active_fact(state, "objective")
    if not objective:
        return ["objective"]
    return infer_required_slots_for_objective(str(objective.value))


def infer_required_slots_for_objective(objective_value: str) -> list[str]:
    if objective_value == "write_python_function":
        return [
            "function_name",
            "input_format",
            "output_format",
            "edge_cases",
            "examples_or_tests",
        ]

    if objective_value == "write_sql_query":
        return [
            "schema",
            "target_columns",
            "filter_conditions",
            "aggregation_rules",
            "ordering",
        ]

    if objective_value == "write_requirements_doc":
        return list(REQUIREMENTS_DOC_SLOTS)

    return ["objective"]


def missing_required_slots(state: TaskState) -> list[str]:
    active = active_fact_keys(state)
    return [slot for slot in infer_required_slots(state) if slot not in active]


def blocking_questions(state: TaskState) -> list[OpenQuestion]:
    return [q for q in state.open_questions if q.blocks_progress]


def choose_next_action(state: TaskState) -> NextAction:
    if blocking_questions(state) or missing_required_slots(state):
        return NextAction.ASK_CLARIFICATION

    if state.active_artifact_id:
        return NextAction.FINALIZE_VERIFIED_ARTIFACT

    return NextAction.GENERATE_CANDIDATE
