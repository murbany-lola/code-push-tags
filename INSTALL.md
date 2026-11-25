# Install Code Push Tags

Play local sounds for your successful Git pushes, PR merges, and related GitHub Actions failures. Installation is optional. Each person controls their own repositories, sound choices, and global mute.

[Download the DMG](https://github.com/murbany-lola/code-push-tags/releases/latest/download/Code-Push-Tags-macOS.dmg) · [Download the ZIP](https://github.com/murbany-lola/code-push-tags/releases/latest/download/Code-Push-Tags-macOS.zip) · [Watch the trailer](docs/code-push-tags-trailer.mp4)

## Requirements

- An Apple Silicon Mac with macOS 12 or later. Intel is not supported yet.
- Python 3.9 or later.
- GitHub CLI (`gh`).
- Git and zsh for the terminal push trigger.
- Your own GitHub account for automatic GitHub event checks.

You can download the public app without repository write access or a GitHub account. Use your own GitHub credentials to check events. Access to private work repositories still depends on your account permissions.

Check the required commands in Terminal:

```sh
python3 --version
gh --version
```

If a command is missing, install [Python for macOS](https://www.python.org/downloads/macos/) or [GitHub CLI](https://cli.github.com/).

## Install the app

1. Download the DMG.
2. Open the DMG.
3. Drag **Code Push Tags.app** to **Applications**.
4. Eject the disk image.
5. Open the app from Applications.

You can use the ZIP instead. Extract it, then move **Code Push Tags.app** to Applications. Keep the app at that path after setup. You can also use your home Applications folder.

Installing or opening the app does not enable automatic sounds.

## If macOS blocks the app

The current public preview has an ad-hoc signature. It is not Developer ID signed or notarized. macOS can block a downloaded copy.

Read [Apple's instructions for opening an app from an unidentified developer](https://support.apple.com/en-us/102445). Check the source of the download before you approve an exception. A managed Mac can have additional restrictions.

## Listen to your repositories

Use your own GitHub account. You do not need an invitation to this app's public repository. You do need access to each work repository you select.

1. Select **GitHub Sign-in**.
2. Complete sign-in in Terminal with your own account.
3. Select **Check setup**.
4. Select **Repositories / Orgs**.
5. Select **Refresh** to check your current GitHub access.
6. Clear **All accessible repositories** if you want a smaller selection.
7. Select the repositories or organizations you want.
8. Select **Save selection**.
9. Choose your push, merge, and failure sounds from the event menus.
10. Select **Enable on this Mac**.
11. Review the setup prompt.
12. Confirm setup when ready.
13. Open a new terminal window.

To check the GitHub account in Terminal, run:

```sh
gh auth status
```

The app confirms access before it saves your selection. An organization selection includes only repositories your account can access. Selecting a repository does not grant GitHub permissions. If a private repository is missing, check your account and your organization's single sign-on (SSO) requirements.

Merge sounds cover PRs you authored or merged. CI sounds cover failures associated with your work. Selecting an organization does not enable sounds for everyone's unrelated activity. Max's local listener does not send sounds to your Mac.

Select **DJ DECKS** or **BOOMBOX** to change the layout. The app saves this choice on your Mac.

## Check your setup

1. Confirm that your test repository is selected in **Repositories / Orgs**.
2. Turn global mute off.
3. Push a normal commit from the new terminal, or merge one of your normal PRs on GitHub.
4. Keep the Mac awake and online until the event arrives.

GitHub web and squash merges are included. A terminal push must use the installed zsh function. Other shells, GUI Git clients, and direct `/usr/bin/git` calls bypass the push trigger.

The first background check sets a baseline. It does not play old events. Use a new event after setup for this check. You can work in another app while the sound plays.

## Choose sounds

The library has Push, Merge, and Failure groups. A sound can appear in more than one group.

- Double-click a library item to preview it.
- A single click does not play or highlight the item.
- Select **CUE** once to preview the sound assigned to that event.
- Use each event's menu to save its sound assignment.
- A new preview stops the previous preview.

## How events arrive

Enablement adds a source line to `.zshrc` and installs a background watcher. The new terminal loads the push trigger. Normal setup does not create GitHub webhooks or change CI workflows.

| Repository status | Event path |
| --- | --- |
| **Live** | A verified listener on this Mac receives merge and CI events. Covered events do not use repository event polling. |
| **Live + polling** | The listener covers one event type. Polling supplies the other type. |
| **Polling available** | No verified listener covers the repository. The enabled watcher checks once per minute. |
| **Access not confirmed** | Refresh the list or check GitHub sign-in before saving. |

The app checks connection health. If the live connection is unavailable, polling supplies the fallback. After a recorded disconnect, a catch-up check covers the gap. GitHub indexing and event delivery can add delay. Polling can take a minute or longer to detect an event.

Keep your Mac awake and online for event checks. Notifications do not need the sound app in front. Closing the window or quitting the app does not stop an installed background watcher.

For an optional live connection to a repository you administer, see [live listener setup](TEAM_README.md#optional-live-listener). The DMG does not include that source-only helper. Standard polling needs no webhook administration access.

## Mute at any time

Select **MUTE ALL** in the app or use the menu bar mute command. Select **TURN SOUNDS ON** when ready.

One global mute covers pushes, merges, CI failures, and previews. Muted events are recorded without playing later.

## Get new sounds and app versions

The app checks this repository's shared audio at startup and once per hour. The enabled background watcher also checks once per hour. Select **Refresh Library** to check immediately. A complete local copy remains available offline.

Audio updates do not require a new app download.

Starting with version 0.2.0, the app checks for new app versions at startup and once per hour. A quiet update bar appears when a newer download is available. It does not open a popup or move the app to the front. Select **Check for Updates** from the app menu to check immediately.

Select **Download update** when ready. Replace the app with the new copy, then open it. The app does not install updates automatically. Your saved choices remain outside the app bundle. **Restart UI** in the app menu restarts the window without stopping the installed background watcher.

Version 0.1.0 does not contain the update checker. Install version 0.2.0 once to receive future update notices. See [update and rollback steps](UPDATES.md).

## Remove setup

1. Open the app.
2. Select **Remove setup**.
3. Confirm removal.
4. Quit the app.
5. Open a new terminal window.
6. Move the app to Trash if you no longer want it.

Removal keeps sound choices and local state in `~/Library/Application Support/Code Push Tags/`. GitHub credentials remain outside the app bundle. Keep private state and logs private.

## Build from source

Install Python 3.9 or later, GitHub CLI, Git, and the Xcode Command Line Tools. Then run:

```sh
git clone https://github.com/murbany-lola/code-push-tags.git
cd code-push-tags
python3 macos/build_app.py --output dist/local-build
```

Use a new output folder for each build. The command creates the app, ZIP, and DMG. Install from the generated DMG with the steps above. The build currently targets Apple Silicon.

## Help

Select **Check setup**. If private GitHub events are missing, check your account and organization authorization. If a library refresh fails, existing local sounds remain available.

See [app controls](MAC_APP.md), [terminal setup](TEAM_README.md), and [sound sources](SOUNDS.md).
