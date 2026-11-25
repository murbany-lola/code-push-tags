#!/usr/bin/env python3
"""Build the macOS app from tracked runtime files."""
import argparse
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ('push_tags.py', 'install.py', 'shell.zsh', 'manifest.json', 'ci_events.py',
           'repo_preferences.py', 'sound_library.py', 'app_updates.py')
LOGO = 'macos/assets/code-push-tags-logo.png'


def build_icon(source, target, output):
    with tempfile.TemporaryDirectory(prefix='icon-', dir=output) as temporary:
        iconset = Path(temporary) / 'AppIcon.iconset'
        iconset.mkdir()
        for points in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                pixels = str(points * scale)
                suffix = '@2x' if scale == 2 else ''
                name = iconset / f'icon_{points}x{points}{suffix}.png'
                subprocess.run(['sips', '-z', pixels, pixels, str(source), '--out', str(name)],
                               check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['iconutil', '-c', 'icns', str(iconset), '-o', str(target)], check=True)


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    app = output / 'Code Push Tags.app'
    if app.exists():
        raise RuntimeError('The output app already exists. Choose a new output folder.')
    tracked = set(subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines())
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    files = list(RUNTIME) + [tag['file'] for tag in manifest['tags']]
    for name in files + [LOGO]:
        path = (ROOT / name).resolve()
        if name not in tracked or not path.is_relative_to(ROOT) or not path.is_file():
            raise RuntimeError(f'Required bundle file is not tracked: {name}')
    resources = app / 'Contents/Resources/kit'
    binary = app / 'Contents/MacOS/CodePushTags'
    binary.parent.mkdir(parents=True)
    resources.mkdir(parents=True)
    logo = resources.parent / 'logo.png'
    shutil.copy2(ROOT / LOGO, logo)
    build_icon(logo, resources.parent / 'AppIcon.icns', output)
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
                    str(ROOT / 'macos/CodePushTags.swift'), str(ROOT / 'macos/TransportArtwork.swift'),
                    str(ROOT / 'macos/LibraryItem.swift'), '-o', str(binary)], check=True)
    subprocess.run(['codesign', '--force', '--sign', '-', str(app)], check=True)
    archive = output / 'Code-Push-Tags-macOS.zip'
    subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(app), str(archive)], check=True)
    disk_image = output / 'Code-Push-Tags-macOS.dmg'
    with tempfile.TemporaryDirectory(prefix='dmg-', dir=output) as temporary:
        staging = Path(temporary)
        shutil.copytree(app, staging / app.name, symlinks=True)
        (staging / 'Applications').symlink_to('/Applications', target_is_directory=True)
        subprocess.run(['hdiutil', 'create', '-volname', 'Code Push Tags', '-srcfolder', str(staging),
                        '-fs', 'HFS+', '-format', 'UDZO', str(disk_image)], check=True)
    print(app)
    print(archive)
    print(disk_image)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    build(args.output.resolve())
