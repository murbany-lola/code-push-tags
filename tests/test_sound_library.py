import base64
import fcntl
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import push_tags as app
import sound_library as library


class SoundLibraryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {'PUSH_TAGS_STATE_DIR': directory.name})
        environment.start()
        self.addCleanup(environment.stop)
        credentials = patch.object(app, 'gh_env', return_value={})
        credentials.start()
        self.addCleanup(credentials.stop)
        self.revision = 'a' * 40
        self.manifest = {'version': 1, 'tags': [
            {'id': 'one', 'text': 'First sound', 'file': 'audio/one.wav',
             'event': 'any', 'use_cases': ['push', 'merge']},
            {'id': 'two', 'text': 'Second sound', 'file': 'audio/two.wav', 'event': 'ci'},
        ], 'source_note': 'Keep manifest metadata'}
        stream = io.BytesIO()
        with wave.open(stream, 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b'\0\0' * 8)
        self.audio = stream.getvalue()
        self.calls = []
        self.failure = None

    def api(self, arguments, env):
        route = arguments[1]
        self.calls.append(route)
        if route.endswith('/commits/main'):
            return {'sha': self.revision}
        self.assertIn('?ref=' + self.revision, route)
        if 'manifest.json?' in route:
            data = json.dumps(self.manifest).encode()
        else:
            if self.failure and self.failure in route:
                raise RuntimeError('Download failed')
            data = self.audio
        return {'encoding': 'base64', 'content': base64.b64encode(data).decode()}

    def sync(self, force=True, now=100000):
        with patch.object(app, 'gh_json', side_effect=self.api), patch.object(library.time, 'time', return_value=now):
            return library.sync(force=force)

    def test_complete_snapshot_uses_one_revision_and_preserves_metadata(self):
        value = self.sync()
        self.assertTrue(value['updated'])
        root = Path(value['root'])
        self.assertEqual(root, (app.state_dir() / 'library' / self.revision).resolve())
        self.assertEqual(json.loads((root / 'manifest.json').read_text()), self.manifest)
        self.assertEqual((root / 'audio/one.wav').read_bytes(), self.audio)
        self.assertEqual(library.current_root(app.ROOT).resolve(), root)
        self.assertEqual(len(self.calls), 4)
        self.assertTrue(all('/commits/main' in call or self.revision in call for call in self.calls))

    def test_downloads_do_not_activate_an_incomplete_snapshot(self):
        original = self.api

        def observe(arguments, env):
            self.assertEqual(library.current_root(app.ROOT), app.ROOT)
            return original(arguments, env)

        with patch.object(app, 'gh_json', side_effect=observe):
            value = library.sync(force=True)
        self.assertTrue(value['updated'])

    def test_partial_download_keeps_previous_complete_snapshot(self):
        first = self.sync()
        self.revision = 'b' * 40
        self.failure = 'two.wav'
        value = self.sync()
        self.assertIn('error', value)
        self.assertEqual(value['root'], first['root'])
        self.assertEqual(library.current_root(app.ROOT).resolve(), Path(first['root']))
        self.assertFalse((app.state_dir() / 'library' / self.revision).exists())
        self.assertFalse(list((app.state_dir() / 'library').glob('.download-*')))

    def test_denied_private_repo_uses_bundled_library_without_payload_details(self):
        with patch.object(app, 'gh_json', side_effect=RuntimeError('403 private response detail')):
            value = library.sync(force=True)
        self.assertEqual(value['root'], str(app.ROOT))
        self.assertIsNone(value['revision'])
        self.assertNotIn('403 private', value['error'])

    def test_offline_sync_keeps_downloaded_library(self):
        first = self.sync()
        with patch.object(app, 'gh_env', side_effect=RuntimeError('Offline')):
            value = library.sync(force=True)
        self.assertEqual(value['root'], first['root'])
        self.assertFalse(value['updated'])

    def test_hourly_boundary_and_force_use_controlled_time(self):
        self.sync(force=False)
        count = len(self.calls)
        self.sync(force=False, now=103599)
        self.assertEqual(len(self.calls), count)
        self.sync(force=False, now=103600)
        self.assertEqual(len(self.calls), count + 1)
        self.sync(force=True, now=103601)
        self.assertEqual(len(self.calls), count + 2)

    def test_failed_check_is_also_throttled(self):
        self.failure = 'one.wav'
        first = self.sync(force=False)
        count = len(self.calls)
        value = self.sync(force=False, now=100001)
        self.assertEqual(len(self.calls), count)
        self.assertEqual(value['error'], first['error'])

    def test_second_sync_does_not_run_while_lock_is_held(self):
        with (app.state_dir() / 'library.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(app, 'gh_json') as request:
                value = library.sync(force=True)
            request.assert_not_called()
        self.assertFalse(value['updated'])

    def test_invalid_manifest_does_not_activate_or_download_audio(self):
        invalid_tags = [
            {'id': 'one', 'text': 'Bad path', 'file': '../push_tags.py'},
            {'id': 'one', 'text': 'Bad extension', 'file': 'audio/one.py'},
            {'id': 'one', 'text': 'Bad path', 'file': 'audio/../../one.wav'},
            {'id': 'one', 'text': 'Bad event', 'file': 'audio/one.wav', 'event': 'execute'},
            {'id': 'one', 'text': 'Bad category', 'file': 'audio/one.wav', 'use_cases': ['other']},
        ]
        for tag in invalid_tags:
            with self.subTest(tag=tag):
                self.manifest['tags'] = [tag]
                self.calls.clear()
                value = self.sync()
                self.assertIn('error', value)
                self.assertEqual(len(self.calls), 2)
                self.assertEqual(library.current_root(app.ROOT), app.ROOT)

    def test_duplicate_ids_are_rejected(self):
        self.manifest['tags'][1]['id'] = 'one'
        self.assertIn('error', self.sync())
        self.assertEqual(len(self.calls), 2)

    def test_invalid_or_truncated_wav_does_not_activate(self):
        for data in (b'not a WAV', self.audio[:-2]):
            with self.subTest(data=data):
                self.audio = data
                self.assertIn('error', self.sync())
                self.assertEqual(library.current_root(app.ROOT), app.ROOT)

    def test_invalid_pointer_cannot_select_a_path_outside_cache(self):
        app.write_json(app.state_dir() / 'library-current.json', {'revision': '../outside'})
        self.assertEqual(library.current_root(app.ROOT), app.ROOT)

    def test_existing_snapshot_can_be_reactivated_without_download(self):
        first = self.sync()
        (app.state_dir() / 'library-current.json').unlink()
        self.calls.clear()
        value = self.sync()
        self.assertTrue(value['updated'])
        self.assertEqual(value['root'], first['root'])
        self.assertEqual(len(self.calls), 1)

    def test_large_content_uses_blob_data_from_same_content_response(self):
        def request(arguments, env):
            if '/contents/' in arguments[1]:
                return {'encoding': 'none', 'sha': 'c' * 40}
            self.assertEqual(arguments[1], library.SOURCE + '/git/blobs/' + 'c' * 40)
            return {'encoding': 'base64', 'content': base64.b64encode(self.audio).decode()}

        with patch.object(app, 'gh_json', side_effect=request):
            self.assertEqual(library.content('audio/one.wav', self.revision, {}), self.audio)

    def test_event_selection_plays_from_downloaded_manifest_and_root(self):
        snapshot = self.sync()
        app.write_json(app.state_dir() / 'config.json', {'push_tag': 'one'})
        available = app.tags()
        self.assertEqual([tag['id'] for tag in available], ['one', 'two'])
        self.assertEqual(Path(available[0]['_root']).resolve(), Path(snapshot['root']))
        with patch.object(app.subprocess, 'Popen') as player:
            self.assertTrue(app.play('push'))
        self.assertEqual(player.call_args.args[0][-1], str(Path(snapshot['root']) / 'audio/one.wav'))

    def test_playback_keeps_captured_root_when_snapshot_changes_after_selection(self):
        first = self.sync()
        first_revision = self.revision
        self.revision = 'b' * 40
        second = self.sync()
        app.write_json(app.state_dir() / 'library-current.json', {'revision': first_revision})
        app.write_json(app.state_dir() / 'config.json', {'push_tag': 'one'})

        def choose(choices):
            app.write_json(app.state_dir() / 'library-current.json', {'revision': self.revision})
            return choices[0]

        with patch.object(app.random, 'choice', side_effect=choose), patch.object(app.subprocess, 'Popen') as player:
            self.assertTrue(app.play('push'))
        self.assertEqual(player.call_args.args[0][-1], str(Path(first['root']) / 'audio/one.wav'))
        self.assertEqual(library.current_root(app.ROOT).resolve(), Path(second['root']))

    def test_offline_refresh_keeps_selected_event_playable(self):
        snapshot = self.sync()
        app.write_json(app.state_dir() / 'config.json', {'ci_tag': 'two'})
        with patch.object(app, 'gh_json', side_effect=RuntimeError('Offline')):
            self.assertIn('error', library.sync(force=True))
        with patch.object(app.subprocess, 'Popen') as player:
            self.assertTrue(app.play('ci'))
        self.assertEqual(player.call_args.args[0][-1], str(Path(snapshot['root']) / 'audio/two.wav'))

    def test_bundled_event_remains_playable_without_repo_access(self):
        with patch.object(app, 'gh_json', side_effect=RuntimeError('Denied')):
            self.assertIn('error', library.sync(force=True))
        with patch.object(app.subprocess, 'Popen') as player:
            self.assertTrue(app.play('push', tag_id='stackaholics'))
        self.assertEqual(player.call_args.args[0][-1], str(app.ROOT / 'audio/stackaholics.wav'))


if __name__ == '__main__':
    unittest.main()
