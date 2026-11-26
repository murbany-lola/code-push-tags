# Fork and use Code Push Tags

**One time for the runtime.**

To use the app without code changes, start with [INSTALL.md](INSTALL.md). A fork is optional. Each person uses their own GitHub account and selects their own repositories.

The original code uses the [MIT license](LICENSE). All audio files are outside the code license. See [NOTICE.md](NOTICE.md) and [sound sources](SOUNDS.md).

## Get your own copy

Use macOS, zsh, Python 3.9 or later, Git, and GitHub CLI (`gh`). The app build also needs the Xcode Command Line Tools and an Apple Silicon Mac.

1. Sign in with your own GitHub account:

   ```sh
   gh auth login
   ```

2. Create a fork and clone it:

   ```sh
   gh repo fork murbany-lola/code-push-tags --clone
   ```

3. Open the cloned folder:

   ```sh
   cd code-push-tags
   ```

Keep this folder at the same path after terminal installation. The installed shell and watcher use this path.

## Use the terminal setup

If another copy is installed on this Mac, remove its setup first. Use **Remove setup** in that app, or run `python3 install.py uninstall` from its source folder. If you installed through a different shell file, use that same `--shell-file` option for removal. Open a new Terminal window after removal.

1. Check the required commands and account access:

   ```sh
   python3 push_tags.py doctor
   ```

2. List the clips:

   ```sh
   python3 push_tags.py list
   ```

3. Preview a clip:

   ```sh
   python3 push_tags.py play --event push
   ```

4. Select a repository:

   ```sh
   python3 repo_preferences.py set --verify-access --repo OWNER/REPO
   ```

   Replace `OWNER/REPO` with a repository that your account can access. Repeat `--repo` to select more repositories. See [terminal setup](TEAM_README.md) for organization selection.

5. Inspect the installation paths:

   ```sh
   python3 install.py plan
   ```

6. Install the local triggers:

   ```sh
   python3 install.py install
   ```

7. Open a new Terminal window.
8. Use `push-tags off` to mute all sounds.
9. Use `push-tags on` to turn sounds on.

The standard setup uses polling. It does not need webhook administration access. [Optional live setup](TEAM_README.md#optional-live-listener) has separate access requirements.

## Build your app

From the fork's source folder, run:

```sh
python3 macos/build_app.py --output dist/my-first-build
```

Use a new output folder for each build. The command creates the app, DMG, and ZIP. See [INSTALL.md](INSTALL.md) to install the app. Do not enable this app's setup while another copy's setup is installed.

The build accepts only tracked runtime files and sound files. Add new sound files to Git before a build. See [SOUNDS.md](SOUNDS.md) for manifest fields and source records.

## Use your own WAV library

**Lossless or GTFO.**

Put your uncompressed PCM WAV files in `audio/`. Add each file to `manifest.json`. Use a unique `id`, a display `text`, and a relative `file` path such as `audio/my-tag.wav`. Set `event` to `any`, `push`, `merge`, or `ci`. Use `additional_use_cases: ["comment"]` for the comment group. See SOUNDS.md for category fields.

Track each new file with `git add -f audio/my-tag.wav`. Keep IDs stable after release. The app copies the files without audio conversion.

Library sync currently reads a GitHub repository with this manifest. It does not import an arbitrary local folder or audio service. To publish your library, follow the source changes below.

## Publish updates from your fork

A new fork still gets shared audio and app update notices from `murbany-lola/code-push-tags`. You can keep these sources if you want the original library and releases.

For your own library and app releases, change these values before you publish:

| File | Value to change |
| --- | --- |
| `sound_library.py` | Set `SOURCE` to `repos/YOUR-ACCOUNT/YOUR-REPO`. Audio updates read its `main` branch. |
| `app_updates.py` | Set `REPOSITORY` to `YOUR-ACCOUNT/YOUR-REPO`. `ENDPOINT` is derived from this value. Release URL checks also use it. |
| `macos/Info.plist` | Set the app version and build number for your release. |
| `README.md` and installation documents | Change download and repository links to your fork. |

Commit and push your audio, manifest, and source changes to your fork's `main` branch. Then run:

```sh
python3 sound_library.py sync --force
```

This command uses the `SOURCE` in your checkout. It updates the local library from the published fork. Local sound edits do not replace a previously downloaded library until you publish and sync them.

Build the app from the changed source. Publish a stable GitHub release with a version tag such as `v0.1.0`. Upload one or both of these generated asset names:

- `Code-Push-Tags-macOS.dmg`
- `Code-Push-Tags-macOS.zip`

The app checks the latest stable release. Draft releases and prereleases do not produce update notices. The app does not install updates automatically. Use **Check for Updates** to check after you publish.

## Local settings and access

The original app and an unchanged fork use the same local settings folder, shell integration, LaunchAgent label, and app bundle identifier. They are alternative installations. They are not separate installations on one Mac.

Settings and event state are in `~/Library/Application Support/Code Push Tags/`. Removing setup keeps these files. Do not commit this private folder, logs, credentials, or webhook secrets to your fork.

A fork does not grant access to private repositories. GitHub access, selected repositories, sound choices, and global mute stay under each person's control. It does not enroll anyone else.
