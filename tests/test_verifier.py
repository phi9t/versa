import pytest

from versa.models.state import Artifact, Fact, FactKind, FactStatus, SourceSpan, TaskState
from versa.verifier import run_code_tests, verify_artifact


@pytest.mark.asyncio
async def test_code_verifier_requires_syntax_and_function_name():
    state = TaskState(
        facts=[
            Fact(
                kind=FactKind.REQUIREMENT,
                key="function_name",
                value="clamp",
                status=FactStatus.ACTIVE,
                source=SourceSpan(message_id="m", quote="clamp"),
            )
        ]
    )
    bad = Artifact(kind="code", content="not python", based_on_state_version=0)
    v = await run_code_tests(bad, state)
    assert not v.passed

    good = Artifact(
        kind="code",
        content="def clamp(x, lo, hi):\n    return max(lo, min(hi, x))\n",
        based_on_state_version=0,
    )
    v2 = await run_code_tests(good, state)
    assert v2.passed


@pytest.mark.asyncio
async def test_verify_routes_by_kind():
    artifact = Artifact(kind="answer", content="objective noted", based_on_state_version=0)
    state = TaskState(
        facts=[
            Fact(
                kind=FactKind.OBJECTIVE,
                key="objective",
                value="explain",
                status=FactStatus.ACTIVE,
                source=SourceSpan(message_id="m", quote="explain"),
            )
        ]
    )
    v = await verify_artifact(artifact, state)
    assert v.passed
