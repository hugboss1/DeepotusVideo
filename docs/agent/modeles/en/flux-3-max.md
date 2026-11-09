---
famille: flux-3-max
natures: [video_i2v, video_fl]
ids: [flux-3-max]
voies: [fal]
releve: 2026-11-09
source: scenario-video, scenario-moderation (scenario-labs/skills, MIT), registre fal_service
description: Use when animating an image into video with FLUX 3 Max (Black Forest Labs), when you want a start frame and an end frame on the same model, a loop that returns to its pose, a seed to recover a take, a silent clip, or a fallback after a moderation refusal at a stricter provider.
---
## Overview

FLUX 3 Max animates a start image, plus an end image if you give one, in the same call. It has a format field and a
seed. It has no negative field. Its sound switch exists, and the app always leaves it off: the clip arrives silent.
Little public feedback exists on this video model; the sheet sticks to the general video rules and the registry.

## Quick reference

- [PROMPT] Describe only the motion: one action, one named camera move, the light that changes. The image already
  carries the setting and the style.
- [PROMPT] One camera and one action per shot. When the shot has two beats, give them in order, with a time cue.
- [PITFALL] With no negative field, an exclusion goes in the prompt, phrased positively when possible. Keep
  "no subtitles, no on-screen text".
- [PITFALL] The format is set in the format field. If the image does not match it, the model crops or fills in: crop
  the image before the run.
- [PROMPT] No need to write a sound line: the clip is silent. Sound comes later from the project's voice-over, music
  or sound effects.
- [METHOD] End image: give it only to land on a precise pose. It keeps the same framing and the same subject as the
  start image.
- [METHOD] Loop: give the same image as start and end, and describe a motion that leaves and comes back. Check the
  seam by playing the clip on loop.
- [METHOD] Seed: note it on a kept take. The same seed with the same prompt and settings lets you find it again;
  change one clause at a time.
- [CHOICE] Moderation: FLUX models are among the most permissive recorded (checked 2026-11). It is a reasonable
  fallback after a refusal at a stricter provider, at a similar cost.
- [COST] Draft first at the lowest resolution in Members, at the final duration. Changing resolution is a new
  generation, even with the same seed.
- [CHOICE] Text-to-video and multi-keyframe video exist at Black Forest Labs but are not in the app yet.

## Example

Brief: "The illustration of my mascot, a fox in a scarf; I want a vertical video that loops on my profile: it blinks
and its scarf floats."

Prompt:

```
The fox stands in place and blinks once, slowly. Its scarf lifts gently in a light breeze, then settles back to
its starting position. The camera stays locked and still. The background does not change. No subtitles, no
on-screen text.
```

Settings: start image = the illustration cropped to vertical; end image: yes, the same image, to close the loop;
vertical format in the format field; short duration; lowest resolution for the draft; seed noted on the kept take;
sound added in the edit.

## Common mistakes

- Writing a sound line and expecting to hear it: the clip arrives silent.
- Giving an end image whose framing differs from the start image: the model invents a camera path.
- Asking for several actions and several camera moves in the same shot: the motion gets muddled.
- Rerunning without noting the seed, then never finding the good take again.
- Changing three clauses at once between two runs: you no longer know which one mattered.
