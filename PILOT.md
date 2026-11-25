# Mac app pilot

## Current state

The source is on `main` in Max's personal repository. Max approved public source and downloads. [Version 0.1.0](https://github.com/murbany-lola/code-push-tags/releases/tag/v0.1.0) is published with a DMG and ZIP.

The installed local app is `~/Applications/Code Push Tags.app`, version 0.1.0, build 9. It targets Apple Silicon and macOS 12 or later. Intel support and automatic app-code updates are deferred. Shared audio updates are implemented.

Max remains the pilot user. No coworker invitations or automatic enrollment were performed. People can download the public app and choose whether to enable setup. See [INSTALL.md](INSTALL.md).

The existing checkout-based polling watcher remains installed on Max's Mac. The native app uses the same local preferences. Opening the app does not replace that installation.

## Current behavior

The app has saved DJ and boombox layouts. Its library has Push, Merge, and Failure groups. Items look like record sleeves or cassette cases. Double-click an item to preview it. A single click does not play or highlight it. Card outlines are removed. CUE plays the assigned sound on one click.

Every clip remains available for every event. A new preview stops the previous preview. Master mute stops the preview and suppresses event sounds.

People can select repositories, organizations, all accessible repositories, or none. Repository and organization selections form a union. The app confirms access before saving a selection. Each person's GitHub account controls private repository access. Previewing does not depend on repository selection.

CI/CD attribution uses verified GitHub actors, exact owned PR head or merge commits, and one verified source-PR link from a bot-created follow-up PR. Shared branch history and nearby timestamps do not establish attribution. Failed and timed-out Actions runs can alert once per run attempt. Cancelled runs do not.

Polling and signed webhook deliveries share saved event state. Muted and excluded events are recorded without replay.

## Connections

Normal setup uses polling once per minute. The app can use an existing verified listener on that Mac. Normal installation does not create a webhook.

Max approved a temporary organization test listener for his Mac. The receiver uses `127.0.0.1:18769` through GitHub's authenticated test-forwarding service. The listener subscribes to `pull_request` and `workflow_run`. It does not restart automatically after a Mac reboot. Polling remains the fallback.

A read-only check on November 25, 2026 confirmed access to 29 repositories for Max's account. Of those repositories, 28 had live merge and CI coverage and one used polling. These counts describe that check, not other accounts.

GitHub's test forwarding is for development and testing. Only one forwarding connection can use a target at a time. A shared webhook service remains future work before a multi-person webhook rollout.

## Shared sounds

The app and enabled watcher check this repository's `main` branch for audio updates once per hour. The app also checks at startup. Refresh Library checks immediately. A complete local copy remains available offline.

The published bundle has 10 clips. The original Wheezy clip is removed from `main`; Branch outta here remains. A post-merge refresh verified the 10-clip shared library.

Third-party audio sources and permission limits remain in [SOUNDS.md](SOUNDS.md). Public repository access does not grant rights to third-party recordings or voices.

## Key choices

Decided by: person (Max). Keep the project in his personal GitHub account and make it public for downloads.

Decided by: person (Max). Supply a DMG, ZIP, and source build option. Installation and automatic sounds remain optional.

Decided by: person (Max). Use native DJ and boombox layouts, local previews, event choices, global mute, and repository or organization selection.

Decided by: person (Max). Use double-click previews. Remove single-click highlighting and sound-card outlines.

Decided by: person (Max). Keep shared audio updates separate from app-code updates. Confirm repository access. Use existing connected listeners with polling as the fallback.

Decided by: person (Max). Test locally before sharing. Build for Apple Silicon first and add Intel later. The approved local build exception applies to this personal app.

Decided by: person (Max). Use the LEGO break-apart recording and label it "LEGO death". Exclude the Yoda scream and original Wheezy clip. Retain Branch outta here.

Decided by: person (Max). Use the original Terio voice and a shorter tag. The agent selected the 2.3-second ending after showing both cuts.

## Validation and limits

Focused tests passed for push and merge behavior, CI attribution, repository preferences, connection status, shared-library updates, receiver handling, listener lifecycle, and global mute. [REVIEW.md](REVIEW.md) records results and limits.

Native checks covered both layouts, grouped sound lists, preview replacement, double-click playback, silent single clicks, global mute, repository refresh, Cancel, and window close/reopen. The final single-click screenshot showed no card outline.

The final DMG mounted read-only. It contained the app and Applications shortcut. Its app signature passed. The bundle contained 10 sound clips, the shared-library helper, and no bytecode cache. The image was ejected.

The app requires Python 3.9 or later and GitHub CLI. It has an ad-hoc signature. It is not Developer ID signed or notarized. macOS can block a downloaded copy.

No new failing deployment was triggered for testing. Real merge delivery and duplicate handling were checked. A signed replay of a failed Actions run used isolated local state and API verification.

The downstream polling scan uses a one-day checkpoint overlap. It discovers repositories from open PRs, saved own merges, and explicit repository selections.

See [app controls](MAC_APP.md), [updates](UPDATES.md), and [sound sources](SOUNDS.md).
