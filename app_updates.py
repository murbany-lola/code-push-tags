#!/usr/bin/env python3
"""Check for a published app update without changing the app."""
import argparse
import datetime as dt
import json
import re
import time
import urllib.request
from urllib.parse import urlsplit

import push_tags as app

REPOSITORY = 'murbany-lola/code-push-tags'
ENDPOINT = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
INTERVAL = 3600
VERSION = re.compile(r'v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')


def version(value):
    match = VERSION.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise ValueError('The version must contain three numbers.')
    return tuple(int(part) for part in match.groups())


def github_url(value, path):
    if not isinstance(value, str):
        return False
    url = urlsplit(value)
    return (url.scheme == 'https' and url.netloc == 'github.com' and url.path == path
            and not url.query and not url.fragment)


def release_info(data):
    if not isinstance(data, dict) or data.get('draft') is not False or data.get('prerelease') is not False:
        raise ValueError('The release is not a stable published release.')
    tag = data.get('tag_name')
    numbers = version(tag)
    if not data.get('published_at') or not github_url(data.get('html_url'), f'/{REPOSITORY}/releases/tag/{tag}'):
        raise ValueError('The release address is invalid.')
    assets = data.get('assets')
    if not isinstance(assets, list):
        raise ValueError('The release has no app download.')
    for name in ('Code-Push-Tags-macOS.dmg', 'Code-Push-Tags-macOS.zip'):
        for asset in assets:
            if (isinstance(asset, dict) and asset.get('name') == name and asset.get('state') == 'uploaded'
                    and github_url(asset.get('browser_download_url'), f'/{REPOSITORY}/releases/download/{tag}/{name}')):
                return {'latest_version': '.'.join(map(str, numbers)), 'download_url': asset['browser_download_url'],
                        'release_url': data['html_url']}
    raise ValueError('The release has no app download.')


def fetch_release():
    request = urllib.request.Request(ENDPOINT, headers={'Accept': 'application/vnd.github+json',
                                                      'User-Agent': 'Code-Push-Tags'})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def check(current, force=False):
    now = time.time()
    result = {'current_version': current, 'latest_version': None, 'update_available': False,
              'download_url': None, 'release_url': None,
              'checked_at': app.stamp(dt.datetime.fromtimestamp(now, app.UTC))}
    try:
        installed = version(current)
    except ValueError:
        return dict(result, error='The installed app version could not be read.')
    path = app.state_dir() / 'app-update-check.json'
    try:
        cache = app.read_json(path, {})
        checked_at = float(cache.get('checked_at', 0))
        release = cache.get('release')
        error = cache.get('error')
    except (OSError, ValueError, TypeError, AttributeError):
        checked_at, release, error = 0, None, None
    if force or now - checked_at >= INTERVAL:
        checked_at = now
        try:
            release = fetch_release()
            release_info(release)
            error = None
        except (OSError, RuntimeError):
            error = 'Update check failed. Check your network connection.'
        except (ValueError, TypeError, KeyError):
            release = None
            error = 'No supported published app release was found.'
        try:
            app.write_json(path, {'checked_at': checked_at, 'release': release, 'error': error})
        except OSError:
            error = 'The update check could not be saved.'
    result['checked_at'] = app.stamp(dt.datetime.fromtimestamp(checked_at, app.UTC))
    try:
        info = release_info(release)
        result.update(info, update_available=version(info['latest_version']) > installed)
    except (ValueError, TypeError, KeyError):
        pass
    if error:
        result['error'] = error
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check'])
    parser.add_argument('--current', required=True)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    print(json.dumps(check(args.current, force=args.force)))
