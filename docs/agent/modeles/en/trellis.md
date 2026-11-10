---
famille: trellis
natures: [modele3d]
ids: [trellis, triposr, trellis-2]
voies: [fal]
releve: 2026-11-09
source: scenario-3d (scenario-labs/skills, MIT) ; asset3d_service, moteurs3d_neufs, pricing (asset3d) registries
description: Use when converting a single image into a GLB 3D model with TRELLIS (Microsoft) or TripoSR: Trellis, TRELLIS 2, TripoSR; a prop or compact object from one image, a quick and cheap test of a concept, resolution and texture size, decimation, remeshing, seed, a textured GLB straight away with no settings.
---
## Overview

Three members that read **a single** image and return a textured GLB, with no text mode and no pose:

- **TripoSR**: the fastest and cheapest rebuild, to judge a concept, not to deliver.
- **Trellis**: a textured GLB straight away, with no settings at all.
- **TRELLIS 2**: the most adjustable (geometry resolution, texture size, decimation, remeshing, seed).

They are launched from Game Assets › 3D › Create.

## Quick reference

- [PROMPT] Source image: one compact object, centered, whole with margin, plain background, even light, no cast
  shadow and no text. Hidden sides are invented: pick the three-quarter angle that shows the most.
- [PROMPT] The "Subject" field of Create is not sent to these members: only the image counts.
- [CHOICE] Prop, weapon, furniture, rock: this family is often enough, one image and a textured GLB straight away.
  Character to rig, or object whose back matters: a member that reads multiple views or poses the subject.
- [CHOICE] No member has an untextured draft (draft column in Members). This family's draft is TripoSR: a shape seen
  fast and cheaply, then the final shot on another member.
- [CHOICE] TRELLIS 2, `resolution`: the fineness of the geometry. The lowest tier for a test, the highest for an
  object with small details.
- [CHOICE] TRELLIS 2, `texture_size`: the size of the maps. A larger texture makes the file heavier without changing
  the shape: keep it moderate for mobile games or the web.
- [CHOICE] TRELLIS 2, `decimation_target`: aims at a face count, with a floor. Below that floor, reduce afterwards
  in 3D Studio › Prepare (local, free).
- [CHOICE] TRELLIS 2, `remesh` (on by default) rebuilds a clean mesh. Turn it off only to compare with the raw mesh.
- [METHOD] Variant of the same object: same image, same `seed` (TRELLIS 2), one setting changed at a time.
- [PITFALL] TRELLIS 2 has no PBR setting: the maps of the delivered GLB are whatever the provider returns, to be
  checked (to be confirmed on the first shot).
- [COST] TRELLIS 2: the price follows `resolution`; the one in Members is the default tier. Texture size and
  decimation do not change the quote.
- [COST] Several members ticked in Create = one paid shot each. To decide, 3D Studio › "Compare engines" measures
  triangles, open edges and watertightness on the same image.
- [PITFALL] Formats: GLB only for all three. FBX, OBJ or STL are made in 3D Studio › Export.
- [CHOICE] Not in the app yet: text-to-3D, multiple views, choice of output format.

## Example

Brief: "a wooden barrel with hoops for my tavern scenery, clean but light".

Image: one barrel, three-quarter view from slightly above, plain light grey background. Create, Image mode, TripoSR
to see the shape cheaply. The silhouette works; same image, TRELLIS 2, settings wheel: `resolution` at the middle
tier, moderate `texture_size`, `remesh` on, `seed` set. The GLB then goes through 3D Studio › Prepare to fit the
scene's budget.

Concept image prompt, in the image generator:

```
A single oak barrel with two iron hoops, three-quarter view from slightly above, whole object in frame with margin,
plain light grey background, soft even lighting, no cast shadow, no text.
```

## Common mistakes

- Delivering the TripoSR mesh as a final asset: it is a test.
- Giving a group photo: the objects often come out welded into a single block. One object per image.
- Pushing `texture_size` to the maximum for a game asset: heavy file, same shape.
- Expecting a T-pose from this family: the screen refuses it.
