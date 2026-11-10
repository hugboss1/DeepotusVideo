---
famille: minimax-music
natures: [musique]
ids: [minimax-music-26, minimax-music-20, minimax-music-3]
voies: [fal]
releve: 2026-11-09
source: scenario-minimax-music, scenario-audio (scenario-labs/skills, MIT) ; music_service registry, Music screen of Sound & VFX
description: Use when you want a real sung song with MiniMax Music (2.6, 2.0 or 3): verses and choruses, lyrics you write or the model writes, opening theme, brand anthem, sung jingle, song for a music video, [Verse] [Chorus] [Bridge] tags, required lyrics refused, MiniMax instrumental, song several minutes long.
---
## Overview

MiniMax Music sings a complete song from two fields: the description (the style) and the lyrics (the words). The
three members are not set the same way:
- **2.6**: optional lyrics and an "instrumental" box; duration picked by the model; price per track.
- **2.0**: lyrics **required**; no instrumental; duration picked by the model; price per track.
- **3**: lyrics **required**; duration slider and seed; price per second of the requested duration.

## Quick reference

- [PROMPT] The description carries the style only: genre, mood, tempo, key, voice timbre ("warm female alto,
  close-mic"), instruments, production. Never lyrics: the model would describe instead of singing.
- [PROMPT] The lyrics carry the words only, one section tag per line. The editor adds verse, chorus and bridge; the
  app sends them as `[Verse]`, `[Chorus]`, `[Bridge]` (and `[Intro]`, `[Outro]`). Any other tag (`[Pre Chorus]`,
  `[Inst]`, `[Solo]`) is sent as is.
- [PROMPT] Two to four lines per section. A line break = a new sung line; a blank line between sections = a breath
  (public source, checked 2026-11).
- [PROMPT] In parentheses, a performance cue, not a sung word: "(whispered)", "(belted)".
- [PROMPT] End with `[Outro]`: without it, the song may stop abruptly.
- [PROMPT] English and Mandarin sing most reliably (public source, checked 2026-11). French works, but check the
  diction before approving.
- [PITFALL] 2.0 and 3 refuse lyrics that are too short, before any spend: tags do not count, only sung words do.
- [METHOD] 2.6: "instrumental" box checked by default; the lyrics editor only shows once the box is unchecked.
  Unchecked with empty lyrics: the model writes the lyrics itself from the description.
- [PITFALL] Lyrics left empty on 2.6 hoping for an instrumental: it sings invented words. Check the box.
- [METHOD] The "persona skeleton" button lays down an outline (verse, chorus, bridge) fed by the brand space: a
  starting point, to rewrite before the run.
- [COST] 3 is billed on the requested duration, not the returned one: set the slider to the useful length.
- [CHOICE] Short song at the lowest price: 2.0. Instrumental, or lyrics written by the model: 2.6. Controlled length
  or a reproducible take (seed): 3.
- [PITFALL] The seed of 3 gives the same song back only with identical settings; changing one word gives a new take.
- [CHOICE] Not in the app yet: covering an existing track in another style, the instrumental switch of 3, the
  output format choice.

## Example

Brief: "a 30-second sung jingle for my bakery, cheerful, in English".

Settings: MiniMax Music 3, duration on the wanted length, a fixed seed (any integer) from the first try.
Description:

```
Bright acoustic pop jingle, 112 BPM, C major, cheerful female lead with a light doubled chorus, ukulele,
hand claps, glockenspiel, clean radio-ready mix
```

Lyrics:

```
[Verse]
Golden crust at early light
Warm bread waiting, baked just right

[Chorus]
(belted) Come on in, the oven's on
Fresh every morning, sing along

[Outro]
Fresh every morning
```

Listen. If the voice is right, keep the seed: an identical relaunch gives it back; change the seed for another take.

## Common mistakes

- Writing "happy pop song about bread" in the lyrics: it sings it word for word.
- Putting the lyrics in the description: the song describes instead of singing.
- Picking 2.0 for an instrumental: it requires lyrics and has no instrumental box.
- Leaving the slider of 3 far beyond the need: the bill follows the requested duration.
