"""Shared test fixtures."""

CLAMP_USER_PROMPT = "Write a Python function named `clamp` that bounds a number."

PYTHON_FUNCTION_SLOTS = [
    ("input_format", "x, lo, hi"),
    ("output_format", "clamped number"),
    ("edge_cases", "none"),
    ("examples_or_tests", []),
]

REQUIREMENTS_OPENING = (
    "Gather requirements for backup CLI. "
    "Objective: write a requirements specification document."
)

REQUIREMENTS_SLOTS = [
    ("scope", "cross-platform CLI backing up ~/Documents to S3"),
    ("target_users", "individual developers on macOS and Linux"),
    ("functional_requirements", ["incremental sync", "resume interrupted uploads"]),
    ("non_functional_requirements", ["p99 latency under 500ms"]),
    ("constraints", ["no PII in logs"]),
    ("success_criteria", ["successful restore from any backup point"]),
]

SYNTHESIS_TRIGGER = "Proceed with synthesis."

CLARIFICATION_TOKENS = ("need", "missing", "detail", "which", "what", "?")


def is_clarification(reply: str) -> bool:
    lower = reply.lower()
    return any(token in lower for token in CLARIFICATION_TOKENS)
