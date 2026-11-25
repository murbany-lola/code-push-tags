import copy
import datetime as dt
import hashlib
import hmac
import http.client
from http.server import HTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import push_tags as app
import webhook_receiver as receiver


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env_patch = patch.dict(os.environ, {'PUSH_TAGS_STATE_DIR': self.temp.name})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.now = dt.datetime(2026, 11, 25, 18, 0, tzinfo=app.UTC)
        self.start = self.now - dt.timedelta(hours=1)
        self.identity = 'https://api.github.com/repos/owner/repo/pulls/17'
        self.payload = {'action': 'closed', 'repository': {'full_name': 'owner/repo'},
                        'pull_request': {'number': 17, 'merged': True, 'url': 'https://untrusted.invalid'}}
        self.detail = {'merged': True, 'merged_at': app.stamp(self.now - dt.timedelta(minutes=1)),
                       'user': {'login': 'Max'}, 'merged_by': {'login': 'other'}}
        self.baseline = {'login': 'max', 'started_at': app.stamp(self.start),
                         'checkpoint': app.stamp(self.start), 'seen': []}
        app.write_json(app.state_dir() / 'merges.json', self.baseline)
        self.auth = patch.object(app, 'gh_env', return_value={})
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.api = patch.object(app, 'gh_json', side_effect=self.api_response)
        self.api_mock = self.api.start()
        self.addCleanup(self.api.stop)
        self.notify = patch.object(app, 'notify')
        self.notify_mock = self.notify.start()
        self.addCleanup(self.notify.stop)

    def api_response(self, args, env):
        if args == ['api', 'user']:
            return {'login': 'max'}
        if args in (['api', 'repos/owner/repo/pulls/17'], ['api', self.identity]):
            return copy.deepcopy(self.detail)
        raise AssertionError(args)

    def send(self, payload=None, event='pull_request'):
        return receiver.handle_event(event, payload or self.payload, self.now)

    def state(self):
        return app.read_json(app.state_dir() / 'merges.json', None)

    def test_remote_verification_and_shared_identity(self):
        self.assertTrue(self.send())
        self.notify_mock.assert_called_once_with('merge')
        self.assertEqual(self.state()['seen'], [[self.identity, self.detail['merged_at']]])
        self.assertEqual(self.state()['checkpoint'], self.baseline['checkpoint'])
        self.assertIn(unittest.mock.call(['api', 'repos/owner/repo/pulls/17'], {}), self.api_mock.call_args_list)

    def test_irrelevant_and_unmerged_deliveries_do_not_call_api(self):
        for event, change in [('ping', {}), ('push', {}), ('pull_request', {'action': 'opened'}),
                              ('pull_request', {'pull_request': {'number': 17, 'merged': False}})]:
            payload = copy.deepcopy(self.payload)
            payload.update(change)
            self.assertFalse(self.send(payload, event))
        self.api_mock.assert_not_called()

    def test_remote_rejection_and_other_users_do_not_play(self):
        for change in ({'merged': False}, {'merged_at': None}, {'user': {'login': 'someone'}}):
            previous = copy.deepcopy(self.detail)
            self.detail.update(change)
            self.assertFalse(self.send())
            self.detail = previous
        self.notify_mock.assert_not_called()
        self.assertEqual(self.state()['seen'], [])

    def test_merger_is_also_eligible(self):
        self.detail.update(user={'login': 'other'}, merged_by={'login': 'MAX'})
        self.assertTrue(self.send())

    def test_time_boundaries_use_remote_timestamp(self):
        for merged_time in (self.start, self.start - dt.timedelta(seconds=1), self.now + dt.timedelta(seconds=1)):
            self.detail['merged_at'] = app.stamp(merged_time)
            self.assertFalse(self.send())
        self.notify_mock.assert_not_called()

    def test_poll_seen_identity_prevents_webhook_replay(self):
        state = self.state()
        state['seen'] = [[self.identity, self.detail['merged_at']]]
        app.write_json(app.state_dir() / 'merges.json', state)
        self.assertFalse(self.send())
        self.notify_mock.assert_not_called()
        self.assertEqual(self.api_mock.call_count, 1)

    def test_webhook_prevents_replay_in_poll_and_after_state_read(self):
        self.assertTrue(self.send())
        matches = {self.identity: {'pull_request': {'url': self.identity}}}
        with patch.object(app, 'search_merges', return_value=matches):
            app.poll(self.now)
        self.assertFalse(self.send())
        self.notify_mock.assert_called_once_with('merge')

    def test_muted_event_is_recorded_without_audio(self):
        self.notify.stop()
        app.write_json(app.state_dir() / 'settings.json', {'muted': True})
        with patch.object(app.subprocess, 'Popen') as playback:
            self.assertTrue(self.send())
            self.assertFalse(self.send())
            playback.assert_not_called()
        self.assertEqual(len(self.state()['seen']), 1)

    def test_disabled_merge_matches_poll_behavior(self):
        app.write_json(app.state_dir() / 'config.json', {'merge_enabled': False})
        self.assertFalse(self.send())
        self.api_mock.assert_not_called()
        self.assertEqual(self.state()['seen'], [])

    def test_account_change_preserves_state(self):
        self.baseline['login'] = 'someone'
        app.write_json(app.state_dir() / 'merges.json', self.baseline)
        with self.assertRaises(RuntimeError):
            self.send()
        self.assertEqual(self.state(), self.baseline)

    def test_github_failure_preserves_state(self):
        self.api_mock.side_effect = RuntimeError('request failed')
        with self.assertRaises(RuntimeError):
            self.send()
        self.assertEqual(self.state(), self.baseline)

    def test_invalid_repository_and_number_do_not_call_api(self):
        for repo, number in [('https://bad.test/x', 17), ('owner/repo', True), ('owner/repo', -1)]:
            p = copy.deepcopy(self.payload)
            p['repository']['full_name'] = repo
            p['pull_request']['number'] = number
            with self.assertRaises(ValueError):
                self.send(p)
        self.api_mock.assert_not_called()


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.secret = b'test-only-secret'
        cls.server = HTTPServer(('127.0.0.1', 0), receiver.Handler)
        cls.server.webhook_secret = cls.secret
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, signed=True):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
        headers = {'X-GitHub-Event': 'ping'}
        if body is not None:
            headers['X-Hub-Signature-256'] = ('sha256=' + hmac.new(self.secret, body, hashlib.sha256).hexdigest()) if signed else 'sha256=invalid'
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        result = response.status, json.loads(response.read())
        conn.close()
        return result

    def test_health_and_unknown_route(self):
        self.assertEqual(self.request('GET', '/health'), (200, {'ok': True}))
        self.assertEqual(self.request('GET', '/elsewhere')[0], 404)
        self.assertEqual(self.request('POST', '/elsewhere', b'{}')[0], 404)

    def test_valid_signature_reaches_handler(self):
        with patch.object(receiver, 'handle_event', return_value=False) as handle:
            self.assertEqual(self.request('POST', '/webhook', b'{}'), (200, {'recorded': False}))
            handle.assert_called_once_with('ping', {})

    def test_invalid_signature_never_reaches_handler(self):
        with patch.object(receiver, 'handle_event') as handle:
            self.assertEqual(self.request('POST', '/webhook', b'{}', signed=False)[0], 401)
            handle.assert_not_called()

    def test_malformed_json_and_non_object(self):
        for body in (b'not JSON', b'[]'):
            self.assertEqual(self.request('POST', '/webhook', body)[0], 400)

    def test_verification_failure_returns_service_error(self):
        with patch.object(receiver, 'handle_event', side_effect=RuntimeError('private details')):
            status, body = self.request('POST', '/webhook', b'{}')
            self.assertEqual(status, 503)
            self.assertNotIn('private details', json.dumps(body))


if __name__ == '__main__':
    unittest.main()
