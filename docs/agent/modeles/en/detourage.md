---
famille: detourage
natures: [detourage_image, detourage_video]
ids: [local-rembg, local-chroma, birefnet-v2, bria-rmbg, pixelcut, ideogram-rmbg, feynobg, sam3-sujet, bria-objet, rembg-fal, birefnet-v2-video, bria-video-v3, veed-video-rapide, pixelcut-video, sam31-video]
voies: [local, fal]
releve: 2026-11-09
source: scenario-image-editing, scenario-image (scenario-labs/skills, MIT) ; detourage registry, matte_service, decor_service
description: Use when removing the background of an image or a video, picking a background remover (local rembg, plain or green background, BiRefNet, Bria, Pixelcut, Ideogram, FeyNobg, SAM 3 or SAM 3.1 for a named subject, VEED), cutting out a product photo, hair, a character, a sprite or a video take, getting a PNG or a video with alpha, or when a cutout leaves a fringe, a halo or leftover background.
---
## Overview

Background removal deletes the background and returns a PNG with alpha (image) or a video with alpha (`.mov`
ProRes or `.webm` VP9). Two members are **local and free**: rembg and plain background (chroma). The others go
through fal and are paid, per image, per second or per batch of frames (price column in Members). Three members
require a **named subject**: they keep what is named and erase the rest. The same registry serves the Library, the
Montage matte, sprites, Card Forge, the 3D Studio and the Avatar live backdrop.

## Quick reference

- [CHOICE] Start **local**: rembg for a clear subject on any background, plain background for a single-color
  background. Move to fal only if the edge is bad.
- [CHOICE] Plain background (`local-chroma`): it takes the color of the border, green or any other. It refuses when
  the border is not uniform or when the subject covers almost the whole frame (or almost nothing). Ideal for a green
  screen or an image generated on a flat background.
- [CHOICE] Hair, fur, fine edges: BiRefNet v2. The app sets the image member to the heavy model at a high working
  resolution with edge refinement; the video member to the light model at a lower resolution.
- [CHOICE] Product photo, crisp object: Bria RMBG 2.0, Pixelcut or Ideogram; the cheapest one that gives a clean edge
  on a test.
- [CHOICE] Several subjects in the image, only one to keep: SAM 3 ("keep a named subject") or Bria object ("extract
  a named object"). Write the subject in a few English words: "the red backpack", "the woman on the left".
- [PITFALL] A subject member without a subject is refused before any spending. The others ignore a subject.
- [CHOICE] `rembg-fal` is the old rembg served by fal; local rembg does the same job for free when it is installed.
- [CHOICE] Video: BiRefNet v2 video is the default. Bria VRMBG 3.0 keeps the sound track. SAM 3.1 tracks a named
  subject through the whole take. VEED fast and Pixelcut video return a `.webm`.
- [METHOD] Video: first cut out **one frame** from the middle of the take with the member's image twin (Bria RMBG
  for Bria video, SAM 3 for SAM 3.1, BiRefNet for BiRefNet video and VEED, Pixelcut for Pixelcut video). The Avatar live "Background only" screen does this before
  running the video.
- [CHOICE] A short animation or a loop can come out cleaner frame by frame (extracted frames) than through video
  removal (survey 2026-11). The cost then follows the number of frames.
- [COST] Per second (Bria video; BiRefNet video too, but "price to be measured"): duration sets the price. Per batch of frames (VEED, Pixelcut video,
  SAM 3.1): at equal duration, a higher frame rate costs more. Trim the take to the useful shot first.
- [COST] Sprites: each frame of the sheet is a billed cutout. Plain background or local rembg first.
- [COST] A member marked "price to be measured" is quoted at zero but billed by fal: the spending cap does not stop
  it. Try it on a single image.
- [COST] Prefer an image generator that renders a true transparent background ("transp." column of its sheet): it
  saves a billed pass.
- [PROMPT] Image generated to be cut out, by a model without a transparent background: ask for "plain light grey
  background, soft even light, subject fully in frame". Avoid a background of the subject's color.
- [PROMPT] Video generated to be cut out: "plain background, locked-off camera, no cuts". A plain background and a
  fixed camera give a clean matte.
- [PITFALL] Fringe: a semi-transparent rim of the old background can stay on the edge. Check on a dark **and** a
  light background, not on the checkerboard.
- [PITFALL] Glass, smoke, veil: the inside can come out holed or opaque depending on the member. Check by measuring
  alpha, not by eye.
- [PITFALL] A matte re-exported as MP4 loses its alpha. Keep the `.mov` or the `.webm` until the Montage.
- [CHOICE] Not in the app yet: the fal members' own settings (choosing BiRefNet's internal model, VEED's "human subject"
  mode); the app fixes them.

## Example

Brief: "I have 12 photos of my candles on the kitchen table; I need cut-out PNGs for the shop, and one of the photos
also shows a vase I don't want."

Settings: local rembg on a test photo. The wick edge stays blurry: Bria RMBG 2.0 on the same photo, clean edge, then
the other 11. For the photo with the vase, SAM 3 with the subject:

```
the white candle in the glass jar
```

Check: each PNG laid on a black background then on a white one, at 100 %, to spot a fringe or a leftover bit of
tablecloth.

## Common mistakes

- Paying a fal remover for an image on a green or plain background: the local plain background is enough.
- Running a whole video without a one-frame preview: a bad edge is paid for over the whole duration.
- Picking a subject member for a single-subject image: refused without a subject, and no better than a general one.
- Writing "transparent background" in a generator's prompt, then being surprised by the opaque background: cut out
  afterwards.
- Judging the cutout on the preview checkerboard: the fringe does not show there.
