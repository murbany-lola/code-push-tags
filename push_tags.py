#!/usr/bin/env python3
"""Play local audio tags for pushes, merges, and failed CI runs."""
import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
UTC = dt.timezone.utc


def state_dir():
    path = Path(os.environ.get('PUSH_TAGS_STATE_DIR', Path.home() / 'Library/Application Support/Code Push Tags'))
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def read_json(path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def write_json(path, value):
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def config():
    return read_json(state_dir() / 'config.json', {})


def tags():
    return read_json(ROOT / 'manifest.json', {'tags': []})['tags']


def play(event='any', tag_id=None):
    if read_json(state_dir() / 'settings.json', {}).get('muted', False):
        return False
    preferences = config()
    if event in ('push', 'merge', 'ci') and not preferences.get(f'{event}_enabled', True):
        return False
    if tag_id is None and event in ('push', 'merge', 'ci'):
        tag_id = preferences.get(f'{event}_tag', 'lego-break-apart' if event == 'ci' else None)
        if tag_id == 'random':
            tag_id = None
    choices = [tag for tag in tags() if (tag_id is None or tag['id'] == tag_id)
               and (tag_id is not None or event == 'any' or tag.get('event', 'any') in (event, 'any'))]
    if not choices:
        return False
    tag = random.choice(choices)
    path = (ROOT / tag['file']).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError('The audio file is missing or outside the kit directory.')
    subprocess.Popen(['afplay', '-v', '0.45', str(path)], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return True


def notify(event):
    try:
        play(event)
    except Exception:
        # An audio error must not change a successful Git result.
        pass


def push(args):
    status = subprocess.call(['git', 'push', *args])
    if status == 0:
        notify_push()
    return status if status >= 0 else 128 - status


def notify_push(git_args=None):
    try:
        import repo_preferences
        if repo_preferences.allowed(None) or repo_preferences.allowed(repo_preferences.git_repository(git_args)):
            notify('push')
    except Exception:
        # A notification error must not change a successful push.
        pass


def gh_env():
    env = os.environ.copy()
    source = config().get('auth', {})
    if source.get('keychain_service'):
        command = ['security', 'find-generic-password', '-s', source['keychain_service'], '-w']
        if source.get('keychain_account'):
            command.extend(['-a', source['keychain_account']])
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode or not result.stdout.strip():
            raise RuntimeError('GitHub authentication failed. Check the configured Keychain item.')
        env['GH_TOKEN'] = result.stdout.strip()
        env.pop('GITHUB_TOKEN', None)
    return env


def gh_json(args, env):
    result = subprocess.run(['gh', *args], env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('GitHub request failed. Check gh authentication and network access.')
    return json.loads(result.stdout)


def stamp(value):
    return value.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def parse_stamp(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))


def gh_events(login, page, env):
    result = subprocess.run(['gh', 'api', '--include', f'users/{login}/events?per_page=100&page={page}'],
                            env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('GitHub Events request failed. Check gh authentication and network access.')
    headers, separator, body = result.stdout.partition('\n\n')
    if not separator:
        raise RuntimeError('GitHub Events response headers are missing.')
    interval = 60
    for line in headers.splitlines():
        key, colon, value = line.partition(':')
        if colon and key.lower() == 'x-poll-interval':
            interval = max(0, int(value.strip()))
    return json.loads(body), interval


def search_merges(login, since, env, state=None, now=None):
    found = {}
    for qualifier in ('author', 'involves'):
        page = 1
        while True:
            query = f'is:pr is:merged {qualifier}:{login} merged:>={stamp(since)}'
            data = gh_json(['api', '--method', 'GET', 'search/issues', '-f', f'q={query}',
                            '-f', 'sort=updated', '-f', 'order=asc', '-f', 'per_page=100', '-f', f'page={page}'], env)
            if data.get('incomplete_results') or data.get('total_count', 0) > 1000:
                raise RuntimeError('GitHub search is incomplete. The checkpoint was not changed.')
            items = data['items']
            for item in items:
                found[item['pull_request']['url']] = item
            if len(items) < 100:
                break
            page += 1
    now = now or dt.datetime.now(UTC)
    if state and state.get('events_next_at') and now < parse_stamp(state['events_next_at']):
        return found
    # Authenticated user events include private events that the token can read.
    # GitHub returns at most 300 events. Search supplies the longer authored history.
    for page in range(1, 4):
        events, interval = gh_events(login, page, env)
        if state is not None:
            next_at = now + dt.timedelta(seconds=interval)
            if state.get('events_next_at'):
                next_at = max(next_at, parse_stamp(state['events_next_at']))
            state['events_next_at'] = stamp(next_at)
            # Save the interval before detail reads, which can fail independently.
            write_json(state_dir() / 'merges.json', state)
        for event in events:
            if event.get('created_at') and parse_stamp(event['created_at']) < since:
                continue
            payload = event.get('payload', {})
            pr = payload.get('pull_request', {})
            if (event.get('type') == 'PullRequestEvent' and payload.get('action') in ('closed', 'merged')
                    and pr.get('id') is not None and pr.get('url')):
                found[pr['url']] = {'pull_request': {'url': pr['url']}}
        if len(events) < 100:
            break
    return found


def poll(now=None):
    now = now or dt.datetime.now(UTC)
    directory = state_dir()
    with (directory / 'poll.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        if not config().get('merge_enabled', True):
            return
        env = gh_env()
        login = gh_json(['api', 'user'], env)['login']
        path = directory / 'merges.json'
        state = read_json(path, None)
        if state is None:
            write_json(path, {'login': login, 'started_at': stamp(now), 'checkpoint': stamp(now), 'seen': []})
            return
        if state['login'].lower() != login.lower():
            raise RuntimeError('GitHub account changed. Remove merges.json to start a new baseline.')
        start = parse_stamp(state['started_at'])
        since = max(start, parse_stamp(state['checkpoint']) - dt.timedelta(days=1))
        matches = search_merges(login, since, env, state, now)
        seen = dict(state['seen'])
        events = []
        for identity, item in matches.items():
            if identity in seen:
                continue
            api_url = item['pull_request']['url']
            # Search metadata can be delayed. The pull request response confirms the merge.
            detail = gh_json(['api', api_url], env)
            merged_at = detail.get('merged_at')
            if not detail.get('merged') or not merged_at:
                continue
            author = (detail.get('user') or {}).get('login', '')
            merger = (detail.get('merged_by') or {}).get('login', '')
            if login.lower() not in (author.lower(), merger.lower()):
                continue
            merged_time = parse_stamp(merged_at)
            if merged_time <= start or merged_time > now:
                continue
            seen[identity] = merged_at
            events.append(identity)
        state['seen'] = sorted(seen.items(), key=lambda pair: pair[1])[-2000:]
        state['checkpoint'] = stamp(now)
        write_json(path, state)
        import repo_preferences
        for identity in events:
            repo = identity.removeprefix('https://api.github.com/repos/').split('/pulls/', 1)[0]
            if repo_preferences.allowed(repo):
                notify('merge')


def doctor():
    good = True
    for name in ('git', 'gh', 'afplay'):
        present = shutil.which(name) is not None
        print(f'{name}: {"available" if present else "missing"}')
        good &= present
    try:
        gh_json(['api', 'user'], gh_env())
        print('GitHub authentication: available')
    except (OSError, RuntimeError, ValueError):
        print('GitHub authentication: unavailable; use gh auth login or configure an existing Keychain item')
        good = False
    print(f'Audio tags: {len(tags())}')
    return 0 if good else 1


def poll_all():
    import ci_events
    failures = []
    for check in (poll, ci_events.poll):
        try:
            check()
        except (OSError, ValueError, RuntimeError, KeyError) as error:
            failures.append(error)
    if failures:
        raise RuntimeError('One or more GitHub event checks failed. Check authentication and network access.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('list')
    player = commands.add_parser('play')
    player.add_argument('tag', nargs='?')
    player.add_argument('--event', choices=['any', 'push', 'merge', 'ci'], default='any')
    commands.add_parser('off')
    commands.add_parser('on')
    for name in ('mute', 'unmute', 'poll', 'doctor'):
        commands.add_parser(name)
    preferences = commands.add_parser('configure')
    preferences.add_argument('--push-tag')
    preferences.add_argument('--merge-tag')
    preferences.add_argument('--ci-tag')
    preferences.add_argument('--push', choices=['on', 'off'])
    preferences.add_argument('--merge', choices=['on', 'off'])
    preferences.add_argument('--ci', choices=['on', 'off'])
    commands.add_parser('push').add_argument('args', nargs=argparse.REMAINDER)
    commands.add_parser('notify-push').add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command == 'list':
        for tag in tags():
            print(f"{tag['id']} [{tag.get('event', 'any')}]: {tag['text']}")
    elif args.command == 'play':
        if not play(args.event, args.tag):
            print('No audio played: muted or no matching tag.', file=sys.stderr)
            return 1
    elif args.command in ('mute', 'unmute', 'off', 'on'):
        write_json(state_dir() / 'settings.json', {'muted': args.command in ('mute', 'off')})
    elif args.command == 'configure':
        settings = config()
        available = tags()
        for event in ('push', 'merge', 'ci'):
            selected = getattr(args, f'{event}_tag')
            if selected is not None:
                if selected != 'random' and not any(tag['id'] == selected for tag in available):
                    parser.error(f'No matching {event} tag: {selected}')
                settings[f'{event}_tag'] = selected
            enabled = getattr(args, event)
            if enabled is not None:
                settings[f'{event}_enabled'] = enabled == 'on'
        write_json(state_dir() / 'config.json', settings)
    elif args.command == 'push':
        return push(args.args[1:] if args.args[:1] == ['--'] else args.args)
    elif args.command == 'notify-push':
        notify_push(args.args[1:] if args.args[:1] == ['--'] else args.args)
    elif args.command == 'poll':
        poll_all()
    elif args.command == 'doctor':
        return doctor()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f'Code Push Tags: {error}', file=sys.stderr)
        sys.exit(1)
