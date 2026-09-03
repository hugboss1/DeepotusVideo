# Quick — parité et différenciation (bacs R1) — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** livrer les six items de parité (P1–P6) puis les trois différenciants (D1–D3) de la section R1 du balayage (`docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md`), pour que l'écran Quick cesse d'être « quatre formulaires » : un rendu se rouvre prérempli, se prolonge, se sous-titre et se lip-synche depuis Quick, les presets couvrent les quatre onglets, et les mouvements de caméra se choisissent à l'œil ou au curseur.

**Architecture :** le backend FastAPI gagne trois services purs (`quick_recipe.py`, `fal_video_tools.py`, `quick_finish.py`) plus `quick_gallery.py` et `camera_lang.py`, des champs additifs sur `GenerateRequest`/`GenerateHeyGenRequest`/`CompositionRequest`, une table `quick_presets`, une colonne `jobs.parent_job_id`, et dix routes ; le pipeline existant (`run`, `run_heygen`, `run_composition`) reçoit des crochets APRÈS le rendu payé (jamais avant). L'écran Quick vit dans le bundle (`um`) : neuf patchers `scripts/patch_bundle_quick*.py` en QUEUE de chaîne, partageant un squelette `scripts/_patch_quick.py` (garde-chaîne, CRLF, `--check`), chacun à ancres uniques mesurées le 03/09/2026. Tout appel fal nouveau (Veo extend, Kling LipSync) est précédé d'une mesure OpenAPI dont la table de décision est dans la tâche.

**Tech Stack :** Python 3.13 embarqué (stdlib + Pillow + fal_client/httpx déjà présents), SQLAlchemy async + SQLite, ffmpeg/ffprobe dans `bin/`, bundle React minifié patché par scripts, node (`node --check`) et puppeteer-core (`scripts/qa`) pour les sondes.

---

## Périmètre — bacs R1 → tâches

| Bac | Item R1 | Tâche | Résumé |
|---|---|---|---|
| P | P1 Rouvrir dans Quick, prérempli | T1 | recette JSON par rendu (`outputs/_recipes`), route `GET /jobs/{id}/recipe`, patch `quickreopen` (Bibliothèque + file + apply dans `um`) |
| P | P2 Extension générative | T2 | mesure OpenAPI Veo extend, `fal_video_tools.py`, `Provider.EXTEND`, colonne `parent_job_id`, routes `/generate/extend(/check)`, patch `quickextend` (menu « Envoyer vers… ») |
| P | P3 Image de fin exposée | T3 | patch `quickend` : le champ lit `/video-models`, grisé avec la raison sur les 5 modèles sans first-last |
| P | P4 Sous-titres dans Quick | T4 | `quick_finish.py` (calage gratuit ou transcription, ASS, gravure), champ `subtitles`, patch `quicksubs` (case + style + langue + texte + ligne de coût) |
| P | P5 Lip-sync dans Quick | T5 | mesure OpenAPI Kling LipSync, registre + gardes 2–10 s / 2–60 s, crochet pipeline AVANT allongement, pricing 0,014 $/s, patch `quicklipsync` |
| P | P6 Presets sur les quatre onglets | T6 | table `quick_presets`, routes `/quick/presets`, patch `quickpresets` (charger / enregistrer / supprimer par onglet, recette de T1) |
| D | D1 Galerie mouvements × styles | T7 | `quick_gallery.py` : 11 caméras × 3 styles rendus UNE fois par ffmpeg (zoompan) sur l'image de marque, routes `/quick/gallery`, patch `quickgallery` |
| D | D2 Curseurs caméra → phrase | T8 | `camera_lang.py` (pan/tilt/zoom/roll → phrase par famille), champ `camera_ctrl`, route `/quick/camera-phrase`, patch `quickcamera` |
| D | D3 Les onglets en « studio » | T9 | patch `quickstudio` : DropZones start/fin, aperçu central par onglet (avatar, ghost de composition), colonne source 360 px |
| — | Campagne de mutations | T10 | `backend/tests/mutations_quick.py` |
| E | E1, E2, E3 | — | voir « Écarté » |

## Coût de patch — tâche par tâche

| Tâche | Backend | Bundle (patcher, ancres) | Couche injectée | Autonome |
|---|---|---|---|---|
| T1 | `quick_recipe.py`, 3 schémas, 3 crochets pipeline, 1 route | `patch_bundle_quickreopen.py` — 7 ancres (helper avant `__dzReopenStudio`, `um` ×4, modal Bibliothèque, carte `yd`) | — | — |
| T2 | `fal_video_tools.py`, `Provider.EXTEND`, colonne, `run_extend`, 2 routes, pricing | `patch_bundle_quickextend.py` — 2 ancres (helper, menu « Envoyer vers… ») | — | — |
| T3 | 0 (lit `/video-models` existant) | `patch_bundle_quickend.py` — 5 ancres dans `um` | — | — |
| T4 | `quick_finish.py`, 3 schémas, 3 crochets pipeline | `patch_bundle_quicksubs.py` — 7 ancres dans `um` (`DzQuickEst` n'est PAS touché : le calage local coûte 0 $, la pastille afficherait le même chiffre — une ligne d'aide sous la case en dit plus) | — | — |
| T5 | `fal_video_tools.py` (lipsync), schéma, crochet, garde, pricing | `patch_bundle_quicklipsync.py` — 5 ancres (toutes sur des chaînes posées par T4/T1) | — | — |
| T6 | table + 3 routes + schéma | `patch_bundle_quickpresets.py` — 2 ancres (les deux branches du conteneur scroll se remplacent d'un coup) | — | — |
| T7 | `quick_gallery.py`, 3 routes, `build_prompt` (caméra sur prompt libre) | `patch_bundle_quickgallery.py` — 2 ancres (grille modale en DOM pur, patron `__dzSendMenu`) | — | — |
| T8 | `camera_lang.py`, schéma, `build_prompt` ×2 branches, 1 route | `patch_bundle_quickcamera.py` — 6 ancres | — | — |
| T9 | 0 | `patch_bundle_quickstudio.py` — 7 ancres (2 composants injectés avant `um`) | — | — |
| T10 | tests seulement | — | — | — |

Le bundle est le coût dominant (9 patchers, 43 ancres comptées) : c'est le prix mesuré de « Quick vit dans le bundle (`um`) » (R1). Aucune couche `frontend/patches/*.js` ni écran autonome n'est concerné.

**Chaîne de patch (mesurée le 03/09/2026)** : `python scripts/repatch_all.py --list` dans ce worktree ne montre que quatre `.bak_*` (`dzrailmotion`, `version`, `dznodecat`, `seedance25`) parce que `.gitignore` ligne 58 exclut `frontend/dist/assets/*.js.bak_*` — la vraie queue de chaîne sur le poste est `libsend` (28/08, `scripts/patch_bundle_libsend.py` en-tête : « EN QUEUE, apres libprov »). Les neuf patchers de ce plan s'enchaînent dans l'ordre des tâches, chacun poussant le mtime de son backup en queue (`_ensure_tail` du squelette) ; rejouer depuis un tag : `python scripts/repatch_all.py --from quickreopen`. Ordre imposé : `quickreopen → quickextend → quickend → quicksubs → quicklipsync → quickpresets → quickgallery → quickcamera → quickstudio` (T5, T7, T8, T9 ancrent sur des chaînes écrites par T1/T3/T4).

## Références vérifiées (section R1, 03/09/2026)

- **fal, Veo 3.1 extend-video (et Fast)** : `video_url` source **≤ 8 s** en 720p/1080p, 16:9 ou 9:16 ; `prompt` ; extension 7 s par défaut ; audio généré par défaut (fal.ai, 03/09). `veo-3.1-fast-fal` est déjà au registre. — fonde T2.
- **fal, lip-sync** : Kling LipSync audio-to-video (vidéo 2–10 s, audio 2–60 s, **0,014 $/s**), Sync Lipsync v2/v3, LatentSync, MuseTalk, veed/lipsync (fal.ai, 03/09). — fonde T5 (Kling par défaut, comme R1 le demande).
- **fal, Kling v3 Pro image-to-video** : pas de `camera_control`, pas de `dynamic_masks`, pas de `seed` (fal.ai, 03/09). — fonde D2 (la caméra passe par le texte) et E3.
- **Kling (application)** : contrôle caméra par « commandes absolues » sur 6 axes (horizontal, vertical, zoom, pan, tilt, roll) + 4 master shots (kling.ai/quickstart, 03/09). — vocabulaire de la famille `kling` dans `camera_lang.py`.
- **Runway** : Motion Brush retirée le 11 mai 2025, contrôle caméra chiffré retiré le 30 juillet 2026, Gen-4/4.5 pilotent la caméra par le prompt (help.runwayml.com, 03/09). — justifie D2 (phrase) plutôt qu'une API de caméra.
- **Code relu le 02/09** (R1) : 11 modèles au registre, image de fin acceptée par 6 sur 11 (`end_image: True` sur seedance-v1-pro, seedance-2, seedance-2-fast, seedance-2.5, kling-v3-pro, kling-v3-standard — `fal_service.py:65-151`), graine par 3 sur 11, presets HeyGen seuls (`routes.py:2968-3022`).

Toute autre affirmation sur un service tiers dans ce plan est marquée « de mémoire, à vérifier » et précédée d'une étape de mesure.

## Conventions du plan (mesurées le 03/09/2026)

**Identifiants module-scope du bundle** (comptés à 1 déclaration chacun) : `r`/`x` (React), `re` (select custom `{value,options,onChange,style}` — pas de `disabled`), `O` (champ `{label,hint,children}`), `Oe` (slider `{value,min,max,step,onChange,unit,label}`), `ie` (section `{label,right,children}`), `K` (bouton, propage `...rest`), `X` (icône), `se` (bouton-icône `{name,title,onClick,size}`), `te` (badge), `le` (input), `Ze` (interrupteur `{checked,onChange(bool),label}`), `vd` (DropZone maquette), `D` (façade API : `postJson`, `listImages`, `listAudio`, `imageUrl`, `jobVideoUrl`), `Ge` (GET + repli), `Te` (base API), `vn` (paramètre d'URL), `um` (écran Quick), `yd` (carte de la file), `DzQuickEst`, `DzVideoModelSel`, `__dzLibPicker`, `__dzSendTo`, `__dzReopenStudio`, `__dzToast`, `__dzSendNav`.

**État de `um` (noms minifiés, `um` commence au caractère 424118 du bundle mesuré ici)** : `o/i` onglet (`seedance|heygen|comp|voice`), `s/a` prompt, `w/v` image de départ, `g/k` image de fin, `A/V` vibe, `VMQ/dzSetVMQ` modèle, `h/b` durée, `_/z` format, `N/P` graine, `H/F` template, `C/Q` avatar, `ee/ne` voix, `R/W` script, `eng/Eng` moteur HeyGen, `hsrc/Hsrc` source HeyGen, `mimg/Mimg` image animée, `mp/Mp` motion prompt, `xp/Xp` expressivité, `We/De` layout, `u` images, `U` avatars, `Y` voix, `Ce/at` résultat, `n` config (`bt()`), `Ee` ligne d'état de la section Avatar. Le pied « Est. cost + Generate » est un SIBLING du conteneur scroll : il est déjà collé en bas (DESIGN §8.1 satisfait sur ce point, rien à faire en T9).

**Bancs** : `backend/tests/test_quick_<x>.py`, scripts autonomes (isolation d'environnement AVANT `import app`, `def test_*` synchrones, `asyncio.run` à l'intérieur), lancés depuis `backend/` par `python tests/test_quick_<x>.py [noms…]` ; chaque fichier se termine par le lanceur ci-dessous, qui force l'UTF-8 et imprime `PASS <nom>` / `FAIL <nom> -- <raison>` / `BILAN …` (c'est ce que lit la campagne T10). Jamais `pytest tests` global.

```python
if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    _only = set(sys.argv[1:])
    _rouges = 0
    for _nom, _fn in sorted((k, v) for k, v in globals().items()
                            if k.startswith("test_") and callable(v)):
        if _only and _nom not in _only:
            continue
        try:
            _fn()
            print("PASS", _nom)
        except Exception as _e:  # noqa: BLE001 — le banc rapporte, il ne cache pas
            _rouges += 1
            print("FAIL", _nom, "--", str(_e)[:300])
    print("BILAN", "OK" if not _rouges else f"{_rouges} rouge(s)")
    sys.exit(1 if _rouges else 0)
```

**Bancs-miroirs** : on lit le fichier écrit (JSON de recette, `.ass`, mp4 sondé par ffprobe, ligne SQLite), l'image dessinée (frame extraite par ffmpeg, lue par Pillow) ou le bundle écrit — jamais le code qui prétend produire.

**Commits** : sujet sans accents (apostrophes permises), corps accentué libre, pied `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`, via `git commit -F -` et heredoc (pas de guillemets doubles dans `-m`).

**Vérification d'un patch bundle** (à chaque tâche bundle, après le patcher) :

```
python scripts/qa/inventory_bundle.py > %TEMP%\inv_apres.txt
Copy-Item frontend\dist\assets\index-BEOJX8L5.js $env:TEMP\quick.mjs ; node --check $env:TEMP\quick.mjs
```
Sortie attendue de `node --check` : rien (code 0). L'inventaire AVANT se prend une fois au début de T1 (`> %TEMP%\inv_avant.txt`) ; entre deux, seules les lignes « fonctions » changent, du nombre exact de fonctions injectées par la tâche (T1 : +2, T2 : +1, T4 : 0, T9 : +2, les autres 0).

---

## Lot 1 — parité

### Task 1 (P1) : rouvrir un rendu dans Quick, prérempli

**Files :**
- Create : `backend/app/services/quick_recipe.py`
- Create : `scripts/_patch_quick.py` (squelette partagé des neuf patchers)
- Create : `scripts/patch_bundle_quickreopen.py`
- Create : `backend/tests/test_quick_recipe.py`, `backend/tests/test_quick_bundle.py`
- Modify : `backend/app/models/schemas.py:174` (GenerateRequest, après `source_graph`), `:244` (GenerateHeyGenRequest, après `source_graph`), `:320` (CompositionRequest, fin de classe)
- Modify : `backend/app/services/pipeline.py:66-78` (voisin de `_save_source_graph`), `:247`, `:472`, `:948-951` (après le commit de `comp_job`)
- Modify : `backend/app/api/routes.py:227-240` (après `get_job_graph`)

- [ ] **Step 1 : inventaire du bundle AVANT toute tâche**

```
python scripts/qa/inventory_bundle.py > %TEMP%\inv_avant.txt
python scripts/repatch_all.py --list
```
Attendu : la liste des `.bak_*` par mtime ; noter le dernier tag (sur ce worktree `seedance25`, sur le poste installé `libsend`). Ce tag est la baseline écrite dans l'en-tête de chaque patcher.

- [ ] **Step 2 : banc rouge — la recette**

`backend/tests/test_quick_recipe.py` :

```python
"""P1 — la recette Quick d'un rendu est ÉCRITE au démarrage du job (avant tout
appel payant) et RELUE par GET /jobs/{id}/recipe. Le banc lit le JSON sur le
disque et la réponse HTTP, pas le code du pipeline.
Run : python tests/test_quick_recipe.py"""
import asyncio
import json
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ["HEYGEN_API_KEY"] = "test-heygen"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import ASGITransport, AsyncClient                      # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services.storage import init_db                            # noqa: E402
from app.services import fal_service, heygen_service                # noqa: E402

RECETTE = {"v": 1, "tab": "seedance",
           "seedance": {"image": "a.png", "end": "", "prompt": "abysse", "vibe": "deep-sea",
                        "model": "kling-v3-pro", "duration": 10, "aspect": "9:16",
                        "seed": "4421", "template": ""},
           "heygen": {"src": "avatar", "avatar": "", "voice": "", "script": "", "engine": "",
                      "image": "", "motion": "", "expr": ""},
           "layout": "sequential"}


async def _stub_upload(*_a, **_k):
    raise RuntimeError("stub: pas de réseau au banc")


async def _client():
    await init_db()
    (settings.images_path / "a.png").write_bytes(b"\x89PNG\r\n\x1a\nstub")
    fal_service.FalSeedanceClient.upload_image = staticmethod(_stub_upload)
    heygen_service.HeyGenClient.generate_video = _stub_upload
    heygen_service.HeyGenClient.generate_video_v3 = _stub_upload
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


def test_recette_ecrite_puis_relue_pour_seedance():
    async def go():
        async with await _client() as c:
            r = await c.post("/api/generate", json={"image_filename": "a.png", "custom_prompt": "abysse",
                                                    "video_model": "kling-v3-pro",
                                                    "quick_recipe": RECETTE})
            assert r.status_code == 200, r.text
            jobs = (await c.get("/api/jobs")).json()
            job = jobs[0]
            assert job["status"] == "failed", job          # le stub coupe APRÈS l'écriture
            p = settings.outputs_path / "_recipes" / f"{job['job_id']}.json"
            assert p.is_file(), p
            assert json.loads(p.read_text("utf-8")) == RECETTE
            r2 = await c.get(f"/api/jobs/{job['job_id']}/recipe")
            assert r2.status_code == 200 and r2.json() == RECETTE, r2.text
            assert (await c.get("/api/jobs/nope/recipe")).status_code == 404
    asyncio.run(go())


def test_recette_heygen_et_absence_dite():
    async def go():
        async with await _client() as c:
            rec = dict(RECETTE, tab="heygen")
            r = await c.post("/api/generate/heygen", json={"avatar_id": "av1", "voice_id": "v1",
                                                           "script": "salut", "quick_recipe": rec})
            assert r.status_code == 200, r.text
            job = (await c.get("/api/jobs")).json()[0]
            assert (await c.get(f"/api/jobs/{job['job_id']}/recipe")).json()["tab"] == "heygen"
            # sans recette : 404, et rien d'écrit
            r = await c.post("/api/generate", json={"image_filename": "a.png", "custom_prompt": "x"})
            assert r.status_code == 200
            job2 = (await c.get("/api/jobs")).json()[0]
            assert (await c.get(f"/api/jobs/{job2['job_id']}/recipe")).status_code == 404
            assert not (settings.outputs_path / "_recipes" / f"{job2['job_id']}.json").exists()
    asyncio.run(go())
```
puis le lanceur `__main__` de la section « Conventions », recopié tel quel.

- [ ] **Step 3 : rouge**

Run : `cd backend ; python tests/test_quick_recipe.py`
Attendu : `FAIL test_recette_ecrite_puis_relue_pour_seedance -- …` (422 : `quick_recipe` inconnu ou 404 sur `/recipe`) et `BILAN 2 rouge(s)`.

- [ ] **Step 4 : service + schémas + crochets + route**

`backend/app/services/quick_recipe.py` :

```python
"""P1 — la RECETTE d'un rendu Quick : le JSON exact que l'écran a envoyé,
écrit à côté du graphe Studio (`outputs/_graphs`), même patron. Pourquoi un
fichier et pas une colonne : la recette grossit à chaque tâche du plan (voix
off, sous-titres, caméra) et un JSON par job ne demande aucune migration.
Écrit AVANT tout appel payant : si fal échoue, la recette existe quand même —
c'est ce que test_quick_recipe.py mesure."""
import json
from pathlib import Path

from loguru import logger

from app.config import settings


def _dir() -> Path:
    d = settings.outputs_path / "_recipes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(job_id: str, recipe) -> None:
    """Silencieux sur échec (un log) : une recette perdue ne vaut pas un rendu perdu."""
    if not isinstance(recipe, dict) or not recipe:
        return
    try:
        (_dir() / f"{Path(job_id).name}.json").write_text(
            json.dumps(recipe, ensure_ascii=False), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"quick_recipe save failed for {job_id}: {e}")


def load(job_id: str) -> dict | None:
    p = _dir() / f"{Path(job_id).name}.json"
    if not p.is_file():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None
```

`schemas.py` — ajouter après chaque `source_graph: Optional[dict] = None` de `GenerateRequest` (l.174) et `GenerateHeyGenRequest` (l.244), et en fin de `CompositionRequest` (l.320) :

```python
    # P1 — recette Quick (JSON de l'écran) pour « Rouvrir dans Quick ».
    quick_recipe: Optional[dict] = None
```

`pipeline.py` — import en tête (`from app.services import quick_recipe`), puis juste après chaque `_save_source_graph(job_id, getattr(request, "source_graph", None))` de `run` (l.247) et `run_heygen` (l.472) :

```python
            quick_recipe.save(job_id, getattr(request, "quick_recipe", None))
```
et dans `run_composition`, après `session.add(comp_job)` / `await session.commit()` (l.950-951) :

```python
        quick_recipe.save(composition_id, getattr(request, "quick_recipe", None))
```

`routes.py` — après `get_job_graph` (l.240) :

```python
@router.get("/jobs/{job_id}/recipe")
async def get_job_recipe(job_id: str):
    """P1 — la recette Quick qui a produit ce rendu (écrite au démarrage du
    job). 404 sans recette : rendu Studio/Template, ou antérieur au plan Quick —
    l'écran retombe alors sur les colonnes du job (__dzQuickFromJob)."""
    from app.services import quick_recipe
    d = quick_recipe.load(job_id)
    if d is None:
        raise HTTPException(404, "No Quick recipe for this render")
    return d
```

- [ ] **Step 5 : vert**

Run : `cd backend ; python tests/test_quick_recipe.py`
Attendu : `PASS test_recette_ecrite_puis_relue_pour_seedance`, `PASS test_recette_heygen_et_absence_dite`, `BILAN OK`.

- [ ] **Step 6 : squelette partagé des patchers**

`scripts/_patch_quick.py` :

```python
# -*- coding: utf-8 -*-
# scripts/_patch_quick.py
"""Squelette partagé des patchers Quick (plan 2026-09-03-plan-quick).

Reprend, sans les réécrire neuf fois, les gardes éprouvées de
patch_bundle_libsend.py (28/08) : TAG neuf + .bak_<tag> dédié ; garde-chaîne
(refus si un backup AVAL existe, sauf --force-unchained posé par
repatch_all.py) ; mtime du backup poussé EN QUEUE (les .bak_* sont gitignorés,
un worktree frais n'en voit que quatre, la vraie queue est libsend) ; CRLF
conservés (lecture/écriture newline="") ; chaque ancre comptée exactement UNE
fois AVANT d'écrire ; marqueur compté APRÈS ; backup restauré si une
vérification échoue ; --check n'écrit rien.

Un patcher = un module qui appelle run(TAG, MARKER, MARKER_ATTENDU, PATCHES,
POST_COUNTS) avec PATCHES = [(section, ancre, remplacement), ...]. Une ancre à
CONSERVER se recopie dans le remplacement (préfixe ou suffixe).
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")


def _root(args):
    if "--root" in args:
        return pathlib.Path(args[args.index("--root") + 1]).resolve()
    here = pathlib.Path(".").resolve()
    if (here / REL_BUNDLE).is_file():
        return here
    return pathlib.Path(__file__).resolve().parent.parent


def _eol(data: bytes):
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf, data.count(b"\r") - crlf


def _guard_downstream(bak, tag):
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in bak.parent.glob(stem + ".bak_*"):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name}. "
                f"Utiliser : python scripts/repatch_all.py --from {tag}")


def _ensure_tail(bak):
    stem = bak.name.rsplit(".bak_", 1)[0]
    others = [p.stat().st_mtime for p in bak.parent.glob(stem + ".bak_*")
              if p != bak]
    if not others or bak.stat().st_mtime > max(others):
        return
    t = max(time.time(), max(others) + 1.0)
    os.utime(bak, (t, t))


def apply(s, anchor, repl, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, repl)


def run(tag, marker, marker_attendu, patches, post_counts=()):
    args = sys.argv[1:]
    root = _root(args)
    bundle = root / REL_BUNDLE
    if not bundle.is_file():
        raise SystemExit(f"[{tag}] bundle introuvable : {bundle}")
    bak = bundle.with_name(bundle.name + ".bak_" + tag)
    if "--force-unchained" not in args:
        _guard_downstream(bak, tag)
    src = bak if bak.exists() else bundle
    s = src.read_text(encoding="utf-8", newline="")
    if marker in s:
        raise SystemExit(f"[{tag}] marqueur deja present x{s.count(marker)} dans "
                         f"{src.name} : double application refusee.")
    for sec, anchor, _r in patches:
        n = s.count(anchor)
        if n != 1:
            raise SystemExit(f"[{tag}/{sec}] anchor count={n} (want 1). Aborting.")
    if "--check" in args:
        print(f"[{tag}] applicable sur {src.name} : {len(patches)} ancres OK, marqueur absent")
        return
    if not bak.exists():
        shutil.copy2(bundle, bak)
        _ensure_tail(bak)
        print("backup ->", bak.name)
    else:
        shutil.copy2(bak, bundle)
        print("restore <-", bak.name)
    before = bundle.read_bytes()
    crlf0, lf0, cr0 = _eol(before)
    if lf0 or cr0:
        raise SystemExit(f"[{tag}] fins de ligne non homogenes. Aborting.")
    s = bundle.read_text(encoding="utf-8", newline="")
    for sec, anchor, repl in patches:
        s = apply(s, anchor, repl, f"{tag}/{sec}")
    with open(bundle, "w", encoding="utf-8", newline="") as fh:
        fh.write(s)
    after = bundle.read_bytes()
    problems = []
    if _eol(after) != (crlf0, 0, 0):
        problems.append("fins de ligne changees")
    if s.count(marker) != marker_attendu:
        problems.append(f"marqueur x{s.count(marker)} (want {marker_attendu})")
    for probe, want in post_counts:
        if s.count(probe) != want:
            problems.append(f"post {probe} x{s.count(probe)} (want {want})")
    if problems:
        shutil.copy2(bak, bundle)
        raise SystemExit(f"[{tag}] VERIFICATION ECHOUEE, bundle restaure :\n  "
                         + "\n  ".join(problems))
    print(f"OK - bundle patche ({tag}) : {len(patches)} sections, {len(after) - len(before):+d} o")
```

- [ ] **Step 7 : banc-miroir du bundle (rouge)**

`backend/tests/test_quick_bundle.py` (créé ici, une fonction ajoutée par tâche bundle) :

```python
"""Miroir du bundle patché par le plan Quick : on lit le fichier ÉCRIT
(frontend/dist/assets/index-BEOJX8L5.js) et l'on compte — marqueurs, ancres
conservées, pins de l'amont (libsend/libpicker) qui attrapent un effacement
silencieux de la chaîne. Run : python tests/test_quick_bundle.py"""
import pathlib
import sys

_RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
_BUNDLE = _RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"


def _s() -> str:
    return _BUNDLE.read_text("utf-8")


def test_amont_intact():
    s = _s()
    assert s.count("__dzQuickStart") == 3, s.count("__dzQuickStart")
    assert s.count("__dzLibPicker") == 10
    assert s.count("__dzSendTo") == 2
    assert s.count("function um(") == 1


def test_quickreopen():
    s = _s()
    assert s.count("__dzReopenQuick") == 3          # définition + modal + carte de la file
    assert s.count("function __dzQuickFromJob(") == 1
    assert s.count("quick_recipe:dzQuickRecipe()") == 3   # /generate, /generate/heygen, /generate/composition
    assert s.count('"deepotus:quick-recipe"') == 2  # émission (helper) + écoute (um)
    assert 'children:"Rouvrir dans Quick"' in s
    assert 'title:"Rouvrir dans Quick (prérempli)"' in s
```
puis le lanceur `__main__` des Conventions.

Run : `cd backend ; python tests/test_quick_bundle.py`
Attendu : `PASS test_amont_intact`, `FAIL test_quickreopen -- …`, `BILAN 1 rouge(s)`.

- [ ] **Step 8 : patcher `quickreopen`**

`scripts/patch_bundle_quickreopen.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_quickreopen.py
"""P1 — « Rouvrir dans Quick, prérempli » (plan 2026-09-03-plan-quick, T1).
BASELINE : bundle POST-patch libsend (queue de chaîne du 28/08).
Backup dédié : .js.bak_quickreopen. Position : EN QUEUE.

Q1 helpers module-scope avant __dzReopenStudio : __dzQuickFromJob (recette de
   repli depuis les colonnes du job, pour les rendus d'avant P1) et
   __dzReopenQuick (GET /recipe, repli GET /jobs/{id}, pose window.__dzQuickRecipe,
   navigue, puis émet deepotus:quick-recipe si Quick est déjà monté).
Q2 um : dzQuickRecipe() (le JSON envoyé) + dzQuickApply(rc) (rejoue chaque
   setter) + effet de montage (global puis événement, via un ref pour lire
   l'état courant, pas celui du montage).
Q3-Q5 les trois payloads portent quick_recipe EN TÊTE (les queues restent
   des ancres libres pour T4/T5/T7/T8).
Q6 modal Bibliothèque : bouton après « Envoyer vers… » (le suffixe ,"dzsend")
   est la fin du bouton libsend — on AJOUTE après, jamais dedans).
Q7 carte de la file (yd) : icône ⚡ avant « Copy », réservée aux vrais jobs (m).
Run : python scripts/patch_bundle_quickreopen.py [--check]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_quick import run  # noqa: E402

TAG = "quickreopen"
MARKER = "__dzReopenQuick"

Q1 = (
    'function __dzQuickFromJob(j){var sd=(j&&j.provider)||"seedance";'
    'return{v:1,tab:sd==="heygen"?"heygen":sd==="composition"?"comp":"seedance",'
    'seedance:{image:j.image_filename||"",end:j.image_filename_end||"",prompt:j.final_prompt||"",'
    'vibe:"cinematic",model:j.video_model||"",duration:j.duration_s||10,aspect:j.aspect_ratio||"9:16",'
    'seed:j.seed!=null?String(j.seed):"",template:j.template_id||""},'
    'heygen:{src:"avatar",avatar:sd==="heygen"?(j.image_filename||""):"",voice:"",'
    'script:sd==="heygen"?(j.final_prompt||""):"",engine:"",image:"",motion:"",expr:""},'
    'layout:j.composition_layout||"sequential"}}'
    'function __dzReopenQuick(id){'
    'fetch("/api/jobs/"+encodeURIComponent(id)+"/recipe").then(function(r){return r.ok?r.json():null})'
    '.then(function(rec){if(rec&&rec.tab)return rec;'
    'return fetch("/api/jobs/"+encodeURIComponent(id)).then(function(r){return r.ok?r.json():null})'
    '.then(function(j){return j?__dzQuickFromJob(j):null})})'
    '.then(function(rec){if(!rec){__dzToast("Rendu introuvable — rien à rouvrir");return}'
    'window.__dzQuickRecipe=rec;__dzSendNav("quick");'
    'setTimeout(function(){window.dispatchEvent(new CustomEvent("deepotus:quick-recipe",{detail:rec}))},60);'
    '__dzToast("Quick prérempli depuis le rendu "+String(id).slice(0,8)+" — varie, puis Générer")})'
    '.catch(function(e){window.alert("Rouvrir dans Quick : "+String(e&&e.message||e))})}'
)

Q2 = (
    'function dzQuickRecipe(){return{v:1,tab:o,seedance:{image:w,end:g,prompt:s,vibe:A,model:VMQ,'
    'duration:h,aspect:_,seed:N,template:H||""},heygen:{src:hsrc,avatar:C,voice:ee,script:R,engine:eng,'
    'image:mimg,motion:mp,expr:xp},layout:We}}'
    'function dzQuickApply(rc){if(!rc)return;var sd=rc.seedance||{},hg=rc.heygen||{};'
    'if(rc.tab&&["seedance","heygen","comp","voice"].indexOf(rc.tab)>=0)i(rc.tab);'
    'if(sd.image!=null){v(sd.image);if(!u.length)try{window.__dzQuickStart=sd.image}catch(_e){}}'
    'if(sd.end!=null)k(sd.end);if(sd.prompt)a(sd.prompt);if(sd.vibe)V(sd.vibe);'
    'if(sd.model!=null){dzSetVMQ(sd.model);try{localStorage.setItem("dz_video_model",sd.model)}catch(_e){}}'
    'if(sd.duration)b(Number(sd.duration));if(sd.aspect)z(sd.aspect);if(sd.seed!=null)P(String(sd.seed));'
    'if(sd.template!=null)F(sd.template);'
    'if(hg.src)Hsrc(hg.src);if(hg.avatar)Q(hg.avatar);if(hg.voice)ne(hg.voice);if(hg.script)W(hg.script);'
    'if(hg.engine!=null)Eng(hg.engine);if(hg.image!=null)Mimg(hg.image);if(hg.motion!=null)Mp(hg.motion);'
    'if(hg.expr!=null)Xp(hg.expr);if(rc.layout)De(rc.layout)}'
    'var dzApplyRef=x.useRef(null);dzApplyRef.current=dzQuickApply;'
    'x.useEffect(function(){var r0=null;try{r0=window.__dzQuickRecipe;delete window.__dzQuickRecipe}catch(_e){}'
    'if(r0)dzApplyRef.current(r0);function onR(ev){dzApplyRef.current(ev.detail)}'
    'window.addEventListener("deepotus:quick-recipe",onR);'
    'return function(){window.removeEventListener("deepotus:quick-recipe",onR)}},[]);'
)

A_STUDIO = "function __dzReopenStudio(id){"
A_STATE = "[Ce,at]=x.useState(null);"
A_P_SEED = "je={video_model:VMQ||void 0,image_filename:w,"
A_P_HG = 'D.postJson("/generate/heygen",{avatar_id:C,'
A_P_COMP = 'D.postJson("/generate/composition",{seedance:{video_model:'
A_MODAL = 'children:"Envoyer vers…"},"dzsend"),'
A_CARD = 'r.jsx(se,{name:"copy",title:e.status==="succeeded"?"Copy video URL":"Copy job id",onClick:n}),'

PATCHES = [
    ("Q1-helpers", A_STUDIO, Q1 + A_STUDIO),
    ("Q2-um-recette", A_STATE, A_STATE + Q2),
    ("Q3-payload-seedance", A_P_SEED, "je={quick_recipe:dzQuickRecipe(),video_model:VMQ||void 0,image_filename:w,"),
    ("Q4-payload-heygen", A_P_HG, 'D.postJson("/generate/heygen",{quick_recipe:dzQuickRecipe(),avatar_id:C,'),
    ("Q5-payload-comp", A_P_COMP, 'D.postJson("/generate/composition",{quick_recipe:dzQuickRecipe(),seedance:{video_model:'),
    ("Q6-modal", A_MODAL, A_MODAL + 'm.kind==="render"&&m.jobId&&r.jsx(K,{variant:"ghost",size:"sm",icon:"bolt",'
     'onClick:()=>{y(null);__dzReopenQuick(m.jobId)},children:"Rouvrir dans Quick"},"dzquick"),'),
    ("Q7-carte-file", A_CARD, 'm&&r.jsx(se,{name:"bolt",title:"Rouvrir dans Quick (prérempli)",'
     'onClick:function(){__dzReopenQuick(e.id)}}),' + A_CARD),
]

if __name__ == "__main__":
    run(TAG, MARKER, 3, PATCHES, [("__dzQuickStart", 4), ("__dzLibPicker", 10), ("__dzSendTo", 2)])
```
Pourquoi `__dzQuickStart` passe à 4 : `dzQuickApply` pose le global quand la liste d'images n'est pas encore chargée, parce que le `.then` de `listImages` (greffe libsend) tient un `w` figé à `""` et écraserait l'image de la recette avec `je[0]` — mesuré dans le code de la greffe (`dzq?v(dzq):(!w&&je.length&&v(je[0]))`). Mettre à jour la pin de `test_library_sendto.py` (`__dzQuickStart` 3 → 4) avec la raison en commentaire, et `test_amont_intact` ci-dessus (3 → 4).

Run : `python scripts/patch_bundle_quickreopen.py --check` puis `python scripts/patch_bundle_quickreopen.py`
Attendu : `[quickreopen] applicable … 7 ancres OK`, puis `backup -> index-BEOJX8L5.js.bak_quickreopen` et `OK - bundle patche (quickreopen) : 7 sections, +NNNN o`. Puis la vérification bundle des Conventions (`node --check` muet ; inventaire : +2 fonctions).

- [ ] **Step 9 : vert + sonde**

Run : `cd backend ; python tests/test_quick_bundle.py` puis `cd backend ; python -m pytest tests/test_library_sendto.py -q`
Attendu : `BILAN OK` ; puis `3 passed` (`test_library_sendto.py` est un banc pytest historique, SANS lanceur `__main__` : `python tests/test_library_sendto.py` ne lancerait rien et sortirait 0 — un vert menteur).
Sonde navigateur (backend relancé par l'utilisateur) : ouvrir Library → un rendu → « Rouvrir dans Quick » ; dans la console : `document.querySelector('[data-dzselect]')` non nul et `!!window.__dzQuickRecipe === false` (consommé), l'onglet actif porte le provider du rendu, le champ Prompt contient `final_prompt` du job.

- [ ] **Step 10 : commit**

```bash
git add backend/app/services/quick_recipe.py backend/app/models/schemas.py backend/app/services/pipeline.py backend/app/api/routes.py scripts/_patch_quick.py scripts/patch_bundle_quickreopen.py backend/tests/test_quick_recipe.py backend/tests/test_quick_bundle.py backend/tests/test_library_sendto.py frontend/dist/assets/index-BEOJX8L5.js
git commit -F - <<'EOF'
quick : P1 - rouvrir un rendu dans Quick, prerempli (recette JSON + patch quickreopen)

La recette est écrite AVANT tout appel payant (outputs/_recipes/{job}.json),
relue par GET /jobs/{id}/recipe, repli sur les colonnes du job pour les rendus
antérieurs. Squelette partagé scripts/_patch_quick.py pour les neuf patchers.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

### Task 2 (P2) : extension générative d'un clip déjà rendu

**Files :**
- Create : `backend/app/services/fal_video_tools.py`, `scripts/patch_bundle_quickextend.py`, `backend/tests/test_quick_extend.py`
- Modify : `backend/app/models/schemas.py:83-89` (`Provider`), `:322-326` (après `CompositionResponse`)
- Modify : `backend/app/services/storage.py:56-57` (colonne `jobs`), `:377-379` (`V1_2_NEW_COLUMNS`)
- Modify : `backend/app/services/pipeline.py:442` (après le `return job_id` de `run`)
- Modify : `backend/app/api/routes.py:3128` (après `generate_composition`)
- Modify : `backend/app/services/pricing.py:68` (DEFAULTS) et `:274` (avant `elif kind == "transcribe"`)
- Modify : `backend/tests/test_quick_bundle.py` (+1 fonction)

- [ ] **Step 1 : MESURE — le contrat exact de l'endpoint fal (la tâche en dépend)**

R1 a vérifié les CAPACITÉS le 03/09 (source ≤ 8 s, 720p/1080p, 16:9 ou 9:16, +7 s, audio par défaut) mais **ni l'identifiant d'endpoint ni les noms de champs**. On les lit avant d'écrire une ligne :

```
curl -s "https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/veo3.1/extend-video" > %TEMP%\veo_extend.json
python -c "import json;d=json.load(open(r'%TEMP%\veo_extend.json',encoding='utf-8'));s=d.get('components',{}).get('schemas',{});print(list(s));print(json.dumps(s,ensure_ascii=False)[:2500])"
```

| Ce que la mesure rend | Ce qu'on écrit dans `EXTEND_MODELS` |
|---|---|
| un schéma avec un champ vidéo `video_url` | `endpoint="fal-ai/veo3.1/extend-video"`, `video_param="video_url"` |
| un schéma avec un autre nom de champ vidéo | ce nom-là, et l'en-tête du module cite la date de mesure |
| 404 / pas de schéma | réessayer `fal-ai/veo3.1/fast/extend-video`, puis `fal-ai/veo3/extend-video` ; le premier qui rend un schéma gagne |
| aucun des trois ne rend de schéma | **T2 s'arrête là** : on livre `fal_video_tools.py` avec `EXTEND_MODELS = {}`, la route qui rend **501 « extension générative : aucun endpoint fal mesuré le 03/09/2026 »**, le banc qui vérifie ce 501, et AUCUN patch bundle. Pas de bouton qui promet ce qui n'existe pas |

Noter la valeur retenue en tête de `fal_video_tools.py` avec la date. La suite suppose la première ligne du tableau.

- [ ] **Step 2 : banc rouge — les gardes lisent ce que ffprobe MESURE**

`backend/tests/test_quick_extend.py` :

```python
"""P2 — les gardes de l'extension portent sur un VRAI fichier : le banc écrit
trois mp4 avec ffmpeg (9 s en 9:16, 5 s en 9:16, 5 s en 1:1), les fait mesurer
par ffprobe, et lit le message de refus. Aucun appel réseau.
Run : python tests/test_quick_extend.py"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import fal_video_tools as FV                       # noqa: E402


def _mp4(nom: str, secs: float, w: int, h: int) -> pathlib.Path:
    p = _tmp / nom
    exe = shutil.which("ffmpeg") or os.path.expandvars(
        r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")
    subprocess.run([exe, "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"testsrc=size={w}x{h}:rate=24:duration={secs}",
                    "-pix_fmt", "yuv420p", str(p)], check=True, timeout=120)
    return p


def test_source_trop_longue_refusee_en_citant_la_mesure():
    src = FV.probe(_mp4("long.mp4", 9, 720, 1280))
    assert 8.5 < src["duration_s"] < 9.5, src
    assert src["ratio"] == "9:16", src
    try:
        FV.guard_extend("veo-3.1-extend", src)
    except ValueError as e:
        m = str(e)
        assert "9.0 s" in m, m                    # la mesure est DANS le refus
        assert "8 s" in m and "Montage" in m, m   # et la sortie de secours aussi
    else:
        raise AssertionError("une source de 9 s a été acceptée")


def test_source_conforme_acceptee_et_args_conformes():
    src = FV.probe(_mp4("court.mp4", 5, 720, 1280))
    FV.guard_extend("veo-3.1-extend", src)        # ne lève pas
    ep, args = FV.build_extend_args("veo-3.1-extend",
                                    video_url="https://x/y.mp4", prompt="plus loin")
    m = FV.EXTEND_MODELS["veo-3.1-extend"]
    assert ep == m["endpoint"], ep
    assert args[m["video_param"]] == "https://x/y.mp4", args
    assert args["prompt"] == "plus loin", args


def test_format_hors_contrat_refuse_en_citant_les_pixels():
    src = FV.probe(_mp4("carre.mp4", 5, 512, 512))
    try:
        FV.guard_extend("veo-3.1-extend", src)
    except ValueError as e:
        assert "512x512" in str(e) and "1:1" in str(e), str(e)
    else:
        raise AssertionError("un carré a été accepté")
```
puis le lanceur `__main__` des Conventions, recopié tel quel.

- [ ] **Step 3 : rouge**

Run : `cd backend ; python tests/test_quick_extend.py`
Attendu : `ModuleNotFoundError: No module named 'app.services.fal_video_tools'` à l'import (le banc s'arrête avant `BILAN` — c'est le rouge d'un module absent).

- [ ] **Step 4 : le service**

`backend/app/services/fal_video_tools.py` :

```python
"""P2/P5 — les outils fal qui prennent une VIDÉO en entrée (extension
générative, lip-sync), par opposition à fal_service.py qui part d'une image.

Pourquoi un module séparé : ici la garde ne porte pas sur ce que l'écran
promet mais sur ce que ffprobe MESURE du fichier déjà rendu — durée, taille,
format. Et un refus doit citer la mesure : « ce clip fait 9,0 s » vaut mieux
que « source invalide », parce que l'utilisateur sait alors quoi couper.

Contrats gelés le 03/09/2026 (capacités vérifiées en R1 du balayage ; noms de
champs relevés à l'étape 1 de T2). Tout est PUR sauf `probe`, qui lance ffprobe.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

EXTEND_MODELS: dict = {
    "veo-3.1-extend": {
        "label": "Veo 3.1 · extension",
        "endpoint": "fal-ai/veo3.1/extend-video",   # ← étape 1 de T2
        "video_param": "video_url",                  # ← étape 1 de T2
        "max_source_s": 8.0,
        "added_s": 7,
        "ratios": ["16:9", "9:16"],
        "usd_per_s": 0.10,          # miroir de pricing.DEFAULTS["extend_usd_per_s"]
    },
}


def _bin(name: str) -> str:
    exe = shutil.which(name)
    if exe:
        return exe
    cand = os.path.expandvars(
        r"%LOCALAPPDATA%\DeepotusVideoGen\bin" + f"\\{name}.exe")
    return cand if os.path.isfile(cand) else name


def ratio_of(w: int, h: int) -> str:
    """Le format NOMMÉ le plus proche — l'app n'en connaît que quatre."""
    if not w or not h:
        return "?"
    r = w / float(h)
    connus = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0, "4:5": 4 / 5}
    return min(connus, key=lambda k: abs(connus[k] - r))


def probe(path) -> dict:
    """{duration_s, width, height, ratio} d'un fichier vidéo, par ffprobe."""
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"Clip source introuvable : {p.name}")
    out = subprocess.run(
        [_bin("ffprobe"), "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-show_entries",
         "format=duration", "-of", "json", str(p)],
        capture_output=True, timeout=60)
    d = json.loads(out.stdout.decode("utf-8", "replace") or "{}")
    st = (d.get("streams") or [{}])[0]
    w, h = int(st.get("width") or 0), int(st.get("height") or 0)
    dur = float((d.get("format") or {}).get("duration") or 0)
    return {"duration_s": round(dur, 3), "width": w, "height": h,
            "ratio": ratio_of(w, h)}


def guard_extend(model_id: str, src: dict) -> None:
    """Lève ValueError AVANT tout appel payant, message citant la mesure."""
    m = EXTEND_MODELS.get(model_id)
    if m is None:
        raise ValueError(
            f"Modèle d'extension inconnu : {model_id}. Disponibles : "
            + (", ".join(sorted(EXTEND_MODELS)) or "aucun (endpoint non mesuré)"))
    d = float(src.get("duration_s") or 0)
    if d <= 0:
        raise ValueError("Durée du clip source illisible — ffprobe n'a rien rendu.")
    if d > m["max_source_s"]:
        raise ValueError(
            f"{m['label']} n'accepte qu'une source de {m['max_source_s']:.0f} s "
            f"au plus ; ce clip fait {d:.1f} s. Coupe-le au Montage, puis relance "
            f"l'extension sur le morceau.")
    if src.get("ratio") not in m["ratios"]:
        raise ValueError(
            f"{m['label']} n'accepte que {' et '.join(m['ratios'])} ; ce clip est "
            f"en {src.get('ratio')} ({src.get('width')}x{src.get('height')}).")


def build_extend_args(model_id: str, *, video_url: str, prompt: str = "") -> tuple:
    m = EXTEND_MODELS[model_id]
    return m["endpoint"], {m["video_param"]: video_url, "prompt": prompt or ""}
```

- [ ] **Step 5 : vert**

Run : `cd backend ; python tests/test_quick_extend.py`
Attendu : `PASS test_format_hors_contrat_refuse_en_citant_les_pixels`, `PASS test_source_conforme_acceptee_et_args_conformes`, `PASS test_source_trop_longue_refusee_en_citant_la_mesure`, `BILAN OK`.

- [ ] **Step 6 : lignée, schéma, pipeline, routes, pricing**

`schemas.py` — dans `Provider`, après `NEWS = "news"` (l.89) :

```python
    EXTEND = "extend"          # P2 — clip prolongé par le modèle
```

`schemas.py` — après `CompositionResponse` (l.326) :

```python
class ExtendRequest(BaseModel):
    """P2 — prolonger un rendu existant. `parent_job_id` porte la lignée : le
    clip fils s'affiche sous son père dans la file et la Bibliothèque."""
    parent_job_id: str = Field(..., min_length=1, max_length=36)
    model: str = Field("veo-3.1-extend", max_length=48)
    prompt: Optional[str] = Field(None, max_length=2000)
    quick_recipe: Optional[dict] = None
```

`storage.py` — dans `JobRecord`, après `video_model` (l.57) :

```python
    # P2 — le rendu dont ce clip est l'extension (lignée dans la file)
    parent_job_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True)
```
et dans `V1_2_NEW_COLUMNS`, après `("video_model", "VARCHAR(48)"),` (l.378) :

```python
    # P2 — lignée d'extension
    ("parent_job_id", "VARCHAR(36)"),
```

`pipeline.py` — méthode ajoutée après le `return job_id` de `run` (l.442), juste avant le commentaire `# ----- HeyGen pipeline (v1.4) -----` :

```python
    async def run_extend(self, request) -> str:
        """P2 — un clip DÉJÀ rendu, prolongé par le modèle. Les gardes ont
        déjà tourné dans la route (400 lisible) ; elles retournent ici parce
        qu'un appel direct au pipeline ne doit pas pouvoir les sauter."""
        import fal_client
        from app.services import fal_video_tools as FV
        from app.services import quick_recipe
        parent = await Pipeline.get_job(request.parent_job_id)
        if parent is None or not parent.final_video_path:
            raise ValueError(
                f"Rendu source introuvable ou sans vidéo : {request.parent_job_id}")
        src = await asyncio.to_thread(FV.probe, parent.final_video_path)
        FV.guard_extend(request.model, src)
        job_id = str(uuid4())
        m = FV.EXTEND_MODELS[request.model]
        async with async_session_factory() as session:
            job = JobRecord(
                id=job_id, status=JobStatus.QUEUED.value,
                image_filename=parent.image_filename or "",
                provider=Provider.EXTEND.value, parent_job_id=parent.id,
                video_model=request.model, aspect_ratio=src["ratio"],
                duration_s=int(round(src["duration_s"])) + m["added_s"],
                final_prompt=request.prompt or "",
                title=f"Extension de {(parent.title or parent.id)[:40]}",
                created_at=datetime.utcnow())
            session.add(job)
            await session.commit()
            quick_recipe.save(job_id, getattr(request, "quick_recipe", None))
            try:
                await self._update(session, job, status=JobStatus.UPLOADING.value,
                                   current_step="Uploading source clip", progress=10)
                url = await fal_client.upload_file_async(str(parent.final_video_path))
                endpoint, args = FV.build_extend_args(
                    request.model, video_url=url, prompt=request.prompt or "")
                await self._update(session, job,
                                   status=JobStatus.GENERATING_VIDEO.value,
                                   current_step="Extending clip", progress=35)
                res = await fal_client.subscribe_async(endpoint, arguments=args,
                                                       with_logs=True)
                vurl = FalSeedanceClient.extract_video_url(res)
                if not vurl:
                    raise RuntimeError("fal.ai : réponse sans URL vidéo")
                dest = settings.outputs_path / "final" / f"{job_id}.mp4"
                await FalSeedanceClient.download_video(vurl, dest)
                await self._update(session, job, video_path=str(dest),
                                   final_video_path=str(dest),
                                   status=JobStatus.DONE.value,
                                   current_step="Complete", progress=100,
                                   completed_at=datetime.utcnow())
            except Exception as e:
                logger.exception(f"Extend {job_id} failed: {e}")
                await self._update(session, job, status=JobStatus.FAILED.value,
                                   current_step="Failed", error=str(e),
                                   completed_at=datetime.utcnow())
                raise
        return job_id
```

`routes.py` — après `generate_composition` (l.3128) ; ajouter `ExtendRequest` à l'import de `app.models.schemas` en tête de fichier :

```python
@router.get("/generate/extend/check")
async def check_extend(job_id: str, model: str = "veo-3.1-extend"):
    """P2 — MESURER avant de proposer. L'écran appelle ceci pour savoir s'il
    peut afficher « Prolonger » : on rend la mesure, le verdict et le prix,
    jamais un simple booléen — la raison du refus est la moitié utile."""
    from app.services import fal_video_tools as FV
    from app.services import pricing as _pricing
    if not FV.EXTEND_MODELS:
        raise HTTPException(501, "Extension générative : aucun endpoint fal "
                                 "mesuré le 03/09/2026.")
    j = await Pipeline.get_job(job_id)
    if j is None or not j.final_video_path:
        raise HTTPException(404, "Rendu introuvable ou sans vidéo finale")
    src = await asyncio.to_thread(FV.probe, j.final_video_path)
    m = FV.EXTEND_MODELS.get(model) or {}
    try:
        FV.guard_extend(model, src)
        ok, reason = True, ""
    except ValueError as e:
        ok, reason = False, str(e)
    est = _pricing.estimate({"kind": "extend", "model": model,
                             "duration_s": m.get("added_s", 7)})
    return {"ok": ok, "reason": reason, "source": src,
            "added_s": m.get("added_s", 7), "usd": est["total_usd"],
            "label": m.get("label", model)}


@router.post("/generate/extend")
async def generate_extend(request: ExtendRequest, background_tasks: BackgroundTasks):
    """P2 — prolonger un rendu. Les gardes tournent ICI, en synchrone : un
    refus doit être une 400 lisible à l'écran, pas un job rouge dans la file."""
    from app.services import fal_video_tools as FV
    if not FV.EXTEND_MODELS:
        raise HTTPException(501, "Extension générative : aucun endpoint fal "
                                 "mesuré le 03/09/2026.")
    if not settings.FAL_KEY:
        raise HTTPException(400, "FAL_KEY not configured. Add it to backend/.env")
    j = await Pipeline.get_job(request.parent_job_id)
    if j is None or not j.final_video_path:
        raise HTTPException(404, "Rendu introuvable ou sans vidéo finale")
    src = await asyncio.to_thread(FV.probe, j.final_video_path)
    try:
        FV.guard_extend(request.model, src)
    except ValueError as e:
        raise HTTPException(400, str(e))

    async def _run():
        try:
            await pipeline.run_extend(request)
        except Exception as e:
            logger.error(f"Background extend error: {e}")

    background_tasks.add_task(_run)
    return GenerateResponse(job_id="pending", status=JobStatus.QUEUED,
                            message="Extension queued. Poll GET /jobs.")
```

`pricing.py` — dans `DEFAULTS`, après le bloc `"video_usd_per_s": {...},` (l.68) :

```python
    # P2 — extension générative d'un clip ($/s de vidéo AJOUTÉE). Miroir de
    # fal_video_tools.EXTEND_MODELS[...]["usd_per_s"] : changer LÀ-BAS d'abord.
    "extend_usd_per_s": {"veo-3.1-extend": 0.10},
```
et dans `estimate`, avant `elif kind == "transcribe":` (l.274) :

```python
    elif kind == "extend":
        model = str(op.get("model") or "veo-3.1-extend")
        secs = float(op.get("duration_s", 7))
        rates = p.get("extend_usd_per_s") or DEFAULTS["extend_usd_per_s"]
        rate = float(rates.get(model, 0.10))
        lines.append(_line("fal", f"Extension ({model})", secs, "s", secs * rate))
```

- [ ] **Step 7 : vert backend**

Run : `cd backend ; python tests/test_quick_extend.py` puis `cd backend ; python tests/test_hygiene_imports.py`
Attendu : `BILAN OK` deux fois (le second garde l'absence d'import local masquant un import de module — la panne seedance du 28/08).

- [ ] **Step 8 : patcher `quickextend` + sa pin**

Ajouter dans `backend/tests/test_quick_bundle.py` :

```python
def test_quickextend():
    s = _s()
    assert s.count("__dzExtendClip") == 2          # définition + entrée du menu
    assert "Prolonger le clip (+7 s, Veo 3.1)" in s
    assert "/api/generate/extend/check?job_id=" in s
```

`scripts/patch_bundle_quickextend.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_quickextend.py
"""P2 — « Prolonger le clip » (plan 2026-09-03-plan-quick, T2).
BASELINE : bundle POST-patch quickreopen. Backup : .js.bak_quickextend. EN QUEUE.

X1 helper __dzExtendClip(id) : MESURE d'abord (GET /generate/extend/check),
   n'ouvre l'invite que si ok, affiche la raison sinon — le refus est ce que
   l'utilisateur a besoin de lire, pas un bouton grisé sans explication.
X2 entrée du menu « Envoyer vers… », branche render (m.kind==="render").
Run : python scripts/patch_bundle_quickextend.py [--check]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_quick import run  # noqa: E402

TAG = "quickextend"
MARKER = "__dzExtendClip"

X1 = (
    'function __dzExtendClip(id){'
    'fetch("/api/generate/extend/check?job_id="+encodeURIComponent(id))'
    '.then(function(r){return r.json().then(function(d){return{s:r.status,d:d}})})'
    '.then(function(o){if(o.s===501){__dzToast("Extension générative : aucun endpoint fal mesuré");return}'
    'if(o.s!==200){__dzToast("Prolonger : "+((o.d&&o.d.detail)||o.s));return}'
    'if(!o.d.ok){window.alert("Prolonger — refusé\\n\\n"+o.d.reason);return}'
    'var p=window.prompt("Que se passe-t-il dans les "+o.d.added_s+" s ajoutées ?\\n"'
    '+"Source "+o.d.source.duration_s+" s · "+o.d.source.ratio+" · ≈ $"+Number(o.d.usd).toFixed(2),"");'
    'if(p===null)return;'
    'fetch("/api/generate/extend",{method:"POST",headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify({parent_job_id:id,model:"veo-3.1-extend",prompt:p})})'
    '.then(function(r){return r.json().then(function(d){return{s:r.status,d:d}})})'
    '.then(function(o2){__dzToast(o2.s===200?"Extension lancée — suis la file":'
    '("Prolonger : "+((o2.d&&o2.d.detail)||o2.s)))})})'
    '.catch(function(e){window.alert("Prolonger : "+String(e&&e.message||e))})}'
)

A_STUDIO = "function __dzReopenStudio(id){"
A_MENU = 'if(m.kind==="render"&&m.jobId){items.push({lbl:"\U0001f39e Montage — clip vidéo",'

PATCHES = [
    ("X1-helper", A_STUDIO, X1 + A_STUDIO),
    ("X2-menu", A_MENU,
     'if(m.kind==="render"&&m.jobId){items.push({lbl:"⚡ Prolonger le clip (+7 s, Veo 3.1)",'
     'fn:function(){onClose&&onClose();__dzExtendClip(m.jobId)}});'
     'items.push({lbl:"\U0001f39e Montage — clip vidéo",'),
]

if __name__ == "__main__":
    run(TAG, MARKER, 2, PATCHES, [("__dzSendTo", 2), ("__dzReopenQuick", 3)])
```

Run : `python scripts/patch_bundle_quickextend.py --check` puis `python scripts/patch_bundle_quickextend.py`
Attendu : `[quickextend] applicable sur … : 2 ancres OK, marqueur absent`, puis `backup -> index-BEOJX8L5.js.bak_quickextend` et `OK - bundle patche (quickextend) : 2 sections, +NNNN o`. Puis la vérification bundle des Conventions (`node --check` muet ; inventaire : +1 fonction).

- [ ] **Step 9 : vert bundle**

Run : `cd backend ; python tests/test_quick_bundle.py`
Attendu : `PASS test_amont_intact`, `PASS test_quickextend`, `PASS test_quickreopen`, `BILAN OK`.

- [ ] **Step 10 : commit**

```bash
git add backend/app/services/fal_video_tools.py backend/app/models/schemas.py backend/app/services/storage.py backend/app/services/pipeline.py backend/app/api/routes.py backend/app/services/pricing.py backend/tests/test_quick_extend.py backend/tests/test_quick_bundle.py scripts/patch_bundle_quickextend.py frontend/dist/assets/index-BEOJX8L5.js
git commit -F - <<'EOF'
quick : P2 - extension generative d'un clip (garde mesuree par ffprobe)

Le refus cite la mesure (« ce clip fait 9,0 s ») et la sortie de secours
(couper au Montage). La lignée passe par jobs.parent_job_id. L'écran mesure
avant de proposer (GET /generate/extend/check) au lieu de griser en silence.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 3 (P3) : l'image de fin exposée, grisée avec la raison

**Files :**
- Create : `scripts/patch_bundle_quickend.py`
- Modify : `backend/tests/test_quick_bundle.py` (+1 fonction)
- Backend : **aucun** — `GET /api/video-models` rend déjà `end_image` par modèle (`routes.py:4884`).

- [ ] **Step 1 : la mesure qui fixe le libellé**

Le refus doit nommer les modèles qui savent le faire, sinon « non supporté » envoie chercher. On relit le registre :

```
cd backend
python -c "from app.services.fal_service import VIDEO_MODELS as V; print('OUI:', [k for k,m in V.items() if m['end_image']]); print('NON:', [k for k,m in V.items() if not m['end_image']])"
```
Attendu : `OUI:` six ids (`seedance-v1-pro`, `seedance-2`, `seedance-2-fast`, `seedance-2.5`, `kling-v3-pro`, `kling-v3-standard`) ; `NON:` cinq ids (`pixverse-v6`, `veo-3.1-fast-fal`, `veo-3.1-google`, `veo-3.1-fast-google`, `veo-3.1-lite-google`). Le patcher n'écrit AUCUNE de ces listes en dur : il lit `/video-models` au montage. La mesure sert à confirmer le 6/11 de R1 et à écrire l'attendu du banc.

- [ ] **Step 2 : banc rouge**

Ajouter dans `backend/tests/test_quick_bundle.py` :

```python
def test_quickend():
    s = _s()
    assert s.count("dzSetEndCaps") == 2     # déclaration + le seul appel
    assert s.count("function dzEndOK(") == 1
    assert s.count("function dzEndWhy(") == 1
    assert "Image de fin — indisponible" in s      # le libellé porte la raison
    assert "n'accepte pas d'image de fin" in s
    assert 'image_filename_end:(dzEndOK()?g:"")||null,' in s
```

Run : `cd backend ; python tests/test_quick_bundle.py`
Attendu : `FAIL test_quickend -- …`, les autres `PASS`, `BILAN 1 rouge(s)`.

- [ ] **Step 3 : le patcher**

`scripts/patch_bundle_quickend.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_quickend.py
"""P3 — l'image de fin, VISIBLE et grisée AVEC LA RAISON (T3).
BASELINE : bundle POST-patch quickextend. Backup : .js.bak_quickend. EN QUEUE.

Pourquoi ce n'est pas une simple prop `disabled` : le select custom `re` du
bundle N'A PAS de prop `disabled` (mesuré le 03/09, cf. Conventions du plan).
On remplace donc le champ par un bloc qui, quand le modèle refuse le
first-last, affiche une ligne d'explication À LA PLACE du select.

E1 état dzEndCaps (id -> end_image) + chargement /video-models + dzEndOK /
   dzEndWhy, greffés sur la chaîne posée par T1 (var dzApplyRef=…).
E2 le champ « End image » devient conditionnel et porte la raison.
E3 le bouton « Parcourir les vignettes… » de fin disparaît quand c'est refusé.
E4 le payload n'envoie JAMAIS une image de fin que le modèle refuse (une 404
   du backend sur un champ grisé serait un mensonge de plus).
E5 changer de modèle vide le champ (sinon la valeur reste, invisible et armée).
Run : python scripts/patch_bundle_quickend.py [--check]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_quick import run  # noqa: E402

TAG = "quickend"
MARKER = "function dzEndOK("

E1 = (
    'var dzEcS=x.useState(null),dzEndCaps=dzEcS[0],dzSetEndCaps=dzEcS[1];'
    'x.useEffect(function(){var on=!0;fetch("/api/video-models")'
    '.then(function(r2){return r2.ok?r2.json():null}).then(function(d2){if(!on)return;'
    'var mm={},ll=[];((d2&&d2.models)||[]).forEach(function(m2){mm[m2.id]=!!m2.end_image;'
    'if(m2.end_image)ll.push(m2.label)});'
    'dzSetEndCaps({map:mm,dflt:(d2&&d2.default)||"",oui:ll})})'
    '.catch(function(){});return function(){on=!1}},[]);'
    'function dzEndOK(){if(!dzEndCaps)return!0;'
    'var id=VMQ||dzEndCaps.dflt;return dzEndCaps.map[id]!==!1}'
    'function dzEndWhy(){return"« "+(VMQ||(dzEndCaps&&dzEndCaps.dflt)||"ce modèle")'
    '+" » n\'accepte pas d\'image de fin. Modèles qui l\'acceptent : "'
    '+((dzEndCaps&&dzEndCaps.oui)||[]).join(", ")}'
)

A_APPLYREF = "var dzApplyRef=x.useRef(null);"
A_FIELD = ('r.jsx(O,{label:"End image (optional)",children:u.length>0?r.jsx(re,{value:g,'
           'options:[{value:"",label:"— none —"},...u.map(B=>({value:B,label:B}))],'
           'onChange:k}):r.jsx(vd,{label:"drop or pick",kind:"image"})}),')
A_BTN = ('r.jsx(O,{label:"",children:r.jsx("button",{style:{width:"100%",fontSize:12,'
         'padding:"6px 12px",borderRadius:7,cursor:"pointer",background:"var(--bg-panel-2)",'
         'border:"1px solid var(--stroke)",color:"var(--ink)"},onClick:function(){'
         '__dzLibPicker({titre:"Image de fin (optionnelle)"},k)},'
         'children:"\U0001f4da Parcourir les vignettes…"},"dzlpe")})')
A_PAYLOAD = "image_filename_end:g||null,"
A_VMCHANGE = ('onChange:function(v2){dzSetVMQ(v2);try{localStorage.setItem('
              '"dz_video_model",v2)}catch(_e){}}')

PATCHES = [
    ("E1-caps", A_APPLYREF, E1 + A_APPLYREF),
    ("E2-champ", A_FIELD,
     'r.jsx(O,{label:dzEndOK()?"Image de fin (optionnelle)":"Image de fin — indisponible",'
     'children:dzEndOK()?(u.length>0?r.jsx(re,{value:g,'
     'options:[{value:"",label:"— aucune —"},...u.map(B=>({value:B,label:B}))],onChange:k})'
     ':r.jsx(vd,{label:"drop or pick",kind:"image"})):r.jsx("div",{style:{fontSize:11,'
     'padding:8,background:"var(--amber-soft)",border:"1px solid var(--amber)",'
     'borderRadius:"var(--r-sm)",color:"var(--ink)"},children:dzEndWhy()})}),'),
    ("E3-bouton", A_BTN, "dzEndOK()&&" + A_BTN),
    ("E4-payload", A_PAYLOAD, 'image_filename_end:(dzEndOK()?g:"")||null,'),
    ("E5-reset", A_VMCHANGE,
     'onChange:function(v2){dzSetVMQ(v2);try{localStorage.setItem("dz_video_model",v2)}'
     'catch(_e){}if(dzEndCaps&&dzEndCaps.map[v2]===!1)k("")}'),
]

if __name__ == "__main__":
    run(TAG, MARKER, 1, PATCHES,
        [("function dzEndWhy(", 1), ("__dzReopenQuick", 3),
         ("__dzExtendClip", 2)])
```

- [ ] **Step 4 : appliquer et vérifier**

Run : `python scripts/patch_bundle_quickend.py --check` puis `python scripts/patch_bundle_quickend.py`
Attendu : `[quickend] applicable sur … : 5 ancres OK, marqueur absent`, puis `OK - bundle patche (quickend) : 5 sections, +NNNN o`.
Puis la vérification bundle des Conventions ; inventaire : **+2 fonctions** (`dzEndOK`, `dzEndWhy`, déclarées dans `um` et donc comptées par `inventory_bundle.py`). Un autre chiffre = une fonction perdue : restaurer `.bak_quickend` et recommencer.

- [ ] **Step 5 : vert + sonde**

Run : `cd backend ; python tests/test_quick_bundle.py`
Attendu : quatre fonctions vertes, `BILAN OK`.
Sonde navigateur (backend relancé par l'utilisateur) : Quick → Modèle « Veo 3.1 Fast (fal) » : le champ affiche « Image de fin — indisponible » et la phrase nomme les six modèles ; repasser à « Kling v3 Pro » : le select revient, vide. Dans la console : `document.body.innerText.includes("n'accepte pas d'image de fin")` vaut `true` sur Veo et `false` sur Kling.

- [ ] **Step 6 : commit**

```bash
git add scripts/patch_bundle_quickend.py backend/tests/test_quick_bundle.py frontend/dist/assets/index-BEOJX8L5.js
git commit -F - <<'EOF'
quick : P3 - l'image de fin exposee, grisee AVEC la raison

Le select custom du bundle n'a pas de prop disabled : le champ devient un bloc
qui nomme le modele fautif et les six qui acceptent le first-last. Changer de
modele vide le champ, et le payload n'envoie jamais une fin refusee.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4 (P4) : sous-titres dans Quick, gravés sur le rendu

**Files :**
- Create : `backend/app/services/quick_finish.py`, `scripts/patch_bundle_quicksubs.py`, `backend/tests/test_quick_subs.py`
- Modify : `backend/app/models/schemas.py:175` (GenerateRequest, après `quick_recipe` de T1), `:245` (GenerateHeyGenRequest), `:321` (CompositionRequest)
- Modify : `backend/app/services/pipeline.py:412` (après `final_video_path=str(final_dest)` dans `run`), `:566` (après `progress=95` dans `run_heygen`), `:925` (dans `run_composition`, avant la création du job parent)
- Modify : `backend/tests/test_quick_bundle.py` (+1 fonction)
- Backend inchangé : `GET /api/subtitles/styles` (neuf préréglages, `routes.py:8178`) et `GET /api/subtitles/estimate` (`routes.py:8551`) existent déjà.

- [ ] **Step 1 : banc rouge — on lit l'IMAGE gravée, pas le code**

`backend/tests/test_quick_subs.py` :

```python
"""P4 — la gravure est mesurée sur le PIXEL : une image extraite du mp4 gravé
est plus claire, dans la bande basse, que la même image du mp4 d'origine.
Le .ass écrit est relu (PlayResY, texte). Aucun réseau : le chemin `align` est
local par construction. Run : python tests/test_quick_subs.py"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                                # noqa: E402
from app.services import quick_finish as QF                          # noqa: E402

TEXTE = ("Des profondeurs, le prophete parle. Le banc se reveille "
         "et la lumiere descend.")


def _exe(n):
    return shutil.which(n) or os.path.expandvars(
        r"%LOCALAPPDATA%\DeepotusVideoGen\bin" + f"\\{n}.exe")


def _clip(nom: str) -> pathlib.Path:
    p = _tmp / nom
    subprocess.run([_exe("ffmpeg"), "-y", "-v", "error",
                    "-f", "lavfi", "-i", "color=c=#02060d:s=540x960:r=24:d=6",
                    "-f", "lavfi", "-i", "sine=frequency=220:duration=6",
                    "-pix_fmt", "yuv420p", "-shortest", str(p)],
                   check=True, timeout=180)
    return p


def _bande_basse(video: pathlib.Path, t: float) -> float:
    """Luminance moyenne du quart bas de l'image a l'instant t."""
    png = _tmp / f"{video.stem}_{t}.png"
    subprocess.run([_exe("ffmpeg"), "-y", "-v", "error", "-ss", f"{t:.2f}",
                    "-i", str(video), "-frames:v", "1", str(png)],
                   check=True, timeout=120)
    im = Image.open(png).convert("L")
    w, h = im.size
    bas = im.crop((0, int(h * 0.72), w, h))
    px = list(bas.getdata())
    return sum(px) / float(len(px))


def test_les_sous_titres_sont_reellement_graves_sur_le_pixel():
    src = _clip("nu.mp4")
    grave = _tmp / "grave.mp4"
    shutil.copy2(src, grave)
    segs = QF.segments_for(grave, TEXTE, lang="fr", source="align", cps=42)
    assert len(segs) >= 2, segs
    assert segs[0]["start"] < segs[-1]["end"] <= 6.2, segs
    ass = QF.burn(grave, segs, style="pop", ratio="9:16")
    avant = _bande_basse(src, 1.0)
    apres = _bande_basse(grave, 1.0)
    assert apres > avant + 3.0, (avant, apres)      # du texte clair est apparu
    t = ass.read_text("utf-8")
    assert "PlayResY: 1920" in t, t[:400]
    assert "prophete" in t.lower(), t[:400]


def test_sans_texte_le_chemin_gratuit_refuse_en_le_disant():
    src = _clip("nu2.mp4")
    try:
        QF.segments_for(src, "   ", lang="fr", source="align")
    except ValueError as e:
        assert "aucun texte" in str(e).lower(), str(e)
        assert "transcription" in str(e).lower(), str(e)
    else:
        raise AssertionError("un calage sans texte a ete accepte")
```
puis le lanceur `__main__` des Conventions, recopié tel quel.

- [ ] **Step 2 : rouge**

Run : `cd backend ; python tests/test_quick_subs.py`
Attendu : `ModuleNotFoundError: No module named 'app.services.quick_finish'` à l'import.

- [ ] **Step 3 : le service**

`backend/app/services/quick_finish.py` :

```python
"""P4 — la finition d'un rendu Quick : graver les sous-titres SUR le mp4 final.

Deux chemins, un seul par défaut :
  * `align` (défaut, GRATUIT, hors ligne) — le texte est déjà connu (script de
    voix off, ou champ « texte des sous-titres ») : transcribe_service le cale
    sur les silences RÉELS du fichier. Mesure du 10/08 conservée dans
    transcribe_service : écart médian 0,070 s contre 0,235 s pour un partage
    uniforme, et le calage n'écrit pas « Dipotus » à la place de « Deepotus ».
  * `transcribe` (PAYANT, choisi explicitement) — aucun texte connu.

Le mp4 final n'est remplacé qu'APRÈS une gravure réussie (temporaire +
`replace`) : un ffmpeg qui échoue laisse le rendu payé intact. Et `apply` ne
laisse jamais remonter d'exception : un sous-titre raté ne coûte pas un rendu.
"""
import asyncio
import subprocess
from pathlib import Path

from loguru import logger

from app.services import subtitle_service as S
from app.services import transcribe_service as T
from app.services.effects_preview import ffmpeg_bin

CANVAS = {"9:16": (1080, 1920), "16:9": (1920, 1080),
          "1:1": (1080, 1080), "4:5": (1080, 1350)}


def segments_for(video, text: str, *, lang: str = "fr", source: str = "align",
                 provider: str = "", cps: int = 42) -> list:
    """Répliques datées pour ce mp4. `align` ne coûte rien ; `transcribe` paie."""
    video = Path(video)
    if source == "align":
        if not (text or "").strip():
            raise ValueError(
                "Sous-titres : aucun texte à caler. Écris le script (ou la voix "
                "off), ou choisis la transcription payante.")
        res = T.align_to_audio(text.strip(), video, lang=lang)
    else:
        res = T.transcribe(video, provider=provider or None, language=lang)
    cues = T.group_words(res["words"], max_chars=cps)
    return [{"id": f"q{i + 1}", "start": c["start"], "end": c["end"],
             "text": c["text"], "words": c.get("words") or []}
            for i, c in enumerate(cues)]


def burn(video, segments: list, *, style="standard", ratio: str = "9:16") -> Path:
    """Grave les répliques sur `video`, en place via un temporaire. Rend l'.ass."""
    video = Path(video)
    ass = video.with_suffix(".ass")
    ass.write_text(S.to_ass(segments, style, canvas=CANVAS.get(ratio, CANVAS["9:16"])),
                   encoding="utf-8")
    tmp = video.with_name(video.stem + ".subs.mp4")
    r = subprocess.run(
        [ffmpeg_bin(), "-y", "-v", "error", "-i", str(video),
         "-vf", S.subtitles_filter(ass), "-c:a", "copy", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "18", str(tmp)],
        capture_output=True, timeout=1800)
    if r.returncode != 0 or not tmp.is_file() or tmp.stat().st_size < 1024:
        if tmp.exists():
            tmp.unlink()
        raise RuntimeError("Gravure des sous-titres : "
                           + r.stderr.decode("utf-8", "replace")[-400:])
    tmp.replace(video)
    return ass


async def apply(video, opts, *, text: str, ratio: str) -> dict:
    """Crochet du pipeline. Ne lève JAMAIS : rend un compte rendu que le job
    peut journaliser. `opts` = le champ `subtitles` de la requête."""
    if not isinstance(opts, dict) or not opts.get("on"):
        return {"on": False}
    try:
        segs = await asyncio.to_thread(
            segments_for, video, text, lang=str(opts.get("lang") or "fr"),
            source=str(opts.get("source") or "align"),
            provider=str(opts.get("provider") or ""),
            cps=int(opts.get("cps") or 42))
        ass = await asyncio.to_thread(burn, video, segs,
                                      style=opts.get("style") or "standard",
                                      ratio=ratio)
        return {"on": True, "segments": len(segs), "ass": ass.name}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"quick_finish: sous-titres sautés ({e})")
        return {"on": True, "error": str(e)[:300]}
```

- [ ] **Step 4 : vert**

Run : `cd backend ; python tests/test_quick_subs.py`
Attendu : `PASS test_les_sous_titres_sont_reellement_graves_sur_le_pixel`, `PASS test_sans_texte_le_chemin_gratuit_refuse_en_le_disant`, `BILAN OK`.

- [ ] **Step 5 : schéma et crochets**

`schemas.py` — après le `quick_recipe: Optional[dict] = None` posé par T1 dans `GenerateRequest` (l.175), `GenerateHeyGenRequest` (l.245) et `CompositionRequest` (l.321) :

```python
    # P4 — sous-titres gravés sur le rendu :
    # {on: bool, style: "pop", lang: "fr", source: "align"|"transcribe",
    #  text: "…", provider: "elevenlabs", cps: 42}
    subtitles: Optional[dict] = None
```

`pipeline.py` — dans `run`, juste après `await self._update(session, job, final_video_path=str(final_dest))` (l.412) :

```python
                # P4 — sous-titres. APRÈS le rendu payé et le mix : le texte
                # de référence est la voix off réellement dite, sinon celle
                # que l'écran a fournie.
                _subs = getattr(request, "subtitles", None)
                if _subs:
                    from app.services import quick_finish
                    _txt = (( _subs.get("text") or "").strip()
                            or (vo_script or "").strip())
                    _rep = await quick_finish.apply(
                        final_dest, _subs, text=_txt,
                        ratio=request.aspect_ratio.value)
                    if _rep.get("error"):
                        await self._update(session, job,
                                           current_step=f"Sous-titres : {_rep['error'][:60]}")
```

`pipeline.py` — dans `run_heygen`, juste après le bloc `await self._update(session, job, video_path=…, final_video_path=str(final_path), progress=95)` (l.566) :

```python
                _subs = getattr(request, "subtitles", None)
                if _subs:
                    from app.services import quick_finish
                    _txt = ((_subs.get("text") or "").strip()
                            or (request.script or "").strip())
                    await quick_finish.apply(final_path, _subs, text=_txt,
                                             ratio=request.aspect_ratio.value)
```

`pipeline.py` — dans `run_composition`, juste après le `raise ValueError(f"Unknown composition layout: {request.layout}")` et AVANT le commentaire `# 4. Create a "composition" parent job` (l.925) :

```python
        # P4 — la composition porte SON champ `subtitles` (au niveau haut de
        # CompositionRequest) : sans ce crochet, l'écran l'enverrait et rien ne
        # le graverait. Le texte de référence est le script de l'avatar, qui
        # est ce que l'on entend.
        _subs = getattr(request, "subtitles", None)
        if _subs:
            from app.services import quick_finish
            _txt = ((_subs.get("text") or "").strip()
                    or (request.heygen.script or "").strip())
            await quick_finish.apply(out_path, _subs, text=_txt,
                                     ratio=request.seedance.aspect_ratio.value)
```

- [ ] **Step 6 : banc rouge du bundle, puis le patcher**

Ajouter dans `backend/tests/test_quick_bundle.py` :

```python
def test_quicksubs():
    s = _s()
    assert s.count("function dzSubs(") == 1
    assert s.count("subtitles:dzSubs(),") == 3       # /generate, /heygen, /composition
    assert s.count("dzSetSubOn") == 3                # déclaration + case + apply
    assert s.count("dzSubOn&&") == 4                 # style, langue, texte, aide
    assert 'label:"Sous-titrer le rendu"' in s
    assert "Voice (HeyGen comp)" not in s            # l'interrupteur mort est parti
    assert "subs:{on:dzSubOn" in s                   # la recette de T1 les porte
```

Run : `cd backend ; python tests/test_quick_bundle.py`
Attendu : `FAIL test_quicksubs -- …`, les autres `PASS`, `BILAN 1 rouge(s)`.

`scripts/patch_bundle_quicksubs.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_quicksubs.py
"""P4 — sous-titres dans Quick (T4).
BASELINE : bundle POST-patch quickend. Backup : .js.bak_quicksubs. EN QUEUE.

S1 état + dzSubs() + chargement des neuf préréglages (/subtitles/styles),
   greffé sur la chaîne posée par T3 (var dzEcS=…).
S2 le bloc « Sous-titres » REMPLACE l'interrupteur MORT « Voice (HeyGen comp) »
   (checked:!1, onChange:()=>{}) — un contrôle qui ne fait rien est pire qu'un
   contrôle absent, et la place est déjà dans la section Parameters.
S3-S5 les trois payloads portent `subtitles`.
S6 la recette de T1 porte l'état des sous-titres (sinon « Rouvrir dans Quick »
   perdrait le réglage, et P1 mentirait sur « prérempli »).
S7 dzQuickApply le restaure.
Run : python scripts/patch_bundle_quicksubs.py [--check]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_quick import run  # noqa: E402

TAG = "quicksubs"
MARKER = "function dzSubs("

S1 = (
    'var dzSoS=x.useState(!1),dzSubOn=dzSoS[0],dzSetSubOn=dzSoS[1],'
    'dzStS=x.useState("standard"),dzSubSty=dzStS[0],dzSetSubSty=dzStS[1],'
    'dzSlS=x.useState("fr"),dzSubLang=dzSlS[0],dzSetSubLang=dzSlS[1],'
    'dzStxS=x.useState(""),dzSubTxt=dzStxS[0],dzSetSubTxt=dzStxS[1],'
    'dzSpS=x.useState([]),dzSubPre=dzSpS[0],dzSetSubPre=dzSpS[1];'
    'x.useEffect(function(){var on=!0;fetch("/api/subtitles/styles?ratio=9:16")'
    '.then(function(r2){return r2.ok?r2.json():null}).then(function(d2){if(on&&d2)'
    'dzSetSubPre((d2.presets||[]).map(function(p2){return{value:p2.id,label:p2.label||p2.id}}))})'
    '.catch(function(){});return function(){on=!1}},[]);'
    'function dzSubs(){if(!dzSubOn)return void 0;'
    'var t2=(dzSubTxt||"").trim()||(o==="seedance"?"":R||"");'
    'return{on:!0,style:dzSubSty,lang:dzSubLang,cps:42,'
    'source:t2?"align":"transcribe",text:t2}}'
)

S2_A = ('r.jsx(O,{children:r.jsx(Ze,{checked:!1,label:"Voice (HeyGen comp)",'
        'onChange:()=>{}})})')
S2_B = (
    'r.jsx(O,{children:r.jsx(Ze,{checked:dzSubOn,label:"Sous-titrer le rendu",'
    'onChange:dzSetSubOn})}),'
    'dzSubOn&&r.jsx(O,{label:"Style de sous-titres",children:r.jsx(re,{value:dzSubSty,'
    'options:dzSubPre.length?dzSubPre:[{value:"standard",label:"Standard"}],'
    'onChange:dzSetSubSty})}),'
    'dzSubOn&&r.jsx(O,{label:"Langue",children:r.jsx(re,{value:dzSubLang,'
    'options:[{value:"fr",label:"Français"},{value:"en",label:"English"}],'
    'onChange:dzSetSubLang})}),'
    'dzSubOn&&r.jsx(O,{label:"Texte à caler (vide = le Script, sinon transcription payante)",'
    'children:r.jsx("textarea",{value:dzSubTxt,onChange:function(e2){dzSetSubTxt(e2.target.value)},'
    'rows:3,style:{width:"100%",padding:8,background:"var(--bg-base)",'
    'border:"1px solid var(--stroke)",borderRadius:8,color:"var(--ink-strong)",'
    'fontFamily:"var(--f-ui)",fontSize:12,resize:"vertical"}})}),'
    'dzSubOn&&r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)",marginTop:-4},'
    'children:((dzSubTxt||"").trim()||(o!=="seedance"&&R))'
    '?"Calage local du texte connu — 0 $, hors ligne, exact sur les noms propres."'
    ':"Sans texte, il faudra TRANSCRIRE : appel payant, et une clé ElevenLabs ou OpenAI."})'
)

PATCHES = [
    ("S1-etat", "var dzEcS=x.useState(null),", S1 + "var dzEcS=x.useState(null),"),
    ("S2-ui", S2_A, S2_B),
    ("S3-seedance", "je={quick_recipe:dzQuickRecipe(),",
     "je={quick_recipe:dzQuickRecipe(),subtitles:dzSubs(),"),
    ("S4-heygen", 'D.postJson("/generate/heygen",{quick_recipe:dzQuickRecipe(),',
     'D.postJson("/generate/heygen",{quick_recipe:dzQuickRecipe(),subtitles:dzSubs(),'),
    ("S5-comp", 'D.postJson("/generate/composition",{quick_recipe:dzQuickRecipe(),',
     'D.postJson("/generate/composition",{quick_recipe:dzQuickRecipe(),subtitles:dzSubs(),'),
    ("S6-recette", "layout:We}}",
     "layout:We,subs:{on:dzSubOn,style:dzSubSty,lang:dzSubLang,text:dzSubTxt}}}"),
    ("S7-apply", "if(rc.layout)De(rc.layout)}",
     'if(rc.layout)De(rc.layout);var sb=rc.subs||{};if(sb.on!=null)dzSetSubOn(!!sb.on);'
     'if(sb.style)dzSetSubSty(sb.style);if(sb.lang)dzSetSubLang(sb.lang);'
     'if(sb.text!=null)dzSetSubTxt(sb.text)}'),
]

if __name__ == "__main__":
    run(TAG, MARKER, 1, PATCHES,
        [("__dzReopenQuick", 3), ("function dzEndOK(", 1),
         ("subtitles:dzSubs(),", 3), ("Voice (HeyGen comp)", 0)])
```

Run : `python scripts/patch_bundle_quicksubs.py --check` puis `python scripts/patch_bundle_quicksubs.py`
Attendu : `[quicksubs] applicable sur … : 7 ancres OK, marqueur absent`, puis `OK - bundle patche (quicksubs) : 7 sections, +NNNN o`. Puis la vérification bundle des Conventions ; inventaire : +1 fonction (`dzSubs`).

- [ ] **Step 7 : vert + sonde**

Run : `cd backend ; python tests/test_quick_bundle.py`
Attendu : cinq fonctions vertes, `BILAN OK`.
Sonde navigateur (backend relancé par l'utilisateur) : Quick → Parameters → « Sous-titrer le rendu » : le style, la langue et le champ texte apparaissent ; la ligne d'aide bascule de « Calage local… 0 $ » à « il faudra TRANSCRIRE… » quand on vide le champ sur l'onglet Seedance. Dans la console : `JSON.stringify(window.__dzQuickRecipe||{})` après « Rouvrir dans Quick » contient `"subs"`.

- [ ] **Step 8 : commit**

```bash
git add backend/app/services/quick_finish.py backend/app/models/schemas.py backend/app/services/pipeline.py backend/tests/test_quick_subs.py backend/tests/test_quick_bundle.py scripts/patch_bundle_quicksubs.py frontend/dist/assets/index-BEOJX8L5.js
git commit -F - <<'EOF'
quick : P4 - sous-titres graves sur le rendu, calage local par defaut

Le chemin gratuit (texte connu cale sur les silences reels) est le defaut ; la
transcription payante se choisit et se dit. Le mp4 n'est remplace qu'apres une
gravure reussie, et une gravure ratee ne fait pas perdre le rendu paye.
L'interrupteur mort « Voice (HeyGen comp) » laisse la place au vrai controle.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 5 (P5) : lip-sync dans Quick

**Files :**
- Create : `scripts/patch_bundle_quicklipsync.py`, `backend/tests/test_quick_lipsync.py`
- Modify : `backend/app/services/fal_video_tools.py` (fin de fichier), `backend/app/models/schemas.py:176` (GenerateRequest), `backend/app/services/pipeline.py:361` (après `download_video`, AVANT l'allongement), `backend/app/services/pricing.py:68` et `:274`
- Modify : `backend/tests/test_quick_bundle.py` (+1 fonction)

- [ ] **Step 1 : MESURE — le contrat Kling LipSync**

R1 a vérifié le 03/09 : Kling LipSync audio-to-video, **vidéo 2–10 s, audio 2–60 s, 0,014 $/s**. L'identifiant d'endpoint et les noms de champs ne sont PAS vérifiés :

```
curl -s "https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/kling-video/lipsync/audio-to-video" > %TEMP%\kling_lip.json
python -c "import json;d=json.load(open(r'%TEMP%\kling_lip.json',encoding='utf-8'));s=d.get('components',{}).get('schemas',{});print(list(s));print(json.dumps(s,ensure_ascii=False)[:2500])"
```

| Ce que la mesure rend | Ce qu'on écrit dans `LIPSYNC_MODELS` |
|---|---|
| un schéma avec `video_url` + `audio_url` | ces deux noms, `endpoint="fal-ai/kling-video/lipsync/audio-to-video"` |
| un schéma aux noms différents | ces noms-là, date de mesure en commentaire |
| 404 | essayer `fal-ai/kling-video/v1/standard/lipsync/audio-to-video` ; sinon **replier sur `fal-ai/sync-lipsync/v2`** (relevé en R1) en écrivant son tarif à lui, pas 0,014 $/s |
| aucun schéma | **T5 s'arrête là** : `LIPSYNC_MODELS = {}`, la case du bundle n'est pas posée, et le plan le dit dans le commit |

- [ ] **Step 2 : banc rouge — les deux bornes, citées**

`backend/tests/test_quick_lipsync.py` :

```python
"""P5 — les bornes du lip-sync (vidéo 2–10 s, audio 2–60 s) sont mesurées sur
de vrais fichiers et CITÉES dans le refus. Aucun réseau.
Run : python tests/test_quick_lipsync.py"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import fal_video_tools as FV                       # noqa: E402


def _exe(n):
    return shutil.which(n) or os.path.expandvars(
        r"%LOCALAPPDATA%\DeepotusVideoGen\bin" + f"\\{n}.exe")


def _v(nom, secs):
    p = _tmp / nom
    subprocess.run([_exe("ffmpeg"), "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"testsrc=size=540x960:rate=24:duration={secs}",
                    "-pix_fmt", "yuv420p", str(p)], check=True, timeout=180)
    return p


def _a(nom, secs):
    p = _tmp / nom
    subprocess.run([_exe("ffmpeg"), "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"sine=frequency=220:duration={secs}", str(p)],
                   check=True, timeout=180)
    return p


def test_video_trop_longue_refusee_en_citant_les_deux_bornes():
    v, a = FV.probe(_v("v12.mp4", 12)), FV.probe(_a("a10.mp3", 10))
    try:
        FV.guard_lipsync("kling-lipsync", v, a)
    except ValueError as e:
        m = str(e)
        assert "12.0 s" in m and "2" in m and "10 s" in m, m
    else:
        raise AssertionError("une video de 12 s a ete acceptee")


def test_audio_trop_court_refuse_et_paire_valide_acceptee():
    v = FV.probe(_v("v6.mp4", 6))
    try:
        FV.guard_lipsync("kling-lipsync", v, FV.probe(_a("a1.mp3", 1)))
    except ValueError as e:
        assert "1.0 s" in str(e) and "2" in str(e), str(e)
    else:
        raise AssertionError("un audio de 1 s a ete accepte")
    FV.guard_lipsync("kling-lipsync", v, FV.probe(_a("a5.mp3", 5)))   # ne leve pas
    ep, args = FV.build_lipsync_args("kling-lipsync",
                                     video_url="https://x/v.mp4",
                                     audio_url="https://x/a.mp3")
    m = FV.LIPSYNC_MODELS["kling-lipsync"]
    assert ep == m["endpoint"] and args[m["video_param"]] == "https://x/v.mp4"
    assert args[m["audio_param"]] == "https://x/a.mp3", args
```
puis le lanceur `__main__` des Conventions.

Run : `cd backend ; python tests/test_quick_lipsync.py`
Attendu : `FAIL … AttributeError: module 'app.services.fal_video_tools' has no attribute 'guard_lipsync'` ×2, `BILAN 2 rouge(s)`.

- [ ] **Step 3 : le registre et les gardes**

`fal_video_tools.py` — en fin de fichier :

```python
# ── P5 — lip-sync ────────────────────────────────────────────────────────
# Bornes vérifiées le 03/09/2026 (R1) : vidéo 2–10 s, audio 2–60 s,
# 0,014 $/s. Endpoint et noms de champs relevés à l'étape 1 de T5.
LIPSYNC_MODELS: dict = {
    "kling-lipsync": {
        "label": "Kling LipSync",
        "endpoint": "fal-ai/kling-video/lipsync/audio-to-video",  # ← étape 1
        "video_param": "video_url",                                # ← étape 1
        "audio_param": "audio_url",                                # ← étape 1
        "video_s": (2.0, 10.0),
        "audio_s": (2.0, 60.0),
        "usd_per_s": 0.014,
    },
}


def guard_lipsync(model_id: str, video: dict, audio: dict) -> None:
    """Lève ValueError AVANT tout appel payant, en citant les DEUX mesures."""
    m = LIPSYNC_MODELS.get(model_id)
    if m is None:
        raise ValueError(
            f"Modèle de lip-sync inconnu : {model_id}. Disponibles : "
            + (", ".join(sorted(LIPSYNC_MODELS)) or "aucun (endpoint non mesuré)"))
    for quoi, src, (lo, hi) in (("clip", video, m["video_s"]),
                                ("audio", audio, m["audio_s"])):
        d = float(src.get("duration_s") or 0)
        if not (lo <= d <= hi):
            raise ValueError(
                f"{m['label']} : le {quoi} doit durer entre {lo:.0f} et "
                f"{hi:.0f} s ; celui-ci fait {d:.1f} s. Règle la durée du clip "
                f"dans Quick, ou coupe la voix off au Montage.")


def build_lipsync_args(model_id: str, *, video_url: str, audio_url: str) -> tuple:
    m = LIPSYNC_MODELS[model_id]
    return m["endpoint"], {m["video_param"]: video_url,
                           m["audio_param"]: audio_url}
```

Run : `cd backend ; python tests/test_quick_lipsync.py`
Attendu : `PASS test_audio_trop_court_refuse_et_paire_valide_acceptee`, `PASS test_video_trop_longue_refusee_en_citant_les_deux_bornes`, `BILAN OK`.

- [ ] **Step 4 : schéma, crochet pipeline, tarif**

`schemas.py` — dans `GenerateRequest`, après `subtitles` de T4 (l.176) :

```python
    # P5 — lip-sync fal sur le clip NATIF (avant tout allongement ffmpeg) :
    # {on: bool, model: "kling-lipsync", file: <nom dans le dossier audio>}
    lipsync: Optional[dict] = None
```

`pipeline.py` — dans `run`, juste après `await video_client.download_video(video_url, video_dest)` (l.361) et AVANT le bloc `if request.duration_s > gen_dur:` :

```python
                # P5 — lip-sync AVANT l'allongement ffmpeg : la borne haute du
                # modèle (10 s) porte sur le clip NATIF ; l'appliquer après une
                # boucle de 60 s le ferait refuser à coup sûr.
                _lip = getattr(request, "lipsync", None)
                if _lip and _lip.get("on"):
                    import fal_client
                    from app.services import fal_video_tools as FV
                    _ap = _resolve_voiceover({"file": _lip.get("file")})
                    if _ap is None:
                        raise ValueError(
                            "Lip-sync : aucune voix off jointe. Génère-la dans "
                            "l'onglet Voice Over, puis choisis-la ici.")
                    _mid = _lip.get("model") or "kling-lipsync"
                    _vs = await asyncio.to_thread(FV.probe, video_dest)
                    _as = await asyncio.to_thread(FV.probe, _ap)
                    FV.guard_lipsync(_mid, _vs, _as)
                    await self._update(session, job,
                                       current_step="Lip-sync", progress=72)
                    _vu = await fal_client.upload_file_async(str(video_dest))
                    _au = await fal_client.upload_file_async(str(_ap))
                    _ep, _args = FV.build_lipsync_args(_mid, video_url=_vu,
                                                       audio_url=_au)
                    _res = await fal_client.subscribe_async(_ep, arguments=_args,
                                                            with_logs=True)
                    _ru = FalSeedanceClient.extract_video_url(_res)
                    if not _ru:
                        raise RuntimeError("fal.ai : lip-sync sans URL vidéo")
                    _lp = settings.outputs_path / "videos" / f"{job_id}_lip.mp4"
                    await FalSeedanceClient.download_video(_ru, _lp)
                    video_dest = _lp
```

`pricing.py` — dans `DEFAULTS`, après `"extend_usd_per_s"` de T2 :

```python
    # P5 — lip-sync ($/s d'audio). Miroir de
    # fal_video_tools.LIPSYNC_MODELS[...]["usd_per_s"].
    "lipsync_usd_per_s": {"kling-lipsync": 0.014},
```
et dans `estimate`, juste après la branche `extend` de T2 :

```python
    elif kind == "lipsync":
        model = str(op.get("model") or "kling-lipsync")
        secs = float(op.get("duration_s", 0))
        rates = p.get("lipsync_usd_per_s") or DEFAULTS["lipsync_usd_per_s"]
        rate = float(rates.get(model, 0.014))
        lines.append(_line("fal", f"Lip-sync ({model})", secs, "s", secs * rate))
```

- [ ] **Step 5 : banc rouge du bundle, puis le patcher**

Ajouter dans `backend/tests/test_quick_bundle.py` :

```python
def test_quicklipsync():
    s = _s()
    assert s.count("function dzLip(") == 1
    assert s.count("lipsync:dzLip(),") == 1          # seedance seul (P5)
    assert s.count("dzLipOn") == 6                   # état, garde, case, ×2 blocs, recette
    assert 'label:"Lip-sync sur la voix off"' in s
    assert "2 a 10 s" in s or "2 à 10 s" in s        # la borne est ecrite a l'ecran
```

`scripts/patch_bundle_quicklipsync.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_quicklipsync.py
"""P5 — lip-sync dans Quick (T5).
BASELINE : bundle POST-patch quicksubs. Backup : .js.bak_quicklipsync. EN QUEUE.

L1 état + dzLip() + liste des fichiers audio (D.listAudio existe déjà), greffé
   sur la chaîne posée par T4 (var dzSoS=…).
L2 le bloc « Lip-sync » sous le bloc sous-titres de T4 : case + choix du
   fichier de voix off + la borne 2–10 s ÉCRITE (le refus backend arrive trop
   tard pour être une information utile).
L3 le payload seedance porte `lipsync`.
L4 la recette de T1/T4 porte l'état du lip-sync.
L5 dzQuickApply le restaure.
Run : python scripts/patch_bundle_quicklipsync.py [--check]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_quick import run  # noqa: E402

TAG = "quicklipsync"
MARKER = "function dzLip("

L1 = (
    'var dzLoS=x.useState(!1),dzLipOn=dzLoS[0],dzSetLipOn=dzLoS[1],'
    'dzLfS=x.useState(""),dzLipFile=dzLfS[0],dzSetLipFile=dzLfS[1],'
    'dzLlS=x.useState([]),dzLipList=dzLlS[0],dzSetLipList=dzLlS[1];'
    'x.useEffect(function(){var on=!0;D.listAudio().then(function(d2){if(on)'
    'dzSetLipList(((d2&&d2.audio)||[]).map(function(z){return z.filename||z}))})'
    '.catch(function(){});return function(){on=!1}},[]);'
    'function dzLip(){if(!dzLipOn||!dzLipFile)return void 0;'
    'return{on:!0,model:"kling-lipsync",file:dzLipFile}}'
)

L2_A = ('r.jsx(O,{children:r.jsx(Ze,{checked:dzSubOn,label:"Sous-titrer le rendu",'
        'onChange:dzSetSubOn})}),')
L2_B = L2_A + (
    'o==="seedance"&&r.jsx(O,{children:r.jsx(Ze,{checked:dzLipOn,'
    'label:"Lip-sync sur la voix off",onChange:dzSetLipOn})}),'
    'o==="seedance"&&dzLipOn&&r.jsx(O,{label:"Voix off à synchroniser",'
    'children:r.jsx(re,{value:dzLipFile,options:[{value:"",label:"— choisir un fichier audio —"}]'
    '.concat(dzLipList.map(function(z){return{value:z,label:z}})),onChange:dzSetLipFile})}),'
    'o==="seedance"&&dzLipOn&&r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)",'
    'marginTop:-4},children:"Kling LipSync : le clip NATIF doit durer 2 à 10 s et la voix 2 à 60 s. '
    'Facturé 0,014 $ la seconde d\'audio, en plus du clip."}),'
)

PATCHES = [
    ("L1-etat", "var dzSoS=x.useState(!1),", L1 + "var dzSoS=x.useState(!1),"),
    ("L2-ui", L2_A, L2_B),
    ("L3-payload", "je={quick_recipe:dzQuickRecipe(),subtitles:dzSubs(),",
     "je={quick_recipe:dzQuickRecipe(),subtitles:dzSubs(),lipsync:dzLip(),"),
    ("L4-recette", "subs:{on:dzSubOn,style:dzSubSty,lang:dzSubLang,text:dzSubTxt}}}",
     "subs:{on:dzSubOn,style:dzSubSty,lang:dzSubLang,text:dzSubTxt},"
     "lip:{on:dzLipOn,file:dzLipFile}}}"),
    ("L5-apply", "if(sb.text!=null)dzSetSubTxt(sb.text)}",
     'if(sb.text!=null)dzSetSubTxt(sb.text);var lp=rc.lip||{};'
     'if(lp.on!=null)dzSetLipOn(!!lp.on);if(lp.file!=null)dzSetLipFile(lp.file)}'),
]

if __name__ == "__main__":
    run(TAG, MARKER, 1, PATCHES,
        [("subtitles:dzSubs(),", 3), ("function dzEndOK(", 1),
         ("__dzReopenQuick", 3)])
```

Run : `python scripts/patch_bundle_quicklipsync.py --check` puis sans `--check`
Attendu : `[quicklipsync] applicable sur … : 5 ancres OK`, puis `OK - bundle patche (quicklipsync) : 5 sections, +NNNN o` ; `node --check` muet ; inventaire : +1 fonction (`dzLip`).

- [ ] **Step 6 : vert + sonde**

Run : `cd backend ; python tests/test_quick_bundle.py` puis `cd backend ; python tests/test_quick_lipsync.py`
Attendu : `BILAN OK` deux fois.
Sonde navigateur : Quick → onglet Seedance → « Lip-sync sur la voix off » : la liste des fichiers audio se remplit ; passer à l'onglet HeyGen fait disparaître le bloc (P5 ne concerne que le clip Seedance — HeyGen synchronise déjà ses lèvres). Régler la durée à 30 s puis générer : le job passe rouge avec « le clip doit durer entre 2 et 10 s ; celui-ci fait … » — la borne est bien celle du NATIF.

- [ ] **Step 7 : commit**

```bash
git add backend/app/services/fal_video_tools.py backend/app/models/schemas.py backend/app/services/pipeline.py backend/app/services/pricing.py backend/tests/test_quick_lipsync.py backend/tests/test_quick_bundle.py scripts/patch_bundle_quicklipsync.py frontend/dist/assets/index-BEOJX8L5.js
git commit -F - <<'EOF'
quick : P5 - lip-sync Kling sur la voix off, avant l'allongement ffmpeg

La borne haute (10 s) porte sur le clip NATIF : appliquer le lip-sync apres une
boucle de 60 s le ferait refuser a coup sur. Les deux mesures sont citees dans
le refus, la borne est ecrite a l'ecran, et le tarif 0,014 $/s entre au pricing.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 6 (P6) : presets personnels sur les quatre onglets

**Files :**
- Create : `scripts/patch_bundle_quickpresets.py`, `backend/tests/test_quick_presets.py`
- Modify : `backend/app/services/storage.py:145` (après `AvatarPreset`), `backend/app/models/schemas.py:327` (après `ExtendRequest` de T2), `backend/app/api/routes.py:3023` (après `delete_avatar_preset`)
- Modify : `backend/tests/test_quick_bundle.py` (+1 fonction)

Un preset **est** la recette de T1, nommée. Un seul mécanisme : ce qui se sauvegarde est exactement ce que « Rouvrir dans Quick » sait rejouer, donc un preset ne peut pas diverger de ce que l'écran applique. `avatar_presets` (castings HeyGen) reste intacte : elle ne porte qu'avatar + voix, et l'onglet HeyGen s'en sert toujours.

- [ ] **Step 1 : banc rouge**

`backend/tests/test_quick_presets.py` :

```python
"""P6 — les presets Quick : écrits, relus par onglet, supprimés. Le banc lit la
réponse HTTP et la LIGNE SQLite, pas le code des routes.
Run : python tests/test_quick_presets.py"""
import asyncio
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import ASGITransport, AsyncClient                          # noqa: E402
from app.main import app                                              # noqa: E402
from app.services.storage import init_db, async_session_factory       # noqa: E402

REC = {"v": 1, "tab": "seedance",
       "seedance": {"image": "a.png", "end": "", "prompt": "abysse",
                    "vibe": "deep-sea", "model": "kling-v3-pro", "duration": 10,
                    "aspect": "9:16", "seed": "4421", "template": ""},
       "heygen": {"src": "avatar", "avatar": "", "voice": "", "script": "",
                  "engine": "", "image": "", "motion": "", "expr": ""},
       "layout": "sequential"}


def test_ecrit_relu_par_onglet_puis_supprime():
    async def go():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            r = await c.post("/api/quick/presets",
                             json={"name": "Abysse 10s", "tab": "seedance",
                                   "recipe": REC})
            assert r.status_code == 200, r.text
            pid = r.json()["id"]
            r2 = await c.post("/api/quick/presets",
                              json={"name": "Avatar news", "tab": "heygen",
                                    "recipe": dict(REC, tab="heygen")})
            assert r2.status_code == 200, r2.text
            tous = (await c.get("/api/quick/presets")).json()["presets"]
            assert len(tous) == 2, tous
            sd = (await c.get("/api/quick/presets?tab=seedance")).json()["presets"]
            assert [p["name"] for p in sd] == ["Abysse 10s"], sd
            assert sd[0]["recipe"]["seedance"]["model"] == "kling-v3-pro", sd
            from sqlalchemy import text as _t
            async with async_session_factory() as s:
                n = (await s.execute(_t("SELECT COUNT(*) FROM quick_presets"))).scalar()
            assert n == 2, n
            assert (await c.delete(f"/api/quick/presets/{pid}")).status_code == 200
            assert len((await c.get("/api/quick/presets")).json()["presets"]) == 1
            assert (await c.delete(f"/api/quick/presets/{pid}")).status_code == 404
    asyncio.run(go())


def test_recette_illisible_refusee():
    async def go():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            r = await c.post("/api/quick/presets",
                             json={"name": "vide", "tab": "seedance", "recipe": {}})
            assert r.status_code == 422, r.text
            r2 = await c.post("/api/quick/presets",
                              json={"name": "onglet inconnu", "tab": "zzz",
                                    "recipe": REC})
            assert r2.status_code == 422, r2.text
    asyncio.run(go())
```
puis le lanceur `__main__` des Conventions.

Run : `cd backend ; python tests/test_quick_presets.py`
Attendu : `FAIL test_ecrit_relu_par_onglet_puis_supprime -- …` (404 sur `/api/quick/presets`) et `FAIL test_recette_illisible_refusee`, `BILAN 2 rouge(s)`.

- [ ] **Step 2 : table, schéma, routes**

`storage.py` — après la classe `AvatarPreset` (l.145) :

```python
class QuickPreset(Base):
    """P6 — un preset Quick = la RECETTE de T1 (quick_recipe), nommée et
    rangée par onglet. Stockée en JSON : la recette grossit à chaque tâche du
    plan (sous-titres, lip-sync, caméra) et une colonne par champ imposerait
    une migration à chaque fois."""
    __tablename__ = "quick_presets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    tab: Mapped[str] = mapped_column(String(16), default="seedance", index=True)
    recipe: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```
Aucune entrée dans les listes d'auto-ALTER : celles-ci ne servent qu'aux tables DÉJÀ créées ; une table neuve est créée par `create_all` d'`init_db`.

`schemas.py` — après `ExtendRequest` (l.327) :

```python
class QuickPresetCreate(BaseModel):
    """P6 — enregistrer l'état complet d'un onglet Quick sous un nom."""
    name: str = Field(..., min_length=1, max_length=120)
    tab: Literal["seedance", "heygen", "comp", "voice"] = "seedance"
    recipe: dict = Field(..., min_length=1)
```

`routes.py` — après `delete_avatar_preset` (l.3023) ; ajouter `QuickPresetCreate` à l'import de `app.models.schemas` :

```python
@router.get("/quick/presets")
async def list_quick_presets(tab: str = ""):
    """P6 — presets Quick, les plus récents d'abord. `tab` filtre l'onglet."""
    import json as _json
    from app.services.storage import QuickPreset, async_session_factory
    from sqlalchemy import select
    async with async_session_factory() as session:
        q = select(QuickPreset).order_by(QuickPreset.created_at.desc())
        if tab:
            q = q.where(QuickPreset.tab == tab)
        rows = (await session.execute(q)).scalars().all()
    out = []
    for p in rows:
        try:
            rec = _json.loads(p.recipe)
        except ValueError:
            rec = {}
        out.append({"id": p.id, "name": p.name, "tab": p.tab, "recipe": rec,
                    "created_at": p.created_at.isoformat() if p.created_at else None})
    return {"presets": out}


@router.post("/quick/presets")
async def create_quick_preset(body: QuickPresetCreate):
    """P6 — enregistrer la recette courante sous un nom."""
    import json as _json
    from app.services.storage import QuickPreset, async_session_factory
    from uuid import uuid4
    pid = str(uuid4())
    async with async_session_factory() as session:
        session.add(QuickPreset(
            id=pid, name=body.name.strip(), tab=body.tab,
            recipe=_json.dumps(body.recipe, ensure_ascii=False)))
        await session.commit()
    return {"id": pid, "name": body.name.strip(), "tab": body.tab,
            "recipe": body.recipe}


@router.delete("/quick/presets/{preset_id}")
async def delete_quick_preset(preset_id: str):
    """P6 — supprimer un preset Quick."""
    from app.services.storage import QuickPreset, async_session_factory
    async with async_session_factory() as session:
        row = await session.get(QuickPreset, preset_id)
        if not row:
            raise HTTPException(404, "Preset not found")
        await session.delete(row)
        await session.commit()
    return {"ok": True}
```

Run : `cd backend ; python tests/test_quick_presets.py`
Attendu : `PASS test_ecrit_relu_par_onglet_puis_supprime`, `PASS test_recette_illisible_refusee`, `BILAN OK`.

- [ ] **Step 3 : banc rouge du bundle, puis le patcher**

Ajouter dans `backend/tests/test_quick_bundle.py` :

```python
def test_quickpresets():
    s = _s()
    assert s.count("dzQpUI") == 3            # définition + les deux branches du scroll
    assert s.count("/api/quick/presets") == 3  # charger, enregistrer, supprimer
    assert 'label:"Preset de cet onglet"' in s
    assert "dzQuickApply(p2.recipe)" in s    # un preset REJOUE la recette de T1
```

Run : `cd backend ; python tests/test_quick_bundle.py`
Attendu : `FAIL test_quickpresets -- …`, `BILAN 1 rouge(s)`.

`scripts/patch_bundle_quickpresets.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_quickpresets.py
"""P6 — presets personnels sur les quatre onglets (T6).
BASELINE : bundle POST-patch quicklipsync. Backup : .js.bak_quickpresets. EN QUEUE.

P1 état + chargement + dzQpUI() : charger rejoue dzQuickApply (T1), enregistrer
   envoie dzQuickRecipe() (T1). Un seul mécanisme : un preset ne peut pas
   porter un réglage que « Rouvrir dans Quick » ne saurait pas appliquer.
P2 la section est insérée en TÊTE des DEUX branches du conteneur scroll (voice
   comprise) — c'est ce que « sur les quatre onglets » veut dire.
Deux ancres seulement : le tableau « Coût de patch » disait 3, la mesure du
03/09 en donne 2 (les deux branches se remplacent d'un seul coup).
Run : python scripts/patch_bundle_quickpresets.py [--check]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_quick import run  # noqa: E402

TAG = "quickpresets"
MARKER = "function dzQpUI("

P1 = (
    'var dzQpS=x.useState([]),dzQpL=dzQpS[0],dzSetQpL=dzQpS[1],'
    'dzQnS=x.useState(""),dzQpN=dzQnS[0],dzSetQpN=dzQnS[1];'
    'function dzQpLoad(){fetch("/api/quick/presets?tab="+encodeURIComponent(o))'
    '.then(function(r2){return r2.ok?r2.json():{presets:[]}})'
    '.then(function(d2){dzSetQpL((d2&&d2.presets)||[])}).catch(function(){})}'
    'x.useEffect(dzQpLoad,[o]);'
    'function dzQpUI(){return r.jsxs(ie,{label:"Presets Quick ("+dzQpL.length+")",children:['
    'r.jsx(O,{label:"Preset de cet onglet",children:r.jsx(re,{value:"",'
    'options:[{value:"",label:dzQpL.length?"— charger un preset —":"— aucun preset pour cet onglet —"}]'
    '.concat(dzQpL.map(function(p2){return{value:p2.id,label:p2.name}})),'
    'onChange:function(v2){var p2=dzQpL.find(function(z){return z.id===v2});'
    'if(p2){dzQuickApply(p2.recipe);__dzToast("Preset « "+p2.name+" » chargé")}}})}),'
    'r.jsx(O,{label:"Enregistrer l\'état courant",children:r.jsxs("div",'
    '{style:{display:"flex",gap:6,alignItems:"center"},children:['
    'r.jsx("div",{style:{flex:1,minWidth:0},children:r.jsx(le,{value:dzQpN,onChange:dzSetQpN,'
    'placeholder:"Nom du preset (ex. Abysse 10s)"})}),'
    'r.jsx(K,{variant:"outline",size:"sm",icon:"save",disabled:!dzQpN.trim(),'
    'onClick:function(){fetch("/api/quick/presets",{method:"POST",'
    'headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify({name:dzQpN.trim(),tab:o,recipe:dzQuickRecipe()})})'
    '.then(function(r2){if(r2.ok){dzSetQpN("");dzQpLoad();__dzToast("Preset enregistré")}'
    'else __dzToast("Preset : "+r2.status)})},children:"Enregistrer"}),'
    'r.jsx(K,{variant:"ghost",size:"sm",icon:"trash",title:"Supprimer le plus récent",'
    'disabled:!dzQpL.length,onClick:function(){var p2=dzQpL[0];if(!p2)return;'
    'fetch("/api/quick/presets/"+p2.id,{method:"DELETE"}).then(dzQpLoad)}})]})})]},"dzqp")}'
)

A_STATE = "var dzLoS=x.useState(!1),"
A_SCROLL = 'children:o==="voice"?[r.jsx(DzQuickVoice,{},"dzqv")]:['

PATCHES = [
    ("P1-etat-et-ui", A_STATE, P1 + A_STATE),
    ("P2-scroll", A_SCROLL,
     'children:o==="voice"?[dzQpUI(),r.jsx(DzQuickVoice,{},"dzqv")]:[dzQpUI(),'),
]

if __name__ == "__main__":
    run(TAG, MARKER, 1, PATCHES,
        [("dzQuickApply", 3), ("dzQuickRecipe", 5), ("dzQpUI", 3),
         ("__dzReopenQuick", 3)])
```

Run : `python scripts/patch_bundle_quickpresets.py --check` puis sans `--check`
Attendu : `[quickpresets] applicable sur … : 2 ancres OK`, puis `OK - bundle patche (quickpresets) : 2 sections, +NNNN o` ; `node --check` muet ; inventaire : +2 fonctions (`dzQpLoad`, `dzQpUI`).

- [ ] **Step 4 : vert + sonde**

Run : `cd backend ; python tests/test_quick_bundle.py` puis `cd backend ; python tests/test_quick_presets.py`
Attendu : `BILAN OK` deux fois.
Sonde navigateur : Quick → régler modèle/durée/prompt → nommer « Abysse 10s » → Enregistrer ; changer tout ; recharger le preset : les champs reviennent. Passer à l'onglet HeyGen : la liste devient vide (« aucun preset pour cet onglet »). Onglet Voice Over : la section est présente au-dessus du panneau de voix.

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/storage.py backend/app/models/schemas.py backend/app/api/routes.py backend/tests/test_quick_presets.py backend/tests/test_quick_bundle.py scripts/patch_bundle_quickpresets.py frontend/dist/assets/index-BEOJX8L5.js
git commit -F - <<'EOF'
quick : P6 - presets personnels sur les quatre onglets

Un preset EST la recette de T1, nommee et rangee par onglet : ce qui se
sauvegarde est exactement ce que « Rouvrir dans Quick » sait rejouer, donc un
preset ne peut pas porter un reglage que l'ecran ignorerait. Les castings
HeyGen (avatar_presets) restent ce qu'ils sont.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Lot 2 — différenciant

Les trois tâches du lot 2 supposent le lot 1 livré : D1 et D2 écrivent dans le prompt via le même point (`prompt_engine.build_prompt`), et D3 déplace des blocs posés par T3, T4, T5 et T6.

### Task 7 (D1) : galerie visuelle de mouvements et de styles

**Files :**
- Create : `backend/app/services/quick_gallery.py`, `scripts/patch_bundle_quickgallery.py`, `backend/tests/test_quick_gallery.py`
- Modify : `backend/app/services/prompt_engine.py:218-227` (la caméra s'applique AUSSI à un prompt libre)
- Modify : `backend/app/api/routes.py:3023` (après les routes presets de T6)
- Modify : `backend/tests/test_quick_bundle.py` (+1 fonction)

**Ce que la galerie prétend, exactement.** Les 33 vignettes (11 caméras × 3 styles) sont rendues **localement, par ffmpeg, sur une image fixe**. Elles montrent le MOUVEMENT et l'ÉTALONNAGE que le mot désigne — un mémo visuel du vocabulaire — et non une prédiction de ce que le modèle produira. Le panneau l'écrit noir sur blanc. Sans cette phrase, la galerie serait un mensonge coûteux : personne n'a de rendu gratuit du vrai clip.

- [ ] **Step 1 : banc rouge — on lit le PIXEL en mouvement**

`backend/tests/test_quick_gallery.py` :

```python
"""D1 — les vignettes bougent VRAIMENT : deux images extraites de la même
vignette diffèrent pour « slow push-in » et ne diffèrent presque pas pour
« static, locked-off ». Aucun réseau, aucun numpy.
Run : python tests/test_quick_gallery.py"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                                # noqa: E402
from app.services import quick_gallery as G                          # noqa: E402


def _exe(n):
    return shutil.which(n) or os.path.expandvars(
        r"%LOCALAPPDATA%\DeepotusVideoGen\bin" + f"\\{n}.exe")


def _source() -> pathlib.Path:
    """Damier contrasté 1080x1920 : du détail à déplacer, mais peint en 135x240
    puis agrandi au plus proche voisin — une double boucle sur 2 M de pixels
    coûterait dix secondes au banc pour le même résultat."""
    p = _tmp / "images" / "marque.png"
    petite = Image.new("RGB", (135, 240))
    px = petite.load()
    for y in range(240):
        for x in range(135):
            v = (x + y) % 2
            px[x, y] = (20 + y, 90 * v, 120 + x)
    petite.resize((1080, 1920), Image.NEAREST).save(p)
    return p


def _diff(video: pathlib.Path, t1: float, t2: float) -> float:
    ims = []
    for i, t in enumerate((t1, t2)):
        png = _tmp / f"{video.stem}_{i}.png"
        subprocess.run([_exe("ffmpeg"), "-y", "-v", "error", "-ss", f"{t:.2f}",
                        "-i", str(video), "-frames:v", "1", str(png)],
                       check=True, timeout=120)
        ims.append(list(Image.open(png).convert("L").resize((90, 160)).getdata()))
    return sum(abs(a - b) for a, b in zip(*ims)) / float(len(ims[0]))


def test_les_vignettes_bougent_ou_ne_bougent_pas_comme_annonce():
    src = _source()
    man = G.build(src, only=[("slow push-in", "cinematic"),
                             ("static, locked-off", "cinematic")])
    assert len(man["tiles"]) == 2, man
    par_cam = {t["camera"]: G.tile_path(t["id"]) for t in man["tiles"]}
    bouge = _diff(par_cam["slow push-in"], 0.1, 1.8)
    fixe = _diff(par_cam["static, locked-off"], 0.1, 1.8)
    assert bouge > 4.0, bouge          # le push-in déplace des pixels
    assert fixe < 1.0, fixe            # le plan fixe n'en déplace pas
    assert bouge > fixe * 4, (bouge, fixe)


def test_le_manifeste_couvre_les_onze_cameras_et_les_trois_styles():
    from app.models.schemas import CameraMove, StylePreset
    assert len(G.CAMERAS) == 11, G.CAMERAS
    assert len(G.GRADES) == 3, G.GRADES
    assert set(G.CAMERAS) == {c.value for c in CameraMove}, set(G.CAMERAS)
    assert set(G.GRADES) == {c.value for c in StylePreset}, set(G.GRADES)
```
puis le lanceur `__main__` des Conventions.

Run : `cd backend ; python tests/test_quick_gallery.py`
Attendu : `ModuleNotFoundError: No module named 'app.services.quick_gallery'`.

- [ ] **Step 2 : le service**

`backend/app/services/quick_gallery.py` :

```python
"""D1 — la galerie de mouvements et de styles : 11 caméras × 3 styles rendus
UNE fois, LOCALEMENT, par ffmpeg, sur une image fixe.

Ce que ces vignettes sont : un mémo visuel du vocabulaire — ce que « dolly
zoom » ou « ugc_raw » veut dire, avant d'écrire le prompt. Ce qu'elles ne sont
PAS : une prédiction du rendu du modèle. Personne n'offre 33 clips gratuits ;
le panneau écrit cette phrase à l'écran, sinon la galerie ment.

Les filtres ci-dessous sont des approximations assumées : `orbit` est un
balancement horizontal, `dolly zoom` un zoom sans correction de perspective,
`rack focus` un flou qui se lève. Le nom reste celui de CameraMove, parce que
c'est ce mot-là qui partira dans le prompt.
Aucun numpy : ffmpeg + Pillow seulement.
"""
import hashlib
import json
import subprocess
from pathlib import Path

from loguru import logger

from app.config import settings
from app.services.effects_preview import ffmpeg_bin

FPS, SECS, W, H = 24, 2.0, 540, 960
_N = int(FPS * SECS) - 1                       # dernier index de trame (47)
_C = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"

#: CameraMove.value -> expression zoompan (+ filtre additionnel éventuel)
CAMERAS: dict = {
    "slow push-in":        (f"z='1+0.18*on/{_N}':{_C}", ""),
    "slow pull-out":       (f"z='1.18-0.18*on/{_N}':{_C}", ""),
    "360-degree orbit":    (f"z='1.15':x='iw/2-(iw/zoom/2)+0.06*iw*sin(2*PI*on/{_N})'"
                            ":y='ih/2-(ih/zoom/2)'", ""),
    "tracking shot":       (f"z='1.12':x='(iw-iw/zoom)*on/{_N}'"
                            ":y='ih/2-(ih/zoom/2)'", ""),
    "handheld with subtle shake":
                           (f"z='1.08':x='iw/2-(iw/zoom/2)+0.012*iw*sin(9*on/{_N})'"
                            f":y='ih/2-(ih/zoom/2)+0.012*ih*cos(7*on/{_N})'", ""),
    "static, locked-off":  (f"z='1':{_C}", ""),
    "low angle dramatic":  (f"z='1.20':x='iw/2-(iw/zoom/2)'"
                            f":y='(ih-ih/zoom)*(1-on/{_N})'", ""),
    "rack focus reveal":   (f"z='1.05':{_C}", "boxblur=6:enable='lt(t,0.9)'"),
    "dolly zoom (vertigo effect)":
                           (f"z='1+0.30*on/{_N}':{_C}", ""),
    "whip pan transition": (f"z='1.25':x='(iw-iw/zoom)*min(1,max(0,(on-18)/12))'"
                            ":y='ih/2-(ih/zoom/2)'",
                            "boxblur=8:enable='between(t,0.75,1.25)'"),
    "crane shot descending":
                           (f"z='1.15':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*on/{_N}'", ""),
}

#: StylePreset.value -> étalonnage
GRADES: dict = {
    "cinematic": "eq=contrast=1.12:saturation=1.05",
    "ugc_raw": "eq=contrast=0.98:saturation=1.12:brightness=0.02,noise=alls=8:allf=t",
    "hybrid": "eq=contrast=1.05:saturation=1.08",
}


def gallery_dir() -> Path:
    d = settings.outputs_path / "_gallery"
    d.mkdir(parents=True, exist_ok=True)
    return d


def tile_id(camera: str, style: str) -> str:
    return hashlib.sha1(f"{camera}|{style}".encode("utf-8")).hexdigest()[:12]


def tile_path(tid: str) -> Path:
    return gallery_dir() / f"{Path(tid).name}.mp4"


def manifest_path() -> Path:
    return gallery_dir() / "manifest.json"


def _render(src: Path, camera: str, style: str) -> Path:
    z, extra = CAMERAS[camera]
    chain = (f"zoompan={z}:d=1:s={W}x{H}:fps={FPS}," + GRADES[style]
             + (("," + extra) if extra else "") + ",setsar=1")
    out = tile_path(tile_id(camera, style))
    r = subprocess.run(
        [ffmpeg_bin(), "-y", "-v", "error", "-loop", "1", "-t", str(SECS),
         "-i", str(src), "-vf", chain, "-r", str(FPS), "-an",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "22", str(out)],
        capture_output=True, timeout=300)
    if r.returncode != 0 or not out.is_file():
        raise RuntimeError(f"Vignette {camera}/{style} : "
                           + r.stderr.decode("utf-8", "replace")[-300:])
    return out


def build(image_path, only: list | None = None) -> dict:
    """Rend les vignettes manquantes et écrit le manifeste. Idempotent : une
    vignette déjà rendue depuis LA MÊME image source n'est pas refaite."""
    src = Path(image_path)
    if not src.is_file():
        raise ValueError(f"Image de marque introuvable : {src.name}")
    sig = hashlib.sha1(src.read_bytes()).hexdigest()[:16]
    ancien = {}
    if manifest_path().is_file():
        try:
            ancien = json.loads(manifest_path().read_text("utf-8"))
        except ValueError:
            ancien = {}
    frais = ancien.get("source_sha1") == sig
    paires = only or [(c, s) for c in CAMERAS for s in GRADES]
    tiles = []
    for camera, style in paires:
        tid = tile_id(camera, style)
        if not (frais and tile_path(tid).is_file()):
            _render(src, camera, style)
        tiles.append({"id": tid, "camera": camera, "style": style,
                      "url": f"/api/quick/gallery/{tid}"})
    man = {"source": src.name, "source_sha1": sig, "n": len(tiles),
           "tiles": tiles,
           "note": ("Vignettes rendues localement par ffmpeg sur une image "
                    "fixe : elles montrent le mot, pas le rendu du modèle.")}
    manifest_path().write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")
    logger.info(f"quick_gallery: {len(tiles)} vignette(s) prêtes ({src.name})")
    return man
```

Run : `cd backend ; python tests/test_quick_gallery.py`
Attendu : `PASS test_le_manifeste_couvre_les_onze_cameras_et_les_trois_styles`, `PASS test_les_vignettes_bougent_ou_ne_bougent_pas_comme_annonce`, `BILAN OK`.

- [ ] **Step 3 : la caméra s'applique enfin à un prompt libre**

Sans cela, la galerie ne changerait rien pour le geste le plus fréquent (réponse 1 de R1 : image → clip, prompt écrit à la main) : `build_prompt` ignore aujourd'hui `request.camera` dès que `custom_prompt` est rempli (`prompt_engine.py:218-227`).

`prompt_engine.py` — dans `build_prompt`, remplacer les lignes 218-220 par :

```python
        if request.custom_prompt:
            base_prompt = request.custom_prompt.strip()
            # D1/D2 — la caméra choisie s'applique AUSSI à un prompt libre.
            # Avant ce plan, `camera` n'était lu que sur la branche template :
            # la galerie et les curseurs n'auraient rien changé au geste le
            # plus fréquent (image -> clip avec prompt écrit à la main).
            if request.camera:
                base_prompt = f"{base_prompt} Camera: {request.camera.value}."
```

Ajouter dans `backend/tests/test_quick_gallery.py` :

```python
def test_la_camera_entre_dans_un_prompt_libre():
    from app.models.schemas import CameraMove, GenerateRequest
    from app.services.prompt_engine import PromptEngine
    req = GenerateRequest(image_filename="a.png", custom_prompt="un trone abyssal",
                          camera=CameraMove.CRANE_DOWN)
    pos, _neg = PromptEngine().build_prompt(req)
    assert "un trone abyssal" in pos, pos
    assert "Camera: crane shot descending." in pos, pos
```

Run : `cd backend ; python tests/test_quick_gallery.py`
Attendu : trois `PASS`, `BILAN OK`.

- [ ] **Step 4 : les routes**

`routes.py` — après les routes presets de T6 :

```python
@router.post("/quick/gallery/build")
async def build_quick_gallery(body: dict = None):
    """D1 — rendre les 33 vignettes (ou les manquantes). Local, gratuit, long
    la première fois (~30 s) : l'appel est synchrone et rend le manifeste, pour
    que l'écran sache quand ouvrir la grille au lieu de deviner."""
    from app.services import quick_gallery as G
    name = str((body or {}).get("image") or "").strip()
    if not name:
        raise HTTPException(400, "Choisis l'image de marque de la galerie.")
    src = settings.images_path / Path(name).name
    if not src.is_file():
        raise HTTPException(404, f"Image introuvable dans la Library : {name}")
    try:
        return await asyncio.to_thread(G.build, src)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(400, str(e))


@router.get("/quick/gallery")
async def get_quick_gallery():
    """D1 — le manifeste, ou `built:false` si la galerie n'a jamais été rendue."""
    from app.services import quick_gallery as G
    import json as _json
    p = G.manifest_path()
    if not p.is_file():
        return {"built": False, "cameras": list(G.CAMERAS), "styles": list(G.GRADES)}
    try:
        return {"built": True, **_json.loads(p.read_text("utf-8"))}
    except ValueError:
        return {"built": False, "cameras": list(G.CAMERAS), "styles": list(G.GRADES)}


@router.get("/quick/gallery/{tile_id}")
async def get_quick_gallery_tile(tile_id: str):
    """D1 — une vignette mp4. `tile_id` est un sha1 tronqué : la garde de nom
    (Path(...).name dans tile_path) empêche toute sortie du dossier."""
    from app.services import quick_gallery as G
    p = G.tile_path(tile_id)
    if not p.is_file():
        raise HTTPException(404, "Vignette non rendue")
    return FileResponse(p, media_type="video/mp4")
```

- [ ] **Step 5 : banc rouge du bundle, puis le patcher**

Ajouter dans `backend/tests/test_quick_bundle.py` :

```python
def test_quickgallery():
    s = _s()
    assert s.count("__dzQuickGallery") == 2       # définition + bouton
    assert s.count("/api/quick/gallery") == 2     # manifeste + build (les URLs
    #                                              des vignettes viennent du manifeste)
    assert "montrent le mot, pas le rendu du mod" in s   # la phrase honnête
    assert 'title:"Galerie de mouvements"' in s
```

`scripts/patch_bundle_quickgallery.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_quickgallery.py
"""D1 — galerie visuelle de mouvements et de styles (T7).
BASELINE : bundle POST-patch quickpresets. Backup : .js.bak_quickgallery. EN QUEUE.

G1 helper __dzQuickGallery(img, onPick) : grille modale en DOM pur (pattern
   __dzSendMenu, déjà éprouvé) — pas de composant React, donc pas d'ancre dans
   le rendu de um et pas de re-render à chaque survol de 33 <video>.
G2 bouton « Galerie » à droite de la section Parameters : choisit caméra ET
   style (le style alimente la Vibe existante, la caméra part dans le prompt).
Run : python scripts/patch_bundle_quickgallery.py [--check]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_quick import run  # noqa: E402

TAG = "quickgallery"
MARKER = "__dzQuickGallery"

G1 = (
    'function __dzQuickGallery(img,onPick){'
    'function grille(d){var old=document.getElementById("__dzGalHost");if(old)old.remove();'
    'var h=document.createElement("div");h.id="__dzGalHost";'
    'h.style.cssText="position:fixed;inset:0;background:rgba(4,6,10,.6);z-index:9500;'
    'display:flex;align-items:center;justify-content:center";'
    'var c=document.createElement("div");'
    'c.style.cssText="width:min(1100px,94vw);max-height:86vh;overflow:auto;background:var(--bg-panel,#13171c);'
    'border:1px solid var(--stroke,#20262d);border-radius:12px;padding:14px";'
    'var t=document.createElement("div");t.style.cssText="font-size:13px;color:var(--ink-strong,#e6edf3);margin-bottom:4px";'
    't.textContent="Galerie de mouvements — 11 caméras × 3 styles";'
    'var n=document.createElement("div");n.style.cssText="font-size:11px;color:var(--ink-soft,#8b97a3);margin-bottom:10px";'
    'n.textContent=d.note||"";c.appendChild(t);c.appendChild(n);'
    'var g=document.createElement("div");'
    'g.style.cssText="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px";'
    '(d.tiles||[]).forEach(function(ti){var b=document.createElement("button");'
    'b.style.cssText="all:unset;cursor:pointer;display:block;border:1px solid var(--stroke,#20262d);'
    'border-radius:8px;overflow:hidden;background:#02060d";'
    'var v=document.createElement("video");v.src=ti.url;v.muted=!0;v.loop=!0;v.autoplay=!0;v.playsInline=!0;'
    'v.style.cssText="width:100%;display:block;aspect-ratio:9/16;object-fit:cover";'
    'var l=document.createElement("div");'
    'l.style.cssText="font-size:10.5px;color:var(--ink,#cfd6dd);padding:5px 6px";'
    'l.textContent=ti.camera+" · "+ti.style;b.appendChild(v);b.appendChild(l);'
    'b.onclick=function(){h.remove();onPick(ti)};g.appendChild(b)});'
    'c.appendChild(g);h.appendChild(c);'
    'h.onclick=function(e){if(e.target===h)h.remove()};document.body.appendChild(h)}'
    'fetch("/api/quick/gallery").then(function(r2){return r2.json()}).then(function(d){'
    'if(d&&d.built)return grille(d);'
    'if(!img){__dzToast("Choisis d\'abord une image de départ : la galerie se rend dessus");return}'
    '__dzToast("Rendu local des 33 vignettes (~30 s, gratuit)…");'
    'return fetch("/api/quick/gallery/build",{method:"POST",'
    'headers:{"Content-Type":"application/json"},body:JSON.stringify({image:img})})'
    '.then(function(r3){return r3.json()}).then(function(d2){'
    'if(d2&&d2.tiles)grille(d2);else __dzToast("Galerie : "+((d2&&d2.detail)||"echec"))})})'
    '.catch(function(e){window.alert("Galerie : "+String(e&&e.message||e))})}'
)

A_STUDIO = "function __dzReopenStudio(id){"
A_PARAMS = 'r.jsxs(ie,{label:"Parameters",children:['

PATCHES = [
    ("G1-helper", A_STUDIO, G1 + A_STUDIO),
    ("G2-bouton", A_PARAMS,
     'r.jsxs(ie,{label:"Parameters",right:r.jsx(K,{variant:"ghost",size:"sm",icon:"film",'
     'title:"Galerie de mouvements",onClick:function(){__dzQuickGallery(w,function(ti){'
     'V(ti.style==="ugc_raw"?"ugc_raw":ti.style==="hybrid"?"hybrid":"cinematic");'
     'a((s+" Camera: "+ti.camera+".").trim());'
     '__dzToast("« "+ti.camera+" » ajouté au prompt")})},children:"Galerie"}),children:['),
]

if __name__ == "__main__":
    run(TAG, MARKER, 2, PATCHES, [("dzQpUI", 3), ("__dzReopenQuick", 3)])
```

Run : `python scripts/patch_bundle_quickgallery.py --check` puis sans `--check`
Attendu : `[quickgallery] applicable sur … : 2 ancres OK`, puis `OK - bundle patche (quickgallery) : 2 sections, +NNNN o` ; `node --check` muet ; inventaire : +1 fonction.

- [ ] **Step 6 : vert + sonde**

Run : `cd backend ; python tests/test_quick_bundle.py` puis `cd backend ; python tests/test_quick_gallery.py`
Attendu : `BILAN OK` deux fois.
Sonde navigateur : Quick → Parameters → « Galerie » : au premier clic, le toast annonce le rendu local, puis la grille de 33 vignettes s'ouvre, chacune jouant en boucle ; la phrase « montrent le mot, pas le rendu du modèle » est visible en tête. Cliquer « crane shot descending · cinematic » : le prompt gagne `Camera: crane shot descending.` et la Vibe passe à `cinematic`. Rouvrir : instantané (manifeste relu).

- [ ] **Step 7 : commit**

```bash
git add backend/app/services/quick_gallery.py backend/app/services/prompt_engine.py backend/app/api/routes.py backend/tests/test_quick_gallery.py backend/tests/test_quick_bundle.py scripts/patch_bundle_quickgallery.py frontend/dist/assets/index-BEOJX8L5.js
git commit -F - <<'EOF'
quick : D1 - galerie de 11 cameras x 3 styles, rendue une fois en local

Les vignettes sont un memo du vocabulaire, pas une prediction du modele : le
panneau l'ecrit. Au passage, la camera choisie entre enfin dans un prompt LIBRE
(build_prompt l'ignorait des qu'un custom_prompt etait rempli), sans quoi ni la
galerie ni les curseurs de D2 ne changeraient rien au geste le plus frequent.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 8 (D2) : curseurs caméra chiffrés, traduits en phrase

**Files :**
- Create : `backend/app/services/camera_lang.py`, `scripts/patch_bundle_quickcamera.py`, `backend/tests/test_quick_camera.py`
- Modify : `backend/app/models/schemas.py:177` (GenerateRequest, après `lipsync` de T5), `backend/app/services/prompt_engine.py:224` (après la ligne caméra de T7), `backend/app/api/routes.py` (après les routes galerie de T7)
- Modify : `backend/tests/test_quick_bundle.py` (+1 fonction)

Mesuré en R1 le 03/09 : via fal, **aucun** des modèles au registre n'expose de `camera_control` (Kling v3 Pro n'en a pas), et Runway a retiré son contrôle chiffré le 30/07/2026 — Gen-4 pilote la caméra **par le prompt**. Les curseurs produisent donc du TEXTE. Le vocabulaire de la famille `kling` reprend celui de l'application Kling (six axes, référence vérifiée) ; celui des autres familles est notre propre anglais de plateau, pas une affirmation sur leur API.

- [ ] **Step 1 : banc rouge**

`backend/tests/test_quick_camera.py` :

```python
"""D2 — la traduction curseurs -> phrase est PURE et déterministe : le banc lit
la phrase rendue, et le prompt final construit par prompt_engine.
Run : python tests/test_quick_camera.py"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import camera_lang as CL                           # noqa: E402


def test_zero_partout_ne_dit_rien():
    assert CL.phrase({a: 0 for a in CL.AXES}, "veo_fal") == ""
    assert CL.phrase({}, "kling") == ""
    assert CL.phrase(None, "kling") == ""


def test_chaque_axe_a_ses_deux_sens_et_trois_intensites():
    for fam in CL.FAMILLES:
        for a in CL.AXES:
            p1 = CL.phrase({a: 9}, fam)
            p2 = CL.phrase({a: -9}, fam)
            p3 = CL.phrase({a: 2}, fam)
            assert p1 and p2 and p3, (fam, a)
            assert p1 != p2, (fam, a, p1)      # les deux sens diffèrent
            assert p3 != p1, (fam, a, p3)      # l'intensité change le mot


def test_la_phrase_kling_parle_kling_et_l_ordre_est_stable():
    p = CL.phrase({"zoom": 6, "pan": -8, "tilt": 3}, "kling")
    assert p.startswith("Camera: "), p
    assert p.endswith("."), p
    assert p.index("zoom") < p.index("pan"), p   # ordre = CL.AXES, pas un dict
    assert CL.phrase({"tilt": 3, "pan": -8, "zoom": 6}, "kling") == p


def test_les_curseurs_entrent_dans_le_prompt_libre():
    from app.models.schemas import GenerateRequest
    from app.services.prompt_engine import PromptEngine
    req = GenerateRequest(image_filename="a.png", custom_prompt="un trone abyssal",
                          video_model="kling-v3-pro",
                          camera_ctrl={"zoom": 7, "tilt": -4})
    pos, _n = PromptEngine().build_prompt(req)
    assert "un trone abyssal" in pos and "Camera: " in pos, pos
    assert "zoom" in pos and "tilt" in pos.lower(), pos


def test_famille_inconnue_retombe_sur_le_vocabulaire_neutre():
    p = CL.phrase({"zoom": 5}, "famille-qui-n-existe-pas")
    assert p == CL.phrase({"zoom": 5}, "neutre"), p
```
puis le lanceur `__main__` des Conventions.

Run : `cd backend ; python tests/test_quick_camera.py`
Attendu : `ModuleNotFoundError: No module named 'app.services.camera_lang'`.

- [ ] **Step 2 : le service**

`backend/app/services/camera_lang.py` :

```python
"""D2 — six curseurs chiffrés -> une phrase de caméra, par famille de modèle.

Pourquoi du texte : mesuré le 03/09/2026 (R1), aucun modèle du registre
n'expose de `camera_control` via fal (Kling v3 Pro n'en a pas), et Runway a
retiré son contrôle chiffré le 30/07/2026 — Gen-4 pilote la caméra par le
prompt. Les curseurs sont donc un dialecte que l'on TRADUIT.

Le vocabulaire de la famille `kling` reprend celui de l'application Kling (six
axes en commandes absolues, kling.ai/quickstart, 03/09) ; les autres familles
utilisent notre propre anglais de plateau — ce n'est pas une affirmation sur
leur API. Si l'API Kling directe entre un jour au registre, les mêmes curseurs
alimenteront `camera_control` sans changer l'écran.

Fonction pure, sans dépendance : arithmétique et tables.
"""
from app.services.fal_service import VIDEO_MODELS

#: ordre d'énonciation — stable, indépendant de l'ordre des clés reçues
AXES = ("zoom", "horizontal", "vertical", "pan", "tilt", "roll")

_NEUTRE = {
    "zoom": ("pushing in", "pulling out"),
    "horizontal": ("tracking right", "tracking left"),
    "vertical": ("craning up", "craning down"),
    "pan": ("panning right", "panning left"),
    "tilt": ("tilting up", "tilting down"),
    "roll": ("rolling clockwise", "rolling counter-clockwise"),
}
_KLING = {
    "zoom": ("zoom in", "zoom out"),
    "horizontal": ("horizontal movement right", "horizontal movement left"),
    "vertical": ("vertical movement up", "vertical movement down"),
    "pan": ("pan right", "pan left"),
    "tilt": ("tilt up", "tilt down"),
    "roll": ("roll clockwise", "roll counter-clockwise"),
}
#: famille (fal_service.VIDEO_MODELS[...]["family"]) -> lexique
FAMILLES: dict = {
    "neutre": _NEUTRE, "kling": _KLING, "seedance1": _NEUTRE,
    "seedance2": _NEUTRE, "seedance25": _NEUTRE, "pixverse": _NEUTRE,
    "veo_fal": _NEUTRE, "veo_google": _NEUTRE,
}
#: |valeur| -> qualificatif. 0 = l'axe est muet.
_FORCE = ((3, "slightly"), (7, ""), (10, "strongly"))


def famille_du_modele(model_id: str | None) -> str:
    """La famille du modèle, `neutre` si l'id est inconnu (jamais d'exception :
    une phrase de caméra ne doit pas pouvoir faire échouer un rendu)."""
    m = VIDEO_MODELS.get((model_id or "").strip())
    fam = (m or {}).get("family") or "neutre"
    return fam if fam in FAMILLES else "neutre"


def _mot(lex: dict, axe: str, v: int) -> str:
    base = lex[axe][0 if v > 0 else 1]
    n = min(10, abs(int(v)))
    q = next(q for seuil, q in _FORCE if n <= seuil)
    return f"{q} {base}".strip()


def phrase(ctrl, family: str = "neutre") -> str:
    """`ctrl` = {axe: -10..10}. Rend `Camera: a, b, c.` ou `""` si tout est nul."""
    if not isinstance(ctrl, dict):
        return ""
    lex = FAMILLES.get(family) or _NEUTRE
    bouts = []
    for axe in AXES:
        try:
            v = int(round(float(ctrl.get(axe) or 0)))
        except (TypeError, ValueError):
            v = 0
        if v:
            bouts.append(_mot(lex, axe, max(-10, min(10, v))))
    return ("Camera: " + ", ".join(bouts) + ".") if bouts else ""


def phrase_pour(ctrl, model_id: str | None) -> str:
    return phrase(ctrl, famille_du_modele(model_id))
```

- [ ] **Step 3 : schéma, prompt, route**

`schemas.py` — dans `GenerateRequest`, après `lipsync` de T5 (l.177) :

```python
    # D2 — six curseurs de caméra (-10..10) traduits en phrase par
    # camera_lang, selon la famille du modèle choisi.
    camera_ctrl: Optional[dict] = None
```

`prompt_engine.py` — dans `build_prompt`, juste après la ligne `Camera:` ajoutée par T7 :

```python
            # D2 — les curseurs, traduits dans le dialecte de la famille du
            # modèle. Après la caméra nommée : les deux se cumulent sans se
            # contredire (l'une nomme le plan, l'autre le chiffre).
            if getattr(request, "camera_ctrl", None):
                from app.services import camera_lang
                _cp = camera_lang.phrase_pour(request.camera_ctrl,
                                              getattr(request, "video_model", None))
                if _cp:
                    base_prompt = f"{base_prompt} {_cp}"
```
et la même paire de lignes à la fin de la branche template, juste avant `return positive.strip(), …` (l.257), en remplaçant `positive` :

```python
        if getattr(request, "camera_ctrl", None):
            from app.services import camera_lang
            _cp = camera_lang.phrase_pour(request.camera_ctrl,
                                          getattr(request, "video_model", None))
            if _cp:
                positive = f"{positive} {_cp}"
```

`routes.py` — après les routes galerie de T7 :

```python
@router.post("/quick/camera-phrase")
async def quick_camera_phrase(body: dict = None):
    """D2 — l'aperçu de la phrase, pendant qu'on bouge les curseurs. Une route
    plutôt qu'un calcul dans le bundle : la traduction doit être LA MÊME que
    celle du rendu, et elle vit dans camera_lang."""
    from app.services import camera_lang as CL
    b = body or {}
    ctrl = b.get("ctrl") if isinstance(b.get("ctrl"), dict) else {}
    fam = CL.famille_du_modele(b.get("model"))
    return {"family": fam, "phrase": CL.phrase(ctrl, fam), "axes": list(CL.AXES)}
```

Run : `cd backend ; python tests/test_quick_camera.py`
Attendu : cinq `PASS`, `BILAN OK`.

- [ ] **Step 4 : banc rouge du bundle, puis le patcher**

Ajouter dans `backend/tests/test_quick_bundle.py` :

```python
def test_quickcamera():
    s = _s()
    assert s.count("function dzCam(") == 1
    assert s.count("camera_ctrl:dzCam(),") == 2      # solo + slot seedance de comp
    assert s.count("dzCamCtl") >= 8                  # état + 6 curseurs + aperçu
    assert "/api/quick/camera-phrase" in s
    assert 'label:"Caméra (curseurs)"' in s
```

`scripts/patch_bundle_quickcamera.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_quickcamera.py
"""D2 — curseurs caméra traduits en phrase (T8).
BASELINE : bundle POST-patch quickgallery. Backup : .js.bak_quickcamera. EN QUEUE.

C1 état dzCamCtl (six axes) + dzCam() + aperçu de phrase par la ROUTE (la
   traduction ne doit exister qu'à un endroit : camera_lang).
C2 les six curseurs Oe + la phrase, insérés au-dessus du select « Modèle ».
C3 payload solo, C4 payload composition (slot seedance).
C5 recette, C6 dzQuickApply.
Run : python scripts/patch_bundle_quickcamera.py [--check]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_quick import run  # noqa: E402

TAG = "quickcamera"
MARKER = "function dzCam("

C1 = (
    'var dzCcS=x.useState({zoom:0,horizontal:0,vertical:0,pan:0,tilt:0,roll:0}),'
    'dzCamCtl=dzCcS[0],dzSetCamCtl=dzCcS[1],'
    'dzCpS=x.useState(""),dzCamPh=dzCpS[0],dzSetCamPh=dzCpS[1];'
    'function dzCam(){var vide=!0;for(var k2 in dzCamCtl)if(dzCamCtl[k2])vide=!1;'
    'return vide?void 0:dzCamCtl}'
    'x.useEffect(function(){var on=!0,id=setTimeout(function(){'
    'fetch("/api/quick/camera-phrase",{method:"POST",headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify({ctrl:dzCamCtl,model:VMQ||void 0})})'
    '.then(function(r2){return r2.ok?r2.json():null})'
    '.then(function(d2){if(on)dzSetCamPh((d2&&d2.phrase)||"")}).catch(function(){})},200);'
    'return function(){on=!1;clearTimeout(id)}},[dzCamCtl,VMQ]);'
    'function dzCamSet(a2,v2){dzSetCamCtl(function(p2){var n2=Object.assign({},p2);'
    'n2[a2]=Number(v2)||0;return n2})}'
)

# Ancre = le champ « Modèle » ENTIER : on insère un champ FRÈRE avant lui.
# Ancrer sur `children:r.jsx(DzVideoModelSel,…` obligerait à rouvrir un tableau
# d'enfants et à aller fermer le crochet ailleurs — deux ancres pour une idée,
# et un `]` oublié ne se voit qu'au `node --check`.
C2_A = 'r.jsx(O,{label:"Modèle",children:r.jsx(DzVideoModelSel,{value:VMQ,'
C2_B = (
    'r.jsx(O,{label:"Caméra (curseurs)",children:r.jsxs("div",{children:['
    '["zoom","horizontal","vertical","pan","tilt","roll"].map(function(a2){'
    'return r.jsx(Oe,{label:a2,value:dzCamCtl[a2],min:-10,max:10,step:1,unit:"",'
    'onChange:function(v2){dzCamSet(a2,v2)}},a2)}),'
    'r.jsx("div",{style:{fontSize:10.5,fontFamily:"var(--f-mono)",color:"var(--cyan)",'
    'marginTop:4,minHeight:14},children:dzCamPh||"— aucun mouvement demandé —"},"dzcamph"),'
    'r.jsx("div",{style:{fontSize:10,color:"var(--ink-soft)"},'
    'children:"Aucun modèle du registre n\'expose de contrôle caméra via fal (mesuré le '
    '03/09/2026) : ces curseurs deviennent une phrase, ajoutée au prompt."},"dzcamnote")]})}),'
) + C2_A

PATCHES = [
    ("C1-etat", "var dzQpS=x.useState([]),", C1 + "var dzQpS=x.useState([]),"),
    ("C2-curseurs", C2_A, C2_B),
    ("C3-solo", "je={quick_recipe:dzQuickRecipe(),subtitles:dzSubs(),lipsync:dzLip(),",
     "je={quick_recipe:dzQuickRecipe(),subtitles:dzSubs(),lipsync:dzLip(),camera_ctrl:dzCam(),"),
    ("C4-comp", "seedance:{video_model:VMQ||void 0,image_filename:w,custom_prompt:je,",
     "seedance:{camera_ctrl:dzCam(),video_model:VMQ||void 0,image_filename:w,custom_prompt:je,"),
    ("C5-recette", "lip:{on:dzLipOn,file:dzLipFile}}}",
     "lip:{on:dzLipOn,file:dzLipFile},cam:dzCamCtl}}"),
    ("C6-apply", "if(lp.file!=null)dzSetLipFile(lp.file)}",
     "if(lp.file!=null)dzSetLipFile(lp.file);"
     "if(rc.cam&&typeof rc.cam===\"object\")dzSetCamCtl(Object.assign("
     "{zoom:0,horizontal:0,vertical:0,pan:0,tilt:0,roll:0},rc.cam))}"),
]

if __name__ == "__main__":
    run(TAG, MARKER, 1, PATCHES,
        [("__dzQuickGallery", 2), ("dzQpUI", 3), ("lipsync:dzLip(),", 1),
         ("camera_ctrl:dzCam(),", 2)])
```

Run : `python scripts/patch_bundle_quickcamera.py --check` puis sans `--check`
Attendu : `[quickcamera] applicable sur … : 6 ancres OK`, puis `OK - bundle patche (quickcamera) : 6 sections, +NNNN o` ; `node --check` **muet** (c'est lui qui attraperait un crochet mal fermé — ne pas passer à l'étape suivante sans l'avoir lancé) ; inventaire : +2 fonctions (`dzCam`, `dzCamSet`).

- [ ] **Step 5 : vert + sonde**

Run : `cd backend ; python tests/test_quick_bundle.py` puis `cd backend ; python tests/test_quick_camera.py`
Attendu : `BILAN OK` deux fois.
Sonde navigateur : Quick → Parameters : six curseurs ; pousser `zoom` à +7 et `tilt` à −4 : la ligne cyan affiche `Camera: pushing in, tilting down.` ; passer le modèle à « Kling v3 Pro » : elle devient `Camera: zoom in, tilt down.` (le dialecte suit la famille). Générer, puis lire `final_prompt` du job dans la file : la phrase y est.

- [ ] **Step 6 : commit**

```bash
git add backend/app/services/camera_lang.py backend/app/models/schemas.py backend/app/services/prompt_engine.py backend/app/api/routes.py backend/tests/test_quick_camera.py backend/tests/test_quick_bundle.py scripts/patch_bundle_quickcamera.py frontend/dist/assets/index-BEOJX8L5.js
git commit -F - <<'EOF'
quick : D2 - six curseurs camera traduits en phrase, par famille de modele

Aucun modele du registre n'expose de camera_control via fal (mesure du
03/09/2026) et Runway a retire son controle chiffre : les curseurs produisent
du TEXTE, et l'ecran le dit. La traduction vit a UN seul endroit (camera_lang),
que l'apercu appelle par la route pour ne pas diverger du rendu.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 9 (D3) : les quatre onglets en « studio »

**Files :**
- Create : `scripts/patch_bundle_quickstudio.py`
- Modify : `backend/tests/test_quick_bundle.py` (+1 fonction)
- Backend : **aucun** — `POST /api/images/upload` (`routes.py:2055`) rend `{filename}` et note déjà la provenance.

Mesuré le 03/09 : le pied « Est. cost + Generate » est déjà un frère du conteneur scroll, donc déjà collé en bas — DESIGN §8.1 est satisfait sur ce point, **rien à faire**. Restent trois écarts réels : la colonne source fait 380 px au lieu de 360 ; la DropZone `vd` est une MAQUETTE (elle n'accepte aucun fichier) ; et l'aperçu central montre l'image de départ quel que soit l'onglet — sur HeyGen, sur Composition et sur Voice Over, il ne représente rien.

- [ ] **Step 1 : banc rouge**

Ajouter dans `backend/tests/test_quick_bundle.py` :

```python
def test_quickstudio():
    s = _s()
    assert s.count("function DzQuickDrop(") == 1
    assert s.count("function DzQuickStage(") == 1
    assert s.count("DzQuickDrop") == 3            # définition + départ + fin
    assert 'gridTemplateColumns:"360px 1fr"' in s
    assert 'gridTemplateColumns:"380px 1fr"' not in s
    assert "onDrop:" in s and "/api/images/upload" in s
    assert "DzQuickStage,{tab:o" in s
```

Run : `cd backend ; python tests/test_quick_bundle.py`
Attendu : `FAIL test_quickstudio -- …`, `BILAN 1 rouge(s)`.

- [ ] **Step 2 : le patcher**

`scripts/patch_bundle_quickstudio.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_quickstudio.py
"""D3 — les quatre onglets en « studio » (T9).
BASELINE : bundle POST-patch quickcamera. Backup : .js.bak_quickstudio. EN QUEUE.

Le pied « Est. cost + Generate » est DÉJÀ collé en bas (frère du scroll, mesuré
le 03/09) : rien à y faire. Restent trois écarts.

U1 DzQuickDrop (vraie DropZone : dragover + drop -> POST /images/upload) et
   DzQuickStage (l'aperçu central selon l'onglet), injectés avant um.
U2 la colonne source passe de 380 px à 360 px (DESIGN §8.1).
U3 le champ « Start image » gagne la DropZone réelle.
U4 le champ « Image de fin » (posé par T3) aussi, du côté autorisé.
U5 l'aperçu central devient DzQuickStage.
U6 le bandeau du bas de l'aperçu suit l'onglet.
U7 l'avertissement « You're about to call fal.ai » nomme le vrai fournisseur.
Run : python scripts/patch_bundle_quickstudio.py [--check]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_quick import run  # noqa: E402

TAG = "quickstudio"
MARKER = "DzQuickStage"

U1 = (
    'function DzQuickDrop({label,onFile}){var s0=x.useState(!1),over=s0[0],setOver=s0[1];'
    'function envoyer(f){if(!f)return;var fd=new FormData();fd.append("file",f);'
    'fetch("/api/images/upload",{method:"POST",body:fd})'
    '.then(function(r2){return r2.ok?r2.json():null}).then(function(j){'
    'if(j&&j.filename){onFile(j.filename);__dzToast("« "+j.filename+" » importée")}'
    'else __dzToast("Import refusé par le backend")})'
    '.catch(function(e){window.alert("Import : "+String(e&&e.message||e))})}'
    'return r.jsx("div",{onDragOver:function(e){e.preventDefault();setOver(!0)},'
    'onDragLeave:function(){setOver(!1)},'
    'onDrop:function(e){e.preventDefault();setOver(!1);'
    'var f=e.dataTransfer&&e.dataTransfer.files&&e.dataTransfer.files[0];envoyer(f)},'
    'style:{height:64,padding:8,borderRadius:8,display:"flex",alignItems:"center",'
    'justifyContent:"center",fontSize:11,cursor:"copy",'
    'background:over?"var(--amber-soft)":"transparent",'
    'border:"1px dashed "+(over?"var(--amber)":"var(--stroke-strong)"),'
    'color:"var(--ink-soft)"},children:over?"Lâche l\'image ici":label})}'
    'function DzQuickStage({tab,img,avatarUrl,layout,ratio}){'
    'if(tab==="heygen")return avatarUrl?r.jsx("img",{src:avatarUrl,alt:"avatar",'
    'style:{position:"absolute",inset:0,width:"100%",height:"100%",objectFit:"cover"}})'
    ':r.jsx("div",{style:{position:"absolute",inset:0,display:"flex",alignItems:"center",'
    'justifyContent:"center",fontSize:11,color:"var(--ink-soft)"},'
    'children:"Choisis un avatar : son portrait s\'affiche ici"});'
    'if(tab==="comp")return r.jsxs("div",{style:{position:"absolute",inset:0,display:"grid",'
    'gridTemplateRows:layout==="split_vstack"?"1fr 1fr":"1fr",'
    'gridTemplateColumns:layout==="split_hstack"?"1fr 1fr":"1fr",gap:2},children:['
    'r.jsx("div",{style:{background:img?"#0a1a24":"#061018",backgroundImage:img?'
    '("url("+D.imageUrl(img)+")"):"none",backgroundSize:"cover",backgroundPosition:"center"}}),'
    'layout!=="sequential"&&r.jsx("div",{style:{background:"#12060f",display:"flex",'
    'alignItems:"center",justifyContent:"center",fontSize:10.5,color:"var(--ink-soft)"},'
    'children:"avatar"})]});'
    'if(tab==="voice")return r.jsx("div",{style:{position:"absolute",inset:0,display:"flex",'
    'alignItems:"center",justifyContent:"center",fontSize:11,color:"var(--ink-soft)",'
    'padding:16,textAlign:"center"},'
    'children:"Voix off : le résultat est un fichier audio, pas une image. Il arrive dans la Bibliothèque."});'
    'return img?r.jsx("img",{src:D.imageUrl(img),alt:img,style:{position:"absolute",inset:0,'
    'width:"100%",height:"100%",objectFit:"cover"}}):null}'
)

A_UM = "function um({variant:e,activePersona:t}){var el;"
A_GRID = 'gridTemplateColumns:"380px 1fr"'
A_START = ('r.jsx(O,{label:"Start image",children:u.length>0?r.jsx(re,{value:w,'
           'options:u.map(B=>({value:B,label:B})),onChange:v}):'
           'r.jsx(vd,{label:"upload images in Library",kind:"image"})})')
A_END = ('r.jsx(vd,{label:"drop or pick",kind:"image"})):r.jsx("div",{style:{fontSize:11,')
A_STAGE = ('w?r.jsx("img",{src:D.imageUrl(w),alt:w,style:{position:"absolute",inset:0,'
           'width:"100%",height:"100%",objectFit:"cover"}}):')
A_BAND = 'children:[A," · ",h,"s"]'
A_WARN = ('"You\'re about to call ",r.jsx("span",{className:"mono strong",children:"fal.ai"})')

PATCHES = [
    ("U1-composants", A_UM, U1 + A_UM),
    ("U2-colonne", A_GRID, 'gridTemplateColumns:"360px 1fr"'),
    ("U3-depart", A_START,
     'r.jsxs(O,{label:"Start image",children:[u.length>0?r.jsx(re,{value:w,'
     'options:u.map(B=>({value:B,label:B})),onChange:v}):null,'
     'r.jsx(DzQuickDrop,{label:"glisse une image ici, ou choisis ci-dessus",'
     'onFile:function(nm){f(function(p2){return p2.indexOf(nm)>=0?p2:[nm].concat(p2)});v(nm)}})]})'),
    ("U4-fin", A_END,
     'r.jsx(DzQuickDrop,{label:"glisse l\'image de fin ici",'
     'onFile:function(nm){f(function(p2){return p2.indexOf(nm)>=0?p2:[nm].concat(p2)});k(nm)}})):'
     'r.jsx("div",{style:{fontSize:11,'),
    ("U5-stage", A_STAGE,
     'r.jsx(DzQuickStage,{tab:o,img:w,layout:We,ratio:_,'
     'avatarUrl:(function(){var _a=U.find(function(z){return z.avatar_id===C});'
     'return(_a&&_a.preview_image_url)||""})()})||'),
    ("U6-bandeau", A_BAND,
     'children:[o==="seedance"?A:o==="heygen"?"avatar":o==="comp"?We:"voix off"," · ",h,"s"]'),
    ("U7-avertissement", A_WARN,
     '"You\'re about to call ",r.jsx("span",{className:"mono strong",'
     'children:o==="heygen"?"heygen.com":o==="voice"?"elevenlabs.io":"fal.ai"})'),
]

if __name__ == "__main__":
    run(TAG, MARKER, 2, PATCHES,
        [("dzCamCtl", 8), ("__dzQuickGallery", 2), ("dzQpUI", 3)])
```

Le `||` de U5 conserve la branche de repli existante (le placeholder « upload an image in Library ») : `DzQuickStage` rend `null` sur l'onglet Seedance sans image, et l'ancien `else` prend alors le relais — aucune ligne d'origine n'est perdue.

- [ ] **Step 3 : appliquer, vérifier, sonder**

Run : `python scripts/patch_bundle_quickstudio.py --check` puis sans `--check`
Attendu : `[quickstudio] applicable sur … : 7 ancres OK`, puis `OK - bundle patche (quickstudio) : 7 sections, +NNNN o` ; `node --check` muet ; inventaire : +2 fonctions (`DzQuickDrop`, `DzQuickStage`).
Run : `cd backend ; python tests/test_quick_bundle.py`
Attendu : neuf fonctions vertes, `BILAN OK`.
Sonde navigateur : la colonne de gauche mesure 360 px — dans la console, `[...document.querySelectorAll('div')].some(d => getComputedStyle(d).gridTemplateColumns.startsWith('360px'))` vaut `true` et la même expression avec `'380px'` vaut `false` ; glisser un PNG du bureau sur la zone « glisse une image ici » : le toast nomme le fichier importé et le select le sélectionne ; onglet HeyGen : le centre montre le portrait de l'avatar ; onglet Composition en `split_vstack` : deux bandes ; onglet Voice Over : la phrase qui explique qu'il n'y a pas d'image.

- [ ] **Step 4 : commit**

```bash
git add scripts/patch_bundle_quickstudio.py backend/tests/test_quick_bundle.py frontend/dist/assets/index-BEOJX8L5.js
git commit -F - <<'EOF'
quick : D3 - les quatre onglets en studio (drop reel, apercu par onglet, 360 px)

Le pied etait deja colle en bas : mesure faite, rien a y toucher. Les trois
ecarts reels sont fermes — la colonne source a 360 px, la DropZone accepte
vraiment un fichier (elle etait une maquette), et l'apercu central montre
enfin quelque chose sur HeyGen, Composition et Voice Over.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Écarté

- **E1 — Comparaison multi-moteurs dans Quick.** Voulue au Studio (réponse 4 de R1) : elle est traitée dans le plan de la catégorie Studio, pas ici.
- **E2 — Re-roll à graine fixe.** Trois modèles sur onze acceptent une graine (mesuré, `fal_service.py:65-151`) et le geste réel est de VARIER, pas de rejouer (réponse 6) : P1 sert ce geste-là.
- **E3 — Brosse de mouvement.** Aucun accès via fal (Kling v3 Pro n'expose ni `dynamic_masks` ni `camera_control`, mesuré le 03/09) et Runway l'a retirée le 11/05/2025 : revient à l'ordre du jour seulement si l'API Kling directe (clé séparée) entre au registre — et alors D2 lui donne déjà les six axes.

---

## Campagne de mutations

### Task 10 : `backend/tests/mutations_quick.py`

**Files :**
- Create : `backend/tests/mutations_quick.py`

Patron : `backend/tests/mutations_plaque_slicer.py` (01/09). **Une adaptation, dite ici** : les bancs de ce plan sont des scripts AUTONOMES qui impriment `PASS`/`FAIL <nom>`/`BILAN`, pas des fichiers pytest — le lecteur de rouges lit donc `^FAIL (\w+)` sur la sortie du script, et l'absence de `BILAN` vaut `ERREUR(collecte)` : un import cassé ne doit jamais passer pour une mutation VERTE (c'est la leçon des trois états de l'Établi).

- [ ] **Step 1 : écrire la campagne**

```python
"""Banc de mutations du plan Quick : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (le nom ne commence pas par `test_`).
Il se lance À LA MAIN, depuis backend/ :

    python tests/mutations_quick.py            # toutes
    python tests/mutations_quick.py 3 7        # celles-là

Il MUTE les sources du dépôt une à une et les REMET à l'octet près (assertion
sha256), donc il ne se lance pas pendant qu'un autre banc lit ces fichiers.

Différence avec mutations_plaque_slicer.py : les bancs visés sont des scripts
AUTONOMES (`python tests/test_quick_x.py`), pas des fichiers pytest. On lit
donc les lignes `FAIL <nom>` de leur sortie, et l'ABSENCE de `BILAN` vaut
ERREUR (import cassé) — jamais VERTE : une collecte morte lue comme « aucun
FAILED » ferait passer une assertion manquante pour une assertion présente.

Une mutation VERTE est une assertion qui manque : c'est l'argument de la revue.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable

# (fichier, ancien, nouveau, banc, tests attendus rouges)
M = [
    # ── T1 : la recette ─────────────────────────────────────────────────────
    ("backend/app/services/quick_recipe.py",
     "    if not isinstance(recipe, dict) or not recipe:\n        return",
     "    if not isinstance(recipe, dict):\n        return",
     "tests/test_quick_recipe.py", ["test_recette_heygen_et_absence_dite"]),
    ("backend/app/services/quick_recipe.py",
     '(_dir() / f"{Path(job_id).name}.json").write_text(',
     '(_dir() / f"{job_id}.json").write_text(',
     "tests/test_quick_recipe.py", ["test_recette_ecrite_puis_relue_pour_seedance"]),
    ("backend/app/api/routes.py",
     '    d = quick_recipe.load(job_id)\n    if d is None:\n        raise HTTPException(404, "No Quick recipe for this render")',
     "    d = quick_recipe.load(job_id) or {}",
     "tests/test_quick_recipe.py", ["test_recette_heygen_et_absence_dite"]),
    # ── T2 : les gardes d'extension ─────────────────────────────────────────
    ("backend/app/services/fal_video_tools.py",
     '    if d > m["max_source_s"]:',
     '    if d > m["max_source_s"] * 2:',
     "tests/test_quick_extend.py",
     ["test_source_trop_longue_refusee_en_citant_la_mesure"]),
    ("backend/app/services/fal_video_tools.py",
     'f"au plus ; ce clip fait {d:.1f} s. Coupe-le au Montage, puis relance "',
     'f"au plus. Coupe-le au Montage, puis relance "',
     "tests/test_quick_extend.py",
     ["test_source_trop_longue_refusee_en_citant_la_mesure"]),
    ("backend/app/services/fal_video_tools.py",
     '    if src.get("ratio") not in m["ratios"]:',
     "    if False:",
     "tests/test_quick_extend.py",
     ["test_format_hors_contrat_refuse_en_citant_les_pixels"]),
    ("backend/app/services/fal_video_tools.py",
     '    return min(connus, key=lambda k: abs(connus[k] - r))',
     '    return "9:16"',
     "tests/test_quick_extend.py",
     ["test_format_hors_contrat_refuse_en_citant_les_pixels"]),
    # ── T4 : les sous-titres ────────────────────────────────────────────────
    ("backend/app/services/quick_finish.py",
     '        if not (text or "").strip():',
     "        if False:",
     "tests/test_quick_subs.py", ["test_sans_texte_le_chemin_gratuit_refuse_en_le_disant"]),
    ("backend/app/services/quick_finish.py",
     '           "-vf", S.subtitles_filter(ass), "-c:a", "copy", "-c:v", "libx264",',
     '           "-c:a", "copy", "-c:v", "libx264",',
     "tests/test_quick_subs.py",
     ["test_les_sous_titres_sont_reellement_graves_sur_le_pixel"]),
    ("backend/app/services/quick_finish.py",
     "    tmp.replace(video)",
     "    pass",
     "tests/test_quick_subs.py",
     ["test_les_sous_titres_sont_reellement_graves_sur_le_pixel"]),
    ("backend/app/services/quick_finish.py",
     'canvas=CANVAS.get(ratio, CANVAS["9:16"])',
     "canvas=(540, 960)",
     "tests/test_quick_subs.py",
     ["test_les_sous_titres_sont_reellement_graves_sur_le_pixel"]),
    # ── T5 : les bornes du lip-sync ─────────────────────────────────────────
    ("backend/app/services/fal_video_tools.py",
     "        if not (lo <= d <= hi):",
     "        if not (0 <= d <= hi):",
     "tests/test_quick_lipsync.py",
     ["test_audio_trop_court_refuse_et_paire_valide_acceptee"]),
    ("backend/app/services/fal_video_tools.py",
     '        for quoi, src, (lo, hi) in (("clip", video, m["video_s"]),\n'
     '                                    ("audio", audio, m["audio_s"])):',
     '        for quoi, src, (lo, hi) in (("audio", audio, m["audio_s"]),):',
     "tests/test_quick_lipsync.py",
     ["test_video_trop_longue_refusee_en_citant_les_deux_bornes"]),
    # ── T6 : les presets ────────────────────────────────────────────────────
    ("backend/app/api/routes.py",
     "        if tab:\n            q = q.where(QuickPreset.tab == tab)",
     "        if False:\n            q = q.where(QuickPreset.tab == tab)",
     "tests/test_quick_presets.py", ["test_ecrit_relu_par_onglet_puis_supprime"]),
    ("backend/app/models/schemas.py",
     '    recipe: dict = Field(..., min_length=1)',
     "    recipe: dict = {}",
     "tests/test_quick_presets.py", ["test_recette_illisible_refusee"]),
    # ── T7 : la galerie ─────────────────────────────────────────────────────
    ("backend/app/services/quick_gallery.py",
     '    "static, locked-off":  (f"z=\'1\':{_C}", ""),',
     '    "static, locked-off":  (f"z=\'1+0.18*on/{_N}\':{_C}", ""),',
     "tests/test_quick_gallery.py",
     ["test_les_vignettes_bougent_ou_ne_bougent_pas_comme_annonce"]),
    ("backend/app/services/prompt_engine.py",
     '                base_prompt = f"{base_prompt} Camera: {request.camera.value}."',
     "                pass",
     "tests/test_quick_gallery.py", ["test_la_camera_entre_dans_un_prompt_libre"]),
    # ── T8 : la traduction des curseurs ─────────────────────────────────────
    ("backend/app/services/camera_lang.py",
     "    for axe in AXES:",
     "    for axe in sorted(ctrl):",
     "tests/test_quick_camera.py",
     ["test_la_phrase_kling_parle_kling_et_l_ordre_est_stable"]),
    ("backend/app/services/camera_lang.py",
     '    q = next(q for seuil, q in _FORCE if n <= seuil)\n    return f"{q} {base}".strip()',
     "    return base",
     "tests/test_quick_camera.py",
     ["test_chaque_axe_a_ses_deux_sens_et_trois_intensites"]),
    ("backend/app/services/camera_lang.py",
     '    return fam if fam in FAMILLES else "neutre"',
     "    return fam",
     "tests/test_quick_camera.py",
     ["test_famille_inconnue_retombe_sur_le_vocabulaire_neutre"]),
    ("backend/app/services/camera_lang.py",
     '"kling": _KLING,',
     '"kling": _NEUTRE,',
     "tests/test_quick_camera.py",
     ["test_la_phrase_kling_parle_kling_et_l_ordre_est_stable"]),
]


def rouges(banc: str, noms: list):
    """Les tests rouges d'un banc AUTONOME — et si rien n'a tourné, on le dit."""
    r = subprocess.run([PY, banc] + noms, capture_output=True,
                       cwd=R / "backend", timeout=1800)
    txt = (r.stdout.decode("utf-8", "replace")
           + r.stderr.decode("utf-8", "replace"))
    erreur = ("BILAN" not in txt) or (r.returncode not in (0, 1))
    return set(re.findall(r"^FAIL (\w+)", txt, re.M)), txt, erreur


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, banc, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        assert txt.count(old) == 1, (i, rel, txt.count(old), old[:60])
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace(old, new).replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur = rouges(banc, attendus)
        finally:
            p.write_bytes(src)
            assert hashlib.sha256(p.read_bytes()).hexdigest() == sha_avant, (i, rel)
        manquants = [a for a in attendus if a not in rg]
        if erreur:
            verdict = "ERREUR(banc)"
            print(sortie[-1200:], file=sys.stderr)
        else:
            verdict = ("ROUGE" if not manquants
                       else ("VERTE" if not rg else "ROUGE(autres)"))
        bilan.append((i, rel, verdict))
        print(f"[{i:2d}] {verdict:14s} {rel.split('/')[-1]:24s} "
              f"{old.strip()[:46]!r} -> {sorted(rg)}  sha {sha_avant[:10]}")
        sys.stdout.flush()
    verts = [b for b in bilan if b[2].startswith("VERTE")]
    print(json.dumps(bilan, ensure_ascii=False))
    print(f"BILAN MUTATIONS : {len(bilan)} mutation(s), {len(verts)} VERTE(s)")
    sys.exit(1 if verts else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2 : lancer la campagne**

Run : `cd backend ; python tests/mutations_quick.py`
Attendu : vingt-et-une lignes `[nn] ROUGE …`, puis `BILAN MUTATIONS : 21 mutation(s), 0 VERTE(s)` et code 0. Chaque `sha` affiché prouve que le fichier a été remis à l'octet près.

- [ ] **Step 3 : traiter les vertes**

Pour chaque `VERTE`, l'assertion manque : l'ajouter au banc nommé dans la mutation, relancer **cette mutation seule** (`python tests/mutations_quick.py <n>`) jusqu'à `ROUGE`, puis relancer la campagne entière. Ne jamais retirer une mutation pour faire disparaître une verte — c'est le constat qui a de la valeur.

- [ ] **Step 4 : commit**

```bash
git add backend/tests/mutations_quick.py backend/tests/test_quick_recipe.py backend/tests/test_quick_extend.py backend/tests/test_quick_subs.py backend/tests/test_quick_lipsync.py backend/tests/test_quick_presets.py backend/tests/test_quick_gallery.py backend/tests/test_quick_camera.py
git commit -F - <<'EOF'
quick : campagne de mutations des sept bancs du plan

Vingt-et-une mutations, chacune nommant le test qu'elle doit faire rougir et le
banc a lancer. Adaptation du patron de la plaque : les bancs de ce plan sont des
scripts autonomes, donc on lit les lignes FAIL de leur sortie et l'absence de
BILAN vaut ERREUR — un import casse ne doit pas passer pour une mutation verte.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```
