---
famille: gemini-omni
natures: [video_i2v, video_fl]
ids: [gemini-omni-flash, gemini-omni-flash-google]
voies: [fal, gemini]
releve: 2026-11-09
source: scenario-gemini-omni, scenario-video, scenario-moderation (scenario-labs/skills, MIT), registre fal_service
description: Use when animating an image with Gemini Omni Flash 1.1 (Google), through the fal route or the Google key, when choosing between these two twins, when replacing a retired Google Veo 3.1, when a Google render is refused by moderation, or when wondering why the clip comes with sound.
---
## Overview

Gemini Omni Flash animates a start image, plus an end image if you give one. It comes as two twins: the fal route
(fal balance) and the Google route (Google key, Google credits). It is the same model on both sides. It has neither a
seed nor a negative field. It always generates a sound track.

## Quick reference

- [PROMPT] With a start image, describe the motion that carries it forward, not a still scene. The image already sets
  the setting and the style.
- [PROMPT] Full sentences: one action, one named camera move, the light. Mood words alone do not survive rendering.
- [PITFALL] A clip holds a single continuous moment. A multi-scene story in one run gets muddled: split it into shots
  and edit them together.
- [PITFALL] With no negative field, an exclusion goes in the prompt, phrased positively when possible. Keep only
  "no subtitles, no on-screen text".
- [PITFALL] With no seed, two runs of the same prompt always differ. To keep a take, keep the file, not the recipe.
- [PITFALL] The model always delivers a sound track; it has no switch. If the project has its own voice-over or music,
  plan to replace the track in the edit (to be confirmed on the first run).
- [PROMPT] If the generated track will be kept, end the prompt with a positive sound line ("soft wind, distant
  birds"); dialogue goes in quotes. Without a sound line, the model picks on its own.
- [PROMPT] Never write "no music": name the sounds you want.
- [CHOICE] fal route or Google route: pick by the key present and the balance to spend. Settings and expected output
  are the same.
- [CHOICE] The Veo 3.1 models served by the Google key are retired; this Google twin replaces them.
- [CHOICE] Moderation: the family goes through Google's filter, the strictest recorded (checked 2026-11). After a
  refusal, try the twin on the other route first, then a family from another provider.
- [COST] The app's quote prices each resolution differently. A public source recorded the opposite, the same price
  at any resolution: to be confirmed on the first run by comparing quote and invoice.
- [COST] The cheapest draft is a short duration. The higher resolution is upsampled (checked 2026-11): it adds no real
  detail.
- [METHOD] End image: give it only to land on a precise pose, with the same framing and the same subject as the start
  image.
- [CHOICE] Text-to-video, identity references, video editing and video extension exist at Google but are not in the
  app yet.

## Example

Brief: "A portrait of a cyclist in the city at sunset; I want a short vertical video where she sets off and rides
away, with street sound."

Prompt:

```
The cyclist pushes off and rides slowly away down the street, her jacket moving in the wind. The camera holds
still at eye level and lets her shrink into the warm evening light. Sound: light city traffic, a bicycle chain
clicking, distant voices. No subtitles, no on-screen text.
```

Settings: start image = the portrait; end image: no; vertical format in the format field; short duration; lowest
resolution; route by the key present; sound track kept or replaced in the edit depending on the project.

## Common mistakes

- Telling three scenes in one run: the model holds only one. One run per shot.
- Paying for the higher resolution to gain detail: it would be upsampled (checked 2026-11). Keep the lowest unless
  delivery requires more.
- Rewriting a refused prompt three times: switch to the twin first, then to another provider.
- Forgetting the clip comes with sound: listen to it, or replace it.
- Describing again the outfit and face already visible in the image: those words fight the image.
