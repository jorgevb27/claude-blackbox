<p align="center">
  <img src="assets/banner.svg" alt="claude-blackbox — the flight recorder for Claude Code" width="100%">
</p>

<p align="center">
  <a href="https://github.com/__USER__/claude-blackbox/stargazers"><img src="https://img.shields.io/github/stars/__USER__/claude-blackbox?style=flat&color=ff8a3d" alt="Stars"></a>
  <a href="https://github.com/__USER__/claude-blackbox/releases"><img src="https://img.shields.io/github/v/release/__USER__/claude-blackbox?color=ff8a3d" alt="Release"></a>
  <img src="https://img.shields.io/badge/Claude_Code-plugin_%2B_skill-ff8a3d" alt="Claude Code plugin + skill">
  <img src="https://img.shields.io/badge/dependencies-0-3fb950" alt="Zero dependencies">
  <img src="https://img.shields.io/badge/python-3.8%2B-79c0ff" alt="Python 3.8+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-8b949e" alt="MIT"></a>
</p>

<p align="center">
  <b>English</b> · <a href="README.es.md">Español</a>
</p>

---

**Your power goes out. Your laptop reboots. The terminal closes. The context gets compacted.**
And Claude has no idea what it was doing five minutes ago.

**claude-blackbox** records everything Claude does in your project — every prompt, command, edited file and decision —
into a local, crash-proof timeline. When you come back, Claude **already knows where it left off**, which command was
interrupted, and what the next step is.

<p align="center">
  <img src="assets/demo.svg" alt="blackbox resume after a power cut" width="760">
</p>

## ✨ Features

- 🛬 **Auto-resume:** on every new session, the recovered state is injected into Claude's context. No re-explaining.
- ⚠️ **Interrupted-command detection:** flags commands that *started* but never *finished* (`alembic upgrade head` during a power cut…), so Claude doesn't assume they succeeded.
- 📼 **Full timeline:** an append-only log of prompts, shell commands, edited files, checkpoints and decisions, grouped by day → session.
- 💾 **Crash-proof by design:** atomic writes + `fsync`, rotating snapshots, and tolerance for torn lines after a power cut.
- 🔐 **Secret redaction:** API keys (`sk-…`, `ghp_…`, `AKIA…`), bearer tokens, `password=…`, private keys and URL credentials are masked before anything hits disk.
- 🛡️ **Safety rules:** Claude is told never to run `git reset --hard`, `git clean -fd`, `docker volume prune`, or drop databases on its own.
- 🪶 **Zero dependencies:** one Python file. Works on Windows, macOS and Linux. 100% local; nothing leaves your machine.

## 🚀 Install

### Option A: Claude Code plugin (recommended, 2 commands)

Inside Claude Code:

```
/plugin marketplace add __USER__/claude-blackbox
/plugin install claude-blackbox@claude-blackbox
```

Restart Claude Code. That's it: the hooks are armed and the skill is loaded.

### Option B: Project skill (copy the folder)

<details>
<summary><b>macOS / Linux</b></summary>

```bash
git clone --depth 1 https://github.com/__USER__/claude-blackbox /tmp/claude-blackbox
mkdir -p .claude/skills && cp -r /tmp/claude-blackbox/skills/claude-blackbox .claude/skills/
python3 .claude/skills/claude-blackbox/scripts/blackbox.py install-hooks
```
</details>

<details>
<summary><b>Windows (PowerShell)</b></summary>

```powershell
git clone --depth 1 https://github.com/__USER__/claude-blackbox $env:TEMP\claude-blackbox
New-Item -ItemType Directory -Force .claude\skills | Out-Null
Copy-Item -Recurse $env:TEMP\claude-blackbox\skills\claude-blackbox .claude\skills\
python .claude\skills\claude-blackbox\scripts\blackbox.py install-hooks
```
</details>

`install-hooks` **merges** into your existing `.claude/settings.json` (it never overwrites it, and it writes a `.bak` first)
and adds `.blackbox/` to `.gitignore`. Use `--global` to record every project from `~/.claude/settings.json`.

### Option C: Claude.ai (web / desktop)

Download `claude-blackbox-skill.zip` from the [latest release](https://github.com/__USER__/claude-blackbox/releases/latest)
→ **Settings → Capabilities → Skills → Upload skill**. (Hooks are a Claude Code feature; on Claude.ai you get the checkpoint workflow.)

## 🕹️ Usage

Just talk to Claude:

> *"Where did we leave off?"* · *"Resume the last session"* · *"Save a checkpoint"* · *"Show me the project timeline"*

Or use the CLI directly:

| Command | What it does |
|---|---|
| `blackbox.py resume` | Everything you need after a crash: state, interrupted commands, git, last events |
| `blackbox.py checkpoint --task "…" --done "…" --next "…"` | Save progress (Claude does this on its own after each step) |
| `blackbox.py checkpoint --decision "…"` | Record an important decision in `decisions.md` |
| `blackbox.py timeline` | The whole story: day → session → event |
| `blackbox.py history -n 30` | Latest events |
| `blackbox.py status` · `verify` | Last checkpoint · integrity check |

## 🧠 How it works

```
 Claude Code hooks                       .blackbox/   (local, git-ignored)
 ─────────────────                       ─────────────────────────────────
 SessionStart ──────► inject recovered ─► checkpoints/state.json   ← atomic
 UserPromptSubmit ──► prompts.md          snapshots/state-*.json   ← last 50
 PreToolUse (Bash) ─► "started" marker    history/events.jsonl     ← append-only
 PostToolUse ───────► files changed       history/prompts.md
 PreCompact / Stop ─► checkpoint + git    history/commands.log
                                          history/decisions.md
```

Each event also stores Claude Code's `transcript_path`, so the full conversation can always be found.

## ❓ FAQ

**Does it slow Claude down?** No. Each hook is a few milliseconds of local file I/O; it has a 10 s timeout and never blocks or fails your session.

**Is my data sent anywhere?** No. Everything is plain files inside `.blackbox/` in your project.

**Can it recover what Claude was typing when the power went out?** No, and nobody can: text that was only in memory is gone. What you get is the last persisted state, the last checkpoint, the interrupted command, and the transcript path. That is usually all you need to continue.

**I installed it mid-project. Do I get my old history?** History starts at installation. Older Claude Code transcripts in `~/.claude/projects/` are still on disk, and Claude can read them if you ask.

## 🤝 Contributing

Issues and PRs are welcome. Ideas: an HTML timeline viewer, daily summaries, a transcript indexer, a VS Code panel.
If this saved your session once, **a ⭐ helps other people find it.**

## 📄 License

[MIT](LICENSE)
