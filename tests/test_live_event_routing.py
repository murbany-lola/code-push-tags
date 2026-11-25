import datetime as dt
import fcntl
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ci_events as ci
import push_tags as app
import repo_preferences as preferences
import webhook_receiver as receiver


class LiveEventRoutingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        environment = patch.dict(os.environ, {'PUSH_TAGS_STATE_DIR': temporary.name})
        environment.start()
        self.addCleanup(environment.stop)
        self.now = dt.datetime(2026, 11, 25, 20, tzinfo=app.UTC)
        self.start = self.now - dt.timedelta(hours=1)
        self.live = {'connected': True, 'target': '--org=team',
                     'events': ['pull_request', 'workflow_run']}
        self.target = ('org', 'team')
        self.live_url = 'https://api.github.com/repos/team/live/pulls/1'
        self.other_url = 'https://api.github.com/repos/person/own/pulls/2'
        app.write_json(app.state_dir() / 'merges.json', {
            'login': 'max', 'started_at': app.stamp(self.start),
            'checkpoint': app.stamp(self.start), 'seen': []})
        app.write_json(app.state_dir() / 'ci.json', {
            'login': 'max', 'started_at': app.stamp(self.start), 'seen': []})
        auth = patch.object(app, 'gh_env', return_value={})
        auth.start()
        self.addCleanup(auth.stop)

    def detail(self):
        return {'merged': True, 'merged_at': app.stamp(self.now - dt.timedelta(minutes=1)),
                'user': {'login': 'max'}, 'merged_by': {'login': 'max'}}

    def merge_api(self, args, env):
        if args == ['api', 'user']:
            return {'login': 'max'}
        if 'search/issues' in args:
            return {'items': [{'pull_request': {'url': url}} for url in (self.live_url, self.other_url)],
                    'total_count': 2}
        if args[1] in (self.live_url, self.other_url, 'repos/team/live/pulls/1'):
            return self.detail()
        raise AssertionError(args)

    def test_event_coverage_is_independent_and_case_insensitive(self):
        target = app.live_target(dict(self.live, target='--org=TEAM', events=['pull_request']), 'pull_request')
        self.assertEqual(target, self.target)
        self.assertTrue(app.live_covers('TEAM/Live', target))
        self.assertFalse(app.live_covers('person/own', target))
        self.assertIsNone(app.live_target(dict(self.live, events=['pull_request']), 'workflow_run'))
        self.assertIsNone(app.live_target(dict(self.live, connected=False), 'pull_request'))
        self.assertEqual(app.live_target(dict(self.live, events=['*']), 'workflow_run'), self.target)

    def test_exact_repository_does_not_cover_other_org_repositories(self):
        target = app.live_target(dict(self.live, target='--repo=TEAM/LIVE'), 'pull_request')
        self.assertEqual(target, ('repo', 'team/live'))
        self.assertTrue(app.live_covers('team/live', target))
        self.assertFalse(app.live_covers('team/other', target))
        with patch.object(app, 'gh_json', return_value={'items': [], 'total_count': 0}) as api, \
                patch.object(app, 'gh_events', return_value=([], 60)):
            app.search_merges('max', self.start, {}, now=self.now, live=target)
        self.assertTrue(all('-repo:team/live' in call.args[0][5] for call in api.call_args_list))

    def test_merge_queries_exclude_live_org_and_account_feed_filters_covered_results(self):
        events = [{'type': 'PullRequestEvent', 'payload': {'action': 'closed',
                   'pull_request': {'id': number, 'url': url}}}
                  for number, url in enumerate((self.live_url, self.other_url), 1)]
        with patch.object(app, 'gh_json', side_effect=self.merge_api) as api, \
                patch.object(app, 'gh_events', return_value=(events, 60)):
            found = app.search_merges('max', self.start, {}, now=self.now, live=self.target)
        self.assertEqual(set(found), {self.other_url})
        self.assertTrue(all('-org:team' in call.args[0][5] for call in api.call_args_list))

    def test_merge_poll_does_not_read_covered_pr_and_fallback_backfills_it(self):
        with patch.object(app, 'gh_json', side_effect=self.merge_api) as api, \
                patch.object(app, 'gh_events', return_value=([], 60)), patch.object(app, 'notify') as sound:
            app.poll(self.now, live=self.target)
            self.assertFalse(any(call.args[0] == ['api', self.live_url] for call in api.call_args_list))
            sound.assert_called_once_with('merge')
            app.poll(self.now + dt.timedelta(minutes=1))
        self.assertEqual(sound.call_count, 2)
        state = app.read_json(app.state_dir() / 'merges.json', {})
        self.assertEqual(set(dict(state['seen'])), {self.live_url, self.other_url})

    def test_webhook_still_confirms_and_plays_covered_merge(self):
        payload = {'action': 'closed', 'repository': {'full_name': 'team/live'},
                   'pull_request': {'number': 1, 'merged': True}}
        with patch.object(app, 'gh_json', side_effect=self.merge_api), \
                patch.object(preferences, 'listener_status', return_value=self.live) as status, \
                patch.object(app, 'notify') as sound:
            self.assertTrue(receiver.handle_event('pull_request', payload, self.now))
        sound.assert_called_once_with('merge')
        status.assert_not_called()

    def test_webhook_still_confirms_and_plays_covered_ci_failure(self):
        payload = {'action': 'completed', 'repository': {'full_name': 'team/live'},
                   'workflow_run': {'id': 9, 'run_attempt': 1}}
        run = {'id': 9, 'run_attempt': 1, 'status': 'completed', 'conclusion': 'failure',
               'updated_at': app.stamp(self.now - dt.timedelta(minutes=1)), 'actor': {'login': 'max'}}
        def github(args, env):
            return {'login': 'max'} if args == ['api', 'user'] else run
        with patch.object(app, 'gh_json', side_effect=github), \
                patch.object(preferences, 'listener_status', return_value=self.live) as status, \
                patch.object(app, 'notify') as sound:
            self.assertTrue(receiver.handle_event('workflow_run', payload, self.now))
        sound.assert_called_once_with('ci')
        status.assert_not_called()

    def test_poll_all_verifies_listener_once_and_passes_event_specific_coverage(self):
        for events, expected_merge, expected_ci in [
                (['pull_request', 'workflow_run'], True, True),
                (['pull_request'], True, False), (['workflow_run'], False, True)]:
            with self.subTest(events=events), \
                    patch.object(preferences, 'listener_status', return_value=dict(self.live, events=events)) as status, \
                    patch.object(app, 'poll') as merge, patch.object(ci, 'poll') as checks, \
                    patch('sound_library.sync'):
                app.poll_all()
                status.assert_called_once_with()
                merge.assert_called_once_with(**({'live': self.target} if expected_merge else {}))
                checks.assert_called_once_with(**({'live': self.target} if expected_ci else {}))

    def test_disconnected_listener_uses_existing_polling_calls(self):
        with patch.object(preferences, 'listener_status', return_value=dict(self.live, connected=False)), \
                patch.object(app, 'poll') as merge, patch.object(ci, 'poll') as checks, \
                patch('sound_library.sync'):
            app.poll_all()
        merge.assert_called_once_with()
        checks.assert_called_once_with()

    def recovery_marker(self, identity='gap-one', target='--org=team'):
        marker = {'id': identity, 'target': target}
        app.write_json(app.state_dir() / 'webhook-recovery.json', marker)
        return marker

    def test_recovered_connection_backfills_covered_merge_once_then_resumes_live(self):
        self.recovery_marker()
        merge_poll = app.poll
        with patch.object(preferences, 'listener_status', return_value=self.live), \
                patch.object(app, 'poll', side_effect=lambda **kwargs: merge_poll(self.now, **kwargs)) as merge, \
                patch.object(ci, 'poll') as checks, patch('sound_library.sync'), \
                patch.object(app, 'gh_json', side_effect=self.merge_api) as api, \
                patch.object(app, 'gh_events', return_value=([], 60)), patch.object(app, 'notify') as sound:
            app.poll_all()
            self.assertFalse((app.state_dir() / 'webhook-recovery.json').exists())
            self.assertTrue(any(request.args[0] == ['api', self.live_url] for request in api.call_args_list))
            app.poll_all()
        self.assertEqual(merge.call_args_list, [call(), call(live=self.target)])
        self.assertEqual(checks.call_args_list, [call(), call(live=self.target)])
        queries = [request.args[0][5] for request in api.call_args_list if 'search/issues' in request.args[0]]
        self.assertTrue(all('-org:team' not in query for query in queries[:2]))
        self.assertTrue(all('-org:team' in query for query in queries[2:]))
        self.assertEqual(sound.call_count, 2)

    def test_recovery_catchup_preserves_a_new_disconnect_marker(self):
        self.recovery_marker()
        with patch.object(preferences, 'listener_status', return_value=self.live), \
                patch.object(app, 'poll', side_effect=lambda: self.recovery_marker('gap-two')), \
                patch.object(ci, 'poll'), patch('sound_library.sync'):
            app.poll_all()
        self.assertEqual(app.read_json(app.state_dir() / 'webhook-recovery.json', {})['id'], 'gap-two')

    def test_failed_recovery_catchup_preserves_marker(self):
        for failing in ('merge', 'ci'):
            with self.subTest(failing=failing):
                marker = self.recovery_marker()
                with patch.object(preferences, 'listener_status', return_value=self.live), \
                        patch.object(app, 'poll', side_effect=RuntimeError('failed') if failing == 'merge' else None), \
                        patch.object(ci, 'poll', side_effect=RuntimeError('failed') if failing == 'ci' else None), \
                        patch('sound_library.sync'):
                    with self.assertRaises(RuntimeError):
                        app.poll_all()
                self.assertEqual(app.read_json(app.state_dir() / 'webhook-recovery.json', {}), marker)

    def test_disconnected_recovery_polls_until_healthy_then_clears(self):
        self.recovery_marker()
        statuses = [dict(self.live, connected=False), self.live, self.live]
        with patch.object(preferences, 'listener_status', side_effect=statuses), \
                patch.object(app, 'poll') as merge, patch.object(ci, 'poll') as checks, patch('sound_library.sync'):
            app.poll_all()
            self.assertTrue((app.state_dir() / 'webhook-recovery.json').exists())
            app.poll_all()
            self.assertFalse((app.state_dir() / 'webhook-recovery.json').exists())
            app.poll_all()
        self.assertEqual(merge.call_args_list, [call(), call(), call(live=self.target)])
        self.assertEqual(checks.call_args_list, [call(), call(), call(live=self.target)])

    def test_other_target_recovery_does_not_poll_a_healthy_live_scope(self):
        self.recovery_marker(target='--repo=person/own')
        with patch.object(preferences, 'listener_status', return_value=self.live), \
                patch.object(app, 'poll') as merge, patch.object(ci, 'poll') as checks, patch('sound_library.sync'):
            app.poll_all()
        merge.assert_called_once_with(live=self.target)
        checks.assert_called_once_with(live=self.target)
        self.assertTrue((app.state_dir() / 'webhook-recovery.json').exists())

    def test_recovery_waits_for_merge_lock(self):
        self.recovery_marker()
        with (app.state_dir() / 'poll.lock').open('a') as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(preferences, 'listener_status', return_value=self.live), \
                    patch.object(ci, 'poll'), patch('sound_library.sync'), patch.object(app, 'gh_json') as api:
                app.poll_all()
            api.assert_not_called()
        self.assertTrue((app.state_dir() / 'webhook-recovery.json').exists())

    def test_recovery_waits_for_an_incomplete_ci_check(self):
        self.recovery_marker()
        with patch.object(preferences, 'listener_status', return_value=self.live), \
                patch.object(app, 'poll'), patch.object(ci, 'poll', return_value=False), patch('sound_library.sync'):
            app.poll_all()
        self.assertTrue((app.state_dir() / 'webhook-recovery.json').exists())

    def test_recovery_waits_for_due_account_feed(self):
        self.recovery_marker()
        state = app.read_json(app.state_dir() / 'merges.json', {})
        state['events_next_at'] = app.stamp(self.now + dt.timedelta(seconds=60))
        app.write_json(app.state_dir() / 'merges.json', state)
        event = {'type': 'PullRequestEvent', 'payload': {'action': 'closed',
                 'pull_request': {'id': 1, 'url': self.live_url}}}
        def github(args, env):
            if args == ['api', 'user']:
                return {'login': 'max'}
            if 'search/issues' in args:
                return {'items': [], 'total_count': 0}
            if args[1] == self.live_url:
                return dict(self.detail(), user={'login': 'someone'})
            raise AssertionError(args)
        original_poll = app.poll
        tick = [self.now]
        with patch.object(preferences, 'listener_status', return_value=self.live), \
                patch.object(app, 'poll', side_effect=lambda **kwargs: original_poll(tick[0], **kwargs)), \
                patch.object(ci, 'poll'), patch('sound_library.sync'), \
                patch.object(app, 'gh_json', side_effect=github), \
                patch.object(app, 'gh_events', return_value=([event], 60)) as feed, \
                patch.object(app, 'notify') as sound:
            app.poll_all()
            feed.assert_not_called()
            self.assertTrue((app.state_dir() / 'webhook-recovery.json').exists())
            tick[0] += dt.timedelta(seconds=60)
            app.poll_all()
            feed.assert_called_once_with('max', 1, {})
            sound.assert_called_once_with('merge')
        self.assertFalse((app.state_dir() / 'webhook-recovery.json').exists())

    def ci_api(self, args, env):
        if args == ['api', 'user']:
            return {'login': 'max'}
        if 'search/issues' in args:
            return {'items': [{'repository_url': 'https://api.github.com/repos/' + repo, 'number': 1}
                              for repo in ('team/live', 'person/own')], 'total_count': 2}
        if '/pulls/' in args[1]:
            return {'state': 'open', 'user': {'login': 'max'}, 'head': {'sha': 'a' * 40}}
        if '/actions/runs?' in args[1]:
            return {'workflow_runs': []}
        raise AssertionError(args)

    def test_ci_excludes_live_org_before_pr_and_workflow_reads(self):
        app.write_json(app.state_dir() / 'config.json', {'repositories': ['team/live', 'person/own']})
        with patch.object(app, 'gh_json', side_effect=self.ci_api) as api:
            ci.poll(self.now, live=self.target)
        queries = [call.args[0][5] for call in api.call_args_list if 'search/issues' in call.args[0]]
        self.assertTrue(queries and all('-org:team' in query for query in queries))
        routes = [call.args[0][1] for call in api.call_args_list]
        self.assertFalse(any(route.startswith('repos/team/live/') for route in routes))
        self.assertTrue(any(route.startswith('repos/person/own/actions/runs?') for route in routes))

    def test_ci_fallback_fetches_the_previously_covered_repository(self):
        app.write_json(app.state_dir() / 'config.json', {'repositories': ['team/live']})
        with patch.object(app, 'gh_json', side_effect=self.ci_api) as api:
            ci.poll(self.now, live=self.target)
            self.assertFalse(any(call.args[0][1].startswith('repos/team/live/') for call in api.call_args_list))
            ci.poll(self.now + dt.timedelta(minutes=1))
        self.assertTrue(any(call.args[0][1].startswith('repos/team/live/actions/runs?')
                            for call in api.call_args_list))


if __name__ == '__main__':
    unittest.main()
