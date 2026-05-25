# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-25

### Added

- Conversation state compiler: `TaskState`, `TurnDelta`, deterministic reducer, readiness policy
- `AgentRuntime` turn loop with extractor → reducer → solver → verifier → commit
- Codex CLI substrate (`codex exec --ephemeral`) with JSON schema for `TurnDelta`
- `versa` CLI: `doctor`, `chat`, `turn`
- In-memory store MVP and Postgres DDL (`schema.sql`)
- Unit tests and optional Codex integration test
- RFC for future `codex_app_server` SDK adapter

[0.1.0]: https://github.com/phi9t/versa/releases/tag/v0.1.0
