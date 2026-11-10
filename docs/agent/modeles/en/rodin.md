---
famille: rodin
natures: [modele3d]
ids: [rodin, rodin-2.5]
voies: [fal]
releve: 2026-11-09
source: scenario-rodin, scenario-3d (scenario-labs/skills, MIT) ; asset3d_service, moteurs3d_neufs, pose3d, pricing (asset3d) registries
description: Use when generating a 3D model with Rodin (Hyper3D, Deemos): Rodin and Rodin Gen-2.5; a character to rig in a T-pose or A-pose, several views of the same subject, text-to-3D, tier, quad or triangle mesh (quality_mesh_option), PBR material, HighPack, HD textures, GLB FBX OBJ STL USDZ export.
---
## Overview

Rodin rebuilds a mesh from one or several views of the same subject; Rodin 2.5 can also start from a text. With Meshy,
it is one of the two families that ask the engine itself for a **rig pose**: the T-pose or A-pose works without
multiple views.
Five output formats. Rodin 2.5 exposes all its settings in the wheel of Game Assets › 3D › Create.

## Quick reference

- [PROMPT] Source image: one subject, centered, whole with margin, plain background, even light with no cast
  shadow. Several images must show the **same** subject from other angles, never another concept.
- [PROMPT] Rodin 2.5, Image mode: the "Subject" field is sent as the prompt. Empty, the model describes the images
  itself. A short English sentence naming the subject, the material and what is not visible ("a quiver on the
  back").
- [PROMPT] Text mode (2.5 only): one English sentence, one subject, its material, its silhouette, its style.
- [CHOICE] Character to rig: pick T-pose or A-pose in Create. Full body, arms clear of the torso. For an object, the
  screen refuses the pose.
- [PITFALL] Rodin 2.5 only receives "a rig pose", without saying which. To force the A-pose, also write it in the
  Subject ("standing in an A-pose, arms angled down"). The first Rodin receives the pose sentence on its own.
- [CHOICE] Multiple views: Create sends one image per shot (Multi-image = one model per image). Several views of the
  same subject go through "Views first" in the 3D Studio, or the former 3D form (Multiple views box). Read the views
  column in Members.
- [CHOICE] Rodin 2.5, `tier`: geometry density, from lightest to densest. `quality_mesh_option` sets topology and
  budget in one value ("18K Quad", "50K Triangle"); the allowed budgets depend on `tier`, fal refuses the others.
- [CHOICE] Rodin 2.5, `material`: PBR (default) for a game engine, Shaded for a painted-light render, None for the
  shape only.
- [CHOICE] Rodin 2.5: `hd_texture` sharpens the texture; `highpack` adds finer textures and denser geometry. On a
  quad mesh, HighPack multiplies the face count sharply (surveyed 2026-11).
- [METHOD] Variant of the same subject: same image, same `seed`, one setting changed.
- [PITFALL] Rodin 2.5, `geometry_file_format`: the app always stores the main file as `model.glb`. Keep GLB and
  convert in 3D Studio › Export (to be confirmed: an FBX chosen here would arrive misnamed).
- [COST] `highpack` is a surcharge added to the quote. The price in Members is the default settings'.
- [COST] The Rodin 2.5 quote does not move with `tier`; an extreme tier may be billed more by fal (surveyed 2026-11,
  to be confirmed). Compare with the spending table after a first shot.
- [COST] No untextured draft (draft column). Try first at a low `tier`, without HighPack; the final afterwards.
- [CHOICE] Not in the app yet: the first Rodin's quality tier from a screen (it goes out at medium), symmetric mode,
  creative mode, splitting a mesh into parts with Rodin.
- [METHOD] Rig: once approved, 3D Studio › Prepare › "Approve the geometry", then the Rig screen.

## Example

Brief: "a stylized archer to animate in Unity, quiver on her back".

Image: the approved archer, front view, full body, in an A-pose, plain grey background, flat light. Create, Image
mode, Rodin 2.5, A-pose. Settings wheel: `tier` Gen-2.5-Low for the test, `material` PBR, `quality_mesh_option`
"18K Quad", `seed` set, HighPack off. Subject:

```
A stylized female archer standing in an A-pose, arms straight and angled down away from the body, leather armor,
a quiver of arrows on her back.
```

Once the silhouette is approved, same image and same `seed` at the default `tier`, then the rig in the 3D Studio.

## Common mistakes

- Ticking T-pose on a sword or a chest: refused, it is not a character.
- Mixing two concepts in the images of one shot: the mesh fuses them.
- Turning HighPack on for a quad mesh meant for real time: too many faces.
- Judging the family on the first Rodin: it always goes out at the medium tier. Rodin 2.5 sets its density.
