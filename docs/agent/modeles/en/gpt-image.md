---
famille: gpt-image
natures: [image]
ids: [gpt-image-1, gpt-image-1-mini, gpt-image-2, gpt-image-2-fal, gpt-image-2.5-flare, gpt-image-2.5-sunburst, gpt-image-2.5-flare-fal, gpt-image-2.5-sunburst-fal]
voies: [openai, fal]
releve: 2026-11-09
source: scenario-image, scenario-gpt-image, scenario-multi-reference, scenario-text-overlay (scenario-labs/skills, MIT), image_providers and pricing registries
description: Use when generating or editing an image with GPT Image (GPT Image 2.5 Flare, 2.5 Sunburst, GPT Image 2, GPT Image 1, 1 mini), choosing between the OpenAI key and the fal key, picking a quality tier (low draft, high final, xhigh, max), wanting a real transparent background, several reference images, readable text on packaging or a poster, or when a GPT image drops instructions, comes out opaque or in the wrong frame.
---
## Overview

GPT Image (OpenAI) generates and edits from a single prompt. The app offers GPT Image 1 and 1 mini (OpenAI key only),
GPT Image 2, and GPT Image 2.5 in two variants, Flare and Sunburst. GPT Image 2 and both 2.5 variants exist on two twin
routes: direct (OpenAI key) or via fal (fal key). It is the same model, with two invoices and slightly different
settings. No member has a seed: every run is a new image.

## Quick reference

- [CHOICE] Flare is fast and economical, with quality close to GPT Image 2: it is for everyday work. Sunburst is for
  quality: dense packaging text, figures, diagrams, edits that must hold the geometry.
- [CHOICE] New work starts on 2.5. GPT Image 2 lacks the top tiers. GPT Image 1 and 1 mini have neither a quality
  tier nor a transparent background in the app; 1 mini remains the cheapest for a try.
- [CHOICE] fal route only: several references in an edit, transparent background on Sunburst and on GPT Image 2,
  xhigh and max tiers on 2.5. The direct route sends only ONE input image.
- [COST] The "Quality" row of the model chip moves the price more than the format does: low, medium, high, plus
  xhigh and max via fal on 2.5. Default high. The choice is remembered per model, for every screen.
- [COST] Low draft, high final: low costs a small fraction of high. Search for the composition in low, then rerun the
  kept prompt in high: with no seed, it is a new draw, close but not identical. A higher tier does not guarantee a better result: xhigh and max only when high missed a
  precise requirement.
- [COST] Edit via fal: each reference image is billed as input, on top of the rendered image (surveyed 2026-11).
  Attach only references that have a job.
- [COST] GPT Image 2 direct with no tier chosen: OpenAI applies its own default, and the quote counts high.
- [PITFALL] Real transparent background: 2.5 Flare (both routes), 2.5 Sunburst via fal and GPT Image 2 via fal. The
  words "transparent background" in the prompt set the switch automatically on these members. On the others, the
  image comes out opaque and the reply says so: cut it out afterwards (background removal sheet).
- [PITFALL] A transparent background keeps a colour halo under the erased pixels. Keep PNG or WebP end to end: a JPEG
  or a dark background shows a fringe.
- [PROMPT] Order = weight: style, medium, subject and mood first; then scene, details, light, text. Naming the use
  (advertising, UI mock-up, infographic, key art) sets the level of finish.
- [PROMPT] Photorealism: write "photorealistic" and concrete textures (pores, worn fabric, grain). For a person:
  framing, gaze, what the hands are doing.
- [PROMPT] A detailed brief is normalised, not embellished. Never add a character, brand, slogan or left/right
  placement that was not asked for.
- [PROMPT] Text: on top of the quotes, give a layout brief (zone of each element, size rank, what stays empty), the
  weight, the case and the number of occurrences; end with "no extra words, no duplicate text".
- [PITFALL] Beyond about seven distinct requirements, some drop silently (surveyed 2026-11). Lay down a clean base,
  then one targeted change per edit.
- [PITFALL] Format: direct gives only square, landscape or portrait; a project 16:9 or 4:3 comes out as the nearest
  landscape. Via fal, the project formats pass as they are. Crop afterwards if the exact frame matters.
- [PITFALL] A named public figure gets the image refused: describe an archetype.
- [PITFALL] A complex prompt can take about two minutes (surveyed 2026-11): wait, do not rerun.
- [METHOD] Several references (fal route): one sentence for the medium, then "Each reference picture has exactly one
  job:" and one line per image: "Image N (what it shows) = JOB only. … Do not …". The job most often ignored (style)
  comes first.
- [METHOD] A reference lends everything it shows: say for each one what must not be taken. One main subject per run.
  A leak is fixed by tightening the line and rerunning, not by an edit.
- [CHOICE] Not in the app yet: edit mask, pixel size (4K, true 21:9), several references on the direct route,
  Sunburst transparent background on the direct route, reference-fidelity setting.

## Example

Brief: "A square poster for our COOL LEAF iced tea: the bottle on a mint background, the name large at the top. The
price and the logo will come later."

Prompt:

```
Product advertising poster, clean studio photography. A frosted glass bottle of iced tea stands centered on a
plain mint-green background, with water droplets on the glass and a soft shadow below. Top center, large bold
condensed sans-serif headline in white, all caps, reading "COOL LEAF". The lower third stays empty and calm.
Photorealistic, crisp label edges. No extra words, no duplicate text.
```

Settings: GPT Image 2.5 Sunburst (route according to the key present), square format, quality low for three
drafts; keep the best composition, then the same prompt in high, a single image. Read the headline letter by letter.
The price and the logo are overlaid afterwards in the empty zone (Templates or Card Forge).

## Common mistakes

- Searching for a composition in high: each try costs the final price. Drafts in low.
- Attaching three references on the direct route: only the first one goes. Use the twin via fal.
- Writing "transparent background" on GPT Image 1 or on Sunburst direct: the image comes out opaque. Use Flare or a
  member via fal.
- Saving a cut-out image as JPEG: the background turns opaque and a fringe appears.
- Picking xhigh or max straight away, without knowing what high missed.
- Stacking ten instructions in one prompt: some disappear. Base first, targeted edits next.
