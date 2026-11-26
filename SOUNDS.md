# Sound library

**Lossless or GTFO.** Bring your own WAV catalog. All audio stays outside the platform code license.

Each event can use any listed clip. Preview and select clips locally in the app. Existing sound choices are not changed when a new clip is added.

| ID | Clip | Source |
| --- | --- | --- |
| `stackaholics` | We build different! | TagMyBeat; Max approved the generated clip and confirmed source-voice authorization. |
| `stackaholics-welcome-to-main` | Welcome to main! | TagMyBeat; same authorized reference voice. |
| `stackaholics-thats-a-wrap` | That's a wrap! | TagMyBeat; same authorized reference voice. |
| `branch-outta-here` | Branch outta here! | TagMyBeat; Max confirmed authorization for the Wheezy reference voice. |
| `dj-khaled-another-one` | Another one | [Myinstants](https://www.myinstants.com/en/search/?name=dj+khaled+another+one) |
| `lego-break-apart` | LEGO death — break-apart clip (1.65 s) | [Myinstants](https://www.myinstants.com/en/instant/lego-breaking-57805/) · [requested reference](https://www.youtube.com/watch?v=8Z0JhcWURDY) |
| `terio-kill-em` | Terio kill ’em — original-voice ending cut (2.3 s) | [Downloaded audio](https://www.myinstants.com/media/sounds/terio-mp3.mp3) |
| `metal-gear-alert` | Metal Gear Solid Alert (1.57 s) | [Downloaded audio](https://www.myinstants.com/media/sounds/tindeck_1.mp3) |
| `windows-xp-error` | Windows XP Error sound (download) (1.02 s) | [Downloaded audio](https://www.myinstants.com/media/sounds/erro_5kzwjlL.mp3) |
| `fahhh` | Fahhh (2.28 s) | [Myinstants](https://www.myinstants.com/en/instant/fahhh-42300/) |
| `aol-youve-got-mail` | You've got mail — AOL recording (1.045 s) | [Myinstants](https://www.myinstants.com/en/instant/youve-got-mail/) · [Downloaded audio](https://www.myinstants.com/media/sounds/yougotmail.mp3) |
| `gta-mission-failed` | GTA V mission failed — first 4.000 s, with a 0.2 s end fade | [Voicemod Tuna](https://tuna.voicemod.net/sound/2c033143-ad5c-41de-9794-ef9f6954d044) · [Downloaded audio](https://content-storage.voicemod.net/794ea110da830fe4227f4ddadf295da0918ed9da1919c044bdafd5286a7aee7d) |

The GTA V source page identifies the clip as "GTA V Mission Failed". This identity comes from the community upload. It has not been checked against a recording from the game. The full source is 6.269 s. The distributed clip uses the first 4 s.

The downloaded recordings are community uploads. They were converted from MP3 to PCM WAV. Conversion does not improve the source quality. This repository grants no rights to third-party recordings or voices.

The rejected macOS speech demos and unused source clips remain outside the distributed app. The unused "Mergey outta here" version remains in Max's local source folder.

Choose a sound for each event in the app. All listed clips are available for explicit selection. Each person saves their own choices.

Sound IDs and file names remain stable so existing selections continue to work. A display name can change without changing the audio or its ID.

## Use-case groups

The `use_cases` array in each manifest entry controls the pad browser groups: `push`, `merge`, `ci`, and `comment`. A clip can appear in more than one group. The All view includes every clip.

These groups help people browse. They do not restrict an explicit event selection. The existing `event` field controls random-selection eligibility.

The original-voice Terio clip uses the final 2.3 seconds of the alternate recording that Max preferred. The unused opening cut remains in the local source folder.

## Shared library updates

The app reads the shared library from this repository's `main` branch. The shared audio is public. No repository invitation is required. The app uses each person's own GitHub credentials for its API requests.

The app checks at startup and once per hour. The enabled background watcher also checks once per hour. Select **Refresh Library** to check immediately. The app keeps a complete local copy for offline use. A failed or incomplete download keeps the previous library. New sounds appear without a new DMG. App code updates still need a new app bundle.

To publish a sound:

1. Add a PCM WAV file at `audio/<name>.wav`.
2. Add an entry to `manifest.json`.
3. Give the entry a unique `id`, display `text`, and matching `file` path.
4. Set `event` to `any`, `push`, `merge`, `ci`, or `comment`.
5. Set `use_cases` to the applicable categories: `push`, `merge`, `ci`, or `comment`.
6. Add the source to this document.
7. Merge the audio and manifest changes to `main`.

Keep existing IDs stable so saved sound selections continue to work. A new WAV file needs a manifest entry before it appears.

Double-click a library item to preview it. A single click does not play audio or highlight the item. The CUE buttons still play on one click.

Max requested removal of the original Wheezy clip. The removal is on `main`. `branch-outta-here` remains.

The shared manifest keeps `push`, `merge`, and `ci` in `use_cases` for older app versions. Newer categories use `additional_use_cases`. The mail clip includes `comment` there, so older apps can still receive all new audio.
