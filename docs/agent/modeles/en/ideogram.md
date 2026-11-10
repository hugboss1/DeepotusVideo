---
famille: ideogram
natures: [image]
ids: [ideogram-4.5]
voies: [fal]
releve: 2026-11-09
source: scenario-image, scenario-ideogram, scenario-text-overlay, scenario-brand-kit (scenario-labs/skills, MIT), image_providers and pricing registries
description: Use when generating or editing an image with Ideogram 4.5, when text in the image must come out right (poster headline, shop sign, cover, packaging, brand name, slogan), when deciding whether to turn off prompt rewriting (magic prompt), picking a quality tier, wanting an edit that barely touches the rest or a painted look (watercolor, gouache, pencil), or when an Ideogram image paraphrases the copy or comes out opaque.
---
## Overview

Ideogram 4.5 (via fal, fal key) specialises in typography: readable, correct text in the image. It does text to image
and edits. In an edit, the first image is the one being changed, the following ones are references. It has no seed and
renders no transparent background in the app.

## Quick reference

- [CHOICE] Pick it when the text matters: poster, headline, shop sign, cover, label. It also holds a painted medium
  (watercolor, gouache, pencil) better than generalist models (surveyed 2026-11).
- [CHOICE] In an edit, it changes fewer pixels outside the target zone than a generalist (surveyed 2026-11, one
  sample): a good choice to change a sign's text, add or remove an object.
- [CHOICE] Weaker on a photorealistic product, on a character described in detail, and for changing a precise
  material or colour: it drifts to a nearby hue and may recolour what had to stay.
- [PROMPT] The "Prompt rewriting" switch of the model chip is on by default: the provider rewrites the prompt and may
  paraphrase the copy. Turn it OFF as soon as there is a slogan, a headline or an exact brand name. Leave it on for a
  short exploration prompt.
- [PITFALL] Rewriting only applies to text to image. In an edit, the switch has no effect: the copy must be quoted
  as is in the prompt.
- [PROMPT] Each piece of copy: in quotes, with its place, weight and style ("headline "SPRING MARKET", top center,
  bold serif"). Few strings, short ones.
- [PROMPT] Brand colours: quote the hex codes verbatim. An unnamed colour drifts from one run to the next.
- [PROMPT] Background for a future overlaid card: reserve a calm, text-free zone (empty top band, dark right third)
  and describe it as such.
- [COST] "Quality" row: low, medium, high. Default high, its most expensive tier: high costs several times medium
  (surveyed 2026-11). Drafts in low or medium, final in high. The format does not change the price (surveyed
  2026-11).
- [PITFALL] With no seed, the high final is a new draw: a composition close to the low draft, not identical. Plan
  two finals, or keep the low draft if it is enough.
- [PITFALL] Tier names do not line up between families: Ideogram's high is its ceiling, not another family's "high".
  Compare at equal price, in Members.
- [METHOD] Edit: the image to change first, then the references, each with a job. Write "keep everything else exactly
  the same" then the list of what must stay.
- [PITFALL] "transparent background" in the prompt: the image comes out opaque and the reply says so. Ask for a
  "plain flat background" in one solid colour, then cut it out (background removal sheet).
- [CHOICE] Not in the app yet: edit mask, keeping the exact canvas of the source image, 2K resolution, precise
  editing, native transparent generation, text as editable layers, character from a reference, seed.

## Example

Brief: "A portrait poster for our spring market, watercolor style, with "MARCHÉ DE PRINTEMPS" at the top and the date
at the bottom."

Prompt:

```
Watercolor poster illustration with soft paper texture. A lively open-air flower market under striped awnings,
baskets of tulips and daffodils, pastel spring light. Top center, large hand-lettered serif headline in deep green
reading "MARCHÉ DE PRINTEMPS". The bottom fifth stays as calm blank watercolor wash, with no text. No other text.
```

Settings: Ideogram 4.5, portrait format, "Prompt rewriting" off, quality low for two or three drafts, then the same
prompt in high. Read the headline letter by letter, accent included. The date is overlaid afterwards in the empty band
(Templates): a generated figure can come out wrong.

## Common mistakes

- Leaving rewriting on with a slogan: it comes out reworded. Turn it off.
- Searching for the composition in high: each draft costs the final price.
- Asking for a transparent background: the image comes out opaque. Solid background, then background removal.
- Comparing two families "in high" as if it were the same tier: compare the prices in Members.
- Putting the image to edit in second position: the first one is the one that gets changed.
