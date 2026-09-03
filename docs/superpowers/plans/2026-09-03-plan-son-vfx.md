# Son & VFX — parité puis différenciation (plan d'implémentation)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** donner à la catégorie Son & VFX ce qui lui manque pour être crédible face aux références (stems, isolation de voix, tiroir Sons de référence, chanson chantée, direction d'interprétation), puis ce que les références ne font pas parce que Deepotus est local et scriptable (ducking dès la génération, VFX derrière un sujet détouré, recherche par description, voix par personnage bout en bout).

**Architecture :** tout ce qui coûte de l'argent passe par un REGISTRE figé (patron `MUSIC_MODELS`) et un prix affiché avant le tir ; tout ce qui s'écrit atterrit dans le dossier audio de la Bibliothèque avec le sidecar `_sfx_meta.json` (kind, parent, tags) et une ligne `library_assets` (source `sonvfx`) ; les appels réseau passent par des SEAMS de module (`_fal_subscribe`, `_download`, `_post_isolation`, `_http_json`, `_post_voice_add`) que les bancs remplacent. Les écrans sont des couches injectées (`sfxstudio.js`, `vfxrack.js`, `son-vfx-montage.js`) rafraîchies EN PLACE par un outil neuf qui ne touche à aucun `.bak_*` ; un seul patch du bundle natif (Bibliothèque, tag `libsons`, en queue).

**Tech Stack :** Python embarqué stdlib + Pillow + httpx + fal_client (déjà présents), ffmpeg/ffprobe du PATH, FastAPI ; JS ES5 dans les couches injectées ; un service local OPTIONNEL en Python complet (torch + transformers) pour CLAP, hors backend.

**Point de départ mesuré (03/09/2026) :** `main` = `11e0897`, `APP_VERSION = "2.6.0"`. `python` ci-dessous = le python embarqué (`%LOCALAPPDATA%\DeepotusVideoGen\runtime\python\python.exe`, celui que `scripts/run-tests.ps1` choisit). Tous les bancs se lancent depuis `backend/` : `python tests/test_<x>.py`. Commits : sujet SANS accent, corps accentué, pied `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`, `-m` entre guillemets SIMPLES.

---

## Périmètre

Le périmètre est EXACTEMENT les bacs de `### R4. Son & VFX — réponses` du brief `docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md`.

**Lot 1 — parité, dans l'ordre** : P1 stems Demucs (T2) · P2 isolation ElevenLabs + chaîne « améliorer » (T3) · P3 tiroir Sons vue de référence + puce Audio alignée (T4, T5) · P4 chanson chantée, éditeur de paroles structurées, ACE-Step au registre (T6) · P5 direction d'interprétation, balises Eleven v3 (T7).

**Lot 2 — différenciant** : D1 ducking dès la génération (T8) · D2 VFX derrière un sujet détouré (T9, T10) · D3 recherche par description et similarité — mesure, table de décision, service local optionnel, tiroir (T11, T12, T13) · D4 voix par personnage bout en bout (T14, T15).

**Écarté** (une ligne chacun, section `## Écarté` juste après le lot 2) : E1, E2, E3. Dernière section, dernière tâche : `## Campagne de mutations` (T16). T1 est le socle (outil de rafraîchissement des couches, clés de prix, helper de ducking partagé).

**Ce que le code fait déjà, relu ligne à ligne** : `sfx_service.py` (génération SFX, vocabulaire FX `_FX_ORDER`, `parse_ducking`, `fnum`, audition, ebur128) ; `music_service.py` (`MUSIC_MODELS` 4 entrées, `_payload`, `_audio_url`, `generate_music`) ; `montage_service.py:761` `_build_montage_command` (effets V1 lignes 896-910, ducking lignes 1136-1150 `sidechaincompress`) ; `effects_preview.py:303` `source_still`, `:334` `render_preview` ; `ffmpeg_service.py:70` `FFmpegMerger.merge` (musique mixée sans ducking) ; `routes.py` : `/audio` 2161, `/audio/upload` 2173, `/audio/meta` 2199, `/audio/sfx` 2209, `/music-models` 2260, `/audio/music` 2269, `/audio/{filename}` 2362, `/audio/voiceover` 2405, `/voices` 2491, `/effects/catalog` 7880, `/effects/preview` 7887, bible 5109-5188, `suggest-voice` 5628, `_voice_cast` 6847, `_generate_scene_vo` 6886, `_ALLOWED_ENV_KEYS` 3501 ; `library_index.SOURCES` (dict fermé) ; `storage.BIBLE_ENTITIES_COLUMNS` (auto-ALTER) ; `frontend/atelier/atelier.js` (page autonome : carte entité lignes 247-253, câblage 306-311, carte plan 561-596, câblage 628-634).

---

## Coût de patch

**La chaîne, mesurée le 03/09** : `frontend/dist/assets/index-BEOJX8L5.js` porte 8 marqueurs (SONVFX, SFXSTUDIO, VFXRACK, SUBS × BEGIN/END, un de chaque) et QUATRE `.bak_*` : `dzrailmotion` (28/08 15:47) → `version` (15:50) → `dznodecat` (17:33) → **`seedance25` (18:14, queue)**. Les `.bak_sonvfx`, `.bak_sfxstudio`, `.bak_vfxrack`, `.bak_subs` n'existent PAS dans l'arbre.

**Conséquence, et c'est le piège de ce plan** : `patch_bundle_sfxstudio.py` / `patch_bundle_sonvfx.py` CRÉENT un `.bak_<tag>` frais s'il manque (pollution de la queue de chaîne) ; `patch_bundle_vfxrack.py` fait pire — il crée `.bak_vfxrack` depuis le bundle courant puis abandonne sur `anchor count=0` (V3 déjà appliqué) en laissant ce faux maillon derrière lui. **Aucun de ces trois patchers ne se relance tel quel.** T1 écrit `scripts/refresh_layer.py` : remplacement du SEUL bloc entre marqueurs, CRLF aligné, zéro `.bak` touché, puis (couche `sonvfx` uniquement) rejeu des couples in-bloc de vfxrack/subs par `reapply_inblock_patches.py --no-refresh`.

| Tâche | Surface | Coût |
|---|---|---|
| T2 P1, T3 P2, T6 P4 (registre), T7 P5 (route), T8 D1 (backend), T9 D2a, T11 D3a, T12 D3b (+ `tools/clapbox/`, hors application), T14-T15 D4 (backend), T16 mutations | backend + bancs | **nul** (aucun patch) |
| T4 P3, T13 D3c | `frontend/patches/sfxstudio.js` + `dist/shared/sfxstudio.css` | **faible** : `refresh_layer.py --layer sfxstudio` |
| T10 D2b | `frontend/patches/vfxrack.js` + `vfxrack.css` | **faible** : `refresh_layer.py --layer vfxrack` |
| T6 P4 (éditeur), T7 P5 (carte voix), T8 D1 (carte mix), T10 D2b (écouteur `dz-matte`, payload) | `frontend/patches/son-vfx-montage.js` | **moyen** : `refresh_layer.py --layer sonvfx` rejoue les couples in-bloc ; interdiction de toucher les lignes-ancres de vfxrack (`A_DRAGOK`, `A_DROP`, `A_MIME`, `A_PICKER`, `A_STACKDEF`, `A_INSPECTOR`, `A_PAYLOAD` = la ligne `effects:c.effects&&c.effects.length?c.effects:void 0,`) — `reapply_inblock_patches.py --check` avant/après doit compter les MÊMES couples |
| T5 P3b (puce Audio de la Bibliothèque) | bundle natif | **élevé** : patcher NEUF `patch_bundle_libsons.py`, tag `libsons`, `.bak_libsons`, EN QUEUE après `seedance25`, ancre unique (mesurée : 1 occurrence), `repatch_all.py --from libsons` ne rejoue que lui |
| T14 D4 (carte entité), T15 D4 (carte plan) | `frontend/atelier/atelier.js` (page autonome) | **faible** : édition directe, aucun patch |
| T8 D1 (Quick) | `ffmpeg_service.py` seulement | **nul** : la Quick n'a rien à afficher, le mix change côté rendu |

Vérification d'un rafraîchissement, toujours par inventaire (README « Patching the compiled UI ») : `grep -o "/\*__DZ_[A-Z]*__\*/" frontend/dist/assets/index-BEOJX8L5.js | sort | uniq -c` → 8 lignes à `1`.

---

## Références vérifiées

Seules les références VÉRIFIÉES servent d'argument. Relues par `WebFetch` le **03/09/2026** dans la session d'écriture de ce plan (en plus de celles de R4) :

| Référence | Ce qui est figé | Prix |
|---|---|---|
| fal `fal-ai/demucs` (page `/api`) | `audio_url` ; `model` ∈ {htdemucs, htdemucs_ft, **htdemucs_6s** (défaut), hdemucs_mmi, mdx, mdx_extra, mdx_q, mdx_extra_q} ; `stems` liste ; `shifts`=1 ; `overlap`=0.25 ; `output_format` ∈ {wav, **mp3**} ; sortie = un champ par stem `vocals/drums/bass/other/guitar/piano` → `{url, content_type, file_name, file_size}` | page modèle : « $0.0007 per second » |
| fal `fal-ai/birefnet/v2/video` | `video_url` ; `model` ∈ {"General Use (Light)" (défaut), "General Use (Light 2K)", "General Use (Heavy)", "Matting", "Portrait", "General Use (Dynamic)"} ; `operating_resolution` ∈ {1024x1024, 2048x2048, 2304x2304} ; `refine_foreground`=true ; `video_output_type` ∈ {"X264 (.mp4)", "VP9 (.webm)", **"PRORES4444 (.mov)"**, "GIF (.gif)"} ; `output_mask` ; sortie `video`, `mask_video` | page modèle : « $0 per compute second » — **chiffre non crédible**, à mesurer au premier tir (T9) |
| fal `fal-ai/ace-step` | `tags` (requis, genres séparés par virgules), `lyrics` (`[verse]`/`[chorus]`/`[bridge]`, `[inst]` = instrumental), `duration`=60, `number_of_steps`=27, `seed`, `scheduler`, `guidance_scale`=15 ; sortie `audio.url`, `seed` | « $0.0002 per second of generated audio » |
| fal `fal-ai/minimax-music/v2` (Music 2.0) | `prompt` 10-300 car. (requis), `lyrics_prompt` 10-3000 (requis) ; sortie `audio.url` | R4 : 0,03 $/génération (page `/api` sans prix) |
| fal `fal-ai/minimax-music/v2.6` (déjà au registre) | `prompt` 10-2000, `lyrics` ≤ 3500 (`[Intro]`, `[Verse]`, `[Chorus]`), `lyrics_optimizer`, `is_instrumental` | 0,14 $ (registre) |
| **MiniMax Music 3** (R4 : « jusqu'à 5 min ») | `fal-ai/minimax-music/v3` → **404**, `fal-ai/minimax/music-03` → 404, recherche « minimax music » sans carte musique | **identifiant NON retrouvé** : entre au registre seulement si T6 étape 1 le retrouve, sinon consigné |
| ElevenLabs `POST /v1/audio-isolation` | multipart, champ `audio`, `file_format` optionnel (`pcm_s16le_16` \| `other`) ; réponse = audio | R4 : 1 000 caractères/minute, ≤ 500 Mo, ≤ 1 h |
| ElevenLabs `POST /v1/voices/add` (clone instantané) | multipart `name`, `files`, `description`, `labels`, `remove_background_noise` ; réponse `voice_id`, `requires_verification` | à la voix, plan du compte |
| Eleven v3, balises (docs prompting) | `[laughs]` `[laughs harder]` `[starts laughing]` `[wheezing]` `[whispers]` `[sighs]` `[exhales]` `[sarcastic]` `[curious]` `[excited]` `[crying]` `[snorts]` `[mischievously]` ; sons `[gunshot]` `[applause]` `[clapping]` `[explosion]` `[swallows]` `[gulps]` ; expérimentaux `[strong X accent]` `[sings]` `[woo]` ; stabilité Creative/Natural/Robust (= 0/0.5/1, déjà snappé par `clamp_voice_settings`) ; pas de SSML `<break>` en v3. `[pause]` : cité par R4, ABSENT de la page relue → gardé, marqué expérimental | — |
| CLAP `laion/clap-htsat-unfused` (`huggingface.co/api/models/...`) | `pipeline_tag: feature-extraction`, `library_name: transformers`, tags `endpoints_compatible` ; **aucun fournisseur d'inférence serverless listé** ; fal : aucun endpoint CLAP | endpoint dédié HF = facturé à l'heure, à déployer soi-même |

Epidemic, Artlist, Splice, EmberGen, Adobe Podcast, Audition, Reaper : de mémoire, non vérifiés — pas un argument.

**Règle pour chaque tâche qui tire un endpoint fal** : l'étape 1 relit la page `/api` par `WebFetch` (commande donnée dans la tâche), compare aux paramètres figés dans le registre, et corrige le registre AVANT d'écrire le service. Un écart = une ligne dans le commit.

---

## Lot 1 — parité

### Task 1 : socle — `refresh_layer.py`, clés de prix, helper de ducking partagé

**Files :**
- Create : `scripts/refresh_layer.py`
- Modify : `backend/app/services/pricing.py` (DEFAULTS + `estimate`), `backend/app/services/sfx_service.py` (fin de fichier), `backend/app/services/montage_service.py:1136-1150`, `backend/app/services/library_index.py:24-38`
- Test : `backend/tests/test_son_vfx_socle.py`

- [ ] **Étape 1 : mesurer la chaîne avant tout**

Run : `python scripts/repatch_all.py --list`
Expected (ordre par mtime, dernier = queue) :
```
dzrailmotion     OK (bak ... o)
version          OK (bak ... o)
dznodecat        OK (bak ... o)
seedance25       OK (bak ... o)
```
Si un cinquième tag apparaît, ce plan est à relire : la queue a bougé.

- [ ] **Étape 2 : banc rouge**

```python
# backend/tests/test_son_vfx_socle.py
# -*- coding: utf-8 -*-
"""Socle Son & VFX : helper de ducking octet pour octet, clés de prix, source
`sonvfx` de la Bibliothèque, refresh_layer en contrôle à sec.
Run: python tests/test_son_vfx_socle.py (depuis backend/)"""
import os, subprocess, sys, tempfile
os.environ.setdefault("DEEPOTUS_DATA_DIR", tempfile.mkdtemp(prefix="dzsvx_"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

from app.services import sfx_service as S, pricing as P, library_index as LI
check("ducking bool = ligne historique",
      S.ducking_filter(True) == "sidechaincompress=threshold=0.05:ratio=6:attack=50:release=400")
d = S.parse_ducking({"ratio": 8, "attack_ms": 20, "release_ms": 300, "threshold": 0.1})
check("ducking dict = mêmes champs, même ordre",
      S.ducking_filter(d) == "sidechaincompress=threshold=0.1:ratio=8:attack=20:release=300")
p = P.load()
for k, v in (("demucs_usd_per_s", 0.0007), ("ace_step_usd_per_s", 0.0002),
             ("minimax_music_20_usd", 0.03), ("birefnet_video_usd_per_s", 0.0),
             ("elevenlabs_isolation_chars_per_min", 1000.0)):
    check(f"clé de prix {k}", p.get(k) == v, str(p.get(k)))
e = P.estimate({"kind": "stems", "duration_s": 100})
check("estimation stems = 100 s × 0,0007", abs(e["total_usd"] - 0.07) < 1e-6, str(e))
e = P.estimate({"kind": "isolate", "duration_s": 90})
check("estimation isolation = 1,5 min × 1000 car. × tarif",
      abs(e["total_usd"] - 1500 * p["elevenlabs_usd_per_char"]) < 1e-9, str(e))
e = P.estimate({"kind": "matte", "duration_s": 10})
check("estimation matte = 0 $ MAIS ligne présente et libellée « à mesurer »",
      e["total_usd"] == 0.0 and "mesurer" in e["breakdown"][0]["label"], str(e))
check("source sonvfx connue de la Bibliothèque", LI.SOURCES.get("sonvfx") == "Son & VFX")
r = subprocess.run([sys.executable, "../scripts/refresh_layer.py", "--layer", "sfxstudio", "--check"],
                   capture_output=True, text=True, timeout=60)
check("refresh_layer --check sfxstudio : 1 bloc, 0 .bak touché",
      r.returncode == 0 and "bloc: 1" in r.stdout and "bak: 0" in r.stdout, r.stdout[-300:] + r.stderr[-300:])
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```

Run : `python tests/test_son_vfx_socle.py`
Expected : `AttributeError: module 'app.services.sfx_service' has no attribute 'ducking_filter'`

- [ ] **Étape 3 : helper de ducking dans `sfx_service.py` (fin de fichier) et refactor du Montage, octet pour octet**

```python
# sfx_service.py — après parse_ducking
def ducking_filter(ducking) -> str:
    """sidechaincompress=… — LA chaîne du Montage, partagée avec la Quick
    (FFmpegMerger) et l'aperçu /audio/duck. Bool = ligne historique en dur ;
    dict (parse_ducking) = paramètres. Octet pour octet : test_son_vfx_socle."""
    if isinstance(ducking, dict):
        return (f"sidechaincompress=threshold={_g(ducking['threshold'])}:"
                f"ratio={_g(ducking['ratio'])}:attack={_g(ducking['attack'])}:"
                f"release={_g(ducking['release'])}")
    return "sidechaincompress=threshold=0.05:ratio=6:attack=50:release=400"
```
Dans `montage_service.py`, remplacer les lignes 1138-1150 (le `if isinstance(ducking, dict): … else: …`) par :
```python
            parts.append(f"{music_lbl}[vsc]{sfx_service.ducking_filter(ducking)}[mduck]")
```
Preuve de non-régression : `python tests/test_montage_effects.py` puis `python -m pytest tests/test_effects_timing.py -q` restent verts, et l'assertion « octet pour octet » du banc.

- [ ] **Étape 4 : clés de prix et kinds d'estimation**

Dans `pricing.DEFAULTS`, après `"stt_usd_per_min"` :
```python
    # Son & VFX (plan 03/09/2026). Demucs : page fal relue le 03/09,
    # « $0.0007 per second ». ACE-Step : « $0.0002 per second of generated
    # audio ». MiniMax Music 2.0 : 0,03 $ la génération (R4). BiRefNet vidéo :
    # la page affiche « $0 per compute second » — chiffre non crédible, gardé
    # à 0 et LIBELLÉ « à mesurer » tant qu'un premier tir n'a pas été lu sur
    # le tableau de bord fal. Isolation ElevenLabs : 1 000 caractères/min.
    "demucs_usd_per_s": 0.0007,
    "ace_step_usd_per_s": 0.0002,
    "minimax_music_20_usd": 0.03,
    "birefnet_video_usd_per_s": 0.0,
    "elevenlabs_isolation_chars_per_min": 1000.0,
```
Dans `estimate`, avant `elif kind == "llm":` :
```python
    elif kind == "stems":
        dur = float(op.get("duration_s", 0))
        lines.append(_line("fal", "Séparation en stems (Demucs)", dur, "s",
                           dur * float(p.get("demucs_usd_per_s", DEFAULTS["demucs_usd_per_s"]))))
    elif kind == "isolate":
        mins = float(op.get("duration_s", 0)) / 60.0
        chars = mins * float(p.get("elevenlabs_isolation_chars_per_min", 1000.0))
        lines.append(_line("elevenlabs", "Isolation de voix", chars, "chars",
                           chars * elevenlabs_rate(None, p)))
    elif kind == "matte":
        dur = float(op.get("duration_s", 0))
        rate = float(p.get("birefnet_video_usd_per_s", 0.0))
        lines.append(_line("fal", "Détourage vidéo (BiRefNet) — prix à mesurer au premier tir"
                           if rate == 0.0 else "Détourage vidéo (BiRefNet)", dur, "s", dur * rate))
    elif kind == "music":
        model = str(op.get("model") or "")
        dur = float(op.get("duration_s", 0))
        per_s = {"ace-step": p.get("ace_step_usd_per_s", 0.0002)}
        flat = {"minimax-music-20": p.get("minimax_music_20_usd", 0.03)}
        if model in per_s:
            lines.append(_line("fal", f"Musique ({model})", dur, "s", dur * float(per_s[model])))
        else:
            from app.services.music_service import MUSIC_MODELS
            usd = float(flat.get(model, (MUSIC_MODELS.get(model) or {}).get("usd", 0.0)))
            lines.append(_line("fal", f"Musique ({model})", 1, "gen", usd))
```
Dans `library_index.SOURCES`, après `"import_url"` : `"sonvfx": "Son & VFX",`.

- [ ] **Étape 5 : `scripts/refresh_layer.py`**

```python
# -*- coding: utf-8 -*-
# scripts/refresh_layer.py
"""Rafraîchit UNE couche injectée du bundle, en place, sans toucher à la chaîne.

Pourquoi : les patchers sfxstudio/sonvfx CRÉENT un .bak_<tag> s'il manque, et
vfxrack en crée un puis abandonne (ses ancres V3..V11 sont déjà consommées).
Mesuré le 03/09/2026 : quatre .bak seulement dans l'arbre, aucun des quatre
blocs injectés n'a le sien. Cet outil ne lit et n'écrit QUE le bloc entre
marqueurs, CRLF aligné sur le bundle, et n'ouvre jamais un .bak.

    python scripts/refresh_layer.py --layer sfxstudio|vfxrack|sonvfx [--check]

Couche sonvfx : après le remplacement, rejeu des couples in-bloc de vfxrack et
subs par reapply_inblock_patches.py --no-refresh (son contrat : bloc PROPRE).
"""
import pathlib, subprocess, sys

REPO = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = REPO / "frontend/dist/assets/index-BEOJX8L5.js"
LAYERS = {"sfxstudio": ("SFXSTUDIO", "sfxstudio.js"),
          "vfxrack": ("VFXRACK", "vfxrack.js"),
          "sonvfx": ("SONVFX", "son-vfx-montage.js")}

def main():
    args = sys.argv[1:]
    layer = args[args.index("--layer") + 1]
    tag, src_name = LAYERS[layer]
    begin, end = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
    raw = BUNDLE.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig" if bom else "utf-8")
    crlf = "\r\n" in text
    n_b, n_e = text.count(begin), text.count(end)
    baks = sorted(BUNDLE.parent.glob(BUNDLE.name + ".bak_*"))
    before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in baks}
    if n_b != 1 or n_e != 1:
        raise SystemExit(f"[{layer}] marqueurs: begin={n_b} end={n_e} (attendu 1/1). Rien écrit.")
    if "--check" in args:
        print(f"[{layer}] bloc: 1 · bak: 0 touché · crlf={crlf}")
        return
    src = (REPO / "frontend/patches" / src_name).read_bytes().decode("utf-8-sig")
    src = src.replace("\r\n", "\n")
    src = src.replace("\n", "\r\n") if crlf else src
    head, rest = text.split(begin, 1)
    _old, tail = rest.split(end, 1)
    nl = "\r\n" if crlf else "\n"
    text = head + begin + nl + src + nl + end + tail
    out = text.encode("utf-8")
    BUNDLE.write_bytes((b"\xef\xbb\xbf" + out) if bom else out)
    after = {p.name: (p.stat().st_size, p.stat().st_mtime_ns)
             for p in BUNDLE.parent.glob(BUNDLE.name + ".bak_*")}
    assert before == after, "un .bak a bougé — interdit"
    print(f"[{layer}] bloc rafraîchi ({len(src)} car.) · bak: 0 touché")
    if layer == "sonvfx":
        rc = subprocess.run([sys.executable, str(REPO / "scripts/reapply_inblock_patches.py"),
                             "--no-refresh"]).returncode
        if rc != 0:
            raise SystemExit(f"[sonvfx] rejeu des couples in-bloc échoué (rc={rc})")

if __name__ == "__main__":
    main()
```

- [ ] **Étape 6 : vert, puis commit**

Run : `python tests/test_son_vfx_socle.py` → `=== 11 passed, 0 failed ===`. Run : `python tests/test_montage_effects.py` → `MONTAGE EFFECTS TEST: PASS`.
```
git add scripts/refresh_layer.py backend/app/services/pricing.py backend/app/services/sfx_service.py backend/app/services/montage_service.py backend/app/services/library_index.py backend/tests/test_son_vfx_socle.py
git commit -m 'son-vfx : socle - refresh_layer, cles de prix, ducking partage' -m 'Le helper ducking_filter rend la chaîne du Montage octet pour octet ; refresh_layer ne touche aucun .bak (mesuré : quatre dans l arbre, aucun des blocs injectés n a le sien).' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 2 : P1 — stems par Demucs (fal)

**Files :**
- Create : `backend/app/services/stems_service.py`
- Modify : `backend/app/api/routes.py` (après `/audio/music`, ligne 2290)
- Test : `backend/tests/test_stems_service.py`

- [ ] **Étape 1 : relire l'endpoint**

`WebFetch url=https://fal.ai/models/fal-ai/demucs/api prompt="List input params, stems output field names, output_format values"` — attendu : `audio_url`, `model` défaut `htdemucs_6s`, `stems`, `output_format` mp3 ; sorties `vocals/drums/bass/other/guitar/piano`. Un écart avec `STEMS_MODELS` ci-dessous → corriger le registre d'abord.

- [ ] **Étape 2 : banc rouge**

```python
# backend/tests/test_stems_service.py
# -*- coding: utf-8 -*-
"""P1 — stems Demucs : registre, seams fal stubbés, fichiers ÉCRITS (ffprobe),
sidecar de lignée, provenance sonvfx, refus sans clé.
Run: python tests/test_stems_service.py (depuis backend/)"""
import asyncio, json, os, pathlib, shutil, subprocess, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzstems_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
if not shutil.which("ffmpeg"):
    print("SKIP: ffmpeg introuvable"); sys.exit(0)
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
def probe(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout or 0)
from app.config import settings
from app.services import stems_service as ST, sfx_service as S
from app.services.storage import init_db, LibraryAsset, async_session_factory
asyncio.run(init_db())
audio = settings.images_path.parent / "audio"; audio.mkdir(exist_ok=True)
src = audio / "theme_abysses.mp3"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=3",
                "-c:a", "libmp3lame", str(src)], check=True)
fake = pathlib.Path(_tmp, "fake_stem.mp3")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                "-c:a", "libmp3lame", str(fake)], check=True)
CALLS = []
async def _sub(endpoint, arguments):
    CALLS.append((endpoint, arguments))
    return {s: {"url": f"http://fal.test/{s}.mp3", "content_type": "audio/mpeg"}
            for s in arguments["stems"] if s != "piano"}     # piano manquant : dit, pas fatal
async def _up(path): return "http://fal.test/in.mp3"
async def _dl(url, dest): shutil.copy2(fake, dest)
ST._fal_subscribe, ST._upload, ST._download = _sub, _up, _dl

check("registre : htdemucs_6s a 6 stems", ST.STEMS_MODELS["htdemucs_6s"]["stems"][-1] == "piano")
settings.FAL_KEY = ""
try:
    asyncio.run(ST.separate("theme_abysses.mp3")); check("sans clé : refus", False)
except S.SfxError as e: check("sans clé : 400 nommant fal", e.status == 400 and "fal" in e.message)
settings.FAL_KEY = "test-key"
r = asyncio.run(ST.separate("theme_abysses.mp3", stems=["vocals", "drums", "piano"]))
check("endpoint et format figés", CALLS[0][0] == "fal-ai/demucs" and CALLS[0][1]["output_format"] == "mp3"
      and CALLS[0][1]["model"] == "htdemucs_6s", str(CALLS))
names = [it["filename"] for it in r["items"]]
check("deux fichiers écrits, nommés par stem", names == ["stem_theme_abysses_vocals.mp3", "stem_theme_abysses_drums.mp3"], str(names))
check("durée sondée ≈ 3 s", all(abs(probe(audio / n) - 3.0) < 0.3 for n in names))
meta = S.load_meta()
check("sidecar : kind stem + parent", meta[names[0]]["kind"] == "stem" and meta[names[0]]["parent"] == "theme_abysses.mp3", str(meta.get(names[0])))
check("stem manquant DIT", r["missing"] == ["piano"], str(r))
check("coût = durée × 0,0007", abs(r["usd"] - 3.0 * 0.0007) < 1e-4, str(r["usd"]))
async def _prov():
    async with async_session_factory() as s:
        row = await s.get(LibraryAsset, names[0]); return row and (row.source, row.kind)
check("provenance sonvfx/audio", asyncio.run(_prov()) == ("sonvfx", "audio"))
try:
    asyncio.run(ST.separate("theme_abysses.mp3", stems=["kazoo"])); check("stem inconnu refusé", False)
except S.SfxError as e: check("stem inconnu refusé (400)", e.status == 400)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```
Run : `python tests/test_stems_service.py` → `ModuleNotFoundError: No module named 'app.services.stems_service'`

- [ ] **Étape 3 : le service**

```python
# backend/app/services/stems_service.py
# -*- coding: utf-8 -*-
"""P1 — séparation en stems par Demucs (fal-ai/demucs), page /api relue le
03/09/2026. Chaque stem devient un fichier ordinaire du dossier audio de la
Bibliothèque (sidecar kind « stem », parent = la piste d'origine) : le tiroir
Sons et le Montage les voient sans une ligne de plus. Les appels réseau
passent par trois seams de module que le banc remplace."""
from __future__ import annotations
import asyncio, os
from datetime import datetime
from pathlib import Path
import httpx
from loguru import logger
from app.config import settings, SSL_VERIFY
from app.services import sfx_service, library_index as LI
from app.services.sfx_service import SfxError

ENDPOINT = "fal-ai/demucs"
STEMS_MODELS = {
    "htdemucs_6s": {"label": "Demucs 6 stems", "stems": ("vocals", "drums", "bass", "other", "guitar", "piano")},
    "htdemucs_ft": {"label": "Demucs 4 stems (affiné)", "stems": ("vocals", "drums", "bass", "other")},
}
DEFAULT_MODEL = "htdemucs_6s"

async def _upload(path: Path) -> str:              # seam
    import fal_client
    return await fal_client.upload_file_async(str(path))

async def _fal_subscribe(endpoint: str, arguments: dict) -> dict:   # seam
    import fal_client
    return await fal_client.subscribe_async(endpoint, arguments=arguments, with_logs=False)

async def _download(url: str, dest: Path) -> None:  # seam
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=300) as c:
        r = await c.get(url); r.raise_for_status()
        tmp = dest.with_name(dest.name + ".part"); tmp.write_bytes(r.content); os.replace(tmp, dest)

def _unique(folder: Path, name: str) -> Path:
    p = folder / name
    i = 2
    while p.exists():
        p = folder / f"{Path(name).stem}_{i}{Path(name).suffix}"; i += 1
    return p

async def separate(filename: str, stems: list[str] | None = None, model: str = DEFAULT_MODEL) -> dict:
    if not (settings.FAL_KEY or "").strip():
        raise SfxError(400, "fal.ai: aucune clé configurée (Réglages → clés API) — les stems passent par fal.")
    m = STEMS_MODELS.get(model)
    if m is None:
        raise SfxError(400, f"modèle de stems inconnu : {model!r} ({', '.join(STEMS_MODELS)})")
    want = [str(s).lower() for s in (stems or m["stems"])]
    bad = [s for s in want if s not in m["stems"]]
    if bad:
        raise SfxError(400, f"stems inconnus pour {m['label']} : {', '.join(bad)}")
    folder = sfx_service._audio_dir()
    src = folder / Path(filename).name
    if not src.is_file():
        raise SfxError(404, f"audio introuvable : {filename}")
    loop = asyncio.get_running_loop()
    dur = await loop.run_in_executor(None, sfx_service._probe_duration, src)
    url = await _upload(src)
    args = {"audio_url": url, "model": model, "stems": want, "output_format": "mp3"}
    try:
        result = await _fal_subscribe(ENDPOINT, args)
    except Exception as e:
        raise SfxError(502, f"fal.ai: {str(e)[:300]}") from e
    items, missing = [], []
    for s in want:
        f = (result or {}).get(s)
        u = f.get("url") if isinstance(f, dict) else (f if isinstance(f, str) else None)
        if not u:
            missing.append(s); continue
        dest = _unique(folder, f"stem_{src.stem[:40]}_{s}.mp3")
        await _download(u, dest)
        sdur = await loop.run_in_executor(None, sfx_service._probe_duration, dest)
        sfx_service.record_meta(dest.name, {"kind": "stem", "stem": s, "parent": src.name, "model": model,
                                            "created": datetime.now().isoformat(timespec="seconds")})
        items.append({"filename": dest.name, "url": f"/api/audio/{dest.name}", "name": dest.stem,
                      "stem": s, "dur": round(sdur, 2), "size_kb": dest.stat().st_size // 1024})
    await LI.noter([it["filename"] for it in items], "sonvfx", kind="audio")
    from app.services import pricing
    usd = round(dur * float(pricing.load().get("demucs_usd_per_s", 0.0007)), 4)
    logger.info(f"stems: {src.name} → {len(items)} stems ({missing or 'complet'}) ~{usd} $")
    return {"ok": True, "parent": src.name, "items": items, "missing": missing, "usd": usd, "model": model}
```

- [ ] **Étape 4 : la route (après `/audio/music`)**

```python
@router.get("/audio/stems-models")
async def stems_models():
    from app.services import stems_service as ST
    return {"enabled": bool(settings.FAL_KEY), "default": ST.DEFAULT_MODEL,
            "models": [{"id": k, "label": v["label"], "stems": list(v["stems"])} for k, v in ST.STEMS_MODELS.items()],
            "usd_per_s": pricing_load().get("demucs_usd_per_s", 0.0007)}

@router.post("/audio/stems")
async def audio_stems(request: Request):
    """P1 — Body {filename, stems?: [..], model?}. Chaque stem rejoint la
    Bibliothèque (kind « stem », parent) → {ok, parent, items, missing, usd}."""
    try: payload = await request.json()
    except Exception: payload = {}
    from app.services import stems_service as ST
    fn = str(payload.get("filename") or "").strip()
    if not fn: raise HTTPException(400, "filename requis.")
    try:
        return await ST.separate(fn, stems=payload.get("stems") or None,
                                 model=str(payload.get("model") or ST.DEFAULT_MODEL))
    except ST.SfxError as e:
        raise HTTPException(e.status, e.message)
```
(`pricing_load` = `from app.services.pricing import load as pricing_load` en tête de routes.py, à côté des imports existants.)

- [ ] **Étape 5 : vert, commit**

Run : `python tests/test_stems_service.py` → `=== 10 passed, 0 failed ===`
```
git add backend/app/services/stems_service.py backend/app/api/routes.py backend/tests/test_stems_service.py
git commit -m 'son-vfx P1 : stems Demucs via fal, chaque stem entre en Bibliotheque avec sa lignee' -m 'Registre STEMS_MODELS figé sur la page /api du 03/09 ; un stem absent de la réponse est dit, jamais fatal ; coût = durée × 0,0007 $.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 3 : P2 — isolation de voix ElevenLabs + chaîne « améliorer » en un clic

**Files :**
- Create : `backend/app/services/voice_clean.py`
- Modify : `backend/app/api/routes.py` (après `/audio/stems`)
- Test : `backend/tests/test_voice_clean.py`

- [ ] **Étape 1 : banc rouge**

```python
# backend/tests/test_voice_clean.py
# -*- coding: utf-8 -*-
"""P2 — chaîne « améliorer » (locale, gratuite) MESURÉE par ebur128, et
isolation ElevenLabs (seam HTTP stubbé) : fichiers écrits, sidecar, coût.
Run: python tests/test_voice_clean.py (depuis backend/)"""
import os, pathlib, re, shutil, subprocess, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzclean_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
if not shutil.which("ffmpeg"): print("SKIP: ffmpeg introuvable"); sys.exit(0)
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
def lufs(p):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(p), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])
from app.config import settings
from app.services import voice_clean as VC, sfx_service as S
settings.ELEVENLABS_API_KEY = "test-11l"
audio = settings.images_path.parent / "audio"; audio.mkdir(exist_ok=True)
src = audio / "prise_brute.mp3"   # voix (sinus) + souffle, à −30 dB : loin de −16 LUFS
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=200:duration=4",
                "-f", "lavfi", "-i", "anoisesrc=amplitude=0.02:duration=4", "-filter_complex",
                "[0:a][1:a]amix=inputs=2,volume=0.03[o]", "-map", "[o]", "-c:a", "libmp3lame", str(src)], check=True)
cmd = VC.enhance_command(src, audio / "x.mp3")
af = cmd[cmd.index("-af") + 1]
check("chaîne dans l'ordre de _FX_ORDER : equalizer < afftdn < acompressor < loudnorm",
      af.index("equalizer") < af.index("afftdn") < af.index("acompressor") < af.index("loudnorm"), af)
r = VC.enhance("prise_brute.mp3")
out = audio / r["filename"]
check("fichier clean_ écrit", out.is_file() and r["filename"] == "clean_prise_brute.mp3", str(r))
li = lufs(out)
check("MESURÉ : sortie normalisée à −16 ± 1,5 LUFS", -17.5 <= li <= -14.5, f"{li} LUFS (entrée {lufs(src)})")
m = S.load_meta()[r["filename"]]
check("sidecar : voix, parent, chaîne nommée", m["kind"] == "voix" and m["parent"] == "prise_brute.mp3" and m["chain"] == "ameliorer")
check("gratuit, et dit", r["usd"] == 0.0)
POSTS = []
def _fake_post(key, name, data):
    POSTS.append((key, name, len(data))); return src.read_bytes()
VC._post_isolation = _fake_post
r2 = VC.isolate("prise_brute.mp3")
check("isolation : iso_ écrit, meta voix + parent", (audio / r2["filename"]).is_file() and r2["filename"] == "iso_prise_brute.mp3"
      and S.load_meta()[r2["filename"]]["parent"] == "prise_brute.mp3", str(r2))
check("un seul POST, avec la clé", POSTS == [("test-11l", "prise_brute.mp3", src.stat().st_size)], str(POSTS))
check("coût = 4 s / 60 × 1000 car. × tarif", abs(r2["usd"] - (4 / 60) * 1000 * 0.00024) < 1e-4, str(r2["usd"]))
settings.ELEVENLABS_API_KEY = ""
try: VC.isolate("prise_brute.mp3"); check("sans clé : refus", False)
except S.SfxError as e: check("sans clé : 400 ElevenLabs", e.status == 400 and "ElevenLabs" in e.message)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```
Run : `python tests/test_voice_clean.py` → `ModuleNotFoundError: No module named 'app.services.voice_clean'`

- [ ] **Étape 2 : le service**

```python
# backend/app/services/voice_clean.py
# -*- coding: utf-8 -*-
"""P2 — nettoyage de voix. Deux voies, deux prix :
  enhance()  chaîne locale ffmpeg sur le vocabulaire FX de sfx_service —
             0 $, hors ligne. ATTENTION : `fx_chain` RÉORDONNE la liste selon
             `_FX_ORDER`, donc la sortie est eq3 → débruitage → compresseur →
             loudnorm, et non l'ordre de saisie du bac P2 (mesuré le 03/09) ;
  isolate()  ElevenLabs POST /v1/audio-isolation (multipart `audio`), relu le
             03/09/2026 — facturé 1 000 caractères par minute (R4).
Les deux écrivent dans le dossier audio de la Bibliothèque avec parent."""
from __future__ import annotations
import os, subprocess
from datetime import datetime
from pathlib import Path
import httpx
from app.config import settings, SSL_VERIFY
from app.services import sfx_service
from app.services.sfx_service import SfxError

ISOLATION_URL = "https://api.elevenlabs.io/v1/audio-isolation"
MAX_ISOLATION_BYTES = 500 * 1024 * 1024
# Préréglage « améliorer » : mêmes types/bornes que le rack (sanitize_fx clampe).
# L'ordre écrit ici n'est PAS l'ordre rendu : fx_chain trie par _FX_ORDER.
ENHANCE_CHAIN = [
    {"type": "denoise", "params": {"amount": 18}},
    {"type": "eq3", "params": {"bass_db": -2, "mid_db": 1, "treble_db": 2}},
    {"type": "compressor", "params": {"threshold_db": -18, "ratio": 3, "attack_ms": 15, "release_ms": 180}},
    {"type": "normalize", "params": {"target_lufs": -16}},
]

def _src(filename: str) -> Path:
    p = sfx_service._audio_dir() / Path(filename).name
    if not p.is_file():
        raise SfxError(404, f"audio introuvable : {filename}")
    return p

def _dest(prefix: str, src: Path) -> Path:
    folder = sfx_service._audio_dir()
    p = folder / f"{prefix}{src.stem[:48]}.mp3"
    i = 2
    while p.exists():
        p = folder / f"{prefix}{src.stem[:48]}_{i}.mp3"; i += 1
    return p

def enhance_command(src: Path, out: Path) -> list[str]:
    af = sfx_service.fx_chain(sfx_service.sanitize_fx(ENHANCE_CHAIN, "ameliorer"))
    return ["ffmpeg", "-y", "-hide_banner", "-i", str(src), "-vn", "-af", af,
            "-ar", "44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "192k", "-f", "mp3", str(out)]

def _finish(src: Path, out: Path, extra: dict, usd: float) -> dict:
    dur = round(sfx_service._probe_duration(out), 2)
    sfx_service.record_meta(out.name, dict({"kind": "voix", "parent": src.name,
                                            "created": datetime.now().isoformat(timespec="seconds")}, **extra))
    from app.services import library_index as LI
    LI.noter_bg([out.name], "sonvfx", kind="audio")
    return {"ok": True, "filename": out.name, "url": f"/api/audio/{out.name}", "name": out.stem,
            "dur": dur, "size_kb": out.stat().st_size // 1024, "usd": usd, "parent": src.name}

def enhance(filename: str) -> dict:
    """Bloquant (ffmpeg) — à appeler via run_in_executor."""
    src = _src(filename)
    out = _dest("clean_", src)
    tmp = out.with_name(out.name + ".part")
    r = subprocess.run(enhance_command(src, tmp), capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise SfxError(502, f"améliorer : ffmpeg a échoué — {(r.stderr or '')[-300:]}")
    os.replace(tmp, out)
    return _finish(src, out, {"chain": "ameliorer"}, 0.0)

def _post_isolation(key: str, name: str, data: bytes) -> bytes:   # seam
    with httpx.Client(verify=SSL_VERIFY, timeout=600.0) as c:
        r = c.post(ISOLATION_URL, headers={"xi-api-key": key}, files={"audio": (name, data)})
    if r.status_code != 200:
        st = r.status_code if 400 <= r.status_code < 500 else 502
        raise SfxError(st, f"ElevenLabs: {sfx_service._eleven_detail(r)}")
    if not r.content:
        raise SfxError(502, "ElevenLabs: isolation sans audio en retour.")
    return r.content

def isolation_usd(duration_s: float) -> float:
    from app.services import pricing
    p = pricing.load()
    chars = duration_s / 60.0 * float(p.get("elevenlabs_isolation_chars_per_min", 1000.0))
    return round(chars * pricing.elevenlabs_rate(None, p), 4)

def isolate(filename: str) -> dict:
    """Bloquant (httpx sync) — à appeler via run_in_executor."""
    key = (settings.ELEVENLABS_API_KEY or "").strip()
    if not key:
        raise SfxError(400, "ElevenLabs: aucune clé API — ajoute-la dans Réglages → Clés pour isoler une voix.")
    src = _src(filename)
    if src.stat().st_size > MAX_ISOLATION_BYTES:
        raise SfxError(400, "ElevenLabs: fichier > 500 Mo, refusé par l'API.")
    dur = sfx_service._probe_duration(src)
    data = _post_isolation(key, src.name, src.read_bytes())
    out = _dest("iso_", src)
    tmp = out.with_name(out.name + ".part"); tmp.write_bytes(data); os.replace(tmp, out)
    return _finish(src, out, {"chain": "isolation"}, isolation_usd(dur))
```

- [ ] **Étape 3 : deux routes (après `/audio/stems`)**

```python
@router.post("/audio/enhance")
async def audio_enhance(request: Request):
    """P2 — chaîne « améliorer » locale, 0 $ : eq3 → débruitage → compresseur
    → −16 LUFS (ordre imposé par _FX_ORDER). Body {filename}."""
    payload = await request.json()
    from app.services import voice_clean as VC
    try:
        return await asyncio.get_running_loop().run_in_executor(
            None, lambda: VC.enhance(str(payload.get("filename") or "")))
    except VC.SfxError as e:
        raise HTTPException(e.status, e.message)

@router.post("/audio/isolate")
async def audio_isolate(request: Request):
    """P2 — isolation ElevenLabs. Body {filename}. Coût affiché AVANT par
    GET /api/cost/estimate {kind: isolate, duration_s}."""
    payload = await request.json()
    from app.services import voice_clean as VC
    try:
        return await asyncio.get_running_loop().run_in_executor(
            None, lambda: VC.isolate(str(payload.get("filename") or "")))
    except VC.SfxError as e:
        raise HTTPException(e.status, e.message)
```

- [ ] **Étape 4 : vert, commit**

Run : `python tests/test_voice_clean.py` → `=== 9 passed, 0 failed ===`
```
git add backend/app/services/voice_clean.py backend/app/api/routes.py backend/tests/test_voice_clean.py
git commit -m 'son-vfx P2 : isolation ElevenLabs et chaine ameliorer en un clic' -m 'La chaîne locale est mesurée par ebur128 (−16 LUFS ± 1,5), pas décrite ; l isolation passe par un seam HTTP et affiche son coût en caractères par minute. Corrigé au passage : fx_chain réordonne par _FX_ORDER, la chaîne rendue est eq3 avant le débruitage — le bac P2 l annonçait à l envers.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 4 : P3 — le tiroir Sons, vue de référence

**Files :**
- Modify : `backend/app/api/routes.py:2161-2170` (`/audio` + `mtime`), après `/audio/meta` (PUT tags) ; `backend/app/services/sfx_service.py` (`sanitize_tags`) ; `frontend/patches/sfxstudio.js` (états ~304, `refresh` 327, memo `all` 344, `searched` 352, `itemRow` 590, tri 838-844) ; `frontend/dist/shared/sfxstudio.css`
- Test : `backend/tests/test_sons_drawer_api.py`

Ce que le tiroir a DÉJÀ, relu le 03/09, et qu'on ne réécrit pas : la mini-forme
d'onde (`svxWaveEntry`, progression pendant la lecture), les favoris persistés
(`svxFavsLoad`/`svxFavsSave`), les onglets par famille avec compteurs, la
recherche libre nom + prompt, le tri Récents/Nom/Durée/Favoris, le clavier
(Espace, ↑↓, Entrée, F, Suppr, /). Manquent — et c'est le sujet de cette tâche :
la pré-écoute AU SURVOL, les tags éditables, le filtre « mes sons / catalogue »,
le tri par date, et les trois actions par item.

- [ ] **Étape 1 : banc rouge (API)**

```python
# backend/tests/test_sons_drawer_api.py
# -*- coding: utf-8 -*-
"""P3 — l'API du tiroir Sons : mtime dans /audio, tags éditables (PUT
/audio/meta/{fn}) écrits dans le sidecar, garde-fous.
Run: python tests/test_sons_drawer_api.py (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzdrawer_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.services import sfx_service as S
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
audio = settings.images_path.parent / "audio"; audio.mkdir(exist_ok=True)
(audio / "a.mp3").write_bytes(b"ID3a"); (audio / "b.mp3").write_bytes(b"ID3b")
os.utime(audio / "a.mp3", (1_700_000_000, 1_700_000_000))
async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        d = (await c.get("/api/audio")).json()["audio"]
        check("mtime servi, tri décroissant", [x["name"] for x in d] == ["b.mp3", "a.mp3"] and d[1]["mtime"] == 1_700_000_000, str(d))
        r = await c.put("/api/audio/meta/a.mp3", json={"tags": [" Impact ", "impact", "x" * 40, "grave", "", 7] + [f"t{i}" for i in range(20)]})
        check("tags nettoyés : trim, dédoublonnés, ≤ 24 car., ≤ 12", r.status_code == 200 and r.json()["meta"]["tags"][:3] == ["Impact", "x" * 24, "grave"] and len(r.json()["meta"]["tags"]) == 12, r.text)
        check("sidecar écrit", S.load_meta()["a.mp3"]["tags"][0] == "Impact")
        check("kind conservé (import déduit)", S.load_meta()["a.mp3"].get("kind") == "import")
        r = await c.put("/api/audio/meta/zzz.mp3", json={"tags": ["a"]}); check("inconnu : 404", r.status_code == 404)
        r = await c.put("/api/audio/meta/..%2F..%2Fdeepotus.db", json={"tags": ["a"]}); check("traversée : 404", r.status_code == 404)
        m = (await c.get("/api/audio/meta")).json()["meta"]
        check("GET /audio/meta rend les tags", m["a.mp3"]["tags"][0] == "Impact")
asyncio.run(main())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```
Run : `python tests/test_sons_drawer_api.py` → `FAIL  mtime servi…` puis `405`/`404` sur le PUT.

- [ ] **Étape 2 : backend**

`/audio` (ligne 2166) : `out.append({"name": p.name, "url": ..., "size_kb": ..., "mtime": int(p.stat().st_mtime)})`. Dans `sfx_service.py` après `classify_kind` :
```python
def sanitize_tags(raw) -> list[str]:
    """≤ 12 tags, ≤ 24 caractères, trim, dédoublonnés sans casse, chaînes seules."""
    out, seen = [], set()
    for t in (raw if isinstance(raw, list) else []):
        if not isinstance(t, str): continue
        t = " ".join(t.split())[:24]
        if not t or t.lower() in seen: continue
        seen.add(t.lower()); out.append(t)
        if len(out) == 12: break
    return out
```
Route, juste après `get_audio_meta` (l'ordre importe : AVANT `/audio/{filename}`) :
```python
@router.put("/audio/meta/{filename}")
async def put_audio_meta(filename: str, request: Request):
    """P3 — tags éditables du tiroir Sons, fusionnés dans le sidecar."""
    from app.services import sfx_service
    safe = Path(filename).name
    p = _audio_dir() / safe
    if safe != filename or not p.is_file():
        raise HTTPException(404, f"Audio introuvable : {filename}")
    body = await request.json()
    entry = dict(sfx_service.load_meta().get(safe) or {"kind": sfx_service.classify_kind(safe)})
    entry["tags"] = sfx_service.sanitize_tags(body.get("tags"))
    await asyncio.get_running_loop().run_in_executor(None, lambda: sfx_service.record_meta(safe, entry))
    return {"ok": True, "filename": safe, "meta": entry}
```
Run : `python tests/test_sons_drawer_api.py` → `=== 8 passed, 0 failed ===`.

- [ ] **Étape 3 : le tiroir (sfxstudio.js)**

États, à insérer après la ligne `var s11=x.useState(svxFavsLoad),favs=…` :
```js
  var s12=x.useState(function(){try{return localStorage.getItem("dz_sfx_hover")==="1"}catch(_e){return !1}}),hoverPrev=s12[0],setHoverPrev=s12[1];
  var s13=x.useState("tous"),srcFilter=s13[0],setSrcFilter=s13[1];     /* tous | miens | catalogue */
  var s14=x.useState(null),tagEdit=s14[0],setTagEdit=s14[1];           /* {name,val} */
  var s15=x.useState(""),busyAct=s15[0],setBusyAct=s15[1];             /* "stems:<fn>" … */
  var s16=x.useState(null),armAct=s16[0],setArmAct=s16[1];             /* {name,act,usd} : coût à confirmer */
  var hoverTimer=x.useRef(0);
  x.useEffect(function(){try{localStorage.setItem("dz_sfx_hover",hoverPrev?"1":"0")}catch(_e){}},[hoverPrev]);
```
Memo `all` : ajouter dans l'objet `tags:m&&Array.isArray(m.tags)?m.tags:[],mtime:svxN(a.mtime,0),starter:!!(m&&m.starter_id),parent:m&&m.parent?String(m.parent):""`. Memo `searched` : le filtre devient `it.name.toLowerCase().indexOf(qn)>=0||(it.prompt&&…)||it.tags.some(function(t){return t.toLowerCase().indexOf(qn)>=0})`, puis `.filter(function(it){return srcFilter==="tous"||(srcFilter==="catalogue")===it.starter})`. Tri : ajouter `else if(sort==="date")rows.sort(function(a,b){return b.mtime-a.mtime||a.idx-b.idx});` et l'option `r.jsx("option",{value:"date",children:"Date"})`.

Fonctions (avant `function itemRow`) :
```js
  function tagSave(item,val){
    var tags=val.split(/[,;]/).map(function(t){return t.trim()}).filter(Boolean);
    fetch("/api/audio/meta/"+encodeURIComponent(item.name),{method:"PUT",
      headers:{"Content-Type":"application/json"},body:JSON.stringify({tags:tags})})
      .then(function(res){if(!res.ok)throw new Error("tags refusés");return res.json()})
      .then(function(){setTagEdit(null);refresh()})
      .catch(function(e){fireNote("Tags : "+String(e&&e.message||e))})}
  /* actions payantes : premier clic ARME avec le coût, second clic tire */
  function actGo(item,act){
    var key=act+":"+item.name;
    if(busyAct)return;
    var routes={stems:"/api/audio/stems",isolate:"/api/audio/isolate",enhance:"/api/audio/enhance"};
    var usd=act==="stems"?item.dur*7e-4:act==="isolate"?item.dur/60*1000*24e-5:0;
    if(usd>0&&!(armAct&&armAct.name===item.name&&armAct.act===act)){
      setArmAct({name:item.name,act:act,usd:usd});return}
    setArmAct(null);setBusyAct(key);
    fetch(routes[act],{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({filename:item.name})})
      .then(function(res){return res.json().then(function(d){if(!res.ok)throw new Error(d.detail||"échec");return d})})
      .then(function(d){setBusyAct("");refresh();
        fireNote(act==="stems"?(d.items.length+" stems posés en Bibliothèque"+(d.missing.length?" — manquants : "+d.missing.join(", "):"")+" · ~$"+d.usd.toFixed(3))
          :act==="isolate"?"Voix isolée : "+d.filename+" · ~$"+d.usd.toFixed(3):"Voix améliorée : "+d.filename+" (gratuit)")})
      .catch(function(e){setBusyAct("");fireNote(String(e&&e.message||e))})}
  function actBtn(it,act,lbl,tt){
    var armed=armAct&&armAct.name===it.name&&armAct.act===act;
    return r.jsx("button",{className:"svx-abtn"+(armed?" svx-armed":""),tabIndex:-1,
      "data-busy":busyAct===act+":"+it.name?"":void 0,
      title:armed?"~$"+armAct.usd.toFixed(3)+" — cliquer pour confirmer":tt,
      onClick:function(e){e.stopPropagation();actGo(it,act)},
      children:armed?"~$"+armAct.usd.toFixed(2)+" ✓":lbl})}
```
Dans `itemRow` : sur le `div.svx-item`, ajouter `onMouseEnter:function(){if(!hoverPrev)return;clearTimeout(hoverTimer.current);hoverTimer.current=setTimeout(function(){if(!(prev&&prev.name===it.name))prevToggle(it)},350)},onMouseLeave:function(){clearTimeout(hoverTimer.current)}` ; après le `div.svx-iprompt`, la ligne de tags :
```js
        r.jsxs("div",{className:"svx-itags",children:[
          it.tags.map(function(t){return r.jsx("span",{className:"svx-itag",children:t},t)}),
          it.starter?r.jsx("span",{className:"svx-itag svx-itag-cat",title:"catalogue de démarrage (CC0)",children:"catalogue"}):null,
          it.parent?r.jsx("span",{className:"svx-itag svx-itag-cat",title:"dérivé de "+it.parent,children:"← "+it.parent.slice(0,18)}):null,
          tagEdit&&tagEdit.name===it.name?r.jsx("input",{className:"svx-tagin",autoFocus:!0,value:tagEdit.val,
            placeholder:"tags, séparés par des virgules",
            onClick:function(e){e.stopPropagation()},
            onChange:function(e){setTagEdit({name:it.name,val:e.target.value})},
            onKeyDown:function(e){if(e.key==="Enter")tagSave(it,tagEdit.val);if(e.key==="Escape")setTagEdit(null);e.stopPropagation()}})
          :r.jsx("button",{className:"svx-itag svx-itag-add",tabIndex:-1,title:"Éditer les tags",
            onClick:function(e){e.stopPropagation();setTagEdit({name:it.name,val:it.tags.join(", ")})},children:"＋tag"})]}),
```
et dans `div.svx-iact`, avant le bouton `✕` : `it.kind==="musique"?actBtn(it,"stems","≡","Séparer en stems (Demucs, fal)"):null, it.kind==="voix"||it.kind==="import"?actBtn(it,"isolate","◌","Isoler la voix (ElevenLabs)"):null, it.kind==="voix"||it.kind==="import"?actBtn(it,"enhance","✦","Améliorer (eq → débruitage → compresseur → −16 LUFS, gratuit)"):null,`. Dans `svx-filters`, après le `select` de tri :
```js
      r.jsx("div",{className:"svx-seg",role:"group","aria-label":"Origine",children:[["tous","Tous"],["miens","Mes sons"],["catalogue","Catalogue"]].map(function(o){
        return r.jsx("button",{className:"svx-segbtn","data-on":srcFilter===o[0]?"":void 0,onClick:function(){setSrcFilter(o[0])},children:o[1]},o[0])})}),
      r.jsx("button",{className:"svx-iconbtn","data-on":hoverPrev?"":void 0,title:"Pré-écoute au survol (350 ms)","aria-pressed":hoverPrev,
        onClick:function(){setHoverPrev(!hoverPrev)},children:"👂"})
```
CSS (`sfxstudio.css`, fin de fichier) :
```css
.dzsvm .svx-itags{display:flex;flex-wrap:wrap;gap:4px;margin-top:3px}
.dzsvm .svx-itag{font-size:10.5px;line-height:16px;padding:0 6px;border-radius:8px;background:var(--panel2);color:var(--ink3);border:1px solid var(--stroke)}
.dzsvm .svx-itag-cat{color:var(--ink4);border-style:dashed}
.dzsvm .svx-itag-add{cursor:pointer;color:var(--ink3)} .dzsvm .svx-itag-add:hover{color:var(--ink)}
.dzsvm .svx-tagin{font:inherit;font-size:11px;background:var(--panel3);color:var(--ink);border:1px solid var(--stroke2);border-radius:6px;padding:1px 6px;min-width:160px}
.dzsvm .svx-seg{display:inline-flex;border:1px solid var(--stroke);border-radius:6px;overflow:hidden}
.dzsvm .svx-segbtn{font-size:11px;padding:2px 7px;background:transparent;color:var(--ink3);border:0;cursor:pointer}
.dzsvm .svx-segbtn[data-on]{background:var(--panel2);color:var(--ink)}
.dzsvm .svx-abtn.svx-armed{color:var(--amber);border-color:var(--amber)}
.dzsvm .svx-abtn[data-busy]{opacity:.5;pointer-events:none}
```

- [ ] **Étape 4 : injection et preuve à l'écran**

Run : `python scripts/refresh_layer.py --layer sfxstudio` → `[sfxstudio] bloc rafraîchi (… car.) · bak: 0 touché`. Puis `grep -o "/\*__DZ_[A-Z]*__\*/" frontend/dist/assets/index-BEOJX8L5.js | sort | uniq -c` → 8 lignes à 1. Lancer l'app (c'est l'utilisateur qui relance), Montage → `B` : tags, chips Mes sons/Catalogue, tri Date, 👂, boutons ≡/◌/✦ ; **mesurer** `document.querySelectorAll(".svx-item").length` égal au compteur de l'en-tête et `offsetHeight > 0` sur le premier item (piège de la grille effondrée, mémoire 28/08).

- [ ] **Étape 5 : commit**
```
git add backend/app/api/routes.py backend/app/services/sfx_service.py frontend/patches/sfxstudio.js frontend/dist/shared/sfxstudio.css frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_sons_drawer_api.py
git commit -m 'son-vfx P3 : le tiroir Sons devient la vue de reference' -m 'Pré-écoute au survol, tags éditables dans le sidecar, filtre mes sons / catalogue, tri par date, stems / isoler / améliorer par item avec coût armé au premier clic.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 5 : P3b — la puce Audio de la Bibliothèque monte le tiroir (bundle, tag `libsons`)

**Files :**
- Create : `scripts/patch_bundle_libsons.py`
- Modify : `frontend/patches/sfxstudio.js` (`SvxDrawer` : prop `inline`) ; `frontend/dist/shared/sfxstudio.css`

- [ ] **Étape 1 : `inline` dans le Drawer** — dans `SvxDrawer`, remplacer `if(!open)return null;` par `if(!open&&!props.inline)return null;` et, sur le `aside`, `className:"svx-drawer"+(props.inline?" svx-inline":"")` ; le bouton `svx-dclose` devient `props.inline?null:r.jsx("button",…)`. CSS : `.dzsvm .svx-drawer.svx-inline{position:static;width:100%;height:auto;max-height:70vh;border:1px solid var(--stroke);border-radius:8px}` et l'hôte `.dz-libsons{position:relative;min-height:320px;margin-bottom:14px}` (le `.dzsvm` racine est `position:absolute;inset:0` — l'hôte lui donne un contenant). Run : `python scripts/refresh_layer.py --layer sfxstudio`.

- [ ] **Étape 2 : le patcher** (ancre mesurée UNIQUE le 03/09 : `o==="Audio"&&r.jsxs("div",{style:{marginBottom:14,display:"grid",gap:10},children:[`)

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_libsons.py
"""Patcher assert-gardé : la puce Audio de la Bibliothèque monte le tiroir Sons.
BASELINE : bundle POST-patch seedance25 (queue de chaîne, mesurée le 03/09).
Backup : .js.bak_libsons — EN QUEUE. Rejouer : repatch_all.py --from libsons.
Une ancre, une insertion : le tiroir (DzSfx.Drawer inline, dans un hôte
.dzsvm) est rendu AU-DESSUS de la zone d'upload de l'onglet Audio ; couche
absente → rien n'est inséré à l'écran (feature-detect), rien ne casse."""
import pathlib, shutil, sys
REPO = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = REPO / "frontend/dist/assets/index-BEOJX8L5.js"
TAG = "libsons"
ANCHOR = 'o==="Audio"&&r.jsxs("div",{style:{marginBottom:14,display:"grid",gap:10},children:['
INSERT = ('o==="Audio"&&window.DzSfx&&window.DzSfx.ready&&r.jsx("div",{className:"dzsvm dz-libsons",'
          'children:r.jsx(window.DzSfx.Drawer,{open:!0,inline:!0,defaultTab:"tous"})}),')
def main():
    args = sys.argv[1:]
    bak = BUNDLE.with_name(BUNDLE.name + ".bak_" + TAG)
    if "--force-unchained" not in args:
        for other in BUNDLE.parent.glob(BUNDLE.name + ".bak_*"):
            if bak.exists() and other != bak and other.stat().st_mtime > bak.stat().st_mtime:
                raise SystemExit(f"[garde-chaine] maillon aval {other.name} — rejouer avec repatch_all.")
    if bak.exists(): shutil.copy2(bak, BUNDLE)
    raw = BUNDLE.read_bytes(); bom = raw.startswith(b"\xef\xbb\xbf")
    s = raw.decode("utf-8-sig" if bom else "utf-8")
    if "--strip" in args:
        if bak.exists(): shutil.copy2(bak, BUNDLE); print("restauré"); return
        raise SystemExit("pas de .bak_libsons")
    n = s.count(ANCHOR)
    if n != 1: raise SystemExit(f"[{TAG}] anchor count={n} (want 1). Rien écrit.")
    if "--check" in args: print(f"[{TAG}] applicable (1 ancre)"); return
    if not bak.exists(): shutil.copy2(BUNDLE, bak); print("backup ->", bak.name)
    s = s.replace(ANCHOR, INSERT + ANCHOR)
    out = s.encode("utf-8"); BUNDLE.write_bytes((b"\xef\xbb\xbf" + out) if bom else out)
    print(f"[{TAG}] OK, bundle {BUNDLE.stat().st_size} o")
if __name__ == "__main__": main()
```
Run : `python scripts/patch_bundle_libsons.py --check` → `[libsons] applicable (1 ancre)` ; `python scripts/patch_bundle_libsons.py` → `backup -> index-BEOJX8L5.js.bak_libsons` ; `python scripts/repatch_all.py --list` → cinq lignes, `libsons OK` en dernier. Bibliothèque → Audio : le tiroir s'affiche au-dessus de la zone d'upload ; mesurer `document.querySelector(".dz-libsons .svx-item").offsetHeight > 0`.

- [ ] **Étape 3 : commit**
```
git add scripts/patch_bundle_libsons.py frontend/patches/sfxstudio.js frontend/dist/shared/sfxstudio.css frontend/dist/assets/index-BEOJX8L5.js frontend/dist/assets/index-BEOJX8L5.js.bak_libsons
git commit -m 'son-vfx P3b : la puce Audio de la Bibliotheque monte le tiroir Sons (tag libsons, en queue)' -m 'Un seul patch natif de ce plan : ancre unique mesurée, .bak_libsons en queue après seedance25, feature-detect sur window.DzSfx.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 6 : P4 — chanson chantée : éditeur de paroles structurées, ACE-Step et MiniMax 2.0 au registre

**Files :**
- Modify : `backend/app/services/music_service.py` (`MUSIC_MODELS`, `catalog`, `_payload`, + `normalize_lyrics`, `lyrics_skeleton`) ; `backend/app/api/routes.py` (après `/music-models`) ; `frontend/patches/son-vfx-montage.js` (`SvmMusic`, lignes 368-486)
- Test : `backend/tests/test_music_lyrics.py`

- [ ] **Étape 1 : relire, et chercher « Music 3 »**

`WebFetch url=https://fal.ai/models/fal-ai/ace-step/api prompt="input params, lyrics tags, output fields"` → `tags`, `lyrics`, `duration`, `seed`, `audio.url`. `WebFetch url=https://fal.ai/models/fal-ai/minimax-music/v2/api …` → `prompt` 10-300, `lyrics_prompt` 10-3000. Puis, dans l'ordre, `WebFetch` de `https://fal.ai/models/fal-ai/minimax-music/v3/api` (404 le 03/09), `https://fal.ai/models/fal-ai/minimax-music/v2.6/api` (existe : c'est 2.6, déjà au registre). Si aucun identifiant « Music 3 » ne répond, **ne pas l'inventer** : l'étape 3 n'ajoute que `ace-step` et `minimax-music-20`, et le commit le dit.

- [ ] **Étape 2 : banc rouge**

```python
# backend/tests/test_music_lyrics.py
# -*- coding: utf-8 -*-
"""P4 — registre étendu, paroles structurées normalisées par style de modèle,
charge utile fal exacte (tags pour ACE-Step, lyrics_prompt pour Music 2.0),
squelette persona, prix par seconde annoncé avant le tir.
Run: python tests/test_music_lyrics.py (depuis backend/)"""
import os, sys, tempfile
os.environ.setdefault("DEEPOTUS_DATA_DIR", tempfile.mkdtemp(prefix="dzlyr_"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
from app.services import music_service as MS, pricing as P
ace, m20 = MS.MUSIC_MODELS["ace-step"], MS.MUSIC_MODELS["minimax-music-20"]
check("ACE-Step : endpoint, paroles, durée, graine, prix/s", ace["endpoint"] == "fal-ai/ace-step" and ace["lyrics"]
      and ace["seed"] and ace["duration"] == (10, 240) and ace["usd_unit"] == "s" and ace["usd"] == 0.0002)
check("Music 2.0 : endpoint v2, paroles OBLIGATOIRES", m20["endpoint"] == "fal-ai/minimax-music/v2" and m20["lyrics_required"])
L = "[Verse]\nSous la mer\n\n[Refrain]\nDeepotus\n\n[Pont]\nremonte"
check("ace : balises minuscules, [chorus]/[bridge]", MS.normalize_lyrics(L, "ace") == "[verse]\nSous la mer\n\n[chorus]\nDeepotus\n\n[bridge]\nremonte", MS.normalize_lyrics(L, "ace"))
check("ace instrumental = [inst]", MS.normalize_lyrics("", "ace", instrumental=True) == "[inst]")
check("minimax : balises capitalisées gardées", MS.normalize_lyrics(L, "minimax").startswith("[Verse]"))
args, notes = MS._payload(ace, "dark ambient, 70 bpm", {"lyrics": L, "duration_s": 45, "seed": 7})
check("ACE-Step envoie tags + lyrics + duration + seed, jamais prompt",
      args == {"tags": "dark ambient, 70 bpm", "lyrics": MS.normalize_lyrics(L, "ace"), "duration": 45, "seed": 7}, str(args))
args, notes = MS._payload(m20, "hymne pirate", {"lyrics": L})
check("Music 2.0 envoie prompt + lyrics_prompt", set(args) == {"prompt", "lyrics_prompt"} and args["prompt"] == "hymne pirate", str(args))
try: MS._payload(m20, "x" * 20, {"lyrics": ""}); check("Music 2.0 sans paroles : refus", False)
except MS.MusicError as e: check("Music 2.0 sans paroles : 400 explicite", e.status == 400 and "paroles" in e.message)
sk = MS.lyrics_skeleton("deepotus", theme="la remontée")
check("squelette persona : [Verse]/[Chorus], nom de la persona, thème", "[Verse]" in sk and "[Chorus]" in sk and "Deepotus" in sk and "remontée" in sk, sk)
cat = MS.catalog()
row = [m for m in cat["models"] if m["id"] == "ace-step"][0]
check("catalogue expose usd_unit et lyrics_style", row["usd_unit"] == "s" and row["lyrics_style"] == "ace")
e = P.estimate({"kind": "music", "model": "ace-step", "duration_s": 120})
check("estimation 120 s ACE-Step = 0,024 $", abs(e["total_usd"] - 0.024) < 1e-9, str(e))
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```
Run : `python tests/test_music_lyrics.py` → `KeyError: 'ace-step'`

- [ ] **Étape 3 : registre, normalisation, charge utile**

Dans `MUSIC_MODELS`, après `"cassetteai"` :
```python
    "ace-step": {
        "label": "ACE-Step (paroles)", "provider": "fal", "endpoint": "fal-ai/ace-step",
        "desc": "Le moins cher : chanson complète avec paroles structurées [verse]/[chorus]/[bridge]. "
                "Genres en balises, graine reproductible.",
        # /api relu le 03/09/2026 : duration défaut 60, borne haute NON documentée —
        # 240 s prudent, à relever après un premier tir réussi au-delà.
        "duration": (10, 240), "fixed_duration": None,
        "lyrics": True, "instrumental": True, "seed": True,
        "usd": 0.0002, "usd_unit": "s", "lyrics_style": "ace",
    },
    "minimax-music-20": {
        "label": "MiniMax Music 2.0", "provider": "fal", "endpoint": "fal-ai/minimax-music/v2",
        "desc": "Chanson chantée à partir de paroles OBLIGATOIRES (10-3000 car.), description 10-300 car.",
        "duration": None, "fixed_duration": None,
        "lyrics": True, "instrumental": False, "seed": False,
        "usd": 0.03, "usd_unit": "gen", "lyrics_style": "minimax", "lyrics_required": True, "prompt_max": 300,
    },
```
Les quatre entrées existantes reçoivent `"usd_unit": "gen", "lyrics_style": "minimax"` (2.6) ou `None`. `catalog()` ajoute `"usd_unit": v.get("usd_unit", "gen"), "lyrics_style": v.get("lyrics_style"), "lyrics_required": v.get("lyrics_required", False)`. Nouvelles fonctions (après `build_prompt`) :
```python
_TAG_MAP = {"verse": "verse", "couplet": "verse", "chorus": "chorus", "refrain": "chorus",
            "bridge": "bridge", "pont": "bridge", "intro": "intro", "outro": "outro"}
_TAG_RX = re.compile(r"\[([^\[\]\n]{1,24})\]")

def normalize_lyrics(text: str, style: str | None, instrumental: bool = False) -> str:
    """Paroles structurées → convention du modèle. ace : balises minuscules
    (verse/chorus/bridge), instrumental = « [inst] » ; minimax : [Verse]/[Chorus]
    capitalisés (doc 2.6). Un tag inconnu est laissé tel quel."""
    if style == "ace" and instrumental:
        return "[inst]"
    def sub(m):
        k = _TAG_MAP.get(m.group(1).strip().lower())
        if not k:
            return m.group(0)
        return f"[{k}]" if style == "ace" else f"[{k.capitalize()}]"
    return _TAG_RX.sub(sub, str(text or "").strip())[:_MAX_LYRICS]

def lyrics_skeleton(persona_id: str = "deepotus", theme: str = "") -> str:
    """Squelette [Verse]/[Chorus]/[Verse]/[Bridge]/[Chorus] nourri par la
    persona (nom, mots-clés d'univers) — un point de départ, jamais des
    paroles finies : le modèle ou l'utilisateur les écrit."""
    import json
    from app.services.elevenlabs_service import PERSONAS_DIR
    try:
        d = json.loads((PERSONAS_DIR / f"{persona_id}.json").read_text(encoding="utf-8"))
    except Exception:
        d = {}
    name = (d.get("display_name") or persona_id).split(" — ")[0]
    kws = ", ".join((d.get("vibe_keywords") or [])[:4])
    t = theme.strip() or "from the deep"
    return (f"[Verse]\n{name} — {t}\n{kws}\n\n[Chorus]\n{name}, {t}\n\n[Verse]\n…\n\n[Bridge]\n…\n\n[Chorus]\n{name}, {t}")
```
Dans `_payload`, au début : `style = model.get("lyrics_style")` ; la branche durée devient `args["seconds_total" if "stable-audio" in model["endpoint"] else "duration"] = d` (inchangé) ; la branche paroles devient :
```python
    lyrics = str(body.get("lyrics") or "").strip()
    instrumental = bool(body.get("instrumental", True))
    if style == "ace":
        args = {"tags": prompt[:_MAX_PROMPT]}          # ACE-Step n'a pas de prompt : des tags
        if "duration" in body_args: args["duration"] = body_args["duration"]
        args["lyrics"] = normalize_lyrics(lyrics, "ace", instrumental=instrumental or not lyrics)
    elif model["lyrics"]:
        if model.get("lyrics_required"):
            if len(lyrics) < 10:
                raise MusicError(400, f"{model['label']} exige des paroles (10 à 3000 caractères).")
            args["prompt"] = prompt[:model.get("prompt_max", _MAX_PROMPT)]
            args["lyrics_prompt"] = normalize_lyrics(lyrics, "minimax")[:3000]
        elif lyrics:
            args["lyrics"] = normalize_lyrics(lyrics, "minimax"); args["is_instrumental"] = False
        elif instrumental:
            args["is_instrumental"] = True
        else:
            args["is_instrumental"] = False; args["lyrics_optimizer"] = True
    elif lyrics:
        notes.append(f"{model['label']} ne prend pas de paroles — le texte saisi a été ignoré.")
```
(`body_args` = le dict `args` construit AVANT cette branche ; pour ACE-Step on repart d'un dict neuf sans `prompt`, puis on y remet `seed` par la branche graine existante.) Route : `@router.get("/music/lyrics-skeleton")` → `{"lyrics": music_service.lyrics_skeleton("deepotus", theme=theme)}` (`theme: str = ""`).

- [ ] **Étape 4 : l'éditeur (SvmMusic)**

Remplacer le `textarea` des paroles (ligne 461-464) par `r.jsx(SvmLyricsEditor,{value:lyrics,onChange:setLyrics,style:m.lyrics_style,required:!!m.lyrics_required})` et ajouter le composant avant `function SvmMusic` :
```js
/* éditeur de paroles structurées : sections [Verse]/[Chorus]/[Bridge] éditées
   une par une, sérialisées en texte balisé — le backend normalise par modèle */
function svmLyricsParse(t){var out=[],cur=null;
  String(t||"").split(/\r?\n/).forEach(function(l){var m=/^\[([^\]]+)\]\s*$/.exec(l.trim());
    if(m){cur={tag:m[1],text:""};out.push(cur)}else if(cur)cur.text+=(cur.text?"\n":"")+l;
    else if(l.trim()){cur={tag:"Verse",text:l};out.push(cur)}});return out}
function svmLyricsJoin(secs){return secs.map(function(s){return "["+s.tag+"]\n"+s.text.trim()}).join("\n\n")}
function SvmLyricsEditor(props){
  var secs=svmLyricsParse(props.value);
  function set(next){props.onChange(svmLyricsJoin(next))}
  function add(tag){set(secs.concat([{tag:tag,text:""}]))}
  function skeleton(){fetch("/api/music/lyrics-skeleton?theme="+encodeURIComponent(prompt("Thème de la chanson ?")||""))
    .then(function(r2){return r2.json()}).then(function(d){props.onChange(d.lyrics||"")}).catch(function(){})}
  return r.jsxs("div",{className:"svm-lyrics",children:[
    r.jsxs("div",{className:"svm-toolrow",children:[
      ["Verse","Chorus","Bridge"].map(function(t){return r.jsx("button",{className:"svm-minibtn",onClick:function(){add(t)},children:"+ "+(t==="Verse"?"couplet":t==="Chorus"?"refrain":"pont")},t)}),
      r.jsx("button",{className:"svm-minibtn",title:"Squelette nourri par la persona deepotus",onClick:skeleton,children:"squelette persona"}),
      props.required?r.jsx("span",{className:"svm-note",style:{marginTop:0},children:"paroles obligatoires pour ce modèle"}):null]}),
    secs.map(function(s,i){return r.jsxs("div",{className:"svm-lyrsec",children:[
      r.jsx("input",{className:"svm-lyrtag",value:s.tag,onChange:function(e){var n=secs.slice();n[i]=Object.assign({},s,{tag:e.target.value});set(n)}}),
      r.jsx("textarea",{className:"svm-musicprompt",rows:2,value:s.text,onChange:function(e){var n=secs.slice();n[i]=Object.assign({},s,{text:e.target.value});set(n)}}),
      r.jsx("button",{className:"svm-minibtn",title:"Retirer",onClick:function(){set(secs.filter(function(_s,j){return j!==i}))},children:"✕"})]},i)})]})}
```
Le prix : remplacer `"~$"+v.usd.toFixed(2)` par `v.usd_unit==="s"?"~$"+(v.usd*dur).toFixed(3)+" · "+dur+" s":"~$"+v.usd.toFixed(2)` (le `dur` du composant). Le corps du POST envoie `lyrics:m.lyrics&&!inst?lyrics:""` inchangé, plus `seed:m.seed&&seed?seed:void 0` avec un champ graine `r.jsx("input",{className:"svm-transdur",type:"number",placeholder:"graine"…})` visible si `m.seed`. Run : `python scripts/refresh_layer.py --layer sonvfx` → `[sonvfx] bloc rafraîchi … · bak: 0 touché` puis les lignes de `reapply_inblock_patches` ; **avant et après**, `python scripts/reapply_inblock_patches.py --check` doit compter le même nombre de couples in-bloc.

- [ ] **Étape 5 : vert, commit**

Run : `python tests/test_music_lyrics.py` → `=== 11 passed, 0 failed ===` ; `python -m pytest tests/test_starter_particles.py -q` reste vert (contrat des modèles).
```
git add backend/app/services/music_service.py backend/app/api/routes.py frontend/patches/son-vfx-montage.js frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_music_lyrics.py
git commit -m 'son-vfx P4 : chanson chantee - editeur de paroles structurees, ACE-Step et MiniMax 2.0 au registre' -m 'ACE-Step reçoit des tags et des paroles minuscules ([inst] = instrumental), Music 2.0 exige lyrics_prompt ; « MiniMax Music 3 » n a pas d identifiant fal retrouvé le 03/09 (v3 et music-03 : 404), il n entre pas au registre.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 7 : P5 — direction d'interprétation, balises Eleven v3

**Files :**
- Create : `backend/app/services/voice_direction.py`
- Modify : `backend/app/api/routes.py:2405-2460` (`/audio/voiceover` : `style`), + `GET /voice-tags` ; `frontend/patches/son-vfx-montage.js` (`editorCard`, ~680-705 : une vraie carte de génération)
- Test : `backend/tests/test_voice_direction.py`

- [ ] **Étape 1 : banc rouge**

```python
# backend/tests/test_voice_direction.py
# -*- coding: utf-8 -*-
"""P5 — registre des balises v3, application d'un style, retrait propre quand
le fournisseur ne les lit pas (Voicebox, modèles non-v3), route /voice-tags,
texte RÉELLEMENT envoyé au SDK (stub).
Run: python tests/test_voice_direction.py (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile, types
_tmp = tempfile.mkdtemp(prefix="dzdir_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["ELEVENLABS_API_KEY"] = "test-11l"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
SENT = []
class _TTS:
    def convert(self, **kw): SENT.append(kw); return iter([b"ID3" + b"\0" * 64])
class _Client:
    def __init__(self, api_key=None): self.text_to_speech = _TTS()
_m = types.ModuleType("elevenlabs.client"); _m.ElevenLabs = _Client
_p = types.ModuleType("elevenlabs"); _p.client = _m
sys.modules["elevenlabs"] = _p; sys.modules["elevenlabs.client"] = _m
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.services import voice_direction as VD
settings.ELEVENLABS_API_KEY = "test-11l"
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
check("registre : 4 groupes, toutes les balises entre crochets", set(VD.V3_TAGS) == {"emotion", "voix", "rythme", "sons"}
      and all(t.startswith("[") and t.endswith("]") for g in VD.V3_TAGS.values() for t in g))
check("[excited] et [whispers] connus, [pause] marqué expérimental", "[excited]" in VD.KNOWN and "[whispers]" in VD.KNOWN and "[pause]" in VD.EXPERIMENTAL)
st = VD.clamp_style({"tags": ["[excited]", "[foo]", "[whispers]", "[sighs]", "[curious]", "[crying]"], "stability": 0.7})
check("style clampé : inconnu retiré, ≤ 4 balises, stabilité snappée", st == {"tags": ["[excited]", "[whispers]", "[sighs]", "[curious]"], "stability": 0.5}, str(st))
check("apply_style préfixe", VD.apply_style("Bonjour", st) == "[excited] [whispers] [sighs] [curious] Bonjour")
check("texte déjà balisé : pas de double préfixe", VD.apply_style("[sad] Adieu", st) == "[sad] Adieu")
check("unknown_tags", VD.unknown_tags("[sad] et [zzz] puis [laughs]") == ["[zzz]"])
check("strip_tags", VD.strip_tags("[sad] Adieu [pause] monde") == "Adieu monde")
async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        d = (await c.get("/api/voice-tags")).json()
        check("/voice-tags : groupes + fournisseur", d["groups"]["emotion"][0] == "[excited]" and d["providers"]["voicebox"] is False)
        r = await c.post("/api/audio/voiceover", json={"script": "Salut le fond", "model": "eleven_v3", "style": {"tags": ["[whispers]"]}})
        check("v3 : le SDK reçoit le texte balisé", r.status_code == 200 and SENT[-1]["text"] == "[whispers] Salut le fond" and SENT[-1]["model_id"] == "eleven_v3", r.text[:200] + str(SENT[-1:]))
        r = await c.post("/api/audio/voiceover", json={"script": "[sad] Salut", "model": "eleven_multilingual_v2"})
        check("hors v3 : balises retirées ET note", SENT[-1]["text"] == "Salut" and any("v3" in n for n in r.json()["notes"]), r.text[:200])
asyncio.run(main())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```
Run : `python tests/test_voice_direction.py` → `ModuleNotFoundError: No module named 'app.services.voice_direction'`

- [ ] **Étape 2 : le module**

```python
# backend/app/services/voice_direction.py
# -*- coding: utf-8 -*-
"""P5 — direction d'interprétation par balises Eleven v3 (docs prompting
relues le 03/09/2026). Voicebox n'en lit aucune, les modèles v2/flash non
plus : on retire les balises et on le DIT (notes) plutôt que de les laisser
prononcer « crochet excited crochet »."""
from __future__ import annotations
import re
V3_TAGS = {
    "emotion": ["[excited]", "[sad]", "[curious]", "[sarcastic]", "[mischievously]", "[crying]"],
    "voix": ["[whispers]", "[sighs]", "[exhales]", "[laughs]", "[laughs harder]", "[starts laughing]", "[wheezing]", "[snorts]"],
    "rythme": ["[pause]"],
    "sons": ["[applause]", "[clapping]", "[explosion]", "[gunshot]", "[swallows]", "[gulps]"],
}
EXPERIMENTAL = {"[pause]", "[sings]", "[woo]"}   # [pause] : cité par R4, absent de la page relue
KNOWN = {t for g in V3_TAGS.values() for t in g} | EXPERIMENTAL
_TAG_RX = re.compile(r"\[[^\[\]\n]{1,40}\]")
MAX_TAGS = 4

def find_tags(text: str) -> list[str]:
    return _TAG_RX.findall(text or "")

def unknown_tags(text: str) -> list[str]:
    return [t for t in find_tags(text) if t not in KNOWN]

def strip_tags(text: str) -> str:
    return " ".join(_TAG_RX.sub(" ", text or "").split())

def clamp_style(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    tags = [t for t in (raw.get("tags") or []) if isinstance(t, str) and t in KNOWN][:MAX_TAGS]
    try: s = float(raw.get("stability", 0.5))
    except (TypeError, ValueError): s = 0.5
    return {"tags": tags, "stability": min((0.0, 0.5, 1.0), key=lambda v: abs(v - s))}

def apply_style(text: str, style: dict | None) -> str:
    """Préfixe les balises du style — sauf si le texte commence déjà par une."""
    t = (text or "").strip()
    st = clamp_style(style)
    if not st["tags"] or _TAG_RX.match(t):
        return t
    return " ".join(st["tags"]) + " " + t
```

- [ ] **Étape 3 : routes**

`GET /voice-tags` (après `/voice-models`) :
```python
@router.get("/voice-tags")
async def voice_tags():
    from app.services import voice_direction as VD, voice_providers as VP
    prov = await asyncio.get_running_loop().run_in_executor(None, VP.resolve_provider)
    return {"groups": VD.V3_TAGS, "experimental": sorted(VD.EXPERIMENTAL), "model": "eleven_v3",
            "providers": {"elevenlabs": prov == "elevenlabs", "voicebox": prov == "voicebox"}}
```
Dans `create_voiceover`, après `lang = …` et avant le nom du fichier :
```python
    from app.services import voice_direction as VD, voice_providers as VP
    notes: list[str] = []
    prov = await loop.run_in_executor(None, VP.resolve_provider)
    style = VD.clamp_style(payload.get("style"))
    text = VD.apply_style(script, style)
    if prov == "elevenlabs" and (model or "") == "eleven_v3":
        bad = VD.unknown_tags(text)
        if bad: notes.append("balises inconnues d'Eleven v3, laissées telles quelles : " + ", ".join(bad))
        v_settings = dict(v_settings or {}, stability=style["stability"]) if style["tags"] else v_settings
    elif VD.find_tags(text):
        text = VD.strip_tags(text)
        notes.append("balises retirées : " + ("Voicebox ne les interprète pas" if prov == "voicebox"
                                              else "seul Eleven v3 les interprète (modèle choisi : " + (model or "défaut") + ")"))
```
puis `voice.generate_long(text=text, …)` au lieu de `text=script`, et la réponse gagne `"notes": notes`.

- [ ] **Étape 4 : la carte Voix off de Son & VFX devient réelle**

Dans `DzSonVfx`, états après `stG6` : `var stV1=x.useState(""),voScript=stV1[0],setVoScript=stV1[1]; var stV2=x.useState([]),voTags=stV2[0],setVoTags=stV2[1]; var stV3=x.useState(null),tagCat=stV3[0],setTagCat=stV3[1]; var stV4=x.useState(""),voBusy=stV4[0],setVoBusy=stV4[1]; var stV5=x.useState(null),voRes=stV5[0],setVoRes=stV5[1];` + `x.useEffect(function(){fetch("/api/voice-tags").then(function(r2){return r2.json()}).then(setTagCat).catch(function(){setTagCat({groups:{},providers:{}})})},[]);`. La `editorCard` gagne, avant `svm-toolrow`, la zone de saisie :
```js
    r.jsxs("div",{className:"svm-vodir",children:[
      r.jsx("textarea",{className:"svm-musicprompt",rows:3,value:voScript,maxLength:5000,
        placeholder:"Texte de la voix off — clique une balise pour la poser en tête ([whispers], [excited]…)",
        onChange:function(e){setVoScript(e.target.value)}}),
      tagCat&&tagCat.providers.elevenlabs?r.jsx("div",{className:"svm-tagpal",children:Object.keys(tagCat.groups).map(function(g){
        return r.jsxs("div",{className:"svm-taggrp",children:[r.jsx("span",{className:"svm-note",style:{marginTop:0},children:g}),
          tagCat.groups[g].map(function(t){var on=voTags.indexOf(t)>=0;
            return r.jsx("button",{className:"svm-minibtn","data-on":on?"":void 0,
              title:tagCat.experimental.indexOf(t)>=0?"expérimental":"Eleven v3",
              onClick:function(){setVoTags(on?voTags.filter(function(x2){return x2!==t}):voTags.concat([t]).slice(-4))},children:t},t)})]},g)})})
      :r.jsx("div",{className:"svm-note",children:tagCat&&tagCat.providers.voicebox?"Voicebox n'interprète pas les balises v3 — elles seraient retirées.":"balises v3 : clé ElevenLabs requise"}),
      r.jsxs("div",{className:"svm-note",title:"ce qui part au modèle",children:["aperçu : ",r.jsx("b",{children:(voTags.join(" ")+" "+voScript).trim()||"—"})]}),
      r.jsx("button",{className:"svm-nbgold","data-off":voBusy||!voScript.trim()?"":void 0,
        onClick:function(){if(voBusy||!voScript.trim())return;setVoBusy("1");
          fetch("/api/audio/voiceover",{method:"POST",headers:{"Content-Type":"application/json"},
            body:JSON.stringify({script:voScript,language:"fr",name:"sonvfx_vo",voice_id:voices&&voices.enabled?selVoice:void 0,
              model:voTags.length?"eleven_v3":void 0,style:{tags:voTags}})})
            .then(function(r2){return r2.json().then(function(d){if(!r2.ok)throw new Error(d.detail||"échec");return d})})
            .then(function(d){setVoBusy("");setVoRes(d);setCur({file:d.filename,dur:0,pos:0,peaks:cur.peaks,pill:"générée",url:d.url});
              fireNote("Voix générée : "+d.filename+((d.notes||[]).length?" — "+d.notes.join(" · "):""))})
            .catch(function(e){setVoBusy("");fireNote("Voix : "+String(e&&e.message||e))})},
        children:voBusy?"synthèse…":"Générer la voix"})]}),
```
CSS (`son-vfx-montage.css`, fin) : `.dzsvm .svm-tagpal{display:flex;flex-direction:column;gap:4px;margin:6px 0} .dzsvm .svm-taggrp{display:flex;flex-wrap:wrap;gap:4px;align-items:center} .dzsvm .svm-vodir{display:grid;gap:6px;margin-bottom:8px}`. Run : `python scripts/refresh_layer.py --layer sonvfx` (+ `reapply_inblock_patches.py --check` égal avant/après).

- [ ] **Étape 5 : vert, commit**

Run : `python tests/test_voice_direction.py` → `=== 10 passed, 0 failed ===`
```
git add backend/app/services/voice_direction.py backend/app/api/routes.py frontend/patches/son-vfx-montage.js frontend/dist/shared/son-vfx-montage.css frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_voice_direction.py
git commit -m 'son-vfx P5 : direction d interpretation par balises Eleven v3' -m 'Palette de balises dans la carte Voix off, aperçu du texte balisé, stabilité snappée ; Voicebox et les modèles non-v3 voient les balises retirées et le disent. Dette nommée : la même palette dans le tiroir Narration du Montage et l onglet Voice Over de la Quick (bundle).' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Lot 2 — différenciant

### Task 8 : D1 — ducking dès la génération (Son & VFX, Quick)

**Files :**
- Modify : `backend/app/services/ffmpeg_service.py:70-160` (`merge(..., ducking=True)`) ; `backend/app/api/routes.py` (`POST /audio/duck`) ; `frontend/patches/son-vfx-montage.js` (`DzSonVfx` : carte « Mix voix + musique »)
- Test : `backend/tests/test_ducking_generation.py`

- [ ] **Étape 1 : banc rouge, MESURÉ**

```python
# backend/tests/test_ducking_generation.py
# -*- coding: utf-8 -*-
"""D1 — le ducking existe hors du Montage : FFmpegMerger.merge (Quick) et
POST /audio/duck (Son & VFX). Preuve par MESURE : le niveau de la musique
pendant la voix est plus bas qu'après la voix ; sans ducking, égal.
Run: python tests/test_ducking_generation.py (depuis backend/)"""
import asyncio, os, pathlib, re, shutil, subprocess, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzduck_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
if not shutil.which("ffmpeg"): print("SKIP: ffmpeg introuvable"); sys.exit(0)
from app.config import settings
from app.services.ffmpeg_service import FFmpegMerger
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
def ff(*a): subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)
def mean_db(p, ss, t):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-ss", str(ss), "-t", str(t), "-i", str(p), "-af", "volumedetect",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.search(r"mean_volume:\s*(-?[\d.]+) dB", err).group(1))
w = pathlib.Path(_tmp)
ff("-f", "lavfi", "-i", "testsrc=duration=6:size=160x120:rate=15", "-pix_fmt", "yuv420p", str(w / "v.mp4"))
ff("-f", "lavfi", "-i", "sine=frequency=300:duration=2", "-c:a", "libmp3lame", str(w / "vo.mp3"))   # voix : 0-2 s
ff("-f", "lavfi", "-i", "sine=frequency=110:duration=6", "-c:a", "libmp3lame", str(w / "bgm.mp3"))
out = FFmpegMerger.merge(w / "v.mp4", w / "vo.mp3", w / "duck.mp4", music_path=w / "bgm.mp3", music_volume_db=-6, ducking=True)
ff("-i", str(out), "-vn", "-af", "highpass=f=80,lowpass=f=150", str(w / "bgm_only.wav"))   # ne garde que la musique (110 Hz)
during, after = mean_db(w / "bgm_only.wav", 0.5, 1.0), mean_db(w / "bgm_only.wav", 3.5, 1.0)
check("MESURÉ : musique ≥ 4 dB plus basse SOUS la voix qu'après", after - during >= 4.0, f"pendant {during} dB, après {after} dB")
out2 = FFmpegMerger.merge(w / "v.mp4", w / "vo.mp3", w / "flat.mp4", music_path=w / "bgm.mp3", music_volume_db=-6, ducking=False)
ff("-i", str(out2), "-vn", "-af", "highpass=f=80,lowpass=f=150", str(w / "flat_only.wav"))
d2, a2 = mean_db(w / "flat_only.wav", 0.5, 1.0), mean_db(w / "flat_only.wav", 3.5, 1.0)
check("sans ducking : écart < 1 dB", abs(a2 - d2) < 1.0, f"{d2} / {a2}")
audio = settings.images_path.parent / "audio"; audio.mkdir(exist_ok=True)
shutil.copy2(w / "vo.mp3", audio / "vo.mp3"); shutil.copy2(w / "bgm.mp3", audio / "bgm.mp3")
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services import sfx_service as S
async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        r = await c.post("/api/audio/duck", json={"voice": "vo.mp3", "music": "bgm.mp3", "music_db": -12, "ducking": {"ratio": 8}})
        d = r.json()
        check("/audio/duck écrit mix_ en Bibliothèque", r.status_code == 200 and d["filename"] == "mix_vo_bgm.mp3" and (audio / d["filename"]).is_file(), r.text[:200])
        dur = S._probe_duration(audio / d["filename"])
        check("durée = celle de la voix (2 s), pas de la musique", abs(dur - 2.0) < 0.3, str(dur))
        check("sidecar : kind mix + parents", S.load_meta()[d["filename"]]["parents"] == ["vo.mp3", "bgm.mp3"])
        r = await c.post("/api/audio/duck", json={"voice": "nope.mp3", "music": "bgm.mp3"}); check("voix absente : 404", r.status_code == 404)
asyncio.run(main())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```
Run : `python tests/test_ducking_generation.py` → `TypeError: merge() got an unexpected keyword argument 'ducking'`

- [ ] **Étape 2 : `FFmpegMerger.merge`**

Signature : `keep_video_audio: bool = False, ducking: bool = True`. Dans la branche `else` (filter_complex), remplacer le bloc `if has_bgm:` … `alabels.append("[abg]")` par :
```python
            if has_bgm:
                inputs += ["-stream_loop", "-1", "-i", str(music_path)]
                if has_vo and ducking:
                    # D1 — la voix pilote le compresseur de la musique : même
                    # chaîne que le Montage (sfx_service.ducking_filter), la
                    # voix mixée reste [avomix], sa copie [avosc] ne sort pas.
                    from app.services import sfx_service
                    fc[-1] = fc[-1].replace("[avo]", "[avo0]")
                    fc.append("[avo0]asplit=2[avosc][avo]")
                    fc.append(f"[{idx}:a]volume={music_volume_db}dB,aresample=async=1,"
                              f"aformat=sample_rates=44100:channel_layouts=stereo[abg0]")
                    fc.append(f"[abg0][avosc]{sfx_service.ducking_filter(True)}[abg]")
                else:
                    fc.append(f"[{idx}:a]volume={music_volume_db}dB,aresample=async=1[abg]")
                alabels.append("[abg]")
                idx += 1
```
Note : la ligne `[avo]` est celle poussée juste avant (`fc.append(f"[{idx}:a]aresample=async=1[avo]")`) — le remplacement `[avo]`→`[avo0]` porte sur cette dernière entrée. Les trois sites d'appel de `pipeline.py` (408-411, 555-561, 650-657) ne changent pas : `ducking=True` est le défaut, la Quick est ducké dès ce commit.

- [ ] **Étape 3 : `POST /audio/duck`** (après `/audio/isolate`)

```python
@router.post("/audio/duck")
async def audio_duck(request: Request):
    """D1 — mix voix + musique ducké, sans timeline. Body {voice, music,
    music_db=-14, ducking?: bool|{ratio,attack_ms,release_ms,threshold}}.
    Durée = celle de la voix (amix duration=first). → mix_<voix>_<musique>.mp3"""
    payload = await request.json()
    from app.services import sfx_service
    v = _audio_dir() / Path(str(payload.get("voice") or "")).name
    m = _audio_dir() / Path(str(payload.get("music") or "")).name
    if not v.is_file(): raise HTTPException(404, f"voix introuvable : {payload.get('voice')}")
    if not m.is_file(): raise HTTPException(404, f"musique introuvable : {payload.get('music')}")
    try: mdb = max(-40.0, min(0.0, float(payload.get("music_db", -14))))
    except (TypeError, ValueError): mdb = -14.0
    duck = sfx_service.parse_ducking(payload.get("ducking", True))
    out = _audio_dir() / f"mix_{v.stem[:24]}_{m.stem[:24]}.mp3"
    i = 2
    while out.exists():
        out = _audio_dir() / f"mix_{v.stem[:24]}_{m.stem[:24]}_{i}.mp3"; i += 1
    fmt = "aresample=async=1,aformat=sample_rates=44100:channel_layouts=stereo"
    music = f"[1:a]{fmt},volume={sfx_service.fnum(10 ** (mdb / 20))}[m]"
    chain = (f"[0:a]{fmt},asplit=2[vsc][vmix];{music};"
             + (f"[m][vsc]{sfx_service.ducking_filter(duck)}[md];" if duck else "[m]anull[md];[vsc]anullsink;")
             + "[vmix][md]amix=inputs=2:duration=first:normalize=0[outa]")
    tmp = out.with_name(out.name + ".part")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-i", str(v), "-stream_loop", "-1", "-i", str(m),
           "-filter_complex", chain, "-map", "[outa]", "-c:a", "libmp3lame", "-b:a", "192k", "-f", "mp3", str(tmp)]
    import subprocess
    r = await asyncio.get_running_loop().run_in_executor(
        None, lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300))
    if r.returncode != 0 or not tmp.is_file():
        tmp.unlink(missing_ok=True); raise HTTPException(502, f"mix impossible : {(r.stderr or '')[-300:]}")
    import os as _os; _os.replace(tmp, out)
    dur = await asyncio.get_running_loop().run_in_executor(None, sfx_service._probe_duration, out)
    sfx_service.record_meta(out.name, {"kind": "mix", "parents": [v.name, m.name], "music_db": mdb,
                                       "created": datetime.now().isoformat(timespec="seconds")})
    await LI.noter([out.name], "sonvfx", kind="audio")
    return {"ok": True, "filename": out.name, "url": f"/api/audio/{out.name}", "dur": round(dur, 2), "usd": 0.0}
```
(`anullsink` absorbe la copie inutile quand le ducking est coupé.) `svxKindOf` dans `sfxstudio.js` : ajouter `if(k==="mix")return "musique";` et `if(k==="stem")return "musique";` pour que mixes et stems tombent dans l'onglet Musique du tiroir.

- [ ] **Étape 4 : la carte Son & VFX** — dans `DzSonVfx`, états `var stM1=x.useState(null),mixVoice=…; var stM2=x.useState(null),mixMusic=…; var stM3=x.useState("moyen"),mixPreset=…; var stM4=x.useState(null),mixRes=…;` ; presets `{leger:{ratio:3,threshold:.08},moyen:{ratio:6,threshold:.05},fort:{ratio:12,threshold:.03}}`. Après une génération de voix (`setVoRes`) ou de musique (`SvmMusic` reçoit `onGenerated:function(item){setMixMusic(item.filename)}` et l'appelle après `setRes(d)`), la carte s'affiche sous la carte active quand `mixVoice&&mixMusic` : deux libellés, trois boutons de preset, « Écouter le mix ducké » → `POST /api/audio/duck` `{voice:mixVoice,music:mixMusic,ducking:preset}` → `playUrl(d.url)` + note « mix posé en Bibliothèque (Musique) ». `voRes` alimente `mixVoice` via `setMixVoice(d.filename)` dans le `.then` de l'étape 4 de T7. Run : `python scripts/refresh_layer.py --layer sonvfx` (+ `--check` du rejeu avant/après).

- [ ] **Étape 5 : vert, commit**

Run : `python tests/test_ducking_generation.py` → `=== 6 passed, 0 failed ===` ; `python tests/test_render_voiceover.py` reste vert (merge avec VO seule = chemin rapide inchangé).
```
git add backend/app/services/ffmpeg_service.py backend/app/api/routes.py frontend/patches/sfxstudio.js frontend/patches/son-vfx-montage.js frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_ducking_generation.py
git commit -m 'son-vfx D1 : ducking des la generation - Quick et carte mix de Son et VFX' -m 'FFmpegMerger.merge duck la musique sous la voix par défaut (mesuré : ≥ 4 dB d écart) avec la chaîne du Montage ; POST /audio/duck rend le mix sans timeline, à la durée de la voix.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 9 : D2a — le matte : BiRefNet vidéo → ProRes 4444 (fal)

**Files :**
- Create : `backend/app/services/matte_service.py`
- Modify : `backend/app/api/routes.py` (`POST /matte`, `GET /matte/{id}`) ; `backend/app/services/montage_service.py:734` (`_resolve_src` : `{matte: name}`)
- Test : `backend/tests/test_matte_service.py`

- [ ] **Étape 1 : relire l'endpoint**

`WebFetch url=https://fal.ai/models/fal-ai/birefnet/v2/video/api prompt="input params and enum values, output fields"` → `video_url`, `model` (six libellés), `video_output_type` avec `"PRORES4444 (.mov)"`, sortie `video.url`. `WebFetch url=https://fal.ai/models/fal-ai/birefnet/v2/video prompt="pricing sentence"` → si la page dit encore « $0 per compute second », la clé `birefnet_video_usd_per_s` reste à 0 et le libellé « à mesurer » reste. **Après le premier tir réel**, lire le montant sur le tableau de bord fal, le diviser par la durée du clip, et l'écrire dans `pricing.DEFAULTS` avec la date.

- [ ] **Étape 2 : banc rouge**

```python
# backend/tests/test_matte_service.py
# -*- coding: utf-8 -*-
"""D2a — registre BiRefNet vidéo, arguments figés (ProRes 4444), travail
suivi en mémoire, fichier .mov écrit sous outputs/mattes, confinement.
Run: python tests/test_matte_service.py (depuis backend/)"""
import asyncio, os, pathlib, shutil, subprocess, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzmatte_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
if not shutil.which("ffmpeg"): print("SKIP: ffmpeg introuvable"); sys.exit(0)
from app.config import settings
from app.services import matte_service as MT
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
w = pathlib.Path(_tmp)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=10",
                "-pix_fmt", "yuv420p", str(w / "clip.mp4")], check=True)
fake_mov = w / "fake.mov"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red@0.5:size=64x64:rate=10:duration=1",
                "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(fake_mov)], check=True)
CALLS = []
async def _up(p): return "http://fal.test/clip.mp4"
async def _sub(endpoint, arguments): CALLS.append((endpoint, arguments)); return {"video": {"url": "http://fal.test/m.mov"}}
async def _dl(url, dest): shutil.copy2(fake_mov, dest)
MT._upload, MT._fal_subscribe, MT._download = _up, _sub, _dl
check("registre : trois modèles, libellés fal exacts", MT.MATTE_MODELS["matting"]["fal"] == "Matting" and MT.MATTE_MODELS["portrait"]["fal"] == "Portrait")
mid = MT.start(w / "clip.mp4", "matting", label="clip")
async def wait():
    for _ in range(50):
        st = MT.status(mid)
        if st["status"] in ("done", "failed"): return st
        await asyncio.sleep(0.05)
st = asyncio.run(wait())
check("travail terminé", st["status"] == "done", str(st))
check("arguments figés : ProRes 4444, refine, modèle", CALLS[0][0] == "fal-ai/birefnet/v2/video" and CALLS[0][1]["video_output_type"] == "PRORES4444 (.mov)"
      and CALLS[0][1]["refine_foreground"] is True and CALLS[0][1]["model"] == "Matting", str(CALLS))
p = MT.matte_path(st["file"])
check("fichier .mov écrit sous outputs/mattes", p.is_file() and p.parent == MT.mattes_dir() and st["file"].endswith(".mov"))
pix = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=pix_fmt", "-of", "csv=p=0", str(p)],
                     capture_output=True, text=True).stdout.strip()
check("alpha présent (yuva444p10le)", pix == "yuva444p10le", pix)
check("statut : note de prix « à mesurer »", "mesurer" in st["usd_note"])
for bad in ("../x.mov", "C:/Windows/win.ini", "x.mp4"):
    try: MT.matte_path(bad); check(f"chemin refusé : {bad}", False)
    except ValueError: check(f"chemin refusé : {bad}", True)
check("inconnu : 404 dict", MT.status("zzz")["status"] == "unknown")
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```
Run : `python tests/test_matte_service.py` → `ModuleNotFoundError: No module named 'app.services.matte_service'`

- [ ] **Étape 3 : le service**

```python
# backend/app/services/matte_service.py
# -*- coding: utf-8 -*-
"""D2a — matte vidéo par BiRefNet v2 (fal-ai/birefnet/v2/video, page /api
relue le 03/09/2026) : le sujet détouré sort en ProRes 4444 (alpha), rangé
sous outputs/mattes/, et le Montage compose les effets ENTRE le fond et lui.
Travaux suivis en mémoire (un matte dure quelques dizaines de secondes, le
panneau interroge tout de suite) — même choix que _SUBS_JOBS."""
from __future__ import annotations
import asyncio, os, re
from pathlib import Path
from uuid import uuid4
import httpx
from loguru import logger
from app.config import settings, SSL_VERIFY

ENDPOINT = "fal-ai/birefnet/v2/video"
MATTE_MODELS = {
    "general": {"label": "Général (léger)", "fal": "General Use (Light)"},
    "matting": {"label": "Matting — cheveux, transparence", "fal": "Matting"},
    "portrait": {"label": "Portrait", "fal": "Portrait"},
}
ARGS_FIXED = {"video_output_type": "PRORES4444 (.mov)", "refine_foreground": True,
              "operating_resolution": "1024x1024", "video_quality": "high"}
USD_NOTE = ("prix fal non affiché (« $0 per compute second » le 03/09) — à mesurer sur le "
            "tableau de bord fal après ce tir, puis à écrire dans pricing.birefnet_video_usd_per_s")
_JOBS: dict[str, dict] = {}
_JOBS_MAX = 40
_SAFE = re.compile(r"^[A-Za-z0-9_-]+\.mov$")

def mattes_dir() -> Path:
    p = settings.outputs_path / "mattes"; p.mkdir(parents=True, exist_ok=True); return p

def matte_path(name: str) -> Path:
    n = str(name or "")
    if not _SAFE.match(n):
        raise ValueError(f"nom de matte refusé : {n[:40]!r}")
    p = (mattes_dir() / n).resolve()
    if p.parent != mattes_dir().resolve():
        raise ValueError("matte hors dossier")
    return p

async def _upload(path: Path) -> str:                       # seam
    import fal_client
    return await fal_client.upload_file_async(str(path))

async def _fal_subscribe(endpoint: str, arguments: dict) -> dict:   # seam
    import fal_client
    return await fal_client.subscribe_async(endpoint, arguments=arguments, with_logs=False)

async def _download(url: str, dest: Path) -> None:          # seam
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=600) as c:
        r = await c.get(url); r.raise_for_status()
        tmp = dest.with_name(dest.name + ".part"); tmp.write_bytes(r.content); os.replace(tmp, dest)

def status(mid: str) -> dict:
    return dict(_JOBS.get(mid) or {"status": "unknown"})

async def _run(mid: str, src: Path, model_key: str):
    j = _JOBS[mid]
    try:
        j.update(status="upload", pct=10)
        url = await _upload(src)
        j.update(status="fal", pct=30)
        args = dict(ARGS_FIXED, video_url=url, model=MATTE_MODELS[model_key]["fal"])
        res = await _fal_subscribe(ENDPOINT, args)
        vurl = ((res or {}).get("video") or {}).get("url")
        if not vurl:
            raise RuntimeError(f"fal.ai: aucune vidéo dans la réponse (clés : {', '.join(map(str, res or {}))})")
        j.update(status="download", pct=80)
        dest = mattes_dir() / f"{j['label']}_{mid[:8]}.mov"
        await _download(vurl, dest)
        j.update(status="done", pct=100, file=dest.name, url=f"/api/matte/file/{dest.name}")
        logger.info(f"matte {mid}: {dest.name} ({dest.stat().st_size // 1024} KB) — {USD_NOTE}")
    except Exception as e:  # noqa: BLE001
        logger.exception(f"matte {mid} failed: {e}")
        j.update(status="failed", error=str(e)[:300])

def start(src: Path, model_key: str = "general", label: str = "clip") -> str:
    if not (settings.FAL_KEY or "").strip():
        raise ValueError("fal.ai: aucune clé configurée (Réglages → clés API).")
    if model_key not in MATTE_MODELS:
        raise ValueError(f"modèle de détourage inconnu : {model_key!r}")
    if not Path(src).is_file():
        raise ValueError("source vidéo introuvable")
    while len(_JOBS) >= _JOBS_MAX:
        _JOBS.pop(next(iter(_JOBS)))
    mid = uuid4().hex
    _JOBS[mid] = {"status": "queued", "pct": 0, "file": None, "error": None,
                  "label": re.sub(r"[^A-Za-z0-9_-]+", "_", label)[:24] or "clip", "usd_note": USD_NOTE}
    asyncio.get_running_loop().create_task(_run(mid, Path(src), model_key))
    return mid
```
Hors boucle asyncio (le banc appelle `start` avant `asyncio.run`) : `start` doit obtenir une boucle — utiliser `asyncio.get_event_loop()` si `get_running_loop()` lève `RuntimeError`, et le banc lance alors `wait()` sur cette même boucle (`loop.run_until_complete(wait())`). Écrire le banc avec `loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)` en tête, `st = loop.run_until_complete(wait())`.

- [ ] **Étape 4 : routes et résolution**

```python
@router.post("/matte")
async def matte_start(request: Request):
    """D2a — Body {job_id, model?: general|matting|portrait}. → {matte_id}."""
    payload = await request.json()
    from app.services import matte_service as MT
    from app.services.montage_service import _resolve_src
    src = await _resolve_src({"job_id": str(payload.get("job_id") or "")})
    if src is None: raise HTTPException(404, "rendu introuvable pour ce job_id")
    try:
        mid = MT.start(src, str(payload.get("model") or "general"), label=src.stem[:16])
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "matte_id": mid, "usd_note": MT.USD_NOTE}

@router.get("/matte/{matte_id}")
async def matte_status(matte_id: str):
    from app.services import matte_service as MT
    st = MT.status(matte_id)
    if st["status"] == "unknown": raise HTTPException(404, "matte inconnu")
    return st

@router.get("/matte/file/{name}")
async def matte_file(name: str):
    from app.services import matte_service as MT
    try: p = MT.matte_path(name)
    except ValueError as e: raise HTTPException(404, str(e))
    if not p.is_file(): raise HTTPException(404, "matte absent")
    return FileResponse(p, media_type="video/quicktime")
```
(Déclarer `/matte/file/{name}` AVANT `/matte/{matte_id}`.) Dans `montage_service._resolve_src`, avant `fp = src.get("file_path")` :
```python
    mt = src.get("matte")
    if mt:
        from app.services import matte_service as MT
        try:
            q = MT.matte_path(str(mt)); return q if q.is_file() else None
        except ValueError:
            return None
```

- [ ] **Étape 5 : vert, commit**

Run : `python tests/test_matte_service.py` → `=== 10 passed, 0 failed ===`
```
git add backend/app/services/matte_service.py backend/app/services/montage_service.py backend/app/api/routes.py backend/tests/test_matte_service.py
git commit -m 'son-vfx D2a : matte video par BiRefNet, ProRes 4444 sous outputs/mattes' -m 'Arguments figés sur la page /api du 03/09 ; le prix n est pas affiché par fal, la note « à mesurer » suit le travail jusqu à l écran.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 10 : D2b — composer les effets entre le fond et le sujet (Montage, aperçu, rack)

**Files :**
- Modify : `backend/app/services/montage_service.py:860-918` (segments V1) et `:1276/1521` (`matte` dans le payload) ; `backend/app/services/effects_preview.py:303-406` (`matte=`) ; `backend/app/api/routes.py:7887` (`/effects/preview` : `matte`) ; `frontend/patches/vfxrack.js` (`vfxPreviewUrl` 380, `VfxStack` rangée « Sujet », `row()` 924 : bascule `behind`) ; `frontend/patches/son-vfx-montage.js` (écouteur `dz-matte`, `renderPayload` après `opacity:c.opacity};`)
- Test : `backend/tests/test_matte_compose.py`

- [ ] **Étape 1 : banc rouge, MESURÉ au pixel**

```python
# backend/tests/test_matte_compose.py
# -*- coding: utf-8 -*-
"""D2b — un effet « derrière » n'atteint pas le sujet ; un effet « devant »
l'atteint. Preuve par lecture de pixels sur un rendu ffmpeg réel : fond bleu
uni, sujet = moitié gauche rouge opaque (ProRes 4444), effet = négatif.
Run: python tests/test_matte_compose.py (depuis backend/)"""
import os, pathlib, shutil, subprocess, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzcomp_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
if not shutil.which("ffmpeg"): print("SKIP: ffmpeg introuvable"); sys.exit(0)
from PIL import Image
from app.services import montage_service as M, matte_service as MT, effects_preview as FXP
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
def ff(*a): subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)
w = pathlib.Path(_tmp); W, H = 64, 64
ff("-f", "lavfi", "-i", f"color=c=0x0000ff:size={W}x{H}:rate=10:duration=1", "-pix_fmt", "yuv420p", str(w / "bg.mp4"))
fr = w / "fr"; fr.mkdir()
for i in range(10):                                    # sujet : moitié gauche rouge opaque, droite transparente
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); im.paste((255, 0, 0, 255), (0, 0, W // 2, H)); im.save(fr / f"{i:03d}.png")
mov = MT.mattes_dir() / "sujet_test.mov"
ff("-framerate", "10", "-i", str(fr / "%03d.png"), "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(mov))
def px(video, x, y):
    out = w / "f.png"; ff("-i", str(video), "-frames:v", "1", "-update", "1", str(out))
    return Image.open(out).convert("RGB").getpixel((x, y))
def render(effects, name):
    v1 = [{"path": w / "bg.mp4", "src_dur": 1.0, "src_in": 0.0, "start": 0.0, "end": 1.0, "transition": "cut",
           "effects": effects, "matte": mov}]
    cmd, _ = M._build_montage_command(v1, [], [], None, w=W, h=H, fps=10, mix_db={"dialogue": -6, "musique": -18, "sfx": -12},
                                      ducking=False, duration_master=False, preview=True, out=w / name)
    subprocess.run(cmd, check=True, capture_output=True); return w / name
o = render([{"type": "invert", "behind": True}], "behind.mp4")
l, r_ = px(o, 8, 32), px(o, 56, 32)
check("derrière : sujet rouge intact, fond inversé (bleu → jaune)", l[0] > 200 and l[2] < 60 and r_[0] > 200 and r_[1] > 200 and r_[2] < 60, f"{l} {r_}")
o = render([{"type": "invert", "behind": False}], "front.mp4")
l, r_ = px(o, 8, 32), px(o, 56, 32)
check("devant : sujet aussi inversé (rouge → cyan)", l[0] < 60 and l[1] > 200 and l[2] > 200, f"{l} {r_}")
o = render([], "none.mp4")
l, r_ = px(o, 8, 32), px(o, 56, 32)
check("sans effet : sujet rouge sur fond bleu", l[0] > 200 and r_[2] > 200, f"{l} {r_}")
v1 = [{"path": w / "bg.mp4", "src_dur": 1.0, "src_in": 0.0, "start": 0.0, "end": 1.0, "transition": "cut", "effects": [{"type": "invert"}]}]
cmd, _ = M._build_montage_command(v1, [], [], None, w=W, h=H, fps=10, mix_db={}, ducking=False, duration_master=False, preview=True, out=w / "h.mp4")
check("sans matte : filtergraph historique (n0pre → cfx0, aucun overlay)", "overlay" not in " ".join(cmd) and "[n0pre]" in " ".join(cmd))
# aperçu : la vignette respecte le matte
Image.new("RGB", (W, H), (0, 0, 255)).save(pathlib.Path(os.environ["IMAGES_FOLDER"]) / "bleu.png")
p = FXP.render_preview("invert", {}, source="image:bleu.png", matte=mov.name, width=W)
l, r_ = Image.open(p).convert("RGB").getpixel((8, 32)), Image.open(p).convert("RGB").getpixel((56, 32))
check("aperçu : sujet intact, fond inversé", l[0] > 180 and r_[2] < 80, f"{l} {r_}")
try: FXP.render_preview("invert", {}, source="image:bleu.png", matte="../evil.mov"); check("matte hostile refusé", False)
except ValueError: check("matte hostile refusé", True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```
Run : `python tests/test_matte_compose.py` → `FAIL  derrière : …` (le matte est ignoré) puis `TypeError: render_preview() got an unexpected keyword argument 'matte'`.

- [ ] **Étape 2 : le Montage compose**

Dans la boucle des entrées (ligne ~868, branche `else` non-gap), après `seg_durs.append(d)` et le `seg_idx.append(idx); idx += 1` qui suit, ajouter :
```python
        if not audio_only and not s.get("gap") and s.get("matte"):
            # D2 — le sujet détouré (ProRes 4444) est une entrée de plus, lue
            # sur la même fenêtre source que le plan ; son index est gardé sur
            # le segment pour la composition ci-dessous.
            if s["src_in"] > 0:
                inputs.extend(["-ss", str(s["src_in"])])
            inputs.extend(["-t", str(d_src), "-i", str(s["matte"])])
            s["_midx"] = idx
            idx += 1
```
(`d_src` est celui calculé pour le segment ; hors branche `spd`, `d_src = d`.) Dans la boucle des `parts` (ligne ~896), remplacer le bloc `reff = s.get("effects")` … `else: parts.append(...)` par :
```python
            reff = s.get("effects") or []
            midx = s.get("_midx")
            ctx = {"w": w, "h": h, "dur": seg_durs[k], "fps": fps}
            if midx is None:
                if reff:
                    parts.append(f"[{seg_idx[k]}:v]{chain}[n{k}pre]")
                    parts += _fx.build_chain(reff, f"n{k}pre", f"n{k}", f"cfx{k}", ctx)
                else:
                    parts.append(f"[{seg_idx[k]}:v]{chain}[n{k}]")
                continue
            # D2 — fond → effets « derrière » → sujet par-dessus → effets « devant ».
            # `behind` absent = derrière (c'est la raison d'être du matte).
            behind = [e for e in reff if e.get("behind", True)]
            front = [e for e in reff if not e.get("behind", True)]
            parts.append(f"[{seg_idx[k]}:v]{chain}[n{k}pre]")
            cur_lbl = f"n{k}pre"
            if behind:
                parts += _fx.build_chain(behind, cur_lbl, f"n{k}bg", f"cfx{k}b", ctx)
                cur_lbl = f"n{k}bg"
            parts.append(f"[{midx}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
                         f"setsar=1,fps={fps},format=yuva420p,setpts=PTS-STARTPTS[m{k}]")
            parts.append(f"[{cur_lbl}][m{k}]overlay=eof_action=pass:format=auto,format=yuv420p[n{k}ov]")
            cur_lbl = f"n{k}ov"
            if front:
                parts += _fx.build_chain(front, cur_lbl, f"n{k}", f"cfx{k}f", ctx)
            else:
                parts.append(f"[{cur_lbl}]null[n{k}]")
```
Dans `montage_render` (~1400-1446) et `montage_measure` (~1570-1610), là où chaque clip V1 est résolu, ajouter `"matte": await _resolve_src({"matte": c.get("matte")}) if c.get("matte") else None` à côté de `"effects"`.

- [ ] **Étape 3 : l'aperçu**

`effects_preview.render_preview(effect_type, raw_params, *, source=None, t=T_DEFAULT, width=W_DEFAULT, job_video=None, matte=None)`. Avant le calcul de `key` :
```python
    matte_png = None
    if matte:
        from app.services import matte_service as MT
        mp = MT.matte_path(str(matte))          # ValueError si hostile
        if not mp.is_file():
            raise ValueError("matte absent")
        slug = f"m{hashlib.sha1(mp.name.encode()).hexdigest()[:10]}"
        matte_png = cache_dir() / f"{slug}_{t:.2f}.png"
        if not matte_png.is_file():
            subprocess.run([ffmpeg_bin(), "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(mp),
                            "-frames:v", "1", "-pix_fmt", "rgba", "-update", "1", str(matte_png)],
                           check=True, timeout=60)
        sig += f":matte:{mp.name}:{int(mp.stat().st_mtime)}"
```
Le graphe devient, quand `matte_png` : `[0:v]scale…[fxin]` + chain + `[1:v]scale={w}:{h}[mt]` + `[fxout][mt]overlay=format=auto,format=yuv420p[fxjpg]`, avec `-i matte_png` ajouté après `-i still` dans `cmd` (et `-loop 1 -framerate 25 -t …` devant lui aussi). Route `/effects/preview` : `matte = q.pop("matte", "") or None` passé à `render_preview`. Sécurité : le nom passe par `matte_path` (regex `[A-Za-z0-9_-]+\.mov`, dossier confiné).

- [ ] **Étape 4 : le rack et le Montage**

`vfxrack.js` — `vfxPreviewUrl` : après `if(so)q.push("source="+…)`, `if(clip&&clip.matte)q.push("matte="+encodeURIComponent(clip.matte));`. Dans `VfxStack`, en tête du rendu de la pile (avant la liste des `row(f,i)`), la rangée « Sujet » :
```js
  var matteBusy=x.useState("")[0]; /* état local via ref, cf. ci-dessous */
  function matteRow(){
    var c=props.clip;if(!c||!c.src||!c.src.job_id)return null;
    function go(){
      if(VFX_MATTE.busy)return;VFX_MATTE.busy=!0;emitMatte(null);
      vfxJson("/api/matte",{method:"POST",body:{job_id:c.src.job_id,model:VFX_MATTE.model}}).then(function(d){
        (function poll(){vfxJson("/api/matte/"+d.matte_id).then(function(st){
          if(st.status==="done"){VFX_MATTE.busy=!1;emitMatte(st.file)}
          else if(st.status==="failed"){VFX_MATTE.busy=!1;alert("Détourage : "+st.error)}
          else setTimeout(poll,1200)})})()}).catch(function(e){VFX_MATTE.busy=!1;alert("Détourage : "+e.message)})}
    function emitMatte(name){window.dispatchEvent(new CustomEvent("dz-matte",{detail:{id:c.id,matte:name}}))}
    return r.jsxs("div",{className:"vfx-matte",children:[
      r.jsx("span",{className:"vfx-mlbl",children:c.matte?"Sujet détouré : "+c.matte:"Sujet non détouré"}),
      r.jsxs("select",{className:"vfx-sel",defaultValue:VFX_MATTE.model,onChange:function(e){VFX_MATTE.model=e.target.value},
        children:[["general","Général"],["matting","Matting"],["portrait","Portrait"]].map(function(o){return r.jsx("option",{value:o[0],children:o[1]},o[0])})}),
      r.jsx("button",{className:"vfx-btn",onClick:go,title:"BiRefNet vidéo via fal — prix non affiché par fal, à lire sur le tableau de bord après le tir",
        children:c.matte?"Redétourer":"Détourer (fal)"}),
      c.matte?r.jsx("button",{className:"vfx-btn",onClick:function(){emitMatte(null)},children:"retirer"}):null]})}
```
avec, au niveau module, `var VFX_MATTE={busy:!1,model:"general"};` et `vfxJson` étendu pour accepter `{method,body}` (POST JSON, même garde Content-Type). Dans `row(f,i)`, quand `props.clip&&props.clip.matte`, une bascule `r.jsx("button",{className:"vfx-tog","data-on":f.behind!==!1?"":void 0,title:"derrière le sujet / devant",onClick:function(){patchAt(i,{behind:f.behind===!1},!0)},children:f.behind!==!1?"derrière":"devant"})`. CSS (`vfxrack.css`) : `.vfx-matte{display:flex;gap:6px;align-items:center;flex-wrap:wrap;padding:6px 0;border-bottom:1px solid var(--stroke,#2a2930)} .vfx-mlbl{font-size:11.5px;opacity:.85}`.

`son-vfx-montage.js` (Montage) — après le `useEffect` des favoris/tiroir (zone ~1406), un écouteur :
```js
  x.useEffect(function(){
    function onMatte(ev){var d=ev.detail||{};
      pushHistory();
      setClips(clipsRef.current.map(function(k){return k.id===d.id?Object.assign({},k,{matte:d.matte||void 0}):k}));
      setDirty(!0);fireNote(d.matte?"Sujet détouré posé — les effets se composent derrière lui.":"Sujet retiré.")}
    window.addEventListener("dz-matte",onMatte);return function(){window.removeEventListener("dz-matte",onMatte)}},[]);
```
et dans `renderPayload`, juste après la ligne `opacity:c.opacity};` : `if(c.tr==="v1"&&c.matte)o.matte=c.matte;`. **Ne pas toucher** à la ligne `effects:` (ancre V9). Run : `python scripts/refresh_layer.py --layer vfxrack` puis `--layer sonvfx` (+ `reapply_inblock_patches.py --check` égal avant/après).

- [ ] **Étape 5 : vert, commit**

Run : `python tests/test_matte_compose.py` → `=== 6 passed, 0 failed ===` ; `python tests/test_montage_effects.py` et `python -m pytest tests/test_effects_timing.py -q` verts.
```
git add backend/app/services/montage_service.py backend/app/services/effects_preview.py backend/app/api/routes.py frontend/patches/vfxrack.js frontend/dist/shared/vfxrack.css frontend/patches/son-vfx-montage.js frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_matte_compose.py
git commit -m 'son-vfx D2b : les effets se composent entre le fond et le sujet detoure' -m 'Mesuré au pixel : un négatif « derrière » laisse le sujet rouge intact et inverse le fond ; sans matte le filtergraph est celui d avant. La vignette du rack respecte le matte.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 11 : D3a — la porte CLAP : mesurer les deux voies, trancher, et le dire

**Files :**
- Create : `backend/app/services/sound_search.py`
- Modify : `backend/app/config.py:82` (après `VOICEBOX_URL`), `backend/app/api/routes.py:3501` (`_ALLOWED_ENV_KEYS`)
- Test : `backend/tests/test_sound_search_gate.py`

Cette tâche n'indexe rien et ne cherche rien. Elle pose la PORTE : d'où viennent
les vecteurs, ce qui se passe quand rien n'est là, et la preuve chiffrée que le
backend stdlib peut faire le reste. La mesure d'abord, la décision ensuite,
l'index à T12.

- [ ] **Étape 1 : mesurer les deux voies**

Trois lectures, dans cet ordre, et l'on écrit le résultat dans la table de
décision de l'étape 3 (le docstring du module) :

1. `WebFetch url=https://huggingface.co/api/models/laion/clap-htsat-unfused prompt="List inference_provider_mapping entries, pipeline_tag, library_name, and the projection dimension if stated"` — le 03/09/2026 : `pipeline_tag: feature-extraction`, `library_name: transformers`, **aucun `inference_provider_mapping`** → pas de serverless gratuit ; un Inference Endpoint dédié est facturé à l'heure de machine allumée.
2. `WebFetch url=https://fal.ai/models?keywords=clap prompt="Is there any CLAP or audio-text embedding model listed?"` — le 03/09/2026 : aucun. fal ne sert pas d'embeddings audio-texte.
3. La mesure locale, celle qui tranche vraiment. Run :
```
python -c "import pathlib,os,sys;d=pathlib.Path(os.environ.get('LOCALAPPDATA',''),'DeepotusVideoGen','data','audio');print(len([p for p in d.glob('*') if p.suffix.lower() in ('.mp3','.wav','.m4a','.ogg','.flac','.opus')]) if d.is_dir() else 'dossier audio absent')"
```
Expected : un entier de l'ordre de 600 (606 SFX CC0 + les générations). C'est la
taille du corpus : elle décide si un produit scalaire en Python pur suffit.
L'étape 2 la mesure pour de bon sur 606 vecteurs synthétiques.

- [ ] **Étape 2 : banc rouge**

```python
# backend/tests/test_sound_search_gate.py
# -*- coding: utf-8 -*-
"""D3a — la porte : détection du service d'embeddings (patron Voicebox),
repli PROPRE quand il est absent, index compact (array + base64, stdlib) et
cosinus en Python pur MESURÉ sur 606 vecteurs de 512.
Run: python tests/test_sound_search_gate.py (depuis backend/)"""
import os, random, sys, tempfile, time
_tmp = tempfile.mkdtemp(prefix="dzclap_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["IMAGES_FOLDER"] = os.path.join(_tmp, "images"); os.makedirs(os.environ["IMAGES_FOLDER"])
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
random.seed(4)
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
from app.config import settings
from app.services import sound_search as SS

# ── 1. la porte fermée : personne, et rien ne casse ────────────────────────
SS._reach = lambda url, timeout=2.0: False
SS._reach_cache.update(t=0.0, ok=False)
settings.CLAP_REMOTE_URL = ""
check("aucun service : resolve_embedder rend '' et ne lève pas", SS.resolve_embedder() == "")
st = SS.status()
check("statut fermé : ready False, raison nommant les DEUX voies",
      st["ready"] is False and "Clapbox" in st["hint"] and "CLAP_REMOTE_URL" in st["hint"], str(st))
# ── 2. la porte ouverte par le service local ───────────────────────────────
SS._reach = lambda url, timeout=2.0: url == SS.clapbox_url()
SS._reach_cache.update(t=0.0, ok=False)
check("clapbox joignable : voie locale préférée", SS.resolve_embedder() == "clapbox")
# ── 3. la porte ouverte par l'endpoint distant seul ────────────────────────
SS._reach = lambda url, timeout=2.0: False
SS._reach_cache.update(t=0.0, ok=False)
settings.CLAP_REMOTE_URL = "https://clap.test/v1"
check("distant seul : voie remote", SS.resolve_embedder() == "remote")
check("statut ouvert : ready True et provider dit", SS.status()["ready"] is True and SS.status()["provider"] == "remote")
settings.CLAP_REMOTE_URL = ""
# ── 4. l'index : aller-retour exact, dimension gardée ──────────────────────
v = [random.uniform(-1, 1) for _ in range(512)]
ix = SS.Index(dim=512, model="laion/clap-htsat-unfused", provider="clapbox")
ix.put("boom.wav", v, sig="1:2")
check("normalisé à l'écriture (norme 1)", abs(SS.norm(ix.get("boom.wav")) - 1.0) < 1e-5, str(SS.norm(ix.get("boom.wav"))))
ix.save()
ix2 = SS.Index.load()
check("relu à l'identique (array 'f' + base64)",
      max(abs(a - b) for a, b in zip(ix.get("boom.wav"), ix2.get("boom.wav"))) < 1e-6)
check("métadonnées relues : dim, modèle, provider, signature",
      (ix2.dim, ix2.model, ix2.provider, ix2.sig("boom.wav")) == (512, "laion/clap-htsat-unfused", "clapbox", "1:2"))
try: ix.put("x.wav", v[:256], sig=""); check("dimension étrangère refusée", False)
except ValueError: check("dimension étrangère refusée", True)
try: ix.put("z.wav", [0.0] * 512, sig=""); check("vecteur nul refusé", False)
except ValueError: check("vecteur nul refusé", True)
# ── 5. LA MESURE : 606 vecteurs, un chargement, une requête ────────────────
big = SS.Index(dim=512, model="m", provider="clapbox")
for i in range(606):
    big.put(f"s{i}.wav", [random.uniform(-1, 1) for _ in range(512)], sig="0:0")
big.save()
t0 = time.perf_counter(); big2 = SS.Index.load(); t_load = time.perf_counter() - t0
q = [random.uniform(-1, 1) for _ in range(512)]
t0 = time.perf_counter(); top = big2.nearest(q, 8); t_q = time.perf_counter() - t0
check(f"MESURÉ : index de 606 vecteurs relu en {t_load * 1000:.0f} ms (budget 1500)", t_load < 1.5)
check(f"MESURÉ : une requête en {t_q * 1000:.1f} ms (budget 60) SANS numpy", t_q < 0.06)
check("8 voisins, score décroissant", len(top) == 8 and all(top[i][1] >= top[i + 1][1] for i in range(7)))
check("un vecteur est son propre plus proche voisin",
      big2.nearest(big2.get("s42.wav"), 1)[0][0] == "s42.wav")
check("exclude retire le demandeur", big2.nearest(big2.get("s42.wav"), 1, exclude="s42.wav")[0][0] != "s42.wav")
check("index d'une autre dimension : rejeté au chargement, pas planté",
      SS.Index.load(dim=384).count() == 0)
# ── 6. la décision est DANS le module, datée ───────────────────────────────
check("table de décision datée dans le docstring", "03/09/2026" in SS.__doc__ and "IMPOSSIBLE" in SS.__doc__)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```
Run : `python tests/test_sound_search_gate.py`
Expected : `ModuleNotFoundError: No module named 'app.services.sound_search'`

- [ ] **Étape 3 : le module, et la table de décision qu'il porte**

```python
# backend/app/services/sound_search.py
# -*- coding: utf-8 -*-
"""D3 — recherche de sons par DESCRIPTION et par SIMILARITÉ (index CLAP).

Le backend ne fait JAMAIS tourner le modèle : le python embarqué est stdlib +
Pillow, sans numpy ni torch (mémoire du 02/09/2026). Il ne garde que des
VECTEURS et fait des produits scalaires — mesuré le 03/09 dans
test_sound_search_gate : 606 × 512 en Python pur, une requête sous 60 ms,
index relu sous 1,5 s. C'est tenable ; le modèle, non.

Table de décision (mesures du 03/09/2026, ne pas la refaire de mémoire) :

| Voie                        | Coût            | Exige                     | Verdict   |
|-----------------------------|-----------------|---------------------------|-----------|
| modèle DANS le backend      | 0 $             | torch + numpy embarqués   | IMPOSSIBLE |
| service local « Clapbox »   | 0 $             | un processus Python à part | RETENUE (défaut) |
| endpoint distant (HF dédié) | à l'heure de machine allumée — la fiche `laion/clap-htsat-unfused` n'a AUCUN `inference_provider_mapping` le 03/09, donc pas de serverless ; fal ne sert pas d'embeddings audio-texte | une URL + une clé | POSSIBLE, même façade |

Les deux voies ouvertes passent par le même contrat HTTP (le nôtre) :
    GET  /health          → {"ok": true, "model": "...", "dim": 512}
    POST /embed/text      {"texts": ["porte qui grince"]}  → {"dim","model","vectors":[[…]]}
    POST /embed/audio     multipart `files`                → {"dim","model","vectors":[[…]]}
L'implémentation de référence du service local est dans `tools/clapbox/`
(hors dépôt d'exécution : son propre environnement, ses propres poids).

Absence = repli PROPRE, jamais une erreur : `resolve_embedder()` rend "" et le
tiroir Sons affiche la raison. Patron repris de `voice_providers.py`
(détection cachée, provider résolu, `available()`).
"""
from __future__ import annotations
import base64, json, os
from array import array
from operator import mul
from pathlib import Path
import httpx
from loguru import logger
from app.config import settings

CLAPBOX_DEFAULT_URL = "http://127.0.0.1:17494"
INDEX_NAME = "_clap_index.json"
DEFAULT_DIM = 512          # fiche laion/clap-htsat-unfused ; /health fait foi
BYTEORDER = "little"       # array('f') est natif : un index d'une autre machine est rejeté


def clapbox_url() -> str:
    return (getattr(settings, "CLAPBOX_URL", "") or "").strip().rstrip("/") or CLAPBOX_DEFAULT_URL


def remote_url() -> str:
    return (getattr(settings, "CLAP_REMOTE_URL", "") or "").strip().rstrip("/")


def _reach(url: str, timeout: float = 2.0) -> bool:      # seam (le banc le remplace)
    try:
        return httpx.get(url + "/health", timeout=timeout).status_code == 200
    except Exception:
        return False


_reach_cache = {"t": 0.0, "ok": False}


def clapbox_reachable(timeout: float = 2.0, ttl: float = 5.0) -> bool:
    """Comme voicebox_reachable : un ping au plus toutes les `ttl` secondes —
    le tiroir Sons interroge le statut à chaque ouverture."""
    import time
    now = time.monotonic()
    if ttl > 0 and now - _reach_cache["t"] < ttl:
        return _reach_cache["ok"]
    ok = _reach(clapbox_url(), timeout)
    _reach_cache.update(t=now, ok=ok)
    return ok


def resolve_embedder() -> str:
    """« clapbox » | « remote » | «  » (aucun). Le local d'abord : gratuit."""
    if clapbox_reachable():
        return "clapbox"
    if remote_url():
        return "remote"
    return ""


def embedder_url(provider: str | None = None) -> str:
    p = provider or resolve_embedder()
    return clapbox_url() if p == "clapbox" else remote_url()


def status() -> dict:
    """Ce que le tiroir Sons affiche quand la recherche par description est
    demandée : prête ou non, et POURQUOI non."""
    prov = resolve_embedder()
    ix = Index.load()
    return {"ready": bool(prov), "provider": prov, "model": ix.model, "dim": ix.dim,
            "indexed": ix.count(),
            "hint": "" if prov else
                    ("Recherche par description indisponible : lance le service local Clapbox "
                     f"({clapbox_url()}, voir tools/clapbox/) ou renseigne CLAP_REMOTE_URL "
                     "dans Réglages → Clés.")}


def available() -> list[dict]:
    return [{"id": "clapbox", "label": "Clapbox (local, gratuit)", "ready": clapbox_reachable()},
            {"id": "remote", "label": "Endpoint CLAP distant", "ready": bool(remote_url())}]


# ───────────────────────────── vecteurs, en stdlib ──────────────────────────

def norm(v) -> float:
    return sum(x * x for x in v) ** 0.5


def unit(v, dim: int) -> list[float]:
    if len(v) != dim:
        raise ValueError(f"vecteur de dimension {len(v)}, attendu {dim}")
    n = norm(v)
    if not n or n != n:                      # 0 ou NaN
        raise ValueError("vecteur nul ou non fini — rien à comparer")
    return [float(x) / n for x in v]


def _enc(v: list[float]) -> str:
    return base64.b64encode(array("f", v).tobytes()).decode("ascii")


def _dec(s: str, dim: int) -> list[float]:
    a = array("f"); a.frombytes(base64.b64decode(s))
    if len(a) != dim:
        raise ValueError(f"vecteur encodé de dimension {len(a)}, attendu {dim}")
    return list(a)


class Index:
    """L'index des sons : un vecteur unitaire par fichier, plus la SIGNATURE
    du fichier au moment du calcul (« mtime:taille ») pour ne réindexer que ce
    qui a bougé. Format : un JSON, des vecteurs en base64 d'array('f') —
    1,6 Mo pour 606 sons, relu en une passe, sans dépendance."""

    def __init__(self, dim: int = DEFAULT_DIM, model: str = "", provider: str = ""):
        self.dim, self.model, self.provider = int(dim), model, provider
        self._v: dict[str, list[float]] = {}
        self._s: dict[str, str] = {}

    # — chemin —
    @staticmethod
    def path() -> Path:
        from app.services import sfx_service
        return sfx_service._audio_dir() / INDEX_NAME

    # — écriture —
    def put(self, name: str, vec, sig: str = "") -> None:
        self._v[str(name)] = unit(vec, self.dim)
        self._s[str(name)] = str(sig)

    def drop(self, name: str) -> None:
        self._v.pop(str(name), None); self._s.pop(str(name), None)

    def get(self, name: str) -> list[float] | None:
        return self._v.get(str(name))

    def sig(self, name: str) -> str:
        return self._s.get(str(name), "")

    def count(self) -> int:
        return len(self._v)

    def names(self) -> list[str]:
        return list(self._v)

    def save(self) -> Path:
        p = self.path()
        doc = {"dim": self.dim, "model": self.model, "provider": self.provider,
               "byteorder": BYTEORDER,
               "items": {n: {"v": _enc(self._v[n]), "sig": self._s.get(n, "")} for n in self._v}}
        tmp = p.with_name(p.name + ".part")
        tmp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)
        return p

    @classmethod
    def load(cls, dim: int | None = None) -> "Index":
        """Un index absent, illisible, d'une autre dimension ou d'un autre
        boutisme rend un index VIDE — jamais une exception : la recherche se
        contente alors de dire qu'elle n'a rien."""
        p = cls.path()
        if not p.is_file():
            return cls(dim or DEFAULT_DIM)
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            ix = cls(int(d.get("dim") or DEFAULT_DIM), d.get("model") or "", d.get("provider") or "")
            if d.get("byteorder") not in (None, BYTEORDER):
                logger.warning("index CLAP d'un autre boutisme — ignoré")
                return cls(dim or DEFAULT_DIM)
            if dim is not None and ix.dim != int(dim):
                logger.warning(f"index CLAP en dim {ix.dim}, attendu {dim} — ignoré")
                return cls(int(dim))
            for n, e in (d.get("items") or {}).items():
                try:
                    ix._v[n] = _dec(e["v"], ix.dim); ix._s[n] = e.get("sig", "")
                except Exception:
                    continue
            return ix
        except Exception as e:                        # noqa: BLE001
            logger.warning(f"index CLAP illisible ({e}) — reparti de zéro")
            return cls(dim or DEFAULT_DIM)

    # — lecture —
    def nearest(self, q, k: int = 8, exclude: str | None = None) -> list[tuple[str, float]]:
        """Cosinus : tout est unitaire, donc un produit scalaire suffit.
        `map(mul, …)` plutôt qu'une boucle : mesuré 3× plus rapide, et c'est
        ce qui tient le budget de 60 ms sur 606 × 512 sans numpy."""
        qn = unit(q, self.dim)
        out = [(n, sum(map(mul, qn, v))) for n, v in self._v.items() if n != exclude]
        out.sort(key=lambda t: -t[1])
        return out[:max(1, int(k))]
```

Dans `app/config.py`, après `VOICEBOX_URL` :
```python
    # Clapbox (optional, D3 03/09/2026) — service local d'embeddings CLAP
    # (texte ↔ audio) ; vide = http://127.0.0.1:17494. Voir tools/clapbox/.
    CLAPBOX_URL: str = ""
    # Repli distant : une URL qui parle le MÊME contrat (/health, /embed/text,
    # /embed/audio). Facturé par l'hébergeur, pas par nous.
    CLAP_REMOTE_URL: str = ""
    CLAP_REMOTE_KEY: str = ""
```
Dans `_ALLOWED_ENV_KEYS` (routes.py:3501), après `"OLLAMA_URL", "OLLAMA_MODEL",` :
```python
    "VOICEBOX_URL", "CLAPBOX_URL", "CLAP_REMOTE_URL", "CLAP_REMOTE_KEY",
```
(`VOICEBOX_URL` y entre au passage : il manquait, et Réglages ne pouvait donc
pas le régler — dette du 11/07 fermée en une ligne, à dire dans le commit.)

- [ ] **Étape 4 : vert, commit**

Run : `python tests/test_sound_search_gate.py` → `=== 17 passed, 0 failed ===`.
Lire les deux lignes `MESURÉ :` de la sortie et **les recopier dans le corps du
commit** — c'est la mesure qui autorise la suite.
```
git add backend/app/services/sound_search.py backend/app/config.py backend/app/api/routes.py backend/tests/test_sound_search_gate.py
git commit -m 'son-vfx D3a : la porte CLAP - service local ou endpoint distant, cosinus en Python pur' -m 'Mesuré le 03/09 : la fiche laion/clap-htsat-unfused n a aucun fournisseur serverless et fal ne sert pas d embeddings audio-texte ; le modèle ne peut pas tourner dans le python embarqué. Le backend ne garde que des vecteurs — 606 × 512 relus en <1,5 s, une requête en <60 ms sans numpy. Absence de service = repli propre avec la raison affichée. VOICEBOX_URL entre enfin dans les clés réglables.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 12 : D3b — indexer les sons, chercher par description, trouver les voisins

**Files :**
- Create : `tools/clapbox/server.py`, `tools/clapbox/requirements.txt`, `tools/clapbox/README.md`
- Modify : `backend/app/services/sound_search.py` (seams d'embedding, `reindex`, `search`, `similar`) ; `backend/app/api/routes.py` (quatre routes, après `/audio/isolate`)
- Test : `backend/tests/test_sound_search_index.py`

- [ ] **Étape 1 : banc rouge — un VRAI serveur HTTP stub, pas un monkeypatch**

Le contrat de Clapbox est le nôtre : le banc le vérifie en parlant HTTP pour de
bon (`http.server` dans un thread), pas en remplaçant la fonction qui parle.

```python
# backend/tests/test_sound_search_index.py
# -*- coding: utf-8 -*-
"""D3b — indexation et recherche : le client parle le contrat Clapbox à un
VRAI serveur HTTP stub, l'index sur disque est relu (banc-miroir : on lit le
fichier, pas le code), la recherche ordonne, la similarité s'exclut, la
signature évite de repayer, un fichier effacé quitte l'index.
Run: python tests/test_sound_search_index.py (depuis backend/)"""
import json, os, pathlib, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
_tmp = tempfile.mkdtemp(prefix="dzclapix_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
import asyncio
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

# ── le stub : trois vecteurs orthogonaux, un par « son », et un vecteur texte
#    qui pointe vers l'un d'eux. Pas de modèle : de la géométrie qui se lit.
DIM = 4
AXES = {"porte.wav": [1, 0, 0, 0], "pluie.wav": [0, 1, 0, 0], "boom.wav": [0, 0, 1, 0]}
SEEN = {"text": [], "audio": []}
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, obj):
        b = json.dumps(obj).encode(); self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == "/health": self._send({"ok": True, "model": "stub-clap", "dim": DIM})
        else: self.send_response(404); self.end_headers()
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if self.path == "/embed/text":
            txt = json.loads(body)["texts"]
            SEEN["text"] += txt
            v = [[1, 0, 0, 0] if "grince" in t else [0, 0, 0, 1] for t in txt]
            self._send({"dim": DIM, "model": "stub-clap", "vectors": v})
        elif self.path == "/embed/audio":
            # multipart : on ne parse que les noms de fichiers déposés
            names = [p.split(b'filename="', 1)[1].split(b'"', 1)[0].decode()
                     for p in body.split(b"--") if b'filename="' in p]
            SEEN["audio"] += names
            self._send({"dim": DIM, "model": "stub-clap",
                        "vectors": [AXES.get(n, [0, 0, 0, 1]) for n in names]})
        else: self.send_response(404); self.end_headers()
srv = HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
from app.config import settings
settings.CLAPBOX_URL = f"http://127.0.0.1:{srv.server_port}"
from app.services import sound_search as SS, sfx_service as S
SS._reach_cache.update(t=0.0, ok=False)
check("le stub est vu comme Clapbox", SS.resolve_embedder() == "clapbox")

audio = settings.images_path.parent / "audio"; audio.mkdir(exist_ok=True)
for n in AXES: (audio / n).write_bytes(b"RIFF" + n.encode() + b"\0" * 200)
r = asyncio.run(SS.reindex())
check("trois sons indexés, dimension prise du service", r["indexed"] == 3 and r["dim"] == DIM, str(r))
# banc-miroir : on relit le FICHIER, pas l'objet qui vient d'écrire
doc = json.loads((audio / "_clap_index.json").read_text(encoding="utf-8"))
check("le fichier d'index porte dim, modèle, provider et trois items",
      doc["dim"] == DIM and doc["model"] == "stub-clap" and doc["provider"] == "clapbox"
      and set(doc["items"]) == set(AXES), str(doc)[:200])
check("chaque item porte sa signature mtime:taille",
      all(":" in doc["items"][n]["sig"] for n in AXES), str({n: doc["items"][n]["sig"] for n in AXES}))
r2 = asyncio.run(SS.reindex())
check("rien n'a bougé : 0 réindexé, 0 appel audio de plus",
      r2["indexed"] == 0 and r2["skipped"] == 3 and len(SEEN["audio"]) == 3, str(r2) + str(SEEN["audio"]))
res = asyncio.run(SS.search("une porte qui grince", k=2))
check("recherche par description : porte.wav en tête, score ≈ 1",
      res[0]["name"] == "porte.wav" and res[0]["score"] > 0.99 and len(res) == 2, str(res))
check("le texte est parti tel quel au service", SEEN["text"][-1] == "une porte qui grince", str(SEEN["text"]))
sim = asyncio.run(SS.similar("porte.wav", k=2))
check("similarité : le demandeur est EXCLU", all(x["name"] != "porte.wav" for x in sim) and len(sim) == 2, str(sim))
(audio / "pluie.wav").unlink()
r3 = asyncio.run(SS.reindex())
check("fichier effacé : retiré de l'index et dit", r3["dropped"] == ["pluie.wav"] and SS.Index.load().count() == 2, str(r3))
check("un son absent de l'index : similar rend une liste vide, pas une erreur",
      asyncio.run(SS.similar("pluie.wav", k=3)) == [])
SS._reach = lambda url, timeout=2.0: False
SS._reach_cache.update(t=0.0, ok=False); settings.CLAP_REMOTE_URL = ""
try: asyncio.run(SS.search("porte", k=2)); check("service coupé : refus explicite", False)
except SS.SearchUnavailable as e: check("service coupé : refus explicite nommant Clapbox", "Clapbox" in str(e), str(e))
check("service coupé : similar reste servi depuis l'index (0 $)",
      [x["name"] for x in asyncio.run(SS.similar("porte.wav", k=1))] == ["boom.wav"])
from httpx import AsyncClient, ASGITransport
from app.main import app
async def routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        d = (await c.get("/api/audio/search/status")).json()
        check("GET /audio/search/status : indisponible, raison, compte", d["ready"] is False and d["indexed"] == 2 and "Clapbox" in d["hint"], str(d))
        d = (await c.get("/api/audio/similar/porte.wav?k=1")).json()
        check("GET /audio/similar : servi sans service", d["items"][0]["name"] == "boom.wav", str(d))
        r4 = await c.get("/api/audio/search", params={"q": "porte"})
        check("GET /audio/search sans service : 503 lisible", r4.status_code == 503 and "Clapbox" in r4.json()["detail"], r4.text[:160])
        r5 = await c.get("/api/audio/similar/..%2Fevil.mp3")
        check("similar : traversée refusée", r5.status_code in (400, 404), str(r5.status_code))
asyncio.run(routes())
srv.shutdown()
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```
Run : `python tests/test_sound_search_index.py`
Expected : `AttributeError: module 'app.services.sound_search' has no attribute 'reindex'`

- [ ] **Étape 2 : les seams d'embedding, `reindex`, `search`, `similar`**

À la fin de `sound_search.py` :
```python
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".opus"}
BATCH_AUDIO = 8            # multipart raisonnable pour un service local
MAX_TEXT = 400


class SearchUnavailable(RuntimeError):
    """Ni Clapbox ni endpoint distant : la recherche par description ne peut
    pas avoir lieu. La similarité, elle, se sert de l'index déjà écrit."""


def _headers() -> dict:
    key = (getattr(settings, "CLAP_REMOTE_KEY", "") or "").strip()
    return {"Authorization": f"Bearer {key}"} if key and resolve_embedder() == "remote" else {}


async def _post(path: str, **kw) -> dict:
    prov = resolve_embedder()
    if not prov:
        raise SearchUnavailable(status()["hint"])
    url = embedder_url(prov) + path
    async with httpx.AsyncClient(timeout=300.0) as c:
        r = await c.post(url, headers=_headers(), **kw)
    if r.status_code != 200:
        raise SearchUnavailable(f"service d'embeddings ({prov}) : HTTP {r.status_code} — {r.text[:200]}")
    return r.json()


async def _embed_text(texts: list[str]) -> tuple[list[list[float]], int, str]:   # seam
    d = await _post("/embed/text", json={"texts": [t[:MAX_TEXT] for t in texts]})
    return d["vectors"], int(d.get("dim") or DEFAULT_DIM), str(d.get("model") or "")


async def _embed_audio(paths: list[Path]) -> tuple[list[list[float]], int, str]:  # seam
    files = [("files", (p.name, p.read_bytes(), "application/octet-stream")) for p in paths]
    d = await _post("/embed/audio", files=files)
    return d["vectors"], int(d.get("dim") or DEFAULT_DIM), str(d.get("model") or "")


def _sig(p: Path) -> str:
    st = p.stat()
    return f"{int(st.st_mtime)}:{st.st_size}"


async def reindex(force: bool = False) -> dict:
    """Indexe ce qui manque ou a bougé. Rien d'autre : un son déjà vu avec la
    même signature ne repasse pas par le service (gratuit ou non, c'est du
    temps). Rend {indexed, skipped, dropped, dim, model, provider}."""
    from app.services import sfx_service
    folder = sfx_service._audio_dir()
    present = sorted(p for p in folder.iterdir()
                     if p.is_file() and p.suffix.lower() in AUDIO_EXT)
    ix = Index.load()
    dropped = [n for n in ix.names() if not (folder / n).is_file()]
    for n in dropped:
        ix.drop(n)
    todo = [p for p in present if force or ix.get(p.name) is None or ix.sig(p.name) != _sig(p)]
    done = 0
    for i in range(0, len(todo), BATCH_AUDIO):
        chunk = todo[i:i + BATCH_AUDIO]
        vecs, dim, model = await _embed_audio(chunk)
        if ix.count() == 0 and (ix.dim != dim or ix.model != model):
            ix = Index(dim=dim, model=model, provider=resolve_embedder())
        elif dim != ix.dim:
            raise SearchUnavailable(
                f"le service rend des vecteurs de dimension {dim}, l'index est en {ix.dim} — "
                "réindexe tout (bouton « Tout réindexer ») après un changement de modèle.")
        for p, v in zip(chunk, vecs):
            try:
                ix.put(p.name, v, sig=_sig(p))
            except ValueError as e:
                logger.warning(f"index CLAP : {p.name} ignoré ({e})")
                continue
            done += 1
    ix.provider = resolve_embedder() or ix.provider
    ix.save()
    logger.info(f"index CLAP : {done} indexés, {len(present) - len(todo)} inchangés, "
                f"{len(dropped)} retirés ({ix.count()} au total)")
    return {"indexed": done, "skipped": len(present) - len(todo), "dropped": dropped,
            "dim": ix.dim, "model": ix.model, "provider": ix.provider, "total": ix.count()}


def _rows(pairs, ix: "Index") -> list[dict]:
    from app.services import sfx_service
    meta = sfx_service.load_meta()
    out = []
    for n, s in pairs:
        m = meta.get(n) or {}
        out.append({"name": n, "url": f"/api/audio/{n}", "score": round(float(s), 4),
                    "kind": m.get("kind") or sfx_service.classify_kind(n),
                    "tags": m.get("tags") or []})
    return out


async def search(query: str, k: int = 12) -> list[dict]:
    """Description libre → sons. Coûte un embedding de texte (une phrase)."""
    q = (query or "").strip()
    if not q:
        return []
    ix = Index.load()
    if ix.count() == 0:
        return []
    vecs, dim, _model = await _embed_text([q])
    if dim != ix.dim:
        raise SearchUnavailable(f"le service rend du {dim}, l'index est en {ix.dim} — réindexe.")
    return _rows(ix.nearest(vecs[0], k), ix)


async def similar(filename: str, k: int = 8) -> list[dict]:
    """« comme celui-ci » : PUREMENT local, aucun appel — le vecteur est déjà
    dans l'index. Un son non indexé rend une liste vide, pas une erreur."""
    ix = Index.load()
    v = ix.get(Path(str(filename)).name)
    if v is None:
        return []
    return _rows(ix.nearest(v, k, exclude=Path(str(filename)).name), ix)
```

- [ ] **Étape 3 : les routes (après `/audio/isolate`)**

```python
@router.get("/audio/search/status")
async def audio_search_status():
    """D3 — l'état de la recherche par description : prête ou non, et pourquoi."""
    from app.services import sound_search as SS
    return await asyncio.get_running_loop().run_in_executor(None, SS.status)


@router.post("/audio/search/index")
async def audio_search_index(request: Request):
    """D3 — (ré)indexe le dossier audio. Body {force?: bool}."""
    try: payload = await request.json()
    except Exception: payload = {}
    from app.services import sound_search as SS
    try:
        return await SS.reindex(force=bool(payload.get("force")))
    except SS.SearchUnavailable as e:
        raise HTTPException(503, str(e))


@router.get("/audio/search")
async def audio_search(q: str = "", k: int = 12):
    """D3 — recherche par DESCRIPTION. 503 explicite si aucun service."""
    from app.services import sound_search as SS
    try:
        return {"query": q, "items": await SS.search(q, k=max(1, min(int(k), 50)))}
    except SS.SearchUnavailable as e:
        raise HTTPException(503, str(e))


@router.get("/audio/similar/{filename}")
async def audio_similar(filename: str, k: int = 8):
    """D3 — « comme celui-ci ». Purement local : jamais de 503, jamais un sou."""
    from app.services import sound_search as SS
    safe = Path(filename).name
    if safe != filename:
        raise HTTPException(400, "nom de fichier refusé")
    return {"name": safe, "items": await SS.similar(safe, k=max(1, min(int(k), 50)))}
```
Ces quatre routes se déclarent **avant** `/audio/{filename}` (ligne 2362), sans
quoi `search` serait lu comme un nom de fichier — même piège que `/audio/meta`.

- [ ] **Étape 4 : l'implémentation de référence du service local**

```python
# tools/clapbox/server.py
# -*- coding: utf-8 -*-
"""Clapbox — service local d'embeddings CLAP pour DeepotusVideoGen (D3, 03/09/2026).

CE FICHIER NE TOURNE PAS DANS L'APPLICATION. Le python embarqué de l'app est
stdlib + Pillow ; ici il faut torch et transformers. Environnement séparé :

    py -3.11 -m venv .venv
    .venv\\Scripts\\python -m pip install -r tools/clapbox/requirements.txt
    .venv\\Scripts\\python tools/clapbox/server.py          # écoute 127.0.0.1:17494

Puis, dans l'app : Réglages → Clés → CLAPBOX_URL (vide = ce défaut). Le tiroir
Sons détecte le service tout seul (GET /health) et se replie proprement s'il
n'est pas lancé — exactement comme Voicebox pour les voix.

Contrat (le nôtre, figé par backend/tests/test_sound_search_index.py) :
    GET  /health       → {"ok": true, "model": "...", "dim": 512}
    POST /embed/text   {"texts": [...]} → {"dim", "model", "vectors": [[...]]}
    POST /embed/audio  multipart `files` → {"dim", "model", "vectors": [[...]]}
"""
import cgi, io, json, tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import librosa
import torch
from transformers import ClapModel, ClapProcessor

MODEL_ID = "laion/clap-htsat-unfused"
SR = 48000
HOST, PORT = "127.0.0.1", 17494

print(f"Clapbox: chargement de {MODEL_ID} (première fois : ~2 Go à télécharger)…")
_proc = ClapProcessor.from_pretrained(MODEL_ID)
_model = ClapModel.from_pretrained(MODEL_ID).eval()
DIM = int(_model.config.projection_dim)
print(f"Clapbox: prêt sur http://{HOST}:{PORT} (dim={DIM})")


def _vecs(t: torch.Tensor) -> list[list[float]]:
    return [[float(x) for x in row] for row in t.detach()]


def embed_text(texts):
    with torch.no_grad():
        i = _proc(text=list(texts), return_tensors="pt", padding=True)
        return _vecs(_model.get_text_features(**i))


def embed_audio(paths):
    waves = [librosa.load(str(p), sr=SR, mono=True)[0] for p in paths]
    with torch.no_grad():
        i = _proc(audios=waves, sampling_rate=SR, return_tensors="pt", padding=True)
        return _vecs(_model.get_audio_features(**i))


class H(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        b = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/health":
            self._json({"ok": True, "model": MODEL_ID, "dim": DIM})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            if self.path == "/embed/text":
                texts = json.loads(self.rfile.read(n))["texts"]
                self._json({"dim": DIM, "model": MODEL_ID, "vectors": embed_text(texts)})
            elif self.path == "/embed/audio":
                form = cgi.FieldStorage(
                    fp=io.BytesIO(self.rfile.read(n)), headers=self.headers,
                    environ={"REQUEST_METHOD": "POST",
                             "CONTENT_TYPE": self.headers.get("Content-Type")})
                items = form["files"] if "files" in form else []
                items = items if isinstance(items, list) else [items]
                tmp = Path(tempfile.mkdtemp(prefix="clapbox_"))
                paths = []
                for it in items:
                    p = tmp / (Path(it.filename or "x").name or "x")
                    p.write_bytes(it.file.read())
                    paths.append(p)
                self._json({"dim": DIM, "model": MODEL_ID, "vectors": embed_audio(paths)})
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:                       # noqa: BLE001
            self._json({"error": f"{type(e).__name__}: {e}"}, 500)


if __name__ == "__main__":
    HTTPServer((HOST, PORT), H).serve_forever()
```
```
# tools/clapbox/requirements.txt
torch>=2.2
transformers>=4.40
librosa>=0.10
soundfile>=0.12
```
```markdown
<!-- tools/clapbox/README.md -->
# Clapbox — embeddings CLAP en local (optionnel)

Sert la recherche de sons **par description** et **par similarité** du tiroir
Sons. Optionnel : sans lui, l'app dit pourquoi la recherche par description est
indisponible, et « comme celui-ci » continue de marcher sur l'index déjà écrit.

    py -3.11 -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt
    .venv\Scripts\python server.py

Premier lancement : ~2 Go de poids téléchargés dans le cache Hugging Face.
Ensuite, dans l'app : tiroir Sons → « Indexer les sons » (une fois ; les
générations suivantes s'ajoutent toutes seules).

Repli distant : renseigne `CLAP_REMOTE_URL` (+ `CLAP_REMOTE_KEY`) dans
Réglages → Clés vers n'importe quel service parlant le même contrat.
```

- [ ] **Étape 5 : vert, commit**

Run : `python tests/test_sound_search_index.py` → `=== 16 passed, 0 failed ===` ;
`python tests/test_sound_search_gate.py` reste vert.
```
git add backend/app/services/sound_search.py backend/app/api/routes.py tools/clapbox/server.py tools/clapbox/requirements.txt tools/clapbox/README.md backend/tests/test_sound_search_index.py
git commit -m 'son-vfx D3b : indexation CLAP, recherche par description, voisins par similarite' -m 'Le contrat Clapbox est mesuré contre un VRAI serveur HTTP stub, pas contre un monkeypatch. La signature mtime:taille evite de repayer un son deja vu ; un fichier efface quitte l index. « Comme celui-ci » est purement local : servi meme service coupe, et gratuit.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 13 : D3c — le tiroir Sons cherche par description et montre les voisins

**Files :**
- Modify : `frontend/patches/sfxstudio.js` (états après `s16`, `svx-filters` ~831, `itemRow` ~600, `svx-list` ~849) ; `frontend/dist/shared/sfxstudio.css`
- Test : aucun banc neuf — la surface est du JS injecté ; la preuve est **à
  l'écran**, mesurée (étape 3). Les routes derrière sont couvertes par T12.

- [ ] **Étape 1 : les états et le chargement du statut**

Après les états `s12`–`s16` posés par T4 :
```js
  var s17=x.useState(null),ssStatus=s17[0],setSsStatus=s17[1];   /* {ready,hint,indexed,provider} */
  var s18=x.useState(!1),semantic=s18[0],setSemantic=s18[1];     /* mode « décrire » */
  var s19=x.useState(null),semRes=s19[0],setSemRes=s19[1];       /* [{name,score}] | null */
  var s20=x.useState(""),semBusy=s20[0],setSemBusy=s20[1];
  var s21=x.useState(null),nearOf=s21[0],setNearOf=s21[1];       /* {name,items} */
  x.useEffect(function(){if(!open)return;
    fetch("/api/audio/search/status").then(function(r2){return r2.json()})
      .then(setSsStatus).catch(function(){setSsStatus({ready:!1,indexed:0,hint:"statut indisponible"})})},[open]);
```

- [ ] **Étape 2 : la barre de recherche gagne un mode, et l'item un bouton**

Dans `svx-filters` (après le bloc `svx-search`), la bascule et l'action
d'indexation :
```js
      r.jsx("button",{className:"svx-iconbtn","data-on":semantic?"":void 0,
        title:ssStatus&&ssStatus.ready
          ?"Chercher par DESCRIPTION ("+(ssStatus.indexed||0)+" sons indexés)"
          :(ssStatus&&ssStatus.hint||"recherche par description indisponible"),
        "aria-pressed":semantic,disabled:!(ssStatus&&ssStatus.ready),
        onClick:function(){setSemantic(!semantic);setSemRes(null)},children:"✧"}),
      semantic?r.jsx("button",{className:"svx-abtn","data-busy":semBusy?"":void 0,
        title:"Indexer les sons qui ne le sont pas encore (local, gratuit)",
        onClick:function(){setSemBusy("ix");
          fetch("/api/audio/search/index",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"})
            .then(function(r2){return r2.json().then(function(d){if(!r2.ok)throw new Error(d.detail||"échec");return d})})
            .then(function(d){setSemBusy("");setSsStatus(function(p){return Object.assign({},p,{indexed:d.total})});
              fireNote(d.indexed+" sons indexés, "+d.skipped+" inchangés"+(d.dropped.length?", "+d.dropped.length+" retirés":""))})
            .catch(function(e){setSemBusy("");fireNote("Indexation : "+String(e&&e.message||e))})},
        children:semBusy?"…":"indexer"}):null,
```
La recherche part sur Entrée quand le mode est actif : sur l'`input.svx-searchin`,
ajouter `onKeyDown:function(e){if(e.key!=="Enter"||!semantic)return;e.preventDefault();
setSemBusy("q");setNearOf(null);
fetch("/api/audio/search?k=24&q="+encodeURIComponent(query))
  .then(function(r2){return r2.json().then(function(d){if(!r2.ok)throw new Error(d.detail||"échec");return d})})
  .then(function(d){setSemBusy("");setSemRes(d.items||[])})
  .catch(function(e){setSemBusy("");setSemRes([]);fireNote(String(e&&e.message||e))})}`
et, quand `semantic`, le `placeholder` devient
`"Décrire le son cherché, puis Entrée — « une porte lourde qui grince »"`.

Dans `itemRow`, `div.svx-iact`, avant le bouton `✕` (donc après les boutons
`≡ ◌ ✦` de T4) :
```js
      ssStatus&&ssStatus.indexed?r.jsx("button",{className:"svx-abtn",tabIndex:-1,
        title:"Sons proches de celui-ci (local, gratuit)",
        onClick:function(e){e.stopPropagation();
          fetch("/api/audio/similar/"+encodeURIComponent(it.name)+"?k=8")
            .then(function(r2){return r2.json()})
            .then(function(d){setSemRes(null);setNearOf({name:it.name,items:d.items||[]});
              if(!(d.items||[]).length)fireNote("« "+it.name+" » n'est pas encore indexé — clique ✧ puis « indexer ».")})
            .catch(function(){fireNote("Voisins indisponibles.")})},
        children:"≈"}):null,
```

- [ ] **Étape 3 : la liste montre le résultat, et le dit**

Le `div.svx-list` (ligne ~849) devient :
```js
    r.jsx("div",{className:"svx-list",children:
      tab==="gen"?genPanel()
      :(semRes||nearOf)?semanticPanel()
      :(shown.length?shown.map(itemRow):emptyState())}),
```
avec, avant `function itemRow` :
```js
  /* résultat d'une recherche par description ou d'un « voisins » : les mêmes
     lignes que la liste normale, plus le score, plus une sortie explicite */
  function semanticPanel(){
    var rows=nearOf?nearOf.items:semRes;
    var byName={};all.forEach(function(it){byName[it.name]=it});
    return r.jsxs("div",{className:"svx-sem",children:[
      r.jsxs("div",{className:"svx-semhead",children:[
        r.jsx("span",{children:nearOf?"Proches de « "+nearOf.name+" »":"Décrit : « "+query+" »"}),
        r.jsx("button",{className:"svx-minix",onClick:function(){setSemRes(null);setNearOf(null)},children:"retour à la liste"})]}),
      semBusy==="q"?r.jsx("div",{className:"svx-note",children:"recherche…"})
      :rows.length?rows.map(function(row){
        var it=byName[row.name]||{name:row.name,url:row.url,kind:row.kind,dur:0,size_kb:0,tags:row.tags||[],prompt:void 0,idx:0,starter:!1,parent:"",mtime:0};
        return r.jsxs("div",{className:"svx-semrow",children:[
          r.jsx("span",{className:"svx-semscore svm-mono",title:"cosinus texte ↔ audio",children:row.score.toFixed(2)}),
          itemRow(it)]},row.name)})
      :r.jsx("div",{className:"svx-note",children:nearOf
        ?"Aucun voisin — ce son n'est pas dans l'index."
        :"Rien trouvé. Vérifie que les sons sont indexés (bouton « indexer »)."})]})}
```
CSS (`sfxstudio.css`, fin) :
```css
.dzsvm .svx-sem{display:flex;flex-direction:column;gap:4px}
.dzsvm .svx-semhead{display:flex;justify-content:space-between;align-items:center;font-size:11.5px;color:var(--ink3);padding:2px 4px}
.dzsvm .svx-minix{font-size:11px;background:transparent;border:0;color:var(--cyan);cursor:pointer}
.dzsvm .svx-semrow{display:flex;align-items:center;gap:6px;min-height:44px}
.dzsvm .svx-semrow>.svx-item{flex:1;min-width:0}
.dzsvm .svx-semscore{font-size:10.5px;color:var(--ink4);width:30px;text-align:right;flex:none}
```

- [ ] **Étape 4 : injection et preuve à l'écran, MESURÉE**

Run : `python scripts/refresh_layer.py --layer sfxstudio` →
`[sfxstudio] bloc rafraîchi (… car.) · bak: 0 touché`, puis
`grep -o "/\*__DZ_[A-Z]*__\*/" frontend/dist/assets/index-BEOJX8L5.js | sort | uniq -c` → 8 lignes à `1`.

Service ARRÊTÉ (l'état par défaut) : Montage → `B` → le bouton `✧` est
désactivé et son infobulle donne la raison ; `≈` est absent tant que l'index
est vide. Service LANCÉ (`tools/clapbox/server.py`) : `✧` s'active, « indexer »
avance, une phrase suivie d'Entrée rend des lignes avec un score. **Mesurer**
dans la console, pas à l'œil (piège de la grille effondrée, mémoire du 28/08) :
`document.querySelectorAll(".svx-semrow").length` égal au nombre de lignes
annoncé, et `document.querySelector(".svx-semrow .svx-item").offsetHeight > 0`.

- [ ] **Étape 5 : commit**
```
git add frontend/patches/sfxstudio.js frontend/dist/shared/sfxstudio.css frontend/dist/assets/index-BEOJX8L5.js
git commit -m 'son-vfx D3c : le tiroir Sons cherche par description et montre les voisins' -m 'Le bouton ✧ est desactive avec la RAISON en infobulle quand aucun service d embeddings n est la ; « comme celui-ci » reste servi depuis l index local. Score affiche a cote de chaque ligne, retour a la liste explicite.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```
### Task 14 : D4a — la voix d'un personnage lui appartient : clonage et tempérament

**Files :**
- Create : `backend/app/services/voice_clone.py`
- Modify : `backend/app/services/storage.py:174-178` (le modèle `BibleEntity`) et `:420-431` (`BIBLE_ENTITIES_COLUMNS`) ; `backend/app/api/routes.py:5091-5106` (`_entity_dict`), `:5170-5172` (PUT), + `POST /bible/entities/{id}/voice-clone` ; `frontend/atelier/atelier.js:247-253` (carte entité), `:306-311` (câblage)
- Test : `backend/tests/test_voice_clone.py`

- [ ] **Étape 1 : banc rouge**

```python
# backend/tests/test_voice_clone.py
# -*- coding: utf-8 -*-
"""D4a — clonage instantané ElevenLabs rattaché à une ENTITÉ de la bible, et
tempérament (balises v3 par personnage) persistés en base. Seam multipart
stubbé : on lit ce qui PART, et ce qui reste écrit sur l'entité.
Run: python tests/test_voice_clone.py (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
from uuid import uuid4
_tmp = tempfile.mkdtemp(prefix="dzclone_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.services import voice_clone as VC
from app.services.storage import init_db, BibleEntity, async_session_factory
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
asyncio.run(init_db())
settings.ELEVENLABS_API_KEY = "test-11l"
audio = settings.images_path.parent / "audio"; audio.mkdir(exist_ok=True)
for n in ("prise_a.mp3", "prise_b.mp3"):
    (audio / n).write_bytes(b"ID3" + b"\0" * 4096)
SENT = []
def _fake_add(key, name, files, description, labels, remove_noise):
    SENT.append({"key": key, "name": name, "files": [f[0] for f in files],
                 "description": description, "labels": labels, "noise": remove_noise})
    return {"voice_id": "vx_deep_01", "requires_verification": False}
VC._post_voice_add = _fake_add
EID = uuid4().hex
async def main():
    async with async_session_factory() as s:
        s.add(BibleEntity(id=EID, kind="character", name="Deepotus"))
        await s.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        r = await c.post(f"/api/bible/entities/{EID}/voice-clone",
                         json={"files": ["prise_a.mp3", "prise_b.mp3"], "description": "voix des abysses"})
        d = r.json()
        check("clone : 200 et voice_id écrit sur l'entité",
              r.status_code == 200 and d["voice_id"] == "vx_deep_01" and d["voice_name"] == "Deepotus", r.text[:200])
        check("le POST porte la clé, le nom de l'entité et les DEUX prises",
              SENT[-1]["key"] == "test-11l" and SENT[-1]["name"] == "Deepotus"
              and SENT[-1]["files"] == ["prise_a.mp3", "prise_b.mp3"] and SENT[-1]["noise"] is True, str(SENT[-1]))
        check("labels : l'entité est nommée, pour retrouver la voix côté ElevenLabs",
              SENT[-1]["labels"]["deepotus_entity"] == EID, str(SENT[-1]["labels"]))
        e = (await c.get("/api/bible/entities")).json()["entities"][0]
        check("relu depuis la base : voix rattachée, tempérament encore vide",
              e["voice_id"] == "vx_deep_01" and e["voice_name"] == "Deepotus" and e["voice_style"] == {"tags": [], "stability": 0.5}, str(e))
        r = await c.put(f"/api/bible/entities/{EID}",
                        json={"voice_style": {"tags": ["[whispers]", "[curious]", "[zzz]", "[sad]", "[excited]"], "stability": 0.9}})
        st = r.json()["voice_style"]
        check("tempérament clampé par le MÊME clamp que la voix off (inconnu retiré, ≤ 4, stabilité snappée)",
              st == {"tags": ["[whispers]", "[curious]", "[sad]", "[excited]"], "stability": 1.0}, str(st))
        r = await c.put(f"/api/bible/entities/{EID}", json={"voice_style": None})
        check("tempérament effaçable", r.json()["voice_style"] == {"tags": [], "stability": 0.5}, r.text[:160])
        r = await c.post(f"/api/bible/entities/{EID}/voice-clone", json={"files": []})
        check("sans prise : 400 qui dit combien il en faut",
              r.status_code == 400 and "1" in r.json()["detail"], r.text[:160])
        r = await c.post(f"/api/bible/entities/{EID}/voice-clone", json={"files": ["../../secret.mp3"]})
        check("prise hors du dossier audio : refusée", r.status_code in (400, 404), str(r.status_code))
        r = await c.post(f"/api/bible/entities/{uuid4().hex}/voice-clone", json={"files": ["prise_a.mp3"]})
        check("entité inconnue : 404", r.status_code == 404)
        settings.ELEVENLABS_API_KEY = ""
        r = await c.post(f"/api/bible/entities/{EID}/voice-clone", json={"files": ["prise_a.mp3"]})
        check("sans clé : 400 nommant ElevenLabs (Voicebox clone dans SON app)",
              r.status_code == 400 and "ElevenLabs" in r.json()["detail"] and "Voicebox" in r.json()["detail"], r.text[:200])
asyncio.run(main())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```
Run : `python tests/test_voice_clone.py`
Expected : `ModuleNotFoundError: No module named 'app.services.voice_clone'`

- [ ] **Étape 2 : la colonne, le service, les routes**

**DEUX endroits, pas un** — c'est le piège de ce mécanisme : la liste
`BIBLE_ENTITIES_COLUMNS` ne sert qu'à l'auto-ALTER des bases DÉJÀ créées ; sans
la déclaration dans la classe, `e.voice_style` lèverait `AttributeError` et une
base neuve n'aurait pas la colonne du tout.

Dans le modèle `BibleEntity` (ligne 178, juste après `voice_prev`) :
```python
    # D4 (03/09/2026) — tempérament de jeu du personnage, JSON
    # {"tags": ["[whispers]", …], "stability": 0.0 | 0.5 | 1.0}, toujours
    # clampé par voice_direction.clamp_style avant écriture ET à la lecture.
    voice_style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```
Dans `storage.BIBLE_ENTITIES_COLUMNS`, après `("voice_prev", "TEXT")` :
```python
    ("voice_style", "TEXT"),
```
(L'auto-ALTER de `_migrate_columns` s'en charge sur les bases existantes — aucune
migration à écrire, même mécanique que `model3d_job` le 28/08. Contrôle :
`python tests/test_voice_clone.py` sur une base neuve ET, si une base
utilisateur est sous la main, une COPIE de celle-ci — la leçon du 29/08.)

```python
# backend/app/services/voice_clone.py
# -*- coding: utf-8 -*-
"""D4 — clonage instantané ElevenLabs (POST /v1/voices/add, page relue le
03/09/2026 : multipart `name`, `files`, `description`, `labels`,
`remove_background_noise` ; réponse `voice_id`, `requires_verification`),
rattaché à une ENTITÉ de la bible.

Pourquoi ici et pas dans elevenlabs_service : c'est un acte de BIBLE (une
entité gagne une voix), pas un acte de synthèse. Voicebox ne clone pas par
API — ses profils se créent dans son app ; on le dit plutôt que de faire
semblant."""
from __future__ import annotations
from pathlib import Path
import httpx
from loguru import logger
from app.config import settings, SSL_VERIFY
from app.services import sfx_service
from app.services.sfx_service import SfxError

ADD_URL = "https://api.elevenlabs.io/v1/voices/add"
MIN_FILES, MAX_FILES = 1, 25
MAX_TOTAL_BYTES = 100 * 1024 * 1024


def _post_voice_add(key: str, name: str, files: list, description: str,
                    labels: dict, remove_noise: bool) -> dict:      # seam
    import json as _json
    data = {"name": name, "description": description[:500],
            "labels": _json.dumps(labels, ensure_ascii=False),
            "remove_background_noise": "true" if remove_noise else "false"}
    payload = [("files", (n, b, "application/octet-stream")) for n, b in files]
    with httpx.Client(verify=SSL_VERIFY, timeout=600.0) as c:
        r = c.post(ADD_URL, headers={"xi-api-key": key}, data=data, files=payload)
    if r.status_code not in (200, 201):
        st = r.status_code if 400 <= r.status_code < 500 else 502
        raise SfxError(st, f"ElevenLabs: {sfx_service._eleven_detail(r)}")
    d = r.json() or {}
    if not d.get("voice_id"):
        raise SfxError(502, "ElevenLabs: clonage sans voice_id en retour.")
    return d


def clone_for_entity(entity_id: str, entity_name: str, filenames: list[str],
                     description: str = "") -> dict:
    """Bloquant (httpx sync) — à appeler via run_in_executor."""
    key = (settings.ELEVENLABS_API_KEY or "").strip()
    if not key:
        raise SfxError(400, "Clonage de voix : clé ElevenLabs requise (Réglages → Clés). "
                            "Voicebox clone dans sa propre application, pas par cette API.")
    names = [Path(str(f)).name for f in (filenames or []) if str(f).strip()]
    if len(names) != len(filenames or []) or not names:
        raise SfxError(400, f"Clonage : donne entre {MIN_FILES} et {MAX_FILES} prises du dossier "
                            "audio (1 à 2 minutes d'audio propre suffisent).")
    if len(names) > MAX_FILES:
        raise SfxError(400, f"Clonage : {MAX_FILES} prises au maximum.")
    folder = sfx_service._audio_dir()
    files, total = [], 0
    for n in names:
        p = folder / n
        if not p.is_file():
            raise SfxError(404, f"prise introuvable dans le dossier audio : {n}")
        b = p.read_bytes(); total += len(b)
        if total > MAX_TOTAL_BYTES:
            raise SfxError(400, "Clonage : plus de 100 Mo de prises, refusé par l'API.")
        files.append((n, b))
    d = _post_voice_add(key, entity_name[:100], files, description,
                        {"deepotus_entity": entity_id}, True)
    logger.info(f"clone voix « {entity_name} » → {d['voice_id']} ({len(files)} prises, {total // 1024} KB)")
    return {"voice_id": d["voice_id"], "voice_name": entity_name,
            "requires_verification": bool(d.get("requires_verification"))}
```

Dans `routes.py`, `_entity_dict` (ligne 5102, après `"voice_prev"`) :
```python
            "voice_style": _entity_style(getattr(e, "voice_style", None)),
```
avec, juste au-dessus de `_entity_dict` :
```python
def _entity_style(raw) -> dict:
    """Le tempérament d'un personnage, TOUJOURS servi clampé et complet —
    l'atelier n'a jamais à deviner une forme (D4, 03/09/2026)."""
    import json as _json
    from app.services import voice_direction as VD
    try:
        return VD.clamp_style(_json.loads(raw) if isinstance(raw, str) else raw)
    except Exception:
        return VD.clamp_style(None)
```
Dans `update_bible_entity` (ligne 5170), juste avant la boucle `for vk in (...)` :
```python
        if "voice_style" in body:
            import json as _json
            from app.services import voice_direction as VD
            e.voice_style = _json.dumps(VD.clamp_style(body["voice_style"]), ensure_ascii=False)
```
Et la route de clonage, après `generate_bible_model3d` :
```python
@router.post("/bible/entities/{entity_id}/voice-clone")
async def clone_bible_voice(entity_id: str, body: dict = None):
    """D4 — clone instantané ElevenLabs à partir de prises du dossier audio,
    rattaché à cette entité. Body {files: [nom, …], description?}.
    La voix obtenue est écrite sur l'entité : le storyboard la reprend seul."""
    from app.services.storage import BibleEntity, async_session_factory
    from app.services import voice_clone as VCL
    body = body or {}
    async with async_session_factory() as session:
        e = await session.get(BibleEntity, entity_id)
        if e is None:
            raise HTTPException(404, "Entité introuvable")
        try:
            d = await asyncio.get_running_loop().run_in_executor(
                None, lambda: VCL.clone_for_entity(
                    entity_id, e.name, body.get("files") or [],
                    str(body.get("description") or e.description or "")))
        except VCL.SfxError as ex:
            raise HTTPException(ex.status, ex.message)
        e.voice_id, e.voice_name, e.voice_prev = d["voice_id"], d["voice_name"], None
        e.updated_at = datetime.utcnow()
        await session.commit(); await session.refresh(e)
        return dict(d, entity=_entity_dict(e))
```

- [ ] **Étape 3 : la carte entité de l'Atelier (page autonome, aucun patch)**

Dans `frontend/atelier/atelier.js`, la `voice-row` (ligne 248-253) gagne deux
choses — le clonage et le tempérament :
```js
      <div class="voice-row">
        🎙 <span class="voice-name">${e.voice_name ? esc(e.voice_name) : "<i style='opacity:.55'>pas de voix</i>"}</span>
        ${e.voice_prev ? `<button class="btn ghost act-voice-play" title="Pré-écouter la voix">▶</button>` : ""}
        <button class="btn act-voice-suggest" title="L'agent croise la fiche du personnage (genre, âge, ton) avec les voix ElevenLabs de ton compte et propose la meilleure + des alternatives du même profil">🎙 Suggérer</button>
        <button class="btn ghost act-voice-all" title="Choisir manuellement parmi toutes les voix du compte">⌄ Toutes</button>
        <button class="btn ghost act-voice-clone" title="Cloner une voix pour CE personnage à partir de prises du dossier audio (1 à 2 min d'audio propre) — ElevenLabs, facturé à la voix">🧬 Cloner</button>
      </div>
      <div class="voice-temper" title="Tempérament par défaut : ces balises Eleven v3 sont posées devant chaque réplique de ce personnage">
        <span style="font-size:11px;color:var(--ink-soft)">Tempérament :</span>
        ${VOICE_TAGS.map(t => `<button class="btn ghost act-temper${(e.voice_style && e.voice_style.tags || []).includes(t) ? " on" : ""}" data-t="${esc(t)}">${esc(t)}</button>`).join("")}
      </div>` : ""}
```
(la fermeture `` ` : "" `` de la ligne 253 se déplace à la fin du nouveau bloc).
En tête de module, à côté des autres constantes de catalogue :
```js
// D4 — palette courte de tempérament (le catalogue complet vit dans
// /api/voice-tags ; ici on garde les six balises qui servent au jeu, les
// bruitages n'ont rien à faire sur une fiche de personnage).
const VOICE_TAGS = ["[excited]", "[sad]", "[curious]", "[whispers]", "[sarcastic]", "[mischievously]"];
```
Câblage, après `if (vall) vall.addEventListener(…)` (ligne 311) :
```js
    const vclone = card.querySelector(".act-voice-clone");
    if (vclone) vclone.addEventListener("click", async () => {
      const raw = prompt("Prises du dossier audio, séparées par des virgules "
        + "(1 à 2 min d'audio propre de ce personnage) :", "");
      const files = (raw || "").split(",").map(s => s.trim()).filter(Boolean);
      if (!files.length) return;
      if (!confirm(`Cloner « ${ent().name} » depuis ${files.length} prise(s) ? `
        + "ElevenLabs facture une voix de clone au plan du compte.")) return;
      try {
        const d = await api.send("POST", `/bible/entities/${id}/voice-clone`, { files });
        Object.assign(ent(), d.entity);
        toast(`Voix clonée : ${d.voice_id}`
          + (d.requires_verification ? " — vérification demandée par ElevenLabs" : ""));
        await renderBible();
      } catch (e) { toast("Clonage échoué : " + e.message, true); }
    });
    card.querySelectorAll(".act-temper").forEach(b => b.addEventListener("click", async () => {
      const t = b.dataset.t;
      const cur = (ent().voice_style && ent().voice_style.tags) || [];
      const next = cur.includes(t) ? cur.filter(x => x !== t) : cur.concat([t]).slice(-4);
      try {
        const up = await api.send("PUT", "/bible/entities/" + id, {
          voice_style: { tags: next, stability: (ent().voice_style || {}).stability },
        });
        Object.assign(ent(), up); await renderBible();
      } catch (e) { toast("Tempérament : " + e.message, true); }
    }));
```
CSS (`frontend/atelier/atelier.css`, fin) :
```css
.voice-temper{display:flex;flex-wrap:wrap;gap:4px;align-items:center;margin-top:4px}
.voice-temper .btn{font-size:10.5px;padding:1px 6px}
.voice-temper .btn.on{color:var(--cyan);border-color:var(--cyan)}
```

- [ ] **Étape 4 : vert, preuve à l'écran, commit**

Run : `python tests/test_voice_clone.py` → `=== 10 passed, 0 failed ===`.
Puis, l'app relancée par l'utilisateur, `/atelier` → Bible → un personnage :
les six balises de tempérament s'allument et **survivent à un rechargement**
(c'est la base qui parle, pas l'état React) ; « 🧬 Cloner » sans clé
ElevenLabs affiche le refus qui nomme Voicebox.
```
git add backend/app/services/voice_clone.py backend/app/services/storage.py backend/app/api/routes.py frontend/atelier/atelier.js frontend/atelier/atelier.css backend/tests/test_voice_clone.py
git commit -m 'son-vfx D4a : la voix d un personnage lui appartient - clonage rattache a l entite et temperament' -m 'La colonne voice_style entre par l auto-ALTER (aucune migration a ecrire) et passe par le MEME clamp que la voix off : un tempérament ne peut pas contenir une balise que le modèle ne lit pas. Le refus sans clé nomme Voicebox, qui clone dans sa propre application.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 15 : D4b — le storyboard joue chaque personnage avec SA voix et SA direction

**Files :**
- Modify : `backend/app/api/routes.py:6862-6884` (`_voice_cast`), `:6886-6932` (`_generate_scene_vo`), + `GET /voice-cast` ; `frontend/atelier/atelier.js:561-596` (carte plan), `:628-634` (câblage)
- Test : `backend/tests/test_scene_voice_cast.py`

- [ ] **Étape 1 : banc rouge — on lit ce qui PART au TTS, segment par segment**

```python
# backend/tests/test_scene_voice_cast.py
# -*- coding: utf-8 -*-
"""D4b — bout en bout : chaque réplique part avec la voix DU personnage et son
tempérament ; la narration prend celui du Narrateur ; hors Eleven v3 les
balises sont retirées et la note le dit. Banc-miroir : on lit les appels
RÉELLEMENT faits au TTS, pas la fonction qui prétend les faire.
Run: python tests/test_scene_voice_cast.py (depuis backend/)"""
import asyncio, json, os, pathlib, shutil, subprocess, sys, tempfile
from uuid import uuid4
_tmp = tempfile.mkdtemp(prefix="dzcast_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["ELEVENLABS_API_KEY"] = "test-11l"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
if not shutil.which("ffmpeg"): print("SKIP: ffmpeg introuvable"); sys.exit(0)
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.services.elevenlabs_service import VoiceoverService
from app.services.storage import init_db, BibleEntity, Chapter, Scene, async_session_factory
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
settings.ELEVENLABS_API_KEY = "test-11l"
CALLS = []
def _fake_long(self, text, output_path, language="EN", voice_id=None, model_id=None, **kw):
    CALLS.append({"text": text, "voice_id": voice_id, "model_id": model_id})
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=1",
                    "-c:a", "libmp3lame", str(output_path)], check=True)
    return output_path
VoiceoverService.generate_long = _fake_long
VoiceoverService.is_enabled = staticmethod(lambda: True)
asyncio.run(init_db())
CH, SC = uuid4().hex, uuid4().hex
FOUNTAIN = ("Le fond bouge à peine.\n\n"
            "DEEPOTUS\nJe remonte.\n\n"
            "MARIN\nPas ce soir.\n")
async def seed():
    async with async_session_factory() as s:
        s.add(BibleEntity(id=uuid4().hex, kind="character", name="Narrateur", voice_id="v_narr",
                          voice_style=json.dumps({"tags": ["[curious]"], "stability": 0.5})))
        s.add(BibleEntity(id=uuid4().hex, kind="character", name="Deepotus", voice_id="v_deep",
                          voice_style=json.dumps({"tags": ["[whispers]", "[sad]"], "stability": 1.0})))
        s.add(BibleEntity(id=uuid4().hex, kind="character", name="Marin", voice_id="v_marin"))
        s.add(BibleEntity(id=uuid4().hex, kind="character", name="Silhouette"))
        s.add(Chapter(id=CH, title="Ch1"))
        s.add(Scene(id=SC, chapter_id=CH, idx=0, slugline="INT. ABYSSE", fountain_text=FOUNTAIN))
        await s.commit()
asyncio.run(seed())
async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        d = (await c.get("/api/voice-cast")).json()
        check("GET /voice-cast : narrateur, deux rôles castés, tempéraments servis",
              d["narrator"]["voice_id"] == "v_narr" and d["cast"]["deepotus"]["style"]["tags"] == ["[whispers]", "[sad]"]
              and d["cast"]["marin"]["style"]["tags"] == [], str(d)[:250])
        check("GET /voice-cast : personne sans voix listé à part", d["uncast"] == ["Silhouette"], str(d.get("uncast")))
        r = await c.post(f"/api/scenes/{SC}/voiceover", json={"language": "fr"})
        check("VO de scène : 200 et trois segments", r.status_code == 200 and len(r.json()["segments"]) == 3, r.text[:200])
        check("narration : voix du Narrateur, SON tempérament posé devant",
              CALLS[0] == {"text": "[curious] Le fond bouge à peine.", "voice_id": "v_narr", "model_id": "eleven_v3"}, str(CALLS[0]))
        check("Deepotus : sa voix, ses deux balises, dans l'ordre de la fiche",
              CALLS[1] == {"text": "[whispers] [sad] Je remonte.", "voice_id": "v_deep", "model_id": "eleven_v3"}, str(CALLS[1]))
        check("Marin sans tempérament : texte NU et modèle par défaut (aucune balise inventée)",
              CALLS[2] == {"text": "Pas ce soir.", "voice_id": "v_marin", "model_id": None}, str(CALLS[2]))
        check("le plan de scène nomme le locuteur ET son tempérament",
              [s["speaker"] for s in r.json()["segments"]] == ["Narrateur", "Deepotus", "Marin"]
              and r.json()["segments"][1]["tags"] == ["[whispers]", "[sad]"], str(r.json()["segments"]))
        # provider sans balises : elles partent, mais nettoyées, et c'est DIT
        from app.services import voice_providers as VP
        VP.resolve_provider = lambda requested=None: "voicebox"
        CALLS.clear()
        r = await c.post(f"/api/scenes/{SC}/voiceover", json={"language": "fr"})
        check("Voicebox : aucune balise dans le texte envoyé",
              all("[" not in x["text"] for x in CALLS) and CALLS[1]["text"] == "Je remonte.", str(CALLS))
        check("Voicebox : la réponse le DIT une fois, pas trois",
              len([n for n in r.json()["notes"] if "Voicebox" in n]) == 1, str(r.json().get("notes")))
asyncio.run(main())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```
Run : `python tests/test_scene_voice_cast.py`
Expected : `KeyError: 'narrator'` (la route `/voice-cast` n'existe pas encore ;
FastAPI rend un 404 dont le JSON n'a pas cette clé).

- [ ] **Étape 2 : `_voice_cast` rend aussi le tempérament**

Remplacer le corps de `_voice_cast` (lignes 6862-6884) par :
```python
async def _voice_cast(session) -> tuple:
    """(narrateur {voice_id,name,style} | None, map nom/alias replié → rôle,
    noms des personnages SANS voix). Le style est déjà clampé : les segments
    n'ont plus qu'à l'appliquer (D4, 03/09/2026)."""
    from app.services.storage import BibleEntity
    from app.services import voice_direction as VD
    from sqlalchemy import select
    import json as _json
    rows = (await session.execute(
        select(BibleEntity).where(BibleEntity.kind == "character"))).scalars().all()
    narrator, cues, uncast = None, {}, []
    for e in rows:
        try:
            style = VD.clamp_style(_json.loads(e.voice_style) if getattr(e, "voice_style", None) else None)
        except Exception:
            style = VD.clamp_style(None)
        v = {"voice_id": e.voice_id, "name": e.name, "style": style}
        if _fold_name(e.name) in ("narrateur", "narrator"):
            narrator = v if e.voice_id else None
            continue
        if not e.voice_id:
            uncast.append(e.name)
            continue
        cues[_fold_name(e.name)] = v
        try:
            for a in (_json.loads(e.aliases) if e.aliases else []):
                cues.setdefault(_fold_name(a), v)
        except Exception:
            pass
    return narrator, cues, uncast
```
Les DEUX autres appels de `_voice_cast` (celui de `_generate_scene_vo` ligne
6895 et tout autre) doivent déballer TROIS valeurs — `grep -n "_voice_cast(" backend/app/api/routes.py`
avant de commiter : chaque site doit lire `narrator, cues, uncast = await _voice_cast(session)`.

La route de lecture, juste après (`_fold_name` est déjà en portée) :
```python
@router.get("/voice-cast")
async def voice_cast():
    """D4 — qui parle avec quelle voix et quel tempérament. Lu par la carte
    plan de l'Atelier : le casting doit être VISIBLE avant de générer."""
    from app.services.storage import async_session_factory
    async with async_session_factory() as session:
        narrator, cues, uncast = await _voice_cast(session)
    return {"narrator": narrator, "cast": cues, "uncast": uncast}
```

- [ ] **Étape 3 : les segments partent balisés — ou nettoyés, et dits**

Dans `_generate_scene_vo`, remplacer la ligne `narrator, cues = await _voice_cast(session)`
par `narrator, cues, _uncast = await _voice_cast(session)`, puis la boucle
`for i, seg in enumerate(segments):` par :
```python
    from app.services import voice_direction as VD, voice_providers as VP
    prov = await loop.run_in_executor(None, VP.resolve_provider)
    notes: list[str] = []
    for i, seg in enumerate(segments):
        if seg["kind"] == "dialogue":
            v = cues.get(_fold_name(seg["character"] or "")) or narrator or {}
        else:
            v = narrator or {}
        vid, speaker = v.get("voice_id"), v.get("name")
        style = v.get("style") or {"tags": [], "stability": 0.5}
        text = VD.apply_style(seg["text"], style)
        # Seul Eleven v3 lit les balises. Ailleurs on les retire — les laisser
        # ferait PRONONCER « crochet whispers crochet » (P5, même règle).
        if style["tags"] and prov == "elevenlabs":
            mid = "eleven_v3"
        else:
            mid = None
            if VD.find_tags(text):
                text = VD.strip_tags(text)
                if not notes:
                    notes.append("Tempéraments retirés : "
                                 + ("Voicebox n'interprète pas les balises Eleven v3."
                                    if prov == "voicebox" else
                                    "aucun fournisseur v3 actif."))
        dest = tmp / f"part_{i:03d}.mp3"
        await loop.run_in_executor(
            None, lambda s=text, d=dest, vv=vid, mm=mid: voice.generate_long(
                text=s, output_path=d, language=l11, voice_id=vv, model_id=mm))
        parts.append(dest)
        plan.append({"kind": seg["kind"], "speaker": speaker,
                     "chars": len(seg["text"]), "tags": style["tags"]})
```
et la valeur de retour gagne `"notes": notes` :
```python
    return {"scene": _scene_dict(scene), "segments": plan, "duration_s": dur, "notes": notes}
```

- [ ] **Étape 4 : la carte plan de l'Atelier montre qui parlera**

Dans `frontend/atelier/atelier.js`, au chargement des plans, charger le casting
une fois (à côté du chargement des entités) :
```js
let voiceCast = { narrator: null, cast: {}, uncast: [] };
async function loadVoiceCast() {
  try { voiceCast = await api.send("GET", "/voice-cast"); } catch (_e) { /* casting muet */ }
}
function castChip(name) {
  const k = String(name || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const v = voiceCast.cast[k];
  if (!v) return `<span class="cast-chip cast-none" title="Pas de voix castée — 🎙 Suggérer ou 🧬 Cloner sur sa fiche de bible">${esc(name)} · sans voix</span>`;
  const t = (v.style && v.style.tags || []).join(" ");
  return `<span class="cast-chip" title="Voix ${esc(v.voice_id)}${t ? " · tempérament " + esc(t) : ""}">${esc(name)} · ${esc(v.name)}${t ? " " + esc(t) : ""}</span>`;
}
```
`loadVoiceCast()` est appelé dans le même `await Promise.all([...])` que
`renderBible()` au chargement d'un chapitre, et de nouveau après un clonage
(dans le `.then` de `act-voice-clone`, ajouter `await loadVoiceCast();`).
Sur la carte plan, après la ligne `shot-ents` (ligne ~595) :
```js
      <div class="shot-cast">${(s.entities || []).map(id => {
        const en = entities.find(x => x.id === id);
        return en && en.kind === "character" ? castChip(en.name) : "";
      }).join("") || "<span style='opacity:.5'>aucun personnage dans ce plan</span>"}</div>
```
CSS (`atelier.css`) :
```css
.shot-cast{display:flex;flex-wrap:wrap;gap:4px;margin-top:3px}
.cast-chip{font-size:10.5px;line-height:16px;padding:0 6px;border-radius:8px;background:var(--panel-2);color:var(--ink-soft);border:1px solid var(--stroke)}
.cast-chip.cast-none{border-style:dashed;color:var(--amber)}
```

- [ ] **Étape 5 : vert, commit**

Run : `python tests/test_scene_voice_cast.py` → `=== 9 passed, 0 failed ===` ;
`python tests/test_voice_direction.py` et `python tests/test_voice_clone.py` restent verts.
Run : `grep -n "_voice_cast(" backend/app/api/routes.py` → chaque site déballe bien trois valeurs.
```
git add backend/app/api/routes.py frontend/atelier/atelier.js frontend/atelier/atelier.css backend/tests/test_scene_voice_cast.py
git commit -m 'son-vfx D4b : le storyboard joue chaque personnage avec sa voix et sa direction' -m 'Mesuré sur les appels réellement faits au TTS : la narration prend le tempérament du Narrateur, Deepotus ses deux balises, un personnage sans tempérament part NU. Hors Eleven v3 les balises sont retirées et la note le dit UNE fois. La carte plan montre le casting avant de générer, et nomme en ambre ceux qui n ont pas de voix.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Écarté

Trois bacs de R4 restent dehors, et ils y restent pour une raison chiffrée.

- **E1 — Génération de particules par IA.** Les 12 presets simulés localement (`particle_service.py`) couvrent le besoin déclaré, tournent hors ligne et coûtent 0 $ ; appeler un modèle pour de la fumée qu'une simulation rend déjà serait payer une régression de contrôle.
- **E2 — VFX vidéo → vidéo par modèle (Kling O1, Runway).** D2 répond au besoin « derrière un sujet » pour le prix d'UN détourage, réutilisable autant de fois qu'on change d'effet ; un modèle vidéo→vidéo repaye la scène entière à chaque essai et ne garantit pas la stabilité du sujet entre deux tirs.
- **E3 — Recherche par similarité SANS description.** Les deux voies partagent l'index CLAP et le même produit scalaire — `/audio/similar` n'est que `/audio/search` avec un vecteur au lieu d'une phrase (T12) : un bac de plus serait un doublon, pas une fonction.

---

## Campagne de mutations

### Task 16 : la campagne — casser chaque garde, vérifier qu'un banc rouge le dit

**Files :**
- Create : `backend/tests/mutations_son_vfx.py`
- Modify : `backend/tests/test_ducking_generation.py` (étape 3, un trou nommé) ; `backend/app/services/pricing.py` (étape 3, une dette nommée) ; `backend/tests/test_music_lyrics.py` (étape 3)
- Test : le script EST la mesure — il n'a pas de banc à lui.

Ce que la campagne mesure : chaque garde écrite par ce plan est-elle SURVEILLÉE
par une assertion ? On casse une ligne, on lance le banc qui devrait rougir, on
lit les libellés rouges, on remet le fichier à l'octet près. Une mutation VERTE
n'est pas une bonne nouvelle : c'est une assertion qui manque.

**Différence avec `mutations_plaque_slicer.py`** : ses bancs sont collectés par
pytest ; ceux de ce plan sont des scripts AUTONOMES (`python tests/test_x.py`).
On lit donc les lignes `  FAIL  <libellé>` et la ligne de bilan
`=== N passed, M failed ===`. **Trois états, pas deux** : une sortie sans ligne
de bilan (import cassé) ou commençant par `SKIP:` (ffmpeg absent) n'est PAS une
mutation verte — c'est une mesure qui n'a pas eu lieu.

- [ ] **Étape 1 : le harnais**

```python
# backend/tests/mutations_son_vfx.py
# -*- coding: utf-8 -*-
"""Campagne de mutations Son & VFX : casser → rouge → remettre.

PAS UN TEST : le nom ne commence pas par `test_`, pytest ne le collecte pas et
run-tests.ps1 ne le liste pas. Il se lance À LA MAIN, depuis backend/ :

    python tests/mutations_son_vfx.py           # toutes
    python tests/mutations_son_vfx.py 3 17      # celles-là

Il MUTE les sources du dépôt une à une et les REMET à l'octet près (assertion
sha256) : ne pas le lancer pendant qu'un autre banc lit ces fichiers, ni sur un
arbre sale. Chaque mutation nomme le ou les LIBELLÉS d'assertion qu'elle doit
faire rougir ; `attendus=None` signale une mutation qu'on s'attend à voir
VERTE, avec la raison en commentaire (garde redondante, défense en profondeur).

Trois verdicts, parce que deux ne suffisent pas : ROUGE (la garde est
surveillée), VERTE (l'assertion manque — c'est le butin), ERREUR (le banc n'a
pas tourné : import cassé, ffmpeg absent, SKIP — rien n'a été mesuré).
"""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
BACKEND = R / "backend"
PY = sys.executable

SOCLE = "test_son_vfx_socle.py"
DRAWER = "test_sons_drawer_api.py"
STEMS = "test_stems_service.py"
CLEAN = "test_voice_clean.py"
LYRICS = "test_music_lyrics.py"
DIREC = "test_voice_direction.py"
DUCK = "test_ducking_generation.py"
MATTE = "test_matte_service.py"
COMPOSE = "test_matte_compose.py"
GATE = "test_sound_search_gate.py"
INDEX = "test_sound_search_index.py"
CLONE = "test_voice_clone.py"
CAST = "test_scene_voice_cast.py"

SFX = "backend/app/services/sfx_service.py"
PRICING = "backend/app/services/pricing.py"
LIBIX = "backend/app/services/library_index.py"
STEMSVC = "backend/app/services/stems_service.py"
VCLEAN = "backend/app/services/voice_clean.py"
MUSIC = "backend/app/services/music_service.py"
VDIR = "backend/app/services/voice_direction.py"
FFM = "backend/app/services/ffmpeg_service.py"
MATTESVC = "backend/app/services/matte_service.py"
MONTAGE = "backend/app/services/montage_service.py"
FXPREV = "backend/app/services/effects_preview.py"
SEARCH = "backend/app/services/sound_search.py"
VCLONE = "backend/app/services/voice_clone.py"
ROUTES = "backend/app/api/routes.py"
REFRESH = "scripts/refresh_layer.py"

M = [
    # ── T1 socle : le ducking partagé, les prix, la source de Bibliothèque ──
    (SFX, '    return "sidechaincompress=threshold=0.05:ratio=6:attack=50:release=400"',
     '    return "sidechaincompress=threshold=0.05:ratio=6"',
     SOCLE, ["ducking bool = ligne historique"]),
    (SFX, "                f\"ratio={_g(ducking['ratio'])}:attack={_g(ducking['attack'])}:\"",
     "                f\"attack={_g(ducking['attack'])}:ratio={_g(ducking['ratio'])}:\"",
     SOCLE, ["ducking dict = mêmes champs, même ordre"]),
    (PRICING, '    "demucs_usd_per_s": 0.0007,', '    "demucs_usd_per_s": 0.007,',
     SOCLE, ["clé de prix demucs_usd_per_s", "estimation stems = 100 s × 0,0007"]),
    (PRICING,
     '        lines.append(_line("fal", "Détourage vidéo (BiRefNet) — prix à mesurer au premier tir"\n'
     '                           if rate == 0.0 else "Détourage vidéo (BiRefNet)", dur, "s", dur * rate))',
     '        lines.append(_line("fal", "Détourage vidéo (BiRefNet)", dur, "s", dur * rate))',
     SOCLE, ["estimation matte = 0 $ MAIS ligne présente"]),
    (LIBIX, '    "sonvfx": "Son & VFX",\n', "",
     SOCLE, ["source sonvfx connue de la Bibliothèque"]),
    # mutant FAIBLE assumé : à sec, --check ne peut prouver que son message.
    # C'est la limite de la mesure « sans rien écrire », pas un trou du plan.
    (REFRESH, '        print(f"[{layer}] bloc: 1 · bak: 0 touché · crlf={crlf}")',
     '        print(f"[{layer}] ok")',
     SOCLE, ["refresh_layer --check sfxstudio"]),

    # ── T2 stems ────────────────────────────────────────────────────────────
    (STEMSVC, '    args = {"audio_url": url, "model": model, "stems": want, "output_format": "mp3"}',
     '    args = {"audio_url": url, "model": model, "stems": want, "output_format": "wav"}',
     STEMS, ["endpoint et format figés"]),
    (STEMSVC, "            missing.append(s); continue", "            continue",
     STEMS, ["stem manquant DIT"]),
    (STEMSVC, '    bad = [s for s in want if s not in m["stems"]]', "    bad = []",
     STEMS, ["stem inconnu refusé (400)"]),
    (STEMSVC, '    await LI.noter([it["filename"] for it in items], "sonvfx", kind="audio")\n', "",
     STEMS, ["provenance sonvfx/audio"]),
    (STEMSVC, '"parent": src.name, "model": model,', '"parent": dest.name, "model": model,',
     STEMS, ["sidecar : kind stem + parent"]),
    (STEMSVC, '    usd = round(dur * float(pricing.load().get("demucs_usd_per_s", 0.0007)), 4)',
     "    usd = round(dur * 0.0, 4)",
     STEMS, ["coût = durée × 0,0007"]),

    # ── T3 isolation et chaîne « améliorer » ────────────────────────────────
    (VCLEAN, '    {"type": "normalize", "params": {"target_lufs": -16}},',
     '    {"type": "normalize", "params": {"target_lufs": -24}},',
     CLEAN, ["MESURÉ : sortie normalisée à −16 ± 1,5 LUFS"]),
    # NE PAS retirer l'eq3 : le banc ferait `af.index("equalizer")` sur une
    # chaîne qui n'en a plus, lèverait, et l'on aurait ERREUR au lieu de ROUGE.
    # On mute l'ORDRE lui-même, qui EST le contrat.
    (SFX, '_FX_ORDER = ("filter", "eq3", "denoise", "deesser", "compressor",',
     '_FX_ORDER = ("filter", "denoise", "eq3", "deesser", "compressor",',
     CLEAN, ["chaîne dans l'ordre de _FX_ORDER"]),
    (VCLEAN, "    if not key:", "    if False:",
     CLEAN, ["sans clé : 400 ElevenLabs"]),
    (VCLEAN, '    chars = duration_s / 60.0 * float(p.get("elevenlabs_isolation_chars_per_min", 1000.0))',
     '    chars = duration_s * float(p.get("elevenlabs_isolation_chars_per_min", 1000.0))',
     CLEAN, ["coût = 4 s / 60 × 1000 car. × tarif"]),

    # ── T6 chanson chantée ──────────────────────────────────────────────────
    (MUSIC, '_TAG_MAP = {"verse": "verse", "couplet": "verse", "chorus": "chorus", "refrain": "chorus",',
     '_TAG_MAP = {"verse": "verse", "couplet": "verse", "chorus": "chorus",',
     LYRICS, ["ace : balises minuscules"]),
    (MUSIC, '        return f"[{k}]" if style == "ace" else f"[{k.capitalize()}]"',
     '        return f"[{k}]"',
     LYRICS, ["minimax : balises capitalisées gardées"]),
    (MUSIC, '    if style == "ace" and instrumental:\n        return "[inst]"\n', "",
     LYRICS, ["ace instrumental = [inst]"]),
    (MUSIC, "            if len(lyrics) < 10:", "            if False:",
     LYRICS, ["Music 2.0 sans paroles : 400 explicite"]),
    (MUSIC, '        args = {"tags": prompt[:_MAX_PROMPT]}          # ACE-Step n\'a pas de prompt : des tags',
     '        args["tags"] = prompt[:_MAX_PROMPT]            # ACE-Step n\'a pas de prompt : des tags',
     LYRICS, ["ACE-Step envoie tags + lyrics + duration + seed, jamais prompt"]),
    # après l'étape 3 de CETTE tâche seulement : l'unité de prix vient du
    # registre. AVANT la correction, cette mutation est VERTE — c'est elle qui
    # a révélé que l'unité était écrite à deux endroits.
    (MUSIC, '        "usd": 0.0002, "usd_unit": "s", "lyrics_style": "ace",',
     '        "usd": 0.0002, "usd_unit": "gen", "lyrics_style": "ace",',
     LYRICS, ["catalogue expose usd_unit et lyrics_style", "estimation 120 s ACE-Step = 0,024 $"]),

    # ── T7 direction d'interprétation ───────────────────────────────────────
    (VDIR, '    tags = [t for t in (raw.get("tags") or []) if isinstance(t, str) and t in KNOWN][:MAX_TAGS]',
     '    tags = [t for t in (raw.get("tags") or []) if isinstance(t, str) and t in KNOWN]',
     DIREC, ["style clampé", "apply_style préfixe"]),
    (VDIR, '    return {"tags": tags, "stability": min((0.0, 0.5, 1.0), key=lambda v: abs(v - s))}',
     '    return {"tags": tags, "stability": s}',
     DIREC, ["style clampé"]),
    (VDIR, '    if not st["tags"] or _TAG_RX.match(t):', '    if not st["tags"]:',
     DIREC, ["texte déjà balisé : pas de double préfixe"]),
    (VDIR, 'EXPERIMENTAL = {"[pause]", "[sings]", "[woo]"}', 'EXPERIMENTAL = {"[sings]", "[woo]"}',
     DIREC, ["[pause] marqué expérimental"]),
    (ROUTES, "        text = VD.strip_tags(text)\n", "",
     DIREC, ["hors v3 : balises retirées ET note"]),

    # ── T8 ducking dès la génération ────────────────────────────────────────
    (FFM, "                if has_vo and ducking:", "                if has_vo and False:",
     DUCK, ["MESURÉ : musique ≥ 4 dB plus basse SOUS la voix qu'après"]),
    (ROUTES,
     '             + (f"[m][vsc]{sfx_service.ducking_filter(duck)}[md];" if duck else "[m]anull[md];[vsc]anullsink;")',
     '             + "[m]anull[md];[vsc]anullsink;"',
     DUCK, ["MESURÉ : /audio/duck aussi"]),

    # ── T9 / T10 matte et composition ───────────────────────────────────────
    (MATTESVC, 'ARGS_FIXED = {"video_output_type": "PRORES4444 (.mov)", "refine_foreground": True,',
     'ARGS_FIXED = {"video_output_type": "X264 (.mp4)", "refine_foreground": True,',
     MATTE, ["arguments figés : ProRes 4444, refine, modèle"]),
    # les DEUX gardes du confinement tombent ensemble : chacune seule est
    # rattrapée par l'autre (défense en profondeur voulue).
    (MATTESVC,
     [('_SAFE = re.compile(r"^[A-Za-z0-9_-]+\\.mov$")', '_SAFE = re.compile(r"^.+\\.mov$")'),
      ('    if p.parent != mattes_dir().resolve():\n        raise ValueError("matte hors dossier")\n', "")],
     None, MATTE, ["chemin refusé : ../x.mov"]),
    (MATTESVC, '"usd_note": USD_NOTE}', '"usd_note": ""}',
     MATTE, ["statut : note de prix « à mesurer »"]),
    (MONTAGE, '            behind = [e for e in reff if e.get("behind", True)]',
     '            behind = [e for e in reff if e.get("behind", False)]',
     COMPOSE, ["derrière : sujet rouge intact, fond inversé"]),
    (MONTAGE,
     '            parts.append(f"[{cur_lbl}][m{k}]overlay=eof_action=pass:format=auto,format=yuv420p[n{k}ov]")',
     '            parts.append(f"[m{k}][{cur_lbl}]overlay=eof_action=pass:format=auto,format=yuv420p[n{k}ov]")',
     COMPOSE, ["derrière : sujet rouge intact, fond inversé"]),
    (MONTAGE, '        if not audio_only and not s.get("gap") and s.get("matte"):', "        if False:",
     COMPOSE, ["derrière : sujet rouge intact, fond inversé"]),
    # VERTE ATTENDUE : la garde « matte absent » de render_preview rattrape le
    # nom hostile. Deux filets pour une chute — on le note, on ne le « corrige »
    # pas en retirant un filet.
    (FXPREV, "        mp = MT.matte_path(str(matte))          # ValueError si hostile",
     "        mp = MT.mattes_dir() / str(matte)",
     COMPOSE, None),

    # ── T11 la porte CLAP ───────────────────────────────────────────────────
    (SEARCH, '    if clapbox_reachable():\n        return "clapbox"\n', "",
     GATE, ["clapbox joignable : voie locale préférée"]),
    (SEARCH, "    if not n or n != n:                      # 0 ou NaN", "    if False:",
     GATE, ["vecteur nul refusé"]),
    (SEARCH, '    if len(v) != dim:\n        raise ValueError(f"vecteur de dimension {len(v)}, attendu {dim}")\n', "",
     GATE, ["dimension étrangère refusée"]),
    (SEARCH, "    out = [(n, sum(map(mul, qn, v))) for n, v in self._v.items() if n != exclude]",
     "    out = [(n, sum(map(mul, qn, v))) for n, v in self._v.items()]",
     GATE, ["exclude retire le demandeur"]),
    (SEARCH, "        out.sort(key=lambda t: -t[1])\n", "",
     GATE, ["8 voisins, score décroissant"]),
    (SEARCH, "            if dim is not None and ix.dim != int(dim):", "            if False:",
     GATE, ["index d'une autre dimension"]),

    # ── T12 indexation et recherche ─────────────────────────────────────────
    (SEARCH, "    todo = [p for p in present if force or ix.get(p.name) is None or ix.sig(p.name) != _sig(p)]",
     "    todo = list(present)",
     INDEX, ["rien n'a bougé : 0 réindexé"]),
    (SEARCH, "    dropped = [n for n in ix.names() if not (folder / n).is_file()]", "    dropped = []",
     INDEX, ["fichier effacé : retiré de l'index et dit"]),
    (SEARCH, "    return _rows(ix.nearest(v, k, exclude=Path(str(filename)).name), ix)",
     "    return _rows(ix.nearest(v, k), ix)",
     INDEX, ["similarité : le demandeur est EXCLU"]),
    (SEARCH, '    st = p.stat()\n    return f"{int(st.st_mtime)}:{st.st_size}"', '    return ""',
     INDEX, ["chaque item porte sa signature mtime:taille"]),

    # ── T14 clonage et tempérament ──────────────────────────────────────────
    # les deux clamps (écriture ET lecture) tombent ensemble : un seul suffit
    # à tenir l'invariant, ce qui est exactement le but.
    (ROUTES,
     [('            e.voice_style = _json.dumps(VD.clamp_style(body["voice_style"]), ensure_ascii=False)',
       '            e.voice_style = _json.dumps(body["voice_style"], ensure_ascii=False)'),
      ("        return VD.clamp_style(_json.loads(raw) if isinstance(raw, str) else raw)",
       "        return _json.loads(raw) if isinstance(raw, str) else raw")],
     None, CLONE, ["tempérament clampé par le MÊME clamp que la voix off"]),
    (VCLONE, "    if len(names) != len(filenames or []) or not names:", "    if False:",
     CLONE, ["sans prise : 400 qui dit combien il en faut"]),
    (VCLONE, '                        {"deepotus_entity": entity_id}, True)', "                        {}, True)",
     CLONE, ["labels : l'entité est nommée"]),
    (ROUTES, '        e.voice_id, e.voice_name, e.voice_prev = d["voice_id"], d["voice_name"], None',
     "        e.voice_prev = None",
     CLONE, ["relu depuis la base : voix rattachée"]),

    # ── T15 le storyboard joue les personnages ──────────────────────────────
    (ROUTES, '        text = VD.apply_style(seg["text"], style)', '        text = seg["text"]',
     CAST, ["narration : voix du Narrateur, SON tempérament posé devant",
            "Deepotus : sa voix, ses deux balises"]),
    (ROUTES, '        if style["tags"] and prov == "elevenlabs":', "        if False:",
     CAST, ["Deepotus : sa voix, ses deux balises"]),
    (ROUTES, "                if not notes:\n                    notes.append(\"Tempéraments retirés : \"",
     "                if True:\n                    notes.append(\"Tempéraments retirés : \"",
     CAST, ["Voicebox : la réponse le DIT une fois, pas trois"]),
    (ROUTES, "            uncast.append(e.name)", "            pass",
     CAST, ["personne sans voix listé à part"]),

    # ── T4 le tiroir Sons, côté backend (ajoutées en queue pour ne pas
    #    décaler les indices déjà cités dans le plan) ──────────────────────
    (SFX, "        if len(out) == 12: break", "        if len(out) == 99: break",
     DRAWER, ["tags nettoyés : trim, dédoublonnés, ≤ 24 car., ≤ 12"]),
    (ROUTES, '    entry = dict(sfx_service.load_meta().get(safe) or {"kind": sfx_service.classify_kind(safe)})',
     "    entry = {}",
     DRAWER, ["kind conservé (import déduit)"]),
]


def mesurer(banc):
    """Lance UN banc autonome et rend (libellés rouges, sortie, erreur, note).

    « Erreur » = le banc n'a pas mesuré : pas de ligne de bilan (import cassé),
    un SKIP (ffmpeg absent), ou un code de sortie inattendu. Lue comme « aucun
    FAIL », une telle sortie passerait pour une mutation VERTE alors que rien
    n'a été mesuré — c'est le piège que ce troisième état ferme.
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([PY, f"tests/{banc}"], capture_output=True,
                       cwd=BACKEND, timeout=1800, env=env)
    txt = (r.stdout.decode("utf-8", "replace")
           + "\n--- stderr ---\n" + r.stderr.decode("utf-8", "replace"))
    bilan = re.search(r"^=== (\d+) passed, (\d+) failed ===$", txt, re.M)
    saute = bool(re.search(r"^SKIP:", txt, re.M))
    erreur = saute or bilan is None or r.returncode not in (0, 1)
    labels = set(re.findall(r"^  FAIL  (.+?)\s*$", txt, re.M))
    return labels, txt, erreur, ("SKIP" if saute else "" if bilan else "pas de bilan")


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, banc, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        # l'arbre est en CRLF (autocrlf) : on apparie en LF, on réécrit avec la
        # fin de ligne du fichier, et l'on remet à l'octet près depuis `src`.
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        paires = old if isinstance(old, list) else [(old, new)]
        for o, n_ in paires:
            assert txt.count(o) == 1, (i, rel, txt.count(o), o[:70])
            txt = txt.replace(o, n_)
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur, note = mesurer(banc)
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        manquants = [a for a in (attendus or []) if not any(a in n for n in rg)]
        if erreur:
            verdict = f"ERREUR({note or 'code'})"
            print(sortie[-1500:], file=sys.stderr)
        elif attendus:
            verdict = "ROUGE" if not manquants else ("VERTE" if not rg else "ROUGE(autres)")
        else:
            verdict = "VERTE(attendue)" if not rg else "ROUGE(inattendu)"
        bilan.append((i, rel, banc, verdict, sorted(rg), manquants))
        apercu = paires[0][0].strip()[:46]
        print(f"[{i:2d}] {verdict:16s} {banc:28s} {apercu!r} -> {sorted(rg)}"
              f"  sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:4] for b in bilan], ensure_ascii=False))
    # Le butin : tout libellé ATTENDU resté VERT, même quand un autre libellé
    # de la même mutation a rougi — sinon une garde à moitié surveillée passe.
    verts = [b for b in bilan if b[5]]
    print(f"\n{len(bilan)} mutations · "
          f"{sum(1 for b in bilan if b[3] == 'ROUGE')} ROUGE · "
          f"{sum(1 for b in bilan if b[3].startswith('VERTE'))} VERTE · "
          f"{sum(1 for b in bilan if b[3].startswith('ERREUR'))} ERREUR")
    if verts:
        print("Libellés attendus restés VERTS — assertions manquantes (le butin) :")
        for b in verts:
            print(f"  [{b[0]}] {b[1]} — attendu rouge : {b[5]}")


if __name__ == "__main__":
    main()
```

- [ ] **Étape 2 : le premier tour, en entier**

Run : `python tests/mutations_son_vfx.py`
Expected (lecture, pas décor) :
- **zéro `ERREUR`**. Une seule suffit à invalider le tour : un `SKIP` veut dire
  que ffmpeg n'est pas dans le PATH, un « pas de bilan » qu'une mutation casse
  l'import et qu'on n'a donc rien mesuré. Corriger l'environnement et relancer
  la mutation seule (`python tests/mutations_son_vfx.py 12`) avant d'aller plus loin.
- **la seule `VERTE(attendue)`** est la mutation **35** (l'aperçu : la garde
  « matte absent » rattrape un nom hostile). Elle doit sortir `VERTE(attendue)`
  et non `ROUGE(inattendu)`. Les deux autres couples de gardes redondantes
  (**30**, le confinement des mattes ; **46**, le clamp de tempérament) sont
  mutés ENSEMBLE et doivent donc sortir `ROUGE` : c'est la preuve qu'aucune des
  deux gardes n'est décorative.
- **tout libellé attendu resté vert = une assertion manquante**, listé dans le
  bloc final « Libellés attendus restés VERTS ». À l'écriture de ce plan, deux
  sont attendus, et l'étape 3 les ferme :
  1. **mutation 28** (le filtergraph de `POST /audio/duck`) sort `VERTE` : le
     banc D1 mesure le ducking de `FFmpegMerger.merge`, jamais celui de la
     route — on peut débrancher le ducking de `/audio/duck` sans qu'un seul
     banc s'en aperçoive ;
  2. **mutation 21** (`"usd_unit": "s"` d'ACE-Step) sort `ROUGE(autres)` avec
     « estimation 120 s ACE-Step = 0,024 $ » dans les manquants : le catalogue
     rougit, la facture non, parce que `pricing.estimate` code l'unité en dur
     au lieu de la lire au registre. Le registre peut donc mentir sur l'unité
     sans que le prix affiché bouge d'un centime.

- [ ] **Étape 3 : fermer les deux trous nommés**

**(1) `/audio/duck` n'est pas mesuré.** Dans `backend/tests/test_ducking_generation.py`,
à la fin de la fonction `main()` (après le contrôle « voix absente : 404 »),
ajouter une voix qui se TAIT à la moitié — c'est le silence qui rend le ducking
lisible :
```python
        ff("-f", "lavfi", "-i", "sine=frequency=400:duration=1",
           "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:d=1",
           "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[o]", "-map", "[o]",
           str(audio / "vo_gap.mp3"))
        r = await c.post("/api/audio/duck", json={"voice": "vo_gap.mp3", "music": "bgm.mp3", "music_db": -6})
        mix = audio / r.json()["filename"]
        parle, silence = mean_db(mix, 0.2, 0.5), mean_db(mix, 1.3, 0.5)
        check("MESURÉ : /audio/duck aussi — musique ≥ 4 dB plus basse pendant la voix que dans le silence",
              silence - parle >= 4.0, f"pendant {parle} dB, silence {silence} dB")
```
(`ff`, `audio` et `mean_db` sont déjà au niveau module du banc.) Le bilan passe
de `=== 7 passed` à `=== 8 passed`.

**(2) L'unité de prix est écrite deux fois.** Dans `pricing.estimate`, remplacer
la branche `elif kind == "music":` posée par T1 par :
```python
    elif kind == "music":
        # UNE seule source pour l'unité : le registre MUSIC_MODELS. Le TARIF,
        # lui, reste réglable (clé de prix) quand une clé existe — sans quoi le
        # registre pourrait annoncer « à la seconde » et la facture « au
        # forfait » sans que rien ne rougisse (campagne de mutations, 03/09).
        from app.services.music_service import MUSIC_MODELS
        model = str(op.get("model") or "")
        m = MUSIC_MODELS.get(model) or {}
        dur = float(op.get("duration_s", 0))
        keys = {"ace-step": "ace_step_usd_per_s", "minimax-music-20": "minimax_music_20_usd"}
        usd = float(p.get(keys[model], m.get("usd", 0.0))) if model in keys else float(m.get("usd", 0.0))
        if m.get("usd_unit") == "s":
            lines.append(_line("fal", f"Musique ({model})", dur, "s", dur * usd))
        else:
            lines.append(_line("fal", f"Musique ({model})", 1, "gen", usd))
```
et ajouter au banc `backend/tests/test_music_lyrics.py`, après l'estimation ACE-Step :
```python
e = P.estimate({"kind": "music", "model": "minimax-music-20", "duration_s": 200})
check("un modèle au forfait ne se facture PAS à la seconde", abs(e["total_usd"] - 0.03) < 1e-9, str(e))
```
Le bilan passe de `=== 11 passed` à `=== 12 passed`.

- [ ] **Étape 4 : le second tour, et le commit**

Run : `python tests/mutations_son_vfx.py 21 28`
Expected : les deux mutations qui étaient VERTE sont maintenant `ROUGE`.
Run : `python tests/mutations_son_vfx.py` (tour complet)
Expected : `56 mutations · 55 ROUGE · 1 VERTE · 0 ERREUR`, la seule VERTE étant
la `VERTE(attendue)` de la mutation 35, et le bloc « Libellés attendus restés
VERTS » VIDE.
Run, pour finir, les douze bancs du plan en entier :
```powershell
# PowerShell (le shell du projet), depuis backend/ :
foreach ($t in @("test_son_vfx_socle","test_stems_service","test_voice_clean","test_sons_drawer_api",
                 "test_music_lyrics","test_voice_direction","test_ducking_generation","test_matte_service",
                 "test_matte_compose","test_sound_search_gate","test_sound_search_index","test_voice_clone",
                 "test_scene_voice_cast")) {
  python "tests/$t.py"; if (-not $?) { Write-Host "ROUGE: $t" }
}
```
Expected : treize bilans `0 failed`, aucune ligne `ROUGE:`.
```
git add backend/tests/mutations_son_vfx.py backend/tests/test_ducking_generation.py backend/tests/test_music_lyrics.py backend/app/services/pricing.py
git commit -m 'son-vfx : campagne de mutations - 56 gardes cassees, deux trous fermes' -m 'Trois verdicts, pas deux : un banc qui SKIP ou dont l import casse ne compte pas comme vert. Butin du premier tour : POST /audio/duck n était pas mesuré (seul merge l était) et pricing.estimate codait l unité de prix en dur au lieu de la lire au registre — les deux fermés ici. Une seule mutation reste verte par CONCEPTION : la garde « matte absent » de l aperçu rattrape un nom hostile — deux filets pour une chute, on le note plutôt que d en retirer un.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```
