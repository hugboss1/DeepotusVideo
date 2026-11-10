---
famille: cassetteai
natures: [musique]
ids: [cassetteai]
voies: [fal]
releve: 2026-11-09
source: scenario-audio (scenario-labs/skills, MIT) ; music_service registry, Music screen of Sound & VFX
description: Use when you want background music very fast and for next to nothing with CassetteAI: iterating on a mood, quick tries before a pricier model, instrumental track of a few minutes, background music for a video, billing per started minute.
---
## Overview

CassetteAI returns an instrumental track in a few seconds of compute, with a duration slider. No lyrics, no seed, no
instrumental box. It is billed **per started minute of output**: it is the cheapest way to try a mood before handing
it to a more polished model.

## Quick reference

- [COST] Started minute: a track of one minute and one second costs two minutes. Set the duration just under a round
  minute when possible.
- [METHOD] Iterate here: find the genre, instrumentation and tempo in several short tries, then replay the same
  description on a more polished model for the final version.
- [PROMPT] One or two sentences: genre, mood, instruments, tempo. Say how much room to leave for a voice-over
  ("sparse, leaves room for narration") when the track goes under a voice.
- [PITFALL] A mood of the screen already carries a tempo: do not write a second one in the description.
- [PITFALL] Typed lyrics are not sent; the app returns a note. For a song, take a model with a lyrics field.
- [PITFALL] The duration has a floor: the slider does not go below the model's minimum (read the model card). For a
  very short jingle, trim in the Editor.
- [PITFALL] No seed: each relaunch is a new take. Keep the good track.
- [CHOICE] Production quality below the pricier models (checked 2026-11): good for a demo, an internal video or a
  discreet background; listen on headphones before publishing.
- [CHOICE] Not in the app yet: several takes per run, a sung track.

## Example

Brief: "I don't know what style to put under my two-minute travel video; suggest some tracks".

Settings: CassetteAI, duration just under two minutes. Three runs, one description each:

```
Upbeat acoustic travel pop, bright ukulele, hand claps, light percussion, sunny and carefree, 116 BPM
```

```
Cinematic indie, warm electric guitar swells, soft piano, steady kick, wide and nostalgic, 90 BPM
```

```
Chill electronic, mellow synth chords, soft side-chained pads, relaxed groove, 100 BPM
```

The user picks by ear; the chosen description then goes to a more polished model for the final version, if it is
to be published.

## Common mistakes

- Setting the duration to a minute and a few seconds: the started minute is billed in full.
- Expecting a voice or lyrics: the app sends it only the description, for an instrumental track.
- Publishing a demo without a second listen: the production is simpler than the pricier models'.
