# Chapitres — bible relationnelle, versions, cohérence, animatique, formats — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Porter la catégorie Chapitres (bible, storyboard, scénario, épisodes) au niveau des références vérifiées le 03/09/2026 (NovelCrafter pour la bible relationnelle, Boords pour l'animatique, fal Veo 3.1 / Kling v3 / Nano Banana Pro pour la cohérence multi-références), puis livrer les trois différenciants de R3 (réécriture dans le ton de la bible, un chapitre → quatre sorties, l'animatique qui s'ouvre au Montage).

**Architecture:** Tout le travail d'écran se fait dans la page autonome `/atelier` (`frontend/atelier/{index.html,atelier.js,atelier.css}`, vanilla JS, même origine) : **mesuré le 03/09, la bible, le storyboard et le scénario ne sont PAS dans le bundle** (voir « Coût de patch »). Le backend reçoit des services purs et testables (`text_versions.py`, `identity_drift.py`, `animatique_service.py`, `screenplay_import.py`, `pdf_mini.py`, `text_export.py`) et des routes minces dans `backend/app/api/routes.py` ; les tables neuves passent par `create_all`, les colonnes ajoutées par `_auto_migrate` (patron `SHOTS_COLUMNS`, `storage.py:436`). Aucun patch du bundle dans ce plan.

**Tech Stack:** FastAPI + SQLAlchemy async (SQLite), Python 3.13 embarqué (stdlib + Pillow 12 ; `python-docx` 1.2 et `pypdf` 6.16 sont dans `requirements.txt` et présents dans le runtime installé — mesuré le 03/09 : `import docx, pypdf, PIL` OK, **numpy ABSENT**), ffmpeg/ffprobe dans `bin/`, fal (`fal_client`), ElevenLabs/Voicebox via `VoiceoverService`, vanilla JS côté `/atelier`.

---

## Conventions de ce plan

- **Python** : `PY="/c/Users/olivi/AppData/Local/DeepotusVideoGen/runtime/python/python.exe"` (runtime embarqué, mesuré présent ; `runtime/python/` n'existe pas dans le dépôt). Tous les tests se lancent **depuis `backend/`**, un processus par fichier : `cd backend && $PY tests/test_<x>.py`. Jamais `pytest tests` global.
- **Tests** : fichiers `backend/tests/test_<x>.py` sur le patron de `test_vector_docs.py` (fonctions `def test_…():` qui font `asyncio.run(scenario())`, collectables par `pytest -k` pour la campagne de mutations) et `test_atelier.py` (stub `fal_client` par `sys.modules`, `httpx.AsyncClient.get` détourné, `SUMZ._chat_dispatch` stubbé). Le pied de chaque fichier force l'UTF-8 et enchaîne les tests :

  ```python
  if __name__ == "__main__":
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
      for _f in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
          _f()
      print("<NOM> TEST: PASS")
  ```

  Un banc-miroir **lit ce qui est écrit** (le fichier produit, la ligne en base, la source JS) et **compte ses assertions** (`assert` ≥ le nombre annoncé dans l'en-tête du fichier).
- **Commits** : sujet SANS accent (apostrophes permises), corps accentué, pied `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`, jamais de guillemet double dans `-m`. Forme unique, depuis la racine du dépôt (Git Bash) :

  ```bash
  git add <fichiers> && git commit -F - <<'EOF'
  chapitres : <sujet sans accent>

  <corps accentué : le POURQUOI et la mesure>

  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  EOF
  ```

- **JS** : après toute édition de `frontend/atelier/atelier.js`, `node --check frontend/atelier/atelier.js` (sortie vide = OK).
- **Jamais** : lancer le backend (`launch.ps1`, `uvicorn`, `python -m app.main`), `scripts/run-tests.ps1` complet, ni une commande git autre que `add`/`commit`. Le déploiement vers `%LOCALAPPDATA%` et la relance sont l'affaire de l'utilisateur (mémoire : comparer par `git hash-object`, jamais par sha256).

---

## Périmètre

Les bacs de `R3. Chapitres — réponses (03/09/2026)` du brief `docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md` sont le périmètre exact.

| Lot | Item | Tâches |
|---|---|---|
| 1 — parité | **P1** bible relationnelle (plan ↔ entités, fiche « apparitions ») | T1, T2 |
| 1 — parité | **P2** versions du texte (instantanés, comparaison, restauration) | T3, T4, T5 |
| 1 — parité | **P3** cohérence multi-références (image, vidéo) + banc de dérive | T6, T7, T8, T9 |
| 1 — parité | **P4** animatique depuis les plans | T10, T11 |
| 1 — parité | **P5** import Fountain et FDX | T12, T13 |
| 1 — parité | **P6** exports docx/PDF, PDF du storyboard | T14, T15, T16 |
| 2 — différenciant | **D1** réécriture / génération à la demande dans le ton de la bible | T17 |
| 2 — différenciant | **D2** un chapitre, quatre sorties | T18, T19 |
| 2 — différenciant | **D3** l'animatique s'ouvre au Montage | T20 |
| — | campagne de mutations | T21 |

**Ce que le code fait déjà et qu'on prolonge** (relu le 03/09, numéros de ligne réels) : `Shot.entities` (JSON d'ids, `storage.py:276`) est rempli par `_ai_shots` (`routes.py:5849`, noms → ids par `name2id`, `:5897`) mais laissé vide par `_paragraph_shots` (`routes.py:5834`) et non éditable dans `/atelier` (`renderBoard`, `atelier.js:550`, chips en lecture seule) ; `Scene.entities` (`storage.py:311`) est rempli par `_run_adapt_job` (`routes.py:7046`). Les planches sont composées par code (`board_service.py`), la recette v2 garde clé/prompt/seed/modèle par panneau **mais pas le fichier** (`routes.py:5561`). Nano Banana Pro reçoit **une** référence (`image_providers.py:126`, `"image_urls": [image_url]`). Le rendu d'épisode (`pipeline.run_episode`, `pipeline.py:763`) fournit la mécanique image fixe + voix + concaténation (`FFmpegMerger.scene_clip` / `concat_clips`, `ffmpeg_service.py:184/224`). `vector_store.py` est le patron de versionnage du dépôt (courant + `.v<n>` × 10 — `_GARDE_HISTORIQUE`, `vector_store.py:21` —, écriture atomique). Le Montage sauvegarde un projet JSON (`montage_service.py:467`, `_write_saved`) dont les clips acceptent `src: {file_path}` (`_resolve_src`, `montage_service.py:734`).

---

## Coût de patch (mesuré le 03/09/2026)

Le brief R3 estimait « Chapitres est un écran du bundle ». **Mesure** : dans `frontend/dist/assets/index-BEOJX8L5.js`, `DzChapitres` est un sélecteur de mode — `"origine"` rend `DzEpisodes` (bundle), `"atelier"` rend `<iframe src="/atelier">`. Occurrences des routes (bundle / `frontend/atelier/atelier.js`) : `storyboard/decoupe` 0/1 · `screenplay/adapt` 0/1 · `/sketch` 0/1 · `/shots` 0/7 · `/scenes` 1/4 · `bible/entities` 2/11 · `/vector/docs` 0/5 · `atelier/manuscript` 0/4 · `episodes/render` 1/0 · `episodes/scenes` 1/0. Donc **bible, storyboard, scénario, manuscrit = page autonome `/atelier`** (1 395 lignes de JS, 255 d'HTML, 347 de CSS : on édite la source, `node --check`, aucun patcher). Seul le mode Épisodes vit dans le bundle ; D2 y accède par une route backend qui appelle `pipeline.run_episode`, pas par un patch.

Chaîne des patchers aujourd'hui (`python scripts/repatch_all.py --list`) : `dzrailmotion → version → dznodecat → seedance25` (queue). **Aucune tâche de ce plan ne touche le bundle.** Si une tâche future devait le faire (par exemple un bouton « Chapitres » dans l'écran Épisodes), le tag serait `chapitres`, backup `.js.bak_chapitres`, en queue après `seedance25`, chaque ancre `s.count(anchor) == 1`, puis `python scripts/repatch_all.py --from chapitres`.

| Tâche | Surface | Coût |
|---|---|---|
| T1, T3, T4, T6, T7, T8, T9, T10, T12, T14, T15 (routes), T18 | backend (`routes.py`, services, `storage.py`) | tests seuls |
| T2, T5, T11 (bouton), T13 (bouton), T15/T16 (liens), T17, T19, T20 | `/atelier` autonome | `node --check`, banc-miroir de la source |
| toutes | bundle | **0** |

---

## Références vérifiées

Seules les références **vérifiées et datées** de R3 servent d'argument ; le reste est « de mémoire, à vérifier » et n'appuie aucune décision.

- **NovelCrafter, Codex** (docs.novelcrafter.com, 03/09) : mentions indexées (nom, alias, pluriels), carte des mentions par entrée. → P1 : l'app a les mentions et les alias (`compute_spans`), il lui manque le lien aux plans et la fiche « apparitions ».
- **Boords, animatique** (boords.com, help.boords.com, 03/09) : durée par image réglée, voix off téléversée (WAV/MP4, 20 Mo max) qui **fixe la durée**, export MP4 et PDF, champs de texte en sous-titres. → P4 : la voix témoin fixe la durée du plan ; P6 : PDF du storyboard.
- **fal, Veo 3.1 reference-to-video** (fal.ai, 03/09) : **1 à 9 images** de référence, aussi sur Veo 3.1 Fast. → P3 : plafond commun de 9 références.
- **fal, Kling v3 Pro** (fal.ai, 03/09, R1) : `elements` (références image/vidéo nommées `@Element` dans le prompt), pas de `seed`. → P3 vidéo.
- **fal, Nano Banana Pro** : `image_urls` accepte plusieurs images (fal.ai, 03/09) ; l'app n'en passe qu'une (mesuré, `image_providers.py:126`) ; note interne « 2K/4K, 14 refs » (`routes.py:4909`, 28/08) ; 0,15 $ l'image (pricing.py, re-vérifié 27/08).
- **Mesures dépôt (03/09)** : `grep -c elements backend/app/services/fal_service.py` → 0 (les `elements` Kling ne sont pas branchés) ; `veo-3.1-fast-fal` au registre (`fal_service.py:122`), aucune entrée reference-to-video ; `_flux_generate` ne prend qu'une `image_url` (`routes.py:4767`).
- **Mesures runtime (03/09, python embarqué `runtime/python/python.exe`, 3.13.15)** : `docx` 1.2.0 **OK**, `pypdf` 6.16.2 **OK**, `PIL` 12.3.0 **OK** ; `numpy`, `reportlab`, `fpdf` **ABSENTS**. C'est ce qui décide P3 (dérive en PIL pur, T6) et P6 (PDF écrit à la main, T14).
- **Écrasements silencieux mesurés (03/09)** : `update_chapter` (`routes.py:5751`), `update_scene` (`:6797`), `storyboard_decoupe` (`:5939`), `_run_adapt_job` (`:7095`, `session.delete(s)` sur toutes les scènes). Aucun ne garde l'ancien état → P2.
- **Invariants qu'une tâche casse, et qui doivent suivre** : `tests/test_video_models.py:40` asserte `set(VIDEO_MODELS) == EXPECTED_IDS` et `:47` exige une ligne de prix par modèle — T9 met les deux à jour dans son propre commit.
- **De mémoire, à vérifier** (n'appuient rien) : Sudowrite, Final Draft, Celtx ; le format FDX (XML de Final Draft, pas de spécification publique) ; les marges du scénario papier (Courier 12, cue à 3,7", dialogue à 2,5").
- **Fountain** : spécification publique, relue par `WebFetch` en première étape de T12 (commande exacte dans la tâche).

---

## Lot 1 — parité

### T1 — P1a : la table plan ↔ entités remplie sans LLM, et la route « apparitions »

**Files:**
- Modify: `backend/app/api/routes.py:5834-5847` (`_paragraph_shots`), `:5969-5970` (`storyboard_decoupe`, branche paragraphe), avant `@router.post("/bible/entities")` (`:5122`)
- Test: `backend/tests/test_chapitres_relationnel.py`

**Pourquoi** : `_ai_shots` sait déjà lier les entités (mesuré : `name2id`, `routes.py:5890`), mais le découpage par paragraphe — le seul chemin sans clé LLM — laisse `entities=[]` ; et rien ne répond à « où apparaît Elias ? » (réponse 1 : la fiche liste ses apparitions et ses planches).

- [ ] **Étape 1 : le test qui échoue** — `backend/tests/test_chapitres_relationnel.py` (13 assertions)

```python
"""P1 — bible relationnelle : entités des plans sans LLM (paragraphe) et
route /bible/entities/{id}/apparitions. 13 assertions.
Run: <embedded python> backend/tests/test_chapitres_relationnel.py"""
import asyncio, json, os, sys, tempfile, pathlib, types
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
_stub = types.ModuleType("fal_client"); sys.modules["fal_client"] = _stub
from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.main import app                               # noqa: E402
from app.services.storage import init_db               # noqa: E402

SCRIPT = ("Elias Vane s'éveille avant l'alarme.\n\n"
          "Vane serre la Clé de Nacre. Le Prophète l'observe.\n\n"
          "Dehors, Londres disparaît sous la pluie.")


def test_paragraphe_lie_les_entites_et_la_fiche_liste_les_apparitions():
    async def scenario():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            elias = (await c.post("/api/bible/entities", json={"kind": "character", "name": "Elias Vane"})).json()
            await c.put(f"/api/bible/entities/{elias['id']}", json={"aliases": ["Vane"]})
            cle = (await c.post("/api/bible/entities", json={"kind": "object", "name": "Clé de Nacre"})).json()
            ch = (await c.post("/api/chapters", json={"title": "Ch1", "script_text": SCRIPT,
                  "spans": [{"start": 0, "end": 10, "text": "Elias Vane", "entity_id": elias["id"]}]})).json()
            r = await c.post(f"/api/chapters/{ch['id']}/storyboard/decoupe", json={"method": "paragraph"})
            assert r.status_code == 200, r.text
            shots = r.json()["shots"]
            assert len(shots) == 3
            assert shots[0]["entities"] == [elias["id"]]                   # nom
            assert set(shots[1]["entities"]) == {elias["id"], cle["id"]}    # alias + objet
            assert shots[2]["entities"] == []
            r = await c.get(f"/api/bible/entities/{elias['id']}/apparitions")
            assert r.status_code == 200, r.text
            a = r.json()
            assert a["totals"] == {"chapters": 1, "mentions": 1, "shots": 2, "scenes": 0}
            assert a["chapters"][0]["title"] == "Ch1"
            assert [s["idx"] for s in a["chapters"][0]["shots"]] == [0, 1]
            assert a["chapters"][0]["shots"][0]["action"].startswith("Elias")
            r = await c.get("/api/bible/entities/inconnu/apparitions")
            assert r.status_code == 404
            # édition à la main : le plan 3 reçoit Elias, la fiche le voit
            await c.put(f"/api/shots/{shots[2]['id']}", json={"entities": [elias["id"]]})
            a = (await c.get(f"/api/bible/entities/{elias['id']}/apparitions")).json()
            assert a["totals"]["shots"] == 3
            assert len(a["chapters"][0]["shots"]) == 3
    asyncio.run(scenario())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for _f in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        _f()
    print("P1 RELATIONNEL TEST: PASS")
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_relationnel.py` → `AssertionError` sur `shots[0]["entities"] == [...]` (liste vide aujourd'hui).

- [ ] **Étape 3 : `_paragraph_shots` lit les entités** — remplacer la fonction (`routes.py:5834`) :

```python
def _paragraph_shots(script: str, bible: list[dict] | None = None) -> list[dict]:
    """Fallback sans LLM : un plan par paragraphe, durée estimée à la lecture
    (~150 mots/min, bornée 3–12 s). P1 (03/09) : les entités présentes sont
    LUES dans le paragraphe — nom + alias, bornes de mots, sans casse ni
    accents (MA.compute_spans, le même moteur que le surlignage) — pour que
    la table plan ↔ entités existe aussi sans clé LLM."""
    from app.services import manuscript_agent as MA
    parts = [p.strip() for p in re.split(r"\n\s*\n", script) if p.strip()]
    ents = [{"id": e["id"], "name": e["name"], "aliases": e.get("aliases") or [],
             "quotes": []} for e in (bible or [])]
    out = []
    for p in parts:
        words = len(p.split())
        dur = max(3.0, min(12.0, round(words / 2.5, 1)))
        found = list(dict.fromkeys(sp["entity_id"] for sp in MA.compute_spans(p, ents))) if ents else []
        out.append({"source_text": p, "action": p[:200], "entities": found,
                    "shot_type": "medium", "camera_move": "static, locked-off",
                    "duration_s": dur, "prompt": "",
                    "motion_recipe": None, "energy": None})
    return out
```

et dans `storyboard_decoupe`, la branche `else:` (`routes.py:5969-5970`) devient :

```python
        else:
            ents_resp = await list_bible_entities(None)
            drafts = _paragraph_shots(script, ents_resp["entities"])
```

- [ ] **Étape 4 : la route « apparitions »** — juste avant `@router.post("/bible/entities")` (`routes.py:5122`) :

```python
@router.get("/bible/entities/{entity_id}/apparitions")
async def entity_apparitions(entity_id: str):
    """P1 — la fiche relationnelle : où l'entité apparaît, chapitre par
    chapitre — mentions (spans du script), plans (shots.entities) et scènes
    (scenes.entities), dans l'ordre de lecture. Lu en base, aucun LLM."""
    from app.services.storage import (BibleEntity, Chapter, Shot, Scene,
                                      async_session_factory)
    from sqlalchemy import select
    import json as _json
    async with async_session_factory() as session:
        e = await session.get(BibleEntity, entity_id)
        if not e:
            raise HTTPException(404, "Entity not found")
        chapters = (await session.execute(select(Chapter).order_by(Chapter.created_at.asc()))).scalars().all()
        shots = (await session.execute(select(Shot).order_by(Shot.idx.asc()))).scalars().all()
        scenes = (await session.execute(select(Scene).order_by(Scene.idx.asc()))).scalars().all()

    def _has(row) -> bool:
        try:
            return entity_id in (_json.loads(row.entities) if row.entities else [])
        except Exception:
            return False

    out = []
    for ch in chapters:
        try:
            spans = _json.loads(ch.spans) if ch.spans else []
        except Exception:
            spans = []
        mentions = sum(1 for sp in spans if sp.get("entity_id") == entity_id)
        sh = [{"id": s.id, "idx": s.idx, "action": (s.action or "")[:120],
               "sketch_image": s.sketch_image} for s in shots if s.chapter_id == ch.id and _has(s)]
        sc = [{"id": s.id, "idx": s.idx, "slugline": s.slugline}
              for s in scenes if s.chapter_id == ch.id and _has(s)]
        if mentions or sh or sc:
            out.append({"chapter_id": ch.id, "title": ch.title, "series": ch.series,
                        "mentions": mentions, "shots": sh, "scenes": sc})
    return {"entity_id": entity_id, "name": e.name, "kind": e.kind,
            "ref_image": e.ref_image, "voice_name": e.voice_name, "chapters": out,
            "totals": {"chapters": len(out), "mentions": sum(c["mentions"] for c in out),
                       "shots": sum(len(c["shots"]) for c in out),
                       "scenes": sum(len(c["scenes"]) for c in out)}}
```

- [ ] **Étape 5 : vert** — `cd backend && $PY tests/test_chapitres_relationnel.py` → `P1 RELATIONNEL TEST: PASS`. Non-régression : `$PY tests/test_atelier_p2.py` → `ATELIER P2 TEST: PASS` (le découpage paragraphe y est appelé sans bible : `entities == []` reste vrai).

- [ ] **Étape 6 : commit** — sujet `chapitres : le decoupage par paragraphe lie les entites, la fiche liste ses apparitions` ; corps : « P1. `_paragraph_shots` relit nom + alias par `compute_spans` (le moteur du surlignage) ; route `GET /bible/entities/{id}/apparitions` : mentions, plans, scènes par chapitre. 13 assertions. »

### T2 — P1b : `/atelier` — entités éditables sur le plan, apparitions sur la fiche

**Files:**
- Modify: `frontend/atelier/atelier.js:543-549` (`entChips`), `:550-642` (`renderBoard`), `:205-320` (`renderBible`), après `:1212` (nouvelles fonctions)
- Modify: `frontend/atelier/atelier.css` (fin de fichier)
- Test: `backend/tests/test_chapitres_relationnel.py` (banc-miroir de la source, +5 assertions)

- [ ] **Étape 1 : le banc-miroir de la source** — ajouter au test T1 :

```python
def test_la_source_atelier_porte_les_deux_surfaces_p1():
    src = pathlib.Path(__file__).resolve().parents[2].joinpath("frontend/atelier/atelier.js").read_text("utf-8")
    assert src.count("/apparitions") == 1
    assert "shot-ents-edit" in src and "act-apps" in src
    assert "function showApparitions(" in src
    assert "function entPicker(" in src
    css = pathlib.Path(__file__).resolve().parents[2].joinpath("frontend/atelier/atelier.css").read_text("utf-8")
    assert ".entity-apps" in css and ".shot-ents-edit" in css
```

Rouge : `cd backend && $PY tests/test_chapitres_relationnel.py` → `AssertionError` (aucune des chaînes n'existe).

- [ ] **Étape 2 : le sélecteur d'entités du plan** — après `debounce` (`atelier.js:1212`) :

```js
/* ═════════ P1 — plan ↔ entités, apparitions ═════════ */
function entPicker(selected) {
  const sel = new Set(selected || []);
  return `<details class="shot-ents-edit"><summary>⛓ entités du plan</summary>
    ${entities.map(e => `<label class="chip k-${e.kind}"><input type="checkbox" value="${e.id}" ${sel.has(e.id) ? "checked" : ""}> ${esc(e.name)}</label>`).join("")}
  </details>`;
}

async function showApparitions(id, card) {
  const box = card.querySelector(".entity-apps");
  if (!box.classList.contains("hidden")) { box.classList.add("hidden"); return; }
  box.innerHTML = "…"; box.classList.remove("hidden");
  try {
    const a = await api.get(`/bible/entities/${id}/apparitions`);
    const t = a.totals;
    box.innerHTML = `<div class="apps-total">${t.chapters} chapitre(s) · ${t.mentions} mention(s) · ${t.shots} plan(s) · ${t.scenes} scène(s)</div>` +
      (a.chapters.map(c => `<div class="apps-ch"><b>${esc(c.title)}</b> — ${c.mentions} mention(s)
        ${c.shots.map(s => `<button class="btn ghost apps-shot" data-ch="${c.chapter_id}" data-shot="${s.id}" title="${esc(s.action)}">PLAN ${s.idx + 1}</button>`).join("")}
        ${c.scenes.map(s => `<button class="btn ghost apps-scene" data-ch="${c.chapter_id}" title="${esc(s.slugline)}">SC. ${s.idx + 1}</button>`).join("")}</div>`).join("")
       || `<div class="empty-note">Aucune apparition — découpe un chapitre (🎬) ou lie l'entité à un plan.</div>`);
    box.querySelectorAll(".apps-shot").forEach(b => b.addEventListener("click", async () => {
      $("#chapterSelect").value = b.dataset.ch; await openChapter(b.dataset.ch); setMode("board");
      setTimeout(() => { const el = document.querySelector(`.shot-card[data-id="${b.dataset.shot}"]`); if (el) el.scrollIntoView({ block: "center" }); }, 400);
    }));
    box.querySelectorAll(".apps-scene").forEach(b => b.addEventListener("click", async () => {
      $("#chapterSelect").value = b.dataset.ch; await openChapter(b.dataset.ch); setMode("screenplay");
    }));
  } catch (e) { box.innerHTML = `<div class="empty-note">${esc(e.message)}</div>`; }
}
```

- [ ] **Étape 3 : brancher le plan** — dans `renderBoard`, remplacer la ligne `<div class="shot-ents">${entChips(s.entities) || "<span style='opacity:.5'>aucune entité détectée</span>"}</div>` par :

```js
      <div class="shot-ents">${entChips(s.entities) || "<span style='opacity:.5'>aucune entité détectée</span>"}</div>
      ${entPicker(s.entities)}
```

et dans le câblage de la carte, après `card.querySelector(".act-down")…` :

```js
    card.querySelectorAll(".shot-ents-edit input").forEach(cb => cb.addEventListener("change", async () => {
      const ids = [...card.querySelectorAll(".shot-ents-edit input:checked")].map(x => x.value);
      try {
        const up = await api.send("PUT", "/shots/" + id, { entities: ids });
        Object.assign(sh(), up);
        card.querySelector(".shot-ents").innerHTML = entChips(up.entities) || "<span style='opacity:.5'>aucune entité</span>";
      } catch (e) { toast("Entités du plan : " + e.message, true); }
    }));
```

- [ ] **Étape 4 : brancher la fiche** — dans `renderBible`, après `<button class="btn ghost act-del" …>🗑</button>` ajouter `<button class="btn ghost act-apps" title="Où cette entité apparaît : mentions, plans, scènes, chapitre par chapitre">⛓ Apparitions</button>` ; après la ligne `<input class="entity-style" …>` ajouter `<div class="entity-apps hidden"></div>` ; dans le câblage, après `card.querySelector(".act-del")…` : `card.querySelector(".act-apps").addEventListener("click", () => showApparitions(id, card));`.

- [ ] **Étape 5 : CSS** — fin de `atelier.css` :

```css
/* P1 — apparitions et entités du plan */
.entity-apps{font-size:11.5px;color:var(--ink);display:flex;flex-direction:column;gap:6px;padding:8px 10px;border:1px solid var(--stroke);border-radius:var(--r);background:var(--bg-panel-3)}
.apps-total{font-family:var(--f-mono);font-size:10.5px;color:var(--cyan)}
.apps-ch .btn{padding:2px 7px;font-size:10.5px}
.shot-ents-edit{font-size:11px}.shot-ents-edit summary{cursor:pointer;color:var(--ink-muted);font-family:var(--f-mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase}
.shot-ents-edit label{display:inline-flex;align-items:center;gap:4px;margin:3px 3px 0 0;cursor:pointer}
```

- [ ] **Étape 6 : vert + syntaxe** — `node --check frontend/atelier/atelier.js` (vide) ; `cd backend && $PY tests/test_chapitres_relationnel.py` → `P1 RELATIONNEL TEST: PASS`.

- [ ] **Étape 7 : commit** — sujet `chapitres : entites editables sur le plan, apparitions sur la fiche de la bible` ; corps : « P1, surface `/atelier` (page autonome, pas de patch bundle — mesuré). Cases à cocher par plan → PUT /shots ; bouton ⛓ sur la fiche → route apparitions, clic sur un plan ouvre le chapitre en mode storyboard. »

### T3 — P2a : la table des versions et `text_versions.py`

**Files:**
- Modify: `backend/app/services/storage.py:319-325` (après `class AtelierSetting`)
- Create: `backend/app/services/text_versions.py`
- Test: `backend/tests/test_chapitres_versions.py`

**Pourquoi** : réponse 5 — « instantanés + retour arrière à chaque passe LLM ou édition manuelle ». Mesuré : `update_chapter` (`routes.py:5751`) écrase `script_text` sans rien garder ; `_run_adapt_job` (`routes.py:7046`) **supprime toutes les scènes** avant d'écrire les neuves ; `storyboard_decoupe` (`routes.py:5939`) fait de même pour les plans ; `update_scene` (`routes.py:6790`) écrase `fountain_text`. Quatre écrasements silencieux. Le dépôt a déjà le patron (`vector_store.ecrire`, 10 versions) — on le porte en SQLite parce que le texte versionné est déjà en base.

- [ ] **Étape 1 : le test qui échoue** — `backend/tests/test_chapitres_versions.py` (16 assertions)

```python
"""P2 — versions du texte : instantané, historique élagué à 10, comparaison
ligne à ligne, restauration. 16 assertions (T3) + 12 (T4) + 5 (T5).
Run: <embedded python> backend/tests/test_chapitres_versions.py"""
import asyncio, os, sys, tempfile, pathlib, types
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.modules["fal_client"] = types.ModuleType("fal_client")
from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.main import app                               # noqa: E402
from app.services.storage import init_db, async_session_factory  # noqa: E402
from app.services import text_versions as TV           # noqa: E402


def test_la_comparaison_est_ligne_a_ligne_et_compte():
    d = TV.diff("un\ndeux\ntrois", "un\nDEUX\ntrois\nquatre")
    assert d["identiques"] == 2
    assert d["ajoutees"] == 2 and d["supprimees"] == 1
    assert [l["op"] for l in d["lignes"]] == ["=", "~", "=", "+"]
    assert d["lignes"][1] == {"op": "~", "a": "deux", "b": "DEUX"}
    assert TV.diff("x", "x")["ajoutees"] == 0


def test_l_instantane_garde_dix_versions_et_refuse_les_doublons():
    async def scenario():
        await init_db()
        async with async_session_factory() as s:
            assert await TV.snapshot(s, "chapter", "c1", "", "manuelle") is None
            v = await TV.snapshot(s, "chapter", "c1", "alpha", "manuelle")
            assert v["n"] == 1 and v["passe"] == "manuelle"
            assert await TV.snapshot(s, "chapter", "c1", "alpha", "manuelle") is None
            for i in range(2, 15):
                v = await TV.snapshot(s, "chapter", "c1", f"texte {i}", "decoupe")
            assert v["n"] == 14
            h = await TV.historique(s, "chapter", "c1")
            assert len(h) == 10, f"{len(h)} versions gardees (10 attendues)"
            assert [x["n"] for x in h] == list(range(14, 4, -1))
            assert h[0]["apercu"].startswith("texte 14")
            assert "text" not in h[0], "l'historique est une liste, pas un dump"
            assert await TV.historique(s, "scene", "c1") == []
            plein = await TV.lire(s, h[0]["id"])
            assert plein["text"] == "texte 14" and plein["meta"] == {}
            assert await TV.lire(s, "inconnu") is None
    asyncio.run(scenario())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for _f in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        _f()
    print("P2 VERSIONS TEST: PASS")
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_versions.py` → `ModuleNotFoundError: No module named 'app.services.text_versions'`.

- [ ] **Étape 3 : la table** — dans `storage.py`, après `class AtelierSetting` (`:319-325`) :

```python
class TextVersion(Base):
    """P2 (03/09/2026) — un instantané du texte AVANT une écriture qui
    l'aurait perdu : édition manuelle, adaptation, découpe, réécriture,
    import. `kind` = chapter (script_text) | scene (fountain_text) ;
    `n` numérote les instantanés d'une cible ; l'historique est élagué aux
    10 derniers (même garde que vector_store._GARDE_HISTORIQUE). Table
    NEUVE : create_all suffit, aucune colonne à migrer."""
    __tablename__ = "text_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), index=True)
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    n: Mapped[int] = mapped_column(Integer, default=1)
    passe: Mapped[str] = mapped_column(String(16), default="manuelle")
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow)
```

- [ ] **Étape 4 : le service** — `backend/app/services/text_versions.py` :

```python
"""P2 (03/09/2026) — versions du texte des chapitres et des scènes.

Règle unique : `snapshot` écrit l'ANCIEN texte — celui qui va disparaître —
jamais le neuf. C'est ce qui permet de revenir en arrière APRÈS avoir vu le
résultat de la passe. Un texte vide, ou identique au dernier instantané, ne
crée rien (sinon dix passes sans effet chassent l'historique utile).

Stdlib seule (difflib) : ni LLM, ni réseau, ni numpy.
"""
from __future__ import annotations

import difflib
import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select

GARDE = 10
KINDS = ("chapter", "scene")
PASSES = ("manuelle", "adaptation", "decoupe", "reecriture", "import",
          "restauration")


def _dict(v, plein: bool = False) -> dict:
    d = {"id": v.id, "kind": v.kind, "target_id": v.target_id, "n": v.n,
         "passe": v.passe, "taille": len(v.text or ""),
         "apercu": (v.text or "")[:120].replace("\n", " "),
         "created_at": v.created_at.isoformat() if v.created_at else None}
    if plein:
        d["text"] = v.text or ""
        try:
            d["meta"] = json.loads(v.meta) if v.meta else {}
        except ValueError:
            d["meta"] = {}
    return d


async def _rows(session, kind: str, target_id: str):
    from app.services.storage import TextVersion
    return (await session.execute(
        select(TextVersion).where(TextVersion.kind == kind,
                                  TextVersion.target_id == target_id)
        .order_by(TextVersion.n.desc()))).scalars().all()


async def snapshot(session, kind: str, target_id: str, ancien: str,
                   passe: str, meta: dict | None = None) -> dict | None:
    """Garde `ancien` avant qu'il soit écrasé. Rend le dict de la version
    créée, ou None quand il n'y avait rien à garder (texte vide, ou
    identique au dernier instantané)."""
    from app.services.storage import TextVersion
    if kind not in KINDS:
        raise ValueError(f"kind inconnu: {kind}")
    ancien = ancien or ""
    if not ancien.strip():
        return None
    rows = await _rows(session, kind, target_id)
    if rows and (rows[0].text or "") == ancien:
        return None
    v = TextVersion(id=str(uuid4()), kind=kind, target_id=target_id,
                    n=(rows[0].n + 1) if rows else 1,
                    passe=passe if passe in PASSES else "manuelle",
                    text=ancien,
                    meta=json.dumps(meta or {}, ensure_ascii=False),
                    created_at=datetime.utcnow())
    session.add(v)
    for vieux in rows[GARDE - 1:]:
        await session.delete(vieux)
    await session.commit()
    return _dict(v)


async def historique(session, kind: str, target_id: str) -> list[dict]:
    """Du plus récent au plus ancien, SANS le texte (aperçu + taille) — la
    liste sert une barre latérale, pas un dump de dix chapitres."""
    return [_dict(v) for v in await _rows(session, kind, target_id)]


async def lire(session, version_id: str) -> dict | None:
    from app.services.storage import TextVersion
    v = await session.get(TextVersion, version_id)
    return _dict(v, plein=True) if v else None


def diff(ancien: str, neuf: str) -> dict:
    """Comparaison LIGNE À LIGNE : la matière du côte à côte. Chaque entrée
    de `lignes` est une paire alignée ; `None` d'un côté = ligne absente de
    ce côté. `~` = ligne modifiée, `+`/`-` = ajoutée/supprimée."""
    a = (ancien or "").splitlines()
    b = (neuf or "").splitlines()
    lignes: list[dict] = []
    ajout = retire = 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(
            a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                lignes.append({"op": "=", "a": a[i1 + k], "b": b[j1 + k]})
        elif op == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                ga = a[i1 + k] if i1 + k < i2 else None
                gb = b[j1 + k] if j1 + k < j2 else None
                lignes.append({"op": "~", "a": ga, "b": gb})
                if ga is not None:
                    retire += 1
                if gb is not None:
                    ajout += 1
        elif op == "delete":
            for k in range(i1, i2):
                lignes.append({"op": "-", "a": a[k], "b": None})
                retire += 1
        else:
            for k in range(j1, j2):
                lignes.append({"op": "+", "a": None, "b": b[k]})
                ajout += 1
    return {"lignes": lignes, "ajoutees": ajout, "supprimees": retire,
            "identiques": sum(1 for x in lignes if x["op"] == "=")}


async def restaurer(session, version_id: str) -> dict | None:
    """Réécrit la cible avec le texte de la version — APRÈS avoir gardé le
    texte courant en instantané `restauration`. Rien n'est perdu, dans les
    deux sens. Rend {kind, target_id, text} ou None (version inconnue)."""
    from app.services.storage import Chapter, Scene, TextVersion
    v = await session.get(TextVersion, version_id)
    if not v:
        return None
    if v.kind == "chapter":
        cible = await session.get(Chapter, v.target_id)
        courant = (cible.script_text or "") if cible else ""
    else:
        cible = await session.get(Scene, v.target_id)
        courant = (cible.fountain_text or "") if cible else ""
    if not cible:
        return None
    await snapshot(session, v.kind, v.target_id, courant, "restauration",
                   {"depuis": v.id, "n": v.n})
    if v.kind == "chapter":
        cible.script_text = v.text or ""
    else:
        cible.fountain_text = v.text or ""
    cible.updated_at = datetime.utcnow()
    await session.commit()
    return {"kind": v.kind, "target_id": v.target_id, "text": v.text or ""}
```

- [ ] **Étape 5 : vert** — `cd backend && $PY tests/test_chapitres_versions.py` → `P2 VERSIONS TEST: PASS`.

- [ ] **Étape 6 : commit**

```bash
git add backend/app/services/text_versions.py backend/app/services/storage.py backend/tests/test_chapitres_versions.py && git commit -F - <<'EOF'
chapitres : la table des versions du texte et son service

P2. Quatre ecrasements silencieux mesures (update_chapter routes.py:5751,
update_scene :6790, storyboard_decoupe :5939, _run_adapt_job :7046).
`snapshot` garde l'ANCIEN texte, jamais le neuf ; historique elague a 10
(la garde de vector_store) ; `diff` ligne a ligne par difflib ; `restaurer`
prend lui-meme un instantane avant d'ecrire. Table neuve : create_all
suffit. 16 assertions.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

### T4 — P2b : les routes, et l'instantané posé aux quatre points d'écrasement

**Files:**
- Modify: `backend/app/api/routes.py:5751-5771` (`update_chapter`), `:5939-5987` (`storyboard_decoupe`), `:6790-6828` (`update_scene`), `:7046-7130` (`_run_adapt_job`) ; routes neuves avant `@router.delete("/chapters/{chapter_id}")` (`:5773`)
- Test: `backend/tests/test_chapitres_versions.py` (+12 assertions)

- [ ] **Étape 1 : le test qui échoue** — ajouter au fichier de T3 :

```python
def test_les_routes_versions_et_les_points_d_ecrasement():
    async def scenario():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            ch = (await c.post("/api/chapters", json={
                "title": "V", "script_text": "premier jet\n\nsecond para"})).json()
            assert (await c.get(f"/api/chapters/{ch['id']}/versions")).json()["versions"] == []
            await c.put(f"/api/chapters/{ch['id']}",
                        json={"script_text": "deuxieme jet\n\nsecond para"})
            await c.put(f"/api/chapters/{ch['id']}", json={"title": "V2"})
            vs = (await c.get(f"/api/chapters/{ch['id']}/versions")).json()["versions"]
            assert len(vs) == 1, f"{len(vs)} versions (1 : le titre ne versionne pas)"
            assert vs[0]["passe"] == "manuelle"
            assert vs[0]["apercu"].startswith("premier jet")
            r = await c.post(f"/api/chapters/{ch['id']}/storyboard/decoupe",
                             json={"method": "paragraph"})
            assert r.status_code == 200, r.text
            vs = (await c.get(f"/api/chapters/{ch['id']}/versions")).json()["versions"]
            assert [v["passe"] for v in vs] == ["decoupe", "manuelle"]
            d = (await c.get(f"/api/versions/{vs[1]['id']}/diff")).json()
            assert d["ajoutees"] == 1 and d["supprimees"] == 1
            assert d["lignes"][0] == {"op": "~", "a": "premier jet", "b": "deuxieme jet"}
            r = await c.post(f"/api/versions/{vs[1]['id']}/restore")
            assert r.status_code == 200 and r.json()["text"].startswith("premier jet")
            got = (await c.get(f"/api/chapters/{ch['id']}")).json()["script_text"]
            assert got.startswith("premier jet")
            vs = (await c.get(f"/api/chapters/{ch['id']}/versions")).json()["versions"]
            assert vs[0]["passe"] == "restauration", "la restauration se garde aussi"
            assert (await c.post("/api/versions/inconnu/restore")).status_code == 404
    asyncio.run(scenario())
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_versions.py` → `AssertionError` (la route `/versions` répond 404, `.json()["versions"]` lève `KeyError`).

- [ ] **Étape 3 : les routes** — dans `routes.py`, juste avant `@router.delete("/chapters/{chapter_id}")` (`:5773`) :

```python
@router.get("/chapters/{chapter_id}/versions")
async def chapter_versions(chapter_id: str):
    """P2 — l'historique du manuscrit du chapitre (10 derniers, sans le
    texte : aperçu, taille, passe)."""
    from app.services import text_versions as TV
    from app.services.storage import async_session_factory
    async with async_session_factory() as session:
        return {"versions": await TV.historique(session, "chapter", chapter_id)}


@router.get("/scenes/{scene_id}/versions")
async def scene_versions(scene_id: str):
    from app.services import text_versions as TV
    from app.services.storage import async_session_factory
    async with async_session_factory() as session:
        return {"versions": await TV.historique(session, "scene", scene_id)}


@router.get("/versions/{version_id}")
async def read_version(version_id: str):
    from app.services import text_versions as TV
    from app.services.storage import async_session_factory
    async with async_session_factory() as session:
        v = await TV.lire(session, version_id)
    if not v:
        raise HTTPException(404, "Version not found")
    return v


@router.get("/versions/{version_id}/diff")
async def diff_version(version_id: str):
    """La version FACE au texte courant de sa cible — le côte à côte."""
    from app.services import text_versions as TV
    from app.services.storage import Chapter, Scene, async_session_factory
    async with async_session_factory() as session:
        v = await TV.lire(session, version_id)
        if not v:
            raise HTTPException(404, "Version not found")
        if v["kind"] == "chapter":
            cible = await session.get(Chapter, v["target_id"])
            courant = (cible.script_text or "") if cible else ""
        else:
            cible = await session.get(Scene, v["target_id"])
            courant = (cible.fountain_text or "") if cible else ""
    out = TV.diff(v["text"], courant)
    out.update({"version": {k: v[k] for k in ("id", "n", "passe", "created_at")},
                "kind": v["kind"], "target_id": v["target_id"]})
    return out


@router.post("/versions/{version_id}/restore")
async def restore_version(version_id: str):
    """Réécrit la cible avec cette version — après avoir gardé le courant."""
    from app.services import text_versions as TV
    from app.services.storage import async_session_factory
    async with async_session_factory() as session:
        out = await TV.restaurer(session, version_id)
    if not out:
        raise HTTPException(404, "Version not found")
    return out
```

- [ ] **Étape 4 : les quatre points d'écrasement** — quatre insertions, chacune AVANT l'écriture :

1. `update_chapter` (`routes.py:5751`) — remplacer les deux lignes `if "script_text" in body:` / `ch.script_text = body["script_text"] or ""` par :

```python
        if "script_text" in body:
            neuf = body["script_text"] or ""
            if neuf != (ch.script_text or ""):
                from app.services import text_versions as TV
                await TV.snapshot(session, "chapter", ch.id,
                                  ch.script_text or "", "manuelle")
            ch.script_text = neuf
```

2. `storyboard_decoupe` (`routes.py:5952`) — juste après `raise HTTPException(400, "Le chapitre est vide")`, avant `drafts = []` :

```python
        from app.services import text_versions as TV
        await TV.snapshot(session, "chapter", chapter_id, script, "decoupe",
                          {"method": method})
```

3. `update_scene` (`routes.py:6797`) — remplacer la boucle `for k in ("fountain_text", "camera_notes"):` par :

```python
        if ("fountain_text" in body
                and (body["fountain_text"] or "") != (s.fountain_text or "")):
            from app.services import text_versions as TV
            await TV.snapshot(session, "scene", s.id, s.fountain_text or "",
                              "manuelle")
        for k in ("fountain_text", "camera_notes"):
            if k in body:
                setattr(s, k, body[k] or "")
```

4. `_run_adapt_job` (`routes.py:7095`) — remplacer les deux lignes `for s in await _list_scenes(session, chapter_id):` / `await session.delete(s)` par :

```python
            from app.services import text_versions as TV
            for s in await _list_scenes(session, chapter_id):
                await TV.snapshot(session, "scene", s.id,
                                  s.fountain_text or "", "adaptation",
                                  {"slugline": s.slugline})
                await session.delete(s)
```

- [ ] **Étape 5 : vert** — `cd backend && $PY tests/test_chapitres_versions.py` → `P2 VERSIONS TEST: PASS`. Non-régression, un processus chacun : `$PY tests/test_screenplay.py` → `SCREENPLAY TEST: PASS` ; `$PY tests/test_atelier_p2.py` → `ATELIER P2 TEST: PASS` ; `$PY tests/test_manuscript.py` → `MANUSCRIT AGENT TEST: PASS`.

- [ ] **Étape 6 : commit** — sujet `chapitres : les routes de versions, et l'instantane pose aux quatre ecrasements` ; corps accentué : « P2. `GET /chapters/{id}/versions`, `/scenes/{id}/versions`, `GET /versions/{id}`, `/diff`, `POST /restore`. Instantané avant : édition du manuscrit (un titre seul ne versionne pas), découpe, édition de scène, adaptation. 12 assertions de plus. »

### T5 — P2c : `/atelier` — le tiroir des versions, le côte à côte, la restauration

**Files:**
- Modify: `frontend/atelier/index.html:19` (après `#saveState`), `:252` (avant `#toast`)
- Modify: `frontend/atelier/atelier.js` après `:1212` (`debounce`), wiring `:1228`
- Modify: `frontend/atelier/atelier.css` (fin de fichier)
- Test: `backend/tests/test_chapitres_versions.py` (+5 assertions, banc-miroir de la source)

- [ ] **Étape 1 : le banc-miroir** — ajouter au fichier :

```python
def test_la_source_atelier_porte_le_tiroir_des_versions():
    r = pathlib.Path(__file__).resolve().parents[2]
    js = r.joinpath("frontend/atelier/atelier.js").read_text("utf-8")
    html = r.joinpath("frontend/atelier/index.html").read_text("utf-8")
    css = r.joinpath("frontend/atelier/atelier.css").read_text("utf-8")
    assert js.count("/versions") >= 2 and "/restore" in js
    assert "function openVersions(" in js and "async function renderDiff(" in js
    assert 'id="verModal"' in html and 'id="verBtn"' in html
    assert js.count("verList") >= 2
    assert ".ver-mod" in css and ".ver-add" in css and ".ver-del" in css
```

Rouge : `cd backend && $PY tests/test_chapitres_versions.py` → `AssertionError` sur `js.count("/versions") >= 2`.

- [ ] **Étape 2 : le bouton et la modale** — `index.html`, après `<span id="saveState" class="savestate">—</span>` (`:19`) :

```html
    <button id="verBtn" class="btn ghost" title="Versions du manuscrit : chaque passe (édition, découpe, adaptation, réécriture) a laissé un instantané — comparer et revenir en arrière">🕘 Versions</button>
```

et avant `<div id="toast" class="toast hidden"></div>` (`:252`) :

```html
<div id="verModal" class="modal hidden">
  <div class="modal-box wide">
    <div class="modal-head">
      <b>Versions du texte</b>
      <span id="verNote" class="da-note"></span>
      <button id="verClose" class="btn ghost">✕</button>
    </div>
    <div class="ver-body">
      <div id="verList" class="ver-list"></div>
      <div id="verDiff" class="ver-diff"><div class="empty-note">Choisis une version à gauche : le côte à côte compare cet instantané au texte courant.</div></div>
    </div>
  </div>
</div>
```

- [ ] **Étape 3 : le JS** — après `debounce` (`atelier.js:1212`) :

```js
/* ═════════ P2 — versions du texte ═════════ */
const PASSE_LABEL = { manuelle: "édition", decoupe: "découpe",
                      adaptation: "adaptation", reecriture: "réécriture",
                      import: "import", restauration: "retour arrière" };

function openVersions() {
  if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
  $("#verModal").classList.remove("hidden");
  $("#verDiff").innerHTML = `<div class="empty-note">Choisis une version à gauche.</div>`;
  const list = $("#verList");
  list.innerHTML = "…";
  api.get(`/chapters/${chapter.id}/versions`).then(({ versions }) => {
    $("#verNote").textContent = `${versions.length}/10 instantanés — « ${chapter.title} »`;
    if (!versions.length) {
      list.innerHTML = `<div class="empty-note">Aucun instantané : rien n'a encore été écrasé sur ce chapitre.</div>`;
      return;
    }
    list.innerHTML = versions.map(v => `
      <div class="ver-item" data-id="${v.id}">
        <div class="ver-line"><b>v${v.n}</b> · ${PASSE_LABEL[v.passe] || v.passe}
          <span class="ver-size">${v.taille} car.</span></div>
        <div class="ver-when">${(v.created_at || "").replace("T", " ").slice(0, 19)}</div>
        <div class="ver-prev">${esc(v.apercu)}…</div>
      </div>`).join("");
    list.querySelectorAll(".ver-item").forEach(el =>
      el.addEventListener("click", () => {
        list.querySelectorAll(".ver-item").forEach(x => x.classList.remove("sel"));
        el.classList.add("sel");
        renderDiff(el.dataset.id);
      }));
  }).catch(e => { list.innerHTML = `<div class="empty-note">${esc(e.message)}</div>`; });
}

async function renderDiff(vid) {
  const box = $("#verDiff");
  box.innerHTML = "…";
  try {
    const d = await api.get(`/versions/${vid}/diff`);
    const cls = { "=": "ver-same", "~": "ver-mod", "+": "ver-add", "-": "ver-del" };
    const col = (k) => d.lignes.map(l =>
      `<div class="ver-l ${cls[l.op]}">${l[k] === null ? "" : (esc(l[k]) || "&nbsp;")}</div>`).join("");
    box.innerHTML = `
      <div class="ver-diff-head">
        <span>v${d.version.n} · ${PASSE_LABEL[d.version.passe] || d.version.passe}</span>
        <span class="ver-counts">+${d.ajoutees} / −${d.supprimees} · ${d.identiques} inchangées</span>
        <button id="verRestore" class="btn primary" title="Réécrit le chapitre avec cette version — le texte courant est gardé en instantané avant.">↩ Restaurer</button>
      </div>
      <div class="ver-cols">
        <div class="ver-col"><header>instantané</header>${col("a")}</div>
        <div class="ver-col"><header>texte courant</header>${col("b")}</div>
      </div>`;
    $("#verRestore").addEventListener("click", async () => {
      if (!confirm("Restaurer cette version ? Le texte courant est gardé en instantané.")) return;
      try {
        const out = await api.send("POST", `/versions/${vid}/restore`);
        $("#script").value = out.text;
        chapter.script_text = out.text;
        renderScript();
        $("#verModal").classList.add("hidden");
        toast("Version restaurée — le texte précédent est dans l'historique.");
      } catch (e) { toast("Restauration échouée : " + e.message, true); }
    });
  } catch (e) { box.innerHTML = `<div class="empty-note">${esc(e.message)}</div>`; }
}
```

et dans le wiring, après `["#chapterTitle", "#chapterSeries"].forEach(…)` (`atelier.js:1228`) :

```js
  $("#verBtn").addEventListener("click", openVersions);
  $("#verClose").addEventListener("click", () => $("#verModal").classList.add("hidden"));
```

- [ ] **Étape 4 : CSS** — fin de `atelier.css` :

```css
/* P2 — tiroir des versions */
.modal-box.wide{max-width:1100px;width:92vw}
.ver-body{display:grid;grid-template-columns:260px 1fr;gap:12px;max-height:70vh}
.ver-list{overflow:auto;display:flex;flex-direction:column;gap:6px}
.ver-item{padding:7px 9px;border:1px solid var(--stroke);border-radius:var(--r);cursor:pointer;background:var(--bg-panel-2)}
.ver-item.sel{border-color:var(--cyan)}
.ver-size,.ver-when{font-family:var(--f-mono);font-size:10px;color:var(--ink-muted)}
.ver-prev{font-size:11px;color:var(--ink-soft);margin-top:3px}
.ver-diff{overflow:auto}
.ver-diff-head{display:flex;align-items:center;gap:12px;margin-bottom:8px;font-size:12px}
.ver-counts{font-family:var(--f-mono);font-size:11px;color:var(--ink-muted)}
.ver-cols{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.ver-col header{font-family:var(--f-mono);font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-muted);padding-bottom:4px}
.ver-l{font-family:var(--f-mono);font-size:11px;white-space:pre-wrap;padding:1px 5px;border-left:2px solid transparent;min-height:14px}
.ver-mod{background:rgba(245,183,49,.14);border-left-color:var(--amber)}
.ver-add{background:rgba(60,200,120,.14);border-left-color:var(--green)}
.ver-del{background:rgba(230,80,80,.14);border-left-color:var(--red)}
```

- [ ] **Étape 5 : vert + syntaxe** — `node --check frontend/atelier/atelier.js` (sortie vide) ; `cd backend && $PY tests/test_chapitres_versions.py` → `P2 VERSIONS TEST: PASS`.

- [ ] **Étape 6 : commit** — sujet `chapitres : le tiroir des versions, le cote a cote et le retour arriere` ; corps : « P2, surface `/atelier` (page autonome — aucun patch du bundle, mesuré). Bouton 🕘 Versions ; liste des 10 instantanés (passe, taille, aperçu) ; côte à côte en lignes alignées ; ↩ Restaurer garde le courant avant d'écrire. 5 assertions de miroir. »

### T6 — P3a : `identity_drift.py`, la mesure de dérive en PIL pur — et ce qu'elle ne mesure pas

**Files:**
- Create: `backend/app/services/identity_drift.py`
- Test: `backend/tests/test_chapitres_derive.py`

**Pourquoi** : réponse 3 — « non, même les images dérivent (visage, costume, palette) ». Un plan qui améliore la cohérence sans mesure ne peut être ni validé ni défendu. Mesure du dépôt : `numpy` **absent** du python embarqué (`python -c "import numpy"` → `ModuleNotFoundError`, 03/09), Pillow 12.3.0 présent. Donc la mesure est en PIL pur, et son honnêteté vient de ce qu'elle **déclare son angle mort**.

- [ ] **Étape 1 : le test qui échoue** — `backend/tests/test_chapitres_derive.py` (16 assertions)

```python
"""P3 — banc de dérive d'identité (PIL pur, aucun réseau, aucun modèle).
Fixtures SYNTHÉTIQUES : on connaît la perturbation, on vérifie que la mesure
bouge du bon côté — et qu'elle NE bouge PAS sur son angle mort déclaré.
16 assertions. Run: <embedded python> backend/tests/test_chapitres_derive.py"""
import os, sys, pathlib, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import Image, ImageDraw                       # noqa: E402
from app.services import identity_drift as ID          # noqa: E402

TMP = pathlib.Path(tempfile.mkdtemp())
FOND = (242, 239, 233)          # board_service._BG, le fond des planches


def figure(nom, *, cape=(30, 60, 140), peau=(226, 190, 160), larg=90,
           yeux=(20, 20, 20), fond=FOND):
    """Un personnage schématique sur fond d'atelier : cape (le costume),
    tête (la peau), deux yeux (les traits). Chaque paramètre isole UN axe."""
    im = Image.new("RGB", (320, 480), fond)
    d = ImageDraw.Draw(im)
    d.rectangle([160 - larg, 220, 160 + larg, 440], fill=cape)
    d.ellipse([120, 90, 200, 200], fill=peau)
    d.ellipse([138, 130, 150, 142], fill=yeux)
    d.ellipse([170, 130, 182, 142], fill=yeux)
    p = TMP / f"{nom}.png"
    im.save(p)
    return p


def test_deux_images_identiques_ne_derivent_pas():
    a = figure("a")
    d = ID.derive(a, a)
    assert d["ecart_couleur"] == 0.0
    assert d["ecart_silhouette"] == 0.0
    assert d["verdict"] == "stable"


def test_le_costume_qui_change_de_teinte_bouge_la_couleur_pas_la_silhouette():
    a, b = figure("a"), figure("b_cape", cape=(150, 40, 40))
    d = ID.derive(a, b)
    assert d["ecart_couleur"] > 15, d
    assert d["ecart_silhouette"] < 0.02, d
    assert d["verdict"] == "derive"


def test_la_carrure_qui_grossit_bouge_la_silhouette_pas_la_couleur():
    a, b = figure("a"), figure("b_larg", larg=140)
    d = ID.derive(a, b)
    assert d["ecart_silhouette"] > 0.15, d
    assert d["ecart_couleur"] < 4.0, d


def test_l_angle_mort_est_mesure_et_dit_le_visage_ne_compte_pas():
    """Deux figures au même costume, à la même carrure, aux YEUX différents :
    la mesure sort à ~0. Ce n'est pas un bug, c'est la limite déclarée du
    banc — assertée pour qu'on ne l'oublie jamais."""
    a, b = figure("a"), figure("b_yeux", yeux=(210, 40, 40))
    d = ID.derive(a, b)
    assert d["ecart_couleur"] < 2.0, d
    assert d["ecart_silhouette"] < 0.02, d
    assert d["verdict"] == "stable"
    assert "visage" in ID.CE_QUE_CA_NE_MESURE_PAS.lower()


def test_la_palette_est_ordonnee_par_poids_et_somme_a_un():
    p = ID.palette(Image.open(figure("a")))
    assert 2 <= len(p) <= 8
    assert p == sorted(p, reverse=True)
    assert abs(sum(w for w, _ in p) - 1.0) < 1e-6
    assert max(p)[0] > 0.4, "le fond domine la planche"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for _f in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        _f()
    print("P3 DERIVE TEST: PASS")
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_derive.py` → `ModuleNotFoundError: No module named 'app.services.identity_drift'`.

- [ ] **Étape 3 : le service** — `backend/app/services/identity_drift.py` :

```python
"""P3 (03/09/2026) — mesurer la dérive d'identité entre deux images, en PIL
pur (numpy est ABSENT du python embarqué — mesuré le 03/09).

CE QUE ÇA MESURE
  1. `ecart_couleur` — la distance entre les PALETTES. Les 8 couleurs
     dominantes de chaque image (PIL.quantize, MEDIANCUT, le moteur déjà
     employé par board_service._palette_colors), appariées au plus proche
     voisin dans les DEUX sens, en ΔE76 sur L*a*b*, pondérées par la part de
     surface. Un costume qui change de teinte, une peau qui vire, une lumière
     qui bascule : la mesure bouge. Unité : ΔE (0 = identique ; ~2,3 = seuil
     de perception ; > 10 = deux couleurs franchement différentes).
  2. `ecart_silhouette` — la distance entre les OCCUPATIONS. Chaque image est
     réduite à une grille 16×16 de « sujet / fond », le fond étant la couleur
     la plus fréquente du BORD de l'image (les panneaux de planche sont sur
     fond d'atelier uni, board_service._BG). Distance = 1 − Jaccard. Une
     carrure qui grossit, une cape qui apparaît, un cadrage qui glisse : la
     mesure bouge. Unité : 0 (mêmes cases) à 1 (aucune case commune).

CE QUE ÇA NE MESURE PAS — et ne pourra pas dans ce runtime
  - LE VISAGE. Aucun modèle d'identité faciale n'est embarqué, et il n'y en
    aura pas sans numpy. Deux figures au même costume, à la même carrure et
    au même fond, mais aux traits différents, sortent à 0. Le banc est une
    ALARME DE RÉGRESSION (« passer 6 références au lieu d'une a-t-il réduit
    la dérive mesurée ? »), jamais une preuve d'identité.
  - LA COMPARAISON ENTRE NATURES DIFFÉRENTES. Un plan large avec décor, ciel
    et deux personnages n'a ni la palette ni l'occupation d'un panneau de
    planche sur fond uni. Comparer panneau ↔ panneau, ou plan ↔ plan ; pas
    l'un à l'autre. La fonction ne l'interdit pas, elle le dit ici.
  - LA POSE. Un personnage identique vu de dos change de silhouette autant
    qu'un personnage remplacé.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from PIL import Image

CE_QUE_CA_NE_MESURE_PAS = (
    "le visage (aucun modele d'identite faciale, numpy absent), la "
    "comparaison entre natures d'image differentes, et la pose"
)

SEUIL_COULEUR = 8.0     # ΔE76 au-dela duquel on parle de derive
SEUIL_SILHOUETTE = 0.12  # Jaccard complementaire au-dela duquel idem


def _lin(c: int) -> float:
    v = c / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _f(t: float) -> float:
    return t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29


def lab(rgb) -> tuple[float, float, float]:
    """sRGB (0-255) -> CIE L*a*b* D65. Pur Python, ~2 us l'appel."""
    r, g, b = _lin(rgb[0]), _lin(rgb[1]), _lin(rgb[2])
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    fx, fy, fz = _f(x), _f(y), _f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def de76(a, b) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
            + (a[2] - b[2]) ** 2) ** 0.5


def palette(im: Image.Image, n: int = 8) -> list[tuple[float, tuple]]:
    """[(part de surface, (r,g,b))], du plus dominant au moins. Somme = 1."""
    small = im.convert("RGB").resize((96, 96), Image.LANCZOS)
    q = small.quantize(colors=n, method=Image.Quantize.MEDIANCUT,
                       dither=Image.Dither.NONE)
    pal = q.getpalette()[: n * 3]
    counts = {i: c for c, i in (q.getcolors(n * 4) or [])}
    total = sum(counts.values()) or 1
    out = [(counts[i] / total, tuple(pal[i * 3:i * 3 + 3]))
           for i in sorted(counts) if counts[i]]
    return sorted(out, reverse=True)


def _sens(a, b) -> float:
    labs_b = [lab(c) for _, c in b]
    return sum(w * min(de76(lab(c), lb) for lb in labs_b) for w, c in a)


def ecart_couleur(pa, pb) -> float:
    """ΔE76 moyen, apparié au plus proche voisin dans les DEUX sens : un seul
    sens récompenserait l'image la plus pauvre en couleurs."""
    if not pa or not pb:
        return 100.0
    return round((_sens(pa, pb) + _sens(pb, pa)) / 2, 3)


def _fond(im: Image.Image) -> tuple[int, int, int]:
    """La couleur du BORD, arrondie au pas de 16 : le fond d'atelier."""
    w, h = im.size
    px = im.load()
    bord = ([px[x, 0] for x in range(w)] + [px[x, h - 1] for x in range(w)]
            + [px[0, y] for y in range(h)] + [px[w - 1, y] for y in range(h)])
    c = Counter((r // 16 * 16, g // 16 * 16, b // 16 * 16) for r, g, b in bord)
    return c.most_common(1)[0][0]


def occupation(im: Image.Image, grille: int = 16,
               seuil: float = 12.0) -> list[bool]:
    """Grille grille×grille : True = la case est majoritairement du SUJET
    (plus de la moitié de ses pixels à plus de `seuil` ΔE du fond)."""
    small = im.convert("RGB").resize((grille * 4, grille * 4), Image.LANCZOS)
    lf = lab(_fond(small))
    px = small.load()
    cells = []
    for cy in range(grille):
        for cx in range(grille):
            sujet = 0
            for y in range(cy * 4, cy * 4 + 4):
                for x in range(cx * 4, cx * 4 + 4):
                    if de76(lab(px[x, y]), lf) > seuil:
                        sujet += 1
            cells.append(sujet > 8)
    return cells


def ecart_silhouette(oa: list[bool], ob: list[bool]) -> float:
    """1 − Jaccard. Deux images sans aucun sujet détecté : 0 (rien à
    comparer, on ne crie pas au loup)."""
    inter = sum(1 for a, b in zip(oa, ob) if a and b)
    union = sum(1 for a, b in zip(oa, ob) if a or b)
    return 0.0 if not union else round(1 - inter / union, 4)


def derive(reference, genere) -> dict:
    """La mesure complète entre deux fichiers image (chemins ou Image).
    `verdict` = "stable" tant que les DEUX écarts sont sous leur seuil."""
    a = reference if isinstance(reference, Image.Image) \
        else Image.open(Path(reference))
    b = genere if isinstance(genere, Image.Image) else Image.open(Path(genere))
    ec = ecart_couleur(palette(a), palette(b))
    es = ecart_silhouette(occupation(a), occupation(b))
    return {"ecart_couleur": ec, "ecart_silhouette": es,
            "verdict": ("stable" if ec <= SEUIL_COULEUR
                        and es <= SEUIL_SILHOUETTE else "derive"),
            "seuils": {"couleur": SEUIL_COULEUR,
                       "silhouette": SEUIL_SILHOUETTE},
            "angle_mort": CE_QUE_CA_NE_MESURE_PAS}
```

- [ ] **Étape 4 : vert** — `cd backend && $PY tests/test_chapitres_derive.py` → `P3 DERIVE TEST: PASS`.

- [ ] **Étape 5 : commit** — sujet `chapitres : le banc de derive d'identite, en PIL pur, et son angle mort` ; corps : « P3. Deux axes indépendants : ΔE76 entre palettes pondérées (couleur) et 1 − Jaccard d'une occupation 16×16 relative au fond du bord (silhouette). Fixtures synthétiques : la teinte du costume bouge la couleur sans la silhouette, la carrure l'inverse. L'angle mort — le visage — est ASSERTÉ, pas commenté : numpy est absent du python embarqué (mesuré 03/09). 16 assertions. »

### T7 — P3b : la recette de planche garde ses panneaux (v3), et la route « vues »

**Files:**
- Modify: `backend/app/api/routes.py:5419` et `:5430` (garde `v == 2`), `:5561-5562` (`recipe_panels.append`), `:5565-5566` (miroirs), `:5579-5582` (écriture de la recette) ; route neuve avant `@router.post("/bible/entities/{entity_id}/suggest-voice")` (`:5628`)
- Test: `backend/tests/test_chapitres_references.py`

**Pourquoi** : pour passer PLUSIEURS références à un générateur, il faut savoir où sont les vues. Mesuré : la recette v2 (`routes.py:5561`) garde `key`/`prompt`/`seed`/`model` — **pas le nom de fichier du panneau** ; seule la planche composite (`e.ref_image`) survit, et un modèle qui reçoit une planche 4 colonnes reçoit une mosaïque, pas quatre vues.

- [ ] **Étape 1 : le test qui échoue** — `backend/tests/test_chapitres_references.py` (21 assertions ; T7 en pose 11)

```python
"""P3 — la recette v3 garde les fichiers de panneaux, et les vues d'une
entité alimentent les générations multi-références. 21 assertions (11 en T7, 10 en T8).
Run: <embedded python> backend/tests/test_chapitres_references.py"""
import asyncio, io, json, os, sys, tempfile, pathlib, types
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CALLS = []


async def _fake_subscribe(model, arguments=None, **kw):
    CALLS.append({"model": model, "arguments": arguments})
    return {"images": [{"url": "http://fal.test/img.png"}],
            "seed": (arguments or {}).get("seed", 424242)}


async def _fake_upload(path):
    return f"http://fal.test/up/{pathlib.Path(path).name}"

_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
_stub.upload_file_async = _fake_upload
sys.modules["fal_client"] = _stub

from httpx import AsyncClient, ASGITransport          # noqa: E402
import httpx as _httpx                                 # noqa: E402
from PIL import Image as _Im                           # noqa: E402
from app.main import app                               # noqa: E402
from app.services.storage import init_db               # noqa: E402

_buf = io.BytesIO(); _Im.new("RGB", (16, 16), (30, 60, 90)).save(_buf, "PNG")
PNG = _buf.getvalue()
_orig_get = _httpx.AsyncClient.get


async def _fake_get(self, url, *a, **kw):
    if str(url).startswith("http://fal.test/"):
        return _httpx.Response(200, content=PNG,
                               request=_httpx.Request("GET", str(url)))
    return await _orig_get(self, url, *a, **kw)

_httpx.AsyncClient.get = _fake_get


def test_la_recette_v3_garde_les_fichiers_et_les_vues_les_servent():
    async def scenario():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            e = (await c.post("/api/bible/entities", json={
                "kind": "character", "name": "Elias",
                "description": "homme fatigue, cape bleue"})).json()
            CALLS.clear()
            r = await c.post(f"/api/bible/entities/{e['id']}/generate", json={"seed": 777})
            assert r.status_code == 200, r.text
            ent = r.json()
            got = (await c.get("/api/bible/entities?kind=character")).json()["entities"][0]
            assert got["has_recipe"] is True
            rec = json.loads((await c.get(
                f"/api/bible/entities/{e['id']}/recette")).json()["recette_brute"])
            assert rec["v"] == 3, rec["v"]
            assert len(rec["panels"]) == 5, len(rec["panels"])
            assert all(p.get("file", "").endswith(".png") for p in rec["panels"])
            assert set(rec["mirrors"]) == {"face_right", "right"}
            assert rec["board"] == ent["ref_image"]
            v = (await c.get(f"/api/bible/entities/{e['id']}/vues")).json()
            assert v["source"] == "recette"
            assert len(v["vues"]) == 7, v["vues"]
            assert ent["ref_image"] not in v["vues"], "la planche n'est pas une vue"
            # une entite SANS recette retombe sur sa planche (bases d'avant)
            p = (await c.post("/api/bible/entities",
                              json={"kind": "place", "name": "Caverne"})).json()
            await c.put(f"/api/bible/entities/{p['id']}", json={"ref_image": "vieux.png"})
            v2 = (await c.get(f"/api/bible/entities/{p['id']}/vues")).json()
            assert v2 == {"entity_id": p["id"], "source": "planche",
                          "vues": ["vieux.png"]}
    asyncio.run(scenario())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for _f in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        _f()
    print("P3 REFERENCES TEST: PASS")
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_references.py` → `AssertionError` sur `rec["v"] == 3` (la recette écrite vaut 2), après un 404 sur `/recette`.

- [ ] **Étape 3 : la recette v3** — trois édits dans `generate_bible_reference` :

1. `routes.py:5419` — `if recipe and recipe.get("v") == 2:` devient `if recipe and recipe.get("v") in (2, 3):`
2. `routes.py:5430` — `if not desc and not (recipe and recipe.get("v") == 2):` devient `if not desc and not (recipe and recipe.get("v") in (2, 3)):`
3. `routes.py:5561` — remplacer les deux lignes de `recipe_panels.append` par :

```python
            recipe_panels.append({"key": key, "prompt": prompt,
                                  "seed": out.get("seed"), "model": model,
                                  # v3 (P3, 03/09) : LE FICHIER. Sans lui,
                                  # seule la planche composite survivait — et
                                  # une mosaïque 4 colonnes n'est pas quatre
                                  # références.
                                  "file": out["images"][0]})
```

4. `routes.py:5565` — remplacer la boucle des miroirs par :

```python
        mirrors_files: dict[str, str] = {}
        for tgt, src in (plan.get("mirrors") or {}).items():
            panels[tgt] = BS.mirror_panel(settings.images_path, panels[src])
            mirrors_files[tgt] = panels[tgt]
```

5. `routes.py:5579` — remplacer l'écriture de la recette par :

```python
        e.prompt_recipe = _json.dumps(
            {"v": 3, "kind": e.kind, "ref_file": insp_file,
             "provider": provider, "style_ref": style_ref or None,
             "canon": canon_key, "panels": recipe_panels,
             "mirrors": mirrors_files, "board": board}, ensure_ascii=False)
```

- [ ] **Étape 4 : les vues** — juste avant `async def _fetch_11l_voices()` (`routes.py:5589`) :

```python
def _entity_ref_views(e) -> tuple[str, list[str]]:
    """P3 — les VUES d'une entité : les panneaux séparés de sa planche
    (recette v3), miroirs compris, dans l'ordre du plan de panneaux. Les
    bases d'avant le 03/09 (recette v2 ou pas de recette) n'ont que la
    planche composite : on la rend, en le disant — c'est une vue mosaïque,
    et l'appelant doit pouvoir le savoir.
    Retourne (source, [filenames])."""
    import json as _json
    try:
        rec = _json.loads(e.prompt_recipe) if e.prompt_recipe else None
    except Exception:
        rec = None
    if rec and rec.get("v") == 3:
        vues = [p["file"] for p in (rec.get("panels") or []) if p.get("file")]
        vues += [f for f in (rec.get("mirrors") or {}).values() if f]
        vues = [f for f in dict.fromkeys(vues)
                if (settings.images_path / f).is_file()]
        if vues:
            return "recette", vues
    return "planche", ([e.ref_image] if e.ref_image else [])


@router.get("/bible/entities/{entity_id}/vues")
async def entity_views(entity_id: str):
    """Les vues de référence de l'entité (P3) — ce qu'on enverra au
    générateur multi-références."""
    from app.services.storage import BibleEntity, async_session_factory
    async with async_session_factory() as session:
        e = await session.get(BibleEntity, entity_id)
        if not e:
            raise HTTPException(404, "Entity not found")
    source, vues = _entity_ref_views(e)
    return {"entity_id": entity_id, "source": source, "vues": vues}


@router.get("/bible/entities/{entity_id}/recette")
async def entity_recipe(entity_id: str):
    """La recette de génération, telle quelle (diagnostic et bancs)."""
    from app.services.storage import BibleEntity, async_session_factory
    async with async_session_factory() as session:
        e = await session.get(BibleEntity, entity_id)
        if not e:
            raise HTTPException(404, "Entity not found")
    if not e.prompt_recipe:
        raise HTTPException(404, "Pas de recette sur cette entité")
    return {"entity_id": entity_id, "recette_brute": e.prompt_recipe}
```

- [ ] **Étape 5 : vert** — `cd backend && $PY tests/test_chapitres_references.py` → `P3 REFERENCES TEST: PASS`. Non-régression : `$PY tests/test_atelier.py` → `ATELIER P1 TEST: PASS` (il compte 5 appels fal et rejoue la recette — la garde `in (2, 3)` doit le laisser passer).

- [ ] **Étape 6 : commit** — sujet `chapitres : la recette de planche garde ses panneaux, et l'entite sait dire ses vues` ; corps : « P3. Recette v3 : chaque panneau porte son `file`, les miroirs et la planche sont nommés ; le rejeu accepte v2 ET v3. `GET /bible/entities/{id}/vues` rend les 7 vues d'un personnage (5 générées + 2 miroirs) ou, pour les bases d'avant, la planche composite **en le disant** (`source: planche`). 11 assertions. »

### T8 — P3c : le générateur reçoit TOUTES les vues (plafond 9), et le plan a son image de production

**Files:**
- Modify: `backend/app/services/image_providers.py:114-133` (`build_banana_request`), `:136-150` (`_banana_generate`), `:191-218` (`generate`)
- Modify: `backend/app/services/storage.py:436-441` (`SHOTS_COLUMNS`), `:264-289` (`class Shot`)
- Modify: `backend/app/api/routes.py:5806-5817` (`_shot_dict`), route neuve après `generate_shot_sketch` (`:6112`)
- Test: `backend/tests/test_chapitres_references.py` (+10 assertions)

**Pourquoi** : mesuré, `image_providers.py:126` — `"image_urls": [image_url]`, **une** référence, alors que la doc fal du 03/09 dit que `image_urls` en accepte plusieurs. Le plafond commun retenu est **9**, celui que la doc fal donne pour Veo 3.1 reference-to-video (1 à 9) : un seul chiffre à tenir dans toute la catégorie.

- [ ] **Étape 1 : le test qui échoue** — ajouter au fichier de T7 :

```python
def test_banana_prend_jusqu_a_neuf_references_et_le_plan_les_recoit():
    from app.services import image_providers as IP
    m, a = IP.build_banana_request("p", "square_hd", 1, [], pro=True)
    assert m == "fal-ai/nano-banana-pro" and "image_urls" not in a
    m, a = IP.build_banana_request("p", "square_hd", 1, ["u1"], pro=True)
    assert m == "fal-ai/nano-banana-pro/edit" and a["image_urls"] == ["u1"]
    m, a = IP.build_banana_request("p", "square_hd", 1, [f"u{i}" for i in range(12)])
    assert len(a["image_urls"]) == IP.REF_MAX == 9
    assert a["image_urls"][0] == "u0", "l'ordre est gardé : la face d'abord"
    m, a = IP.build_banana_request("p", "square_hd", 1, "u1", ratio="9:16")
    assert a["image_urls"] == ["u1"] and a["aspect_ratio"] == "9:16"

    async def scenario():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            e = (await c.post("/api/bible/entities", json={
                "kind": "character", "name": "Vane", "description": "cape"})).json()
            await c.post(f"/api/bible/entities/{e['id']}/generate", json={"seed": 1})
            await c.put("/api/atelier/settings", json={"image_provider": "nano-banana-pro"})
            ch = (await c.post("/api/chapters", json={
                "title": "C", "script_text": "Vane entre.\n\nIl se tait."})).json()
            sh = (await c.post(f"/api/chapters/{ch['id']}/storyboard/decoupe",
                               json={"method": "paragraph"})).json()["shots"][0]
            await c.put(f"/api/shots/{sh['id']}", json={"entities": [e["id"]]})
            CALLS.clear()
            r = await c.post(f"/api/shots/{sh['id']}/image", json={})
            assert r.status_code == 200, r.text
            assert len(CALLS) == 1
            args = CALLS[0]["arguments"]
            assert CALLS[0]["model"] == "fal-ai/nano-banana-pro/edit"
            assert len(args["image_urls"]) == 7, len(args["image_urls"])
            assert r.json()["image_refs"] == 7 and r.json()["image"].endswith(".png")
    asyncio.run(scenario())
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_references.py` → `TypeError` : `build_banana_request` reçoit une liste là où il attend `str | None`.

- [ ] **Étape 3 : le constructeur accepte une liste** — `image_providers.py`, remplacer `build_banana_request` (`:114-133`) et le corps de `_banana_generate` (`:136-150`) :

```python
REF_MAX = 9   # P3 (03/09/2026) : le plafond de la doc fal Veo 3.1
              # reference-to-video (1 a 9), tenu partout dans Chapitres.


def build_banana_request(prompt: str, size: str, n: int,
                         image_urls: list[str] | str | None,
                         ratio: str | None = None,
                         pro: bool = False) -> tuple[str, dict]:
    """(model_id, arguments) fal pour Nano Banana. Exposé pur pour les tests.
    `image_urls` accepte MAINTENANT une liste (P3, 03/09) : la doc fal du
    03/09 dit que le champ en prend plusieurs, et l'application n'en passait
    qu'une (mesuré). L'ordre est conservé — la première vue est la plus
    porteuse d'identité (le visage de face, cf. board_service.PANEL_PLANS) —
    et la liste est tronquée à REF_MAX.
    `ratio` (ex. "9:16") force le cadre d'un EDIT ; par défaut l'edit suit le
    cadre de la première image. `pro` vise fal-ai/nano-banana-pro."""
    endpoint = "fal-ai/nano-banana-pro" if pro else "fal-ai/nano-banana"
    if isinstance(image_urls, str):
        image_urls = [image_urls]
    urls = [u for u in (image_urls or []) if u][:REF_MAX]
    if urls:
        args = {"prompt": prompt, "image_urls": urls,
                "num_images": n, "output_format": "png"}
        if ratio:
            args["aspect_ratio"] = ratio
        return (endpoint + "/edit", args)
    return (endpoint,
            {"prompt": prompt, "num_images": n, "output_format": "png",
             "aspect_ratio": _BANANA_ASPECT.get(size, "1:1")})


async def _banana_generate(prompt: str, size: str, n: int,
                           image_paths: list[Path] | None,
                           ratio: str | None = None,
                           pro: bool = False) -> list[str]:
    import fal_client
    urls: list[str] = []
    if image_paths:
        from app.services.fal_service import FalSeedanceClient
        for p in list(image_paths)[:REF_MAX]:
            urls.append(await FalSeedanceClient.upload_image(p))
    model, arguments = build_banana_request(prompt, size, n, urls, ratio, pro)
    result = await fal_client.subscribe_async(model, arguments=arguments)
    out = [im.get("url") for im in (result or {}).get("images", [])
           if im.get("url")]
    if not out:
        raise RuntimeError(f"Nano Banana returned no images: {result}")
    return await _download(out)
```

puis dans `generate` (`:191`), ajouter le paramètre et le passer :

```python
async def generate(provider: str, prompt: str, size: str, n: int = 1,
                   seed: int | None = None,
                   image_path: Path | None = None,
                   ratio: str | None = None,
                   image_paths: list[Path] | None = None) -> dict:
```

et dans la branche banana, remplacer l'appel par :

```python
        refs = list(image_paths) if image_paths else (
            [image_path] if image_path else [])
        imgs = await _banana_generate(prompt, size, n, refs, ratio,
                                      pro=(provider == "nano-banana-pro"))
```

- [ ] **Étape 4 : le plan porte son image de production** — `storage.py`, dans `class Shot` après `sketch_seed` (`:279`) :

```python
    # v2.9 (P3, 03/09/2026) — l'image de PRODUCTION du plan, générée avec
    # TOUTES les vues des entités en référence (le croquis, lui, reste le
    # jet FLUX bon marché). `image_refs` = combien de références ont été
    # réellement envoyées : la mesure qui rend la coherence discutable.
    image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_refs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
```

et `SHOTS_COLUMNS` (`:436`) :

```python
SHOTS_COLUMNS = [
    ("motion_recipe", "VARCHAR(60)"),
    ("energy", "INTEGER"),
    # v2.9 (P3, 03/09/2026) — image de production + nombre de references
    ("image", "VARCHAR(255)"),
    ("image_refs", "INTEGER"),
]
```

et `_shot_dict` (`routes.py:5817`), ajouter avant `"motion_recipe"` :

```python
            "image": s.image, "image_refs": s.image_refs,
```

- [ ] **Étape 5 : la route** — après `generate_shot_sketch` (`routes.py:6112`) :

```python
@router.post("/shots/{shot_id}/image")
async def generate_shot_image(shot_id: str, body: dict):
    """P3 (03/09/2026) — l'image de PRODUCTION du plan, générée avec TOUTES
    les vues de référence des entités présentes (plafond IP.REF_MAX = 9,
    celui de la doc fal Veo 3.1 reference-to-video du 03/09), au lieu d'une
    seule. Body: {provider?, size?}. Le croquis (FLUX, /sketch) n'est pas
    touché : il reste le jet bon marché."""
    from app.services import image_providers as IP
    from app.services.storage import Shot, BibleEntity, async_session_factory
    import json as _json
    async with async_session_factory() as session:
        s = await session.get(Shot, shot_id)
        if not s:
            raise HTTPException(404, "Shot not found")
        action = (s.action or s.source_text or "").strip()
        if not action:
            raise HTTPException(400, "Décris l'action du plan avant l'image")
        provider = (body.get("provider")
                    or await _atelier_setting(session, "image_provider")
                    or "nano-banana-pro")
        if provider not in ("nano-banana", "nano-banana-pro"):
            raise HTTPException(
                400, f"« {provider} » ne prend pas plusieurs références. "
                     "Choisis Nano Banana (Pro) dans la DA, ou 🎨 pour le "
                     "croquis FLUX.")
        try:
            eids = _json.loads(s.entities) if s.entities else []
        except Exception:
            eids = []
        refs: list[Path] = []
        descs: list[str] = []
        for eid in eids:
            e = await session.get(BibleEntity, eid)
            if not e:
                continue
            descs.append(f"{e.name}: {(e.description or '')[:100]}")
            for f in _entity_ref_views(e)[1]:
                p = settings.images_path / f
                if p.is_file() and p not in refs:
                    refs.append(p)
        if not refs:
            raise HTTPException(
                400, "Aucune vue de référence : génère la planche 🎨 des "
                     "entités du plan d'abord (bible).")
        style = await _atelier_setting(session, "global_style")
        prompt = (f"Shot: {s.shot_type}, camera: {s.camera_move}. {action}")
        if descs:
            prompt += ". Characters/places (keep them EXACTLY as in the "
            prompt += "reference images): " + "; ".join(descs)
        if style:
            prompt += f". Style: {style}"
        refs = refs[:IP.REF_MAX]
        out = await IP.generate(provider, prompt, "portrait_16_9", 1,
                                ratio="9:16", image_paths=refs)
        await LI.noter([out["images"][0]], "atelier")
        s.image = out["images"][0]
        s.image_refs = len(refs)
        s.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(s)
        return _shot_dict(s)
```

- [ ] **Étape 6 : vert** — `cd backend && $PY tests/test_chapitres_references.py` → `P3 REFERENCES TEST: PASS`. Non-régression : `$PY tests/test_image_model_default.py` et `$PY tests/test_images_process.py` (les deux bancs qui touchent `image_providers`) → `PASS`.

- [ ] **Étape 7 : commit** — sujet `chapitres : Nano Banana recoit toutes les vues, plafond 9, et le plan a son image` ; corps : « P3. Mesuré avant : `image_providers.py:126` n'envoyait qu'une référence. `build_banana_request` prend une liste, l'ordre est gardé (le visage de face d'abord), la troncature est à `REF_MAX = 9` — le plafond de la doc fal Veo 3.1 reference-to-video du 03/09, tenu partout dans la catégorie. `POST /shots/{id}/image` rassemble les vues des entités du plan ; `shots.image` et `shots.image_refs` par colonnes ajoutées (`SHOTS_COLUMNS`). 10 assertions. »

### T9 — P3d : la vidéo — Veo 3.1 reference-to-video et les `elements` de Kling (constructeur pur)

**Files:**
- Modify: `backend/app/services/fal_service.py:100-114` (Kling v3), `:122-128` (Veo fal), `:187-262` (`build_fal_args`)
- Test: `backend/tests/test_chapitres_video_refs.py`

**Pourquoi** : R3, vérifié le 03/09 sur fal.ai — Veo 3.1 reference-to-video accepte **1 à 9 images** de référence (aussi en Fast) ; Kling v3 Pro a `elements` (références nommées `@Element` dans le prompt) et **pas** de `seed`. Mesuré dans le dépôt : `grep -c elements backend/app/services/fal_service.py` → **0**, et le registre n'a aucune entrée reference-to-video (`fal_service.py:122` = `image-to-video`).

- [ ] **Étape 1 : relire la doc AVANT d'écrire (obligatoire)** — deux `WebFetch`, exactement :

```
WebFetch url="https://fal.ai/models/fal-ai/veo3.1/reference-to-video/api"
         prompt="Give the exact model endpoint id, the exact name of the input field that carries the reference images, its minimum and maximum count, and the exact names and allowed values of the duration, aspect_ratio and resolution fields. Quote the field names verbatim."
WebFetch url="https://fal.ai/models/fal-ai/kling-video/v3/pro/image-to-video/api"
         prompt="Give the exact name and JSON shape of the field carrying named reference elements, how the prompt refers to them, and whether a seed field exists. Quote verbatim."
```

Écrire dans le corps du commit la valeur mesurée de chaque champ. Si l'endpoint ou le nom de champ diffère des constantes ci-dessous, **corriger la constante ET l'assertion du test dans le même édit** — le plan fixe une valeur, la doc tranche.

- [ ] **Étape 2 : le test qui échoue** — `backend/tests/test_chapitres_video_refs.py` (14 assertions)

```python
"""P3 vidéo — constructeur d'arguments multi-références (Veo 3.1
reference-to-video, elements de Kling v3). Pur, aucun réseau. 14 assertions.
Run: <embedded python> backend/tests/test_chapitres_video_refs.py"""
import os, sys, pathlib
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services import fal_service as FS             # noqa: E402


def test_le_registre_porte_les_deux_entrees_de_reference():
    assert FS.VIDEO_MODELS["veo-3.1-ref-fal"]["endpoint"] == FS.VEO_REF_ENDPOINT
    assert FS.VIDEO_MODELS["veo-3.1-ref-fal"]["refs"] == (1, 9)
    assert FS.VIDEO_MODELS["veo-3.1-fast-ref-fal"]["refs"] == (1, 9)
    assert FS.VIDEO_MODELS["kling-v3-pro"]["refs"] == (1, 4)
    assert FS.VIDEO_MODELS["seedance-v1-pro"].get("refs") is None


def test_veo_prend_de_une_a_neuf_references_et_le_dit_quand_il_tronque():
    ep, args, notes = FS.build_reference_video_args(
        "veo-3.1-ref-fal", "un plan", [f"u{i}" for i in range(12)],
        duration=8, aspect_ratio="9:16", resolution="1080p")
    assert ep == FS.VEO_REF_ENDPOINT
    assert len(args[FS.VEO_REF_FIELD]) == 9
    assert args["duration"] == "8s" and args["aspect_ratio"] == "9:16"
    assert any("9" in n for n in notes), notes
    try:
        FS.build_reference_video_args("veo-3.1-ref-fal", "p", [])
        raise AssertionError("zero reference doit lever")
    except ValueError as e:
        assert "reference" in str(e).lower()


def test_kling_nomme_ses_elements_et_n_a_pas_de_seed():
    ep, args, notes = FS.build_reference_video_args(
        "kling-v3-pro", "Elias regarde @Element1", ["a.png", "b.png"],
        duration=5, seed=42)
    assert args["elements"] == [{"image_url": "a.png"}, {"image_url": "b.png"}]
    assert "seed" not in args
    assert "@Element1" in args["prompt"]
    assert any("seed" in n for n in notes), notes


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for _f in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        _f()
    print("P3 VIDEO REFS TEST: PASS")
```

- [ ] **Étape 3 : le voir rouge** — `cd backend && $PY tests/test_chapitres_video_refs.py` → `AttributeError: module 'app.services.fal_service' has no attribute 'VEO_REF_ENDPOINT'`.

- [ ] **Étape 4 : le registre** — `fal_service.py`, ajouter `"refs": (1, 4)` aux deux entrées `kling-v3-*` (`:100-114`), `"refs": None` n'est pas écrit (absent = pas de références), et deux entrées neuves après `"veo-3.1-fast-fal"` (`:128`) :

```python
# P3 (verifie sur fal.ai le 03/09/2026) : Veo 3.1 reference-to-video accepte
# 1 a 9 images de reference pour la constance du sujet, en Pro comme en Fast.
VEO_REF_ENDPOINT = "fal-ai/veo3.1/reference-to-video"
VEO_REF_FAST_ENDPOINT = "fal-ai/veo3.1/fast/reference-to-video"
VEO_REF_FIELD = "reference_image_urls"
```

et, dans `VIDEO_MODELS` :

```python
    "veo-3.1-ref-fal": {
        "label": "Veo 3.1 références (fal)", "provider": "fal",
        "family": "veo_fal", "endpoint": VEO_REF_ENDPOINT,
        "durations": [4, 6, 8], "ratios": ["9:16", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": False, "seed": True,
        "audio_param": "generate_audio", "refs": (1, 9),
    },
    "veo-3.1-fast-ref-fal": {
        "label": "Veo 3.1 Fast références (fal)", "provider": "fal",
        "family": "veo_fal", "endpoint": VEO_REF_FAST_ENDPOINT,
        "durations": [4, 6, 8], "ratios": ["9:16", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": False, "seed": True,
        "audio_param": "generate_audio", "refs": (1, 9),
    },
```

- [ ] **Étape 5 : le constructeur** — après `build_fal_args` (`fal_service.py:262`) :

```python
def build_reference_video_args(model_id: str, prompt: str,
                               reference_urls: list[str],
                               duration: int = 5,
                               aspect_ratio: str = "9:16",
                               resolution: str | None = "1080p",
                               seed: int | None = None
                               ) -> tuple[str, dict, list]:
    """P3 (03/09/2026) — l'appel MULTI-RÉFÉRENCES. Fonction PURE (aucun
    réseau) : (endpoint, arguments, notes).

    Deux grammaires, vérifiées sur fal.ai le 03/09 :
      - Veo 3.1 reference-to-video : une liste plate d'URL d'images,
        1 à 9, champ VEO_REF_FIELD ;
      - Kling v3 : `elements`, une liste d'objets {image_url}, nommés
        @Element1… dans le prompt — et PAS de seed (le registre le dit
        déjà : "seed": False).
    Un modèle sans clé `refs` n'a pas de mode références : ValueError.
    Au-delà du plafond, on TRONQUE et on le dit dans `notes` (jamais
    d'échec silencieux ni de facture surprise)."""
    m = resolve_video_model(model_id)
    bornes = m.get("refs")
    if not bornes:
        raise ValueError(f"{m['label']} n'a pas de mode references "
                         f"(image-to-video seulement).")
    lo, hi = bornes
    urls = [u for u in (reference_urls or []) if u]
    if len(urls) < lo:
        raise ValueError(f"{m['label']} demande au moins {lo} image(s) de "
                         f"reference ({len(urls)} fournie(s)).")
    notes: list = []
    if len(urls) > hi:
        notes.append(f"{len(urls)} references -> {hi} (plafond {m['label']})")
        urls = urls[:hi]
    dur = clamp_duration(m, duration)
    if dur != duration:
        notes.append(f"duration {duration}s->{dur}s")
    res = clamp_resolution(m, resolution)
    args: dict = {"prompt": prompt}
    if m["family"] == "kling":
        args["elements"] = [{"image_url": u} for u in urls]
    else:
        args[VEO_REF_FIELD] = urls
    args["duration"] = f"{dur}s" if m["family"] == "veo_fal" else dur
    if m["ratios"] is not None and aspect_ratio in m["ratios"]:
        args["aspect_ratio"] = aspect_ratio
    if res is not None:
        args["resolution"] = res
    if seed is not None:
        if m["seed"]:
            args["seed"] = seed
        else:
            notes.append("seed unsupported -> dropped")
    if m["audio_param"]:
        args[m["audio_param"]] = False
    return m["endpoint"], args, notes
```

- [ ] **Étape 6 : les deux invariants que le registre casse** — mesuré : `tests/test_video_models.py:40` asserte `set(VIDEO_MODELS) == EXPECTED_IDS`, et `:47` exige une ligne de prix pour chaque modèle. Deux édits obligatoires, dans le même commit :

1. `backend/tests/test_video_models.py:30-36` — ajouter les deux ids à `EXPECTED_IDS` :

```python
    "veo-3.1-fast-fal", "veo-3.1-ref-fal", "veo-3.1-fast-ref-fal",
    "veo-3.1-google", "veo-3.1-fast-google",
```

2. `backend/app/services/pricing.py:63` — deux lignes après `"veo-3.1-fast-fal": {"*": 0.10},` :

```python
        # P3 (03/09/2026) : reference-to-video. Le tarif est celui relevé au
        # WebFetch de l'étape 1 ; à défaut de prix publié par seconde, on
        # aligne sur la variante image-to-video du même modèle et l'on
        # marque l'estimation — comme les lignes Google de ce bloc.
        "veo-3.1-ref-fal":      {"*": 0.40},
        "veo-3.1-fast-ref-fal": {"*": 0.10},
```

- [ ] **Étape 7 : vert** — `cd backend && $PY tests/test_chapitres_video_refs.py` → `P3 VIDEO REFS TEST: PASS` ; `$PY -m pytest tests/test_video_models.py -q` → `passed`.

- [ ] **Étape 8 : commit** — sujet `chapitres : le constructeur video multi-references, Veo 3.1 et les elements de Kling` ; corps : « P3 vidéo. Avant : `grep -c elements fal_service.py` → 0, aucune entrée reference-to-video au registre. `build_reference_video_args` est PUR — deux grammaires (liste plate pour Veo, `elements` nommés pour Kling), plafonds au registre (Veo 1–9, Kling 1–4), troncature **dite** dans `notes`, seed jeté avec une note sur Kling. Champs et tarifs relus sur fal.ai le 03/09 — recopier ici les quatre valeurs exactes lues à l'étape 1 : l'endpoint, le nom du champ de références, ses bornes, et le tarif par seconde. `EXPECTED_IDS` et la table de prix suivent, sinon `test_video_models` rougit. Aucun appel réseau branché : ce lot livre l'argument, pas la facture. 14 assertions. »

### T10 — P4a : `animatique_service.py` — le plan de montage, le carton, le rendu

**Files:**
- Create: `backend/app/services/animatique_service.py`
- Modify: `backend/app/api/routes.py` — routes neuves après `reorder_storyboard` (`:6465-6535`), avant `@router.post("/atelier/manuscript")` (`:6536`)
- Test: `backend/tests/test_chapitres_animatique.py`

**Pourquoi** : réponse 2 — « animatique depuis les plans du storyboard, croquis + durée + voix témoin, avant toute génération payante ». Référence vérifiée (Boords, help.boords.com, 03/09) : **la voix off téléversée FIXE la durée de l'image**. Mesuré dans le dépôt : la mécanique existe déjà (`FFmpegMerger.scene_clip` `ffmpeg_service.py:184` + `concat_clips` `:224`, orchestrées par `pipeline.run_episode` `pipeline.py:763`) — elle travaille sur des *scènes* d'épisode, jamais sur des *plans*.

- [ ] **Étape 1 : le test qui échoue** — `backend/tests/test_chapitres_animatique.py` (17 assertions)

```python
"""P4 — animatique depuis les plans : plan de montage pur, carton de secours,
route de rendu (ffmpeg et voix stubbés). 17 assertions (T10) + 4 (T11).
Run: <embedded python> backend/tests/test_chapitres_animatique.py"""
import asyncio, os, sys, tempfile, pathlib, types
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.modules["fal_client"] = types.ModuleType("fal_client")
from httpx import AsyncClient, ASGITransport          # noqa: E402
from PIL import Image                                  # noqa: E402
from app.main import app                               # noqa: E402
from app.services.storage import init_db               # noqa: E402
from app.services import animatique_service as AN      # noqa: E402

SHOTS = [
    {"id": "s1", "idx": 0, "action": "Vane entre", "duration_s": 4.0,
     "sketch_image": "k1.png", "image": None},
    {"id": "s2", "idx": 1, "action": "Il se tait", "duration_s": 6.0,
     "sketch_image": "k2.png", "image": "prod2.png"},
    {"id": "s3", "idx": 2, "action": "Le Prophete parle", "duration_s": 5.0,
     "sketch_image": None, "image": None},
]


def test_la_voix_fixe_la_duree_et_l_image_de_production_gagne():
    p = AN.plan(SHOTS, voix={"s1": 7.25, "s3": 0.2})
    assert [x["dur"] for x in p] == [7.25, 6.0, 5.0]
    assert [x["source_duree"] for x in p] == ["voix", "plan", "plan"]
    assert p[0]["image"] == "k1.png"
    assert p[1]["image"] == "prod2.png", "l'image de production prime"
    assert p[2]["image"] is None and p[2]["carton"] is True
    assert AN.duree_totale(p) == 18.25


def test_le_carton_de_secours_est_un_vrai_png_au_bon_cadre():
    dest = pathlib.Path(_tmp) / "carton.png"
    AN.carton("PLAN 3", "Le Prophète parle, très longuement, dans le noir "
                        "de la caverne noyée", dest)
    im = Image.open(dest)
    assert im.size == (1080, 1920)
    assert im.mode == "RGB"
    assert dest.stat().st_size > 1000


def test_la_route_rend_un_clip_par_plan_dans_l_ordre():
    from app.services.ffmpeg_service import FFmpegMerger
    from app.services.elevenlabs_service import VoiceoverService
    vus = []

    def _clip(image, audio, out, *, motion="kenburns", dur=4.0, **kw):
        vus.append({"image": None if image is None else pathlib.Path(image).name,
                    "dur": round(dur, 2), "out": pathlib.Path(out).name})
        pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(out).write_bytes(b"mp4")
        return out

    def _concat(clips, out):
        vus.append({"concat": [pathlib.Path(c).name for c in clips]})
        pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(out).write_bytes(b"mp4")
        return out

    FFmpegMerger.scene_clip = staticmethod(_clip)
    FFmpegMerger.concat_clips = staticmethod(_concat)
    VoiceoverService.is_enabled = staticmethod(lambda: False)

    async def scenario():
        await init_db()
        Image.new("RGB", (64, 64), (10, 10, 10)).save(
            pathlib.Path(_tmp, "images", "k1.png"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            ch = (await c.post("/api/chapters", json={
                "title": "A", "script_text": "un\n\ndeux"})).json()
            shots = (await c.post(f"/api/chapters/{ch['id']}/storyboard/decoupe",
                                  json={"method": "paragraph"})).json()["shots"]
            await c.put(f"/api/shots/{shots[0]['id']}", json={"duration_s": 3.0})
            r = await c.post(f"/api/chapters/{ch['id']}/animatique",
                             json={"voix": False})
            assert r.status_code == 200, r.text
            jid = r.json()["job_id"]
            for _ in range(80):
                st = (await c.get(f"/api/atelier/manuscript/{jid}")).json()
                if st["done"]:
                    break
                await asyncio.sleep(0.05)
            assert st["error"] is None, st
            assert st["stats"]["plans"] == 2
            clips = [v for v in vus if "out" in v]
            assert [v["out"] for v in clips] == ["p000.mp4", "p001.mp4"]
            assert clips[0]["dur"] == 3.0
            concat = [v for v in vus if "concat" in v][-1]
            assert concat["concat"] == ["p000.mp4", "p001.mp4"]
            e = (await c.get(f"/api/chapters/{ch['id']}/animatique")).json()
            assert e["existe"] is True and e["plans"] == 2
            assert e["url"].endswith("/animatique.mp4")
    asyncio.run(scenario())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for _f in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        _f()
    print("P4 ANIMATIQUE TEST: PASS")
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_animatique.py` → `ModuleNotFoundError: No module named 'app.services.animatique_service'`.

- [ ] **Étape 3 : le service** — `backend/app/services/animatique_service.py` :

```python
"""P4 (03/09/2026) — l'animatique : les plans du storyboard montés en vidéo
9:16 AVANT toute génération payante.

Règle de durée, reprise de Boords (help.boords.com, vérifié le 03/09) : une
voix off attachée à une image FIXE sa durée ; sans voix, c'est la durée
réglée sur le plan qui vaut. `plan()` est PUR — il ne touche ni au disque ni
au réseau — pour que la règle soit testable sans ffmpeg.

Le rendu réutilise la mécanique déjà éprouvée du dépôt : une image fixe +
un audio par clip (FFmpegMerger.scene_clip) puis une concaténation
(concat_clips) — la même que pipeline.run_episode, appliquée aux PLANS.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LARGEUR, HAUTEUR = 1080, 1920
FOND_CARTON = (12, 14, 18)
ENCRE = (222, 228, 236)
ACCENT = (86, 200, 226)          # le cyan du produit : action / generation
DUREE_MINI = 0.8                 # sous ce seuil, un audio n'est pas une voix
POLICES = (Path("C:/Windows/Fonts/segoeui.ttf"),
           Path("C:/Windows/Fonts/arial.ttf"))


def plan(shots: list[dict], voix: dict | None = None,
         mini: float = DUREE_MINI) -> list[dict]:
    """Le plan de montage de l'animatique. PUR.

    `shots` = dicts de _shot_dict ; `voix` = {shot_id: duree mesuree}.
    Chaque entrée : {idx, shot_id, image, texte, dur, source_duree, carton}.
    L'image de PRODUCTION (P3) prime sur le croquis ; sans l'une ni l'autre,
    `carton` est vrai et le rendu fabriquera une carte de texte — un trou
    noir muet ferait croire à une panne."""
    voix = voix or {}
    out = []
    for i, s in enumerate(sorted(shots, key=lambda x: x.get("idx", 0))):
        img = s.get("image") or s.get("sketch_image") or None
        dv = float(voix.get(s.get("id")) or 0)
        if dv >= mini:
            dur, src = round(dv, 3), "voix"
        else:
            dur, src = round(float(s.get("duration_s") or 4.0), 3), "plan"
        out.append({"idx": i, "shot_id": s.get("id"), "image": img,
                    "texte": (s.get("action") or s.get("source_text") or "").strip(),
                    "dur": dur, "source_duree": src, "carton": img is None})
    return out


def duree_totale(entrees: list[dict]) -> float:
    return round(sum(e["dur"] for e in entrees), 3)


def _police(taille: int):
    for p in POLICES:
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), taille)
            except OSError:
                continue
    return ImageFont.load_default()


def carton(titre: str, texte: str, dest: Path,
           w: int = LARGEUR, h: int = HAUTEUR) -> Path:
    """La carte de secours d'un plan sans image : le numéro du plan et son
    action, au cadre de sortie. Écrite par PIL, jamais par un modèle."""
    im = Image.new("RGB", (w, h), FOND_CARTON)
    d = ImageDraw.Draw(im)
    ft = _police(40)
    ptit = _police(58)
    d.text((80, h // 2 - 260), titre, font=ptit, fill=ACCENT)
    d.line([(80, h // 2 - 180), (w - 80, h // 2 - 180)], fill=ACCENT, width=3)
    y = h // 2 - 130
    for ligne in textwrap.wrap(texte or "(pas d'action décrite)", width=34)[:12]:
        d.text((80, y), ligne, font=ft, fill=ENCRE)
        y += 56
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest)
    return dest


def dossier(outputs: Path, chapter_id: str) -> Path:
    d = outputs / "animatique" / chapter_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def rendre(entrees: list[dict], *, images: Path, sortie: Path,
           audios: dict | None = None, progres=None) -> Path:
    """Monte l'animatique. Un clip par plan (pXXX.mp4, GARDÉS — D3 en fera
    des clips de timeline), puis animatique.mp4. `progres(i, n)` est appelé
    avant chaque plan."""
    from app.services.ffmpeg_service import FFmpegMerger
    audios = audios or {}
    sortie.mkdir(parents=True, exist_ok=True)
    clips = []
    n = len(entrees)
    for e in entrees:
        if progres:
            progres(e["idx"] + 1, n)
        if e["carton"]:
            img = carton(f"PLAN {e['idx'] + 1}", e["texte"],
                         sortie / f"p{e['idx']:03d}.png")
        else:
            img = images / e["image"]
            if not img.is_file():
                img = carton(f"PLAN {e['idx'] + 1}", e["texte"],
                             sortie / f"p{e['idx']:03d}.png")
        clip = sortie / f"p{e['idx']:03d}.mp4"
        FFmpegMerger.scene_clip(img, audios.get(e["shot_id"]), clip,
                                motion="still", dur=e["dur"],
                                w=LARGEUR, h=HAUTEUR)
        clips.append(clip)
    final = sortie / "animatique.mp4"
    FFmpegMerger.concat_clips(clips, final)
    return final
```

- [ ] **Étape 4 : les routes** — dans `routes.py`, juste avant `@router.post("/atelier/manuscript")` (`:6536`) :

```python
@router.get("/chapters/{chapter_id}/animatique")
async def animatique_etat(chapter_id: str):
    """P4 — l'animatique déjà rendue de ce chapitre, s'il y en a une."""
    from app.services import animatique_service as AN
    d = AN.dossier(settings.outputs_path, chapter_id)
    final = d / "animatique.mp4"
    plans = sorted(d.glob("p[0-9][0-9][0-9].mp4"))
    return {"existe": final.is_file(), "plans": len(plans),
            "url": f"/api/chapters/{chapter_id}/animatique.mp4",
            "clips": [p.name for p in plans]}


@router.get("/chapters/{chapter_id}/animatique.mp4")
async def animatique_fichier(chapter_id: str):
    from app.services import animatique_service as AN
    p = AN.dossier(settings.outputs_path, chapter_id) / "animatique.mp4"
    if not p.is_file():
        raise HTTPException(404, "Pas encore d'animatique pour ce chapitre")
    return FileResponse(p, media_type="video/mp4")


@router.post("/chapters/{chapter_id}/animatique")
async def animatique_rendre(chapter_id: str, body: dict,
                            background_tasks: BackgroundTasks):
    """P4 — monte l'animatique du storyboard. Body: {voix?: bool (défaut
    true), language?}. Suivre GET /atelier/manuscript/{job_id}."""
    from app.services.storage import Chapter, async_session_factory
    async with async_session_factory() as session:
        if not await session.get(Chapter, chapter_id):
            raise HTTPException(404, "Chapter not found")
        shots = [_shot_dict(s) for s in await _list_shots(session, chapter_id)]
    if not shots:
        raise HTTPException(400, "Pas de storyboard — découpe le chapitre "
                                 "(🎬 ou ¶) d'abord.")
    jid = str(uuid4())
    _ms_register(jid, {"job_id": jid, "phase": "animatique", "chapter_i": 0,
                       "chapter_n": len(shots), "message": "Animatique…",
                       "done": False, "error": None, "stats": {}})
    background_tasks.add_task(_run_animatique_job, jid, chapter_id, shots,
                             bool(body.get("voix", True)),
                             str(body.get("language") or "fr").lower())
    return {"job_id": jid, "plans": len(shots)}


async def _run_animatique_job(jid: str, chapter_id: str, shots: list,
                              avec_voix: bool, lang: str):
    """Voix témoin par plan (facultative), puis montage. La voix, quand elle
    existe, FIXE la durée du plan (règle Boords, vérifiée le 03/09)."""
    from app.services import animatique_service as AN
    from app.services.elevenlabs_service import VoiceoverService

    def upd(**kw):
        _MS_JOBS[jid].update(kw)

    loop = asyncio.get_running_loop()
    try:
        d = AN.dossier(settings.outputs_path, chapter_id)
        audios: dict = {}
        durees: dict = {}
        if avec_voix and await loop.run_in_executor(
                None, VoiceoverService.is_enabled):
            voice = VoiceoverService()
            l11 = "FR" if lang.startswith("fr") else "EN"
            for i, s in enumerate(shots):
                texte = (s.get("action") or s.get("source_text") or "").strip()
                if len(texte) < 3:
                    continue
                upd(chapter_i=i + 1,
                    message=f"Voix témoin {i + 1}/{len(shots)}")
                dest = d / f"p{i:03d}.mp3"
                await loop.run_in_executor(
                    None, lambda t=texte, o=dest: voice.generate_long(
                        text=t, output_path=o, language=l11))
                if dest.is_file():
                    audios[s["id"]] = dest
                    durees[s["id"]] = _audio_duration(dest)
        entrees = AN.plan(shots, voix=durees)

        def _progres(i, n):
            upd(phase="montage", chapter_i=i, chapter_n=n,
                message=f"Plan {i}/{n} — montage")

        await loop.run_in_executor(
            None, lambda: AN.rendre(entrees, images=settings.images_path,
                                    sortie=d, audios=audios,
                                    progres=_progres))
        upd(phase="terminé", done=True,
            message="Animatique montée — regarde avant de payer un rendu.",
            stats={"plans": len(entrees), "voix": len(audios),
                   "duree_s": AN.duree_totale(entrees)})
    except Exception as e:
        logger.exception(f"animatique {jid}: {e}")
        upd(phase="échec", done=True, error=str(e))
```

- [ ] **Étape 5 : vert** — `cd backend && $PY tests/test_chapitres_animatique.py` → `P4 ANIMATIQUE TEST: PASS`.

- [ ] **Étape 6 : commit** — sujet `chapitres : l'animatique depuis les plans, la voix temoin fixe la duree` ; corps : « P4. `plan()` est pur : l'image de production prime sur le croquis, la voix témoin fixe la durée (règle Boords vérifiée le 03/09), sinon la durée réglée du plan. Un plan sans image reçoit un CARTON PIL (numéro + action) — un noir muet passerait pour une panne. Les clips par plan sont GARDÉS (`pXXX.mp4`) : D3 en fera des clips de timeline. 17 assertions, ffmpeg et la voix stubbés. »

### T11 — P4b : `/atelier` — le bouton 🎞 Animatique, la progression, le lecteur

**Files:**
- Modify: `frontend/atelier/index.html:86` (barre du storyboard), `:252` (modale lecteur)
- Modify: `frontend/atelier/atelier.js` après `decoupe` (`:681`), wiring `:1269`
- Modify: `frontend/atelier/atelier.css` (fin)
- Test: `backend/tests/test_chapitres_animatique.py` (+4 assertions de miroir)

- [ ] **Étape 1 : le banc-miroir** — ajouter au fichier de T10 :

```python
def test_la_source_atelier_porte_l_animatique():
    r = pathlib.Path(__file__).resolve().parents[2]
    js = r.joinpath("frontend/atelier/atelier.js").read_text("utf-8")
    html = r.joinpath("frontend/atelier/index.html").read_text("utf-8")
    assert "async function animatique(" in js and "/animatique" in js
    assert 'id="animBtn"' in html and 'id="animModal"' in html
    assert "animatique.mp4" in js
    assert js.count("msSetProgress") >= 2, "la barre de progression est réutilisée"
```

Rouge : `cd backend && $PY tests/test_chapitres_animatique.py` → `AssertionError`.

- [ ] **Étape 2 : le bouton et le lecteur** — `index.html`, après `<button id="boardReset" …>` (`:86`) :

```html
        <button id="animBtn" class="btn primary" title="Monte l'animatique : chaque plan devient une image fixe à sa durée, avec une voix témoin quand une voix est configurée. C'est la répétition — elle ne coûte rien et se regarde avant de payer un rendu.">🎞 Animatique</button>
        <button id="animOpen" class="btn ghost hidden" title="Revoir la dernière animatique montée">▶ Revoir</button>
```

et avant `<div id="toast" class="toast hidden"></div>` (`:252`) :

```html
<div id="animModal" class="modal hidden">
  <div class="modal-box">
    <div class="modal-head">
      <b>Animatique</b>
      <span id="animNote" class="da-note"></span>
      <button id="animClose" class="btn ghost">✕</button>
    </div>
    <video id="animVideo" class="anim-video" controls preload="metadata"></video>
  </div>
</div>
```

- [ ] **Étape 3 : le JS** — après `decoupe` (`atelier.js:681`) :

```js
/* ═════════ P4 — animatique ═════════ */
async function animatiqueEtat() {
  if (!chapter) return;
  try {
    const e = await api.get(`/chapters/${chapter.id}/animatique`);
    $("#animOpen").classList.toggle("hidden", !e.existe);
    if (e.existe) $("#animOpen").title = `Revoir l'animatique (${e.plans} plans)`;
  } catch (_) { $("#animOpen").classList.add("hidden"); }
}

async function animatique() {
  if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
  if (!shots.length) { toast("Découpe le chapitre en plans d'abord (🎬 ou ¶).", true); return; }
  const voix = confirm("Générer une voix témoin par plan ?\n\nOK = oui (la voix fixe alors la durée de chaque plan, comme sur un banc d'animatique).\nAnnuler = images muettes, aux durées réglées.");
  $("#msModal").classList.remove("hidden");
  $("#msProgress").classList.remove("hidden");
  try {
    const r = await api.send("POST", `/chapters/${chapter.id}/animatique`, { voix, language: "fr" });
    const tick = setInterval(async () => {
      const st = await api.get(`/atelier/manuscript/${r.job_id}`);
      msSetProgress(st);
      if (!st.done) return;
      clearInterval(tick);
      if (st.error) { toast("Animatique échouée : " + st.error, true); return; }
      $("#msModal").classList.add("hidden");
      await animatiqueEtat();
      ouvrirAnimatique(st.stats);
    }, 700);
  } catch (e) {
    $("#msModal").classList.add("hidden");
    toast("Animatique échouée : " + e.message, true);
  }
}

function ouvrirAnimatique(stats) {
  $("#animVideo").src = `/api/chapters/${chapter.id}/animatique.mp4?t=${Date.now()}`;
  $("#animNote").textContent = stats
    ? `${stats.plans} plans · ${stats.voix} voix témoin · ${fmtDur(stats.duree_s || 0)}`
    : "";
  $("#animModal").classList.remove("hidden");
}
```

et dans le wiring, après `$("#addShot").addEventListener(…)` (`atelier.js:1269`) :

```js
  $("#animBtn").addEventListener("click", animatique);
  $("#animOpen").addEventListener("click", () => ouvrirAnimatique(null));
  $("#animClose").addEventListener("click", () => {
    $("#animVideo").pause(); $("#animVideo").removeAttribute("src");
    $("#animModal").classList.add("hidden");
  });
```

et dans `setMode` (`atelier.js:381`), remplacer `if (board) loadShotcraft().then(() => loadShots(true));` par :

```js
  if (board) loadShotcraft().then(() => loadShots(true)).then(animatiqueEtat);
```

- [ ] **Étape 4 : CSS** — fin de `atelier.css` :

```css
/* P4 — lecteur d'animatique */
.anim-video{width:100%;max-height:70vh;background:#000;border-radius:var(--r)}
```

- [ ] **Étape 5 : vert + syntaxe** — `node --check frontend/atelier/atelier.js` (vide) ; `cd backend && $PY tests/test_chapitres_animatique.py` → `P4 ANIMATIQUE TEST: PASS`.

- [ ] **Étape 6 : commit** — sujet `chapitres : le bouton animatique, sa progression et son lecteur` ; corps : « P4, surface `/atelier`. 🎞 Animatique demande d'abord si l'on veut la voix témoin (et dit qu'elle fixera les durées), réutilise la barre de progression de l'agent manuscrit (`msSetProgress`, job store commun) et ouvre le lecteur. ▶ Revoir n'apparaît que si un montage existe. 4 assertions de miroir. »

### T12 — P5a : `screenplay_import.py` — Fountain et FDX vers scènes

**Files:**
- Create: `backend/app/services/screenplay_import.py`
- Test: `backend/tests/test_chapitres_import_scenario.py`

**Pourquoi** : réponse 8 — « import Fountain/FDX ». Le dépôt sait EXPORTER du Fountain (`MA.assemble_fountain`, `manuscript_agent.py:354`) et lire des segments de scène (`parse_fountain_segments`, `:433`) ; il ne sait pas lire un scénario complet et en faire des scènes.

- [ ] **Étape 1 : relire les deux formats AVANT d'écrire (obligatoire)** — deux `WebFetch`, exactement :

```
WebFetch url="https://fountain.io/syntax/"
         prompt="List precisely the rules for Scene Headings (prefixes INT EXT EST INT./EXT INT/EXT I/E, forced with a leading dot), Action (forced with !), Character (uppercase line with an empty line before and none after, forced with @, extensions, ^ dual dialogue), Dialogue, Parentheticals, Transitions (uppercase ending in TO:, forced with >), Title Page key: value, Sections #, Synopses =, Notes [[ ]], Boneyard /* */, Centered >text<, Page Breaks ===. Quote each rule."
WebFetch url="https://www.finaldraft.com/support/"
         prompt="Any published description of the .fdx file format: the XML root element, the Content element, Paragraph elements and their Type attribute values, and Text children. Quote verbatim, or answer ABSENT if nothing is published."
```

**Grammaire minimale supportée, fixée ici** (relue sur fountain.io/syntax le 03/09/2026) : en-tête de scène par les six préfixes suivis d'un point ou d'une espace, ou forcé par un point initial unique ; action, forcée par `!` ; personnage = ligne entièrement en capitales, précédée d'une ligne vide et suivie d'une ligne non vide, ou forcée par `@`, extension entre parenthèses tolérée, `^` de double dialogue retiré ; parenthétique entre parenthèses après un personnage ou du dialogue ; dialogue = ce qui suit ; transition = capitales terminant par `TO:` entre deux lignes vides, ou forcée par `>` (sauf `>texte<`, qui est du centré) ; page de titre `clé: valeur` avant la première ligne vide ; sections `#`, synopsis `=`, notes `[[…]]`, boneyard `/*…*/`, centré `>…<`, saut de page `===`. **Non supportés, et dits comme tels** : la mise en forme (gras, italique, souligné), les listes à puces des notes, les numéros de scène `#42#`, le lyrique `~`. Ils traversent l'import comme du texte brut.

**FDX** : aucune spécification publique n'a été trouvée le 03/09 (le WebFetch ci-dessus le confirme ou l'infirme — écrire le verdict dans le commit). Le parseur est donc écrit pour **ne pas en dépendre** : il prend n'importe quel élément `Paragraph` portant un attribut `Type`, concatène ses descendants `Text`, et traduit le type en ligne Fountain — un type inconnu devient de l'action. La grammaire Fountain reste l'unique chemin vers les scènes.

- [ ] **Étape 2 : le test qui échoue** — `backend/tests/test_chapitres_import_scenario.py` (21 assertions)

```python
"""P5 — import Fountain et FDX vers scènes. Pur, aucun réseau. 21 assertions (T12) + 8 (T13).
Run: <embedded python> backend/tests/test_chapitres_import_scenario.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services import screenplay_import as SI        # noqa: E402

FOUNTAIN = """Title: L'Éveil
Author: Deepotus

/* cette note ne doit pas sortir */

INT. CAVERNE NOYÉE - AUBE

Le Prophète observe. [[relire ce passage]]

ELIAS
(à voix basse)
Je suis venu pour la Clé.

LE PROPHÈTE ^
Tu es en retard.

CUT TO:

EXT. LONDRES - NUIT

!INT. ceci est une action forcée

.SALLE BLANCHE

@mcclane
Yippee.
"""

FDX = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Version="5">
<Content>
<Paragraph Type="Scene Heading"><Text>INT. BUREAU - JOUR</Text></Paragraph>
<Paragraph Type="Action"><Text>Elias </Text><Text>entre.</Text></Paragraph>
<Paragraph Type="Character"><Text>ELIAS</Text></Paragraph>
<Paragraph Type="Parenthetical"><Text>(sec)</Text></Paragraph>
<Paragraph Type="Dialogue"><Text>Bonjour.</Text></Paragraph>
<Paragraph Type="Shot"><Text>GROS PLAN sur la main</Text></Paragraph>
<Paragraph Type="Transition"><Text>FADE OUT.</Text></Paragraph>
<Paragraph Type="Scene Heading"><Text>EXT. RUE - NUIT</Text></Paragraph>
</Content>
</FinalDraft>
"""


def test_fountain_decoupe_en_scenes_et_lit_les_sluglines():
    doc = SI.parse_fountain(FOUNTAIN)
    assert doc["meta"]["Title"] == "L'Éveil"
    assert doc["meta"]["Author"] == "Deepotus"
    sc = doc["scenes"]
    assert [s["slugline"] for s in sc] == [
        "INT. CAVERNE NOYÉE - AUBE", "EXT. LONDRES - NUIT", "SALLE BLANCHE"]
    assert sc[0]["int_ext"] == "INT" and sc[1]["int_ext"] == "EXT"
    assert sc[0]["location"] == "CAVERNE NOYÉE"
    assert sc[0]["time_of_day"] == "AUBE"
    assert sc[1]["time_of_day"] == "NUIT"
    assert sc[2]["int_ext"] == "INT", "un en-tête forcé sans préfixe = INT"


def test_fountain_garde_le_dialogue_et_jette_notes_et_boneyard():
    sc = SI.parse_fountain(FOUNTAIN)["scenes"]
    t = sc[0]["fountain_text"]
    assert "ELIAS" in t and "(à voix basse)" in t and "Je suis venu" in t
    assert "LE PROPHÈTE" in t and "^" not in t, "le caret de double dialogue part"
    assert "relire ce passage" not in t and "[[" not in t
    assert "cette note ne doit pas sortir" not in t
    assert "CUT TO:" in t, "la transition reste dans la scène qu'elle termine"
    assert sc[1]["fountain_text"].strip().startswith("INT. ceci est une action")
    assert "MCCLANE" in sc[2]["fountain_text"]
    assert sc[0]["personnages"] == ["ELIAS", "LE PROPHÈTE"]


def test_fdx_passe_par_la_meme_grammaire():
    doc = SI.parse_fdx(FDX)
    sc = doc["scenes"]
    assert [s["slugline"] for s in sc] == ["INT. BUREAU - JOUR", "EXT. RUE - NUIT"]
    assert "Elias entre." in sc[0]["fountain_text"]
    assert sc[0]["personnages"] == ["ELIAS"]
    assert "GROS PLAN sur la main" in sc[0]["fountain_text"], \
        "un type non couvert devient de l'action, il ne disparaît pas"
    assert SI.detecter("x.FDX") == "fdx" and SI.detecter("x.fountain") == "fountain"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for _f in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        _f()
    print("P5 IMPORT SCENARIO TEST: PASS")
```

- [ ] **Étape 3 : le voir rouge** — `cd backend && $PY tests/test_chapitres_import_scenario.py` → `ModuleNotFoundError: No module named 'app.services.screenplay_import'`.

- [ ] **Étape 4 : le parseur** — `backend/app/services/screenplay_import.py` :

```python
"""P5 (03/09/2026) — importer un scénario : Fountain (spécification publique,
relue sur fountain.io/syntax le 03/09) et FDX (XML de Final Draft, sans
spécification publique trouvée le 03/09).

GRAMMAIRE FOUNTAIN SUPPORTÉE : en-tête de scène (INT, EXT, EST, INT./EXT,
INT/EXT, I/E suivis d'un point ou d'une espace ; ou point initial unique),
action (forcée par !), personnage (ligne toute en capitales, ligne vide avant
et ligne non vide après ; ou forcé par @ ; extension entre parenthèses ;
caret ^ de double dialogue retiré), parenthétique, dialogue, transition
(capitales finissant par TO:, ou forcée par >), page de titre (clé: valeur
avant la première ligne vide), sections #, synopsis =, notes [[…]], boneyard
/*…*/, centré >…<, saut de page ===.
NON SUPPORTÉ, ET TRAVERSE EN TEXTE BRUT : la mise en forme (*gras*,
_souligné_), les numéros de scène #42#, le lyrique ~.

FDX : le parseur ne dépend d'AUCUN schéma mémorisé. Il prend tout élément
`Paragraph` portant un attribut `Type`, concatène ses descendants `Text`, et
traduit le type en ligne Fountain — un type inconnu devient de l'action, il
ne disparaît jamais. Le Fountain reste l'unique chemin vers les scènes.
"""
from __future__ import annotations

import re

PREFIXES = ("INT./EXT", "INT/EXT", "I/E", "INT", "EXT", "EST")
_HEAD = re.compile(r"^(INT\./EXT|INT/EXT|I/E|INT|EXT|EST)[\.\s]",
                   re.IGNORECASE)
_TOD = ("AUBE", "MATIN", "JOUR", "MIDI", "SOIR", "CRÉPUSCULE", "CREPUSCULE",
        "NUIT", "DAY", "NIGHT", "DAWN", "DUSK", "MORNING", "EVENING",
        "CONTINUOUS", "LATER")
_CUE_EXT = re.compile(r"\s*\((?:[^()]*)\)\s*$")
_BONEYARD = re.compile(r"/\*.*?\*/", re.S)
_NOTE = re.compile(r"\[\[.*?\]\]", re.S)


def detecter(nom: str) -> str:
    """"fdx" | "fountain" — d'après l'extension, sans casse."""
    return "fdx" if (nom or "").lower().endswith(".fdx") else "fountain"


def _est_capitales(s: str) -> bool:
    lettres = [c for c in s if c.isalpha()]
    return bool(lettres) and all(c.isupper() for c in lettres)


def _slug_parts(ligne: str) -> tuple[str, str, str]:
    """(int_ext, lieu, moment) d'un en-tête de scène."""
    corps = ligne.strip()
    ie = "INT"
    m = _HEAD.match(corps)
    if m:
        tete = m.group(1).upper()
        ie = "EXT" if tete == "EXT" else "INT"
        corps = corps[m.end():].strip()
    corps = corps.lstrip(". ").strip()
    moment = "JOUR"
    parts = re.split(r"\s+[-–—]\s+", corps)
    if len(parts) > 1 and parts[-1].strip().upper() in _TOD:
        moment = parts[-1].strip().upper()
        corps = " - ".join(p.strip() for p in parts[:-1])
    return ie, corps.strip(), moment


def parse_fountain(texte: str) -> dict:
    """{meta: {clé: valeur}, scenes: [{slugline, int_ext, location,
    time_of_day, fountain_text, personnages}]}."""
    texte = _NOTE.sub("", _BONEYARD.sub("", (texte or "").replace("\r\n", "\n")))
    lignes = texte.split("\n")
    meta: dict = {}
    i = 0
    if lignes and re.match(r"^[A-Za-zÀ-ÿ ]{2,30}:", lignes[0]):
        while i < len(lignes) and lignes[i].strip():
            m = re.match(r"^([A-Za-zÀ-ÿ ]{2,30}):\s*(.*)$", lignes[i])
            if m:
                meta[m.group(1).strip()] = m.group(2).strip()
            i += 1
    scenes: list[dict] = []
    courante: dict | None = None
    corps: list[str] = []
    perso: list[str] = []

    def fermer():
        if courante is None:
            return
        courante["fountain_text"] = "\n".join(corps).strip()
        courante["personnages"] = list(dict.fromkeys(perso))
        scenes.append(courante)

    prev_vide = True
    while i < len(lignes):
        brute = lignes[i]
        ligne = brute.strip()
        suiv = lignes[i + 1].strip() if i + 1 < len(lignes) else ""
        entete = None
        if ligne.startswith(".") and not ligne.startswith(".."):
            entete = ligne[1:].strip()
        elif _HEAD.match(ligne) and _est_capitales(ligne):
            entete = ligne
        if ligne.startswith("!"):
            entete = None                       # action forcée : jamais un en-tête
            ligne = ligne[1:]
        if entete is not None:
            fermer()
            ie, lieu, moment = _slug_parts(entete)
            courante = {"slugline": entete, "int_ext": ie, "location": lieu,
                        "time_of_day": moment}
            corps, perso = [], []
            prev_vide = True
            i += 1
            continue
        if ligne.startswith("@"):
            cue = _CUE_EXT.sub("", ligne[1:].strip()).rstrip("^").strip()
            perso.append(cue.upper())
            corps.append(cue.upper())
        elif (prev_vide and ligne and suiv and _est_capitales(ligne)
                and not ligne.endswith("TO:")):
            cue = _CUE_EXT.sub("", ligne).rstrip("^").strip()
            perso.append(cue.upper())
            corps.append(ligne.rstrip("^").strip())
        elif re.fullmatch(r"={3,}", ligne):
            corps.append("")
        elif ligne.startswith("=") and not ligne.startswith("=="):
            pass                                  # synopsis : hors du texte joué
        elif ligne.startswith("#"):
            pass                                  # section : idem
        else:
            corps.append(ligne)
        prev_vide = not ligne
        i += 1
    if courante is None and any(x.strip() for x in corps):
        courante = {"slugline": "", "int_ext": "INT", "location": "",
                    "time_of_day": "JOUR"}
    fermer()
    return {"meta": meta, "scenes": scenes}


_FDX_LIGNE = {
    "scene heading": lambda t: t.upper(),
    "character": lambda t: t.upper(),
    "parenthetical": lambda t: t if t.startswith("(") else f"({t})",
    "dialogue": lambda t: t,
    "transition": lambda t: t if t.upper().endswith("TO:") else "> " + t,
}


def fdx_vers_fountain(xml: str) -> str:
    """Le XML de Final Draft rendu en Fountain — la seule grammaire que ce
    module sait découper en scènes."""
    import xml.etree.ElementTree as ET
    racine = ET.fromstring(xml)
    out: list[str] = []
    for p in racine.iter():
        if not p.tag.endswith("Paragraph"):
            continue
        typ = (p.get("Type") or "Action").strip().lower()
        txt = "".join(t.text or "" for t in p.iter()
                      if t.tag.endswith("Text")).strip()
        if not txt:
            continue
        rendu = _FDX_LIGNE.get(typ, lambda t: t)(txt)
        if typ in ("dialogue", "parenthetical") and out and out[-1] == "":
            out.pop()                              # colle la réplique au cue
        if typ not in ("dialogue", "parenthetical"):
            out.append("")
        out.append(rendu)
    return "\n".join(out).strip() + "\n"


def parse_fdx(xml: str) -> dict:
    return parse_fountain(fdx_vers_fountain(xml))


def parse(nom: str, data: bytes) -> dict:
    """Point d'entrée d'un upload : détecte, décode, découpe."""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            texte = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("fichier illisible (encodage inconnu)")
    return parse_fdx(texte) if detecter(nom) == "fdx" else parse_fountain(texte)
```

- [ ] **Étape 5 : vert** — `cd backend && $PY tests/test_chapitres_import_scenario.py` → `P5 IMPORT SCENARIO TEST: PASS`.

- [ ] **Étape 6 : commit** — sujet `chapitres : le parseur Fountain et FDX, grammaire minimale fixee` ; corps : « P5. Grammaire relue sur fountain.io/syntax le 03/09 et FIXÉE dans la docstring, avec ce qui n'est PAS supporté (mise en forme, numéros de scène, lyrique) : ils traversent en texte brut. FDX : recopier ici le verdict du WebFetch de l'étape 1 — soit la citation trouvée, soit « rien de publié le 03/09 » — le parseur ne dépend d'aucun schéma mémorisé, il traduit tout `Paragraph[Type]` en ligne Fountain et un type inconnu devient de l'action. Un seul chemin vers les scènes. 21 assertions. »

### T13 — P5b : la route d'import et le bouton `/atelier`

**Files:**
- Modify: `backend/app/api/routes.py` — route neuve après `reset_screenplay` (`:7007-7020`)
- Modify: `frontend/atelier/index.html:73` (barre du scénario)
- Modify: `frontend/atelier/atelier.js` après `adaptChapter` (`:531`), wiring `:1266`
- Test: `backend/tests/test_chapitres_import_scenario.py` (+8 assertions)

- [ ] **Étape 1 : le test qui échoue** — ajouter au fichier de T12 :

```python
def test_la_route_importe_remplace_et_versionne():
    import asyncio, pathlib, tempfile, types
    _t = tempfile.mkdtemp()
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_t,'t.db').as_posix()}"
    os.environ.setdefault("FAL_KEY", "test-key")
    os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_t, "images"))
    pathlib.Path(_t, "images").mkdir(exist_ok=True)
    sys.modules.setdefault("fal_client", types.ModuleType("fal_client"))
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            ch = (await c.post("/api/chapters", json={"title": "I"})).json()
            r = await c.post(f"/api/chapters/{ch['id']}/screenplay/import",
                             files={"file": ("s.fountain", FOUNTAIN.encode("utf-8"),
                                             "text/plain")})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["format"] == "fountain" and d["scenes"] == 3
            assert d["entites_creees"] >= 1
            sc = (await c.get(f"/api/chapters/{ch['id']}/scenes")).json()["scenes"]
            assert [s["idx"] for s in sc] == [0, 1, 2]
            assert sc[0]["time_of_day"] == "AUBE"
            assert sc[0]["location_entity_id"], "le lieu rejoint la bible"
            r = await c.post(f"/api/chapters/{ch['id']}/screenplay/import",
                             files={"file": ("s.fdx", FDX.encode("utf-8"),
                                             "text/xml")})
            assert r.json()["scenes"] == 2, "l'import REMPLACE"
            vs = (await c.get(f"/api/scenes/{sc[0]['id']}/versions")).json()["versions"]
            assert vs and vs[0]["passe"] == "import"
    asyncio.run(scenario())
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_import_scenario.py` → `AssertionError: 404` sur l'import.

- [ ] **Étape 3 : la route** — dans `routes.py`, après `reset_screenplay` (`:7020`) :

```python
@router.post("/chapters/{chapter_id}/screenplay/import")
async def import_screenplay(chapter_id: str, file: UploadFile = File(...)):
    """P5 (03/09/2026) — importe un scénario Fountain ou FDX et REMPLACE les
    scènes du chapitre. Les lieux rejoignent la bible (comme l'adaptation),
    et chaque scène remplacée laisse un instantané `import` (P2)."""
    from app.services import screenplay_import as SI
    from app.services import text_versions as TV
    from app.services.storage import (BibleEntity, Chapter, Scene,
                                      async_session_factory)
    from sqlalchemy import select
    import json as _json
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(400, "Fichier trop lourd (8 Mo max)")
    try:
        doc = await asyncio.to_thread(SI.parse, file.filename or "", data)
    except Exception as e:
        raise HTTPException(422, f"Scénario illisible : {e}")
    if not doc["scenes"]:
        raise HTTPException(422, "Aucune scène trouvée — vérifie les en-têtes "
                                 "(INT./EXT.) ou force-les par un point.")
    async with async_session_factory() as session:
        ch = await session.get(Chapter, chapter_id)
        if not ch:
            raise HTTPException(404, "Chapter not found")
        rows = (await session.execute(select(BibleEntity))).scalars().all()
        by_key = {(e.kind, e.name.strip().lower()): e for e in rows}
        crees = 0

        def trouver_ou_creer(kind: str, nom: str, desc: str):
            nonlocal crees
            cle = (kind, nom.strip().lower())
            e = by_key.get(cle)
            if e:
                return e
            e = BibleEntity(id=str(uuid4()), kind=kind, name=nom[:120],
                            description=desc, aliases="[]", evidence="[]",
                            inspiration_images="[]",
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow())
            session.add(e)
            by_key[cle] = e
            crees += 1
            return e

        for s in await _list_scenes(session, chapter_id):
            await TV.snapshot(session, "scene", s.id, s.fountain_text or "",
                              "import", {"slugline": s.slugline})
            await session.delete(s)
        n = 0
        for i, d in enumerate(doc["scenes"]):
            ids = []
            if d["location"]:
                loc = trouver_ou_creer(
                    "place", d["location"].title(),
                    f"Lieu importé du scénario de « {ch.title} ».")
                ids.append(loc.id)
            else:
                loc = None
            for nom in d["personnages"]:
                e = by_key.get(("character", nom.strip().lower()))
                if e:
                    ids.append(e.id)
            session.add(Scene(
                id=str(uuid4()), chapter_id=chapter_id, idx=i,
                slugline=d["slugline"][:200], int_ext=d["int_ext"],
                location_entity_id=(loc.id if loc else None),
                time_of_day=d["time_of_day"][:20],
                fountain_text=d["fountain_text"],
                entities=_json.dumps(list(dict.fromkeys(ids))),
                source_text=d["fountain_text"],
                created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
            n += 1
        await session.commit()
    return {"ok": True, "format": SI.detecter(file.filename or ""),
            "scenes": n, "entites_creees": crees, "meta": doc["meta"]}
```

- [ ] **Étape 4 : le bouton** — `index.html`, après `<a id="fountainDl" …>⬇ .fountain</a>` (`:73`) :

```html
        <label class="btn" for="spImport" title="Importer un scénario Fountain (.fountain, .txt) ou Final Draft (.fdx) — il REMPLACE les scènes de ce chapitre, chaque scène remplacée laissant un instantané dans 🕘 Versions">⬆ Importer scénario</label>
        <input type="file" id="spImport" accept=".fountain,.txt,.fdx" hidden>
```

et dans `atelier.js`, après `adaptChapter` (`:531`) :

```js
async function importerScenario(f) {
  if (!chapter) { toast("Ouvre un chapitre d'abord.", true); return; }
  if (scenes.length && !confirm(`Importer « ${f.name} » remplacera les ${scenes.length} scènes actuelles (un instantané est gardé). Continuer ?`)) return;
  const fd = new FormData(); fd.append("file", f);
  toast("Lecture du scénario…");
  try {
    const r = await fetch(`/api/chapters/${chapter.id}/screenplay/import`,
                          { method: "POST", body: fd });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || r.statusText);
    await loadScenes(true);
    await loadEntities(); renderBible();
    toast(`${d.scenes} scènes importées (${d.format})` +
          (d.entites_creees ? ` — ${d.entites_creees} lieu(x) ajouté(s) à la bible.` : "."));
  } catch (e) { toast("Import échoué : " + e.message, true); }
}
```

et dans le wiring, après `$("#adaptBtn").addEventListener("click", adaptChapter);` (`:1266`) :

```js
  $("#spImport").addEventListener("change", (e) => {
    const f = e.target.files && e.target.files[0];
    if (f) importerScenario(f);
    e.target.value = "";
  });
```

- [ ] **Étape 5 : vert + syntaxe** — `node --check frontend/atelier/atelier.js` (vide) ; `cd backend && $PY tests/test_chapitres_import_scenario.py` → `P5 IMPORT SCENARIO TEST: PASS` ; `$PY tests/test_screenplay.py` → `SCREENPLAY TEST: PASS`.

- [ ] **Étape 6 : commit** — sujet `chapitres : la route d'import de scenario et son bouton` ; corps : « P5. `POST /chapters/{id}/screenplay/import` (multipart, 8 Mo max) remplace les scènes, verse les lieux dans la bible comme le fait l'adaptation, et laisse un instantané `import` par scène remplacée (P2). Bouton ⬆ dans la barre Scénario, qui annonce le remplacement avant de le faire. 8 assertions. »

### T14 — P6a : `pdf_mini.py` — le PDF écrit à la main (stdlib + Pillow)

**Files:**
- Create: `backend/app/services/pdf_mini.py`
- Test: `backend/tests/test_chapitres_exports.py`

**Pourquoi** : mesuré le 03/09 dans le runtime installé — `pypdf` 6.16.2 et `python-docx` 1.2.0 présents, **`reportlab` et `fpdf` absents**. `pypdf` sait assembler et lire un PDF, pas en composer un depuis du texte. Card Forge écrit déjà des PDF à la main (`cards/print.py:2510`, `build_pdf`), mais en traçant sa propre fonte au vecteur — pour une carte de trois mots. Un chapitre entier demande du texte SÉLECTIONNABLE : on prend les fontes base-14 (Helvetica, Helvetica-Bold, Courier), qu'aucun lecteur n'a besoin de voir incorporées.

- [ ] **Étape 1 : le test qui échoue** — `backend/tests/test_chapitres_exports.py` (25 assertions ; T14 en pose 11)

```python
"""P6 — exports : PDF écrit à la main (pdf_mini), docx et PDF du chapitre et
du scénario, PDF du storyboard. 11 assertions (T14) + 7 (T15) + 7 (T16).
Run: <embedded python> backend/tests/test_chapitres_exports.py"""
import io, os, sys, pathlib, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import Image                                   # noqa: E402
from app.services import pdf_mini as PM                 # noqa: E402

TMP = pathlib.Path(tempfile.mkdtemp())


def test_les_largeurs_de_fonte_et_la_coupe_tiennent_dans_la_boite():
    assert PM.largeur("i", 12, "helv") < PM.largeur("m", 12, "helv")
    assert PM.largeur("ABC", 10, "courier") == PM.largeur("iii", 10, "courier")
    assert PM.largeur("été", 12, "helv") == PM.largeur("ete", 12, "helv"), \
        "en Helvetica un accent ne change pas la chasse de sa lettre"
    lignes = PM.couper("Le Prophète observe Elias Vane depuis la caverne "
                       "noyée d'une lumière bleutée d'aube froide.", 200, 11)
    assert len(lignes) >= 3
    assert all(PM.largeur(l, 11, "helv") <= 200 for l in lignes)
    assert " ".join(lignes) == ("Le Prophète observe Elias Vane depuis la "
                                "caverne noyée d'une lumière bleutée d'aube "
                                "froide.")
    assert PM.couper("", 200, 11) == []


def test_le_pdf_ecrit_est_relisible_par_pypdf():
    from pypdf import PdfReader
    img = TMP / "v.png"
    Image.new("RGB", (40, 60), (200, 60, 60)).save(img)
    p1 = PM.Page()
    p1.texte(60, 80, "L'Éveil — chapitre premier", 20, "helv-gras")
    p1.trait(60, 92, 535, 92)
    for i, l in enumerate(PM.couper("Elias Vane s'éveille avant l'alarme. " * 8,
                                    475, 11)):
        p1.texte(60, 120 + i * 15, l, 11)
    p2 = PM.Page()
    p2.image(60, 60, 120, 180, img)
    p2.cadre(60, 60, 120, 180)
    dest = TMP / "out.pdf"
    PM.ecrire([p1, p2], dest, titre="L'Éveil")
    assert dest.stat().st_size > 800
    assert dest.read_bytes().startswith(b"%PDF-1.4")
    r = PdfReader(str(dest))
    assert len(r.pages) == 2
    t = r.pages[0].extract_text() or ""
    assert "Éveil" in t and "Elias Vane" in t


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for _f in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        _f()
    print("P6 EXPORTS TEST: PASS")
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_exports.py` → `ModuleNotFoundError: No module named 'app.services.pdf_mini'`.

- [ ] **Étape 3 : le module** — `backend/app/services/pdf_mini.py` :

```python
"""P6 (03/09/2026) — écrire un PDF à la main : stdlib (zlib) + Pillow.

Pourquoi pas une bibliothèque : mesuré le 03/09 dans le runtime installé,
`reportlab` et `fpdf` sont ABSENTS ; `pypdf` sait lire et assembler, pas
composer. Card Forge (cards/print.py) trace sa propre fonte au vecteur —
excellent pour trois mots de cartouche, absurde pour un chapitre.

Choix : les fontes BASE-14 (Helvetica, Helvetica-Bold, Courier) en
WinAnsiEncoding. Elles ne sont pas incorporées — un contrôle avant-vol
d'imprimeur les refuserait, et c'est assumé : ces PDF se lisent et se
partagent, ils ne partent pas en presse (pour la presse, il y a Card Forge).
Le texte, lui, est SÉLECTIONNABLE et cherchable, ce qu'une page rastérisée
ne serait pas.

Les chasses sont celles des métriques Adobe (de mémoire, à vérifier) ; une
erreur de quelques millièmes ne casse rien — elle rend une coupe un peu
lâche ou un peu serrée. `couper` garde 2 % de marge pour cela.

Repère de coordonnées : ORIGINE EN HAUT À GAUCHE, en points (1/72 pouce),
converti à l'écriture. `y` d'un texte est sa LIGNE DE BASE.
"""
from __future__ import annotations

import unicodedata
import zlib
from pathlib import Path

A4 = (595.28, 841.89)
LETTER = (612.0, 792.0)
MARGE_COUPE = 0.98      # 2 % de garde sur les chasses (metriques de memoire)

_W_HELV = (
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584)
_W_GRAS = (
    278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
    975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
    333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
    611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584)

FONTES = {"helv": ("F1", "Helvetica", _W_HELV),
          "helv-gras": ("F2", "Helvetica-Bold", _W_GRAS),
          "courier": ("F3", "Courier", None)}   # None = chasse fixe 600


def _base(ch: str) -> str:
    """La lettre sans son accent : en Helvetica, « é » a la chasse de « e »."""
    d = unicodedata.normalize("NFD", ch)
    b = [c for c in d if unicodedata.category(c) != "Mn"]
    return b[0] if b else ch


def largeur(texte: str, taille: float, fonte: str = "helv") -> float:
    """Largeur en points du texte à cette taille."""
    table = FONTES.get(fonte, FONTES["helv"])[2]
    if table is None:
        return len(texte or "") * 600 * taille / 1000.0
    total = 0
    for ch in (texte or ""):
        c = _base(ch)
        o = ord(c)
        total += table[o - 32] if 32 <= o <= 126 else table[ord("n") - 32]
    return total * taille / 1000.0


def couper(texte: str, boite: float, taille: float,
           fonte: str = "helv") -> list[str]:
    """Coupe aux espaces pour tenir dans `boite` points. Un mot plus long que
    la boîte n'est PAS tronqué : il déborde seul sur sa ligne — mieux vaut un
    débordement visible qu'un mot amputé en silence."""
    mots = (texte or "").split()
    if not mots:
        return []
    lim = boite * MARGE_COUPE
    lignes, cur = [], mots[0]
    for m in mots[1:]:
        essai = cur + " " + m
        if largeur(essai, taille, fonte) <= lim:
            cur = essai
        else:
            lignes.append(cur)
            cur = m
    lignes.append(cur)
    return lignes


def _txt(s: str) -> bytes:
    """Chaîne PDF littérale en WinAnsi (cp1252), parenthèses échappées."""
    b = (s or "").encode("cp1252", "replace")
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


class Page:
    """Une page. Coordonnées EN HAUT À GAUCHE, en points."""

    def __init__(self, taille=A4):
        self.w, self.h = taille
        self.items: list[dict] = []

    def texte(self, x, y, s, taille=11, fonte="helv", gris=0.0):
        self.items.append({"t": "texte", "x": x, "y": y, "s": s,
                           "taille": taille, "fonte": fonte, "gris": gris})
        return self

    def trait(self, x1, y1, x2, y2, ep=0.7, gris=0.35):
        self.items.append({"t": "trait", "x1": x1, "y1": y1, "x2": x2,
                           "y2": y2, "ep": ep, "gris": gris})
        return self

    def cadre(self, x, y, w, h, ep=0.6, gris=0.5):
        self.items.append({"t": "cadre", "x": x, "y": y, "w": w, "h": h,
                           "ep": ep, "gris": gris})
        return self

    def image(self, x, y, w, h, chemin):
        self.items.append({"t": "image", "x": x, "y": y, "w": w, "h": h,
                           "src": Path(chemin)})
        return self


def _image_objet(chemin: Path) -> tuple[bytes, int, int]:
    from PIL import Image
    im = Image.open(chemin).convert("RGB")
    if max(im.size) > 1400:                       # un PDF de storyboard n'a
        im.thumbnail((1400, 1400), Image.LANCZOS)  # pas besoin de 4K
    return zlib.compress(im.tobytes(), 6), im.size[0], im.size[1]


def ecrire(pages: list[Page], dest: Path, titre: str = "") -> Path:
    """Écrit le PDF. Un objet par page, un flux de contenu, un XObject par
    image, trois fontes base-14 déclarées une fois."""
    dest = Path(dest)
    objets: list[bytes] = []

    def ajouter(corps: bytes) -> int:
        objets.append(corps)
        return len(objets)

    ajouter(b"")                                   # 1 = catalogue (rempli plus bas)
    ajouter(b"")                                   # 2 = arbre des pages
    fontes_ref = {}
    for cle, (nom_res, base, _w) in FONTES.items():
        n = ajouter(b"<< /Type /Font /Subtype /Type1 /BaseFont /" +
                    base.encode("ascii") + b" /Encoding /WinAnsiEncoding >>")
        fontes_ref[cle] = (nom_res, n)
    pages_refs = []
    for pg in pages:
        ops: list[bytes] = []
        xobjets: list[bytes] = []
        for k, it in enumerate(pg.items):
            if it["t"] == "texte":
                nom_res = fontes_ref[it["fonte"] if it["fonte"] in fontes_ref
                                     else "helv"][0]
                ops.append(b"BT /" + nom_res.encode("ascii") +
                           b" %.2f Tf %.3f g %.2f %.2f Td (" % (
                               it["taille"], it["gris"], it["x"],
                               pg.h - it["y"]) + _txt(it["s"]) + b") Tj ET")
            elif it["t"] == "trait":
                ops.append(b"%.3f G %.2f w %.2f %.2f m %.2f %.2f l S" % (
                    it["gris"], it["ep"], it["x1"], pg.h - it["y1"],
                    it["x2"], pg.h - it["y2"]))
            elif it["t"] == "cadre":
                ops.append(b"%.3f G %.2f w %.2f %.2f %.2f %.2f re S" % (
                    it["gris"], it["ep"], it["x"], pg.h - it["y"] - it["h"],
                    it["w"], it["h"]))
            else:
                data, iw, ih = _image_objet(it["src"])
                n = ajouter(b"<< /Type /XObject /Subtype /Image /Width %d "
                            b"/Height %d /ColorSpace /DeviceRGB "
                            b"/BitsPerComponent 8 /Filter /FlateDecode "
                            b"/Length %d >>\nstream\n" % (iw, ih, len(data))
                            + data + b"\nendstream")
                nom = b"/Im%d" % k
                xobjets.append(nom + b" %d 0 R" % n)
                ops.append(b"q %.2f 0 0 %.2f %.2f %.2f cm " % (
                    it["w"], it["h"], it["x"], pg.h - it["y"] - it["h"])
                    + nom + b" Do Q")
        flux = zlib.compress(b"\n".join(ops), 6)
        n_flux = ajouter(b"<< /Length %d /Filter /FlateDecode >>\nstream\n"
                         % len(flux) + flux + b"\nendstream")
        res = (b"/Font << " + b" ".join(
            b"/" + fontes_ref[c][0].encode("ascii") + b" %d 0 R"
            % fontes_ref[c][1] for c in FONTES) + b" >>")
        if xobjets:
            res += b" /XObject << " + b" ".join(xobjets) + b" >>"
        pages_refs.append(ajouter(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] "
            b"/Resources << %s >> /Contents %d 0 R >>"
            % (pg.w, pg.h, res, n_flux)))
    kids = b" ".join(b"%d 0 R" % n for n in pages_refs)
    objets[1] = (b"<< /Type /Pages /Kids [" + kids + b"] /Count %d >>"
                 % len(pages_refs))
    n_info = ajouter(b"<< /Title (" + _txt(titre) +
                     b") /Producer (DeepotusVideoGen pdf_mini) >>")
    objets[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    sortie = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, corps in enumerate(objets, start=1):
        offsets.append(len(sortie))
        sortie += b"%d 0 obj\n" % i + corps + b"\nendobj\n"
    xref = len(sortie)
    sortie += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objets) + 1)
    for off in offsets:
        sortie += b"%010d 00000 n \n" % off
    sortie += (b"trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R >>\n"
               b"startxref\n%d\n%%%%EOF\n"
               % (len(objets) + 1, n_info, xref))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(bytes(sortie))
    return dest
```

- [ ] **Étape 4 : vert** — `cd backend && $PY tests/test_chapitres_exports.py` → `P6 EXPORTS TEST: PASS`.

- [ ] **Étape 5 : commit** — sujet `chapitres : pdf_mini, le PDF ecrit a la main en stdlib et Pillow` ; corps : « P6. Mesuré : `reportlab` et `fpdf` absents du runtime installé, `pypdf` sait lire et assembler mais pas composer. Fontes base-14 (Helvetica, Helvetica-Bold, Courier) en WinAnsiEncoding, non incorporées — assumé : ces PDF se lisent, ils ne partent pas en presse ; en échange le texte est sélectionnable. Coordonnées en haut à gauche, images en Flate/DeviceRGB, xref écrite à la main. Le PDF produit est relu par `pypdf` dans le banc. 11 assertions. »

### T15 — P6b : `text_export.py` — docx et PDF du chapitre et du scénario

**Files:**
- Create: `backend/app/services/text_export.py`
- Modify: `backend/app/api/routes.py` — routes neuves après `get_chapter_screenplay` (`:6771-6789`)
- Test: `backend/tests/test_chapitres_exports.py` (+7 assertions)

- [ ] **Étape 1 : le test qui échoue** — ajouter au fichier de T14 :

```python
def test_docx_et_pdf_du_chapitre_et_du_scenario():
    import asyncio, types
    _t = pathlib.Path(tempfile.mkdtemp())
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_t/'t.db').as_posix()}"
    os.environ.setdefault("FAL_KEY", "test-key")
    os.environ["IMAGES_FOLDER"] = str(_t / "images")
    (_t / "images").mkdir(exist_ok=True)
    sys.modules.setdefault("fal_client", types.ModuleType("fal_client"))
    import docx                                            # noqa: F401
    from pypdf import PdfReader
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            ch = (await c.post("/api/chapters", json={
                "title": "L'Éveil",
                "script_text": "Elias s'éveille.\n\nLe Prophète observe."})).json()
            r = await c.get(f"/api/chapters/{ch['id']}/export.docx")
            assert r.status_code == 200
            assert r.headers["content-type"].startswith(
                "application/vnd.openxmlformats")
            d = docx.Document(io.BytesIO(r.content))
            paras = [p.text for p in d.paragraphs]
            assert paras[0] == "L'Éveil"
            assert "Le Prophète observe." in paras
            r = await c.get(f"/api/chapters/{ch['id']}/export.pdf")
            assert r.status_code == 200 and r.content.startswith(b"%PDF")
            t = PdfReader(io.BytesIO(r.content)).pages[0].extract_text() or ""
            assert "Elias" in t and "Éveil" in t
            r = await c.get(f"/api/chapters/{ch['id']}/export.pdf?kind=scenario")
            assert r.status_code == 400, "pas de scenes : refus qui le dit"
    asyncio.run(scenario())
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_exports.py` → `AssertionError: 404` sur `export.docx`.

- [ ] **Étape 3 : le module** — `backend/app/services/text_export.py` :

```python
"""P6 (03/09/2026) — exports mis en page du chapitre et du scénario.

docx par python-docx 1.2.0 (mesuré présent) ; PDF par pdf_mini (base-14).
Deux mises en page :
  - MANUSCRIT : A4, Helvetica 11/15, titre en gras, paragraphes séparés.
  - SCÉNARIO : Letter (le format du métier), Courier 12/14,4 — les retraits
    (cue à 3,7", parenthétique à 3,1", dialogue à 2,5", action à 1,5") sont
    ceux de la tradition américaine, DE MÉMOIRE, à vérifier : ils ne
    conditionnent aucune décision du plan, seulement l'allure d'un export.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.services import pdf_mini as PM

PO = 72.0                                  # points par pouce
M_HAUT, M_BAS = 72.0, 72.0
MANU_GAUCHE, MANU_LARGEUR = 72.0, 451.28   # A4 : 595,28 - 2 x 72
SC_ACTION, SC_DIALOGUE, SC_PAREN, SC_CUE = 1.5, 2.5, 3.1, 3.7
SC_LARGEUR = {"action": 6.0 * PO, "dialogue": 3.5 * PO, "paren": 2.5 * PO}


def _pages(blocs, taille_page, interligne, fonte, taille):
    """Découpe une suite de (x, texte, fonte, taille) en pages."""
    pages, page = [], PM.Page(taille_page)
    y = M_HAUT
    for x, texte, f, t in blocs:
        if texte == "":
            y += interligne
            continue
        if y > taille_page[1] - M_BAS:
            pages.append(page)
            page = PM.Page(taille_page)
            y = M_HAUT
        page.texte(x, y, texte, t, f)
        y += interligne
    pages.append(page)
    return pages


def chapitre_pdf(titre: str, texte: str, dest: Path) -> Path:
    blocs = [(MANU_GAUCHE, titre, "helv-gras", 20), (0, "", "helv", 0)]
    for para in re.split(r"\n\s*\n", texte or ""):
        for ligne in PM.couper(para.strip(), MANU_LARGEUR, 11):
            blocs.append((MANU_GAUCHE, ligne, "helv", 11))
        blocs.append((0, "", "helv", 0))
    return PM.ecrire(_pages(blocs, PM.A4, 15.0, "helv", 11), dest, titre)


def _classer(ligne: str) -> str:
    s = ligne.strip()
    if not s:
        return "vide"
    if re.match(r"^(INT|EXT|EST|INT\./EXT|INT/EXT|I/E)[\.\s]", s, re.I):
        return "entete"
    if s.startswith("(") and s.endswith(")"):
        return "paren"
    lettres = [c for c in s if c.isalpha()]
    if lettres and all(c.isupper() for c in lettres):
        return "transition" if s.endswith("TO:") else "cue"
    return "texte"


def scenario_pdf(titre: str, fountain: str, dest: Path) -> Path:
    """Le scénario au format du métier : Courier 12, retraits par élément.
    Une ligne de texte qui suit un cue ou un parenthétique est du dialogue."""
    blocs = [(SC_ACTION * PO, titre.upper(), "courier", 12), (0, "", "courier", 0)]
    prec = "vide"
    for brute in (fountain or "").splitlines():
        k = _classer(brute)
        if k == "vide":
            blocs.append((0, "", "courier", 0))
            prec = k
            continue
        if k == "texte" and prec in ("cue", "paren", "dialogue"):
            k = "dialogue"
        x, larg = {
            "entete": (SC_ACTION * PO, SC_LARGEUR["action"]),
            "transition": (SC_CUE * PO, SC_LARGEUR["action"]),
            "cue": (SC_CUE * PO, SC_LARGEUR["dialogue"]),
            "paren": (SC_PAREN * PO, SC_LARGEUR["paren"]),
            "dialogue": (SC_DIALOGUE * PO, SC_LARGEUR["dialogue"]),
        }.get(k, (SC_ACTION * PO, SC_LARGEUR["action"]))
        texte = brute.strip()
        if k in ("entete", "transition"):
            texte = texte.upper()
        for ligne in PM.couper(texte, larg, 12, "courier"):
            blocs.append((x, ligne, "courier", 12))
        prec = k
    return PM.ecrire(_pages(blocs, PM.LETTER, 14.4, "courier", 12), dest, titre)


def chapitre_docx(titre: str, texte: str, dest: Path) -> Path:
    import docx
    d = docx.Document()
    d.add_heading(titre, level=1)
    for para in re.split(r"\n\s*\n", texte or ""):
        if para.strip():
            d.add_paragraph(para.strip())
    dest.parent.mkdir(parents=True, exist_ok=True)
    d.save(str(dest))
    return dest


def scenario_docx(titre: str, fountain: str, dest: Path) -> Path:
    """Le scénario en docx : Courier New 12, retraits par style de ligne."""
    import docx
    from docx.shared import Inches, Pt
    d = docx.Document()
    st = d.styles["Normal"]
    st.font.name = "Courier New"
    st.font.size = Pt(12)
    d.add_paragraph(titre.upper())
    prec = "vide"
    for brute in (fountain or "").splitlines():
        k = _classer(brute)
        if k == "vide":
            prec = k
            continue
        if k == "texte" and prec in ("cue", "paren", "dialogue"):
            k = "dialogue"
        p = d.add_paragraph(brute.strip().upper()
                            if k in ("entete", "transition") else brute.strip())
        p.paragraph_format.left_indent = Inches(
            {"entete": SC_ACTION, "transition": SC_CUE, "cue": SC_CUE,
             "paren": SC_PAREN, "dialogue": SC_DIALOGUE}.get(k, SC_ACTION))
        prec = k
    dest.parent.mkdir(parents=True, exist_ok=True)
    d.save(str(dest))
    return dest
```

- [ ] **Étape 4 : les routes** — dans `routes.py`, après `get_chapter_screenplay` (`:6789`) :

```python
def _export_nom(titre: str, ext: str) -> str:
    base = "".join(c for c in (titre or "chapitre")
                   if c.isalnum() or c in " -_")[:60].strip() or "chapitre"
    return f"{base}.{ext}"


async def _export_matiere(chapter_id: str, kind: str):
    """(chapitre, texte) pour l'export — le manuscrit ou le scénario
    assemblé. 400 explicite quand le scénario n'existe pas encore."""
    from app.services import manuscript_agent as MA
    from app.services.storage import Chapter, async_session_factory
    async with async_session_factory() as session:
        ch = await session.get(Chapter, chapter_id)
        if not ch:
            raise HTTPException(404, "Chapter not found")
        if kind == "scenario":
            scenes = [_scene_dict(s)
                      for s in await _list_scenes(session, chapter_id)]
            if not scenes:
                raise HTTPException(400, "Pas de scénario — lance 🎭 Adapter "
                                         "ou importe un .fountain/.fdx.")
            return ch, MA.assemble_fountain(ch.title, scenes)
        if not (ch.script_text or "").strip():
            raise HTTPException(400, "Le chapitre est vide")
        return ch, ch.script_text


@router.get("/chapters/{chapter_id}/export.docx")
async def export_chapter_docx(chapter_id: str, kind: str = "manuscrit"):
    """P6 — docx mis en page. ?kind=manuscrit|scenario."""
    from app.services import text_export as TE
    import tempfile as _tf
    ch, texte = await _export_matiere(chapter_id, kind)
    dest = Path(_tf.mkdtemp()) / _export_nom(ch.title, "docx")
    fn = TE.scenario_docx if kind == "scenario" else TE.chapitre_docx
    await asyncio.to_thread(fn, ch.title, texte, dest)
    return FileResponse(
        dest, filename=dest.name,
        media_type=("application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"))


@router.get("/chapters/{chapter_id}/export.pdf")
async def export_chapter_pdf(chapter_id: str, kind: str = "manuscrit"):
    """P6 — PDF mis en page (pdf_mini). ?kind=manuscrit|scenario."""
    from app.services import text_export as TE
    import tempfile as _tf
    ch, texte = await _export_matiere(chapter_id, kind)
    dest = Path(_tf.mkdtemp()) / _export_nom(ch.title, "pdf")
    fn = TE.scenario_pdf if kind == "scenario" else TE.chapitre_pdf
    await asyncio.to_thread(fn, ch.title, texte, dest)
    return FileResponse(dest, filename=dest.name, media_type="application/pdf")
```

- [ ] **Étape 5 : vert** — `cd backend && $PY tests/test_chapitres_exports.py` → `P6 EXPORTS TEST: PASS`.

- [ ] **Étape 6 : commit** — sujet `chapitres : docx et PDF mis en page du chapitre et du scenario` ; corps : « P6. Manuscrit : A4, Helvetica 11/15. Scénario : Letter, Courier 12/14,4, retraits par élément (cue, parenthétique, dialogue, action) — retraits **de mémoire, à vérifier**, ils ne conditionnent rien d'autre que l'allure. Un export scénario sans scènes est un 400 qui dit quoi faire. 7 assertions, docx relu par python-docx et PDF par pypdf. »

### T16 — P6c : le PDF du storyboard, et les liens dans `/atelier`

**Files:**
- Modify: `backend/app/services/text_export.py` (ajout de `storyboard_pdf`)
- Modify: `backend/app/api/routes.py` (route neuve après `export_chapter_pdf`)
- Modify: `frontend/atelier/index.html:36` (barre du script), `:73` (barre scénario), `:86` (barre storyboard)
- Modify: `frontend/atelier/atelier.js` — `openChapter` (`:62-73`), `setMode` (`:371-384`)
- Test: `backend/tests/test_chapitres_exports.py` (+7 assertions de contenu et de miroir)

- [ ] **Étape 1 : le test qui échoue** — ajouter au fichier :

```python
def test_le_pdf_du_storyboard_porte_une_fiche_par_plan():
    # PAS de reset d'environnement ici : app.config est deja importe par le
    # test precedent, et un DATABASE_URL/IMAGES_FOLDER change apres coup
    # n'aurait aucun effet (le moteur et settings sont crees a l'import).
    # Ce banc travaille donc sur la meme base, avec un autre chapitre.
    import asyncio, types
    from pypdf import PdfReader
    from httpx import AsyncClient, ASGITransport
    sys.modules.setdefault("fal_client", types.ModuleType("fal_client"))
    from app.main import app
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            ch = (await c.post("/api/chapters", json={
                "title": "Board", "script_text": "Vane entre.\n\nIl se tait."})).json()
            shots = (await c.post(f"/api/chapters/{ch['id']}/storyboard/decoupe",
                                  json={"method": "paragraph"})).json()["shots"]
            await c.put(f"/api/shots/{shots[0]['id']}",
                        json={"action": "Vane pousse la porte", "duration_s": 4.5})
            r = await c.get(f"/api/chapters/{ch['id']}/storyboard.pdf")
            assert r.status_code == 200 and r.content.startswith(b"%PDF")
            t = PdfReader(io.BytesIO(r.content)).pages[0].extract_text() or ""
            assert "PLAN 1/2" in t and "Vane pousse la porte" in t
            assert "4.5 s" in t and "medium" in t
            await c.delete(f"/api/chapters/{ch['id']}/shots")
            assert (await c.get(
                f"/api/chapters/{ch['id']}/storyboard.pdf")).status_code == 400
    asyncio.run(scenario())


def test_la_source_atelier_porte_les_trois_liens_d_export():
    r = pathlib.Path(__file__).resolve().parents[2]
    html = r.joinpath("frontend/atelier/index.html").read_text("utf-8")
    js = r.joinpath("frontend/atelier/atelier.js").read_text("utf-8")
    for i in ("dlDocx", "dlPdf", "dlBoardPdf", "dlScDocx", "dlScPdf"):
        assert f'id="{i}"' in html, i
    assert "function majLiensExport(" in js
    assert js.count("export.pdf") >= 1 and "storyboard.pdf" in js
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_exports.py` → `AssertionError: 404` sur `storyboard.pdf`.

- [ ] **Étape 3 : la mise en page** — ajouter à la fin de `text_export.py` :

```python
FICHE_H = 180.0          # hauteur d'une fiche de plan, en points
VIGNETTE_W = 190.0


def storyboard_pdf(titre: str, shots: list[dict], noms: dict,
                   images: Path, dest: Path) -> Path:
    """P6 — la planche de travail : une fiche par plan (vignette, numéro,
    durée, cadrage, caméra, action, entités), quatre par page A4. `noms` =
    {entity_id: nom}. Une vignette manquante laisse un cadre vide légendé —
    on ne cache pas qu'un plan n'a pas encore d'image."""
    pages: list[PM.Page] = []
    page = None
    total = round(sum(float(s.get("duration_s") or 0) for s in shots), 1)
    for i, s in enumerate(shots):
        rang = i % 4
        if rang == 0:
            page = PM.Page(PM.A4)
            pages.append(page)
            page.texte(MANU_GAUCHE, 54, titre, 16, "helv-gras")
            page.texte(MANU_GAUCHE + 360, 54,
                       f"{len(shots)} plans · {total} s", 10, "helv", 0.35)
            page.trait(MANU_GAUCHE, 62, 523, 62)
        y = 84 + rang * FICHE_H
        page.cadre(MANU_GAUCHE, y, VIGNETTE_W, 107)
        fichier = s.get("image") or s.get("sketch_image")
        if fichier and (images / fichier).is_file():
            page.image(MANU_GAUCHE + 2, y + 2, VIGNETTE_W - 4, 103,
                       images / fichier)
        else:
            page.texte(MANU_GAUCHE + 40, y + 58, "(pas encore d'image)", 9,
                       "helv", 0.55)
        x = MANU_GAUCHE + VIGNETTE_W + 16
        page.texte(x, y + 12, f"PLAN {i + 1}/{len(shots)}", 12, "helv-gras")
        page.texte(x, y + 28,
                   f"{s.get('shot_type') or ''} · {s.get('camera_move') or ''}",
                   9, "helv", 0.35)
        page.texte(x, y + 42, f"{float(s.get('duration_s') or 0)} s", 9,
                   "helv", 0.35)
        ligne = y + 60
        for txt in PM.couper(s.get("action") or "", 245, 10)[:5]:
            page.texte(x, ligne, txt, 10)
            ligne += 13
        ents = [noms.get(e, "?") for e in (s.get("entities") or [])]
        if ents:
            page.texte(x, ligne + 4, "⛓ " + ", ".join(ents)[:90], 9,
                       "helv", 0.4)
        page.trait(MANU_GAUCHE, y + 120, 523, y + 120, 0.4, 0.75)
    return PM.ecrire(pages or [PM.Page(PM.A4)], dest, titre + " — storyboard")
```

- [ ] **Étape 4 : la route** — dans `routes.py`, après `export_chapter_pdf` :

```python
@router.get("/chapters/{chapter_id}/storyboard.pdf")
async def export_storyboard_pdf(chapter_id: str):
    """P6 — le PDF du storyboard : une fiche par plan (vignette, durée,
    cadrage, caméra, action, entités), quatre par page."""
    from app.services import text_export as TE
    from app.services.storage import (BibleEntity, Chapter,
                                      async_session_factory)
    from sqlalchemy import select
    import tempfile as _tf
    async with async_session_factory() as session:
        ch = await session.get(Chapter, chapter_id)
        if not ch:
            raise HTTPException(404, "Chapter not found")
        shots = [_shot_dict(s) for s in await _list_shots(session, chapter_id)]
        rows = (await session.execute(select(BibleEntity))).scalars().all()
    if not shots:
        raise HTTPException(400, "Pas de storyboard — découpe le chapitre "
                                 "(🎬 ou ¶) d'abord.")
    noms = {e.id: e.name for e in rows}
    dest = Path(_tf.mkdtemp()) / _export_nom(ch.title + " storyboard", "pdf")
    await asyncio.to_thread(TE.storyboard_pdf, ch.title, shots, noms,
                            settings.images_path, dest)
    return FileResponse(dest, filename=dest.name, media_type="application/pdf")
```

- [ ] **Étape 5 : les liens `/atelier`** — `index.html`, dans `.script-actions` (`:36`, après l'input caché) :

```html
      <a id="dlDocx" class="btn ghost" title="Le manuscrit de ce chapitre, mis en page en .docx (Word, LibreOffice)" download>⬇ .docx</a>
      <a id="dlPdf" class="btn ghost" title="Le manuscrit de ce chapitre en PDF A4, texte sélectionnable" download>⬇ .pdf</a>
```

dans la barre du scénario, après `<a id="fountainDl" …>` (`:73`) :

```html
        <a id="dlScDocx" class="btn ghost" title="Le scénario en .docx, Courier 12 et retraits du métier" download>⬇ .docx</a>
        <a id="dlScPdf" class="btn ghost" title="Le scénario en PDF Letter, Courier 12 et retraits du métier" download>⬇ .pdf</a>
```

dans la barre du storyboard, après `<button id="animOpen" …>` (`:86`) :

```html
        <a id="dlBoardPdf" class="btn ghost" title="La planche de travail : une fiche par plan (vignette, durée, cadrage, caméra, action, entités), quatre par page A4" download>⬇ storyboard .pdf</a>
```

et dans `atelier.js`, après `openChapter` (`:73`) :

```js
function majLiensExport() {
  const id = chapter ? chapter.id : null;
  const liens = {
    dlDocx: id && `/api/chapters/${id}/export.docx`,
    dlPdf: id && `/api/chapters/${id}/export.pdf`,
    dlScDocx: id && `/api/chapters/${id}/export.docx?kind=scenario`,
    dlScPdf: id && `/api/chapters/${id}/export.pdf?kind=scenario`,
    dlBoardPdf: id && `/api/chapters/${id}/storyboard.pdf`,
  };
  Object.entries(liens).forEach(([k, href]) => {
    const el = $("#" + k);
    if (!el) return;
    el.href = href || "#";
    el.classList.toggle("hidden", !href);
  });
}
```

et appeler `majLiensExport();` à la fin de `openChapter` (après `await loadVectorDocs();`) et à la fin de `setMode` (après le bloc `if (sp) loadScenes(true);`).

- [ ] **Étape 6 : vert + syntaxe** — `node --check frontend/atelier/atelier.js` (vide) ; `cd backend && $PY tests/test_chapitres_exports.py` → `P6 EXPORTS TEST: PASS`.

- [ ] **Étape 7 : commit** — sujet `chapitres : le PDF du storyboard et les cinq liens d'export` ; corps : « P6. `GET /chapters/{id}/storyboard.pdf` : quatre fiches par page A4 — vignette (image de production sinon croquis), numéro, durée, cadrage, caméra, action coupée à cinq lignes, entités liées. Un plan sans image affiche « (pas encore d'image) » : le trou se voit. Cinq liens de téléchargement dans les trois barres de `/atelier`, cachés tant qu'aucun chapitre n'est ouvert. »

---

## Lot 2 — différenciant

### T17 — D1 : réécriture et génération à la demande, dans le ton de la bible

**Files:**
- Create: `backend/app/services/reecriture.py`
- Modify: `backend/app/api/routes.py` — route neuve après `chapter_versions` (`:5773+`, cf. T4)
- Modify: `frontend/atelier/index.html:39-51` (`#selBar`), `:252` (modale)
- Modify: `frontend/atelier/atelier.js` — `refreshSelBar` (`:164-174`), après `addSpan` (`:193`), wiring `:1258`
- Test: `backend/tests/test_chapitres_reecriture.py`

**Pourquoi** : réponse 6 — « polissage/réécriture à la demande et génération de scènes ou de dialogues souhaités ; aucune zone interdite ». Le différenciant, c'est que la passe reçoit **la bible visuelle ET le casting de voix** du projet — aucune référence relue le 03/09 ne relie les deux — et qu'elle **ne peut pas écraser** : le résultat est une proposition, l'application est un second appel qui prend un instantané (P2).

- [ ] **Étape 1 : le test qui échoue** — `backend/tests/test_chapitres_reecriture.py` (17 assertions)

```python
"""D1 — réécriture / génération dans le ton de la bible. LLM stubbé.
17 assertions. Run: <embedded python> backend/tests/test_chapitres_reecriture.py"""
import asyncio, os, sys, tempfile, pathlib, types
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.modules["fal_client"] = types.ModuleType("fal_client")
from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.main import app                               # noqa: E402
from app.services.storage import init_db               # noqa: E402
from app.services import summarizer as SUMZ            # noqa: E402
from app.services import reecriture as RE              # noqa: E402

VUS = []


def _stub(prompt, system, max_tokens):
    VUS.append({"prompt": prompt, "system": system})
    return "Elias franchit le seuil, la Cle serree.", "stub"

SUMZ._chat_dispatch = _stub
SUMZ.available = lambda: True


def test_les_actions_sont_closes_et_chacune_a_sa_consigne():
    assert set(RE.ACTIONS) == {"reformuler", "resserrer", "traduire",
                               "scene", "dialogue"}
    for a in RE.ACTIONS:
        assert len(RE.ACTIONS[a]["consigne"]) > 20, a
        assert RE.ACTIONS[a]["mode"] in ("remplace", "insere")
    assert RE.ACTIONS["scene"]["mode"] == "insere"
    assert RE.ACTIONS["resserrer"]["mode"] == "remplace"


def test_la_passe_propose_puis_applique_et_versionne():
    async def scenario():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            await c.post("/api/bible/entities", json={
                "kind": "character", "name": "Elias Vane",
                "description": "homme fatigue"})
            await c.put("/api/atelier/settings", json={"global_style": "vitrail"})
            ch = (await c.post("/api/chapters", json={
                "title": "R", "script_text": "Elias entre. Il tient la Cle."})).json()
            VUS.clear()
            r = await c.post(f"/api/chapters/{ch['id']}/reecrire", json={
                "start": 0, "end": 12, "action": "resserrer"})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["proposition"].startswith("Elias franchit")
            assert d["mode"] == "remplace" and d["applique"] is False
            assert "Elias Vane" in VUS[0]["prompt"], "la bible est injectee"
            assert "vitrail" in VUS[0]["prompt"], "le style du projet aussi"
            assert "resserr" in VUS[0]["system"].lower()
            inchange = (await c.get(f"/api/chapters/{ch['id']}")).json()
            assert inchange["script_text"].startswith("Elias entre.")
            assert (await c.get(
                f"/api/chapters/{ch['id']}/versions")).json()["versions"] == []
            r = await c.post(f"/api/chapters/{ch['id']}/reecrire", json={
                "start": 0, "end": 12, "action": "resserrer",
                "appliquer": True, "texte": d["proposition"]})
            assert r.json()["applique"] is True
            got = (await c.get(f"/api/chapters/{ch['id']}")).json()["script_text"]
            assert got == "Elias franchit le seuil, la Cle serree. Il tient la Cle."
            vs = (await c.get(f"/api/chapters/{ch['id']}/versions")).json()["versions"]
            assert len(vs) == 1 and vs[0]["passe"] == "reecriture"
            r = await c.post(f"/api/chapters/{ch['id']}/reecrire", json={
                "start": 0, "end": 3, "action": "inventer"})
            assert r.status_code == 400 and "inventer" in r.text
    asyncio.run(scenario())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for _f in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        _f()
    print("D1 REECRITURE TEST: PASS")
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_reecriture.py` → `ModuleNotFoundError: No module named 'app.services.reecriture'`.

- [ ] **Étape 3 : le service** — `backend/app/services/reecriture.py` :

```python
"""D1 (03/09/2026) — réécrire ou engendrer un passage DANS LE TON DE LA BIBLE.

Ce que fait le différenciant : la passe reçoit la bible du projet (les noms,
les descriptions, et pour les personnages LA VOIX CASTÉE), le style global de
la DA, et la phrase exacte à traiter. Aucune référence relue le 03/09 ne
relie une réécriture à une bible visuelle ET à un casting de voix.

Ce qu'elle ne fait jamais : écrire. `construire` est pur, la route propose,
et seule une seconde requête (`appliquer: true`) écrit — après instantané
(P2). Réponse 6 : aucune zone interdite déclarée ; la garde est la version,
pas l'interdiction.
"""
from __future__ import annotations

ACTIONS = {
    "reformuler": {
        "mode": "remplace",
        "consigne": ("Réécris ce passage dans la même voix et la même "
                     "longueur approximative. Ne change ni les faits, ni les "
                     "noms, ni l'ordre des événements."),
    },
    "resserrer": {
        "mode": "remplace",
        "consigne": ("Resserre ce passage : même sens, même voix, un tiers de "
                     "mots en moins. Coupe les redondances et les adverbes, "
                     "garde chaque fait."),
    },
    "traduire": {
        "mode": "remplace",
        "consigne": ("Traduis ce passage dans la langue demandée, en gardant "
                     "les noms propres de la bible intacts et le registre "
                     "d'origine."),
    },
    "scene": {
        "mode": "insere",
        "consigne": ("Écris UNE scène nouvelle qui suit immédiatement ce "
                     "passage : ce que l'on voit, ce qui se dit, où cela se "
                     "passe. Sers-toi des lieux et des objets de la bible ; "
                     "n'invente pas de personnage absent de la bible."),
    },
    "dialogue": {
        "mode": "insere",
        "consigne": ("Écris un échange de répliques entre les personnages de "
                     "la bible présents dans ce passage. Chaque personnage "
                     "parle selon sa fiche ET selon le grain de la voix qui "
                     "lui est castée. Aucune didascalie superflue."),
    },
}


def bloc_bible(entites: list[dict], style: str = "") -> str:
    """La bible telle qu'un modèle doit la lire : nom, sorte, description
    courte, alias, et la VOIX castée quand il y en a une."""
    lignes = []
    for e in entites:
        bout = f"- {e['name']} ({e['kind']})"
        if e.get("description"):
            bout += f" : {e['description'][:140]}"
        if e.get("aliases"):
            bout += f" [alias : {', '.join(e['aliases'][:4])}]"
        if e.get("voice_name"):
            bout += f" [voix : {e['voice_name']}]"
        lignes.append(bout)
    tete = "\n".join(lignes) or "(bible vide)"
    return (f"BIBLE DU PROJET :\n{tete}\n"
            + (f"\nSTYLE DE RÉALISATION DU PROJET : {style}\n" if style else ""))


def construire(action: str, passage: str, contexte: str,
               entites: list[dict], style: str = "",
               langue: str = "fr") -> tuple[str, str, str]:
    """(system, prompt, mode). PUR — aucun appel réseau, testable seul."""
    if action not in ACTIONS:
        raise ValueError(f"action inconnue : {action}")
    spec = ACTIONS[action]
    langname = "français" if langue.startswith("fr") else "anglais"
    system = ("Tu es l'assistant d'écriture d'un auteur, sur SON manuscrit. "
              "Tu rends UNIQUEMENT le texte demandé, sans préambule, sans "
              "guillemets d'encadrement et sans commentaire. Consigne : "
              + spec["consigne"])
    prompt = (bloc_bible(entites, style)
              + f"\nLANGUE DE SORTIE : {langname}.\n"
              + (f"\nCONTEXTE (ne pas réécrire) :\n{contexte[:2000]}\n"
                 if contexte else "")
              + f"\nPASSAGE À TRAITER :\n{passage}\n")
    return system, prompt, spec["mode"]


def nettoyer(sortie: str) -> str:
    """Un modèle bavard ajoute des guillemets ou un « Voici : » — on les
    retire, sinon ils entrent dans le manuscrit."""
    t = (sortie or "").strip()
    for tete in ("Voici", "Bien sûr", "Here"):
        if t.startswith(tete) and ":" in t[:60]:
            t = t.split(":", 1)[1].strip()
    if len(t) > 1 and t[0] in "\"«“" and t[-1] in "\"»”":
        t = t[1:-1].strip()
    return t
```

- [ ] **Étape 4 : la route** — dans `routes.py`, après `chapter_versions` (route de T4) :

```python
@router.post("/chapters/{chapter_id}/reecrire")
async def reecrire_passage(chapter_id: str, body: dict):
    """D1 — réécrit ou engendre un passage dans le ton de la bible.
    Body: {start, end, action, language?, appliquer?, texte?}.
    SANS `appliquer`, rien n'est écrit : la réponse est une PROPOSITION.
    Avec `appliquer: true` et `texte`, le manuscrit est modifié après
    instantané (P2, passe `reecriture`)."""
    from app.services import reecriture as RE
    from app.services import text_versions as TV
    from app.services.storage import Chapter, async_session_factory
    from app.services.summarizer import available, _chat_dispatch
    action = str(body.get("action") or "").strip()
    if action not in RE.ACTIONS:
        raise HTTPException(400, f"Action « {action } » inconnue — "
                                 f"attendu : {', '.join(RE.ACTIONS)}.")
    async with async_session_factory() as session:
        ch = await session.get(Chapter, chapter_id)
        if not ch:
            raise HTTPException(404, "Chapter not found")
        texte = ch.script_text or ""
        try:
            a = max(0, min(len(texte), int(body.get("start", 0))))
            b = max(a, min(len(texte), int(body.get("end", 0))))
        except (TypeError, ValueError):
            raise HTTPException(400, "start et end doivent être des entiers")
        if b <= a:
            raise HTTPException(400, "Sélectionne d'abord un passage.")
        mode = RE.ACTIONS[action]["mode"]
        if body.get("appliquer"):
            neuf = str(body.get("texte") or "").strip()
            if not neuf:
                raise HTTPException(400, "Rien à appliquer.")
            await TV.snapshot(session, "chapter", ch.id, texte, "reecriture",
                              {"action": action, "start": a, "end": b})
            ch.script_text = (texte[:a] + neuf + texte[b:] if mode == "remplace"
                              else texte[:b] + "\n\n" + neuf + texte[b:])
            ch.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(ch)
            return {"applique": True, "mode": mode, "chapter": _chapter_dict(ch)}
        if not available():
            raise HTTPException(400, "Aucun LLM configuré (Réglages → clés).")
        ents = (await list_bible_entities(None))["entities"]
        style = await _atelier_setting(session, "global_style")
    system, prompt, mode = RE.construire(
        action, texte[a:b], texte[max(0, a - 900):a], ents, style,
        str(body.get("language") or "fr").lower())
    loop = asyncio.get_running_loop()
    out, prov = await loop.run_in_executor(
        None, lambda: _chat_dispatch(prompt, system, 2000))
    if not out:
        raise HTTPException(502, "Le modèle n'a rien renvoyé — réessaie.")
    return {"applique": False, "mode": mode, "action": action,
            "provider": prov, "proposition": RE.nettoyer(out),
            "start": a, "end": b}
```

- [ ] **Étape 5 : la surface `/atelier`** — `index.html`, dans `#selBar` après `<select id="linkSelect" …>` (`:47-51`) :

```html
      <select id="reeAction" title="Demander au modèle une passe sur la sélection — la bible et le casting de voix lui sont donnés">
        <option value="">✍ Réécrire…</option>
        <option value="reformuler">Reformuler</option>
        <option value="resserrer">Resserrer</option>
        <option value="traduire">Traduire</option>
        <option value="scene">Proposer une scène</option>
        <option value="dialogue">Proposer un dialogue</option>
      </select>
```

et avant `<div id="toast" …>` (`:252`) :

```html
<div id="reeModal" class="modal hidden">
  <div class="modal-box">
    <div class="modal-head">
      <b id="reeTitre">Proposition</b>
      <span id="reeNote" class="da-note"></span>
      <button id="reeClose" class="btn ghost">✕</button>
    </div>
    <textarea id="reeTexte" rows="12" class="ree-texte"></textarea>
    <div class="modal-actions">
      <button id="reeAppliquer" class="btn primary">✔ Appliquer</button>
      <button id="reeAnnuler" class="btn ghost">Laisser tel quel</button>
    </div>
  </div>
</div>
```

et dans `atelier.js`, après `addSpan` (`:193`) :

```js
/* ═════════ D1 — réécriture dans le ton de la bible ═════════ */
let reeEnCours = null;      // {start, end, mode}

async function reecrire(action) {
  const sel = currentSelection();
  if (!chapter || !sel) { toast("Sélectionne un passage d'abord.", true); return; }
  toast("Le modèle relit la bible… (5-20 s)");
  try {
    const d = await api.send("POST", `/chapters/${chapter.id}/reecrire`, {
      start: sel.start, end: sel.end, action, language: "fr" });
    reeEnCours = { start: d.start, end: d.end, mode: d.mode };
    $("#reeTitre").textContent = d.mode === "remplace"
      ? "Proposition — remplacera la sélection"
      : "Proposition — sera insérée après la sélection";
    $("#reeNote").textContent = `${action} · ${d.provider}`;
    $("#reeTexte").value = d.proposition;
    $("#reeModal").classList.remove("hidden");
  } catch (e) { toast("Réécriture échouée : " + e.message, true); }
}

async function reecrireAppliquer() {
  if (!reeEnCours) return;
  try {
    const d = await api.send("POST", `/chapters/${chapter.id}/reecrire`, {
      start: reeEnCours.start, end: reeEnCours.end,
      action: $("#reeAction").value || "reformuler",
      appliquer: true, texte: $("#reeTexte").value });
    chapter = d.chapter;
    $("#script").value = chapter.script_text;
    renderScript();
    $("#reeModal").classList.add("hidden");
    reeEnCours = null;
    toast("Appliqué — l'état d'avant est dans 🕘 Versions.");
  } catch (e) { toast("Application échouée : " + e.message, true); }
}
```

et dans le wiring, après `$("#linkSelect").addEventListener(…)` (`:1258`) :

```js
  $("#reeAction").addEventListener("change", (e) => {
    const a = e.target.value; e.target.value = "";
    if (a) reecrire(a);
  });
  $("#reeAppliquer").addEventListener("click", reecrireAppliquer);
  ["#reeClose", "#reeAnnuler"].forEach(s => $(s).addEventListener("click",
    () => { $("#reeModal").classList.add("hidden"); reeEnCours = null; }));
```

et en CSS, fin de `atelier.css` : `.ree-texte{width:100%;font-family:var(--f-mono);font-size:12.5px;line-height:1.55;background:var(--bg-panel-3);color:var(--ink);border:1px solid var(--stroke);border-radius:var(--r);padding:10px}`

- [ ] **Étape 6 : vert + syntaxe** — `node --check frontend/atelier/atelier.js` (vide) ; `cd backend && $PY tests/test_chapitres_reecriture.py` → `D1 REECRITURE TEST: PASS`.

- [ ] **Étape 7 : commit** — sujet `chapitres : reecrire et engendrer dans le ton de la bible, sans jamais ecraser` ; corps : « D1. Cinq passes closes (reformuler, resserrer, traduire, scène, dialogue), chacune avec son mode (remplace / insère). Le prompt porte la bible — descriptions, alias, **et la voix castée de chaque personnage** — plus le style global de la DA : aucune référence relue le 03/09 ne relie la réécriture à une bible visuelle ET à un casting de voix. Deux temps : la première requête PROPOSE, la seconde applique après instantané (P2). `nettoyer` retire les « Voici : » et les guillemets d'encadrement. 17 assertions, LLM stubbé. »

### T18 — D2a : `sorties.py` — un chapitre, quatre sorties (le plan, pur)

**Files:**
- Create: `backend/app/services/sorties.py`
- Test: `backend/tests/test_chapitres_sorties.py`

**Pourquoi** : réponse 7 — « les quatre : épisodes narrés 9:16, plans vidéo montés en film, le manuscrit lui-même (livre), reels courts ». Tout existe en morceaux (`pipeline.run_episode`, l'animatique de T10, les exports de T15) ; ce qui manque est **le choix de la sortie depuis la même bible et le même storyboard**.

- [ ] **Étape 1 : le test qui échoue** — `backend/tests/test_chapitres_sorties.py` (31 assertions ; T18 en pose 17)

```python
"""D2 — un chapitre, quatre sorties. Le plan est PUR. 17 (T18) + 5 (T19) + 9 (T20) assertions.
Run: <embedded python> backend/tests/test_chapitres_sorties.py"""
import os, sys, pathlib, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services import sorties as SO                  # noqa: E402

SHOTS = [
    {"id": "a", "idx": 0, "action": "Vane entre", "duration_s": 6.0,
     "energy": 2, "image": "a.png", "sketch_image": None},
    {"id": "b", "idx": 1, "action": "La Cle brille", "duration_s": 9.0,
     "energy": 5, "image": None, "sketch_image": "b.png"},
    {"id": "c", "idx": 2, "action": "Le Prophete parle", "duration_s": 12.0,
     "energy": 4, "image": None, "sketch_image": None},
    {"id": "d", "idx": 3, "action": "Noir", "duration_s": 40.0,
     "energy": 1, "image": None, "sketch_image": None},
]
SCENES = [
    {"id": "s1", "idx": 0, "slugline": "INT. CAVERNE - AUBE",
     "fountain_text": "Le Prophete observe.", "vo_audio": "vo1.mp3",
     "duration_s": 3.2},
    {"id": "s2", "idx": 1, "slugline": "EXT. LONDRES - NUIT",
     "fountain_text": "La pluie tombe.", "vo_audio": None, "duration_s": None},
]


def test_les_quatre_sorties_sont_closes_et_decrites():
    assert set(SO.SORTIES) == {"episode", "film", "reel", "livre"}
    for k, v in SO.SORTIES.items():
        assert v["quoi"] and v["depuis"] in ("scenes", "plans", "texte")
    assert SO.SORTIES["reel"]["depuis"] == "plans"
    assert SO.SORTIES["livre"]["depuis"] == "texte"


def test_l_episode_reprend_la_charge_utile_de_episodes_render():
    p = SO.episode(SCENES, {"s1": "img1.png"})
    assert [s["text"] for s in p] == ["Le Prophete observe.", "La pluie tombe."]
    assert p[0]["image_filename"] == "img1.png" and p[1]["image_filename"] is None
    assert p[0]["motion"] == "kenburns"


def test_le_reel_choisit_la_fenetre_la_plus_intense_dans_la_borne():
    f = SO.reel(SHOTS, mini=15.0, maxi=60.0, cible=30.0)
    assert [s["id"] for s in f["plans"]] == ["a", "b", "c"]
    assert f["duree_s"] == 27.0
    assert f["energie"] == 11
    court = SO.reel([SHOTS[0]], mini=15.0, maxi=60.0, cible=30.0)
    assert court["plans"] == [] and "15" in court["pourquoi"]


def test_les_clips_de_montage_pointent_les_fichiers_de_l_animatique():
    d = pathlib.Path(tempfile.mkdtemp())
    for i in range(3):
        (d / f"p{i:03d}.mp4").write_bytes(b"mp4")
    entrees = [{"idx": i, "shot_id": s["id"], "dur": s["duration_s"],
                "image": s["image"], "texte": s["action"], "carton": False,
                "source_duree": "plan"} for i, s in enumerate(SHOTS[:3])]
    clips = SO.clips_montage(entrees, d)
    assert [c["tr"] for c in clips] == ["v1", "v1", "v1"]
    assert clips[0]["start"] == 0.0 and clips[0]["end"] == 6.0
    assert clips[1]["start"] == 6.0 and clips[2]["end"] == 27.0
    assert clips[0]["src"] == {"file_path": str(d / "p000.mp4")}
    assert clips[1]["label"].startswith("PLAN 2")
    assert clips[0]["transition"] == "cut" and clips[1]["transition"] == "xfade 0.4"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for _f in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        _f()
    print("D2 SORTIES TEST: PASS")
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_sorties.py` → `ModuleNotFoundError: No module named 'app.services.sorties'`.

- [ ] **Étape 3 : le service** — `backend/app/services/sorties.py` :

```python
"""D2 (03/09/2026) — un chapitre, quatre sorties, depuis la MÊME bible et le
MÊME storyboard : épisode narré 9:16, film des plans, reel court, livre.

Tout est PUR ici : ces fonctions décrivent une sortie, elles ne rendent rien.
Les moteurs existent déjà (pipeline.run_episode, animatique_service,
text_export) — ce module est le carrefour qui leur donne leur charge utile.
"""
from __future__ import annotations

from pathlib import Path

SORTIES = {
    "episode": {"quoi": "Épisode narré 9:16 — une image par scène, la voix "
                        "du casting, Ken Burns.", "depuis": "scenes"},
    "film": {"quoi": "Film des plans — l'animatique montée, ouverte au "
                     "Montage pour y remplacer les croquis.", "depuis": "plans"},
    "reel": {"quoi": "Reel court — la fenêtre de plans la plus intense entre "
                     "15 et 60 s, avec les images déjà générées.",
             "depuis": "plans"},
    "livre": {"quoi": "Livre — le manuscrit mis en page (docx, PDF).",
              "depuis": "texte"},
}


def episode(scenes: list[dict], images: dict | None = None) -> list[dict]:
    """La charge utile de POST /episodes/render : {text, image_filename,
    motion} par scène, dans l'ordre. `images` = {scene_id: filename}."""
    images = images or {}
    return [{"text": (s.get("fountain_text") or "").strip(),
             "image_filename": images.get(s.get("id")),
             "motion": "kenburns"}
            for s in sorted(scenes, key=lambda x: x.get("idx", 0))]


def reel(shots: list[dict], mini: float = 15.0, maxi: float = 60.0,
         cible: float = 30.0) -> dict:
    """La FENÊTRE de plans consécutifs qui tient entre `mini` et `maxi`
    secondes, et qui porte le plus d'énergie (la somme des niveaux 1-5 du
    storyboard) ; à énergie égale, la plus proche de `cible`. Rien ne tient ?
    On le dit, on ne rogne pas un plan de force."""
    ordre = sorted(shots, key=lambda x: x.get("idx", 0))
    best = None
    for i in range(len(ordre)):
        total = 0.0
        for j in range(i, len(ordre)):
            total += float(ordre[j].get("duration_s") or 0)
            if total > maxi:
                break
            if total < mini:
                continue
            energie = sum(int(s.get("energy") or 3) for s in ordre[i:j + 1])
            cle = (energie, -abs(total - cible))
            if best is None or cle > best[0]:
                best = (cle, ordre[i:j + 1], round(total, 3), energie)
    if best is None:
        total = round(sum(float(s.get("duration_s") or 0) for s in ordre), 1)
        return {"plans": [], "duree_s": total, "energie": 0,
                "pourquoi": f"Aucune suite de plans ne tient entre {mini:.0f} "
                            f"et {maxi:.0f} s (storyboard : {total} s au "
                            f"total). Ajuste les durées ou découpe plus fin."}
    _, plans, duree, energie = best
    return {"plans": plans, "duree_s": duree, "energie": energie,
            "pourquoi": f"{len(plans)} plans consécutifs, {duree} s, "
                        f"énergie cumulée {energie}."}


def clips_montage(entrees: list[dict], dossier: Path,
                  fondu: float = 0.4) -> list[dict]:
    """Les clips de timeline d'une animatique : un par plan, bout à bout, au
    format que Montage sauvegarde (montage_service.montage_save). Chaque
    `src` est un {file_path} — la forme que _resolve_src accepte
    (montage_service.py:734) — pour qu'un plan GÉNÉRÉ puisse plus tard
    remplacer son croquis sans toucher au minutage."""
    clips, t = [], 0.0
    for e in sorted(entrees, key=lambda x: x["idx"]):
        f = Path(dossier) / f"p{e['idx']:03d}.mp4"
        fin = round(t + float(e["dur"]), 3)
        clips.append({
            "tr": "v1", "id": f"v1_p{e['idx']:03d}",
            "label": f"PLAN {e['idx'] + 1} · {(e.get('texte') or '')[:36]}",
            "start": round(t, 3), "end": fin,
            "src": {"file_path": str(f)}, "srcIn": 0,
            "shot_id": e.get("shot_id"),
            "transition": "cut" if not clips else f"xfade {fondu}",
            "transition_s": 0.0 if not clips else fondu})
        t = fin
    return clips
```

- [ ] **Étape 4 : vert** — `cd backend && $PY tests/test_chapitres_sorties.py` → `D2 SORTIES TEST: PASS`.

- [ ] **Étape 5 : commit** — sujet `chapitres : le carrefour des quatre sorties, en fonctions pures` ; corps : « D2. `episode` rend la charge utile exacte de `/episodes/render` ; `reel` choisit la fenêtre de plans consécutifs la plus intense entre 15 et 60 s (énergie du storyboard, puis proximité de la cible) et REFUSE en disant pourquoi quand rien ne tient ; `clips_montage` produit des clips `{file_path}` — la forme que `_resolve_src` accepte (`montage_service.py:734`) — en portant le `shot_id` pour le remplacement de D3. Aucun rendu ici : que des fonctions pures. 17 assertions. »

### T19 — D2b : la route de sortie et le sélecteur `/atelier`

**Files:**
- Modify: `backend/app/api/routes.py` — route neuve après `animatique_rendre` (T10)
- Modify: `frontend/atelier/index.html:86` (barre storyboard)
- Modify: `frontend/atelier/atelier.js` après `ouvrirAnimatique` (T11), wiring
- Test: `backend/tests/test_chapitres_sorties.py` (+5 assertions)

- [ ] **Étape 1 : le test qui échoue** — ajouter au fichier de T18 :

```python
def test_la_route_de_sortie_annonce_avant_de_faire():
    import asyncio, types
    from httpx import AsyncClient, ASGITransport
    _t = pathlib.Path(tempfile.mkdtemp())
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_t/'t.db').as_posix()}"
    os.environ.setdefault("FAL_KEY", "test-key")
    os.environ["IMAGES_FOLDER"] = str(_t / "images")
    os.environ["OUTPUTS_FOLDER"] = str(_t / "outputs")
    (_t / "images").mkdir(exist_ok=True)
    sys.modules.setdefault("fal_client", types.ModuleType("fal_client"))
    from app.main import app
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            ch = (await c.post("/api/chapters", json={
                "title": "S", "script_text": "un\n\ndeux"})).json()
            r = await c.get(f"/api/chapters/{ch['id']}/sorties")
            assert r.status_code == 200
            d = {s["kind"]: s for s in r.json()["sorties"]}
            assert set(d) == {"episode", "film", "reel", "livre"}
            assert d["livre"]["pret"] is True
            assert d["film"]["pret"] is False and "animatique" in d["film"]["manque"]
            assert (await c.post(f"/api/chapters/{ch['id']}/sortie/reel",
                                 json={})).status_code == 400
    asyncio.run(scenario())
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_sorties.py` → `AssertionError: 404` sur `/sorties`.

- [ ] **Étape 3 : les routes** — dans `routes.py`, après `_run_animatique_job` (T10) :

```python
@router.get("/chapters/{chapter_id}/sorties")
async def sorties_disponibles(chapter_id: str):
    """D2 — les quatre sorties du chapitre, chacune avec ce qui lui manque.
    Une sortie qui n'est pas prête DIT pourquoi : c'est la moitié du
    différenciant — le studio annonce, il ne rate pas en silence."""
    from app.services import animatique_service as AN
    from app.services import sorties as SO
    from app.services.storage import Chapter, async_session_factory
    async with async_session_factory() as session:
        ch = await session.get(Chapter, chapter_id)
        if not ch:
            raise HTTPException(404, "Chapter not found")
        shots = [_shot_dict(s) for s in await _list_shots(session, chapter_id)]
        scenes = [_scene_dict(s) for s in await _list_scenes(session, chapter_id)]
    anim = (AN.dossier(settings.outputs_path, chapter_id)
            / "animatique.mp4").is_file()
    manques = {
        "episode": "" if scenes else "des scènes (🎭 Adapter ou ⬆ importer)",
        "film": "" if anim else "une animatique montée (🎞)",
        "reel": "" if shots else "un storyboard (🎬 ou ¶)",
        "livre": "" if (ch.script_text or "").strip() else "du texte",
    }
    return {"chapter_id": chapter_id, "sorties": [
        {"kind": k, **SO.SORTIES[k], "pret": not manques[k],
         "manque": manques[k]} for k in ("episode", "film", "reel", "livre")]}


@router.post("/chapters/{chapter_id}/sortie/{kind}")
async def produire_sortie(chapter_id: str, kind: str, body: dict,
                          background_tasks: BackgroundTasks):
    """D2 — produit la sortie demandée depuis la même bible et le même
    storyboard. `episode` lance un rendu (job) ; `film` et `reel` posent une
    timeline dans le Montage ; `livre` rend les liens d'export."""
    from app.services import animatique_service as AN
    from app.services import sorties as SO
    from app.services.storage import Chapter, async_session_factory
    if kind not in SO.SORTIES:
        raise HTTPException(400, f"Sortie « {kind} » inconnue — attendu : "
                                 f"{', '.join(SO.SORTIES)}.")
    async with async_session_factory() as session:
        ch = await session.get(Chapter, chapter_id)
        if not ch:
            raise HTTPException(404, "Chapter not found")
        shots = [_shot_dict(s) for s in await _list_shots(session, chapter_id)]
        scenes = [_scene_dict(s) for s in await _list_scenes(session, chapter_id)]
    if kind == "livre":
        return {"ok": True, "kind": kind, "liens": {
            "docx": f"/api/chapters/{chapter_id}/export.docx",
            "pdf": f"/api/chapters/{chapter_id}/export.pdf",
            "storyboard_pdf": f"/api/chapters/{chapter_id}/storyboard.pdf"}}
    if kind == "episode":
        if not scenes:
            raise HTTPException(400, "Pas de scènes — 🎭 Adapter ou ⬆ importer.")
        images = {s["id"]: None for s in scenes}
        for i, s in enumerate(scenes):
            m = next((x for x in shots if x["idx"] == i), None)
            images[s["id"]] = (m or {}).get("image") or (m or {}).get("sketch_image")
        jid = str(uuid4())
        background_tasks.add_task(
            pipeline.run_episode, job_id=jid, title=ch.title,
            language=str(body.get("language") or "fr"),
            scenes=SO.episode(scenes, images))
        return {"ok": True, "kind": kind, "job_id": jid,
                "message": f"Épisode en rendu — suivre GET /api/jobs/{jid}."}
    if not shots:
        raise HTTPException(400, "Pas de storyboard — 🎬 ou ¶ d'abord.")
    d = AN.dossier(settings.outputs_path, chapter_id)
    if not (d / "animatique.mp4").is_file():
        raise HTTPException(400, "Monte l'animatique (🎞) d'abord : le film "
                                 "et le reel réutilisent ses clips.")
    retenus = shots
    pourquoi = f"{len(shots)} plans"
    if kind == "reel":
        f = SO.reel(shots)
        if not f["plans"]:
            raise HTTPException(400, f["pourquoi"])
        retenus, pourquoi = f["plans"], f["pourquoi"]
    entrees = [e for e in AN.plan(shots)
               if e["shot_id"] in {s["id"] for s in retenus}]
    clips = SO.clips_montage(entrees, d)
    return await _poser_timeline(ch, kind, clips, pourquoi)
```

- [ ] **Étape 4 : le sélecteur `/atelier`** — `index.html`, après `<a id="dlBoardPdf" …>` (`:86`) :

```html
        <select id="sortieSelect" title="Produire une sortie depuis ce chapitre : la même bible et le même storyboard servent les quatre">
          <option value="">🎯 Sortie…</option>
        </select>
```

et dans `atelier.js`, après `ouvrirAnimatique` (T11) :

```js
async function chargerSorties() {
  if (!chapter) return;
  const sel = $("#sortieSelect");
  try {
    const { sorties } = await api.get(`/chapters/${chapter.id}/sorties`);
    sel.innerHTML = `<option value="">🎯 Sortie…</option>` + sorties.map(s =>
      `<option value="${s.kind}" ${s.pret ? "" : "disabled"} title="${esc(s.quoi)}">${
        s.kind}${s.pret ? "" : ` — manque ${esc(s.manque)}`}</option>`).join("");
  } catch (_) { /* le sélecteur reste tel quel */ }
}

async function produireSortie(kind) {
  try {
    const d = await api.send("POST", `/chapters/${chapter.id}/sortie/${kind}`, {});
    if (kind === "livre") { window.open(d.liens.pdf, "_blank"); return; }
    if (kind === "episode") { toast("Épisode en rendu — suis-le dans la Bibliothèque."); return; }
    toast(`${d.clips} clips posés dans le Montage (${d.pourquoi}).`);
  } catch (e) { toast("Sortie échouée : " + e.message, true); }
}
```

wiring, après le bloc animatique de T11 :

```js
  $("#sortieSelect").addEventListener("change", (e) => {
    const k = e.target.value; e.target.value = "";
    if (k) produireSortie(k);
  });
```

et ajouter `chargerSorties();` à la fin de `animatiqueEtat()` (T11).

- [ ] **Étape 5 : vert** — `node --check frontend/atelier/atelier.js` (vide) ; `cd backend && $PY tests/test_chapitres_sorties.py` → `D2 SORTIES TEST: PASS`. **`_poser_timeline` est écrite en T20** : jusque-là, la route `film`/`reel` lève `NameError` — c'est pourquoi le test de T19 n'exerce que `/sorties` et le refus 400.

- [ ] **Étape 6 : commit** — sujet `chapitres : la route des quatre sorties et son selecteur` ; corps : « D2. `GET /sorties` dit, pour chacune des quatre, si elle est prête et **ce qui lui manque** — le sélecteur affiche l'option grisée avec le manque, au lieu d'échouer après le clic. `livre` rend des liens, `episode` lance `pipeline.run_episode` avec les images des plans, `film`/`reel` posent une timeline (T20). 5 assertions. »

### T20 — D3 : l'animatique s'ouvre au Montage, et un plan généré remplace son croquis

**Files:**
- Modify: `backend/app/api/routes.py` — helper `_poser_timeline` avant `sorties_disponibles` (T19)
- Test: `backend/tests/test_chapitres_sorties.py` (+9 assertions)

**Pourquoi** : réponse D3 — « chaque plan de l'animatique devient un clip de la timeline ; un plan généré remplace son croquis sans perdre le timing ». Mesuré : le Montage lit une sauvegarde JSON (`montage_service.py:467`, `_write_saved`) et `_resolve_src` (`:734`) accepte `{"file_path": …}`.

- [ ] **Étape 1 : le test qui échoue** — ajouter au fichier de T18 :

```python
def test_l_animatique_se_pose_au_montage_et_le_plan_genere_remplace_son_croquis():
    # PAS de reset d'environnement (cf. T16) : settings est deja fige par le
    # test precedent. Ce banc reutilise la meme base et le meme dossier de
    # sorties, avec un autre chapitre.
    import asyncio, types
    from httpx import AsyncClient, ASGITransport
    from PIL import Image
    sys.modules.setdefault("fal_client", types.ModuleType("fal_client"))
    from app.main import app
    from app.services.storage import init_db
    from app.services import animatique_service as AN
    from app.config import settings

    async def scenario():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            ch = (await c.post("/api/chapters", json={
                "title": "M", "script_text": "un\n\ndeux"})).json()
            shots = (await c.post(f"/api/chapters/{ch['id']}/storyboard/decoupe",
                                  json={"method": "paragraph"})).json()["shots"]
            d = AN.dossier(settings.outputs_path, ch["id"])
            (d / "animatique.mp4").write_bytes(b"mp4")
            for i in range(2):
                (d / f"p{i:03d}.mp4").write_bytes(b"mp4")
            r = await c.post(f"/api/chapters/{ch['id']}/sortie/film", json={})
            assert r.status_code == 200, r.text
            assert r.json()["clips"] == 2
            proj = (await c.get("/api/montage/project")).json()
            assert proj["saved"] is True
            assert [x["tr"] for x in proj["clips"]] == ["v1", "v1"]
            assert proj["clips"][0]["src"]["file_path"].endswith("p000.mp4")
            t0 = (proj["clips"][0]["start"], proj["clips"][0]["end"])
            # un plan GÉNÉRÉ remplace son croquis : la source change, pas le temps
            Image.new("RGB", (32, 32), (1, 2, 3)).save(_t / "images" / "g.png")
            (d / "rendu000.mp4").write_bytes(b"mp4")
            r = await c.post(f"/api/shots/{shots[0]['id']}/vers-montage",
                             json={"file_path": str(d / "rendu000.mp4")})
            assert r.status_code == 200, r.text
            proj = (await c.get("/api/montage/project")).json()
            assert proj["clips"][0]["src"]["file_path"].endswith("rendu000.mp4")
            assert (proj["clips"][0]["start"], proj["clips"][0]["end"]) == t0
            assert proj["clips"][1]["src"]["file_path"].endswith("p001.mp4")
    asyncio.run(scenario())
```

- [ ] **Étape 2 : le voir rouge** — `cd backend && $PY tests/test_chapitres_sorties.py` → `NameError: name '_poser_timeline' is not defined`.

- [ ] **Étape 3 : le helper et la route de remplacement** — dans `routes.py`, avant `sorties_disponibles` (T19) :

```python
async def _poser_timeline(ch, kind: str, clips: list, pourquoi: str) -> dict:
    """D3 — pose ces clips comme projet du Montage. On passe par la MÊME
    sauvegarde que l'éditeur (montage_service, écriture atomique) : rouvrir
    le Montage suffit, il n'y a rien à importer."""
    from app.services import montage_service as MS
    from datetime import datetime as _dt
    data = {"name": f"{ch.title[:60]} — {kind}", "ratio": "9:16",
            "duration": round(max((c["end"] for c in clips), default=0.0), 3),
            "mix": {"dialogue": -6, "musique": -18, "sfx": -12},
            "duration_master": True, "ducking": True, "clips": clips,
            "saved_at": _dt.utcnow().replace(microsecond=0).isoformat() + "Z"}
    await asyncio.to_thread(MS._write_saved, data)
    return {"ok": True, "kind": kind, "clips": len(clips),
            "duree_s": data["duration"], "pourquoi": pourquoi,
            "message": "Timeline posée — ouvre le Montage."}


@router.post("/shots/{shot_id}/vers-montage")
async def shot_vers_montage(shot_id: str, body: dict):
    """D3 — remplace, DANS LA TIMELINE DÉJÀ POSÉE, le clip d'animatique de ce
    plan par un rendu, SANS toucher au minutage : seule la source change.
    Body: {file_path} (un rendu sur disque) ou {job_id} (un rendu de la
    Bibliothèque). Le clip est retrouvé par son `shot_id`, jamais par son
    rang : réordonner le storyboard entre-temps ne casse rien."""
    from app.services import montage_service as MS
    from app.services.storage import Shot, async_session_factory
    async with async_session_factory() as session:
        s = await session.get(Shot, shot_id)
        if not s:
            raise HTTPException(404, "Shot not found")
    saved = await asyncio.to_thread(MS._load_saved)
    if not saved:
        raise HTTPException(400, "Aucune timeline posée — produis d'abord la "
                                 "sortie « film » ou « reel » (🎯).")
    src = None
    if body.get("job_id"):
        src = {"job_id": str(body["job_id"])}
    elif body.get("file_path"):
        p = Path(str(body["file_path"]))
        if not p.is_file():
            raise HTTPException(400, f"Fichier introuvable : {p}")
        src = {"file_path": str(p)}
    if not src:
        raise HTTPException(400, "Donne {file_path} ou {job_id}.")
    vus = 0
    for c in saved["clips"]:
        if c.get("shot_id") == shot_id:
            c["src"] = src
            c["label"] = (c.get("label") or "") + " · rendu"
            vus += 1
    if not vus:
        raise HTTPException(404, "Ce plan n'est pas dans la timeline posée.")
    await asyncio.to_thread(MS._write_saved, saved)
    return {"ok": True, "clips_remplaces": vus, "shot_id": shot_id}
```

- [ ] **Étape 4 : vert** — `cd backend && $PY tests/test_chapitres_sorties.py` → `D2 SORTIES TEST: PASS`. Non-régression : `$PY tests/test_montage_effects.py` → `PASS`.

- [ ] **Étape 5 : commit** — sujet `chapitres : l'animatique se pose au Montage, et un rendu remplace son croquis` ; corps : « D3. La timeline passe par la sauvegarde de l'éditeur (`montage_service._write_saved`, écriture atomique) : rien à importer, il suffit d'ouvrir le Montage. Chaque clip porte son `shot_id` ; `POST /shots/{id}/vers-montage` échange la seule `src` et laisse `start`/`end` intacts — le minutage de l'animatique est le contrat, le rendu ne le renégocie pas. Le clip est retrouvé par `shot_id`, jamais par rang : réordonner le storyboard entre-temps ne casse rien. 9 assertions. »

---

## Écarté

- **E1 — ordre imposé texte → image ou image → texte** : réponse 4, « les deux selon le projet ». Rien n'est ajouté ; les deux chemins restent ouverts et aucune route de ce plan ne présuppose l'ordre.
- **E2 — zones interdites aux LLM** : réponse 6, aucune déclarée. La garde est la version (P2, T3–T5), qui rend toute passe réversible — pas une liste d'interdits qu'il faudrait maintenir.
- **E3 — progressions façon NovelCrafter** (l'évolution d'un personnage dans le temps) : non demandées ; la bible relationnelle (P1, T1–T2) et la fiche « apparitions » couvrent le besoin exprimé, et une progression sans demande serait une table de plus à tenir.

---

## Campagne de mutations

### T21 — `mutations_chapitres.py` : casser, voir rouge, remettre

**Files:**
- Create: `backend/tests/mutations_chapitres.py`

**Pourquoi** : le patron du dépôt (`backend/tests/mutations_plaque_slicer.py`, 428 lignes, lot B de l'Établi) a trouvé une ligne morte, un trou d'assertion et un mutant faible que la relecture avait laissés passer. Une mutation **VERTE** est une assertion qui manque : c'est l'argument de la revue, pas une formalité. Différence avec le patron : Chapitres a **huit bancs**, pas un — chaque mutation nomme donc SON banc.

- [ ] **Étape 1 : le fichier** — `backend/tests/mutations_chapitres.py`

```python
"""Banc de mutations de la catégorie Chapitres : casser → rouge → remettre.

PAS UN TEST : pytest ne le collecte pas (le nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas (il filtre `test_*.py`). Il se lance À LA
MAIN, depuis backend/ :

    <embedded python> tests/mutations_chapitres.py         # toutes
    <embedded python> tests/mutations_chapitres.py 3 17     # celles-là

Il MUTE les sources du dépôt une à une et les REMET à l'octet près
(assertion sha256), donc il ne se lance pas pendant qu'un autre banc lit ces
fichiers. Chaque mutation : (fichier, ancien, nouveau, banc, tests attendus
rouges). Différence avec mutations_plaque_slicer : le BANC est par mutation —
Chapitres en a huit.

Une mutation « VERTE » est une assertion qui manque. C'est le seul verdict
qui demande du travail.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable

VERS = "tests/test_chapitres_versions.py"
REL = "tests/test_chapitres_relationnel.py"
DER = "tests/test_chapitres_derive.py"
REF = "tests/test_chapitres_references.py"
VID = "tests/test_chapitres_video_refs.py"
ANI = "tests/test_chapitres_animatique.py"
IMP = "tests/test_chapitres_import_scenario.py"
EXP = "tests/test_chapitres_exports.py"
REE = "tests/test_chapitres_reecriture.py"
SOR = "tests/test_chapitres_sorties.py"

M = [
    # ── P1 : le lien plan ↔ entités et la fiche ──────────────────────────
    ("backend/app/api/routes.py",
     "    found = list(dict.fromkeys(sp[\"entity_id\"] for sp in MA.compute_spans(p, ents))) if ents else []",
     "    found = []",
     REL, ["paragraphe_lie_les_entites"]),
    ("backend/app/api/routes.py",
     "            ents_resp = await list_bible_entities(None)\n            drafts = _paragraph_shots(script, ents_resp[\"entities\"])",
     "            drafts = _paragraph_shots(script)",
     REL, ["paragraphe_lie_les_entites"]),
    ("backend/app/api/routes.py",
     "        mentions = sum(1 for sp in spans if sp.get(\"entity_id\") == entity_id)",
     "        mentions = len(spans)",
     REL, ["paragraphe_lie_les_entites"]),
    ("backend/app/api/routes.py",
     "        if mentions or sh or sc:",
     "        if True:",
     REL, ["paragraphe_lie_les_entites"]),
    # ── P2 : les versions ────────────────────────────────────────────────
    ("backend/app/services/text_versions.py",
     "    if rows and (rows[0].text or \"\") == ancien:\n        return None",
     "",
     VERS, ["l_instantane_garde_dix_versions"]),
    ("backend/app/services/text_versions.py",
     "    for vieux in rows[GARDE - 1:]:\n        await session.delete(vieux)",
     "",
     VERS, ["l_instantane_garde_dix_versions"]),
    ("backend/app/services/text_versions.py",
     "    if not ancien.strip():\n        return None",
     "",
     VERS, ["l_instantane_garde_dix_versions"]),
    ("backend/app/services/text_versions.py",
     "    await snapshot(session, v.kind, v.target_id, courant, \"restauration\",",
     "    await snapshot(session, v.kind, v.target_id, \"\", \"restauration\",",
     VERS, ["les_routes_versions"]),
    ("backend/app/services/text_versions.py",
     "                lignes.append({\"op\": \"~\", \"a\": ga, \"b\": gb})",
     "                lignes.append({\"op\": \"=\", \"a\": ga, \"b\": gb})",
     VERS, ["la_comparaison_est_ligne_a_ligne"]),
    ("backend/app/api/routes.py",
     "            if neuf != (ch.script_text or \"\"):\n                from app.services import text_versions as TV",
     "            if True:\n                from app.services import text_versions as TV",
     VERS, ["les_routes_versions"]),
    # ── P3 : la dérive et les références ─────────────────────────────────
    ("backend/app/services/identity_drift.py",
     "    return round((_sens(pa, pb) + _sens(pb, pa)) / 2, 3)",
     "    return round(_sens(pa, pb), 3)",
     DER, ["le_costume_qui_change_de_teinte"]),
    ("backend/app/services/identity_drift.py",
     "    return 0.0 if not union else round(1 - inter / union, 4)",
     "    return 0.0",
     DER, ["la_carrure_qui_grossit"]),
    ("backend/app/services/identity_drift.py",
     "    lf = lab(_fond(small))",
     "    lf = lab((0, 0, 0))",
     DER, ["la_carrure_qui_grossit", "deux_images_identiques"]),
    ("backend/app/services/identity_drift.py",
     "    return sorted(out, reverse=True)",
     "    return out",
     DER, ["la_palette_est_ordonnee"]),
    ("backend/app/api/routes.py",
     "                                  \"file\": out[\"images\"][0]})",
     "                                  })",
     REF, ["la_recette_v3_garde_les_fichiers"]),
    ("backend/app/api/routes.py",
     "    if rec and rec.get(\"v\") == 3:",
     "    if rec and rec.get(\"v\") == 9:",
     REF, ["la_recette_v3_garde_les_fichiers"]),
    ("backend/app/services/image_providers.py",
     "    urls = [u for u in (image_urls or []) if u][:REF_MAX]",
     "    urls = [u for u in (image_urls or []) if u][:1]",
     REF, ["banana_prend_jusqu_a_neuf"]),
    ("backend/app/services/image_providers.py",
     "    if isinstance(image_urls, str):\n        image_urls = [image_urls]",
     "",
     REF, ["banana_prend_jusqu_a_neuf"]),
    ("backend/app/services/fal_service.py",
     "    if len(urls) > hi:",
     "    if False:",
     VID, ["veo_prend_de_une_a_neuf"]),
    ("backend/app/services/fal_service.py",
     "        args[\"elements\"] = [{\"image_url\": u} for u in urls]",
     "        args[VEO_REF_FIELD] = urls",
     VID, ["kling_nomme_ses_elements"]),
    ("backend/app/services/fal_service.py",
     "    if len(urls) < lo:",
     "    if False:",
     VID, ["veo_prend_de_une_a_neuf"]),
    # ── P4 : l'animatique ────────────────────────────────────────────────
    ("backend/app/services/animatique_service.py",
     "        if dv >= mini:\n            dur, src = round(dv, 3), \"voix\"",
     "        if False:\n            dur, src = round(dv, 3), \"voix\"",
     ANI, ["la_voix_fixe_la_duree"]),
    ("backend/app/services/animatique_service.py",
     "        img = s.get(\"image\") or s.get(\"sketch_image\") or None",
     "        img = s.get(\"sketch_image\") or s.get(\"image\") or None",
     ANI, ["la_voix_fixe_la_duree"]),
    ("backend/app/services/animatique_service.py",
     "    for e in sorted(entrees, key=lambda x: x[\"idx\"]):",
     "    for e in entrees:",
     ANI, ["la_route_rend_un_clip_par_plan"]),
    ("backend/app/services/animatique_service.py",
     "    im = Image.new(\"RGB\", (w, h), FOND_CARTON)",
     "    im = Image.new(\"RGB\", (h, w), FOND_CARTON)",
     ANI, ["le_carton_de_secours"]),
    # ── P5 : l'import ────────────────────────────────────────────────────
    ("backend/app/services/screenplay_import.py",
     "    texte = _NOTE.sub(\"\", _BONEYARD.sub(\"\", (texte or \"\").replace(\"\\r\\n\", \"\\n\")))",
     "    texte = (texte or \"\").replace(\"\\r\\n\", \"\\n\")",
     IMP, ["garde_le_dialogue_et_jette_notes"]),
    ("backend/app/services/screenplay_import.py",
     "        if ligne.startswith(\".\") and not ligne.startswith(\"..\"):\n            entete = ligne[1:].strip()",
     "        if False:\n            entete = ligne[1:].strip()",
     IMP, ["decoupe_en_scenes_et_lit_les_sluglines"]),
    ("backend/app/services/screenplay_import.py",
     "        if ligne.startswith(\"!\"):\n            entete = None",
     "        if False:\n            entete = None",
     IMP, ["decoupe_en_scenes_et_lit_les_sluglines"]),
    ("backend/app/services/screenplay_import.py",
     "        if len(parts) > 1 and parts[-1].strip().upper() in _TOD:",
     "        if len(parts) > 1:",
     IMP, ["decoupe_en_scenes_et_lit_les_sluglines"]),
    ("backend/app/services/screenplay_import.py",
     "        rendu = _FDX_LIGNE.get(typ, lambda t: t)(txt)",
     "        rendu = _FDX_LIGNE.get(typ, lambda t: \"\")(txt)",
     IMP, ["fdx_passe_par_la_meme_grammaire"]),
    # ── P6 : les exports ─────────────────────────────────────────────────
    ("backend/app/services/pdf_mini.py",
     "        total += table[o - 32] if 32 <= o <= 126 else table[ord(\"n\") - 32]",
     "        total += 500",
     EXP, ["les_largeurs_de_fonte_et_la_coupe"]),
    ("backend/app/services/pdf_mini.py",
     "        c = _base(ch)",
     "        c = ch",
     EXP, ["les_largeurs_de_fonte_et_la_coupe"]),
    ("backend/app/services/pdf_mini.py",
     "    sortie += b\"xref\\n0 %d\\n0000000000 65535 f \\n\" % (len(objets) + 1)",
     "    sortie += b\"xref\\n0 %d\\n0000000000 65535 f \\n\" % (len(objets) + 2)",
     EXP, ["le_pdf_ecrit_est_relisible"]),
    ("backend/app/services/pdf_mini.py",
     "    lim = boite * MARGE_COUPE",
     "    lim = boite * 1.6",
     EXP, ["les_largeurs_de_fonte_et_la_coupe"]),
    ("backend/app/services/text_export.py",
     "        if k == \"texte\" and prec in (\"cue\", \"paren\", \"dialogue\"):\n            k = \"dialogue\"",
     "",
     EXP, ["docx_et_pdf_du_chapitre"]),
    # ── D1, D2, D3 ───────────────────────────────────────────────────────
    ("backend/app/services/reecriture.py",
     "    return (f\"BIBLE DU PROJET :\\n{tete}\\n\"",
     "    return (f\"\\n{''}\\n\"",
     REE, ["la_passe_propose_puis_applique"]),
    ("backend/app/api/routes.py",
     "        if body.get(\"appliquer\"):",
     "        if True:",
     REE, ["la_passe_propose_puis_applique"]),
    ("backend/app/services/sorties.py",
     "            if total < mini:\n                continue",
     "            pass",
     SOR, ["le_reel_choisit_la_fenetre"]),
    ("backend/app/services/sorties.py",
     "            cle = (energie, -abs(total - cible))",
     "            cle = (0, -abs(total - cible))",
     SOR, ["le_reel_choisit_la_fenetre"]),
    ("backend/app/services/sorties.py",
     "            \"src\": {\"file_path\": str(f)}, \"srcIn\": 0,\n            \"shot_id\": e.get(\"shot_id\"),",
     "            \"src\": {\"file_path\": str(f)}, \"srcIn\": 0,",
     SOR, ["les_clips_de_montage", "l_animatique_se_pose_au_montage"]),
    ("backend/app/api/routes.py",
     "        if c.get(\"shot_id\") == shot_id:",
     "        if True:",
     SOR, ["l_animatique_se_pose_au_montage"]),
    ("backend/app/api/routes.py",
     "            c[\"src\"] = src\n            c[\"label\"] = (c.get(\"label\") or \"\") + \" · rendu\"",
     "            c[\"src\"] = src\n            c[\"start\"] = 0.0\n            c[\"label\"] = (c.get(\"label\") or \"\") + \" · rendu\"",
     SOR, ["l_animatique_se_pose_au_montage"]),
]


def rouges(banc: str, k: str):
    """Les tests rouges du banc ciblé — et si RIEN n'a tourné, on le dit.

    pytest sort 0 (tout vert) ou 1 (des rouges) quand il a tourné ; 2 à 5
    quand la COLLECTE a cassé (une erreur de syntaxe dans routes.py, un
    import qui lève) ou qu'aucun test ne correspond. Lue comme « aucun
    FAILED », une collecte cassée passerait pour une mutation VERTE alors
    que rien n'a été mesuré."""
    r = subprocess.run([PY, "-m", "pytest", banc, "-q", "--no-header",
                        "-p", "no:warnings", "-k", k],
                       capture_output=True, cwd=R / "backend", timeout=900)
    txt = r.stdout.decode("utf-8", "replace")
    erreur = (r.returncode not in (0, 1)
              or bool(re.search(r"^ERROR ", txt, re.M)))
    return set(re.findall(r"^FAILED [^:]+::(\w+)", txt, re.M)), txt, erreur


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, banc, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        # les fichiers de l'arbre sont en CRLF (autocrlf) : on apparie en LF
        # et l'on réécrit avec la fin de ligne du fichier ; la remise se fait
        # à l'octet près depuis `src`.
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        assert txt.count(old) == 1, (i, rel, txt.count(old), old[:60])
        txt = txt.replace(old, new)
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur = rouges(banc, " or ".join(attendus))
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        manquants = [a for a in attendus if not any(a in n for n in rg)]
        if erreur:
            verdict = "ERREUR(collecte)"
            print(sortie[-1200:], file=sys.stderr)
        elif not manquants:
            verdict = "ROUGE"
        else:
            verdict = "VERTE" if not rg else "ROUGE(autres)"
        bilan.append((i, rel, banc, verdict, sorted(rg), manquants))
        print(f"[{i:2d}] {verdict:16s} {pathlib.Path(rel).name:24s} "
              f"{pathlib.Path(banc).stem:30s} {old.strip()[:44]!r} "
              f"-> {sorted(rg)}  sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:4] for b in bilan], ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
```

- [ ] **Étape 2 : lancer la campagne** — `cd backend && $PY tests/mutations_chapitres.py`. Attendu : 42 lignes, chacune `ROUGE`, et le JSON final. Durée indicative : chaque mutation relance un banc, compter ~4 à 10 min pour la campagne complète.

- [ ] **Étape 3 : traiter CHAQUE verte** — une `VERTE` = une assertion qui manque. Pour chacune : ajouter l'assertion au banc nommé (jamais changer la mutation pour la faire rougir), relancer `$PY tests/mutations_chapitres.py <i>`, vérifier `ROUGE`. Une `ROUGE(autres)` = le test attendu n'a pas rougi mais un autre oui : soit le nom attendu est faux (corriger la liste), soit le banc mesure autre chose que ce qu'on croit (le dire).

- [ ] **Étape 4 : traiter chaque `ERREUR(collecte)`** — c'est une mutation qui casse l'import, pas le comportement : elle ne mesure rien. La remplacer par une mutation plus fine (muter une valeur, pas une structure).

- [ ] **Étape 5 : la relecture complète** — un processus par fichier, depuis `backend/` :

```bash
for t in relationnel versions derive references video_refs animatique import_scenario exports reecriture sorties; do
  $PY tests/test_chapitres_$t.py || echo "ECHEC: $t"
done
```

Attendu : dix lignes `… TEST: PASS`, aucun `ECHEC`.

- [ ] **Étape 6 : commit**

```bash
git add backend/tests/mutations_chapitres.py backend/tests/test_chapitres_*.py && git commit -F - <<'EOF'
chapitres : la campagne de mutations, et les assertions qu'elle a trouvees

42 mutations sur les dix bancs de la categorie, patron de
mutations_plaque_slicer (lot B de l'Etabli) avec une difference : le BANC
est par mutation, Chapitres en ayant dix. Chaque mutation est verifiee
appliquee une fois, le fichier est remis a l'octet pres (sha256 asserte),
et le code de sortie de pytest est lu pour distinguer une collecte cassee
d'une mutation verte.

Vertes trouvees et fermees : lister ici chaque index de mutation verte et
l'assertion ajoutee pour la fermer ; ecrire AUCUNE si la campagne est
integralement rouge du premier coup.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Relecture finale (faite le 03/09/2026)

**Couverture du périmètre** — P1 : T1 (route apparitions, découpe paragraphe entity-aware) + T2 (surface). P2 : T3 (table + service) + T4 (routes + quatre points d'écrasement) + T5 (surface). P3 : T6 (banc de dérive) + T7 (recette v3, vues) + T8 (multi-références image) + T9 (multi-références vidéo). P4 : T10 (service + routes) + T11 (surface). P5 : T12 (parseurs) + T13 (route + bouton). P6 : T14 (pdf_mini) + T15 (docx/PDF) + T16 (PDF du storyboard + liens). D1 : T17. D2 : T18 + T19. D3 : T20. E1–E3 : section « Écarté ». Campagne : T21. Aucun item de R3 sans tâche.

**Dépendances entre tâches** — T2 dépend de T1 ; T4 et T5 de T3 ; T8 de T7 ; T11 de T10 ; T13 de T12 ; T15 et T16 de T14 ; T17 de T4 (l'instantané `reecriture`) ; T19 de T18 **et** de T10 (le dossier d'animatique) ; T20 de T18 (`clips_montage`) — et la route `film`/`reel` de T19 ne fonctionne qu'une fois T20 écrite, ce qui est dit dans l'étape 5 de T19. T21 dépend de tout.

**Cohérence des noms** — `_entity_ref_views` (T7) est appelée par T8 ; `IP.REF_MAX` (T8) et `refs: (1, 9)` (T9) portent le même plafond de 9 ; `TV.snapshot` (T3) a la même signature dans T4, T13, T17 ; `AN.plan` / `AN.dossier` / `AN.rendre` (T10) sont appelées avec les mêmes noms dans T11, T19, T20 ; `PM.Page` / `PM.couper` / `PM.largeur` / `PM.ecrire` (T14) dans T15 et T16 ; `SO.clips_montage` (T18) dans T19 et T20 ; `shot_id` est porté par le clip de T18 et lu par T20.

**Ce qui reste ouvert, et qu'il faudra mesurer en exécutant** — (a) l'endpoint et le nom de champ exacts de Veo 3.1 reference-to-video (T9, étape 1 : la doc tranche, pas ce plan) ; (b) l'existence d'une description publique du FDX (T12, étape 1 — le parseur est écrit pour s'en passer) ; (c) les chasses Helvetica de `pdf_mini` (métriques Adobe de mémoire ; conséquence bornée à une coupe un peu lâche, d'où les 2 % de garde) ; (d) les retraits du scénario papier (de mémoire ; ils ne conditionnent que l'allure d'un export) ; (e) les seuils du banc de dérive (`SEUIL_COULEUR = 8`, `SEUIL_SILHOUETTE = 0,12`) sont des points de départ : la première campagne sur de vraies planches dira s'ils crient trop ou pas assez, et le dire est le travail de qui exécute.
