from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dragon_codex_boot.launcher import Config, ConfigError, parse_command, resolve_video_path


class ConfigTests(unittest.TestCase):
    def write_config(self, root: Path, **overrides):
        data = {
            "DisplayName": "Dragon Codex Boot",
            "Video": "media/startup.mp4",
            "AppCommand": "chatgpt",
            "HoldAt": 11.3,
            "TransitionStart": 12.7,
            "TransitionEnd": 13.65,
            "MaxWaitSeconds": 60,
            "Volume": 1.0,
            "Fullscreen": True,
            "PlayerWidth": 1280,
            "PlayerHeight": 720,
            "SkipFadeSeconds": 0.25,
        }
        data.update(overrides)
        path = root / "launcher.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_loads_valid_config(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config.load(self.write_config(Path(temp)))
            self.assertEqual(config.display_name, "Dragon Codex Boot")
            self.assertEqual(config.app_command, ["chatgpt"])
            self.assertEqual(config.activate_command, ["chatgpt"])
            self.assertTrue(config.fullscreen)

    def test_rejects_invalid_transition_order(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_config(Path(temp), HoldAt=13.0)
            with self.assertRaises(ConfigError):
                Config.load(path)

    def test_rejects_invalid_volume(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_config(Path(temp), Volume=1.5)
            with self.assertRaises(ConfigError):
                Config.load(path)

    def test_parses_shell_style_command(self):
        self.assertEqual(parse_command("chatgpt --new-window"), ["chatgpt", "--new-window"])

    def test_relative_video_is_resolved_from_package_root(self):
        path = resolve_video_path("media/test.mp4")
        self.assertTrue(path.is_absolute())
        self.assertEqual(path.name, "test.mp4")


if __name__ == "__main__":
    unittest.main()
