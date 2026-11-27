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

## Saved layouts and transport animation

Both layouts use the existing event controls and settings. The separate artwork view replaces the previous static record view.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 238 | 239 |
| Test net LOC | 0 | 0 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 1 | 1 |

- reuse-hunter: pass; no findings.
- loc-minimizer: pass; no findings.
- path-correctness: minor; selection animation ran before artwork layout. Applied: complete artwork layout before the selection animation.
- path-correctness: minor; preview motion resumed before restored sound choices. Applied: restore choices before preview motion resumes.

Validation: the targeted Apple Silicon build passed. The app signature check passed. A temporary Swift check verified the first selection animation, continuous preview motion, a save during a preview, and stopping all motion. It used animation state checks without time delays. Native UI checks verified both layout switches and the saved boombox choice after an app restart. Screenshots show both layouts. Build 4 is installed locally. No release was published.

The documentation uses short, direct instructions. A complete ASD-STE100 dictionary check was not performed.

## Connection status, grouped library, and DMG

The change reuses the repository catalog, GitHub credentials, local listener state, event filters, and preview player. It replaces the sound pad view with a cassette or record item.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 258 | 261 |
| Test net LOC | 146 | 147 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 1 | 1 |

- reuse-hunter: pass; no findings.
- loc-minimizer: pass; no findings.
- path-correctness: minor; a fresh install implied active polling before setup. Applied: state that polling is available and requires enabled setup. A focused regression check passed.

Validation: 14 new connection tests and 12 existing repository preference tests passed. The focused polling text regression passed after the review fix. Swift typecheck and the targeted Apple Silicon build passed. A live read confirmed access to 29 repositories: 28 had connected merge and CI listeners, and one used polling. No hooks were created. Native UI checks covered both library styles, category filters, and a filtered repository list after a fresh access check. An observed list alignment error was fixed; both lists now start at the top. The installed app signature passed after normal use.

The DMG mounted read-only. It contained the app and an Applications shortcut. The app signature passed from the mounted image. The image was ejected. Build 6 is installed locally. No release was published. The app remains ad-hoc signed and is not notarized.

The documentation uses short, direct instructions. A complete ASD-STE100 dictionary check was not performed.

## Shared audio, double-click preview, and card borders

The native app and background watcher use the same library helper. The helper downloads one immutable repository revision and activates it only after the complete manifest and WAV files pass checks. Playback keeps the root used for the selected tag.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 199 | 193 |
| Test net LOC | 189 | 232 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 1 | 1 |

- reuse-hunter: pass; no findings.
- path-correctness: release prerequisite; library sync reads `main`, which still contains the original Wheezy sample. Recorded: merge the manifest removal before sharing this automatic-sync build. No code change is required for this release order.

Validation: 18 library tests passed, including offline playback, partial downloads, access denial, cache activation, elapsed-time boundaries, and playback during a pointer change. The 21 existing push and merge tests passed. The focused CI polling test passed with library sync mocked. Swift typecheck and the targeted Apple Silicon build passed. A real authenticated download from `main` cached 11 WAVs in isolated state; all decoded. No credentials were stored with the files.

A native mouse-event check confirmed that one click did not play the first clip and a double-click did. Max then requested no focus change or card outlines. The explicit focus change, card borders, and card focus rings were removed. A new single-click check left the preview idle. The screenshot after that click showed no outline. Build 9 is installed locally.

The final DMG mounted read-only. Its app signature passed. It contains 10 bundled clips, retains Branch outta here, excludes the original Wheezy clip, and includes the shared-library helper. It contains no bytecode cache. The image was ejected. The running prototype can still show the older shared manifest until this PR reaches `main`; select Refresh Library after merge.

The documentation uses short, direct instructions. A complete ASD-STE100 dictionary check was not performed.

## Public downloads, install guide, and trailer

Decided by: person (Max). Make this personal repository public. Add an install guide and a short app trailer. Record only the app and exclude sensitive content.

Before the visibility change, a text-pattern check covered 18 reachable Git revisions. It found no matches for the selected credential formats. No committed credential-file names were found. The repository had no Actions runs. This was a limited pattern check, not a complete security audit. The existing third-party audio source notes remain. Redistribution permission for community uploads was not established.

Anonymous GitHub requests confirmed public repository and release access. An anonymous DMG download matched the published SHA-256 digest. No collaborators were invited.

INSTALL.md covers app and source installation, dependencies, opt-in, GitHub access, sound controls, updates, background playback, and removal. Existing delivery documents now use the public release links. A complete ASD-STE100 dictionary check was not performed.

The trailer is 29.5 seconds at 1440 × 1080. It uses three app-window recordings, title cards, and three selected WAV clips. It contains no microphone or system-audio capture. Sampled frames were checked for a full app view, real preview playback, and the absence of desktop, browser, or private repository names. Raw recordings remain outside the repository. Audio decoded without clipping.

A real merge-notification sound played while Slack remained in front. Focus did not change during the observation. Recording controls, rather than the notification path, brought the app forward during trailer work. The previous foreground app and saved layout/mute state were restored after recording.

The pre-merge gate skipped review because the changes contain documentation and generated media only. Prod net LOC, test net LOC, new prod files, tables, columns, and data resources remain zero for this change. No app code changed.

## General sound-library language

Decided by: person (Max). Use general app language instead of one tag's name. Max also approved direct pushes to `main` for this personal repository.

The onboarding guides use event-based preview commands. Three sound display names no longer include the producer-tag prefix. Their IDs, file paths, audio, event categories, and saved selections are unchanged. Source attribution remains in SOUNDS.md.

Validation: the manifest parser accepted all 10 entries. A comparison with the previous manifest confirmed that only display names changed. All referenced audio files exist. The diff check passed. The pre-merge gate skipped review for a six-line production change with no new files, schema, or release change. Prod net LOC, test net LOC, new prod files, tables, columns, and data resources are zero. No app build was needed. A complete ASD-STE100 dictionary check was not performed.

## Logo, quiet app updates, and UI restart

Decided by: person (Max). Add a silly general logo and app-version notices. Keep interruptions small and preserve background processing during UI restarts. Defer official Apple signing and notarization.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 220 | 220 |
| Test net LOC | 172 | 172 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 2 | 2 |

- reuse-hunter: pass; no findings.
- loc-minimizer: pass; no findings.
- path-correctness: pass; no findings.

Validation: 16 update-check tests passed. They cover numeric version comparison, the cache, offline responses, unsupported releases, URL checks, and uploaded assets. The real public API returned version 0.1.0 and correctly reported no update for that same installed version.

Swift typecheck and the targeted Apple Silicon build passed. The native update-bar test used a controlled version 0.3.0 response in isolated local state. The bar fit the window. No actual version 0.3.0 release was created and its download was not opened.

The Restart UI test started a new UI PID. The launchd watcher remained registered. Hashes of the saved configuration, mute, and layout files were unchanged. No long-running test webhook process was present during this check; this check did not establish a stable webhook PID.

The DMG mounted read-only. It contained version 0.2.0, build 10, the update helper, header PNG, and generated ICNS icon. Its ad-hoc signature passed and its architecture was arm64. No bytecode cache was present. The image was ejected. Logo corner alpha was zero, which confirmed transparent margins.

The logo came from the built-in image generation tool. The exact prompt is in docs/logo-prompt.md. The current public preview is not Developer ID signed or notarized. Version 0.1.0 users must install this update once before they can receive future app-update notices.

The documentation uses short, direct instructions. A complete ASD-STE100 dictionary check was not performed.

## Tagline and live-event recovery

Decided by: person (Max). Add "Millennial in the streets, Gen Z in the commits." under the app name and in the README. Prefer live events over polling for connected repositories. Add clear instructions for each person's repositories.

A reported delay occurred after the live test forwarder exited on WebSocket close 1006 with unexpected EOF. Polling remained healthy. The next recorded checkpoint was 42 seconds after the reported merge. The live source process was restored. Real GitHub deliveries returned HTTP 200.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 65 | 80 |
| Test net LOC | 358 | 431 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 0 | 0 |

- path-correctness: P2; failed hook cleanup masked the disconnect error and stopped retry. Applied: preserve the active error and saved identity. Retry later startup errors after a known connection loss. First startup errors still stop the helper. Round 2 passed.

Focused checks passed: 21 push tests, 33 CI tests, 12 repository preference tests, and 14 connection tests. The final live-routing module has 18 passing cases. Listener checks passed before the cleanup change; five focused cleanup/startup checks then passed. All tests simulate retry delays and provider intervals.

Two incomplete-recovery failures were reproduced before their fixes. A busy merge lock and a deferred account feed each cleared recovery too soon. The merge check now reports incomplete work. Recovery remains pending until the same target is healthy, both checks complete, and the marker ID still matches under its short lock. A later disconnect cannot be removed by an earlier catch-up.

A real authenticated event-check trace used the healthy organization listener. It made zero organization repository-specific reads and excluded that organization from search queries. GitHub's account activity feed remains global for uncovered work; covered entries do not cause PR or workflow reads. A controlled source-process restart recorded a gap. The scheduled watcher completed recovery and removed that marker after the connection returned.

The local build passed. Its bundled runtime files match the final source. The tagline fits under the app name. Version 0.2.1, build 13 retains the ad-hoc Apple Silicon preview format. No autostart service or shared team relay was added. The optional live helper must remain running.

INSTALL.md and TEAM_README.md now cover own-account sign-in, access checks, repository selection, enablement, testing, live permissions, reconnect, and terminal/reboot limits. A complete ASD-STE100 dictionary check was not performed.

## Version 0.3.0: PR comment sounds

Decided by: person (Max). Add sounds for other people's comments on the member's own PRs. Exclude bots and the member's own comments. Add AOL mail and GTA Mission Failed clips.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 9010 | 301 |
| Test net LOC | 288 | 308 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 3 | 3 |

The first gate counted untracked WAV data as text. The final gate identified the staged audio as binary. The production count includes one new Python module and two WAV files.

Reuse, LOC, and path reviewers reported no actionable findings. Parent inspection found repeated reads for old comments and one failed item that stopped valid items. Both were corrected before review. The tests cover old records, deleted records, partial failures, own comments, bots, authorship, and live/poll deduplication. The notification fallback can combine or miss comments; INSTALL.md states this limit. The previous app's manifest validator accepts the new sound library.

Focused checks: 88 connection, routing, CI, and comment tests passed. Receiver and sound library checks passed. The listener checks passed. The native Apple Silicon preview build passed. No full test suite was run. A complete ASD-STE100 dictionary check was not performed.

The installed 0.3.0 app shows 12 clips. The COMMENTS filter shows the AOL clip. The comment sheet shows the saved default. Turning the checkbox off and on saves the selected state. CUE starts the preview. The public v0.3.0 release contains DMG and ZIP downloads. The local live listener confirms all five subscriptions, including all three comment event types. No real PR comment was created for this check.

## Version 0.3.1: tagline and fork guide

Decided by: person (Max). Use "One time for the runtime." as the product tagline. Add "Lossless or GTFO" by the sound library. Use MIT for the original platform code and technical documentation. Keep all audio and other media outside that code license.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 21 | 21 |
| Test net LOC | 0 | 0 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 1 | 1 |

The gate counts LICENSE as a new production file. Reuse and path reviewers reported no actionable findings. The changes add strings, documentation, and license files to the existing bundle list. The native Apple Silicon build passed. The installed app shows both new strings without overlap. Sound, mute, and layout settings have the same file hashes after replacement. LICENSE and NOTICE.md are in the bundle. No new unit tests were required for these string and packaging changes.

FORKING.md gives the source installation and build commands. A fork can retain the original update sources or change the two source constants before release. The current WAV catalog uses a GitHub manifest. Arbitrary local folder import is not implemented. Media permissions remain separate from the MIT code license.

The reel outro and social kit use the new tagline. The feature crop excludes the old tagline. The sound sections and audio cues are unchanged. A complete ASD-STE100 dictionary check was not performed.

## Version 0.3.2: producer groups and five parodies

Decided by: person (Max). Add the completed London, Tay Keith, Turbo, Jetsonmade, and Pi’erre parodies. Group sounds by producer. Exclude Metro, Murda, Just Blaze, Conductor, and Jahlil from this batch.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 85 | 85 |
| Test net LOC | 0 | 0 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 5 | 5 |

The five new production files are WAV files. The existing manifest supplies optional producer metadata. One helper groups the library columns and sound menus. The existing shared-library update path remains in use.

Reuse-hunter: no findings. Path-correctness: no findings. No second review round was required.

Swift typechecking and 18 focused sound-library tests passed. All 17 manifest paths resolve. The five new WAV files match the downloaded conversions. Their source MP3 hashes match the generation record. They are mono, 44.1 kHz, 16-bit PCM. They are conversions from MP3 exports. Conversion does not improve source quality.

The Apple Silicon build, ad-hoc signature check, and archive inspection passed. The ZIP has 17 clips and no private settings or local source folders. The app is not Developer ID signed or notarized.

A separate local test state confirmed producer headings in sound menus, saved sound selection, playback, global mute, the six-clip Failure filter, both layouts, and window close/reopen behavior. The new menu selection preserved the event's disabled state. Screenshots show only the app: [records](docs/library-producers-records.png) and [cassettes](docs/library-producers-cassettes.png). User preference hashes were recorded before replacement.

Existing sound IDs remain the same. Older apps can receive the new clips through shared-library updates. Producer groups require the new app code. A complete ASD-STE100 dictionary check was not performed.

## Version 0.4.0: search and compact LED player

Decided by: person (Max). Add producer search and a compact player with a pixel LED activity display.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 313 | 313 |
| Test net LOC | 46 | 46 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 1 | 1 |

Search uses the existing producer metadata, clip titles, and event filters. Case, accents, spaces, and punctuation do not prevent a name match. The compact view uses the existing playback and mute controls. The playback function writes a small local record after it launches the audio process. A directory event observer reads this record. No new GitHub listener or provider call was added.

Reuse-hunter: no findings. LOC-minimizer: no cuts. Path-correctness: minor, wrong producer label on a sound-effect preview after a background producer tag; applied. The native check confirmed **Sound effects / PREVIEW** for LEGO after a London tag. No blocker or major finding required a second review round.

25 focused playback tests passed. Swift typechecking passed. The final Apple Silicon build and ad-hoc signature check passed. The indicator uses expected WAV duration. It does not measure audio device output or detect early termination of an external audio player.

Native checks used separate settings. Producer searches for `pierre` and `TAY KEITH` each returned one clip. The existing Failure filter retained six clips. CUE playback, mini/full switching, and mute controls worked. A real background `push` playback lit the LED with **London on da Track / PUSH** while Finder stayed in front. Global mute blocked background playback and did not write a new playback record. The fixed preview label was checked in the final build.

Screenshots show only the app: [producer search](docs/producer-search.png) and [compact player](docs/mini-player.png). Version 0.4.0 includes the producer catalog from the 0.3.2 source checkpoint. A complete ASD-STE100 dictionary check was not performed.

The installed app is version 0.4.0, build 20. Its shared cache has all 17 clips. The installed window exposes the search field and shows **17 / 17**. Hash checks confirmed that the user's sound configuration, global mute setting, and layout setting did not change. The final 18 sound-library tests also passed with the playback signal in place.

[Version 0.4.0](https://github.com/murbany-lola/code-push-tags/releases/tag/v0.4.0) contains the DMG and ZIP. GitHub asset sizes and SHA-256 digests match the local build. No GitHub Actions runs are configured for this repository. Validation used the focused local checks and the authorized native app build.

## Version 0.4.1: event columns and producer stacks

Decided by: person (Max). Keep Push, Merge, Failure, and Comments in separate columns. Stack expandable producer groups vertically inside each event. Use record artwork for DJ mode and cassette artwork for boombox mode. Add clear app-only screenshots to the README. Shorten the Tay Keith clip.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 178 | 178 |
| Test net LOC | 0 | 0 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 0 | 0 |

Reuse-hunter: minor, duplicate text renderer; applied. Cards and headers share one file-scope text renderer with the same default alignment. Final reuse and path reviews reported no remaining findings. No blocker or major finding required a second review round.

Native checks confirmed four 247-point event columns in All. Each producer list has a vertical scrollbar when required. The outer library has no scrollbar. Event headings remain in place while producers scroll. Expanding a producer at a nonzero offset kept its header position. Expansion in Push did not expand the same producer in Merge. A specific Failure filter showed one 336-point column. A Pi’erre search kept all four event columns and showed the matching clip in Merge. Empty columns showed NO MATCHES. Both layouts displayed the correct stack artwork. Existing sound cards and preview IDs remain in use.

Swift typechecking, the final Apple Silicon build, ad-hoc signature verification, and ZIP inspection passed. The final build is version 0.4.1, build 24. No unit tests were added for this display change. The audio edit removed only exact-zero samples: 5.799 seconds became 3.140 seconds. Audible samples, phrase, speed, sample rate, and channel count stayed the same. The final bundle contains the shortened WAV.

The README shows [DJ event columns](docs/library-event-columns-records.png), [boombox event columns](docs/library-event-columns-cassettes.png), and the existing [mini-player LED display](docs/mini-player.png). All images show only the app. The local preview pack also uses the shortened Tay Keith WAV. Original audio exports remain in the local source folder and preview pack's original-exports directory.

A complete ASD-STE100 dictionary check was not performed.

The installed app and shared cache were checked after replacement. Version 0.4.1, build 24 shows four event columns and no outer scrollbar. The shared cache has 17 clips and the 3.140-second Tay Keith WAV. Preference hashes confirmed that sound assignments, global mute, and layout settings stayed the same. The published [DMG and ZIP](https://github.com/murbany-lola/code-push-tags/releases/tag/v0.4.1) match local sizes and SHA-256 hashes.

## Version 0.4.2: plain event headings

Decided by: person (Max). Make the broad event categories clear without using bundle cells. Keep the artwork on expandable producer groups.

| Value | Before | After |
| --- | --- | --- |
| Prod net LOC | 2 | 2 |
| Test net LOC | 0 | 0 |
| New tables | 0 | 0 |
| New columns | 0 | 0 |
| New data resources | 0 | 0 |
| New prod files | 0 | 0 |

Path-correctness: no findings. Plain labels, counts, and separators replace the static event cards. Unused category-card branches were removed. The producer lists gained 23 points of vertical space. No playback, search, or saved-choice code changed.

Swift typechecking and the Apple Silicon build passed. Native checks showed four event labels as static text, no event checkbox cells, four 247-point producer lists, and no outer scrollbar. Producer expansion worked in boombox mode. The README uses current app-only [DJ](docs/library-clean-event-headings-records.png) and [boombox](docs/library-clean-event-headings-cassettes.png) screenshots. No unit tests were added for this display change. A complete ASD-STE100 dictionary check was not performed.
