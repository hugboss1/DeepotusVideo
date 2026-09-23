# Lot E-B du Montage — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** livrer E-2 (tiroir Médias : rendus vidéo paginés, chips de provenance, recherche), E-5 (barre de titre « Preview · Rendre · Publier »), E-11 (voile sous les popovers qui arment un mode), E-8 (inspecteur repliable et redimensionnable), E-9 (séparateur lecteur/timeline + durée sur les clips) et D-7 (mini-carte) de `docs/superpowers/specs/2026-09-22-montage-vs-resolve-app-design.md` (validée le 22/09/2026), sans complexifier : chaque geste réutilise un mécanisme existant mesuré.

**Architecture :** backend = un seul juge « vidéo » et la pagination dans `Pipeline.list_jobs` / `GET /api/jobs` ; couche `frontend/patches/montage.js` = fonctions pures + composants qui lisent `r`/`x` à l'appel, exportés par `DzTracks` ; patcher `scripts/patch_bundle_montage.py` = sections `EB1…EB9` en queue de `PATCHES`, replis dans `R_TT11` et `R_M16D` quand l'ancre est consommée ; CSS dans `frontend/dist/shared/montage.css` (jamais `son-vfx-montage.css`).

**Tech :** FastAPI + SQLAlchemy async, bundle React pré-compilé patché en octets, bancs Python maison lancés par le python embarqué.

---

## Conventions valables pour tout le plan

```powershell
$PY = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"
Set-Location backend
& $PY tests\test_montage_eb.py                           # NEUF (T1)
& $PY tests\test_montage_ea.py                           # 31/0
& $PY tests\test_montage_edition.py                      # 207/0 au départ
& $PY tests\test_montage_bundle.py                       # 1776/0 au départ
& $PY tests\test_montage_historique.py                   # 51/0
& $PY tests\test_montage_projets.py                      # 159/0
& $PY tests\test_montage_l3.py                           # 86/0
Set-Location ..
& $PY scripts\patch_bundle_montage.py --check --force-unchained   # 125 ancres OK au départ
& $PY scripts\repatch_all.py --from montage ; & $PY scripts\repatch_all.py --list   # finit montage OK / dzcout OK
node --check frontend\dist\assets\index-BEOJX8L5.js ; node --check frontend\patches\montage.js
```

- Un banc = un processus, jamais `pytest`. `check(label, cond, detail)`, fin `=== N passed, M failed ===`, code de sortie 1 si rouge. Labels snake_case sans accent.
- **Règle des assertions négatives** : une négation établit d'abord que la mesure a eu lieu (témoin positif dans la même expression). Chaque banc construit son état vide (le `TypeError`/`404` de l'ancien code EST l'état vide du backend ; un shim sur fichier vide EST celui du cœur JS).
- **Faute n°6** : aucune lecture nue (`[0]`, `.index`, `.json()`, `group()`) avant un `check`.
- **Ancres** : comptées sur `frontend/dist/assets/index-BEOJX8L5.js.bak_montage` (1 421 572 o, présent). Ancre saine = 1 dans `.bak`, 0 dans le patcher hors sa section. Ancre consommée → repli dans le remplacement hôte. **Le `.bak_dzcout` est plus récent : lancer le patcher montage seul est refusé par la garde, toujours `repatch_all --from montage`.** Sections nouvelles EN QUEUE de `PATCHES`, après `AJ7-pose-d-effet-sur-l-ajustement`. Préfixes pris : `M E H R T K X V TT EA DZ KF AJ`. **Préfixe de ce lot : `EB`.**
- Le bundle se lit/écrit en OCTETS. Après tout rejeu : `--list` complet, `node --check`, CRLF == LF, `git hash-object`, sonde dzcout `("montage","DzTracks",114)` (`scripts/patch_bundle_dzcout.py:314`) remesurée à chaque tâche qui ajoute une référence `DzTracks.` dans le bundle (comptage `str.count` brut, les commentaires comptent) ; monter le chiffre ET le justifier ligne à ligne comme les entrées précédentes.
- `localStorage` : clés préfixées `dz_`, toujours dans `try{}catch(_e){}`.
- Commits : `git commit --only <chemins>`, première ligne sans accent, trailer EXACT `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` ; push de `chantier/montage-eb` après chaque tâche. Preuve à l'écran par le contrôleur (backend du worktree sur 8799, projet réel, Playwright + Chrome).
- Chaque agent CONTESTE le plan si la mesure le contredit : mesurer, écrire l'écart daté dans la docstring, puis implémenter la forme mesurée.

## Faits mesurés le 23/09/2026 (relevé lecture seule)

- `openPicker(trId)` (`.bak:3721`) : son bloc `Promise.all(...)` est CONSOMMÉ par `M16c` (`R_M16C` porte `/api/montage/media-rules` + `DzTracks.isVideoJob(j3,xt)`, `.slice(0,12)` survivant). `ovPicker()` (`.bak:4291`) rend un `.svm-pop` `top:96` ; son titre est consommé par `M15b`. Le `+` d'en-tête de piste (`openPicker(tr.id)},children:"+"},"add");`) est consommé par `TT11` → toute action nouvelle sur le `+` se replie dans `R_TT11` (qui porte déjà `dzTtAdd` et `dzAjAdd`). Drag existant : `draggable:!0` + `dragPayload(e,{job_id:…},label,"video",dur)` ; réception `svmDragOk`/`dropOnTrack`.
- Tiroirs `.svm-mid` (`.bak:4997`) : `DzSfx.Drawer` (`open:sfxOn`), `subsPanel()`, `narrPanel()`, `.svm-playerzone`, `aside.svm-insp` ; trois booléens EXCLUSIFS `sfxOn/subsOn/narrOn` basculés par chips `svm-themechip` de la barre de titre (`sfxToggle`, `narrToggle`) ; `.svm-mid{flex:1;display:flex;min-height:0}`. Pas d'état `mid`.
- Pose d'un clip : `addAsset(src,label,kind,srcDur,trId,atTime)` (`.bak:3752`), `DzTracks.pickTrack(ts,kind)`, `DzTracks.twinPlan(neuf,ts,clips,v,locked)`.
- Backend : `GET /api/jobs` (`routes.py:3368`) → `Pipeline.list_jobs(limit=50)` (`pipeline.py:1283-1321`, `limit` seul, exclut `montage_proxy`/`montage_stab`, tri `created_at.desc()`), `_job_to_dict` (`routes.py:3330`) expose `provider,title,created_at,duration_s,video_path,final_video_path`, PAS de `project_id`. Providers réels : `seedance, heygen, composition, template, news, episode, ugc, montage, animation, asset3d, sprite2d, card3d` (+ NULL lu `seedance`). Juge vidéo unique : `GET /api/montage/media-rules` (`montage_service.py:1884`) + `DzTracks.isVideoJob(j,exts)` (`montage.js:458`). Vignette : `GET /api/montage/strip?src=&n=12&w=78&h=44` (`montage_service.py:3865`).
- Barre de titre (`.bak:4967-4990`) : `children:"Preview 480p (gratuit)"}),` (libre), `"Rendre & publier →"` consommé par `EA5d` (→ `"Rendre →"`), chips `sons`/`narration`/thème libres. `launchRender` garde consommée par `EA6`. Bandeau `DzmFinBandeau` (`montage.js:6109`, export `FinBandeau`), monté par `R_EA5E` entre `popover(),` et `fxPicker(),` sur l'état `dzFin` (`{job_id,name,project_id}`, remis à `null` par `onClose` et par `EA6`). Aucune mémoire durable du dernier rendu final ; `JobRecord` sans `project_id`.
- Popovers : `.svm-pop{position:absolute;top:52px;right:18px;z-index:20;width:300px}` (`son-vfx-montage.css:388`). Arment un mode : `popover()` (état `pop` `""|"preview"|"render"`, `.bak:1703`), `ovPicker()` (`ovPick`, mode remplacement M15b, **drag vers les bandes**), `FinBandeau`. Inspection : `transPopover` (a déjà Échap), `fxPicker`, `kbPanel` (a un VOILE : `.svm-kbscrim{position:absolute;inset:0;z-index:20;…;background:rgba(0,0,0,.38)}` `son-vfx-montage.css:708`, JSX `onClick:setKbOn(!1)` + `stopPropagation` sur le popover). Ancre libre : `    transPopover(),\n    kbPanel(),` (1/0/1).
- Inspecteur : `.svm-insp{width:300px;flex:none;…}` (`son-vfx-montage.css:233`), JSX `      r.jsxs("aside",{className:"svm-insp",children:[` (1/0/1). `.svm-tl` est FRÈRE de `.svm-mid` sous `.dzsvm.svm-col` : la timeline a DÉJÀ toute la largeur (« la timeline reprend la largeur » = rien à faire).
- Timeline : `.svm-tl{flex:none;height:auto;min-height:312px;max-height:48vh}` (`son-vfx-montage.css:303`) surchargé par `montage.css:18` `.dzsvm .svm-tl{height:auto;min-height:356px;max-height:48vh}` ; `.svm-scroll{flex:1;overflow:auto}` > `.svm-lanes{style:{width:zoomPct+"%"}}` ; zoom `zoomPct` 100..800 % (`SVM_ZOOMW`, `.bak:1696`), `tlScrollRef` (`.bak:1730`), gouttière `.svm-gutter{width:88px;sticky}`, PAS de `pxPerSec` (positions en %). Label du clip `r.jsx("div",{className:"svm-cliplabel",children:c.label}),` consommé par `M16d` → repli dans `R_M16D`. Ancres libres : `      r.jsx("div",{className:"svm-scroll",ref:tlScrollRef,children:` et `        r.jsxs("div",{className:"svm-lanes",style:{width:zoomPct+"%"},children:[`.

### Trois affirmations de la conception démenties par la mesure (décisions prises)

1. **Chips « Tout · Studio · Chapitres · Quick · News · Templates · Importés »** : aucun `provider` ne vaut `studio`, `quick` ni `chapitres`. → Table de libellés `DZM_PROV_LBL` (provider → groupe affiché : `seedance/heygen/composition/animation` → « Studio », `episode` → « Chapitres », `news` → « News », `template` → « Templates », `ugc` → « Importés », `montage` → « Montages », autres → le provider tel quel), chips DÉRIVÉES des jobs reçus (comme `libprov`), « Tout » en tête.
2. **Pagination `limit/offset`** : n'existe pas. → T1 l'ajoute à `Pipeline.list_jobs` + `GET /api/jobs` avec `offset`, `providers` (liste), `q` (titre) et `video=1` (juge unique côté backend, même règle que `/media-rules`).
3. **« Publier » sur le dernier rendu final du projet** : aucun lien job↔projet. → le dernier `dzFin` est PERSISTÉ côté client (`localStorage["dz_montage_lastfin"]`, objet `{project_id: {job_id,name,at}}`), « Publier » ouvre le bandeau dessus, grisé avec infobulle s'il n'y a rien pour ce projet ; deux états distincts : `dzFin` (il y a un rendu) et `dzFinOpen` (le bandeau est visible).
4. **Voile sous `ovPicker`** : le voile `inset:0` couvre la timeline et tue le glisser vers les bandes, geste assumé par `R_M15B`. → E-11 pose le voile sous `popover()` (preview/rendu) et sous le bandeau `FinBandeau` seulement ; `ovPicker` reste sans voile (écart daté). Le voile réutilise `.svm-kbscrim` (`.38` déjà mesuré, variante claire incluse) via une classe jumelle `.svm-modescrim` définie dans `montage.css` par les MÊMES déclarations (pas deux opacités).
5. **Séparateur 30–70 % vs `max-height:48vh`** : incompatibles. → quand une hauteur est choisie, `.dzsvm .svm-tl[data-h]{max-height:none;min-height:0}` et `height` inline ; sans choix, l'ancien plafond reste.
6. **Mini-carte « au-dessus de la règle »** : dans `.svm-lanes` elle suivrait le zoom. → posée dans `.svm-tl` AVANT `.svm-scroll` (ancre 21), hors zoom ; les planchers `min-height` de `montage.css:18` montent de 30 px (356 → 386) pour ne pas perdre de pistes ; « clic = centrer » vit dans l'hôte (seul détenteur de `tlScrollRef`), la fonction pure ne rend que des rectangles en fractions.
7. **Images et sons** : le tiroir Médias sert les RENDUS VIDÉO (l'exigence n°1) ; le popover `ovPicker` garde Images/Sons pour « lier » des images et des pistes audio (écart daté : « le sélecteur devient un tiroir » n'est vrai que pour les vidéos, pour ne pas dupliquer trois fetchs ni rouvrir `R_M16C`).

## Fichiers

| Fichier | Rôle dans ce lot |
|---|---|
| `backend/app/services/pipeline.py` | `list_jobs(limit, offset, providers, q, video_exts)` (T1) |
| `backend/app/api/routes.py` | `GET /jobs` avec `offset`, `providers`, `q`, `video` (T1) |
| `backend/app/services/montage_service.py` | exposer la règle vidéo (`media_rules()` → `{video_exts, video_providers}`) si elle n'est pas déjà une fonction (T1) |
| `backend/tests/test_montage_eb.py` | banc backend du lot : `[1]` pagination/filtres, `[2]` espion `/jobs` depuis le juge vidéo (T1) |
| `frontend/patches/montage.js` | `DZM_PROV_LBL`, `dzmProvGroupe`, `dzmProvChips`, `dzmMediaFiltre`, `DzmMediaDrawer` (T2) ; `dzmFinStore` (T4) ; `dzmClamp` + `dzmInspW`/`dzmTlH` (T6/T7) ; `dzmDurLbl` (T7) ; `dzmMinimap` + `DzmMinimap` (T8) — exports en queue de `DzTracks` |
| `scripts/patch_bundle_montage.py` | sections `EB1…EB9` en queue ; replis dans `R_TT11` (T3) et `R_M16D` (T7) |
| `frontend/dist/shared/montage.css` | `.svm-meddrawer`, chips, `.svm-modescrim`, `.svm-insp[data-w]`, poignées, `.svm-tl[data-h]`, `.svm-minimap` |
| `backend/tests/test_montage_edition.py` | section `[19]` couche E-B (T2, T4, T6, T7, T8) |
| `backend/tests/test_montage_bundle.py` | section `[EB]` (T3, T4, T5, T6, T7, T8) ; compte de référence 1776 → remesuré |
| `scripts/patch_bundle_dzcout.py` | sonde `("montage","DzTracks",N)` (T3, T4, T8) |
| `backend/tests/mutations_montage_eb.py` | harnais de mutations (T9) |
| `docs/superpowers/specs/2026-09-22-montage-vs-resolve-app-design.md` | lignes E-2, E-5, E-8, E-9, E-11 + D-7 datées « exécuté » (T9) |

---

## Tâche 1 — E-2 backend : pagination et filtres de `GET /api/jobs`, juge vidéo côté serveur

**Files :** modifier `backend/app/services/pipeline.py:1283-1321`, `backend/app/api/routes.py:3368-3372`, `backend/app/services/montage_service.py` (autour de :1884) ; créer `backend/tests/test_montage_eb.py`.

- [ ] **Étape 1 : banc rouge.** Modèle : `backend/tests/test_montage_ea.py` (en-tête UTF-8, `check`, `TestClient` SANS lifespan si le banc ea le fait ainsi — copier sa fixture de base temporaire). Section `[1]` :

```python
print("\n[1] E-2 backend : GET /api/jobs pagine (offset), filtre providers/q, juge video unique")
# etat vide : l ancien /jobs ignore offset (rend la meme premiere page)
r0 = c.get("/api/jobs", params={"limit": 3}); j0 = r0.json() if r0.status_code == 200 else []
r1 = c.get("/api/jobs", params={"limit": 3, "offset": 3}); j1 = r1.json() if r1.status_code == 200 else []
ids0 = [j.get("job_id") for j in j0 if isinstance(j, dict)]; ids1 = [j.get("job_id") for j in j1 if isinstance(j, dict)]
check("eb_jobs_offset_rend_la_page_suivante_sans_recouvrement", r0.status_code == 200 and len(ids0) == 3 and len(ids1) >= 1 and not set(ids0) & set(ids1), (ids0, ids1))
rp = c.get("/api/jobs", params={"limit": 50, "providers": "episode,news"}); jp = rp.json() if rp.status_code == 200 else None
check("eb_jobs_providers_ne_rend_que_ces_providers", isinstance(jp, list) and len(jp) >= 1 and all(j.get("provider") in ("episode", "news") for j in jp), jp and [j.get("provider") for j in jp][:8])
rq = c.get("/api/jobs", params={"limit": 50, "q": "PREUVE-EB"}); jq = rq.json() if rq.status_code == 200 else None
check("eb_jobs_q_filtre_par_titre_insensible_a_la_casse", isinstance(jq, list) and len(jq) == 1 and "preuve-eb" in (jq[0].get("title") or "").lower(), jq)
rv = c.get("/api/jobs", params={"limit": 50, "video": 1}); jv = rv.json() if rv.status_code == 200 else None
check("eb_jobs_video_1_ne_rend_que_des_jobs_video_selon_media_rules", isinstance(jv, list) and len(jv) >= 1 and all(_est_video(j) for j in jv) and any(not _est_video(j) for j in (rp.json() if False else j_tous)), (len(jv), len(j_tous)))
check("eb_jobs_offset_negatif_ou_limit_hors_bornes_sont_ramenes", c.get("/api/jobs", params={"limit": 9999, "offset": -5}).status_code == 200)
```

Avant la section, le banc insère dans la base temporaire (comme `test_montage_ea.py` insère ses jobs) au moins : 5 jobs `done` seedance `.mp4`, 1 `episode`, 1 `news`, 1 job `done` titré `PREUVE-EB`, 1 job à artefact `.png` (non vidéo), 1 `montage_proxy` (doit rester exclu). `_est_video(j)` du banc lit `GET /api/montage/media-rules` UNE fois (témoin `status 200`) et applique la règle par extension du chemin ET provider — **le banc ne recopie pas la règle en dur : il la lit**. `j_tous` = `GET /api/jobs?limit=50`.

- [ ] **Étape 2 : lancer → rouge** (offset ignoré : `ids0 == ids1[:3]` ; providers/q/video ignorés).

- [ ] **Étape 3 : implémenter.** `pipeline.py` :

```python
    async def list_jobs(self, limit: int = 50, offset: int = 0, providers=None, q: str | None = None, video_exts=None):
        """E-2 (23/09/2026) : pagination `offset`, filtre `providers` (liste), recherche `q` sur le titre
        (insensible a la casse), et `video_exts` = tuple d extensions : ne garder que les jobs dont
        l artefact (final_video_path ou video_path) porte une de ces extensions. Les proxys et analyses
        restent exclus. Bornes : limit 1..200, offset >= 0."""
        limit = max(1, min(200, int(limit or 50))); offset = max(0, int(offset or 0))
        stmt = (select(JobRecord)
                .where(func.coalesce(JobRecord.provider, "").notin_([_PROXY_PROVIDER, _STAB_PROVIDER])))
        if providers:
            stmt = stmt.where(func.coalesce(JobRecord.provider, "seedance").in_(list(providers)))
        if q:
            stmt = stmt.where(func.lower(func.coalesce(JobRecord.title, "")).like(f"%{q.lower()}%"))
        if video_exts:
            chemin = func.lower(func.coalesce(JobRecord.final_video_path, JobRecord.video_path, ""))
            stmt = stmt.where(or_(*[chemin.like(f"%{e}") for e in video_exts]))
        stmt = stmt.order_by(JobRecord.created_at.desc()).offset(offset).limit(limit)
```

(lire la forme réelle de la requête existante — colonnes, `_PROXY_PROVIDER`, session — et l'étendre sans la réécrire ; `or_`/`func` déjà importés ou à importer de `sqlalchemy`). `routes.py` :

```python
@router.get("/jobs")
async def list_jobs(limit: int = 50, offset: int = 0, providers: str | None = None, q: str | None = None, video: int = 0):
    provs = [p.strip() for p in providers.split(",") if p.strip()] if providers else None
    exts = tuple(montage_service.media_rules().get("video_exts") or ()) if video else None
    jobs = await Pipeline.list_jobs(limit=limit, offset=offset, providers=provs, q=q, video_exts=exts)
    return [_job_to_dict(j) for j in jobs]
```

`montage_service.media_rules()` : si `/media-rules` construit son dict inline, extraire la fonction pure `media_rules() -> dict` et faire appeler la route par elle (un seul juge). Si la règle « vidéo » de `/media-rules` inclut aussi des `providers`, `video=1` doit appliquer la MÊME règle (extension OU provider) : mesurer ce que dit `/media-rules` et l'appliquer identiquement (l'assertion `eb_jobs_video_1…` la lit).

- [ ] **Étape 4 : vert**, `test_montage_ea.py` 31/0, `test_montage_projets.py` 159/0, `test_hygiene_imports.py` rc 0.
- [ ] **Étape 5 : commit** `montage : E-2 - GET /jobs pagine, filtres providers/q, juge video serveur` ; push.

---

## Tâche 2 — E-2 couche : provenance, filtre, `DzmMediaDrawer`

**Files :** modifier `frontend/patches/montage.js` (avant `var DzTracks={`), `backend/tests/test_montage_edition.py` (section `[19]`).

- [ ] **Étape 1 : banc rouge** — section `[19]` sur le modèle des sections `[17]/[18]` (shim sur fichier vide = état vide ; `PROBE` node qui charge la couche et imprime `JSON.stringify(out)`) :

```js
out.prov = [T.provGroupe("seedance"), T.provGroupe("episode"), T.provGroupe("ugc"), T.provGroupe(null), T.provGroupe("zzz")];
out.chips = T.provChips([{provider:"seedance"},{provider:"heygen"},{provider:"episode"},{provider:null},{provider:"zzz"}]);
out.filtre = T.mediaFiltre([{title:"Alpha",provider:"seedance"},{title:"Beta",provider:"episode"},{title:"alphabet",provider:"news"}], {groupe:"Studio", q:""}).map(function(j){return j.title});
out.filtre_q = T.mediaFiltre([{title:"Alpha",provider:"seedance"},{title:"Beta",provider:"episode"}], {groupe:"Tout", q:"ALP"}).map(function(j){return j.title});
out.filtre_vide = T.mediaFiltre([], {groupe:"Tout", q:""}).length;
out.drawer_pure = typeof T.MediaDrawer;
```

Checks Python : `provGroupe` rend `["Studio","Chapitres","Importés","Studio","zzz"]` ; `chips == ["Tout","Studio","Chapitres","zzz"]` (dérivées, uniques, « Tout » en tête, ordre d'apparition) ; `filtre == ["Alpha"]` ; `filtre_q == ["Alpha"]` ; `filtre_vide == 0` ; `drawer_pure == "function"` ; et « le cœur reste pur » : le corps des trois fonctions pures ne contient ni `r.jsx` ni `x.use` (lecture de la source en octets, regex gardée avec témoin `len(corps) > 100`) ; état vide : les six clés absentes sur le shim vide.

- [ ] **Étape 2 : lancer → rouge** (`T.provGroupe is not a function`).

- [ ] **Étape 3 : implémenter** dans la couche :

```js
/* E-2 (23/09/2026) — PROVENANCE des rendus : aucun provider ne s appelle « Studio » ni
   « Chapitres » ; le groupe affiche est DERIVE du provider par cette table (comme les chips
   de la Bibliotheque, patch_bundle_libprov). Un provider inconnu s affiche tel quel. */
var DZM_PROV_LBL={seedance:"Studio",heygen:"Studio",composition:"Studio",animation:"Studio",
  episode:"Chapitres",news:"News",template:"Templates",ugc:"Importés",montage:"Montages"};
function dzmProvGroupe(p){var k=(p==null||p==="")?"seedance":String(p);return DZM_PROV_LBL[k]||k}
function dzmProvChips(jobs){var out=["Tout"],seen={};(jobs||[]).forEach(function(j){var g=dzmProvGroupe(j&&j.provider);if(!seen[g]){seen[g]=1;out.push(g)}});return out}
function dzmMediaFiltre(jobs,f){var g=(f&&f.groupe)||"Tout",q=String((f&&f.q)||"").trim().toLowerCase();
  return (jobs||[]).filter(function(j){if(!j)return false;if(g!=="Tout"&&dzmProvGroupe(j.provider)!==g)return false;
    return !q||String(j.title||j.job_id||"").toLowerCase().indexOf(q)>=0})}
```

`DzmMediaDrawer(props)` : composant (lit `r`/`x` à l'appel comme `DzmFinBandeau`), props `{open, trId, exts, onAdd(job), onClose, dragPayload}` ; état : `jobs` (accumulés), `offset`, `fin` (dernière page courte), `groupe`, `q`, `chargement` ; au premier `open` et à chaque « Plus » : `fetch("/api/jobs?limit=24&offset="+offset+"&video=1")` ; chips = `dzmProvChips(jobs)` ; liste = `dzmMediaFiltre(jobs,{groupe,q})` ; chaque ligne `.svm-medrow` : vignette `img src="/api/montage/strip?src="+encodeURIComponent(JSON.stringify({job_id:j.job_id}))+"&n=1&w=96&h=54"` (loading lazy), titre, `dzmDur(j.duration_s)` (réutiliser le formateur de durée existant de la couche s'il y en a un — mesurer `dzmFmt`/`fmtTc`), chip groupe, `draggable` + `onDragStart:function(e){props.dragPayload(e,{job_id:j.job_id},j.title||j.job_id,"video",j.duration_s||0)}`, clic → `props.onAdd(j)`. Le tiroir rend `null` si `!open`. Recherche `q` locale sur la page chargée ET, si `q.length>=2`, re-fetch `&q=` côté serveur (une seule vérité : le serveur ; la locale n'est qu'un raccourci sur ce qui est déjà là — dater ce choix dans le commentaire). Filtre `groupe` : local sur les pages chargées (les groupes sont dérivés ; si l'utilisateur choisit un groupe et que la page est courte, « Plus » continue de paginer sans filtre serveur — dater). Exports : `provGroupe:dzmProvGroupe, provChips:dzmProvChips, mediaFiltre:dzmMediaFiltre, MediaDrawer:DzmMediaDrawer`.

- [ ] **Étape 4 : vert**, `node --check frontend/patches/montage.js`, édition 207 → +N/0.
- [ ] **Étape 5 : commit** `montage : E-2 - provenance, filtre et tiroir Medias dans la couche` ; push.

---

## Tâche 3 — E-2 bundle : onglet « Médias », tiroir dans `.svm-mid`, « + » vidéo → tiroir

**Files :** modifier `scripts/patch_bundle_montage.py` (sections `EB1`, `EB2`, `EB3` + repli dans `R_TT11`), `frontend/dist/shared/montage.css`, `backend/tests/test_montage_bundle.py` (section `[EB]`), `scripts/patch_bundle_dzcout.py` (sonde).

- [ ] **Étape 1 : banc rouge** — section `[EB]` du banc bundle (modèle `[D-9]`) : ancres 1/0/1 mesurées (`EB1` = état `medOn` : ancre `  var stO=x.useState(""),ovPick=stO[0],setOvPick=stO[1];` → ajoute `var stMed=x.useState(!1),medOn=stMed[0],setMedOn=stMed[1];` ; `EB2` = chip « médias » dans la barre de titre : ancre = la ligne du chip `sons` (`svm-sfxchip`, mesurer le texte exact, 1/0/1) → insère AVANT un chip `svm-themechip` « médias » `onClick:function(){setMedOn(!medOn);setSfxOn(!1);setSubsOn(!1);setNarrOn(!1)}` et fait que `sfxToggle`/`narrToggle`/`setSubsOn(!0)` ferment `medOn` (mesurer où ces trois exclusions s'écrivent : si `sfxToggle` est une fonction 1/0/1, l'étendre par une section ; sinon repli) ; `EB3` = montage du tiroir : ancre `      subsPanel(),\n      narrPanel(),` → `      subsPanel(),\n      narrPanel(),\n      r.jsx(DzTracks.MediaDrawer,{open:medOn,trId:medTr,exts:null,onClose:function(){setMedOn(!1)},dragPayload:dragPayload,onAdd:function(j){addAsset({job_id:j.job_id},j.title||j.job_id,"video",j.duration_s||0,medTr||DzTracks.pickTrack(tracks,"video"),null)}}),` (mesurer les noms réels : `tracks`/`trackList`, `addAsset` signature, `atTime` = `null` ⇒ tête ? — lire `addAsset` :3752 ; `medTr` = état `useState("")` posé avec `medOn` dans `EB1`) ; repli `R_TT11` : la branche vidéo du `+` (`openPicker(tr.id)`) devient `if(trackKind(tr.id)==="video"){setMedTr(tr.id);setMedOn(!0);setSfxOn(!1);setSubsOn(!1);setNarrOn(!1);return}openPicker(tr.id)` — pins : forme neuve ×1 dans le bundle, `openPicker(tr.id)` toujours présent (audio), `dzAjAdd`/`dzTtAdd` intacts). Checks génériques (ancre .bak 1 / patcher 0 / bundle A 0 R 1), queue `…AJ7, EB1, EB2, EB3`, `medOn` exclusif (les quatre `set…(!1)` présents dans le handler du chip), CSS `.svm-meddrawer` présent dans `montage.css` avec `min-width`/`overflow:auto`, sonde dzcout montée (`DzTracks.MediaDrawer` + `DzTracks.pickTrack` = +2 → 116, justifiées).

- [ ] **Étape 2 : rouge.** **Étape 3 : implémenter** (sections en queue, CSS : `.dzsvm .svm-meddrawer{width:340px;flex:none;border-right:1px solid var(--stroke);background:var(--panel);overflow:auto;min-height:0;padding:10px}`, `.svm-medchips{display:flex;gap:6px;flex-wrap:wrap}`, `.svm-medrow{display:flex;gap:8px;align-items:center;padding:6px;border-radius:8px;cursor:grab}`, `.svm-medrow img{width:96px;height:54px;object-fit:cover;border-radius:6px;background:#000}`, `.svm-medrow:hover{background:color-mix(in srgb,var(--acc) 12%,transparent)}`).
- [ ] **Étape 4 : chaîne** `repatch_all --from montage`, `--list`, `node --check`, CRLF == LF, bancs bundle/édition, sonde.
- [ ] **Étape 5 : commit** `montage : E-2 - onglet Medias, tiroir dans svm-mid, plus video vers le tiroir` ; push. Preuve écran (contrôleur) : chip « médias » → tiroir avec chips dérivées (« Tout », « Importés » pour les uploads ugc), recherche, clic → clip V1 + jumeau A1, « + » de V2 → tiroir ciblant V2, « Plus » quand > 24 rendus, F5.

---

## Tâche 4 — E-5 : barre « Preview · Rendre · Publier », dernier rendu mémorisé

**Files :** modifier `frontend/patches/montage.js` (`dzmFinStore`), `scripts/patch_bundle_montage.py` (`EB4`, repli `R_EA4`/`R_EA5E`), `backend/tests/test_montage_edition.py` `[19]`, `backend/tests/test_montage_bundle.py` `[EB]`.

- [ ] **Étape 1 : banc rouge.** Couche : `dzmFinStore(store, project_id, fin)` pure → nouvel objet `{...store, [pid]: {job_id,name,at}}` ; `dzmFinOf(store, pid)` → l'entrée ou `null` ; bornes : `pid` vide → clé `"_"` ; `fin` null → retire la clé. Sonde : `out.fin = T.finStore({}, "p1", {job_id:"j",name:"n",at:1})`, `out.fin_of = T.finOf(out.fin, "p1")`, `out.fin_rm = T.finStore(out.fin, "p1", null)`, `out.fin_none = T.finOf({}, "zz")`. Bundle : `EB4` remplace `children:"Preview 480p (gratuit)"}),` par le groupe à trois boutons : `Preview` (même handler), `Rendre` (handler de l'ancien bouton or, conservé : mesurer `R_EA5D` et NE PAS le dupliquer — le bouton or existant reste, l'ancre `EB4` ne touche que le libellé `Preview` et insère « Publier » APRÈS le bouton or via une seconde ancre 1/0/1 sur la ligne suivante, mesurer) ; « Publier » : `disabled:!dzLast`, `title:dzLast?"Envoyer le dernier rendu au Scheduler":"Aucun rendu final pour ce projet"`, `onClick:function(){setDzFin(dzLast)}` ; `dzLast=DzTracks.finOf(dzFinStoreState, proj.project_id||"_")` ; le store est lu de `localStorage["dz_montage_lastfin"]` au montage et écrit à chaque `setDzFin(non null)` (repli dans `R_EA4` : après `setDzFin({...})` ajouter la persistance par `DzTracks.finStore`) ; `onClose` du bandeau ne vide plus la mémoire (il ferme seulement : `setDzFin(null)` reste le « fermé », la mémoire est le store). Pins : `"Publier"` ×1, `dz_montage_lastfin` ×2 (lecture + écriture), `DzTracks.finOf(` ×1, `DzTracks.finStore(` ×1 (sonde +2 → 118), `Preview 480p (gratuit)` ×0 dans le bundle et `"Preview"` ×1 à sa place, bouton or `"Rendre →"` toujours ×1.
- [ ] **Étapes 2-4 : rouge → implémenter → vert** (chaîne complète). **Étape 5 : commit** `montage : E-5 - barre Preview Rendre Publier, dernier rendu memorise par projet` ; push. Preuve écran : « Publier » grisé avec infobulle sur un projet sans rendu ; après un Preview 480p réel il reste grisé (Preview n'est pas un rendu final : vérifier que `R_EA4` ne pose `dzFin` que pour le final) ; après un rendu final « Publier » s'arme et rouvre le bandeau après F5.

---

## Tâche 5 — E-11 : voile sous les popovers qui arment un mode

**Files :** `scripts/patch_bundle_montage.py` (`EB5`), `frontend/dist/shared/montage.css`, `backend/tests/test_montage_bundle.py` `[EB]`.

- [ ] **Étape 1 : banc rouge.** Ancre `    transPopover(),\n    kbPanel(),` (1/0/1) → `    transPopover(),\n    (pop||dzFin)?r.jsx("div",{className:"svm-modescrim",onClick:function(){setPop("");setDzFin(null)}}):null,\n    kbPanel(),` ; ET les deux popovers concernés reçoivent `onClick:function(e){e.stopPropagation()}` — mesurer : `popover()` rend un `div.svm-pop` (ancre de sa racine 1/0/1 ? sinon repli `R_EA5A`) ; `DzmFinBandeau` est dans la couche : y ajouter le `stopPropagation` (couche, banc édition : regex `svm-pop` + `stopPropagation` dans le corps de `DzmFinBandeau`). Ordre DOM : le voile doit être rendu AVANT les deux popovers pour passer dessous — `popover()` et `FinBandeau` sont rendus avant `transPopover()` (mesurer l'ordre réel dans le bundle : si les popovers viennent avant le voile dans le DOM, le voile les couvre ; alors ancrer le voile AVANT `    popover(),` — ancre consommée par `EA5E` → repli `R_EA5E`, et bancer par z-index : `.svm-modescrim{z-index:19}` sous `.svm-pop{z-index:20}` est la parade la plus simple et indépendante de l'ordre DOM : la RETENIR et le dater). CSS `montage.css` : `.dzsvm .svm-modescrim{position:absolute;inset:0;z-index:19;background:rgba(0,0,0,.38)}` + `[data-svm-theme="light"] .dzsvm .svm-modescrim{background:rgba(0,0,0,.22)}` (reprendre exactement l'opacité claire de `.svm-kbscrim` mesurée). Échap : si un `keydown` global existe (mesurer `case "Escape"`/`e.key==="Escape"` dans le bundle : `transPopover` en a un local), ajouter `if(e.key==="Escape"&&(pop||dzFin)){setPop("");setDzFin(null);return}` dans le gestionnaire global de raccourcis (ancre à mesurer, repli `R_R2` si consommée). Pins : `svm-modescrim` ×1 bundle + ×1 CSS, `z-index:19`, `ovPicker` SANS voile (le texte `svm-modescrim` n'apparaît pas dans le corps de `ovPicker`, témoin `ovPicker(){` ×1).
- [ ] **Étapes 2-4**, **Étape 5 : commit** `montage : E-11 - voile sous les popovers de mode` ; push. Preuve écran : popover Rendre ouvert → clic hors du popover le ferme, un clic sur le popover ne le ferme pas ; Échap ferme ; le sélecteur « lier » n'a pas de voile et le glisser vers V1 marche toujours.

---

## Tâche 6 — E-8 : inspecteur repliable et redimensionnable

**Files :** `frontend/patches/montage.js` (`dzmClamp`, `dzmInspW`), `scripts/patch_bundle_montage.py` (`EB6`), `frontend/dist/shared/montage.css`, bancs édition `[19]` et bundle `[EB]`.

- [ ] **Étape 1 : banc rouge.** Couche : `dzmClamp(v,lo,hi,def)` (NaN → def) ; `dzmInspW(raw)` = `dzmClamp(+raw,260,480,300)`. Sondes : `T.inspW("999")==480`, `T.inspW("abc")==300`, `T.inspW(261)==261`. Bundle : `EB6a` : ancre `      r.jsxs("aside",{className:"svm-insp",children:[` → `      inspOn?r.jsxs("aside",{className:"svm-insp",style:{width:inspW},"data-w":inspW,children:[r.jsx("div",{className:"svm-insphandle",onPointerDown:inspDown}),` ; fermeture du `]})` de l'aside : mesurer sa ligne (1/0/1) → `]}):null,` ; `EB6b` : états `var stIn=x.useState(function(){try{var s=JSON.parse(localStorage.getItem("dz_svm_insp")||"{}");return{on:s.on!==!1,w:DzTracks.inspW(s.w)}}catch(_e){return{on:!0,w:300}}}),inspSt=stIn[0],setInspSt=stIn[1],inspOn=inspSt.on,inspW=inspSt.w;` près de `stO` (ancre `EB1` déjà prise → poser `EB6b` sur `  var stA=x.useState(""),pop=stA[0],setPop=stA[1];` 1/0/1) + `inspDown` (pointer capture sur `window`, `pointermove` → `setInspSt({on:!0,w:DzTracks.inspW(startW+(startX-e.clientX))})`, `pointerup` → persist `localStorage.setItem("dz_svm_insp",JSON.stringify(...))` dans try/catch) ; `EB6c` : bouton bascule « inspecteur » `svm-themechip` dans la barre de titre (à côté du chip « médias » de `EB2` : ancre = le chip `sons`, DÉJÀ prise par `EB2` → replier le second chip dans le remplacement `R_EB2` : mettre les deux chips dans `EB2` dès T3 ? NON — T3 ne connaît pas E-8 : `EB6c` s'ancre sur le remplacement de `EB2` (= « ancre naît d'un remplacement » → repli dans `R_EB2`, autorisé et documenté). CSS : `.dzsvm .svm-insphandle{position:absolute;left:0;top:0;bottom:0;width:6px;cursor:col-resize}` + `.dzsvm .svm-insp{position:relative}`. Pins : `dz_svm_insp` ×2, `DzTracks.inspW(` ×2 (sonde +2), `svm-insphandle` ×1 bundle ×1 CSS, `inspOn?` ×1, l'aside fermé rend `null`.
- [ ] **Étapes 2-4**, **Étape 5 : commit** `montage : E-8 - inspecteur a bascule et poignee 260-480` ; push. Preuve écran : glisser la poignée → largeur mesurée change et survit à F5 ; bascule → `aside` absent, lecteur plus large ; rouvrir.

---

## Tâche 7 — E-9 : séparateur lecteur/timeline, durée sur les clips

**Files :** `frontend/patches/montage.js` (`dzmTlH`, `dzmDurLbl`), `scripts/patch_bundle_montage.py` (`EB7` + repli `R_M16D`), `frontend/dist/shared/montage.css:11-18`, bancs.

- [ ] **Étape 1 : banc rouge.** Couche : `dzmTlH(raw, total)` → hauteur px bornée `[0.30*total, 0.70*total]`, `null` si `raw` vide/NaN (= plafond historique) ; `dzmDurLbl(label, start, end, on)` → `on ? label+" · "+dzmTc(end-start) : label` (réutiliser le formateur de timecode court existant de la couche — mesurer son nom ; sinon `m:ss`). Sondes : `T.tlH("50",1000)==300`, `T.tlH("900",1000)==700`, `T.tlH("",1000)==null`, `T.durLbl("a",0,6,true)=="a · 0:06"`, `T.durLbl("a",0,6,false)=="a"`. Bundle : `EB7a` = états `tlH` (localStorage `dz_svm_tlh`) et `showDur` (`dz_svm_showdur`) sur l'ancre `  var stA=x.useState(""),…` DÉJÀ prise par `EB6b` → repli dans `R_EB6B` (ancre née d'un remplacement) ; `EB7b` = poignée : ancre = la racine de `.svm-tl` (`      r.jsxs("div",{className:"svm-tl",` — mesurer 1/0/1 ; `.bak:5218`) → `      r.jsx("div",{className:"svm-tlhandle",onPointerDown:tlDown}),\n      r.jsxs("div",{className:"svm-tl","data-h":tlH||void 0,style:tlH?{height:tlH}:void 0,` ; `tlDown` mesure `document.querySelector(".dzsvm").clientHeight` comme `total` et pose `DzTracks.tlH(startH+(startY-e.clientY),total)` ; repli `R_M16D` : `children:c.label` → `children:DzTracks.durLbl(c.label,c.start,c.end,showDur)` ; chip « durées » `svm-themechip` dans la barre de titre (repli `R_EB2`, comme E-8). CSS : `.dzsvm .svm-tl[data-h]{max-height:none;min-height:0}`, `.dzsvm .svm-tlhandle{height:6px;cursor:row-resize;flex:none;background:transparent}` `.dzsvm .svm-tlhandle:hover{background:var(--acc)}`. Pins : `dz_svm_tlh` ×2, `dz_svm_showdur` ×2, `DzTracks.tlH(` ×2, `DzTracks.durLbl(` ×1 (sonde +3), `svm-tlhandle` ×1/×1, `data-h` ×1, `max-height:none` ×1, et `montage.css:18` toujours présent (plafond historique conservé sans choix).
- [ ] **Étapes 2-4**, **Étape 5 : commit** `montage : E-9 - separateur lecteur timeline et duree sur les clips` ; push. Preuve écran : glisser la poignée → `.svm-tl` 30–70 % mesuré, F5 ; chip durées → « beta_1 · 0:06 » sur le clip.

---

## Tâche 8 — D-7 : mini-carte de la timeline

**Files :** `frontend/patches/montage.js` (`dzmMinimap`, `DzmMinimap`), `scripts/patch_bundle_montage.py` (`EB8`), `frontend/dist/shared/montage.css:11-18`, `scripts/patch_bundle_dzcout.py`, bancs.

- [ ] **Étape 1 : banc rouge.** Couche : `dzmMinimap(clips, tracks, dur)` pure → `{rows:[{id,kind}], rects:[{tr,row,x0,x1,kind}]}` avec `x0/x1` en fractions `[0,1]` (`start/dur`, `end/dur` bornés), lignes = pistes dans l'ordre reçu, `rects` ignore les clips hors `[0,dur]` et les clips sans piste connue ; `dur<=0` → `{rows:[],rects:[]}`. Sondes : deux pistes/trois clips → 2 rows, 2 rects (le troisième hors durée exclu), fractions exactes ; état vide. Composant `DzmMinimap({clips,tracks,dur,viewFrac:[a,b],onSeek(frac)})` : `div.svm-minimap` 30 px, un `div.svm-mmrow` par ligne, `div.svm-mmrect` positionnés en %, une fenêtre `div.svm-mmview` à `[a,b]`, clic → `onSeek((e.clientX-rect.left)/rect.width)`. Bundle `EB8` : ancre `      r.jsx("div",{className:"svm-scroll",ref:tlScrollRef,children:` (1/0/1) → insère AVANT `      r.jsx(DzTracks.Minimap,{clips:clips,tracks:tracks,dur:proj.duration,viewFrac:mmView,onSeek:function(f){var el=tlScrollRef.current;if(!el)return;var w=el.scrollWidth-88;el.scrollLeft=Math.max(0,f*w-(el.clientWidth-88)/2)}}),` (mesurer les noms `clips`/`tracks`/`proj.duration` réels dans cette portée) ; `mmView` = `[scrollLeft/(scrollWidth-88), (scrollLeft+clientWidth-88)/(scrollWidth-88)]` recalculé sur `scroll` de `.svm-scroll` et sur `zoomPct` (un `useEffect` qui écoute `tlScrollRef.current` — ancre : le `useEffect [zoomPct]` existant `.bak:2827-2828`, mesurer 1/0/1). CSS : `.dzsvm .svm-minimap{height:30px;flex:none;position:relative;margin-left:88px;background:color-mix(in srgb,var(--panel) 80%,transparent);border-bottom:1px solid var(--stroke);cursor:pointer}`, `.svm-mmrow{position:relative;height:calc(30px / var(--mmrows,1))}`, `.svm-mmrect{position:absolute;top:1px;bottom:1px;border-radius:2px;background:var(--c-v)}`, `.svm-mmrect[data-kind="audio"]{background:var(--c-a)}`, `.svm-mmview{position:absolute;top:0;bottom:0;border:1px solid var(--acc);background:color-mix(in srgb,var(--acc) 15%,transparent);pointer-events:none}` ; `montage.css:18` : `min-height:356px` → `386px` (commentaire : +30 px de mini-carte, 23/09). Pins : `DzTracks.Minimap` ×1 (sonde +1), `svm-minimap` ×1/×1, `min-height:386px`, `scrollWidth-88` ×2 (gouttière déduite).
- [ ] **Étapes 2-4**, **Étape 5 : commit** `montage : D-7 - mini-carte de la timeline au-dessus de la regle` ; push. Preuve écran : mini-carte 30 px avec un rect par clip, fenêtre qui suit le zoom 320 %, clic à droite → `scrollLeft` change.

---

## Tâche 9 — clôture E-B : mutations, comptes, conception

- [ ] `backend/tests/mutations_montage_eb.py` (modèle `mutations_montage_l3.py` : `N_ROUGES` comparé par le code, `sys.exit`) ≥ 12 mutations : `list_jobs` sans `offset` ; `providers` ignoré ; `q` sensible à la casse ; `video` sans règle ; `dzmProvGroupe` sans repli `seedance` ; `dzmProvChips` sans « Tout » ; `dzmMediaFiltre` sans `groupe` ; `dzmFinStore` qui ne retire pas sur `null` ; `dzmInspW` sans borne haute ; `dzmTlH` sans borne basse ; `dzmDurLbl` qui ignore `on` ; `dzmMinimap` qui garde les clips hors durée ; `EB5` sans `stopPropagation` (bundle) ; `R_TT11` où le `+` vidéo rappelle `openPicker` (bundle) ; `EB6a` sans `inspOn?` (bundle). Table mesurée, rc 0.
- [ ] Comptes finaux, `--list`, `node --check`, hash, sonde (114 → valeur finale justifiée).
- [ ] Conception (`2026-09-22-montage-vs-resolve-app-design.md`, édition en octets, EOL conservé) : E-2, E-5, E-8, E-9, E-11 du §1/§2 et D-7 (dans `2026-09-21-montage-vs-resolve-design.md` l.48 + ligne L7 l.178) « — **exécuté <date>** : … ; **écarts** : … » — E-2 : chips dérivées par table (pas la liste figée), tiroir = vidéos seulement (images/sons restent dans `ovPicker`), filtre groupe local aux pages chargées, recherche serveur dès 2 caractères, `video=1` juge serveur, vignette `strip n=1` ; E-5 : dernier rendu mémorisé côté client par projet (pas de `project_id` sur les jobs), Preview n'arme pas Publier ; E-11 : `ovPicker` sans voile (glisser), voile par z-index 19, opacité `.38` de `kbscrim` ; E-8 : « la timeline reprend la largeur » était déjà vrai (frères flex) ; E-9 : plafond 48vh conservé tant qu'aucune hauteur n'est choisie ; D-7 : hors zoom au-dessus de `.svm-scroll`, planchers +30 px, clic = centrer dans l'hôte.
- [ ] Mémoire tenue par le contrôleur. Commit, push, rapport. Déploiement et PR à demander à l'utilisateur.

---

## Relecture du plan (faite avant remise)

- Couverture : E-2 (T1–T3), E-5 (T4), E-11 (T5), E-8 (T6), E-9 (T7), D-7 (T8), clôture (T9). Les sept démentis mesurés sont tranchés en tête et datés en T9.
- Cohérence des noms : `dzmProvGroupe/dzmProvChips/dzmMediaFiltre/DzmMediaDrawer` (T2 → T3), `dzmFinStore/dzmFinOf` (T4), `dzmClamp/dzmInspW` (T6), `dzmTlH/dzmDurLbl` (T7), `dzmMinimap/DzmMinimap` (T8) ; exports `provGroupe, provChips, mediaFiltre, MediaDrawer, finStore, finOf, inspW, tlH, durLbl, minimap, Minimap` ; backend `list_jobs(limit, offset, providers, q, video_exts)`, `media_rules()`. Clés `localStorage` : `dz_montage_lastfin`, `dz_svm_insp`, `dz_svm_tlh`, `dz_svm_showdur`.
- Ancres partagées : `stA` (E-8 `EB6b`, puis E-9 replié dans `R_EB6B`), chip `sons` (E-2 `EB2`, puis E-8/E-9 repliés dans `R_EB2`), `+` de piste (`R_TT11`), label du clip (`R_M16D`), `dzFin` (`R_EA4`). Chaque tâche remesure avant d'écrire.
