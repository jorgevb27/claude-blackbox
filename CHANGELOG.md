# Changelog

## 1.1.0 — 2026-11-03

**Fixes**
- Stripe keys (`sk_live_…`, `sk_test_…`, `rk_…`, `whsec_…`) were not redacted; now they are. Also added Google `AIza…` keys and JWTs.
- When installed as a plugin, `.blackbox/` could be committed to git. The folder now contains its own `.gitignore`, so it ignores itself in every install mode.

**New**
- 11 automated tests (redaction, interrupted-command detection, torn lines, idempotent install) + CI on Windows, macOS and Linux.
- Redesigned README (EN/ES) and a 14-section user manual in English and Spanish.
- New visuals built from real CLI output: install, SessionStart injection, resume, timeline; plus before/after and how-it-works diagrams.

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
