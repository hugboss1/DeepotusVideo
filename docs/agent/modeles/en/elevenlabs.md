---
famille: elevenlabs
natures: [voix, sfx_texte, musique]
ids: [eleven_multilingual_v2, eleven_v3, eleven_flash_v2_5, elevenlabs-direct, elevenlabs-v2-fal, elevenlabs-music-2.5]
voies: [elevenlabs, fal]
releve: 2026-11-09
source: scenario-elevenlabs, scenario-audio (scenario-labs/skills, MIT) ; elevenlabs_service, voice_direction, sfx_service, music_service registries
description: Use when making a voiceover or narration with ElevenLabs (Multilingual v2, Eleven v3, Flash v2.5), directing the delivery with tags ([whispers], [laughs], [excited]), setting stability, similarity or speed, when a tag is read aloud, when generating an ElevenLabs SFX sound effect (direct or via fal) or ElevenLabs Music 2.5 music, or when weighing quality, expressiveness and cost of a voice.
---
## Overview

ElevenLabs serves three natures. **Voice** (Multilingual v2 by default, expressive Eleven v3, fast and cheaper
Flash v2.5) goes through the ElevenLabs key. The **sound effect** from a description exists direct (ElevenLabs key)
and as a twin via fal. **Music** (Music 2.5) goes through fal. Screens: Sound & VFX › Voiceover (also Quick's
Voiceover tab and the Studio Voiceover node); Sound & VFX › SFX › "Generate SFX" and the Montage Sounds drawer ›
Generate; Sound & VFX › Music › Generate.

## Quick reference

- [PROMPT] Voice: the script holds **only** the words to speak, in their language. "Say this angrily" written in the
  text may be spoken. Delivery goes through tags (v3) or through the settings.
- [CHOICE] Eleven v3 is the only member that reads inline tags (`[whispers]`, `[sighs]`, `[excited]`…). On
  Multilingual v2 and Flash v2.5, the app strips the known tags before sending and says so in the closing note.
- [PITFALL] Only the palette's tags are stripped. Any other bracket ("[Scene 2]") is sent as is and will be read.
  On v3, a tag outside the palette is sent too, with a note: it may be read aloud.
- [PITFALL] A tag is a request, not a guarantee: two identical runs can perform differently. Listen before
  approving, retry when the tag was ignored.
- [PROMPT] Pauses: through punctuation (ellipsis, short sentence). v3 does not read SSML pause tags.
- [CHOICE] Eleven v3 sets only stability, in three notches: Creative (more acting, follows tags better), Natural,
  Robust (steadier, responds less to tags). Multilingual v2 and Flash v2.5 have the Stability, Similarity and Speed
  sliders.
- [CHOICE] Calm narration, quality: Multilingual v2. Expressive acting or emotions: Eleven v3. Volume, drafts, long
  texts: Flash v2.5.
- [PITFALL] "Text language" (French or English) picks the language's default voice; it translates nothing and is not
  sent to the model. Write the text in the wanted language and pick a voice that speaks it.
- [METHOD] A text longer than the per-request limit ("chars max" column) is split at sentence ends, then joined. On
  Sound & VFX › Voiceover and Quick, the field stops at that limit; long narrations go through Chapters, which stay
  on the app's default model.
- [COST] Voice is paid per character sent, tags included (price column, per 1,000 characters). First click: the
  quote; second click: the synthesis.
- [CHOICE] "Clone this voice" (voice library) creates an ElevenLabs voice from takes: only clone a voice you have the
  right to.
- [PROMPT] Sound effect: name the source, the material, the action and the space ("a ceramic mug set down on a
  wooden table, small kitchen, close and dry"). One event per sound; a variant is another generation.
- [PROMPT] A dry acoustic is stated positively ("dry, close-miked"), not with "no reverb".
- [CHOICE] Sound effect: high "Fidelity" sticks to the text, low leaves more freedom. Duration: auto (the model
  chooses) or exact, clamped to the range in Members.
- [CHOICE] Without an ElevenLabs key but with the fal key, the app serves the fal twin ("via fal") with the same
  description. After a moderation refusal, try the other route before rewriting.
- [COST] Direct sound effect: quoted per requested second and per variation; with auto duration, the cost follows
  the rendered length. The fal twin is "price to be measured": quoted at zero, the spending cap does not stop it.
  Sound & VFX's "Generate SFX" always runs two variations.
- [PROMPT] Music: genre, mood, instruments and tempo in the description; the duration in its field. A mood tile
  already carries a tempo: do not write a second one.
- [CHOICE] Music: the "instrumental" switch is the only reliable way to get a track without vocals. Switch off, the
  model may sing, but the lyrics field is ignored (note): you do not choose the words.
- [COST] Music 2.5 is billed per started minute: a track of one minute and two seconds pays two minutes.
- [METHOD] Music: the same seed and the same settings give back the same track. Change the seed for another take.
- [CHOICE] Not in the app yet: language code, voice seed, multi-voice dialogue, dubbing, voice changing, loopable
  sound (`loop`), section-based music plan, imposed lyrics on Music 2.5.

## Example

Brief: "a few seconds of French voiceover for a coffee ad: a knowing whisper, then a cheerful tone".

Settings: Sound & VFX › Voiceover, model Eleven v3, stability Creative, text language French, a French voice from
the library. Script (the words stay in French, the tags in English):

```
[whispers] Chut… le café est prêt. [excited] Et cette fois, il est vraiment bon !
```

First click: the quote shows; second click: the synthesis. Listen: if the whisper is ignored, retry as is. For a
calmer read, switch to Multilingual v2: the tags are stripped and the tone goes through stability.

## Common mistakes

- Writing the tone instruction in the script ("(angry)"): it is read. A palette tag on v3, otherwise stability.
- Keeping tags when switching to Multilingual v2 or Flash v2.5, then being surprised by a flat read: they were
  stripped.
- Putting several noises in one description ("door, steps, then scream"): one event per sound, assembled in the
  Montage.
- Asking Music 2.5 for a song with lyrics: the lyrics are not sent. Pick a music member with a "lyrics" column.
- Choosing a music duration just above a round minute: the started minute is paid.
