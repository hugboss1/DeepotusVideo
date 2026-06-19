# 🐙 Deepotus Video Gen — v1.15.1

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
  `index.html`. ⚠️ The React **source is not in this repo** — the app ships
  compiled-only, and UI changes are made by surgically patching the minified
  bundle. `package.json` is kept for reference.
- **`installer/deepotus.iss`** — Inno Setup script that packages the whole app
  into a one-file installer.
- **`scripts/`** — silent launcher + `build-installer.ps1` (full build).
- **`docs/guide/`** — illustrated FR/EN user guide (HTML + PDF), served in-app
  at `/guide`.
- **`assets/`** — brand logo/icons.

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

## Required API keys (bring-your-own)
**fal.ai** is required (images + video). Optional: **HeyGen** (avatars),
**ElevenLabs** (voiceover), **Anthropic/OpenAI/Gemini** or local **Ollama**
(news summaries, marketing plans, AI script polish), **X/Telegram**
(auto-publish). See `backend/.env.example`.

## License

**Proprietary — © 2026 Deepotus (hugboss1). All rights reserved.**
Provided for the author's own development and backup. Not licensed for redistribution, resale, or public use — see [`LICENSE`](LICENSE). Bundled third-party components (Python, ffmpeg, the packages in `backend/requirements.txt`) keep their own licenses.

## Changelog

Full version history (v1.8.0 and earlier) lives in [`CHANGELOG.md`](CHANGELOG.md).

---

🐙 **From the deep, for the deep.**
