#!/usr/bin/env python3
"""Get shared WAV files and keep a complete local copy."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
from pathlib import Path
import re
import shutil
import tempfile
import time
import wave

SOURCE = 'repos/murbany-lola/code-push-tags'
INTERVAL = 3600
REVISION = re.compile(r'[0-9a-f]{40}')
AUDIO_PATH = re.compile(r'audio/[A-Za-z0-9_.-]+\.wav')


def app_module():
    import push_tags
    return push_tags


def validate_manifest(value):
    if not isinstance(value, dict) or not isinstance(value.get('tags'), list) or not value['tags']:
        raise ValueError('The sound manifest has no tags.')
    ids = set()
    for tag in value['tags']:
        if (not isinstance(tag, dict) or not isinstance(tag.get('id'), str) or not tag['id']
                or tag['id'] in ids or not isinstance(tag.get('text'), str)
                or not isinstance(tag.get('file'), str) or not AUDIO_PATH.fullmatch(tag['file'])
                or tag.get('event') not in (None, 'any', 'push', 'merge', 'ci')):
            raise ValueError('The sound manifest has an invalid tag.')
        cases = tag.get('use_cases')
        if cases is not None and (not isinstance(cases, list)
                                  or any(item not in ('push', 'merge', 'ci') for item in cases)):
            raise ValueError('The sound manifest has an invalid category.')
        extra = tag.get('additional_use_cases')
        if extra is not None and (not isinstance(extra, list) or any(not isinstance(item, str) for item in extra)):
            raise ValueError('The sound manifest has an invalid additional category.')
        ids.add(tag['id'])
    return value


def current_root(bundled_root):
    app = app_module()
    try:
        pointer = app.read_json(app.state_dir() / 'library-current.json', {})
        revision = pointer.get('revision', '')
        if not isinstance(revision, str) or not REVISION.fullmatch(revision):
            return Path(bundled_root)
        root = app.state_dir() / 'library' / revision
        manifest = validate_manifest(json.loads((root / 'manifest.json').read_text()))
        if all((root / tag['file']).is_file() for tag in manifest['tags']):
            return root
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return Path(bundled_root)


def content(path, revision, env):
    app = app_module()
    result = app.gh_json(['api', f'{SOURCE}/contents/{path}?ref={revision}'], env)
    if result.get('encoding') == 'none' and result.get('sha'):
        result = app.gh_json(['api', f"{SOURCE}/git/blobs/{result['sha']}"], env)
    if result.get('encoding') != 'base64' or not isinstance(result.get('content'), str):
        raise ValueError('The shared file response has no content.')
    return base64.b64decode(''.join(result['content'].split()), validate=True)


def result(updated=False, error=None):
    app = app_module()
    root = current_root(app.ROOT)
    value = {'root': str(root.resolve()), 'revision': root.name if REVISION.fullmatch(root.name) else None,
             'updated': updated}
    if error:
        value['error'] = error
    return value


def sync(force=False):
    app = app_module()
    state = app.state_dir()
    with (state / 'library.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return result()
        check = state / 'library-check.json'
        try:
            previous = app.read_json(check, {})
            if not force and time.time() - previous.get('checked_at', 0) < INTERVAL:
                return result(error=previous.get('error'))
        except (ValueError, TypeError, AttributeError):
            pass
        checked_at = time.time()
        app.write_json(check, {'checked_at': checked_at})
        staging = None
        try:
            env = app.gh_env()
            revision = app.gh_json(['api', f'{SOURCE}/commits/main'], env)['sha']
            if not isinstance(revision, str) or not REVISION.fullmatch(revision):
                raise ValueError('The shared revision is invalid.')
            before = current_root(app.ROOT)
            cache = state / 'library'
            cache.mkdir(exist_ok=True)
            destination = cache / revision
            if before == destination:
                return result()
            if not destination.exists():
                manifest = validate_manifest(json.loads(content('manifest.json', revision, env)))
                staging = Path(tempfile.mkdtemp(prefix='.download-', dir=cache))
                (staging / 'audio').mkdir()

                def download(path):
                    target = staging / path
                    target.write_bytes(content(path, revision, env))
                    with wave.open(str(target), 'rb') as audio:
                        if audio.getnframes() < 1:
                            raise ValueError('The shared WAV file is empty.')
                        size = audio.getnframes() * audio.getnchannels() * audio.getsampwidth()
                        if len(audio.readframes(audio.getnframes())) != size:
                            raise ValueError('The shared WAV file is incomplete.')

                with ThreadPoolExecutor(max_workers=4) as workers:
                    list(workers.map(download, sorted({tag['file'] for tag in manifest['tags']})))
                (staging / 'manifest.json').write_text(json.dumps(manifest))
                staging.rename(destination)
                staging = None
            manifest = validate_manifest(json.loads((destination / 'manifest.json').read_text()))
            if not all((destination / tag['file']).is_file() for tag in manifest['tags']):
                raise ValueError('The local library is incomplete.')
            app.write_json(state / 'library-current.json', {'revision': revision})
            return result(updated=True)
        except (OSError, RuntimeError, ValueError, TypeError, KeyError, AttributeError, wave.Error, EOFError):
            error = 'Library sync failed. Check GitHub access or the shared sound files. Local sounds remain available.'
            app.write_json(check, {'checked_at': checked_at, 'error': error})
            return result(error=error)
        finally:
            if staging is not None:
                shutil.rmtree(staging)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['sync'])
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    print(json.dumps(sync(force=args.force)))
