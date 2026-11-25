import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import push_tags as app
import repo_preferences as preferences


class ConnectionStatusTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {'PUSH_TAGS_STATE_DIR': directory.name})
        environment.start()
        self.addCleanup(environment.stop)
        self.catalogue = [
            {'full_name': 'team/one', 'private': True, 'organization': True},
            {'full_name': 'team/two', 'private': True, 'organization': True},
            {'full_name': 'person/project', 'private': True, 'organization': False},
        ]

    def report(self, target='--org=team', events=None, connected=True):
        listener = {'target': target, 'events': events if events is not None else ['pull_request', 'workflow_run'],
                    'connected': connected, 'reason': 'Listener verified.'}
        with patch.object(preferences, 'repositories', return_value=self.catalogue), \
                patch.object(preferences, 'listener_status', return_value=listener):
            report = preferences.connections()
        return {row['full_name']: row for row in report['repositories']}

    def test_org_connection_covers_only_its_repositories(self):
        result = self.report()
        self.assertEqual(result['team/one']['connection'], 'live')
        self.assertTrue(result['team/two']['ci_live'])
        self.assertEqual(result['person/project']['connection'], 'polling')
        self.assertEqual(result['person/project']['access'], 'confirmed')

    def test_repo_connection_uses_exact_case_insensitive_name(self):
        result = self.report(target='--repo=TEAM/ONE')
        self.assertEqual(result['team/one']['connection'], 'live')
        self.assertEqual(result['team/two']['connection'], 'polling')

    def test_partial_event_subscription_is_explicit(self):
        result = self.report(events=['pull_request'])
        self.assertEqual(result['team/one']['connection'], 'partial')
        self.assertTrue(result['team/one']['merge_live'])
        self.assertFalse(result['team/one']['ci_live'])
        self.assertIn('other events use polling', result['team/one']['reason'])

    def test_inactive_listener_uses_polling(self):
        result = self.report(connected=False)
        self.assertTrue(all(row['connection'] == 'polling' for row in result.values()))
        self.assertTrue(all('when setup is enabled' in row['reason'] for row in result.values()))

    def test_saved_inaccessible_repository_is_not_live(self):
        preferences.set_preferences(['team/missing'], [])
        result = self.report()
        self.assertEqual(result['team/missing']['access'], 'unconfirmed')
        self.assertEqual(result['team/missing']['connection'], 'unconfirmed')
        self.assertFalse(result['team/missing']['merge_live'])

    def test_catalogue_failure_does_not_return_cached_confirmation(self):
        with patch.object(preferences, 'repositories', side_effect=RuntimeError('denied')), \
                patch.object(preferences, 'listener_status', return_value={}):
            with self.assertRaisesRegex(RuntimeError, 'denied'):
                preferences.connections()

    def prepare_hook(self):
        app.write_json(app.state_dir() / 'webhook-pilot.json', {'target': '--org=team', 'id': 12})
        (app.state_dir() / 'listener.lock').touch()

    def test_saved_hook_requires_a_running_local_listener(self):
        self.prepare_hook()
        with patch.object(preferences.urllib.request, 'urlopen') as request:
            status = preferences.listener_status()
        self.assertFalse(status['connected'])
        request.assert_not_called()

    def test_saved_hook_requires_receiver_health(self):
        self.prepare_hook()
        with patch.object(preferences.fcntl, 'flock', side_effect=BlockingIOError), \
                patch.object(preferences.urllib.request, 'urlopen', side_effect=OSError('offline')), \
                patch.object(app, 'gh_json') as api:
            status = preferences.listener_status()
        self.assertFalse(status['connected'])
        api.assert_not_called()

    def verified_hook(self, result=None, error=None):
        self.prepare_hook()
        response = MagicMock()
        response.__enter__.return_value.status = 200
        hook = result if result is not None else {'name': 'cli', 'active': True, 'events': ['pull_request', 'workflow_run']}
        with patch.object(preferences.fcntl, 'flock', side_effect=BlockingIOError), \
                patch.object(preferences.urllib.request, 'urlopen', return_value=response), \
                patch.object(app, 'gh_env', return_value={}), \
                patch.object(app, 'gh_json', side_effect=error, return_value=hook) as api:
            status = preferences.listener_status()
        self.assertEqual(api.call_args.args[0], ['api', 'orgs/team/hooks/12'])
        return status

    def test_active_owned_hook_is_verified(self):
        status = self.verified_hook()
        self.assertTrue(status['connected'])
        self.assertEqual(status['target'], '--org=team')

    def test_missing_inactive_and_unrelated_hooks_are_not_live(self):
        for hook in ({'active': False, 'name': 'cli'}, {'active': True, 'name': 'web'}):
            with self.subTest(hook=hook):
                self.assertFalse(self.verified_hook(result=hook)['connected'])
        self.assertFalse(self.verified_hook(error=RuntimeError('404'))['connected'])

    def test_permission_denial_retains_polling(self):
        status = self.verified_hook(error=RuntimeError('403'))
        self.assertFalse(status['connected'])
        self.assertIn('Polling', status['reason'])

    def test_verified_save_accepts_accessible_repo_and_org(self):
        with patch.object(preferences, 'repositories', return_value=self.catalogue):
            result = preferences.set_preferences(['TEAM/ONE'], ['team'], verify=True)
        self.assertEqual(result, {'repositories': ['TEAM/ONE'], 'organizations': ['team']})

    def test_failed_access_verification_keeps_previous_selection(self):
        preferences.set_preferences(['person/project'], [])
        original = app.config()
        for repos, orgs in [(['team/missing'], []), ([], ['missing-team'])]:
            with self.subTest(repos=repos, orgs=orgs), \
                    patch.object(preferences, 'repositories', return_value=self.catalogue):
                with self.assertRaises(ValueError):
                    preferences.set_preferences(repos, orgs, verify=True)
                self.assertEqual(app.config(), original)

    def test_cli_verifies_access_before_saving(self):
        with patch.object(sys, 'argv', ['repo_preferences.py', 'set', '--verify-access', '--repo', 'team/one']), \
                patch.object(preferences, 'repositories', return_value=self.catalogue), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            preferences.main()
        self.assertEqual(json.loads(output.getvalue())['repositories'], ['team/one'])


if __name__ == '__main__':
    unittest.main()
