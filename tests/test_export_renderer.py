from versa.export.renderer import render_requirements_markdown
from versa.models.delta import FactPatch, TurnDelta
from versa.models.state import FactKind, TaskState
from versa.reducer import apply_delta


def _add_fact(state: TaskState, key: str, value, kind: FactKind = FactKind.REQUIREMENT) -> TaskState:
    return apply_delta(
        state,
        TurnDelta(
            fact_patches=[
                FactPatch(
                    op="add",
                    kind=kind,
                    key=key,
                    value=value,
                    evidence_quote=str(value),
                )
            ]
        ),
        f"msg-{key}",
    )


def test_render_requirements_markdown_includes_sections():
    state = TaskState()
    state = _add_fact(state, "objective", "write_requirements_doc", FactKind.OBJECTIVE)
    state = _add_fact(state, "scope", "CLI backup tool")
    state = _add_fact(state, "target_users", "developers")
    state = _add_fact(state, "functional_requirements", ["sync", "resume"])

    md = render_requirements_markdown(state)

    assert "# Overview" in md
    assert "CLI backup tool" in md
    assert "# Target Users" in md
    assert "- sync" in md
