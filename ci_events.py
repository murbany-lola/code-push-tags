"""Confirm failed GitHub Actions runs caused by the current person's work."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import datetime as dt
import fcntl
import re
from urllib.parse import urlencode

import push_tags as app


def repository(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value):
        raise ValueError('A repository name is required.')
    return value


@contextmanager
def session(now):
    directory = app.state_dir()
    with (directory / 'ci.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        env = app.gh_env()
        login = app.gh_json(['api', 'user'], env)['login']
        path = directory / 'ci.json'
        state = app.read_json(path, None)
        fresh = state is None
        if fresh:
            state = {'login': login, 'started_at': app.stamp(now), 'seen': []}
            app.write_json(path, state)
        elif state['login'].lower() != login.lower():
            raise RuntimeError('GitHub account changed. Check the CI baseline.')
        yield env, login, state, fresh


def read_run(repo, run_id, attempt, env):
    return app.gh_json(['api', f'repos/{repo}/actions/runs/{run_id}/attempts/{attempt}'], env)


def read_pr(repo, number, env, cache):
    key = (repo, number)
    if key not in cache:
        cache[key] = app.gh_json(['api', f'repos/{repo}/pulls/{number}'], env)
    return cache[key]


def owns_pr(pr, login):
    return ((pr.get('user') or {}).get('login', '').casefold() == login.casefold()
            or (pr.get('merged') is True
                and (pr.get('merged_by') or {}).get('login', '').casefold() == login.casefold()))


def bot_source(repo, pr, login, env, cache):
    if (pr.get('user') or {}).get('type') != 'Bot':
        return False
    pattern = r'https://github\.com/' + re.escape(repo) + r'/(?:issues|pull)/(\d+)\b'
    for number in set(re.findall(pattern, pr.get('body') or '', re.IGNORECASE)):
        source = read_pr(repo, int(number), env, cache)
        if source.get('merged') is True and owns_pr(source, login):
            return True
    return False


def attribution(repo, run, login, env, cache=None):
    """Use exact GitHub actor, commit, and source-PR links."""
    for field in ('actor', 'triggering_actor'):
        if (run.get(field) or {}).get('login', '').casefold() == login.casefold():
            return field
    sha = run.get('head_sha')
    if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-fA-F]{40,64}', sha):
        return None
    cache = cache if cache is not None else {}
    candidates = {pr['number'] for pr in run.get('pull_requests', [])}
    page = 1
    while True:
        prs = app.gh_json(['api', f'repos/{repo}/commits/{sha}/pulls?per_page=100&page={page}'], env)
        candidates.update(pr['number'] for pr in prs)
        if len(prs) < 100:
            break
        page += 1

    def matches(pr):
        return ((pr.get('head') or {}).get('sha') == sha
                or (pr.get('merged') is True and pr.get('merge_commit_sha') == sha))

    found = [read_pr(repo, number, env, cache) for number in candidates]
    if not any(matches(pr) for pr in found) and run.get('head_branch'):
        owner = ((run.get('head_repository') or {}).get('owner') or {}).get('login') or repo.split('/')[0]
        page = 1
        while True:
            query = urlencode({'state': 'all', 'head': f"{owner}:{run['head_branch']}",
                               'per_page': 100, 'page': page})
            prs = app.gh_json(['api', f'repos/{repo}/pulls?{query}'], env)
            matching = [pr for pr in prs if matches(pr)]
            found.extend(read_pr(repo, pr['number'], env, cache) for pr in matching)
            if matching or len(prs) < 100:
                break
            page += 1
    for pr in found:
        if matches(pr):
            if owns_pr(pr, login):
                return 'pull_request'
            if bot_source(repo, pr, login, env, cache):
                return 'bot_source_pull_request'
    return None


def identity(repo, run):
    return f"https://api.github.com/repos/{repo}/actions/runs/{run['id']}/attempts/{run['run_attempt']}"


def record(repo, run, state, now):
    if run.get('status') != 'completed' or run.get('conclusion') not in ('failure', 'timed_out'):
        return False
    finished = app.parse_stamp(run['updated_at'])
    if not app.parse_stamp(state['started_at']) < finished <= now:
        return False
    key = identity(repo, run)
    seen = dict(state['seen'])
    if key in seen:
        return False
    seen[key] = run['updated_at']
    state['seen'] = sorted(seen.items(), key=lambda pair: pair[1])[-2000:]
    app.write_json(app.state_dir() / 'ci.json', state)
    import repo_preferences
    if repo_preferences.allowed(repo):
        app.notify('ci')
    return True


def consider(repo, run, login, env, state, now, cache=None):
    if run.get('status') != 'completed' or run.get('conclusion') not in ('failure', 'timed_out'):
        return False
    if not app.parse_stamp(state['started_at']) < app.parse_stamp(run['updated_at']) <= now:
        return False
    key = identity(repo, run)
    ignored = dict(state.get('ignored', []))
    if key in dict(state['seen']) or key in ignored:
        return False
    if attribution(repo, run, login, env, cache):
        return record(repo, run, state, now)
    ignored[key] = run['updated_at']
    state['ignored'] = sorted(ignored.items(), key=lambda pair: pair[1])[-2000:]
    app.write_json(app.state_dir() / 'ci.json', state)
    return False


def handle_event(payload, now=None):
    run = payload.get('workflow_run')
    if payload.get('action') != 'completed' or not isinstance(run, dict):
        return False
    repo = repository((payload.get('repository') or {}).get('full_name'))
    run_id, attempt = run.get('id'), run.get('run_attempt')
    if type(run_id) is not int or run_id < 1 or type(attempt) is not int or attempt < 1:
        raise ValueError('A workflow run and attempt are required.')
    if not app.config().get('ci_enabled', True):
        return False
    now = now or dt.datetime.now(app.UTC)
    with session(now) as (env, login, state, fresh):
        if fresh:
            return False
        detail = read_run(repo, run_id, attempt, env)
        return consider(repo, detail, login, env, state, now)


def open_heads(login, env):
    items = []
    page = 1
    while True:
        query = f'is:pr is:open author:{login}'
        result = app.gh_json(['api', '--method', 'GET', 'search/issues', '-f', f'q={query}',
                              '-f', 'per_page=100', '-f', f'page={page}'], env)
        if result.get('incomplete_results') or result.get('total_count', 0) > 1000:
            raise RuntimeError('GitHub pull request search is incomplete.')
        items.extend(result['items'])
        if len(result['items']) < 100:
            break
        page += 1

    def read(item):
        repo = repository(item['repository_url'].removeprefix('https://api.github.com/repos/'))
        pr = app.gh_json(['api', f"repos/{repo}/pulls/{item['number']}"], env)
        if pr.get('state') == 'open' and (pr.get('user') or {}).get('login', '').lower() == login.lower():
            return repo, pr['head']['sha']

    with ThreadPoolExecutor(max_workers=4) as workers:
        return set(head for head in workers.map(read, items) if head is not None)


def runs_for_head(head, env):
    repo, sha = head
    page = 1
    runs = []
    while True:
        result = app.gh_json(['api', f'repos/{repo}/actions/runs?head_sha={sha}&status=completed&per_page=100&page={page}'], env)
        runs.extend((repo, run) for run in result['workflow_runs'])
        if len(result['workflow_runs']) < 100:
            return runs
        page += 1


def recent_runs(repo, since, env):
    page = 1
    runs = []
    while True:
        query = urlencode({'status': 'completed', 'created': '>=' + app.stamp(since),
                           'per_page': 100, 'page': page})
        result = app.gh_json(['api', f'repos/{repo}/actions/runs?{query}'], env)
        runs.extend((repo, run) for run in result['workflow_runs'])
        if len(result['workflow_runs']) < 100:
            return runs
        page += 1


def relevant_repositories(heads):
    repos = {repo for repo, _ in heads}
    merges = app.read_json(app.state_dir() / 'merges.json', {})
    for url, _ in merges.get('seen', []):
        match = re.fullmatch(r'https://api\.github\.com/repos/([^/]+/[^/]+)/pulls/\d+', url)
        if match:
            repos.add(repository(match[1]))
    repos.update(repository(repo) for repo in app.config().get('repositories') or [])
    return repos


def poll(now=None):
    if not app.config().get('ci_enabled', True):
        return
    now = now or dt.datetime.now(app.UTC)
    with session(now) as (env, login, state, fresh):
        if fresh:
            return
        heads = open_heads(login, env)
        repos = relevant_repositories(heads)
        since = max(app.parse_stamp(state['started_at']),
                    app.parse_stamp(state.get('checkpoint', state['started_at'])) - dt.timedelta(days=1))
        with ThreadPoolExecutor(max_workers=4) as workers:
            batches = list(workers.map(lambda head: runs_for_head(head, env), heads))
            batches.extend(workers.map(lambda repo: recent_runs(repo, since, env), repos))
        seen = dict(state['seen'])
        seen.update(state.get('ignored', []))
        candidates = {(repo, run['id'], run['run_attempt']) for batch in batches for repo, run in batch
                      if run.get('conclusion') in ('failure', 'timed_out')
                      and app.parse_stamp(run['updated_at']) > app.parse_stamp(state['started_at'])
                      and identity(repo, run) not in seen}
        with ThreadPoolExecutor(max_workers=4) as workers:
            details = list(workers.map(lambda key: (key[0], read_run(*key, env)), candidates))
        cache = {}
        for repo, detail in details:
            consider(repo, detail, login, env, state, now, cache)
        state['checkpoint'] = app.stamp(now)
        app.write_json(app.state_dir() / 'ci.json', state)
