from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel

from versa.llm.base import LLMClient
from versa.models.delta import TurnDelta
from versa.models.state import FactKind

T = TypeVar("T", bound=BaseModel)


class MockLLM(LLMClient):
    """Rule-based LLM for tests and local demos without API keys."""

    async def generate(self, prompt: str) -> str:
        if "authoritative task state" in prompt.lower():
            return self._generate_solver_output(prompt)
        raise NotImplementedError("MockLLM.generate only supports solver prompts")

    async def generate_json(self, prompt: str, schema: type[T]) -> T:
        if schema is TurnDelta:
            return TurnDelta.model_validate(self._extract_delta(prompt))
        raise NotImplementedError(f"MockLLM.generate_json does not support {schema}")

    def _extract_delta(self, prompt: str) -> dict:
        match = re.search(r'Latest user message:\s*"""\s*(.*?)\s*"""', prompt, re.S)
        user_text = match.group(1).strip() if match else prompt

        patches: list[dict] = []
        lower = user_text.lower()

        if "python function" in lower or "write a function" in lower:
            patches.append(
                {
                    "op": "add",
                    "kind": FactKind.OBJECTIVE.value,
                    "key": "objective",
                    "value": "write_python_function",
                    "evidence_quote": user_text[:120],
                }
            )

        name_match = re.search(r"named?\s+`?(\w+)`?", user_text, re.I)
        if name_match:
            patches.append(
                {
                    "op": "add",
                    "kind": FactKind.REQUIREMENT.value,
                    "key": "function_name",
                    "value": name_match.group(1),
                    "evidence_quote": name_match.group(0),
                }
            )

        if "sql" in lower and "query" in lower:
            patches.append(
                {
                    "op": "add",
                    "kind": FactKind.OBJECTIVE.value,
                    "key": "objective",
                    "value": "write_sql_query",
                    "evidence_quote": user_text[:120],
                }
            )

        use_match = re.match(r"use\s+(\w+):\s*(.+)", user_text.strip(), re.I)
        if use_match:
            key, value = use_match.group(1), use_match.group(2).strip()
            if key == "examples_or_tests" and value.startswith("["):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    value = []
            patches.append(
                {
                    "op": "add",
                    "kind": FactKind.REQUIREMENT.value,
                    "key": key,
                    "value": value,
                    "evidence_quote": use_match.group(0),
                }
            )

        if lower.strip() in {"yes", "yes.", "correct", "proceed with implementation."}:
            patches.append(
                {
                    "op": "add",
                    "kind": FactKind.CONSTRAINT.value,
                    "key": "empty_list_behavior",
                    "value": "return_false",
                    "evidence_quote": user_text.strip(),
                }
            )

        return {
            "user_intent_summary": user_text[:200],
            "fact_patches": patches,
            "assumption_patches": [],
            "new_questions_for_user": [],
        }

    def _generate_solver_output(self, prompt: str) -> str:
        if "write_python_function" in prompt:
            fn = "solution"
            m = re.search(r"function_name = (.+)", prompt)
            if m:
                try:
                    fn = json.loads(m.group(1).strip())
                except json.JSONDecodeError:
                    fn = m.group(1).strip().strip('"')
            return (
                f"def {fn}(x, lo, hi):\n"
                f'    """Clamp x to [lo, hi]."""\n'
                f"    return max(lo, min(hi, x))\n"
            )
        return "I need more information from the authoritative state."
