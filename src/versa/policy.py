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


def infer_required_slots(state: TaskState) -> list[str]:
    objective = find_active_fact(state, "objective")
    if not objective:
        return ["objective"]

    if objective.value == "write_python_function":
        return [
            "function_name",
            "input_format",
            "output_format",
            "edge_cases",
            "examples_or_tests",
        ]

    if objective.value == "write_sql_query":
        return [
            "schema",
            "target_columns",
            "filter_conditions",
            "aggregation_rules",
            "ordering",
        ]

    if objective.value == "write_requirements_doc":
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
