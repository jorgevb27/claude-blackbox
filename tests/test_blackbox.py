import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1] / "skills" / "claude-blackbox"
SCRIPT = ROOT / "scripts" / "blackbox.py"
sys.path.insert(0, str(SCRIPT.parent))
import blackbox as bb  # noqa: E402


class RedactionTest(unittest.TestCase):
    SECRETS = [
        "sk-ant-api03-abcdefghijklmnopqrstuvwxyz",
        "sk_live_51Habc123def456ghi789",
        "sk_test_51Habc123def456ghi789",
        "whsec_abcdef1234567890",
        "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        "AKIAABCDEFGHIJKLMNOP",
        "AIzaSyA1234567890abcdefghijklmnopqrstu",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
    ]

    def test_known_token_formats_are_redacted(self):
        for s in self.SECRETS:
            self.assertNotIn(s, bb.redact(f"my key is {s} ok"), s)

    def test_key_value_and_url_credentials(self):
        out = bb.redact("password=hunter2 postgres://admin:s3cret@db:5432/app Bearer abcdefghijklmnop")
        for s in ("hunter2", "s3cret", "abcdefghijklmnop"):
            self.assertNotIn(s, out)

    def test_plain_text_untouched(self):
        self.assertEqual(bb.redact("pytest tests/test_cart.py"), "pytest tests/test_cart.py")


class HookFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = dict(os.environ, CLAUDE_PROJECT_DIR=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def hook(self, **payload):
        payload.setdefault("cwd", self.tmp.name)
        payload.setdefault("session_id", "s1")
        return subprocess.run([sys.executable, str(SCRIPT), "hook"], input=json.dumps(payload), env=self.env,
                              capture_output=True, text=True, encoding="utf-8", check=True).stdout

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.tmp.name, env=self.env,
                              capture_output=True, text=True, encoding="utf-8").stdout

    def test_prompt_secret_never_reaches_disk(self):
        self.hook(hook_event_name="UserPromptSubmit", prompt="use sk_live_51Habc123def456ghi789 please")
        base = pathlib.Path(self.tmp.name) / ".blackbox"
        for f in base.rglob("*"):
            if f.is_file():
                self.assertNotIn("sk_live_51H", f.read_text(encoding="utf-8"), f)

    def test_interrupted_command_is_detected_on_resume(self):
        self.hook(hook_event_name="SessionStart", source="startup")
        self.cli("checkpoint", "--task", "T", "--next", "N")
        self.hook(hook_event_name="PreToolUse", tool_name="Bash", tool_input={"command": "alembic upgrade head"})
        ctx = self.hook(hook_event_name="SessionStart", session_id="s2", source="startup")
        self.assertIn("next step: N", ctx)
        self.assertIn("alembic upgrade head", ctx)
        self.assertIn("STARTED but never reported", self.cli("resume"))

    def test_finished_command_is_not_flagged(self):
        self.cli("checkpoint", "--task", "T")
        for name in ("PreToolUse", "PostToolUse"):
            self.hook(hook_event_name=name, tool_name="Bash", tool_input={"command": "pytest"})
        self.assertNotIn("never reported", self.cli("resume"))

    def test_edited_files_are_tracked_relative(self):
        self.hook(hook_event_name="PostToolUse", tool_name="Edit",
                  tool_input={"file_path": str(pathlib.Path(self.tmp.name) / "src" / "a.py")})
        state = json.loads((pathlib.Path(self.tmp.name) / ".blackbox/checkpoints/state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["files_changed"], ["src/a.py"])

    def test_history_folder_ignores_itself(self):
        self.hook(hook_event_name="SessionStart", source="startup")
        gi = pathlib.Path(self.tmp.name) / ".blackbox" / ".gitignore"
        self.assertIn("*", gi.read_text(encoding="utf-8").splitlines())

    def test_bad_input_never_breaks_the_session(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "hook"], input="{not json", env=self.env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)

    def test_torn_line_is_tolerated(self):
        self.cli("checkpoint", "--task", "T")
        with open(pathlib.Path(self.tmp.name) / ".blackbox/history/events.jsonl", "a", encoding="utf-8") as f:
            f.write('{"half": ')
        out = self.cli("verify")
        self.assertIn("torn line", out)
        self.assertIn("checkpoint OK", out)

    def test_install_hooks_is_idempotent_and_keeps_settings(self):
        settings = pathlib.Path(self.tmp.name) / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text('{"model": "opus"}', encoding="utf-8")
        self.cli("install-hooks")
        self.cli("install-hooks")
        cfg = json.loads(settings.read_text(encoding="utf-8"))
        self.assertEqual(cfg["model"], "opus")
        self.assertEqual(len(cfg["hooks"]["SessionStart"]), 1)


if __name__ == "__main__":
    unittest.main()
