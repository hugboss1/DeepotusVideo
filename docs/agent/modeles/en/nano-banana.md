---
famille: nano-banana
natures: [image]
ids: [nano-banana, nano-banana-pro, nano-banana-2.1]
voies: [fal]
releve: 2026-11-09
source: scenario-image, scenario-gemini-image, scenario-multi-reference, scenario-consistency, scenario-product-shots (scenario-labs/skills, MIT) ; image_providers and pricing registries
description: Use when generating or editing an image with Nano Banana (Google's Gemini image): Nano Banana, Nano Banana Pro, Nano Banana 2.1, instruction-based editing, merging several reference images, keeping a character or product identical, faithful product shots, a misspelled word in the image, choosing the 1K, 2K or 4K resolution, the cheapest Nano Banana member.
---
## Overview

Nano Banana generates an image from text or edits images by instruction, with several references. Three members:
Nano Banana (the oldest), Nano Banana Pro (complex edits and image merging) and Nano Banana 2.1. No member has a
seed, a mask, a negative field or a transparent background. Pro and 2.1 have a "Resolution" row in the model pill.

## Quick reference

- [PROMPT] Sentences: subject, setting, light, style. A comma-separated keyword list renders worse.
- [PROMPT] Separate what is imposed from what the model may invent. Invented details obey the constraints too ("no
  lettering anywhere" also forbids decorative runes).
- [PROMPT] Identity: state outright that the facial features stay identical while pose, light or setting change.
- [PROMPT] Several references: one line per image, "Image N = <job> only", then what it must **not** lend. An image
  lends everything it shows unless forbidden (the character in a style reference walks into the scene).
- [PROMPT] Put first the job most often ignored (often style), with "This is the most important job". Lend concretely:
  "copy its soft clay materials and warm bounce light", not "use its style".
- [PROMPT] One main subject per image. Two identities split the attention: generate them separately, then bring them
  together with an edit.
- [PITFALL] With no mask, a local edit is written as a sentence: name the area, the change, and what does not move.
- [PITFALL] With no seed, a retry gives a variation, never the same image. Keep the good output.
- [PITFALL] A word comes out warped: do not re-run the whole visual. Pass the kept image back as a reference and spell
  the word letter by letter ("spelled L, U, M, E, N"), changing nothing else.
- [PITFALL] Nano Banana and Pro: an edit keeps the input image's frame unless a format is requested. Nano Banana 2.1
  always receives the request's format: set it to the input image's format so it is not cropped.
- [PITFALL] No transparent background: the image comes out opaque and the reply says so. Ask for "plain white
  background", then cut out (cutout sheet).
- [PITFALL] "Film still" or "cinematic" often bake in black bars. Add "full frame edge to edge, no letterboxing".
- [PROMPT] Visible skin: name the texture ("visible pores, fine peach fuzz"), or the render comes out airbrushed.
- [METHOD] Product shot: start from the real photo, never from text. "Preserve-first" prompt: the exact product from
  the reference, proportions and colors unchanged, the text already on the label quoted word for word, then the
  surface, the light and the contact shadow.
- [METHOD] Product check: read the label letter by letter. A label that drifted is re-run from the source photo with
  a tighter clause, never from the faulty output.
- [METHOD] A set (angles, poses, scenes) = one call per item. The image count of a call only gives variations of the
  same prompt.
- [METHOD] Consistency on Pro and 2.1, which take many references: fill the slots with approved views of the same
  character (front, profile, full body), clean and without a setting.
- [METHOD] A reference leaking: check that its job is visible and that nothing else from it is. Fix by tightening its
  line and re-running, not by editing the output.
- [CHOICE] Nano Banana to iterate cheaply; Pro for complex edits, image merging and product fidelity; 2.1 for
  everyday use with an adjustable resolution.
- [CHOICE] The reference count in Members is the app's limit. For Nano Banana (the first one), it is lower than the
  provider's, as a precaution.
- [COST] The price gap is mostly **between members**, less between resolutions. Compare the quote of two members
  before a series.
- [COST] Pro: 2K costs the same as 1K, 4K costs double. Take 2K straight away for a final; 4K only for print.
- [PITFALL] With no choice, Pro runs at 1K: set the "Resolution" row to 2K, same price.
- [COST] Nano Banana 2.1 is billed by tokens: the resolution sets the price, each reference adds input cost, and the
  quote stays an estimate. Draft at 1K, final at the wanted resolution.
- [CHOICE] Not in the app yet: thinking level, the provider's web search, a frame taken from a video, a lighter and
  faster member, resolutions below 1K.

## Example

Brief: "my blue ceramic mug (photo attached) on a terrace table in the morning, in the mood of my moodboard, for a
square post".

References: image 1 = the mug photo; image 2 = the moodboard. Prompt:

```
A photo for a square social post. Each reference picture has exactly one job.
Image 1 (the blue ceramic mug) = subject only. Keep the exact mug: shape, handle, glaze color and the small white
rim unchanged. Do not copy its studio background or lighting.
Image 2 (the moodboard) = mood and color palette only: warm early-morning light, soft cream and terracotta tones.
Do not copy any object, plant or furniture from it.
The mug stands on a weathered wooden café table on a terrace, low side light from the left, a soft contact shadow
falling right, shallow depth of field. Full frame edge to edge. No lettering anywhere.
```

Settings: Nano Banana Pro, 2K resolution (same price as 1K), square format requested, one image per call. Check: the
mug's shape, handle and white rim; the setting reuses no object from the moodboard. Another angle = a new call with
the same prompt and only the last clause changed.

## Common mistakes

- Re-running to get "the same image, but better": with no seed, it is another image.
- Writing "transparent background": the output is opaque. Plain background, then cutout.
- Giving two references with no job: their features blend.
- Chaining each edit onto the previous one: the product drifts. Go back to the source photo.
