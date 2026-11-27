import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import push_tags as app
import install


class TagsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.log = self.root / 'calls'
        self.env = patch.dict(os.environ, {
            'PATH': str(self.bin) + os.pathsep + os.environ['PATH'],
            'PUSH_TAGS_STATE_DIR': str(self.root / 'state'),
            'TEST_LOG': str(self.log),
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.fake('git', 'import sys, os, json\nwith open(os.environ["TEST_LOG"], "a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\nprint("git output")\nprint("git error output", file=sys.stderr)\nsys.exit(int(os.environ.get("GIT_STATUS", "0")))')
        self.fake('afplay', 'pass')
        self.fake('gh', 'import sys\nprint("private error", file=sys.stderr)\nsys.exit(1)')
        self.now = dt.datetime(2026, 1, 1, 12, tzinfo=app.UTC)

    def fake(self, name, body):
        path = self.bin / name
        path.write_text(f'#!{sys.executable}\n{body}\n')
        path.chmod(0o755)
        return path

    def baseline(self):
        with patch.object(app, 'gh_json', return_value={'login': 'coder'}), patch.object(app, 'notify') as sound:
            app.poll(self.now)
            sound.assert_not_called()

    def item(self, identity='7'):
        return {'id': int(identity), 'pull_request': {'url': f'https://api.github.com/repos/org/repo/pulls/{identity}'}}

    def detail(self, when, author='coder', merger='other'):
        return {'merged': True, 'merged_at': app.stamp(when), 'user': {'login': author}, 'merged_by': {'login': merger}}

    def test_successful_push_forwards_and_plays(self):
        with patch.object(app, 'notify') as sound:
            self.assertEqual(app.push(['origin', 'HEAD', '--force-with-lease']), 0)
            sound.assert_called_once_with('push')
        self.assertEqual(json.loads(self.log.read_text()), ['push', 'origin', 'HEAD', '--force-with-lease'])

    def test_failed_push_keeps_exact_status(self):
        with patch.dict(os.environ, {'GIT_STATUS': '42'}), patch.object(app, 'notify') as sound:
            self.assertEqual(app.push(['origin']), 42)
            sound.assert_not_called()

    def test_audio_failure_does_not_change_push(self):
        with patch.object(app, 'play', side_effect=OSError('missing')):
            self.assertEqual(app.push([]), 0)

    def test_shell_global_arguments_and_output(self):
        command = f'source "{ROOT / "shell.zsh"}"; CODE_PUSH_TAGS_PYTHON=""; git -C "some directory" -c x=y --no-pager push origin HEAD'
        result = subprocess.run(['zsh', '-f', '-c', command], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, 'git output\n')
        self.assertEqual(result.stderr, 'git error output\n')
        self.assertEqual(json.loads(self.log.read_text()), ['-C', 'some directory', '-c', 'x=y', '--no-pager', 'push', 'origin', 'HEAD'])

    def test_shell_failed_status_and_other_commands(self):
        with patch.dict(os.environ, {'GIT_STATUS': '27'}):
            result = subprocess.run(['zsh', '-f', '-c', f'source "{ROOT / "shell.zsh"}"; git log push'], capture_output=True)
        self.assertEqual(result.returncode, 27)
        self.assertEqual(json.loads(self.log.read_text()), ['log', 'push'])

    def test_first_run_only_stores_baseline(self):
        self.baseline()
        state = app.read_json(app.state_dir() / 'merges.json', {})
        self.assertEqual(state['started_at'], app.stamp(self.now))
        self.assertEqual(state['seen'], [])

    def test_authored_and_merged_events_deduplicate(self):
        self.baseline()
        later = self.now + dt.timedelta(minutes=1)
        def gh(args, env):
            if args == ['api', 'user']:
                return {'login': 'coder'}
            if 'search/issues' in args:
                return {'items': [dict(self.item(), id=6569347267)], 'total_count': 1}
            if '/events?' in args[1]:
                return [{'type': 'PullRequestEvent', 'payload': {'action': 'closed', 'pull_request': {'id': 5461662178, 'url': self.item()['pull_request']['url'], 'merged': True}}}]
            return self.detail(later, author='other', merger='coder')
        with patch.object(app, 'gh_json', side_effect=gh), patch.object(app, 'gh_events', side_effect=lambda login, page, env: (gh(['api', f'users/{login}/events?'], env), 60)), patch.object(app, 'notify') as sound:
            app.poll(later)
            state = app.read_json(app.state_dir() / 'merges.json', {})
            self.assertEqual(state['seen'], [[self.item()['pull_request']['url'], app.stamp(later)]])
            # Each poll reads its deduplication state from disk.
            app.poll(later + dt.timedelta(minutes=1))
            sound.assert_called_once_with('merge')

    def test_delayed_search_result_survives_restart(self):
        self.baseline()
        with patch.object(app, 'gh_json', return_value={'login': 'coder'}), patch.object(app, 'search_merges', return_value={}):
            app.poll(self.now + dt.timedelta(hours=2))
        with patch.object(app, 'gh_json', side_effect=[{'login': 'coder'}, self.detail(self.now + dt.timedelta(minutes=2))]), patch.object(app, 'search_merges', return_value={'7': self.item()}) as search, patch.object(app, 'notify') as sound:
            app.poll(self.now + dt.timedelta(hours=3))
            self.assertEqual(search.call_args.args[1], self.now)
            sound.assert_called_once_with('merge')

    def test_historic_and_unrelated_merges_are_silent(self):
        self.baseline()
        with patch.object(app, 'gh_json', side_effect=[{'login': 'coder'}, self.detail(self.now - dt.timedelta(seconds=1)), self.detail(self.now + dt.timedelta(seconds=1), 'other', 'other')]), patch.object(app, 'search_merges', return_value={'7': self.item(), '8': self.item('8')}), patch.object(app, 'notify') as sound:
            app.poll(self.now + dt.timedelta(minutes=1))
            sound.assert_not_called()

    def test_auth_failure_keeps_checkpoint_and_hides_stderr(self):
        self.baseline()
        path = app.state_dir() / 'merges.json'
        before = path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'authentication') as error:
            app.poll(self.now + dt.timedelta(minutes=1))
        self.assertNotIn('private error', str(error.exception))
        self.assertEqual(path.read_bytes(), before)

    def test_mute_skips_audio(self):
        app.write_json(app.state_dir() / 'settings.json', {'muted': True})
        with patch.object(app.subprocess, 'Popen') as player:
            self.assertFalse(app.play('push'))
            player.assert_not_called()
        self.assertFalse((app.state_dir() / 'last-playback.json').exists())

    def test_audio_uses_afplay_without_wait(self):
        audio = ROOT / 'tests' / 'temporary.wav'
        audio.write_bytes(b'fake')
        self.addCleanup(lambda: audio.unlink(missing_ok=True))
        with patch.object(app, 'tags', return_value=[{'id': 'x', 'file': 'tests/temporary.wav', 'event': 'push'}]), patch.object(app.subprocess, 'Popen') as player:
            self.assertTrue(app.play('push'))
            self.assertEqual(player.call_args.args[0][:3], ['afplay', '-v', '0.45'])
            self.assertTrue(player.call_args.kwargs['start_new_session'])

    def playback_tag(self):
        with wave.open(str(self.root / 'sample.wav'), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b'\0\0' * 3200)
        return {'id': 'sample', 'text': 'Build complete', 'producer': 'Test producer',
                'file': 'sample.wav', 'event': 'any', '_root': str(self.root)}

    def test_audio_launch_records_display_signal_with_wav_duration(self):
        tag = self.playback_tag()
        with patch.object(app, 'tags', return_value=[tag]), patch.object(app.subprocess, 'Popen'), patch.object(app.time, 'time', return_value=1234.5):
            self.assertTrue(app.play('merge', 'sample'))
            record = app.read_json(app.state_dir() / 'last-playback.json', {})
            self.assertEqual({key: value for key, value in record.items() if key != 'id'}, {
                'tag_id': 'sample', 'text': 'Build complete', 'producer': 'Test producer',
                'event': 'merge', 'started_at': 1234.5, 'duration_seconds': 0.4,
            })
            self.assertEqual(len(record['id']), 32)
            self.assertTrue(app.play('merge', 'sample'))
            self.assertNotEqual(record['id'], app.read_json(app.state_dir() / 'last-playback.json', {})['id'])

    def test_audio_spawn_failure_does_not_record_display_signal(self):
        tag = self.playback_tag()
        with patch.object(app, 'tags', return_value=[tag]), patch.object(app.subprocess, 'Popen', side_effect=OSError('Cannot start afplay')):
            with self.assertRaises(OSError):
                app.play('push', 'sample')
        self.assertFalse((app.state_dir() / 'last-playback.json').exists())

    def test_display_signal_write_failure_preserves_audio_success(self):
        tag = self.playback_tag()
        with patch.object(app, 'tags', return_value=[tag]), patch.object(app.subprocess, 'Popen') as player, patch.object(app, 'write_json', side_effect=OSError('Display state unavailable')):
            self.assertTrue(app.play('push', 'sample'))
            player.assert_called_once()

    def test_disabled_or_unavailable_sound_does_not_record_display_signal(self):
        tag = self.playback_tag()
        app.write_json(app.state_dir() / 'config.json', {'push_enabled': False})
        with patch.object(app, 'tags', return_value=[tag]), patch.object(app.subprocess, 'Popen') as player:
            self.assertFalse(app.play('push', 'sample'))
            self.assertFalse(app.play('any', 'missing'))
            player.assert_not_called()
        self.assertFalse((app.state_dir() / 'last-playback.json').exists())

    def test_personal_selection_and_disabled_triggers(self):
        audio = ROOT / 'tests' / 'temporary.wav'
        audio.write_bytes(b'fake')
        self.addCleanup(lambda: audio.unlink(missing_ok=True))
        available = [{'id': 'selected', 'file': 'tests/temporary.wav', 'event': 'push'},
                     {'id': 'other', 'file': 'tests/temporary.wav', 'event': 'push'}]
        app.write_json(app.state_dir() / 'config.json', {'push_tag': 'selected', 'merge_enabled': False})
        with patch.object(app, 'tags', return_value=available), patch.object(app.subprocess, 'Popen'), patch.object(app.random, 'choice', side_effect=lambda choices: choices[0]) as choice:
            self.assertTrue(app.play('push'))
            self.assertEqual([tag['id'] for tag in choice.call_args.args[0]], ['selected'])
        with patch.object(app, 'gh_json') as github:
            app.poll(self.now)
            github.assert_not_called()
        app.write_json(app.state_dir() / 'config.json', {'push_enabled': False})
        with patch.object(app.subprocess, 'Popen') as player:
            self.assertFalse(app.play('push'))
            player.assert_not_called()

    def test_concurrent_poll_returns_without_network(self):
        import fcntl
        with (app.state_dir() / 'poll.lock').open('a') as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(app, 'gh_json') as github:
                app.poll(self.now)
                github.assert_not_called()

    def test_old_events_do_not_fetch_historic_metadata(self):
        def gh(args, env):
            if 'search/issues' in args:
                return {'items': [], 'total_count': 0}
            return [{'type': 'PullRequestEvent', 'created_at': app.stamp(self.now - dt.timedelta(days=5)),
                     'payload': {'action': 'closed', 'pull_request': {'id': 7, 'url': 'unused', 'merged': True}}}]
        with patch.object(app, 'gh_json', side_effect=gh), patch.object(app, 'gh_events', side_effect=lambda login, page, env: (gh(['api', f'users/{login}/events?'], env), 60)):
            self.assertEqual(app.search_merges('coder', self.now, {}), {})

    def test_compact_merged_event_is_confirmed_with_pr_detail(self):
        self.baseline()
        later = self.now + dt.timedelta(minutes=1)
        compact = {'type': 'PullRequestEvent', 'created_at': app.stamp(later),
                   'payload': {'action': 'merged', 'pull_request': {'id': 7, 'number': 7,
                       'url': self.item()['pull_request']['url'], 'head': {}, 'base': {}}}}
        def gh(args, env):
            if args == ['api', 'user']:
                return {'login': 'coder'}
            if 'search/issues' in args:
                return {'items': [], 'total_count': 0}
            return self.detail(later, author='other', merger='coder')
        with patch.object(app, 'gh_json', side_effect=gh) as github, patch.object(app, 'gh_events', return_value=([compact], 60)), patch.object(app, 'notify') as sound:
            app.poll(later)
            sound.assert_called_once_with('merge')
            self.assertIn(unittest.mock.call(['api', compact['payload']['pull_request']['url']], unittest.mock.ANY), github.call_args_list)

    def test_events_poll_interval_persists_and_search_continues(self):
        self.baseline()
        later = self.now + dt.timedelta(minutes=1)
        def gh(args, env):
            return {'login': 'coder'} if args == ['api', 'user'] else {'items': [], 'total_count': 0}
        with patch.object(app, 'gh_json', side_effect=gh) as github, patch.object(app, 'gh_events', return_value=([], 180)) as events:
            app.poll(later)
            self.assertEqual(events.call_count, 1)
            self.assertEqual(app.read_json(app.state_dir() / 'merges.json', {})['events_next_at'], app.stamp(later + dt.timedelta(seconds=180)))
            app.poll(later + dt.timedelta(seconds=60))
            self.assertEqual(events.call_count, 1)
            # A new poll reads the saved interval, with no in-memory timer.
            app.poll(later + dt.timedelta(seconds=179))
            self.assertEqual(events.call_count, 1)
            app.poll(later + dt.timedelta(seconds=180))
            self.assertEqual(events.call_count, 2)
            self.assertEqual(sum('search/issues' in call.args[0] for call in github.call_args_list), 8)

    def test_events_header_read(self):
        response = subprocess.CompletedProcess([], 0, 'HTTP/2.0 200 OK\nX-Poll-Interval: 180\nContent-Type: application/json\n\n[]\n', '')
        with patch.object(app.subprocess, 'run', return_value=response) as request:
            self.assertEqual(app.gh_events('coder', 1, {}), ([], 180))
            self.assertIn('--include', request.call_args.args[0])

    def test_explicit_selection_can_use_any_event_tag(self):
        audio = ROOT / 'tests' / 'temporary.wav'
        audio.write_bytes(b'fake')
        self.addCleanup(lambda: audio.unlink(missing_ok=True))
        available = [{'id': 'merge-clip', 'file': 'tests/temporary.wav', 'event': 'merge'}]
        with patch.object(app, 'tags', return_value=available), patch.object(sys, 'argv', ['push_tags.py', 'configure', '--push-tag', 'merge-clip']):
            self.assertEqual(app.main(), 0)
        with patch.object(app, 'tags', return_value=available), patch.object(app.subprocess, 'Popen'):
            self.assertTrue(app.play('push'))
            self.assertTrue(app.play('push', 'merge-clip'))
        app.write_json(app.state_dir() / 'config.json', {'push_tag': 'random'})
        with patch.object(app, 'tags', return_value=available), patch.object(app.subprocess, 'Popen') as player:
            self.assertFalse(app.play('push'))
            player.assert_not_called()

    def test_installer_backup_idempotence_and_removal(self):
        path = self.root / '.zshenv'
        path.write_text('export EXAMPLE=yes\n')
        with patch.object(install.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'git: command\n', '')):
            install.install_shell(path)
            install.install_shell(path)
        self.assertEqual(path.read_text().count(install.BEGIN), 1)
        self.assertTrue(list(self.root.glob('.zshenv.push-tags-backup-*')))
        self.assertIn('export EXAMPLE=yes', install.strip_block(path.read_text()))

    def test_installer_refuses_custom_git(self):
        path = self.root / '.zshrc'
        path.write_text('git() { echo custom; }\n')
        with self.assertRaisesRegex(RuntimeError, 'existing git'):
            install.install_shell(path)
        self.assertEqual(path.read_text(), 'git() { echo custom; }\n')


if __name__ == '__main__':
    unittest.main()
