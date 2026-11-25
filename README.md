# Code Push Tags

An optional sound for successful Git pushes and GitHub pull request merges on macOS.

The pilot clip says: **Stackaholics! We build different!** Max approved this clip. Each person installs the tool on their own Mac. There is no team broadcast or automatic enrollment.

## Listen first

```sh
afplay audio/stackaholics.wav
```

## Saved merge tags

The merge clips are included. Select one when you want to change the merge sound:

```sh
python3 push_tags.py configure --merge-tag stackaholics-welcome-to-main
python3 push_tags.py configure --merge-tag stackaholics-thats-a-wrap
python3 push_tags.py configure --merge-tag wheezy-outta-here
python3 push_tags.py configure --merge-tag branch-outta-here
```

The push sound has its own setting. Adding these files does not change an existing selection.

## Requirements

Use macOS, zsh, Python 3.9 or later, Git, and GitHub CLI (`gh`). The installation folder must remain at the same path after installation.

## Opt in

Clone this repository into a permanent folder. Open Terminal in that folder. Authenticate your own GitHub account:

```sh
gh auth login
```

Select the pilot clip for both events:

```sh
python3 push_tags.py configure --push-tag stackaholics --merge-tag stackaholics --push on --merge on
python3 push_tags.py doctor
```

Inspect the installation paths:

```sh
python3 install.py plan
```

Enable the tool:

```sh
python3 install.py install
```

Open a new terminal. The installer backs up `.zshrc`, adds a source line, and installs a local launchd job for merge checks. It does not change repository hooks or CI configuration.

To include noninteractive zsh commands, such as ordinary Git calls from a coding agent, use `.zshenv` instead. Use this same path for removal:

```sh
python3 install.py plan --shell-file ~/.zshenv
python3 install.py install --shell-file ~/.zshenv
```

Existing Git functions and aliases are not replaced automatically.

## Mute or remove

```sh
python3 push_tags.py mute
python3 push_tags.py unmute
python3 push_tags.py configure --push off
python3 push_tags.py configure --merge off
python3 install.py uninstall
```

If you installed into `.zshenv`, remove that installation with:

```sh
python3 install.py uninstall --shell-file ~/.zshenv
```

Open a new terminal after removal. Audio files and private settings remain on the Mac.

## Trigger behavior

The shell function plays the clip after a successful `git push`. It preserves Git output, exit status, and existing hooks. A successful push with no changes can also play the clip. Audio plays in the background at reduced volume.

The shell function covers Git commands that use the selected zsh startup file. An absolute `/usr/bin/git` command, another shell, or a GUI Git client bypasses it. An explicit command also works:

```sh
python3 push_tags.py push -- origin HEAD
```

The merge watcher checks GitHub once per minute. It confirms that a pull request was merged and that you authored or merged it. The first check sets a baseline without playing old merges. The Mac must be awake and online. GitHub search indexing and event delivery can delay the sound; the event feed can lag by up to six hours and contains at most 300 events.

Mute suppresses playback. The watcher still records events, so unmuting does not replay those events.

## Credentials and settings

The watcher uses your `gh` login. An optional Keychain reference is supported:

```sh
python3 install.py install --keychain-service code-push-tags.github --keychain-account YOUR_GITHUB_LOGIN
```

Create that Keychain item through your normal credential process before use. The installer stores only the item name and account reference. It does not place the token in this repository or the launchd file.

Settings, logs, and merge state are in `~/Library/Application Support/Code Push Tags/`. Keep those files private.

## Checks

```sh
python3 -m unittest discover -s tests -q
zsh -n shell.zsh
```

The unit tests use simulated Git, GitHub, audio, and time responses. They do not push or merge code. These checks do not establish that the tool works with every Git client.

The clip was generated with TagMyBeat from a source voice. Max confirmed authorization to clone that voice. No license for third-party source voices is granted by this repository.

Sources: [Fenzo guide](https://fenzo.ai/courses/drop-your-producer-tag-every-git-push/hear-it-on-your-OuM3wCUFM), [Git hooks](https://git-scm.com/docs/githooks#_pre_push), and [GitHub event limits](https://docs.github.com/en/rest/activity/events).

The original Wheezy clip is a community upload from [Myinstants](https://www.myinstants.com/en/search/?name=wheezy+outta+here). It was converted from MP3 to WAV. This repository grants no rights to that recording.

Max approved the "Branch outta here!" parody as his merge sound. It was generated with TagMyBeat from the Wheezy reference voice after Max confirmed authorization to clone that voice.
