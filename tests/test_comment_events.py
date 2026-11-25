import copy
import datetime as dt
import fcntl
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import comment_events as comments
import push_tags as app


class CommentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.now = dt.datetime(2026, 11, 25, 20, tzinfo=app.UTC)
        self.timestamp = app.stamp(self.now - dt.timedelta(minutes=1))
        patcher = patch.dict(os.environ, {'PUSH_TAGS_STATE_DIR': temporary.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.path = app.state_dir() / 'comments.json'
        self.baseline()
        self.payload = {'action': 'created', 'repository': {'full_name': 'Owner/Repo'},
                        'issue': {'number': 17, 'pull_request': {}}, 'comment': {'id': 123}}
        self.payload['issue']['pull_request'] = {'url': 'https://untrusted.invalid/'}
        self.detail = {'id': 123, 'issue_url': 'https://api.github.com/repos/owner/repo/issues/17',
                       'pull_request_url': 'https://api.github.com/repos/owner/repo/pulls/17',
                       'created_at': self.timestamp, 'submitted_at': self.timestamp,
                       'user': {'type': 'User', 'login': 'other'}, 'body': 'A private comment.'}
        self.pr = {'user': {'login': 'MAX'}}
        self.calls = []
        for target, kwargs in [(('gh_env'), {'return_value': {}}),
                               (('gh_json'), {'side_effect': self.api}),
                               (('notify'), {}), (('config'), {'return_value': {}})]:
            patcher = patch.object(app, target, **kwargs)
            mock = patcher.start()
            self.addCleanup(patcher.stop)
            if target == 'notify':
                self.notify = mock
        patcher = patch.object(comments.repo_preferences, 'allowed', return_value=True)
        self.allowed = patcher.start()
        self.addCleanup(patcher.stop)
        self.notifications = [{'repository': {'full_name': 'owner/repo'}, 'subject': {
            'type': 'PullRequest', 'url': 'https://api.github.com/repos/owner/repo/pulls/17',
            'latest_comment_url': 'https://api.github.com/repos/owner/repo/issues/comments/123'}}]
        patcher = patch.object(comments, 'read_notifications', side_effect=self.feed)
        self.reader = patcher.start()
        self.addCleanup(patcher.stop)

    def baseline(self, **extra):
        start = app.stamp(self.now - dt.timedelta(hours=1))
        state = {'login': 'max', 'started_at': start, 'checkpoint': start,
                 'initialized': True, 'seen': []}
        state.update(extra)
        app.write_json(self.path, state)

    def api(self, args, _env):
        self.calls.append(args)
        if args == ['api', 'user']:
            return {'login': 'max'}
        if args[1].casefold() == 'repos/owner/repo/pulls/17':
            return copy.deepcopy(self.pr)
        if args[1] in ('repos/owner/repo/issues/comments/123',
                        'repos/owner/repo/pulls/comments/123',
                        'repos/owner/repo/pulls/17/reviews/123'):
            return copy.deepcopy(self.detail)
        raise AssertionError(args)

    def feed(self, route, env):
        return self.notifications, 90

    def send(self, event='issue_comment'):
        return comments.handle_event(event, self.payload, self.now)

    def state(self):
        return app.read_json(self.path, None)

    def test_webhook_then_poll_deduplicates_without_reading_comment_again(self):
        self.assertTrue(self.send())
        self.assertTrue(comments.poll(self.now))
        self.assertEqual(sum(call[1].endswith('comments/123') for call in self.calls), 1)
        self.notify.assert_called_once_with('comment')
        self.assertNotIn('private', self.path.read_text())
        self.assertNotIn('other', self.path.read_text())

    def test_poll_then_webhook_deduplicates(self):
        self.assertTrue(comments.poll(self.now))
        self.assertFalse(self.send())
        self.notify.assert_called_once_with('comment')
        self.assertIn('all=true', self.reader.call_args.args[0])

    def test_all_three_event_types(self):
        for event in comments.EVENTS:
            with self.subTest(event=event):
                self.baseline()
                self.payload.update(pull_request={'number': 17}, review={'id': 123},
                                    action='submitted' if event == 'pull_request_review' else 'created')
                self.assertTrue(self.send(event))
        self.assertEqual(self.notify.call_count, 3)

    def test_ignore_own_bot_and_unrelated_pr(self):
        for actor in ({'login': 'MAX', 'type': 'User'}, {'login': 'bot', 'type': 'Bot'},
                      {'login': 'review[bot]', 'type': 'User'}):
            self.baseline()
            self.detail['user'] = actor
            self.assertFalse(self.send())
        self.baseline()
        self.detail['user'] = {'login': 'other', 'type': 'User'}
        self.pr['user']['login'] = 'someone'
        self.assertFalse(self.send())
        self.notify.assert_not_called()

    def test_ignores_issue_edits_and_empty_reviews(self):
        self.payload['issue'].pop('pull_request')
        self.assertFalse(self.send())
        self.payload.update(action='edited', pull_request={'number': 17})
        self.assertFalse(self.send('pull_request_review_comment'))
        self.payload.update(action='submitted', review={'id': 123})
        self.detail['body'] = '  '
        self.assertFalse(self.send('pull_request_review'))
        self.notify.assert_not_called()

    def test_remote_pr_and_time_boundaries(self):
        self.detail['issue_url'] = 'https://api.github.com/repos/owner/repo/issues/99'
        self.assertFalse(self.send())
        self.detail['issue_url'] = 'https://api.github.com/repos/owner/repo/issues/17'
        for stamp in (self.state()['started_at'], app.stamp(self.now + dt.timedelta(seconds=1))):
            self.detail['created_at'] = stamp
            self.assertFalse(self.send())
        self.notify.assert_not_called()

    def test_excluded_and_disabled_events_do_not_replay(self):
        self.allowed.return_value = False
        self.assertFalse(self.send())
        self.allowed.return_value = True
        self.assertFalse(self.send())
        self.notify.assert_not_called()
        self.baseline()
        with patch.object(app, 'config', return_value={'comment_enabled': False}):
            self.assertFalse(self.send())
        self.assertFalse(self.send())

    def test_baseline_does_not_read_or_play_history(self):
        self.path.unlink()
        self.assertTrue(comments.poll(self.now))
        self.reader.assert_not_called()
        self.notify.assert_not_called()
        self.assertEqual(self.state()['started_at'], app.stamp(self.now))

    def test_account_change_fails(self):
        self.baseline(login='someone')
        with self.assertRaisesRegex(RuntimeError, 'account changed'):
            comments.poll(self.now)
        self.reader.assert_not_called()

    def test_live_scope_skips_details_for_only_covered_event(self):
        with patch.object(app, 'live_covers', return_value=True, create=True):
            self.assertTrue(comments.poll(self.now, {'issue_comment': ('org', 'owner')}))
        self.assertEqual(self.calls, [['api', 'user']])
        self.notify.assert_not_called()

    def test_untrusted_route_does_not_call_api(self):
        self.notifications[0]['subject']['latest_comment_url'] = 'https://untrusted.invalid/comments/123'
        comments.poll(self.now)
        self.assertEqual(self.calls, [['api', 'user']])
        self.notify.assert_not_called()

    def test_pagination_and_provider_interval(self):
        self.reader.side_effect = [(self.notifications * 50, 120), ([], 60)]
        self.assertTrue(comments.poll(self.now))
        self.assertEqual(self.reader.call_count, 2)
        self.assertFalse(comments.poll(self.now + dt.timedelta(seconds=119)))
        self.assertEqual(self.reader.call_count, 2)
        self.reader.side_effect = None
        self.reader.return_value = ([], 60)
        self.assertTrue(comments.poll(self.now + dt.timedelta(seconds=120)))

    def test_concurrent_webhook_write_is_preserved(self):
        original = self.api
        def api(args, env):
            if args[1].endswith('comments/123'):
                state = self.state()
                state['seen'] = [['https://api.github.com/repos/owner/repo/issues/comments/456', self.timestamp]]
                app.write_json(self.path, state)
            return original(args, env)
        with patch.object(app, 'gh_json', side_effect=api):
            comments.poll(self.now)
        self.assertEqual(len(self.state()['seen']), 2)

    def test_old_feed_comment_is_cached_without_playback(self):
        self.detail['created_at'] = self.state()['started_at']
        self.assertTrue(comments.poll(self.now))
        first_reads = len(self.calls)
        self.assertTrue(comments.poll(self.now + dt.timedelta(seconds=90)))
        self.assertEqual(len(self.calls), first_reads + 1)
        self.assertEqual(len(self.state()['seen']), 1)
        self.notify.assert_not_called()

    def test_deleted_item_does_not_block_valid_comment(self):
        for status in (404, 410):
            with self.subTest(status=status):
                self.baseline()
                self.notify.reset_mock()
                notifications = copy.deepcopy(self.notifications)
                deleted = copy.deepcopy(notifications[0])
                deleted['subject']['latest_comment_url'] = 'https://api.github.com/repos/owner/repo/issues/comments/456'
                self.notifications = notifications + [deleted]
                original = self.api
                def api(args, env):
                    if args[1].endswith('comments/456'):
                        raise app.GitHubAPIError(status)
                    return original(args, env)
                with patch.object(app, 'gh_json', side_effect=api) as call:
                    self.assertTrue(comments.poll(self.now))
                    self.notify.assert_called_once_with('comment')
                    self.assertEqual(len(self.state()['seen']), 2)
                    call.reset_mock()
                    self.assertTrue(comments.poll(self.now + dt.timedelta(seconds=90)))
                    self.assertEqual(call.call_args_list, [unittest.mock.call(['api', 'user'], {})])
                self.notifications = notifications

    def test_transient_item_failure_keeps_valid_comment_and_checkpoint(self):
        failed = copy.deepcopy(self.notifications[0])
        failed['subject']['latest_comment_url'] = 'https://api.github.com/repos/owner/repo/issues/comments/456'
        self.notifications.append(failed)
        checkpoint = self.state()['checkpoint']
        original = self.api
        def api(args, env):
            if args[1].endswith('comments/456'):
                raise app.GitHubAPIError(503)
            return original(args, env)
        with patch.object(app, 'gh_json', side_effect=api):
            self.assertFalse(comments.poll(self.now))
        self.notify.assert_called_once_with('comment')
        self.assertEqual(len(self.state()['seen']), 1)
        self.assertEqual(self.state()['checkpoint'], checkpoint)

    def test_network_reads_do_not_hold_state_lock(self):
        original = self.api
        def api(args, env):
            with (app.state_dir() / 'comments.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return original(args, env)
        with patch.object(app, 'gh_json', side_effect=api):
            comments.poll(self.now)
        self.notify.assert_called_once_with('comment')

    def test_receiver_dispatches_comment_events(self):
        import webhook_receiver
        with patch.object(comments, 'handle_event', return_value=True) as handler:
            for event in comments.EVENTS:
                self.assertTrue(webhook_receiver.handle_event(event, {}, self.now))
                handler.assert_called_with(event, {}, self.now)

    def test_provider_failure_preserves_checkpoint(self):
        before = self.state()['checkpoint']
        with patch.object(app, 'gh_json', side_effect=lambda args, env: {'login': 'max'}
                          if args[1] == 'user' else (_ for _ in ()).throw(RuntimeError('Unavailable'))):
            self.assertFalse(comments.poll(self.now))
        self.assertEqual(self.state()['checkpoint'], before)



class ResponseTests(unittest.TestCase):
    def test_gh_json_preserves_status_without_provider_text(self):
        for stderr, expected in [('gh: private details (HTTP 404)', 404),
                                 ('gh: private details (HTTP 503)', 503),
                                 ('connection failure secret details', None)]:
            with self.subTest(expected=expected), patch.object(app.subprocess, 'run',
                    return_value=Mock(returncode=1, stderr=stderr)):
                with self.assertRaises(app.GitHubAPIError) as caught:
                    app.gh_json(['api', 'user'], {})
                self.assertEqual(caught.exception.status_code, expected)
                self.assertNotIn('details', str(caught.exception))

    def test_provider_interval(self):
        with patch.object(comments.subprocess, 'run', return_value=Mock(returncode=0,
                stdout='HTTP/2.0 200 OK\r\nX-Poll-Interval: 180\r\n\r\n[]')):
            self.assertEqual(comments.read_notifications('notifications', {}), ([], 180))


if __name__ == '__main__':
    unittest.main()
