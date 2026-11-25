# Code Push Tags: coworker setup

For the Apple Silicon app, start with [INSTALL.md](INSTALL.md). The current public preview is available as a DMG or ZIP. The terminal setup below is an alternative.

Play a short audio tag after your successful Git pushes, GitHub PR merges, and related GitHub Actions failures. Installation is optional. Each person controls their own Mac and sound choices.

## Before you start

Use macOS, zsh, Python 3.9 or later, Git, and GitHub CLI (`gh`). The source and downloads are public. Use your own GitHub account for event checks.

The standard setup uses local Git commands and GitHub polling. You do not need an organization webhook, webhook administration access, or a voice-generation account.

## Get the files

Sign in to GitHub:

```sh
gh auth login
```

If you already use `gh`, check your account first:

```sh
gh auth status
```

Clone the repository into a permanent folder:

```sh
gh repo clone murbany-lola/code-push-tags ~/code-push-tags
cd ~/code-push-tags
```

Keep this folder at the same path after installation.

## Listen and choose

List the sound library:

```sh
python3 push_tags.py list
```

Preview sounds for each event:

```sh
python3 push_tags.py play --event push
python3 push_tags.py play --event merge
python3 push_tags.py play --event ci
```

These commands use saved sound selections when available. In the app, browse the Push, Merge, and Failure groups. Double-click an item to preview it. Use each event's menu to save its sound assignment.

For terminal selection options, run:

```sh
python3 push_tags.py configure --help
```

Each selection changes only your local settings. New library clips do not replace an existing selection. See [sound sources and updates](SOUNDS.md).

## Select your repositories

Use the app's **Repositories / Orgs** window with this terminal installation. It uses the same local configuration.

1. Select **GitHub Sign-in** if you have not signed in.
2. Select **Check setup**.
3. Select **Repositories / Orgs**.
4. Select **Refresh** to confirm current access.
5. Clear **All accessible repositories** to choose a subset.
6. Select individual repositories, organizations, or both.
7. Select **Save selection**.

The selection applies to terminal pushes, GitHub merges, and related CI failures. An organization selection includes its accessible repositories. It does not grant new permissions or enable sounds for other people's unrelated work.

For terminal-only setup, list accessible repositories and save a selection:

```sh
python3 repo_preferences.py list
python3 repo_preferences.py set --verify-access --repo OWNER/REPO
```

Replace `OWNER/REPO` with your repository name. Repeat `--repo` for more repositories. Use `--org ORGANIZATION` to include an organization's accessible repositories. The command replaces your previous repository selection.

## Enable sounds

Check the required commands and GitHub access:

```sh
python3 push_tags.py doctor
```

Inspect the installation paths:

```sh
python3 install.py plan
```

Install the terminal push trigger and background merge watcher:

```sh
python3 install.py install
```

Open a new Terminal window. The installer adds a source line to `.zshrc` and saves a backup. It also installs a local launchd job. The merge watcher sets its first baseline without playing old merges.

For Git commands from a coding agent or another noninteractive zsh process, use `.zshenv` instead of the default installation:

```sh
python3 install.py plan --shell-file ~/.zshenv
python3 install.py install --shell-file ~/.zshenv
```

Choose one startup file. Use the same file when you uninstall. The installer stops if an existing Git function or alias needs manual review.

## Global mute

These commands work from any folder in a new zsh terminal:

```sh
push-tags off
push-tags on
```

One global mute controls all sounds across all repositories. It stays set until you turn sounds on. The watcher records muted merges without playing them later.

If the short command is unavailable in your current terminal, use the full path:

```sh
python3 ~/code-push-tags/push_tags.py mute
python3 ~/code-push-tags/push_tags.py unmute
```

## Try it

Preview your push sound manually:

```sh
push-tags play --event push
```

Test the push trigger from a new terminal:

```sh
git -C ~/code-push-tags push
```

A successful "Everything up-to-date" response can play the sound. GitHub can reject this test if you have read-only repository access. Use a repository where you can push instead.

Merge one of your normal PRs in a selected repository to test the merge sound. GitHub web and squash merges are included. Use a new event after the first background check sets its baseline.

A connected listener receives covered events live. The watcher polls uncovered repositories or event types once per minute. If the live connection is unavailable, polling supplies the fallback. A recovery check covers a recorded connection gap. GitHub indexing and event delivery can add delay. Your Mac must be awake and online.

## What you will hear

Push sounds follow successful Git commands that use your configured zsh function. GUI Git clients, other shells, and direct `/usr/bin/git` calls bypass this trigger.

Merge sounds cover PRs that you authored or merged in repositories your GitHub account can read. Each merge is recorded once. Other people's unrelated merges do not play.

## Remove the tool

For the default `.zshrc` installation:

```sh
python3 ~/code-push-tags/install.py uninstall
```

For a `.zshenv` installation:

```sh
python3 ~/code-push-tags/install.py uninstall --shell-file ~/.zshenv
```

Open a new terminal after removal. Audio files and private settings remain in place.

## Optional live listener

Standard polling works without webhook administration access. Use these steps only for a live test on a repository you own or administer. The helper is part of the source checkout. The DMG does not contain `listen.py`.

The [GitHub forwarding tool](https://docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/using-the-github-cli-to-forward-webhooks-for-testing) is for testing and development. GitHub does not support it as a production webhook service. Only one person can forward events for each repository or organization at a time.

Repository read access alone is insufficient for live setup. GitHub requires repository ownership or admin access to [create a repository webhook](https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks). Organization webhooks require an organization owner and the applicable webhook authorization.

If you do not have a source checkout, clone it first:

```sh
git clone https://github.com/murbany-lola/code-push-tags.git ~/code-push-tags
```

1. Check your GitHub account:

   ```sh
   gh auth status
   ```

2. Open the permanent source checkout:

   ```sh
   cd ~/code-push-tags
   ```

3. Install the tested forwarding extension:

   ```sh
   gh extension install cli/gh-webhook --pin v0.2.0
   ```

   If the extension is already installed, continue with the availability check.

4. Confirm the extension is available:

   ```sh
   gh webhook forward --help
   ```

5. Start the helper for your repository:

   ```sh
   python3 -B listen.py --repo OWNER/REPO
   ```

   Replace `OWNER/REPO` with your repository name. The helper starts its local receiver and requests merge and workflow events. It stores its signing secret in Keychain.

6. Keep this terminal process running.
7. Open **Repositories / Orgs** in the app.
8. Select **Refresh** to check the connection.
9. Confirm that the repository shows **Live**.
10. Trigger a new normal event in that selected repository.

The live connection covers only this Mac. Another person's listener does not connect your Mac automatically. The repository selection, account attribution, and global mute still apply.

A dropped connected session retries after five seconds. The installed watcher uses polling while no live connection is verified. Startup or permission errors stop the helper. If GitHub denies access, check the reported permission requirement or keep using standard polling. Do not share a token to bypass access checks.

Use Control-C to stop the helper. Start it again after closing the terminal or restarting the Mac. No automatic live-listener startup service is installed.

A `Hook already exists` error means another forwarding connection uses that target. Do not delete someone else's hook to take it over. Max's temporary organization listener is for his Mac. Coworkers should not start a second `--org lola-labs` session.

The app receives covered events through the verified live connection. It polls other selected repositories or event types. Connection-health checks continue. A shared multi-person webhook service remains future work.

## Help

Run the status check:

```sh
python3 ~/code-push-tags/push_tags.py doctor
```

If private Lola Labs PRs are missing, check that your GitHub login and organization authorization permit access to those repositories.

Private configuration and logs are in `~/Library/Application Support/Code Push Tags/`. Do not share tokens or raw private logs.

## Optional app or source

The [published release](https://github.com/murbany-lola/code-push-tags/releases/latest) supplies `Code-Push-Tags-macOS.dmg`. Open it and drag the app to Applications. Installation does not enable automatic sounds. Use your own GitHub account, select your repositories, then enable setup when ready. The current app requires Apple Silicon, Python 3, and GitHub CLI. It has an ad-hoc signature and is not notarized. macOS can block a downloaded copy.

You can also build from the public repository source. No repository invitation is required. See [installation and source builds](UPDATES.md). No credentials or private settings are included in the bundle or source.

The repository window shows verified live connections and available polling. Access is checked again before a selection is saved. See [app controls](MAC_APP.md).
