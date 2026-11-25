# Personal webhook pilot

## Scope

Max remains the only enrolled person. The code stays in the private personal repository. Other engineers are not invited or enrolled.

Global controls: `push-tags off` and `push-tags on`. They mute or enable both event types across all repositories.

Current push sound: `stackaholics` ("We build different"). Current merge sound: `branch-outta-here`.

The live test used `murbany-lola/code-push-tags` PR #1. It merged into a temporary branch. Polling was paused. The signed webhook receiver saved the merge. A second delivery did not play again. Polling was restored. The temporary target branch was removed.

## Lola Labs connection request

Target: one temporary GitHub CLI test webhook for the `lola-labs` organization. Subscribe only to `pull_request` events. Forward signed events through GitHub's authenticated service to Max's local receiver. The receiver confirms the PR and filters for Max before playback.

Required action: authorize an exception for this temporary organization settings change, or route it through the infrastructure owner and the applicable platform PR. The user instructions require infrastructure changes through platform PRs. The agent treats an organization-wide webhook as an infrastructure change.

Command after authorization:

```sh
python3 listen.py --org lola-labs
```

The command uses the existing token from Keychain. It needs hook administration access. It does not change Lola product code, deployments, or CI workflows.

Acceptance: confirm connection, merge a Max-authored or Max-merged PR, confirm one sound, and confirm no second sound from polling. The Mac must be awake and online. Source branch deletion is not required for the event.

Rollback: stop the listener with Control-C. The command deletes its saved test webhook. Polling remains installed.

GitHub permits only one forwarding session for each organization. This is a one-person test. A shared authenticated service must precede a coworker rollout. Each coworker must opt in to their own Mac receiver and can mute or remove it.
