---
famille: meshy
natures: [modele3d]
ids: [meshy-7.1]
voies: [fal]
releve: 2026-11-09
source: scenario-meshy, scenario-3d (scenario-labs/skills, MIT) ; moteurs3d_neufs, pose3d, pricing (asset3d) registries
description: Use when generating a 3D model with Meshy 7.1 through fal: image or text to 3D, a character to rig in an A-pose or T-pose, triangle or quad topology, target polycount, remeshing, symmetry, geometry only then texture, PBR, geometry resolution, GLB FBX OBJ USDZ export; to tell apart from the Meshy retexture and rig of the 3D Studio.
---
## Overview

Meshy 7.1 rebuilds a mesh from **one** image or from a text, through fal. It poses a character in a T-pose or
A-pose and sets its topology at the source (triangles or quads, target polygons, remeshing, symmetry). It is
launched from Game Assets › 3D › Create, settings in the wheel. The retexture and rig of the 3D Studio go through
the Meshy key, outside this member.

## Quick reference

- [PROMPT] Source image: one subject, centered, whole with margin, plain background, even light with no cast shadow
  and no text. Only one image is sent: hidden sides are invented.
- [PROMPT] Text mode: one English sentence, one subject, its material, its silhouette, its style, and the pose for
  a character. An approved concept image gives more control.
- [PROMPT] The "Subject" field of Create is not sent in Image mode: only the image counts.
- [CHOICE] Character to rig: pick A-pose or T-pose in Create (an A-pose usually rigs better: arms at about 45°, a
  clear gap between limbs and torso). For an object, the screen refuses the pose.
- [CHOICE] `topology`: triangle for a game engine, quad to rework the mesh in 3D software. glTF stores only
  triangles: the GLB of a quad shot arrives triangulated.
- [PITFALL] `target_polycount` only acts during remeshing (`should_remesh`, on by default). With remeshing off, the
  app refuses the polycount rather than pay for nothing.
- [CHOICE] `should_remesh` off: the model's raw mesh, denser. Keep it on for a face budget.
- [CHOICE] `symmetry_mode`: auto by default; on for a symmetric subject (vehicle, armor), off for an asymmetric one
  (walking pose, object held in one hand).
- [CHOICE] `geometry_resolution`: fineness of the shape. Raise it only for an object with small details.
- [PITFALL] PBR is "opt-in" (Members): `enable_pbr` is off by default. Tick it to get PBR maps.
- [CHOICE] `model_type` has a single value, standard: Meshy's smart topology is another service, not in the app.
- [COST] Draft first: `should_texture` unticked in the wheel, the shot costs less (quote). Judge the silhouette, then
  shoot again textured, or texture the approved mesh.
- [COST] The price in Members is the default textured shot's. Several images in Multi-image or a quantity above
  one: one paid shot each.
- [METHOD] Texturing an approved draft: 3D Studio › Prepare › "Approve the geometry", then the Texture screen
  (Meshy retexture, billed in Meshy credits, Meshy key required).
- [METHOD] Rig: 3D Studio › Rig, on the approved mesh. The rig is not done by this member.
- [CHOICE] Not in the app yet for this member: multiple views, a separate texture image, keeping the pre-remesh
  mesh, real height in metres.

## Example

Brief: "a knight in armor for my game, to rig and animate afterwards".

Image: the approved knight, front view, full body, in an A-pose, plain grey background, flat light. Create, Image
mode, Meshy 7.1, A-pose. Settings wheel: `topology` triangle, `target_polycount` at a game-character budget,
`should_remesh` on, `symmetry_mode` on, `should_texture` unticked for the draft.

Once the draft is approved in Prepare, the texture is made in the Texture screen with the source image as reference,
then the rig in the Rig screen.

Concept image prompt, in the image generator:

```
A knight in full plate armor standing in an A-pose, arms straight and angled down away from the body, full body
head to feet, front view, plain mid-grey background, soft even lighting, no cast shadow, no text.
```

## Common mistakes

- Setting `target_polycount` then turning remeshing off: refused before sending.
- Choosing quad for a real-time game engine: the GLB is triangulated anyway.
- Forgetting `enable_pbr` and being surprised by a material with no metal and roughness maps.
- Confusing this member with the 3D Studio retexture: two keys, two bills.
