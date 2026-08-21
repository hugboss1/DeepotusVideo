# 🐙 Deepotus Video Gen — v2.4.0

Local Windows studio for generating 9:16 crypto/Web3 videos — Seedance clips,
HeyGen talking avatars, spatial compositions, and RSS→reel news posts — with a
node-based **Studio**, a **Scheduler**, a real-time **cost widget**, and
**bring-your-own** API keys. Everything runs on your machine; only provider
calls (fal.ai, HeyGen, ElevenLabs, Anthropic/OpenAI/Gemini) and your publishes
leave it.

## Repository layout
- **`backend/`** — FastAPI app (Python). Source of truth for `/api/*` and the
  app version (`app/config.py`). Frontend is served from here at `/`.
- **`frontend/dist/`** — the **compiled** React bundle (`assets/index-*.js`) +
  `index.html`. ⚠️ `dist/` is still the **source of record for the UI**: every
  feature since v1.15.1 was added by surgically patching the minified bundle
  (`scripts/patch_bundle_*.py`), and those patches are NOT in `frontend/src`.
- **`frontend/src/`** — the recovered **initial React source** (v1.15.1
  pre-patch state). `npm run build` reproduces the pristine v1.15.1 assets
  byte-for-byte — see `frontend/SOURCE.md` for provenance, proof and the gap
  with today's bundle. Do **not** rebuild over `dist/` without replaying the
  patches.
- **`installer/deepotus.iss`** — Inno Setup script that packages the whole app
  into a one-file installer.
- **`scripts/`** — silent launcher + `build-installer.ps1` (full build).
- **`docs/guide/`** — illustrated FR/EN user guide (HTML + PDF), served in-app
  at `/guide`.
- **`assets/`** — brand logo/icons.
- **`backend/app/assets/starter/`** — the **starter catalog**: 606 sound
  effects, 80 particle textures and 5 animated sequences shipped with the app,
  all **CC0**. Tracked on purpose (22 MB): upstream download URLs carry a
  content hash that changes on every release, so a repo without these files
  would stop being buildable. Regenerate with
  `python scripts/build_starter_catalog.py --fetch`.

**Not tracked** (see `.gitignore`): the bundled embedded **Python runtime**
(`runtime/`, ~137 MB) and **ffmpeg** (`bin/`, ~193 MB) — fetched at build time;
the built installer (it's a Release asset); and any secrets. **Your API keys
and database are never in this repo** — they live per-machine in
`%LOCALAPPDATA%\DeepotusVideoGenData`.

## Use it on any machine (easiest)
Download the latest installer from the **[Releases](../../releases)** page and
run it. It's self-contained (bundles Python + ffmpeg, zero prerequisites),
installs to `%LOCALAPPDATA%\DeepotusVideoGen`, and preserves your data across
reinstalls. After install, launch from the desktop shortcut and paste your keys
in **Settings → API keys**.

## Build from source
`powershell -ExecutionPolicy Bypass -File scripts\build-installer.ps1` —
downloads the embedded Python + ffmpeg, installs backend deps, and compiles the
installer (auto-installs Inno Setup 6 via winget if missing). Needs a build
Python on PATH matching the embeddable minor version.
> Note: `scripts\build-installer.ps1` (`$StageRoot`) and `installer\deepotus.iss`
> (`StageDir`, `OutputDir`) contain machine-specific paths — adjust them for
> your machine before building.

## What works with no API key at all
Since v2.2.0 the **Sound & VFX** screen is usable the moment you install,
before any key is configured:

- **606 sound effects**, browsable and playable, in 8 families (impacts,
  footsteps & materials, interface, retro/digital, sci-fi, objects, cards,
  jingles). One click copies a sound into your Library, where the Edit
  timeline and the render pipeline treat it as any other user asset.
- **Particle sprite generation** — 12 presets (explosion, smoke, gold burst,
  sparks, magic aura, muzzle flash, dust, trail, embers, shockwave, lightning
  arcs, ash & snow) over 80 CC0 textures. The emitter is simulated **locally**
  (Pillow + ffmpeg): no network call, no credits, $0. Output is an ordinary
  sprite job, so the Library Sprites tab, the animated viewer, the ZIP export
  and the Unity pack all work on it.
- **5 ready-made animated sequences** assembled into a sprite sheet in one
  click.

Everything above is Creative Commons Zero ([Kenney](https://kenney.nl)):
free for commercial use, no attribution required. Attributions are shipped in
`backend/app/assets/starter/NOTICE.txt` anyway.

Since v2.3.0, **Card Forge** — the playing-card editor under Game Assets — is
fully usable with no key at all too: 300 DPI print exports with bleed and safe
zone (`TrimBox`/`BleedBox`, cut marks), CSV-driven decks, PBR textures (8
maps), and glTF/GLB 3D export with real card thickness, all computed locally
(Pillow + pypdf). v2.4.0 adds the pixel-proven **layered export** and a free,
local **Forge 3D graph** — plane/relief treatments, tiled materials,
holographic finishes, glTF/GLB + STL artifacts. The only steps that use keys
are optional: AI face generation (fal.ai) and the image→3D engines of the
Forge 3D graph (5 fal engines billed in $, or Meshy 6/7 in credits — the
price is shown before every launch).

## Required API keys (bring-your-own)
**fal.ai** is required (images + video, and **music generation** since v2.2.0 —
Lyria 3, Stable Audio 2.5, MiniMax Music 2.6, CassetteAI, all on the same key).
Optional: **HeyGen** (avatars), **ElevenLabs** (voiceover and SFX generation
from a description), **Meshy** (image→3D in the 3D Studio and in Card Forge's
mesh nodes, billed in Meshy credits), **Anthropic/OpenAI/Gemini** or local
**Ollama** (news summaries, marketing plans, AI script polish), **X/Telegram**
(auto-publish).
See `backend/.env.example`.

## Patching the compiled UI (read before editing `frontend/patches/`)
The UI is a minified bundle modified by `scripts/patch_bundle_*.py`. Two traps
have cost real debugging time — both fail **silently**, leaving a valid bundle:

1. `patch_bundle_sonvfx.py` **refreshes its injected block in place**, and
   `vfxrack` / `subs` do not merely append their own blocks — they also modify
   text *inside* the sonvfx block. Refreshing it silently reverts 22 of their
   edits. After editing `frontend/patches/son-vfx-montage.js`, always run
   **`python scripts/reapply_inblock_patches.py`** (it refreshes, then replays
   those pairs, restricted to the block so out-of-block pairs are never
   duplicated). `repatch_all.py --from sonvfx` does **not** cover this case.
2. The injected blocks are stored **CRLF**. An editor that rewrites a patch
   source as LF makes every multi-line anchor fail to match, with no symptom
   other than `anchor count=0`.

Verify a bundle change by **inventory diff**, never by eye — marker counts and
file size will not show the loss:
```
git show HEAD:frontend/dist/assets/index-BEOJX8L5.js \
  | grep -o "function [A-Za-z_$][A-Za-z0-9_$]*(" | sort -u > /tmp/before.txt
grep -o "function [A-Za-z_$][A-Za-z0-9_$]*(" frontend/dist/assets/index-BEOJX8L5.js \
  | sort -u | comm -23 /tmp/before.txt -
```

## License

**Proprietary — © 2026 Deepotus (hugboss1). All rights reserved.**
Provided for the author's own development and backup. Not licensed for redistribution, resale, or public use — see [`LICENSE`](LICENSE). Bundled third-party components (Python, ffmpeg, the packages in `backend/requirements.txt`) keep their own licenses.

## Changelog

Full version history lives in [`CHANGELOG.md`](CHANGELOG.md).

---

🐙 **From the deep, for the deep.**
