---
famille: _commun
releve: 2026-11-09
source: scenario-image, scenario-video, scenario-consistency, scenario-moderation, scenario-text-overlay, scenario-audio (scenario-labs/skills, MIT)
description: Use when reading any model sheet: prompt, reference, on-image text, sound, consistency and moderation rules that hold for every image, video, audio and 3D family.
---
## Overview

These rules hold for every family. A family sheet refines or overrides them; when it does, the sheet wins. A model's
parameters (durations, formats, prices) are read in the "Members" block, never in the text.

## Quick reference

- [PROMPT] Write full sentences, not a list of keywords.
- [PROMPT] A written word draws what it names: "no gray" brings gray in. Phrase it positively ("plain white
  background") or use the negative field when the member has one.
- [PROMPT] Set the format in its field, never in the text: a ratio written in prose gives black bars or a crop.
- [PROMPT] Ask for a transparent background through the parameter or a cutout; written in the prompt, it comes out
  opaque.
- [PROMPT] On-image text: quote it, state its role and position, end with "no other text".
- [PITFALL] A price, legal line, number or a brand's existing logo is **never** generated: overlay it afterwards
  (Templates, Montage, Card Forge), a generated figure can come out wrong. A new logo is drawn (Recraft sheet).
- [PROMPT] Prompt in English. Text to display stays quoted in its own language, accents included.
- [METHOD] Editing: "change only X", then the list of what must stay. One change per pass; repeat the list on every
  pass.
- [METHOD] References: give each image a role by position ("image 1: face identity, image 2: outfit"). A reference
  with no role is often ignored.
- [METHOD] Consistency: one strong, approved reference feeds **every** image of the set. Never chain an output onto
  the previous one: drift adds up.
- [METHOD] Base + delta: a base text, identical from one image to the next, describes everything that does not
  change; only the last clause changes.
- [PITFALL] A seed does not carry an identity from one prompt to another, and "same as before" has no memory.
- [METHOD] Continuity and identity are different: the last frame of a kept shot can open the next shot (a match
  cut), but the character is always checked against the approved image, never against the previous output.
- [METHOD] Image-to-video: describe only the motion, not what is already visible. One camera move and one action per
  shot; time markers when there are several beats.
- [PITFALL] Orbiting a subject seen in a single photo: the model invents the hidden sides. Limit the angle, or give
  an end image that shows the wanted side.
- [METHOD] Still image first, approved, then animate from that image. Retry from the approved image, never from an
  output that drifted.
- [PROMPT] Sound: name sounds positively. "No music" often gets the track refused; to drop audio, use the member's
  switch.
- [COST] Draft first when the member allows it (low tier, low resolution, preview), at the final duration; the final
  afterwards.
- [CHOICE] Moderation: after a refusal, switch **provider** first at a similar cost (the twin route counts), because
  one family shares one filter. Then one honest rewrite, then stop.
- [COST] A video refused after rendering may still be billed.

## Example

Brief: "three views of the same character for a sheet". Generate the front view, approve it, then write for each other
view: "Same character as image 1: short black hair, round glasses, yellow raincoat with two pockets, green boots, plain
unlettered studio background. Change only the view: left profile, nose pointing left." The other views repeat the same
base sentence, only the end changes, and all start from the approved front view.

## Common mistakes

- Putting an exact price or slogan in the prompt: it comes out misspelled. Overlay it.
- Fixing three things at once in an edit: the model changes others. One at a time.
