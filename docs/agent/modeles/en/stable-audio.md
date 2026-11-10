---
famille: stable-audio
natures: [musique, sfx_texte]
ids: [stable-audio-25, stable-audio-3, stable-audio-3-sfx]
voies: [fal]
releve: 2026-11-09
source: scenario-audio (scenario-labs/skills, MIT) ; music_service and sfx_service registries, Music and SFX screens of Sound & VFX
description: Use when you want long instrumental music or a pad with Stable Audio (Stability AI): Stable Audio 2.5 or 3, a track covering a whole video, ambience, drone, sound texture, duration set to the second, reproducible seed; or a sound effect from a description with Stable Audio 3 SFX (impact, whoosh, place ambience) in the SFX screen.
---
## Overview

Stable Audio returns **instrumental** audio from a description: never a sung voice, never lyrics. Two members serve
the Music screen (Sound & VFX) with a duration slider and a seed. The third, Stable Audio 3 SFX, serves the SFX
screen: a sound effect from a description, with no seed. Both music members are billed **per track**, whatever the
duration set.

## Quick reference

- [CHOICE] A track that must cover the whole video: set the duration to the edit's length. Stable Audio 3 goes
  further than 2.5 (read the range on the model card).
- [COST] Price per track: a long track costs the same as a short one. Generate at the final length rather than
  stitching pieces.
- [PROMPT] Music: genre, mood, instrumentation, texture, tempo, in one or two sentences. Textures work well: "slow
  evolving pad", "granular shimmer", "sub bass drone".
- [PROMPT] Progression: name it in plain words ("builds slowly, peaks near the end"). No structure field: precise
  timing is not guaranteed.
- [PITFALL] Typed lyrics are not sent: the app returns a note. For a song, take a model with a lyrics field.
- [PITFALL] No "instrumental" box here: the member does not sing. Writing "no vocals" is useless and may hurt.
- [PITFALL] A mood of the screen already carries a tempo: do not write a second one.
- [METHOD] Seed: set one from the first try. Same seed and same settings give the same track back; changing the seed
  alone gives a variant of the same prompt.
- [CHOICE] Not in the app yet: the negative prompt of Stable Audio 3 on screen (the server accepts it), several takes
  per run, reworking an existing audio.
- [PROMPT] SFX: one event per run, in the order source, material, action, space, intensity: "heavy oak door slams
  shut in a stone hallway, short tail". Physical words ("hollow", "muffled", "punchy") rather than moods.
- [PITFALL] SFX with no duration set: the sound is sent at the model's default duration, far longer than an impact.
  Set the duration to the event.
- [PITFALL] The SFX screen asks for two variations, but Stable Audio 3 SFX returns one per run. Relaunch for a
  variant.
- [COST] Stable Audio 3 SFX is "price to be measured": the quote is zero and the cap does not stop it, but fal bills
  it. Try it on a single sound before a series.
- [CHOICE] Stable Audio 3 SFX suits place ambiences and sounds of a few seconds; for a very brief impact, compare
  with another model of the SFX-from-description nature.

## Example

Brief: "a dark pad under my 3-minute short film about the sea floor, no voice".

Settings: Stable Audio 3, duration set to the edit's length, fixed seed. Description:

```
Dark ambient underwater score, slow evolving synth pad, deep sub bass pulses, distant metallic pings,
soft granular shimmer, builds slowly and fades out at the end, 60 BPM
```

Mood: none (the tempo is already written). If the track is too busy, keep the seed and remove "distant metallic
pings": only that part changes.

## Common mistakes

- Looking for a sung voice from Stable Audio: it does not make one.
- Stitching several short tracks to cover a video: one long track costs the same.
- Leaving the duration empty for a sound effect: the file comes out far longer than the event.
- Putting several sounds in one SFX prompt ("door slam then footsteps"): one event per run.
