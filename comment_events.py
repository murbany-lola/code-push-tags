"""Confirm human comments on pull requests authored by the current user."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import datetime as dt
import fcntl
import json
import re
import subprocess
from urllib.parse import urlencode

import push_tags as app
import repo_preferences

EVENTS = ('issue_comment', 'pull_request_review_comment', 'pull_request_review')
REPOSITORY = r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+'


@contextmanager
def locked_state(login, now):
    """Keep state writes short. Do not use the network with this lock held."""
    directory = app.state_dir()
    with (directory / 'comments.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = directory / 'comments.json'
        state = app.read_json(path, None)
        if state is None:
            state = {'login': login, 'started_at': app.stamp(now),
                     'checkpoint': app.stamp(now), 'seen': []}
        elif state['login'].casefold() != login.casefold():
            raise RuntimeError('GitHub account changed. Check the comment baseline.')
        yield state
        app.write_json(path, state)


def parse_route(url):
    """Accept only GitHub comment and review routes with positive IDs."""
    if not isinstance(url, str):
        return None
    match = re.fullmatch(r'https://api\.github\.com/repos/(' + REPOSITORY
                         + r')/(issues/comments|pulls/comments|pulls/[1-9][0-9]*/reviews)/([1-9][0-9]*)', url)
    if not match:
        return None
    repo, kind, item = match.groups()
    event = (EVENTS[0] if kind == 'issues/comments' else
             EVENTS[1] if kind == 'pulls/comments' else EVENTS[2])
    return repo, event, f'repos/{repo.casefold()}/{kind}/{item}'


def pr_number(url, repo):
    if not isinstance(url, str):
        return None
    match = re.fullmatch(r'https://api\.github\.com/repos/' + re.escape(repo)
                         + r'/(?:pulls|issues)/([1-9][0-9]*)', url, re.IGNORECASE)
    return int(match[1]) if match else None


def verified(route, repo, event, number, login, env, now):
    try:
        return read_comment(route, repo, event, number, login, env, now)
    except app.GitHubAPIError as error:
        if error.status_code not in (404, 410):
            raise
        return 'https://api.github.com/' + route, app.stamp(now), repo, False


def read_comment(route, repo, event, number, login, env, now):
    """Read the provider record. Do not use text from a webhook as evidence."""
    detail = app.gh_json(['api', route], env)
    eligible = True
    if event == EVENTS[2]:
        actual_number = pr_number(detail.get('pull_request_url'), repo)
        timestamp = detail.get('submitted_at')
        has_text = isinstance(detail.get('body'), str) and bool(detail['body'].strip())
        eligible = detail.get('state') not in ('PENDING', 'DISMISSED') and has_text
    else:
        actual_number = pr_number(detail.get('issue_url' if event == EVENTS[0]
                                            else 'pull_request_url'), repo)
        timestamp = detail.get('created_at')
    if actual_number != number or not timestamp:
        return None
    actor = detail.get('user') or {}
    actor_login = actor.get('login', '')
    eligible = (eligible and actor.get('type') == 'User' and bool(actor_login)
                and actor_login.casefold() != login.casefold()
                and not actor_login.casefold().endswith('[bot]'))
    when = app.parse_stamp(timestamp)
    if when > now:
        return None
    if eligible:
        pr = app.gh_json(['api', f'repos/{repo}/pulls/{number}'], env)
        eligible = (pr.get('user') or {}).get('login', '').casefold() == login.casefold()
    return 'https://api.github.com/' + route, timestamp, repo, eligible


def commit(records, login, now, checkpoint=None):
    """Merge with webhook writes before playback."""
    count = 0
    with locked_state(login, now) as state:
        seen = dict(state['seen'])
        for identity, timestamp, repo, eligible in records:
            if identity in seen:
                continue
            seen[identity] = timestamp
            eligible = eligible and app.parse_stamp(timestamp) > app.parse_stamp(state['started_at'])
            if eligible and app.config().get('comment_enabled', True) and repo_preferences.allowed(repo):
                count += 1
        state['seen'] = sorted(seen.items(), key=lambda item: item[1])
        if checkpoint is not None:
            state['checkpoint'] = app.stamp(max(app.parse_stamp(state['checkpoint']), checkpoint))
    for _ in range(count):
        app.notify('comment')
    return bool(count)


def handle_event(event, payload, now=None):
    if event not in EVENTS:
        return False
    action = 'submitted' if event == EVENTS[2] else 'created'
    if payload.get('action') != action:
        return False
    subject = payload.get('issue') if event == EVENTS[0] else payload.get('pull_request')
    if not isinstance(subject, dict) or (event == EVENTS[0] and not subject.get('pull_request')):
        return False
    comment = payload.get('review' if event == EVENTS[2] else 'comment')
    repo = (payload.get('repository') or {}).get('full_name')
    number = subject.get('number')
    item = comment.get('id') if isinstance(comment, dict) else None
    if (not isinstance(repo, str) or not re.fullmatch(REPOSITORY, repo)
            or type(number) is not int or number < 1 or type(item) is not int or item < 1):
        raise ValueError('A repository, pull request, and comment ID are required.')
    kind = {EVENTS[0]: 'issues/comments', EVENTS[1]: 'pulls/comments',
            EVENTS[2]: f'pulls/{number}/reviews'}[event]
    route = f'repos/{repo.casefold()}/{kind}/{item}'
    now = now or dt.datetime.now(app.UTC)
    env = app.gh_env()
    login = app.gh_json(['api', 'user'], env)['login']
    with locked_state(login, now) as state:
        if 'https://api.github.com/' + route in dict(state['seen']):
            return False
    result = verified(route, repo, event, number, login, env, now)
    return commit([result] if result else [], login, now)


def read_notifications(route, env):
    """Read the provider interval without printing headers or response data."""
    result = subprocess.run(['gh', 'api', '--include', route], env=env,
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('GitHub comment notifications are unavailable. Check GitHub token access.')
    head, separator, body = result.stdout.replace('\r\n', '\n').partition('\n\n')
    if not separator:
        raise RuntimeError('GitHub returned an invalid notifications response.')
    headers = {}
    for line in head.splitlines()[1:]:
        key, colon, value = line.partition(':')
        if colon:
            headers[key.casefold()] = value.strip()
    interval = headers.get('x-poll-interval', '60')
    return json.loads(body), max(60, int(interval))


def poll(now=None, live=None):
    """Poll changed notification threads. A thread can combine several comments."""
    now = now or dt.datetime.now(app.UTC)
    env = app.gh_env()
    login = app.gh_json(['api', 'user'], env)['login']
    with locked_state(login, now) as state:
        if not state.get('initialized'):
            state['initialized'] = True
            return True
        if state.get('next_poll_at') and now < app.parse_stamp(state['next_poll_at']):
            return False
        snapshot = dict(state)
    since = app.parse_stamp(snapshot['checkpoint']) - dt.timedelta(days=1)
    tasks = {}
    interval = 60
    page = 1
    while True:
        query = urlencode({'all': 'true', 'since': app.stamp(since), 'per_page': 50, 'page': page})
        notifications, wait = read_notifications('notifications?' + query, env)
        interval = max(interval, wait)
        for notification in notifications:
            subject = notification.get('subject') or {}
            repo = (notification.get('repository') or {}).get('full_name')
            if subject.get('type') != 'PullRequest' or not isinstance(repo, str):
                continue
            number = pr_number(subject.get('url'), repo)
            parsed = parse_route(subject.get('latest_comment_url'))
            if not number or not parsed or parsed[0].casefold() != repo.casefold():
                continue
            _, event, route = parsed
            scope = (live or {}).get(event)
            if scope and app.live_covers(repo, scope):
                continue
            if 'https://api.github.com/' + route not in dict(snapshot['seen']):
                tasks[route] = (route, repo, event, number, login, env, now)
        if len(notifications) < 50:
            break
        page += 1
    with locked_state(login, now) as state:
        state['next_poll_at'] = app.stamp(now + dt.timedelta(seconds=interval))
    complete = True
    records = []
    with ThreadPoolExecutor(max_workers=4) as workers:
        futures = [workers.submit(verified, *args) for args in tasks.values()]
        for future in futures:
            try:
                record = future.result()
                if record:
                    records.append(record)
            except (OSError, RuntimeError, ValueError):
                complete = False
    commit(records, login, now, checkpoint=now if complete else None)
    return complete
