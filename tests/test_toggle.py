import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import push_tags as app


class GlobalMuteTests(unittest.TestCase):
    def test_short_commands_mute_both_event_types_and_restore(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'PUSH_TAGS_STATE_DIR': directory}):
            for command in ('off', 'on'):
                with patch.object(sys, 'argv', ['push-tags', command]):
                    app.main()
                self.assertEqual(app.read_json(Path(directory) / 'settings.json', {})['muted'], command == 'off')
                if command == 'off':
                    with patch.object(app.subprocess, 'Popen') as sound:
                        self.assertFalse(app.play('push'))
                        self.assertFalse(app.play('merge'))
                        sound.assert_not_called()

    def test_shell_helper_can_toggle_from_another_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            env = os.environ.copy()
            env['PUSH_TAGS_STATE_DIR'] = directory
            command = f'source "{app.ROOT / "shell.zsh"}"; push-tags off'
            result = subprocess.run(['zsh', '-f', '-c', command], cwd='/', env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(app.read_json(Path(directory) / 'settings.json', {})['muted'])
