---
famille: veo
natures: [video_i2v, video_fl]
ids: [veo-3.1-fast-fal, veo-3.1-fal, veo-3.1-lite-fal]
voies: [fal]
releve: 2026-11-09
source: scenario-veo (scenario-labs/skills, MIT) ; fal_service registry
description: Use when animating an image with Veo (Google): Veo 3.1, Veo 3.1 Fast or Veo 3.1 Lite served by fal, image-to-video or a transition between a start and an end image, a long cinematic prompt, a fixed seed to compare wordings, the negative field, a Google moderation refusal, extending a Veo clip, choosing between Lite and 3.1.
---
## Overview

The three Veo members go through fal; the direct Google entries are retired. Each one animates a start image and
takes an end image, a seed and a negative field. With an end image, the app switches to the transition endpoint on
its own. The app always drops the audio track.

## Quick reference

- [PROMPT] Present-tense prose, in this order: framing and camera, subject, action, context, style. One main arc per
  shot.
- [PROMPT] Veo follows developed prompts: aim for about 90 to 250 words (checked 2026-11). In image-to-video, those
  words describe motion, camera and light, not what the image already shows.
- [PROMPT] Several beats: one line per beat with its time marker, all within the chosen duration.
- [PROMPT] Start → end transition: describe one continuous move that leads from the first image to the second.
- [PROMPT] Describe the wanted scene, not a list of negations. The negative field discourages a few precise defects
  ("text, watermark, extra fingers").
- [PROMPT] The app drops the sound: write no dialogue, effect or ambience. Sound is laid in the Montage.
- [PITFALL] A start image that does not match the requested format may be cropped. Prepare it at the delivery format
  before the shot.
- [METHOD] Comparing wordings: keep the same seed and change one clause at a time. A seed does not promise the same
  take from one member to another.
- [CHOICE] Lite for tests and series, Fast for everyday use, 3.1 for the final shot that has to hold.
- [COST] Lite costs much less than 3.1 for the same shot (actual gap in Members). Draft in Lite at the final
  duration, final in 3.1 or Fast with the same prompt.
- [COST] On 3.1 and Fast, the price does not depend on resolution: take the highest. On Lite, it changes the price.
- [COST] The app's Veo extension cost more than a fresh shot (checked 2026-11). Aim for the shot in a single pass
  first, at the longest duration read in Members.
- [PITFALL] Extension: the prompt is mandatory, and a clip from another model may be refused or poorly extended. To
  continue a shot, the clip's last frame can serve as the start image of a new shot.
- [CHOICE] Moderation: Google's filter is the strictest on brands, known characters and likenesses of real people.
  The three members share this filter, and a higher tier does not loosen it. After a refusal, switch to another
  provider with the same prompt.
- [CHOICE] Not in the app yet: text-to-video and reference images (subject or style).

## Example

Brief: "a vertical TikTok video: my coffee cup on the terrace table, steam rising, morning light; I want to end on a
close-up of the cup".

Start image: the terrace in 9:16, cup on the lower third. End image: the same cup in close-up, generated from the
start image. Prompt:

```
Medium shot slowly pushing in to a close-up, camera at table height, steady and smooth. A white ceramic cup of black
coffee sits on a weathered wooden café table. Thin steam rises from the cup and curls to the left in a light breeze.
Low morning sun from the right rakes across the table and catches the steam, warm highlights on the rim. Leaves in
the soft background sway gently. The push-in is one continuous move that ends framed tight on the cup. Natural
photographic look, shallow depth of field, no subtitles, no on-screen text.
```

Negative: "text, logo, watermark, extra cups". Settings: Veo 3.1 Lite for the test, longest duration, end image: yes,
seed fixed. Prompt and seed kept for the final in Veo 3.1.

## Common mistakes

- Writing a ten-word prompt: Veo fills the gap its own way. Give camera, light and motion in sentences.
- Putting the defects to avoid in the prompt ("no blur, no people"): they show up. Put them in the negative field.
- Changing the prompt and the seed at the same time: you no longer know what made the difference.
- Relying on extension to lengthen a short shot: it costs more than a fresh shot.
