import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import push_tags as app
import repo_preferences as preferences


class RepoPreferencesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(os.environ, {'PUSH_TAGS_STATE_DIR': self.directory.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_legacy_and_all_allow_all_repositories(self):
        self.assertEqual(preferences.get(), {'repositories': None, 'organizations': []})
        self.assertTrue(preferences.allowed('anywhere/project'))
        self.assertTrue(preferences.allowed(None))
        preferences.set_preferences(['one/project'], ['some-org'])
        preferences.set_preferences([], [], all_repos=True)
        self.assertEqual(preferences.get(), {'repositories': None, 'organizations': []})
        self.assertTrue(preferences.allowed('elsewhere/project'))

    def test_empty_selection_allows_none(self):
        preferences.set_preferences([], [])
        self.assertFalse(preferences.allowed('lola-labs/lola-agent'))
        self.assertFalse(preferences.allowed(None))

    def test_repository_and_org_selections_form_case_insensitive_union(self):
        preferences.set_preferences(['Person/Project'], ['Lola-Labs'])
        self.assertTrue(preferences.allowed('person/PROJECT'))
        self.assertTrue(preferences.allowed('lola-labs/new-repository'))
        self.assertFalse(preferences.allowed('person/other-project'))
        self.assertFalse(preferences.allowed('lola-labs-other/project'))
        self.assertFalse(preferences.allowed(None))
        self.assertFalse(preferences.allowed('lola-labs/../project'))

    def test_save_preserves_sound_and_auth_settings(self):
        settings = {'muted': True, 'merge_tag': 'branch-outta-here',
                    'auth': {'keychain_service': 'private-item'}}
        app.write_json(app.state_dir() / 'config.json', settings)
        preferences.set_preferences(['owner/repo'], ['organization'])
        saved = app.config()
        for name, value in settings.items():
            self.assertEqual(saved[name], value)
        self.assertEqual(saved['repositories'], ['owner/repo'])
        self.assertEqual(saved['organizations'], ['organization'])

    def test_invalid_selections_do_not_replace_settings(self):
        preferences.set_preferences(['owner/repo'], [])
        original = app.config()
        for repos, orgs in [(['owner/repo/extra'], []), (['../repo'], []),
                           ([], ['owner/repo']), ([], ['..'])]:
            with self.subTest(repos=repos, orgs=orgs):
                with self.assertRaises(ValueError):
                    preferences.set_preferences(repos, orgs)
                self.assertEqual(app.config(), original)

    def test_github_remote_formats(self):
        for remote in ('git@github.com:Owner/Repo.git',
                       'https://github.com/Owner/Repo.git',
                       'ssh://git@github.com/Owner/Repo.git',
                       'https://github.com/Owner/Repo/'):
            with self.subTest(remote=remote):
                self.assertEqual(preferences.repository_name(remote), 'Owner/Repo')

    def test_rejects_other_hosts_and_invalid_repository_paths(self):
        for remote in ('git@gitlab.com:owner/repo.git',
                       'https://github.com.evil/owner/repo',
                       'https://github.com/owner/repo/extra',
                       'https://github.com/../repo',
                       'https://github.com/owner/repo?token=private',
                       '/local/path', None):
            with self.subTest(remote=remote):
                self.assertIsNone(preferences.repository_name(remote))

    def test_git_global_options_keep_the_requested_checkout(self):
        result = subprocess.CompletedProcess([], 0, 'git@github.com:owner/repo.git\n', '')
        with patch.object(preferences.subprocess, 'run', return_value=result) as run:
            name = preferences.git_repository(['-C', 'other checkout', '-c', 'color.ui=false',
                                               '--no-pager', 'push', 'origin', 'HEAD'])
        self.assertEqual(name, 'owner/repo')
        self.assertEqual(run.call_args.args[0], ['git', '-C', 'other checkout', '-c',
                                               'color.ui=false', '--no-pager',
                                               'config', '--get', 'remote.origin.url'])

    def test_git_attached_options_and_current_checkout(self):
        result = subprocess.CompletedProcess([], 0, 'https://github.com/owner/repo.git\n', '')
        with patch.object(preferences.subprocess, 'run', return_value=result) as run:
            self.assertEqual(preferences.git_repository(['-C/tmp/checkout', 'push']), 'owner/repo')
            self.assertEqual(run.call_args.args[0][:2], ['git', '-C/tmp/checkout'])
            self.assertEqual(preferences.git_repository(['origin', 'HEAD']), 'owner/repo')
            self.assertEqual(run.call_args.args[0], ['git', 'config', '--get', 'remote.origin.url'])

    def test_missing_git_context_does_not_guess_repository(self):
        with patch.object(preferences.subprocess, 'run') as run:
            self.assertIsNone(preferences.git_repository(['-C']))
            run.assert_not_called()
        with patch.object(preferences.subprocess, 'run',
                          return_value=subprocess.CompletedProcess([], 1, '', '')):
            self.assertIsNone(preferences.git_repository())
        with patch.object(preferences.subprocess, 'run', side_effect=OSError('missing git')):
            self.assertIsNone(preferences.git_repository())

    def test_accessible_repository_pagination_and_organizations(self):
        first = [{'full_name': f'org/repo-{i}', 'private': True,
                  'owner': {'type': 'Organization'}} for i in range(100)]
        second = [{'full_name': 'person/project', 'private': False,
                   'owner': {'type': 'User'}}]
        with patch.object(app, 'gh_env', return_value={}), \
                patch.object(app, 'gh_json', side_effect=[first, second]) as api:
            values = preferences.repositories()
        self.assertEqual(len(values), 101)
        self.assertTrue(values[0]['organization'])
        self.assertEqual(values[-1], {'full_name': 'person/project', 'private': False,
                                     'organization': False})
        self.assertIn('affiliation=owner,collaborator,organization_member', api.call_args_list[0].args[0][1])
        self.assertIn('page=2', api.call_args_list[1].args[0][1])

    def test_cli_lists_organizations_and_saves_explicit_none(self):
        values = [{'full_name': 'org/one', 'organization': True},
                  {'full_name': 'org/two', 'organization': True},
                  {'full_name': 'person/repo', 'organization': False}]
        output = io.StringIO()
        with patch.object(sys, 'argv', ['repo_preferences.py', 'organizations']), \
                patch.object(preferences, 'repositories', return_value=values), \
                contextlib.redirect_stdout(output):
            preferences.main()
        self.assertEqual(json.loads(output.getvalue()), ['org'])
        with patch.object(sys, 'argv', ['repo_preferences.py', 'set']), \
                contextlib.redirect_stdout(io.StringIO()):
            preferences.main()
        self.assertEqual(preferences.get(), {'repositories': [], 'organizations': []})
