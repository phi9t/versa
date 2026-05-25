"""Shared test fixtures."""

CLAMP_USER_PROMPT = "Write a Python function named `clamp` that bounds a number."

PYTHON_FUNCTION_SLOTS = [
    ("input_format", "x, lo, hi"),
    ("output_format", "clamped number"),
    ("edge_cases", "none"),
    ("examples_or_tests", []),
]

CLARIFICATION_TOKENS = ("need", "missing", "detail", "which", "what", "?")


def is_clarification(reply: str) -> bool:
    lower = reply.lower()
    return any(token in lower for token in CLARIFICATION_TOKENS)
