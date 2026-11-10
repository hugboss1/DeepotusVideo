---
famille: sam3-objets
natures: [objets3d]
ids: [sam-3-3d-objects, sam-3-3d-body]
voies: [fal]
releve: 2026-11-09
source: scenario-walkable-room, scenario-3d (scenario-labs/skills, MIT) ; storyboard3d, pricing (objets3d) registries
description: Use when rebuilding in 3D the objects or people of a shot's image with SAM 3 (Meta): "Rebuild in 3D" in the Atelier, 3D storyboard, 3D objects placed on the Stage, 3D human body, list of objects separated by commas, 3D scene from an image, previs, objects missing or misplaced after a rebuild.
---
## Overview

SAM 3 isolates elements of a shot's image and rebuilds them as **placed** GLBs, set as instances of the Stage scene
linked to the shot. Two members:

- **3D objects** (default): one GLB per named object, each with its position;
- **3D human body**: every person in the image in a single GLB, set as one "subject" instance.

It is launched from the Atelier: shot card › "Rebuild in 3D (SAM 3)". The source image is the shot's production
image, otherwise its sketch.

## Quick reference

- [PROMPT] Objects: short names separated by commas, in English, one per object to isolate:
  "knight, wooden table, oil lamp". The field is prefilled with the shot's objects: reread it and translate it.
- [PROMPT] Name what is clearly visible in the image, with a word that tells it apart ("red chair" when there are
  two chairs). An object missing from the image does not come out.
- [PITFALL] SAM 3 returns no name per object. The app sets the names of the list in the order the objects come
  back, which may differ from the written order. Check each instance on the Stage.
- [CHOICE] Human body: the list is optional and is not sent to the model; it only serves for naming. People come out
  welded into a single GLB, with no position per person.
- [CHOICE] Production image rather than sketch: a line sketch gives poor volumes and a flat texture.
- [PROMPT] An image that rebuilds well: separated objects, little hidden behind one another, visible floor,
  readable light. An object cut by the frame comes back incomplete.
- [PITFALL] The frame of reference between SAM 3 and the Stage is not confirmed yet (the app assumes they match, to
  be settled on the first real shot). A wrong position or rotation is fixed by hand on the Stage.
- [PITFALL] Each rebuild replaces the shot's previous SAM 3 instances. Scenery placed by hand stays.
- [PITFALL] Beyond a cap of objects per shot, the extra objects are dropped; the screen says so. Split into two
  shots if the list is long.
- [COST] Price per request, whatever the number of objects; fal's billing unit is to be confirmed on the first shot
  (the screen reminds it). The quote goes through the "chapters" cap.
- [METHOD] Check: open the shot's Stage (offered at the end), count the objects, check names, scale and floor
  contact, and only then generate the shot's video from the Stage.
- [CHOICE] A single object to polish as an asset (topology, texture, rig): not this model, but a 3D generator in
  Game Assets › 3D › Create from an isolated image.
- [CHOICE] Not in the app yet: pointing at objects with rectangles, setting the detection threshold, fixing a seed.

## Example

Brief: "on shot 4, the tavern: I want the knight, the table and the lantern in 3D to frame the camera".

Atelier, shot 4, "Rebuild in 3D (SAM 3)", 3D objects model, production image. Objects field:

```
knight, wooden table, hanging lantern
```

After the shot, open the Stage: three instances. The lantern carries the name "wooden table": rename it, raise the
lantern under the beam, set the camera, then start the shot's video.

## Common mistakes

- Leaving the list in another language than English, or in sentences: the objects are found less well.
- Believing the displayed name matches the object: the order can shift.
- Shooting again to add a forgotten object: the shot replaces the SAM 3 objects already placed. Shoot again with
  the full list.
- Picking human body for two characters to place separately: they arrive as a single block.
