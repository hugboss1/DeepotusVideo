---
famille: kling
natures: [video_i2v, video_fl]
ids: [kling-v3-pro, kling-v3-standard, kling-v3-turbo-pro, kling-v4]
voies: [fal]
releve: 2026-11-09
source: scenario-kling, scenario-video (scenario-labs/skills, MIT), registre fal_service
description: Use when animating an image with Kling (Kling 4.0, Kling v3 Pro, v3 Standard, v3 Turbo Pro), choosing between these members, wanting an end image to pin where the shot lands, a negative field, one long continuous shot, or when a Kling clip moves too much, freezes, drifts or comes out in the wrong format.
---
## Overview

Kling (Kuaishou) animates a start image, with an end image on three of its four members. The app offers v3 Standard,
v3 Pro, v3 Turbo Pro and 4.0. No member has a format field: the frame follows the start image. No member has a seed:
every run is a new take.

## Quick reference

- [CHOICE] v3 Standard is for finding the motion at a lower cost. v3 Pro is for the final take of the same shot.
- [CHOICE] v3 Turbo Pro does **not** accept an end image or a negative. It suits a free shot where only the opening
  matters. For an imposed landing, use v3 Pro, v3 Standard or 4.0.
- [CHOICE] 4.0 is the longest member (read the maximum duration in Members). It takes an end image and a
  resolution, but no negative and no seed.
- [PROMPT] Director's order: subject, one action, one named camera move, then light and style. Natural sentences,
  not a keyword list.
- [PROMPT] Compound move ("dolly in while orbiting"): keep one dominant move per shot. The second one goes in
  another shot.
- [PROMPT] Negative (v3 Pro and v3 Standard only): a short list of artifacts. A long list stiffens the motion.
- [PITFALL] A busy scene holds better in a short shot. Over a long duration, ask for one simple, continuous action,
  or the clip hesitates or freezes; splitting into several shots works better.
- [PITFALL] The format follows the image: a landscape image gives a landscape clip. Prepare the start image in the
  wanted format before the run.
- [PITFALL] The end image pins the landing. It must show the same setting, subject and light as the start image;
  otherwise the model invents a transition (dissolve, morphing).
- [METHOD] Kling does not extend a clip. To continue, extract the last frame of the kept clip and use it as the start
  image of a new run. Write that prompt from what this frame shows, then edit with a hard cut.
- [PITFALL] v3 Turbo Pro and 4.0 have no sound switch: the app removes the track they deliver on download. Ask for
  neither music nor silence in the prompt; sound is laid in the Edit.
- [COST] With no seed, redoing in Pro a shot found in Standard gives another take. If the Standard take works, keep
  it and upscale it rather than re-rendering.
- [CHOICE] Not in the app yet: several shots in one run, element-based characters, identity references, talking
  head. Do not promise them.

## Example

Brief: "A vertical video for TikTok: our steaming coffee cup on a wooden table, the camera moves in gently and ends
on a close-up of the cup." The 9:16 start image (cup in a medium shot) is approved. The 9:16 end image (same cup in
close-up, same light) is edited from the start image.

Prompt:

```
Steam rises slowly from the coffee cup. The camera performs a slow, steady dolly in toward the cup and settles on
a close-up. Soft morning window light from the left stays constant. Smooth, natural motion.
```

Settings: Kling v3 Standard for a first try, then v3 Pro; start image and end image: yes; short duration; negative:
"subtitles, on-screen text, warped cup, flicker". The logo and tagline are overlaid afterwards in Montage.

## Common mistakes

- Picking v3 Turbo Pro for a shot that must end on a precise image: it has no end image. Switch to v3 Pro or 4.0.
- Starting from a landscape image for a vertical video: the clip keeps the image's format. Crop or regenerate the
  image first.
- Writing two camera moves and three actions in a long shot: the motion blurs or stops.
- Filling the negative with twenty terms: the subject barely moves. Three or four artifacts are enough.
- Re-rendering in Pro hoping to get the Standard take back: with no seed, it is another clip.
