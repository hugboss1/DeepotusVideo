# Génération IA enrichie (t182 → t193) : plan d'implémentation

> **Pour les agents :** sous-skill requis : superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans. Les étapes sont des cases (`- [ ]`). **Un lot = une branche `chantier/<nom>` partie de `origin/main` = une PR.** Jamais dans le dossier `C:\Users\olivi\DeepotusVideo` lui-même, qui est en retard sur main (279 commits le 11/10) : travailler dans un worktree.

## En-tête

- **Date :** 11/10/2026.
- **Demande :** enrichir tous les encarts de génération IA avec les modèles manquants, chacun dans sa nature d'appel ; montrer **les deux voies** (clé individuelle / clé fal) avec leur coût. Ajouts demandés :
  - SAM 3 (objets 3D) dans le storyboard de Chapitres, avant la vidéo ;
  - les meilleurs modèles de SFX ;
  - les modèles de VFX ;
  - tous les modèles de détourage ;
  - Veo 3.1 fast et first-last-frame pour les compositions du Studio ;
  - la génération d'image **par calque** dans le Vectorlab et le Photolab ;
  - la traduction FR/EN et les guides illustrés FR/EN.
- **Contrainte :** toutes les connexions actuelles restent (OpenAI, Gemini, ElevenLabs, Meshy, HeyGen, Decart, local). On **ajoute** la voie fal à côté ; on ne retire rien.
- **Sources :**
  - `docs/superpowers/specs/2026-10-11-balayage-fournisseurs-fal.md` (skill `balayage-fournisseurs-fal`) ;
  - deux relevés du code sur origin/main **b74fdf2a**.
- **Suivi :** lot « Génération IA », tâches **t182 à t193** de l'artifact des chantiers (t181 est la dernière utilisée).
- **Schémas fal :** relus le 11/10 avec `python ~/.claude/skills/balayage-fournisseurs-fal/scripts/fal_schema.py <id>`. **Toujours les relire au début du lot** : les noms de paramètres bougent.
- **Prix fal :** `fal_prix.py <id>`. Un prix non affiché se code `0.0` et le libellé dit « prix à mesurer », comme `birefnet_video_usd_per_s` aujourd'hui. On n'invente jamais un chiffre.

## Constat (code de main b74fdf2a)

1. **Une seule nature a déjà deux voies : l'image GPT.** Les paires `gpt-image-2` / `gpt-image-2-fal` existent dans `image_providers.PROVIDERS` (`backend/app/services/image_providers.py:23-50`). Mais `/api/image-models` (`backend/app/api/routes.py:8926`) ne renvoie que les modèles **disponibles**, sans prix ni nom de clé. L'UI recolle la clé depuis le miroir `CATALOGUE_IMAGE` (`frontend/shared/dz-champ-ia.js:626-642`). Aucun écran ne regroupe « votre clé » et « clé fal ».
2. **Les listes d'images ont divergé.**
   - `PROVIDERS` a 10 ids : `gpt-image-1-mini` y manque.
   - `pricing._IMAGE_MODELS` (`pricing.py:166-186`) et `material_store.MODELS` en ont 11.
3. **Plusieurs encarts ont leur liste codée en dur :**
   - `dzVmRates` (bundle) ;
   - le moteur 3D `var ENG=[{value:"tripo"` (bundle) ;
   - `MODEL_COST` / `MODEL_SEC` (`frontend/materialforge/materialforge.js:135-146`) ;
   - `SVM_GENS` (`frontend/patches/son-vfx-montage.js:127-134`), où le SFX est affiché **« gratuit »** alors qu'il est payant ;
   - `dzLip` (`kling-lipsync` en dur) ;
   - le détourage du nœud Studio (`scripts/patch_bundle_imagegen.py:162-165`) ;
   - le détourage Spritelab (`frontend/spritelab/index.html:172-178`).
4. **Vidéo.** `VIDEO_MODELS` (`backend/app/services/fal_service.py:69-154`) ne contient que des modèles image→vidéo.
   - Veo 3.1 fal a `end_image: False`, alors que fal sert `fal-ai/veo3.1[/fast|/lite]/first-last-frame-to-video`.
   - Le port `end` du nœud Seedance du Studio n'est lu par **aucun** compilateur.
   - `/generate/composition` n'envoie jamais `image_filename_end`.
5. **Détourage.** Il n'existe aucun registre. Chaque site code sa méthode : `fal-ai/imageutils/rembg` (2023), rembg local, chroma, `fal-ai/birefnet/v2` (décor seulement), `fal-ai/birefnet/v2/video` (matte).
6. **SFX.** Il n'y a qu'ElevenLabs direct, sans choix de modèle (`backend/app/services/sfx_service.py:47`).
7. **VFX.** Aucun modèle IA : le rack est en ffmpeg local et les particules sont locales. La seule action IA est le matte BiRefNet vidéo.
8. **Chapitres.** Le parcours est : découpe → croquis FLUX (R:10356) → image de production nano-banana (R:10427) → Plateau 3D local (`frontend/plateau/`, `backend/app/services/scene3d_routes.py`) → animatique. `vers-plan` écrit `keyframe_image` et `keyframe_end` sur le plan (`scene3d_routes.py:507-546`), mais **aucune route n'en fait une vidéo**.
9. **Vectorlab.** `mod-image.js:223-237` `generer()` pose déjà une image générée sur le calque **actif**, mais sans choix de modèle ni de prix, et sans détourage.
10. **Photolab.** Aucune IA. On peut seulement placer une image de la Bibliothèque (`/api/photolab/placer`, `backend/app/api/photolab_routes.py:567`).
11. **Piège de banc.** `backend/tests/test_i18n_l6.py` [2] compare chaque module L6 du Vectorlab à sa BASE `e7fb1ac1` plus sa table d'éditions. Toucher `mod-image.js` ou `mod-layers.js` rend 2a/2b rouges, sauf si on met à jour `scripts/i18n_l6/` (voir t190).

## Architecture

Une **source unique** décrit chaque modèle appelable, `backend/app/services/catalogue_ia.py`, pour toutes les natures. Une entrée porte :

```
id · nature · libellé · voie (fal | openai | gemini | elevenlabs | meshy | local) · clé requise
· endpoint · clé de prix · jumeau (le même modèle sur l'autre voie) · famille · date · note
```

- Une route **gratuite** `GET /api/ia/catalogue?nature=…` renvoie **toutes** les entrées : `dispo` selon la clé, `usd` et `unite` calculés depuis `pricing.load()`, et `jumeau`.
- Les routes existantes (`/image-models`, `/video-models`, `/music-models`, `/matte-models`, `/voice-models`) gardent leur forme pour la compatibilité des bancs, et **gagnent** les champs `voie`, `cle`, `dispo`, `usd`, `jumeau`.
- Côté pages, un composant partagé `frontend/shared/dz-modeles-ia.js` construit un `<select>` avec un `<optgroup>` par voie (« Avec votre clé OpenAI », « Avec la clé fal », « Local, gratuit »).
  - Chaque option affiche son prix.
  - Une option sans clé reste **visible ET choisissable** (décision de l'utilisateur, 11/10), avec la mention « clé X à ajouter dans Réglages » ; le refus (503, avant le plafond) n'arrive qu'au lancement.
  - Le bundle SPA reçoit le même rendu par une couche `frontend/patches/` rafraîchie avec `scripts/refresh_layer.py`.
- Les appels payants nouveaux suivent la règle de la maison :
  - `Depends(_require_local_depense)` ;
  - les refus d'abord (400, 404, 503 sur clé absente) ;
  - `_garde_cout` si la vidéo a un plafond par requête ;
  - `await _plafond(op, categorie)` ;
  - ensuite seulement l'appel.
  - Chaque route est ajoutée à `PAYANTES` (`backend/tests/test_plafonds_garde.py:30-82`) et chaque `kind` à `pricing.estimate`.

**Tech :** FastAPI, `fal_client.subscribe_async` (via les coutures `_fal_subscribe` déjà en place), JS sans framework pour les labs, couches injectées dans le bundle. Les bancs sont des scripts `backend/tests/test_*.py` lancés un par processus, avec des tests node `frontend/<lab>/qa/*.test.mjs`.

## Lots

| Tâche | Lot | Contenu | Dépend de |
|---|---|---|---|
| t182 | G0 | Catalogue unique « deux voies » + `/api/ia/catalogue` + image : nouveaux modèles fal | — |
| t183 | G1 | Encarts alignés : composant `dz-modeles-ia.js`, couche bundle, fin des listes codées en dur | G0 |
| t184 | G2 | Vidéo : nouveaux i2v, **first-last-frame** (Veo 3.1 fast/standard/lite et autres), deux voies Veo | G0 |
| t185 | G3 | Studio : compositions Veo 3.1 fast + first-last-frame, port `end` compilé | G2 |
| t186 | G4 | Détourage : registre image + vidéo, tous les sites branchés | G0, G1 |
| t187 | G5 | SFX (texte → son et vidéo → son) + musique à jour | G0, G1 |
| t188 | G6 | VFX IA : registre vidéo → vidéo, rail Son & VFX + rack | G0, G1, G4 |
| t189 | G7 | Chapitres : SAM 3 objets 3D → Plateau → plan vidéo first-last-frame | G2, G4 |
| t190 | G8 | Vectorlab : générer et détourer par calque | G1, G4 |
| t191 | G9 | Photolab : générer et détourer par calque | G1, G4 |
| t192 | G10 | Traduction FR/EN : balayage final et banc transverse | G0-G9 |
| t193 | G11 | Guides illustrés FR/EN + fiches didactiques | G0-G10 |

**Règle transversale de traduction :** chaque lot G0 à G9 ajoute **dans le même commit** ses clés `fr` et `en` au catalogue de sa zone (`frontend/shared/i18n/<zone>.json`, voir le tableau de G10), puis lance `python scripts/i18n_assembler.py`. G10 ne fait que le contrôle final et le banc transverse.

## Dépendances et règles

- **Aucun tir réel dans les bancs.** On espionne `fal_client.*`, `_fal_subscribe`, `IP._openai_generate` et `IP._fal_gpt_generate`. On compte tout `httpx.AsyncClient.post` qui sortirait.
- **Avant chaque commit :** lancer tous les bancs qui lisent le bundle (après `python scripts/restaurer_bak_montage.py`) et les bancs de plafonds :

  ```powershell
  .\scripts\run-tests.ps1 -Filter "plafonds|champ_ia|video_models|gpt_image|images_process|i18n|guide"
  ```
- **Mutations après le vert** (mémoire « Mutations : restauration sûre ») : copier les sources **avant**, puis `cmp` **après**. Chaque lot liste ses mutations ; chacune doit faire passer au rouge un banc précis.
- **Preuve à l'écran sur 8799** (backend de preuve), jamais sur 8765, en FR **et** en EN, avant de demander « commit et PR ».
- **Changer un modèle par défaut** demande un tir d'essai réel sous plafond et l'accord explicite de l'utilisateur. Ce plan **n'en change aucun**.

---

## t182 · G0 : catalogue unique « deux voies » et nouveaux modèles d'image

**Fichiers :**
- Créer : `backend/app/services/catalogue_ia.py`
- Modifier :
  - `backend/app/services/image_providers.py` (registre `PROVIDERS` ; nouveau builder générique fal)
  - `backend/app/services/pricing.py` (`DEFAULTS`, `_IMAGE_MODELS`)
  - `backend/app/services/material_store.py:172` (`MODELS`)
  - `backend/app/api/routes.py` : `/image-models` (R:8926) et nouvelle route `/ia/catalogue`
  - `frontend/shared/dz-champ-ia.js:626-642` (`CATALOGUE_IMAGE`), copie octet pour octet dans `frontend/dist/shared/`
  - `frontend/materialforge/materialforge.js:135-146`
- Tester :
  - créer `backend/tests/test_catalogue_ia.py` ;
  - relancer `test_gpt_image_25.py`, `test_image_model_default.py`, `test_champ_ia.py` et `test_cards_face*.py`.

### Nouveaux ids d'image (voie fal)

Schémas relus le 11/10 :

| id app | t2i | edit | Taille envoyée | Prix (`fal_prix.py`) |
|---|---|---|---|---|
| `nano-banana-2.1` | `google/nano-banana-2.1` | `google/nano-banana-2.1/edit` (`image_urls`) | `aspect_ratio` + `resolution:"1K"` | aux jetons, 35,29 $/M en sortie : « prix à mesurer » |
| `flux-3` | `blackforestlabs/flux-3/text-to-image` | `blackforestlabs/flux-3/edit-image` (`image_urls`) | `aspect_ratio` + `resolution:"1k"` | 0,048 $ l'image 1 MP (promo terminée le 08/10) |
| `seedream-5-pro` | `bytedance/seedream/v5/pro/text-to-image` | `bytedance/seedream/v5/pro/edit` (`image_urls`) | `image_size` | 0,0675 $ en edit, t2i « à mesurer » |
| `ideogram-4.5` | `ideogram/v4.5` | `ideogram/v4.5/edit` | `image_size` + `quality:"high"` | à mesurer |
| `qwen-image-3` | `alibaba/qwen-image-3/text-to-image` | `alibaba/qwen-image-3/edit` | `image_size` | à mesurer |
| `recraft-4.1-vecteur` | `fal-ai/recraft/v4.1/text-to-vector` | — | `image_size` | à mesurer (le relevé « 0,70 $ » est douteux : à vérifier sur la page) |

Les deux voies existantes, rendues **visibles** :

| id app | voie | clé | jumeau |
|---|---|---|---|
| `gpt-image-2`, `gpt-image-2.5-flare`, `gpt-image-2.5-sunburst`, `gpt-image-1`, `gpt-image-1-mini` | openai | `OPENAI_API_KEY` | `-fal` quand il existe |
| `gpt-image-2-fal`, `gpt-image-2.5-flare-fal`, `gpt-image-2.5-sunburst-fal` | fal | `FAL_KEY` | l'id sans `-fal` |
| `flux`, `nano-banana`, `nano-banana-pro` | fal | `FAL_KEY` | — |

- [ ] **Étape 1 : relire les schémas et les prix** (ils peuvent avoir bougé depuis le 11/10).

  ```bash
  python ~/.claude/skills/balayage-fournisseurs-fal/scripts/fal_schema.py google/nano-banana-2.1 google/nano-banana-2.1/edit blackforestlabs/flux-3/text-to-image blackforestlabs/flux-3/edit-image bytedance/seedream/v5/pro/text-to-image bytedance/seedream/v5/pro/edit ideogram/v4.5 ideogram/v4.5/edit alibaba/qwen-image-3/text-to-image alibaba/qwen-image-3/edit fal-ai/recraft/v4.1/text-to-vector
  python ~/.claude/skills/balayage-fournisseurs-fal/scripts/fal_prix.py google/nano-banana-2.1 blackforestlabs/flux-3/text-to-image bytedance/seedream/v5/pro/text-to-image ideogram/v4.5 alibaba/qwen-image-3/text-to-image fal-ai/recraft/v4.1/text-to-vector
  ```

  Attendu : les mêmes champs que dans le tableau. Sinon, corriger le tableau `FAL_IMAGES` de l'étape 3 **avant** d'écrire le banc.

- [ ] **Étape 2 : écrire le banc qui échoue**, `backend/tests/test_catalogue_ia.py`. Il reprend l'en-tête du banc `test_gpt_image_25.py` : dossier temporaire, `FAL_KEY` et `OPENAI_API_KEY` simulées, autres clés retirées.

  ```python
  """t182 / G0 — catalogue unique « deux voies ».

  [0] catalogue_ia.lister("image") rend TOUTES les entrées image, chacune avec
      voie, cle, dispo, usd (float), unite, jumeau ; les jumeaux sont symétriques ;
  [1] dispo suit la clé : sans OPENAI_API_KEY, les ids openai sont dispo=False
      mais PRÉSENTS ; sans FAL_KEY, les ids fal idem ;
  [2] les nouveaux ids fal (nano-banana-2.1, flux-3, seedream-5-pro,
      ideogram-4.5, qwen-image-3, recraft-4.1-vecteur) sont dans PROVIDERS,
      pricing._IMAGE_MODELS, material_store.MODELS et CATALOGUE_IMAGE ;
      gpt-image-1-mini est dans PROVIDERS ;
  [3] build_fal_image_request vise le bon endpoint et la bonne forme de taille
      (aspect_ratio / image_size / resolution) pour t2i et edit ;
  [4] /images/generate avec un nouvel id part par IP._fal_image_generate
      (espion), jamais par OpenAI ni FLUX ;
  [5] /image-models garde `models` filtré (compat) et ajoute `tous` (toutes
      les entrées, champs de [0]) ; GET /ia/catalogue?nature=image idem ;
      nature inconnue -> 400 ;
  [6] un prix inconnu donne usd=0.0 et `note` contenant « prix à mesurer ».
  Run: & $PY tests/test_catalogue_ia.py   (depuis backend/)
  """
  import asyncio, json, os, re, subprocess, sys, tempfile
  from pathlib import Path
  sys.stdout.reconfigure(encoding="utf-8")
  TMP = tempfile.mkdtemp(prefix="catia_")
  os.environ.update({
      "DEEPOTUS_DATA_DIR": TMP,
      "DATABASE_URL": "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/"),
      "IMAGES_FOLDER": TMP + "/images", "OUTPUTS_FOLDER": TMP + "/outputs",
      "FAL_KEY": "test-key", "OPENAI_API_KEY": "test-oa"})
  for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY"):
      os.environ.pop(_k, None)
  Path(TMP, "images").mkdir(parents=True, exist_ok=True)
  Path(TMP, "outputs").mkdir(parents=True, exist_ok=True)
  ICI = Path(__file__).resolve().parent
  sys.path.insert(0, str(ICI.parent))

  OK, KO = 0, 0
  def check(lbl, cond, detail=""):
      global OK, KO
      if cond: OK += 1; print("  ok  ", lbl)
      else: KO += 1; print("  FAIL", lbl, detail)

  from app.config import settings
  from app.services import catalogue_ia as CI, image_providers as IP, pricing as P, material_store as MS

  NOUVEAUX = ["nano-banana-2.1", "flux-3", "seedream-5-pro", "ideogram-4.5", "qwen-image-3", "recraft-4.1-vecteur"]

  print("[0] lister('image')")
  img = CI.lister("image")
  ids = {e["id"] for e in img}
  for e in img:
      check(f"{e['id']} a ses champs", all(k in e for k in ("voie", "cle", "dispo", "usd", "unite", "jumeau", "label")), e)
  for e in img:
      if e["jumeau"]:
          j = next((x for x in img if x["id"] == e["jumeau"]), None)
          check(f"jumeau symétrique {e['id']}", j is not None and j["jumeau"] == e["id"] and j["voie"] != e["voie"])

  print("[1] dispo suit la clé")
  settings.OPENAI_API_KEY = ""
  img2 = {e["id"]: e for e in CI.lister("image")}
  check("gpt-image-2 présent sans clé", "gpt-image-2" in img2)
  check("gpt-image-2 dispo=False sans clé", img2["gpt-image-2"]["dispo"] is False)
  check("gpt-image-2-fal reste dispo", img2["gpt-image-2-fal"]["dispo"] is True)
  settings.OPENAI_API_KEY = "test-oa"

  print("[2] registres alignés")
  cat_js = (ICI.parent.parent / "frontend/shared/dz-champ-ia.js").read_text(encoding="utf-8")
  for i in NOUVEAUX:
      check(f"{i} dans PROVIDERS", i in IP.PROVIDERS)
      check(f"{i} dans _IMAGE_MODELS", i in P._IMAGE_MODELS)
      check(f"{i} dans material_store", i in MS.MODELS)
      check(f"{i} dans CATALOGUE_IMAGE", f'"{i}"' in cat_js)
      check(f"{i} dans lister", i in ids)
  check("gpt-image-1-mini dans PROVIDERS", "gpt-image-1-mini" in IP.PROVIDERS)

  print("[3] requêtes fal pures")
  ep, a = IP.build_fal_image_request("flux-3", "un chat", "portrait_16_9", [])
  check("flux-3 t2i endpoint", ep == "blackforestlabs/flux-3/text-to-image", ep)
  check("flux-3 aspect 9:16 + 1k", a.get("aspect_ratio") == "9:16" and a.get("resolution") == "1k", a)
  ep, a = IP.build_fal_image_request("flux-3", "un chat", "square", ["https://x/a.png"])
  check("flux-3 edit endpoint", ep == "blackforestlabs/flux-3/edit-image" and a.get("image_urls") == ["https://x/a.png"], (ep, a))
  ep, a = IP.build_fal_image_request("seedream-5-pro", "x", "landscape_16_9", [])
  check("seedream image_size", ep.endswith("/text-to-image") and a.get("image_size") == "landscape_16_9", (ep, a))
  ep, a = IP.build_fal_image_request("nano-banana-2.1", "x", "square_hd", [])
  check("nano 2.1 aspect 1:1", ep == "google/nano-banana-2.1" and a.get("aspect_ratio") == "1:1", (ep, a))
  try:
      IP.build_fal_image_request("recraft-4.1-vecteur", "x", "square", ["https://x/a.png"])
      check("recraft refuse l'edit", False)
  except ValueError:
      check("recraft refuse l'edit", True)

  print("[4]-[6] routes")
  from fastapi.testclient import TestClient
  from app.main import app
  appels = []
  async def espion(model, prompt, size, n, image_paths=None, **kw):
      appels.append(model); return ["gen_test.png"]
  IP._fal_image_generate = espion
  async def interdit(*a, **k): raise AssertionError("voie interdite")
  IP._openai_generate = interdit
  with TestClient(app, client=("127.0.0.1", 50000)) as c:
      r = c.post("/api/images/generate", json={"prompt": "chat", "n": 1, "model": "flux-3"},
                 headers={"X-DZ-Plafond": "confirme"})
      check("generate flux-3 200", r.status_code == 200, r.text[:200])
      check("passé par _fal_image_generate", appels == ["flux-3"], appels)
      r = c.get("/api/image-models").json()
      check("models filtré conservé", all(m.get("id") for m in r["models"]))
      check("tous présent", len(r.get("tous", [])) >= len(r["models"]))
      r = c.get("/api/ia/catalogue", params={"nature": "image"})
      check("catalogue image 200", r.status_code == 200 and len(r.json()["modeles"]) == len(img))
      check("nature inconnue 400", c.get("/api/ia/catalogue", params={"nature": "zzz"}).status_code == 400)
  e = next(x for x in CI.lister("image") if x["id"] == "ideogram-4.5")
  check("prix inconnu = 0.0 + à mesurer", e["usd"] == 0.0 and "prix à mesurer" in (e.get("note") or ""), e)

  # [2b] node --check sur la copie et identité octets
  for f in ("frontend/shared/dz-champ-ia.js", "frontend/materialforge/materialforge.js"):
      r = subprocess.run(["node", "--check", str(ICI.parent.parent / f)], capture_output=True, text=True)
      check(f"node --check {f}", r.returncode == 0, r.stderr[:200])
  a = (ICI.parent.parent / "frontend/shared/dz-champ-ia.js").read_bytes()
  b = (ICI.parent.parent / "frontend/dist/shared/dz-champ-ia.js").read_bytes()
  check("copie dist octet pour octet", a == b)

  print(f"\n{OK} ok, {KO} fail"); sys.exit(1 if KO else 0)
  ```

- [ ] **Étape 3 : le lancer et le voir échouer.** Depuis `backend/` : `& $PY tests/test_catalogue_ia.py`. Attendu : `ModuleNotFoundError: app.services.catalogue_ia`.

- [ ] **Étape 4 : builder générique fal** dans `image_providers.py`, à placer sous `_FAL_GPT`.

  ```python
  # Modèles d'image fal « simples » (schémas relus le 11/10/2026 avec fal_schema.py).
  # taille : "aspect" -> aspect_ratio (+ resolution) ; "image_size" -> image_size tel quel.
  FAL_IMAGES = {
      "nano-banana-2.1": {"t2i": "google/nano-banana-2.1", "edit": "google/nano-banana-2.1/edit",
                          "taille": "aspect", "resolution": "1K"},
      "flux-3": {"t2i": "blackforestlabs/flux-3/text-to-image", "edit": "blackforestlabs/flux-3/edit-image",
                 "taille": "aspect", "resolution": "1k"},
      "seedream-5-pro": {"t2i": "bytedance/seedream/v5/pro/text-to-image",
                         "edit": "bytedance/seedream/v5/pro/edit", "taille": "image_size"},
      "ideogram-4.5": {"t2i": "ideogram/v4.5", "edit": "ideogram/v4.5/edit", "taille": "image_size",
                       "extra": {"quality": "high"}},
      "qwen-image-3": {"t2i": "alibaba/qwen-image-3/text-to-image", "edit": "alibaba/qwen-image-3/edit",
                       "taille": "image_size"},
      "recraft-4.1-vecteur": {"t2i": "fal-ai/recraft/v4.1/text-to-vector", "edit": None,
                              "taille": "image_size", "svg": True},
  }


  def build_fal_image_request(model: str, prompt: str, size: str, image_urls: list[str],
                              n: int = 1) -> tuple[str, dict]:
      """(endpoint, arguments) pour un id de FAL_IMAGES. Pur : aucun réseau."""
      m = FAL_IMAGES[model]
      edit = bool(image_urls)
      if edit and not m["edit"]:
          raise ValueError(f"{model} : pas de retouche (texte → image seulement).")
      args: dict = {"prompt": prompt}
      if m["taille"] == "aspect":
          args["aspect_ratio"] = _BANANA_ASPECT.get(size, "1:1")
          args["resolution"] = m["resolution"]
      else:
          args["image_size"] = size if size in _BANANA_ASPECT else "square_hd"
      if n > 1 and not m.get("svg"):
          args["num_images"] = int(n)
      args.update(m.get("extra", {}))
      if edit:
          args["image_urls"] = list(image_urls)
      return (m["edit"] if edit else m["t2i"]), args


  async def _fal_image_generate(model, prompt, size, n, image_paths=None, **kw) -> list[str]:  # couture
      import fal_client
      urls = [await fal_client.upload_file_async(p) for p in (image_paths or [])]
      ep, args = build_fal_image_request(model, prompt, size, urls, n)
      res = await fal_client.subscribe_async(ep, arguments=args)
      imgs = res.get("images") or ([res["image"]] if res.get("image") else [])
      return await _download([i["url"] for i in imgs if i.get("url")])
  ```

  Ajouter les entrées dans `PROVIDERS` (`"needs": "FAL_KEY", "seeds": False`, libellé « … (via fal) ») et `gpt-image-1-mini` (`"needs": "OPENAI_API_KEY"`). Dans `generate()`, router **avant** le cas nano-banana :

  ```python
      if model in FAL_IMAGES:
          return await _fal_image_generate(model, prompt, size, n, image_paths=image_paths)
  ```

  `via_facade()` rend déjà `True` pour tout id `FAL_KEY` hors `flux` ; rien à changer.

- [ ] **Étape 5 : prix.** Ajouter à `pricing.DEFAULTS` les clés `nano_banana_21_usd: 0.0`, `flux3_usd: 0.048`, `seedream5_pro_usd: 0.0675`, `ideogram45_usd: 0.0`, `qwen_image3_usd: 0.0`, `recraft41_vecteur_usd: 0.0`, puis les lignes correspondantes de `_IMAGE_MODELS` (`(libellé, "fal", clé)`). Dans `material_store.MODELS`, ajouter les mêmes ids ; dans `materialforge.js`, ajouter les mêmes ids dans `MODEL_COST` (crédits = usd × 100, arrondi) et `MODEL_SEC` (6 s).

- [ ] **Étape 6 : `catalogue_ia.py`** (nature `image` seulement dans ce lot ; les lots suivants ajoutent leurs natures).

  ```python
  """Catalogue unique des modèles appelables, par NATURE d'appel, avec leurs
  deux voies (clé individuelle / clé fal). Source des sélecteurs de l'app.
  Gratuit à lire ; ne fait aucun appel réseau."""
  from app.config import settings
  from app.services import pricing as P

  CLES = {"fal": "FAL_KEY", "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY",
          "elevenlabs": "ELEVENLABS_API_KEY", "meshy": "MESHY_API_KEY",
          "heygen": "HEYGEN_API_KEY", "local": None}
  NATURES = ("image",)            # étendu par G2 (video_i2v, video_fl), G4, G5, G6, G7

  _SOURCES = {}                   # nature -> fonction () -> list[dict] brutes


  def source(nature):
      def deco(fn):
          _SOURCES[nature] = fn
          return fn
      return deco


  def _dispo(voie: str) -> bool:
      cle = CLES.get(voie)
      return True if cle is None else bool(str(getattr(settings, cle, "") or "").strip())


  @source("image")
  def _images() -> list[dict]:
      from app.services import image_providers as IP
      p = P.load()
      out = []
      for mid, (label, voie, cle_prix) in P._IMAGE_MODELS.items():
          usd = float(p.get(cle_prix, P.DEFAULTS.get(cle_prix, 0.0)) or 0.0)
          if mid in IP._FAL_GPT:
              jumeau = IP._FAL_GPT[mid]
          else:
              jumeau = next((k for k, v in IP._FAL_GPT.items() if v == mid), None)
          out.append({"id": mid, "label": label, "voie": voie, "usd": usd, "unite": "image",
                      "jumeau": jumeau,
                      "note": "" if usd else "prix à mesurer",
                      "edit": mid not in ("recraft-4.1-vecteur",)})
      return out


  def lister(nature: str) -> list[dict]:
      if nature not in _SOURCES:
          raise KeyError(nature)
      out = []
      for e in _SOURCES[nature]():
          e = dict(e)
          e["nature"] = nature
          e["cle"] = CLES.get(e["voie"])
          e["dispo"] = _dispo(e["voie"])
          out.append(e)
      return out
  ```

- [ ] **Étape 7 : routes.** Dans `routes.py`, juste après `list_image_models` :

  ```python
  @router.get("/ia/catalogue")
  async def ia_catalogue(nature: str = ""):
      """Tous les modèles d'une nature d'appel, disponibles OU NON, avec voie,
      clé, prix et jumeau. Lecture seule, gratuite."""
      from app.services import catalogue_ia as CI
      try:
          return {"nature": nature, "modeles": CI.lister(nature)}
      except KeyError:
          raise HTTPException(400, f"nature inconnue : {nature or '(vide)'} — "
                                   f"{', '.join(sorted(CI._SOURCES))}.")
  ```

  Dans `list_image_models`, ajouter à la réponse `"tous": CI.lister("image")` et ajouter à chaque entrée de `out` les champs `voie`, `cle` et `usd`, lus dans la même liste. `models` reste filtré : `test_gpt_image_25` [2] y tient.

- [ ] **Étape 8 : `CATALOGUE_IMAGE`.** Ajouter les six ids avec `"FAL_KEY"`, recopier le fichier dans `frontend/dist/shared/` (octet pour octet), puis lancer `node --check`.

- [ ] **Étape 9 : relancer le banc G0 puis les voisins.**

  ```powershell
  & $PY tests/test_catalogue_ia.py; & $PY tests/test_gpt_image_25.py; & $PY tests/test_image_model_default.py; & $PY tests/test_champ_ia.py
  ```

  Attendu : `N ok, 0 fail` pour chacun.

- [ ] **Étape 10 : mutations.** Chacune doit faire passer au rouge le banc indiqué.
  1. Retirer `flux-3` de `CATALOGUE_IMAGE` → [2].
  2. Router `FAL_IMAGES` après nano-banana → [4].
  3. Rendre `jumeau` non symétrique → [0].
  4. Filtrer `tous` par la clé → [5].

  Restaurer, puis vérifier avec `cmp`.

- [ ] **Étape 11 : traduction.** Ajouter les nouveaux libellés visibles (« via fal », « prix à mesurer ») à `frontend/shared/i18n/commun.json` (clés `ia.voie.fal`, `ia.voie.openai`, `ia.voie.gemini`, `ia.voie.elevenlabs`, `ia.voie.meshy`, `ia.voie.local`, `ia.prix.a_mesurer`, `ia.cle.absente` = « clé {cle} absente » / "{cle} key missing"), puis lancer `python scripts/i18n_assembler.py`.

- [ ] **Étape 12 : commit.**

  ```bash
  git add backend/app/services/catalogue_ia.py backend/app/services/image_providers.py backend/app/services/pricing.py backend/app/services/material_store.py backend/app/api/routes.py frontend/shared/dz-champ-ia.js frontend/dist/shared/dz-champ-ia.js frontend/materialforge/materialforge.js frontend/shared/i18n/commun.json frontend/shared/dz-i18n-dico.js frontend/dist/shared/dz-i18n-dico.js backend/tests/test_catalogue_ia.py
  git commit -m "génération IA G0 : catalogue unique deux voies + 6 modèles d'image fal (t182)"
  ```

---

## t183 · G1 : encarts alignés, chacun montre ses deux voies et ses prix

**But :** partout où l'on choisit un modèle, la liste vient du catalogue, groupée par voie, avec le prix de chaque option. Les miroirs codés en dur disparaissent.

**Fichiers :**
- Créer :
  - `frontend/shared/dz-modeles-ia.js` (+ copie dans `frontend/dist/shared/`)
  - `frontend/shared/qa/modeles_ia.test.mjs`
  - `backend/tests/test_encarts_ia.py`
- Modifier :
  - `frontend/shared/dz-champ-ia.js` : le chargeur `image` lit `/api/ia/catalogue?nature=image` ; la liste affiche des groupes par voie.
  - `frontend/materialforge/materialforge.js:554-566` : `#model` construit par `DzModelesIA.select`.
  - `frontend/atelier/atelier.js:1383-1394` : `#daProvider` ; `:953-957` : l'image de production prend son prix dans le catalogue.
  - `frontend/spritelab/spritelab.js:1036-1065` : ajoute un sélecteur ; aujourd'hui, aucun modèle n'est envoyé.
  - `frontend/vectorlab/js/mod-image.js` : traité en G8, pas ici.
  - Bundle, couche `montage` (`frontend/patches/montage.js`) : `DzImgModelSel`, `DzVideoModelSel` et `DzImageModel` affichent des `<optgroup>` par voie et le prix, et lisent `tous` au lieu de `models`.
  - Bundle : le panneau Game Assets 3D (`var ENG=[{value:"tripo"`) lit `/api/assets3d/engines` (R:903) au lieu de sa liste à prix écrits. **Patcher de queue** `scripts/patch_bundle_encartsia.py`, avec un `MARKER_ATTENDU` amont comme `patch_bundle_dzcout.py:46-50`, et son inverse dans `avant_<maillon>` (mémoire « tout maillon de queue ajoute son inverse »).
  - `frontend/patches/son-vfx-montage.js:127-134` : `SVM_GENS` ne porte plus de prix ; le rail lit `/api/ia/catalogue` (musique et SFX, natures ajoutées en G5) ; **supprimer « gratuit » sur le SFX**.

- [ ] **Étape 1 : écrire le test node du composant**, `frontend/shared/qa/modeles_ia.test.mjs`. Il charge le module dans un `vm`, avec un DOM minimal comme `test_champ_ia.py`.

  ```js
  import assert from "node:assert/strict";
  import { readFileSync } from "node:fs";
  import vm from "node:vm";
  const src = readFileSync(new URL("../dz-modeles-ia.js", import.meta.url), "utf8");
  const ctx = { window: {}, dzT: (k, v) => k + (v ? JSON.stringify(v) : "") };
  vm.createContext(ctx); vm.runInContext(src, ctx);
  const M = ctx.window.DzModelesIA;
  const mods = [
    { id: "gpt-image-2", label: "GPT Image 2", voie: "openai", cle: "OPENAI_API_KEY", dispo: false, usd: 0.12, unite: "image", jumeau: "gpt-image-2-fal" },
    { id: "gpt-image-2-fal", label: "GPT Image 2 (via fal)", voie: "fal", cle: "FAL_KEY", dispo: true, usd: 0.145, unite: "image", jumeau: "gpt-image-2" },
    { id: "ideogram-4.5", label: "Ideogram 4.5", voie: "fal", cle: "FAL_KEY", dispo: true, usd: 0, unite: "image", jumeau: null, note: "prix à mesurer" },
  ];
  const g = M.grouper(mods);
  assert.deepEqual(g.map(x => x.voie), ["fal", "openai"]);            // fal d'abord, puis l'ordre CLES
  assert.equal(g[1].options[0].desactive, false);                     // clé absente : visible ET choisissable (décision 11/10)
  assert.match(g[1].options[0].texte, /ia\.cle\.a_ajouter/);
  assert.match(g[0].options[0].texte, /0,145 \$/);                    // prix au format FR
  assert.match(g[0].options[1].texte, /ia\.prix\.a_mesurer/);
  assert.equal(M.prix(0.0475, "s"), "0,048 $/s");
  console.log("modeles_ia ok");
  ```

- [ ] **Étape 2 : le lancer et le voir échouer.** `node frontend/shared/qa/modeles_ia.test.mjs`. Attendu : `ENOENT … dz-modeles-ia.js`.

- [ ] **Étape 3 : écrire `frontend/shared/dz-modeles-ia.js`.**

  ```js
  /* DzModelesIA — sélecteur de modèle partagé : un <optgroup> par voie
     (clé individuelle / clé fal / local), prix sur chaque option, options
     sans clé VISIBLES et CHOISISSABLES (jamais disabled, décision 11/10). Source : GET /api/ia/catalogue?nature=… */
  (function (W) {
    const T = (k, v) => (W.dzT ? W.dzT(k, v) : (typeof dzT === "function" ? dzT(k, v) : k));
    const ORDRE = ["fal", "openai", "gemini", "elevenlabs", "meshy", "heygen", "local"];
    function prix(usd, unite) {
      if (!usd) return T("ia.prix.a_mesurer");
      const s = (Math.round(usd * 1000) / 1000).toString().replace(".", ",");
      return s + " $" + (unite === "s" ? "/s" : unite === "min" ? "/min" : "");
    }
    function grouper(mods) {
      const par = {};
      for (const m of mods) (par[m.voie] = par[m.voie] || []).push(m);
      return ORDRE.filter(v => par[v]).map(v => ({
        voie: v, titre: T("ia.voie." + v),
        options: par[v].map(m => ({
          id: m.id, desactive: false,            // jamais désactivé : décision de l'utilisateur 11/10
          texte: m.label + " · " + (m.usd ? prix(m.usd, m.unite) : T("ia.prix.a_mesurer")) +
                 (m.dispo ? "" : " · " + T("ia.cle.a_ajouter", { cle: m.cle })),
        })),
      }));
    }
    async function charger(nature) {
      const r = await fetch("/api/ia/catalogue?nature=" + encodeURIComponent(nature));
      if (!r.ok) throw new Error("catalogue " + nature + " : " + r.status);
      return (await r.json()).modeles;
    }
    async function select(el, nature, opts = {}) {
      const mods = await charger(nature);
      el.textContent = "";
      for (const g of grouper(mods)) {
        const og = el.ownerDocument.createElement("optgroup"); og.label = g.titre;
        for (const o of g.options) {
          const op = el.ownerDocument.createElement("option");
          op.value = o.id; op.textContent = o.texte; op.disabled = o.desactive;
          og.appendChild(op);
        }
        el.appendChild(og);
      }
      const v = opts.valeur && mods.find(m => m.id === opts.valeur && m.dispo) ? opts.valeur
              : (mods.find(m => m.dispo) || {}).id || "";
      el.value = v;
      if (opts.onChange) el.addEventListener("change", () => opts.onChange(el.value, mods.find(m => m.id === el.value)));
      return mods;
    }
    W.DzModelesIA = { grouper, prix, charger, select, ORDRE };
  })(typeof window !== "undefined" ? window : globalThis);
  ```

  Ajouter `<script src="/shared/dz-modeles-ia.js"></script>` avant le code du lab dans `frontend/{atelier,materialforge,spritelab,vectorlab,photolab}/index.html`, puis copier le fichier dans `frontend/dist/shared/`.

- [ ] **Étape 4 : relancer le test node.** Attendu : `modeles_ia ok`.

- [ ] **Étape 5 : `backend/tests/test_encarts_ia.py`, le recensement des encarts.** Il lit les sources et le bundle.

  ```python
  """t183 / G1 — plus aucune liste de modèles codée en dur dans un encart.
  [0] chaque page de lab qui génère charge /shared/dz-modeles-ia.js ;
  [1] materialforge.js n'a plus de MODEL_COST littéral par id (il lit usd) ;
  [2] le bundle n'a plus `var ENG=[{value:"tripo"` ni de « ~$ » dans les libellés 3D ;
  [3] son-vfx-montage.js : SVM_GENS ne contient plus « gratuit » ni « ~$0.10 » ;
  [4] dz-champ-ia.js lit /api/ia/catalogue et rend des groupes (optgroup ou en-têtes de voie) ;
  [5] copies dist octet pour octet (dz-modeles-ia.js, dz-champ-ia.js)."""
  import re, sys
  from pathlib import Path
  sys.stdout.reconfigure(encoding="utf-8")
  R = Path(__file__).resolve().parents[2]
  OK = KO = 0
  def check(l, c, d=""):
      global OK, KO
      OK, KO = (OK + 1, KO) if c else (OK, KO + 1); print("  ok  " if c else "  FAIL", l, "" if c else d)
  for lab in ("atelier", "materialforge", "spritelab", "vectorlab", "photolab"):
      html = (R / f"frontend/{lab}/index.html").read_text(encoding="utf-8")
      check(f"{lab} charge dz-modeles-ia", "/shared/dz-modeles-ia.js" in html)
  mf = (R / "frontend/materialforge/materialforge.js").read_text(encoding="utf-8")
  check("materialforge sans MODEL_COST littéral", not re.search(r"MODEL_COST\s*=\s*\{", mf))
  bundle = next((R / "frontend/dist/assets").glob("index-*.js")).read_text(encoding="utf-8")
  check("bundle sans ENG codé en dur", 'var ENG=[{value:"tripo"' not in bundle)
  svm = (R / "frontend/patches/son-vfx-montage.js").read_text(encoding="utf-8")
  bloc = svm[svm.index("SVM_GENS"): svm.index("SVM_GENS") + 1500]
  check("SVM_GENS sans « gratuit »", "gratuit" not in bloc)
  check("SVM_GENS sans ~$0.10", "~$0.10" not in bloc)
  ch = (R / "frontend/shared/dz-champ-ia.js").read_text(encoding="utf-8")
  check("champ-ia lit le catalogue", "/api/ia/catalogue" in ch)
  for f in ("dz-modeles-ia.js", "dz-champ-ia.js"):
      check(f"dist {f} identique", (R / "frontend/shared" / f).read_bytes() == (R / "frontend/dist/shared" / f).read_bytes())
  print(f"\n{OK} ok, {KO} fail"); sys.exit(1 if KO else 0)
  ```

- [ ] **Étape 6 : le lancer et le voir échouer**, puis brancher chaque encart de la liste « Fichiers ».
  - Pour le bundle : éditer `frontend/patches/montage.js`, puis lancer `python scripts/refresh_layer.py --layer montage --check` puis `python scripts/refresh_layer.py --layer montage`.
  - Créer `scripts/patch_bundle_encartsia.py` pour `ENG`.
  - Éditer `son-vfx-montage.js`, puis lancer `refresh_layer.py --layer sonvfx`.

- [ ] **Étape 7 : bancs voisins à garder verts.** `test_champ_ia.py`, `test_p1_champ_ia_ecarts.py`, `test_defauts_modeles.py`, `test_cout_pastille.py`, `test_son_vfx_socle.py`, `test_gpt_image_25.py` [6] (son assertion sur `MODEL_COST` doit être **mise à jour** pour lire `usd`), et le compteur figé `useState` 731 (mémoire t141).

- [ ] **Étape 8 : mutations.**
  1. Remettre « gratuit » dans `SVM_GENS` → [3].
  2. Retirer le `<script>` d'un lab → [0].
  3. `grouper` qui filtre OU désactive les options sans clé → le test node passe au rouge.

- [ ] **Étape 9 : traduction et commit.** Clés `ia.voie.*` déjà posées en G0. Ajouter `ia.choisir_modele` (« Modèle » / "Model") dans `commun.json`. Commit : « génération IA G1 : encarts alignés sur le catalogue (t183) ».

---

## t184 · G2 : vidéo, nouveaux modèles et first-last-frame

**Fichiers :**
- Modifier :
  - `backend/app/services/fal_service.py:69-154` : `VIDEO_MODELS` ; `build_fal_args` à `:209-270`.
  - `backend/app/services/pricing.py:76-94` : `video_usd_per_s`.
  - `backend/app/services/catalogue_ia.py` : natures `video_i2v` et `video_fl`.
- Tester : créer `backend/tests/test_video_fl.py` ; relancer `test_video_models.py`, `test_seedance_garde.py`, `test_p1_garde_cout_video.py`.

**Nouveaux champs du registre :**
- `image_arg` (défaut `"image_url"`) ;
- `end_arg` (défaut `"end_image_url"`) ;
- `endpoint_fl` : un endpoint **séparé** quand il y a une image de fin (cas Veo) ;
- `fl_args` : `("first_frame_url", "last_frame_url")` pour Veo ;
- `duree_suffixe` (`"s"` pour Veo, qui attend `"8s"`).

**Entrées à ajouter**, schémas du 11/10 et prix de `fal_prix.py` :

| id | endpoint | image de fin | durées | résolutions | $/s |
|---|---|---|---|---|---|
| `veo-3.1-fast-fal` (existant) | `fal-ai/veo3.1/fast/image-to-video` + `endpoint_fl` `fal-ai/veo3.1/fast/first-last-frame-to-video` | **oui** (via `endpoint_fl`) | 4, 6, 8 | 720p, 1080p | 0,10 (0,15 avec son) |
| `veo-3.1-fal` | `fal-ai/veo3.1/image-to-video` + `endpoint_fl` `fal-ai/veo3.1/first-last-frame-to-video` | oui | 4, 6, 8 | 720p, 1080p | 0,20 (0,40 avec son) |
| `veo-3.1-lite-fal` | `fal-ai/veo3.1/lite/image-to-video` + `endpoint_fl` `fal-ai/veo3.1/lite/first-last-frame-to-video` | oui | 4, 6, 8 | 720p, 1080p | à mesurer |
| `h3-max` | `minimax/h3-max/image-to-video` (`prompt_expansion_mode` requis : `"auto"` à relire au schéma) | `end_image_url` | 5-10 | 480P, 768P, 1080P | 0,05 / 0,08 / 0,16 (promo −40 % : 0,03 / 0,048 / 0,096) |
| `wan-3.0` | `alibaba/wan-3.0/image-to-video`, `image_arg="start_image_url"` | `end_image_url` | 2-15 (à relire) | 480p, 720p, 1080p | 0,05 / 0,10 / 0,20 |
| `gemini-omni-flash` | `google/gemini-omni-flash/v1.1/image-to-video` | `end_image_url` | à relire | 720p, 1080p | 0,10 / 0,15 |
| `ltx-2.5-fast` | `lightricks/ltx-2.5/image-to-video/fast` | `end_image_url` | 6-20, pas de 2 | 1080p, 1440p, 2160p, 720p | 0,09 (720p), 0,13 (1080p) |
| `kling-v3-turbo-pro` | `fal-ai/kling-video/v3/turbo/pro/image-to-video` | non | 3-15 (chaînes) | — | 0,14 |

Les entrées Google natives `veo-3.1-google`, `veo-3.1-fast-google` et `veo-3.1-lite-google` (clé `GEMINI_API_KEY`) **restent**. Dans le catalogue, elles deviennent les jumeaux de `veo-3.1-fal`, `veo-3.1-fast-fal` et `veo-3.1-lite-fal` : c'est la double voie demandée pour Veo.

- [ ] **Étape 1 : relire les schémas.**

  ```bash
  python ~/.claude/skills/balayage-fournisseurs-fal/scripts/fal_schema.py minimax/h3-max/image-to-video alibaba/wan-3.0/image-to-video google/gemini-omni-flash/v1.1/image-to-video lightricks/ltx-2.5/image-to-video/fast fal-ai/kling-video/v3/turbo/pro/image-to-video fal-ai/veo3.1/image-to-video fal-ai/veo3.1/first-last-frame-to-video fal-ai/veo3.1/fast/first-last-frame-to-video fal-ai/veo3.1/lite/image-to-video fal-ai/veo3.1/lite/first-last-frame-to-video
  ```

  Recopier les enums de `duration` et `resolution` dans les entrées.

- [ ] **Étape 2 : banc qui échoue**, `backend/tests/test_video_fl.py` (en-tête identique à G0).

  ```python
  from app.services import fal_service as F, catalogue_ia as CI
  print("[0] Veo first-last-frame passe par l'endpoint FL avec first/last")
  ep, a = F.build_fal_args("veo-3.1-fast-fal", "https://x/a.png", "travelling", duration=8,
                           resolution="720p", end_image_url="https://x/b.png")
  check("endpoint FL", ep == "fal-ai/veo3.1/fast/first-last-frame-to-video", ep)
  check("first/last", a.get("first_frame_url") == "https://x/a.png" and a.get("last_frame_url") == "https://x/b.png", a)
  check("pas d'image_url sur FL", "image_url" not in a, a)
  check("durée '8s'", a.get("duration") == "8s", a)
  ep, a = F.build_fal_args("veo-3.1-fast-fal", "https://x/a.png", "x", duration=8, resolution="720p")
  check("sans fin -> i2v", ep == "fal-ai/veo3.1/fast/image-to-video" and a.get("image_url") == "https://x/a.png")
  print("[1] Wan 3.0 : start_image_url")
  ep, a = F.build_fal_args("wan-3.0", "https://x/a.png", "x", duration=5, resolution="720p",
                           end_image_url="https://x/b.png")
  check("wan start/end", a.get("start_image_url") == "https://x/a.png" and a.get("end_image_url") == "https://x/b.png" and "image_url" not in a, a)
  print("[2] Kling turbo refuse la fin proprement")
  try:
      F.build_fal_args("kling-v3-turbo-pro", "https://x/a.png", "x", duration=5, end_image_url="https://x/b.png")
      check("refus fin", False)
  except ValueError as e:
      check("refus fin", "image de fin" in str(e) or "end" in str(e).lower(), str(e))
  print("[3] catalogue : video_fl = seulement les modèles qui acceptent une fin ; jumeaux Veo")
  fl = {e["id"] for e in CI.lister("video_fl")}
  check("veo fast FL", "veo-3.1-fast-fal" in fl and "veo-3.1-fal" in fl)
  check("kling turbo exclu", "kling-v3-turbo-pro" not in fl)
  i2v = {e["id"]: e for e in CI.lister("video_i2v")}
  check("jumeau Veo google <-> fal", i2v["veo-3.1-fast-fal"]["jumeau"] == "veo-3.1-fast-google")
  check("veo google voie gemini", i2v["veo-3.1-fast-google"]["voie"] == "gemini")
  print("[4] prix au registre")
  for mid in ("h3-max", "wan-3.0", "gemini-omni-flash", "ltx-2.5-fast", "kling-v3-turbo-pro", "veo-3.1-fal"):
      check(f"{mid} dans video_usd_per_s", mid in P.DEFAULTS["video_usd_per_s"])
  ```

- [ ] **Étape 3 : implémenter.** Dans `build_fal_args`, après le choix du modèle `m` :

  ```python
      if end_image_url and not (m.get("end_image") or m.get("endpoint_fl")):
          raise ValueError(f"{m['label']} : pas d'image de fin (first-last-frame) sur ce modèle.")
      if end_image_url and m.get("endpoint_fl"):
          endpoint = m["endpoint_fl"]
          k1, k2 = m.get("fl_args", ("first_frame_url", "last_frame_url"))
          args = {"prompt": prompt, k1: image_url, k2: end_image_url}
      else:
          endpoint = m["endpoint"]
          args = {"prompt": prompt, m.get("image_arg", "image_url"): image_url}
          if end_image_url:
              args[m.get("end_arg", "end_image_url")] = end_image_url
      if duration is not None:
          args["duration"] = f"{int(duration)}{m['duree_suffixe']}" if m.get("duree_suffixe") else int(duration)
  ```

  Ce bloc **remplace** la construction actuelle de `args` (`:250-266`). Le cas Seedance v1 lite/pro (`:250`) reste à part, en tête, inchangé. Les entrées Veo reçoivent `"duree_suffixe": "s"`. Renseigner `"end_image": True` sur les nouvelles entrées qui ont `end_arg`.

  Dans `catalogue_ia.py`, ajouter `NATURES += ("video_i2v", "video_fl")` et deux sources :
  - elles lisent `VIDEO_MODELS` ;
  - `voie` = `"gemini"` si `provider == "google"`, sinon `"fal"` ;
  - `usd` = `pricing.video_rate(id, "720p")` ou `"*"`, `unite` = `"s"` ;
  - jumeaux tirés de `{"veo-3.1-fast-fal": "veo-3.1-fast-google", "veo-3.1-fal": "veo-3.1-google", "veo-3.1-lite-fal": "veo-3.1-lite-google"}` et de l'inverse ;
  - `video_fl` filtre `end_image or endpoint_fl`.

  `/api/video-models` (R:8888) ajoute `voie`, `cle`, `jumeau` et `fl: bool` à chaque entrée.

- [ ] **Étape 4 : bancs.** `test_video_fl.py` et `test_video_models.py` (sa liste d'ids attendus **gagne** les nouveaux ids : mettre la liste à jour **dans le même commit**). Puis `test_seedance_garde.py` et `test_p1_garde_cout_video.py` (plafond par requête : vérifier que `video_request_op` connaît les nouveaux ids).

- [ ] **Étape 5 : mutations.**
  1. Envoyer `image_url` en plus sur FL → [0].
  2. Retirer `image_arg` de Wan → [1].
  3. Mettre `endpoint_fl` sur Kling turbo → [2] et [3].

- [ ] **Étape 6 : traduction et commit.** Clés `studio.video.fl` (« Image de début et de fin » / "First and last frame") et `studio.video.fl_absent` (« Ce modèle n'accepte pas d'image de fin » / "This model has no last-frame input") dans `studio.json`. Commit : « génération IA G2 : vidéo first-last-frame + 6 modèles (t184) ».

---

## t185 · G3 : Studio, compositions en Veo 3.1 fast et first-last-frame

**Fichiers :**
- Modifier :
  - `frontend/patches/montage.js` : le compilateur solo du nœud Seedance (chercher `summary:\`Seedance`) et `dzCompose` (chercher `async function dzCompose(`) **lisent le port `end`** ; le panneau du nœud propose les modèles de la nature `video_fl` quand `end` est branché.
  - La couche Quick, composition (`/generate/composition`) : envoie `image_filename_end` quand Quick a une image de fin (`dzEndOK`).
  - `backend/app/api/routes.py` R:6083 (`/generate/composition`) et `/layout-templates/{id}/render` R:495 : vérifier que `image_filename_end` passe jusqu'à `build_fal_args`.
- Tester : créer `backend/tests/test_studio_fl_bundle.py`.

- [ ] **Étape 1 : banc qui échoue.** Il lit le bundle **et** passe par le backend.

  ```python
  """t185 / G3 — le port `end` est compilé.
  [0] bundle : le compilateur Seedance lit l'entrée `end` (Wt(…,"end") ou équivalent) ;
  [1] bundle : dzCompose envoie image_filename_end pour un créneau dont le nœud a `end` ;
  [2] bundle : le sélecteur bascule sur nature video_fl quand `end` est branché ;
  [3] backend : /generate/composition avec seedance.image_filename_end et
      video_model=veo-3.1-fast-fal appelle build_fal_args avec end_image_url (espion) ;
  [4] backend : même payload avec kling-v3-turbo-pro -> 400 « pas d'image de fin »."""
  ```

  Pour [0]-[2], chercher dans le bundle les **chaînes de la source** `frontend/patches/montage.js` : le banc lit la source, puis vérifie qu'elle est présente dans le bundle, comme le fait `test_defauts_modeles.py`. Pour [3]-[4], utiliser le `TestClient`. L'espion est posé sur `fal_service.submit` (la couture de `fal_service.py:371`) et lève une exception après avoir capturé les arguments.

- [ ] **Étape 2 : implémenter**, dans la couche `montage` :
  - dans le compilateur solo et dans `dzCompose`, lire `const fin = Wt(node, "end")` (forme exacte : celle qu'utilise déjà le port `image` dans le même bloc) ;
  - si `fin` existe, poser `payload.image_filename_end = fin` ;
  - le panneau du nœud appelle `DzModelesIA.select(sel, fin ? "video_fl" : "video_i2v", {valeur: props.model})` ;
  - si `fin` est branché et que `props.model` n'est pas dans `video_fl`, afficher un bandeau `dzT("studio.video.fl_absent")` et proposer « Veo 3.1 Fast (first-last) ».

  **On ne change pas le modèle en silence.**

  Lancer `python scripts/refresh_layer.py --layer montage`.

- [ ] **Étape 3 : backend.**
  - Si `CompositionRequest.seedance.image_filename_end` (`backend/app/models/schemas.py:142-154, 327-341`) arrive à `pipeline` sans être relayé : le relayer dans `pipeline.py:394` (`end_image_url=upload(image_filename_end)`).
  - Garder le refus propre de G2 et le traduire en 400.
  - L'estimation `DzStudioEst` reste la même (prix au $/s).

- [ ] **Étape 4 : bancs.** `test_studio_fl_bundle.py`, `test_defauts_modeles.py`, `test_cout_pastille.py`, `test_studio_*`, le compteur `useState` et `DzTracks` 180/181 (mémoire t120).

- [ ] **Étape 5 : mutations.**
  1. Supprimer la lecture de `end` dans `dzCompose` → [1].
  2. Le sélecteur reste en `video_i2v` → [2].

- [ ] **Étape 6 : traduction et commit.** Clés `studio.compose.fin` (« Image de fin du créneau » / "Slot last frame") dans `studio.json`. Commit : « génération IA G3 : compositions Studio en Veo 3.1 fast et first-last-frame (t185) ».

---

## t186 · G4 : détourage, un registre et tous les sites branchés

**Registre** `backend/app/services/detourage.py`, schémas du 11/10. Les prix viennent de `fal_prix.py` ; « — » = à mesurer.

| id | nature | voie | endpoint | arguments clés | prix |
|---|---|---|---|---|---|
| `local-rembg` | detourage_image | local | — (python `rembg`) | — | 0 |
| `local-chroma` | detourage_image | local | — (`sprite_service`) | — | 0 |
| `birefnet-v2` | detourage_image | fal | `fal-ai/birefnet/v2` | `model` ∈ {General Use (Light), Light 2K, Heavy, Matting, Portrait, Dynamic}, `operating_resolution`, `refine_foreground` | — |
| `bria-rmbg` | detourage_image | fal | `fal-ai/bria/background/remove` | `image_url` | 0,018 $ (affiché 0,03 $ : à relire) |
| `pixelcut` | detourage_image | fal | `pixelcut/background-removal` | `output_format:"rgba"` | — |
| `ideogram-rmbg` | detourage_image | fal | `fal-ai/ideogram/remove-background` | — | 0,01 $ |
| `feynobg` | detourage_image | fal | `fal-ai/feynobg` | — | — |
| `sam3-sujet` | detourage_image | fal | `fal-ai/sam-3/image` | `prompt` (le sujet à garder), `apply_mask:true` | 0,005 $ |
| `bria-objet` | detourage_image | fal | `bria/extract-object` | `prompt`, `remove_background:true`, `autocrop` | — |
| `rembg-fal` (ancien) | detourage_image | fal | `fal-ai/imageutils/rembg` | — | 0,003 $ (`rembg_api_usd`) |
| `birefnet-v2-video` (existant, matte) | detourage_video | fal | `fal-ai/birefnet/v2/video` | `model` | — |
| `bria-video-v3` | detourage_video | fal | `bria/video/background-removal/v3` | `background_color:"Transparent"`, `output_container_and_codec:"mov_proresks"`, `preserve_audio` | 0,05 $/s |
| `veed-video-rapide` | detourage_video | fal | `veed/video-background-removal/fast` | `output_codec:"vp9"`, `subject_is_person` | 0,012 $ par tranche de 30 images |
| `pixelcut-video` | detourage_video | fal | `pixelcut/video-background-removal` | — | 0,022 $ par tranche de 30 images |
| `sam31-video` | detourage_video | fal | `fal-ai/sam-3-1/video` | `prompt`, `apply_mask:true` | 0,01 $ par tranche de 16 images |

**Fichiers :**
- Créer :
  - `backend/app/services/detourage.py` : `REGISTRE`, `build_request(id, image_url, prompt=None)`, `async detourer_image(id, chemin, prompt=None) -> nom_png` (couture `_fal_subscribe` de `matte_service`), et `detourer_video` pour la nature vidéo.
  - `backend/tests/test_detourage.py`.
- Modifier :
  - `catalogue_ia.py` : natures `detourage_image` et `detourage_video`.
  - `routes.py` `/images/process` `op=remove-bg` (R:8645-8686) : accepte `modele` (un id du registre) ; `method:"api"` = `rembg-fal` et `method:"local"` = `local-rembg` restent pour la compatibilité.
  - `pricing.py` : clés de prix, et un `estimate` kind `detourage` qui reçoit `modele`, `images` ou `secondes` ou `images_video`.
  - `matte_service.py` : `/matte` accepte les ids `detourage_video`.
  - `/api/matte-models` R:4707 : lit le registre.
  - Sites :
    - nœud Studio « Détourage » : `patch_bundle_imagegen.py:162-165`, via la couche montage ou un maillon de queue `encartsia` ;
    - Spritelab `#removeBg` : `index.html:172-178` + `sprite_service.py:244-266` ;
    - Studio3D vues : `vues.js:166, 190-192` + `asset3d_views.py:196` ;
    - Cardforge capture : `mod-capture.js:1364-1387` + `cards/capture.py:1226` ;
    - Avatar décor : `decor_service.py:32` ;
    - rack VFX matte : `vfxrack.js:85-91`, puis `refresh_layer --layer vfxrack`.
- Mettre à jour `PAYANTES` si une **nouvelle** route payante apparaît. Normalement non : les routes existantes gagnent un paramètre.

- [ ] **Étape 1 : relire les schémas.**

  ```bash
  python ~/.claude/skills/balayage-fournisseurs-fal/scripts/fal_schema.py fal-ai/birefnet/v2 fal-ai/bria/background/remove pixelcut/background-removal fal-ai/ideogram/remove-background fal-ai/feynobg fal-ai/sam-3/image bria/extract-object bria/video/background-removal/v3 veed/video-background-removal/fast pixelcut/video-background-removal fal-ai/sam-3-1/video fal-ai/birefnet/v2/video
  ```

- [ ] **Étape 2 : banc qui échoue**, `backend/tests/test_detourage.py`.

  ```python
  from app.services import detourage as D, catalogue_ia as CI
  print("[0] requêtes pures")
  ep, a = D.build_request("sam3-sujet", "https://x/a.png", prompt="le chat")
  check("sam3 endpoint", ep == "fal-ai/sam-3/image" and a["prompt"] == "le chat" and a["apply_mask"] is True, (ep, a))
  ep, a = D.build_request("bria-video-v3", "https://x/v.mp4")
  check("bria vidéo transparent prores", a["background_color"] == "Transparent" and a["output_container_and_codec"] == "mov_proresks" and a["video_url"] == "https://x/v.mp4", a)
  ep, a = D.build_request("birefnet-v2", "https://x/a.png")
  check("birefnet modèle par défaut", a.get("model") == "General Use (Heavy)", a)
  try:
      D.build_request("sam3-sujet", "https://x/a.png"); check("sam3 sans prompt refusé", False)
  except ValueError:
      check("sam3 sans prompt refusé", True)
  print("[1] catalogue")
  im = {e["id"]: e for e in CI.lister("detourage_image")}
  check("local présent et dispo sans clé", im["local-rembg"]["dispo"] is True and im["local-rembg"]["voie"] == "local")
  check(">= 9 modèles image", len(im) >= 9)
  check(">= 5 modèles vidéo", len(CI.lister("detourage_video")) >= 5)
  print("[2] /images/process remove-bg modele=pixelcut part par detourage.detourer_image (espion)")
  # (TestClient + espion sur D.detourer_image ; method:"api" sans modele -> rembg-fal, témoin)
  print("[3] estimate kind detourage")
  e = P.estimate({"kind": "detourage", "modele": "ideogram-rmbg", "images": 3})
  check("3 × 0,01", abs(e["total_usd"] - 0.03) < 1e-9, e)
  e = P.estimate({"kind": "detourage", "modele": "bria-video-v3", "secondes": 10})
  check("10 s × 0,05", abs(e["total_usd"] - 0.5) < 1e-9, e)
  ```

- [ ] **Étape 3 : implémenter `detourage.py`.**

  ```python
  """Registre UNIQUE du détourage (image et vidéo) : une entrée par modèle,
  avec voie, endpoint et forme des arguments (schémas fal relus le 11/10/2026)."""
  REGISTRE = {
      "local-rembg":  {"nature": "detourage_image", "voie": "local", "label": "rembg (local, gratuit)"},
      "local-chroma": {"nature": "detourage_image", "voie": "local", "label": "Fond uni / chroma (local)"},
      "birefnet-v2":  {"nature": "detourage_image", "voie": "fal", "label": "BiRefNet v2",
                       "endpoint": "fal-ai/birefnet/v2", "fixe": {"model": "General Use (Heavy)",
                       "operating_resolution": "2048x2048", "refine_foreground": True, "output_format": "png"},
                       "prix": "birefnet_image_usd"},
      "bria-rmbg":    {"nature": "detourage_image", "voie": "fal", "label": "Bria RMBG 2.0",
                       "endpoint": "fal-ai/bria/background/remove", "prix": "bria_rmbg_usd"},
      "pixelcut":     {"nature": "detourage_image", "voie": "fal", "label": "Pixelcut",
                       "endpoint": "pixelcut/background-removal", "fixe": {"output_format": "rgba"},
                       "prix": "pixelcut_rmbg_usd"},
      "ideogram-rmbg": {"nature": "detourage_image", "voie": "fal", "label": "Ideogram",
                        "endpoint": "fal-ai/ideogram/remove-background", "prix": "ideogram_rmbg_usd"},
      "feynobg":      {"nature": "detourage_image", "voie": "fal", "label": "FeyNobg",
                       "endpoint": "fal-ai/feynobg", "prix": "feynobg_usd"},
      "sam3-sujet":   {"nature": "detourage_image", "voie": "fal", "label": "SAM 3 — garder un sujet nommé",
                       "endpoint": "fal-ai/sam-3/image", "prompt": True, "fixe": {"apply_mask": True,
                       "output_format": "png"}, "prix": "sam3_image_usd"},
      "bria-objet":   {"nature": "detourage_image", "voie": "fal", "label": "Bria — extraire un objet nommé",
                       "endpoint": "bria/extract-object", "prompt": True,
                       "fixe": {"remove_background": True, "autocrop": False}, "prix": "bria_objet_usd"},
      "rembg-fal":    {"nature": "detourage_image", "voie": "fal", "label": "rembg (fal, ancien)",
                       "endpoint": "fal-ai/imageutils/rembg", "prix": "rembg_api_usd"},
      "birefnet-v2-video": {"nature": "detourage_video", "voie": "fal", "label": "BiRefNet v2 vidéo",
                            "endpoint": "fal-ai/birefnet/v2/video", "video": True,
                            "prix_s": "birefnet_video_usd_per_s"},
      "bria-video-v3": {"nature": "detourage_video", "voie": "fal", "label": "Bria VRMBG 3.0",
                        "endpoint": "bria/video/background-removal/v3", "video": True,
                        "fixe": {"background_color": "Transparent", "output_container_and_codec": "mov_proresks",
                                 "preserve_audio": True}, "prix_s": "bria_video_usd_per_s"},
      "veed-video-rapide": {"nature": "detourage_video", "voie": "fal", "label": "VEED rapide",
                            "endpoint": "veed/video-background-removal/fast", "video": True,
                            "fixe": {"output_codec": "vp9"}, "prix_30i": "veed_rmbg_usd_per_30f"},
      "pixelcut-video": {"nature": "detourage_video", "voie": "fal", "label": "Pixelcut vidéo",
                         "endpoint": "pixelcut/video-background-removal", "video": True,
                         "prix_30i": "pixelcut_video_usd_per_30f"},
      "sam31-video":  {"nature": "detourage_video", "voie": "fal", "label": "SAM 3.1 — suivre un sujet nommé",
                       "endpoint": "fal-ai/sam-3-1/video", "video": True, "prompt": True,
                       "fixe": {"apply_mask": True}, "prix_16i": "sam31_video_usd_per_16f"},
  }


  def build_request(mid: str, url: str, prompt: str | None = None) -> tuple[str, dict]:
      m = REGISTRE[mid]
      if m["voie"] != "fal":
          raise ValueError(f"{mid} : modèle local, pas de requête distante.")
      if m.get("prompt") and not (prompt or "").strip():
          raise ValueError(f"{m['label']} : dites quel sujet garder.")
      args = {("video_url" if m.get("video") else "image_url"): url}
      args.update(m.get("fixe", {}))
      if m.get("prompt"):
          args["prompt"] = prompt.strip()
      return m["endpoint"], args
  ```

  Prix dans `pricing.DEFAULTS` :
  - `bria_rmbg_usd: 0.018` ;
  - `ideogram_rmbg_usd: 0.01` ;
  - `sam3_image_usd: 0.005` ;
  - `bria_video_usd_per_s: 0.05` ;
  - `veed_rmbg_usd_per_30f: 0.012` ;
  - `pixelcut_video_usd_per_30f: 0.022` ;
  - `sam31_video_usd_per_16f: 0.01` ;
  - `pixelcut_rmbg_usd: 0.0`, `feynobg_usd: 0.0`, `bria_objet_usd: 0.0` (« à mesurer »).

  Dans `estimate`, ajouter le kind `detourage` ; **supprimer au passage la branche `matte` morte** (`pricing.py:557`), avec un banc qui le prouve (voir [3]).

- [ ] **Étape 4 : brancher les sites**, un par un. Chaque site affiche `DzModelesIA.select(sel, "detourage_image")`. Si le modèle choisi a `prompt:true`, un champ « Sujet à garder » apparaît. Le choix est mémorisé par site dans `localStorage` (`dz_detour_<site>`).
  - Pour le bundle (nœud Studio), passer par la couche montage ou le maillon `encartsia`.
  - Le rack matte passe par `vfxrack`.
  - Les écrans **gardent leur ancien défaut** : `api` = `rembg-fal`, `local` = `local-rembg`, matte = `birefnet-v2-video`.

- [ ] **Étape 5 : bancs.** `test_detourage.py`, `test_images_process.py`, `test_matte_service.py`, `test_matte_ecran.py`, `test_matte_compose.py`, `test_cards_capture*.py`, `test_avatar_*decor*`, Spritelab `qa/run.mjs`, `test_plafonds_garde.py` (A2 : aucune route qui joint fal sans garde).

- [ ] **Étape 6 : mutations.**
  1. `sam3-sujet` sans `apply_mask` → [0].
  2. Une entrée vidéo envoyée en `image_url` → [0].
  3. Retirer la garde de `/images/process` → `test_plafonds_garde` A1.

- [ ] **Étape 7 : traduction et commit.** Clés `detour.*` dans `commun.json` : un libellé par modèle, plus `detour.sujet` (« Sujet à garder » / "Subject to keep") et `detour.sujet_requis`. Commit : « génération IA G4 : registre de détourage image et vidéo, 15 modèles, tous les sites (t186) ».

---

## t187 · G5 : SFX et musique

**Registre SFX** `backend/app/services/sfx_service.py`, schémas du 11/10 :

| id | nature | voie | endpoint | arguments | prix |
|---|---|---|---|---|---|
| `elevenlabs-direct` (existant, défaut) | sfx_texte | elevenlabs | `api.elevenlabs.io/v1/sound-generation` | inchangé | grille ElevenLabs actuelle |
| `elevenlabs-v2-fal` (jumeau) | sfx_texte | fal | `fal-ai/elevenlabs/sound-effects/v2` | `text`, `duration_seconds`, `prompt_influence`, `loop`, `output_format:"mp3_44100_128"` | à mesurer |
| `sonilo-1.1` | sfx_texte | fal | `sonilo/v1.1/text-to-sound-effects` | `prompt`, `duration`, `audio_format:"wav"` | 0,0018 $/s |
| `mirelo-1.6` | sfx_texte | fal | `mirelo-ai/sfx1.6/text-to-audio` | `text_prompt`, `duration`, `num_samples` | à mesurer |
| `stable-audio-3-sfx` | sfx_texte | fal | `fal-ai/stable-audio-3/small/sfx/text-to-audio` | `prompt`, `duration`, `output_format:"wav"` | à mesurer |
| `sonilo-video` | sfx_video | fal | `sonilo/v1.1/video-to-sound-effects` | `video_url`, `prompt`, `keep_speech_vocal` | 0,009 $/s |
| `mirelo-video` | sfx_video | fal | `mirelo-ai/sfx1.6/video-to-video` | `video_url`, `text_prompt`, `num_samples` | à mesurer |
| `kling-v2a` | sfx_video | fal | `fal-ai/kling-video/video-to-audio` | `video_url`, `sound_effect_prompt`, `background_music_prompt` | 0,035 $ la vidéo |
| `hunyuan-foley` | sfx_video | fal | `fal-ai/hunyuan-video-foley` | `video_url`, `text_prompt` | à mesurer |
| `thinksound` | sfx_video | fal | `fal-ai/thinksound` | `video_url`, `prompt` | 0,001 $/s de calcul |

**Musique** (`backend/app/services/music_service.py:42-110`). Ajouter :
- `lyria-3.5` (`google/lyria-3.5`, `prompt`, `negative_prompt`) ;
- `elevenlabs-music-2.5` (`elevenlabs/music/v2.5`, `prompt`, `music_length_ms`, `force_instrumental` ; 0,60 $/min) ;
- `minimax-music-3` (`minimax/music-3`) ;
- `stable-audio-3` (`fal-ai/stable-audio-3/medium/text-to-audio`) ;
- `mureka-9.5` (`mureka/api/generate/song`).

Vérifier aussi la casse de `CassetteAI/music-generator` : le catalogue fal liste `cassetteai/…`.

**Fichiers :**
- Modifier :
  - `backend/app/services/sfx_service.py` : `SFX_MODELS` + `build_request` + `async generer(modele, …)`. ElevenLabs direct reste le chemin actuel.
  - `routes.py` `/audio/sfx` R:4484 : accepte `modele`.
  - Nouvelle route payante `POST /audio/sfx-video` `{video_filename|clip_id, modele, prompt}` : son seul (`sfx_video`) ou vidéo sonorisée.
  - `pricing.py` : kinds `sfx` (avec `modele`) et `sfx_video`.
  - `music_service.py` + `pricing` musique.
  - `catalogue_ia.py` : natures `sfx_texte`, `sfx_video` et `musique`.
  - UI :
    - `frontend/patches/son-vfx-montage.js` `genSfxGo` (lignes 697-711) : sélecteur, puis `refresh_layer --layer sonvfx` ;
    - tiroir Sons du Montage `frontend/patches/sfxstudio.js:259-266, 918` : sélecteur + une action « Bruitage depuis la vidéo » sur un clip, puis `refresh_layer --layer sfxstudio` ;
    - le rail musique lit `musique`.
- Tester :
  - créer `backend/tests/test_sfx_modeles.py` ;
  - ajouter `("routes", "POST", "/audio/sfx-video")` à `PAYANTES` ;
  - relancer `test_retours_sfx.py`, `test_retours_musique.py`, `test_music_lyrics.py`, `test_son_vfx_t102_ecran.py`.

- [ ] **Étape 1 : relire les schémas** :

  ```bash
  python ~/.claude/skills/balayage-fournisseurs-fal/scripts/fal_schema.py fal-ai/elevenlabs/sound-effects/v2 sonilo/v1.1/text-to-sound-effects mirelo-ai/sfx1.6/text-to-audio fal-ai/stable-audio-3/small/sfx/text-to-audio sonilo/v1.1/video-to-sound-effects mirelo-ai/sfx1.6/video-to-video fal-ai/kling-video/video-to-audio fal-ai/hunyuan-video-foley fal-ai/thinksound google/lyria-3.5 elevenlabs/music/v2.5 minimax/music-3 fal-ai/stable-audio-3/medium/text-to-audio mureka/api/generate/song
  ```

- [ ] **Étape 2 : banc qui échoue**, `backend/tests/test_sfx_modeles.py`.

  ```python
  from app.services import sfx_service as S, catalogue_ia as CI
  print("[0] requêtes pures")
  ep, a = S.build_request("sonilo-1.1", prompt="porte qui grince", duree=4)
  check("sonilo", ep == "sonilo/v1.1/text-to-sound-effects" and a == {"prompt": "porte qui grince", "duration": 4, "audio_format": "wav"}, a)
  ep, a = S.build_request("mirelo-1.6", prompt="pluie", duree=6)
  check("mirelo text_prompt", a.get("text_prompt") == "pluie" and "prompt" not in a, a)
  ep, a = S.build_request("elevenlabs-v2-fal", prompt="tonnerre", duree=3)
  check("eleven fal = text + duration_seconds", a.get("text") == "tonnerre" and a.get("duration_seconds") == 3, a)
  ep, a = S.build_request("kling-v2a", prompt="pas sur gravier", video_url="https://x/v.mp4")
  check("kling v2a", a == {"video_url": "https://x/v.mp4", "sound_effect_prompt": "pas sur gravier"}, a)
  print("[1] deux voies ElevenLabs")
  t = {e["id"]: e for e in CI.lister("sfx_texte")}
  check("jumeaux eleven", t["elevenlabs-direct"]["jumeau"] == "elevenlabs-v2-fal" and t["elevenlabs-v2-fal"]["jumeau"] == "elevenlabs-direct")
  check("direct = voie elevenlabs", t["elevenlabs-direct"]["voie"] == "elevenlabs")
  check(">= 5 sfx texte, >= 5 sfx vidéo", len(t) >= 5 and len(CI.lister("sfx_video")) >= 5)
  print("[2] /audio/sfx sans modele = ElevenLabs direct (témoin) ; modele=sonilo-1.1 -> fal (espion)")
  print("[3] /audio/sfx-video : garde + plafond ; 503 sans FAL_KEY ; PAYANTES le liste")
  print("[4] musique : lyria-3.5, elevenlabs-music-2.5 au catalogue ; défaut toujours lyria3")
  ```

- [ ] **Étape 3 : implémenter.** `build_request` part d'une table `SFX_MODELS[id] = {nature, voie, endpoint, champs: {"prompt": "<nom du champ>", "duree": "<nom>"|None, "video": "video_url"|None}, fixe: {...}, prix…}` et fabrique `args` à partir de `champs`. `generer()` télécharge le résultat dans le dossier audio par la même couture que `music_service._fal_subscribe`.

  **On ne change aucun défaut** : `/audio/sfx` sans `modele` = `elevenlabs-direct` si la clé ElevenLabs est posée. **Nouveau :** sans clé ElevenLabs mais avec `FAL_KEY`, le défaut devient `elevenlabs-v2-fal`, avec la note « via fal » (c'est le gain « une seule clé »).

- [ ] **Étape 4 : UI**, Son & VFX et tiroir Sons :
  - sélecteur `sfx_texte` ;
  - un bouton « Depuis la vidéo » sur un clip sélectionné, avec sélecteur `sfx_video` ;
  - le prix vient de `/api/cost/estimate {kind:"sfx", modele, secondes}`, comme le bouton armé existant (`svxActEstimate`).

  Lancer `refresh_layer.py --layer sonvfx` puis `--layer sfxstudio` (attention : `keepstate` et `sfxstudio` sont à égalité de mtime, donc **on ne rejoue pas la chaîne**, on rafraîchit seulement la couche).

- [ ] **Étape 5 : bancs, mutations, traduction, commit.**
  - Mutations : inverser `text` et `text_prompt` sur mirelo → [0] ; supprimer la garde de `/audio/sfx-video` → `test_plafonds_garde`.
  - Clés `son.sfx.*` (`son.sfx.modele`, `son.sfx.depuis_video`, `son.sfx.garder_voix`) dans `sfx.json` / `son.json`.
  - Commit : « génération IA G5 : SFX texte et vidéo (10 modèles), musique à jour (t187) ».

---

## t188 · G6 : VFX IA (vidéo → vidéo)

**Registre** `backend/app/services/vfx_ia.py`. Tous les modèles passent par la clé fal ; schémas du 11/10.

| id | geste pour l'utilisateur | endpoint | arguments | prix |
|---|---|---|---|---|
| `relight-h3` | Rééclairer (image de lumière) | `minimax/h3-max/relight` | `video_url`, `reference_image_url`, `resolution` | 0,08 $/s en 768p |
| `inserer-h3` | Insérer une scène | `minimax/h3-max/insert-video` | à relire au schéma | 0,06 $/s en 768p |
| `effacer-perso` | Effacer un personnage (plaque propre) | `fal-ai/ltx-2.3-quality/clean-plate` | `video_url`, `prompt`, `resolution` | 0,0024075 $/MP |
| `effacer-objet` | Effacer un objet nommé | `fal-ai/void-video-inpainting` | `video_url`, `prompt`, `mask_prompt` | 0,05 $ la vidéo (0,10 $ avec la passe 2) |
| `jour-nuit` | Jour → nuit | `fal-ai/ltx-2.3-quality/day-to-night` | `video_url` | 0,0024075 $/MP |
| `eau` | Simulation d'eau | `fal-ai/ltx-2.3-quality/water-simulation` | `video_url`, `prompt` | idem |
| `coloriser` | Coloriser | `fal-ai/ltx-2.3-quality/colorization` | `video_url` | idem |
| `retoucher-kling` | Modifier par une phrase (Kling O3) | `fal-ai/kling-video/o3/pro/video-to-video/edit` | `video_url`, `prompt`, `keep_audio:true` | 0,168 $/s |
| `retoucher-flux3` | Modifier par une phrase (rapide) | `blackforestlabs/flux-3/edit-video` | `video_url`, `prompt` | 0,03 $/s |
| `recadrer` | Changer le format (9:16 ↔ 16:9) | `fal-ai/ltx-2.3/reframe` | `video_url`, `aspect_ratio`, `resolution` | 0,10 $/s en 720p |
| `agrandir` | Agrandir / netteté (Topaz) | `topaz/upscale/video/precision` | `video_url`, `upscale_factor`, `model:"Proteus"` | 0,10 $ par 10 s en 720p |
| `effets-pixverse` | Effet prêt à l'emploi (image → vidéo) | `fal-ai/pixverse/v5.5/effects` | `image_url`, `effect` | 0,15 $ à 0,40 $ |

**Fichiers :**
- Créer :
  - `backend/app/services/vfx_ia.py` : `REGISTRE`, `build_request`, `async appliquer`, via la couture `_fal_subscribe`.
  - Route payante `POST /vfx-ia` `{clip|video_filename, modele, prompt?, image_filename?, options?}`.
  - `GET /vfx-ia/modeles`, qui n'est qu'un alias de `/ia/catalogue?nature=vfx`.
  - `backend/tests/test_vfx_ia.py`.
- Modifier :
  - `catalogue_ia.py` : nature `vfx`.
  - `pricing.py` : kind `vfx_ia` (unités `s`, `mp` ou `video`).
  - `PAYANTES` : `("routes", "POST", "/vfx-ia")`.
  - Son & VFX `SVM_GENS` : nouvelle entrée de rail « VFX IA », rendue dans `son-vfx-montage.js` comme le rail Musique (cartes `.svm-model`).
  - Rack VFX du Montage `frontend/patches/vfxrack.js` : une section « IA » sous « Détourer », même principe deux clics (estimation, puis lancement).
  - Le résultat entre dans la Bibliothèque avec sa provenance (mémoire « Bibliothèque provenance & Envoyer vers » : `library_assets` + hooks producteurs).

- [ ] **Étape 1 : relire les schémas** :

  ```bash
  python ~/.claude/skills/balayage-fournisseurs-fal/scripts/fal_schema.py minimax/h3-max/relight minimax/h3-max/insert-video fal-ai/ltx-2.3-quality/clean-plate fal-ai/void-video-inpainting fal-ai/ltx-2.3-quality/day-to-night fal-ai/ltx-2.3-quality/water-simulation fal-ai/ltx-2.3-quality/colorization fal-ai/kling-video/o3/pro/video-to-video/edit blackforestlabs/flux-3/edit-video fal-ai/ltx-2.3/reframe topaz/upscale/video/precision fal-ai/pixverse/v5.5/effects
  ```

  Remplir `inserer-h3` et `effets-pixverse` (liste des `effect`) **à partir de ce relevé**.

- [ ] **Étape 2 : banc qui échoue**, `backend/tests/test_vfx_ia.py`.

  ```python
  from app.services import vfx_ia as V, catalogue_ia as CI
  ep, a = V.build_request("relight-h3", video_url="https://x/v.mp4", image_url="https://x/l.png")
  check("relight", ep == "minimax/h3-max/relight" and a["reference_image_url"] == "https://x/l.png", a)
  try:
      V.build_request("relight-h3", video_url="https://x/v.mp4"); check("relight sans image refusé", False)
  except ValueError:
      check("relight sans image refusé", True)
  ep, a = V.build_request("retoucher-kling", video_url="https://x/v.mp4", prompt="ciel orageux")
  check("kling edit garde le son", a.get("keep_audio") is True and a["prompt"] == "ciel orageux", a)
  ep, a = V.build_request("recadrer", video_url="https://x/v.mp4", options={"aspect_ratio": "9:16"})
  check("reframe 9:16", a["aspect_ratio"] == "9:16", a)
  check(">= 10 VFX au catalogue", len(CI.lister("vfx")) >= 10)
  e = P.estimate({"kind": "vfx_ia", "modele": "retoucher-flux3", "secondes": 5})
  check("flux3 5 s = 0,15 $", abs(e["total_usd"] - 0.15) < 1e-9, e)
  # route : 503 sans FAL_KEY ; 402 au-dessus du plafond ; espion _fal_subscribe ; PAYANTES le liste
  ```

- [ ] **Étape 3 : implémenter, puis l'UI** (`refresh_layer --layer sonvfx`, `--layer vfxrack`). Chaque geste affiche sous son libellé une phrase pour l'utilisateur (« Rééclairer : donnez une image de la lumière voulue »).

- [ ] **Étape 4 : bancs.** `test_vfx_ia.py`, `test_plafonds_garde.py`, `test_son_vfx_socle.py`, `test_matte_ecran.py` (le rack garde « Détourer »), et le compteur `DzTracks`.

- [ ] **Étape 5 : mutations.**
  1. `keep_audio` absent → rouge.
  2. Route sans `_plafond` → A1.
  3. VFX hors catalogue → rouge.

- [ ] **Étape 6 : traduction et commit.** Clés `vfx.ia.*` dans `vfx.json` : un titre et une phrase par geste, plus `vfx.ia.rail`. Commit : « génération IA G6 : 12 VFX IA vidéo → vidéo, rail et rack (t188) ».

---

## t189 · G7 : Chapitres, storyboard 3D (SAM 3) puis plan vidéo

**Le parcours voulu**, pour un plan du storyboard et avant toute génération vidéo :

1. Croquis ou image de production. Ces deux étapes existent déjà.
2. **« Reconstruire en 3D (SAM 3) »**, qui appelle `fal-ai/sam-3/3d-objects` (schéma du 11/10) :
   - entrée : `image_url` (l'image de production, sinon le croquis) ; `prompt` (« personnage, voiture, table » : les objets à isoler) ou `box_prompts` ; `export_textured_glb: true` ;
   - sortie : `model_glb` (la scène), `individual_glbs` (un GLB par objet) et `metadata` (rotation, translation et échelle par objet) ;
   - prix relevé : 0,005 $ par requête, plus 0,02 $ par unité (à relire).
3. Chaque objet devient une **instance `assets3d`** de la scène 3D du plan (`scene3d_routes`, `_instances` accepte `{"kind":"assets3d","job","file"}`), placée avec la transformation SAM 3 :
   - les GLB sont écrits dans `outputs/assets3d/sam3_<hex8>_<i>/model.glb` (`mesh_sources._jobs_dir()`) ;
   - le premier objet qui correspond au premier mot du `prompt` prend le rôle `sujet` ;
   - les autres sont `decor`.
4. L'utilisateur ouvre **le Plateau 3D** (bouton existant `act-plateau`), règle caméra et mouvement, puis capture le **début** et la **fin** : `vers-plan` écrit déjà `keyframe_image` et `keyframe_end`.
5. **« Générer le plan (vidéo) »**, nouveau, sur la carte du plan :
   - `image_filename` = `keyframe_image`, sinon l'image de production, sinon le croquis ;
   - `image_filename_end` = `keyframe_end` s'il existe ;
   - `custom_prompt` = `motion_prompt` du plan, sinon son action ;
   - sélecteur `video_fl` si une fin existe, sinon `video_i2v`. Le défaut proposé avec une fin est **Veo 3.1 Fast (first-last)**, avec le prix affiché et une confirmation. Le défaut global de l'app ne change pas.
   - Le clip est rattaché au plan (`shot.video`) et l'animatique le préfère à l'image.

**Fichiers :**
- Créer :
  - `backend/app/services/storyboard3d.py` : `build_request(image_url, prompt, boxes)`, `async reconstruire(shot) -> {scene_id, objets}`, `instances_depuis_sam3(meta, jobs)` (pure).
  - `backend/tests/test_storyboard3d.py`.
  - `backend/tests/test_chapitres_video.py`.
- Modifier :
  - `routes.py` : `POST /shots/{id}/objets3d` (payant), `POST /shots/{id}/video` (payant, mêmes gardes que `/generate`, plafond « chapitres »).
  - `backend/app/services/storage.py:497-498` : colonne `video` sur `Shot` (migration douce au démarrage, comme les colonnes `keyframe_*`), sérialisée à R:10082.
  - `pricing.py` : kind `objets3d`.
  - `catalogue_ia.py` : nature `objets3d` (une seule entrée aujourd'hui, `sam-3-3d-objects` ; `fal-ai/sam-3/3d-body` en option « corps humain »).
  - `animatique_service.py` : préférer `shot.video`.
  - `frontend/atelier/atelier.js` `renderBoard()` (lignes 805-920) : deux boutons sur la carte du plan, entre « Image de production » et « Plateau 3D », plus la vignette vidéo.
  - `PAYANTES` : les deux routes.

- [ ] **Étape 1 : relire les schémas.** `fal_schema.py fal-ai/sam-3/3d-objects fal-ai/sam-3/3d-body`, puis `fal_prix.py fal-ai/sam-3/3d-objects`.

- [ ] **Étape 2 : banc qui échoue**, `backend/tests/test_storyboard3d.py`.

  ```python
  from app.services import storyboard3d as SB
  ep, a = SB.build_request("https://x/p.png", "personnage, table", [])
  check("endpoint", ep == "fal-ai/sam-3/3d-objects")
  check("glb texturé + prompt", a == {"image_url": "https://x/p.png", "prompt": "personnage, table", "export_textured_glb": True}, a)
  meta = [{"rotation": [0, 0.5, 0, 0.866], "translation": [1.0, 0.0, -2.0], "scale": [0.8, 0.8, 0.8]},
          {"rotation": [0, 0, 0, 1], "translation": [0, 0, 0], "scale": [1.2, 1.2, 1.2]}]
  inst = SB.instances_depuis_sam3(meta, ["sam3_ab12cd34_0", "sam3_ab12cd34_1"], ["personnage", "table"])
  check("2 instances assets3d", [i["source"]["kind"] for i in inst] == ["assets3d", "assets3d"])
  check("premier = sujet", inst[0]["role"] == "sujet" and inst[1]["role"] == "decor")
  check("position reprise", inst[0]["transform"]["pos"] == [1.0, 0.0, -2.0])
  check("échelle scalaire (moyenne)", abs(inst[0]["transform"]["scale"] - 0.8) < 1e-9)
  check("rotation en degrés d'Euler", len(inst[0]["transform"]["rot"]) == 3 and abs(inst[0]["transform"]["rot"][1] - 60.0) < 0.5)
  # la sortie passe la validation de scene3d_routes._instances (import et appel direct)
  from app.services import scene3d_routes as SR
  check("valide pour le Plateau", len(SR._instances(inst)) == 2)
  # route : espion _fal_subscribe renvoie model_glb + individual_glbs + metadata ;
  # les GLB (octets factices "glTF") sont écrits sous outputs/assets3d/sam3_*/model.glb ;
  # une Scene3D liée au shot est créée ou mise à jour ; 404 plan inconnu ; 400 sans image ;
  # 503 sans FAL_KEY ; plafond ; PAYANTES.
  ```

  Le banc `backend/tests/test_chapitres_video.py` couvre `/shots/{id}/video` :
  - avec `keyframe_image` et `keyframe_end` et `veo-3.1-fast-fal`, l'espion sur `fal_service.submit` reçoit `end_image_url` ;
  - sans fin, le sélecteur ne propose que `video_i2v` ;
  - avec une fin sur un modèle sans FL → 400 ;
  - le clip est rattaché à `shot.video` ;
  - l'animatique le préfère (lecture de `animatique_service`) ;
  - plafond « chapitres » ; `PAYANTES`.

- [ ] **Étape 3 : implémenter `storyboard3d.py`.**

  ```python
  """Storyboard 3D : SAM 3 (fal-ai/sam-3/3d-objects) reconstruit les objets
  d'une image de plan en GLB placés ; on en fait les instances de la scène
  du Plateau 3D de ce plan. Pur sauf `reconstruire` (réseau via couture)."""
  import math

  ENDPOINT = "fal-ai/sam-3/3d-objects"


  def build_request(image_url: str, prompt: str, boxes: list) -> tuple[str, dict]:
      args = {"image_url": image_url, "export_textured_glb": True}
      if boxes:
          args["box_prompts"] = boxes
      elif (prompt or "").strip():
          args["prompt"] = prompt.strip()
      return ENDPOINT, args


  def _euler_deg(q):
      x, y, z, w = (list(q) + [0, 0, 0, 1])[:4]
      ex = math.degrees(math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
      ey = math.degrees(math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x)))))
      ez = math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))
      return [round(ex, 3), round(ey, 3), round(ez, 3)]


  def instances_depuis_sam3(meta: list, jobs: list, noms: list) -> list:
      out = []
      for i, (m, job) in enumerate(zip(meta, jobs)):
          s = m.get("scale") or [1, 1, 1]
          s = sum(s) / len(s) if isinstance(s, list) else float(s)
          out.append({"id": f"sam3_{i + 1:02d}", "nom": (noms[i] if i < len(noms) else f"objet {i + 1}")[:80],
                      "source": {"kind": "assets3d", "job": job, "file": "model.glb"}, "niveau": "allege",
                      "role": "sujet" if i == 0 else "decor",
                      "transform": {"pos": [float(v) for v in (m.get("translation") or [0, 0, 0])[:3]],
                                    "rot": _euler_deg(m.get("rotation") or [0, 0, 0, 1]),
                                    "scale": max(s, 1e-3)}})
      return out
  ```

  `reconstruire(shot)` enchaîne :
  - choisir l'image source ;
  - `fal_client.upload_file_async` ;
  - `_fal_subscribe(ENDPOINT, args)` (couture de `matte_service`) ;
  - télécharger `individual_glbs` (ou `model_glb` s'il n'y a qu'un objet) vers `outputs/assets3d/sam3_<hex8>_<i>/model.glb` ;
  - créer ou mettre à jour la `Scene3D` du plan avec `instances_depuis_sam3`. Le contrôle d'axes réels se fait à l'étape 6, sur la preuve visuelle.

  **Si l'axe vertical de SAM 3 diffère de celui du Plateau** (à vérifier à la preuve), ajouter une conversion dans `instances_depuis_sam3` **et** une assertion de banc.

- [ ] **Étape 4 : `/shots/{id}/video`.** Réutiliser `pipeline.run_generate` (le même chemin que `POST /generate`) avec `image_filename`, `image_filename_end`, `custom_prompt`, `video_model`, `duration` (la `duration` du plan, bornée par le modèle) et `resolution`. Appliquer `_garde_cout` + `_plafond(…, "chapitres")`. Rattacher le résultat au plan.

- [ ] **Étape 5 : UI de l'Atelier.**
  - « Reconstruire en 3D » ouvre un dialogue maison avec le champ « Objets à isoler » (prérempli avec les entités du plan), le prix et une confirmation ; à la fin, un toast « 3 objets posés dans le Plateau » et le bouton « Ouvrir le Plateau ».
  - « Générer le plan (vidéo) » propose `DzModelesIA.select(…, plan.keyframe_end ? "video_fl" : "video_i2v")`, le prix, une confirmation, puis la vignette vidéo sur la carte.

- [ ] **Étape 6 : preuve à l'écran sur 8799**, avec des fausses clés et les réponses fal simulées par la couture. La vraie reconstruction sur une image réelle se fait **une fois**, sous plafond, avec l'accord de l'utilisateur. Vérifier sur cette preuve que les objets sont **debout**, à l'échelle et devant la caméra.

- [ ] **Étape 7 : bancs, mutations, traduction, commit.**
  - Bancs : `test_storyboard3d.py`, `test_chapitres_video.py`, `test_chapitres_image.py`, `test_chapitres_animatique.py`, `test_plafonds_garde.py`, les bancs du Plateau (`test_scene3d*`).
  - Mutations :
    1. Rôle `sujet` sur tous les objets → `_instances` lève « un seul sujet » ;
    2. quaternion → Euler faux → [rot] ;
    3. `end_image_url` non relayé → `test_chapitres_video`.
  - Clés `atelier.plan.reconstruire3d`, `atelier.plan.objets`, `atelier.plan.objets_poses`, `atelier.plan.video`, `atelier.plan.video_fin` dans `atelier.json` et `episodes.json`.
  - Commit : « génération IA G7 : storyboard 3D SAM 3 → Plateau → plan vidéo first-last-frame (t189) ».

---

## t190 · G8 : Vectorlab, générer et détourer par calque

**Le geste voulu :** fond ; calque 1, générer une image ; retirer son fond ; calque 2, texte et formes personnelles ; calque 3, générer une autre image ; et ainsi de suite.

**Ce qui existe :** `generer()` (`frontend/vectorlab/js/mod-image.js:223-237`) demande un prompt, appelle `/api/images/generate` et pose l'image sur le **calque actif**. Il manque :
- le choix du **calque cible** depuis la barre des calques ;
- le **modèle**, avec les deux voies et le prix ;
- le **ratio** et la **taille** relatifs à la planche ;
- **« retirer le fond »**, en option à la génération ou ensuite sur une image ;
- les références (une image du calque inférieur comme guide, en option).

**Fichiers :**
- Créer :
  - `frontend/vectorlab/js/mod-iacalque.js` : panneau flottant « Image IA sur le calque », sur le modèle de `mod-ia.js` (`hote()` sur `#stage`, en-tête glissable) ;
  - `frontend/vectorlab/qa/iacalque.test.mjs`.
- Modifier :
  - `frontend/vectorlab/js/mod-layers.js:79-93` : bouton `data-act="ia"` dans `#calquesActions`, et `:201-219`, son gestionnaire (`etat.calqueActif = id` puis `VL.iaCalque.ouvrir(id)`).
  - `frontend/vectorlab/js/mod-image.js:269-296` : bouton « Retirer le fond » dans `rendrePanneauImage`, qui appelle `/api/images/process {op:"remove-bg", filename, modele}` (registre G4), puis `deposer` et `op_image_rev` pour que **l'annulation** restaure l'image d'avant.
  - `frontend/vectorlab/js/mod-image.js:223-237` : `generer(opts)` accepte `{calqueId, modele, taille, ratio, detourer, modeleDetour, sujet}` ; sans `opts`, il garde son comportement actuel (Menu Fichier, flyout).
  - `frontend/vectorlab/index.html` : `<script src="js/mod-iacalque.js">` après `mod-image.js`, et `dz-modeles-ia.js` (G1).
  - `frontend/vectorlab/js/mod-flyout.js:158-170` et `mod-menus.js:14` : l'entrée « Générer une image » ouvre le nouveau panneau sur le calque actif.
  - `scripts/i18n_l6/` : la table d'éditions L6 de `mod-image.js` et `mod-layers.js` est **mise à jour** dans le même commit, sinon `test_i18n_l6.py` [2] passe au rouge. Lire d'abord `scripts/i18n_l6/CONSIGNE.md`. Vérifier avant le lot si `test_i18n_l6` est déjà rouge sur main (b2a956ed a touché `mod-impression.js` après L6).
  - `frontend/shared/i18n/vectorlab.json` : clés `vectorlab.iacalque.*`.
  - `frontend/vectorlab/aide/index.json` : deux fiches (G11).

- [ ] **Étape 0 : vérifier le banc L6 sur main avant de toucher quoi que ce soit.** Depuis `backend/` : `& $PY tests/test_i18n_l6.py`. S'il est déjà rouge, le **dire** à l'utilisateur et le traiter à part (une tâche `spawn_task`), sans le mélanger à ce lot.

- [ ] **Étape 1 : test node qui échoue**, `frontend/vectorlab/qa/iacalque.test.mjs`. Il teste les parties pures du module.

  ```js
  import assert from "node:assert/strict";
  import { charger } from "./outils/charger.mjs";      // le chargeur des tests vectorlab existants
  const VL = await charger(["js/mod-doc.js", "js/mod-image.js", "js/mod-iacalque.js"]);
  const P = VL.iaCalque;
  // ratio de la planche -> taille demandée au modèle
  assert.equal(P.taillePour({ w: 1080, h: 1920 }), "portrait_16_9");
  assert.equal(P.taillePour({ w: 1920, h: 1080 }), "landscape_16_9");
  assert.equal(P.taillePour({ w: 1000, h: 1000 }), "square_hd");
  // la requête respecte calque, modèle, détourage
  const q = P.requete({ prompt: "un renard", modele: "flux-3", taille: "square_hd" });
  assert.deepEqual(q, { prompt: "un renard", n: 1, model: "flux-3", size: "square_hd", source: "vectorlab" });
  // l'enchaînement planifie generate -> remove-bg -> poser sur LE calque demandé
  const plan = P.etapes({ calqueId: "c3", detourer: true, modeleDetour: "birefnet-v2" });
  assert.deepEqual(plan.map(e => e.op), ["generer", "detourer", "poser"]);
  assert.equal(plan[2].calqueId, "c3");
  // un calque verrouillé est refusé AVANT tout appel (pas de dépense)
  const doc = VL.docVierge(); doc.calques[0].verrou = true;
  assert.throws(() => P.verifierCible(doc, doc.calques[0].id), /verrouill/);
  console.log("iacalque ok");
  ```

  Si `qa/outils/charger.mjs` n'existe pas sous ce nom, reprendre le chargeur qu'utilisent `image.test.mjs` et `calques.test.mjs` (même dossier), sans en créer un nouveau.

- [ ] **Étape 2 : le lancer et le voir échouer.** `node frontend/vectorlab/qa/run.mjs iacalque`. Attendu : module absent.

- [ ] **Étape 3 : écrire `mod-iacalque.js`.** Parties pures en tête : `taillePour`, `requete`, `etapes`, `verifierCible`. Puis le panneau :
  - un champ prompt `data-dz-ia` (pour que `dz-champ-ia` mette le badge, la pastille et le micro) ;
  - `DzModelesIA.select(sel, "image")` ;
  - la case « Retirer le fond », avec `DzModelesIA.select(sel2, "detourage_image")` et le champ « Sujet à garder » si le modèle choisi l'exige ;
  - le prix total = image + détourage, via `/api/cost/estimate {kind:"campaign", ops:[{kind:"image",model},{kind:"detourage",modele,images:1}]}` ;
  - le bouton « Générer sur « {calque} » ».

  L'exécution suit la séquence ci-dessous. `VL.executer` garantit l'annulation en une étape et les erreurs en toast ; le 402 du plafond est géré par `dz-plafonds.js`, déjà chargé.

  ```js
  async function lancer(o) {
    verifierCible(VL.etat.doc, o.calqueId);
    const r = await VL.post("/api/images/generate", requete(o));
    let nom = r.images[0];
    if (o.detourer) {
      const d = await VL.post("/api/images/process", { op: "remove-bg", filename: nom, modele: o.modeleDetour, sujet: o.sujet });
      nom = d.filename;
    }
    VL.etat.calqueActif = o.calqueId;
    await VL.actions.image.poserDepuisLibrary(nom);
  }
  ```

  Exposer `VL.iaCalque = {ouvrir, taillePour, requete, etapes, verifierCible}`. **Aucun `window.prompt`** : dialogues maison.

- [ ] **Étape 4 : barre des calques et panneau Image.** Dans le panneau Image, « Retirer le fond » :
  1. lit le PNG du document ;
  2. appelle `/images/process` ;
  3. `PUT …/images/{name}` comme le fait la persona Pixel ;
  4. `op_image_rev`.

  L'annulation restaure ainsi l'image d'avant (`/annuler` du journal pixel).

- [ ] **Étape 5 : bancs.**
  - `node frontend/vectorlab/qa/run.mjs` (les 94 tests + le nouveau) ;
  - `& $PY tests/test_i18n_l6.py` (table d'éditions à jour) ;
  - `test_vector_docs.py`, `test_images_process.py`, `test_icones_g3_vectorlab.py` (une icône Glyph pour le bouton « IA » du calque : `dz-media-generer-image`, déjà existante).

- [ ] **Étape 6 : mutations.**
  1. `poser` sur le calque actif au lieu de `o.calqueId` → [etapes].
  2. Supprimer `verifierCible` → [verrouillé].
  3. Une clé `vectorlab.iacalque.*` absente de l'anglais → `test_i18n_l6` [3].

- [ ] **Étape 7 : preuve sur 8799, FR puis EN.**
  1. Un document avec un fond.
  2. Calque 1 : « IA », prompt, case « Retirer le fond » → l'image détourée apparaît sur le calque 1.
  3. Calque 2 : un texte.
  4. Calque 3 : une seconde image IA.
  5. Annuler trois fois, puis refaire.

  Les réponses fal sont simulées par les coutures. La capture sert aussi aux guides (G11).

- [ ] **Étape 8 : commit.** « génération IA G8 : Vectorlab, image IA et détourage par calque (t190) ».

---

## t191 · G9 : Photolab, générer et détourer par calque

**Le moteur ne change pas** : tout passe par des routes existantes, plus une nouvelle route de pont.

**Fichiers :**
- Créer :
  - `frontend/photolab/js/mod-iacalque.js` ;
  - `frontend/photolab/qa/iacalque.test.mjs` ;
  - route `POST /api/photolab/calque/ia` dans `backend/app/api/photolab_routes.py` (payante) ;
  - `backend/tests/test_photolab_iacalque.py`.
- Modifier :
  - `frontend/photolab/js/mod-calques.js:206-219` : bouton « IA » dans le `pied` ; gestionnaires `:229-243`.
  - Le menu Calque de `frontend/photolab/donnees/menus.json` : entrées « Nouveau calque IA… » et « Retirer le fond du calque » (pas des entrées « bientôt » : elles sont actives).
  - `frontend/photolab/index.html` : `dz-modeles-ia.js` et `dz-champ-ia.js`. Aujourd'hui, le Photolab ne charge que `dz-plafonds.js`.
  - `frontend/shared/i18n/photolab.json` : clés `photolab.iacalque.*`.
  - `PAYANTES` : `("photolab_routes", "POST", "/api/photolab/calque/ia")`. Prendre le préfixe tel que `_recensement_payant` le voit.

**La route `/calque/ia`** reçoit `{prompt, modele, taille, detourer, modeleDetour, sujet, auDessusDe, nom}`. Elle enchaîne :
1. Refus d'abord : document ouvert, calque cible existant, clé présente.
2. `_plafond` image (+ détourage).
3. Génération par la façade `IP.generate` (même chemin que `/images/generate`).
4. Détourage éventuel par `detourage.detourer_image` (G4).
5. `layer.select {layer: auDessusDe}`.
6. `photolab_moteur.placer(s, chemin, nom, objet_dynamique=False, reduire=True)` : un calque de **pixels**, au-dessus du calque choisi.
7. `layer.renameLayer` en « IA — <15 premiers caractères du prompt> ».
8. Renvoi de `{layer, bounds}`.

**« Retirer le fond du calque »** suit cette séquence :
1. `/calque/exporter` du calque ;
2. détourage ;
3. `placer` au-dessus ;
4. masquage du calque d'origine (`layer.setProps {visible:false}`).

C'est non destructif : l'original reste masqué dessous. La route s'appelle `POST /api/photolab/calque/detourer` et elle aussi est payante.

- [ ] **Étape 1 : banc backend qui échoue**, `backend/tests/test_photolab_iacalque.py`. Il reprend le patron de `test_photolab_routes.py` (moteur simulé ou réel selon ce banc).

  ```python
  # [0] sans document ouvert -> 409 ; calque inconnu -> 404 ; sans FAL_KEY pour un modèle fal -> 503 (AVANT tout appel)
  # [1] espions : IP.generate appelé avec model/size ; detourage.detourer_image appelé seulement si detourer=True
  # [2] la séquence moteur est exactement : layer.select(auDessusDe) -> placer(objet_dynamique=False) -> layer.renameLayer("IA — …")
  # [3] /calque/detourer : exporter -> détourer -> placer -> setProps(visible=False) sur l'original ; l'original N'EST PAS supprimé
  # [4] plafond : 402 sans X-DZ-Plafond quand le budget est dépassé ; PAYANTES liste les deux routes
  # [5] test_photolab_textes : aucune chaîne française hors dictionnaire dans mod-iacalque.js
  ```

- [ ] **Étape 2 : test node**, `frontend/photolab/qa/iacalque.test.mjs`. `PL.iaCalque.requete(...)` produit le corps de `/calque/ia` ; un calque groupe ou verrouillé comme cible est refusé sans appel ; le bouton du pied porte `data-act="ia"`.

- [ ] **Étape 3 : implémenter** la route, le module et le bouton. Le panneau reprend celui de G8 : `DzModelesIA`, case détourage, prix total, phrase « Le nouveau calque se place au-dessus de « {calque} » ». Le parcours passe par `PL.cycle()`, puis la sélection du nouveau calque.

- [ ] **Étape 4 : bancs.**
  - `test_photolab_iacalque.py` ;
  - `test_photolab_routes.py`, `test_photolab_textes.py`, `test_photolab_libelles.py` ;
  - `node frontend/photolab/qa/run.mjs` ;
  - `test_plafonds_garde.py` ;
  - le recensement « bientôt » du skill `parite-photolab` (`lister_bientot.mjs`) : les deux nouvelles entrées n'y figurent pas.

- [ ] **Étape 5 : mutations.**
  1. `objet_dynamique=True` → [2].
  2. Supprimer l'original au lieu de le masquer → [3].
  3. Appeler `IP.generate` avant le contrôle de clé → [0].

- [ ] **Étape 6 : preuve sur 8799, FR puis EN.** Même scénario que G8 (fond → IA détourée → texte → IA), plus l'annulation par l'historique du moteur.

- [ ] **Étape 7 : commit.** « génération IA G9 : Photolab, calque IA et détourage non destructif (t191) ».

---

## t192 · G10 : traduction FR/EN, contrôle final

Chaque lot a déjà posé ses clés. Ce lot vérifie l'ensemble et ajoute **un banc transverse**.

**Clés par catalogue** (`frontend/shared/i18n/`) :

| Catalogue | Préfixes ajoutés | Lot |
|---|---|---|
| `commun.json` | `ia.voie.*`, `ia.prix.a_mesurer`, `ia.cle.absente`, `ia.cle.a_ajouter`, `ia.choisir_modele`, `detour.*` | G0, G1, G4 |
| `studio.json` | `studio.video.fl`, `studio.video.fl_absent`, `studio.compose.fin` | G2, G3 |
| `sfx.json` / `son.json` | `son.sfx.*` (modèle, depuis la vidéo, garder la voix) | G5 |
| `vfx.json` | `vfx.ia.*` (12 gestes × titre + phrase, rail) | G6 |
| `atelier.json` / `episodes.json` | `atelier.plan.reconstruire3d`, `.objets`, `.objets_poses`, `.video`, `.video_fin` | G7 |
| `vectorlab.json` | `vectorlab.iacalque.*` | G8 |
| `photolab.json` | `photolab.iacalque.*`, `photolab.menu.calque_ia`, `photolab.menu.calque_detourer` | G9 |
| serveur `backend/app/i18n/messages.json` | messages des nouvelles erreurs 400/503 (`ia.cle_absente`, `ia.pas_de_fin`, `detour.sujet_requis`, `vfx.image_requise`) | G2, G4, G6, G7 |

**Les libellés de modèles** (« Flux 3 », « Veo 3.1 Fast ») sont des **noms propres** : on ne les traduit pas. Seules les notes (« via fal », « prix à mesurer ») passent par `dzT`.

**Fichiers :** créer `backend/tests/test_i18n_generation_ia.py`, puis lancer `scripts/i18n_assembler.py --check`.

- [ ] **Étape 1 : banc transverse.**

  ```python
  """t192 / G10 — toutes les clés des lots G0-G9 existent en fr ET en en, mêmes {variables} ;
  aucune chaîne française en dur dans les fichiers créés par ces lots ; dico assemblé à jour."""
  import json, re, subprocess, sys
  from pathlib import Path
  R = Path(__file__).resolve().parents[2]
  PREFIXES = {"commun": ("ia.", "detour."), "studio": ("studio.video.fl", "studio.compose.fin"),
              "son": ("son.sfx.",), "sfx": ("son.sfx.",), "vfx": ("vfx.ia.",),
              "atelier": ("atelier.plan.reconstruire3d", "atelier.plan.objets", "atelier.plan.video"),
              "vectorlab": ("vectorlab.iacalque.",), "photolab": ("photolab.iacalque.", "photolab.menu.calque_")}
  VAR = re.compile(r"\{(\w+)\}")
  OK = KO = 0
  def check(l, c, d=""):
      global OK, KO
      OK, KO = (OK + 1, KO) if c else (OK, KO + 1); print("  ok  " if c else "  FAIL", l, "" if c else d)
  vus = 0
  for cat, pref in PREFIXES.items():
      p = R / f"frontend/shared/i18n/{cat}.json"
      if not p.exists(): continue
      d = json.loads(p.read_text(encoding="utf-8"))
      for k, v in d.items():
          if k.startswith(pref):
              vus += 1
              check(f"{cat}:{k} fr+en", bool(v.get("fr")) and bool(v.get("en")), v)
              check(f"{cat}:{k} mêmes variables", set(VAR.findall(v.get("fr", ""))) == set(VAR.findall(v.get("en", ""))), v)
  check("au moins 60 clés nouvelles", vus >= 60, vus)
  for f in ("frontend/shared/dz-modeles-ia.js", "frontend/vectorlab/js/mod-iacalque.js", "frontend/photolab/js/mod-iacalque.js"):
      s = (R / f).read_text(encoding="utf-8")
      litt = [m for m in re.findall(r'"([^"\n]{4,})"', s) if re.search(r"[éèàùçê]|\b(le|la|les|une|des|du)\b", m)]
      check(f"{f} sans français en dur", not litt, litt[:5])
  r = subprocess.run([sys.executable, str(R / "scripts/i18n_assembler.py"), "--check"], capture_output=True, text=True)
  check("dico assemblé à jour", r.returncode == 0, r.stdout[-300:])
  print(f"\n{OK} ok, {KO} fail"); sys.exit(1 if KO else 0)
  ```

- [ ] **Étape 2 : lancer tous les bancs i18n.**

  ```powershell
  .\scripts\run-tests.ps1 -Filter "i18n|photolab_textes|photolab_libelles|avatar_i18n"
  ```

- [ ] **Étape 3 : relevé DOM en EN sur 8799.** Ouvrir chaque écran touché en anglais (`localStorage.dz_lang="en"`) et chercher le français restant avec le relevé du skill `traduction-deepotus` (`releve_chaines.py`). Écrans : Studio (nœud vidéo avec fin), Quick, Son & VFX (SFX, VFX IA), rack VFX, Atelier (storyboard), Vectorlab (panneau IA calque), Photolab (pied des calques, menu Calque), Material Forge, Spritelab.

- [ ] **Étape 4 : mutations.**
  1. Supprimer l'`en` d'une clé `vfx.ia.*` → rouge.
  2. Un `{cle}` absent de l'anglais → rouge.
  3. Recoder « Retirer le fond » en dur dans `mod-iacalque.js` → rouge.

- [ ] **Étape 5 : commit.** « génération IA G10 : traduction FR/EN des lots G0-G9, banc transverse (t192) ».

---

## t193 · G11 : guides illustrés FR/EN et fiches didactiques

Suivre le skill `guide-deepotus` : relevé, rédaction FR, scènes, traduction EN, construction, bancs. Pour les fiches, suivre le skill `didacticiel-option`.

**Ajouts au guide** (`docs/guide/src/`) :

| Chapitre (id existant ou nouveau) | Section ajoutée | Scènes (3 temps) |
|---|---|---|
| **Nouveau** `modeles-et-cles` (famille Réglages) | « Choisir un modèle : votre clé ou la clé fal » ; « Lire le prix d'une option » ; « Une option « clé à ajouter » : la choisir, puis poser la clé » | `modeles/groupes`, `modeles/prix`, `modeles/cle-absente` |
| `studio` (existant) | « Une composition avec image de début et de fin (Veo 3.1 Fast) » | `studio/composition-fl` |
| `chapitres` ou `atelier` (existant) | « Du storyboard à la 3D : reconstruire un plan avec SAM 3 » ; « Cadrer dans le Plateau, capturer début et fin » ; « Générer la vidéo du plan » | `chapitres/sam3`, `chapitres/plateau-capture`, `chapitres/plan-video` |
| `son-vfx` (existant) | « Bruitages : choisir un modèle » ; « Sonoriser une vidéo » ; « VFX IA : rééclairer, effacer, recadrer… » | `son/sfx-modeles`, `son/sfx-video`, `vfx/ia` |
| `montage` (existant) | « Détourer avec le modèle de son choix » (rack) | `montage/detour-modeles` |
| `vectorlab` (existant) | « Composer par calques avec l'IA » (fond → image détourée → texte → seconde image) | `vectorlab/ia-calque`, `vectorlab/retirer-fond` |
| `photolab-avance` (existant) | « Nouveau calque IA » ; « Retirer le fond d'un calque (non destructif) » | `photolab/ia-calque`, `photolab/detourer-calque` |

**Fiches didactiques** (320 × 200, trois temps, FR et EN) :
- `frontend/vectorlab/aide/index.json` : `iacalque.ouvrir`, `image.retirer_fond` ;
- `frontend/photolab/aide/index.json` : `photolab.iacalque`, `photolab.detourer_calque`.

**Fichiers :**
- `docs/guide/src/chapitres.json` : nouvelle entrée `modeles-et-cles` (`famille`, `lot: "t193"`, `icone` `dz-*`, `fr`, `en`, `etat: "v3"`), sections ajoutées aux chapitres existants (en gardant leurs ancres `anciens`).
- `docs/guide/src/{fr,en}/*.html`.
- `docs/guide/src/scenes/plans/t193.json`.
- `docs/guide/src/scenes/<chapitre>/<scene>/scene.json` + captures `.fr.webp` / `.en.webp`.
- `docs/guide/MANQUES.md`.
- `scripts/guide/semer_*.py` : semer les données de démonstration (document Vectorlab à trois calques, plan de storyboard avec image de production).

- [ ] **Étape 1 : relevé** (skill `guide-deepotus`, étape 1). Tableau « couvert / à corriger / manquant » pour chaque ligne du tableau ci-dessus. Ce tableau ouvre la PR.

- [ ] **Étape 2 : rédiger en FR**, au plus ~1 200 mots par chapitre ; `<b class="ui">` = le libellé **exact** à l'écran, en FR comme en EN, puisque le banc vérifie leur existence dans les dictionnaires de G10.

- [ ] **Étape 3 : plan de capture `t193.json` et captures.**

  ```bash
  NODE_PATH=C:/Users/olivi/DeepotusVideo/scripts/qa/node_modules node scripts/guide/capturer.js docs/guide/src/scenes/plans/t193.json http://127.0.0.1:8799
  ```

  Pour chaque scène, en FR puis en EN : backend de preuve 8799, clés factices, réponses fal simulées. Regarder **chaque** WebP à l'œil.

- [ ] **Étape 4 : traduire en EN** avec le même squelette (sections, scènes, encarts dans le même ordre).

- [ ] **Étape 5 : fiches didactiques** (skill `didacticiel-option`) : capture dans la page → `scripts/assembler.py` → `scripts/verifier.py frontend/vectorlab iacalque.ouvrir` (et les autres) → `qa/aide.test.mjs`.

- [ ] **Étape 6 : construire et tester.**

  ```bash
  python scripts/guide/construire_guide.py --check
  python scripts/guide/construire_guide.py --pdf
  ```

  ```powershell
  & $PY tests/test_guide_v3.py; & $PY tests/test_guide_liens_app.py; & $PY tests/test_i18n_l6.py; node frontend/vectorlab/qa/run.mjs aide; node frontend/photolab/qa/run.mjs aide
  ```

  Puis aperçu FR/EN, clair/sombre, mobile et impression.

- [ ] **Étape 7 : commit.** « génération IA G11 : guides FR/EN (modèles et clés, storyboard 3D, SFX/VFX, calques IA) + 4 fiches (t193) ».

---

## Auto-relecture (faite à l'écriture du plan)

**Couverture de la demande :**

| Demande | Où |
|---|---|
| Garder toutes les connexions actuelles | Architecture : on ajoute, rien n'est retiré ; les défauts ne changent pas (règle commune). |
| Enrichir chaque encart IA selon la nature de l'appel | G0 (image), G1 (tous les encarts), G2 (vidéo), G4 (détourage), G5 (SFX et musique), G6 (VFX). |
| Lister les deux voies et leurs coûts | Champs `voie`, `cle`, `usd` et `jumeau` (G0) ; `<optgroup>` par voie avec le prix (G1) ; Veo Google/fal (G2) ; ElevenLabs direct/fal (G5). |
| SAM 3 (`sam-3/3d-objects`) dans le storyboard de Chapitres, avant la vidéo | G7. |
| Meilleurs SFX | G5. |
| VFX | G6. |
| Tous les détourages (nœuds et fonctions intermédiaires) | G4, avec les six sites listés. |
| Studio, compositions en Veo 3.1 fast et first-last-frame | G2 (backend) + G3 (Studio). |
| Vectorlab et Photolab : génération par calque, puis détourage, texte, autre image | G8, G9. |
| Traductions FR/EN | Règle transversale + G10. |
| Guides illustrés FR/EN | G11. |

**Écarts assumés :**
- Les prix « à mesurer » sont écrits tels quels (doctrine de la maison), jamais inventés.
- Les champs `duration` de `h3-max`, `wan-3.0` et `gemini-omni-flash` sont à relire au schéma à l'étape 1 de G2 (ils n'étaient pas des enums dans le relevé du 11/10).
- `inserer-h3` et `effets-pixverse` sont à compléter depuis le relevé de G6, étape 1.

**Cohérence des noms entre lots :**
- `catalogue_ia.lister(nature)`.
- Natures : `image`, `video_i2v`, `video_fl`, `detourage_image`, `detourage_video`, `sfx_texte`, `sfx_video`, `musique`, `vfx`, `objets3d`.
- `DzModelesIA.select(el, nature, {valeur, onChange})`.
- `detourage.build_request` / `detourer_image`.
- `/images/process` reçoit `modele` + `sujet`.
- `VL.iaCalque` / `PL.iaCalque`.

**Ordre conseillé :** G0 → G1 → G2 → G3 → G4 → G5 → G6 → G7 → G8 → G9 → G10 → G11. G5, G6 et G8/G9 peuvent avancer en parallèle après G4, dans des worktrees séparés. **Attention :** deux lots qui touchent la même couche du bundle (`montage`, `sonvfx`) ne fusionnent pas en même temps (mémoire « session concurrente sur le bundle → rejouer la chaîne »).
