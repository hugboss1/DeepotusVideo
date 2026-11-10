---
famille: qwen-image
natures: [image]
ids: [qwen-image-3]
voies: [fal]
releve: 2026-11-09
source: scenario-image, scenario-multi-reference (scenario-labs/skills, MIT) ; image_providers, pricing and parallaxe registries
description: Use when generating or editing an image with Qwen Image (Alibaba): Qwen Image 3, quick and cheap tries, composition options before a final on another model, editing with one or several reference images, splitting a painting into layers (Qwen-Image-Layered).
---
## Overview

Qwen Image 3 generates an image from text, or edits from one or more reference images. It is inexpensive
(read Members). It has no seed, no mask, no negative field and no transparent background,
and its pill has no quality tier and no resolution row. Little public feedback exists on this model: the sheet keeps
to the general image rules and the registry.

## Quick reference

- [CHOICE] Take it to explore cheaply: composition, framing, palette. The final can then move to a more faithful
  model, with the kept image as a reference.
- [PROMPT] Separate what is imposed from what the model may invent: invented details obey the constraints too (no
  decorative letters in a visual without text).
- [PROMPT] Several references: one line per image, "Image N = <job> only", then what it must **not** lend. The number
  of references sent is read in Members.
- [METHOD] Editing: "change only X", then the list of what stays. Anything not named may change.
- [PITFALL] The app sends the chosen format on every call, edits included: the output follows that format, not the
  input image's frame. Pick the input image's format so it is not cropped.
- [PITFALL] The rendered size can differ from the expected one. Read the file's width and height.
- [PITFALL] The image count of a call repeats the same prompt: it gives variations, not a set. A set (angles,
  variants) = one call per item.
- [PITFALL] No transparent background: the image comes out opaque and the reply says so. Ask for "plain white
  background", then cut out (cutout sheet).
- [PITFALL] "Film still" or a ratio written in prose bake in black bars. Add "full frame edge to edge, no
  letterboxing".
- [PITFALL] With no seed, a retry is a new image. Keep the chosen output.
- [CHOICE] Splitting into layers: Qwen-Image-Layered is not in the pill. It is served only by the Tilelab's "Parallax
  backdrop" tab.

## Example

Brief: "three quick options for a forest backdrop for my platformer, before picking a direction".

Prompt (one call, several images):

```
A side-scrolling platformer background: an old pine forest at dusk, layered depth from a misty far ridge to dark
trunks in the foreground, warm orange sky fading to violet. Painterly, soft edges, readable silhouettes. No
characters, no lettering anywhere. Full frame edge to edge.
```

Settings: Qwen Image 3, landscape format, three images in the same call: they are three variations of the same
prompt, which is what is wanted here. The chosen option becomes the reference for the final; the next views of the
same level are made one call per view.

## Common mistakes

- Asking for "three angles of the same backdrop" in one call: you get three variations, not three angles.
- Writing "transparent background": the output is opaque.
- Editing a square image with a landscape format chosen: the output is cropped.
