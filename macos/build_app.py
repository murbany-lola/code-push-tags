#!/usr/bin/env python3
"""Build the macOS app from tracked runtime files."""
import argparse
import json
from pathlib import Path
import plistlib
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ('push_tags.py', 'install.py', 'shell.zsh', 'manifest.json', 'ci_events.py', 'repo_preferences.py')


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    app = output / 'Code Push Tags.app'
    if app.exists():
        raise RuntimeError('The output app already exists. Choose a new output folder.')
    tracked = set(subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines())
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    files = list(RUNTIME) + [tag['file'] for tag in manifest['tags']]
    for name in files:
        path = (ROOT / name).resolve()
        if name not in tracked or not path.is_relative_to(ROOT) or not path.is_file():
            raise RuntimeError(f'Required runtime file is not tracked: {name}')
    resources = app / 'Contents/Resources/kit'
    binary = app / 'Contents/MacOS/CodePushTags'
    binary.parent.mkdir(parents=True)
    resources.mkdir(parents=True)
    for name in dict.fromkeys(files):
        target = resources / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    with (ROOT / 'macos/Info.plist').open('rb') as stream:
        info = plistlib.load(stream)
    with (app / 'Contents/Info.plist').open('wb') as stream:
        plistlib.dump(info, stream)
    subprocess.run(['xcrun', 'swiftc', '-swift-version', '5', '-O', '-framework', 'AppKit',
                    '-target', 'arm64-apple-macosx12.0',
                    str(ROOT / 'macos/CodePushTags.swift'), '-o', str(binary)], check=True)
    subprocess.run(['codesign', '--force', '--sign', '-', str(app)], check=True)
    archive = output / 'Code-Push-Tags-macOS.zip'
    subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(app), str(archive)], check=True)
    print(app)
    print(archive)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    build(args.output.resolve())
