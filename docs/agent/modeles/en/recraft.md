---
famille: recraft
natures: [image]
ids: [recraft-4.1-vecteur]
voies: [fal]
releve: 2026-11-09
source: scenario-image, scenario-brand-kit (scenario-labs/skills, MIT), image_providers and pricing registries
description: Use when wanting a VECTOR image (SVG) with Recraft 4.1 vector: logo, icon, pictogram, pattern, flat illustration to recolour or enlarge without loss in Vectorlab, when looking for why Recraft does not appear in an image screen, or when wanting to edit, derive or recolour a generated SVG.
---
## Overview

Recraft 4.1 vector (via fal, fal key) renders an SVG: editable paths, not pixels. It only does text to image: no edit,
no reference image, no seed. It is only served to requests that ask for an SVG: today the
agent; no screen offers it yet (checked 2026-11). A raster request is refused before any run; the rendered SVG then opens
in Vectorlab. Each image is one call.

## Quick reference

- [CHOICE] Pick it for what must stay sharp at any size and be recoloured: logo, icon, pictogram, pattern, flat
  illustration. Not for photorealism, textures or rich gradients.
- [PROMPT] Describe flat, closed geometry, few colours, the brand's hex codes quoted verbatim. Write "flat vector
  illustration", not "photo" or "render".
- [PROMPT] Say what to avoid (mesh gradient, sparkles, decorative lightning bolt, globe): otherwise the model falls
  back on its default motifs.
- [PROMPT] Logo: one single idea about what the brand does, reduced until it reads in one colour at browser-tab icon
  size.
- [METHOD] Three candidates, each on a different construction method (monogram, product verb as a symbol,
  double-reading negative space, grid geometry), rather than three runs of the same idea.
- [METHOD] Check in Vectorlab: name read letter by letter, closed and centred shapes, colours checked on the SVG
  fills, not on the preview. On failure, rerun with a tighter prompt.
- [METHOD] Variants (monochrome, inverted, on paper background): recolour the fills in Vectorlab. Regenerating would
  change the geometry too.
- [PITFALL] No edit by prompt: fix the paths in Vectorlab, or rerun.
- [PITFALL] A generated "font" is only a drawing. The wordmark is drawn once then reused; the rest of the text is
  set in Vectorlab with a real font.
- [COST] The provider publishes two different prices for this model; the quote keeps the higher one (surveyed
  2026-10). The invoice can therefore be lower than the quote.
- [CHOICE] Not in the app yet: palette imposed by a parameter, reference style, vectorising a raster image.

## Example

Brief: "A logo for our bike workshop, Roue Libre, in two colours from our brand: #1F3A5F and #F2B134."

Prompt:

```
Flat vector logo mark for a bicycle repair workshop. A single bicycle wheel whose spokes form a wrench, closed
geometric shapes, centered, generous empty margin. Two colors only: #1F3A5F and #F2B134. Wordmark below reading
"ROUE LIBRE" in a bold geometric sans serif. No gradients, no sparkles, no globe, no other text.
```

Settings: Recraft 4.1 vector requested by the agent as SVG output, square format, three calls with three different construction ideas
(wheel-wrench, looped chain, R monogram). Keep the best, check both colours in the fills, then derive the monochrome
version by recolouring.

## Common mistakes

- Looking for it in a raster image screen (Library, Workshop art direction): it is not there, on purpose.
- Attaching an image to edit: refused. Edit the paths in Vectorlab.
- Regenerating to get the inverted version: the shape changes. Recolour the kept SVG.
- Leaving colours implicit: they drift from one run to the next. Quote the hex codes.
