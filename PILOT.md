# Private Mac prototype

## Current state

The source is on `feat/macos-app-ci-sounds` in Max's private personal repository. The installed local prototype is `~/Applications/Code Push Tags.app`. Version 0.1.0, build 2 targets Apple Silicon and macOS 12 or later.

Max remains the pilot user. No invitations or release publication were performed by this agent. Intel support and automatic updates are deferred.

The existing checkout-based polling watcher remains installed. The native app uses the same local preferences. Opening the app does not replace that installation.

## Current behavior

The app has Push and Merge decks, a center master strip, and sample pads. Use-case groups help people browse. Every clip remains available for every event. A new preview stops the previous preview. Master mute stops the preview and suppresses all event sounds.

People can select individual repositories, whole organizations, all accessible repositories, or none. Repository and organization selections form a union. Their GitHub account still controls private access. Previewing does not depend on repository selection.

CI/CD attribution uses verified GitHub actors, exact owned PR head or merge commits, and one verified source-PR link from a bot-created follow-up PR. Shared branch history and nearby timestamps do not establish attribution. Failed and timed-out Actions runs can alert once per run attempt. Cancelled runs do not.

Polling and signed webhook deliveries share saved event state. Muted and excluded events are recorded without replay.

## Live connection

Max approved a temporary Lola Labs organization test hook. The current saved hook ID is `716801373`. It subscribes to `pull_request` and `workflow_run`. The receiver listens on `127.0.0.1:18769` through GitHub's authenticated test-forwarding service.

The previous test relay disconnected and its hook disappeared. Cleanup now accepts an exact HTTP 404 as an already-removed hook. Other errors preserve saved identity. The current connection is active. Polling remains the fallback.

The listener is a running pilot process. It does not restart automatically after a Mac reboot. GitHub documents test forwarding for development and testing and permits one connection per target.

## Key choices

Decided by: person (Max). Keep the project in his private personal GitHub repository. Coworkers can opt in later.

Decided by: person (Max). Use a small native app with local previews, event choices, one global mute, and repo or org selection.

Decided by: person (Max). Test locally before sharing. Build for Apple Silicon now and add Intel later.

Decided by: person (Max). Use a DJ-table layout with two decks and sample pads. Remove the gun graphic. New previews stop earlier previews.

Decided by: person (Max). Use the LEGO break-apart recording and label it "LEGO death". The Yoda scream is excluded from the app.

Decided by: person (Max). Use the original Terio voice and a shorter tag. The current 2.3-second ending cut was selected by the agent after showing both cuts.

Decided by: person (Max). Expand CI alerts to downstream workflows and bot-created follow-up PRs caused by his work.

Decided by: person (Max). Approve the temporary organization-hook exception after the infrastructure rule and exact scope were explained.

Decided by: person (Max). Approve the targeted local prototype build and UI checks. Normal build rules remain in effect elsewhere.

Decided by: agent. Propose versioned private GitHub Releases for manual pilot updates. No release or automatic updater was created.

## Validation

Focused unit tests passed for CI attribution, repo preferences, event filters, existing push/merge behavior, receiver handling, listener lifecycle, and global mute. The final record is in REVIEW.md.

A real personal-repository squash merge reached the receiver while polling was paused. A second signed delivery did not play again. Polling was restored. The temporary branch and test hook were removed.

A signed local replay used a real failed Actions run and API verification. It recorded one event and rejected the duplicate. The replay used isolated saved state and the current sound choice.

Read-only checks traced three real release-chain runs through backend bot PR #1165 to Max's merged source PR #1116. Those runs succeeded, so they validate attribution rather than failure playback. An unrelated failed bot run was not attributed to Max.

The wiki freshness check could not validate all delivery dependencies. Current workflow YAML was fetched directly before those checks.

The app was built and opened locally. Close/reopen, Cancel, repo refresh, preview replacement, and global mute were exercised. Signature checks passed after UI use. The bundle has only the allowlisted runtime and 11 sound files. Python bytecode writes are disabled for app, shell, and installed watcher commands.

## Known limits

The app requires Python 3.9 or later and GitHub CLI. It has an ad-hoc local signature, not Developer ID signing or notarization.

The downstream polling scan uses a one-day checkpoint overlap. It discovers repos from open PRs, saved own merges, and explicit repo selections. Webhook coverage is currently the one-person Lola Labs test connection.

No new failing deployment was triggered for testing. A shared authenticated webhook service is future work before a multi-person webhook rollout.

See MAC_APP.md for controls, UPDATES.md for update procedures, and SOUNDS.md for recordings and use-case metadata.
