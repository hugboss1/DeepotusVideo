---
famille: sonilo
natures: [sfx_texte, sfx_video]
ids: [sonilo-1.1, sonilo-video]
voies: [fal]
releve: 2026-11-09
source: scenario-sonilo, scenario-audio (scenario-labs/skills, MIT) ; sfx_service registry (fal schemas reread on 2026-10-12)
description: Use when generating a sound effect with Sonilo 1.1, from a description (long sound, ambience, layered effects) or from a Montage video clip (sound effects synced to the picture, sound track only), when keeping the speech of a video while adding effects, or when looking for a video sound effect priced per second.
---
## Overview

Sonilo 1.1 makes sound effects, never speech or singing. Two members: **Sonilo 1.1** starts from a description,
**Sonilo 1.1 (video)** starts from a video clip and returns a **sound track only**, synced to the picture, to lay
under the clip. Both return WAV. Screens: Sound & VFX › SFX › "Generate SFX" and the Montage Sounds drawer ›
Generate ("Model" selector) for a description; Sounds drawer › Generate › "From the video" for the video clip
selected on the timeline. Sonilo video is the model offered by default for a clip.

## Quick reference

- [PROMPT] Description: one event per sound. Order: source, material, space, intensity ("a heavy steel door slams
  shut, concrete stairwell, loud and close").
- [PROMPT] Physical words rather than moods: "hollow", "muffled", "punchy" describe a sound; "scary" tells the model
  nothing.
- [PROMPT] Sonilo has no time markers inside a described sound: state the duration intent in the text ("a short
  click", "a long rumbling roll") **and** set the duration.
- [PITFALL] Without a duration, the model's default is sent, not a length fitted to the sound: set the wanted
  duration. It is clamped to the range in Members.
- [CHOICE] Long, continuous description (ambience, rumble, wind): Sonilo covers the longest duration range of the
  list (Members).
- [PROMPT] Video: the picture decides **when** the sound comes, the description only **what** it sounds like. Sound
  effects follow the picture; the original track only serves "Keep the voice".
- [PROMPT] Video: an empty description is allowed and often the best: the model reads the clip and adds sound to
  each shot. Write only to fix a missed sound ("wet footsteps on gravel").
- [CHOICE] "Keep the voice" (Sonilo video's checkbox only) asks the model to keep the video's speech. Its exact
  effect on the returned track is to be confirmed: listen to the first test.
- [PITFALL] Sonilo never returns a generated voice or sung music. For a voice, the voice sheets; for music, the
  music nature.
- [METHOD] Sound effects and music are generated as separate tracks and mixed in the Montage. Never send a clip that
  already has effects to a tool that replaces its whole track: the effects disappear.
- [CHOICE] No seed: each run is a new take. Keep the good takes in the Library.
- [COST] Description: per second of rendered sound, and per variation (each variation is a run). Sound & VFX's
  "Generate SFX" always runs two.
- [COST] Video: per second **of the source clip**. Trim the clip to the useful shot before adding sound.
- [METHOD] Apart from direct ElevenLabs, the button arms in two clicks: the first shows the server's quote, the
  second runs.
- [CHOICE] The drawer's "Fidelity" slider is not sent to Sonilo: only the text counts.
- [CHOICE] Not in the app yet: per-time-range descriptions (`segments`), start offset, audio format choice, Sonilo
  music, returned video with the mixed track.

## Example

Brief: "add sound to my shot of a skater landing on concrete; he shouts "yes!" on landing and I want to keep his
shout".

Settings: Montage, video clip selected on the timeline, then Sounds drawer (B) › Generate › "From the video". Model
Sonilo 1.1 (video), "Keep the voice" ticked. First test with an empty description. The wheels sound too smooth:
second test with

```
rough urethane wheels rolling on cracked concrete, hard deck slap on landing, open street air
```

First click: the quote per second of the clip; second click: the run. The track joins the Library (sounds), linked
to the clip; lay it under the clip in the Montage.

## Common mistakes

- Describing the whole scene in one sentence for a sound from a description ("door, steps, scream"): one event per
  sound.
- Adding sound to a whole multi-shot clip for a single effect: the price follows the whole clip duration.
- Writing a detailed prompt on the first video test: the empty description often does better.
- Expecting a voice or singing from Sonilo: it does not produce any.
