---
famille: hunyuan3d
natures: [modele3d]
ids: [hunyuan, hunyuan-local, hunyuan-3.1]
voies: [fal, local]
releve: 2026-11-09
source: scenario-3d (scenario-labs/skills, MIT) ; asset3d_service, moteurs3d_neufs, local3d_service, pricing (asset3d) registries
description: Use when generating a 3D model with Hunyuan3D (Tencent): Hunyuan3D v2 through fal, Hunyuan 3D 3.1 Pro (image or text), Hunyuan3D 2.1 run locally for free on one's own graphics card (GPU, VRAM, LOCAL3D_URL); geometry only then texture, PBR, high face budget, object or character from a single image, a 3D model with no spending.
---
## Overview

Hunyuan3D rebuilds a mesh from **a single** image; Hunyuan 3D 3.1 can also start from a text. Three members: v2
through fal, 3.1 Pro through fal (the most adjustable), and 2.1 running **locally**, free, served by a GPU service
the user starts next to the app (`LOCAL3D_URL` setting). No member reads multiple views or poses a character. They
are launched from Game Assets › 3D › Create.

## Quick reference

- [PROMPT] Source image: one subject, centered, whole with margin, plain background, even light with no cast
  shadow. The member sees only this image: hidden sides are invented. Pick the angle that shows the most.
- [PROMPT] Four-legged creature: at eye level, side or three-quarter view, every leg visible and clear of the body.
  A top view hides the underside and the height.
- [PROMPT] Text mode (3.1 only): one English sentence, one object, its material, its shape, its style. An approved
  concept image gives more control.
- [CHOICE] Character to rig: no member has a pose parameter and the screen refuses a T-pose or A-pose. Supply an
  image already in an A-pose, arms clear of the torso.
- [CHOICE] Local (2.1): free and offline, but only when the service answers; otherwise the generation is refused
  before any shot. The shape alone fits on a mid-range card; the texture needs much more VRAM (model README,
  surveyed 2026-11). Below that threshold, the service returns a bare shape.
- [CHOICE] Local: the service removes the background; the image is sent to no provider.
- [CHOICE] 3.1: `generate_type` Geometry returns the shape only (draft); Normal returns it textured.
- [CHOICE] 3.1: the face budget (`face_count`) starts from a high floor. For a light asset, generate then reduce in
  3D Studio › Prepare (local, free), or pick another member aimed at low-poly.
- [PITFALL] 3.1: PBR is "opt-in" (Members): the `enable_pbr` setting is off by default. Tick it in the wheel when
  PBR maps are wanted.
- [COST] 3.1: `enable_pbr` and a set `face_count` are surcharges, added to the quote only when set. `enable_pbr` is
  not counted with Geometry.
- [COST] v2: geometry only costs clearly less than the textured version (quote). The draft is set with the Textures
  box of the former 3D form; Create always sends the texture for v2.
- [COST] Draft first: local for free or Geometry, judge the silhouette, then the textured shot.
- [METHOD] Texturing an approved draft: 3D Studio › Prepare › "Approve the geometry", then the Texture screen.
- [PITFALL] Formats: v2 and 3.1 list GLB and OBJ, local GLB only. Another format is converted in 3D Studio › Export.
- [CHOICE] Not in the app yet: seed and step count for the local member (the app fixes them), texturing an existing
  mesh with Hunyuan.

## Example

Brief: "a gargoyle statue for my scenery, I want to see the shape first without paying anything".

Image: crouching gargoyle in three-quarter view, folded wings, plain grey background, flat light. Create, Image
mode, Hunyuan3D 2.1 (local): shape only, free. The silhouette works; same image, Hunyuan 3D 3.1, settings wheel:
`generate_type` Normal, `enable_pbr` ticked. The quote shows the PBR surcharge before Generate.

Concept image prompt, in the image generator:

```
A stone gargoyle crouching on a plinth, folded wings, three-quarter view at eye level, whole statue in frame with
margin, plain mid-grey background, soft even lighting, no cast shadow, no text.
```

## Common mistakes

- Launching the local member without starting the service: immediate refusal, nothing paid, but nothing done.
- Expecting a texture from the local member on a card that is too small: the shape comes back bare.
- Sending a top view: the underside and the thickness come out wrong.
- Setting a `face_count` with no need: a surcharge paid for a budget the default already met.
