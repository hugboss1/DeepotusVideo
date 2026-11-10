---
famille: mirelo
natures: [sfx_texte, sfx_video]
ids: [mirelo-1.6, mirelo-video]
voies: [fal]
releve: 2026-11-09
source: scenario-audio (scenario-labs/skills, MIT) ; sfx_service registry (fal schemas reread on 2026-10-12)
description: Use when generating a sound effect with Mirelo SFX 1.6, from a description (several variants of one sound in a single run) or from a Montage video clip to get the video with sound, or when a Mirelo sound effect is refused for its duration or shown as "price to be measured".
---
## Overview

Mirelo SFX 1.6 makes sound effects. **Mirelo SFX 1.6** starts from a description and returns all its variations in
**a single run**. **Mirelo SFX 1.6 (video with sound)** starts from a clip and returns the **video with its sound
effects**: the app files it in the Library (Renders) and extracts its sound track, filed with the sounds. Screens:
Sound & VFX › SFX › "Generate SFX" and the Montage Sounds drawer › Generate ("Model" selector) for a description;
Sounds drawer › Generate › "From the video" for the video clip selected on the timeline.

## Quick reference

- [PROMPT] Description: one event per sound; the source, the material, the action, the space ("a heavy wooden door
  creaks open slowly, stone hallway, faint echo").
- [PROMPT] Concrete sound words ("creak", "thud", "crackle") rather than a general mood.
- [CHOICE] Several variants of one sound: Mirelo returns them in a single run (the number of variations is sent as
  the number of samples). Useful to pick the best of several steps, hits or impacts.
- [PITFALL] The app always sends the wanted number of samples, even one: without it, the provider makes and bills
  several.
- [PITFALL] Without a duration, the model's default is sent. Set the wanted duration; it is clamped to the range in
  Members.
- [CHOICE] The drawer's "Fidelity" slider is not sent to Mirelo: only the text counts.
- [CHOICE] Video: pick Mirelo when you want the **video already with sound** (a render to lay as is). For a sound
  track only, synced under the original clip, another member of the "From the video" list.
- [PITFALL] Video: the app sends the source clip's duration. A clip longer than the range in Members is refused
  before any run, never trimmed: trim the clip to the useful shot first.
- [PROMPT] Video: the description is optional; the picture sets when sounds happen. Write only the nature of a sound
  the model misses ("boots on wet cobblestones").
- [CHOICE] Video: no "Keep the voice" checkbox. What happens to the original speech in the returned video is to be
  confirmed: on a dialogue shot, prefer a member that keeps the voice, or mix in the Montage.
- [METHOD] The video with sound becomes a Library render (Renders): lay it in the Montage through that render; the
  extracted track serves when you prefer to keep the original picture.
- [COST] Both members are "price to be measured": quoted at zero but billed by fal, the spending cap does not stop
  them. Make one short test before a series.
- [METHOD] Apart from direct ElevenLabs, the button arms in two clicks: the first shows the quote, the second runs.
- [CHOICE] Not in the app yet: seed, audio format choice, several videos with sound in one run.

## Example

Brief: "I need a cellar door creak for my short film, I want to be able to choose".

Settings: Montage › Sounds drawer (B) › Generate, model Mirelo SFX 1.6, a duration of a few seconds, Variations: 3.
Description:

```
a heavy wooden cellar door creaks open slowly on rusty hinges, stone stairwell, faint echo
```

First click: the quote (price to be measured); second click: a single run, three sounds. Listen, keep the best as a
favorite, delete the others.

## Common mistakes

- Running several one-variation runs to compare: a single run with several variations is enough.
- Sending a long clip for sound: it is refused, trim it first.
- Taking the video with sound of a dialogue shot without listening: nothing asks to keep the speech.
- Running a series relying on the zero quote: the real price is billed by fal.
