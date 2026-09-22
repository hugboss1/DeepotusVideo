# Montage « classe Resolve » — lot L3 (propriétés de plan) — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Un sous-agent frais par tâche, deux revues (conformité puis qualité), corrections en boucle, commit `--only` par tâche, push après chaque tâche. **Chaque agent conteste le plan avec des mesures** : sur L0/L1/L2 le plan avait tort dix-huit fois (ancres à replier, attente d'un banc fausse, section manquante) et l'agent avait raison à chaque fois. Ce plan a DÉJÀ été contredit par l'exploration du 22/09 (voir « Deux affirmations de la conception démenties ») : il en reste sûrement.

**Goal :** donner aux plans V1 du Montage les quatre propriétés de clip de Resolve qui tiennent en ffmpeg natif — dynamic zoom (D-13), retime à interpolation (D-15), stabilisation vidstab (D-16), keyframes d'échelle et d'opacité sur les overlays (D-14) — et la piste d'ajustement (D-9) ; décisions §1.1 (D-9) et §1.2 (D-13…D-16) de `docs/superpowers/specs/2026-09-21-montage-vs-resolve-design.md`, validées le 21/09/2026.

**Architecture :** RIEN de l'existant n'est réécrit. Chaque propriété est un **champ optionnel** du clip (`dz`, `retime`, `stab`, `motion_points[].scale/opacity`) ou de la commande (`adjust_clips`) : en son absence, `_build_montage_command` émet une commande **octet pour octet identique** (règle R1…S1, bancée par `BUILD(x=None) == BUILD()`). Le backend ajoute des helpers purs de clamp (`_dz_spec`, `_v1_retime`, `_v1_stab`), des fragments de filtergraph posés dans la chaîne V1 entre des maillons existants, une analyse `vidstabdetect` en cache par source (calquée sur `/proxy`), et un post-pass borné par le mécanisme `t0/t1` de `effects_engine._timed`. Le client gagne des fonctions **pures** dans `frontend/patches/montage.js` (exportées sur `window.DzTracks`, jouées sous node), un composant hôte unique `DzmPlanProps` pour les trois propriétés de plan, deux rectangles de cadrage dans le lecteur, et des sections en QUEUE de `PATCHES` de `scripts/patch_bundle_montage.py` — **repliées** dans le remplacement qui pose leur ancre quand celle-ci vaut 0 dans `.bak_montage` (R_M5 pour le filtre du payload, R_TT10 pour la ligne de vitesse du payload, R_TT1 pour `trackKind`, R_V3 pour la tête de `liveSync`, R_M16REF pour les refs et gestes). Le bloc `sonvfx`, `subs.js`, `vfxrack.js`, `son-vfx-montage.css` restent intouchables ; les règles CSS neuves vont dans `frontend/dist/shared/montage.css`.

**Tech Stack :** Python 3.13 embarqué (stdlib + Pillow), FastAPI + TestClient, ffmpeg 8.1.1 essentials (`C:\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe` ; `zoompan`, `vidstabdetect/transform`, `minterpolate`, `tblend`, `sendcmd`), node 24 (bancs du cœur JS par FICHIER shim), bundle `frontend/dist/assets/index-BEOJX8L5.js` en OCTETS, chaîne `python scripts/repatch_all.py --from montage` puis `--list` (`montage OK`, `dzcout OK`).

---

## Conventions valables pour tout le plan

```powershell
$PY = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"
Set-Location backend
& $PY tests\test_montage_bundle.py                       # 1636/0 au départ
& $PY tests\test_montage_edition.py                      # 158/0
& $PY tests\test_montage_historique.py                   # 51/0
& $PY tests\test_montage_projets.py                      # 159/0
& $PY tests\test_montage_l2.py                           # 78/0
& $PY tests\test_montage_l3.py                           # NEUF (tâche 1)
& $PY ..\scripts\patch_bundle_montage.py --check --force-unchained   # 96 ancres OK au départ
& $PY ..\scripts\repatch_all.py --from montage ; & $PY ..\scripts\repatch_all.py --list
node --check ..\frontend\dist\assets\index-BEOJX8L5.js
```

- Un banc = un processus, jamais `pytest`. `check(label, cond, detail)`, fin `=== N passed, M failed ===`, code de sortie 1 si rouge. Labels stables, snake_case sans accent.
- **Règle des assertions négatives** : une négation établit d'abord que la mesure a eu lieu (`"cle" in D and …`, `r.status_code == 200 and … not in …`). Chaque banc construit son état vide (le `TypeError` de `BUILD()` sur un mot-clé inconnu EST l'état vide du backend ; un shim sur fichier vide EST celui du cœur JS).
- **Faute n°6** : aucune lecture nue (`[1]`, `.index`, `.json()`) avant un `check` — `A()`, `J()`, `find()` avec repli.
- **Ancres** : comptées sur `.bak_montage` (`--check --force-unchained`), présent dans ce worktree (1 421 572 o, copié après `cmp` du bundle livré). Une ancre qui n'existe que parce qu'un remplacement la crée, ou qu'un remplacement CONSOMME, se REPLIE dans ce remplacement (précédents : R4/R5 dans R_M6/R_M7, E1–E3, K1–K4/K6, W1/W2, X1, V1, TT2 dans R_M5, TT3 dans R_M7, TT4a dans R_M16REF). Sections nouvelles EN QUEUE de `PATCHES`. **Préfixes pris** (mesurés 22/09) : `M, E, H, R, T, K, X, V, TT`. **Préfixes de ce lot** : `DZ` (D-13), `RT` (D-15), `SB` (D-16), `KF` (D-14), `AJ` (D-9).
- Le bundle se lit et s'écrit en OCTETS (`read_text`/`write_text` du patcher gèrent le BOM et `nl()` les fins de ligne). Après tout rejeu : `--list` complet, `node --check`, CRLF == LF, `git hash-object`, et la sonde `("montage","DzTracks",98)` de `scripts/patch_bundle_dzcout.py:279` remesurée à chaque tâche qui ajoute une référence `DzTracks.` — **le comptage est un `str.count` brut, les commentaires JS comptent** : écrire `dzOf()` sans namespace dans la prose.
- Commits : `git commit --only <chemins>`, première ligne sans accent, trailer EXACT `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` ; push de `chantier/montage-l3` après chaque tâche. La preuve à l'écran est faite par le contrôleur (backend du worktree sur 8799, `.claude/launch.json` gitignoré écrit par un script Python, `DEEPOTUS_DATA_DIR` = scratchpad, projet réel obtenu par `POST /api/videos/upload` de deux mp4 ffmpeg `testsrc2`, PointerEvent synthétiques sur `.svm-clip`, touches sur `document.body` seul, `preview_stop` + port libre après chaque preuve).

## Faits mesurés le 22/09/2026 qui bornent ce lot (rapport d'exploration, lecture seule)

- **Chaîne V1** (`montage_service.py:2118-2185`) : par segment `k`, préfixe `sf = scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps},format=yuv420p` ; avec vitesse (`spd = float(s.get("speed") or 0.0)`, `:2166-2172`) le préfixe devient `scale…,crop…,setsar=1,setpts=PTS/{spd},fps={fps},format=yuv420p` ; puis `,tpad=stop_mode=clone:stop_duration={seg_durs[k]},trim=0:{seg_durs[k]},setpts=PTS-STARTPTS` (`:2173-2174`) ; effets par segment via `_fx.build_chain(reff, f"n{k}pre", f"n{k}", f"cfx{k}", {"w","h","dur":seg_durs[k],"fps"})` (`:2182`). Entrées : `-ss src_in` (si > 0) `-t d_src -i path` (`:2145-2148`). Bornes vitesse `_v1_speed` (`:772-790`) : `[0.25, 4]`, `0.0` = historique. La spec V1 est construite dans `/render` `:2877-2885` (`{"path","src_dur","src_in","start","end","transition","transition_s","speed","effects"}`) — **c'est là que `dz`, `retime`, `stab` s'ajoutent**.
- **Aucun post-pass global n'existe dans `montage_service.py`** : `build_chain` n'y est appelé qu'à `:2182`. Les précédents de post-pass sont `template_service.py:879` et `:1077`. Après les overlays (`:2283-2382`) la chaîne continue par les titres `[{cur}]…[tt{j}]` (`:2525-2529`) puis S1 (`:2536-2540`) ; l'horloge y est GLOBALE (les segments V1 sont à `setpts=PTS-STARTPTS` puis concaténés par `xfade`, `tpad` maître `:2270-2281`).
- **`effects_engine._timed`** (`:840-903`) borne un effet à `[t0, t1]` SANS `enable=` (pixelate/mirror/vhs/shake le refusent) : `split` + `sendcmd` + `blend@…env=all_mode=normal:all_opacity=0`, pas `_RAMP_STEP = 1/25`, `t1 = min(t1, ctx["dur"])`, abandon si `t1 - t0 < 0.05`. **C'est exactement « un post-pass borné »** : D-9 n'a rien à inventer.
- **`_mp_lerp_expr(pts)`** (`:742-757`) prend des paires `(t, v)` ; trois appels : rotation `:2358` (horloge LOCALE), x/y `:2373-2374` (horloge GLOBALE, `xpts = [(round(st+t,3), …)]`). `_motion_points` (`:678-740`) lit `{t,x,y,rotate?}`, `_MP_MAX_POINTS = 8`, **ignore `scale` et `opacity`**. L'opacité d'overlay est `colorchannelmixer=aa=` (`:2325`, `:2337`), l'échelle une **largeur paire figée** `ow2` (`:2333-2335`).
- **Persistance** : `_save_record` (`:877-1010`) n'a AUCUNE liste blanche de clés de clip ; mesuré `POST /save` puis `GET /project` : `dz`, `retime`, `stab`, un clip sans `src` sur une piste `adjust`, tout traverse intact. `_tracks_meta` (`:239-303`) accepte `kind:"adjust"` (id ≤ 8 caractères). Les cinq filtres par `kind` (`:2675, 2821, 2894, 2916, 3101`) rendent un clip `adjust` **inerte** aujourd'hui (état vide de D-9).
- **`/proxy`** (`:3430-3515`) : `POST` → `{ok, ready, job_id}`, `JobRecord(provider="montage_proxy")` sans chemin d'artefact, `BackgroundTasks.add_task` + `asyncio.to_thread(MM.proxy, p)`, suivi client par `GET /api/jobs/{id}` ; cache `montage_media._cache_path(src, kind)` = `sha1(chemin résolu|mtime_ns|genre)[:20]` dans `outputs/montage_cache`, `_EXT = {"peaks":".json","strip":".jpg","proxy":".mp4"}`, écriture atomique `_tmp_de` + `os.replace`, **pas de `_prune_cache`** (celui de `effects_preview.py:332` est par motif, sur `fxpreview/`). **Le client ne demande JAMAIS `/proxy`** (0 occurrence dans le bundle, `.bak_montage`, les patches) : le seul précédent de polling est `launchRender` (`.bak_montage:3928-3990`, `setInterval` sur `fetch("/api/jobs/"+job.id)`).
- **ffmpeg 8.1.1 mesuré** : `zoompan` (options `z,x,y,d,s,fps` toutes expressions, `d` défaut 90) ; `vidstabdetect` (`shakiness 1..10`, `accuracy 1..15`, `result`), `vidstabtransform` (`input`, `smoothing 0..1000`, `crop keep|black`, `zoom −100..100`, `optzoom 0|1|2`, `interpol no|linear|bilinear|bicubic`) ; `minterpolate` (`mi_mode dup|blend|mci`, `mc_mode obmc|aobmc`, `me_mode bidir|bilat`, `vsbmc`, `scd none|fdiff`) ; `tblend` (`all_mode` 41 modes dont `average`). **Chemins Windows dans `input=`/`result=`** : la forme qui marche est `'C\:/Users/…/x.trf'` (apostrophes + UN antislash), exactement ce que produit `subtitle_service._ff_escape_path` (`:2134-2142`) entre apostrophes. Sous Git Bash ces chemins sont mutilés par MSYS : mesurer sous PowerShell ou par `subprocess.run` en liste.
- **Bundle `.bak_montage`** (ancres comptées 1/1 sauf mention) : inspecteur du clip = bloc JSX inline `r.jsxs("aside",{className:"svm-insp",…` (`:5107`), IIFE In/Out/Vitesse `:5114-5146` (`var v1spd=!!(sel&&sel.tr==="v1"&&sel.src&&sel.src.job_id);` `:5124`, `          if(v1spd){` 1/1 non consommée, `<select className="svm-vitsel">` `:5136-5142`, `svmSetV1Speed(id,v)` `:3141-3178`), puis `        subsInspector(),` / `        transInspector(),` (consommée 5× par le patcher) / **`        ovInspector(),` (1/1, patcher 0)** / `        audioInspector(),`. `  function ovInspector(){` `:4063` (1/1, patcher 0) : garde `sel.tr!=="v2"`, champs Échelle `:4117-4126` (`svmOvTfField({scale})` statique), Opacité `:4138-4150` (écrit `{opacity}` sur le clip), Trajectoire `:4151-4186`. `SVM_MP_CAP=8,SVM_MP_EPS=.15` `:1481`, `svmMpOf` `:1482`, `svmMpLerp(pts,tl,key)` `:1487`, **`svmOvTfAt(c,t)` `:1502` avec `scale:base.scale` en dur `:1511`**, `svmMpApply(c,res)` `:2749-2757` (seul écrivain de `motion_points`), `svmMpHere` `:2762`, `svmMpRemove` `:2777`, `svmMpField(c,patch)` `:2798-2814`. Lecteur : `  function liveSync(){` `:2220` **consommée par V3**, `playbackRate` `:2259-2260`, hôtes `.svm-live`/`.svm-liveov`/`.svm-livegap` `:5040-5044`, **cadre `.svm-tf` `:5045-5062`** (8 poignées `svm-tfh` + `svm-tfrot`, `ovHandleDown(e,"scale"|"rotate")`, positionné par `tfSyncBox`, hors `vzoom`) dont la dernière ligne `            r.jsx("div",{className:"svm-tfbadge",ref:tfBadgeRef})]}):null,` vaut 1/1, patcher 0. `renderPayload` `:3854-3927` = **liste blanche stricte** (`dz/retime/stab` seraient jetés) ; `A_M5` consommée (repli R_M5) ; la ligne de vitesse V1 `if(c.tr==="v1"&&c.src.job_id&&typeof c.speed==="number"&&c.speed>0&&` est **consommée par TT10** (`R_TT10`) ; la ligne suivante `           Math.abs(c.speed-1)>1e-6)o.speed=Math.round(c.speed*100)/100;` est à mesurer (attendue 1/1, patcher 0) ; `        if(c.tr==="v2"){` `:3898` vaut 1 dans `.bak` **et 1 dans le patcher** (consommée : trouver le tag par `grep -n 'if(c.tr==="v2"){' scripts/patch_bundle_montage.py`). `trackKind` `:3533` ne lit que l'INITIALE, consommée par TT1 (`R_TT1`). `vfxStackSection` `:4224`, garde `    if(d&&d.Stack&&sel&&sel.src&&trackKind(sel.tr)==="video")` 1/1, patcher 0. Le « + » de l'en-tête de piste est consommé par TT11 (`R_TT11`, `dzTtAdd` replié dans R_M16REF `:1022`).
- **Couche `montage.js`** (6053 l., script plat, `var DzTracks={…}` `:5972`, `window.DzTracks=DzTracks;` `:6053`) : `DZM_DEFAULT_TRACKS` (7 pistes, `:166-184`), `dzmSkin(id,kind,type)` `:197-217` (branche `title` `:213`), `dzmKindOf(id,kind)` `:226-230`, `dzmAdd(ts,kind)` `:336`, `dzmAddDit` `:360`, `dzmTitleTrack(ts)` `:5659`, `dzmTitleNew` `:5678`, `dzmCarve(clips,tr,a,b)` `:4875` (propage `srcIn` avec la vitesse), `dzmPose` `:4888` (retire `srcDur`), `dzmSpeedNum(c)` `:1849`, `dzmR3` `:556`, `DZM_HIST_CLES` `:4694` (un champ de CLIP est déjà couvert par `s.clips`). Aucun identifiant de piste ne commence par « j » dans `.bak_montage` (à REMESURER : `grep -c 'id:"j' frontend/dist/assets/index-BEOJX8L5.js.bak_montage`).
- **Bancs** : `test_montage_l2.py` porte `BUILD(**kw)` (`:581-593`, appel direct de `_build_montage_command([V1SPEC()],[],[],None,**a)`, `TypeError` = état vide) et `V1SPEC(**kw)` (`:568-574`), plus l'espion sur `/render` (`:705-739`, affectation directe de `MS._build_montage_command`/`MS._run_ffmpeg` + `finally`, source `testsrc2` réelle pour passer P8). `test_montage_edition.py` : shim par FICHIER (`:578-583`), `PROBE` finit par `console.log(JSON.stringify(out))`, sections `[1]…[6]`. `test_montage_bundle.py` : boucle `for tag,a,r in P.PATCHES` (`:857-864`, `_remplace` + `_ancre_consommee`), replis épinglés à la main, compte de référence `:34-41` = 1636. `mutations_montage_l2.py` : 5-uplets `(banc, fichier, ancien|[(ancien,nouveau)…], nouveau, rouges attendues)`, octets, sha256 dans `finally`, état MORT.

### Deux affirmations de la conception démenties par la mesure

1. **`crop+scale par expression t` ÉCHOUE** (`[Parsed_crop_0] Error when evaluating the expression 'ih*(0.5+0.5*t/3)'`, code −22) : `crop` n'accepte `t` que dans `x`/`y`, et `scale:eval=frame` fige la taille à t=0. **Seul `zoompan` tient**, avec `d=1:s={w}x{h}:fps={fps}` (90 images / 3,000 s préservées) et le temps par `it` (timestamp d'entrée), jamais `t`. Et il doit venir **APRÈS `fps={fps}`** : posé avant, sur un flux `setpts=PTS/2` à 60 i/s effectifs, il dupliquerait chaque image à 30 i/s et doublerait la durée.
2. **« Cache par source comme `/proxy` » sous-entend un client qui demande le proxy : il n'existe pas.** Tout le chemin client de D-16 (déclenchement, suivi du job, réaffichage) est à écrire ; le seul modèle est `launchRender`.

## Fichiers

| Fichier | Rôle dans ce plan |
|---|---|
| `backend/app/services/montage_service.py` | `_dz_spec`/`_dz_filter` (T1), `_v1_retime`/`_RETIME` (T3), `_v1_stab` + spec `stab` + entrée non tronquée + `POST/GET /stab` (T5), `_motion_points` étendu + `_mp_cmds` (T7), `adjust_clips` + collecte des clips d'ajustement (T8) |
| `backend/app/services/montage_media.py` | `_EXT["stab"]`, `stab_path`, `stab_detect` (T5) |
| `frontend/patches/montage.js` | pures : `dzmDzNorm/dzmDzAt/dzmDzPreset/dzmDzMove/dzmDzScale/dzmDzCss` (T2), `dzmRetimeOf/dzmRampe` (T4), `dzmStabNorm/dzmStabOf` (T6), `dzmMpLerp2` (T7), `dzmAdjustTrack/dzmAdjustNew/dzmAdjustAt` (T9) ; composants `DzmPlanProps` (T2, étendu T4/T6), `DzmDzRects` (T2) ; exports |
| `scripts/patch_bundle_montage.py` | sections `DZ1…DZ3` + repli R_V3 + repli R_TT10 (T2), `RT1` (T4), `SB1` (T6), `KF1…KF4` (T7), `AJ1…AJ4` + replis R_TT1/R_M5/R_TT11/R_M16REF (T9) — en queue |
| `frontend/dist/shared/montage.css` | `.dzm-plan*`, `.dzm-dzrect*`, `.dzm-stab*`, `.dzm-adj*` |
| `scripts/patch_bundle_dzcout.py` | sonde `("montage","DzTracks",N)` remesurée |
| `backend/tests/test_montage_l3.py` | NEUF — backend : `[1]` D-13, `[2]` D-15, `[3]` D-16, `[4]` D-14, `[5]` D-9, `[6]` routes et espion `/render` |
| `backend/tests/test_montage_edition.py` | + sections `[7]` D-13, `[8]` D-15, `[9]` D-16, `[10]` D-14, `[11]` D-9 (cœur JS sous node) |
| `backend/tests/test_montage_bundle.py` | pins DZ/RT/SB/KF/AJ, replis nommés, comptes de référence |
| `backend/tests/mutations_montage_l3.py` | NEUF — campagne de mutations (clôture) |
| `docs/superpowers/specs/2026-09-21-montage-vs-resolve-design.md` | « exécuté » + écarts pour D-13, D-15, D-16, D-14, D-9 |

---

## Tâche 1 — D-13 backend : le champ `dz`, le `zoompan` après `fps`

**Files :** modifier `backend/app/services/montage_service.py` (helpers sous `_v1_speed`, préfixe de segment `:2166-2174`, spec V1 `:2877-2885`), créer `backend/tests/test_montage_l3.py`.

- [ ] **Étape 1 : banc rouge.** Créer `backend/tests/test_montage_l3.py` en COPIANT l'en-tête de `test_montage_l2.py` (`:1-104` : `reconfigure`, `TMP`, les cinq variables d'environnement AVANT `import app`, `check`, `J`, `A`) et ses helpers `V1SPEC`/`FLAT`/`BUILD` (`:568-593`) tels quels. Section `[1]` :

```python
print("\n[1] D-13 dynamic zoom : le champ dz devient un zoompan apres fps")
from app.services import montage_service as MS
_dz_spec = A("_dz_spec", lambda c: "ABSENT")
_dz_filter = A("_dz_filter", lambda *a, **k: "ABSENT")
DZ_IN = {"x0": 0, "y0": 0, "w0": 1, "x1": 0.2, "y1": 0.2, "w1": 0.6}
check("d13_un_dz_valide_est_clampe_et_porte_ease_doux",
      _dz_spec({"dz": DZ_IN}) == {"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "doux"},
      _dz_spec({"dz": DZ_IN}))
check("d13_les_bornes_sont_tenues_w_min_0_1_et_x_dans_le_cadre",
      _dz_spec({"dz": {"x0": 0.9, "y0": -1, "w0": 0.02, "x1": 5, "y1": 5, "w1": 3}})
      == {"x0": 0.9, "y0": 0.0, "w0": 0.1, "x1": 0.0, "y1": 0.0, "w1": 1.0, "ease": "doux"},
      _dz_spec({"dz": {"x0": 0.9, "y0": -1, "w0": 0.02, "x1": 5, "y1": 5, "w1": 3}}))
check("d13_plein_cadre_des_deux_cotes_ne_vaut_aucun_zoom",
      _dz_spec({"dz": {"x0": 0, "y0": 0, "w0": 1, "x1": 0, "y1": 0, "w1": 1}}) is None)
check("d13_absent_non_dict_ou_nan_rend_none",
      _dz_spec({}) is None and _dz_spec({"dz": "x"}) is None
      and _dz_spec({"dz": dict(DZ_IN, w1="nan")}) is None and _dz_spec({"dz": dict(DZ_IN, x1=None)}) is None)
check("d13_ease_lin_est_gardee_tout_autre_mot_retombe_a_doux",
      (_dz_spec({"dz": dict(DZ_IN, ease="lin")}) or {}).get("ease") == "lin"
      and (_dz_spec({"dz": dict(DZ_IN, ease="zzz")}) or {}).get("ease") == "doux")
f = _dz_filter({"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "lin"}, 64, 64, 25, 3.0)
check("d13_le_filtre_est_un_zoompan_d1_a_la_taille_du_canvas",
      isinstance(f, str) and f.startswith("zoompan=z='") and ":d=1:s=64x64:fps=25" in f, f)
check("d13_le_temps_est_it_sur_la_duree_jamais_t",
      isinstance(f, str) and "clip(it/3,0,1)" in f and "*t" not in f and "(t" not in f, f)
check("d13_z_est_l_inverse_de_la_largeur_x_y_en_fraction_du_cadre",
      isinstance(f, str) and "z='1/(1+(-0.4)*" in f and ":x='iw*(0+(0.2)*" in f and ":y='ih*(0+(0.2)*" in f, f)
fd = _dz_filter({"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "doux"}, 64, 64, 25, 3.0)
check("d13_ease_doux_est_la_smoothstep_u_u_3_2u",
      isinstance(fd, str) and "*(3-2*" in fd and fd != f, fd)
_c0 = BUILD()
check("d13_sans_dz_la_commande_est_octet_pour_octet_l_historique",
      BUILD(dz=None) == _c0 and "zoompan" not in _c0, _c0[:200])
_cz = BUILD(dz={"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "doux"})
check("d13_avec_dz_le_zoompan_est_pose_apres_fps_et_avant_format",
      "zoompan" in _cz and _cz.find("fps=25,zoompan=") > 0 and _cz.find(":fps=25,format=yuv420p,tpad=") > 0, _cz[:400])
_czs = BUILD(dz={"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "doux"}, speed=2.0)
check("d13_avec_vitesse_le_zoompan_reste_apres_le_fps_qui_suit_setpts",
      "setpts=PTS/2" in _czs and _czs.find("setpts=PTS/2,fps=25,zoompan=") > 0, _czs[:400])
check("d13_la_duree_du_zoom_est_celle_du_segment",
      "clip(it/" in _cz and ("clip(it/%s" % _cz.split("stop_duration=")[1].split(",")[0]) in _cz if "stop_duration=" in _cz else False, _cz[:400])
```

`V1SPEC(**kw)` doit accepter `dz=` et `speed=` — vérifier qu'il fait `spec.update(kw)` ; sinon l'étendre dans CE banc (copie locale), pas dans `test_montage_l2.py`.

- [ ] **Étape 2 : lancer → rouge** (`A("_dz_spec")` rend le repli `"ABSENT"`, `BUILD(dz=…)` rend `TypeError`).

- [ ] **Étape 3 : implémenter.** Sous `_v1_speed` (`:790`) :

```python
# D-13 (22/09/2026) — DYNAMIC ZOOM. Champ optionnel `dz` d'un clip V1 :
# {x0, y0, w0, x1, y1, w1, ease?} en FRACTIONS du cadre (le segment est
# déjà recadré au ratio du canvas par scale/crop, donc la hauteur de la
# fenêtre est la MÊME fraction que sa largeur). w ∈ [0.1, 1], x et y ∈
# [0, 1−w]. Plein cadre aux deux bouts = aucun zoom (None). MESURÉ le
# 22/09 : `crop=w='…t…'` ÉCHOUE à la configuration (−22) et `scale:eval=
# frame` fige la taille — seul `zoompan` tient, et il doit venir APRÈS
# `fps=` (avant, il dupliquerait chaque image d'un flux retimé).
_DZ_EASES = ("doux", "lin")


def _dz_spec(c: dict) -> dict | None:
    raw = c.get("dz")
    if not isinstance(raw, dict):
        return None
    lbl = c.get("label") or c.get("tr") or "v1"
    out: dict = {}
    for k in ("x0", "y0", "w0", "x1", "y1", "w1"):
        try:
            f = float(raw.get(k))
        except (TypeError, ValueError):
            f = float("nan")
        if f != f:  # NaN / absent — jamais dans un filtergraph
            logger.warning(f"montage: dz.{k} invalide ({raw.get(k)!r}), zoom ignoré — {lbl}")
            return None
        out[k] = f
    for i in ("0", "1"):
        out["w" + i] = max(0.1, min(1.0, out["w" + i]))
        out["x" + i] = max(0.0, min(1.0 - out["w" + i], out["x" + i]))
        out["y" + i] = max(0.0, min(1.0 - out["w" + i], out["y" + i]))
    if all(abs(out[k]) < 1e-6 for k in ("x0", "y0", "x1", "y1")) and out["w0"] >= 1.0 and out["w1"] >= 1.0:
        return None
    out["ease"] = raw.get("ease") if raw.get("ease") in _DZ_EASES else "doux"
    return out


def _dz_filter(dz: dict, w: int, h: int, fps: int, dur: float) -> str:
    """Le zoompan d'un segment : u = clip(it/dur, 0, 1) (smoothstep si `doux`),
    z = 1/lerp(w0,w1), x/y = iw·lerp(x0,x1) / ih·lerp(y0,y1). d=1 : une image
    de sortie par image d'entrée, durée et compte d'images préservés (mesure)."""
    n = sfx_service.fnum
    d = max(0.04, float(dur))
    u = f"clip(it/{n(d)},0,1)"
    if dz.get("ease") == "doux":
        u = f"({u})*({u})*(3-2*({u}))"

    def lerp(a: float, b: float) -> str:
        return f"({n(a)}+({n(b - a)})*({u}))"

    return (f"zoompan=z='1/{lerp(dz['w0'], dz['w1'])}'"
            f":x='iw*{lerp(dz['x0'], dz['x1'])}'"
            f":y='ih*{lerp(dz['y0'], dz['y1'])}'"
            f":d=1:s={w}x{h}:fps={fps}")
```

Dans `_build_montage_command`, le préfixe de segment (`:2166-2172`) devient :

```python
            spd = float(s.get("speed") or 0.0)
            dzf = s.get("dz")
            dzp = f",{_dz_filter(dzf, w, h, fps, seg_durs[k])}" if isinstance(dzf, dict) else ""
            if spd:
                pre = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                       f"crop={w}:{h},setsar=1,"
                       f"setpts=PTS/{sfx_service.fnum(spd)},"
                       f"fps={fps}{dzp},format=yuv420p")
            else:
                pre = sf if not dzp else (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                                          f"crop={w}:{h},setsar=1,fps={fps}{dzp},format=yuv420p")
```

(vérifier que `sf` reste utilisé tel quel sans `dz` : l'assertion « octet pour octet » le tient). Dans `/render` (`:2877-2885`) ajouter `"dz": _dz_spec(c),` à la spec V1. Mettre à jour la docstring de `_build_montage_command` (`:2042-2096`) d'une règle « D-13 ».

- [ ] **Étape 4 : mesure ffmpeg réelle** (une ligne de banc, sous `SKIP` si ffmpeg absent, comme les bancs-miroirs) : générer `testsrc2` 2 s dans `TMP`, appeler `_build_montage_command` avec `dz` sur cette source, `subprocess.run(cmd)` → code 0 et `ffprobe` compte `nb_frames` = 50 à 25 i/s (`d=1` préserve). Sans ffmpeg : `check("d13_rendu_reel_SKIP", True)` avec le mot SKIP dans le label.

- [ ] **Étape 5 : lancer → vert ; `test_montage_l2.py` inchangé (78/0). Commit** `--only montage_service.py test_montage_l3.py` : `montage : D-13 - le champ dz devient un zoompan apres fps`.

---

## Tâche 2 — D-13 client : `dzmDz*` pures, hôte `DzmPlanProps`, deux rectangles dans le lecteur, zoom en direct

**Files :** modifier `frontend/patches/montage.js`, `scripts/patch_bundle_montage.py` (DZ1…DZ3, replis R_V3 et R_TT10), `frontend/dist/shared/montage.css`, `backend/tests/test_montage_edition.py` (`[7]`), `backend/tests/test_montage_bundle.py`, `scripts/patch_bundle_dzcout.py`.

- [ ] **Étape 1 : banc rouge** — section `[7]` de `test_montage_edition.py`, dans `PROBE` :

```javascript
/* [7] D-13 : le zoom dynamique, cote client */
var DZ1={x0:0,y0:0,w0:1,x1:.2,y1:.2,w1:.6};
out.dz_norm=T.dzNorm(DZ1);
out.dz_norm_clamp=T.dzNorm({x0:.9,y0:-1,w0:.02,x1:5,y1:5,w1:3});
out.dz_norm_vide=[T.dzNorm(null),T.dzNorm({x0:0,y0:0,w0:1,x1:0,y1:0,w1:1}),T.dzNorm({x0:"a"})];
out.dz_at=[T.dzAt(DZ1,0),T.dzAt(DZ1,1),T.dzAt(Object.assign({ease:"lin"},DZ1),.5)];
out.dz_at_doux=T.dzAt(DZ1,.5);
out.dz_preset=[T.dzPreset("in"),T.dzPreset("out"),T.dzPreset("zzz")];
out.dz_move=[T.dzMove(DZ1,1,.5,.5),T.dzMove(DZ1,0,.1,.1)];
out.dz_scale=[T.dzScale(DZ1,1,.3),T.dzScale(DZ1,1,-.9)];
out.dz_css=[T.dzCss(DZ1,0),T.dzCss(DZ1,1),T.dzCss(null,.5)];
out.dz_of=[T.dzOf({dz:DZ1}),T.dzOf({dz:{x0:0,y0:0,w0:1,x1:0,y1:0,w1:1}}),T.dzOf({})];
out.dz_pur=JSON.stringify(DZ1)==='{"x0":0,"y0":0,"w0":1,"x1":0.2,"y1":0.2,"w1":0.6}';
```

Python :

```python
print("\n[7] D-13 zoom dynamique (client)")
check("dz_norm_clampe_et_pose_ease_doux",
      D.get("dz_norm") == {"x0": 0, "y0": 0, "w0": 1, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "doux"}, D.get("dz_norm"))
check("dz_norm_tient_les_memes_bornes_que_le_backend",
      D.get("dz_norm_clamp") == {"x0": 0.9, "y0": 0, "w0": 0.1, "x1": 0, "y1": 0, "w1": 1, "ease": "doux"}, D.get("dz_norm_clamp"))
check("dz_norm_rend_null_pour_vide_plein_cadre_et_invalide",
      "dz_norm_vide" in D and D["dz_norm_vide"] == [None, None, None], D.get("dz_norm_vide"))
check("dz_at_rend_le_rectangle_debut_fin_et_le_milieu_lineaire",
      D.get("dz_at") == [{"x": 0, "y": 0, "w": 1}, {"x": 0.2, "y": 0.2, "w": 0.6}, {"x": 0.1, "y": 0.1, "w": 0.8}], D.get("dz_at"))
check("dz_at_doux_est_la_smoothstep_a_mi_course_egale_au_lineaire",
      D.get("dz_at_doux") == {"x": 0.1, "y": 0.1, "w": 0.8}, D.get("dz_at_doux"))
check("dz_preset_in_zoome_au_centre_out_l_inverse_inconnu_null",
      D.get("dz_preset") == [{"x0": 0, "y0": 0, "w0": 1, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "doux"},
                             {"x0": 0.2, "y0": 0.2, "w0": 0.6, "x1": 0, "y1": 0, "w1": 1, "ease": "doux"}, None], D.get("dz_preset"))
check("dz_move_deplace_un_rectangle_en_restant_dans_le_cadre",
      D.get("dz_move") == [dict(D["dz_norm"], x1=0.4, y1=0.4), D["dz_norm"]] if "dz_norm" in D else False, D.get("dz_move"))
check("dz_scale_change_la_largeur_autour_du_centre_borne_0_1",
      "dz_scale" in D and D["dz_scale"][0]["w1"] == 0.9 and abs(D["dz_scale"][0]["x1"] - 0.05) < 1e-9
      and D["dz_scale"][1]["w1"] == 0.1 and abs(D["dz_scale"][1]["x1"] - 0.45) < 1e-9, D.get("dz_scale"))
check("dz_css_est_une_translation_puis_une_echelle_origine_0_0",
      D.get("dz_css") == ["translate(0%, 0%) scale(1)", "translate(-33.3333%, -33.3333%) scale(1.66667)", ""], D.get("dz_css"))
check("dz_of_lit_le_clip_et_rend_null_hors_zoom",
      "dz_of" in D and D["dz_of"][0] == D.get("dz_norm") and D["dz_of"][1] is None and D["dz_of"][2] is None, D.get("dz_of"))
check("dz_pur", D.get("dz_pur") is True)
```

- [ ] **Étape 2 : implémenter** (montage.js, avant `var DzTracks=`) :

```javascript
/* ── D-13 (22/09/2026) : LE ZOOM DYNAMIQUE ───────────────────────────────
   `dz` = {x0,y0,w0,x1,y1,w1,ease} en FRACTIONS du cadre — MÊMES bornes que
   `montage_service._dz_spec` (w ∈ [0.1,1], x/y ∈ [0,1−w], plein cadre aux
   deux bouts = null). Le rendu est un zoompan (backend) ; en direct, le
   lecteur applique `dzmDzCss` à la <video> active (translate puis scale,
   origine 0 0) — même géométrie, pas le même moteur. */
function dzmDzR(v){return Math.round(v*1e6)/1e6}
function dzmDzNorm(raw){
  if(!raw||typeof raw!=="object")return null;
  var ks=["x0","y0","w0","x1","y1","w1"],o={},i,v;
  for(i=0;i<ks.length;i++){v=Number(raw[ks[i]]);if(!isFinite(v))return null;o[ks[i]]=v}
  ["0","1"].forEach(function(s){
    o["w"+s]=Math.max(.1,Math.min(1,o["w"+s]));
    o["x"+s]=dzmDzR(Math.max(0,Math.min(1-o["w"+s],o["x"+s])));
    o["y"+s]=dzmDzR(Math.max(0,Math.min(1-o["w"+s],o["y"+s])));
    o["w"+s]=dzmDzR(o["w"+s])});
  if(o.x0===0&&o.y0===0&&o.x1===0&&o.y1===0&&o.w0>=1&&o.w1>=1)return null;
  o.ease=raw.ease==="lin"?"lin":"doux";
  return o}
function dzmDzOf(c){return c&&c.dz?dzmDzNorm(c.dz):null}
function dzmDzAt(dz,u){
  var d=dzmDzNorm(dz);if(!d)return {x:0,y:0,w:1};
  u=Math.max(0,Math.min(1,Number(u)||0));
  if(d.ease!=="lin")u=u*u*(3-2*u);
  return {x:dzmDzR(d.x0+(d.x1-d.x0)*u),y:dzmDzR(d.y0+(d.y1-d.y0)*u),w:dzmDzR(d.w0+(d.w1-d.w0)*u)}}
function dzmDzPreset(name){
  if(name==="in")return dzmDzNorm({x0:0,y0:0,w0:1,x1:.2,y1:.2,w1:.6});
  if(name==="out")return dzmDzNorm({x0:.2,y0:.2,w0:.6,x1:0,y1:0,w1:1});
  return null}
/* k = 0 (début) | 1 (fin) ; dx/dy en fraction du cadre — le rectangle reste
   dans le cadre, la largeur ne bouge pas */
function dzmDzMove(dz,k,dx,dy){
  var d=dzmDzNorm(dz);if(!d)return null;var s=k?"1":"0",o=Object.assign({},d);
  o["x"+s]=o["x"+s]+(Number(dx)||0);o["y"+s]=o["y"+s]+(Number(dy)||0);
  return dzmDzNorm(o)||d}
/* dw en fraction : la largeur change AUTOUR DU CENTRE du rectangle, bornée
   [0.1, 1] et ramenée dans le cadre par la normalisation */
function dzmDzScale(dz,k,dw){
  var d=dzmDzNorm(dz);if(!d)return null;var s=k?"1":"0",o=Object.assign({},d);
  var w0=o["w"+s],w1=Math.max(.1,Math.min(1,w0+(Number(dw)||0))),cx=o["x"+s]+w0/2,cy=o["y"+s]+w0/2;
  o["w"+s]=w1;o["x"+s]=cx-w1/2;o["y"+s]=cy-w1/2;
  return dzmDzNorm(o)||d}
/* la transformation CSS de la <video> pour la fenêtre à u : scale = 1/w,
   puis translation de −x·s / −y·s (en % de la boîte de l'élément), origine
   0 0 — l'appelant pose transformOrigin:"0 0". "" quand il n'y a pas de zoom. */
function dzmDzCss(dz,u){
  var d=dzmDzNorm(dz);if(!d)return "";
  var r=dzmDzAt(d,u),s=1/r.w,f=function(v){return String(Math.round(v*1e5)/1e5)};
  return "translate("+f(-r.x*s*100)+"%, "+f(-r.y*s*100)+"%) scale("+f(s)+")"}
```

Puis l'hôte des propriétés de plan et les rectangles (composants, `r`/`x` lus à l'appel comme `DzmTitleInspector`) :

```javascript
/* L'HÔTE DES PROPRIÉTÉS DE PLAN (D-13, puis D-15 en T4 et D-16 en T6) :
   UNE section de l'inspecteur, montée UNE fois (DZ1) sur un clip V1 réel.
   props : {clip, u (avancement 0..1 de la tête dans le clip), onChange(patch,
   heavy), onSeek(u)} — `onChange` reçoit un patch de clip ({dz:…} ou
   {dz:void 0}) et l'appelant écrit l'historique. */
function DzmPlanProps(o){
  var c=o&&o.clip,on=typeof (o&&o.onChange)==="function"?o.onChange:function(){};
  if(!c)return null;
  var dz=dzmDzOf(c),k=dz?0:0;
  var row=function(label,kids,key){return r.jsxs("div",{className:"svm-prop dzm-plan-row",children:[
    r.jsx("div",{className:"svm-propk",children:label}),r.jsx("div",{className:"svm-propv",children:kids})]},key)};
  var sel=function(cur,opts,cb,title){return r.jsx("select",{className:"svm-vitsel",value:cur,title:title,
    onChange:function(e){cb(e.target.value)},children:opts.map(function(p){return r.jsx("option",{value:p[0],children:p[1]},p[0])})})};
  var kids=[];
  kids.push(row("Zoom dyn.",sel(dz?(dz.w1<dz.w0?"in":dz.w1>dz.w0?"out":"custom"):"off",
    [["off","aucun"],["in","zoom avant"],["out","zoom arrière"],["custom","personnalisé"]],
    function(v){if(v==="off")on({dz:void 0},!0);else if(v==="custom")on({dz:dz||dzmDzPreset("in")},!0);else on({dz:dzmDzPreset(v)},!0)},
    "Zoom dynamique (D-13) : deux fenêtres, début et fin du plan — glisser les rectangles dans le lecteur, le rendu interpole"),"dz"));
  if(dz){
    kids.push(row("Courbe",sel(dz.ease,[["doux","douce"],["lin","linéaire"]],function(v){on({dz:Object.assign({},dz,{ease:v})},!0)},"Interpolation du zoom"),"dz-ease"));
    kids.push(row("Fenêtres",r.jsxs("span",{className:"dzm-plan-hint",children:[
      "début "+Math.round(dz.w0*100)+" % · fin "+Math.round(dz.w1*100)+" %"]}),"dz-w"));}
  return r.jsxs("div",{className:"dzm-plan",children:[r.jsx("div",{className:"dzm-plan-t",children:"Propriétés du plan"}),
    r.jsx("div",{className:"svm-props",children:kids})]})}
/* LES DEUX RECTANGLES (vert = début, rouge = fin) dans le cadre du lecteur,
   en % du cadre — glisser le corps = déplacer, glisser le coin = échelle.
   props : {dz, onChange(dz), box:{w,h} en px du cadre} ; les gestes sont
   des PointerEvent capturés sur l'élément lui-même (comme les poignées
   `.svm-tfh`), rejoués depuis l'état du pointerdown (fonctions pures). */
function DzmDzRects(o){
  var dz=dzmDzNorm(o&&o.dz),on=typeof (o&&o.onChange)==="function"?o.onChange:function(){},box=(o&&o.box)||{w:1,h:1};
  if(!dz)return null;
  var mk=function(k){
    var s=k?"1":"0",x=dz["x"+s],y=dz["y"+s],w=dz["w"+s];
    var down=function(mode){return function(e){
      var el=e.currentTarget,sx=e.clientX,sy=e.clientY,base=dz;
      try{el.setPointerCapture(e.pointerId)}catch(_e){}
      e.preventDefault();e.stopPropagation();
      var mv=function(e2){var dx=(e2.clientX-sx)/Math.max(1,box.w),dy=(e2.clientY-sy)/Math.max(1,box.h);
        on(mode==="move"?dzmDzMove(base,k,dx,dy):dzmDzScale(base,k,dx))};
      var up=function(){el.removeEventListener("pointermove",mv);el.removeEventListener("pointerup",up);el.removeEventListener("pointercancel",up)};
      el.addEventListener("pointermove",mv);el.addEventListener("pointerup",up);el.addEventListener("pointercancel",up)}};
    return r.jsxs("div",{className:"dzm-dzrect","data-k":k?"fin":"debut",
      style:{left:(x*100)+"%",top:(y*100)+"%",width:(w*100)+"%",height:(w*100)+"%"},
      title:(k?"Fin":"Début")+" du zoom — glisser : déplacer · coin : échelle",
      onPointerDown:down("move"),children:[
        r.jsx("span",{className:"dzm-dzlab",children:k?"fin":"début"}),
        r.jsx("i",{className:"dzm-dzh",onPointerDown:down("scale")})]},k)};
  return r.jsxs("div",{className:"dzm-dzwrap",children:[mk(0),mk(1)]})}
```

Exports : `dzNorm:dzmDzNorm,dzOf:dzmDzOf,dzAt:dzmDzAt,dzPreset:dzmDzPreset,dzMove:dzmDzMove,dzScale:dzmDzScale,dzCss:dzmDzCss,PlanProps:DzmPlanProps,DzRects:DzmDzRects,`.

CSS (`montage.css`) :

```css
/* D-13 — propriétés de plan et rectangles du zoom dynamique */
.dzsvm .dzm-plan{margin-top:10px}
.dzsvm .dzm-plan-t{font-family:var(--f-mono);font-size:10px;color:var(--ink2);text-transform:uppercase;letter-spacing:.06em;margin:6px 0 2px}
.dzsvm .dzm-plan-hint{font-family:var(--f-mono);font-size:10px;color:var(--ink2)}
.dzsvm .dzm-dzwrap{position:absolute;inset:0;pointer-events:none}
.dzsvm .dzm-dzrect{position:absolute;box-sizing:border-box;border:2px solid #3fbf5a;pointer-events:auto;cursor:move;touch-action:none}
.dzsvm .dzm-dzrect[data-k="fin"]{border-color:#e0453f}
.dzsvm .dzm-dzlab{position:absolute;left:0;top:-14px;font:10px var(--f-mono);color:#fff;background:rgba(0,0,0,.6);padding:0 4px}
.dzsvm .dzm-dzh{position:absolute;right:-5px;bottom:-5px;width:10px;height:10px;background:#fff;border:1px solid #000;cursor:nwse-resize}
```

- [ ] **Étape 3 : sections.** MESURE d'abord chaque ancre (`--check --force-unchained` et `grep -cF` dans `.bak_montage` ET dans le patcher) :

```python
# ── DZ1 (D-13) : l'hôte des propriétés de plan, sous In/Out/Vitesse ──────
A_DZ1 = "        ovInspector(),"          # attendu 1/1, patcher 0
R_DZ1 = ('        (sel&&sel.tr==="v1"&&sel.src&&sel.src.job_id&&DzTracks.PlanProps\n'
         '          ?r.jsx(DzTracks.PlanProps,{clip:sel,\n'
         '            u:sel.end>sel.start?Math.max(0,Math.min(1,(phc-sel.start)/(sel.end-sel.start))):0,\n'
         '            onChange:function(patch,heavy){\n'
         '              /* une entrée d\'historique par rafale de 600 ms — même règle que le rack VFX */\n'
         '              var id=selRef.current,now=Date.now();\n'
         '              if(heavy||now-(dzPlanHist.t||0)>600)pushHistory();dzPlanHist.t=now;\n'
         '              setClips(clipsRef.current.map(function(k){if(k.id!==id)return k;var nk=Object.assign({},k,patch);\n'
         '                Object.keys(patch).forEach(function(q){if(patch[q]===void 0)delete nk[q]});return nk}));\n'
         '              setDirty(!0)}}):null),\n'
         '        ovInspector(),')
# `phc` : MESURER le nom de la valeur de tête disponible dans l'aside
# (c'est celui que l'IIFE In/Out lit pour `outT`… sinon `phRef.current`) ;
# `dzPlanHist` : `var dzPlanHist={t:0};` posé en REPLI dans R_M16REF, à côté
# de `dzTracksRef`.
# ── DZ2 (D-13) : les deux rectangles, après le cadre .svm-tf ─────────────
A_DZ2 = '            r.jsx("div",{className:"svm-tfbadge",ref:tfBadgeRef})]}):null,'   # attendu 1/1, patcher 0
R_DZ2 = (A_DZ2 + '\n'
         '          liveOn&&sel&&sel.tr==="v1"&&DzTracks.dzOf(sel)?r.jsx(DzTracks.DzRects,{dz:sel.dz,\n'
         '            box:(function(){var h=liveHostRef.current;return h?{w:h.clientWidth,h:h.clientHeight}:{w:1,h:1}})(),\n'
         '            onChange:function(nd){var id=selRef.current,now=Date.now();\n'
         '              if(now-(dzPlanHist.t||0)>600)pushHistory();dzPlanHist.t=now;\n'
         '              setClips(clipsRef.current.map(function(k){return k.id===id?Object.assign({},k,{dz:nd}):k}));setDirty(!0)}}):null,')
# MESURER le parent : `.dzm-dzwrap` est en `position:absolute;inset:0` — le
# conteneur du lecteur doit être positionné ET ne pas porter `vzoom` (sinon
# les % sont faux) ; si `.svm-tf` est ce conteneur, poser DzRects DANS le
# bloc `.svm-tf` plutôt qu'après. Rapporter la mesure (offsetWidth des
# rectangles vs du cadre).
# ── DZ3 (D-13) : le zoom EN DIRECT — REPLI dans R_V3 (l'ancre
# `  function liveSync(){` est consommée par V3) : après la ligne du voile,
# ajouter :
#   try{var _dzh=liveHostRef.current,_dzc=<le clip V1 actif que liveSync calcule (svmActiveV1)>,
#     _dzv=_dzh&&_dzh.querySelector("video");
#     if(_dzv){var _dzd=_dzc&&DzTracks.dzOf(_dzc);
#       _dzv.style.transformOrigin="0 0";
#       _dzv.style.transform=_dzd?DzTracks.dzCss(_dzd,(<tête>-_dzc.start)/Math.max(.04,_dzc.end-_dzc.start)):""}}catch(_e){}
# — la <tête> et le clip actif sont CEUX que le voile V3 lit déjà dans R_V3
# (même variable, mesurer son nom) ; si liveSync calcule le clip actif
# APRÈS la ligne du voile, poser ce bloc là où `liveClip` est connu.
# ── DZ4 (D-13) : le payload — REPLI dans R_TT10 si la ligne suivante de la
# vitesse n'est pas 1/1, sinon section propre :
A_DZ4 = "           Math.abs(c.speed-1)>1e-6)o.speed=Math.round(c.speed*100)/100;"   # MESURER 1/1, patcher 0
R_DZ4 = (A_DZ4 + '\n'
         '        /* D-13 : le zoom dynamique — joint seulement s\'il existe (payload d\'avant sinon) */\n'
         '        if(c.tr==="v1"&&DzTracks.dzOf(c))o.dz=DzTracks.dzOf(c);')
```

Rappels : `renderPayload` tourne dans le composant (pas de `x.useRef` neuf) ; `dzPlanHist` en repli R_M16REF ; quatre références `DzTracks.` de plus dans le bundle **au moins** (PlanProps, dzOf ×3, DzRects, dzCss…) → remesurer la sonde dzcout et l'écrire.

- [ ] **Étape 4 : bancs.** `test_montage_bundle.py` : pins `DZ1_remplace`/`DZ2_remplace`/`DZ4_remplace` par la boucle, replis nommés (`dzPlanHist` ×1 dans R_M16REF, bloc DZ3 dans R_V3 : `s.count("DzTracks.dzCss(") == 1`), compte de référence mis à jour ; `--check` (97+ ancres) ; `repatch_all --from montage` puis `--list` ; `node --check` ; CRLF == LF ; sonde dzcout remesurée et le nombre écrit dans `patch_bundle_dzcout.py:279` avec sa ligne d'historique.

- [ ] **Étape 5 : commit** `--only montage.js patch_bundle_montage.py montage.css test_montage_edition.py test_montage_bundle.py patch_bundle_dzcout.py index-BEOJX8L5.js` : `montage : D-13 - zoom dynamique, hote des proprietes de plan, rectangles du lecteur`. Preuve écran par le contrôleur : sélectionner un clip V1 réel → « Zoom dyn. : zoom avant » → deux rectangles vert/rouge dans le lecteur, glisser le rouge (PointerEvent sur `.dzm-dzrect[data-k=fin]`) → `dz.x1` change, Ctrl+Z, lecture : la `<video>` porte un `transform` qui grandit, Preview 480p grave le zoom.

---

## Tâche 3 — D-15 backend : `retime` blend / flow entre `setpts` et `fps`

**Files :** modifier `backend/app/services/montage_service.py`, `backend/tests/test_montage_l3.py` (`[2]`).

- [ ] **Étape 1 : banc rouge**, section `[2]` :

```python
print("\n[2] D-15 retime : blend / flow s'intercalent entre setpts et fps")
_v1_retime = A("_v1_retime", lambda c: "ABSENT")
check("d15_nearest_absent_ou_inconnu_rend_none",
      _v1_retime({}) is None and _v1_retime({"retime": "nearest"}) is None and _v1_retime({"retime": "zzz"}) is None
      and _v1_retime({"retime": 3}) is None)
check("d15_blend_et_flow_sont_les_deux_valeurs", _v1_retime({"retime": "blend"}) == "blend" and _v1_retime({"retime": "flow"}) == "flow")
_c0 = BUILD(); _cs = BUILD(speed=2.0)
check("d15_sans_retime_les_commandes_sont_l_historique",
      BUILD(retime=None) == _c0 and BUILD(retime=None, speed=2.0) == _cs and "tblend" not in _cs and "minterpolate" not in _cs)
_cb = BUILD(speed=2.0, retime="blend")
check("d15_blend_pose_tblend_average_entre_setpts_et_fps",
      "setpts=PTS/2,tblend=all_mode=average,fps=25," in _cb, _cb[:400])
_cf = BUILD(speed=0.5, retime="flow")
check("d15_flow_pose_minterpolate_mci_a_la_cadence_du_canvas_entre_setpts_et_fps",
      "setpts=PTS/0.5,minterpolate=fps=25:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none,fps=25," in _cf, _cf[:400])
check("d15_sans_vitesse_retime_ne_change_rien",
      BUILD(retime="flow") == _c0 and BUILD(retime="blend") == _c0)
_cfz = BUILD(speed=0.5, retime="flow", dz={"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "lin"})
check("d15_avec_dz_l_ordre_est_setpts_retime_fps_zoompan_format",
      _cfz.find("setpts=PTS/0.5,minterpolate=") > 0 and _cfz.find(":scd=none,fps=25,zoompan=") > 0 and _cfz.find(":fps=25,format=yuv420p,tpad=") > 0, _cfz[:500])
```

- [ ] **Étape 2 : lancer → rouge.**

- [ ] **Étape 3 : implémenter.** Sous `_dz_filter` :

```python
# D-15 (22/09/2026) — RETIME. Champ optionnel `retime` d'un clip V1 :
# "nearest" (historique : fps= duplique ou saute, None) | "blend" (tblend
# moyenne deux images voisines : flou de mouvement au ralenti, traîne à
# l'accéléré) | "flow" (minterpolate à compensation de mouvement, LENT).
# Sans vitesse, aucun sens : ignoré. MESURÉ le 22/09 : les deux passent en
# aval d'un setpts et CHANGENT le nombre d'images → posés entre
# `setpts=PTS/spd` et `fps={fps}`, le tpad/trim aval ramenant à seg_durs[k].
_RETIME = {"blend": "tblend=all_mode=average",
           "flow": "minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none"}


def _v1_retime(c: dict) -> str | None:
    v = c.get("retime")
    return v if isinstance(v, str) and v in _RETIME else None
```

Dans le préfixe de segment (branche `if spd:` de T1) : `rt = s.get("retime"); rtp = f",{_RETIME[rt].format(fps=fps)}" if rt in _RETIME else ""` puis `f"setpts=PTS/{sfx_service.fnum(spd)}{rtp},fps={fps}{dzp},format=yuv420p"`. Dans `/render`, `"retime": _v1_retime(c),` dans la spec V1. Docstring : règle « D-15 ».

- [ ] **Étape 4 : mesure ffmpeg réelle** (SKIP sans ffmpeg) : `testsrc2` 2 s, `speed=0.5, retime="flow"` → code 0, `nb_frames` = 100 à 25 i/s (durée timeline 4 s : `tpad/trim` tiennent) — ATTENTION : `d` timeline = `min(want, d_src/spd)` ; poser `end-start=4`, `src_dur=2` et vérifier la durée de sortie par `ffprobe`.

- [ ] **Étape 5 : vert, l2 78/0, commit** : `montage : D-15 - retime blend et flow entre setpts et fps`.

---

## Tâche 4 — D-15 client : l'interpolation dans l'hôte, la rampe par division

**Files :** modifier `frontend/patches/montage.js`, `scripts/patch_bundle_montage.py` (RT1 = extension de R_DZ4), `backend/tests/test_montage_edition.py` (`[8]`), `backend/tests/test_montage_bundle.py`, `scripts/patch_bundle_dzcout.py`.

- [ ] **Étape 1 : banc rouge**, section `[8]` :

```javascript
/* [8] D-15 : interpolation et rampe de vitesse */
out.rt_of=[T.retimeOf({retime:"flow"}),T.retimeOf({retime:"blend"}),T.retimeOf({retime:"nearest"}),T.retimeOf({}),T.retimeOf({retime:9})];
var RC=[{id:"p1",tr:"v1",start:0,end:4,srcIn:1,speed:2,src:{job_id:"j"}},{id:"p2",tr:"v1",start:4,end:6,src:{job_id:"j"}}];
var RR=T.rampe(RC,"p1",2,1,4);
out.rt_rampe=RR&&RR.clips.map(function(c){return [c.id===RR.left?"L":c.id===RR.right?"R":c.id,c.start,c.end,c.srcIn,c.speed||1]});
out.rt_rampe_refus=[T.rampe(RC,"p1",0.1,1,2).refus,T.rampe(RC,"p1",3.9,1,2).refus,T.rampe(RC,"zz",2,1,2).refus,T.rampe(RC,"p2",5,1,2).refus];
out.rt_rampe_pur=JSON.stringify(RC[0])==='{"id":"p1","tr":"v1","start":0,"end":4,"srcIn":1,"speed":2,"src":{"job_id":"j"}}';
```

Python :

```python
print("\n[8] D-15 interpolation et rampe")
check("rt_of_ne_rend_que_blend_ou_flow_sinon_null",
      D.get("rt_of") == ["flow", "blend", None, None, None], D.get("rt_of"))
check("rt_rampe_fend_a_t_et_pose_les_deux_vitesses_srcin_propage_a_l_ancienne_vitesse",
      D.get("rt_rampe") == [["L", 0, 2, 1, 1], ["R", 2, 4, 5, 4], ["p2", 4, 6, 0, 1]] or D.get("rt_rampe") == [["L", 0, 2, 1, 1], ["R", 2, 4, 5, 4], ["p2", 4, 6, None, 1]], D.get("rt_rampe"))
check("rt_rampe_refuse_les_bords_a_moins_de_0_3_s_l_inconnu_et_le_hors_clip",
      "rt_rampe_refus" in D and D["rt_rampe_refus"] == ["bord", "bord", "clip", "hors"], D.get("rt_rampe_refus"))
check("rt_rampe_pur", D.get("rt_rampe_pur") is True)
```

(la propagation de `srcIn` : la partie droite commence à `srcIn + (t−start)·speed_ancienne` = 1 + 2·2 = 5 — **la même règle que `dzmCarve`** ; si `dzmCarve` rend un `srcIn` différent, c'est la règle de `dzmCarve` qui gagne : corriger la sonde et le dire).

- [ ] **Étape 2 : implémenter** :

```javascript
/* ── D-15 (22/09/2026) : INTERPOLATION ET RAMPE ───────────────────────────
   `retime` = "blend" | "flow" (nearest = absent, l'historique). La RAMPE de
   Resolve devient « diviser à t puis deux vitesses » — dzmCarve fend déjà
   en propageant srcIn à l'ancienne vitesse. Bornes 0,3 s aux deux bords
   (comme les trims). Rend {clips, left, right, refus:""|"clip"|"hors"|"bord"}. */
function dzmRetimeOf(c){var v=c&&c.retime;return v==="blend"||v==="flow"?v:null}
function dzmRampe(clips,id,t,spdL,spdR){
  var cs=Array.isArray(clips)?clips:[],c=cs.filter(function(k){return k&&k.id===id})[0];
  if(!c)return {clips:cs,left:null,right:null,refus:"clip"};
  t=Number(t);if(!(t>c.start&&t<c.end))return {clips:cs,left:null,right:null,refus:"hors"};
  if(t-c.start<.3||c.end-t<.3)return {clips:cs,left:null,right:null,refus:"bord"};
  var cl=function(v){v=Number(v);return isFinite(v)&&v>0?Math.max(.25,Math.min(4,Math.round(v*100)/100)):1};
  var sp=dzmSpeedNum(c),L=Object.assign({},c,{end:dzmR3(t)}),R=Object.assign({},c,{id:c.id+"_r"+Date.now().toString(36),start:dzmR3(t),
    srcIn:dzmR3((Number(c.srcIn)||0)+(t-c.start)*sp)});
  if(cl(spdL)===1)delete L.speed;else L.speed=cl(spdL);
  if(cl(spdR)===1)delete R.speed;else R.speed=cl(spdR);
  delete R.transition;delete R.transition_s;
  var out=[],i;for(i=0;i<cs.length;i++){if(cs[i]===c){out.push(L);out.push(R)}else out.push(cs[i])}
  return {clips:out,left:L.id,right:R.id,refus:""}}
```

`DzmPlanProps` gagne (props `speed` = `svmSpeedOf(clip)` passé par DZ1 — **modifier R_DZ1 pour passer `speed:svmSpeedOf(sel),head:phc`**) :

```javascript
  var spd=Number(o.speed)||1,rt=dzmRetimeOf(c);
  kids.push(row("Interpolation",sel(rt||"nearest",[["nearest","image voisine"],["blend","fondu d'images"],["flow","flux optique (lent)"]],
    function(v){on({retime:v==="nearest"?void 0:v},!0)},
    spd===1?"Sans effet à 100 % — change d'abord la vitesse":"Qualité du retime (D-15) : fondu = flou de mouvement, flux optique = images intermédiaires calculées"),"rt"));
  var head=Number(o.head),inClip=isFinite(head)&&head-c.start>=.3&&c.end-head>=.3;
  kids.push(row("Rampe",r.jsxs("span",{className:"dzm-plan-hint",children:[
    r.jsx("button",{className:"svm-minibtn",disabled:!inClip,title:inClip?"Diviser le plan à la tête : la partie gauche garde sa vitesse, la droite passe à la vitesse choisie ci-dessous":"Placer la tête à 0,3 s au moins des deux bords du plan",
      onClick:function(){if(typeof o.onRampe==="function")o.onRampe(head,spd,rampSpd)},children:"Diviser à la tête →"}),
    sel(String(rampSpd),[["0.5","50 %"],["0.75","75 %"],["1","100 %"],["1.5","150 %"],["2","200 %"],["3","300 %"]],function(v){setRampSpd(Number(v))},"Vitesse de la partie droite")]}),"rampe"));
```

avec `var st=x.useState(2),rampSpd=st[0],setRampSpd=st[1];` en tête du composant (le composant lit `x` à l'appel). Dans R_DZ1 ajouter `onRampe:function(t,sL,sR){var res=DzTracks.rampe(clipsRef.current,selRef.current,t,sL,sR);if(res.refus){fireNote(res.refus==="bord"?"Trop près d'un bord (0,3 s)":"Impossible de diviser ici");return}pushHistory();setClips(res.clips);setSel(res.right);setDirty(!0)}` — **mesurer les noms** `fireNote`, `setSel` (celui qu'utilise `svmSetV1Speed` `:3141-3178` pour la note, et la sélection dans `clipDown`). Payload (extension de R_DZ4) : `        if(o.speed&&DzTracks.retimeOf(c))o.retime=DzTracks.retimeOf(c);`. Exports : `retimeOf:dzmRetimeOf,rampe:dzmRampe,`.

- [ ] **Étape 3 : bancs, chaîne, sonde, commit** : `montage : D-15 - interpolation dans l hote et rampe par division`. Preuve écran : clip V1 réel à 200 % → « Interpolation : flux optique » persiste après F5 ; tête à 2 s → « Diviser à la tête » → deux clips, le droit à 200 % ; Ctrl+Z.

---

## Tâche 5 — D-16 backend : analyse vidstab en cache par source, transformation dans la chaîne, routes `/stab`

**Files :** modifier `backend/app/services/montage_media.py`, `backend/app/services/montage_service.py`, `backend/tests/test_montage_l3.py` (`[3]`, `[6]`).

- [ ] **Étape 1 : banc rouge**, section `[3]` :

```python
print("\n[3] D-16 stabilisation : analyse en cache, transformation avant le recadrage")
from app.services import montage_media as MM
_v1_stab = A("_v1_stab", lambda c: "ABSENT")
check("d16_stab_absent_ou_faux_rend_none", _v1_stab({}) is None and _v1_stab({"stab": "x"}) is None and _v1_stab({"stab": {"on": False}}) is None)
check("d16_stab_vrai_porte_les_defauts_15_keep_0",
      _v1_stab({"stab": {"on": True}}) == {"smooth": 15, "crop": "keep", "zoom": 0}, _v1_stab({"stab": {"on": True}}))
check("d16_stab_est_clampe_smooth_1_100_zoom_m30_30_crop_black_ou_keep",
      _v1_stab({"stab": {"on": True, "smooth": 999, "crop": "black", "zoom": -80}}) == {"smooth": 100, "crop": "black", "zoom": -30}
      and _v1_stab({"stab": {"on": True, "smooth": 0, "crop": "zzz", "zoom": "7"}}) == {"smooth": 1, "crop": "keep", "zoom": 7})
check("d16_le_cache_stab_a_son_extension_trf", getattr(MM, "_EXT", {}).get("stab") == ".trf")
_sp = getattr(MM, "stab_path", None)
_src = os.path.join(TMP, "s.txt"); open(_src, "wb").write(b"x")
check("d16_stab_path_est_dans_montage_cache_et_ne_fabrique_rien",
      callable(_sp) and str(_sp(pathlib.Path(_src))).endswith("_stab.trf") and not _sp(pathlib.Path(_src)).exists())
_c0 = BUILD()
check("d16_sans_stab_la_commande_est_l_historique", BUILD(stab=None) == _c0 and "vidstab" not in _c0)
_trf = os.path.join(TMP, "a b.trf"); open(_trf, "wb").write(b"TRF1")
_cs = BUILD(stab={"smooth": 20, "crop": "black", "zoom": 5, "trf": _trf}, src_in=1.5)
check("d16_avec_stab_l_entree_n_est_plus_tronquee_par_ss_t",
      "vidstabtransform=" in _cs and " -ss 1.5" not in _cs and " -t " not in _cs.split("-filter_complex")[0], _cs[:300])
check("d16_la_transformation_precede_trim_puis_le_recadrage",
      "vidstabtransform=input='" in _cs and ":smoothing=20:crop=black:zoom=5:optzoom=1:interpol=bilinear,trim=start=1.5:duration=" in _cs
      and _cs.find("vidstabtransform=") < _cs.find("scale=64:64"), _cs[:400])
check("d16_le_chemin_trf_est_echappe_comme_un_ass",
      "input='" + _trf.replace("\\", "/").replace(":", r"\:") + "'" in _cs, _cs[:400])
check("d16_stab_sans_trf_est_ignore_avec_la_commande_historique",
      BUILD(stab={"smooth": 20, "crop": "keep", "zoom": 0}) == _c0)
```

Section `[6]` (routes) :

```python
print("\n[6] D-16 routes /stab")
r = c.post("/api/montage/stab", json={"src": {"job_id": "nope"}}); d = J(r)
check("d16_post_stab_source_inconnue_400_ou_404", r.status_code in (400, 404), r.status_code)
r = c.get("/api/montage/stab", params={"src": json.dumps({"job_id": "nope"})}); d = J(r)
check("d16_get_stab_repond_ready_false_ou_404_sans_fabriquer", r.status_code in (200, 404) and (r.status_code == 404 or d.get("ready") is False), (r.status_code, d))
```

puis, avec la source `testsrc2` réelle de l'espion `/render` (copier `:706-713` de `test_montage_l2.py`, l'enregistrer comme un job `done` avec `video_path` si le pré-vol l'exige — regarder comment `test_montage_l2.py` obtient un `{job_id}` valide) : `POST /stab` → `{ok: True, ready: False, job_id}` la première fois, puis polling `GET /api/jobs/{id}` (≤ 60 s) jusqu'à `done`, `stab_path(src).exists()`, et `POST /stab` → `{ready: True, job_id: None}` la seconde fois. Espion `/render` : un clip V1 avec `stab:{on:true}` → la spec V1 capturée porte `stab` avec `trf` = ce fichier (`_cap["v1"][0]["stab"]["trf"]`), et la commande contient `vidstabtransform`.

- [ ] **Étape 2 : lancer → rouge.**

- [ ] **Étape 3 : implémenter.** `montage_media.py` :

```python
_EXT = {"peaks": ".json", "strip": ".jpg", "proxy": ".mp4", "stab": ".trf"}   # `:79`


def stab_path(src: Path) -> Path:
    """D-16 — le fichier de transformations vidstab d'une source (cache par
    chemin+mtime+genre, comme le proxy). NE FABRIQUE RIEN."""
    return _cache_path(src, "stab")


def stab_detect(src: Path) -> Path:
    """Passe 1 de la stabilisation : vidstabdetect sur TOUTE la source
    (le rendu la relit entière puis trim — les images doivent coïncider).
    Idempotent : rend le fichier s'il existe. Atomique : ffmpeg écrit dans
    un .tmp puis os.replace. shakiness 5 / accuracy 15 = défauts ffmpeg."""
    out = stab_path(src)
    if out.exists():
        return out
    from app.services.subtitle_service import _ff_escape_path
    tmp = _tmp_de(out)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-an",
           "-vf", f"vidstabdetect=shakiness=5:accuracy=15:result='{_ff_escape_path(tmp)}'",
           "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size < 8:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"vidstabdetect a échoué ({r.returncode}) : {(r.stderr or '')[-400:]}")
    os.replace(tmp, out)
    return out
```

(vérifier que `_tmp_de` garde l'extension `.trf` — sa docstring le dit — et que `montage_media` utilise bien `"ffmpeg"` nu comme `proxy()` `:361`.) `montage_service.py`, sous `_v1_retime` :

```python
# D-16 (22/09/2026) — STABILISATION. Champ optionnel `stab` d'un clip V1 :
# {on, smooth 1..100 (défaut 15), crop "keep"|"black", zoom −30..30}. Le
# fichier .trf est résolu PAR SOURCE au rendu (`montage_media.stab_detect`,
# cache chemin+mtime) — jamais envoyé par le client. Dans la chaîne, la
# transformation lit la source ENTIÈRE puis `trim` fait le travail de
# -ss/-t (mesuré : les transformations sont indexées par image d'entrée).
def _v1_stab(c: dict) -> dict | None:
    raw = c.get("stab")
    if not isinstance(raw, dict) or not raw.get("on"):
        return None

    def num(k, lo, hi, dv):
        try:
            f = float(raw.get(k, dv))
        except (TypeError, ValueError):
            f = float("nan")
        return int(round(max(lo, min(hi, f)))) if f == f else int(dv)
    return {"smooth": num("smooth", 1, 100, 15),
            "crop": "black" if raw.get("crop") == "black" else "keep",
            "zoom": num("zoom", -30, 30, 0)}
```

Dans `_build_montage_command` : (a) entrées `:2145-2148` — si `s.get("stab")` est un dict AVEC `trf` existant, émettre `["-i", str(s["path"])]` seul (ni `-ss` ni `-t`) et mémoriser `stab_ok = True` sur le segment ; (b) préfixe — pour ce segment, préfixer la chaîne par `f"vidstabtransform=input='{_ff_escape_path(Path(trf))}':smoothing={st['smooth']}:crop={st['crop']}:zoom={st['zoom']}:optzoom=1:interpol=bilinear,trim=start={sfx_service.fnum(s['src_in'])}:duration={sfx_service.fnum(d_src)},setpts=PTS-STARTPTS,"` avant `scale=` (importer `_ff_escape_path` de `subtitle_service`). `stab` sans `trf` (ou `trf` inexistant) → segment historique + `logger.warning`. **À MESURER par l'implémenteur** : l'audio du segment V1 — si `[{seg_idx[k]}:a]` est référencé quelque part (grep `:a]`), l'entrée non tronquée désynchroniserait le son : dans ce cas garder `-ss/-t` pour un second `-i` audio ou poser `atrim` symétrique ; rapporter la mesure. Dans `/render` (`:2877-2885`) : `st = _v1_stab(c)` ; si `st` : `job.current_step = "Analyse de stabilisation"` (via le même chemin que « Aperçu 480p » dans `/proxy`), `trf = await asyncio.to_thread(MM.stab_detect, p)` dans un `try` (échec → `await _fail(f"Stabilisation impossible : {e}")`), `st["trf"] = str(trf)` ; `"stab": st` dans la spec. Routes, à côté de `/proxy` :

```python
@router.post("/stab")
async def montage_stab_build(request: Request, background_tasks: BackgroundTasks):
    """D-16 — lance (ou confirme) l'analyse vidstab d'une source ; même contrat
    que POST /proxy : {ok, ready, job_id}, suivi par GET /api/jobs/{id}."""
    # copier le corps de montage_proxy_build (:3430-3495) en remplaçant
    # MM.proxy_path → MM.stab_path, MM.proxy → MM.stab_detect,
    # _PROXY_PROVIDER → _STAB_PROVIDER = "montage_stab", "Aperçu 480p" →
    # "Analyse de stabilisation", "Aperçu prêt" → "Analyse prête".


@router.get("/stab")
async def montage_stab_state(request: Request, src: str = ""):
    """{ready: bool} — ne fabrique jamais (même règle que GET /proxy)."""
```

Factoriser si `montage_proxy_build` s'y prête (une fonction `_bg_par_source(request, background_tasks, body, path_fn, build_fn, provider, steps)`) — sinon copier et le dire ; ne PAS toucher au comportement de `/proxy` (l2 78/0 et projets 159/0 le tiennent).

- [ ] **Étape 4 : mesure ffmpeg réelle** (SKIP sans ffmpeg) : `testsrc2` 3 s → `stab_detect` → `.trf` > 1 000 o ; `_build_montage_command` avec `stab` → code 0, `nb_frames` = 75 à 25 i/s.

- [ ] **Étape 5 : vert, l2 78/0, projets 159/0, commit** `--only montage_media.py montage_service.py test_montage_l3.py` : `montage : D-16 - analyse vidstab en cache par source, transformation avant trim, routes stab`.

---

## Tâche 6 — D-16 client : la section Stabilisation, l'analyse suivie par le job

**Files :** modifier `frontend/patches/montage.js`, `scripts/patch_bundle_montage.py` (SB1 = extension de R_DZ4 ; état dans R_M16REF), `frontend/dist/shared/montage.css`, `backend/tests/test_montage_edition.py` (`[9]`), `backend/tests/test_montage_bundle.py`, `scripts/patch_bundle_dzcout.py`.

- [ ] **Étape 1 : banc rouge**, section `[9]` :

```javascript
/* [9] D-16 : stabilisation, cote client */
out.sb_norm=[T.stabNorm({on:true}),T.stabNorm({on:true,smooth:999,crop:"black",zoom:-80}),T.stabNorm({on:false}),T.stabNorm(null),T.stabNorm({on:true,smooth:"x",crop:1,zoom:"7"})];
out.sb_of=[T.stabOf({stab:{on:true,smooth:30}}),T.stabOf({}),T.stabOf({stab:{on:false,smooth:30}})];
out.sb_state=[T.stabState(null),T.stabState({status:"running",progress:40}),T.stabState({status:"done"}),T.stabState({status:"failed",error:"x"})];
```

Python :

```python
print("\n[9] D-16 stabilisation (client)")
check("sb_norm_tient_les_bornes_du_backend_et_rend_null_hors_on",
      D.get("sb_norm") == [{"on": True, "smooth": 15, "crop": "keep", "zoom": 0}, {"on": True, "smooth": 100, "crop": "black", "zoom": -30},
                           None, None, {"on": True, "smooth": 15, "crop": "keep", "zoom": 7}], D.get("sb_norm"))
check("sb_of_lit_le_clip", "sb_of" in D and D["sb_of"] == [{"on": True, "smooth": 30, "crop": "keep", "zoom": 0}, None, None], D.get("sb_of"))
check("sb_state_phrase_les_quatre_etats",
      D.get("sb_state") == ["à analyser", "analyse 40 %", "analysée", "échec : x"], D.get("sb_state"))
```

- [ ] **Étape 2 : implémenter** :

```javascript
/* ── D-16 (22/09/2026) : STABILISATION ───────────────────────────────────
   `stab` = {on, smooth 1..100, crop keep|black, zoom −30..30} — mêmes bornes
   que `_v1_stab`. L'analyse (.trf) vit chez le backend, par source : le
   client la DEMANDE (POST /api/montage/stab) et la suit par GET /api/jobs/
   {id} — c'est le premier consommateur client d'un job « par source ». */
function dzmStabNorm(raw){
  if(!raw||typeof raw!=="object"||!raw.on)return null;
  var n=function(v,lo,hi,dv){v=Number(v);return isFinite(v)?Math.round(Math.max(lo,Math.min(hi,v))):dv};
  return {on:!0,smooth:n(raw.smooth,1,100,15),crop:raw.crop==="black"?"black":"keep",zoom:n(raw.zoom,-30,30,0)}}
function dzmStabOf(c){return c&&c.stab?dzmStabNorm(c.stab):null}
function dzmStabState(job){
  if(!job)return "à analyser";
  if(job.status==="done")return "analysée";
  if(job.status==="failed")return "échec : "+String(job.error||"?");
  return "analyse "+Math.round(Number(job.progress)||0)+" %"}
```

`DzmPlanProps` gagne la section (props `stabJob` = état `{status,progress,error}|null` du job en cours pour CETTE source, `onStab()` = déclenche l'analyse) :

```javascript
  var sb=dzmStabOf(c);
  kids.push(row("Stabilis.",r.jsxs("span",{className:"dzm-plan-hint dzm-stab",children:[
    r.jsx("input",{type:"checkbox",checked:!!sb,title:"Stabiliser le plan (vidstab, deux passes au rendu)",
      onChange:function(e){on({stab:e.target.checked?dzmStabNorm({on:!0}):void 0},!0)}}),
    r.jsx("button",{className:"svm-minibtn",disabled:!sb||(o.stabJob&&o.stabJob.status!=="done"&&o.stabJob.status!=="failed"),
      title:"Analyser la source maintenant (sinon le rendu le fera, plus long)",onClick:function(){if(typeof o.onStab==="function")o.onStab()},children:"Analyser"}),
    r.jsx("span",{className:"dzm-stab-st","data-st":o.stabJob?o.stabJob.status:"",children:sb?dzmStabState(o.stabJob):""})]}),"stab"));
  if(sb){
    var rng=function(key,lo,hi,label,title){return row(label,r.jsxs("span",{className:"dzm-plan-hint",children:[
      r.jsx("input",{type:"range",min:lo,max:hi,value:sb[key],title:title,
        onChange:function(e){var p={};p[key]=Number(e.target.value);on({stab:dzmStabNorm(Object.assign({},sb,p))},!1)}}),
      " "+sb[key]]}),"stab-"+key)};
    kids.push(rng("smooth",1,100,"Lissage","Fenêtre de lissage (images) — 15 par défaut"));
    kids.push(rng("zoom",-30,30,"Zoom","Zoom fixe en % pour cacher les bords (0 = optzoom)"));
    kids.push(row("Bords",sel(sb.crop,[["keep","garder"],["black","noir"]],function(v){on({stab:dzmStabNorm(Object.assign({},sb,{crop:v}))},!0)},"Que faire des bords découverts"),"stab-crop"))}
```

Dans R_DZ1, passer `stabJob:dzStabJobs[JSON.stringify(sel.src)]||null, onStab:function(){dzStabStart(sel.src)}` ; en REPLI R_M16REF (à côté de `dzTtAdd`) :

```javascript
  var stDzStab=x.useState({}),dzStabJobs=stDzStab[0],setDzStabJobs=stDzStab[1];
  function dzStabStart(src){
    var key=JSON.stringify(src);
    fetch("/api/montage/stab",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({src:src})})
      .then(function(r2){return r2.json()}).then(function(d){
        if(d&&d.ready){setDzStabJobs(function(m){var n=Object.assign({},m);n[key]={status:"done"};return n});return}
        if(!d||!d.job_id){setDzStabJobs(function(m){var n=Object.assign({},m);n[key]={status:"failed",error:(d&&d.error)||"refus"};return n});return}
        var tick=function(){fetch("/api/jobs/"+d.job_id).then(function(r3){return r3.json()}).then(function(j){
          var st=String(j.status||"").toLowerCase(),fin=st==="done"||st==="failed";
          setDzStabJobs(function(m){var n=Object.assign({},m);n[key]={status:fin?st:"running",progress:j.progress||0,error:j.error||null};return n});
          if(!fin)setTimeout(tick,1500)}).catch(function(){})};
        setDzStabJobs(function(m){var n=Object.assign({},m);n[key]={status:"running",progress:10};return n});tick()})
      .catch(function(e){setDzStabJobs(function(m){var n=Object.assign({},m);n[key]={status:"failed",error:String(e)};return n})})}
```

(**mesurer** la casse de `job.status` rendue par `GET /api/jobs/{id}` — `launchRender` compare quoi ? — et le nom exact de l'état `progress`). Payload (extension de R_DZ4) : `        if(c.tr==="v1"&&DzTracks.stabOf(c))o.stab=DzTracks.stabOf(c);`. Exports : `stabNorm:dzmStabNorm,stabOf:dzmStabOf,stabState:dzmStabState,`. CSS : `.dzsvm .dzm-stab-st[data-st="done"]{color:#3fbf5a}.dzsvm .dzm-stab-st[data-st="failed"]{color:#e0453f}.dzsvm .dzm-stab input[type=range]{width:90px;vertical-align:middle}`.

- [ ] **Étape 3 : bancs, chaîne, sonde, commit** : `montage : D-16 - section stabilisation, analyse suivie par le job`. Preuve écran : cocher « Stabilis. » → « à analyser » ; « Analyser » → « analyse n % » → « analysée » ; F5 → `stab` persiste ; Preview 480p : le journal montre `vidstabtransform`.

---

## Tâche 7 — D-14 : keyframes d'échelle et d'opacité sur les overlays (backend + client)

**Files :** modifier `backend/app/services/montage_service.py` (`_motion_points`, chaîne overlay `:2317-2382`), `backend/tests/test_montage_l3.py` (`[4]`), `frontend/patches/montage.js`, `scripts/patch_bundle_montage.py` (KF1…KF4), `backend/tests/test_montage_edition.py` (`[10]`), `backend/tests/test_montage_bundle.py`, `scripts/patch_bundle_dzcout.py`.

**Le point dur, à MESURER AVANT d'écrire** (le plan ne tranche pas, il impose une mesure) : la largeur d'overlay est figée (`ow2`). Trois candidats pour animer l'échelle, à essayer sur `testsrc2` 3 s + un PNG RGBA 200×100 en overlay, dans le scratchpad, SOUS POWERSHELL :

- **A — `sendcmd` sur `scale@mps`** (`scale` accepte les commandes `w`/`h`) : `[1:v]sendcmd=c='0.0 scale@mps w 100;0.04 scale@mps w 104;…',scale@mps=w=100:h=-2,format=rgba[ov];[0:v][ov]overlay=…` — passe si ffmpeg rend 0 ET que `ffprobe` compte 75 images ET qu'une image à t=2,5 s montre l'overlay plus large (lecture Pillow de deux `-frames:v 1` à t=0,2 et t=2,5, largeur du rectangle non transparent).
- **B — `zoompan` sur l'overlay paddé** : `scale=w={owmax}:h=-2,format=rgba,pad=w={F}:h={F}:x=(ow-iw)/2:y=(oh-ih)/2:color=black@0,zoompan=z='{smax/smin}/(lerp)':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=1:s={F}x{F}:fps={fps}` — passe si `zoompan` accepte `rgba` (sinon l'alpha est perdu : mesurer que le fond reste visible autour).
- **Opacité** : `sendcmd` sur `colorchannelmixer@mpo aa` (mesurer `ffmpeg -h filter=colorchannelmixer` : « supports … commands ») ; repli mesuré : le mécanisme de `effects_engine._timed` (`split` + `blend@…:all_opacity` piloté par `sendcmd`), qui EST le précédent du dépôt.

Retenir le premier candidat qui passe, l'écrire dans la docstring avec la mesure, et **si aucun ne passe pour l'échelle, livrer l'opacité seule et dater l'écart** (« l'échelle reste statique — mesuré le <date> : A échoue sur …, B perd l'alpha »). Ce qui suit suppose A pour l'échelle et `sendcmd` pour l'opacité ; adapter les assertions de forme (pas de sens) au candidat retenu.

- [ ] **Étape 1 : banc rouge**, section `[4]` :

```python
print("\n[4] D-14 keyframes d'echelle et d'opacite sur les overlays")
_mp = A("_motion_points", lambda c: "ABSENT")
pts = _mp({"start": 1, "end": 4, "motion_points": [{"t": 0, "x": .5, "y": .5, "scale": .5, "opacity": 1},
                                                   {"t": 3, "x": .5, "y": .5, "scale": 1.5, "opacity": .2, "rotate": 10}]})
check("d14_les_points_portent_scale_et_opacity_ou_none",
      isinstance(pts, list) and len(pts) == 2 and len(pts[0]) == 6 and pts[0][4] == .5 and pts[0][5] == 1.0
      and pts[1][4] == 1.5 and pts[1][5] == .2 and pts[1][3] == 10.0, pts)
pts2 = _mp({"start": 0, "end": 3, "motion_points": [{"t": 0, "x": .5, "y": .5}, {"t": 3, "x": .6, "y": .5, "scale": 9, "opacity": -1}]})
check("d14_scale_clampe_0_05_3_opacity_0_1_absent_none",
      isinstance(pts2, list) and pts2[0][4] is None and pts2[0][5] is None and pts2[1][4] == 3.0 and pts2[1][5] == 0.0, pts2)
_mp_cmds = A("_mp_cmds", lambda *a, **k: "ABSENT")
cm = _mp_cmds([(0.0, 0.5), (2.0, 1.5)], "scale@mps0", "w", lambda v: str(int(round(v * 100))), 0.0, 2.0)
check("d14_mp_cmds_echantillonne_a_1_25_de_la_premiere_a_la_derniere_cle",
      isinstance(cm, str) and cm.startswith("0 scale@mps0 w 50;") and "1 scale@mps0 w 100;" in cm and cm.rstrip(";").endswith("scale@mps0 w 150")
      and cm.count(";") >= 49, cm[:160])
# la chaîne overlay : reprendre OV() du banc pistes_rendu (ou construire un
# overlay minimal comme test_montage_l2 le fait pour V2) puis :
_ov = OVBUILD(motion_points=[{"t": 0, "x": .5, "y": .5, "scale": .5, "opacity": 1}, {"t": 2, "x": .5, "y": .5, "scale": 1.5, "opacity": .2}])
check("d14_l_echelle_animee_passe_par_scale_at_mps_et_sendcmd", "scale@mps" in _ov and "sendcmd=c='" in _ov and " w " in _ov, _ov[:400])
check("d14_l_opacite_animee_passe_par_colorchannelmixer_at_mpo_et_sendcmd", "colorchannelmixer@mpo" in _ov and " aa " in _ov, _ov[:400])
_ov0 = OVBUILD(motion_points=[{"t": 0, "x": .5, "y": .5}, {"t": 2, "x": .6, "y": .5}])
check("d14_sans_scale_ni_opacity_sur_les_points_la_chaine_est_celle_de_l2", "sendcmd" not in _ov0 and "@mps" not in _ov0 and "@mpo" not in _ov0, _ov0[:300])
```

- [ ] **Étape 2 : implémenter** — `_motion_points` rend des 6-uplets `(t, x, y, rotate|None, scale|None, opacity|None)` (clamps `0.05..3` et `0..1`, NaN → None avec warning) ; adapter les trois lecteurs existants (`rpts`, `xpts`, `ypts` `:2358-2374`) à l'indice — **pas de changement de forme pour eux** ; `_mp_cmds(pairs, target, opt, fmt, t_min, t_max)` échantillonne à `_RAMP_STEP` (importer de `effects_engine` ou redéclarer `1/25` avec le commentaire) en `_mp_lerp` python (interpolation linéaire entre paires, constante hors bornes) ; dans la chaîne transformée (`:2333-2337`), si un point porte `scale` : `sendcmd=c='…',scale@mps{j}=w={ow2}:h=-2` à la place de `scale={ow2}:-2`, et si un point porte `opacity` : `colorchannelmixer@mpo{j}=aa={op}` avec un second `sendcmd` (ou le même `c=` cumulé) ; horloge = celle de la rotation (LOCALE, `:2358`), mesurer que `sendcmd` lit la même. Client : `dzmMpLerp2(pts,tl,key,dv)` pur (lerp sur le sous-ensemble des points qui portent `key`, comme `svmMpLerp`), sections **KF1** `svmOvTfAt` (`:1502-1511`, `scale:base.scale` → `scale:DzTracks.mpLerp2(pts,tl,"scale",base.scale)` ; ancre = la ligne exacte, mesurer 1/1), **KF2** `svmMpApply` (`:2749-2757`) garde `scale`/`opacity` des points (ancre `motion_points:res.pts});` mesurer), **KF3** champs Échelle/Opacité de `ovInspector` : quand `mp`, écrire sur le point le plus proche via `svmMpField(sel,{scale:v})` / `{opacity:v}` au lieu du clip (mesurer que `svmMpField` pose un patch générique sur le point — `:2798-2814` ; sinon étendre par une pure `dzmMpPatch(pts,t,patch)`), infobulle « l'échelle ne se keyframe pas » réécrite, **KF4** payload : le bloc `if(c.tr==="v2"){` est CONSOMMÉ (patcher 1) → replier dans son remplacement : `q.scale`/`q.opacity` joints quand présents. Live : `liveSync` applique déjà `svmOvTfAt` (échelle) ; pour l'opacité, mesurer où `opacity` est appliqué à l'overlay vivant et y lire `mpLerp2(...,"opacity",c.opacity)` (repli dans R_V3 si la ligne est consommée).

- [ ] **Étape 3 : banc `[10]`** (`mpLerp2` : sous-ensemble, constante hors bornes, défaut sans point porteur ; `mpPatch` si créé), pins bundle, chaîne, sonde, mesure ffmpeg réelle (SKIP sans ffmpeg : 75 images, largeur d'overlay mesurée à deux instants par Pillow), **commit** : `montage : D-14 - keyframes d echelle et d opacite sur les overlays`. Preuve écran : overlay V2 avec trajectoire à 2 points, Échelle 50 % puis à la tête de fin 150 % → le lecteur vivant grandit en lecture ; Preview 480p.

---

## Tâche 8 — D-9 backend : `adjust_clips`, le post-pass borné après les overlays

**Files :** modifier `backend/app/services/montage_service.py`, `backend/tests/test_montage_l3.py` (`[5]`).

- [ ] **Étape 1 : banc rouge**, section `[5]` :

```python
print("\n[5] D-9 piste d'ajustement : un post-pass borne apres les overlays, avant les titres")
_c0 = BUILD()
check("d9_sans_adjust_clips_la_commande_est_l_historique", BUILD(adjust_clips=None) == _c0 and BUILD(adjust_clips=[]) == _c0)
AJ = [{"start": 1.0, "end": 2.5, "effects": [{"type": "vignette", "intensity": 60}]}]
_ca = BUILD(adjust_clips=AJ, subs_ass=None)
check("d9_un_clip_d_ajustement_pose_build_chain_sur_le_cadre_final",
      "[aj0]" in _ca and "ajfx0" in _ca and _ca.find("[aj0]") > _ca.find("[vext]") if "[vext]" in _ca else "[aj0]" in _ca, _ca[:600])
check("d9_les_bornes_du_clip_deviennent_t0_t1_de_chaque_effet",
      "sendcmd" in _ca and "blend@ajfx0" in _ca and ("1.0" in _ca or " 1 " in _ca) and "2.5" in _ca, _ca[:600])
_t0 = os.path.join(TMP, "t0.ass"); open(_t0, "w", encoding="utf-8").write("[Script Info]\n")
_cat = BUILD(adjust_clips=AJ, titles_ass=[_t0])
check("d9_l_ajustement_precede_les_titres_et_s1",
      _cat.find("[aj0]") < _cat.find("[tt0]") and "[tt0]" in _cat, _cat[:600])
_c2 = BUILD(adjust_clips=[AJ[0], {"start": 3, "end": 4, "effects": [{"type": "vignette", "intensity": 30}]}])
check("d9_deux_clips_s_enchainent_aj0_puis_aj1", "[aj0]" in _c2 and "[aj1]" in _c2 and _c2.find("[aj0]") < _c2.find("[aj1]"), _c2[:600])
check("d9_un_clip_sans_effet_ou_hors_duree_est_ignore",
      BUILD(adjust_clips=[{"start": 1, "end": 2, "effects": []}]) == _c0 and BUILD(adjust_clips=[{"start": 900, "end": 950, "effects": AJ[0]["effects"]}]) == _c0)
check("d9_un_effet_avec_ses_propres_bornes_locales_est_ramene_dans_le_clip",
      "blend@ajfx0" in BUILD(adjust_clips=[{"start": 1, "end": 3, "effects": [{"type": "vignette", "intensity": 60, "t0": 0.5, "t1": 9}]}]))
```

(prendre un `type` qui existe dans `EFFECTS` — vérifier `vignette` dans `effects_engine.EFFECTS`, sinon un autre ; l'assertion « bornes » se lit sur la forme réelle de `_timed` : mesurer une commande et fixer le motif exact, par exemple `"1.0 blend@ajfx0env all_opacity"` — la ligne DOIT rougir quand `t0/t1` ne sont pas posés).

- [ ] **Étape 2 : lancer → rouge** (`TypeError` sur `adjust_clips`).

- [ ] **Étape 3 : implémenter.** Signature : `…, subs_ass=None, titles_ass=None, adjust_clips=None)`. Après les overlays et le maître de durée, AVANT le bloc des titres (`:2525`) :

```python
    # D-9 (22/09/2026) — PISTE D'AJUSTEMENT : chaque clip est un post-pass
    # BORNÉ sur le cadre composé (V1 + overlays), avant les titres et S1 —
    # comme les clips d'ajustement de Resolve, qui agissent sur tout ce qui
    # est dessous. Le bornage est celui de effects_engine._timed (t0/t1 →
    # split + sendcmd + blend, PAS enable=), horloge GLOBALE ici. Un effet
    # qui porte déjà t0/t1 (bornes LOCALES posées par le rack) est ramené
    # dans [start, end]. Sans clip : rien n'est émis (commande historique).
    if not audio_only:
        for j, aj in enumerate(adjust_clips or []):
            try:
                a0 = max(0.0, float(aj.get("start") or 0)); a1 = min(float(total), float(aj.get("end") or 0))
            except (TypeError, ValueError):
                continue
            effs = [e for e in (aj.get("effects") or []) if isinstance(e, dict) and e.get("type") in _fx.EFFECTS and not e.get("off")]
            if a1 - a0 < 0.05 or not effs:
                continue
            bounded = []
            for e in effs:
                e2 = dict(e)
                lt0 = float(e.get("t0") or 0); lt1 = float(e.get("t1")) if e.get("t1") is not None else (a1 - a0)
                e2["t0"] = round(a0 + max(0.0, lt0), 3); e2["t1"] = round(min(a1, a0 + lt1), 3)
                bounded.append(e2)
            parts += _fx.build_chain(bounded, cur, f"aj{j}", f"ajfx{j}", {"w": w, "h": h, "dur": total, "fps": fps})
            cur = f"aj{j}"
```

(`_fx` est importé plus haut dans la fonction, `:2152` ; `total` et `cur` existent à cet endroit — mesurer les noms exacts après le maître de durée.) Dans `/render`, après la collecte V2 : `adjust = [{"start": float(c.get("start") or 0), "end": float(c.get("end") or 0), "effects": c.get("effects") if isinstance(c.get("effects"), list) else []} for c in clips if (meta.get(str(c.get("tr"))) or {}).get("kind") == "adjust"]`, passé `adjust_clips=adjust`. Docstring : règle « D-9 ».

- [ ] **Étape 4 : mesure ffmpeg réelle** (SKIP sans ffmpeg) : `testsrc2` 3 s + un clip d'ajustement `[1, 2]` → code 0, 75 images. **Espion `/render`** (section `[6]`) : projet avec `tracks:[…,{id:"j1",kind:"adjust"},…]` et un clip `{tr:"j1",start:1,end:2,kind:"adjust",effects:[…]}` sans `src` → `_cap["adjust_clips"]` porte ce clip, et un clip `j1` sans effets n'y est pas.

- [ ] **Étape 5 : vert, l2/projets inchangés, commit** : `montage : D-9 - adjust_clips, le post-pass borne apres les overlays`.

---

## Tâche 9 — D-9 client : la piste `j1`, le clip d'ajustement, le rack sur un clip sans source

**Files :** modifier `frontend/patches/montage.js`, `scripts/patch_bundle_montage.py` (AJ1…AJ4 + replis R_TT1, R_M5, R_TT11, R_M16REF), `frontend/dist/shared/montage.css`, `backend/tests/test_montage_edition.py` (`[11]`), `backend/tests/test_montage_bundle.py`, `scripts/patch_bundle_dzcout.py`.

- [ ] **Étape 0 : mesures préalables** (à rapporter) : `grep -c 'id:"j' .bak_montage` (attendu 0 : la lettre « j » est libre — sinon choisir une autre lettre libre et le dire), le tag du patcher qui pose `kind:c.kind` dans le payload (TT2b : joint-il `kind` pour tout clip ou seulement les cartons ?), comment `dzmGroup` classe un genre inconnu (`:?` — l'ajustement doit rejoindre le groupe 0 avec t1/v2), et l'endroit de la barre/menu où `dzmAddDit(ts,"video"|"audio")` est appelé (le « + piste »).

- [ ] **Étape 1 : banc rouge**, section `[11]` :

```javascript
/* [11] D-9 : la piste d'ajustement */
out.aj_kind=[T.kindOf("j1"),T.kindOf("j2","adjust"),T.kindOf("a1"),T.kindOf("t1"),T.kindOf("v1")];
var AJS=T.skin("j1","adjust");
out.aj_skin=[AJS.kind,AJS.type,AJS.id,typeof AJS.h];
var TS0=T.DEFAULTS.map(function(t){return t.id});
var TS1=T.adjustTrack(T.DEFAULTS);
out.aj_track=[TS1.map(function(t){return t.id}),T.adjustTrack(TS1)===TS1,T.adjustTrack([]).map(function(t){return t.id})];
out.aj_new=T.adjustNew(2.5,[{id:"p",tr:"v1",start:0,end:10}],"j1");
out.aj_new_dur=[T.adjustNew(9,[{id:"p",tr:"v1",start:0,end:10}],"j1").end,T.adjustNew(-1,[],"j1")];
out.aj_group=T.group?[T.group("j1","adjust"),T.group("v2","video"),T.group("a1","audio")]:"nogroup";
out.aj_pur=TS0.join()===T.DEFAULTS.map(function(t){return t.id}).join();
```

Python :

```python
print("\n[11] D-9 piste d'ajustement (client)")
check("aj_kind_j_est_le_cinquieme_genre", D.get("aj_kind") == ["adjust", "adjust", "audio", "title", "video"], D.get("aj_kind"))
check("aj_skin_habille_la_piste", "aj_skin" in D and D["aj_skin"][0] == "adjust" and D["aj_skin"][1] == "ajustement" and D["aj_skin"][2] == "j1" and D["aj_skin"][3] == "number", D.get("aj_skin"))
check("aj_track_pose_j1_sous_t1_au_dessus_de_v2_idempotent",
      "aj_track" in D and D["aj_track"][0] == ["t1", "j1", "v2", "v1", "a1", "a2", "a3", "s1"] and D["aj_track"][1] is True and D["aj_track"][2] == ["j1"], D.get("aj_track"))
check("aj_new_est_un_clip_sans_src_de_3_s_a_la_tete",
      "aj_new" in D and D["aj_new"] and D["aj_new"]["tr"] == "j1" and D["aj_new"]["start"] == 2.5 and D["aj_new"]["end"] == 5.5
      and "src" not in D["aj_new"] and D["aj_new"]["kind"] == "adjust" and D["aj_new"]["effects"] == [] and D["aj_new"]["label"] == "Ajustement", D.get("aj_new"))
check("aj_new_est_borne_par_la_fin_de_la_timeline_et_refuse_le_negatif",
      "aj_new_dur" in D and D["aj_new_dur"] == [10, None], D.get("aj_new_dur"))
check("aj_group_range_l_ajustement_avec_les_incrustations",
      D.get("aj_group") == "nogroup" or (isinstance(D.get("aj_group"), list) and D["aj_group"][0] == D["aj_group"][1] and D["aj_group"][0] != D["aj_group"][2]), D.get("aj_group"))
check("aj_pur", D.get("aj_pur") is True)
```

(vérifier les noms exportés : `kindOf`, `skin`, `group`, `DEFAULTS` — lire la queue de `montage.js` ; `adjustNew(t, clips, tr)` : durée 3 s bornée par la fin de la timeline `max(end)` des clips, `null` si `t < 0` ou vide).

- [ ] **Étape 2 : implémenter** : `dzmKindOf` → `k==="j"?"adjust":` ; `dzmSkin` branche `if(kind==="adjust")return {id:id,name:String(id).toUpperCase(),type:"ajustement",h:40,c:"--c-3d",mix:13,kind:"adjust"};` ; `dzmGroup` : `adjust` avec le groupe des incrustations ; `dzmAdjustTrack(ts)` (modèle `dzmTitleTrack` — insère `j1` juste après la piste `title` s'il y en a une, sinon en tête) ; `dzmAdjustNew(t,clips,tr)` ; `dzmAdjustAt(ts)` si utile aux ▲▼. Sections :

```python
# AJ1 (D-9) : « j » = adjust dans trackKind — REPLI dans R_TT1 :
#   '    return k==="a"?"audio":k==="s"?"subs":k==="t"?"title":k==="j"?"adjust":"video"}'
# AJ2 (D-9) : le rack VFX accepte un clip d'ajustement (sans source)
A_AJ2 = '    if(d&&d.Stack&&sel&&sel.src&&trackKind(sel.tr)==="video")'     # 1/1, patcher 0
R_AJ2 = '    if(d&&d.Stack&&sel&&((sel.src&&trackKind(sel.tr)==="video")||sel.kind==="adjust"))'
# AJ3 (D-9) : le payload laisse passer le clip d'ajustement — REPLI dans R_M5 :
#   'clips.filter(function(c){return c.src||c.kind==="title"||c.kind==="adjust"})'
#   et `kind` joint (mesurer TT2b : si `kind:c.kind` n'est joint que pour les cartons, l'étendre à `adjust`).
# AJ4 (D-9) : le « + » de l'en-tête de j1 pose un clip d'ajustement — REPLI dans R_TT11 :
#   '                if(trackKind(tr.id)==="adjust"){dzAjAdd();return}\n' avant la ligne title,
#   et l'infobulle « Poser un clip d'ajustement de 3 s à la tête de lecture — ses effets s'appliquent à tout ce qui est dessous ».
# dzAjAdd en REPLI R_M16REF (modèle dzTtAdd :1022-1030) :
#   function dzAjAdd(){var ts=svmTracksOf(dzProjRef.current),ts2=DzTracks.adjustTrack(ts);
#     if(ts2!==ts){<poser les pistes comme dzTtAdd le fait>}
#     var c=DzTracks.adjustNew(<tête>,clipsRef.current,"j1");if(!c){fireNote("Rien à ajuster ici");return}
#     pushHistory();setClips(clipsRef.current.concat([c]));setSel(c.id);setDirty(!0);fireNote("Clip d'ajustement posé — ouvre le rack VFX pour lui donner des effets")}
# AJ5 (D-9) : l'entrée « piste d'ajustement » dans le menu « + piste » — ancre à MESURER (étape 0) ;
#   si le menu est une section déjà consommée, replier ; sinon section propre.
```

Le lecteur vivant ne joue PAS les effets d'ajustement (comme il ne joue pas les effets par clip) : l'inspecteur le dit (« visible après Preview »). CSS : `.dzsvm .svm-clip[data-kind="adjust"]{background:repeating-linear-gradient(45deg,var(--c-3d),var(--c-3d) 6px,transparent 6px,transparent 12px)}` — mesurer que `.svm-clip` porte un `data-kind` ; sinon ajouter la classe par la section qui rend le clip (mesurer l'ancre) ou renoncer et le dater.

- [ ] **Étape 3 : bancs, chaîne, sonde, commit** : `montage : D-9 - piste d ajustement j1, clip sans source, rack VFX`. Preuve écran : « + piste » → « Piste d'ajustement » → `J1` sous `T1` ; « + » de J1 → clip hachuré de 3 s ; rack VFX → ajouter « vignette » ; F5 → persiste ; Preview 480p : le journal montre `blend@ajfx0`.

---

## Tâche 10 — clôture L3 : mutations, comptes, conception, mémoire

- [ ] `backend/tests/mutations_montage_l3.py` (modèle `mutations_montage_l2.py`) : ≥ 15 mutations en octets — `_dz_spec` sans clamp de `w` ; `_dz_filter` avec `t` au lieu de `it` ; zoompan posé AVANT `fps` ; `_v1_retime` accepte `"nearest"` ; `tblend` posé après `fps` ; `_v1_stab` sans borne de `zoom` ; entrée stab qui garde `-ss` ; `_ff_escape_path` retiré du `input=` ; `_motion_points` qui perd `opacity` ; `_mp_cmds` à pas 1 s ; `adjust_clips` posé APRÈS les titres ; un effet d'ajustement sans `t1` ; `dzmDzNorm` sans borne ; `dzmDzCss` sans le signe moins ; `dzmRampe` qui oublie `srcIn` ; `dzmKindOf` sans « j » ; `dzmAdjustTrack` en queue ; R_AJ2 sans `||sel.kind==="adjust"` (bundle) ; DZ4 sans `o.dz` (bundle) — chacune rougit une ligne nommée, table mesurée, restauration sha256, état MORT distingué.
- [ ] Banc croisé : les bornes client/backend (`dzmDzNorm` vs `_dz_spec`, `dzmStabNorm` vs `_v1_stab`) — lire `montage.js` en octets, extraire les littéraux par regex gardée, comparer aux constantes du service.
- [ ] Comptes de référence des bancs ; `repatch_all --list` ; `node --check` ; hash du bundle ; sonde dzcout finale.
- [ ] Conception §1.1 (D-9) et §1.2 (D-13, D-14, D-15, D-16) : « — **exécuté <date>** : … ; **écarts** : » — D-13 : `zoompan` (pas `crop+scale`, démenti mesuré), fenêtre carrée en fraction (pas de ratio libre), pas d'ease bézier, zoom direct = transform CSS sur la `<video>` (approximation, le 480p fait foi) ; D-15 : rampes par division seulement, pas de courbe, « lisser la jonction » NON livré (écart), Speed Warp écarté ; D-16 : analyse sur la source ENTIÈRE (coût au premier rendu), pas de « camera lock », `crop` keep|black seulement, l'analyse n'est pas purgée (comme le proxy) ; D-14 : candidat retenu pour l'échelle (ou écart si aucun), pas d'éditeur de courbes ; D-9 : une seule piste `j1`, pas d'empilement, effets non joués en direct.
- [ ] Mémoire (`montage-vs-resolve-inventaire.md`, par Edit) : commits, comptes, pièges neufs.
- [ ] Commit, push, rapport. Le déploiement de L3 et la PR vers `main` restent à demander à l'utilisateur.

---

## Relecture du plan (faite avant remise)

- Couverture : D-13 (T1–T2), D-15 (T3–T4), D-16 (T5–T6), D-14 (T7), D-9 (T8–T9), clôture (T10). La ligne §1.2 D-13 dit « ease douce/linéaire » : `doux`/`lin`. La ligne D-15 dit « option lisser la jonction » : NON planifiée (elle demanderait un crossfade entre deux vitesses — à dater en écart). La ligne D-16 dit « bouton Stabiliser + curseurs » : case + Analyser + 2 curseurs + bords.
- Ancres : toutes celles citées ont été comptées le 22/09/2026 dans `.bak_montage` ET dans le patcher (rapport d'exploration §B4–B7, §C) : `ovInspector(),` 1/0, `svm-tfbadge` 1/0, `vfxStackSection` garde 1/0, `if(v1spd){` 1/0 ; consommées → replis : `liveSync(){` (V3), ligne de vitesse du payload (TT10), `trackKind` (TT1), filtre du payload (M5), « + » d'en-tête (TT11), `if(c.tr==="v2"){` (tag à trouver). La ligne `Math.abs(c.speed-1)>1e-6)o.speed=…` est ATTENDUE 1/0 mais pas mesurée : T2 la mesure d'abord.
- Cohérence des noms : `dzmDzNorm/dzOf/dzAt/dzPreset/dzMove/dzScale/dzCss` (T2, lus par DZ1–DZ4), `DzmPlanProps` (T2, étendu T4/T6 sans nouvelle ancre), `dzmRetimeOf/dzmRampe` (T4), `dzmStabNorm/stabOf/stabState` (T6), `dzmMpLerp2` (T7), `dzmAdjustTrack/adjustNew` (T9) ; backend `_dz_spec/_dz_filter` (T1), `_v1_retime/_RETIME` (T3), `_v1_stab` + `MM.stab_path/stab_detect` (T5), `_motion_points` 6-uplets + `_mp_cmds` (T7), `adjust_clips` (T8). `BUILD(**kw)` porte les mots-clés `dz, retime, stab, speed, src_in, adjust_clips, titles_ass, subs_ass` : les cinq premiers passent par `V1SPEC(**kw)` (spec), les trois derniers par la signature — le banc l3 DOIT distinguer les deux (un `BUILD(adjust_clips=…)` qui les pousserait dans la spec V1 rendrait la commande historique et verdirait « sans adjust » à vide : c'est pour cela que `d9_…pose_build_chain…` exige `[aj0]`).
- Le bloc `sonvfx` n'est jamais réécrit ; `son-vfx-montage.css` n'est pas touché ; `/proxy` n'est pas modifié (T5 copie ou factorise sans changer son contrat).
