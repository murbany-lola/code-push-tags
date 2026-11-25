# Code Push Tags: coworker setup

A [native Apple Silicon app prototype](MAC_APP.md) is available for local testing. Team distribution is pending that test. The terminal setup below remains available.

Play a short audio tag after your successful Git pushes and GitHub PR merges. Installation is optional. Each person controls their own Mac and sound choices.

## Before you start

Use macOS, zsh, Python 3.9 or later, Git, and GitHub CLI (`gh`). Ask Max for read access to this private repository. Use your own GitHub account.

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

Listen to the default push and merge clips:

```sh
afplay audio/stackaholics.wav
afplay audio/branch-outta-here.wav
```

The default push line is "Stackaholics! We build different!" The default merge line is "Branch outta here!"

List all available clips:

```sh
python3 push_tags.py list
```

Set the defaults:

```sh
python3 push_tags.py configure --push-tag stackaholics --merge-tag branch-outta-here --push on --merge on
```

To use "Another one" for merges instead:

```sh
python3 push_tags.py configure --merge-tag dj-khaled-another-one
```

Replace that ID with another ID from the list to choose a different clip. These commands change only your settings.

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

Play one clip manually:

```sh
push-tags play stackaholics
```

Test the push trigger from a new terminal:

```sh
git -C ~/code-push-tags push
```

A successful "Everything up-to-date" response can play the sound. GitHub can reject this test if you have read-only repository access. Use a repository where you can push instead.

Merge one of your normal PRs to test the merge sound. GitHub web and squash merges are included. The watcher checks once per minute. GitHub indexing and event delivery can add delay. Your Mac must be awake and online.

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

## Keep the one-person webhook separate

Max is testing a direct GitHub webhook connection on his Mac. GitHub's test forwarding allows one connection per organization. Do not start a second `--org lola-labs` forwarding session for coworker setup. Use the standard polling installation above.

A shared webhook listener is future work. Coworkers can already use this polling setup independently. Their mute settings and tag choices remain local.

## Help

Run the status check:

```sh
python3 ~/code-push-tags/push_tags.py doctor
```

If private Lola Labs PRs are missing, check that your GitHub login and organization authorization permit access to those repositories.

Private configuration and logs are in `~/Library/Application Support/Code Push Tags/`. Do not share tokens or raw private logs.

## Optional app or source

The prototype builder supplies `Code-Push-Tags-macOS.dmg`. Open it and drag the app to Applications. Installation does not enable automatic sounds. Use your own GitHub account, select your repositories, then enable setup when ready. The current app requires Apple Silicon, Python 3, and GitHub CLI. It has an ad-hoc signature and is not notarized. macOS can block a downloaded copy.

You can also build from the private repository source. Repository access must be granted separately. See [installation and source builds](UPDATES.md). No credentials or private settings are included in the bundle or source.

The repository window shows verified live connections and available polling. Access is checked again before a selection is saved. See [app controls](MAC_APP.md).
