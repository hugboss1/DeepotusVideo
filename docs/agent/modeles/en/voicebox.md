---
famille: voicebox
natures: [voix]
ids: [voicebox]
voies: [local]
releve: 2026-11-09
source: scenario-audio (scenario-labs/skills, MIT) ; voice_providers facade (Voicebox v0.5.0 contract), voice_direction
description: Use when you want a free, local or offline voiceover with Voicebox, when choosing the voice provider (Auto, ElevenLabs or Voicebox), when drafting a narration before the paid voice, when creating or picking a Voicebox voice profile (Kokoro, Chatterbox, cloned voice), or when Voicebox is unreachable, slow or has no profile.
---
## Overview

Voicebox is a **local and free** voice server, started next to the app. It has no key and no quote. Voices are
**profiles** created in the Voicebox application (preset or cloned voice); the app only reads them. The synthesis
engine comes from the profile: Kokoro by default, Chatterbox for cloning on a recent graphics card. It serves the
same screens as the ElevenLabs voice: Sound & VFX › Voiceover, Quick's Voiceover tab, the Studio Voiceover node,
Chapters.

## Quick reference

- [METHOD] The provider is chosen in Settings › Provider defaults › Voice provider. "Auto" takes ElevenLabs when its
  key is set, else Voicebox when it answers. To force Voicebox while an ElevenLabs key is set, pick it explicitly.
- [PITFALL] Voicebox set but unreachable: the setting falls back to ElevenLabs when its key is set, and the
  Voiceover page goes back to paid mode (quote, two clicks). Quick and the Voiceover node, which ask for Voicebox
  explicitly, are refused with no switch. Start the server (Settings › Provider defaults gives the command).
- [PITFALL] No profile: generation fails. Create one in the Voicebox application (Voices), then reload the voice
  list.
- [CHOICE] With no voice picked, the app takes a profile in the text's language, Kokoro preferred, else the first
  profile found. An inherited ElevenLabs voice id is ignored in favour of that profile.
- [PROMPT] The text holds only the words to speak, in the profile's language. The language sent is the one of the
  "Text language" selector (French or English).
- [PITFALL] Voicebox reads no performance tag. Known tags (`[whispers]`, `[laughs]`…) are stripped before sending;
  any other bracket is sent as is and will be read.
- [CHOICE] Model and settings (stability, speed…) are fixed by the Voicebox application: those on the page are
  ignored. Tone is set by the choice of profile and by punctuation.
- [COST] Free: a single click, no quote, no cap. The price is paid in time: synthesis is asynchronous and much
  slower on a CPU alone than with a graphics card, especially with Chatterbox.
- [METHOD] Narration draft: time the edit on a Voicebox voice, then generate the final voice on ElevenLabs with the
  same text. The pacing will change: re-time the cuts afterwards.
- [CHOICE] Cloning happens in the Voicebox application, not through "Clone this voice" (which creates an ElevenLabs
  voice). Only clone a voice you have the right to.
- [CHOICE] No expressive acting, no tags, no multi-voice dialogue: for these, the ElevenLabs voice (ElevenLabs
  sheet).

## Example

Brief: "a free French voiceover to time my teaser edit; I'll pay for the real voice once the cuts are locked".

Settings: Settings › Provider defaults › Voice provider: Voicebox. In the Voicebox application, a French profile on
Kokoro. Sound & VFX › Voiceover: the "French profile" voice, text language French, script:

```
Sous la surface, quelque chose remonte… Et cette fois, personne ne l'arrêtera.
```

One click, free. The track joins the Library (sounds) and goes into the Montage. Cuts locked: switch the provider
back to ElevenLabs and generate the final version.

## Common mistakes

- Leaving v3 tags in the script thinking they will play: they are stripped, the read stays flat.
- Setting stability or speed on the page with Voicebox active: no effect.
- Having no profile in the text's language: the app takes another profile, whose voice is not made for that
  language. Create the language's profile.
- Running a long text on a CPU alone without planning the time: test one sentence first.
