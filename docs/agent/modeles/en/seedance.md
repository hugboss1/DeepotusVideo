---
famille: seedance
natures: [video_i2v, video_fl]
ids: [seedance-v1-pro, seedance-2, seedance-2-fast, seedance-2.5]
voies: [fal]
releve: 2026-11-09
source: scenario-seedance, scenario-seedance-drafts, scenario-seedance-storyboard, scenario-seedance-music-video (scenario-labs/skills, MIT) ; fal_service registry
description: Use when animating an image with Seedance (ByteDance): Seedance 2.5, 2.0, 2.0 Fast or 1.0 Pro, image-to-video or a start + end frame shot, chaining shots through poses, choreography, dance, fight, music video, a ByteDance moderation refusal, picking the cheapest Seedance member for a draft.
---
## Overview

Seedance animates a start image, with or without an end image. The model has no camera field and no mask: the camera
is written in the prompt. The app always drops the audio track and sends the duration in whole seconds. Seedance 2.5
is the default member; Seedance 1.0 Pro is the only member that takes a seed.

## Quick reference

- [PROMPT] One dominant camera move and one action per shot. A list of actions with no markers makes the model cut
  inside the clip.
- [PROMPT] Several beats: time-stamped beats, one per beat, the last one finished before the end of the duration, and
  the words "one continuous take".
- [PROMPT] Choreography and action: verbs plus entry and exit poses, never adjectives ("dances energetically" gives
  nothing). Write the action as physics: approach, contact, push, recovery; fabric follows a beat late.
- [PROMPT] Name the screen position as well as the pose ("on the left third, facing right"): a mirrored pose breaks
  the cut.
- [PROMPT] The app drops the sound: write no sound or music line. Music is laid in the Montage.
- [PITFALL] Seedance 2.5 has no format field: the frame follows the start image. Prepare the image at the delivery
  format before the shot.
- [PITFALL] The delivered format often lands near the requested one, not on it. Measure the file and crop to the
  delivery format.
- [PITFALL] The delivered duration can differ from the requested one. Read the real duration before cutting.
- [PITFALL] A duration missing from the member's list is moved to the nearest one, with a note. Read the allowed
  durations in Members.
- [METHOD] Chained shots: each shot ends in the pose where the next one starts. N shots need N + 1 edge images; shot N
  starts on image N and ends on image N + 1.
- [METHOD] Edge images: one prompt identical from image to image, only the pose clause changes, same framing. Review
  the whole set before animating: every costume drift lands on a cut.
- [PITFALL] At a joint, the shot size cannot change: it is the same image on both sides. Change scale with a camera
  move inside the shot.
- [PITFALL] A character who leaves the frame and comes back in the same shot often comes back changed. Put exits and
  returns on an edge image.
- [CHOICE] No seed on 2.0 and 2.5: every retry is a new take. Keep the good take; re-rendering at a higher resolution
  gives another take.
- [COST] Prices vary widely between members for the same shot: read them in Members. Compare the quote of two
  members before a series.
- [COST] Draft: 2.5 at the low tier or 2.0 Fast, at the final duration. It validates the prompt and the motion; the
  final, at the high tier, is a new take.
- [COST] Seedance 2.5 is billed by tokens: the quote is an estimate, the invoice may differ. Dropping the sound does
  not change its price.
- [CHOICE] With an end image, Seedance 1.0 Pro is served by its Lite variant, not by Pro.
- [CHOICE] Moderation: a refusal of the render comes from the family filter, and another Seedance refuses the same
  way. Switch provider, same prompt. A character read as a protected work is blocked whatever the wording; weapon or
  violence words block even in a cartoon.
- [CHOICE] Not in the app yet: image, video or audio references, a draft finalized without re-rendering,
  text-to-video, extension.
- [METHOD] Reviewing a take: a contact sheet of the whole clip at two frames per second, then close-ups where things
  break (fast hands, long hair in turns, face), then playback at real speed.

## Example

Brief: "a 9:16 Reel of the dancer from my poster: she spins on the spot then bows, street at dusk behind her".

Start image: the poster cropped to 9:16, dancer facing front in the center. Prompt:

```
One continuous take. Medium-wide shot, slow dolly-in from street level. First half: she pivots on her left foot,
a full turn, her skirt swinging out and settling a beat after her body stops. Second half: she ends facing the
camera in the center third and bows, right hand on her chest. Street lamps stay steady, no subtitles, no
on-screen text.
```

Settings: Seedance 2.5, low tier for the test take, short duration, end image: no. Once the take is approved, same
prompt at the high tier: it is a new take, to review like the first one.

## Common mistakes

- Writing "9:16" in a Seedance 2.5 prompt: the format comes only from the start image.
- Asking for an "energetic" dance: without verbs and edge poses, the motion stays vague.
- Chaining a shot onto the previous output without checking its last frame: write the next prompt from the real image
  (positions, facing), not from the planned shot.
- Retrying unchanged after a moderation refusal: the filter blocks again, and a refused render may be billed.
