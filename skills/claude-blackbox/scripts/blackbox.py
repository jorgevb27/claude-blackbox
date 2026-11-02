#!/usr/bin/env python3
"""claude-blackbox — the flight recorder for Claude Code.

Records an append-only timeline of your Claude sessions (prompts, commands,
edited files, decisions) plus an atomic checkpoint, so you can resume exactly
where you left off after a crash, power cut, reboot or context compaction.

Usage:
  blackbox.py checkpoint [--task T] [--next N] [--done D] [--decision X] [--note M]
  blackbox.py status | verify | resume | history [-n 20] | timeline
  blackbox.py install-hooks [--global]
  blackbox.py hook            (called by Claude Code hooks, reads JSON on stdin)

Zero dependencies. Python 3.8+. Everything stays local in .blackbox/.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

VERSION = "1.0.0"
DATA_DIR = ".blackbox"
MAX_FILES = 200
MAX_SNAPSHOTS = 50
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

def project_root(payload=None):
    if payload and payload.get("cwd"):
        env = os.environ.get("CLAUDE_PROJECT_DIR")
        return Path(env) if env else Path(payload["cwd"])
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


class P:
    def __init__(self, root):
        self.root = Path(root)
        self.base = self.root / DATA_DIR
        self.history = self.base / "history"
        self.state = self.base / "checkpoints" / "state.json"
        self.snapshots = self.base / "snapshots"
        self.events = self.history / "events.jsonl"
        self.commands = self.history / "commands.log"
        self.prompts = self.history / "prompts.md"
        self.decisions = self.history / "decisions.md"

    def ensure(self):
        for d in (self.history, self.state.parent, self.snapshots):
            d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"\b(sk-[A-Za-z0-9_\-]{16,})"), "[REDACTED]"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"), "[REDACTED]"),
    (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "[REDACTED]"),
    (re.compile(r"\b(xox[abprs]-[A-Za-z0-9\-]{10,})"), "[REDACTED]"),
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-~+/=]{8,}"), r"\1 [REDACTED]"),
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)(\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|\S+)"), r"\1\2[REDACTED]"),
    (re.compile(r"(?i)(://[^:/\s]+:)[^@/\s]+@"), r"\1[REDACTED]@"),
]


def redact(text, limit=None):
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False) if text is not None else ""
    for rx, repl in SECRET_PATTERNS:
        text = rx.sub(repl, text)
    if limit and len(text) > limit:
        text = text[:limit] + "…"
    return text


def git_status(root):
    try:
        p = subprocess.run(["git", "status", "--short", "--branch"], cwd=str(root),
                           text=True, capture_output=True, timeout=5)
        return p.stdout.strip() if p.returncode == 0 else "(not a git repository)"
    except Exception as e:  # git missing / timeout
        return f"(git unavailable: {e})"


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def append(path, line):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


def load_state(p):
    if p.state.exists():
        try:
            return json.loads(p.state.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def blank_state():
    return {"schema": 3, "updated_at": "", "session_id": "", "task": "",
            "last_prompt": "", "last_command": "", "completed": [],
            "next_step": "", "files_changed": [], "decisions": [],
            "git": "", "last_event_id": ""}


def event(p, kind, data=None, session_id=""):
    p.ensure()
    e = {"event_id": str(uuid.uuid4()), "timestamp": now(), "kind": kind,
         "session_id": session_id or "", "data": data or {}}
    append(p.events, json.dumps(e, ensure_ascii=False))
    return e


def read_events(p):
    if not p.events.exists():
        return []
    out = []
    for line in p.events.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue  # tolerate a torn last line after a power cut
    return out


def snapshot(p, state):
    p.snapshots.mkdir(parents=True, exist_ok=True)
    name = f"state-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    atomic_json(p.snapshots / name, state)
    snaps = sorted(p.snapshots.glob("state-*.json"))
    for old in snaps[:-MAX_SNAPSHOTS]:
        try:
            old.unlink()
        except OSError:
            pass


def unfinished_command(events):
    """Return the last Bash command that started but never reported back."""
    pending = {}
    for e in events:
        d = e.get("data", {})
        if d.get("tool") != "Bash":
            continue
        key = (e.get("session_id"), d.get("command"))
        if e.get("kind") == "PreToolUse":
            pending[key] = e
        elif e.get("kind") == "PostToolUse":
            pending.pop(key, None)
    return list(pending.values())[-1] if pending else None


# --------------------------------------------------------------------------- #
# CLI commands
# --------------------------------------------------------------------------- #

def cmd_checkpoint(a, p):
    p.ensure()
    s = {**blank_state(), **load_state(p)}
    if a.task:
        s["task"] = a.task
    if a.next:
        s["next_step"] = a.next
    if a.done:
        s["completed"].append({"at": now(), "what": a.done})
    if a.decision:
        s["decisions"].append({"at": now(), "what": a.decision})
        append(p.decisions, f"- **{now()}** — {a.decision}")
    e = event(p, "checkpoint", {"task": s["task"], "next_step": s["next_step"],
                                "done": a.done or "", "decision": a.decision or "",
                                "note": a.note or ""}, s.get("session_id", ""))
    s.update(updated_at=now(), git=git_status(p.root), last_event_id=e["event_id"])
    atomic_json(p.state, s)
    snapshot(p, s)
    print(f"✔ checkpoint saved → {p.state}")
    print(f"  task:      {s['task'] or '-'}")
    print(f"  next step: {s['next_step'] or '-'}")


def print_state(s):
    print(f"  updated:      {s.get('updated_at') or '-'}")
    print(f"  session:      {s.get('session_id') or '-'}")
    print(f"  task:         {s.get('task') or '-'}")
    print(f"  next step:    {s.get('next_step') or '-'}")
    print(f"  last prompt:  {s.get('last_prompt') or '-'}")
    print(f"  last command: {s.get('last_command') or '-'}")
    done = s.get("completed") or []
    if done:
        print("  completed:")
        for d in done[-5:]:
            print(f"    ✔ {d.get('what') if isinstance(d, dict) else d}")
    files = s.get("files_changed") or []
    if files:
        print(f"  files changed ({len(files)}):")
        for f in files[-10:]:
            print(f"    • {f}")


def cmd_status(a, p):
    s = load_state(p)
    if not s:
        print("No checkpoint yet. Run: blackbox.py checkpoint --task \"...\" --next \"...\"")
        return 0
    print("■ claude-blackbox status")
    print_state(s)


def cmd_verify(a, p):
    errors, warnings = [], []
    if not p.state.exists():
        errors.append("no checkpoint (state.json) found")
    else:
        try:
            json.loads(p.state.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"state.json is corrupt: {e} — restore the newest file from {p.snapshots}")
    bad = 0
    if p.events.exists():
        for line in p.events.read_text(encoding="utf-8").splitlines():
            try:
                json.loads(line)
            except Exception:
                bad += 1
        if bad:
            warnings.append(f"{bad} torn line(s) in events.jsonl (normal after a power cut; ignored)")
    else:
        warnings.append("events.jsonl does not exist yet (hooks not installed or never fired)")
    for w in warnings:
        print(f"⚠ {w}")
    if errors:
        for e in errors:
            print(f"✖ {e}")
        return 1
    print("✔ checkpoint OK")
    print("✔ history OK")
    return 0


def cmd_resume(a, p):
    if cmd_verify(a, p) != 0:
        return 1
    s = load_state(p)
    events = read_events(p)
    print("\n■ RESUME — where you left off")
    print_state(s)
    pend = unfinished_command(events)
    if pend:
        print(f"\n⚠ This command STARTED but never reported a result (crash/cut?):\n    {pend['data'].get('command')}")
        print("  Do not assume it finished. Check its effects before continuing.")
    print("\n■ git")
    print("  " + git_status(p.root).replace("\n", "\n  "))
    print("\n■ last events")
    for e in events[-10:]:
        print("  " + fmt_event(e))
    print("\nNext: review the files above, then continue from 'next step'.")


def fmt_event(e):
    d = e.get("data", {})
    t = e.get("timestamp", "")[11:19]
    k = e.get("kind", "")
    detail = d.get("command") or d.get("file") or d.get("prompt") or d.get("next_step") or d.get("tool") or d.get("source") or ""
    tool = f"{d['tool']} " if d.get("tool") and detail != d.get("tool") else ""
    return f"{t}  {k:<17} {tool}{redact(detail, 100)}".rstrip()


def cmd_history(a, p):
    events = read_events(p)
    if not events:
        print("No events recorded yet.")
        return 0
    print(f"■ {len(events)} events recorded")
    for e in events[-a.n:]:
        print("  " + fmt_event(e))


def cmd_timeline(a, p):
    events = read_events(p)
    if not events:
        print("No events recorded yet.")
        return 0
    day = sess = None
    for e in events:
        d = e.get("timestamp", "")[:10]
        if d != day:
            day, sess = d, None
            print(f"\n📅 {day}")
        s = e.get("session_id") or "-"
        if s != sess:
            sess = s
            print(f"  └─ session {s[:8]}")
        print("      " + fmt_event(e))


# --------------------------------------------------------------------------- #
# Hook handler (called by Claude Code)
# --------------------------------------------------------------------------- #

def cmd_hook(a, p_unused):
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        handle_hook(payload)
    except Exception as e:  # a hook must never break the user's session
        sys.stderr.write(f"claude-blackbox: {e}\n")
    return 0


def handle_hook(payload):
    p = P(project_root(payload))
    p.ensure()
    name = payload.get("hook_event_name", "unknown")
    sid = payload.get("session_id", "")
    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input") or {}
    s = {**blank_state(), **load_state(p)}
    s["session_id"] = sid or s["session_id"]
    data = {}

    if name == "SessionStart":
        data = {"source": payload.get("source", ""), "transcript_path": payload.get("transcript_path", "")}
        context = session_context(p, s)
        if context:
            print(context)  # stdout of SessionStart is injected into Claude's context
    elif name == "UserPromptSubmit":
        prompt = redact(payload.get("prompt", ""), 1000)
        data = {"prompt": redact(prompt, 200)}
        s["last_prompt"] = redact(prompt, 300)
        append(p.prompts, f"\n### {now()} · session {sid[:8]}\n\n{prompt}\n")
    elif name in ("PreToolUse", "PostToolUse"):
        data = {"tool": tool}
        if tool == "Bash":
            cmd = redact(ti.get("command", ""), 500)
            data["command"] = cmd
            if name == "PreToolUse":
                s["last_command"] = cmd
                append(p.commands, f"{now()}  [{sid[:8]}]  $ {cmd}")
        elif ti.get("file_path") or ti.get("notebook_path"):
            f = ti.get("file_path") or ti.get("notebook_path")
            m = re.match(r"^/([a-zA-Z])/(.*)", f) if os.name == "nt" else None
            if m:  # Git Bash style /c/Users/... -> C:/Users/...
                f = f"{m.group(1).upper()}:/{m.group(2)}"
            try:
                f = Path(f).resolve().relative_to(p.root.resolve()).as_posix()
            except Exception:
                pass
            data["file"] = f
            if name == "PostToolUse" and tool in EDIT_TOOLS:
                files = [x for x in s["files_changed"] if x != f] + [f]
                s["files_changed"] = files[-MAX_FILES:]
        if name == "PreToolUse" and tool != "Bash":
            return  # only Bash needs a "started" marker; keep the log lean
    elif name == "PreCompact":
        data = {"trigger": payload.get("trigger", ""), "transcript_path": payload.get("transcript_path", "")}
    elif name in ("Stop", "SessionEnd"):
        data = {"transcript_path": payload.get("transcript_path", ""), "reason": payload.get("reason", "")}
    else:
        data = {"tool": tool} if tool else {}

    e = event(p, name, data, sid)
    s.update(updated_at=now(), last_event_id=e["event_id"])
    if name in ("Stop", "PreCompact", "SessionEnd"):
        s["git"] = git_status(p.root)
        atomic_json(p.state, s)
        snapshot(p, s)
    else:
        atomic_json(p.state, s)


def session_context(p, s):
    if not s.get("updated_at"):
        return ""
    events = read_events(p)
    lines = ["[claude-blackbox] Recovered state from the previous session:",
             f"- last activity: {s.get('updated_at')}"]
    for label, key in (("task", "task"), ("next step", "next_step"),
                       ("last user prompt", "last_prompt"), ("last command", "last_command")):
        if s.get(key):
            lines.append(f"- {label}: {s[key]}")
    files = s.get("files_changed") or []
    if files:
        lines.append(f"- recently changed files: {', '.join(files[-8:])}")
    pend = unfinished_command(events)
    if pend:
        lines.append(f"- WARNING: this command started but never reported a result: {pend['data'].get('command')} — verify its effects before continuing.")
    lines.append("Before continuing, check `git status` and inspect partially edited files. "
                 "Save progress with: blackbox.py checkpoint --task \"...\" --next \"...\"")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Installer
# --------------------------------------------------------------------------- #

HOOK_EVENTS = {
    "SessionStart": None,
    "UserPromptSubmit": None,
    "PreToolUse": "Bash",
    "PostToolUse": "*",
    "PreCompact": None,
    "Stop": None,
}


def cmd_install_hooks(a, p):
    runner = (Path(__file__).resolve().parent.parent / "hooks" / "run.sh")
    if a.use_global:
        settings = Path.home() / ".claude" / "settings.json"
        command = f'sh "{runner.as_posix()}" hook'
    else:
        settings = p.root / ".claude" / "settings.json"
        try:
            rel = runner.relative_to(p.root.resolve()).as_posix()
            command = f'sh "$CLAUDE_PROJECT_DIR/{rel}" hook'
        except ValueError:
            command = f'sh "{runner.as_posix()}" hook'

    cfg = {}
    if settings.exists():
        try:
            cfg = json.loads(settings.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"✖ {settings} is not valid JSON ({e}). Fix it first; nothing was changed.")
            return 1
        backup = settings.with_suffix(".json.bak")
        backup.write_text(settings.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  backup → {backup}")

    hooks = cfg.setdefault("hooks", {})
    added = 0
    for ev, matcher in HOOK_EVENTS.items():
        groups = hooks.setdefault(ev, [])
        if any("blackbox" in h.get("command", "") for g in groups for h in g.get("hooks", [])):
            continue
        group = {"hooks": [{"type": "command", "command": command, "timeout": 10}]}
        if matcher:
            group = {"matcher": matcher, **group}
        groups.append(group)
        added += 1
    atomic_json(settings, cfg)
    print(f"✔ {added} hook(s) added to {settings} (existing settings preserved)")

    if not a.use_global:
        gi = p.root / ".gitignore"
        content = gi.read_text(encoding="utf-8") if gi.exists() else ""
        if DATA_DIR + "/" not in content.split():
            with gi.open("a", encoding="utf-8") as f:
                f.write(("" if content.endswith("\n") or not content else "\n") + DATA_DIR + "/\n")
            print(f"✔ added {DATA_DIR}/ to .gitignore (your history stays private)")
    print("Restart Claude Code (or run /hooks) to activate. Your flight recorder is armed. ✈")


# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser(prog="blackbox", description="claude-blackbox — flight recorder for Claude Code")
    ap.add_argument("--version", action="version", version=f"claude-blackbox {VERSION}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("checkpoint", help="save a recoverable checkpoint")
    c.add_argument("--task", help="what you are working on")
    c.add_argument("--next", help="the very next step")
    c.add_argument("--done", help="mark something as completed")
    c.add_argument("--decision", help="record an important decision")
    c.add_argument("--note", help="free-form note for the timeline")
    sub.add_parser("status", help="show the last checkpoint")
    sub.add_parser("verify", help="check checkpoint and history integrity")
    sub.add_parser("resume", help="everything you need to continue after a crash")
    h = sub.add_parser("history", help="show the latest events")
    h.add_argument("-n", type=int, default=20)
    sub.add_parser("timeline", help="full timeline grouped by day and session")
    i = sub.add_parser("install-hooks", help="add the hooks to .claude/settings.json safely")
    i.add_argument("--global", dest="use_global", action="store_true", help="install in ~/.claude/settings.json")
    sub.add_parser("hook", help="internal: handle a Claude Code hook event from stdin")
    a = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    fn = globals()["cmd_" + a.cmd.replace("-", "_")]
    return fn(a, P(project_root())) or 0


if __name__ == "__main__":
    sys.exit(main())
