from __future__ import annotations

import argparse
import asyncio
import sys

from pydantic import ValidationError

from versa.llm.codex_cli import CodexExecError, codex_is_ready
from versa.llm.factory import make_codex_clients
from versa.orchestrator import AgentRuntime
from versa.store.memory import InMemoryStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="versa",
        description="Versa conversation state compiler (Codex CLI substrate)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Check Codex CLI installation and auth")

    for name, help_text in (("chat", "Interactive multi-turn session"), ("turn", "Handle a single user message")):
        p = sub.add_parser(name, help=help_text)
        if name == "turn":
            p.add_argument("message", help="User message text")
        _add_turn_args(p)

    args = parser.parse_args(argv)

    if args.command == "doctor":
        return 0 if codex_is_ready() else 1

    if args.command == "chat":
        return asyncio.run(cmd_chat(args))

    if args.command == "turn":
        return asyncio.run(cmd_turn(args))

    return 1


def _add_turn_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--task-id", default="default", help="Task identifier")
    parser.add_argument("--repo", default=None, help="Repo root for solver -C")
    parser.add_argument("--model", default=None)
    parser.add_argument("--profile", default=None)


def _build_runtime(args: argparse.Namespace) -> AgentRuntime:
    extractor, solver = make_codex_clients(
        repo_root=args.repo,
        model=args.model,
        profile=args.profile,
    )
    return AgentRuntime(solver, InMemoryStore(), extractor_llm=extractor)


def _print_llm_error(exc: BaseException) -> None:
    print(f"error: {exc}", file=sys.stderr)
    if isinstance(exc, CodexExecError) and exc.stderr:
        print(exc.stderr.strip(), file=sys.stderr)


async def cmd_chat(args: argparse.Namespace) -> int:
    runtime = _build_runtime(args)

    print(
        f"Versa chat (task_id={args.task_id}). "
        "State is in-memory for this process only. Ctrl-D or 'exit' to quit."
    )
    while True:
        try:
            line = (await asyncio.to_thread(input, "you> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in {"exit", "quit"}:
            break
        reply = await _handle_turn(runtime, args.task_id, line)
        if reply is None:
            continue
        print(reply)
        print()

    return 0


async def _handle_turn(
    runtime: AgentRuntime,
    task_id: str,
    message: str,
) -> str | None:
    try:
        return await runtime.handle_user_turn(task_id, message)
    except (CodexExecError, ValidationError) as exc:
        _print_llm_error(exc)
        return None


async def cmd_turn(args: argparse.Namespace) -> int:
    runtime = _build_runtime(args)
    reply = await _handle_turn(runtime, args.task_id, args.message)
    if reply is None:
        return 1
    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
