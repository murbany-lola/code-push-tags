import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import listen


class ListenerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state = Path(directory.name)
        state = patch.object(listen.app, 'state_dir', return_value=self.state)
        state.start()
        self.addCleanup(state.stop)

    def test_existing_secret_is_reused(self):
        result = subprocess.CompletedProcess([], 0, stdout='saved-secret\n')
        with patch.object(listen.subprocess, 'run', return_value=result) as command:
            self.assertEqual(listen.webhook_secret('coder'), 'saved-secret')
        command.assert_called_once()
        self.assertNotIn('add-generic-password', command.call_args.args[0])

    def test_missing_secret_is_saved(self):
        results = [subprocess.CompletedProcess([], 44, stdout=''),
                   subprocess.CompletedProcess([], 0)]
        with patch.object(listen.subprocess, 'run', side_effect=results) as command, \
                patch.object(listen.secrets, 'token_hex', return_value='new-secret'):
            self.assertEqual(listen.webhook_secret('coder'), 'new-secret')
        self.assertIn('add-generic-password', command.call_args.args[0])
        self.assertIn('new-secret', command.call_args.args[0])

    def test_keychain_denial_does_not_create_a_secret(self):
        result = subprocess.CompletedProcess([], 36, stdout='')
        with patch.object(listen.subprocess, 'run', return_value=result) as command, \
                patch.object(listen.secrets, 'token_hex') as generate:
            with self.assertRaisesRegex(RuntimeError, 'Could not read'):
                listen.webhook_secret('coder')
        command.assert_called_once()
        generate.assert_not_called()

    def run_patches(self):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(listen.app, 'gh_env', return_value={'GH_TOKEN': 'test-token'}))
        stack.enter_context(patch.object(listen.app, 'gh_json', side_effect=lambda args, env:
                                         {'login': 'coder'} if args == ['api', 'user'] else []))
        stack.enter_context(patch.object(listen, 'webhook_secret', return_value='test-secret'))
        stack.enter_context(patch.object(listen.time, 'sleep'))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        response = MagicMock()
        response.__enter__.return_value.status = 200
        stack.enter_context(patch.object(listen.urllib.request, 'urlopen', return_value=response))
        return stack

    def test_unidentified_cli_hook_is_not_removed(self):
        self.run_patches()
        with patch.object(listen.app, 'gh_json', side_effect=[{'login': 'coder'},
                                                            [{'name': 'cli', 'id': 17}]]), \
                patch.object(listen.subprocess, 'run') as command, \
                patch.object(listen.subprocess, 'Popen') as start:
            with self.assertRaisesRegex(RuntimeError, 'already exists'):
                listen.run('--repo=coder/project')
        command.assert_not_called()
        start.assert_not_called()

    def test_second_listener_preserves_active_hook_and_makes_no_external_calls(self):
        path = self.state / 'webhook-pilot.json'
        saved = {'target': '--repo=coder/project', 'id': 23}
        listen.app.write_json(path, saved)
        with (self.state / 'listener.lock').open('a') as lock:
            listen.fcntl.flock(lock, listen.fcntl.LOCK_EX | listen.fcntl.LOCK_NB)
            with patch.object(listen.app, 'gh_env') as auth, \
                    patch.object(listen.app, 'gh_json') as api, \
                    patch.object(listen.subprocess, 'run') as command, \
                    patch.object(listen.subprocess, 'Popen') as start:
                with self.assertRaisesRegex(RuntimeError, 'already running'):
                    listen.run(saved['target'])
            auth.assert_not_called()
            api.assert_not_called()
            command.assert_not_called()
            start.assert_not_called()
        self.assertEqual(listen.app.read_json(path, {}), saved)

    def test_saved_hook_cleanup_uses_exact_id_and_target(self):
        env = {'GH_TOKEN': 'test-token'}
        for target, route in [('--repo=coder/project', 'repos/coder/project/hooks/17'),
                              ('--org=example', 'orgs/example/hooks/17')]:
            with self.subTest(target=target):
                path = self.state / 'webhook-pilot.json'
                listen.app.write_json(path, {'target': target, 'id': 17})
                result = subprocess.CompletedProcess([], 0)
                with patch.object(listen.subprocess, 'run', return_value=result) as command:
                    listen.remove_pilot_hook(target, env)
                command.assert_called_once_with(['gh', 'api', '--include', '--method', 'DELETE', route],
                                                env=env, capture_output=True)
                self.assertFalse(path.exists())

    def test_failed_hook_deletion_preserves_saved_identity(self):
        path = self.state / 'webhook-pilot.json'
        saved = {'target': '--repo=coder/project', 'id': 17}
        listen.app.write_json(path, saved)
        with patch.object(listen.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
            with self.assertRaisesRegex(RuntimeError, 'Could not remove'):
                listen.remove_pilot_hook(saved['target'], {})
        self.assertEqual(listen.app.read_json(path, {}), saved)

    def test_already_removed_hook_clears_saved_identity(self):
        path = self.state / 'webhook-pilot.json'
        saved = {'target': '--repo=coder/project', 'id': 17}
        for protocol in (b'HTTP/1.1', b'HTTP/2.0'):
            with self.subTest(protocol=protocol):
                listen.app.write_json(path, saved)
                response = subprocess.CompletedProcess([], 1, stdout=protocol + b' 404 Not Found\r\n\r\n')
                with patch.object(listen.subprocess, 'run', return_value=response):
                    listen.remove_pilot_hook(saved['target'], {})
                self.assertFalse(path.exists())

    def test_other_http_errors_preserve_saved_identity(self):
        path = self.state / 'webhook-pilot.json'
        saved = {'target': '--repo=coder/project', 'id': 17}
        for status in (b'403 Forbidden', b'500 Internal Server Error'):
            with self.subTest(status=status):
                listen.app.write_json(path, saved)
                response = subprocess.CompletedProcess([], 1, stdout=b'HTTP/2.0 ' + status +
                                                       b'\r\n\r\n{"message":"not a 404"}')
                with patch.object(listen.subprocess, 'run', return_value=response):
                    with self.assertRaisesRegex(RuntimeError, 'Could not remove'):
                        listen.remove_pilot_hook(saved['target'], {})
                self.assertEqual(listen.app.read_json(path, {}), saved)

    def test_other_target_saved_hook_is_not_removed(self):
        path = self.state / 'webhook-pilot.json'
        saved = {'target': '--repo=coder/other', 'id': 18}
        listen.app.write_json(path, saved)
        with patch.object(listen.subprocess, 'run') as command:
            listen.remove_pilot_hook('--repo=coder/project', {})
        command.assert_not_called()
        self.assertEqual(listen.app.read_json(path, {}), saved)

    def test_created_hook_is_recorded_and_removed_on_forwarding_exit(self):
        self.run_patches()
        receiver = MagicMock()
        receiver.poll.return_value = None
        forward = MagicMock()
        forward.poll.side_effect = [None, 4, 4]
        forward.returncode = 4
        with patch.object(listen.app, 'gh_json', side_effect=[{'login': 'coder'}, [],
                                                            [{'name': 'cli', 'id': 19}]]), \
                patch.object(listen.subprocess, 'Popen', side_effect=[receiver, forward]), \
                patch.object(listen.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as command:
            with self.assertRaisesRegex(RuntimeError, 'forwarding stopped'):
                listen.run('--repo=coder/project')
        self.assertEqual(command.call_args.args[0],
                         ['gh', 'api', '--include', '--method', 'DELETE', 'repos/coder/project/hooks/19'])
        self.assertFalse((self.state / 'webhook-pilot.json').exists())

    def test_receiver_start_failure_does_not_start_forwarding(self):
        self.run_patches()
        receiver = MagicMock()
        receiver.poll.return_value = 7
        with patch.object(listen.subprocess, 'Popen', return_value=receiver) as start:
            with self.assertRaisesRegex(RuntimeError, 'receiver stopped'):
                listen.run('--repo=coder/project')
        self.assertEqual(start.call_count, 1)
        receiver.terminate.assert_not_called()

    def test_forwarding_exit_stops_receiver_and_keeps_private_payloads_off_stdout(self):
        self.run_patches()
        receiver = MagicMock()
        receiver.poll.return_value = None
        forward = MagicMock()
        forward.poll.return_value = 4
        forward.returncode = 4
        with patch.object(listen.subprocess, 'Popen', side_effect=[receiver, forward]) as start:
            with self.assertRaisesRegex(RuntimeError, 'forwarding stopped.*4'):
                listen.run('--repo=coder/project', port=8770)
        receiver.terminate.assert_called_once()
        receiver.wait.assert_called_once_with(timeout=5)
        forward.terminate.assert_not_called()
        receiver_call, forward_call = start.call_args_list
        self.assertEqual(receiver_call.kwargs['env']['PUSH_TAGS_WEBHOOK_SECRET'], 'test-secret')
        self.assertEqual(forward_call.kwargs['env']['GH_TOKEN'], 'test-token')
        self.assertIn('--url=http://127.0.0.1:8770/webhook', forward_call.args[0])
        self.assertIn('--repo=coder/project', forward_call.args[0])
        self.assertEqual(forward_call.kwargs['stdout'], subprocess.DEVNULL)

    def test_receiver_runtime_failure_stops_forwarding(self):
        self.run_patches()
        receiver = MagicMock()
        receiver.poll.side_effect = [None, 9, 9]
        forward = MagicMock()
        forward.poll.return_value = None
        with patch.object(listen.subprocess, 'Popen', side_effect=[receiver, forward]):
            with self.assertRaisesRegex(RuntimeError, 'receiver stopped'):
                listen.run('--org=example')
        forward.terminate.assert_called_once()
        forward.wait.assert_called_once_with(timeout=5)

    def test_startup_timeout_stops_receiver_without_a_real_wait(self):
        self.run_patches()
        receiver = MagicMock()
        receiver.poll.return_value = None
        with patch.object(listen.subprocess, 'Popen', return_value=receiver) as start, \
                patch.object(listen.urllib.request, 'urlopen', side_effect=urllib.error.URLError('offline')), \
                patch.object(listen.time, 'monotonic', side_effect=[0, 16]):
            with self.assertRaisesRegex(RuntimeError, 'did not start'):
                listen.run('--repo=coder/project')
        self.assertEqual(start.call_count, 1)
        receiver.terminate.assert_called_once()


if __name__ == '__main__':
    unittest.main()
