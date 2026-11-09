---
famille: ltx
natures: [video_i2v, video_fl]
ids: [ltx-2.5-fast, ltx-2.5-pro]
voies: [fal]
releve: 2026-11-09
source: scenario-video, scenario-moderation (scenario-labs/skills, MIT) ; fal_service registry
description: Use when animating an image with LTX (Lightricks): LTX 2.5 Fast or LTX 2.5 Pro, image-to-video or a shot between a start and an end image, a longer shot at a low price, choosing between Fast and Pro.
---
## Overview

LTX 2.5 comes in two variants of the same model: Fast, and Pro, the "quality" variant. Both animate a start image and
take an end image. They have no seed and no negative field. The app drops the audio track, and leaves camera motion
and frame rate at their defaults.

## Quick reference

- [PROMPT] The camera has no field in the app: write it in the prompt, one named, slow move per shot ("slow push-in",
  "static camera").
- [PROMPT] The start image carries identity and style. The prompt describes motion, camera and pacing, not what the
  image already shows.
- [PROMPT] No negative field: state positively what must stay ("the background stays still"). A defect named in the
  prompt tends to appear.
- [PROMPT] The app drops the sound: write no sound line.
- [PITFALL] Durations come in fixed steps, different between Fast and Pro. A duration off the steps is moved to the
  nearest one, with a note: read the steps in Members.
- [PITFALL] No seed: every retry is a new take. Change one clause at a time and keep the good take.
- [CHOICE] Fast for long shots and tests; Pro for a short shot that needs more polish.
- [COST] Native sound is included in the price of both variants: dropping it lowers nothing.
- [COST] Draft in Fast at the final duration, then Pro with the same prompt if the shot fits its durations.
- [METHOD] End image: describe one continuous move from the first image to the second.

## Example

Brief: "a 9:16 Story showing my denim jacket on a rack, the camera slowly circling it".

Start image: the jacket on its rack, in 9:16, light workshop background. Prompt:

```
Slow orbit to the right around the denim jacket hanging on a metal rack, camera at chest height, steady and smooth.
The jacket sways slightly as the air moves, the fabric folds shifting with the motion. Soft window light from the
left stays constant. The rack and the workshop background stay still. No subtitles, no on-screen text.
```

Settings: LTX 2.5 Fast, medium duration, end image: no. If the motion works and the duration exists on Pro, rerun on
Pro with the same prompt: it is a new take.

## Common mistakes

- Asking for a duration off the steps and finding a shorter or longer clip afterwards: read Members before the shot.
- Writing "no camera shake": describe "steady and smooth" instead.
- Rerunning on Pro hoping for the same take, improved: with no seed, it is another render.
