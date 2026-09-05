# Montage (timeline) — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Un sous-agent frais par tâche, puis deux revues — conformité d'abord, qualité ensuite.

**Goal :** amener l'écran Montage au niveau des références vérifiées en R5 (CapCut pour les sous-titres, Descript pour le montage par le texte, Resolve pour l'étalonnage et le recadrage), en commençant par **mesurer** le défaut signalé — « la piste overlay ou la piste musique n'est pas rendue » — sur le fichier rendu, jamais sur le code.

**Architecture :** le rendu reste `montage_service._build_montage_command` (ffmpeg, une commande, testable sans backend) ; chaque évolution s'y ajoute par un champ **optionnel** du payload dont l'absence laisse la commande **octet pour octet** identique (règle déjà en vigueur : R1…R4b, C4, S1). Côté écran, on ne rafraîchit **jamais** le bloc `son-vfx-montage.js` (voir « Coût de patch » : ce bloc porte dans le bundle 5 sections `vfxrack` et 15 sections `subs` qu'un rafraîchissement effacerait) : toute l'interface nouvelle vit dans une **couche neuve** `frontend/patches/montage.js` (`window.DzMontage`) injectée par un **patcher neuf** `scripts/patch_bundle_montage.py` (tag `montage`, `.bak_montage`, EN QUEUE), avec des hooks assert-gardés sur des ancres **uniques** du bundle courant. Les bancs sont des scripts autonomes qui lisent le fichier rendu (ffprobe, PIL, astats).

**Tech Stack :** Python 3.13 embarqué (stdlib + Pillow 12.3.0, **pas de numpy** — mesuré), ffmpeg 8.1.1 (PATH, `C:\ffmpeg\…\bin` ; repli `%LOCALAPPDATA%\DeepotusVideoGen\bin`), libass, FastAPI + TestClient, node 24 (`node --check` du bundle, tests du cœur JS), puppeteer-core pour les QA navigateur lancés **avec le backend démarré par l'utilisateur**.

---

## Ce que le terrain dit — mesuré le 03/09/2026

| Fait mesuré | Conséquence pour ce plan |
|---|---|
| `montage_service.py` (1 632 l.) : V2 = **une seule couche** d'overlays triés par `start` (l. ~1010), musique = **premier** clip `a2` (l. ~1447, `-stream_loop -1` l. 1090), second clip `a2` → `a_clips` au gain du bus **sfx** (`base = g_voice if a1 else g_sfx`, l. ~1454) | P1 introduit `tracks` (bus par piste, rang de composition) ; le second clip musique prend le bus musique — changement délibéré, nommé |
| Le bloc sonvfx du bundle = source + **V3, V4, V6, V8, V9** de `vfxrack` + **S3…S17** de `subs` (ancres présentes dans la source, remplacements présents dans le bundle) ; cette copie n'a **que 4 `.bak`** (`dzrailmotion`, `version`, `dznodecat`, `seedance25`) ; `.bak_sonvfx/vfxrack/subs` n'existent que dans le dépôt principal (gitignorés) | rafraîchir `son-vfx-montage.js` effacerait 20 sections et **rien ne peut les rejouer ici** (V10 déjà consommé → abort). D'où le patcher neuf en queue |
| Le lecteur vivant **ne joue pas A2/A3** (commentaire du vu-mètre, `son-vfx-montage.js` ~l. 2077 : « musique et SFX ne jouent pas en live ») ; le bouton **M** d'une piste écrit `-40 dB` dans `proj.mixDb`, **autosauvegardé et envoyé au rendu** (`svmTrackMute`, l. 2943) | deux hypothèses UI du défaut signalé, à consigner en P0 si le banc backend est vert ; P7 fait jouer A2/A3 en direct |
| `SVM_TRACKS` est une constante (l. 840) ; `trackKind` lit la **première lettre** de l'id (`v`/`a`/`s`) ; `SVM_TRACK_BUS` est un objet module-level (l. 973) | des ids `v3`, `a4` marchent sans toucher `trackKind` ; le bus se resynchronise en mutant l'objet en place (1 ancre au lieu de 8) |
| ffmpeg 8.1.1 : `xfade` connaît **58 transitions** (`zoomin`, `hlwind`, `hblur`, `smoothleft`…), `colortemperature`, `lutyuv`, `lut3d`, `tile`, `astats`, `signalstats` présents | P4, D1, D4 tiennent en filtres natifs, sans bibliothèque |
| `subtitle_service` : karaoké `\k` par mot, animations `fondu`/`pop` sur la **ligne** (`_ANIMS`, l. 846) ; `_measure_px(line, st, scale)` mesure un texte avec la fonte embarquée (l. 1211) | P2 pose **un événement ASS par mot** (`\pos` + `\t`) : la largeur des mots se mesure avec la même fonte que libass |
| `transcribe_service.align_known_text` rend des mots datés `{w, start, end, speech_end, clip}` ; `/subtitles/from-narration` les groupe | P3 et D3 réutilisent ces mots : gratuit quand le texte est connu |
| `effects_engine._CATALOG` pilote le rack **et** la vignette d'aperçu (`/api/effects/preview`) ; `GRADES` est fait de `colorbalance/eq/curves` | P4 et D1 = deux types d'effet de plus, sliders et vignette gratuits |
| `/studio-graphs` : dossier de JSON `{id,name,updated_at,graph}` sous `outputs_path.parent` | P5 reprend la mécanique, dossier `montage_projects/` |
| Python du PATH **sans** `loguru` ; runtime embarqué complet | toutes les commandes utilisent `$PY` (ci-dessous) |
| `POST /videos/upload` enregistre un job `provider="ugc"` ; `provider="episode"` existe ; `Chapter.script_text` porte le texte connu d'un épisode | D3 sait d'où viennent « épisodes, films et vidéos externes » |

**Conventions valables pour tout le plan**

```powershell
$PY = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"   # Pillow oui, numpy non
Set-Location backend                                                   # les bancs se lancent d'ici
```

- Un banc = `backend/tests/test_<x>.py` **autonome** (un processus par fichier, `& $PY tests\test_<x>.py`), jamais `pytest tests`. En tête : `sys.stdout.reconfigure(encoding="utf-8")`, puis les variables d'environnement **avant** tout `import app.…` (`app.config` crée `DATA_ROOT` à l'import). Chaque banc expose `check(label, cond, detail)` qui imprime `  PASS  <label>` / `  FAIL  <label> <detail>` (label = identifiant sans espace : la campagne de mutations lit ces lignes) et finit par `=== N passed, M failed ===`, code de sortie 1 si rouge.
- Bancs-miroirs : les clips de test sont fabriqués par ffmpeg (`color=`, `sine=`) ; on lit le **fichier** (ffprobe, PIL, `astats`), jamais la commande.
- Commits (PowerShell, jamais de guillemets doubles) : `git commit -m 'montage : <sujet sans accent>' -m '<corps accentué>' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`.
- Le POURQUOI avec la mesure : chaque tâche commence par un banc rouge.

---

## Périmètre

Les bacs de R5 (`docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md`, « R5. Montage ») sont le périmètre **exact**.

**Lot 1 — parité (dans l'ordre)** : P0 chaque piste arrive au rendu (banc-miroir d'abord) · P1 pistes dynamiques et réordonnables · P2 sous-titres animés mot par mot · P3 montage par le texte · P4 étalonnage (4 curseurs sous la LUT) · P5 projets nommés · P6 remplacer un clip par sa nouvelle version · P7 lecture fluide.

**Lot 2 — différenciant** : D1 correspondance de couleur entre plans · D2 recadrage multi-format avec suivi de sujet (mesuré, tranché par table) · D3 auto-clips · D4 titres animés et transitions dynamiques · D5 export EDL/FCPXML.

**Écarté** : E1, E2, E3 — une ligne chacun en fin de document.

---

## Coût de patch

**Le bloc `son-vfx-montage.js` ne se rafraîchit pas dans ce plan.** Mesure du 03/09 : dans le bundle, ce bloc contient les remplacements V3/V4/V6/V8/V9 de `patch_bundle_vfxrack.py` et S3…S17 de `patch_bundle_subs.py` ; `patch_bundle_sonvfx.py` remplace le bloc **en place** depuis la source et effacerait ces 20 sections ; ni `vfxrack` ni `subs` ne peuvent être rejoués ici (pas de `.bak_vfxrack`/`.bak_subs` dans cette copie — gitignorés — et l'ancre V10 est déjà consommée : `anchor count=0 → Aborting`).

**La voie du dépôt (README « Patching the compiled UI », patchers `vfxrack` et `subs`)** :

| Élément | Décision |
|---|---|
| Couche | `frontend/patches/montage.js` — `window.DzMontage`, injectée juste après `/*__DZ_SUBS_END__*/`, même scope module (alias `r`/`x` du bundle). **Ne touche ni `r` ni `x` au chargement** (le cœur pur est testable sous node) |
| Patcher | `scripts/patch_bundle_montage.py` — `TAG="montage"`, `BEGIN="/*__DZ_MONTAGE_BEGIN__*/"`, `.bak_montage`, mécanique **copiée** de `patch_bundle_subs.py` (`guard_downstream`, `--check`, `--strip`, `nl()`), liste `PATCHES=[(tag, ancre, remplacement)]` — chaque ancre doit exister **exactement une fois** |
| Feuille | `frontend/dist/shared/montage.css` liée après `subs.css` (section M2, comme S2) ; `son-vfx-montage.css` est un fichier **commis** : on l'édite directement, sans patch |
| Rejouer | après toute édition de `montage.js` ou du patcher : `& $PY scripts\patch_bundle_montage.py --check ; & $PY scripts\patch_bundle_montage.py` (restaure `.bak_montage` puis réapplique) ; `& $PY scripts\repatch_all.py --list` doit montrer `montage` **en dernier** ; `node --check frontend\dist\assets\index-BEOJX8L5.js` |
| Miroir | `backend/tests/test_montage_bundle.py` lit le **bundle** : un seul bloc `MONTAGE`, chaque remplacement présent une fois, chaque ancre consommée, `node --check` vert |

Coût par tâche (les sections `M<n>` s'ajoutent à `PATCHES`, la couche grandit) : P0 **0** · P1 M1–M9 (la plus chère : en-têtes de piste, payloads, toolbar) · P2 M10 (une chip de style) · P3 M11–M12 (tiroir Texte, coupe par plage) · P4 M13 (bouton « à tous les plans ») · P5 M14 (popover Projets) · P6 M15–M16 (mode remplacement dans `addAsset`) · P7 M17–M19 (pics, filmstrip, pool audio) · D1 M20 · D2 M21 · D3 M22 · D4 M23–M24 (liste `SVM_TRANS`, galerie) · D5 M25. Tout le backend est hors patch.

---

## Références vérifiées (R5, 03/09/2026)

- **CapCut** (capcut.com, 03/09) : sous-titres automatiques mot par mot, styles animés (Glow, Trending, Word, Frame…), rebond, emoji automatiques → P2 (rebond, glow, couleur ; emoji par mot-clé en option).
- **Descript** (help.descript.com, 03/09) : mots de remplissage détectés et soulignés, suppression en lot, langues dont **FR** ; le montage par le texte coupe la vidéo → P3.
- **DaVinci Resolve** (blackmagicdesign.com, 03/09) : Smart Reframe réservé à Resolve Studio, modes auto/pan/tilt, pensé pour vertical et carré ; « color matching » cité sans détail → D1, D2.
- **fal** (fal.ai, 03/09) : Luma Ray 2 Reframe, Wan VACE Long Reframe (modes general/human/auto), LTX-2.3 Reframe — **génératifs** → D2 les garde en option payante par clip, jamais par défaut (E2).
- **De mémoire, non vérifiés** (n'argumentent rien) : Opus Clip, Premiere Auto Reframe, Final Cut, **EDL CMX 3600 et FCPXML** → D5 commence par relire la spec.

---

## Lot 1 — parité

### Tâche 1 — P0 : chaque piste arrive au rendu (banc-miroir d'abord)

**Files :** créer `backend/tests/test_montage_pistes_rendu.py` ; modifier `backend/app/services/montage_service.py` **seulement si le banc rougit**.

- [ ] **Étape 1 : écrire le banc (rouge ou vert, on ne le sait pas encore — c'est le point).**

```python
# -*- coding: utf-8 -*-
"""P0 — chaque piste arrive au rendu. Banc-MIROIR : on lit le FICHIER rendu
(ffprobe, PIL, astats), jamais le code qui pretend le produire.
Sources synthetiques : V1 bleu 4 s muet, overlay PNG rouge, musique 440 Hz,
voix 880 Hz. Deux chemins : _build_montage_command en direct, puis la ROUTE
POST /api/montage/render (TestClient, tache de fond executee avant le retour).
Run : & $PY tests\\test_montage_pistes_rendu.py   (depuis backend/)"""
import json, os, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp0_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FF = shutil.which("ffmpeg") or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")
FP = shutil.which("ffprobe") or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffprobe.exe")
from PIL import Image                                   # noqa: E402
from app.services import montage_service as M           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

def sh(cmd, timeout=240):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")

V1, OV, MUS, VOX = (os.path.join(TMP, n) for n in ("v1.mp4", "ov.png", "theme_music.wav", "voice.wav"))
sh([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x2040a0:s=270x480:r=30:d=4", "-pix_fmt", "yuv420p", V1])
Image.new("RGB", (96, 96), (255, 40, 40)).save(OV)
sh([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=6", MUS])
sh([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=44100:duration=2", VOX])

def probe(path):
    d = json.loads(sh([FP, "-v", "error", "-show_entries", "stream=codec_type:format=duration",
                       "-of", "json", path]).stdout or "{}")
    return [s["codec_type"] for s in d.get("streams", [])], float(d.get("format", {}).get("duration") or 0)

def frame(path, t):
    png = os.path.join(TMP, f"f_{os.path.basename(path)}_{t}.png")
    sh([FF, "-y", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", png])
    return Image.open(png).convert("RGB")

def mean_rgb(im, box=None):
    if box: im = im.crop(box)
    px = list(im.getdata()); n = float(len(px))
    return tuple(round(sum(p[i] for p in px) / n, 1) for i in range(3))

def rms_db(path, t0, t1):
    r = sh([FF, "-hide_banner", "-ss", str(t0), "-t", str(t1 - t0), "-i", path, "-vn",
            "-af", "astats=measure_overall=RMS_level:measure_perchannel=none", "-f", "null", "-"])
    for ln in r.stderr.splitlines():
        if "RMS level dB" in ln:
            v = ln.split(":")[-1].strip()
            return -999.0 if v == "-inf" else float(v)
    return -999.0

def v1_spec():
    return [{"path": V1, "src_dur": 4.0, "src_in": 0.0, "start": 0.0, "end": 4.0,
             "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}]
def ov_spec(tf=None):
    return {"path": OV, "is_image": True, "src_dur": 0.0, "src_in": 0.0, "start": 1.0,
            "end": 3.0, "opacity": None, "tf": tf, "mp": None}
AUD = {"fade_in": 0, "fade_out": 0, "fade_in_curve": None, "fade_out_curve": None,
       "fx_chain": "", "speed": 0.0, "volume_points": None}
def vox_spec():
    return [dict(AUD, tr="a1", path=VOX, src_dur=2.0, src_in=0.0, start=0.0, end=2.0,
                 gain=M._db_to_gain(-6))]
def mus_spec():
    return dict(AUD, path=MUS, gain=M._db_to_gain(-18))

def verify(tag, out, cover=True):
    kinds, dur = probe(out)
    check(f"{tag}_une_video_une_audio", kinds.count("video") == 1 and kinds.count("audio") == 1, str(kinds))
    check(f"{tag}_duree_4s", abs(dur - 4.0) < 0.15, f"{dur}")
    b0, b2, b35 = mean_rgb(frame(out, 0.5)), mean_rgb(frame(out, 2.0)), mean_rgb(frame(out, 3.5))
    check(f"{tag}_overlay_absent_avant", b0[2] > b0[0] + 60, f"{b0}")
    if cover:
        check(f"{tag}_overlay_visible_pendant", b2[0] > 180 and b2[0] > b2[2] + 100, f"{b2}")
    else:
        im = frame(out, 2.0); w, h = im.size
        c = mean_rgb(im, (w // 2 - 8, h // 2 - 8, w // 2 + 8, h // 2 + 8))
        k = mean_rgb(im, (0, 0, 16, 16))
        check(f"{tag}_overlay_centre_rouge", c[0] > 180 and c[0] > c[2] + 100, f"{c}")
        check(f"{tag}_overlay_coin_bleu", k[2] > k[0] + 60, f"{k}")
    check(f"{tag}_overlay_absent_apres", b35[2] > b35[0] + 60, f"{b35}")
    m = rms_db(out, 3.0, 3.8); v = rms_db(out, 0.2, 1.8)
    check(f"{tag}_musique_audible_seule_3s", m > -45, f"{m} dB")
    check(f"{tag}_voix_plus_forte_que_musique", v > m + 6, f"voix {v} dB, musique {m} dB")

print("\n[1] _build_montage_command en direct — overlay cover, voix, musique bouclée")
out1 = os.path.join(TMP, "direct.mp4")
cmd, total = M._build_montage_command(v1_spec(), [ov_spec()], vox_spec(), mus_spec(), w=270, h=480,
                                      fps=30, mix_db={}, ducking=True, duration_master=True,
                                      preview=False, out=out1)
r = sh(cmd); check("direct_ffmpeg_ok", r.returncode == 0 and os.path.getsize(out1) > 0, r.stderr[-300:])
verify("direct", out1)

print("\n[2] overlay TRANSFORMÉ (scale 0,3 au centre) + aperçu 480p")
out2 = os.path.join(TMP, "tf.mp4")
cmd, _ = M._build_montage_command(v1_spec(), [ov_spec({"x": .5, "y": .5, "scale": .3, "rotate": 0.0})],
                                  vox_spec(), mus_spec(), w=66, h=120, fps=30, mix_db={},
                                  ducking=True, duration_master=True, preview=True, out=out2)
r = sh(cmd); check("tf_ffmpeg_ok", r.returncode == 0, r.stderr[-300:])
verify("tf", out2, cover=False)

print("\n[3] par la ROUTE — clips v2 / a1 / a2 en {file_path}, tâche de fond")
from fastapi.testclient import TestClient               # noqa: E402
from app.main import app                                # noqa: E402
body = {"name": "p0", "ratio": "9:16", "preview": False, "mix": {"dialogue": -6, "musique": -18, "sfx": -12},
        "clips": [{"tr": "v1", "src": {"file_path": V1}, "start": 0, "end": 4, "srcIn": 0, "transition": "cut"},
                  {"tr": "v2", "src": {"file_path": OV}, "start": 1, "end": 3},
                  {"tr": "a1", "src": {"file_path": VOX}, "start": 0, "end": 2},
                  {"tr": "a2", "src": {"file_path": MUS}, "start": 0, "end": 4, "loop": True}]}
with TestClient(app) as c:
    r = c.post("/api/montage/render", json=body)
    check("route_lancee", r.status_code == 200 and r.json().get("job_id"), r.text[:200])
    j = c.get("/api/jobs/" + r.json()["job_id"]).json()
    check("route_job_done", j.get("status") == "done", str(j.get("error") or j.get("status")))
    fp = j.get("final_video_path") or ""
    check("route_fichier_present", fp and os.path.exists(fp), fp)
    if fp and os.path.exists(fp):
        # le rendu réel est 1080×1920 : mêmes lectures, seuls les seuils sont relatifs
        verify("route", fp)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```

- [ ] **Étape 2 : lancer.** `& $PY tests\test_montage_pistes_rendu.py`
  Attendu : `=== 27 passed, 0 failed ===` **ou** des `FAIL` nommés. Les trois cas possibles et ce qu'on fait :
  - `*_overlay_visible_pendant` rouge → l'overlay n'est pas composé : lire la commande (`" ".join(cmd)`), vérifier l'ordre `[cur][ovj]overlay=…enable='between(t,st,en)'` et `eof_action=pass` ; corriger dans la boucle V2 de `_build_montage_command` (l. ~1010-1085).
  - `*_musique_audible_seule_3s` rouge → la musique n'entre pas au mix : vérifier `music_lbl` et les `labels` (l. ~1090-1150) — cas connu : `voice_lbl` vide **et** `ducking` vrai laisse `music_lbl` dans `labels` ; s'il manque, c'est là.
  - `route_*` rouge alors que `direct_*` est vert → le défaut est dans la **classification** des clips de `montage_render` (`_run`, l. ~1370-1465) : `tr`, `_has_audio_stream`, `_resolve_src`.
- [ ] **Étape 3 : si rouge — corriger au plus court, relancer jusqu'au vert, puis ajouter au banc l'assertion qui aurait attrapé le défaut si elle manquait.**
  - **Effet de bord assumé.** La route `POST /api/montage/measure` partage ce graphe audio (`audio_only=True`) : le correctif du ducking change la valeur LUFS retournée pour tout projet voix + musique + ducking — elle mesurait jusqu'ici un mix tronqué à la dernière syllabe de la voix, fidèlement puisque le rendu l'était aussi, les deux étant corrigés ensemble ; toute mesure relevée avant le 03/09/2026 sur un tel projet est périmée.
- [ ] **Étape 4 : si vert — la tâche le dit et ferme.** Ajouter en tête du banc, dans la docstring, le constat daté et les **deux hypothèses côté écran** que P1 et P7 traitent : (a) le bouton **M** d'une piste écrit `−40 dB` dans `proj.mixDb`, autosauvegardé et **envoyé au rendu** (`svmTrackMute`) — une musique « mise en sourdine pour écouter la voix » est rendue à −40 dB ; (b) le **lecteur vivant** ne joue ni A2 ni A3 (mesuré au commentaire du vu-mètre) — ce que l'utilisateur entend avant le rendu n'est pas le mix. Rien d'autre n'est changé.
- [ ] **Étape 5 : commit.**
  `git add backend/tests/test_montage_pistes_rendu.py backend/app/services/montage_service.py; git commit -m 'montage : P0 - banc-miroir des pistes au rendu' -m 'Le banc lit le fichier rendu : ffprobe (une vidéo, une audio, durée), PIL (overlay visible entre 1 et 3 s, absent avant et après, transformé au centre), astats (musique seule audible à 3 s, voix plus forte que la musique). Chemin direct et route. Constat : <vert / rouge corrigé>.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

### Tâche 2 — P1 : pistes dynamiques et réordonnables, le rendu compose dans l'ordre

**Files :** modifier `backend/app/services/montage_service.py` (`_tracks_meta`, classification, tri des overlays) ; créer `backend/tests/test_montage_pistes_dyn.py`, `frontend/patches/montage.js`, `frontend/dist/shared/montage.css`, `scripts/patch_bundle_montage.py`, `backend/tests/test_montage_bundle.py` ; modifier `frontend/dist/shared/son-vfx-montage.css:292`.

- [ ] **Étape 1 : banc backend rouge — l'ordre des pistes décide de la composition.**

```python
# backend/tests/test_montage_pistes_dyn.py — même en-tête (env, FF/FP, check, sh, frame, mean_rgb)
# que test_montage_pistes_rendu.py, puis :
print("\n[1] _tracks_meta : absent = table historique, sinon ordre haut→bas")
m = M._tracks_meta(None)
check("meta_legacy_v2_layer0", m["v2"]["layer"] == 0 and m["v2"]["kind"] == "video")
check("meta_legacy_a2_musique_loop", m["a2"]["bus"] == "musique" and m["a2"]["loop"] is True)
check("meta_legacy_a3_sfx", m["a3"]["bus"] == "sfx" and m["a3"]["loop"] is False)
m = M._tracks_meta([{"id": "v3", "kind": "video"}, {"id": "v2", "kind": "video"}, {"id": "v1", "kind": "video"},
                    {"id": "a1", "kind": "audio", "bus": "dialogue"},
                    {"id": "a4", "kind": "audio", "bus": "musique", "loop": True},
                    {"id": "a2", "kind": "audio", "bus": "musique", "loop": False}])
check("meta_v3_au_dessus_de_v2", m["v3"]["layer"] == 1 and m["v2"]["layer"] == 0)
check("meta_a4_boucle_a2_non", m["a4"]["loop"] is True and m["a2"]["loop"] is False and m["a2"]["bus"] == "musique")
check("meta_bus_inconnu_retombe_sfx", M._tracks_meta([{"id": "a9", "kind": "audio", "bus": "x"}])["a9"]["bus"] == "sfx")

print("\n[2] non-régression : sans `layer`, la commande ne bouge pas d'un octet")
ref, _ = M._build_montage_command(v1_spec(), [ov_spec()], vox_spec(), mus_spec(), w=270, h=480, fps=30,
                                  mix_db={}, ducking=True, duration_master=True, preview=False, out="o.mp4")
got, _ = M._build_montage_command(v1_spec(), [dict(ov_spec(), layer=0)], vox_spec(), mus_spec(), w=270, h=480,
                                  fps=30, mix_db={}, ducking=True, duration_master=True, preview=False, out="o.mp4")
check("cmd_identique_layer0", got == ref)

print("\n[3] miroir : deux pistes d'overlay — celle du HAUT couvre celle du bas")
GV = os.path.join(TMP, "green.png"); Image.new("RGB", (40, 40), (40, 220, 60)).save(GV)
def two(top_green):
    red = dict(ov_spec({"x": .5, "y": .5, "scale": .6, "rotate": 0.0}), layer=0 if top_green else 1)
    grn = dict(ov_spec({"x": .5, "y": .5, "scale": .3, "rotate": 0.0}), path=GV, layer=1 if top_green else 0)
    out = os.path.join(TMP, f"two_{int(top_green)}.mp4")
    cmd, _ = M._build_montage_command(v1_spec(), [red, grn], [], None, w=270, h=480, fps=30, mix_db={},
                                      ducking=False, duration_master=False, preview=False, out=out)
    sh(cmd); im = frame(out, 2.0); w, h = im.size
    return mean_rgb(im, (w // 2 - 6, h // 2 - 6, w // 2 + 6, h // 2 + 6))
c = two(True);  check("vert_au_dessus_centre_vert", c[1] > 150 and c[1] > c[0] + 60, f"{c}")
c = two(False); check("rouge_au_dessus_centre_rouge", c[0] > 150 and c[0] > c[1] + 60, f"{c}")
```

- [ ] **Étape 2 : lancer → `FAIL` sur `_tracks_meta` (AttributeError) puis sur `layer`.** `& $PY tests\test_montage_pistes_dyn.py`
- [ ] **Étape 3 : backend minimal.** Dans `montage_service.py`, sous `_MUSIC_HINT` :

```python
# P1 : pistes dynamiques. `tracks` du payload, du HAUT vers le BAS de la
# timeline (l'ordre de SVM_TRACKS). Absent → table historique, commande
# octet pour octet identique. `layer` = rang de composition des pistes vidéo
# d'overlay, 0 = juste au-dessus de V1 : la piste listée le plus HAUT est
# composée en DERNIER, donc au-dessus de tout. V1 reste la piste de base.
_LEGACY_TRACKS = [{"id": "v2", "kind": "video"}, {"id": "v1", "kind": "video"},
                  {"id": "a1", "kind": "audio", "bus": "dialogue"},
                  {"id": "a2", "kind": "audio", "bus": "musique", "loop": True},
                  {"id": "a3", "kind": "audio", "bus": "sfx"}]
_BUSES = ("dialogue", "musique", "sfx")


def _tracks_meta(raw) -> dict:
    rows = raw if isinstance(raw, list) and raw else _LEGACY_TRACKS
    meta, ov = {}, []
    for t in rows:
        if not isinstance(t, dict) or not t.get("id"):
            continue
        tid = str(t["id"])[:8]
        kind = str(t.get("kind") or {"a": "audio", "s": "subs"}.get(tid[:1], "video"))
        bus = str(t.get("bus") or {"a1": "dialogue", "a2": "musique"}.get(tid, "sfx"))
        loop = bool(t.get("loop", tid == "a2")) and kind == "audio"
        meta[tid] = {"kind": kind, "bus": bus if bus in _BUSES else "sfx", "loop": loop, "layer": 0}
        if kind == "video" and tid != "v1":
            ov.append(tid)
    for k, tid in enumerate(reversed(ov)):
        meta[tid]["layer"] = k
    return meta
```

Dans `_run()` de `montage_render` **et** dans `montage_measure` : `meta = _tracks_meta(body.get("tracks"))` ; boucle V2 : `m = meta.get(c.get("tr")); if not m or m["kind"] != "video" or c.get("tr") == "v1": continue` et le dict reçoit `"layer": m["layer"]` ; boucle audio : `if not m or m["kind"] != "audio": continue`, `bus = m["bus"]`, `if m["loop"] and music is None:` → musique ; sinon `base = {"dialogue": g_voice, "musique": g_music, "sfx": g_sfx}[bus]` et `"tr": "a1" if bus == "dialogue" else "a3"` (changement délibéré : un **second** clip du bus musique prend le gain musique, plus le gain sfx). **Ce correctif répare le GAIN seulement** : `"a1" if bus == "dialogue" else "a3"` renvoie toujours un second clip du bus musique dans les **bruitages**, donc il restera **non ducké et non bouclé** (seul le premier clip `a2` devient `music`, la seule entrée à porter `-stream_loop -1` et à alimenter le sidechaincompress). P1 le corrige ou l'assume, mais ne doit pas laisser croire que « second clip musique » est réglé en entier. Dans `_build_montage_command`, le tri des overlays devient `sorted(v2, key=lambda k2: (int(k2.get("layer") or 0), k2["start"]))`. Docstring de `montage_render` : ajouter `tracks?: [{id, kind, bus?, loop?}]`. `montage_save` stocke `tracks` tel quel si c'est une liste.

- [ ] **Étape 4 : lancer → `=== 9 passed, 0 failed ===`.**
- [ ] **Étape 5 : le patcher neuf.** Copier `scripts/patch_bundle_subs.py` en `scripts/patch_bundle_montage.py` ; remplacer l'en-tête par la phrase du plan (« couche `window.DzMontage`, EN QUEUE après `subs`, AVERTISSEMENT DE CHAÎNE recopié »), puis les constantes :

```python
PATCH_SRC = REPO / "frontend" / "patches" / "montage.js"
TAG = "montage"
BEGIN = "/*__DZ_MONTAGE_BEGIN__*/"
END = "/*__DZ_MONTAGE_END__*/"
ANCHOR_INJECT = "/*__DZ_SUBS_END__*/"
CSS_ANCHOR = '<link rel="stylesheet" href="/shared/subs.css">'
CSS_INSERT = '\n    <link rel="stylesheet" href="/shared/montage.css">'

A_M3 = "          SVM_TRACKS.map(function(tr){"                      # M3 : les pistes viennent du projet
R_M3 = "          svmTracksOf(proj).map(function(tr){"
A_M4 = "    setProj(np);"                                             # M4 : bus resynchronisé à l'application
R_M4 = "    svmTrackBusSync(np.tracks);\n    setProj(np);"
A_M5 = "      clips:clips.filter(function(c){return c.src}).map(function(c){"   # M5 : payload de rendu
R_M5 = "      tracks:svmTracksPayload(proj),\n      clips:clips.filter(function(c){return c.src}).map(function(c){"
A_M6 = "      duration_master:durMaster,ducking:ducking,clips:clips,"          # M6 : autosave
R_M6 = "      duration_master:durMaster,ducking:ducking,clips:clips,\n      tracks:svmTracksPayload(proj),"
A_M7 = 'var np={demo:!1,name:d.name||"montage",version:"v1",ratio:d.ratio||"9:16",'   # M7 : restauration
R_M7 = 'var np={demo:!1,tracks:svmTracksFrom(d.tracks),name:d.name||"montage",version:"v1",ratio:d.ratio||"9:16",'
A_M8 = 'r.jsx("button",{className:"svm-tbtn",title:"Raccourcis ("+svmKeyLabel("keys_panel")+") — personnalisables",'
R_M8 = ('r.jsx(DzMontage.TrackAdd,{tracks:svmTracksOf(proj),onChange:function(ts){pushHistory();'      # M8 : « + piste »
        'svmTrackBusSync(ts);setProj(function(p){return Object.assign({},p,{tracks:ts})});setDirty(!0)}}),\n'
        '        ' + A_M8)
A_M9a = 'children:[thAdd,thM,thS,thLock]},"br"),'                    # M9 : ▲ ▼ × et poignée sur les en-têtes
R_M9a = 'children:[thAdd,thM,thS,thLock,DzMontage.headBtns(tr,svmTracksOf(proj),svmTracksSet,clips,setClips,fireNote)]},"br"),'
A_M9b = 'children:[thType,thLock]},"tr")]}),'
R_M9b = 'children:[thType,thLock,DzMontage.headBtns(tr,svmTracksOf(proj),svmTracksSet,clips,setClips,fireNote)]},"tr")]}),'
PATCHES = [("M3-tracks", A_M3, R_M3), ("M4-bus", A_M4, R_M4), ("M5-payload", A_M5, R_M5),
           ("M6-save", A_M6, R_M6), ("M7-apply", A_M7, R_M7), ("M8-toolbar", A_M8, R_M8),
           ("M9a-head-audio", A_M9a, R_M9a), ("M9b-head-video", A_M9b, R_M9b)]
```

`svmTracksSet` n'existe pas dans le composant : M8 le crée en tête de la section M4 → remplacer `R_M4` par `"    svmTrackBusSync(np.tracks);\n    setProj(np);"` **et** ajouter `("M4b-setter", "  function svmApplyProject(d){", "  function svmTracksSet(ts){pushHistory();svmTrackBusSync(ts);setProj(function(p){return Object.assign({},p,{tracks:ts})});setDirty(!0)}\n  function svmApplyProject(d){")` à `PATCHES` (ancre unique, mesurée).

- [ ] **Étape 6 : la couche.** `frontend/patches/montage.js` — cœur pur d'abord (aucun `r`/`x` au chargement) :

```javascript
/* ── Montage, couche window.DzMontage — injectée après le bloc subs, même scope
   module. Le CŒUR (tracks*, rippleCut) est pur : testable sous node. ── */
"use strict";
var DZM_DEFAULT_TRACKS=[
 {id:"v2",name:"V2",type:"overlay/VFX",h:40,c:"--c-3d",mix:13,kind:"video"},
 {id:"v1",name:"V1",type:"vidéo",h:54,c:"--c-video",mix:12,kind:"video"},
 {id:"a1",name:"A1",type:"dialogue",h:52,c:"--c-audio",mix:13,kind:"audio",bus:"dialogue"},
 {id:"a2",name:"A2",type:"musique",h:48,c:"--c-text",mix:8,kind:"audio",bus:"musique",loop:!0},
 {id:"a3",name:"A3",type:"sfx",h:48,c:"--c-3d",mix:13,kind:"audio",bus:"sfx"},
 {id:"s1",name:"S1",type:"sous-titres",h:44,c:"--c-text",mix:11,kind:"subs"}];
function svmTracksOf(proj){return (proj&&proj.tracks&&proj.tracks.length)?proj.tracks:DZM_DEFAULT_TRACKS}
function svmTracksFrom(raw){
  if(!Array.isArray(raw)||!raw.length)return null;
  var seen={},out=[];
  raw.forEach(function(t){if(!t||!t.id||seen[t.id])return;seen[t.id]=1;
    var d=DZM_DEFAULT_TRACKS.filter(function(k){return k.id===t.id})[0]||{};
    out.push(Object.assign({},d,t,{kind:t.kind||d.kind||(t.id[0]==="a"?"audio":t.id[0]==="s"?"subs":"video")}))});
  return out.some(function(t){return t.id==="v1"})?out:null}
function svmTracksPayload(proj){return svmTracksOf(proj).map(function(t){
  var o={id:t.id,kind:t.kind};if(t.bus)o.bus=t.bus;if(t.loop)o.loop=!0;return o})}
/* SVM_TRACK_BUS est un objet module-level lu à 8 endroits du bloc sonvfx :
   on le MUTE en place plutôt que de poser 8 ancres. */
function svmTrackBusSync(ts){
  Object.keys(SVM_TRACK_BUS).forEach(function(k){delete SVM_TRACK_BUS[k]});
  (ts||DZM_DEFAULT_TRACKS).forEach(function(t){if(t.kind==="audio"&&t.bus)SVM_TRACK_BUS[t.id]=t.bus})}
/* règle d'ordre : overlays au-dessus de V1 (V1 = dernière piste vidéo),
   audio au milieu, S1 en bas. Un déplacement ne sort jamais de son groupe. */
function dzmGroup(t){return t.kind==="video"?(t.id==="v1"?1:0):t.kind==="audio"?2:3}
function dzmMove(ts,id,dir){
  var i=ts.findIndex(function(t){return t.id===id}),j=i+dir;
  if(i<0||j<0||j>=ts.length||dzmGroup(ts[i])!==dzmGroup(ts[j]))return ts;
  var n=ts.slice();n[i]=ts[j];n[j]=ts[i];return n}
function dzmAdd(ts,kind){
  var n=1,ids=ts.map(function(t){return t.id});
  while(ids.indexOf(kind[0]+n)>=0)n++;
  var t=kind==="video"?{id:"v"+n,name:"V"+n,type:"overlay",h:40,c:"--c-3d",mix:13,kind:"video"}
    :{id:"a"+n,name:"A"+n,type:"sfx",h:48,c:"--c-3d",mix:13,kind:"audio",bus:"sfx"};
  var at=kind==="video"?0:ts.findIndex(function(k){return k.kind==="subs"});
  var out=ts.slice();out.splice(at<0?ts.length:at,0,t);return out}
function dzmRemove(ts,id){return id==="v1"?ts:ts.filter(function(t){return t.id!==id})}
```

puis les composants (`TrackAdd` : deux boutons « + vidéo » / « + audio » ; `headBtns(tr, ts, set, clips, setClips, note)` : `▲`, `▼`, `×` — `×` refuse V1, demande confirmation inline (`data-arm`) quand la piste porte des clips et retire ces clips avec `setClips` ; poignée `⋮` `draggable` qui appelle `dzmMove` au `drop` selon la position verticale). Export : `window.DzMontage={ready:!0,TrackAdd:…,headBtns:…,tracksOf:svmTracksOf,move:dzmMove,add:dzmAdd,remove:dzmRemove}`.

- [ ] **Étape 7 : CSS.** `son-vfx-montage.css:292` → `.svm-tl{flex:none; height:auto; min-height:312px; max-height:48vh; …}` (le reste de la règle inchangé ; `.svm-scroll` est déjà `overflow:auto`). `montage.css` : `.dzm-hb{display:flex;gap:2px}.dzm-hb button{…}` sur les tokens `--stroke`/`--ink2` de `son-vfx-montage.css`.
- [ ] **Étape 8 : le miroir du bundle.** `backend/tests/test_montage_bundle.py` : lit `frontend/dist/assets/index-BEOJX8L5.js` ; `check("bloc_montage_unique", s.count(BEGIN)==1 and s.count(END)==1)` ; pour chaque `(tag,a,r)` de `PATCHES` (importé du patcher avec `importlib`) : `check(tag+"_remplace", s.count(r)==1)` et, si `a` n'est pas préfixe de `r`, `check(tag+"_ancre_consommee", s.count(a)==0)` ; `check("node_check", subprocess.run(["node","--check",bundle]).returncode==0)` ; **cœur JS sous node** : écrire dans `TMP` un fichier `shim.js` = `var window={};var SVM_TRACK_BUS={};` + le contenu de `montage.js` + `console.log(JSON.stringify(window.DzMontage.move(window.DzMontage.tracksOf(null),"a3",-1).map(t=>t.id)))` puis `node shim.js` (jamais `node -e` : la ligne de commande Windows plafonne à 32 767 caractères) → attendu `["v2","v1","a1","a3","a2","s1"]` ; `check("js_move_v1_refuse", move("v1",-1) inchangé)` ; `add(...,"video")` → commence par `v3`.
- [ ] **Étape 9 : rejouer et mesurer.** `& $PY scripts\patch_bundle_montage.py --check ; & $PY scripts\patch_bundle_montage.py` → `OK — bundle patché … Size: …` ; `& $PY scripts\repatch_all.py --list` → dernière ligne `montage          OK` ; `& $PY tests\test_montage_bundle.py` → tout vert.
- [ ] **Étape 10 : au navigateur (backend démarré par l'utilisateur).** Montage → « + vidéo » ajoute V3 au-dessus de V2, ▲▼ déplacent A3 avant A2, × sur A3 vide la retire, la timeline défile verticalement à 8 pistes, un aperçu 480p avec deux overlays superposés montre celui du haut par-dessus (le banc [3] l'a prouvé au fichier ; ici on regarde la même chose dans le lecteur).
- [ ] **Étape 11 : commit.** `git add backend/app/services/montage_service.py backend/tests/test_montage_pistes_dyn.py backend/tests/test_montage_bundle.py frontend/patches/montage.js frontend/dist/shared/montage.css frontend/dist/shared/son-vfx-montage.css frontend/dist/index.html frontend/dist/assets/index-BEOJX8L5.js scripts/patch_bundle_montage.py; git commit -m 'montage : P1 - pistes dynamiques, ordre de composition au rendu' -m 'Payload tracks (haut vers bas) ; layer des overlays ; second clip musique au bus musique. Couche DzMontage et patcher montage en queue de chaine.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

### Tâche 3 — P2 : sous-titres animés mot par mot (rebond, glow, couleur ; emoji en option)

**Files :** modifier `backend/app/services/subtitle_service.py` (`to_ass`, nouveau `_word_events`), `subtitle_ui.py` (`ui_word_anim`), `montage_service._subs_ass` ; créer `backend/tests/test_subs_animes.py` ; section M10 du patcher (chip de style dans le tiroir n'est pas touchable → chip dans la barre d'outils du Montage : « mot : couleur / rebond / glow »).

- [ ] **Étape 1 : banc rouge.**

```python
# backend/tests/test_subs_animes.py — en-tête commun (env, FF, check, sh, frame, mean_rgb) puis :
from app.services import subtitle_service as S, subtitle_ui as SU, montage_service as M
UI = {"font": "Anton", "size": 52, "upper": True, "color": "#ffffff", "outOn": True, "outW": 4,
      "karOn": True, "karColor": "#ffd23f", "karMode": "fill", "anim": "none", "wordAnim": "rebond",
      "align": "center", "valign": "bottom", "marginV": 20, "width": 84, "maxChars": 30}
SEG = [{"start": 0.5, "end": 2.5, "text": "SOUS LA SURFACE",
        "words": [{"w": "SOUS", "start": 0.5, "end": 1.1}, {"w": "LA", "start": 1.1, "end": 1.5},
                  {"w": "SURFACE", "start": 1.5, "end": 2.5}]}]
print("\n[1] l'ASS porte un événement par mot, positionné et animé")
p, info = M._subs_ass({"style": UI, "segments": SEG}, (270, 480), "anim1")
txt = p.read_text(encoding="utf-8"); ev = [l for l in txt.splitlines() if l.startswith("Dialogue:")]
check("trois_evenements_mots", len(ev) == 3, str(len(ev)))
check("chaque_mot_pose", all("\\pos(" in l for l in ev))
check("chaque_mot_rebondit", all("\\t(0,120,\\fscx115\\fscy115)" in l for l in ev))
check("mot_2_commence_a_1s10", ev[1].split(",")[1] == "0:00:01.10", ev[1][:40])
check("info_word_anim", info.get("word_anim") == "rebond")
print("\n[2] miroir : un mot SEUL est plus GROS au sommet du rebond (130 ms) qu'une fois posé (400 ms)")
SEG1 = [{"start": 0.5, "end": 2.5, "text": "SURFACE", "words": [{"w": "SURFACE", "start": 0.5, "end": 2.5}]}]
p1, _ = M._subs_ass({"style": UI, "segments": SEG1}, (270, 480), "anim2")
out = os.path.join(TMP, "anim.mp4")
cmd, _ = M._build_montage_command(v1_spec(), [], [], None, w=270, h=480, fps=30, mix_db={}, ducking=False,
                                  duration_master=False, preview=False, out=out, subs_ass=p1)
r = sh(cmd); check("anim_ffmpeg_ok", r.returncode == 0, r.stderr[-300:])
def text_px(t):
    im = frame(out, t).convert("L"); w, h = im.size
    band = im.crop((0, int(h * .55), w, h)); return sum(1 for v in band.getdata() if v > 200)
a, b = text_px(0.63), text_px(0.9)          # 130 ms : ~113 % ; 400 ms : 100 % → aire ×1,28
check("rebond_plus_gros_au_debut", a > b * 1.15, f"{a} px à 130 ms, {b} px à 400 ms")
check("sans_wordAnim_ass_inchange", "\\pos(" not in M._subs_ass({"style": dict(UI, wordAnim="none"),
      "segments": SEG}, (270, 480), "anim0")[0].read_text(encoding="utf-8"))
```

- [ ] **Étape 2 : lancer → `FAIL trois_evenements_mots`.**
- [ ] **Étape 3 : implémenter.** `subtitle_ui.py` : `UI_WORD_ANIMS = {"none": "none", "couleur": "none", "rebond": "rebond", "glow": "glow"}` et `def ui_word_anim(ui): return UI_WORD_ANIMS.get(str((ui or {}).get("wordAnim") or "none"), "none")`. `subtitle_service.py` :

```python
WORD_ANIMS = ("none", "rebond", "glow")
_WORD_TAGS = {"rebond": "\\fscx70\\fscy70\\t(0,120,\\fscx115\\fscy115)\\t(120,220,\\fscx100\\fscy100)",
              "glow": "\\bord1\\t(0,160,\\bord6)\\t(160,320,\\bord2)"}

def _word_events(seg, st, name, canvas, scale, word_anim):
    """Un evenement ASS par mot : le mot apparait a son start, reste jusqu'a la
    fin de la replique, pose en \\pos a sa place dans la ligne centree. Les
    largeurs viennent de la MEME fonte que libass (_measure_px) ; sans PIL on
    rend [] et l'appelant retombe sur le karaoke \\k (dit dans info)."""
    W, H = int(canvas[0]), int(canvas[1])
    words = _normalize_words(seg.get("words"), seg.get("text", ""), _f(seg["start"]), _f(seg["end"]))
    if not words:
        return []
    up = bool(st["uppercase"])
    txts = [(w["w"].upper() if up else w["w"]) for w in words]
    sp = _measure_px(" ", st, scale)
    widths = [_measure_px(t, st, scale) for t in txts]
    if sp is None or any(x is None for x in widths):
        return []
    line_w = sum(widths) + sp * (len(widths) - 1)
    x0 = W / 2.0 - line_w / 2.0
    y = H - st["margin_v"] * scale if st["valign"] == "bottom" else (
        st["margin_v"] * scale if st["valign"] == "top" else H / 2.0)
    an = {"bottom": 1, "middle": 4, "top": 7}[st["valign"]]
    out, x = [], x0
    for w, t, wd in zip(words, txts, widths):
        tag = "{\\an%d\\pos(%d,%d)%s}" % (an, int(round(x)), int(round(y)), _WORD_TAGS.get(word_anim, ""))
        out.append(f"Dialogue: 1,{_ass_time(_f(w['start']))},{_ass_time(_f(seg['end']))},"
                   f"{name},,0,0,0,,{tag}{_ass_escape(t)}")
        x += wd + sp
    return out
```

Dans `to_ass(..., word_anim="none")` : pour chaque segment, si `word_anim != "none"` et `_word_events(...)` non vide → ces événements **remplacent** la ligne karaoké ; sinon ligne historique. Dans `_subs_ass` : `wa = SU.ui_word_anim(ui)`, passer `word_anim=wa`, `info["word_anim"] = wa`, et si `wa != "none"` et aucun `\pos` écrit → `info["unsupported"].append("wordAnim:mesure impossible (PIL/fonte)")`. `WrapStyle: 2` reste (les mots sont posés un à un, jamais repliés) — les répliques longues (> `chars_per_line`) passent en `\k` avec `info["word_anim_skipped"]` : un rebond sur trois lignes n'a pas de sens.

- [ ] **Étape 4 : lancer → `=== 8 passed, 0 failed ===`.**
- [ ] **Étape 5 : emoji par mot-clé (option).** `subtitle_service.EMOJI_HINTS = {"feu": "fire", "lune": "crescent_moon", "vague": "ocean", "poulpe": "octopus", "or": "coin", "fusée": "rocket"}` et `def emoji_hints(segments) -> [{t, png}]` qui lit `backend/assets/emoji/manifest.json` (Twemoji servi par `/emoji/<f>.png`) ; route `POST /api/subtitles/emoji-hints {segments}` ; la couche pose, sur la première piste vidéo d'overlay, un clip `{tr:"v2", src:{file_path:<png absolu>}, start:t, end:t+0.8, scale:0.18, x:0.5, y:0.62}` (chemin déjà accepté par `_resolve_src`). Test : `emoji_hints([{"text":"le feu sacré","start":1,"end":2,"words":[…]}])` → un item à `t==start du mot`, `png` existant.
- [ ] **Étape 6 : M10.** Ancre `A_M8` (déjà consommée par M8 → poser la chip **dans** `R_M8`, avant `TrackAdd`) : `r.jsx(DzMontage.WordAnimChip,{value:(proj.subsStyle||{}).wordAnim||"couleur",onChange:function(v){subsStyleSet({wordAnim:v})}}),`. `subsStyleSet` existe (S5). Rejouer : `--check`, patcher, `test_montage_bundle`, `node --check`.
- [ ] **Étape 7 : commit.** `git add backend/app/services/subtitle_service.py backend/app/services/subtitle_ui.py backend/app/services/montage_service.py backend/app/api/routes.py backend/tests/test_subs_animes.py frontend/patches/montage.js scripts/patch_bundle_montage.py frontend/dist/assets/index-BEOJX8L5.js; git commit -m 'montage : P2 - sous-titres animes mot par mot' -m 'Un événement ASS par mot (pos + t), rebond et glow mesurés à l image ; emoji par mot-clé posé en overlay.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

### Tâche 4 — P3 : montage par le texte (répliques et mots de remplissage)

**Files :** modifier `backend/app/services/transcribe_service.py` (`FILLERS`, `find_fillers`), `backend/app/api/routes.py` (`POST /subtitles/fillers`) ; créer `backend/tests/test_montage_texte.py` ; `montage.js` (`rippleCut` pur + tiroir « Texte ») ; sections M11–M12.

- [ ] **Étape 1 : banc rouge (backend + cœur JS sous node).**

```python
# backend/tests/test_montage_texte.py — en-tête commun, puis :
from app.services import transcribe_service as T
W = [{"i": 0, "w": "bon", "start": 0.0, "end": 0.3, "clip": "a1x"}, {"i": 1, "w": "euh", "start": 0.3, "end": 0.7, "clip": "a1x"},
     {"i": 2, "w": "la", "start": 0.7, "end": 0.9, "clip": "a1x"}, {"i": 3, "w": "marée", "start": 0.9, "end": 1.4, "clip": "a1x"},
     {"i": 4, "w": "hum", "start": 1.4, "end": 1.6, "clip": "a1x"}, {"i": 5, "w": "hum", "start": 1.6, "end": 1.8, "clip": "a1x"}]
f = T.find_fillers(W, "fr")
check("deux_plages", len(f) == 2, str(f))
check("plage_fusionnee", f[1]["start"] == 1.4 and f[1]["end"] == 1.8 and f[1]["words"] == [4, 5])
check("en_um_uh", [x["words"] for x in T.find_fillers([{"i": 0, "w": "um", "start": 0, "end": .2},
      {"i": 1, "w": "ok", "start": .2, "end": .4}, {"i": 2, "w": "uh", "start": .4, "end": .6}], "en")] == [[0], [2]])
check("mot_sans_temps_ignore", T.find_fillers([{"i": 0, "w": "euh"}], "fr") == [])
# cœur JS : couper [0.3, 0.7[ dans une timeline de 3 clips (V1 0-4, A1 0-2, A2 0-4 loop) + un s1 0.5-2.5
LAYER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "frontend", "patches", "montage.js")
shim = os.path.join(TMP, "shim.js")          # fichier, jamais `node -e` (32 767 caractères max sous Windows)
open(shim, "w", encoding="utf-8").write(
    'var window={};var SVM_TRACK_BUS={};' + open(LAYER, encoding="utf-8").read() +
    ';console.log(JSON.stringify(window.DzMontage.rippleCut(' + json.dumps([
    {"tr": "v1", "id": "v", "start": 0, "end": 4, "srcIn": 0}, {"tr": "a1", "id": "a", "start": 0, "end": 2, "srcIn": 0},
    {"tr": "a2", "id": "m", "start": 0, "end": 4, "srcIn": 0, "loop": True}, {"tr": "s1", "id": "s", "start": 0.5, "end": 2.5}]) +
    ',0.3,0.7,{loopTracks:["a2"]})))')
out = json.loads(subprocess.run(["node", shim], capture_output=True, text=True, encoding="utf-8").stdout)
byid = {c["id"]: c for c in out["clips"]}
check("v1_coupe_en_deux", sorted((c["start"], c["end"], c["srcIn"]) for c in out["clips"] if c["tr"] == "v1") == [(0, 0.3, 0), (0.3, 3.6, 0.7)])
check("a1_coupe_en_deux", sorted((c["start"], c["end"], c["srcIn"]) for c in out["clips"] if c["tr"] == "a1") == [(0, 0.3, 0), (0.3, 1.6, 0.7)])
check("musique_bouclee_raccourcie", byid["m"]["start"] == 0 and byid["m"]["end"] == 3.6)
check("sous_titre_decale_et_rogne", byid["s"]["start"] == 0.3 and byid["s"]["end"] == 2.1)
check("duree_retiree", out["removed"] == 0.4)
```

- [ ] **Étape 2 : lancer → `FAIL` (`find_fillers` absent, `rippleCut` absent).**
- [ ] **Étape 3 : backend.**

```python
FILLERS = {"fr": {"euh", "heu", "hum", "hmm", "bah", "ben", "hein", "voilà", "genre", "enfin", "quoi"},
           "en": {"um", "uh", "er", "erm", "hmm", "like", "okay", "so", "well", "right"}}

def find_fillers(words: list[dict], lang: str = "fr") -> list[dict]:
    """Plages de mots de remplissage, voisins fusionnes : [{start, end, words:[i]}].
    Un mot sans start/end n'est jamais une plage (on ne coupe pas a l'aveugle)."""
    bag = FILLERS.get(str(lang)[:2].lower(), FILLERS["fr"])
    out: list[dict] = []
    for w in words or []:
        if not isinstance(w, dict) or w.get("start") is None or w.get("end") is None:
            continue
        if _fold(str(w.get("w") or "")).strip(".,!?;:…") not in bag:
            continue
        s, e = round(float(w["start"]), 3), round(float(w["end"]), 3)
        if out and abs(out[-1]["end"] - s) < 0.02:
            out[-1]["end"] = e; out[-1]["words"].append(int(w.get("i", -1)))
        else:
            out.append({"start": s, "end": e, "words": [int(w.get("i", -1))]})
    return out
```

Route : `POST /api/subtitles/fillers {words?, segments?, lang}` → si `segments`, aplatir leurs `words` en `{i, w, start, end}` ; réponse `{ok, lang, spans, count}`.

- [ ] **Étape 4 : cœur JS.** Dans `montage.js` (avant tout composant) :

```javascript
/* coupe par plage [t0,t1[ sur TOUTES les pistes non verrouillées : ce qui est
   dedans disparaît, ce qui chevauche est fendu (srcIn suit, vitesse comprise),
   tout ce qui suit remonte de (t1−t0). Les pistes en boucle (musique) ne se
   fendent pas : elles raccourcissent. Pur : aucune lecture d'état. */
function dzmRippleCut(clips,t0,t1,opts){
  var loop=(opts&&opts.loopTracks)||[],locked=(opts&&opts.locked)||{},len=Math.round((t1-t0)*1000)/1000,out=[];
  function r3(v){return Math.round(v*1000)/1000}
  clips.forEach(function(c){
    if(locked[c.tr]){out.push(c);return}
    var sp=(typeof c.speed==="number"&&c.speed>0)?c.speed:1;
    if(loop.indexOf(c.tr)>=0){out.push(Object.assign({},c,{end:r3(Math.max(c.start,c.end-len))}));return}
    if(c.end<=t0){out.push(c);return}
    if(c.start>=t1){out.push(Object.assign({},c,{start:r3(c.start-len),end:r3(c.end-len)}));return}
    if(c.start<t0)out.push(Object.assign({},c,{end:r3(t0)}));
    if(c.end>t1){var k=Object.assign({},c,{id:c.start<t0?c.id+"_r":c.id,start:r3(t0),end:r3(c.end-len)});
      if(c.srcIn!=null||c.src)k.srcIn=r3((c.srcIn||0)+(t1-c.start)*sp);
      if(c.tr==="s1"&&Array.isArray(c.words))k.words=c.words.filter(function(w){return w.start>=t1||w.end<=t0});
      out.push(k)}});
  return {clips:out,removed:len}}
```

Export `rippleCut:dzmRippleCut`. Note : un clip fendu en deux garde son `id` à gauche, la moitié droite prend `id+"_r"` ; un clip seulement rogné à gauche garde son `id` (le banc lit `byid["s"]`).

- [ ] **Étape 5 : tiroir « Texte » (M11–M12).** Composant `DzMontage.TextDrawer({open, clips, onCut, note})` : à l'ouverture, `POST /api/subtitles/from-narration {clips}` (mots calés, gratuit) puis `POST /api/subtitles/fillers {words}` ; affiche le texte mot par mot (bouton par mot, `data-filler` sur les remplissages), sélection par clic-glisser (premier et dernier mot), boutons « Couper la sélection », « Retirer les N « euh » » (coupes appliquées de la fin vers le début pour ne pas décaler les suivantes). M11 : hook d'état + bouton dans la barre (dans `R_M8`) : `r.jsx("button",{className:"svm-toolchip","data-on":textOn?"":void 0,onClick:function(){setTextOn(!textOn)},children:"texte"})` ; M12 : montage du tiroir, ancre `A_M4` déjà consommée → poser le tiroir dans `R_M9b`… non : ancre **unique** dédiée `      narrPanel(),` est consommée par S9 ; utiliser `      subsDrawer(),` si présent une fois (mesurer avec `--check`), sinon `        transInspector(),`. La coupe : `onCut(t0,t1)` → `pushHistory(); var res=DzMontage.rippleCut(clipsRef.current,t0,t1,{loopTracks:svmTracksOf(proj).filter(t=>t.loop).map(t=>t.id),locked:…}); setClips(res.clips); setProj(p=>Object.assign({},p,{dur:Math.max(1,p.dur-res.removed)})); setDirty(!0)`.
- [ ] **Étape 6 : lancer le banc (vert), rejouer le patcher, `test_montage_bundle`, navigateur : « Retirer les euh » sur une narration transcrite raccourcit V1 et A1 ensemble, la tête reste calée.**
- [ ] **Étape 7 : commit.** `git commit -m 'montage : P3 - montage par le texte, coupe par plage' -m 'find_fillers FR/EN (plages fusionnées, jamais sans temps) ; rippleCut pur testé sous node : V1 et A1 fendus, musique raccourcie, S1 décalé.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

### Tâche 5 — P4 : étalonnage — quatre curseurs sous la LUT

**Files :** modifier `backend/app/services/effects_engine.py` (`_PARAM_DEFAULTS`, `_CATALOG`, `_grade_basic`, `EFFECTS`) ; créer `backend/tests/test_montage_etalonnage.py` ; section M13.

- [ ] **Étape 1 : banc rouge (miroir sur l'image).**

```python
# backend/tests/test_montage_etalonnage.py — en-tête commun, puis :
from app.services.effects_engine import build_chain, catalog
def render(eff, name):
    out = os.path.join(TMP, name + ".mp4")
    ch = build_chain([eff], "0:v", "vout", "u", {"w": 270, "h": 480, "dur": 4.0, "fps": 30})
    r = sh([FF, "-y", "-v", "error", "-i", V1, "-filter_complex", ";".join(ch), "-map", "[vout]", "-t", "1", "-pix_fmt", "yuv420p", out])
    return out if r.returncode == 0 else None
def ycc(path):
    im = frame(path, 0.5).convert("YCbCr"); px = list(im.getdata()); n = float(len(px))
    return tuple(sum(p[i] for p in px) / n for i in range(3))
spec = catalog().get("grade_basic")
check("catalogue_grade_basic", bool(spec) and spec["params"] == ["exposure", "contrast", "saturation", "temperature"], str(spec))
check("bornes_temperature", spec and spec["bounds"]["temperature"]["min"] == 2000 and spec["bounds"]["temperature"]["default"] == 6500)
ref = ycc(render({"type": "grade_basic"}, "neutre")); base = ycc(V1)
check("neutre_identique", all(abs(a - b) < 3 for a, b in zip(ref, base)), f"{ref} vs {base}")
e = ycc(render({"type": "grade_basic", "exposure": 60}, "expo"))
check("exposition_eclaircit", e[0] > ref[0] + 25, f"Y {e[0]:.1f} vs {ref[0]:.1f}")
s = ycc(render({"type": "grade_basic", "saturation": 0}, "sat0"))
check("saturation_zero_gris", abs(s[1] - 128) < 4 and abs(s[2] - 128) < 4, f"{s}")
w = mean_rgb(frame(render({"type": "grade_basic", "temperature": 3200}, "chaud"), 0.5))
c = mean_rgb(frame(V1, 0.5))
check("temperature_chaude_rougit", (w[0] - w[2]) > (c[0] - c[2]) + 20, f"{w} vs {c}")
ch = build_chain([{"type": "grade_basic", "temperature": 6500}], "0:v", "o", "u", {"w": 270, "h": 480, "dur": 4, "fps": 30})
check("6500K_n_emet_pas_colortemperature", "colortemperature" not in ";".join(ch), ";".join(ch))
```

- [ ] **Étape 2 : lancer → `FAIL catalogue_grade_basic`.**
- [ ] **Étape 3 : implémenter.** `_PARAM_DEFAULTS` reçoit `"exposure": {"type":"range","min":-100,"max":100,"step":1,"default":0,"label":"Exposition"}`, `"contrast": {…,"min":0,"max":200,"default":100,"label":"Contraste"}`, `"saturation": {…,"min":0,"max":200,"default":100,"label":"Saturation"}`, `"temperature": {…,"min":2000,"max":12000,"step":100,"default":6500,"label":"Température","unit":"K"}`. `_CATALOG["grade_basic"] = ("etalonnage", "Réglages de base", ["exposure","contrast","saturation","temperature"], "Exposition, contraste, saturation, température — sous la LUT.", {})` (placé juste après `"grade"`). Builder :

```python
def _grade_basic(eff, i, o, u, ctx):
    ex = _num(eff, "exposure", 0, -100, 100) / 200.0          # eq brightness −0,5..0,5
    ct = _num(eff, "contrast", 100, 0, 200) / 100.0
    sa = _num(eff, "saturation", 100, 0, 200) / 100.0
    k = int(_num(eff, "temperature", 6500, 2000, 12000))
    parts = [f"eq=brightness={ex:.3f}:contrast={ct:.3f}:saturation={sa:.3f}"]
    if k != 6500:
        parts.append(f"colortemperature=temperature={k}")
    return _one(i, o, ",".join(parts))
```

et `EFFECTS["grade_basic"] = _grade_basic`. La vignette du rack (`/api/effects/preview`) et les sliders viennent du catalogue : **rien d'autre**.

- [ ] **Étape 4 : lancer → `=== 7 passed, 0 failed ===`.**
- [ ] **Étape 5 : « global » (M13).** Dans `R_M9b`… non — bouton dans l'inspecteur : ancre `        transInspector(),` → `        DzMontage.gradeAllBtn(sel,clips,setClips,pushHistory,fireNote),\n        transInspector(),` : si le clip sélectionné porte un `grade_basic`, propose « Appliquer cet étalonnage à tous les plans V1 » (copie l'effet, remplace un `grade_basic` existant, historique une entrée). Rejouer patcher, `test_montage_bundle`.
- [ ] **Étape 6 : commit.** `git commit -m 'montage : P4 - etalonnage de base sous la LUT' -m 'grade_basic : eq + colortemperature (omis à 6500 K), bornes au catalogue ; mesuré : exposition, saturation nulle, chaud.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

### Tâche 6 — P5 : projets nommés (liste, ouvrir, dupliquer, renommer)

**Files :** modifier `backend/app/services/montage_service.py` (routes `/projects*`, `_projects_dir`, `_write_saved` miroir) ; créer `backend/tests/test_montage_projets.py` ; section M14.

- [ ] **Étape 1 : banc rouge (TestClient).**

```python
# backend/tests/test_montage_projets.py — en-tête commun + TestClient, puis :
with TestClient(app) as c:
    tl = {"name": "abysse", "ratio": "9:16", "duration": 4, "mix": {}, "clips": [{"tr": "v1", "id": "v", "start": 0, "end": 4, "src": {"file_path": V1}}]}
    check("save_courant", c.post("/api/montage/save", json=tl).status_code == 200)
    r = c.post("/api/montage/projects", json={"name": "Abysse v1"}); pid = r.json().get("id")
    check("creer_depuis_courant", r.status_code == 200 and pid and r.json()["clips"] == 1, r.text[:120])
    check("liste", [p["id"] for p in c.get("/api/montage/projects").json()["projects"]] == [pid])
    check("courant_porte_project_id", c.get("/api/montage/project").json().get("project_id") == pid)
    tl2 = dict(tl, project_id=pid, clips=tl["clips"] * 2); c.post("/api/montage/save", json=tl2)
    check("autosave_miroir", c.get(f"/api/montage/projects/{pid}").json()["clips"].__len__() == 2)
    r = c.post(f"/api/montage/projects/{pid}/duplicate"); did = r.json()["id"]
    check("dupliquer", did != pid and c.get(f"/api/montage/projects/{did}").json()["name"] == "Abysse v1 (copie)")
    check("renommer", c.patch(f"/api/montage/projects/{did}", json={"name": "Abysse v2"}).json()["name"] == "Abysse v2")
    check("ouvrir_change_le_courant", c.post(f"/api/montage/projects/{did}/open").status_code == 200 and c.get("/api/montage/project").json()["project_id"] == did)
    check("supprimer", c.delete(f"/api/montage/projects/{pid}").json()["deleted"] and len(c.get("/api/montage/projects").json()["projects"]) == 1)
    check("nom_hostile_reduit", c.post("/api/montage/projects", json={"name": "../x"}).json()["name"] == "x")
```

- [ ] **Étape 2 : lancer → `FAIL creer_depuis_courant` (404).**
- [ ] **Étape 3 : implémenter** (même mécanique que `/studio-graphs`, écriture atomique de `_write_saved`) :

```python
def _projects_dir() -> Path:
    d = settings.images_path.parent / "montage_projects"; d.mkdir(parents=True, exist_ok=True); return d

def _project_path(pid: str) -> Path:
    return _projects_dir() / f"{Path(str(pid)).name}.json"

def _write_json_atomic(path: Path, data: dict) -> None:
    tmp = path.with_name(f"{path.name}.{uuid4().hex[:8]}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8"); tmp.replace(path)

def _project_meta(d: dict) -> dict:
    return {"id": d.get("id"), "name": d.get("name"), "updated_at": d.get("saved_at"),
            "clips": len(d.get("clips") or []), "ratio": d.get("ratio"), "duration": d.get("duration")}

@router.get("/projects")
async def montage_projects():
    out = []
    for f in _projects_dir().glob("*.json"):
        try: out.append(_project_meta(json.loads(f.read_text(encoding="utf-8"))))
        except (OSError, ValueError): continue
    out.sort(key=lambda p: p.get("updated_at") or "", reverse=True)
    return {"ok": True, "projects": out}

@router.post("/projects")
async def montage_project_create(request: Request):
    """{name} : le COURANT (montage_saved.json) devient un projet nommé ; le
    courant reçoit project_id (l'autosave le mirrore ensuite)."""
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    cur = await asyncio.to_thread(_load_saved)
    if cur is None: raise HTTPException(400, "Aucune timeline courante à enregistrer.")
    pid = f"m_{uuid4().hex[:8]}"
    name = (Path(str(body.get("name") or cur.get("name") or "montage")).name.strip() or "montage")[:80]
    rec = dict(cur, id=pid, name=name, project_id=pid)
    await asyncio.to_thread(_write_json_atomic, _project_path(pid), rec)
    await asyncio.to_thread(_write_saved, rec)
    return {"ok": True, **_project_meta(rec)}
```

`GET /projects/{pid}` (404 sinon), `PATCH /projects/{pid}` `{name}`, `POST /projects/{pid}/duplicate` (nouvel id, `name + " (copie)"`), `POST /projects/{pid}/open` (copie le projet dans `montage_saved.json`), `DELETE /projects/{pid}`. `montage_save` : `data["project_id"] = str(body["project_id"])[:24]` si présent, et après `_write_saved`, si `project_id` → `_write_json_atomic(_project_path(pid), dict(data, id=pid))`. `montage_project` (GET) resserre `project_id`. **Sans `project_id`, rien ne change** (le banc P0 par la route reste vert).

- [ ] **Étape 4 : lancer → `=== 10 passed, 0 failed ===`.**
- [ ] **Étape 5 : M14.** Popover « Projets » dans `R_M8` : `r.jsx(DzMontage.Projects,{name:proj.name,projectId:proj.project_id,onOpen:function(d){svmApplyProject(d)},onNamed:function(pid,name){setProj(function(p){return Object.assign({},p,{project_id:pid,name:name})})},note:fireNote})` — liste (`GET`), « Enregistrer sous… » (`POST`), ouvrir (`POST /open` puis `GET /project` → `svmApplyProject`), dupliquer, renommer (champ inline), supprimer (confirmation inline `data-arm`, jamais de modale). `svmSavePayload` doit joindre `project_id` : ajouter à `R_M6` `project_id:proj.project_id,` ; `R_M7` joint `project_id:d.project_id,`. Rejouer, `test_montage_bundle`.
- [ ] **Étape 6 : commit.** `git commit -m 'montage : P5 - projets nommes' -m 'Dossier montage_projects, même mécanique que studio-graphs ; l autosave mirrore le projet ouvert ; sans project_id rien ne change.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

### Tâche 7 — P6 : remplacer un clip par sa nouvelle version

**Files :** modifier `backend/app/services/montage_service.py` (`GET /newer`) ; créer `backend/tests/test_montage_remplacer.py` ; sections M15–M16.

- [ ] **Étape 1 : banc rouge.** Backend : deux `JobRecord` `done` de même `title` « plan_01 » (le second `completed_at` plus récent, `final_video_path` = V1) + un troisième de titre différent → `GET /api/montage/newer?job_id=<premier>` → `{candidates:[{job_id:<second>,…}]}` ; `job_id` inconnu → `{candidates:[]}` ; le titre est comparé **sans** le suffixe « (aperçu 480p) » et sans casse (`check("titre_apercu_ignore", …)`). JS sous node : `window.DzMontage.replaceSrc(clip, {job_id:"j2"}, "plan_01 v2", 3.0)` sur `{tr:"v1",id:"v",start:2,end:8,srcIn:1,effects:[{type:"grain"}],transition:"fade"}` → `src` remplacé, `label` remplacé, `effects`/`transition`/`start`/`end` **intacts**, `srcIn` ramené à `0` et `end` à `5` quand la nouvelle source (3 s) ne couvre pas `srcIn + (end-start)`, `src_history` = `[{src:{…ancien}, label:"…", at:<ms>}]`, `warn` non vide dans ce cas.
- [ ] **Étape 2 : lancer → rouge.**
- [ ] **Étape 3 : backend** — `import re` en tête de `montage_service.py` ; `GET /newer` : `select(JobRecord).where(status == DONE, provider != "montage", id != job_id, completed_at > ref.completed_at)`, filtre Python `_norm_title(j.title) == _norm_title(ref.title)` avec `_norm_title = lambda t: re.sub(r"\s*\(aperçu 480p\)\s*$", "", str(t or "")).strip().lower()`, tri `completed_at` décroissant, 5 au plus, `{job_id, title, completed_at, duration_s}`. « Heuristique par le titre » est **dit** dans la réponse (`"origin": "heuristique"`, même vocabulaire que la Bibliothèque).
- [ ] **Étape 4 : cœur JS** (pur) :

```javascript
function dzmReplaceSrc(c,src,label,srcDur,now){
  var len=c.end-c.start,sp=(typeof c.speed==="number"&&c.speed>0)?c.speed:1,k=Object.assign({},c),warn="";
  k.src_history=(c.src_history||[]).concat([{src:c.src,label:c.label,at:now||Date.now()}]).slice(-10);
  k.src=src;k.label=label||c.label;
  if(srcDur>0&&(c.srcIn||0)+len*sp>srcDur+1e-3){k.srcIn=0;
    if(len*sp>srcDur){k.end=Math.round((c.start+srcDur/sp)*1000)/1000;warn="source plus courte : clip ramené à "+(srcDur/sp).toFixed(2)+" s"}
    else warn="fenêtre source ramenée au début"}
  return {clip:k,warn:warn}}
```

- [ ] **Étape 5 : M15–M16.** M15 : mode remplacement dans `addAsset` — ancre `  function addAsset(src,label,kind,srcDur,trId,atTime){` → même ligne suivie de `\n    if(dzmReplaceRef.current){var rc=dzmReplaceRef.current;dzmReplaceRef.current=null;setOvPick("");pushHistory();setClips(clipsRef.current.map(function(k){if(k.id!==rc)return k;var rr=DzMontage.replaceSrc(k,src,label,srcDur);if(rr.warn)fireNote(rr.warn);return rr.clip}));setDirty(!0);return}` ; `dzmReplaceRef` déclaré par M4b (`var dzmReplaceRef=x.useRef(null);` avant `svmTracksSet`). M16 : inspecteur (`        transInspector(),`, ancre déjà consommée par M13 → mettre le bouton **dans** `R_M13`) : « Remplacer la source… » arme `dzmReplaceRef.current=sel.id` puis `openPicker(sel.tr)` ; sous le bouton, `DzMontage.NewerHint({jobId:sel.src&&sel.src.job_id,onPick:…})` qui interroge `/newer` et propose « Version plus récente : <titre> — remplacer » ; « Revenir à la version précédente » quand `src_history` existe. Rejouer, `test_montage_bundle`.
- [ ] **Étape 6 : commit.** `git commit -m 'montage : P6 - remplacer la source d un clip' -m 'Mêmes bornes, mêmes effets, historique des sources ; candidats plus récents par titre (heuristique dite).' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

### Tâche 8 — P7 : lecture fluide — mesurer, précalculer, faire jouer toutes les pistes

**Files :** créer `scripts/qa/qa-montage-scrub.js`, `backend/app/services/montage_media.py`, `backend/tests/test_montage_media.py` ; modifier `montage_service.py` (routes `/peaks`, `/strip`, `/proxy`) ; sections M17–M19.

- [ ] **Étape 1 : mesurer d'abord.** `scripts/qa/qa-montage-scrub.js` (puppeteer-core, `CHROME` et `BASE` comme `qa-subs-consistency.js`) : ouvre Montage, attend `.svm-lanes`, puis pour 60 positions de la règle (`.svm-ruler`, `clientX` régulièrement espacés) fait `mouse.down/move/up` et mesure, par `page.evaluate`, l'intervalle entre deux `requestAnimationFrame` pendant 300 ms et le délai jusqu'au premier `timeupdate`/`seeked` du `<video>` visible ; imprime `scrub p50/p95 ms, seek p50/p95 ms, images/s`. Lancé **par l'utilisateur** avec le backend démarré : `node scripts/qa/qa-montage-scrub.js`. La valeur mesurée est consignée dans le commit de l'étape 6 ; **cible** : p95 des intervalles rAF < 33 ms, premier `seeked` < 150 ms.
- [ ] **Étape 2 : banc backend rouge.**

```python
# backend/tests/test_montage_media.py — en-tête commun, puis :
from app.services import montage_media as MM
pk = MM.peaks(MUS, bins=120)
check("pics_120", len(pk["peaks"]) == 120 and abs(pk["dur"] - 6.0) < 0.1)
check("pics_normalises_sinus", max(pk["peaks"]) == 1.0 and min(pk["peaks"]) > 0.8, f"{min(pk['peaks'])}")
SIL = os.path.join(TMP, "sil.wav"); sh([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=2", SIL])
check("silence_a_zero", max(MM.peaks(SIL, bins=20)["peaks"]) == 0.0)
check("cache_par_mtime", MM.peaks(MUS, bins=120) is not None and MM._cache_path(MUS, "peaks120").exists())
st = MM.strip(V1, n=6, w=78, h=44); im = Image.open(st)
check("filmstrip_6x", im.size == (468, 44), str(im.size))
px = MM.proxy(V1); kinds, dur = probe(px)
check("proxy_duree_source", abs(dur - 4.0) < 0.15, str(dur))
r = sh([FP, "-v", "error", "-select_streams", "v", "-show_entries", "stream=height", "-of", "csv=p=0", px])
check("proxy_hauteur_480", r.stdout.strip() == "480", r.stdout)
r = sh([FP, "-v", "error", "-skip_frame", "nokey", "-select_streams", "v", "-show_entries", "frame=pts_time", "-of", "csv=p=0", px])
check("proxy_gop_court", len([l for l in r.stdout.splitlines() if l.strip()]) >= 7, r.stdout[:80])   # 4 s × 30 i/s / g=15 → 8 clés
```

- [ ] **Étape 3 : implémenter `montage_media.py`.**

```python
"""Précalculs du Montage : pics d'onde, filmstrip, proxy 480p — mis en cache
sous outputs/montage_cache/<sha(path, mtime)>_<kind>.* ; stdlib + PIL."""
import array, hashlib, json, subprocess
from pathlib import Path
from app.config import settings

def _cache_path(src, kind: str) -> Path:
    p = Path(src); d = settings.outputs_path / "montage_cache"; d.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{p.resolve()}|{p.stat().st_mtime_ns}|{kind}".encode()).hexdigest()[:20]
    ext = {"proxy": ".mp4"}.get(kind.rstrip("0123456789"), ".json" if kind.startswith("peaks") else ".jpg")
    return d / f"{key}_{kind}{ext}"

def peaks(src, bins: int = 300, rate: int = 2000) -> dict:
    """Décodage ffmpeg en s8 mono `rate` Hz (2 000 o/s), max |x| par case,
    normalisé 0..1 (sinus plein → 1.0, silence → 0.0). Sans numpy : array('b')."""
    out = _cache_path(src, f"peaks{bins}")
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", str(rate),
                        "-f", "s8", "-"], capture_output=True, timeout=120)
    a = array.array("b"); a.frombytes(r.stdout)
    n = max(1, len(a)); step = max(1, n // bins); pk = []
    for i in range(bins):
        seg = a[i * step:(i + 1) * step] if i * step < n else array.array("b")
        pk.append(max((abs(int(v)) for v in seg), default=0))
    mx = max(pk) or 1
    data = {"peaks": [round(v / mx, 3) if mx > 1 else 0.0 for v in pk], "dur": round(n / float(rate), 3), "bins": bins}
    out.write_text(json.dumps(data), encoding="utf-8"); return data

def strip(src, n: int = 12, w: int = 78, h: int = 44) -> Path:
    out = _cache_path(src, f"strip{n}x{w}x{h}")
    if not out.exists():
        dur = max(0.1, _dur(src)); fps = max(0.01, n / dur)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf",
                        f"fps={fps:.4f},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},tile={n}x1",
                        "-frames:v", "1", "-q:v", "5", str(out)], check=True, timeout=180)
    return out

def proxy(src) -> Path:
    """480p, GOP 15 (une image clé toutes les 0,5 s : c'est ce qui rend le scrub
    instantané), veryfast/crf 28, audio copié en aac 96k."""
    out = _cache_path(src, "proxy")
    if not out.exists():
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", "scale=-2:480", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "28", "-g", "15", "-keyint_min", "15", "-sc_threshold", "0",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)],
                       check=True, timeout=600)
    return out
```

(`_dur` = copie locale de `_probe_duration`.) Routes dans `montage_service.py` : `GET /peaks?src=<json>&bins=` → `FileResponse` du JSON (`_resolve_src`, 404 sinon) ; `GET /strip?src=&n=&w=&h=` → JPEG ; `POST /proxy {src}` → job de fond (`JobRecord provider="montage_proxy"`, titre « proxy ») ; `GET /proxy?src=` → `FileResponse` du mp4 s'il existe, 404 sinon. Les `src` sont le vocabulaire du Montage (`job_id`/`audio`/`image`/`file_path`), jamais un chemin libre.

- [ ] **Étape 4 : lancer → `=== 8 passed, 0 failed ===`.**
- [ ] **Étape 5 : M17–M19.** M17 (ancre `function svmWavePeaks(src,cb){`) : avant le décodage WebAudio, `fetch("/api/montage/peaks?src="+encodeURIComponent(JSON.stringify(src))+"&bins=300")` ; si `Content-Type` JSON → `e.peaks/e.dur` et `fin(!0)` ; sinon chemin historique. M18 (ancre `function SvmFilmstrip(props){`) : la bande devient **une** `<img>` `/api/montage/strip?…&n=12` en `background-position` par vignette (plus d'extraction `<video>` par vignette). M19 (ancre `  x.useEffect(function(){liveSync()});`) : **pool audio** des clips A1/A2/A3 réels (éléments `<audio>` par source, cap 6) : à chaque `liveSync` en lecture, chaque clip audio sous la tête joue à `currentTime = srcIn + (t − start)` avec `volume = 10^((bus + gain)/20)` (musique bouclée : `loop=true`) ; à l'arrêt, pause. Le vu-mètre existant reste sur la voix. Et `livePoolGet` (ancre `  function livePoolGet(src,role){`) préfère `/api/montage/proxy?src=…` quand `HEAD` répond 200 (mémo par source), sinon la source. Rejouer, `test_montage_bundle`.
- [ ] **Étape 6 : re-mesurer** avec `qa-montage-scrub.js` (utilisateur) ; consigner avant/après dans le corps du commit. Si p95 reste > 33 ms, la cause n'est pas le média : profiler `liveSync` (un `console.time` par section) avant toute autre modification.
- [ ] **Étape 7 : commit.** `git commit -m 'montage : P7 - lecture fluide, precalculs et pistes audio en direct' -m 'Pics, filmstrip et proxy 480p GOP 15 en cache ; le lecteur vivant joue A1/A2/A3 aux gains de bus. Mesure scrub avant/après : <valeurs>.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

---

## Lot 2 — différenciant

### Tâche 9 — D1 : correspondance de couleur entre plans

**Files :** créer `backend/app/services/color_match.py`, `backend/tests/test_montage_couleur.py` ; modifier `effects_engine.py` (`colormatch`), `montage_service.py` (`POST /color-match`) ; section M20.

- [ ] **Étape 1 : banc rouge (miroir).**

```python
# backend/tests/test_montage_couleur.py — en-tête commun, puis :
from app.services import color_match as CM
ORG = os.path.join(TMP, "orange.mp4")
sh([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0xc06030:s=270x480:r=30:d=4", "-vf", "noise=alls=12:allf=t",
    "-pix_fmt", "yuv420p", ORG])
a, b = CM.frame_stats(V1, 2.0), CM.frame_stats(ORG, 2.0)
check("stats_ycc", set(a) == {"y", "u", "v"} and all(len(a[k]) == 2 for k in a))
eff = CM.match_effect(a, b)
check("effet_colormatch", eff["type"] == "colormatch" and 0.5 <= eff["y_gain"] <= 2.0)
out = os.path.join(TMP, "matched.mp4")
from app.services.effects_engine import build_chain
ch = build_chain([eff], "0:v", "vout", "u", {"w": 270, "h": 480, "dur": 4, "fps": 30})
sh([FF, "-y", "-v", "error", "-i", ORG, "-filter_complex", ";".join(ch), "-map", "[vout]", "-t", "1", "-pix_fmt", "yuv420p", out])
m = CM.frame_stats(out, 0.5)
check("moyennes_alignees_6_sur_255", all(abs(m[k][0] - a[k][0]) < 6 for k in "yuv"), f"{m} vs {a}")
check("sans_effet_rien_ne_bouge", "lutyuv" not in ";".join(build_chain([{"type": "grain"}], "0:v", "o", "u", {"w": 270, "h": 480, "dur": 4, "fps": 30})))
```

- [ ] **Étape 2 : lancer → `FAIL` (module absent).**
- [ ] **Étape 3 : implémenter.**

```python
"""Correspondance de couleur entre deux plans — statistiques YCbCr par plan
(PIL, pas de numpy) et transfert affine par canal (Reinhard réduit : gain =
écart-type réf / cible borné 0,5..2, décalage = moyenne réf − moyenne cible ×
gain), émis en `lutyuv` : il agit directement en yuv420p, sans conversion."""
import os, subprocess, tempfile
from PIL import Image, ImageStat

def frame_stats(path, t: float = 1.0) -> dict:
    png = os.path.join(tempfile.mkdtemp(prefix="dzcm_"), "f.png")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", str(path), "-frames:v", "1",
                    "-vf", "scale=96:-2", png], check=True, timeout=60)
    st = ImageStat.Stat(Image.open(png).convert("YCbCr"))
    return {k: (round(st.mean[i], 2), round(st.stddev[i], 2)) for i, k in enumerate("yuv")}

def match_effect(ref: dict, tgt: dict) -> dict:
    out = {"type": "colormatch"}
    for k in "yuv":
        (mr, sr), (mt, stt) = ref[k], tgt[k]
        g = 1.0 if stt < 1.0 or sr < 1.0 else max(0.5, min(2.0, sr / stt))
        out[f"{k}_gain"] = round(g, 3); out[f"{k}_off"] = round(mr - mt * g, 1)
    return out
```

`effects_engine` : `_CATALOG["colormatch"] = ("etalonnage", "Accord de couleur", ["y_gain","y_off","u_gain","u_off","v_gain","v_off"], "Aligne ce plan sur les statistiques d'un autre (bouton de l'inspecteur).", {})`, bornes `*_gain` 0.5..2 (step .01, défaut 1), `*_off` −128..128 (défaut 0) ; builder `_one(i, o, "lutyuv=y='clip(val*%s+%s,0,255)':u='clip(val*%s+%s,0,255)':v='clip(val*%s+%s,0,255)'" % (...))`. Route `POST /api/montage/color-match {ref:{src,t?}, target:{src,t?}}` → `{ok, effect, ref, target}` (`_resolve_src`, `asyncio.to_thread`).

- [ ] **Étape 4 : lancer → `=== 4 passed, 0 failed ===`.**
- [ ] **Étape 5 : M20** (dans `R_M13`, inspecteur) : bouton « Accorder sur le plan précédent » — `svmLeftNeighbor(clips, sel)` fournit la référence ; l'effet reçu remplace un `colormatch` existant dans `sel.effects` ; la vignette du rack le prévisualise (catalogue). Rejouer, `test_montage_bundle`.
- [ ] **Étape 6 : commit.** `git commit -m 'montage : D1 - accord de couleur entre plans' -m 'Statistiques YCbCr par plan (PIL), transfert affine en lutyuv ; mesuré : moyennes alignées à 6/255.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

### Tâche 10 — D2 : recadrage multi-format — mesurer, tabler, trancher

**Files :** créer `backend/app/services/reframe.py`, `backend/tests/test_montage_reframe.py` ; modifier `montage_service.py` (champ `reframe` sur V1, `POST /reframe`, `ratio` de rendu) ; section M21.

- [ ] **Étape 1 : la mesure qui tranche.** Le suivi de sujet « pro » (détection de visage) demande un modèle hors stdlib (même constat que CLAP en R4). Trois voies, mesurées ici :

| Voie | Coût | Dépendance | Ce que le banc mesure |
|---|---|---|---|
| **Énergie de mouvement PIL** (différence d'images à 4 i/s en 96 px, barycentre des colonnes, lissage EMA) | 0 € | aucune | erreur ≤ 8 % de la largeur sur un carré qui traverse le cadre ; centre quand rien ne bouge |
| Service local optionnel (patron Voicebox, `127.0.0.1:<port>/track`) | 0 € | à installer par l'utilisateur, **inexistant aujourd'hui** | rien à mesurer — non retenu tant qu'aucun service n'existe |
| Reframe génératif fal (Luma Ray 2, Wan VACE `human`, LTX-2.3 — vérifiés 03/09) | payant **par clip**, prix à relever au moment de l'exécution (`pricing.py`) | clé fal | invente les bords : option, jamais défaut (E2) |

**Règle** : si `erreur_max ≤ 8 %` sur le banc synthétique → « suivi » est le mode par défaut des plans avec mouvement ; sinon « centré réglable ». Le résultat du banc est recopié dans cette table au commit.

- [ ] **Étape 2 : banc rouge.**

```python
# backend/tests/test_montage_reframe.py — en-tête commun, puis :
from app.services import reframe as RF
MOV = os.path.join(TMP, "move.mp4")   # carré clair 60 px qui traverse 480×270 en 4 s (overlay : x/y acceptent t ; drawbox non)
sh([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x202020:s=480x270:r=30:d=4",
    "-f", "lavfi", "-i", "color=c=0xe0e0e0:s=60x60:r=30:d=4",
    "-filter_complex", "[0:v][1:v]overlay=x='40+t*95':y=105:shortest=1", "-pix_fmt", "yuv420p", MOV])
tr = RF.motion_track(MOV, fps=4)
check("points_4_par_seconde", 12 <= len(tr["points"]) <= 16 and tr["mode"] == "suivi", str(len(tr["points"])))
err = max(abs(p["x"] - (40 + p["t"] * 95 + 30) / 480.0) for p in tr["points"] if 0.5 <= p["t"] <= 3.5)
check("erreur_max_sous_8_pct", err <= 0.08, f"{err:.3f}")
st = RF.motion_track(V1, fps=4)
check("statique_centre", st["mode"] == "centre" and all(abs(p["x"] - 0.5) < 1e-6 for p in st["points"]))
print("\n[2] miroir : rendu 9:16 d'une source 16:9 avec le suivi — le carré reste dans le cadre")
out = os.path.join(TMP, "reframed.mp4")
v1 = [dict(v1_spec()[0], path=MOV, reframe={"mode": "suivi", "points": tr["points"]})]
cmd, _ = M._build_montage_command(v1, [], [], None, w=152, h=270, fps=30, mix_db={}, ducking=False,
                                  duration_master=False, preview=False, out=out)
r = sh(cmd); check("reframe_ffmpeg_ok", r.returncode == 0, r.stderr[-300:])
for t in (0.8, 2.0, 3.2):
    im = frame(out, t).convert("L"); w, h = im.size
    bright = [x for x in range(w) if max(im.getpixel((x, y)) for y in range(h // 2 - 2, h // 2 + 3)) > 150]
    check(f"carre_visible_t{t}", bright and 8 < sum(bright) / len(bright) < w - 8, f"{bright[:3]}…{bright[-3:]}" if bright else "aucun")
check("sans_reframe_commande_intacte", "crop=152:270:x=" not in " ".join(M._build_montage_command(
    [dict(v1_spec()[0], path=MOV)], [], [], None, w=152, h=270, fps=30, mix_db={}, ducking=False,
    duration_master=False, preview=False, out=out)[0]))
```

- [ ] **Étape 3 : implémenter `reframe.py`.**

```python
"""Suivi de sujet par énergie de mouvement, sans numpy : images grises 96 px à
`fps` i/s (ffmpeg → PNG), différence absolue entre voisines (ImageChops), puis
l'image est RÉDUITE à une ligne (resize BOX) : chaque pixel est la moyenne de
sa colonne. Barycentre des colonnes au-dessus du bruit, lissé (EMA 0,5)."""
import os, subprocess, tempfile
from PIL import Image, ImageChops

def _frames(path, fps, width=96):
    d = tempfile.mkdtemp(prefix="dzrf_")
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={fps},scale={width}:-2,format=gray",
                    os.path.join(d, "f%04d.png")], check=True, timeout=300)
    return [os.path.join(d, f) for f in sorted(os.listdir(d))]

def motion_track(path, fps: int = 4, noise: int = 12) -> dict:
    files = _frames(path, fps)
    prev, pts, ema, seen = None, [], None, False
    for k, f in enumerate(files):
        im = Image.open(f).convert("L")
        if prev is not None:
            row = list(ImageChops.difference(im, prev).resize((im.width, 1), Image.BOX).getdata())
            tot = sum(v for v in row if v > noise)
            if tot > 0:
                cx = sum(x * v for x, v in enumerate(row) if v > noise) / tot / (im.width - 1); seen = True
                ema = cx if ema is None else 0.5 * ema + 0.5 * cx
        pts.append({"t": round(k / float(fps), 3), "x": round(ema if ema is not None else 0.5, 4)})
        prev = im
    return {"mode": "suivi" if seen else "centre", "points": pts, "fps": fps}
```

`montage_service` : champ V1 optionnel `reframe: {mode: "centre"|"suivi"|"manuel", x?: 0..1, points?: [{t,x}]}` sanitizé par `_reframe_of(c)` (bornes, max 240 points, `t` en secondes **source** — le tracker tourne sur la fenêtre `srcIn..srcIn+d_src`) ; dans `_build_montage_command`, quand `s.get("reframe")` : `crop={w}:{h}:x='clip(iw*({EXPR})-{w}/2,0,iw-{w})':y=(ih-{h})/2` (le sujet au centre de la fenêtre, borné aux bords) remplace `crop={w}:{h}` dans `pre`, `EXPR` = `_mp_lerp_expr([(t, x)…])` (temps local à l'entrée trimée : `-ss` avant `-i` remet `t` à 0) ou la constante `x`. Sans champ, `pre` reste octet pour octet. Route `POST /api/montage/reframe {src, srcIn, dur, fps?}` → `motion_track` sur la fenêtre (via `-ss/-t` ajoutés à `_frames`).

- [ ] **Étape 4 : lancer, lire l'erreur mesurée, recopier dans la table, trancher selon la règle. Attendu : `=== 8 passed, 0 failed ===`.**
- [ ] **Étape 5 : M21** — popover « Formats » dans `R_M8` : choisir 1:1 / 16:9 / 4:5 → pour chaque clip V1 réel `POST /reframe` (mode suivi ou centre, réglable par clip : curseur `x` en mode « manuel » dans l'inspecteur, section `R_M13`), puis `POST /render` avec `ratio` cible, les `reframe` joints et `name + " · " + ratio` ; overlays et S1 sont en fractions du canevas et suivent. Option « reframe génératif fal » : lien vers le nœud existant, **jamais** lancé d'ici (E2). Rejouer, `test_montage_bundle`.
- [ ] **Étape 6 : commit.** `git commit -m 'montage : D2 - recadrage multi-format avec suivi mesure' -m 'Suivi par énergie de mouvement (PIL, sans numpy) : erreur max <valeur> sur le banc synthétique → mode <retenu>. Crop animé par _mp_lerp_expr, commande intacte sans le champ.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

### Tâche 11 — D3 : auto-clips depuis épisodes, films et vidéos externes

**Files :** créer `backend/app/services/autoclips.py`, `backend/tests/test_montage_autoclips.py` ; modifier `montage_service.py` (`POST /autoclips`, `POST /autoclips/create`) ; section M22.

- [ ] **Étape 1 : banc rouge (LLM factice injecté — aucun réseau).**

```python
# backend/tests/test_montage_autoclips.py — en-tête commun, puis :
from app.services import autoclips as AC
from app.services import transcribe_service as T
TXT = ("Sous la surface quelque chose remue. La marée ne demande pas la permission. Huit bras une seule volonté. "
       "Le prophète des profondeurs a parlé. La houle porte déjà son nom. Personne ne dort cette nuit. ") * 6
words = T.align_known_text(TXT, start=0.0, end=120.0)["words"]
wins = AC.windows(words, min_s=15, max_s=60, step_s=5)
check("fenetres_bornees", wins and all(15 <= w["end"] - w["start"] <= 60 for w in wins), str(len(wins)))
check("fenetres_sur_phrases", all(w["text"].rstrip().endswith((".", "!", "?")) for w in wins))
fake = lambda prompt, system, max_tokens: ('[{"i": 0, "score": 91, "title": "La marée", "hook": "Elle ne demande pas"},'
                                           '{"i": 3, "score": 40, "title": "x", "hook": "y"}]', "fake")
res = AC.score(wins, llm=fake, n=3, persona="prophet")
check("tri_par_score", [c["score"] for c in res["clips"]] == [91, 40] and res["source"] == "llm:fake")
bad = lambda p, s, m: ("pas du json", "fake")
res2 = AC.score(wins, llm=bad, n=3)
check("json_casse_repli_heuristique", res2["source"] == "heuristique" and len(res2["clips"]) == 3)
check("heuristique_deterministe", AC.heuristic(wins) == AC.heuristic(wins))
c0 = res["clips"][0]
check("clip_porte_segments_sous_titres", c0["segments"] and c0["segments"][0]["start"] >= c0["start"])
```

- [ ] **Étape 2 : lancer → rouge (module absent).**
- [ ] **Étape 3 : implémenter.** `windows(words, min_s, max_s, step_s)` : phrases = suites de mots jusqu'à une ponctuation forte (`punct` de `align_known_text`) ; fenêtres = concaténations de phrases consécutives dont la durée tient dans `[min_s, max_s]`, en glissant de `step_s` (dédoublonnées par `(start,end)`), chacune `{i, start, end, text, words}`. `heuristic(wins)` : score = 40 + 15·(a un `?`) + 10·(chiffre) + 5·mots-clés persona (`deepotus`, `abysse`, `marée`, `prophète`) − pénalité de longueur > 45 s, borné 0..100, **déterministe**. `score(wins, llm=None, n=4, persona=None)` : `llm` = `summarizer._chat_dispatch` par défaut ; prompt système « Tu es le monteur de <persona> » + consigne JSON strict `[{i, score, title, hook}]`, `max_tokens=800` ; parse `json.loads` (tolère un bloc ```json) ; toute erreur → `heuristic` ; tri `clips.sort(key=lambda c: -c["score"])` puis coupe à `n` ; réponse `{clips:[{start,end,score,title,hook,segments}], source}` où `segments = T.group_words(w["words"], max_chars=30)` normalisés (`_subs_cues_to_segments`). Route `POST /api/montage/autoclips {src, text?, lang, n, confirm?}` : si `text` (épisode : `Chapter.script_text` via `chapter_id`, ou narration) → `T.align_to_audio` (**gratuit**) ; sinon `T.estimate_transcription` d'abord et `{ok:false, estimate}` tant que `confirm` n'est pas vrai, puis `T.transcribe`. `POST /autoclips/create {src, clip, style?}` : crée un **projet nommé** (P5) — V1 = `{src, srcIn:start, start:0, end:dur}`, A1 « son du plan » si la source a de l'audio, S1 = `clip.segments` décalés de `−start`, `subs_style` avec `wordAnim:"rebond"` (P2) — et renvoie `{project_id}` ; « Envoyer au Scheduler » réutilise le `POST /api/schedule` déjà appelé après un rendu final (`hook` = `clip.hook`).
- [ ] **Étape 4 : lancer → `=== 6 passed, 0 failed ===`.**
- [ ] **Étape 5 : M22** — tiroir « Auto-clips » (bouton dans `R_M8`) : source = clip V1 sélectionné, un job de la Bibliothèque (`/api/jobs`, `provider` ∈ `episode|montage|ugc`) ou un fichier (`POST /videos/upload`) ; estimation affichée **avant** toute transcription payante (convention de l'app) ; liste des propositions (score, titre, hook, durée) ; « Créer le projet » → `POST /autoclips/create` puis ouverture (P5). Rejouer, `test_montage_bundle`.
- [ ] **Étape 6 : commit.** `git commit -m 'montage : D3 - auto-clips scores' -m 'Fenêtres sur phrases 15–60 s, score LLM (JSON strict, repli heuristique déterministe dit), projet nommé par clip avec sous-titres animés.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

### Tâche 12 — D4 : titres animés et transitions dynamiques dans la charte

**Files :** créer `backend/app/services/titles.py`, `backend/tests/test_montage_titres.py` ; modifier `montage_service.py` (`_XFADE`, `titles_ass`), `frontend/dist/shared/montage.css` ; sections M23–M24.

- [ ] **Étape 1 : banc rouge.**

```python
# backend/tests/test_montage_titres.py — en-tête commun, puis :
from app.services import titles as TT
print("\n[1] transitions : zoom, whip, morph acceptées par ffmpeg 8.1.1")
for name, xf in (("zoom", "zoomin"), ("whip", "hlwind"), ("morph", "hblur")):
    v1 = v1_spec() + [dict(v1_spec()[0], start=4.0, end=8.0, transition=name, transition_s=0.4)]
    out = os.path.join(TMP, f"tr_{name}.mp4")
    cmd, total = M._build_montage_command(v1, [], [], None, w=270, h=480, fps=30, mix_db={}, ducking=False,
                                          duration_master=False, preview=False, out=out)
    check(f"xfade_{name}", f"xfade=transition={xf}:" in " ".join(cmd) and sh(cmd).returncode == 0)
    check(f"duree_{name}", abs(probe(out)[1] - 7.6) < 0.15, str(probe(out)[1]))
print("\n[2] titre : un lower-third gravé SOUS les sous-titres, visible dans sa bande")
p = TT.to_ass_title({"preset": "lower_third", "text": "DEEPOTUS", "sub": "from the deep", "start": 1.0, "end": 3.0}, (270, 480))
txt = p.read_text(encoding="utf-8")
check("titre_fonte_embarquee", ",Bebas Neue," in txt and "\\move(" in txt and "\\fad(" in txt)
check("titre_couleur_de_marque", "&H003CB2E6" in txt)               # #e6b23c en BGR ASS
out = os.path.join(TMP, "title.mp4")
cmd, _ = M._build_montage_command(v1_spec(), [], [], None, w=270, h=480, fps=30, mix_db={}, ducking=False,
                                  duration_master=False, preview=False, out=out, titles_ass=[p])
fc = cmd[cmd.index("-filter_complex") + 1]
check("titre_avant_les_sous_titres", fc.split(";")[-1].startswith("[tt0]") or "subtitles=" in fc.split(";")[-2], fc[-200:])
sh(cmd); im = frame(out, 2.0).convert("L"); w, h = im.size
band = sum(1 for v in im.crop((0, int(h * .7), w, int(h * .9))).getdata() if v > 200)
top = sum(1 for v in im.crop((0, 0, w, int(h * .2))).getdata() if v > 200)
check("texte_dans_le_tiers_bas", band > 150 and top < 20, f"bas {band}, haut {top}")
check("sans_titre_commande_intacte", "titles" not in " ".join(M._build_montage_command(v1_spec(), [], [], None, w=270, h=480, fps=30, mix_db={}, ducking=False, duration_master=False, preview=False, out=out)[0]))
```

- [ ] **Étape 2 : lancer → rouge.**
- [ ] **Étape 3 : implémenter.** `_XFADE` gagne `"zoom": ("zoomin", None), "whip": ("hlwind", None), "morph": ("hblur", None)` (« morph » est un fondu flouté — c'est dit dans le libellé UI : « morph (fondu flouté) »). `titles.py` :

```python
"""Titres animés dans la charte : ASS écrit avec les fontes EMBARQUÉES et les
couleurs de DESIGN.md (or de marque #e6b23c, cyan #00e5ff, encre #14181d),
gravé par le même filtre `subtitles=` que S1, AVANT S1 (le sous-titre passe
au-dessus). Tout est mesurable à l'image."""
from pathlib import Path
from app.config import settings
from app.services import subtitle_service as S

BRAND = {"or": "#e6b23c", "cyan": "#00e5ff", "encre": "#14181d", "blanc": "#eef2f6"}
PRESETS = {
    "lower_third": {"font": "Bebas Neue", "size": 64, "color": "blanc", "box": "or", "an": 1, "y": 0.80,
                    "anim": "\\move({x0},{y},{x1},{y},0,260)\\fad(200,200)"},
    "titre_plein": {"font": "Anton", "size": 120, "color": "or", "box": None, "an": 5, "y": 0.50,
                    "anim": "\\fscx80\\fscy80\\t(0,300,\\fscx100\\fscy100)\\fad(150,300)"},
    "fin":         {"font": "Bebas Neue", "size": 72, "color": "cyan", "box": "encre", "an": 2, "y": 0.92,
                    "anim": "\\fad(400,0)"},
}

def to_ass_title(spec: dict, canvas: tuple[int, int]) -> Path:
    pr = PRESETS[str(spec.get("preset") or "lower_third")]
    W, H = int(canvas[0]), int(canvas[1]); k = H / float(S.REF_HEIGHT)
    st = S.resolve_style({"font": pr["font"], "size": pr["size"], "color": BRAND[pr["color"]],
                          "back_mode": "wrap" if pr["box"] else "none",
                          "back_color": BRAND[pr["box"]] if pr["box"] else "#000000", "back_opacity": 0.9,
                          "outline": 0, "shadow": 0, "align": "left" if pr["an"] in (1, 4, 7) else "center",
                          "valign": "bottom", "margin_v": 0, "margin_h": 0, "uppercase": 1})
    y = int(H * pr["y"]); x1 = int(W * 0.08) if pr["an"] == 1 else W // 2
    anim = pr["anim"].format(x0=-W // 2, x1=x1, y=y)
    pose = "" if "\\move(" in anim else f"\\pos({x1},{y})"     # \pos et \move s'excluent
    text = S._ass_escape(str(spec.get("text") or "")).upper()
    if spec.get("sub"):
        text += "\\N{\\fs%d\\c%s}" % (int(pr["size"] * 0.45), S._ass_color(BRAND["encre"] if pr["box"] else BRAND["blanc"])) + S._ass_escape(str(spec["sub"]))
    head = ["[Script Info]", "ScriptType: v4.00+", "WrapStyle: 2", "ScaledBorderAndShadow: yes",
            f"PlayResX: {W}", f"PlayResY: {H}", "", "[V4+ Styles]", S._ASS_FORMAT_STYLE,
            S._ass_style_line("T1", st, k, False), "", "[Events]", S._ASS_FORMAT_EVENT,
            f"Dialogue: 0,{S._ass_time(float(spec['start']))},{S._ass_time(float(spec['end']))},T1,,0,0,0,,"
            f"{{\\an{pr['an']}{pose}{anim}}}{text}"]
    d = settings.outputs_path / "subtitles"; d.mkdir(parents=True, exist_ok=True)
    p = d / f"title_{hashlib.sha1((str(sorted(spec.items())) + str(canvas)).encode()).hexdigest()[:10]}.ass"
    p.write_text("\n".join(head) + "\n", encoding="utf-8", newline="\n"); return p
```

(`import hashlib` en tête.) `_build_montage_command(..., titles_ass=None)` : après le maître de durée et les overlays, avant S1 : `for j, t in enumerate(titles_ass or []): parts.append(f"[{cur}]{subtitles_filter(t)}[tt{j}]"); cur = f"tt{j}"`. `montage_render` : les clips `{tr:"v<n>", kind:"title", title:{preset,text,sub}, start, end}` (sans `src`, donc **non** filtrés par `_resolve_src`) deviennent `titles_ass` triés par piste puis par `start`.

- [ ] **Étape 4 : lancer → `=== 11 passed, 0 failed ===`.**
- [ ] **Étape 5 : M23–M24.** M23 (ancre `var SVM_TRANS=[["cut","coupe sèche"],["fade","fondu"],["dissolve","dissolution"],`) → même ligne + `["zoom","zoom"],["whip","whip (balayage)"],["morph","morph (fondu flouté)"],`. M24 : galerie « Titres » (bouton dans `R_M8`) : trois cartes (aperçu = `/api/montage/title-preview?preset=&text=` → PNG rendu par ffmpeg sur fond `--srf-app`, 1 s en cache), champs texte/sous-texte, « Poser à la tête » → clip `{tr:<première piste vidéo d'overlay>, kind:"title", title:{…}, start:ph, end:ph+3, label:text}` ; `renderPayload` doit **garder** ces clips sans `src` : modifier `R_M5` pour `clips.filter(function(c){return c.src||c.kind==="title"})`. Le lecteur vivant les montre en HTML (`DzMontage.TitleOverlay`, mêmes tokens) ; l'aperçu 480p fait foi. Rejouer, `test_montage_bundle`.
- [ ] **Étape 6 : commit.** `git commit -m 'montage : D4 - titres animes et transitions dynamiques' -m 'Trois presets ASS en fontes embarquées et couleurs de la charte, gravés avant S1 ; zoomin/hlwind/hblur mesurés sur ffmpeg 8.1.1.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

### Tâche 13 — D5 : export EDL / FCPXML (relire la spec d'abord)

**Files :** créer `backend/app/services/edl_export.py`, `backend/tests/test_montage_export.py` ; modifier `montage_service.py` (`GET /export`) ; section M25.

- [ ] **Étape 1 : relire la spec — WebFetch exact, avant d'écrire une ligne.** `WebFetch("https://developer.apple.com/documentation/professional-video-applications/fcpxml-reference", "Liste les éléments et attributs de resources/format, resources/asset, library/event/project/sequence/spine/asset-clip et le format des durées (rationnels en s). Quelle est la dernière version de fcpxml ?")`. Consigner dans la docstring de `edl_export.py` : version (`1.11` de mémoire — **à remplacer par la valeur lue**), noms d'attributs confirmés, format `"<num>/<den>s"`. Si la page ne rend rien (docs JS), second essai sur `https://developer.apple.com/documentation/professional-video-applications/fcpxml-reference/story-elements` puis, à défaut, garder « de mémoire » **écrit dans la docstring** et prévoir l'import Resolve de l'étape 6 comme seule preuve.
- [ ] **Étape 2 : banc rouge.**

```python
# backend/tests/test_montage_export.py — en-tête commun, puis :
import re, xml.etree.ElementTree as ET
from app.services import edl_export as EX
PRJ = {"name": "abysse", "ratio": "9:16", "duration": 9.0, "clips": [
    {"tr": "v1", "id": "a", "label": "plan_01", "start": 0.0, "end": 4.0, "srcIn": 1.0, "src": {"file_path": V1}, "transition": "cut"},
    {"tr": "v1", "id": "b", "label": "plan_02", "start": 4.0, "end": 9.0, "srcIn": 0.0, "src": {"file_path": V1}, "transition": "fade", "transition_s": 0.4},
    {"tr": "a1", "id": "c", "label": "voice", "start": 0.5, "end": 2.5, "srcIn": 0.0, "src": {"file_path": VOX}},
    {"tr": "v2", "id": "t", "kind": "title", "title": {"preset": "lower_third", "text": "X"}, "start": 1, "end": 3}]}
paths = {"a": V1, "b": V1, "c": VOX}
edl = EX.to_edl(PRJ, paths, fps=30)
lines = edl.splitlines()
check("edl_titre", lines[0] == "TITLE: abysse" and lines[1] == "FCM: NON-DROP FRAME")
check("edl_evenement_1", re.match(r"^001  AX       V     C        00:00:01:00 00:00:05:00 00:00:00:00 00:00:04:00$", lines[2]), lines[2])
check("edl_nom_de_clip", "* FROM CLIP NAME: plan_01" in edl and "* SOURCE FILE: " in edl)
check("edl_audio_sur_piste_a", any(re.match(r"^003  AX       A     C        00:00:00:00 00:00:02:00 00:00:00:15 00:00:02:15$", l) for l in lines), edl)
check("edl_titre_ignore", "* SKIPPED: title X" in edl and not any(l.startswith("004 ") for l in lines))
x = EX.to_fcpxml(PRJ, paths, fps=30); root = ET.fromstring(x)
check("fcpxml_bien_forme", root.tag == "fcpxml" and root.get("version"))
res = {r.get("id"): r for r in root.find("resources")}
clips = root.findall(".//spine/asset-clip")
check("fcpxml_refs_resolues", clips and all(c.get("ref") in res for c in clips))
check("fcpxml_durees_rationnelles", all(re.match(r"^\d+/30s$|^\d+s$", c.get("duration")) and re.match(r"^\d+/30s$|^\d+s$", c.get("offset")) for c in clips))
check("fcpxml_offsets_croissants", [c.get("offset") for c in clips] == ["0s", "120/30s"])
check("fcpxml_chemins_absolus", all(a.get("src", "").startswith("file:///") for a in res.values() if a.tag == "asset"))
```

- [ ] **Étape 3 : implémenter** (`to_edl` : CMX 3600 — `TITLE:`, `FCM: NON-DROP FRAME`, un événement par clip V1 (`V`) puis audio (`A`), numéros `001…`, bobine `AX`, timecodes `hh:mm:ss:ff` à `fps`, `* FROM CLIP NAME:` et `* SOURCE FILE: <chemin absolu>` ; les titres et overlays sans source **ne s'exportent pas**, ils sont listés dans un commentaire `* SKIPPED: title X` ; `to_fcpxml` : `<fcpxml version="…"><resources><format id="r1" name="FFVideoFormat1080p30" frameDuration="1/30s" width="1080" height="1920"/><asset id="r2" name src="file:///C:/…" start="0s" duration="…s" hasVideo="1" hasAudio="0|1"/>…</resources><library><event name="Deepotus"><project name="abysse"><sequence format="r1" duration="270/30s" tcStart="0s"><spine><asset-clip ref="r2" name="plan_01" offset="0s" start="30/30s" duration="120/30s"/>…</spine></sequence></project></event></library></fcpxml>` — chaque durée = `f"{round(t*fps)}/{fps}s"` (`"0s"` pour zéro), chemins `Path(...).resolve().as_uri()`, transitions **ignorées** (sujet d'un lot ultérieur ; dit dans la docstring). Route `GET /api/montage/export?format=edl|fcpxml` : timeline courante (`_load_saved`), `_resolve_src` de chaque clip, `PlainTextResponse` avec `Content-Disposition: attachment; filename="<name>.<edl|fcpxml>"`, `400` sans timeline.
- [ ] **Étape 4 : lancer → `=== 10 passed, 0 failed ===`.**
- [ ] **Étape 5 : M25** — deux entrées « Exporter EDL » / « Exporter FCPXML » dans le popover Projets (M14) : `window.open("/api/montage/export?format=…")`. Rejouer, `test_montage_bundle`.
- [ ] **Étape 6 : preuve d'import (utilisateur).** Importer le `.fcpxml` dans Resolve (Fichier → Importer → Timeline) : deux plans à leurs positions, sources relinkées par chemin absolu. Résultat consigné dans le corps du commit ; un écart d'attribut se corrige dans `edl_export.py` avec son assertion.
- [ ] **Étape 7 : commit.** `git commit -m 'montage : D5 - export EDL et FCPXML' -m 'CMX 3600 et FCPXML <version lue> : sous-ensemble asset-clip sur spine, durées rationnelles, chemins absolus ; titres et transitions non exportés, dits.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

---

## Écarté

- **E1 — Multicam, proxies 4K** : sources 1080p générées, hors pratique (le proxy 480p de P7 sert la fluidité, pas le 4K).
- **E2 — Recadrage génératif systématique** : payant par clip et inventif ; reste une option par clip dans D2, jamais la voie par défaut.
- **E3 — Retouche corps/visage façon CapCut** : hors du produit.

---

### Tâche 14 — campagne de mutations `backend/tests/mutations_montage.py`

**Files :** créer `backend/tests/mutations_montage.py` (patron `mutations_plaque_slicer.py`, adapté aux bancs **autonomes** : on lance `& $PY tests\<banc>.py` et on lit les lignes `  FAIL  <label>`).

- [ ] **Étape 1 : écrire la campagne.**

```python
"""Banc de mutations du Montage : casser → rouge → remettre à l'octet près.
PAS UN TEST (pas de préfixe test_). Depuis backend/ :  & $PY tests\\mutations_montage.py [n…]
Chaque mutation : (fichier, ancien, nouveau, banc, labels attendus rouges).
Les bancs sont des scripts autonomes : un « rouge » est une ligne `  FAIL  <label>`,
un « ERREUR » un code de sortie hors {0,1} ou une trace Python (rien n'a été mesuré)."""
import hashlib, json, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
R = pathlib.Path(__file__).resolve().parents[2]; PY = sys.executable
MS, FX, SS, TS = ("backend/app/services/montage_service.py", "backend/app/services/effects_engine.py",
                  "backend/app/services/subtitle_service.py", "backend/app/services/transcribe_service.py")
M = [
 (MS, "eof_action=pass:", "eof_action=endall:", "tests/test_montage_pistes_rendu.py", ["overlay_absent_apres", "direct_duree_4s"]),
 (MS, "f\"enable='between(t,{st},{en})'[ob{j}]\")", "f\"enable='between(t,{st},{st})'[ob{j}]\")", "tests/test_montage_pistes_rendu.py", ["overlay_visible_pendant"]),
 (MS, 'inputs.extend(["-stream_loop", "-1", "-i", str(music["path"])])', 'inputs.extend(["-i", str(music["path"])])', "tests/test_montage_pistes_rendu.py", ["musique_audible_seule_3s"]),
 (MS, "    if music_lbl:\n        labels.append(music_lbl)", "", "tests/test_montage_pistes_rendu.py", ["musique_audible_seule_3s"]),
 (MS, "key=lambda k2: (int(k2.get(\"layer\") or 0), k2[\"start\"])", "key=lambda k2: k2[\"start\"]", "tests/test_montage_pistes_dyn.py", ["vert_au_dessus_centre_vert"]),
 (MS, "    for k, tid in enumerate(reversed(ov)):", "    for k, tid in enumerate(ov):", "tests/test_montage_pistes_dyn.py", ["meta_v3_au_dessus_de_v2", "vert_au_dessus_centre_vert"]),
 (MS, 'loop = bool(t.get("loop", tid == "a2")) and kind == "audio"', 'loop = kind == "audio"', "tests/test_montage_pistes_dyn.py", ["meta_legacy_a3_sfx", "meta_a4_boucle_a2_non"]),
 (SS, "\\\\t(0,120,\\\\fscx115\\\\fscy115)", "\\\\t(0,120,\\\\fscx100\\\\fscy100)", "tests/test_subs_animes.py", ["chaque_mot_rebondit", "rebond_plus_gros_au_debut"]),
 (SS, "        x += wd + sp", "        x += wd", "tests/test_subs_animes.py", ["rebond_plus_gros_au_debut"]),
 (TS, "        if out and abs(out[-1][\"end\"] - s) < 0.02:", "        if False:", "tests/test_montage_texte.py", ["plage_fusionnee"]),
 (TS, "        if not isinstance(w, dict) or w.get(\"start\") is None or w.get(\"end\") is None:", "        if not isinstance(w, dict):", "tests/test_montage_texte.py", ["mot_sans_temps_ignore"]),
 (FX, "    if k != 6500:", "    if True:", "tests/test_montage_etalonnage.py", ["6500K_n_emet_pas_colortemperature"]),
 (FX, '    sa = _num(eff, "saturation", 100, 0, 200) / 100.0', "    sa = 1.0", "tests/test_montage_etalonnage.py", ["saturation_zero_gris"]),
 ("backend/app/services/color_match.py", "max(0.5, min(2.0, sr / stt))", "1.0", "tests/test_montage_couleur.py", ["moyennes_alignees_6_sur_255"]),
 ("backend/app/services/reframe.py", "ema = cx if ema is None else 0.5 * ema + 0.5 * cx", "ema = 0.5", "tests/test_montage_reframe.py", ["erreur_max_sous_8_pct"]),
 ("backend/app/services/autoclips.py", "clips.sort(key=lambda c: -c[\"score\"])", "pass", "tests/test_montage_autoclips.py", ["tri_par_score"]),
 ("backend/app/services/titles.py", '"or": "#e6b23c"', '"or": "#e6b23d"', "tests/test_montage_titres.py", ["titre_couleur_de_marque"]),
 (MS, "    for j, t in enumerate(titles_ass or []):", "    for j, t in enumerate([]):", "tests/test_montage_titres.py", ["titre_avant_les_sous_titres", "texte_dans_le_tiers_bas"]),
 ("backend/app/services/edl_export.py", "FCM: NON-DROP FRAME", "FCM: DROP FRAME", "tests/test_montage_export.py", ["edl_titre"]),
 ("frontend/patches/montage.js", "if(c.srcIn!=null||c.src)k.srcIn=r3((c.srcIn||0)+(t1-c.start)*sp);", "", "tests/test_montage_texte.py", ["v1_coupe_en_deux", "a1_coupe_en_deux"]),
 ("frontend/patches/montage.js", "if(i<0||j<0||j>=ts.length||dzmGroup(ts[i])!==dzmGroup(ts[j]))return ts;", "if(i<0||j<0||j>=ts.length)return ts;", "tests/test_montage_bundle.py", ["js_move_v1_refuse"]),
]

def rouges(banc):
    r = subprocess.run([PY, banc], capture_output=True, cwd=R / "backend", timeout=1200)
    txt = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
    erreur = r.returncode not in (0, 1) or "Traceback (most recent call last)" in txt
    return set(re.findall(r"^\s+FAIL\s+(\S+)", txt, re.M)), txt, erreur

def main():
    seuls, bilan = sys.argv[1:], []
    for i, (rel, old, new, banc, attendus) in enumerate(M):
        if seuls and str(i) not in seuls: continue
        p = R / rel; src = p.read_bytes(); brut = src.decode("utf-8")
        eol = "\r\n" if "\r\n" in brut else "\n"; txt = brut.replace("\r\n", "\n")
        assert txt.count(old) == 1, (i, rel, txt.count(old), old[:60])
        sha0 = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace(old, new).replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur = rouges(banc)
        finally:
            p.write_bytes(src); assert hashlib.sha256(p.read_bytes()).hexdigest() == sha0, (i, rel)
        manquants = [a for a in attendus if not any(a in n for n in rg)]
        verdict = ("ERREUR(banc)" if erreur else "ROUGE" if not manquants else "VERTE" if not rg else "ROUGE(autres)")
        if erreur: print(sortie[-1200:], file=sys.stderr)
        bilan.append((i, rel, verdict, sorted(rg), manquants))
        print(f"[{i:2d}] {verdict:14s} {rel:44s} {old.strip()[:44]!r} -> {sorted(rg)}"); sys.stdout.flush()
    print(json.dumps([b[:3] for b in bilan], ensure_ascii=False))

if __name__ == "__main__":
    main()
```

La mutation 20 suppose que `test_montage_bundle.py` porte un `check("js_move_v1_refuse", …)` — l'ajouter à l'étape 8 de P1 si absent (c'est la campagne qui le dit). Les mutations dont le texte « ancien » n'existe pas à l'octet près (le code final peut différer du plan) se corrigent **dans la campagne**, jamais en tordant le code.

- [ ] **Étape 2 : lancer.** `& $PY tests\mutations_montage.py` → chaque ligne `ROUGE` ; une `VERTE` = une assertion qui manque : l'ajouter au banc nommé, relancer la mutation seule (`& $PY tests\mutations_montage.py 7`), puis tout.
- [ ] **Étape 3 : suite complète.** `.\scripts\run-tests.ps1 -Filter montage` puis `.\scripts\run-tests.ps1 -Filter subs` : tout vert, un processus par fichier.
- [ ] **Étape 4 : commit.** `git add backend/tests/mutations_montage.py backend/tests/test_montage_*.py; git commit -m 'montage : campagne de mutations' -m 'Vingt et une mutations sur le rendu, les pistes, les mots animés, le texte, l étalonnage, l accord, le suivi, les titres, l export et le cœur JS ; chaque VERTE a reçu son assertion.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

---

## Relecture du plan (faite avant remise)

Couverture : P0→T1, P1→T2, P2→T3, P3→T4, P4→T5, P5→T6, P6→T7, P7→T8, D1→T9, D2→T10 (table + règle), D3→T11, D4→T12, D5→T13, E1–E3 nommés, mutations→T14. Noms tenus d'une tâche à l'autre : `_tracks_meta`/`layer`/`tracks`, `svmTracksOf`/`svmTracksPayload`/`svmTracksFrom`/`svmTrackBusSync`/`svmTracksSet`, `rippleCut`, `replaceSrc`, `grade_basic`, `colormatch`/`match_effect`, `motion_track`/`reframe`, `windows`/`score`/`heuristic`, `to_ass_title`/`titles_ass`, `to_edl`/`to_fcpxml`, `word_anim`/`wordAnim`/`ui_word_anim`. Toutes les ancres du patcher ont été mesurées **uniques** dans le bundle courant le 03/09 ; une ancre consommée par une section antérieure reçoit ses ajouts **dans** le remplacement de cette section (dit à chaque fois) ; `--check` valide avant chaque écriture. Aucun « TBD » : les seules valeurs à remplir sont des mesures (scrub avant/après, erreur du suivi, version FCPXML lue).

## Incertitudes non levées

1. Le défaut signalé n'est **ni reproduit ni expliqué** avant T1 ; les deux hypothèses UI (M → −40 dB persisté ; lecteur vivant sans A2/A3) sont traitées par P1/P7 mais ne seront confirmées que par l'utilisateur.
2. P2 pose les mots avec `_measure_px` (PIL, fonte embarquée) : l'écart avec la mise en page libass (interlettrage, crénage) n'est borné que par le ratio de pixels du banc, pas au pixel près. D2 : le tracker par énergie de mouvement n'a été pensé que sur un cas synthétique ; le seuil de 8 % est une règle de décision, pas une garantie sur des plans générés.
3. D5 : FCPXML « de mémoire » jusqu'au WebFetch de T13 ; la preuve finale est l'import Resolve, fait par l'utilisateur. `.svm-tl` en `max-height:48vh` avec 8 pistes n'est vérifié qu'au navigateur (T2, étape 10) — un probe DOM en onglet caché ne verrait pas un effondrement (piège hérité).

---

## Lot 3 — remontées de l'utilisateur du 04/09/2026 (bloquantes : à passer AVANT le Lot 2)

Deux défauts rapportés à l'écran, **mesurés avant d'être écrits ici**. Le code
d'un plan est une intention ; ce qui suit est une mesure, et les deux ne se
lisent pas de la même façon.

**Sources de la mesure.** Journal
`%LOCALAPPDATA%\DeepotusVideoGenData\logs\deepotus-2026-09-04.log`, job de
montage `a32009c4`, 15:57:44 ; sauvegarde
`…\DeepotusVideoGenData\assets\montage_saved.json` (`saved_at`
`2026-09-04T13:53:27Z`) ; `deepotus.db` interrogée **sur une copie** (base +
`-wal` + `-shm`), l'application tournant — on ne lit pas une base vivante en
place.

### Fait n°1 — les quatre « plans » de la piste V1 ne sont pas des vidéos

| clip de la capture | job | `provider` | `duration_s` | `final_video_path` |
|---|---|---|---|---|
| Particules · Aura magique | `27eae33c` | `sprite2d` | `None` | `outputs/sprites/27eae33c/sheet.png` — 3072×2560 |
| Particules · Fumée douce | `a94e7dfd` | `sprite2d` | `None` | `outputs/sprites/a94e7dfd/sheet.png` — 3072×3072 |
| 3D · tripo | `b6cec0f5` | `asset3d` | `None` | `outputs/assets3d/b6cec0f5/model.glb` |
| Particules · Traînée | `3760f756` | `sprite2d` | `None` | `outputs/sprites/3760f756/sheet.png` |

`GET /api/montage/project` retient les jobs `done` les plus récents dont
`final_video_path or video_path` **existe**, sans jamais vérifier que le fichier
est une vidéo — et `sprite2d` comme `asset3d` rangent leur planche PNG et leur
maillage GLB dans cette même colonne. `_probe_duration` rend 0 sur un PNG,
`duration_s` est `None`, le repli `or 4.0` donne quatre clips de 4 s : les 16,0 s
exactes de la capture. La base porte pourtant 35 rendus `seedance`, 33
`template`, 9 `ugc` et 5 `heygen` : **aucune vraie vidéo n'a été retenue**, elles
sont seulement moins récentes que les planches de sprites.

Le rendu meurt ensuite sur le maillage :
`[in#2] Error opening input: Invalid data found when processing input` puis
`Error opening input file …\assets3d\b6cec0f5\model.glb.` Les deux PNG, eux,
étaient bel et bien ouverts (`Input #0, png_pipe`) : sans le GLB, l'aperçu aurait
« réussi » en montrant deux planches de sprites plein cadre. **L'échec est le
symptôme le moins grave des deux.**

### Fait n°2 — le message d'erreur est une tranche aveugle

`_run_ffmpeg` lève `f"ffmpeg a échoué ({r.returncode}) : {tail}"` avec
`tail = (r.stderr or "")[-1200:]` : mille deux cents **caractères**, pas des
lignes. La coupure tombe au milieu de la bannière de compilation
(`libtheora --enable-libvo-amrwbenc …`) ; la seule ligne qui dit quelque chose —
`Error opening input file …model.glb.` — arrive après neuf cents caractères de
drapeaux de build et de dumps de flux. C'est le mur rouge de la capture.

### Fait n°3 — « Envoyer vers → Montage » dépose le clip sur une piste inexistante

`scripts/patch_bundle_libsend.py`, greffon `GREFFE_MONTAGE`, appelle
`addAsset({job_id:…}, title, "video", p.dur||0, "v2")`. Mesuré dans la
sauvegarde, `tracks` vaut `[v1, a2, a1, a3, s1]` : **il n'y a pas de piste
`v2`**. Et `addAsset` fait `var tr2=trId||"v2"` sans vérifier que la piste
existe. Le clip entre donc dans `clips`, il est sauvegardé, il partirait au rendu
comme overlay — mais la timeline ne dessine que `svmTracksOf(proj).map(…)` : il
est invisible et inselectionnable. « Rien n'est apparu » est exact, et le clip
est pourtant là.

Deux causes de plus, indépendantes, cumulables avec la première :

* le greffon consomme `window.__dzMontageAdd` dans un `setTimeout(…, 450)`, et
  `addAsset` borne le clip par `durRef.current` — encore 0 tant que
  `GET /project` n'a pas répondu (il ffprobe chaque asset). Au-delà de 450 ms,
  `en − st < .5` et le clip est ramené à une longueur nulle ;
* tout le corps du greffon tient dans un `try{…}catch(_e2){}` : **aucune panne
  ne se dit**, jamais.

### Fait n°4 — il n'existe aucun bouton « ajouter une vidéo »

`openPicker` n'est appelé qu'à **un seul** endroit du bundle : le petit `+` de
l'en-tête de piste. Les boutons `+ vidéo` / `+ audio` de la barre de transport,
posés par P1/M8, ajoutent une **PISTE** — c'est ce que l'utilisateur a lu comme
« ajouter une vidéo », et le libellé lui donne raison.

---

### Tâche 15 — P8 : seule de la vidéo sur V1, et une erreur de rendu lisible

**Files :** modifier `backend/app/services/montage_service.py`
(`montage_project`, `_run_ffmpeg`, pré-vol de `montage_render`) ; créer
`backend/tests/test_montage_sources.py`. **Aucune section de patch : rien de
cette tâche ne touche le bundle**, donc rien n'entre en conflit avec la chaîne.

- [ ] **Étape 1 : banc rouge.** `backend/tests/test_montage_sources.py`,
  en-tête commun de `test_montage_texte.py` (env avant tout `from app…`,
  `check`, `=== N passed ===`). Insérer en base des `JobRecord` `done` réels —
  un `seedance` avec un vrai `.mp4`, un `sprite2d` avec un `.png`, un `asset3d`
  avec un `.glb`, un quatrième dont le chemin n'existe plus — puis :
  `check("v1_ne_prend_que_la_video", [c["src"]["job_id"] for c in r["clips"]
  if c["tr"] == "v1"] == [<id du mp4>])` ; `check("sprite_exclu", …)` et
  `check("glb_exclu", …)` **séparément** — une seule ligne agrégée resterait
  verte si l'un des deux repassait ; `check("aucune_video_has_assets_faux", …)`
  quand la base ne porte QUE des planches ; et la non-régression
  `check("image_posee_a_la_main_reste_valide", …)` : un clip `{image: …}` monté
  par l'utilisateur passe toujours `_resolve_src`. **La règle ne vaut que pour
  la construction AUTOMATIQUE depuis la Bibliothèque**, jamais pour ce que
  l'utilisateur pose lui-même.
- [ ] **Étape 2 : lancer → rouge sur `sprite_exclu` et `glb_exclu`.**
- [ ] **Étape 3 : implémenter.**

```python
# extensions qu'un DÉMULTIPLEXEUR vidéo sait ouvrir. La liste est fermée par
# choix : `sprite2d` range sa planche et `asset3d` son maillage dans la MÊME
# colonne final_video_path, et un jour un provider de plus fera pareil.
_VIDEO_EXTS = (".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi")

def _is_video_artifact(p: Path) -> bool:
    return p.suffix.lower() in _VIDEO_EXTS
```

  dans la boucle `for j in jobs:` de `montage_project`, juste après le test
  d'existence :

```python
        if not _is_video_artifact(Path(fp)):
            logger.info(f"montage: job {j.id[:8]} ({j.provider}) ecarte de V1 — "
                        f"{Path(fp).suffix or 'sans extension'} n'est pas une video")
            continue
```

  **Pré-vol du rendu**, dans `montage_render`, AVANT de créer le `JobRecord` :
  résoudre chaque `src` et refuser en **400** ceux qu'aucun démultiplexeur
  n'ouvrira, en nommant le `label` du clip et le fichier — pas la ligne 1700 du
  journal. Un rendu qui ne peut pas aboutir ne doit coûter ni une entrée de file
  d'attente ni deux minutes d'attente.

  **`_run_ffmpeg`** : garder la tranche brute, mais la faire précéder de la
  ligne qui décide. Chercher dans `r.stderr`, **par lignes**, les motifs
  `Error opening input file`, `Invalid data found`, `No such file`,
  `Conversion failed`, `Unknown encoder` ; s'il y en a, les mettre EN TÊTE du
  message, la tranche de 1200 caractères restant derrière. Sans motif trouvé, le
  message ne change pas — c'est ce que doit prouver une assertion dédiée, sans
  quoi la ligne serait verte à vide.
- [ ] **Étape 4 : lancer → vert.** Puis `test_montage_pistes_rendu.py` et
  `test_montage_pistes_dyn.py` : ils rendent par la route, ce sont eux qui
  verraient un pré-vol trop zélé refuser un rendu légitime.
- [ ] **Étape 5 : commit.** Sujet :
  `montage : P8 - seule de la video sur V1, et une erreur de rendu lisible`.
  Corps accentué : les quatre jobs mesurés, le repli `or 4.0` qui fabriquait les
  4 s, et la tranche de 1200 caractères remplacée par la ligne qui décide.
  Pied : `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

### Tâche 16 — P9 : un bouton « Bibliothèque… » qui pose un clip, et la remise qui se perdait

**Files :** modifier `frontend/patches/montage.js`,
`scripts/patch_bundle_montage.py`, `backend/tests/test_montage_bundle.py`.

**DEUX PIÈGES DE CHAÎNE, à lire avant d'écrire une ligne.**

1. `scripts/patch_bundle_libsend.py` est un maillon **AMONT**. Le relancer seul
   effacerait ce que les maillons suivants ont écrit — le mode de panne qui a
   déjà coûté vingt-deux correctifs au dépôt. **La correction du greffon ne se
   fait donc pas dans `libsend`.** Elle se porte **en aval**, dans la chaîne
   `montage`, sur `addAsset` : c'est `addAsset` qui choisit la piste, et le
   corriger là répare ce greffon *et* toute remise future. (Rejouer
   `repatch_all.py --from libsend` reste la voie officielle si l'on tenait à
   éditer le greffon lui-même — mais sa faisabilité est à **mesurer** d'abord :
   le brief de reprise consigne que `.bak_vfxrack` et `.bak_subs` n'existent pas
   dans cette copie.)
2. **Collision d'ancre avec la tâche 7.**
   `  function addAsset(src,label,kind,srcDur,trId,atTime){` est l'ancre que M15
   (tâche 7, mode remplacement) revendique déjà, et elle ne vaut qu'**une**
   fois. Celle des deux tâches qui passe en second **replie sa section dans le
   remplacement de l'autre**, exactement comme M10 et M11b vivent dans `R_M8`.
   Le dire dans le commentaire de la section, et ajouter au miroir une ligne par
   greffon replié — sans quoi retirer l'un des deux du patcher laisserait le
   banc entièrement vert.

- [ ] **Étape 1 : banc rouge sous node**, dans `test_montage_bundle.py` §[3].
  Le cœur à écrire est PUR, donc mesurable : `DzTracks.pickTrack(tracks, kind)`
  rend l'identifiant d'une piste **existante** du genre demandé — la première
  dans l'ordre d'affichage — et `""` si le projet n'en porte aucune.
  `check("pick_video_sans_v2", DzTracks.pickTrack([{id:"v1",kind:"video"},
  {id:"a1",kind:"audio"}], "video") === "v1")` — c'est le cas MESURÉ de la
  capture ; `check("pick_video_prend_la_premiere", … [{id:"v3"},{id:"v1"}] …
  === "v3")` ; `check("pick_sans_piste_du_genre", … === "")`.
  Prouver chacune par mutation : rendre `"v2"` en dur doit faire rougir la
  première **seule**.
- [ ] **Étape 2 : lancer → rouge** (`pickTrack` n'existe pas).
- [ ] **Étape 3 : la couche.** `dzmPickTrack(ts, kind)` dans
  `frontend/patches/montage.js`, exportée sous `pickTrack`. Rappel des gardes :
  **`DzTracks`, jamais `DzMontage`** (nom déjà pris au premier niveau du
  bundle), et **aucune ancre du patcher citée dans un commentaire de la
  couche** — un contrôle général le vérifie pour toutes les sections.
- [ ] **Étape 4 : la section de patch sur `addAsset`.** Remplacer
  `var tr2=trId||"v2"` par une résolution qui **retombe sur une piste
  existante** : la piste demandée si elle est dans `svmTracksOf(proj)`, sinon
  `DzTracks.pickTrack(svmTracksOf(proj), kind==="audio"?"audio":"video")`, sinon
  un refus **dit** (`fireNote`) — jamais un clip muet posé dans le vide.
  Le clip déjà invisible dans la sauvegarde de l'utilisateur ne se répare pas
  tout seul : le dire dans la note, et prévoir que recréer une piste V2 à la
  main le fasse réapparaître.
- [ ] **Étape 5 : le bouton, dans `R_M8`.** L'ancre `A_M8` est **déjà
  consommée** par M8 : le bouton se replie dans `R_M8`, comme M10 et M11b.
  Libellé **`Bibliothèque…`** — pas `+ clip` : « bibliothèque » est le mot que
  l'utilisateur a employé. `onClick` → `openPicker(<piste vidéo résolue>)`.
  **Et lever l'ambiguïté mesurée au fait n°4** : `+ vidéo` / `+ audio`
  deviennent `+ piste vidéo` / `+ piste audio` — ils ajoutent une piste, ils
  doivent le dire. C'est une édition de `DzmTrackAdd` dans la couche, pas une
  section de plus.
- [ ] **Étape 6 : le délai fixe de 450 ms.** Il ne peut pas être corrigé dans
  `libsend` (piège n°1). Le remplacer côté `montage` par une attente de la
  condition — `durRef.current > 0` — bornée à quelques secondes, et **dire**
  l'échec au lieu de l'avaler. Si cela exigeait de toucher au greffon amont
  lui-même, **ne pas le faire** : consigner l'écart et laisser la remise
  imparfaite mais VISIBLE. Le fait n°3 montre que la piste inexistante suffit
  déjà à tout expliquer ; la course des 450 ms **n'a pas été isolée
  séparément** et reste une hypothèse.
- [ ] **Étape 7 : rejouer et mesurer.** `--check`, patcher, `repatch_all.py
  --list` doit finir par `montage OK`, `test_montage_bundle` vert,
  **`bloc_EST_la_couche_octet_pour_octet` compris**.
- [ ] **Étape 8 : commit.** Sujet :
  `montage : P9 - un bouton Bibliotheque, et la remise qui se perdait`.
  Corps accentué : la piste `v2` absente des cinq pistes sauvegardées, le clip
  invisible mais présent, et pourquoi la correction est portée en aval plutôt
  que dans `libsend`.
  Pied : `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

**Dette navigateur ajoutée par cette tâche** (non mesurable sans l'application
lancée **par l'utilisateur**) : le bouton `Bibliothèque…` et la largeur réelle
de la barre de transport qui reçoit un contrôle de plus ; les deux libellés
renommés ; et la remise depuis la fenêtre de la Bibliothèque, refaite de bout en
bout sur un projet SANS piste V2 puis sur un projet qui en porte une.

---

### Tâche 16 — compléments mesurés pendant la tâche 15

Deux ajouts au périmètre, tous deux **mesurés** en implémentant P8, et tous deux
à traiter dans la même passe : ils touchent la même surface et la même chaîne.

#### Le défaut jumeau du sélecteur d'assets

Le filtre fautif de `GET /project` n'était pas le seul. `openPicker()` —
`frontend/patches/son-vfx-montage.js`, lignes **3620** et **3628** — construit
sa liste « Rendus vidéo » à partir de `/api/jobs` avec **exactement le même
critère** : `status === "done" && (video_path || final_video_path)`. Les
planches `sprite2d` et les maillages `asset3d` y sont donc **encore proposés**,
et rien n'empêche l'utilisateur de reposer à la main les clips que la tâche 15
vient d'écarter de la construction automatique.

**LE PIÈGE, et il décide de l'endroit du correctif.** `son-vfx-montage.js` est
le fichier que cette chaîne **ne peut pas rejouer** : le bloc correspondant du
bundle porte les vingt sections V3/V4/V6/V8/V9 de `patch_bundle_vfxrack.py` et
S3…S17 de `patch_bundle_subs.py`, `.bak_vfxrack` et `.bak_subs` sont absents de
cette copie, et l'ancre V10 est déjà consommée. **Éditer ce fichier et relancer
son patcher effacerait les vingt sections, sans un mot et sans retour.** Le
correctif se porte donc **en aval, dans la chaîne `montage`** — même règle et
même raison que pour `addAsset` (piège n°1 ci-dessus).

Le backend possède déjà la règle : `_is_video_artifact` et `_VIDEO_EXTS`
(`montage_service.py`, tâche 15). Ne la réécris pas en JavaScript — **fais-la
servir** : soit la liste du sélecteur passe par une route qui l'applique, soit
le filtre client interroge la même liste d'extensions exposée par le backend.
Une seconde copie de la règle divergera de la première.

#### Le champ `v1_non_video` attend son lecteur

La tâche 15 a **choisi de ne pas élaguer** la sauvegarde de l'utilisateur — la
mesure est au commit `8dc8e7d` : son `montage_saved.json` porte 17 clips, dont
seulement 4 fautifs, et élaguer aurait vidé la piste V1 puis fait repartir la
construction depuis la Bibliothèque, détruisant le reste sans retour. Les clips
fautifs sont donc **signalés** : `GET /project` rend la clé `v1_non_video`, la
liste de leurs identifiants.

**Aujourd'hui aucune interface ne la lit** — c'est une dette déclarée en toutes
lettres dans l'en-tête du banc, et elle appartient à cette tâche. Ce qu'il faut :
que ces clips **se voient** sur la timeline (un état visuel sur la rangée, un
titre qui dit pourquoi), et que la voie de sortie soit offerte sur place plutôt
que devinée — c'est le même geste que le bouton `Bibliothèque…` de l'étape 5.
Sans lecteur, le champ est un mensonge poli : le backend sait, et l'écran se
tait.

**Note pour l'implémenteur** : `POST /render` refuse déjà ces clips en **400**
en les nommant (pré-vol de la tâche 15). Le marquage n'est donc pas la seule
protection — il est là pour que l'utilisateur voie le problème **avant** de
cliquer, pas après.

---

## Lot 4 — remontée du 05/09/2026 : la timeline ne s'étend pas

Rapportée par l'utilisateur après avoir réparé sa piste V1 : « j'ai voulu ajouter
trois vidéos depuis la bibliothèque, or la timeline est fixe, je suis obligé de
raccourcir des pistes vidéo pour les faire rentrer ». Tout ce qui suit est
**mesuré dans le bundle livré et dans `.bak_montage`**, avant d'écrire une ligne.

### Fait n°1 — aucun contrôle n'écrit `proj.dur`

`setProj(` n'est **jamais** appelé avec `dur`. La durée du projet est fixée une
fois pour toutes au chargement : `SVM_DEMO_DUR = 64` pour la maquette, et
`dur: Math.max(1, Number(d.duration) || maxEnd)` dans `svmApplyProject` pour un
projet réel. La barre de transport ne fait que **l'afficher** :
`" % · " + svmRuler(Math.round(dur)) + " total"`.

### Fait n°2 — l'ajout ROGNE en silence

```js
st = Math.min(Math.max(0, st), Math.max(0, d - 1));
var en = Math.min(d, st + defaultLen(kind, srcDur));
if (en - st < .5) st = Math.max(0, en - 1);
```

Le début est plafonné à `durée − 1`, la fin à `durée`. Une vidéo de 6 s posée
près de la fin d'un projet de 16 s **entre à la taille du reste**, sans un mot.
Rien ne peut être placé au-delà de `dur`.

### Fait n°3 — le glissement est plafonné aussi

`var ns = Math.min(Math.max(0, d - len), Math.max(0, c.start + fr / 30));` — un
clip ne peut pas être tiré au-delà de la fin. L'utilisateur ne peut donc ni
poser, ni déplacer hors des bornes.

### Fait n°4 — étendre la durée est SANS RISQUE pour le rendu

`total` est recalculé dans `_build_montage_command` à partir de `seg_durs` (les
durées des segments V1), **jamais** depuis le `duration` posté — celui-ci n'est
lu que par `POST /save` (`montage_service.py:794`) comme valeur à conserver.
`proj.dur` est donc une **borne d'édition**, pas une propriété du rendu :
l'agrandir ne change pas un octet de la vidéo produite.

### Fait n°5 — le défilement horizontal EXISTE DÉJÀ

`.svm-scroll{flex:1; overflow:auto; …}` (`shared/son-vfx-montage.css:331`), les
pistes portent `style={{width: zoomPct + "%"}}`, les paliers sont
`SVM_ZOOMW = [100, 150, 220, 320]` et le **Ctrl+molette** donne un zoom
**continu jusqu'à 800 %**, avec conservation du point sous le curseur
(`pendScrollRef` / `tlScrollRef.scrollLeft`, `useLayoutEffect` sur `[zoomPct]`).
À 100 % il n'y a rien à faire défiler **parce que les pistes remplissent
exactement le cadre**. La demande « défilement horizontal » est donc en grande
partie satisfaite — ce qui manque est **la découvrabilité**, pas le mécanisme.

### Fait n°6 — une dette de P3 arrive à échéance

La note de la coupe par plage dit : « la durée du projet ne bouge pas : la fin de
la timeline est vide, **raccourcissez-la si vous voulez** ». Or **rien ne permet
de la raccourcir**. La phrase promet un geste qui n'existe pas.

---

### Tâche 17 — P10 : la timeline s'étend au lieu de rogner

**Files :** `frontend/patches/montage.js`, `scripts/patch_bundle_montage.py`,
`backend/tests/test_montage_bundle.py`, `frontend/dist/shared/montage.css`.

**Ancres mesurées, toutes à 1 dans le bundle livré ET dans `.bak_montage` :**

| ancre | usage |
|---|---|
| `    st=Math.min(Math.max(0,st),Math.max(0,d-1));` | le rognage de l'ajout |
| `      var ns=Math.min(Math.max(0,d-len),Math.max(0,c.start+fr/30));` | le plafond du glissement |
| `" % · "+svmRuler(Math.round(dur))+" total"]}),` | l'affichage de la durée dans le transport |
| `  var stP=x.useState({demo:!0,name:` | l'état du projet (pour un `durRef` d'écriture) |

- [ ] **Étape 1 : le cœur pur, sous node.** `DzTracks.fitDur(clips, durActuelle, marge)` rend la durée que le projet DOIT avoir : le maximum entre la fin du dernier clip (plus une marge de queue) et la durée demandée, arrondi. PURE, donc mesurable : clips vides, clip unique, clip qui dépasse, clip qui ne dépasse pas, `end` illisible, durée courante nulle ou négative. Prouver chaque ligne par mutation.
- [ ] **Étape 2 : l'ajout n'écrase plus.** Là où `addAsset` rogne, il doit **étendre** : si `st + defaultLen(...)` dépasse `d`, la durée du projet grandit au lieu que le clip rétrécisse. Le clip garde sa longueur naturelle. **Dire dans la note** que la timeline s'est allongée, et de combien — un agrandissement silencieux est aussi désagréable qu'un rognage silencieux. Le geste reste **réversible** : `pushHistory()` avant, et la note dit ce qu'« annuler » ne restaure pas (l'historique ne mémorise que `{clips, mixDb}` — **pas la durée**, c'est mesuré et c'est la raison pour laquelle P3 n'y touchait pas).
- [ ] **Étape 3 : le glissement suit la même règle.** Tirer un clip vers la droite étend la timeline au lieu de buter. Même réserve d'historique, même note.
- [ ] **Étape 4 : un contrôle explicite dans le transport.** La durée affichée devient modifiable : allonger **et raccourcir**, ce qui paie la dette du fait n°6. Raccourcir sous la fin du dernier clip est un **geste destructif à l'écran** (des clips sortent du champ, même s'ils ne sont pas supprimés) : le refuser, ou l'armer, mais ne jamais le faire en silence. Le pas et les bornes sont à **mesurer**, pas à inventer.
- [ ] **Étape 5 : la découvrabilité du zoom** (fait n°5). Le mécanisme existe et il est bon ; ce qui manque est qu'on le trouve. L'infobulle des paliers dit déjà « Ctrl+molette : continu » — vérifier **au navigateur** (utilisateur) que c'est lisible, et que le défilement horizontal se voit dès qu'on dépasse 100 %. **Ne rien réécrire tant que ce n'est pas mesuré à l'écran.**
- [ ] **Étape 6 : rejouer et mesurer.** `--check`, patcher, `repatch_all --list` → `montage OK`, `test_montage_bundle` vert, **`bloc_EST_la_couche_octet_pour_octet` compris**.
- [ ] **Étape 7 : commit.** Sujet : `montage : P10 - la timeline s etend au lieu de rogner`.

**Réserve à porter** : `proj.dur` n'entre pas dans l'historique. Étendre puis
annuler rend les clips, pas la durée — exactement le piège que P3 avait choisi
d'éviter en ne touchant pas à `dur`. Ici on y touche **délibérément**, donc la
note doit le dire à chaque fois, et l'en-tête du banc doit le consigner comme un
reste assumé.
