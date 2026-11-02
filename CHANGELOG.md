# Changelog

## 1.0.0 — 2026-11-02

First public release (evolved from `cloud-resume-history`).

- Append-only event timeline (`.blackbox/history/events.jsonl`) fed by Claude Code hooks.
- Atomic checkpoints with `--task`, `--next`, `--done`, `--decision`; rotating snapshots (last 50).
- `resume` detects commands that started but never finished (crash / power cut).
- `SessionStart` hook injects the recovered state into Claude's context automatically.
- Automatic redaction of API keys, tokens, passwords, private keys and URL credentials.
- `install-hooks` merges into an existing `settings.json` safely (with `.bak` backup) and git-ignores `.blackbox/`.
- Installable as a Claude Code plugin, a plain skill, or a Claude.ai custom skill (ZIP).
- Cross-platform hook runner (Windows Git Bash, macOS, Linux). Zero dependencies.
