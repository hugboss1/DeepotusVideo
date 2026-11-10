---
famille: seedream
natures: [image]
ids: [seedream-5-pro]
voies: [fal]
releve: 2026-11-09
source: scenario-image, scenario-seedream, scenario-multi-reference (scenario-labs/skills, MIT) ; image_providers, pricing and parallaxe registries
description: Use when generating or editing an image with Seedream (ByteDance): Seedream 5 Pro, a poster or visual with an exact title, text in a non-Latin script, editing with several reference images, replacing the text on an existing image, the cost of a multi-reference edit, splitting a painting into layers (Layerize).
---
## Overview

Seedream 5 Pro generates an image from text, or edits from one or more reference images: with no reference it is a
generation; with references, an edit. It holds short, exact text well, non-Latin scripts included. It has no seed,
no mask, no negative field and no transparent background. Its pill has no quality tier and no resolution row.

## Quick reference

- [PROMPT] Text: quote each string, state its position and its size rank ("the title "NIGHT TIDE", large, top
  third"). Few elements, at one or two sizes.
- [PITFALL] Letters are drawn, not typeset: a paragraph or a small label comes out as unreadable shapes. Dates,
  credits, prices and legal lines are overlaid from the start.
- [METHOD] Warped word: re-run, spelling the word letter by letter after the quoted string. If it resists, overlay it.
- [PROMPT] Replacing text on an existing image: quote the new string, pin its position, require the original font,
  size and color, and "everything else unchanged".
- [PROMPT] Several references: one line per image, "Image N = <job> only", then what it must **not** lend. A
  reference lends everything it shows unless forbidden.
- [PROMPT] The job most often ignored (often style) goes first. Lend concretely ("copy its grainy risograph texture
  and two-ink look") rather than "use its style".
- [PROMPT] Separate what is imposed from what the model may invent: invented details obey the constraints too (no
  decorative letters in a visual without text).
- [PITFALL] The app sends the chosen format on every call, edits included: the output follows that format, not the
  input image's frame. Pick the input image's format for an edit that must not crop.
- [PITFALL] The rendered size can differ from the expected one. Read the file's width and height before using it.
- [METHOD] Exact size (banner, icon): generate at the nearest format above, same ratio, then resize. Enlarging does
  not bring detail back.
- [PITFALL] No transparent background: the image comes out opaque and the reply says so. Editing a cutout gives it a
  solid background back; cut out after the edit (cutout sheet).
- [PITFALL] With no seed, a retry is a new image. Keep the good output; for a variant, change only the last clause.
- [PITFALL] "Film still" or a ratio written in prose bake in black bars. Add "full frame edge to edge, no
  letterboxing".
- [METHOD] A set (angles, variants) = one call per item. The image count of a call only gives variations of the same
  prompt.
- [COST] Each input image beyond the first adds a small cost (checked 2026-11). The quote does not count it: the
  invoice for a multi-reference edit runs a little above the quote.
- [COST] One price, no draft tier: every try costs a final. Settle the text and the composition on one image before
  asking for several.
- [CHOICE] Seedream 5 Pro renders more slowly than the family's fast variants (checked 2026-11), which are not in the
  app. Take it for exact text or a reference edit, not for dozens of tries.
- [CHOICE] Splitting into layers: Seedream Layerize is not in the pill. It is served only by the Tilelab's "Parallax
  backdrop" tab, billed per generated layer.
- [CHOICE] Not in the app yet: exact pixel sizes, a set of linked images in a single call, the prompt optimization
  mode, an edit that keeps a reference's transparency, the Lite, Flash and 4.5 members.

## Example

Brief: "a vertical poster for my festival "NIGHT TIDE", in the style of my risograph board (attached); the dates and
venue come later".

Reference: image 1 = the style board. Prompt:

```
A vertical festival poster. Image 1 = style only: copy its grainy risograph texture, two-ink look in deep teal and
coral, slight misregistration. This is the most important job. Do not copy any shape, figure or word from it.
A huge stylized wave curls across the lower two thirds, a small moon above it. The title "NIGHT TIDE" in tall
condensed letters, large, centered in the top third. No other text. Leave a plain teal band empty along the bottom
for later text. Full frame edge to edge.
```

Settings: Seedream 5 Pro, portrait format, one reference. Check: the title letter by letter, the bottom band empty.
The dates and venue are overlaid afterwards (Templates or Card Forge), never in the prompt.

## Common mistakes

- Writing the dates and venue in the prompt: they come out misspelled or unreadable.
- Editing a square photo with a portrait format chosen: the output is cropped.
- Attaching a style reference without saying what not to copy: its subject walks into the poster.
- Trusting the quote for a five-reference edit: each extra image is paid for.
- Writing "transparent background": the output is opaque. Plain background, then cutout.
