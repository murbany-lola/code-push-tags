# Updates and releases

## Current state

Version 0.2.0 is the new public preview with a DMG and ZIP in the [public releases](https://github.com/murbany-lola/code-push-tags/releases/latest). See `CFBundleVersion` in `macos/Info.plist` for the build number. No coworkers are enrolled automatically. Version 0.2.0 adds quiet app-update notices and a UI restart action. Automatic app-code installation is not implemented.

Decided by: person (Max). Test locally before sharing. Keep the repository in his personal GitHub account and make it public for downloads.

## Pilot update method

Use a versioned GitHub Release with the macOS DMG and ZIP attached. The release notes must state the supported architecture and known limits. Public downloads do not require an invitation. People can also build the app from source.

Version 0.1.0 uses this delivery method. Installation and automatic sounds remain optional.

## Prepare a release

1. Review the final code change.
2. Run the required checks for changed files.
3. Change `CFBundleShortVersionString` in `macos/Info.plist`.
4. Increase `CFBundleVersion` in that file.
5. Build the Apple Silicon app with `macos/build_app.py`.
6. Verify its signature and architecture.
7. Test previews, mute, repository selection, and close/reopen behavior.
8. Verify that the DMG and ZIP contain no private state or credentials.
9. Publish the DMG and ZIP to an approved GitHub Release.
10. Add the version, changes, limits, and rollback instructions to the release notes.

Follow the applicable build rules. The local prototype build was a specific user-approved exception. It does not change the normal CI rule.

Developer ID signing and notarization are recommended before a wider distribution. The current ad-hoc signature is for the local prototype.

## Install from a DMG

1. Download `Code-Push-Tags-macOS.dmg`.
2. Open the DMG.
3. Drag **Code Push Tags.app** to the **Applications** shortcut.
4. Eject the disk image.
5. Open the app from Applications.
6. Select **GitHub sign-in** to use your own account.
7. Select your repositories and sounds.
8. Select **Enable on this Mac** when you want automatic sounds.

Installation alone does not enable automatic sounds. The app supports Apple Silicon Macs with macOS 12 or later. It requires Python 3 and GitHub CLI. The current app has an ad-hoc signature. It is not Developer ID signed or notarized. macOS can block a downloaded copy.

The DMG contains the app and a shortcut to `/Applications`. The shortcut does not install the app automatically.

Decided by: person (Max). Supply a DMG for optional installation and retain the source option.

## Build from source

The source is public. Use your own GitHub credentials for event checks. Install Python 3, GitHub CLI, and the Xcode Command Line Tools before the build.

```sh
git clone https://github.com/murbany-lola/code-push-tags.git
cd code-push-tags
python3 macos/build_app.py --output dist/local-build
```

Use a new output folder for each build. The command creates `Code Push Tags.app`, `Code-Push-Tags-macOS.zip`, and `Code-Push-Tags-macOS.dmg`. Follow the DMG installation steps above. The source does not include Max's credentials or private settings.

## Install an update

1. Turn global mute on.
2. Quit Code Push Tags from its menu.
3. Download the new DMG or ZIP from the GitHub Release.
4. Open the DMG or extract the ZIP.
5. Replace the old app in the same Applications folder.
6. Open the updated app.
7. Select **Check setup**.
8. Confirm your sound and repository choices.
9. Open a new terminal if the release changes shell integration.
10. Turn sounds on when ready.

Keep the app at the same path. Installed launchd jobs and shell integration refer to that path. Preferences and Keychain credentials remain outside the app bundle.

An existing checkout-based installation continues to use that checkout. Updating the app alone does not update its runtime. Use `git pull --ff-only` in the checkout, or remove that installation before enabling the app's bundled copy.

## Roll back

1. Turn global mute on.
2. Quit the app.
3. Restore the previous app at the same path.
4. Open it.
5. Select **Check setup**.

Review release notes before rollback if a future release changes the configuration format. The prototype uses the existing JSON settings format and adds optional keys.

## Later work

- Add an Intel build and test it on Intel hardware or a suitable runner.
- Add Developer ID signing and notarization.
- Add repeatable macOS release builds in CI.
- Evaluate an in-app updater after signing and release delivery are established.
- Prepare a shared authenticated webhook service before a multi-person webhook rollout.

These items are not implemented by the current prototype.

## Shared audio updates

New audio does not require a new app bundle. Add the WAV and its manifest entry to the repository, then merge them to `main`. Users with repository access receive the update at the next library check. **Refresh Library** checks immediately. Offline users keep their previous complete library. See [sound library procedure](SOUNDS.md).

Merge library removals before sharing a new bundle that uses them. Library sync reads `main`, even when a local prototype was built from a feature branch.

## Quiet update notices

Version 0.2.0 checks the latest published GitHub release at startup and once per hour. **Check for Updates** starts a manual check. The app compares numeric version numbers and requires an uploaded DMG or ZIP before it shows the update notice.

The notice stays inside the app. It does not open a popup, take focus, or stop sound playback. **Download update** opens the validated release download after a click. The existing download-and-replace procedure still applies.

**Restart UI** starts a new UI process and closes the old UI process. The installed background watcher remains registered. Saved sound, mute, repository, and layout choices remain in place. A UI restart does not download or install app code.

Install version 0.2.0 manually once on Macs that still run version 0.1.0. Earlier versions cannot show the new notice. Audio-library updates remain separate from app-code updates.

Decided by: person (Max). Use a quiet update notice and preserve the background watcher during UI restarts. Apple Developer signing and notarization remain deferred at Max's request.
