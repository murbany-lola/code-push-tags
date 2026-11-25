# Pilot review

The review covered the push wrapper, merge watcher, installer, and tests. The pilot package contains one approved clip. Downloaded source clips and rejected demos remain local.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 718 | 488 |
| Test net LOC | 199 | 258 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 32 | 7 |

The before values are from the initial review gate. The after values are from the staged pilot files. Audio files are binary assets.

- reuse-hunter: pass; no findings.
- loc-minimizer: pass; no required changes.
- path-correctness: major; duplicate merge sounds from different GitHub IDs for one pull request. Applied: use the pull request API URL as the saved identity. The regression test covers both sources and the next poll. Round 2 passed.

Validation: 21 unit tests passed. Shell syntax checks passed in the implementation review. The approved clip is a 3.24-second PCM WAV file. Max approved its sound.

Limits: no real push or merge was made for testing. Merge detection can be delayed by GitHub. The documentation uses short, direct instructions; a complete ASD-STE100 dictionary check was not performed.

## Saved merge clips

Two approved WAV files were added through the existing manifest. The active settings were not changed.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 14 | 14 |
| Test net LOC | 0 | 0 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 2 | 2 |

reuse-hunter: pass; no findings. The manifest IDs are unique. All three WAV files decode. The CLI lists all three tags. The runtime code was not changed.

## Wheezy merge clip

The original Wheezy clip uses the existing manifest and selection command. All saved clips remain. The local merge selection is `wheezy-outta-here`.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 7 | 7 |
| Test net LOC | 0 | 0 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 1 | 1 |

reuse-hunter: pass; no findings. All four WAV files decode. The manifest IDs are unique. The local push selection remains `stackaholics`.

## Branch parody selection

Max selected "Branch outta here!" as the merge sound. It uses the existing manifest and configuration.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 7 | 7 |
| Test net LOC | 0 | 0 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 1 | 1 |

reuse-hunter: pass; no findings. The WAV file decodes. The local merge selection is `branch-outta-here`. The push selection remains `stackaholics`.

## Webhook pilot and global mute

The pilot adds an authenticated GitHub forwarding connection and a signed loopback receiver. The existing polling state prevents duplicate playback. Global on/off commands use the existing mute setting.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 262 | 276 |
| Test net LOC | 379 | 430 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 2 | 2 |

- reuse-hunter: pass; no findings.
- loc-minimizer: minor; unused import. Applied: removed the import.
- path-correctness: major; second start removed an active hook. Applied: hold a listener lock before hook cleanup. Round 2 passed.
- release-safety: major; same active-hook deletion. Applied through the same lock change. Round 2 passed.

Validation: 17 receiver tests, 13 listener tests, and 2 global mute tests passed. Python and shell syntax checks passed. Tests use controlled time. A real personal-repository squash merge reached the receiver with polling paused. A second signed delivery returned `recorded: false`. Polling was restored. The temporary target branch and test hook were removed. No Lola Labs hook was changed.

The gate reported four secret-related source lines. These lines read an environment secret or construct Keychain commands. No secret values were added to the repository.

The webhook forwarding service is for development and testing. It supports one forwarding session per target. Coworker rollout remains outside this one-person pilot. Max later approved the temporary organization-hook exception. The connection is active; see PILOT.md.

## Another one option

The optional DJ Khaled clip uses the existing manifest, player, and selection commands. The active push and merge settings remain unchanged.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 7 | 7 |
| Test net LOC | 0 | 0 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 1 | 1 |

reuse-hunter: pass; no findings. The manifest ID is unique. The WAV decodes and lasts 0.83 seconds. No runtime code changed.

## Native DJ prototype, repo selection, and CI/CD alerts

The native app reuses the existing settings and notification tools. It adds a DJ-table layout, local sample pads, use-case groups, one preview player, repo/org selection, and one master mute.

CI/CD alerts use verified actor, exact PR commit, or explicit bot source-PR attribution. Polling and signed webhook deliveries share event identities.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 917 | 1461 |
| Test net LOC | 430 | 578 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 10 | 10 |

The before values cover the initial native prototype. The after values cover the final requested DJ layout and expanded CI/CD attribution. Incremental review used private snapshots `dab9be9` and `cb6c194`; those snapshots are not part of the branch history.

- reuse-hunter: pass; no findings. Incremental review passed.
- loc-minimizer: pass; no required cuts. Incremental review passed.
- path-correctness: major; fresh install did not save the displayed defaults. Applied: save all choices before installation. Round 2 passed. Incremental review passed.

Local feedback fixes: Dock reopen, Cancel restoring the controller, one-request repo refresh with preserved search/checks, preview replacement, and global mute. Runtime subprocesses disable bytecode writes after a real package signature failure.

A real expired test hook returned HTTP 404 and blocked restart. Applied: accept an exact HTTP 404 as already removed. Other errors preserve hook identity. Fifteen listener tests passed, including this regression.

Validation: 105 focused unit tests passed across the changed runtime paths. Swift typecheck, Python syntax, shell syntax, and plist checks passed. Max approved the targeted local build and UI tests.

The Apple Silicon app was built and opened. Manual checks exercised preview replacement, master mute and restore, Cancel without minimizing, repo refresh, window reopen, and selection persistence. Signature checks passed after runtime use. The bundle contains 6 allowlisted runtime files and 11 sound files, with no private settings, credentials, or recording caches.

Provider checks used the pilot credential from Keychain. A signed isolated local replay verified a real failed run through GitHub and suppressed the duplicate. Real successful release-chain runs validated bot-source attribution. No new failing deployment was triggered. The temporary organization hook is active for PR and workflow events; polling remains installed.

The app is a local ad-hoc-signed Apple Silicon prototype. It is not notarized, released to friends, or configured for automatic updates. Intel support is deferred. Technical text was checked for short, direct instructions; a complete ASD-STE100 dictionary check was not performed.
