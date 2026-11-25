# Updates and releases

## Current state

The app is a private local prototype, version 0.1.0 build 2. No public release or coworker invitation was made for this test. Automatic app updates are not implemented.

Decided by: person (Max). Test locally before sharing the app with friends or coworkers. Keep the repository in Max's personal GitHub account.

## Pilot update method

Use a versioned private GitHub Release with the macOS ZIP attached. Give repository access only to people who want to join. The release notes must state the supported architecture and known limits.

This method is the proposed pilot delivery path. A release has not been published yet.

## Prepare a release

1. Review the final code change.
2. Run the required checks for changed files.
3. Change `CFBundleShortVersionString` in `macos/Info.plist`.
4. Increase `CFBundleVersion` in that file.
5. Build the Apple Silicon app with `macos/build_app.py`.
6. Verify its signature and architecture.
7. Test previews, mute, repository selection, and close/reopen behavior.
8. Verify that the ZIP contains no private state or credentials.
9. Publish the ZIP to an approved private GitHub Release.
10. Add the version, changes, limits, and rollback instructions to the release notes.

Follow the applicable build rules. The local prototype build was a specific user-approved exception. It does not change the normal CI rule.

Developer ID signing and notarization are recommended before a wider distribution. The current ad-hoc signature is for the local prototype.

## Install an update

1. Turn global mute on.
2. Quit Code Push Tags from its menu.
3. Download the new ZIP from the private GitHub Release.
4. Extract the app.
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
