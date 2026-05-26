import pytest

from versa.models.state import Artifact, Fact, FactKind, FactStatus, OpenQuestion, SourceSpan, TaskState
from versa.verifier import verify_requirements_document


@pytest.mark.asyncio
async def test_document_verifier_requires_sections_and_grounding():
    state = TaskState(
        facts=[
            Fact(
                kind=FactKind.OBJECTIVE,
                key="objective",
                value="write_requirements_doc",
                status=FactStatus.ACTIVE,
                source=SourceSpan(message_id="m", quote="doc"),
            ),
            Fact(
                kind=FactKind.REQUIREMENT,
                key="scope",
                value="CLI backup tool",
                status=FactStatus.ACTIVE,
                source=SourceSpan(message_id="m", quote="CLI backup tool"),
            ),
        ]
    )
    bad = Artifact(kind="document", content="empty doc", based_on_state_version=0)
    v = await verify_requirements_document(bad, state)
    assert not v.passed

    good = Artifact(
        kind="document",
        content="# Overview\n\nCLI backup tool\n",
        based_on_state_version=0,
    )
    v2 = await verify_requirements_document(good, state)
    assert v2.passed


@pytest.mark.asyncio
async def test_document_verifier_requires_open_questions_section():
    state = TaskState(
        facts=[
            Fact(
                kind=FactKind.REQUIREMENT,
                key="scope",
                value="CLI backup tool",
                status=FactStatus.ACTIVE,
                source=SourceSpan(message_id="m", quote="CLI backup tool"),
            )
        ],
        open_questions=[OpenQuestion(question="Which cloud provider?", related_keys=["scope"])],
    )
    artifact = Artifact(
        kind="document",
        content="# Overview\n\nCLI backup tool\n",
        based_on_state_version=0,
    )
    v = await verify_requirements_document(artifact, state)
    assert not v.passed
