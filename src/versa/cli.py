from __future__ import annotations

import argparse
import asyncio
import json
import sys

from pydantic import ValidationError

from versa import __version__
from versa.api.session_service import SessionService
from versa.llm.codex_cli import CodexExecError, codex_is_ready
from versa.llm.factory import make_codex_clients
from versa.llm.mock import MockLLM
from versa.orchestrator import AgentRuntime
from versa.store.memory import InMemoryStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="versa",
        description="Versa conversation state compiler (Codex CLI substrate)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Check Codex CLI installation and auth")

    for name, help_text in (("chat", "Interactive multi-turn session"), ("turn", "Handle a single user message")):
        p = sub.add_parser(name, help=help_text)
        if name == "turn":
            p.add_argument("message", help="User message text")
        _add_turn_args(p)

    serve_p = sub.add_parser("serve", help="Run HTTP API + optional UI static files")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8000)
    serve_p.add_argument("--mock", action="store_true", help="Use MockLLM instead of Codex")
    _add_turn_args(serve_p)

    for name in ("state", "export"):
        p = sub.add_parser(name, help=f"Show session {name}")
        p.add_argument("--task-id", default="default", help="Task identifier")
        p.add_argument("--format", choices=["json", "md"], default="json")
        if name == "export":
            p.add_argument("--output", default=None, help="Write export to file")

    args = parser.parse_args(argv)

    if args.command == "doctor":
        return 0 if codex_is_ready() else 1

    if args.command == "chat":
        return asyncio.run(cmd_chat(args))

    if args.command == "turn":
        return asyncio.run(cmd_turn(args))

    if args.command == "serve":
        return cmd_serve(args)

    if args.command == "state":
        return asyncio.run(cmd_state(args))

    if args.command == "export":
        return asyncio.run(cmd_export(args))

    return 1


def _add_turn_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--task-id", default="default", help="Task identifier")
    parser.add_argument("--repo", default=None, help="Repo root for solver -C")
    parser.add_argument("--model", default=None)
    parser.add_argument("--profile", default=None)


def _build_runtime(args: argparse.Namespace, *, mock: bool = False) -> AgentRuntime:
    store = InMemoryStore()
    if mock:
        llm = MockLLM()
        return AgentRuntime(llm, store, extractor_llm=llm)
    extractor, solver = make_codex_clients(
        repo_root=getattr(args, "repo", None),
        model=getattr(args, "model", None),
        profile=getattr(args, "profile", None),
    )
    return AgentRuntime(solver, store, extractor_llm=extractor)


def _build_service(args: argparse.Namespace, *, mock: bool = False) -> SessionService:
    return SessionService(_build_runtime(args, mock=mock))


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


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("error: install api extra: pip install -e '.[api]'", file=sys.stderr)
        return 1

    from versa.api.app import create_app

    runtime = _build_runtime(args, mock=args.mock)
    app = create_app(runtime)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


async def cmd_state(args: argparse.Namespace) -> int:
    service = _build_service(args, mock=True)
    snapshot = await service.get_snapshot(args.task_id)
    if args.format == "md":
        export = await service.export(args.task_id, "md")
        print(export.content)
    else:
        print(json.dumps(snapshot.model_dump(mode="json"), indent=2))
    return 0


async def cmd_export(args: argparse.Namespace) -> int:
    service = _build_service(args, mock=True)
    fmt = "md" if args.format == "md" else "json"
    export = await service.export(args.task_id, fmt)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(export.content)
    else:
        print(export.content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
