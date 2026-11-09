---
famille: wan
natures: [video_i2v, video_fl]
ids: [wan-3.0]
voies: [fal]
releve: 2026-11-09
source: scenario-wan, scenario-video (scenario-labs/skills, MIT), registre fal_service
description: Use when animating an image with Wan 3.0 (Alibaba), wanting an end image, one long continuous shot, a seed to compare variants, a low-resolution draft before the final, or when a Wan clip changes the image content, shows unreadable text or strays from the written prompt.
---
## Overview

Wan 3.0 animates a start image, with an optional end image. It has a seed and a resolution choice, but no negative
field. The frame follows the start image: it has no format field. Its durations run long: read the maximum duration
in Members. The facts below come from the 2.x versions; they are carried over to 3.0 with caution.

## Quick reference

- [PROMPT] Describe only the motion, the camera and the pacing. Re-describing the image wastes the prompt.
- [PITFALL] A clip from an image does not change that image's content. For another setting or outfit, edit the
  image first, then animate it.
- [PROMPT] One action and one named camera move per shot. On a long shot, one slow, continuous action; time markers
  when there are several beats.
- [PITFALL] No negative field. Common exclusions go at the end of the prompt ("no subtitles, no on-screen text"); the
  rest is described positively.
- [PITFALL] Readable text in the image is unreliable across the family. Overlay it in the edit.
- [PITFALL] The 2.x versions rewrite the prompt by default before generating (checked 2026-11). If 3.0 does the
  same, a precise prompt can get diluted: to be confirmed on the first run. A clip that strays from an exact
  instruction is the sign.
- [PITFALL] The format follows the image: a landscape image gives a landscape clip. Prepare the start image in the
  wanted format before the run.
- [PITFALL] The end image must show the same setting, subject and light as the start image; otherwise the model
  invents a transition.
- [COST] Resolution weighs heavily on price: on Wan 2.7, 1080p cost about three times 720p (checked
  2026-11). Read the real gap in Members. Find the motion at low resolution, at the final duration.
- [PITFALL] The same seed and prompt do not give back the same take at another resolution. The draft validates the
  motion, not the final clip.
- [METHOD] The seed is for comparing: same image, same seed, same duration, a single prompt clause changed per run.
- [CHOICE] Not in the app yet: instruction-based video editing, generative reframing, character replacement,
  multiple shots, imported audio lip-synced. Do not promise them.

## Example

Brief: "A vertical Reel for the bakery: the shop window in the early morning, the camera slowly pulls back to reveal
the street, ending on the whole facade." The 9:16 start image (shop window in a close shot) is approved. The 9:16 end
image (whole facade, same light) is edited from the start image.

Prompt:

```
The camera slowly pulls back from the shop window and rises slightly, revealing the quiet street and the full
bakery facade. Warm light glows inside the shop while the early morning sky brightens gently. A few leaves drift
across the pavement. Steady, smooth motion. No subtitles, no on-screen text.
```

Settings: Wan 3.0; start image and end image: yes; medium duration; low resolution for the tries at a fixed seed,
then the highest for the chosen clip; the bakery's name is overlaid in Montage.

## Common mistakes

- Asking the prompt for a setting other than the image's: the clip keeps the image and ignores the instruction.
- Writing the shop's name in the prompt so it shows on the sign: it comes out garbled.
- Looking for a negative field: this member has none. Write common exclusions at the end of the prompt.
- Iterating straight at high resolution: each try costs several times a draft.
