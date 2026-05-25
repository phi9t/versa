from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable

from versa.orchestrator import AgentRuntime


class InteractionMode(str, Enum):
    """Paper-style interaction modes for internal benchmarking."""

    SHARDED = "sharded"
    STRUCTURED = "structured"


@dataclass
class EvalCase:
    task_id: str
    user_shards: list[str]
    expected_substrings: list[str]


@dataclass
class EvalResult:
    mode: InteractionMode
    task_id: str
    passed: bool
    responses: list[str]
    details: dict[str, Any]


def _responses_match_expectations(
    responses: list[str],
    expected_substrings: list[str],
) -> bool:
    return all(any(exp in r for r in responses) for exp in expected_substrings)


async def run_structured(
    runtime: AgentRuntime,
    case: EvalCase,
) -> EvalResult:
    responses: list[str] = []
    for shard in case.user_shards:
        responses.append(await runtime.handle_user_turn(case.task_id, shard))

    return EvalResult(
        mode=InteractionMode.STRUCTURED,
        task_id=case.task_id,
        passed=_responses_match_expectations(responses, case.expected_substrings),
        responses=responses,
        details={"turns": len(case.user_shards)},
    )


async def run_sharded_naive(
    solver: Callable[[str], Awaitable[str]],
    case: EvalCase,
) -> EvalResult:
    """Baseline: grow transcript, pass entire history to solver each turn."""
    transcript: list[str] = []
    responses: list[str] = []
    for shard in case.user_shards:
        transcript.append(f"User: {shard}")
        reply = await solver("\n".join(transcript))
        transcript.append(f"Assistant: {reply}")
        responses.append(reply)

    return EvalResult(
        mode=InteractionMode.SHARDED,
        task_id=case.task_id,
        passed=_responses_match_expectations(responses, case.expected_substrings),
        responses=responses,
        details={"transcript_turns": len(transcript)},
    )
