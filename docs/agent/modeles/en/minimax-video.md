---
famille: minimax-video
natures: [video_i2v, video_fl]
ids: [h3-max]
voies: [fal]
releve: 2026-11-09
source: scenario-minimax-video, scenario-video (scenario-labs/skills, MIT), registre fal_service
description: Use when animating an image with MiniMax H3 Max (Hailuo), when steering the camera with bracketed commands, when pinning a start frame and an end frame, when the background wobbles or the shot drifts, or when wondering whether the prompt gets rewritten or the clip comes with sound.
---
## Overview

H3 Max animates a start image, plus an end image if you give one. The frame follows the image: there is no format
field. It has a seed. It reads the prompt closely, including bracketed camera commands. The app always sends the
"balanced" prompt expansion mode: the text may be reworded before rendering.

## Quick reference

- [PROMPT] Describe only the motion: subject, one action, camera, light that changes. The image already carries the
  setting and the style.
- [PROMPT] Camera moves are named in brackets: `[Push in]`, `[Pull out]`, `[Pan left]`, `[Tilt up]`,
  `[Truck right]`, `[Pedestal up]`, `[Zoom out]`, `[Tracking shot]`, `[Static shot]`.
- [PROMPT] Several commands inside one bracket play together (`[Pan left, Pedestal up]`); separate brackets play one
  after the other. Three commands per bracket at most (checked 2026-11).
- [PITFALL] Past two or three motion cues, the background wobbles and textures shimmer. Keep one camera command and
  one action.
- [PITFALL] Even with no motion requested, the shot drifts. For a still shot, write `[Static shot]` and "locked camera,
  tripod mounted".
- [PITFALL] The prompt is rewritten by the "balanced" expansion, which the app cannot turn off yet. Exact wording may
  shift: check on the output that the requested action is there.
- [PROMPT] Keep the prompt short and dense. The recorded limit is 2,000 characters, and much shorter prompts were
  refused through an intermediary (checked 2026-11).
- [PITFALL] The model always delivers a sound track; it has no switch. Plan to replace it in the edit with the
  project's voice-over or music (to be confirmed on the first run).
- [PROMPT] Do not write "no music" to silence the track: name the sounds you want instead, or say nothing about
  sound.
- [CHOICE] A public source capped image-to-video at 768P, while the app's registry also offers 1080p. To be
  confirmed on the first 1080p run: check the size actually delivered.
- [CHOICE] When the app asks for 720p, the provider receives 768P, its nearest resolution. The delivered file is
  therefore not exactly 720p tall.
- [COST] Draft first at the lowest resolution in Members, at the final duration. The draft validates composition and
  motion, not pixels: changing resolution is a new generation, even with the same seed.
- [METHOD] End image: give it only when the shot must land on a precise pose. It must keep the same framing and the
  same subject as the start image.
- [CHOICE] Identity references, text-to-video, extension, the Turbo tier and person replacement exist at MiniMax but
  are not in the app yet.

## Example

Brief: "My product photo of a perfume bottle on a wet rock; I want a vertical social shot, the camera moving in
slowly, drops falling."

Prompt:

```
[Push in] Slow, steady approach toward the perfume bottle on the wet rock. A few water drops fall from above and
splash softly on the stone beside the bottle. Light ripples move across the glass. The bottle stays still and sharp.
No subtitles, no on-screen text.
```

Settings: start image = the product photo already cropped to vertical (the frame follows the image); end image: no;
short duration; lowest resolution for the draft, then the highest once the motion is approved; seed noted to come
back to the kept draft; the clip's sound track replaced in the edit.

## Common mistakes

- Stacking "orbit", "zoom", "pan" and "dolly" in one sentence: the background wobbles. One bracketed command.
- Giving a landscape image and hoping for a vertical clip: there is no format field. Crop the image to vertical
  before the run.
- Judging final grain on the low-resolution draft, then being surprised the final differs: it is another generation.
- Relying on an exact phrase while the expansion rewords it: review the output.
- Publishing the clip with its generated sound track without listening to it.
