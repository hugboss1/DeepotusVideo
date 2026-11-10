---
famille: flux
natures: [image]
ids: [flux, flux-3]
voies: [fal]
releve: 2026-11-09
source: scenario-image, scenario-consistency (scenario-labs/skills, MIT) ; image_providers registry, image routes
description: Use when generating or editing an image with FLUX (Black Forest Labs): fast FLUX schnell with a seed, FLUX Kontext for its edits, FLUX 3 text-to-image or multi-reference edit; when a recipe must replay identically, a seed must be noted, a Workshop art-direction sheet is made, or a FLUX edit refuses the space identity or comes out in the wrong format.
---
## Overview

The family has two image members. **Fast FLUX** (`flux`, FLUX schnell) does text-to-image and returns a **seed**:
it is the only image generator in the app that replays a recipe pixel for pixel. Its edits go through **FLUX
Kontext**, which takes only **one** input image. **FLUX 3** (`flux-3`) does text-to-image and multi-reference edits,
without a seed. Neither renders a transparent background.

## Quick reference

- [CHOICE] Fast FLUX to search quickly and for anything that must replay identically: Workshop art-direction sheets
  and sketches, 🔁 recipes. It is the default sheet generator when none is chosen.
- [CHOICE] FLUX 3 for a more polished final image, or for an edit that must keep the space identity (mascot,
  products): it receives several references.
- [METHOD] Seed: it shows with 🔒 on the sheet. "Replay the locked recipe" sends the same prompt and the same seed,
  hence the same image. Change one clause at a time to know which one mattered.
- [PITFALL] The seed replays only with the same prompt, the same format and the same member. It carries nothing to
  FLUX 3 or to another prompt.
- [PITFALL] With a generator other than Fast FLUX, the recipe keeps the prompts and the chaining, not the exact image.
  The Workshop says so in its note under the generator choice.
- [PITFALL] Editing with Fast FLUX = FLUX Kontext, one image only. Asking for the space identity is refused before
  any spending: switch to FLUX 3 or another multi-reference model.
- [PITFALL] A FLUX edit (Kontext or FLUX 3) comes out in the requested format, not in the input image's; with no
  format, it comes out vertical. Pick the source image's format before the run.
- [PROMPT] Kontext edit: a short instruction, "change only X", then what must stay (face, outfit, framing). Kontext
  keeps the identity of a single subject well.
- [PROMPT] Natural sentences: subject, action, setting, light, style. No negative field in the app: write the
  exclusion in positive form ("plain white background", "no text").
- [PITFALL] Transparent background: no member has a background field; writing it in the prompt gives an opaque
  background. Ask for "plain light grey background", then cut out (background removal sheet).
- [COST] FLUX 3 renders one image per call: n images = n calls, billed n times. The quote counts them.
- [COST] The quote prices a Kontext edit at the Fast FLUX rate, while Kontext is billed per megapixel, several times
  more (survey 2026-11). The invoice exceeds the quote.
- [COST] Fast FLUX is the cheapest of the family: find the composition there, then move to FLUX 3 for the final.
  That move gives another image, with no shared seed.
- [CHOICE] FLUX 3 has neither a "Quality" row nor a "Resolution" row in the model pill: the app fixes its
  resolution. Not in the app yet: choosing FLUX 3's resolution, or keeping Kontext as a separate edit model.
- [CHOICE] fal's safety checker is on for Fast FLUX text-to-image.

## Example

Brief: "An episode cover, a lighthouse at night in the rain, engraving style; I want to be able to redo it exactly
later, then a dawn variant."

Prompt (Fast FLUX, landscape format):

```
A lone lighthouse on a rocky cliff at night, heavy rain slanting across the beam of light, rough sea below.
Black and white engraving style, fine cross-hatching, high contrast. Full frame edge to edge, no text.
```

Settings: Fast FLUX, landscape format, seed left free on the first run then noted on the kept image. For the variant,
same seed and same text, one clause changed: "at dawn, pale light on the horizon" instead of "at night". For the
final, FLUX 3 with the same prompt: it is a new image, to approve as such.

## Common mistakes

- Asking FLUX 3 to "reuse the seed" of Fast FLUX: it has no seed, the image changes.
- Editing with the space identity while Fast FLUX is selected: refused. Pick FLUX 3.
- Running an edit without choosing a format: the square or horizontal image comes back vertical.
- Writing "transparent background": opaque background. Plain background, then cut out.
- Trusting the quote of a Kontext edit: it is underestimated.
