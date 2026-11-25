#!/usr/bin/env python3
"""Select repositories and organizations for local sounds."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import fcntl
import json
import re
import subprocess
import sys
from urllib.parse import urlsplit
import urllib.request

import push_tags as app

REPOSITORY = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+')
ORGANIZATION = re.compile(r'[A-Za-z0-9_.-]+')


def valid_repository(value):
    return (isinstance(value, str) and REPOSITORY.fullmatch(value) is not None
            and all(part not in ('.', '..') for part in value.split('/')))


def get():
    settings = app.config()
    return {'repositories': settings.get('repositories'),
            'organizations': settings.get('organizations', [])}


def allowed(repo):
    preferences = get()
    if preferences['repositories'] is None:
        return True
    if not valid_repository(repo):
        return False
    repo = repo.casefold()
    return (repo in {name.casefold() for name in preferences['repositories']}
            or repo.split('/')[0] in {name.casefold() for name in preferences['organizations']})


def repository_name(remote_url):
    if not isinstance(remote_url, str):
        return None
    remote_url = remote_url.strip()
    if remote_url.startswith('git@github.com:'):
        path = remote_url[len('git@github.com:'):]
    else:
        parsed = urlsplit(remote_url)
        if parsed.scheme not in ('https', 'ssh') or parsed.hostname != 'github.com':
            return None
        if parsed.query or parsed.fragment:
            return None
        path = parsed.path.lstrip('/')
    path = path.rstrip('/')
    if path.endswith('.git'):
        path = path[:-4]
    return path if valid_repository(path) else None


def git_repository(git_args=None):
    args = list(git_args or [])
    prefix = []
    paired = {'-C', '-c', '--git-dir', '--work-tree', '--namespace', '--config-env'}
    switches = {'--no-pager', '--paginate', '-p', '-P', '--bare', '--no-replace-objects',
                '--literal-pathspecs', '--glob-pathspecs', '--noglob-pathspecs',
                '--icase-pathspecs', '--no-optional-locks', '--no-lazy-fetch'}
    while args:
        value = args.pop(0)
        if value in paired:
            if not args:
                return None
            prefix.extend((value, args.pop(0)))
        elif (value in switches or value.startswith(('--git-dir=', '--work-tree=',
              '--namespace=', '--config-env=', '--exec-path=', '--super-prefix='))
              or value.startswith(('-C', '-c'))):
            prefix.append(value)
        else:
            break
    try:
        result = subprocess.run(['git', *prefix, 'config', '--get', 'remote.origin.url'],
                                capture_output=True, text=True)
    except OSError:
        return None
    return repository_name(result.stdout) if result.returncode == 0 else None


def repositories():
    env = app.gh_env()
    found = {}
    page = 1
    while True:
        route = ('user/repos?per_page=100&sort=full_name'
                 '&affiliation=owner,collaborator,organization_member' + f'&page={page}')
        values = app.gh_json(['api', route], env)
        for repo in values:
            name = repo['full_name']
            found[name.casefold()] = {
                'full_name': name, 'private': bool(repo.get('private')),
                'organization': (repo.get('owner') or {}).get('type') == 'Organization',
            }
        if len(values) < 100:
            return sorted(found.values(), key=lambda repo: repo['full_name'].casefold())
        page += 1


def listener_status():
    status = {'target': None, 'events': [], 'connected': False,
              'reason': 'No connected listener on this Mac. Polling is available.'}
    try:
        saved = app.read_json(app.state_dir() / 'webhook-pilot.json', {})
        target = saved.get('target', '')
        flag, _, name = target.partition('=')
        if flag == '--repo' and valid_repository(name):
            route = f'repos/{name}/hooks'
        elif flag == '--org' and ORGANIZATION.fullmatch(name) and name not in ('.', '..'):
            route = f'orgs/{name}/hooks'
        else:
            return status
        if type(saved.get('id')) is not int or saved['id'] <= 0:
            return status
        status['target'] = target
        with (app.state_dir() / 'listener.lock').open('r') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)
                return status
        with urllib.request.urlopen('http://127.0.0.1:18769/health', timeout=2) as response:
            if response.status != 200:
                return status
        hook = app.gh_json(['api', f"{route}/{saved['id']}"], app.gh_env())
        if hook.get('active') is not True or hook.get('name') != 'cli':
            return status
        status.update(connected=True, events=hook.get('events', []),
                      reason='Connected listener verified on this Mac and GitHub.')
    except (OSError, RuntimeError, ValueError, TypeError, AttributeError):
        status['reason'] = 'Listener could not be verified. Polling is available.'
    return status


def connections():
    with ThreadPoolExecutor(max_workers=2) as workers:
        catalogue = workers.submit(repositories)
        listener = workers.submit(listener_status)
        values = catalogue.result()
        live = listener.result()
    found = {repo['full_name'].casefold(): dict(repo, access='confirmed') for repo in values}
    for name in get()['repositories'] or []:
        if name.casefold() not in found:
            found[name.casefold()] = {'full_name': name, 'private': False, 'organization': False,
                                      'access': 'unconfirmed'}
    flag, _, target = (live.get('target') or '').partition('=')
    events = live['events']
    for key, repo in found.items():
        covered = live['connected'] and (key == target.casefold() if flag == '--repo'
                                         else key.split('/')[0] == target.casefold())
        confirmed = repo['access'] == 'confirmed'
        repo['merge_live'] = bool(confirmed and covered and ('pull_request' in events or '*' in events))
        repo['ci_live'] = bool(confirmed and covered and ('workflow_run' in events or '*' in events))
        if not confirmed:
            repo.update(connection='unconfirmed', reason='Repository access could not be confirmed. Refresh or check GitHub sign-in.')
        elif repo['merge_live'] and repo['ci_live']:
            repo.update(connection='live', reason='Live merge and CI events; polling remains available.')
        elif repo['merge_live'] or repo['ci_live']:
            event = 'merge' if repo['merge_live'] else 'CI'
            repo.update(connection='partial', reason=f'Live {event} events; other events use polling.')
        else:
            reason = live['reason'] if covered or not live['connected'] else 'No connected listener covers this repository.'
            repo.update(connection='polling', reason=reason + ' Polling checks run every 60 seconds when setup is enabled.')
    return {'repositories': sorted(found.values(), key=lambda repo: repo['full_name'].casefold()),
            'checked_at': app.stamp(dt.datetime.now(app.UTC)), 'listener': live}


def verify_access(repos, orgs):
    values = repositories()
    accessible = {repo['full_name'].casefold() for repo in values}
    organizations = {repo['full_name'].split('/')[0].casefold() for repo in values if repo['organization']}
    if any(repo.casefold() not in accessible for repo in repos):
        raise ValueError('Repository access could not be confirmed. Refresh the list before saving.')
    if any(org.casefold() not in organizations for org in orgs):
        raise ValueError('No accessible repositories were found for a selected organization. Refresh before saving.')


def set_preferences(repos, orgs, all_repos=False, verify=False):
    if not all(valid_repository(repo) for repo in repos):
        raise ValueError('Use repository names in owner/name format.')
    if not all(ORGANIZATION.fullmatch(org) and org not in ('.', '..') for org in orgs):
        raise ValueError('Use organization names without a slash.')
    if verify:
        verify_access(repos, orgs)
    settings = app.config()
    settings['repositories'] = None if all_repos else sorted(set(repos), key=str.casefold)
    settings['organizations'] = [] if all_repos else sorted(set(orgs), key=str.casefold)
    app.write_json(app.state_dir() / 'config.json', settings)
    return get()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('list', 'organizations', 'get', 'connections'):
        commands.add_parser(command)
    setter = commands.add_parser('set')
    setter.add_argument('--verify-access', action='store_true')
    setter.add_argument('--repo', action='append', default=[])
    setter.add_argument('--org', action='append', default=[])
    setter.add_argument('--all', dest='all_repos', action='store_true')
    args = parser.parse_args()
    if args.command == 'list':
        value = repositories()
    elif args.command == 'organizations':
        value = sorted({repo['full_name'].split('/')[0] for repo in repositories()
                        if repo['organization']}, key=str.casefold)
    elif args.command == 'connections':
        value = connections()
    elif args.command == 'get':
        value = get()
    else:
        if args.all_repos and (args.repo or args.org):
            parser.error('--all cannot be combined with --repo or --org')
        value = set_preferences(args.repo, args.org, args.all_repos, verify=args.verify_access)
    print(json.dumps(value))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print(f'Code Push Tags: {error}', file=sys.stderr)
        sys.exit(1)
