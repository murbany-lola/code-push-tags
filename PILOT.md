# Personal webhook pilot

## Scope

Max remains the only enrolled person. The code stays in the private personal repository. Other engineers are not invited or enrolled.

Global controls: `push-tags off` and `push-tags on`. They mute or enable both event types across all repositories.

Current push sound: `stackaholics` ("We build different"). Current merge sound: `branch-outta-here`.

The live test used `murbany-lola/code-push-tags` PR #1. It merged into a temporary branch. Polling was paused. The signed webhook receiver saved the merge. A second delivery did not play again. Polling was restored. The temporary target branch was removed.

## Current connection

The `lola-labs` organization test hook is active for `pull_request` events. Its ID is `716782681`. The signed Mac receiver runs on `127.0.0.1:18769`. GitHub recorded HTTP 200 for a real organization ping. No real Lola Labs merge has been used to test the new hook yet.

Decided by: person (Max). Max approved the temporary one-person organization-hook exception after the scope and infrastructure rule were explained in this session.

The existing token lacked `admin:org_hook`. Max completed GitHub CLI device authorization. The pilot credential was updated in Keychain. No credential value is in this repository.

The listener is running as a pilot process. It does not yet restart automatically after a Mac reboot. Polling remains registered with launchd. The code is in PR #2 and is not merged.

## Lola Labs connection procedure

Target: one temporary GitHub CLI test webhook for the `lola-labs` organization. Subscribe only to `pull_request` events. Forward signed events through GitHub's authenticated service to Max's local receiver. The receiver confirms the PR and filters for Max before playback.

The user instructions require infrastructure changes through platform PRs. The agent treated the organization-wide webhook as infrastructure. Max explicitly approved the temporary pilot exception before the hook was created.

Authorized command:

```sh
python3 listen.py --org lola-labs
```

The command uses the existing token from Keychain. It needs hook administration access. It does not change Lola product code, deployments, or CI workflows.

Acceptance: confirm connection, merge a Max-authored or Max-merged PR, confirm one sound, and confirm no second sound from polling. The Mac must be awake and online. Source branch deletion is not required for the event.

Rollback: stop the listener with Control-C. The command deletes its saved test webhook. Polling remains installed.

GitHub permits only one forwarding session for each organization. This is a one-person test. A shared authenticated service must precede a coworker rollout. Each coworker must opt in to their own Mac receiver and can mute or remove it.
