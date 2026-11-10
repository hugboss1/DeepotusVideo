---
famille: mureka
natures: [musique]
ids: [mureka-9.5]
voies: [fal]
releve: 2026-11-09
source: scenario-minimax-music, scenario-audio (scenario-labs/skills, MIT) ; music_service registry, Music screen of Sound & VFX
description: Use when you want a complete, polished song with Mureka 9.5: with your own lyrics or from a description alone, brand song, title for a music video, long lyrics, [Verse] [Chorus] tags, price difference with or without lyrics.
---
## Overview

Mureka 9.5 returns a complete sung song. Two ways to ask for it:
- **with your lyrics**: it sings your words;
- **from a description alone**: it writes the lyrics itself.

The price depends on the case: the request **with lyrics costs less** than the description alone. The model card and
the quote take it into account; the Members block shows the price without lyrics. No duration slider, no seed, no
instrumental box.

## Quick reference

- [COST] Writing lyrics, even short ones, lowers the run price. The description alone is the priciest case.
- [PROMPT] The description carries the style only: genre, mood, tempo, voice timbre, instruments, production. Never
  lyrics.
- [PROMPT] Lyrics: the editor adds verse, chorus and bridge; the app sends them as `[Verse]`, `[Chorus]`, `[Bridge]`
  (and `[Intro]`, `[Outro]`). Any other tag is sent as is.
- [PROMPT] Two to four lines per section, a blank line between sections, `[Outro]` last for a clean ending.
  Performance cues in parentheses: "(softly)".
- [PITFALL] Tags alone do not count as lyrics: an editor holding only empty sections is sent as a description alone,
  at the higher price.
- [PITFALL] No instrumental switch in the app: expect a sung song (a voiceless track on the provider's side: to be
  confirmed). For a track with no voice, take a model with the "instrumental" box.
- [PITFALL] Duration picked by the model: a requested duration is ignored. Trim or loop in the Editor.
- [PITFALL] No seed: each relaunch is a new song. Keep the good take.
- [CHOICE] Long lyrics: the app lets longer texts through to Mureka than to the other song models. Beyond its limit,
  the text is cut at the end, with no warning.
- [METHOD] Test melody and structure on a cheaper song model, then make the final version on Mureka with the same
  lyrics.
- [CHOICE] Not in the app yet: covering an existing track, choosing the duration, instrumental.

## Example

Brief: "an indie-folk song for our association's anniversary video, with our lyrics".

Settings: Mureka 9.5. Description:

```
Warm indie folk, 96 BPM, G major, gentle male lead with group harmonies on the chorus, fingerpicked acoustic
guitar, soft kick, tambourine, mandolin, intimate and hopeful
```

Lyrics (here in French, sung as written):

```
[Verse]
Dix ans déjà, des mains qui se tendent
Des matins froids, des cafés qui attendent

[Chorus]
(all together) On est là, encore là
Et la route continue sous nos pas

[Outro]
Encore là
```

Check the French diction line by line; if a word comes out wrong, rewrite it simpler rather than adding an
instruction to the description.

## Common mistakes

- Leaving the lyrics empty "to see": it is the priciest run.
- Looking for an instrumental from Mureka: the app has no box to ask for it.
- Copying the style into the lyrics ("folk song, warm"): it sings it.
