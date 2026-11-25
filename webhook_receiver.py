#!/usr/bin/env python3
"""Receive GitHub CLI test deliveries on this Mac."""
import argparse
import datetime as dt
import fcntl
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import re
import sys

import push_tags as app

MAX_BODY = 1024 * 1024


def handle_event(event, payload, now=None):
    """Confirm and record one merged pull request before playback."""
    if event == 'workflow_run':
        import ci_events
        return ci_events.handle_event(payload, now)
    import comment_events
    if event in comment_events.EVENTS:
        return comment_events.handle_event(event, payload, now)
    pr = payload.get('pull_request')
    if (event != 'pull_request' or payload.get('action') != 'closed'
            or not isinstance(pr, dict) or pr.get('merged') is not True):
        return False
    repository = payload.get('repository')
    repo = repository.get('full_name') if isinstance(repository, dict) else None
    number = pr.get('number')
    if (not isinstance(repo, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo)
            or type(number) is not int or number < 1):
        raise ValueError('A repository name and pull request number are required.')
    now = now or dt.datetime.now(app.UTC)
    directory = app.state_dir()
    with (directory / 'poll.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not app.config().get('merge_enabled', True):
            return False
        env = app.gh_env()
        login = app.gh_json(['api', 'user'], env)['login']
        path = directory / 'merges.json'
        state = app.read_json(path, None)
        if state is None:
            raise RuntimeError('The merge baseline is missing. Restart the receiver.')
        if state['login'].lower() != login.lower():
            raise RuntimeError('GitHub account changed. Check the merge baseline.')
        route = f'repos/{repo}/pulls/{number}'
        identity = f'https://api.github.com/{route}'
        seen = dict(state['seen'])
        if identity in seen:
            return False
        detail = app.gh_json(['api', route], env)
        merged_at = detail.get('merged_at')
        if detail.get('merged') is not True or not merged_at:
            return False
        author = (detail.get('user') or {}).get('login', '')
        merger = (detail.get('merged_by') or {}).get('login', '')
        if login.lower() not in (author.lower(), merger.lower()):
            return False
        merged_time = app.parse_stamp(merged_at)
        if merged_time <= app.parse_stamp(state['started_at']) or merged_time > now:
            return False
        seen[identity] = merged_at
        state['seen'] = sorted(seen.items(), key=lambda pair: pair[1])[-2000:]
        app.write_json(path, state)
        import repo_preferences
        if repo_preferences.allowed(repo):
            app.notify('merge')
        return True


class Handler(BaseHTTPRequestHandler):
    """Accept local deliveries without recording payload contents."""

    def reply(self, status, value):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path == '/health':
            self.reply(200, {'ok': True})
        else:
            self.reply(404, {'error': 'Route not found.'})

    def do_POST(self):
        if self.path != '/webhook':
            self.reply(404, {'error': 'Route not found.'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY:
                self.reply(413, {'error': 'Invalid body size.'})
                return
            body = self.rfile.read(length)
            expected = 'sha256=' + hmac.new(self.server.webhook_secret, body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(self.headers.get('X-Hub-Signature-256', ''), expected):
                self.reply(401, {'error': 'Invalid webhook signature.'})
                return
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise ValueError('Expected a JSON object.')
            played = handle_event(self.headers.get('X-GitHub-Event'), payload)
        except (ValueError, TypeError, KeyError):
            self.reply(400, {'error': 'Invalid webhook delivery.'})
            return
        except (OSError, RuntimeError):
            self.reply(503, {'error': 'GitHub verification is unavailable.'})
            return
        self.reply(200, {'recorded': played})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8769)
    args = parser.parse_args()
    secret = os.environ.get('PUSH_TAGS_WEBHOOK_SECRET')
    if not secret:
        raise RuntimeError('PUSH_TAGS_WEBHOOK_SECRET is required.')
    if app.config().get('merge_enabled', True) and not (app.state_dir() / 'merges.json').exists():
        app.poll()
    if app.config().get('merge_enabled', True) and not (app.state_dir() / 'merges.json').exists():
        raise RuntimeError('Enable merge sounds before starting the receiver.')
    if not (app.state_dir() / 'ci.json').exists():
        import ci_events
        ci_events.poll()
    if not (app.state_dir() / 'comments.json').exists():
        import comment_events
        comment_events.poll()
    with HTTPServer(('127.0.0.1', args.port), Handler) as server:
        server.webhook_secret = secret.encode()
        print(f'Webhook test receiver: http://127.0.0.1:{server.server_port}/webhook', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except (OSError, RuntimeError, ValueError) as error:
        print(f'Code Push Tags: {error}', file=sys.stderr)
        sys.exit(1)
