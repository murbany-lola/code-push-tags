#!/usr/bin/env python3
"""Forward GitHub test webhooks to the local audio receiver."""
import argparse
import fcntl
import secrets
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

import push_tags as app


def webhook_secret(login):
    command = ['security', 'find-generic-password', '-s', 'code-push-tags.webhook', '-a', login, '-w']
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    if result.returncode != 44:
        raise RuntimeError('Could not read the webhook secret from Keychain.')
    secret = secrets.token_hex(32)
    result = subprocess.run(['security', 'add-generic-password', '-s', 'code-push-tags.webhook',
                             '-a', login, '-w', secret], capture_output=True)
    if result.returncode:
        raise RuntimeError('Could not save the webhook secret in Keychain.')
    return secret


def hook_route(target):
    flag, _, value = target.partition('=')
    return f'repos/{value}/hooks' if flag == '--repo' else f'orgs/{value}/hooks'


def remove_pilot_hook(target, env):
    path = app.state_dir() / 'webhook-pilot.json'
    saved = app.read_json(path, {})
    if saved.get('target') != target:
        return
    result = subprocess.run(['gh', 'api', '--include', '--method', 'DELETE',
                             f"{hook_route(target)}/{saved['id']}"],
                            env=env, capture_output=True)
    lines = (result.stdout or b'').splitlines()
    status = lines[0].split() if lines else []
    missing = len(status) > 1 and status[1] == b'404'
    if result.returncode and not missing:
        raise RuntimeError('Could not remove the saved pilot webhook. Check GitHub hook settings.')
    path.unlink()


def run(target, port=18769):
    with (app.state_dir() / 'listener.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('The webhook listener is already running on this Mac.')
        return run_locked(target, port)


def run_locked(target, port):
    env = app.gh_env()
    login = app.gh_json(['api', 'user'], env)['login']
    remove_pilot_hook(target, env)
    if any(hook['name'] == 'cli' for hook in app.gh_json(['api', hook_route(target)], env)):
        raise RuntimeError('A GitHub test forwarding hook already exists for this target.')
    secret = webhook_secret(login)
    env['PUSH_TAGS_WEBHOOK_SECRET'] = secret
    receiver = subprocess.Popen([sys.executable, str(app.ROOT / 'webhook_receiver.py'),
                                 '--port', str(port)], env=env)
    forward = None
    try:
        deadline = time.monotonic() + 15
        while True:
            if receiver.poll() is not None:
                raise RuntimeError('The local webhook receiver stopped.')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=1) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError):
                if time.monotonic() >= deadline:
                    raise RuntimeError('The local webhook receiver did not start.')
                time.sleep(0.1)
        print(f'Listening for your merges and CI failures as {login}. Keep this process running.', flush=True)
        # The URL prevents the extension from printing private event payloads.
        forward = subprocess.Popen(['gh', 'webhook', 'forward', target, '--events=pull_request,workflow_run',
                                    f'--url=http://127.0.0.1:{port}/webhook', '--secret', secret],
                                   env=env, stdout=subprocess.DEVNULL)
        saved = False
        while forward.poll() is None:
            if receiver.poll() is not None:
                raise RuntimeError('The local webhook receiver stopped.')
            if not saved:
                hooks = app.gh_json(['api', hook_route(target)], env)
                created = [hook for hook in hooks if hook['name'] == 'cli']
                if created:
                    app.write_json(app.state_dir() / 'webhook-pilot.json',
                                   {'target': target, 'id': created[0]['id']})
                    saved = True
            time.sleep(0.25)
        raise RuntimeError(f'GitHub webhook forwarding stopped (exit {forward.returncode}).')
    finally:
        for child in (forward, receiver):
            if child is not None and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
        remove_pilot_hook(target, env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--repo')
    target.add_argument('--org')
    parser.add_argument('--port', type=int, default=18769)
    args = parser.parse_args()
    flag = f'--repo={args.repo}' if args.repo else f'--org={args.org}'
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        run(flag, args.port)
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError) as error:
        print(f'Code Push Tags: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
