from __future__ import annotations

from versa.llm.base import LLMClient
from versa.models.delta import TurnDelta
from versa.models.state import Artifact, ArtifactStatus, OpenQuestion, TaskState, Verification
from versa.policy import NextAction, blocking_questions, choose_next_action, missing_required_slots
from versa.reducer import apply_delta, prune_resolved_questions
from versa.solver import build_coding_solver_context, build_extractor_prompt, classify_artifact_kind
from versa.store.base import Store
from versa.verifier import commit_artifact, verify_artifact


class AgentRuntime:
    def __init__(
        self,
        solver_llm: LLMClient,
        store: Store,
        *,
        extractor_llm: LLMClient | None = None,
    ) -> None:
        self._extractor = extractor_llm or solver_llm
        self._solver = solver_llm
        self.store = store

    async def handle_user_turn(self, task_id: str, user_text: str) -> str:
        message_id = await self.store.append_message(
            task_id=task_id,
            role="user",
            content=user_text,
        )

        state = await self.store.load_state(task_id)
        version_before = state.version

        delta = await self.extract_delta(
            state=state,
            message_id=message_id,
            user_text=user_text,
        )

        state = apply_delta(state=state, delta=delta, message_id=message_id)

        await self.store.save_state(task_id, state)
        await self.store.append_state_event(
            task_id=task_id,
            event_type="delta_applied",
            event_json=delta.model_dump(mode="json"),
            version_before=version_before,
            version_after=state.version,
        )

        action, state = self._resolve_action(state)

        if action == NextAction.ASK_CLARIFICATION:
            await self.store.save_state(task_id, state)
            return await self._finalize_reply(task_id, self.render_clarification(state))

        if action == NextAction.FINALIZE_VERIFIED_ARTIFACT:
            if state.active_artifact_id:
                artifact = await self.store.get_artifact(task_id, state.active_artifact_id)
                if artifact and artifact.status == ArtifactStatus.VERIFIED:
                    return await self._finalize_reply(task_id, artifact.content)
            state = state.model_copy(deep=True)
            state.active_artifact_id = None
            action = choose_next_action(state)

        if action == NextAction.GENERATE_CANDIDATE:
            return await self._generate_verify_respond(task_id, state)

        raise RuntimeError(f"Unsupported action: {action}")

    async def _generate_verify_respond(
        self,
        task_id: str,
        state: TaskState,
        verification_failures: list[str] | None = None,
        max_retries: int = 2,
    ) -> str:
        for attempt in range(max_retries + 1):
            artifact = await self._generate_candidate(
                state,
                verification_failures=verification_failures,
            )

            verification = await verify_artifact(artifact, state)
            await self.store.save_verification(task_id, verification)

            version_before = state.version
            state, artifact = commit_artifact(state, artifact, verification)
            await self.store.save_artifact(task_id, artifact)
            await self.store.save_state(task_id, state)
            await self.store.append_state_event(
                task_id=task_id,
                event_type="artifact_committed",
                event_json={
                    "artifact_id": artifact.id,
                    "passed": verification.passed,
                    "attempt": attempt,
                },
                version_before=version_before,
                version_after=state.version,
            )

            if verification.passed:
                return await self._finalize_reply(task_id, artifact.content)

            verification_failures = verification.failures
            if attempt >= max_retries:
                return await self._finalize_reply(
                    task_id,
                    self.render_failed_candidate(verification),
                )

        raise RuntimeError("retry loop exhausted without returning")

    async def _generate_candidate(
        self,
        state: TaskState,
        verification_failures: list[str] | None = None,
    ) -> Artifact:
        prompt = build_coding_solver_context(state, verification_failures)
        content = await self._solver.generate(prompt)
        return Artifact(
            kind=classify_artifact_kind(state),
            content=content,
            based_on_state_version=state.version,
        )

    def _resolve_action(self, state: TaskState) -> tuple[NextAction, TaskState]:
        action = choose_next_action(state)
        if action != NextAction.ASK_CLARIFICATION:
            return action, state

        state = state.model_copy(deep=True)
        state.open_questions = prune_resolved_questions(state)
        missing = missing_required_slots(state)
        if missing and not any(
            q.related_keys == [missing[0]] for q in state.open_questions if q.blocks_progress
        ):
            state.open_questions.append(
                OpenQuestion(
                    question=f"I need one missing detail before solving: {missing[0]}",
                    related_keys=[missing[0]],
                )
            )
            state.version += 1
        return action, state

    async def extract_delta(
        self,
        state: TaskState,
        message_id: str,
        user_text: str,
    ) -> TurnDelta:
        prompt = build_extractor_prompt(state, user_text)
        return await self._extractor.generate_json(prompt, schema=TurnDelta)

    def render_clarification(self, state: TaskState) -> str:
        blocking = blocking_questions(state)
        if not blocking:
            return "I need one more detail before I can proceed."
        return blocking[0].question

    def render_failed_candidate(self, verification: Verification) -> str:
        if verification.failures:
            return (
                "I found an issue before finalizing. "
                f"The blocking failure is: {verification.failures[0]}"
            )
        return "I could not verify the candidate yet; I need one more constraint."

    async def _finalize_reply(self, task_id: str, reply: str) -> str:
        await self.store.append_message(task_id=task_id, role="assistant", content=reply)
        return reply
