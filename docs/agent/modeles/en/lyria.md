---
famille: lyria
natures: [musique]
ids: [lyria3, lyria-3.5]
voies: [fal]
releve: 2026-11-09
source: scenario-audio (scenario-labs/skills, MIT) ; music_service registry, Music screen of Sound & VFX
description: Use when generating background music with Lyria (Google): Lyria 3, the default model of the Music screen, or Lyria 3.5; pad, jingle, short loop, mood music for a Reel or a video, instrumental track, sung voice without set lyrics, music negative prompt, tempo in BPM, Lyria 3 fixed duration.
---
## Overview

Lyria composes a track from a description, with no lyrics field. Lyria 3 is the default model of the Music screen
(Sound & VFX): its duration is fixed; Lyria 3.5 picks its own. Neither takes a seed. The price is per track,
whatever length comes back. The track lands in the Library (sounds), ready for the Editor.

## Quick reference

- [PROMPT] Useful order: genre, mood, instrumentation, production, tempo. The start of the prompt weighs most; a
  chosen mood goes in front of the description.
- [PROMPT] Describe a simple progression in musician's words: "starts with solo piano, strings join halfway, ends on
  a held chord". No per-second timing: with no structure field, nothing guarantees it.
- [PITFALL] The screen's moods already contain a tempo. Writing a second one in the description puts two tempos in
  the prompt: use either the mood or the written tempo, not both.
- [PROMPT] Write the tempo as "92 BPM". The server accepts a `bpm` field that replaces any written tempo, but the
  screen does not expose it yet.
- [METHOD] Instrumental: the "instrumental" box (checked by default). The app sends it as a negative prompt (vocals,
  singing, lyrics, choir), never in the description. Do not write "no vocals": a word draws what it names.
- [CHOICE] Box unchecked: Lyria may sing, but the words are its own. Exact lyrics need a music model with a lyrics
  field ("lyrics" column of Members).
- [PITFALL] A duration sent to Lyria is ignored; the app returns a note. Lyria 3 always returns the same length (read
  the model card). To cover a longer video, take a model with an adjustable duration.
- [CHOICE] Lyria 3 for a pad or a short jingle, at the lowest price per track; Lyria 3.5 when quality comes first
  and the length may vary.
- [COST] Flat price per track: every try costs the same. Listen before relaunching, and change one thing in the
  prompt per relaunch.
- [PITFALL] No seed: each relaunch is a new take. Keep the good track.
- [CHOICE] Not in the app yet: a free "negative prompt" field on screen (the server accepts it), the tempo field,
  several takes per run.

## Example

Brief: "a calm loop under my recipe Reel, no voice".

Mood: none. Description:

```
Warm acoustic lo-fi, soft brushed drums, muted nylon guitar, gentle upright bass, cozy kitchen mood,
relaxed and steady, clean mix with room for a voice-over, 84 BPM
```

Settings: Lyria 3, "instrumental" box checked. Listen to the track in the Editor under the voice-over; if the
guitar covers the voice, relaunch with "sparse arrangement" instead of "gentle upright bass".

## Common mistakes

- Writing "no vocals" in the description instead of checking "instrumental": singing may appear.
- Picking the "Hype" mood then writing "slow, 70 BPM": two tempos contradict each other.
- Promising an exact duration with Lyria: the screen has no slider for it, and a duration passed through the API is
  not sent.
- Pasting lyrics into the description: nothing guarantees they are sung as written.
