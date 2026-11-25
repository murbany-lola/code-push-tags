#!/usr/bin/env python3
"""Select repositories and organizations for local sounds."""
import argparse
import json
import re
import subprocess
import sys
from urllib.parse import urlsplit

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


def set_preferences(repos, orgs, all_repos=False):
    if not all(valid_repository(repo) for repo in repos):
        raise ValueError('Use repository names in owner/name format.')
    if not all(ORGANIZATION.fullmatch(org) and org not in ('.', '..') for org in orgs):
        raise ValueError('Use organization names without a slash.')
    settings = app.config()
    settings['repositories'] = None if all_repos else sorted(set(repos), key=str.casefold)
    settings['organizations'] = [] if all_repos else sorted(set(orgs), key=str.casefold)
    app.write_json(app.state_dir() / 'config.json', settings)
    return get()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('list', 'organizations', 'get'):
        commands.add_parser(command)
    setter = commands.add_parser('set')
    setter.add_argument('--repo', action='append', default=[])
    setter.add_argument('--org', action='append', default=[])
    setter.add_argument('--all', dest='all_repos', action='store_true')
    args = parser.parse_args()
    if args.command == 'list':
        value = repositories()
    elif args.command == 'organizations':
        value = sorted({repo['full_name'].split('/')[0] for repo in repositories()
                        if repo['organization']}, key=str.casefold)
    elif args.command == 'get':
        value = get()
    else:
        if args.all_repos and (args.repo or args.org):
            parser.error('--all cannot be combined with --repo or --org')
        value = set_preferences(args.repo, args.org, args.all_repos)
    print(json.dumps(value))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print(f'Code Push Tags: {error}', file=sys.stderr)
        sys.exit(1)
