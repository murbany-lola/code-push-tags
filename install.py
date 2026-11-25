#!/usr/bin/env python3
"""Install or remove the reviewed local shell and launchd integration."""
import argparse
import datetime
import os
from pathlib import Path
import plistlib
import re
import shlex
import shutil
import subprocess
import sys

from push_tags import ROOT, config, state_dir, write_json

LABEL = 'local.code-push-tags.merges'
BEGIN = '# BEGIN Code Push Tags'
END = '# END Code Push Tags'


def shell_text(path):
    return path.read_text() if path.exists() else ''


def strip_block(text):
    return re.sub(r'(?m)^# BEGIN Code Push Tags\n.*?^# END Code Push Tags\n?', '', text, flags=re.S)


def backup(path):
    if path.exists():
        name = path.with_name(path.name + '.push-tags-backup-' + datetime.datetime.now().strftime('%Y%m%d%H%M%S%f'))
        shutil.copy2(path, name)
        print(f'Backup: {name}')


def install_shell(path):
    text = shell_text(path)
    clean = strip_block(text)
    if re.search(r'(?m)^\s*(?:function\s+git\b|git\s*\(\s*\)|alias\s+git=)', clean):
        raise RuntimeError(f'An existing git function or alias is in {path}. Resolve it before installation.')
    # Check the active startup files before the first installation.
    if BEGIN not in text:
        check = subprocess.run(['zsh', '-ic', 'whence -w git'], capture_output=True, text=True)
        if 'git: function' in check.stdout or 'git: alias' in check.stdout:
            raise RuntimeError('An existing git function or alias prevents installation.')
    block = f'{BEGIN}\nsource {shlex.quote(str(ROOT / "shell.zsh"))}\n{END}\n'
    backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(clean.rstrip('\n') + '\n' + block)
    print(f'Shell integration: {path}')


def launch_path():
    return Path.home() / 'Library/LaunchAgents' / f'{LABEL}.plist'


def launch_config():
    gh = shutil.which('gh')
    if not gh:
        raise RuntimeError('gh is missing from PATH.')
    path = ':'.join(dict.fromkeys([str(Path(sys.executable).resolve().parent), str(Path(gh).parent),
                                  '/opt/homebrew/bin', '/usr/local/bin', '/usr/bin', '/bin', '/usr/sbin', '/sbin']))
    return {'Label': LABEL, 'ProgramArguments': [str(Path(sys.executable).resolve()), str(ROOT / 'push_tags.py'), 'poll'],
            'StartInterval': 60, 'RunAtLoad': True,
            'EnvironmentVariables': {'PATH': path},
            'StandardOutPath': str(state_dir() / 'watcher.log'),
            'StandardErrorPath': str(state_dir() / 'watcher.log')}


def launchctl(*args, check=True):
    subprocess.run(['launchctl', *args], check=check)


def install_watcher():
    path = launch_path()
    document = launch_config()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup(path)
        launchctl('bootout', f'gui/{os.getuid()}', str(path), check=False)
    with path.open('wb') as stream:
        plistlib.dump(document, stream)
    path.chmod(0o600)
    launchctl('bootstrap', f'gui/{os.getuid()}', str(path))
    print(f'Merge watcher: {path}')


def uninstall(path):
    if path.exists():
        text = shell_text(path)
        if BEGIN in text:
            backup(path)
            path.write_text(strip_block(text))
    watcher = launch_path()
    if watcher.exists():
        launchctl('bootout', f'gui/{os.getuid()}', str(watcher), check=False)
        watcher.unlink()
    print('Integration removed. Open a new shell. Audio and private state remain.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install', 'uninstall', 'plan'])
    parser.add_argument('--shell-file', type=Path, default=Path.home() / '.zshrc')
    parser.add_argument('--no-shell', action='store_true')
    parser.add_argument('--no-watcher', action='store_true')
    parser.add_argument('--keychain-service')
    parser.add_argument('--keychain-account')
    args = parser.parse_args()
    if args.command == 'plan':
        print(f'Kit: {ROOT}\nShell file: {args.shell_file}\nWatcher: {launch_path()}')
        print('No changes were made.')
        return
    if args.command == 'uninstall':
        uninstall(args.shell_file)
        return
    if args.keychain_account and not args.keychain_service:
        parser.error('--keychain-account requires --keychain-service')
    if args.keychain_service:
        settings = config()
        settings['auth'] = {'keychain_service': args.keychain_service, 'keychain_account': args.keychain_account}
        write_json(state_dir() / 'config.json', settings)
    if not args.no_shell:
        install_shell(args.shell_file)
    if not args.no_watcher:
        install_watcher()


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Code Push Tags: {error}', file=sys.stderr)
        sys.exit(1)
