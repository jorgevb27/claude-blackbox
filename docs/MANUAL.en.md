# 📘 claude-blackbox: User Manual

<p align="center"><img src="../assets/banner.svg" alt="claude-blackbox" width="100%"></p>

> **English** · [Español](MANUAL.es.md) · [← Back to README](../README.md)

Everything you need to install, use and trust the flight recorder for Claude Code. Setup takes **2 minutes**.

**Contents**

1. [What it does](#1-what-it-does)
2. [Requirements](#2-requirements)
3. [Install](#3-install)
4. [Check that it's recording](#4-check-that-its-recording)
5. [Day-to-day use](#5-day-to-day-use)
6. [After a crash or power cut](#6-after-a-crash-or-power-cut)
7. [Checkpoints and decisions](#7-checkpoints-and-decisions)
8. [History and timeline](#8-history-and-timeline)
9. [Privacy and secret redaction](#9-privacy-and-secret-redaction)
10. [Files reference](#10-files-reference)
11. [Uninstall](#11-uninstall)
12. [CLI reference](#12-cli-reference)
13. [Troubleshooting](#13-troubleshooting)
14. [Limits](#14-limits)

> All terminal screenshots in this manual are **real output** from a test project, with only the paths shortened.

---

## 1. What it does

<p align="center"><img src="../assets/before-after.svg" alt="Without vs with claude-blackbox" width="100%"></p>

claude-blackbox has two layers:

| Layer | File | Purpose |
|---|---|---|
| **Recovery state** | `.blackbox/checkpoints/state.json` | Where the work stopped: task, next step, changed files, last command |
| **Full history** | `.blackbox/history/` | An append-only timeline of prompts, commands, files and decisions |

Claude Code **hooks** feed both layers automatically. When a new session starts, the recovered state is injected into Claude's context.

---

## 2. Requirements

- **Claude Code** for automatic recording, or **Claude.ai** for the checkpoint workflow only.
- **Python 3.8+**, which is usually already installed. On Windows, `python` from python.org or the Microsoft Store both work.
- **Git** (optional): if present, checkpoints include `git status`.

---

## 3. Install

### A) Plugin: every project, recommended

Inside Claude Code:

```
/plugin marketplace add jorgevb27/claude-blackbox
/plugin install claude-blackbox@claude-blackbox
```

Restart Claude Code. The hooks come with the plugin, so there is nothing else to configure.

### B) One project (copy)

macOS / Linux:

```bash
git clone --depth 1 https://github.com/jorgevb27/claude-blackbox /tmp/claude-blackbox
mkdir -p .claude/skills && cp -r /tmp/claude-blackbox/skills/claude-blackbox .claude/skills/
python3 .claude/skills/claude-blackbox/scripts/blackbox.py install-hooks
```

Windows (PowerShell):

```powershell
git clone --depth 1 https://github.com/jorgevb27/claude-blackbox $env:TEMP\claude-blackbox
New-Item -ItemType Directory -Force .claude\skills | Out-Null
Copy-Item -Recurse $env:TEMP\claude-blackbox\skills\claude-blackbox .claude\skills\
python .claude\skills\claude-blackbox\scripts\blackbox.py install-hooks
```

<p align="center"><img src="../assets/terminal-install.svg" alt="install-hooks output" width="95%"></p>

`install-hooks`:
- **merges** six hook entries into `.claude/settings.json`, keeping everything you already had;
- writes a backup to `.claude/settings.json.bak` first;
- is **idempotent**: running it twice doesn't duplicate anything;
- adds `.blackbox/` to your `.gitignore`.

### C) Every project, without the plugin

```bash
python3 path/to/claude-blackbox/scripts/blackbox.py install-hooks --global
```

This writes to `~/.claude/settings.json` using the absolute path of the script, so keep that folder where it is.

### D) Claude.ai

Download `claude-blackbox-skill.zip` from the [latest release](https://github.com/jorgevb27/claude-blackbox/releases/latest) →
**Settings → Capabilities → Skills → Upload skill**. Claude will save and read checkpoints when you ask. Automatic hooks are a Claude Code feature.

---

## 4. Check that it's recording

1. In Claude Code, run **`/hooks`**. You should see entries for `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact` and `Stop`.
2. Send any prompt, then check that `.blackbox/history/events.jsonl` exists in your project and grows.
3. Ask Claude: *"Show me the blackbox history."*

---

## 5. Day-to-day use

Most of the time you do **nothing**. The recorder works in the background, and the skill tells Claude to save a checkpoint after each meaningful step.

Useful things to say:

| You say | What happens |
|---|---|
| *"Save a checkpoint: next step is the webhook."* | `checkpoint --next "…"` |
| *"We decided to use Stripe Checkout, record it."* | `checkpoint --decision "…"` → `decisions.md` |
| *"Where did we leave off?"* | `resume` |
| *"What did we do yesterday?"* | `timeline` |
| *"Why did we choose Postgres?"* | Claude reads `decisions.md` |

> 💡 Good habit: before a risky step (a migration, a big refactor), ask for a checkpoint with a clear `--next`.

---

## 6. After a crash or power cut

### Step 1: just open Claude Code again

The `SessionStart` hook injects this into Claude's context **automatically**:

<p align="center"><img src="../assets/terminal-sessionstart.svg" alt="Recovered state at SessionStart" width="95%"></p>

### Step 2: let Claude verify before continuing

Claude knows it must:
1. check whether the **interrupted command** (`alembic upgrade head` here) actually ran;
2. review `git status` and any **partially edited files**;
3. continue from the **next step**.

### Step 3 (optional): see the full report

```
python .claude/skills/claude-blackbox/scripts/blackbox.py resume
```

<details>
<summary>Show the real <code>resume</code> output</summary>
<p align="center"><img src="../assets/terminal-resume.svg" alt="resume output" width="95%"></p>
</details>

> ⚠️ **Never assume an interrupted command finished.** For migrations, check the database's migration table; for installs, check the lock file; for deployments, check the target.

---

## 7. Checkpoints and decisions

```bash
blackbox.py checkpoint --task "Stripe checkout on cart page" \
                       --done "Stripe client + cart integration, tests green" \
                       --next "Handle webhook: payment_intent.succeeded" \
                       --decision "Use Stripe Checkout (hosted) instead of Elements"
```

| Option | Saved as |
|---|---|
| `--task` | What you're working on (it stays until you change it) |
| `--done` | Appended to the `completed` list |
| `--next` | The very next step, which is what Claude resumes from |
| `--decision` | Appended to `decisions` and to `history/decisions.md` |
| `--note` | A free note in the timeline |

Each checkpoint is written **atomically** (temp file + `fsync` + rename), so a power cut can never leave a half-written `state.json`.
A copy is also kept in `snapshots/`, which holds the last 50.

---

## 8. History and timeline

```
blackbox.py timeline       # everything, grouped by day → session
blackbox.py history -n 30  # the latest 30 events
```

<p align="center"><img src="../assets/terminal-timeline.svg" alt="timeline output" width="95%"></p>

You can also open these files directly:

- `history/prompts.md`: your prompts by session (redacted)
- `history/commands.log`: every shell command Claude ran
- `history/decisions.md`: your decision log

Each event also stores Claude Code's `transcript_path`, so you can always find the full conversation in `~/.claude/projects/`.

---

## 9. Privacy and secret redaction

- **Local only.** No network calls, ever.
- **Self-ignoring folder.** `.blackbox/` contains its own `.gitignore` with `*`, so it is never committed, whatever the install mode.
- **Redacted before writing to disk:**

| Type | Example pattern |
|---|---|
| OpenAI / Anthropic keys | `sk-…` |
| Stripe | `sk_live_…`, `sk_test_…`, `rk_…`, `whsec_…` |
| GitHub | `ghp_…`, `github_pat_…` |
| AWS | `AKIA…` |
| Google | `AIza…` |
| Slack | `xoxb-…` |
| JWT | `eyJ….eyJ….…` |
| Headers and assignments | `Bearer …`, `password=…`, `token: …`, `api_key=…` |
| Private keys | `-----BEGIN … PRIVATE KEY-----` |
| URL credentials | `postgres://user:pass@host` |

- **Never stored:** file contents and command output. Only file paths and the commands themselves are recorded.

> Redaction is pattern-based. Avoid pasting secrets into prompts anyway, and use environment variables or a secret manager.

---

## 10. Files reference

```
.blackbox/
├── .gitignore                 "*", so the folder ignores itself
├── checkpoints/state.json     last recoverable state (atomic)
├── snapshots/state-*.json     last 50 checkpoints
└── history/
    ├── events.jsonl           append-only, one JSON event per line
    ├── prompts.md             prompts by session (redacted)
    ├── commands.log           shell commands
    └── decisions.md           decision log
```

`state.json` fields: `task`, `next_step`, `completed`, `decisions`, `files_changed`, `last_prompt`, `last_command`, `session_id`, `git`, `updated_at`, `last_event_id`.

---

## 11. Uninstall

| Install mode | Steps |
|---|---|
| Plugin | `/plugin uninstall claude-blackbox@claude-blackbox` |
| Project copy | Restore `.claude/settings.json.bak`, or delete the hook entries whose command contains `blackbox`. Then delete `.claude/skills/claude-blackbox/` |
| Global | Remove the `blackbox` hook entries from `~/.claude/settings.json` |

Your recorded history stays in `.blackbox/` until you delete it.

---

## 12. CLI reference

The script is `skills/claude-blackbox/scripts/blackbox.py`. Use `python` on Windows and `python3` on macOS/Linux.

| Command | Description |
|---|---|
| `resume` | Verify, then show state, interrupted command, git and the last 10 events |
| `status` | Last checkpoint |
| `verify` | Integrity check (tolerates torn lines) |
| `checkpoint [--task] [--next] [--done] [--decision] [--note]` | Save progress |
| `history [-n N]` | Latest N events (default 20) |
| `timeline` | All events by day → session |
| `install-hooks [--global]` | Merge the hooks into `settings.json` safely |
| `hook` | Internal: called by Claude Code with the event JSON on stdin |
| `--version` | Print the version |

---

## 13. Troubleshooting

| Problem | Solution |
|---|---|
| `.blackbox/` never appears | Run `/hooks` to confirm the hooks are present. Restart Claude Code after installing |
| `Python 3.8+ not found` in the hook logs | Install Python and make sure `python3`, `python` or `py` is on your PATH |
| On Windows the hooks don't run | Claude Code runs hooks through Git Bash, so install **Git for Windows** |
| `state.json is corrupt` | Copy the newest file from `.blackbox/snapshots/` over `checkpoints/state.json` |
| `torn line(s) in events.jsonl` | This is normal after a power cut and is ignored automatically |
| `settings.json is not valid JSON` | Fix the JSON first. `install-hooks` refuses to touch a broken file |
| Hooks are duplicated | They shouldn't be (`install-hooks` is idempotent). Restore from `.bak` if you edited them by hand |

---

## 14. Limits

- Text that Claude was generating **only in memory** when the power died cannot be recovered.
- If you install it mid-project, recording starts at installation, although older transcripts remain in `~/.claude/projects/`.
- Redaction catches common formats, not every possible secret.

---

<p align="center">Did it save your session? <a href="https://github.com/jorgevb27/claude-blackbox">⭐ Star the repo</a> · <a href="https://github.com/jorgevb27/claude-blackbox/issues">Report an issue</a></p>
