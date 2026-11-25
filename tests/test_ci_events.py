import copy
import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import push_tags as app
import ci_events as ci
import webhook_receiver as receiver


class CIFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.environment = patch.dict(os.environ, {'PUSH_TAGS_STATE_DIR': self.temp.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.scope = SimpleNamespace(allowed=Mock(return_value=True), listener_status=Mock(return_value={}))
        self.preferences = patch.dict(sys.modules, {'repo_preferences': self.scope})
        self.preferences.start()
        self.addCleanup(self.preferences.stop)
        self.now = dt.datetime(2026, 11, 25, 20, tzinfo=app.UTC)
        self.start = self.now - dt.timedelta(hours=1)
        self.sha = 'a' * 40
        self.run = {'id': 42, 'run_attempt': 1, 'status': 'completed', 'conclusion': 'failure',
                    'updated_at': app.stamp(self.now - dt.timedelta(minutes=1)), 'head_sha': self.sha}
        self.pr = {'number': 7, 'state': 'open', 'user': {'login': 'Max'}, 'head': {'sha': self.sha}}
        self.item = {'repository_url': 'https://api.github.com/repos/owner/repo', 'number': 7}
        self.payload = {'action': 'completed', 'repository': {'full_name': 'owner/repo'},
                        'workflow_run': {'id': 42, 'run_attempt': 1, 'url': 'https://untrusted.invalid'}}
        self.state = {'login': 'max', 'started_at': app.stamp(self.start), 'seen': []}
        app.write_json(app.state_dir() / 'ci.json', self.state)
        self.auth = patch.object(app, 'gh_env', return_value={})
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.api = patch.object(app, 'gh_json', side_effect=self.api_response)
        self.api_mock = self.api.start()
        self.addCleanup(self.api.stop)
        self.playback = patch.object(app, 'notify')
        self.sound = self.playback.start()
        self.addCleanup(self.playback.stop)

    def api_response(self, args, env):
        if args == ['api', 'user']:
            return {'login': 'max'}
        if 'search/issues' in args:
            return {'items': [self.item], 'total_count': 1}
        route = args[1]
        if '/actions/runs?' in route:
            return {'workflow_runs': [copy.deepcopy(self.run)]}
        if '/actions/runs/42/attempts/' in route:
            return copy.deepcopy(self.run)
        if '/commits/' in route:
            return [copy.deepcopy(self.pr)]
        if route == 'repos/owner/repo/pulls/7':
            return copy.deepcopy(self.pr)
        raise AssertionError(args)

    def saved(self):
        return app.read_json(app.state_dir() / 'ci.json', {})

    def test_first_poll_creates_baseline_without_history(self):
        (app.state_dir() / 'ci.json').unlink()
        ci.poll(self.now)
        self.assertEqual(self.saved()['started_at'], app.stamp(self.now))
        self.assertEqual(self.saved()['seen'], [])
        self.sound.assert_not_called()
        self.api_mock.assert_called_once_with(['api', 'user'], {})

    def test_webhook_confirms_exact_run_and_current_person(self):
        self.assertTrue(receiver.handle_event('workflow_run', self.payload, self.now))
        self.sound.assert_called_once_with('ci')
        identity = 'https://api.github.com/repos/owner/repo/actions/runs/42/attempts/1'
        self.assertEqual(self.saved()['seen'], [[identity, self.run['updated_at']]])
        self.assertIn(unittest.mock.call(['api', 'repos/owner/repo/actions/runs/42/attempts/1'], {}), self.api_mock.call_args_list)
        self.assertFalse(any('untrusted' in str(call) for call in self.api_mock.call_args_list))

    def test_other_persons_pr_does_not_play(self):
        self.pr['user']['login'] = 'someone'
        self.assertFalse(ci.handle_event(self.payload, self.now))
        self.sound.assert_not_called()
        self.assertEqual(self.saved()['seen'], [])

    def test_actual_actor_or_triggering_actor_is_eligible(self):
        self.pr['user']['login'] = 'someone'
        for field in ('actor', 'triggering_actor'):
            with self.subTest(field=field):
                app.write_json(app.state_dir() / 'ci.json', self.state)
                self.run[field] = {'login': 'MAX'}
                self.assertTrue(ci.handle_event(self.payload, self.now))
                self.run.pop(field)
        self.assertEqual(self.sound.call_count, 2)

    def test_exact_merge_commit_covers_bot_run_after_my_merge(self):
        self.pr.update(merged=True, merge_commit_sha=self.sha, merged_by={'login': 'max'})
        self.pr['user']['login'] = 'someone'
        self.pr['head']['sha'] = 'b' * 40
        self.run.update(event='workflow_run', actor={'login': 'release[bot]'})
        self.assertTrue(ci.handle_event(self.payload, self.now))
        self.sound.assert_called_once_with('ci')

    def test_common_branch_history_does_not_establish_attribution(self):
        self.pr.update(merged=True, merge_commit_sha='c' * 40)
        self.pr['head']['sha'] = 'b' * 40
        self.run['actor'] = {'login': 'someone'}
        self.assertFalse(ci.handle_event(self.payload, self.now))
        self.sound.assert_not_called()

    def bot_chain(self, link='https://github.com/owner/repo/issues/9'):
        self.pr['user'] = {'login': 'release[bot]', 'type': 'Bot'}
        self.pr['body'] = f'Release changes: {link}'
        source = {'number': 9, 'merged': True, 'user': {'login': 'max'},
                  'merged_by': {'login': 'release[bot]'}}
        base = self.api_mock.side_effect
        def api(args, env):
            if args == ['api', 'repos/owner/repo/pulls/9']:
                return copy.deepcopy(source)
            return base(args, env)
        self.api_mock.side_effect = api
        return source

    def test_bot_release_pr_explicit_issue_link_to_owned_merge(self):
        self.bot_chain()
        self.assertTrue(ci.handle_event(self.payload, self.now))
        self.sound.assert_called_once_with('ci')

    def test_bot_release_pr_pull_link_is_also_supported(self):
        self.bot_chain('https://github.com/owner/repo/pull/9')
        self.assertTrue(ci.handle_event(self.payload, self.now))

    def test_bot_link_must_reference_a_merged_owned_source(self):
        source = self.bot_chain()
        for change in ({'merged': False}, {'user': {'login': 'someone'}}):
            with self.subTest(change=change):
                app.write_json(app.state_dir() / 'ci.json', self.state)
                original = copy.deepcopy(source)
                source.update(change)
                self.assertFalse(ci.handle_event(self.payload, self.now))
                source.clear()
                source.update(original)
        self.sound.assert_not_called()

    def test_human_pr_reference_and_other_repo_reference_do_not_attribute(self):
        self.bot_chain('https://github.com/another/repo/issues/9')
        self.assertFalse(ci.handle_event(self.payload, self.now))
        app.write_json(app.state_dir() / 'ci.json', self.state)
        self.pr['body'] = 'Source: https://github.com/owner/repo/issues/9'
        self.pr['user']['type'] = 'User'
        self.assertFalse(ci.handle_event(self.payload, self.now))
        self.sound.assert_not_called()

    def test_deleted_bot_branch_uses_exact_head_match_from_pr_list(self):
        self.bot_chain()
        self.run.update(head_branch='release-please--branches--main')
        base = self.api_mock.side_effect
        def api(args, env):
            if '/commits/' in args[1]:
                return []
            if args[1].startswith('repos/owner/repo/pulls?'):
                return [copy.deepcopy(self.pr)]
            return base(args, env)
        self.api_mock.side_effect = api
        self.assertTrue(ci.handle_event(self.payload, self.now))
        self.sound.assert_called_once_with('ci')

    def test_branch_name_without_exact_sha_match_is_not_enough(self):
        self.bot_chain()
        self.run['head_branch'] = 'release-please--branches--main'
        self.pr['head']['sha'] = 'b' * 40
        base = self.api_mock.side_effect
        def api(args, env):
            if args[1].startswith('repos/owner/repo/pulls?'):
                return [copy.deepcopy(self.pr)]
            return base(args, env)
        self.api_mock.side_effect = api
        self.assertFalse(ci.handle_event(self.payload, self.now))
        self.sound.assert_not_called()

    def test_remote_head_must_match_the_owned_pr(self):
        self.pr['head']['sha'] = 'b' * 40
        self.assertFalse(ci.handle_event(self.payload, self.now))
        self.sound.assert_not_called()

    def test_cancelled_successful_and_running_workflows_are_ignored(self):
        for status, conclusion in [('completed', 'cancelled'), ('completed', 'success'), ('in_progress', None)]:
            self.run.update(status=status, conclusion=conclusion)
            self.assertFalse(ci.handle_event(self.payload, self.now))
        self.sound.assert_not_called()

    def test_timeout_is_a_failure(self):
        self.run['conclusion'] = 'timed_out'
        self.assertTrue(ci.handle_event(self.payload, self.now))
        self.sound.assert_called_once_with('ci')

    def test_irrelevant_event_does_not_call_github(self):
        self.payload['action'] = 'requested'
        self.assertFalse(ci.handle_event(self.payload, self.now))
        self.api_mock.assert_not_called()

    def test_old_and_future_runs_do_not_play(self):
        for finished in (self.start, self.start - dt.timedelta(seconds=1), self.now + dt.timedelta(seconds=1)):
            self.run['updated_at'] = app.stamp(finished)
            self.assertFalse(ci.handle_event(self.payload, self.now))
        self.sound.assert_not_called()

    def test_same_attempt_plays_once_and_new_failed_attempt_can_play(self):
        self.assertTrue(ci.handle_event(self.payload, self.now))
        self.assertFalse(ci.handle_event(self.payload, self.now))
        self.run['run_attempt'] = 2
        self.payload['workflow_run']['run_attempt'] = 2
        self.assertTrue(ci.handle_event(self.payload, self.now))
        self.assertEqual(self.sound.call_count, 2)

    def test_poll_and_webhook_share_identity(self):
        ci.poll(self.now)
        self.assertFalse(ci.handle_event(self.payload, self.now))
        ci.poll(self.now)
        self.sound.assert_called_once_with('ci')
        self.assertEqual(len(self.saved()['seen']), 1)

    def test_webhook_first_prevents_poll_replay(self):
        self.assertTrue(ci.handle_event(self.payload, self.now))
        ci.poll(self.now)
        self.sound.assert_called_once_with('ci')

    def test_poll_confirms_open_pr_author(self):
        self.pr['user']['login'] = 'someone'
        ci.poll(self.now)
        self.sound.assert_not_called()
        self.assertFalse(any('/actions/runs' in str(call) for call in self.api_mock.call_args_list))

    def test_closed_pr_is_not_a_poll_candidate(self):
        self.pr['state'] = 'closed'
        ci.poll(self.now)
        self.sound.assert_not_called()

    def test_poll_discovers_post_merge_runs_from_saved_own_merge_repositories(self):
        app.write_json(app.state_dir() / 'merges.json', {
            'seen': [['https://api.github.com/repos/owner/repo/pulls/7', app.stamp(self.start)]]})
        self.run['actor'] = {'login': 'max'}
        base = self.api_mock.side_effect
        self.api_mock.side_effect = lambda args, env: {'items': [], 'total_count': 0} if 'search/issues' in args else base(args, env)
        ci.poll(self.now)
        self.sound.assert_called_once_with('ci')
        self.assertEqual(self.saved()['checkpoint'], app.stamp(self.now))

    def test_poll_discovers_runs_from_explicit_repository_selection(self):
        app.write_json(app.state_dir() / 'config.json', {'repositories': ['owner/repo']})
        self.run['actor'] = {'login': 'max'}
        base = self.api_mock.side_effect
        self.api_mock.side_effect = lambda args, env: {'items': [], 'total_count': 0} if 'search/issues' in args else base(args, env)
        ci.poll(self.now)
        self.sound.assert_called_once_with('ci')

    def test_unrelated_attempt_is_cached_in_both_poll_and_webhook(self):
        app.write_json(app.state_dir() / 'config.json', {'repositories': ['owner/repo']})
        self.pr['user']['login'] = 'someone'
        ci.poll(self.now)
        ci.poll(self.now)
        self.assertFalse(ci.handle_event(self.payload, self.now))
        detail_calls = [call for call in self.api_mock.call_args_list if call.args[0] == ['api', 'repos/owner/repo/actions/runs/42/attempts/1']]
        self.assertEqual(len(detail_calls), 2)
        self.assertEqual(len(self.saved()['ignored']), 1)
        self.sound.assert_not_called()

    def test_muted_failure_is_recorded_without_replay(self):
        self.playback.stop()
        app.write_json(app.state_dir() / 'settings.json', {'muted': True})
        with patch.object(app.subprocess, 'Popen') as audio:
            self.assertTrue(ci.handle_event(self.payload, self.now))
            app.write_json(app.state_dir() / 'settings.json', {'muted': False})
            self.assertFalse(ci.handle_event(self.payload, self.now))
            audio.assert_not_called()

    def test_disabled_ci_does_not_call_github(self):
        app.write_json(app.state_dir() / 'config.json', {'ci_enabled': False})
        ci.poll(self.now)
        self.assertFalse(ci.handle_event(self.payload, self.now))
        self.api_mock.assert_not_called()

    def test_unselected_repo_is_recorded_without_later_replay(self):
        self.scope.allowed.return_value = False
        self.assertTrue(ci.handle_event(self.payload, self.now))
        self.sound.assert_not_called()
        self.scope.allowed.assert_called_once_with('owner/repo')
        self.scope.allowed.return_value = True
        self.assertFalse(ci.handle_event(self.payload, self.now))
        self.sound.assert_not_called()

    def test_account_change_preserves_state(self):
        self.state['login'] = 'other'
        app.write_json(app.state_dir() / 'ci.json', self.state)
        with self.assertRaises(RuntimeError):
            ci.poll(self.now)
        self.assertEqual(self.saved(), self.state)

    def test_incomplete_search_preserves_baseline(self):
        original = self.api_mock.side_effect
        self.api_mock.side_effect = lambda args, env: {'incomplete_results': True, 'items': []} if 'search/issues' in args else original(args, env)
        with self.assertRaises(RuntimeError):
            ci.poll(self.now)
        self.assertEqual(self.saved(), self.state)

    def test_invalid_identifiers_do_not_call_github(self):
        for repo, identity in [('https://bad.test/x', 42), ('owner/repo', True), ('owner/repo', -1)]:
            payload = copy.deepcopy(self.payload)
            payload['repository']['full_name'] = repo
            payload['workflow_run']['id'] = identity
            with self.assertRaises(ValueError):
                ci.handle_event(payload, self.now)
        self.api_mock.assert_not_called()

    def test_cli_configures_ci_and_uses_default_failure_clip(self):
        with patch.object(sys, 'argv', ['push-tags', 'configure', '--ci', 'off']):
            app.main()
        self.assertFalse(app.config()['ci_enabled'])
        with patch.object(sys, 'argv', ['push-tags', 'configure', '--ci', 'on', '--ci-tag', 'lego-break-apart']), patch.object(app, 'tags', return_value=[{'id': 'lego-break-apart'}]):
            app.main()
        self.assertEqual(app.config()['ci_tag'], 'lego-break-apart')
        app.write_json(app.state_dir() / 'config.json', {})
        with patch.object(app, 'tags', return_value=[{'id': 'lego-break-apart', 'file': 'push_tags.py', 'event': 'ci'}]), patch.object(app.subprocess, 'Popen') as audio:
            self.assertTrue(app.play('ci'))
            self.assertTrue(audio.call_args.args[0][-1].endswith('push_tags.py'))

    def test_ci_poll_runs_if_merge_poll_fails_or_is_disabled(self):
        with patch.object(app, 'poll', side_effect=RuntimeError('merge check failed')), patch.object(ci, 'poll') as check, patch('sound_library.sync'), patch('comment_events.poll'):
            with self.assertRaises(RuntimeError):
                app.poll_all()
            check.assert_called_once_with()
        app.write_json(app.state_dir() / 'config.json', {'merge_enabled': False})
        with patch.object(ci, 'poll') as check, patch('sound_library.sync'), patch('comment_events.poll'):
            app.poll_all()
            check.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
