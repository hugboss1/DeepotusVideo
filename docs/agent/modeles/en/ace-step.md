---
famille: ace-step
natures: [musique]
ids: [ace-step]
voies: [fal]
releve: 2026-11-09
source: scenario-ace-step, scenario-audio (scenario-labs/skills, MIT) ; music_service registry, Music screen of Sound & VFX
description: Use when you want a song with lyrics at the lowest price with ACE-Step: sung song or instrumental, adjustable duration, reproducible seed, [verse] [chorus] [bridge] [inst] tags, genres as keywords, song demo, many tries before a pricier model.
---
## Overview

ACE-Step (first generation, served by fal) sings structured lyrics or plays an instrumental. It has **no description
field**: the app sends the description as a list of **tags** (genres, mood, instruments). It takes an adjustable
duration and a seed; it is billed per second of the requested duration, which makes it the cheapest member to
iterate with.

## Quick reference

- [PROMPT] Description = comma-separated keywords, not sentences: "synth-pop, upbeat, female vocals, 80s drum
  machine, bright, 120 BPM". This sheet overrides the full-sentence rule here.
- [PROMPT] The voice timbre is also said in tags: "male vocals", "soft female vocals", "choir".
- [METHOD] "Instrumental" box checked (default): the app sends `[inst]` and nothing else; the lyrics editor is hidden.
  Uncheck the box to write lyrics.
- [PITFALL] Box unchecked but lyrics empty: ACE-Step still plays an instrumental (`[inst]`). It does not write
  lyrics itself.
- [PROMPT] Lyrics: the editor adds verse, chorus and bridge; the app converts them to lowercase tags `[verse]`,
  `[chorus]`, `[bridge]` (and `[intro]`, `[outro]`). An unknown tag is sent as is.
- [PROMPT] Short sections, two to four lines; a blank line between sections. End with `[outro]` for a clean ending.
- [COST] Billed per second of the duration set, not of the returned one: set the slider to the useful length.
- [METHOD] Demo: settle the words, structure and tempo on ACE-Step, at a short duration; move to a more polished
  model only once the song holds.
- [METHOD] Seed: set one from the first try. Same seed and same settings give the same take back; changing one word
  of the lyrics gives another take.
- [PITFALL] Voice quality and diction are below the pricier models: listen to every line before publishing.
- [CHOICE] Not in the app yet: ACE-Step 1.5 and its editing modes (cover in another style, rewriting a section,
  adding a track, stem separation), dedicated tempo and key fields, several takes per run.

## Example

Brief: "a funny little song about my cat for a TikTok video, in English, cheap, I want to test several versions".

Settings: ACE-Step, "instrumental" box unchecked, short duration, fixed seed. Description:

```
funk, playful, male vocals, slap bass, clavinet, tight drums, horn stabs, 105 BPM
```

Lyrics:

```
[verse]
He knocks the glass right off the shelf
Then blames the dog and licks his paw

[chorus]
Mister Whiskers, king of the night
Sleeps all day, then starts a fight

[outro]
King of the night
```

For another version, change only the seed; for another feel, change only the tags.

## Common mistakes

- Writing the description as long sentences: the tags get blurry.
- Re-checking "instrumental" after writing lyrics: the editor hides and the lyrics are not sent.
- Expecting lyrics written by the model with an empty editor: it plays an instrumental.
- Setting the duration to the maximum "to see": the bill follows the requested duration.
