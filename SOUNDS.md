# Sound library

Each event can use any listed clip. Preview and select clips locally in the app. Existing sound choices are not changed when a new clip is added.

| ID | Clip | Source |
| --- | --- | --- |
| `stackaholics` | Stackaholics! We build different! | TagMyBeat; Max approved the generated clip and confirmed source-voice authorization. |
| `stackaholics-welcome-to-main` | Stackaholics! Welcome to main! | TagMyBeat; same authorized reference voice. |
| `stackaholics-thats-a-wrap` | Stackaholics! That's a wrap! | TagMyBeat; same authorized reference voice. |
| `branch-outta-here` | Branch outta here! | TagMyBeat; Max confirmed authorization for the Wheezy reference voice. |
| `wheezy-outta-here` | Original Wheezy drop | [Myinstants](https://www.myinstants.com/en/search/?name=wheezy+outta+here) |
| `dj-khaled-another-one` | Another one | [Myinstants](https://www.myinstants.com/en/search/?name=dj+khaled+another+one) |
| `lego-break-apart` | LEGO death — break-apart clip (1.65 s) | [Myinstants](https://www.myinstants.com/en/instant/lego-breaking-57805/) · [requested reference](https://www.youtube.com/watch?v=8Z0JhcWURDY) |
| `terio-kill-em` | Terio kill ’em — original-voice ending cut (2.3 s) | [Downloaded audio](https://www.myinstants.com/media/sounds/terio-mp3.mp3) |
| `metal-gear-alert` | Metal Gear Solid Alert (1.57 s) | [Downloaded audio](https://www.myinstants.com/media/sounds/tindeck_1.mp3) |
| `windows-xp-error` | Windows XP Error sound (download) (1.02 s) | [Downloaded audio](https://www.myinstants.com/media/sounds/erro_5kzwjlL.mp3) |
| `fahhh` | Fahhh (2.28 s) | [Myinstants](https://www.myinstants.com/en/instant/fahhh-42300/) |

The downloaded recordings are community uploads. They were converted from MP3 to PCM WAV. Conversion does not improve the source quality. This repository grants no rights to third-party recordings or voices.

The rejected macOS speech demos and unused source clips remain outside the distributed app. The unused "Mergey outta here" version remains in Max's local source folder.

The default push clip is `stackaholics`. The default merge clip is `branch-outta-here`. The default CI clip is `lego-break-apart`. Each person can change these choices.

## Use-case groups

The `use_cases` array in each manifest entry controls the pad browser groups: `push`, `merge`, and `ci`. A clip can appear in more than one group. The All view includes every clip.

These groups help people browse. They do not restrict an explicit event selection. The existing `event` field controls random-selection eligibility.

The original-voice Terio clip uses the final 2.3 seconds of the alternate recording that Max preferred. The unused opening cut remains in the local source folder.
