---
name: claude-blackbox
description: Flight recorder for Claude projects. Keeps an append-only timeline of prompts, commands, edited files and decisions plus atomic checkpoints, so work can be resumed exactly where it stopped after a crash, power cut, reboot, closed terminal or context compaction. Use when the user wants to resume/recover a previous session, asks "where did we leave off", wants a project history/audit log, or asks to save progress/checkpoint.
---

# claude-blackbox

Turns the project into a **recoverable and auditable** workspace with two layers:

1. **Recovery state** — `.blackbox/checkpoints/state.json`: where the work stopped and the next step.
2. **Full history** — `.blackbox/history/`: chronological record of Claude's activity.

All data stays local in `.blackbox/` (git-ignored by the installer). Never store secrets,
passwords, API keys, tokens or private keys; the recorder redacts common secret patterns automatically.

The CLI lives next to this file: `scripts/blackbox.py` (Python 3.8+, no dependencies).
Below, `BB` means `python <this skill dir>/scripts/blackbox.py`.

## Layout

| Path | Content |
|---|---|
| `.blackbox/history/events.jsonl` | one event per line (append-only) |
| `.blackbox/history/prompts.md` | user prompts (redacted) |
| `.blackbox/history/commands.log` | shell commands executed |
| `.blackbox/history/decisions.md` | important decisions and approvals |
| `.blackbox/checkpoints/state.json` | last recoverable state (atomic write) |
| `.blackbox/snapshots/` | last 50 state snapshots |

## Recovering after a cut

When the user asks to resume, or the session starts with a `[claude-blackbox]` context block:

1. `BB resume` — verifies integrity and prints task, next step, last prompt, changed files, last events.
2. If it reports a command that **started but never reported a result**, do NOT assume it finished. Check its effects.
3. Review `git status` / `git diff`.
4. Inspect any partially modified file listed in "files changed".
5. Continue from `next_step`, after briefly telling the user where things stand.

Expected flow: `cut → restart → resume → review → continue`.

## Saving checkpoints

After each meaningful unit of work, record progress — this is what makes `next_step` useful:

```
BB checkpoint --task "Migrate auth to JWT" --done "Login endpoint migrated" --next "Migrate refresh tokens"
BB checkpoint --decision "Use PostgreSQL instead of SQLite (user approved)"
```

Do this proactively, without asking, whenever a step is completed, before risky operations, and before ending a long response.

## Other commands

- `BB status` — last checkpoint.
- `BB history -n 30` — latest events.
- `BB timeline` — whole history grouped by day → session → event.
- `BB verify` — integrity check (tolerates a torn last line after a power cut).
- `BB install-hooks [--global]` — safely merge the recording hooks into `settings.json` (keeps existing settings, writes a `.bak`).

## Hooks (automatic recording)

If the hooks are not installed yet (no `.blackbox/history/events.jsonl` growing) and the user uses Claude Code,
offer to run `BB install-hooks`. Hooks recorded: `SessionStart` (also injects the recovered state into context),
`UserPromptSubmit`, `PreToolUse` (Bash only, to detect interrupted commands), `PostToolUse`, `PreCompact`, `Stop`.
Each event keeps the `transcript_path`, which Claude Code persists with the full conversation — use it instead
of trying to reconstruct a conversation from fragments.

## Safety rules

Git is the second recovery layer: review `git status`/`git diff` before big changes and prefer small commits.

Never run automatically:

- `git reset --hard`, `git clean -fd`
- `docker volume prune`, `docker system prune --volumes`
- dropping/deleting databases or Docker volumes

Treat PostgreSQL, MySQL, Redis, Docker volumes, `.env` files and backups as protected data.

## Honest limits

- Content Claude was generating in memory that never reached disk or a persisted transcript cannot be recovered.
- If installed mid-project, history starts at installation. Existing Claude Code transcripts
  (`~/.claude/projects/`) may be indexed, but never claim to have recovered conversations that are not available.

Goal: a complete, queryable timeline —
`Day 1 → session → prompt → action → change → decision → checkpoint → next step`.
