# Montage — lot E-A (montage neuf, ouvrir dans le Montage, rendre / publier séparés) — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Un sous-agent frais par tâche, deux revues (conformité puis qualité), corrections en boucle, commit `--only` par tâche, push après chaque tâche. **Chaque agent conteste le plan avec des mesures.** Consigne de l'utilisateur (22/09/2026) : **ne pas complexifier le code, rester efficient et robuste** — chaque tâche vise le MINIMUM de lignes qui tient, et dit ce qu'elle laisse en écart.

**Goal :** (E-1) créer un montage NEUF et vide et l'ouvrir sans que la Bibliothèque le remplisse ; (E-3) « Ouvrir dans le Montage » depuis un épisode terminé de Chapitres et un rendu terminé du Studio, posé sur V1 à la tête AVEC son jumeau A1 (et corriger la porte « Envoyer vers… » de la Bibliothèque, qui vise `v2` en dur) ; (E-4) séparer « Rendre » de « Publier » : plus de brouillon Scheduler automatique, un bandeau de fin de rendu avec un vrai bouton « Envoyer vers le Scheduler » (canaux, heure, légende), le brouillon créé par le backend. Décisions E-1, E-3, E-4 de `docs/superpowers/specs/2026-09-22-montage-vs-resolve-app-design.md`, validées le 22/09/2026.

**Architecture :** RIEN de l'existant n'est réécrit. Backend : un drapeau opt-in `vide` (trois `if` dans `montage_service.py`) et une route `POST /api/montage/publish` qui appelle `create_scheduled_post` (import LAZY, comme `routes.py` fait dans l'autre sens). Client : fonctions pures dans `frontend/patches/montage.js` (exportées sur `window.DzTracks`, jouées sous node), le composant `DzmProjects` étendu dans la couche (pas d'ancre bundle), un composant `DzmFinBandeau`, et cinq sections `EA1…EA5` en QUEUE de `PATCHES` de `scripts/patch_bundle_montage.py` (ancres comptées 1/1 dans `.bak_montage` et 0 dans le patcher le 22/09 — voir la table), plus deux replis (`R_M5` payload, `R_M7` restauration) pour porter `vide`. `patch_bundle_libsend.py` reste INTOUCHABLE : sa greffe est REMPLACÉE en aval par le patcher montage (ancre = sa ligne entière, 1/1).

**Tech Stack :** Python 3.13 embarqué, FastAPI + TestClient, node 24 (bancs du cœur JS par FICHIER shim), bundle en OCTETS, chaîne `python scripts/repatch_all.py --from montage` puis `--list` (`montage OK`, `dzcout OK`), sonde `("montage","DzTracks",98)` de `scripts/patch_bundle_dzcout.py:279` remesurée à chaque tâche client.

---

## Conventions valables pour tout le plan

```powershell
$PY = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"
Set-Location backend
& $PY tests\test_montage_bundle.py        # 1636/0 au départ
& $PY tests\test_montage_edition.py       # 158/0
& $PY tests\test_montage_projets.py       # 159/0
& $PY tests\test_montage_l2.py            # 78/0
& $PY tests\test_montage_ea.py            # NEUF (tâche 1)
& $PY ..\scripts\patch_bundle_montage.py --check --force-unchained   # 96 ancres OK au départ
& $PY ..\scripts\repatch_all.py --from montage ; & $PY ..\scripts\repatch_all.py --list
node --check ..\frontend\dist\assets\index-BEOJX8L5.js
```

- Un banc = un processus, jamais `pytest` ; `check(label, cond, detail)`, fin `=== N passed, M failed ===`, exit 1 si rouge, labels snake_case sans accent. Règle des assertions négatives (une négation prouve d'abord que la mesure a eu lieu). Faute n°6 (aucune lecture nue avant un `check` — `A()`, `J()`, `find()` avec repli).
- Ancres bundle : comptées sur `.bak_montage` (`--check --force-unchained`) ET dans le patcher ; une ancre consommée se REPLIE. Le bundle se lit et s'écrit en OCTETS. Sections `EA*` en queue de `PATCHES`. Écrire `insere()` sans namespace dans la prose (la sonde dzcout compte les commentaires).
- Commits : `git commit --only <chemins>`, première ligne sans accent, trailer EXACT `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` ; push de `chantier/montage-l3` après chaque tâche. Preuve à l'écran par le contrôleur (backend du worktree sur 8799 via `.claude/launch.json`, `DEEPOTUS_DATA_DIR` = scratchpad, deux mp4 `testsrc2` par `POST /api/videos/upload`).

## Faits mesurés le 22/09/2026 qui bornent ce lot

- `POST /projects` (`montage_service.py:1829-1873`) : `cur = _save_record(tl)` si `timeline.clips` est une liste, sinon `_load_saved()` ; **`if cur is None or not cur.get("clips"): raise HTTPException(400, "Aucune timeline à enregistrer.")`** (`:1858`, 1/1) ; `rec = dict(cur, id=pid, project_id=pid, name=…)` ; `_write_json_atomic` + `_write_saved(rec)`. Le 400 est épinglé DEUX fois (`test_montage_projets.py:295-301`, `:722-723`) par des corps `{"name": …}` SANS `vide` → un `vide` **opt-in** (`body.get("vide") is True`) ne rougit rien.
- `_save_record` (`:877-1010`) ne garde que `name, ratio, duration, mix, duration_master, ducking, clips, saved_at` + conditionnelles `ducking_cfg, subs_style, tracks, range, markers` — **toute autre clé est jetée** ; `_load_saved` (`:834-849`) rend le dict tel quel ; `_project_meta` (`:1100-1110`) ne rend que `{id, name, updated_at, clips, ratio, duration}`.
- `GET /project` (`:1150-1280`) : sauvegarde présente → `kept` élagué → **`        if any(c.get("tr") == "v1" for c in kept):`** (`:1240`, 1/1) → `out = {"ok": True, "has_assets": True, "saved": True, …}` ; sinon `logger.warning("montage: sauvegarde sans clip V1 exploitable — timeline reconstruite depuis la Bibliothèque")` et les 4 derniers rendus sont posés. Aucun banc n'épingle cette reconstruction (`test_montage_sources.py:888` épingle `has_assets` FAUX au seuil de 60 candidats, autre chose).
- `POST /projects/{pid}/open` (`:1929-1968`) : `ouvrable` = un clip V1 sans `src` ou à source existante ; **`    if not ouvrable:`** (`:1949`, 1/1) → 409 ; puis `_write_saved(dict(d, id=p, project_id=p))` (le projet ENTIER). `inouvrable_409` (`test_montage_projets.py:655-698`) porte un clip V1 à source disparue, pas un projet vide.
- Pistes par défaut : serveur `_LEGACY_TRACKS` (5 : v2 v1 a1 a2 a3, `:232-237`) pour le rendu ; client `DZM_DEFAULT_TRACKS` (7 : t1 v2 v1 a1 a2 a3 s1, `montage.js:166`), exporté `DzTracks.DEFAULTS`. Un projet neuf écrit `tracks` explicitement (une seule vérité).
- `svmApplyProject(d)` (`.bak_montage:1924-1961`) : **sort sur `if(!d||!d.ok||!d.has_assets)return !1;`** → un montage vide DOIT rendre `has_assets:true` ; `setClips(cs)`, `setSelId("")`, `setPh(0)`, `setDirty(!1)`, historique remis à zéro ; `np={demo:!1,name,version,ratio,dur:Math.max(1,Number(d.duration)||maxEnd),mixDb}` (aucun `tracks` ici : `svmTracksOf` retombe sur `DEFAULTS`) → le serveur pose `duration: 30` sur un projet vide sinon la timeline fait 1 s. `A_M7` (restauration, `patch_bundle_montage.py:399`) et `R_M5` (payload, `:305-324`) sont les deux replis où `vide` circule.
- `DzmProjects` (`montage.js:1399-1727`) : props `projectId, name, nu, note, openReq, payload(), onBefore(), onFail(), onOpen(d), onNamed(pid,nm)` ; helpers `url(p)`, `send(url, method, body)`, `req(url, init)` ; création `send("/api/montage/projects","POST",{name:(nv||"").trim(),timeline:tl})` ; ouverture `send(url(p.id)+"/open","POST").then(()=>req("/api/montage/project")).then(d=>{ if(props.onOpen&&props.onOpen(d)){ if(props.onNamed)props.onNamed(p.id,p.name); setOp(!1)…` ; rangée de création `      r.jsxs("div",{className:"dzm-projsave",children:[` (`:1697`, 1/1). Monté par `R_M14` (`patch_bundle_montage.py:642-664`, posé via `R_M8`) avec `onOpen:function(d){return svmApplyProject(d)}` et `payload:function(){return svmSavePayload()}`.
- Greffe libsend `S4-montage-consomme` (`patch_bundle_libsend.py:248-259`), **ligne entière dans `.bak_montage:3744`, 1/1, patcher 0** :
  `  x.useEffect(function(){var p=null;try{p=window.__dzMontageAdd;delete window.__dzMontageAdd}catch(_e){}if(!p)return;setTimeout(function(){try{if(p.image)addAsset({image:p.image},p.image,"image",0,"v2");else if(p.job_id)addAsset({job_id:p.job_id},p.title||p.job_id,"video",p.dur||0,"v2")}catch(_e2){}},450)},[]);function defaultLen(kind,srcDur){`
  Depuis L1, `addAsset` du bundle APPLIQUÉ (M16a `:1255-1271`) résout `tr2 = (trId && dzTs.some(id===trId)) ? trId : DzTracks.pickTrack(dzTs,dzWant)` et (M22a/M22b) pose le jumeau par `twinPlan` + `insere` **si `wantsTwin(kind,ts,tr2)`** = `kind==="video" && dzmTrackPlein(ts,id)` (`montage.js:2588`) — **plein cadre seulement : sur `v2` la vidéo arrive MUETTE**. `dzmPickTrack(ts,"video")` (`:416-424`) rend la PREMIÈRE piste vidéo dans l'ordre d'affichage = **`v2`** avec les pistes par défaut. Passer `"v1"` en `trId` suffit : si `v1` existe elle est prise, sinon `pickTrack` (repli déjà écrit).
- Chapitres (composant non minifié, bundle l. 336) — ancre **CH-1** `r.jsx(K,{variant:"primary",size:"sm",icon:"calendar",onClick:sendEpisodeToScheduler,children:"Send to Scheduler"})` (bak 1, patcher 0) ; état local : `epJob` (job_id), `title`, `scenes`. Le job `episode` (`pipeline.py:763-843`) ne stocke **aucune** durée de scène (`cost_meta` = `{images, chars}`) → « un clip par scène » N'A PAS de bornes justes : **écart daté, un seul plan**. Studio — ancre **ST-1** `r.jsx("div",{style:{marginTop:10,display:"flex",gap:8},children:r.jsx("a",{href:D.jobVideoUrl(n.id),download:!0,` (bak 1, patcher 0), `n.id` = job_id, `n.title` à mesurer (sinon `"Rendu Studio"`). `__dzSendNav` est dans le scope du bloc libsend, PAS sur `window` : le mécanisme portable est `window.dispatchEvent(new CustomEvent("deepotus:navigate",{detail:{view:"montage"}}))` (Chapitres l'emploie déjà). Le Montage consomme `window.__dzMontageAdd={job_id,title?,dur?}` au montage de l'écran (effet `[]`, `setTimeout 450`).
- `launchRender` (`.bak_montage:3939-3970`) : le poll `setInterval` ; branche `job.kind==="preview"` puis **`else{`** (3 dans `.bak`, 1 dans le patcher — À PROSCRIRE) ; le bloc à remplacer commence par **`            var run=new Date();run.setDate(run.getDate()+1);run.setHours(9,0,0,0);`** (1/1, 0) et finit par `                fireNote("Rendu terminé (Bibliothèque) — création du brouillon Scheduler impossible.")})}}` ; il fait `POST /api/schedule` (`channels:["x","telegram"]`, +1 j 09:00), `deepotus:select-post` à 400 ms, `props.go("scheduler")` à 900 ms. Popover (`.bak:3999-4021`) : `      r.jsx("div",{className:"svm-poptitle",children:isR?"Rendre & publier":"Preview 480p"}),` (1/1, 0), `      isR?r.jsxs("div",{className:"svm-popline",children:[r.jsx("span",{children:"publication · brouillon Scheduler"}),r.jsx("span",{className:"svm-cost",children:"gratuit"})]}):null,` (1/1, 0), `          "Rendu local 1080 (aucun crédit consommé), puis brouillon dans le Scheduler — rien n'est publié sans ta validation.":` (1/1, 0), barre de titre `        r.jsx("button",{className:"svm-goldbtn",onClick:function(){setPop(pop==="render"?"":"render")},children:"Rendre & publier →"}),` (`.bak:4979`, 1/1, 0).
- `create_scheduled_post(body: dict)` (`routes.py:3974-4006`) : pas de Pydantic, `channels` NON validé (`",".join(body.get("channels") or ["x"])`), `run_at` = `fromisoformat` sans « Z », retour `_post_to_dict(p)` ; liste blanche du dépôt `plan_schema._CHANNELS = ("x","telegram","youtube","instagram")` (`:38`) = les 4 canaux du client (`_t={x,telegram,youtube,instagram}`) ; `ScheduledPost` (`storage.py:82-121`) n'a ni `meta` ni `project_id` — **`brief` (Text JSON, déjà écrit par la route quand `body["brief"]` est un dict)** porte `{"project_id"}` sans migration. `montage_service.py` n'importe pas `routes` ; `routes.py` importe `montage_service` en LAZY dans des corps → **import lazy symétrique** dans le handler. Écouteur `deepotus:select-post` : `{detail:{id}}`. **Quatre** conventions de brouillon coexistent (libsend +2 h `["x"]` ; Chapitres +1 j `["youtube","instagram"]` ; Montage +1 j `["x","telegram"]` ; Studio +1 j `["x","telegram"]`) — E-4 n'unifie que celle du Montage (les autres écrans sont hors lot, dit en écart).

## Fichiers

| Fichier | Rôle |
|---|---|
| `backend/app/services/montage_service.py` | `vide` opt-in (`POST /projects`, `_save_record`, `_project_meta`, `GET /project`, `open`) ; `POST /publish` |
| `backend/tests/test_montage_ea.py` | NEUF — `[1]` E-1 backend, `[2]` E-4 backend |
| `frontend/patches/montage.js` | pures `dzmProjetNeuf`, `dzmInstantaneNom`, `dzmPublishDefaults`, `dzmChannelsNorm` ; `DzmProjects` (+ nouveau, + instantané) ; `DzmFinBandeau` ; exports |
| `scripts/patch_bundle_montage.py` | replis `R_M5`/`R_M7` (`vide`), sections `EA1` (greffe libsend → V1), `EA2` (Chapitres), `EA3` (Studio), `EA4` (poll), `EA5` (popover + titre + bandeau), état `dzFin` en repli `R_M16REF` |
| `frontend/dist/shared/montage.css` | `.dzm-fin*`, `.dzm-projnew` |
| `backend/tests/test_montage_edition.py` | `[12]` E-1 pures, `[13]` E-4 pures |
| `backend/tests/test_montage_bundle.py` | pins EA1…EA5 + replis, comptes de référence |
| `scripts/patch_bundle_dzcout.py` | sonde remesurée |
| `backend/tests/mutations_montage_ea.py` | NEUF — clôture |
| `docs/superpowers/specs/2026-09-22-montage-vs-resolve-app-design.md` | « exécuté » + écarts E-1/E-3/E-4 |

---

## Tâche 1 — E-1 backend : le drapeau `vide` (créer, garder, ouvrir, ne pas remplir)

**Files :** modifier `backend/app/services/montage_service.py`, créer `backend/tests/test_montage_ea.py`.

- [ ] **Étape 1 : banc rouge.** Créer `backend/tests/test_montage_ea.py` en copiant l'en-tête de `test_montage_projets.py` (`TMP`, variables d'environnement AVANT `import app`, `check`, `J`, `names()`/`PDIR` si utiles) et son ouverture `with TestClient(app) as c:`. Section `[1]` :

```python
print("\n[1] E-1 un montage NEUF et vide : cree, garde, ouvert, jamais rempli par la Bibliotheque")
r = c.post("/api/montage/projects", json={"name": "sans rien"}); d = J(r)
check("e1_sans_vide_le_400_historique_est_garde", r.status_code == 400, f"{r.status_code} {r.text[:100]}")
r = c.post("/api/montage/projects", json={"name": "neuf", "vide": True,
           "tracks": [{"id": "t1", "kind": "title"}, {"id": "v2", "kind": "video"}, {"id": "v1", "kind": "video"},
                      {"id": "a1", "kind": "audio", "bus": "dialogue"}, {"id": "s1", "kind": "subs"}]}); d = J(r)
check("e1_vide_true_cree_un_projet_200", r.status_code == 200 and d.get("ok") is True and str(d.get("id", "")).startswith("m_"), (r.status_code, d))
pid = str(d.get("id") or "")
check("e1_la_meta_dit_vide_et_zero_clip", d.get("vide") is True and d.get("clips") == 0, d)
r = c.get("/api/montage/projects"); L = J(r); lst = L if isinstance(L, list) else L.get("_liste", L.get("projects", []))
check("e1_la_liste_porte_le_drapeau", any(p.get("id") == pid and p.get("vide") is True for p in lst if isinstance(p, dict)), str(lst)[:200])
r = c.get("/api/montage/project"); d = J(r)
check("e1_get_project_rend_le_vide_sans_le_remplir",
      r.status_code == 200 and d.get("ok") is True and d.get("has_assets") is True and d.get("saved") is True
      and d.get("vide") is True and d.get("clips") == [] and d.get("project_id") == pid, str(d)[:300])
check("e1_les_pistes_et_la_duree_sont_celles_posees",
      [t.get("id") for t in d.get("tracks", [])] == ["t1", "v2", "v1", "a1", "s1"] and float(d.get("duration") or 0) >= 10, (d.get("tracks"), d.get("duration")))
check("e1_vide_sans_tracks_prend_les_pistes_par_defaut_du_client",
      (lambda dd: dd.get("ok") is True and [t.get("id") for t in dd.get("tracks", [])] == ["t1", "v2", "v1", "a1", "a2", "a3", "s1"])(J(c.post("/api/montage/projects", json={"name": "neuf2", "vide": True}))
      if c.post("/api/montage/projects", json={"name": "neuf2b", "vide": True}).status_code == 200 else {}) or True)
# (la ligne ci-dessus est un GARDE-FOU de forme : la réécrire proprement — deux appels, un check — sans lecture nue)
r = c.post("/api/montage/projects/%s/open" % pid); check("e1_ouvrir_un_projet_vide_200_pas_409", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
r = c.post("/api/montage/save", json={"name": "neuf", "vide": True, "clips": [{"id": "a", "tr": "a1", "start": 0, "end": 3, "src": {"audio": "x.mp3"}}]})
check("e1_autosave_garde_vide_quand_le_client_le_renvoie", r.status_code == 200 and J(c.get("/api/montage/project")).get("vide") is True)
r = c.post("/api/montage/save", json={"name": "neuf", "clips": [{"id": "a", "tr": "a1", "start": 0, "end": 3, "src": {"audio": "x.mp3"}}]})
d = J(c.get("/api/montage/project"))
check("e1_sans_vide_et_sans_v1_l_ancien_chemin_reconstruit_depuis_la_bibliotheque",
      r.status_code == 200 and "vide" not in d and d.get("saved") in (False, None), str(d)[:200])
```

Réécrire la ligne « garde-fou » en deux appels propres : `r2 = c.post(... {"name":"neuf2","vide":True})`, `d2 = J(r2)`, puis `check("e1_vide_sans_tracks…", r2.status_code == 200 and [t.get("id") for t in d2.get("tracks", [])] == [...7 ids...])` — **si `POST /projects` ne rend pas `tracks` dans sa méta, lire `GET /project` après `open`**.

- [ ] **Étape 2 : rouge** (400 sur `vide`, `vide` absent des réponses, 409 sur open).

- [ ] **Étape 3 : implémenter** (quatre points, chacun une ancre 1/1) :

```python
# E-1 (22/09/2026) — UN MONTAGE NEUF EST VIDE, ET LE RESTE. Drapeau opt-in
# `vide` : posé par POST /projects {vide:true}, gardé par _save_record quand
# le client le renvoie, lu par GET /project pour NE PAS reconstruire depuis
# la Bibliothèque, et par open pour ne pas rendre 409. Sans lui, tout est
# octet pour octet l'historique (les deux 400 épinglés restent).
```

1. `_save_record` : à côté de `tracks` (conditionnelle), `if body.get("vide") is True: data["vide"] = True`.
2. `montage_project_create` : AVANT `if cur is None or not cur.get("clips"):` —
```python
    if body.get("vide") is True:
        tr = body.get("tracks")
        cur = _save_record({"name": body.get("name"), "clips": [], "duration": 30, "vide": True,
                            "tracks": tr if isinstance(tr, list) and tr else _CLIENT_DEFAULT_TRACKS})
    elif isinstance(tl, dict) …   # la branche existante devient elif
```
avec `_CLIENT_DEFAULT_TRACKS` = la copie des 7 pistes de `DZM_DEFAULT_TRACKS` (id/kind/bus/loop seulement — `_tracks_meta` ne lit que cela) déclarée sous `_LEGACY_TRACKS` avec le commentaire « miroir de montage.js:166, tenu par un banc croisé (tâche 6) ». Et la garde 400 devient `if cur is None or (not cur.get("clips") and cur.get("vide") is not True):`.
3. `_project_meta` : `"vide": True` si `rec.get("vide") is True` (clé absente sinon — la liste historique ne change pas).
4. `GET /project` : `        if saved.get("vide") is True or any(c.get("tr") == "v1" for c in kept):` et, dans `out`, `if saved.get("vide") is True: out["vide"] = True` ; vérifier que `out` porte déjà `tracks` et `duration` (sinon les ajouter depuis `saved`).
5. `open` : `    if not ouvrable and d.get("vide") is not True:`.

- [ ] **Étape 4 : vert ; `test_montage_projets.py` 159/0 inchangé ; commit** `--only montage_service.py test_montage_ea.py` : `montage : E-1 - drapeau vide, un montage neuf n est jamais rempli par la Bibliotheque`.

---

## Tâche 2 — E-1 client : « nouveau » dans le panneau Projets, instantané avant « ouvrir », `vide` porté

**Files :** modifier `frontend/patches/montage.js`, `scripts/patch_bundle_montage.py` (replis R_M5 + R_M7), `frontend/dist/shared/montage.css`, `backend/tests/test_montage_edition.py` (`[12]`), `backend/tests/test_montage_bundle.py`, `scripts/patch_bundle_dzcout.py`.

- [ ] **Étape 1 : banc rouge** `[12]` (PROBE) :

```javascript
/* [12] E-1 : montage neuf */
out.pn_neuf=T.projetNeuf(" Pub été ");
out.pn_neuf_vide=T.projetNeuf("");
out.pn_snap=[T.instantaneNom("",new Date(2026,8,22,14,5)),T.instantaneNom("montage",new Date(2026,8,22,14,5)),T.instantaneNom("Pub",new Date(2026,8,22,14,5))];
out.pn_defaults_pur=JSON.stringify(T.DEFAULTS.map(function(t){return t.id}))==='["t1","v2","v1","a1","a2","a3","s1"]';
```
Python :
```python
print("\n[12] E-1 montage neuf (client)")
check("pn_neuf_porte_nom_vide_et_les_pistes_par_defaut",
      "pn_neuf" in D and D["pn_neuf"].get("name") == "Pub été" and D["pn_neuf"].get("vide") is True
      and [t["id"] for t in D["pn_neuf"].get("tracks", [])] == ["t1", "v2", "v1", "a1", "a2", "a3", "s1"], D.get("pn_neuf"))
check("pn_neuf_sans_nom_s_appelle_montage_neuf", (D.get("pn_neuf_vide") or {}).get("name") == "montage neuf")
check("pn_instantane_nomme_le_non_nomme_et_garde_un_vrai_nom",
      D.get("pn_snap") == ["(non nommé) 22/09 14:05", "(non nommé) 22/09 14:05", "Pub"], D.get("pn_snap"))
check("pn_defaults_pur", D.get("pn_defaults_pur") is True)
```

- [ ] **Étape 2 : implémenter** (montage.js, avant `var DzTracks=`) :

```javascript
/* ── E-1 (22/09/2026) : UN MONTAGE NEUF. Le corps de POST /projects pour un
   projet VIDE : nom nettoyé (« montage neuf » à défaut), `vide:true`, et les
   pistes par défaut du CLIENT écrites explicitement (une seule vérité pour
   l'écran et le rendu). `dzmInstantaneNom` nomme la copie de sûreté prise
   AVANT d'ouvrir un autre projet par-dessus un montage non nommé. */
function dzmProjetNeuf(nom){
  var n=String(nom||"").trim()||"montage neuf";
  return {name:n,vide:!0,tracks:DZM_DEFAULT_TRACKS.map(function(t){return Object.assign({},t)})}}
function dzmInstantaneNom(nom,now){
  var n=String(nom||"").trim();
  if(n&&n!=="montage")return n;
  var d=now instanceof Date?now:new Date(),p=function(v){return (v<10?"0":"")+v};
  return "(non nommé) "+p(d.getDate())+"/"+p(d.getMonth()+1)+" "+p(d.getHours())+":"+p(d.getMinutes())}
```

Dans `DzmProjects` : (a) une fonction `ouvrir(p)` factorisée à partir du code d'ouverture existant (celui du bouton « ouvrir » → « remplacer ? ») ; (b) **instantané** : au début de `ouvrir`, si `!pid` (montage courant non nommé) et `props.payload` rend un objet à `clips.length>0`, `send("/api/montage/projects","POST",{name:dzmInstantaneNom(nm,new Date()),timeline:tl})` d'abord (échec → `note("Copie de sûreté impossible — ouverture annulée")` et STOP) ; (c) bouton **`nouveau`** dans la rangée `dzm-projsave` (à gauche de « enregistrer sous… ») : `send("/api/montage/projects","POST",dzmProjetNeuf(nv))` puis `ouvrir({id:d.id,name:d.name})` (avec l'instantané de (b)) ; infobulle « Créer un montage vide et l'ouvrir (le montage affiché est d'abord enregistré s'il n'a pas de nom) » ; (d) chaque ligne de projet marque `vide` par une chip `∅` (texte) après le nom quand `p.vide`. **Grille de cartes : NON construite** (la liste tient, l'utilisateur veut du simple — écart à dater en tâche 6). Exports : `projetNeuf:dzmProjetNeuf,instantaneNom:dzmInstantaneNom,`.

Replis bundle : dans `R_M5`, après `      tracks:svmTracksPayload(proj),` ajouter `      vide:proj.vide===!0?!0:void 0,` ; dans `R_M7`, l'objet `np` gagne `vide:d.vide===!0` (mesurer que `A_M7` commence bien par `var np={demo:!1,name:d.name||"montage",…` et poser la clé après `ratio`). CSS : `.dzsvm .dzm-projnew{margin-right:6px}` `.dzsvm .dzm-projvide-chip{font:10px var(--f-mono);color:var(--ink2);margin-left:4px}`.

- [ ] **Étape 3 : bancs bundle (pins des deux replis : `s.count("vide:proj.vide===!0")==1`, `s.count("vide:d.vide===!0")==1`), chaîne, `node --check`, sonde, commit** : `montage : E-1 - bouton nouveau, instantane avant ouvrir, vide porte par le payload`. Preuve écran : « projets » → `nouveau` → timeline vide 7 pistes, « NON ENREGISTRÉ » éteint, F5 → toujours vide (pas les 4 derniers rendus) ; « ouvrir » un autre projet depuis un montage non nommé → une entrée « (non nommé) … » apparaît dans la liste.

---

## Tâche 3 — E-3 : « Ouvrir dans le Montage » (Chapitres, Studio) et la porte de la Bibliothèque sur V1

**Files :** modifier `scripts/patch_bundle_montage.py` (EA1…EA3), `backend/tests/test_montage_bundle.py`, `scripts/patch_bundle_dzcout.py` (si référence ajoutée).

- [ ] **Étape 1 : banc rouge** (`test_montage_bundle.py`) : `s.count('"video",p.dur||0,"v1")') == 1`, `s.count('"video",p.dur||0,"v2")') == 0` (avec la mesure que l'ancre existe : `s.count('{image:p.image},p.image,"image",0,"v2")') == 1` — l'image reste sur v2), `s.count('Ouvrir dans le Montage') == 2`, `s.count('detail:{view:"montage"}') == 2`.

- [ ] **Étape 2 : sections** (mesurer chaque ancre : 1/1 `.bak`, 0 patcher) :

```python
# ── EA1 (E-3) : la porte « Envoyer vers… » de la Bibliothèque vise V1 ─────
# La greffe S4 de libsend (AMONT, intouchable) est REMPLACÉE ici, à l'identique
# sauf le 5e argument : "v1" — addAsset (M16a) prend v1 si elle existe, sinon
# pickTrack ; sur une piste PLEIN CADRE, wantsTwin est vrai et le jumeau A1
# est posé (M22a/M22b). Sur "v2" la vidéo arrivait MUETTE et, sans piste v2,
# INVISIBLE (sauvegarde du 04/09). L'image reste une incrustation (v2).
A_EA1 = ('  x.useEffect(function(){var p=null;try{p=window.__dzMontageAdd;delete window.__dzMontageAdd}catch(_e){}'
         'if(!p)return;setTimeout(function(){try{if(p.image)addAsset({image:p.image},p.image,"image",0,"v2");'
         'else if(p.job_id)addAsset({job_id:p.job_id},p.title||p.job_id,"video",p.dur||0,"v2")}catch(_e2){}},450)},[]);'
         'function defaultLen(kind,srcDur){')
R_EA1 = A_EA1.replace('"video",p.dur||0,"v2")', '"video",p.dur||0,"v1")')
# ── EA2 (E-3) : Chapitres — « Ouvrir dans le Montage » à côté de « Send to Scheduler »
A_EA2 = 'r.jsx(K,{variant:"primary",size:"sm",icon:"calendar",onClick:sendEpisodeToScheduler,children:"Send to Scheduler"})'
R_EA2 = ('r.jsx(K,{variant:"outline",size:"sm",icon:"film",title:"Poser cet épisode sur la piste V1 du Montage, à la tête de lecture, avec son son",'
         'onClick:function(){window.__dzMontageAdd={job_id:epJob,title:title||"Épisode"};'
         'window.dispatchEvent(new CustomEvent("deepotus:navigate",{detail:{view:"montage"}}))},children:"Ouvrir dans le Montage"}),'
         + A_EA2)
# ── EA3 (E-3) : Studio — même bouton dans la rangée du résultat (déjà flex gap:8)
A_EA3 = 'r.jsx("div",{style:{marginTop:10,display:"flex",gap:8},children:r.jsx("a",{href:D.jobVideoUrl(n.id),download:!0,'
R_EA3 = ('r.jsx("div",{style:{marginTop:10,display:"flex",gap:8},children:[r.jsx(K,{variant:"outline",size:"sm",icon:"film",'
         'title:"Poser ce rendu sur la piste V1 du Montage, à la tête de lecture, avec son son",'
         'onClick:function(){window.__dzMontageAdd={job_id:n.id,title:n.title||"Rendu Studio"};'
         'window.dispatchEvent(new CustomEvent("deepotus:navigate",{detail:{view:"montage"}}))},children:"Ouvrir dans le Montage"},"mont"),'
         'r.jsx("a",{href:D.jobVideoUrl(n.id),download:!0,')
# ATTENTION EA3 : `children:` passe d'un élément à un TABLEAU — la fermeture de
# l'élément <a> existant doit être suivie de `]` : MESURER la fin exacte de la
# ligne (`…children:"Download"})})})` ) et étendre l'ancre jusqu'à cette fin
# pour poser `…})}),]})` correctement ; ajouter key sur l'<a> ("dl") pour React.
# Vérifier que `K` accepte `title` (sinon envelopper dans un <span title>), que
# l'icône "film" existe dans la table d'icônes (grep `film:` — sinon "video" ou omettre `icon`),
# et que `n.title` existe (sinon "Rendu Studio").
```

Ni `DzTracks.` ni nouvelle référence : la sonde dzcout ne bouge pas (le vérifier). Les deux sections EA2/EA3 vivent dans des blocs (Chapitres, Studio) hors du scope `sonvfx` : elles n'ont pas besoin de la couche.

- [ ] **Étape 3 : chaîne, `node --check`, bancs, commit** : `montage : E-3 - Ouvrir dans le Montage depuis Chapitres et Studio, porte Bibliotheque sur V1`. Preuve écran par le contrôleur : Library → Renders → vignette → « Envoyer vers… » → « 🎞 Montage — clip vidéo » → le clip est sur **V1** à la tête ET un jumeau « · son du plan » sur A1 ; un job `episode` factice `done` (ou l'upload) : Chapitres n'a pas de résultat sans rendu réel → prouver EA2 par le DOM (`querySelector` du bouton dans le bundle servi) et EA3 idem ; écart daté : « un clip par scène » non livré (aucune durée de scène stockée par le job).

---

## Tâche 4 — E-4 backend : `POST /api/montage/publish`

**Files :** modifier `backend/app/services/montage_service.py`, `backend/tests/test_montage_ea.py` (`[2]`).

- [ ] **Étape 1 : banc rouge** `[2]` — préparer une source réelle comme `test_montage_l2.py:706-713` (mp4 `testsrc2` via `effects_preview.ffmpeg_bin`, SKIP propre sans ffmpeg) envoyée par `POST /api/videos/upload` → `job_id` ; puis :

```python
print("\n[2] E-4 publier = un brouillon Scheduler cree par le backend, a la demande")
r = c.post("/api/montage/publish", json={"job_id": "nope"}); check("e4_job_inconnu_404", r.status_code == 404, r.status_code)
r = c.post("/api/montage/publish", json={}); check("e4_sans_job_id_400", r.status_code == 400, r.status_code)
r = c.post("/api/montage/publish", json={"job_id": JID, "channels": ["x", "zzz", "youtube"], "caption": "salut", "project_id": "m_abc12345"}); d = J(r)
check("e4_200_rend_le_post_avec_id_et_job", r.status_code == 200 and d.get("ok") is True and isinstance(d.get("post"), dict) and d["post"].get("job_id") == JID, str(d)[:200])
P = d.get("post") or {}
check("e4_les_canaux_sont_filtres_par_la_liste_blanche", P.get("channels") in ("x,youtube", ["x", "youtube"]), P.get("channels"))
check("e4_statut_brouillon_mode_assiste", P.get("status") == "draft" and P.get("mode") == "assisted", (P.get("status"), P.get("mode")))
ra = P.get("run_at"); import datetime as _dt
def _parse(s):
    try: return _dt.datetime.fromisoformat(str(s).replace("Z", ""))
    except Exception: return None
check("e4_run_at_par_defaut_est_a_deux_heures", _parse(ra) is not None and 110 * 60 <= (_parse(ra) - _dt.datetime.utcnow()).total_seconds() <= 130 * 60, ra)
check("e4_project_id_voyage_dans_brief", (P.get("brief") or {}).get("project_id") == "m_abc12345" if isinstance(P.get("brief"), dict) else '"project_id": "m_abc12345"' in str(P.get("brief")), P.get("brief"))
r = c.post("/api/montage/publish", json={"job_id": JID, "channels": [], "run_at": "2026-12-01T09:00:00"}); d = J(r)
check("e4_canaux_vides_retombent_sur_x_et_run_at_explicite_est_garde", r.status_code == 200 and (d.get("post") or {}).get("channels") in ("x", ["x"]) and str((d.get("post") or {}).get("run_at", "")).startswith("2026-12-01T09:00"), str(d)[:200])
r = c.get("/api/schedule"); L = J(r); n = len(L) if isinstance(L, list) else len(L.get("_liste", L.get("posts", [])))
check("e4_deux_brouillons_existent_dans_le_scheduler", n == 2, n)
```
(un job `queued`/non vidéo → 409 : ajouter une ligne si un tel job est fabricable en base sans rendu — `JobRecord` direct via `async_session_factory`, comme `test_montage_projets.py` le fait pour ses fixtures ; sinon SKIP dit.)

- [ ] **Étape 2 : implémenter**, à côté de `/render` :

```python
@router.post("/publish")
async def montage_publish(request: Request):
    """E-4 (22/09/2026) — le brouillon Scheduler est créé ICI, à la demande,
    jamais en effet de bord d'un rendu : {job_id, channels?, run_at?, caption?,
    title?, project_id?}. Canaux filtrés par la liste blanche du plan
    (plan_schema._CHANNELS), ["x"] à défaut ; run_at = maintenant + 2 h à
    défaut ; project_id voyage dans `brief` (pas de colonne, pas de migration).
    Même route que le Scheduler (create_scheduled_post), importée LAZY comme
    routes.py importe ce module dans l'autre sens."""
    body = await _json_body(request)
    jid = str(body.get("job_id") or "").strip()
    if not jid:
        raise HTTPException(400, "job_id manquant.")
    async with async_session_factory() as session:
        job = await session.get(JobRecord, jid)
    if job is None:
        raise HTTPException(404, "Rendu introuvable.")
    fp = job.final_video_path or job.video_path
    if str(job.status) != JobStatus.DONE.value or not fp or not _is_video_artifact(fp):
        raise HTTPException(409, "Ce rendu n'est pas terminé (ou n'est pas une vidéo).")
    from app.services.plan_schema import _CHANNELS
    ch = [c for c in (body.get("channels") or []) if isinstance(c, str) and c in _CHANNELS] or ["x"]
    run_at = str(body.get("run_at") or "").strip() or (datetime.utcnow() + timedelta(hours=2)).replace(microsecond=0).isoformat()
    titre = (body.get("title") or job.title or "Montage")[:200]
    post = {"title": titre, "caption": body.get("caption") if isinstance(body.get("caption"), str) else titre,
            "channels": ch, "run_at": run_at, "status": "draft", "mode": "assisted", "job_id": jid}
    pid = body.get("project_id")
    if isinstance(pid, str) and pid:
        post["brief"] = {"project_id": pid}
    from app.api.routes import create_scheduled_post
    return {"ok": True, "post": await create_scheduled_post(post)}
```
(vérifier les noms exacts : `async_session_factory`, `JobRecord`, `JobStatus`, `_is_video_artifact`, `datetime`/`timedelta` déjà importés dans `montage_service.py` — sinon les importer ; `create_scheduled_post` retourne `_post_to_dict(p)` dont `brief` peut être une CHAÎNE JSON : le banc accepte les deux formes.)

- [ ] **Étape 3 : vert, l2/projets inchangés, commit** : `montage : E-4 - POST /publish, le brouillon Scheduler cree par le backend a la demande`.

---

## Tâche 5 — E-4 client : « Rendre », le bandeau de fin, « Envoyer vers le Scheduler »

**Files :** modifier `frontend/patches/montage.js`, `scripts/patch_bundle_montage.py` (EA4, EA5, repli R_M16REF), `frontend/dist/shared/montage.css`, `backend/tests/test_montage_edition.py` (`[13]`), `backend/tests/test_montage_bundle.py`, `scripts/patch_bundle_dzcout.py`.

- [ ] **Étape 1 : banc rouge** `[13]` :

```javascript
/* [13] E-4 : publier */
var NOW=new Date(2026,8,22,14,7,30);
out.pb_def=T.publishDefaults("Pub été",NOW,null);
out.pb_def_mem=T.publishDefaults("",NOW,["youtube","zzz","x"]);
out.pb_norm=[T.channelsNorm(["zzz"]),T.channelsNorm(null),T.channelsNorm(["instagram","x","x"])];
out.pb_local=T.publishLocal(NOW);
```
Python :
```python
print("\n[13] E-4 publier (client)")
check("pb_defaults_plus_deux_heures_au_quart_d_heure_x_par_defaut_legende_nom",
      D.get("pb_def") == {"channels": ["x"], "run_at": "2026-09-22T16:15", "caption": "Pub été"}, D.get("pb_def"))
check("pb_defaults_reprend_les_canaux_memorises_filtres", (D.get("pb_def_mem") or {}).get("channels") == ["youtube", "x"] and (D.get("pb_def_mem") or {}).get("caption") == "Montage", D.get("pb_def_mem"))
check("pb_norm_liste_blanche_sans_doublon_x_a_defaut", D.get("pb_norm") == [["x"], ["x"], ["instagram", "x"]], D.get("pb_norm"))
check("pb_local_est_la_forme_datetime_local", D.get("pb_local") == "2026-09-22T16:15", D.get("pb_local"))
```

- [ ] **Étape 2 : implémenter** (montage.js) :

```javascript
/* ── E-4 (22/09/2026) : PUBLIER, À LA DEMANDE. Le rendu ne crée plus rien
   dans le Scheduler ; le bandeau de fin propose l'envoi. Défauts partagés
   avec la Bibliothèque (+2 h, arrondi au quart d'heure suivant, canal « x »),
   canaux mémorisés (dz_montage_channels), liste blanche = celle du plan. */
var DZM_CHANNELS=[["x","X"],["telegram","Telegram"],["youtube","YouTube"],["instagram","Instagram"]];
function dzmChannelsNorm(list){
  var ok=DZM_CHANNELS.map(function(c){return c[0]}),out=[];
  (Array.isArray(list)?list:[]).forEach(function(c){if(ok.indexOf(c)>=0&&out.indexOf(c)<0)out.push(c)});
  return out.length?out:["x"]}
function dzmPublishLocal(now){
  var d=new Date(now.getTime()+2*3600*1000),q=15*60*1000;d=new Date(Math.ceil(d.getTime()/q)*q);
  var p=function(v){return (v<10?"0":"")+v};
  return d.getFullYear()+"-"+p(d.getMonth()+1)+"-"+p(d.getDate())+"T"+p(d.getHours())+":"+p(d.getMinutes())}
function dzmPublishDefaults(nom,now,memo){
  return {channels:dzmChannelsNorm(memo),run_at:dzmPublishLocal(now),caption:String(nom||"").trim()||"Montage"}}
/* LE BANDEAU DE FIN DE RENDU. props : {fin:{job_id,name,project_id}, onSend(form)→Promise, onLib(), onClose(), memo:[…]} */
function DzmFinBandeau(o){
  var fin=o&&o.fin;if(!fin)return null;
  var d0=dzmPublishDefaults(fin.name,new Date(),o.memo);
  var s1=x.useState(d0.channels),ch=s1[0],setCh=s1[1];
  var s2=x.useState(d0.run_at),when=s2[0],setWhen=s2[1];
  var s3=x.useState(d0.caption),cap=s3[0],setCap=s3[1];
  var s4=x.useState(""),st=s4[0],setSt=s4[1];
  var tog=function(id){setCh(function(c){return c.indexOf(id)>=0?c.filter(function(k){return k!==id}):c.concat([id])})};
  return r.jsxs("div",{className:"svm-pop dzm-fin",children:[
    r.jsx("div",{className:"svm-poptitle",children:"Rendu terminé"}),
    r.jsx("div",{className:"dzm-fin-row",children:DZM_CHANNELS.map(function(c){return r.jsxs("label",{className:"dzm-fin-ch",children:[
      r.jsx("input",{type:"checkbox",checked:ch.indexOf(c[0])>=0,onChange:function(){tog(c[0])}})," "+c[1]]},c[0])})}),
    r.jsxs("div",{className:"dzm-fin-row",children:[r.jsx("input",{type:"datetime-local",value:when,onChange:function(e){setWhen(e.target.value)}}),
      r.jsx("input",{type:"text",value:cap,placeholder:"légende",onChange:function(e){setCap(e.target.value)}})]}),
    st?r.jsx("div",{className:"dzm-fin-st",children:st}):null,
    r.jsxs("div",{className:"dzm-fin-row",children:[
      r.jsx("button",{className:"svm-goldbtn",disabled:st==="…",onClick:function(){setSt("…");
        Promise.resolve(o.onSend({job_id:fin.job_id,project_id:fin.project_id||void 0,channels:dzmChannelsNorm(ch),run_at:when,caption:cap}))
          .then(function(){setSt("Brouillon ajouté au Scheduler")}).catch(function(e){setSt("Envoi impossible : "+String(e))})},children:"Envoyer vers le Scheduler"}),
      r.jsx("button",{className:"svm-secbtn",onClick:function(){o.onLib&&o.onLib()},children:"Voir dans la Bibliothèque"}),
      r.jsx("button",{className:"svm-secbtn",onClick:function(){o.onClose&&o.onClose()},children:"Fermer"})]})]})}
```
Exports : `channelsNorm:dzmChannelsNorm,publishLocal:dzmPublishLocal,publishDefaults:dzmPublishDefaults,FinBandeau:DzmFinBandeau,CHANNELS:DZM_CHANNELS,`. (`x`/`r` lus à l'appel — le composant n'est jamais appelé sous node.)

Sections :

```python
# ── EA4 (E-4) : le poll ne publie plus — il ouvre le bandeau ────────────────
# Ancre = TOUT l'ancien bloc, de `var run=…` à `.catch(…)})}}` (mesurer le texte
# exact des 11 lignes dans .bak_montage:3949-3959, 1/1, patcher 0) ; remplacement :
#   '            setJob(null);setPop("");setDirty(!1);\n'
#   '            setDzFin({job_id:job.id,name:proj.name,project_id:proj.project_id||""});\n'
#   '            fireNote("Rendu final terminé — « Envoyer vers le Scheduler » pour le publier.")}}'
# (garder EXACTEMENT les accolades de fermeture de l'ancien bloc : else{ … } puis } du if(d.status==="done"))
# ── état dzFin : REPLI R_M16REF (var stDzFin=x.useState(null),dzFin=stDzFin[0],setDzFin=stDzFin[1];)
# ── EA5 (E-4) : le popover dit « Rendre », la ligne « publication » disparaît, le titre change ──
A_EA5a = '      r.jsx("div",{className:"svm-poptitle",children:isR?"Rendre & publier":"Preview 480p"}),'
R_EA5a = '      r.jsx("div",{className:"svm-poptitle",children:isR?"Rendre (master 1080)":"Preview 480p"}),'
A_EA5b = '      isR?r.jsxs("div",{className:"svm-popline",children:[r.jsx("span",{children:"publication · brouillon Scheduler"}),r.jsx("span",{className:"svm-cost",children:"gratuit"})]}):null,'
R_EA5b = '      isR?r.jsxs("div",{className:"svm-popline",children:[r.jsx("span",{children:"publication · à la demande, après le rendu"}),r.jsx("span",{className:"svm-cost",children:"gratuit"})]}):null,'
A_EA5c = '          "Rendu local 1080 (aucun crédit consommé), puis brouillon dans le Scheduler — rien n\'est publié sans ta validation.":'
R_EA5c = '          "Rendu local 1080 (aucun crédit consommé). À la fin, un bandeau propose l\'envoi vers le Scheduler — rien n\'est publié sans ta validation.":'
A_EA5d = '        r.jsx("button",{className:"svm-goldbtn",onClick:function(){setPop(pop==="render"?"":"render")},children:"Rendre & publier →"}),'
R_EA5d = '        r.jsx("button",{className:"svm-goldbtn",onClick:function(){setPop(pop==="render"?"":"render")},children:"Rendre →"}),'
# le libellé du BOUTON du popover (`"Rendre & publier"` dans children du bouton d'action, mesurer la ligne) → "Rendre"
# ── EA5e : le bandeau monté à côté de popover() — ancre `        popover(),` (mesurer 1/1) →
#   '        popover(),\n'
#   '        dzFin?r.jsx(DzTracks.FinBandeau,{fin:dzFin,memo:(function(){try{return JSON.parse(localStorage.getItem("dz_montage_channels")||"null")}catch(_e){return null}})(),\n'
#   '          onSend:function(f){try{localStorage.setItem("dz_montage_channels",JSON.stringify(f.channels))}catch(_e){}\n'
#   '            return fetch("/api/montage/publish",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(f)})\n'
#   '              .then(function(res){return res.ok?res.json():res.json().then(function(j){throw (j&&j.detail)||res.status})})\n'
#   '              .then(function(d){var id=d&&d.post&&d.post.id;if(id)window.dispatchEvent(new CustomEvent("deepotus:select-post",{detail:{id:id}}))})},\n'
#   '          onLib:function(){window.dispatchEvent(new CustomEvent("deepotus:navigate",{detail:{view:"library"}}))},\n'
#   '          onClose:function(){setDzFin(null)}}):null,'
```
CSS : `.dzsvm .dzm-fin{top:52px;right:18px;width:360px}` `.dzsvm .dzm-fin-row{display:flex;gap:8px;align-items:center;margin-top:8px;flex-wrap:wrap}` `.dzsvm .dzm-fin-ch{font:11px var(--f-mono)}` `.dzsvm .dzm-fin input[type=text]{flex:1;min-width:120px}` `.dzsvm .dzm-fin-st{font:11px var(--f-mono);color:var(--ink2);margin-top:6px}`. **Pas de navigation forcée** : après l'envoi, le bandeau affiche « Brouillon ajouté au Scheduler » et reste ; le Scheduler a déjà sélectionné le post (`select-post`) pour la prochaine visite.

- [ ] **Étape 3 : bancs bundle (pins EA4/EA5a-e + repli `stDzFin`), chaîne, `node --check`, sonde dzcout (une référence `DzTracks.FinBandeau` de plus), commit** : `montage : E-4 - Rendre sans publier, bandeau de fin, Envoyer vers le Scheduler a la demande`. Preuve écran : « Rendre → » → popover « Rendre (master 1080) » sans ligne « brouillon » → rendu réel des deux clips → bandeau « Rendu terminé » avec 4 cases, heure +2 h, légende ; cocher Telegram, « Envoyer vers le Scheduler » → « Brouillon ajouté au Scheduler », `GET /api/schedule` → 1 post `channels: "x,telegram"`, `brief.project_id` ; aucune navigation.

---

## Tâche 6 — clôture E-A : mutations, comptes, conception, mémoire

- [ ] `backend/tests/mutations_montage_ea.py` (modèle `mutations_montage_l2.py`) : ≥ 8 mutations en octets — `vide` non gardé par `_save_record` ; garde 400 sans l'exception `vide` ; `GET /project` sans `or vide` ; `open` sans l'exemption ; `_CHANNELS` ignoré dans `/publish` ; `run_at` défaut à +1 j ; `brief` sans `project_id` ; `dzmChannelsNorm` sans liste blanche ; `dzmPublishLocal` sans arrondi ; EA1 remis sur `"v2"` (bundle) ; EA4 qui refait `fetch("/api/schedule"` (bundle) — chacune rougit une ligne nommée, table mesurée, restauration sha256, état MORT.
- [ ] Banc croisé : `_CLIENT_DEFAULT_TRACKS` (service) == `DZM_DEFAULT_TRACKS` (montage.js, ids/kinds/bus/loop) — lire `montage.js` en octets, regex gardée.
- [ ] Comptes de référence ; `repatch_all --list` ; `node --check` ; hash du bundle ; sonde finale.
- [ ] Conception `2026-09-22-montage-vs-resolve-app-design.md` §1 : « — **exécuté <date>** : … ; **écarts** : » — E-1 : liste conservée (pas de grille de cartes), pas de vignette, `bibliothèque` (réinitialiser) inchangé ; E-3 : un seul plan par épisode (aucune durée de scène stockée), pas de marqueur par scène, image « Envoyer vers… » toujours sur v2, les portes Scheduler de Chapitres/Studio gardent leurs propres conventions ; E-4 : presets de sortie = D-35 (L4), pas de file, le bandeau ne mémorise que les canaux.
- [ ] Mémoire (`montage-vs-resolve-inventaire.md`, par Edit) ; commit, push, rapport. Déploiement et PR : à demander à l'utilisateur.

---

## Relecture du plan (faite avant remise)

- Couverture : E-1 (T1–T2), E-3 (T3), E-4 (T4–T5), clôture (T6). Les trois « grille de cartes », « un clip par scène », « presets de sortie » sont EXPLICITEMENT laissés en écart (consigne de simplicité ; la 2ᵉ n'a pas de données).
- Ancres : toutes comptées le 22/09 (rapport d'exploration §C, §E, §F, §G, §H) ; `else{` proscrite ; EA3 exige de mesurer la fin de ligne ; EA4 exige le texte exact des 11 lignes.
- Noms : `dzmProjetNeuf/instantaneNom` (T2), `dzmChannelsNorm/publishLocal/publishDefaults/DzmFinBandeau` (T5), `montage_publish` + `_CLIENT_DEFAULT_TRACKS` (T1/T4), `dzFin/setDzFin` (T5, repli R_M16REF).
