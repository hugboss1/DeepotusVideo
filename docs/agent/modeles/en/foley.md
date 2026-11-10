---
famille: foley
natures: [sfx_video]
ids: [kling-v2a, hunyuan-foley, thinksound]
voies: [fal]
releve: 2026-11-09
source: scenario-audio (scenario-labs/skills, MIT) ; sfx_service registry (fal schemas reread on 2026-10-12)
description: Use when making synced sound effects (foley) from a Montage video clip with Kling video → sound, Hunyuan Video Foley or ThinkSound, when you want a video with sound or a sound track synced to the picture, when a video sound effect is refused (format, duration, missing description) or when unexpected background music appears.
---
## Overview

Three models that watch a clip's picture and draw its sound effects from it: steps, hits, rubbing, ambience, synced
to what moves. **Kling video → sound** returns a sound track only. **Hunyuan Video Foley** and **ThinkSound** return
the **video with sound**: the app files it in the Library (Renders) and extracts its sound track, filed with the
sounds. A single screen: Montage, video clip selected on the timeline, Sounds drawer › Generate › "From the
video", "Model" selector. The description comes from the "Describe the sound" field of the same tab.

## Quick reference

- [PROMPT] The picture decides **when** each sound comes; the description says **what** it is. Name the visible
  sources and their material ("leather boots on wet cobblestones"), not the action already shown.
- [PROMPT] Name sounds positively. For a track without music, describe only the noises; do not write "no music".
- [PITFALL] Kling video → sound and Hunyuan Video Foley require a description: without it, the app refuses before
  any run ("Describe the sound first"). ThinkSound does without.
- [PITFALL] Kling video → sound only accepts an `.mp4` or `.mov` clip within a short duration range; outside it, the
  refusal names the range, before any run. Its description is short: the refusal gives the limit, the app never
  cuts it.
- [CHOICE] Kling video → sound: the app turns off its background music (otherwise the provider adds one by
  default). You only get the sound effects, to lay under the original clip.
- [CHOICE] Sound track only, original picture intact: Kling video → sound. Video with sound ready to lay: Hunyuan
  Video Foley or ThinkSound.
- [CHOICE] No "Keep the voice" checkbox: nothing asks these models to keep a dialogue shot's speech (its exact fate
  is to be confirmed). Preferably add sound to a shot without speech and mix the voice in the Montage.
- [METHOD] One shot at a time. Several shots in one clip blend the ambiences; trim the clip to the useful shot
  first.
- [METHOD] Listen to the result while watching it, at the contact moments (foot on the ground, object set down): a
  sound early or late shows at once.
- [METHOD] The button arms in two clicks: the first shows the server's quote, the second runs.
- [COST] Kling video → sound: fixed price per video, whatever its duration within the allowed range.
- [COST] Hunyuan Video Foley and ThinkSound are "price to be measured": quoted at zero, billed by fal, the spending
  cap does not stop them. ThinkSound is billed on compute time, unknown in advance. One short test first.
- [CHOICE] Kling video → sound is a sound effects model; it has nothing to do with the Kling video generators.
- [CHOICE] Not in the app yet: Kling's background music, Kling's ASMR mode, Hunyuan's and ThinkSound's own
  settings.

## Example

Brief: "my cooking shot is silent: garlic sizzling, a wooden spoon scraping the pan; I want the video with sound".

Settings: Montage, the clip trimmed to the pan shot alone, selected; Sounds drawer (B) › Generate, model Hunyuan
Video Foley. In "Describe the sound":

```
garlic sizzling in hot olive oil in a steel pan, a wooden spoon scraping the pan bottom, quiet home kitchen
```

"From the video": first click, the quote (price to be measured); second click, the run. The video with sound lands
in the Library (Renders), its track in the sounds. The sizzle lags behind the spoon: retry with the same
description, or try ThinkSound on the same clip.

## Common mistakes

- Running Kling video → sound or Hunyuan without a description: immediate refusal.
- Sending Kling a `.webm` or too long a clip: refused; convert or trim first.
- Adding sound to a multi-shot clip in one go: sounds bleed from one shot to the next.
- Relying on Hunyuan's or ThinkSound's zero quote for a series: the real price is billed by fal.
