# Montage « classe Resolve » — lot L2 (transitions, titres, fondus en direct) — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Un sous-agent frais par tâche, deux revues (conformité puis qualité), corrections en boucle, commit `--only` par tâche, push après chaque tâche. **Chaque agent conteste le plan avec des mesures** : sur L0/L1, le plan avait tort neuf fois (ancres à replier, attente d'un banc fausse, section manquante pour les coupes franches) et l'agent avait raison à chaque fois.

**Goal :** donner au Montage les 58 transitions `xfade` de l'ffmpeg livré avec une galerie par familles et un aperçu animé (D-20), des clips **Titre** rendus en ASS avec huit gabarits animés dans la charte (D-21), et les fondus simples joués en direct dans le lecteur vivant (D-12) — décisions D-20, D-21, D-12 de `docs/superpowers/specs/2026-09-21-montage-vs-resolve-design.md`, validées le 21/09/2026.

**Architecture :** RIEN de l'existant n'est réécrit. Le backend étend `_XFADE` et gagne `titles.py` (ASS par gabarit) plus deux routes de catalogue/aperçu ; le client gagne des fonctions **pures** dans `frontend/patches/montage.js` (exportées sur `window.DzTracks`, jouées sous node), câblées par des sections en queue de `PATCHES` dans `scripts/patch_bundle_montage.py` — et **repliées** dans le remplacement qui pose leur ancre quand celle-ci n'existe pas dans `.bak_montage` (R_M5 pour le payload de rendu, R_M16REF pour les refs). Les titres sont des clips **sans `src`** sur une piste `t1` de genre `title` : la persistance les accepte déjà (mesuré : `POST /save` n'exige aucune clé, `GET /project` garde les clips sans `src`). Le bloc `sonvfx`, `subs.js`, `vfxrack.js`, `son-vfx-montage.css` restent intouchables : les règles CSS neuves vont dans `frontend/dist/shared/montage.css`.

**Tech Stack :** Python 3.13 embarqué (stdlib + Pillow), FastAPI + TestClient, ffmpeg 8.1.1 essentials (`/c/ffmpeg/ffmpeg-8.1.1-essentials_build/bin/ffmpeg`, 58 `xfade`), node 24 (bancs du cœur JS par FICHIER shim), bundle `frontend/dist/assets/index-BEOJX8L5.js` en OCTETS, chaîne `python scripts/repatch_all.py --from montage` puis `--list` (`montage OK`, `dzcout OK`).

---

## Conventions valables pour tout le plan

```powershell
$PY = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"
Set-Location backend
& $PY tests\test_montage_bundle.py                       # 1491/0 au départ
& $PY tests\test_montage_edition.py                      # 89/0
& $PY tests\test_montage_historique.py                   # 51/0
& $PY tests\test_montage_projets.py                      # 159/0
& $PY ..\scripts\patch_bundle_montage.py --check --force-unchained   # 85 ancres OK au départ
& $PY ..\scripts\repatch_all.py --from montage ; & $PY ..\scripts\repatch_all.py --list
node --check ..\frontend\dist\assets\index-BEOJX8L5.js
```

- Un banc = un processus, jamais `pytest`. `check(label, cond, detail)`, fin `=== N passed, M failed ===`, code de sortie 1 si rouge. Labels stables, snake_case sans accent.
- **Règle des assertions négatives** : une négation établit d'abord que la mesure a eu lieu (`"cle" in D and …`, `status_code == 200 and saved is True and "x" not in …`). Chaque banc construit son état vide.
- **Faute n°6** : aucune lecture nue (`[1]`, `.index`, `.json()`) avant un `check` — `at()`, `J()`, `find()` avec repli.
- **Ancres** : comptées sur `.bak_montage` (`--check --force-unchained`). Une ancre qui n'existe que parce qu'un remplacement la crée se REPLIE dans ce remplacement (précédents : R4/R5 dans R_M6/R_M7, E1–E3 dans R_M16REF/R_M15B/R_M22A-B, K1–K4/K6, W1/W2). Sections nouvelles EN QUEUE de `PATCHES`, préfixes libres mesurés : `X` (transitions), `V` (veil D-12), `TT` (titres). Les étiquettes `M23`/`M24` du plan de septembre sont PRISES.
- Le bundle se lit et s'écrit en OCTETS. Après tout rejeu : `--list` complet, `node --check`, CRLF == LF, `git hash-object`, et la sonde `("montage","DzTracks",86)` de `scripts/patch_bundle_dzcout.py` remesurée à chaque tâche qui ajoute une référence `DzTracks.` (commentaires JS compris : écrire `insere()` sans namespace dans la prose).
- Commits : `git commit --only <chemins>`, première ligne sans accent, trailer EXACT `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` ; push de `chantier/montage-resolve` après chaque tâche. La preuve à l'écran est faite par le contrôleur (backend du worktree sur 8799, projet réel obtenu par `POST /api/videos/upload` de deux mp4 ffmpeg `testsrc2`).

## Faits mesurés le 21/09/2026 qui bornent ce lot

- `_XFADE` (`montage_service.py:128-140`) a 9 clés → `(nom_xfade, durée_imposée|None)` ; nom inconnu → `_XFADE["cut"]` = `("fade", 0.04)` (coupe franche silencieuse). La transition est celle du **clip de droite** ; `tau` borné `[0.04, seg_durs[k]-0.1, total-0.1]` ; chaque transition raccourcit la timeline de `tau`. Aucun endpoint ne liste les transitions ; le précédent de catalogue servi est `GET /api/montage/effects` / `GET /api/montage/media-rules` (« le client interroge CETTE liste »).
- Les 58 `xfade` de l'ffmpeg livré (`-h filter=xfade`, 0→57) : `fade wipeleft wiperight wipeup wipedown slideleft slideright slideup slidedown circlecrop rectcrop distance fadeblack fadewhite radial smoothleft smoothright smoothup smoothdown circleopen circleclose vertopen vertclose horzopen horzclose dissolve pixelize diagtl diagtr diagbl diagbr hlslice hrslice vuslice vdslice hblur fadegrays wipetl wipetr wipebl wipebr squeezeh squeezev zoomin fadefast fadeslow hlwind hrwind vuwind vdwind coverleft coverright coverup coverdown revealleft revealright revealup revealdown`.
- Client : `SVM_TRANS` = 7 paires `[id,label]` (`bundle:1215`), `svmTransBase`, `svmTransLabel`, `svmTransS` (0,1–1 s) ; popover `transPopover()` = grille `.svm-transgrid` de tuiles `.svm-transtile` avec micro-scène CSS `.svm-tprev[data-tt]` (7 règles dans `son-vfx-montage.css:466-487`, intouchable) ; `<select>` de `transInspector()` avec option « (hérité) » pour un nom inconnu. Aucune section du patcher ne touche `SVM_TRANS`, `transPopover`, `transInspector`. Ancres 1/1 dans `.bak` : `var SVM_TRANS=[`, `function svmTransBase(t){`, `      r.jsx("div",{className:"svm-transgrid",children:SVM_TRANS.map(function(o){`, `            .concat(SVM_TRANS.map(function(o){`, `  function transPopover(){`, `  function transInspector(){`. Aucun pin du banc bundle sur `SVM_TRANS`.
- Lecteur : deux modes — `<video>` unique (preview 480p, porte les vraies transitions) et lecteur **vivant** (`liveOn=!previewUrl&&!proj.demo`) : hôtes `.svm-live` / `.svm-liveov` remplis impérativement par `liveSync()` (`bundle:2462`, appelé après chaque rendu), clip visible = `svmActiveV1(cs,t)` (un seul à la fois, aucun chevauchement). Ancres 1/1 : `  function liveSync(){`, `liveOn&&!liveClip?r.jsx("div",{className:"svm-livegap",children:"trou"}):null,`, `  var liveOn=!previewUrl&&!proj.demo;`.
- ASS : `_subs_ass(payload, canvas, stem)` (`montage_service.py:2352`) écrit `outputs/subtitles/<stem>.ass` UTF-8 **sans BOM**, gravé par `subtitles_filter(ass_path)` (`subtitle_service.py:2145`, `fontsdir` embarqué, échappement `_ff_escape_path`) en **dernier maillon vidéo** (`montage_service.py:2332-2336`). 16 fontes `FONT_FILES` (`subtitle_service.py:96-113`, nom de famille = table `name` du TTF, sinon fallback silencieux), `REF_HEIGHT=1080`, helpers `resolve_style`, `_ass_style_line`, `_ass_time`, `_ass_escape`, `_ASS_FORMAT_STYLE`, `_ASS_FORMAT_EVENT`, `ass_fontsdir`. Aucun `titles.py`.
- Pistes : `DZM_DEFAULT_TRACKS` (`montage.js:166-172`) v2/v1/a1/a2/a3/s1 ; genres `audio/subs/video` ; **`trackKind(trId)` du bundle (`bundle:3796`) ne lit que l'initiale de l'id** (`t1` → `video`) — 16 sites du bloc sonvfx s'y fient ; `dzmPickTrack` replie sur `video` ; `dzmGroup` classe l'inconnu avec les subs ; `s1` non supprimable (`dzmRemove`). Backend : `_tracks_meta` accepte tout `kind` (id ≤ 8 caractères) ; quatre filtres par `kind` (`:2571, 2644, 2666, 2839`) rendent un `kind:"title"` **inerte** ; `renderPayload` jette les clips sans `src` (`clips.filter(function(c){return c.src})` = **A_M5, consommée, reprise en queue de R_M5** → toute modification s'y REPLIE).
- Plan de septembre (`2026-09-03-plan-montage.md`, tâche 12, jamais construite) : `titles.py` à 3 presets, insertion « titres avant S1 chaînés `[tt{j}]` », modèle de clip sans `src` — encore valables ; étiquettes M23/M24 prises, `DzMontage.TitleOverlay` périmé (lecteur impératif), `trackKind` non traité.

## Fichiers

| Fichier | Rôle dans ce plan |
|---|---|
| `backend/app/services/montage_service.py` | `_XFADE` 58 + familles `_XFADE_FAMILIES`, `GET /transitions`, `_tracks_meta` genre `title`, collecte des clips titre, `titles_ass` dans `_build_montage_command`, `GET /title-preview` |
| `backend/app/services/titles.py` | NEUF — `TEMPLATES` (8 gabarits), `BRAND`, `title_spec(clip)`, `to_ass_title(spec, canvas, stem)`, `render_title_png(spec, w, h)` |
| `frontend/patches/montage.js` | pures : `dzmTransFamilies`, `dzmTransList`, `dzmTransLabel`, `dzmTransLive`, `dzmVeil`, `dzmTitleTrack`, `dzmTitleNew`, `dzmTitleAt`, `dzmTitleHtml` ; composants `DzmTransGrid`, `DzmTitleInspector` ; exports |
| `scripts/patch_bundle_montage.py` | sections `X1…X4` (transitions), `V1…V3` (veil), `TT1…TT8` (titres) en queue ; replis dans `R_M5`, `R_M7`, `R_M16REF`, `R_R1`, `R_R2`, `R_K5` |
| `frontend/dist/shared/montage.css` | `.svm-tprev[data-fam]` (6 familles animées), `.dzm-transfam`, `.svm-xfveil`, `.svm-livetitle`, `.dzm-titre*` |
| `scripts/patch_bundle_dzcout.py` | sonde `("montage","DzTracks",N)` remesurée |
| `backend/tests/test_montage_l2.py` | NEUF — backend : catalogue, `_XFADE`, `titles.py` (ASS + mesure PIL), rendu (commande ffmpeg avec `titles_ass`), routes |
| `backend/tests/test_montage_edition.py` | + sections `[5]` transitions/veil et `[6]` titres (cœur JS sous node) |
| `backend/tests/test_montage_bundle.py` | pins X/V/TT, replis nommés, comptes de référence |
| `backend/tests/mutations_montage_l2.py` | NEUF — campagne de mutations (clôture) |
| `docs/superpowers/specs/2026-09-21-montage-vs-resolve-design.md` | « exécuté » + écarts pour D-20, D-21, D-12 |

---

## Tâche 1 — D-20 backend : les 58 transitions, leurs familles, le catalogue servi

**Files :** modifier `backend/app/services/montage_service.py` (`_XFADE`, `_XFADE_FAMILIES`, route), créer `backend/tests/test_montage_l2.py`.

- [ ] **Étape 1 : banc rouge.** Créer `backend/tests/test_montage_l2.py` sur le gabarit de `test_montage_projets.py` (en-tête `sys.stdout.reconfigure`, `TMP`, variables d'environnement `DEEPOTUS_DATA_DIR`/`DATABASE_URL`/`IMAGES_FOLDER`/`OUTPUTS_FOLDER` AVANT `import app`, `J()`, `check()`, `TestClient(app)` avec `with`). Section `[1] D-20 catalogue` :

```python
print("\n[1] D-20 le catalogue des transitions est servi par le backend")
from app.services import montage_service as MS
XF58 = ("fade wipeleft wiperight wipeup wipedown slideleft slideright slideup slidedown "
        "circlecrop rectcrop distance fadeblack fadewhite radial smoothleft smoothright "
        "smoothup smoothdown circleopen circleclose vertopen vertclose horzopen horzclose "
        "dissolve pixelize diagtl diagtr diagbl diagbr hlslice hrslice vuslice vdslice "
        "hblur fadegrays wipetl wipetr wipebl wipebr squeezeh squeezev zoomin fadefast "
        "fadeslow hlwind hrwind vuwind vdwind coverleft coverright coverup coverdown "
        "revealleft revealright revealup revealdown").split()
check("d20_les_58_xfade_sont_des_cles_de_la_table",
      all(n in MS._XFADE and MS._XFADE[n][0] == n for n in XF58),
      [n for n in XF58 if n not in MS._XFADE][:5])
check("d20_les_neuf_cles_historiques_sont_gardees_telles_quelles",
      MS._XFADE["cut"] == ("fade", 0.04) and MS._XFADE["glitch"] == ("pixelize", None)
      and MS._XFADE["slide"] == ("slideleft", None) and MS._XFADE["flash"] == ("fadewhite", None)
      and MS._XFADE["crossfade"] == ("fade", None))
check("d20_chaque_xfade_a_une_famille_et_une_seule",
      sorted(n for f in MS._XFADE_FAMILIES.values() for n in f["noms"]) == sorted(XF58),
      len([n for f in MS._XFADE_FAMILIES.values() for n in f["noms"]]))
check("d20_six_familles_nommees",
      list(MS._XFADE_FAMILIES) == ["fondus", "glissements", "volets", "formes", "zooms", "pixels"])
r = c.get("/api/montage/transitions"); d = J(r)
check("d20_la_route_rend_les_familles_et_le_direct",
      r.status_code == 200 and isinstance(d.get("familles"), list) and len(d["familles"]) == 6
      and sum(len(f.get("items", [])) for f in d["familles"]) == 58
      and all(set(i) >= {"id", "label", "live"} for f in d["familles"] for i in f["items"]),
      str(d)[:200])
check("d20_le_direct_ne_couvre_que_les_fondus_simples",
      sorted(i["id"] for f in d.get("familles", []) for i in f.get("items", []) if i.get("live"))
      == ["fade", "fadeblack", "fadewhite"])
check("d20_un_nom_inconnu_retombe_toujours_en_coupe_franche",
      MS._XFADE.get("zzz", MS._XFADE["cut"]) == ("fade", 0.04))
```

- [ ] **Étape 2 : lancer → rouge** (`_XFADE_FAMILIES` absent, route 404 → `J()` rend `{}`).

- [ ] **Étape 3 : implémenter.** Dans `montage_service.py`, sous `_XFADE` :

```python
# D-20 (21/09/2026) — LES 58 TRANSITIONS DE L'FFMPEG LIVRÉ (8.1.1 essentials,
# `-h filter=xfade`, indices 0…57), par familles. Chaque nom xfade est SA
# PROPRE clé : le client stocke des noms nus (svmTransBase garde le premier
# mot) et cette table est la seule autorité — GET /transitions la sert, le
# client n'en a pas de copie. Les neuf clés historiques restent au-dessus.
_XFADE_FAMILIES = {
    "fondus":      {"label": "fondus",      "noms": ["fade", "fadeblack", "fadewhite", "fadegrays",
                                                     "fadefast", "fadeslow", "dissolve", "distance"]},
    "glissements": {"label": "glissements", "noms": ["slideleft", "slideright", "slideup", "slidedown",
                                                     "coverleft", "coverright", "coverup", "coverdown",
                                                     "revealleft", "revealright", "revealup", "revealdown"]},
    "volets":      {"label": "volets",      "noms": ["wipeleft", "wiperight", "wipeup", "wipedown",
                                                     "wipetl", "wipetr", "wipebl", "wipebr",
                                                     "smoothleft", "smoothright", "smoothup", "smoothdown",
                                                     "diagtl", "diagtr", "diagbl", "diagbr"]},
    "formes":      {"label": "formes",      "noms": ["circlecrop", "rectcrop", "circleopen", "circleclose",
                                                     "vertopen", "vertclose", "horzopen", "horzclose", "radial"]},
    "zooms":       {"label": "zooms",       "noms": ["zoomin", "squeezeh", "squeezev"]},
    "pixels":      {"label": "pixels",      "noms": ["pixelize", "hblur", "hlslice", "hrslice", "vuslice",
                                                     "vdslice", "hlwind", "hrwind", "vuwind", "vdwind"]},
}
for _f in _XFADE_FAMILIES.values():
    for _n in _f["noms"]:
        _XFADE.setdefault(_n, (_n, None))
# Ceux que le lecteur VIVANT sait jouer en CSS (D-12) : un voile noir/blanc,
# ou une baisse d'opacité — tout le reste n'est visible qu'après Preview.
_XFADE_LIVE = ("fade", "fadeblack", "fadewhite")
_XFADE_LABELS = {  # libellés français du catalogue ; le nom xfade reste l'id
    "fade": "fondu", "fadeblack": "fondu noir", "fadewhite": "fondu blanc", "fadegrays": "fondu gris",
    "fadefast": "fondu rapide", "fadeslow": "fondu lent", "dissolve": "dissolution", "distance": "distance",
    "slideleft": "glisse à gauche", "slideright": "glisse à droite", "slideup": "glisse en haut", "slidedown": "glisse en bas",
    "coverleft": "couvre à gauche", "coverright": "couvre à droite", "coverup": "couvre en haut", "coverdown": "couvre en bas",
    "revealleft": "révèle à gauche", "revealright": "révèle à droite", "revealup": "révèle en haut", "revealdown": "révèle en bas",
    "wipeleft": "volet gauche", "wiperight": "volet droit", "wipeup": "volet haut", "wipedown": "volet bas",
    "wipetl": "volet ↖", "wipetr": "volet ↗", "wipebl": "volet ↙", "wipebr": "volet ↘",
    "smoothleft": "volet doux gauche", "smoothright": "volet doux droit", "smoothup": "volet doux haut", "smoothdown": "volet doux bas",
    "diagtl": "diagonale ↖", "diagtr": "diagonale ↗", "diagbl": "diagonale ↙", "diagbr": "diagonale ↘",
    "circlecrop": "cercle (recadre)", "rectcrop": "rectangle (recadre)", "circleopen": "cercle ouvre", "circleclose": "cercle ferme",
    "vertopen": "rideau vertical ouvre", "vertclose": "rideau vertical ferme", "horzopen": "rideau horizontal ouvre",
    "horzclose": "rideau horizontal ferme", "radial": "balayage radial",
    "zoomin": "zoom avant", "squeezeh": "écrase horizontal", "squeezev": "écrase vertical",
    "pixelize": "pixélisé", "hblur": "flou horizontal", "hlslice": "tranches → droite", "hrslice": "tranches → gauche",
    "vuslice": "tranches ↑", "vdslice": "tranches ↓", "hlwind": "vent → droite", "hrwind": "vent → gauche",
    "vuwind": "vent ↑", "vdwind": "vent ↓",
}


def transitions_catalog() -> dict:
    """Le catalogue que le client affiche : familles ordonnées, items {id, label, live}."""
    return {"familles": [
        {"id": k, "label": f["label"],
         "items": [{"id": n, "label": _XFADE_LABELS.get(n, n), "live": n in _XFADE_LIVE}
                   for n in f["noms"]]}
        for k, f in _XFADE_FAMILIES.items()]}
```

Route, à côté de `GET /effects` (`montage_service.py:1520`) :

```python
@router.get("/transitions")
async def montage_transitions():
    """D-20 — les 58 transitions xfade par familles, avec le drapeau `live`
    (jouable en direct dans le lecteur vivant). Le client n'en a pas de copie."""
    return transitions_catalog()
```

Vérifier que `_XFADE_LABELS` couvre les 58 (une ligne de banc : `all(n in MS._XFADE_LABELS for n in XF58)`).

- [ ] **Étape 4 : lancer → vert ; `test_montage_projets.py` inchangé (159/0). Commit** `--only montage_service.py test_montage_l2.py` : `montage : D-20 - les 58 transitions xfade par familles et le catalogue servi`.

---

## Tâche 2 — D-20 client : la galerie par familles et l'aperçu animé

**Files :** modifier `frontend/patches/montage.js`, `scripts/patch_bundle_montage.py` (X1…X4), `frontend/dist/shared/montage.css`, `backend/tests/test_montage_edition.py` ([5]), `backend/tests/test_montage_bundle.py`, `scripts/patch_bundle_dzcout.py`.

- [ ] **Étape 1 : banc rouge** — section `[5]` de `test_montage_edition.py`, PROBE :

```javascript
/* [5] D-20 : la galerie des transitions */
var CAT={familles:[{id:"fondus",label:"fondus",items:[{id:"fade",label:"fondu",live:!0},{id:"fadeblack",label:"fondu noir",live:!0}]},
  {id:"pixels",label:"pixels",items:[{id:"pixelize",label:"pixélisé",live:!1}]}]};
var LEG=[["cut","coupe sèche"],["fade","fondu"],["glitch","pixélisé"]];
out.tl_liste=T.transList(LEG,CAT).map(function(f){return [f.id,f.items.map(function(i){return i.id})]});
out.tl_cut_en_tete=T.transList(LEG,CAT)[0].items[0].id;
out.tl_sans_catalogue=T.transList(LEG,null).map(function(f){return [f.id,f.items.length]});
out.tl_label=[T.transLabel("fadeblack",LEG,CAT),T.transLabel("cut",LEG,CAT),T.transLabel("zzz",LEG,CAT)];
out.tl_fam=[T.transFamily("wipetl",CAT),T.transFamily("cut",CAT),T.transFamily("zzz",CAT)];
out.tl_live=[T.transLive("fade",CAT),T.transLive("pixelize",CAT),T.transLive("cut",CAT),T.transLive("zzz",CAT)];
out.tl_pur=CAT.familles.length===2&&LEG.length===3;
```

Python :

```python
print("\n[5] D-20 galerie des transitions")
check("tl_la_liste_commence_par_les_coupes_puis_les_familles",
      D.get("tl_liste") == [["coupe", ["cut"]], ["fondus", ["fade", "fadeblack"]], ["pixels", ["pixelize"]]], D.get("tl_liste"))
check("tl_cut_reste_en_tete", D.get("tl_cut_en_tete") == "cut")
check("tl_sans_catalogue_les_sept_historiques_restent",
      D.get("tl_sans_catalogue") == [["coupe", 1], ["historiques", 2]], D.get("tl_sans_catalogue"))
check("tl_le_libelle_vient_du_catalogue_puis_de_l_historique_puis_du_nom",
      D.get("tl_label") == ["fondu noir", "coupe sèche", "zzz"], D.get("tl_label"))
check("tl_la_famille_est_connue_ou_vide", D.get("tl_fam") == ["volets", "coupe", ""], D.get("tl_fam"))
check("tl_le_direct_est_dit_par_le_catalogue", "tl_live" in D and D["tl_live"] == [True, False, True, False], D.get("tl_live"))
check("tl_pur", D.get("tl_pur") is True)
```

ATTENTION : `transFamily("wipetl",CAT)` doit rendre `"volets"` alors que `CAT` de la sonde n'a pas cette famille — la fonction porte donc SA PROPRE table des familles (copie du backend, tenue par un banc croisé de la Tâche 8) et le catalogue serveur ne sert qu'aux libellés/`live`. Corrige la sonde si tu choisis l'autre découpage et dis-le.

- [ ] **Étape 2 : implémenter** (montage.js, avant `var DzTracks=`) :

```javascript
/* ── D-20 (21/09/2026) : LA GALERIE DES TRANSITIONS ────────────────────────
   Le backend sert le catalogue (GET /api/montage/transitions : familles,
   libellés, drapeau `live`). Ici : la FORME de la galerie — « coupe » en
   tête, puis les sept historiques hors catalogue (« historiques »), puis
   les familles. `DZM_TRANS_FAM` est la copie côté client des familles, pour
   l'aperçu CSS quand le catalogue n'est pas encore arrivé. */
var DZM_TRANS_FAM={
  fondus:["fade","fadeblack","fadewhite","fadegrays","fadefast","fadeslow","dissolve","distance"],
  glissements:["slideleft","slideright","slideup","slidedown","coverleft","coverright","coverup","coverdown","revealleft","revealright","revealup","revealdown"],
  volets:["wipeleft","wiperight","wipeup","wipedown","wipetl","wipetr","wipebl","wipebr","smoothleft","smoothright","smoothup","smoothdown","diagtl","diagtr","diagbl","diagbr"],
  formes:["circlecrop","rectcrop","circleopen","circleclose","vertopen","vertclose","horzopen","horzclose","radial"],
  zooms:["zoomin","squeezeh","squeezev"],
  pixels:["pixelize","hblur","hlslice","hrslice","vuslice","vdslice","hlwind","hrwind","vuwind","vdwind"]};
var DZM_TRANS_DIR={left:["slideleft","coverleft","revealleft","wipeleft","smoothleft","hrslice","hrwind"],
  right:["slideright","coverright","revealright","wiperight","smoothright","hlslice","hlwind"],
  up:["slideup","coverup","revealup","wipeup","smoothup","vuslice","vuwind"],
  down:["slidedown","coverdown","revealdown","wipedown","smoothdown","vdslice","vdwind"]};
function dzmTransFamily(id,cat){
  if(id==="cut")return "coupe";
  var k;for(k in DZM_TRANS_FAM)if(DZM_TRANS_FAM[k].indexOf(id)>=0)return k;
  var fs=cat&&Array.isArray(cat.familles)?cat.familles:[],i,j;
  for(i=0;i<fs.length;i++)for(j=0;j<(fs[i].items||[]).length;j++)if(fs[i].items[j]&&fs[i].items[j].id===id)return fs[i].id;
  return ""}
function dzmTransDir(id){var k;for(k in DZM_TRANS_DIR)if(DZM_TRANS_DIR[k].indexOf(id)>=0)return k;return ""}
function dzmTransLive(id,cat){
  var fs=cat&&Array.isArray(cat.familles)?cat.familles:[],i,j;
  for(i=0;i<fs.length;i++)for(j=0;j<(fs[i].items||[]).length;j++){var it=fs[i].items[j];if(it&&it.id===id)return !!it.live}
  return id==="cut"}
function dzmTransLabel(id,legacy,cat){
  var fs=cat&&Array.isArray(cat.familles)?cat.familles:[],i,j;
  for(i=0;i<fs.length;i++)for(j=0;j<(fs[i].items||[]).length;j++){var it=fs[i].items[j];if(it&&it.id===id&&it.label)return String(it.label)}
  var lg=(Array.isArray(legacy)?legacy:[]).filter(function(o){return o&&o[0]===id})[0];
  return lg?String(lg[1]):String(id)}
function dzmTransList(legacy,cat){
  var lg=Array.isArray(legacy)?legacy:[],fs=cat&&Array.isArray(cat.familles)?cat.familles:[];
  var inCat={},out=[{id:"coupe",label:"coupe",items:[{id:"cut",label:dzmTransLabel("cut",lg,cat),live:!0}]}];
  fs.forEach(function(f){(f.items||[]).forEach(function(it){if(it&&it.id)inCat[it.id]=1})});
  var hist=lg.filter(function(o){return o&&o[0]!=="cut"&&!inCat[o[0]]}).map(function(o){return {id:o[0],label:String(o[1]),live:dzmTransLive(o[0],cat)}});
  if(hist.length)out.push({id:"historiques",label:"historiques",items:hist});
  fs.forEach(function(f){out.push({id:String(f.id),label:String(f.label||f.id),
    items:(f.items||[]).filter(Boolean).map(function(it){return {id:String(it.id),label:String(it.label||it.id),live:!!it.live}})})});
  return out}
/* la grille : une rangée de titre par famille, les tuiles reprennent la
   classe `.svm-transtile` et la micro-scène `.svm-tprev` du bundle ; la
   famille et la direction sont posées en data-* pour l'animation CSS de
   montage.css (une règle par famille, la direction en variable). */
function DzmTransGrid(o){
  var lst=dzmTransList(o&&o.legacy,o&&o.cat),cur=o&&o.cur,on=typeof (o&&o.onPick)==="function"?o.onPick:function(){};
  return lst.map(function(f){
    return r.jsxs("div",{className:"dzm-transfam",children:[
      r.jsx("div",{className:"dzm-transfam-t",children:f.label}),
      r.jsx("div",{className:"svm-transgrid dzm-transgrid",children:f.items.map(function(it){
        var fam=dzmTransFamily(it.id,o&&o.cat),dir=dzmTransDir(it.id);
        return r.jsxs("button",{className:"svm-transtile","data-sel":cur===it.id?"":void 0,
          title:it.label+" ("+it.id+")"+(it.live?"":" — visible après Preview"),
          onClick:function(){on(it.id)},children:[
          r.jsxs("span",{className:"svm-tprev","data-tt":it.id,"data-fam":fam,"data-dir":dir||void 0,"aria-hidden":!0,
            children:[r.jsx("i",{className:"svm-ta"}),r.jsx("i",{className:"svm-tb"})]}),
          r.jsx("span",{className:"svm-ttl",children:it.label})]},it.id)})})]},f.id)})}
```

Exports : `transList:dzmTransList,transLabel:dzmTransLabel,transFamily:dzmTransFamily,transLive:dzmTransLive,transDir:dzmTransDir,TransGrid:DzmTransGrid,TRANS_FAM:Object.freeze(DZM_TRANS_FAM),`.

CSS (`montage.css`) — six animations de famille, la direction par variable ; les sept règles `[data-tt]` du bundle gardent la priorité pour les 7 historiques (spécificité égale, mais `montage.css` est chargée APRÈS : préfixer les nôtres par `.svm-tprev[data-fam]:not([data-tt="cut"])…` et mesurer qu'un `fade` historique garde son animation) :

```css
/* D-20 — aperçu animé des 58 transitions : une animation par FAMILLE, la
   direction en variable (--tx/--ty). Les sept historiques gardent leurs
   règles [data-tt] de son-vfx-montage.css (intouchable). */
.dzsvm .dzm-transfam{margin-top:8px}
.dzsvm .dzm-transfam-t{font-family:var(--f-mono);font-size:10px;color:var(--ink2);text-transform:uppercase;letter-spacing:.06em;margin:6px 0 2px}
.dzsvm .dzm-transgrid{grid-template-columns:repeat(3,1fr)}
.dzsvm .svm-tprev[data-dir="left"]{--tx:-100%;--ty:0}
.dzsvm .svm-tprev[data-dir="right"]{--tx:100%;--ty:0}
.dzsvm .svm-tprev[data-dir="up"]{--tx:0;--ty:-100%}
.dzsvm .svm-tprev[data-dir="down"]{--tx:0;--ty:100%}
.dzsvm .svm-tprev[data-fam="fondus"] .svm-tb{animation:svmtFull 1.6s linear infinite,svmtFade 1.6s linear infinite}
.dzsvm .svm-tprev[data-fam="glissements"] .svm-tb{animation:svmtFull 1.6s linear infinite,dzmtSlideDir 1.6s var(--ease) infinite}
.dzsvm .svm-tprev[data-fam="volets"] .svm-tb{animation:svmtFull 1.6s linear infinite,dzmtWipeDir 1.6s linear infinite}
.dzsvm .svm-tprev[data-fam="formes"] .svm-tb{animation:svmtFull 1.6s linear infinite,dzmtCircle 1.6s linear infinite}
.dzsvm .svm-tprev[data-fam="zooms"] .svm-tb{animation:svmtFull 1.6s linear infinite,dzmtZoom 1.6s var(--ease) infinite}
.dzsvm .svm-tprev[data-fam="pixels"] .svm-tb{animation:svmtFull 1.6s linear infinite,svmtGlitch 1.6s steps(2,end) infinite}
@keyframes dzmtSlideDir{0%,20%{transform:translate(var(--tx,100%),var(--ty,0))}60%,100%{transform:translate(0,0)}}
@keyframes dzmtWipeDir{0%,20%{clip-path:inset(0 0 0 100%)}60%,100%{clip-path:inset(0)}}
@keyframes dzmtCircle{0%,20%{clip-path:circle(0% at 50% 50%)}60%,100%{clip-path:circle(75% at 50% 50%)}}
@keyframes dzmtZoom{0%,20%{transform:scale(.2);opacity:0}60%,100%{transform:scale(1);opacity:1}}
```

Mesure que `svmtFull`, `svmtFade`, `svmtGlitch`, `--ease` existent dans `son-vfx-montage.css` (grep) — sinon les redéclarer dans `montage.css` sous des noms `dzmt*`.

- [ ] **Étape 3 : sections.** MESURE d'abord chaque ancre (`--check --force-unchained`) :

```python
# ── X1 (D-20) : le catalogue est chargé une fois, à côté des refs (REPLI R_M16REF) ──
# ajouter DANS R_M16REF, après la déclaration de dzModeRef :
#   var stDzCat=x.useState(null),dzTransCat=stDzCat[0],setDzTransCat=stDzCat[1];
#   x.useEffect(function(){var al=!0;fetch("/api/montage/transitions").then(function(r){return r.ok?r.json():null})
#     .then(function(d){if(al&&d&&Array.isArray(d.familles))setDzTransCat(d)}).catch(function(){});return function(){al=!1}},[]);
# ── X2 (D-20) : la grille du popover devient la galerie par familles ─────────
A_X2 = '      r.jsx("div",{className:"svm-transgrid",children:SVM_TRANS.map(function(o){'
# Le remplacement REMPLACE toute la grille : de A_X2 jusqu'à la fin de la tuile
# (mesurer la fin exacte : `r.jsx("span",{className:"svm-ttl",children:o[1]})]},o[0])})}),`)
# → 'r.jsx(DzTracks.TransGrid,{legacy:SVM_TRANS,cat:dzTransCat,cur:base,onPick:function(id){svmSetTransType(jc.id,id)}}),'
# ── X3 (D-20) : le <select> de l'inspecteur liste tout le catalogue ────────────
A_X3 = '            .concat(SVM_TRANS.map(function(o){'
# → '.concat(DzTracks.transList(SVM_TRANS,dzTransCat).reduce(function(a,f){return a.concat(f.items.map(function(it){return r.jsx("option",{value:it.id,children:f.label+" · "+it.label},it.id)}))},[])' 
# en gardant `known` qui doit devenir : var known=DzTracks.transList(SVM_TRANS,dzTransCat).some(function(f){return f.items.some(function(it){return it.id===base})});
# (ancre `var known=SVM_TRANS.some(function(o){return o[0]===base});` : mesurer 1/1)
# ── X4 (D-20) : le libellé sur le losange et l'étendue vient du catalogue ─────
A_X4 = '  var f=SVM_TRANS.find(function(o){return o[0]===b});return f?f[1]:b}'
R_X4 = '  return DzTracks.transLabel(b,SVM_TRANS,window.__dzTransCat||null)}'
# svmTransLabel est au niveau MODULE (hors composant) : le catalogue lui parvient
# par window.__dzTransCat, posé dans l'effet de X1 (setDzTransCat(d);window.__dzTransCat=d).
```

Toute ancre qui ne vaut pas 1/1 dans le `.bak` se replie ou se re-mesure ; les sections X2/X3/X4 vont en queue de `PATCHES`. Le popover fait 300 px (`.svm-pop`) : la grille à 3 colonnes de 58 tuiles fait ~20 rangées — ajouter `max-height:52vh;overflow:auto` sur `.svm-transpop` via `montage.css` (`.dzsvm .svm-transpop{max-height:52vh;overflow:auto}`) et mesurer que le popover reste dans le cadre.

- [ ] **Étape 4 : bancs.** Bundle : pins `D20_X2_la_grille_est_la_galerie` (`DzTracks.TransGrid` ×1, `svm-transgrid",children:SVM_TRANS.map` ×0), `D20_X3_le_select_liste_le_catalogue`, `D20_X4_le_libelle_vient_du_catalogue`, `D20_X1_le_catalogue_est_charge_une_fois` (repli R_M16REF, 0 dans le .bak), un rendu de `DzmTransGrid` avec le stub JSX (58 + 1 + historiques tuiles, `data-fam` posé, `data-sel` sur `cur`), CSS présente ; sonde dzcout remesurée (+4 : `TransGrid`, `transList` ×2, `transLabel`). Édition `[5]` vert.

- [ ] **Étape 5 : rejouer, bancs, commit.** Preuve à l'écran par le contrôleur : clic sur un losange → galerie par familles, choisir `wipetl` → losange titré « volet ↖ », Preview 480p rend le volet. Commit `montage : D-20 - galerie des transitions par familles, apercu anime, catalogue servi`.

---

## Tâche 3 — D-12 : les fondus simples joués en direct (voile CSS)

**Files :** `frontend/patches/montage.js` (`dzmVeil`), `scripts/patch_bundle_montage.py` (V1 repli R_M16REF, V2, V3), `frontend/dist/shared/montage.css`, `test_montage_edition.py` ([5] suite), `test_montage_bundle.py`.

- [ ] **Étape 1 : banc rouge** (PROBE `[5]` suite) :

```javascript
/* D-12 : le voile du lecteur vivant */
var VC=[{tr:"v1",id:"a",start:0,end:4,src:{job_id:"j"}},{tr:"v1",id:"b",start:4,end:8,src:{job_id:"j"},transition:"fadeblack",transition_s:1},
        {tr:"v1",id:"c",start:8,end:12,src:{job_id:"j"},transition:"pixelize",transition_s:.5},{tr:"v1",id:"d",start:12,end:16,src:{job_id:"j"},transition:"fadewhite",transition_s:.4}];
out.vl_loin=T.veil(VC,2);                                  /* {color:null,alpha:0} */
out.vl_milieu=T.veil(VC,4);                                /* fadeblack : au raccord, alpha 1 */
out.vl_avant=T.veil(VC,3.75);                              /* moitié de la montée : .5 */
out.vl_apres=T.veil(VC,4.25);                              /* moitié de la descente : .5 */
out.vl_pixel=T.veil(VC,8);                                 /* pas jouable en direct : 0 */
out.vl_blanc=T.veil(VC,12).color;                          /* "#fff" */
out.vl_fade=T.veil([{tr:"v1",id:"a",start:0,end:4,src:{job_id:"j"}},{tr:"v1",id:"b",start:4,end:8,src:{job_id:"j"},transition:"fade",transition_s:.4}],4);  /* fade = baisse d'opacité : color "dim" */
out.vl_premier=T.veil([{tr:"v1",id:"b",start:0,end:8,src:{job_id:"j"},transition:"fadeblack",transition_s:1}],0);  /* premier clip : rien */
out.vl_mou=[T.veil(null,1).alpha,T.veil(VC,NaN).alpha];
```

Python : `vl_loin == {"color": None, "alpha": 0}` ; `vl_milieu == {"color":"#000","alpha":1}` ; `vl_avant["alpha"] == 0.5` et `vl_apres["alpha"] == 0.5` ; `vl_pixel["alpha"] == 0` (clé présente) ; `vl_blanc == "#fff"` ; `vl_fade == {"color":"dim","alpha":1}` ; `vl_premier["alpha"] == 0` ; `vl_mou == [0, 0]`. Règle : la transition du clip de droite `b` (jonction `t0=b.start`, durée `s=svmTransS` bornée 0,1–1) donne un voile triangulaire sur `[t0−s/2, t0+s/2]` : alpha monte de 0 à 1 puis redescend ; `fadeblack` → `#000`, `fadewhite` → `#fff`, `fade` → `"dim"` (le lecteur baisse l'opacité de l'hôte au lieu de poser un voile) ; tout autre nom → 0 ; premier clip (pas de voisin gauche à ≤ 0,1 s) → 0.

- [ ] **Étape 2 : implémenter** :

```javascript
/* ── D-12 (21/09/2026) : LES FONDUS SIMPLES EN DIRECT ─────────────────────
   Le lecteur vivant n'a qu'un clip visible à la fois (svmActiveV1) : un
   vrai crossfade A/B demanderait deux hôtes. Un VOILE suffit pour les trois
   fondus que Resolve montre en lecture : noir, blanc, et le fondu simple
   (baisse d'opacité de l'hôte). Le rendu ffmpeg fait foi pour le reste. */
var DZM_VEIL={fadeblack:"#000",fadewhite:"#fff",fade:"dim"};
function dzmVeil(clips,t){
  var cs=Array.isArray(clips)?clips:[],v=Number(t),i,c,k,best=null;
  if(!isFinite(v))return {color:null,alpha:0};
  for(i=0;i<cs.length;i++){c=cs[i];if(!c||c.tr!=="v1"||!c.src)continue;
    k=String(c.transition||"cut").split(/\s+/)[0];if(!DZM_VEIL[k])continue;
    var s=Math.min(1,Math.max(.1,Number(c.transition_s)||.4)),t0=Number(c.start)||0;
    if(Math.abs(v-t0)>s/2)continue;
    var g=dzmVoisins(cs,c).g;if(!g)continue;
    var a=dzmR3(1-Math.abs(v-t0)/(s/2));
    if(!best||a>best.alpha)best={color:DZM_VEIL[k],alpha:a}}
  return best||{color:null,alpha:0}}
```

Export `veil:dzmVeil,VEIL:Object.freeze(DZM_VEIL),`. CSS : `.dzsvm .svm-xfveil{position:absolute;inset:0;pointer-events:none;z-index:6;opacity:0;background:#000}`.

- [ ] **Étape 3 : sections.** V1 (repli R_M16REF) : `var dzVeilRef=x.useRef(null);`. V2 (ancre `liveOn&&!liveClip?r.jsx("div",{className:"svm-livegap",children:"trou"}):null,` 1/1) → ajouter avant : `liveOn?r.jsx("i",{className:"svm-xfveil",ref:dzVeilRef,"aria-hidden":!0}):null,`. V3 (ancre `  function liveSync(){` 1/1) → insérer en TÊTE du corps : `var dzVe=dzVeilRef.current;if(dzVe){var dzVv=DzTracks.veil(clipsRef.current,phRef.current);dzVe.style.background=dzVv.color==="dim"?"transparent":(dzVv.color||"#000");dzVe.style.opacity=dzVv.color==="dim"?"0":String(dzVv.alpha);var dzH=liveHostRef.current;if(dzH)dzH.style.opacity=dzVv.color==="dim"?String(1-dzVv.alpha):""}` — MESURER que `liveSync` ne réécrit pas `liveHostRef.current.style.opacity` plus bas (grep dans son corps) ; sinon poser l'opacité sur l'élément média du pool (`liveVideoRef.current`) et le dire.

- [ ] **Étape 4 : bancs, rejeu, sonde (+1 `DzTracks.veil`), commit** `montage : D-12 - fondus noir, blanc et simple joues en direct par un voile`. Preuve à l'écran : projet réel, transition `fadeblack` 1 s sur le second clip, tête à la jonction → `.svm-xfveil` opacité 1 ; à ±0,25 s → 0,5.

---

## Tâche 4 — D-21 backend : `titles.py`, huit gabarits ASS, mesure à l'image

**Files :** créer `backend/app/services/titles.py` ; `backend/tests/test_montage_l2.py` ([2]).

- [ ] **Étape 1 : banc rouge** (`test_montage_l2.py` `[2]`) :

```python
print("\n[2] D-21 titles.py : huit gabarits ASS dans la charte")
from app.services import titles as TI
check("d21_huit_gabarits_dans_l_ordre",
      list(TI.TEMPLATES) == ["plein_cadre", "tiers_inferieur", "legende", "compteur", "chapitre", "citation", "hashtag", "cta"])
spec = TI.title_spec({"tr": "t1", "id": "x", "start": 2, "end": 6,
                      "title": {"template": "tiers_inferieur", "text": "Abysse", "sub": "épisode 3"}})
check("d21_le_spec_est_assaini", spec.get("template") == "tiers_inferieur" and spec.get("text") == "Abysse"
      and spec.get("sub") == "épisode 3" and spec.get("start") == 2.0 and spec.get("end") == 6.0, spec)
check("d21_un_gabarit_inconnu_retombe_sur_plein_cadre",
      TI.title_spec({"title": {"template": "zzz", "text": "t"}, "start": 0, "end": 1}).get("template") == "plein_cadre")
check("d21_sans_texte_pas_de_titre", TI.title_spec({"title": {"template": "cta"}, "start": 0, "end": 1}) is None)
p = TI.to_ass_title(spec, (1080, 1920), "t_banc")
txt = p.read_text(encoding="utf-8") if p and p.is_file() else ""
check("d21_le_fichier_ass_existe_sans_bom", bool(txt) and not p.read_bytes().startswith(b"\xef\xbb\xbf"), str(p))
check("d21_la_fonte_est_embarquee_par_son_nom_de_famille", ",Bebas Neue," in txt and "PlayResX: 1080" in txt, txt[:300])
check("d21_deux_evenements_titre_et_sous_texte", txt.count("Dialogue:") == 2)
check("d21_l_animation_d_entree_et_de_sortie_est_ecrite", "\\fad(" in txt and ("\\move(" in txt or "\\t(" in txt))
check("d21_les_bornes_sont_celles_du_clip", "0:00:02.00" in txt and "0:00:06.00" in txt, txt[-300:])
check("d21_la_couleur_or_de_la_charte_en_bgr", "&H003CB2E6" in txt)
# MESURE À L'IMAGE : ffmpeg grave le .ass sur un fond uni 1080×1920 à t=3 s ; PIL mesure
# la bande 70–90 % (tiers inférieur) → des pixels clairs, et le haut 0–20 % → aucun.
png = TI.render_title_png(spec, 540, 960, t=3.0)   # PNG via ffmpeg (color=c=#14181d + subtitles=)
from PIL import Image
im = Image.open(png).convert("L") if png and png.is_file() else None
def clairs(im, y0, y1):
    if im is None: return -1
    w, h = im.size; box = im.crop((0, int(h*y0), w, int(h*y1)))
    return sum(1 for v in box.getdata() if v > 150)
check("d21_le_tiers_inferieur_porte_du_texte_et_le_haut_rien",
      im is not None and clairs(im, .70, .90) > 150 and clairs(im, 0, .20) < 20,
      (clairs(im, .70, .90), clairs(im, 0, .20)))
spec2 = TI.title_spec({"title": {"template": "plein_cadre", "text": "GRAND TITRE"}, "start": 0, "end": 3})
png2 = TI.render_title_png(spec2, 540, 960, t=1.5)
im2 = Image.open(png2).convert("L") if png2 and png2.is_file() else None
check("d21_le_plein_cadre_est_centre", im2 is not None and clairs(im2, .40, .60) > 300 and clairs(im2, 0, .15) < 20)
check("d21_chaque_gabarit_produit_un_ass_valide",
      all(TI.to_ass_title(TI.title_spec({"title": {"template": k, "text": "x", "sub": "y"}, "start": 0, "end": 2}), (1920, 1080), "t_" + k).is_file()
          for k in TI.TEMPLATES))
```

- [ ] **Étape 2 : implémenter `backend/app/services/titles.py`** :

```python
"""D-21 (21/09/2026) — CLIPS TITRE : huit gabarits animés dans la charte, rendus
en ASS par le MÊME moteur que les sous-titres (libass, fontes embarquées).
Pas de style par caractère, pas de 3D : c'est de l'ASS, pas du Fusion.

Un clip titre est `{tr:"t1", kind:"title", start, end, title:{template, text,
sub?, color?, font?, size?, pos?}}` — SANS `src` : _resolve_src ne le voit
jamais, POST /save et GET /project le gardent tels quels (mesuré le 21/09).
"""
from __future__ import annotations
import hashlib, json, math, subprocess
from pathlib import Path
from app.config import settings
from app.services import subtitle_service as S

BRAND = {"or": "#e6b23c", "cyan": "#00e5ff", "encre": "#14181d", "blanc": "#eef2f6", "rouge": "#e5484d"}

# gabarit → police (nom de FAMILLE de FONT_FILES), taille à 1080 p, couleur,
# boîte, ancrage \an, y relatif, entrée/sortie (ms), tags d'animation
TEMPLATES = {
    "plein_cadre":     {"font": "Anton",      "size": 120, "color": "or",    "box": None,    "an": 5, "y": .50, "in": 300, "out": 300,
                        "anim": "\\fscx80\\fscy80\\t(0,{in},\\fscx100\\fscy100)"},
    "tiers_inferieur": {"font": "Bebas Neue", "size": 64,  "color": "blanc", "box": "or",    "an": 1, "y": .80, "in": 260, "out": 200,
                        "anim": "\\move({x0},{y},{x1},{y},0,{in})"},
    "legende":         {"font": "Inter",      "size": 40,  "color": "blanc", "box": "encre", "an": 2, "y": .90, "in": 200, "out": 200, "anim": ""},
    "compteur":        {"font": "JetBrains Mono", "size": 96, "color": "cyan", "box": None, "an": 5, "y": .50, "in": 120, "out": 120,
                        "anim": "\\fscx140\\fscy140\\t(0,{in},\\fscx100\\fscy100)"},
    "chapitre":        {"font": "Cinzel",     "size": 80,  "color": "blanc", "box": None,    "an": 4, "y": .50, "in": 400, "out": 300,
                        "anim": "\\move({x0},{y},{x1},{y},0,{in})"},
    "citation":        {"font": "Abril Fatface", "size": 56, "color": "blanc", "box": None, "an": 5, "y": .45, "in": 500, "out": 400, "anim": ""},
    "hashtag":         {"font": "Bungee",     "size": 72,  "color": "or",    "box": "encre", "an": 3, "y": .12, "in": 200, "out": 200,
                        "anim": "\\fscx60\\fscy60\\t(0,{in},\\fscx100\\fscy100)"},
    "cta":             {"font": "Archivo Black", "size": 68, "color": "encre", "box": "or", "an": 5, "y": .85, "in": 220, "out": 220,
                        "anim": "\\fscx90\\fscy90\\t(0,{in},\\fscx105\\fscy105)\\t({in},{in2},\\fscx100\\fscy100)"},
}
DEFAULT_TEMPLATE = "plein_cadre"
MAX_TEXT = 120
MAX_SUB = 160


def _num(v, d=0.0):
    try:
        f = float(v)
        return f if math.isfinite(f) else d
    except (TypeError, ValueError):
        return d


def title_spec(clip: dict) -> dict | None:
    """Assainit un clip titre → spec, ou None s'il n'y a rien à écrire."""
    if not isinstance(clip, dict):
        return None
    t = clip.get("title") if isinstance(clip.get("title"), dict) else {}
    text = str(t.get("text") or "").strip()[:MAX_TEXT]
    if not text:
        return None
    tpl = str(t.get("template") or DEFAULT_TEMPLATE)
    if tpl not in TEMPLATES:
        tpl = DEFAULT_TEMPLATE
    start, end = round(_num(clip.get("start")), 3), round(_num(clip.get("end")), 3)
    if end <= start:
        return None
    color = str(t.get("color") or TEMPLATES[tpl]["color"])
    if color not in BRAND:
        color = TEMPLATES[tpl]["color"]
    font = str(t.get("font") or TEMPLATES[tpl]["font"])
    if font not in S.FONT_FILES:
        font = TEMPLATES[tpl]["font"]
    size = int(max(24, min(200, _num(t.get("size"), TEMPLATES[tpl]["size"]))))
    return {"template": tpl, "text": text, "sub": str(t.get("sub") or "").strip()[:MAX_SUB],
            "color": color, "font": font, "size": size, "start": start, "end": end}


def _bgr(hexrgb: str) -> str:
    h = hexrgb.lstrip("#")
    return "&H00%s%s%s" % (h[4:6].upper(), h[2:4].upper(), h[0:2].upper())


def _ass_text(spec: dict, canvas: tuple[int, int]) -> str:
    W, H = canvas
    tpl = TEMPLATES[spec["template"]]
    scale = H / S.REF_HEIGHT
    size = int(round(spec["size"] * scale))
    subsize = max(20, int(round(size * .45)))
    color = _bgr(BRAND[spec["color"]])
    back = "&H60%s" % _bgr(BRAND[tpl["box"]])[4:] if tpl["box"] else "&H80000000"
    bs = 3 if tpl["box"] else 1
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
             "WrapStyle: 2", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
             "[V4+ Styles]", S._ASS_FORMAT_STYLE,
             f"Style: DzT,{spec['font']},{size},{color},{color},&H00000000,{back},0,0,0,0,100,100,0,0,{bs},2,0,{tpl['an']},40,40,40,1",
             f"Style: DzS,{spec['font']},{subsize},{_bgr(BRAND['blanc'])},{_bgr(BRAND['blanc'])},&H00000000,{back},0,0,0,0,100,100,0,0,{bs},2,0,{tpl['an']},40,40,40,1",
             "", "[Events]", S._ASS_FORMAT_EVENT]
    dur_ms = int(round((spec["end"] - spec["start"]) * 1000))
    fin = min(tpl["in"], max(0, dur_ms // 3)); fout = min(tpl["out"], max(0, dur_ms // 3))
    y = int(round(H * tpl["y"]))
    xa = {1: 40, 4: 40, 7: 40, 2: W // 2, 5: W // 2, 8: W // 2, 3: W - 40, 6: W - 40, 9: W - 40}[tpl["an"]]
    anim = tpl["anim"].format(**{"in": fin, "in2": fin * 2, "y": y, "x0": xa - int(W * .15), "x1": xa})
    pre = "{\\an%d\\pos(%d,%d)\\fad(%d,%d)%s}" % (tpl["an"], xa, y, fin, fout, anim)
    t0, t1 = S._ass_time(spec["start"]), S._ass_time(spec["end"])
    lines.append(f"Dialogue: 0,{t0},{t1},DzT,,0,0,0,,{pre}{S._ass_escape(spec['text'])}")
    if spec["sub"]:
        ysub = y + int(round(size * 1.05)) if tpl["an"] in (7, 8, 9, 4, 5, 6) else y + int(round(size * .1))
        pre2 = "{\\an%d\\pos(%d,%d)\\fad(%d,%d)}" % (tpl["an"], xa, ysub, fin, fout)
        lines.append(f"Dialogue: 1,{t0},{t1},DzS,,0,0,0,,{pre2}{S._ass_escape(spec['sub'])}")
    return "\n".join(lines) + "\n"


def to_ass_title(spec: dict, canvas: tuple[int, int], stem: str) -> Path | None:
    if not spec:
        return None
    out_dir = settings.outputs_path / "subtitles"
    out_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(json.dumps([spec, canvas, 1], sort_keys=True).encode()).hexdigest()[:10]
    p = out_dir / f"title_{stem}_{key}.ass"
    p.write_bytes(_ass_text(spec, canvas).encode("utf-8"))     # UTF-8 SANS BOM (libass)
    return p


def render_title_png(spec: dict, w: int, h: int, t: float = 1.0) -> Path | None:
    """Aperçu : le titre gravé sur un fond uni, une image à t (ffmpeg). Cache
    par clé, même verrou/motif tmp→replace que effects_preview."""
    from app.services.effects_preview import ffmpeg_bin, cache_dir   # mesurer les noms réels
    from app.services.subtitle_service import subtitles_filter
    ass = to_ass_title(spec, (w, h), "prev")
    if not ass:
        return None
    key = hashlib.sha1(json.dumps([spec, w, h, round(t, 2), 1], sort_keys=True).encode()).hexdigest()[:24]
    out = cache_dir() / f"tt_{key}.png"
    if out.is_file():
        return out
    tmp = out.with_suffix(".tmp.png")
    cmd = [ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={BRAND['encre']}:s={w}x{h}:r=25:d={t+0.5}",
           "-vf", subtitles_filter(str(ass)), "-ss", str(t), "-frames:v", "1", "-update", "1", str(tmp)]
    subprocess.run(cmd, check=False, capture_output=True, timeout=60)
    if tmp.is_file():
        tmp.replace(out)
        return out
    return None
```

Les noms `ffmpeg_bin`/`cache_dir` de `effects_preview.py` sont à MESURER (le rapport dit « `shutil.which("ffmpeg")` repli `%LOCALAPPDATA%\…\bin\ffmpeg.exe` », `settings.outputs_path / "fxpreview"`) : réutiliser les fonctions existantes ou recopier leurs deux lignes en le disant. Le nom de famille des 16 fontes : vérifier par `PIL.ImageFont.truetype(...).getname()` que `"Bebas Neue"`, `"Anton"`, `"Cinzel"`, `"Abril Fatface"`, `"Bungee"`, `"Archivo Black"`, `"JetBrains Mono"`, `"Inter"` sont bien les clés de `FONT_FILES` (ils le sont d'après `subtitle_service.py:96-113`).

- [ ] **Étape 3 : lancer → vert (mesure PIL comprise ; si la bande 70–90 % ne dépasse pas 150 pixels clairs, c'est l'ancrage `\an1` + `y` qu'il faut corriger, pas le seuil). Commit** `montage : D-21 - titles.py, huit gabarits ASS mesures a l image`.

---

## Tâche 5 — D-21 backend : la piste `t1`, la gravure, l'aperçu

**Files :** `montage_service.py` (`_tracks_meta`, collecte, `_build_montage_command(..., titles_ass=None)`, `GET /title-preview`, `GET /titles`), `test_montage_l2.py` ([3]).

- [ ] **Étape 1 : banc rouge** (`[3]`) — via `TestClient` et le générateur de commande :

```python
print("\n[3] D-21 la piste t1 est gravee avant S1")
meta = MS._tracks_meta([{"id": "v1", "kind": "video"}, {"id": "t1", "kind": "title"}, {"id": "s1", "kind": "subs"}])
check("d21_tracks_meta_declare_le_genre_title", (meta.get("t1") or {}).get("kind") == "title", meta.get("t1"))
tl = TL("titres", n=2); tl["tracks"] = [{"id": "v1", "kind": "video"}, {"id": "t1", "kind": "title"}]
tl["clips"].append({"tr": "t1", "id": "tt1", "kind": "title", "start": 1, "end": 3,
                    "title": {"template": "tiers_inferieur", "text": "Abysse", "sub": "ep. 3"}})
r = c.post("/api/montage/save", json=tl); cur_ = J(c.get("/api/montage/project"))
check("d21_le_clip_titre_survit_a_la_sauvegarde",
      r.status_code == 200 and any(k.get("tr") == "t1" and (k.get("title") or {}).get("text") == "Abysse" for k in cur_.get("clips", [])),
      str(cur_.get("clips"))[:200])
# la commande de rendu : _build_montage_command reçoit titles_ass et chaîne [tt0] AVANT subtitles S1
cmd = MS._build_montage_command([{"path": V1, "start": 0, "end": 4, "srcIn": 0}], [], [], None, w=540, h=960, fps=25,
                                mix_db={}, ducking=False, duration_master=4, preview=True, out=os.path.join(TMP, "o.mp4"),
                                titles_ass=[os.path.join(TMP, "t.ass")], subs_ass=os.path.join(TMP, "s.ass"))
fc = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
i_t, i_s = fc.find("t.ass"), fc.find("s.ass")
check("d21_le_titre_est_grave_avant_les_sous_titres", 0 <= i_t < i_s and "[tt0]" in fc, (i_t, i_s))
cmd0 = MS._build_montage_command([{"path": V1, "start": 0, "end": 4, "srcIn": 0}], [], [], None, w=540, h=960, fps=25,
                                 mix_db={}, ducking=False, duration_master=4, preview=True, out=os.path.join(TMP, "o.mp4"))
check("d21_sans_titre_la_commande_est_intacte", "tt0" not in (" ".join(cmd0) if isinstance(cmd0, list) else str(cmd0)))
r = c.get("/api/montage/titles"); d = J(r)
check("d21_la_route_titles_liste_les_huit_gabarits", r.status_code == 200 and [g.get("id") for g in d.get("gabarits", [])] == list(TI.TEMPLATES))
r = c.get("/api/montage/title-preview", params={"template": "cta", "text": "Abonnez-vous", "w": 270})
check("d21_l_apercu_est_un_png", r.status_code == 200 and r.headers.get("content-type", "").startswith("image/png") and len(r.content) > 500)
r = c.get("/api/montage/title-preview", params={"template": "cta", "text": ""})
check("d21_l_apercu_sans_texte_est_un_400", r.status_code == 400)
```

La signature réelle de `_build_montage_command` (`v1, v2, a_clips, music, *, w, h, fps, mix_db, ducking, duration_master, preview, out, audio_only=False, subs_ass=None`) et la forme de `v1` (liste de dicts avec `path`) sont à MESURER sur un appel existant du banc `test_montage_pistes_rendu.py` : recopier le plus petit appel vert qui s'y trouve.

- [ ] **Étape 2 : implémenter.** (a) `_build_montage_command(..., subs_ass=None, titles_ass=None)` : juste avant le bloc `if subs_ass:` (`:2332`) :

```python
    # D-21 — les titres, chaînés AVANT S1 (les sous-titres restent le dernier
    # maillon) : un .ass par clip titre, gravé par le même filtre.
    for j, tpath in enumerate(titles_ass or []):
        from app.services.subtitle_service import subtitles_filter
        parts.append(f"[{cur}]{subtitles_filter(tpath)}[tt{j}]")
        cur = f"tt{j}"
```

(b) dans le rendu (`montage_render`, autour de `:2737`), après la collecte des overlays : `titles = [TI.title_spec(c) for c in clips if (meta.get(c.get("tr")) or {}).get("kind") == "title"]` → `titles_ass = [str(TI.to_ass_title(s, (w, h), f"montage_{short}_{i}")) for i, s in enumerate(t for t in titles if t)]` et passer `titles_ass=titles_ass` ; (c) `_tracks_meta` : rien à changer (accepte `title`), mais AJOUTER `title` au commentaire des genres et un `layer` nul ; (d) routes `GET /titles` (`{"gabarits":[{"id","label","font","anim":"…"}]}`, libellés français : plein cadre, tiers inférieur, légende, compteur, chapitre, citation, hashtag, appel à l'action) et `GET /title-preview?template&text&sub&color&w` → `FileResponse` PNG (`w` borné 96–640, hauteur = `w×16/9` pour un aperçu vertical ; 400 si texte vide) ; (e) le pré-vol P8 (`:2571`) ignore déjà les clips sans `src` — laisser.

- [ ] **Étape 3 : vert, `test_montage_projets.py` 159/0, `test_montage_pistes_rendu.py` inchangé, commit** `montage : D-21 - piste t1 gravee avant S1, routes titles et title-preview`.

---

## Tâche 6 — D-21 client : le genre `title`, la piste `t1`, poser un titre

**Files :** `frontend/patches/montage.js`, `scripts/patch_bundle_montage.py` (TT1…TT4 + replis R_M5, R_M7, R_R1, R_R2, R_K5), `test_montage_edition.py` ([6]), `test_montage_bundle.py`, `patch_bundle_dzcout.py`.

- [ ] **Étape 1 : banc rouge** (`[6]`) :

```javascript
/* [6] D-21 : la piste t1 et le clip titre */
out.tt_defaut=T.DEFAULTS.some(function(t){return t.id==="t1"&&t.kind==="title"});
out.tt_ensure=T.titleTrack([{id:"v1",kind:"video"},{id:"a1",kind:"audio"}]).map(function(t){return t.id});   /* t1 inséré AU-DESSUS de v1 */
out.tt_ensure_deja=T.titleTrack([{id:"t1",kind:"title"},{id:"v1",kind:"video"}]).length;
out.tt_group=[T.group({id:"t1",kind:"title"}),T.group({id:"v1",kind:"video"}),T.group({id:"s1",kind:"subs"})];
out.tt_pick=T.pickTrack([{id:"v1",kind:"video"},{id:"t1",kind:"title"}],"title");
var TN=T.titleNew({template:"cta",text:"Abonnez-vous"},4,[],"t1");
out.tt_new=[TN.tr,TN.kind,TN.start,TN.end,TN.title.template,TN.title.text,"src" in TN];
out.tt_new_sans_texte=T.titleNew({template:"cta",text:"  "},4,[],"t1");
out.tt_new_id_unique=T.titleNew({text:"a"},0,[{id:"t1u1"}],"t1").id!=="t1u1";
out.tt_at=T.titleAt([{tr:"t1",kind:"title",start:1,end:3,title:{text:"x"}},{tr:"v1",start:0,end:9,src:{a:1}}],2)&&T.titleAt([{tr:"t1",kind:"title",start:1,end:3,title:{text:"x"}}],5);
out.tt_html=T.titleHtml({tr:"t1",kind:"title",start:0,end:4,title:{template:"tiers_inferieur",text:"<b>Ab",sub:"ép"}},1);
out.tt_remove=T.removeTrack([{id:"t1",kind:"title"},{id:"v1",kind:"video"}],"t1").length;
```

Python : `tt_defaut is True` ; `tt_ensure == ["t1","v1","a1"]` ; `tt_ensure_deja == 2` ; `tt_group == [0, 1, 3]` ; `tt_pick == "t1"` ; `tt_new == ["t1","title",4,8,"cta","Abonnez-vous",False]` (durée par défaut 4 s = `DZM_CLIP_DEFAUTS.image`) ; `tt_new_sans_texte is None` (clé présente) ; `tt_new_id_unique is True` ; `tt_at` = `[True, False]` (renvoyer `!!` des deux) ; `tt_html` contient `&lt;b&gt;Ab` (échappé), `dzm-tt-tiers_inferieur`, `ép` ; `tt_remove == 1` (t1 SE RETIRE, contrairement à s1 — un montage sans titre n'a pas besoin de la piste ; `titleNew` la recrée par `titleTrack`).

- [ ] **Étape 2 : implémenter** : `DZM_DEFAULT_TRACKS` gagne `{id:"t1",name:"T1",type:"titres",h:40,c:"--c-text",mix:11,kind:"title"}` EN TÊTE (au-dessus de v2) ; `dzmKindOf`/`dzmSkin`/`dzmPickTrack`/`dzmGroup` reconnaissent `title` (`want="title"`, groupe 0) ; `dzmTitleTrack(ts)` insère `t1` en tête s'il manque ; `dzmTitleNew(title, t, clips, tr)` → clip `{tr,kind:"title",id:dzmUniqueId(clips,"t1u…"),label:text[:24],start:t,end:t+4,title:{template,text,sub,color,font,size}}` ou `null` sans texte ; `dzmTitleAt(clips,t)` → le clip titre sous `t` ou `null` ; `dzmTitleHtml(clip,t)` → chaîne HTML échappée (`<div class="dzm-tt dzm-tt-<template>"><b>texte</b><i>sub</i></div>`) pour l'aperçu vivant ; exports `titleTrack, titleNew, titleAt, titleHtml, group:dzmGroup, pickTrack:dzmPickTrack, removeTrack:dzmRemove` (vérifier les exports existants : ne pas dupliquer).

- [ ] **Étape 3 : sections** (MESURER chaque ancre) :
  - TT1 (ancre `  function trackKind(trId){var k=String(trId||"").charAt(0);` 1/1) → `return k==="a"?"audio":k==="s"?"subs":k==="t"?"title":"video"}` (les 16 sites du bloc sonvfx refusent alors `t1` comme ils refusent `s1` : dépôt, pile d'effets, mixage — c'est la recette écrite au-dessus de `trackKind`). Vérifier qu'aucun id existant ne commence par `t` (grep `id:"t` dans le bundle et `DZM_DEFAULT_TRACKS`).
  - TT2 REPLI R_M5 : `clips:clips.filter(function(c){return c.src||c.kind==="title"}).map(function(c){` + dans l'objet sérialisé `o`, ajouter `kind:c.kind,title:c.title` (mesurer la ligne `var o={tr:c.tr,src:c.src,…` de R_M5 et l'étendre).
  - TT3 REPLI R_M7 : `tracks:DzTracks.titleTrack(svmTracksFrom(d.tracks))` — NON : n'insérer `t1` que si des clips titre existent dans `d.clips` (sinon un projet sans titre gagne une piste vide au rechargement) : `tracks:(d.clips||[]).some(function(c){return c&&c.kind==="title"})?DzTracks.titleTrack(svmTracksFrom(d.tracks)):svmTracksFrom(d.tracks)`.
  - TT4 REPLI R_R1 + R_R2 : action `title_add` combo `Maj+T` (MESURER : `T` = narration, `Maj+T` libre ? sinon `Alt+T`) → dispatch : `var dzTt=DzTracks.titleNew({template:"tiers_inferieur",text:"Titre"},phRef.current,clipsRef.current,"t1");if(!dzTt)return;pushHistory();svmTracksSet(DzTracks.titleTrack(svmTracksOf(dzProjRef.current)));setClips(clipsRef.current.concat([dzTt]));setSelId(dzTt.id);setDirty(!0);fireNote("Titre posé à "+phRef.current.toFixed(2)+" s — l'inspecteur le règle.")` — MESURER que `svmTracksSet` pousse déjà l'historique (M4b : oui, « pushHistory ») → un seul `pushHistory` : retirer le nôtre ou lui passer l'instantané ; dis ce que tu mesures.
  - TT5 REPLI R_K5 : chip `T+` (`title:"Poser un titre à la tête ("+svmKeyLabel("title_add")+")"`) à côté de « ◆ n ».
  - `svmTracksSet` et les clips `t1` : `svmTracksFrom` (bundle) garde-t-il un `kind:"title"` inconnu ? MESURER ; sinon repli dans R_M7.

- [ ] **Étape 4 : bancs, rejeu, sonde (+ `titleNew`, `titleTrack` ×2, `TITLE…`), commit** `montage : D-21 - genre title, piste t1, poser un titre a la tete`. Preuve : Maj+T → piste T1 apparaît au-dessus, clip « Titre » 4 s ; sauvegarde puis F5 : il revient.

---

## Tâche 7 — D-21 client : l'inspecteur des titres et l'aperçu vivant

**Files :** `montage.js` (`DzmTitleInspector`), `patch_bundle_montage.py` (TT6 repli R_M12, TT7 repli R_M16REF + V2-bis, TT8 dans liveSync), `montage.css`, `test_montage_bundle.py`, `test_montage_edition.py`.

- [ ] **Étape 1 : banc rouge** — bundle : rendu de `DzmTitleInspector({clip, gabarits, onChange})` par le stub JSX : 8 cartes (une par gabarit, `img` `src` = `/api/montage/title-preview?template=…&text=…`), champs texte/sous-texte/couleur (5 de `BRAND`)/police (16)/taille, la carte sélectionnée `data-sel` ; `onChange(id, patch)` appelé au blur du texte et au clic d'une carte ; pin `TT6` (inspecteur monté quand `sel.tr==="t1"`), `TT7` (hôte `.svm-livetitle` dans le cadre), `TT8` (`liveSync` écrit `innerHTML` de l'hôte = `DzTracks.titleHtml(DzTracks.titleAt(...))` ou vide). Édition : `titleUpdate(clips,id,patch)` pur (texte tronqué 120, gabarit inconnu → inchangé, id inconnu → inchangé).

- [ ] **Étape 2 : implémenter** `DzmTitleInspector` (dans `.svm-pop`-like `div.dzm-ttinsp` : galerie `.dzm-ttcards` avec `<img loading="lazy">` par gabarit, texte `<input>` non contrôlé clé `id|text`, sous-texte, `<select>` couleur/police, `<input type=range>` taille 24–200), `dzmTitleUpdate`, CSS `.dzm-ttcards{display:grid;grid-template-columns:repeat(2,1fr);gap:6px}` + `.dzm-tt` (aperçu vivant : positionnement par gabarit en `%`, police par `font-family`, fond de boîte) ; TT6 : dans R_M12 après le TextDrawer : `sel&&sel.tr==="t1"?r.jsx(DzTracks.TitleInspector,{clip:sel,gabarits:dzTitles,onChange:function(id,p){pushHistory();setClips(DzTracks.titleUpdate(clipsRef.current,id,p));setDirty(!0)}}):null,` (`dzTitles` chargé par `fetch("/api/montage/titles")` dans R_M16REF, comme X1) ; TT7 : hôte `liveOn?r.jsx("div",{className:"svm-livetitle",ref:dzTtHostRef}):null,` avant `svm-livegap` (même ancre que V2 : REPLIER TT7 dans la section V2 posée en Tâche 3 — l'ancre est consommée) ; TT8 : dans la section V3 (liveSync) ajouter `var dzTh=dzTtHostRef.current;if(dzTh){var dzTc=DzTracks.titleAt(clipsRef.current,phRef.current);var dzHtml=dzTc?DzTracks.titleHtml(dzTc,phRef.current):"";if(dzTh._dzHtml!==dzHtml){dzTh.innerHTML=dzHtml;dzTh._dzHtml=dzHtml}}`.

- [ ] **Étape 3 : bancs, rejeu, sonde, commit** `montage : D-21 - inspecteur des titres, huit cartes, apercu vivant`. Preuve : sélectionner le clip titre → 8 cartes PNG, choisir « appel à l'action », taper « Abonnez-vous » + Tab → l'aperçu vivant l'affiche en bas ; Preview 480p le grave.

---

## Tâche 8 — clôture L2 : mutations, comptes, conception

- [ ] `backend/tests/mutations_montage_l2.py` (modèle `mutations_montage_l0l1.py`) : ≥ 12 mutations en octets — `_XFADE_FAMILIES` amputée d'une famille ; `_XFADE_LIVE` élargi ; `transitions_catalog` sans `live` ; `dzmTransList` sans « coupe » en tête ; `dzmTransLabel` ignore le catalogue ; `dzmVeil` sans borne du voisin gauche ; `dzmVeil` triangulaire → constante ; `title_spec` accepte le texte vide ; `_ass_text` avec BOM ; `titles_ass` chaîné APRÈS S1 ; `dzmTitleNew` avec `src:{}` ; `trackKind` sans `t` ; `dzmTitleTrack` en queue au lieu de la tête ; chacune rougit une ligne nommée, table mesurée, restauration sha256.
- [ ] Banc croisé : `DZM_TRANS_FAM` (client) == `_XFADE_FAMILIES` (backend) — dans `test_montage_l2.py`, lire `montage.js` en octets, extraire la table par regex gardée, comparer les ensembles par famille.
- [ ] Comptes de référence des bancs ; `repatch_all --list` ; `node --check` ; hash du bundle.
- [ ] Conception §1.3 et §1.2 (D-12) : « — **exécuté <date>** : … ; **écarts** : » — D-20 : aperçu animé en CSS par FAMILLE (pas une vignette ffmpeg par transition), durée 0,1–1 s conservée, `crossfade`/`xfade` hérités restent acceptés ; D-21 : 8 gabarits, pas de style par caractère, aperçu vivant en HTML approximatif (le 480p fait foi), piste `t1` unique (pas de titres empilés), pas d'emoji, pas de navigateur de polices au-delà des 16 embarquées ; D-12 : voile noir/blanc/opacité seulement, pas de crossfade A/B en direct (un seul hôte).
- [ ] Commit, push, rapport.

---

## Relecture du plan (faite avant remise)

- Couverture : D-20 (T1–T2), D-12 (T3), D-21 (T4–T7), clôture (T8). Les huit gabarits de la conception sont les huit clés de `TEMPLATES` ; « champs texte/police/taille/couleur/position/entrée-sortie » : position et entrée/sortie sont portées par le GABARIT (pas de champ libre) — écart à dater si la revue le juge insuffisant.
- Ancres : toutes celles citées ont été comptées 1/1 dans `.bak_montage` le 21/09/2026 (rapport d'exploration §B7, §C6, §E2) sauf A_M5 (consommée → repli R_M5), la ligne de `dzTracksRef` (→ repli R_M16REF), les lignes de R1/R2/K5 (→ replis) et l'ancre `svm-livegap` réutilisée par V2 puis TT7 (→ TT7 replié dans V2).
- Cohérence des noms : `dzmTransList/transLabel/transFamily/transLive/transDir` (T2, lus par X2–X4), `dzmVeil` (T3, lu par V3), `dzmTitleTrack/titleNew/titleAt/titleHtml/titleUpdate` (T6–T7), `TI.title_spec/to_ass_title/render_title_png` (T4, lus par T5), `transitions_catalog` (T1, lu par la route).
- Le bloc `sonvfx` n'est jamais réécrit ; `son-vfx-montage.css` n'est pas touché (toutes les règles neuves vont dans `montage.css`).
