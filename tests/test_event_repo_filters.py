import datetime as dt
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import push_tags as app
import repo_preferences as preferences
import webhook_receiver as receiver


class EventRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'PUSH_TAGS_STATE_DIR': self.temp.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.now = dt.datetime(2026, 11, 25, 12, tzinfo=app.UTC)
        self.identity = 'https://api.github.com/repos/team/project/pulls/7'
        app.write_json(app.state_dir() / 'merges.json', {'login': 'coder', 'started_at': app.stamp(self.now - dt.timedelta(minutes=10)), 'checkpoint': app.stamp(self.now - dt.timedelta(minutes=1)), 'seen': []})
        self.detail = {'merged': True, 'merged_at': app.stamp(self.now - dt.timedelta(seconds=10)), 'user': {'login': 'coder'}, 'merged_by': {'login': 'other'}}

    def test_push_uses_original_git_context_and_selected_organization(self):
        preferences.set_preferences([], ['team'])
        args = ['-C', '/some/checkout', 'push', 'origin', 'HEAD']
        with patch.object(preferences, 'git_repository', return_value='team/project') as origin, patch.object(app, 'notify') as notify:
            app.notify_push(args)
            origin.assert_called_once_with(args)
            notify.assert_called_once_with('push')

    def test_excluded_push_is_silent(self):
        preferences.set_preferences(['other/project'], [])
        with patch.object(preferences, 'git_repository', return_value='team/project'), patch.object(app, 'notify') as notify:
            app.notify_push()
            notify.assert_not_called()

    def test_poll_records_excluded_merge_without_replay(self):
        preferences.set_preferences([], [])
        with patch.object(app, 'gh_env', return_value={}), patch.object(app, 'gh_json', side_effect=[{'login': 'coder'}, self.detail]), patch.object(app, 'search_merges', return_value={self.identity: {'pull_request': {'url': self.identity}}}), patch.object(app, 'notify') as notify:
            app.poll(self.now)
            notify.assert_not_called()
        self.assertIn(self.identity, dict(app.read_json(app.state_dir() / 'merges.json', {})['seen']))
        preferences.set_preferences([], ['team'])
        with patch.object(app, 'gh_env', return_value={}), patch.object(app, 'gh_json', return_value={'login': 'coder'}), patch.object(app, 'search_merges', return_value={self.identity: {'pull_request': {'url': self.identity}}}), patch.object(app, 'notify') as notify:
            app.poll(self.now + dt.timedelta(seconds=1))
            notify.assert_not_called()

    def test_webhook_records_excluded_merge_and_does_not_replay(self):
        preferences.set_preferences([], [])
        payload = {'action': 'closed', 'repository': {'full_name': 'team/project'}, 'pull_request': {'number': 7, 'merged': True}}
        with patch.object(app, 'gh_env', return_value={}), patch.object(app, 'gh_json', side_effect=[{'login': 'coder'}, self.detail]), patch.object(app, 'notify') as notify:
            self.assertTrue(receiver.handle_event('pull_request', payload, self.now))
            notify.assert_not_called()
        preferences.set_preferences([], ['team'])
        with patch.object(app, 'gh_env', return_value={}), patch.object(app, 'gh_json', return_value={'login': 'coder'}), patch.object(app, 'notify') as notify:
            self.assertFalse(receiver.handle_event('pull_request', payload, self.now))
            notify.assert_not_called()

    def test_manual_preview_ignores_repository_selection(self):
        preferences.set_preferences([], [])
        with patch.object(app.subprocess, 'Popen') as audio:
            self.assertTrue(app.play(tag_id='stackaholics'))
            audio.assert_called_once()
