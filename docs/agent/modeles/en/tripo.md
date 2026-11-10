---
famille: tripo
natures: [modele3d]
ids: [tripo, tripo-h3.1, tripo-p2, tripo-p1]
voies: [fal]
releve: 2026-11-09
source: scenario-3d (scenario-labs/skills, MIT) ; asset3d_service, moteurs3d_neufs, pricing (asset3d) registries
description: Use when turning an image or a description into a 3D model with Tripo: Tripo v2.5, Tripo H3.1 (v3.1), Tripo P2, Tripo Smart Mesh (P1); low-poly game asset, face budget, quad mesh, four views front back profiles, untextured draft then texture, PBR, delight, GLB or FBX export to Unity, Unreal, Godot or Blender.
---
## Overview

Tripo rebuilds a mesh from an image, and for P2 and Smart Mesh from a text too. Four members: v2.5 (the widest
choice of formats), H3.1 (multiple views in an imposed order), P2 (the newest, quad topology, four texture tiers)
and Smart Mesh (low-poly). They are launched from Game Assets › 3D › Create; multiple views go through the
"Views first" panel of the 3D Studio or through the former 3D form of Game Assets.

## Quick reference

- [PROMPT] Source image: one subject, centered, whole with margin, on a plain background, soft even light, no cast
  shadow and no text. A shadow or reflection in the photo gets baked into the texture.
- [PROMPT] Text mode (P2 and Smart Mesh): one English sentence naming the object, its material, its silhouette and
  its style. Better: first generate an approved concept image, then convert it.
- [PROMPT] The "Subject" field of Create is not sent to Tripo in Image mode: it only feeds the prompt of the
  generated views.
- [CHOICE] Multiple views: only v2.5 and H3.1 read them (views column in Members). The app itself puts the views in
  the order H3.1 requires; the front view is mandatory.
- [PITFALL] Swapped profiles: "left" is the **character's** left (nose pointing to the left of the frame). A swapped
  pair can merge front and back into a shell. Look at the views in "Views first" before the shot.
- [CHOICE] Character to rig: Tripo has no pose parameter. The T-pose or A-pose goes through the generated views:
  without multiple views, the screen refuses the pose. P2 and Smart Mesh have no way to pose at all.
- [CHOICE] Topology: P2 and Smart Mesh expose `face_limit` (settings wheel); P2 adds `quad`. Smart Mesh targets
  light props and scenery. A quad count is not a triangle count.
- [PITFALL] glTF stores only triangles: the GLB of a `quad` shot arrives triangulated. Create downloads only the
  GLB, and the former form, which can ask for FBX, does not send the wheel settings. P2's native quad mesh therefore
  does not reach the app yet.
- [CHOICE] `delight` (P2, on by default) removes the photo's lighting. Turn it off only when painted shading is
  wanted.
- [CHOICE] `auto_size` (P2) scales the model to real size in metres. Without it, the size is normalized.
- [METHOD] Variant of the same volume: keep the image and `model_seed` (P2, Smart Mesh), change the rest.
- [COST] Draft first: texture off (`texture` unticked in the wheel of P2 and Smart Mesh, Textures box of the former
  form for v2.5 and H3.1). Judge the silhouette, then pay for the texture.
- [COST] On P2, `texture_quality` changes the price; the price in Members is the default tier's. Turning the
  texture off also turns PBR off, otherwise it would be billed.
- [COST] Several ticked models, several images or a quantity above one: one paid shot each. Read the estimated
  total before Generate.
- [METHOD] Texturing an approved draft: 3D Studio › Prepare › "Approve the geometry", then the Texture screen.
- [CHOICE] Not in the app yet: a separate texture seed, texture alignment, H3.1's `face_limit`, `quad` and detailed
  geometry, the HD tier of H3.1 and v2.5 from a screen.
- [METHOD] Torn between two members: 3D Studio › "Compare engines" shoots the same image and measures triangles,
  open edges and watertightness.

## Example

Brief: "a low-poly treasure chest for my mobile game, to import into Unity".

Approved concept image, chest in three-quarter view on a plain light grey background, flat light. Create, Image
mode, Tripo P2, settings wheel: `texture` unticked, low `face_limit`, `model_seed` set. The draft is reviewed: lid,
lock, feet. Once approved, shoot again with `texture` ticked, `texture_quality` standard and the same `model_seed`.
The GLB then goes to Unity through 3D Studio › Export.

Concept prompt, in the image generator:

```
A low-poly wooden treasure chest with iron bands and a round padlock, three-quarter view from slightly above,
whole object in frame with margin, plain light grey background, soft even lighting, no cast shadow, no text.
```

## Common mistakes

- Giving a photo with a busy background: the scenery ends up in the mesh or the texture. Cut out first, or
  regenerate on a plain background.
- Ticking T-pose on P2 or Smart Mesh: refused, these members pose nothing.
- Paying for the texture before seeing the silhouette.
- Believing the GLB of a quad shot keeps its quads.
