# Lot L5 du Montage — couleur — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** livrer le lot L5 de `docs/superpowers/specs/2026-09-21-montage-vs-resolve-design.md` (l.176, tableau l.98-104) : D-27 roues lift/gamma/gain, D-28 accord de couleur (= D1 du plan du 03/09), D-29 courbes à points + teinte/saturation par couleur, D-30 masque statique rectangle/ellipse, D-31 scopes, D-32 copier/coller de grade + lightbox, D-33 huit effets ffmpeg de plus.

**Architecture :** le moteur `effects_engine.py` reçoit les nouveaux types (tous rendus par `build_chain`, donc valables sur V1, sur la piste d'ajustement D-9 et, après T3, sur les overlays V2) ; un module pur `mask_region.py` (masque calculé UNE fois puis bouclé) ; un module `color_match.py` (stats YCbCr PIL, `lutyuv`) ; un module `grading.py` (image étalonnée d'un instant, scopes combinés) ; trois routes. Côté client, un cœur pur dans la couche `frontend/patches/montage.js` (roues ↔ canaux, courbes, masque, prise/pose de grade), un panneau « Étalonnage » monté à côté de `DzmPlanProps`, un panneau Scopes, une lightbox, deux actions clavier.

**Tech :** FastAPI, ffmpeg **9.0.1** essentials (le binaire RÉEL de l'app, voir faits mesurés), PIL 12.3.0 (numpy/cv2/scipy ABSENTS), bundle patché en octets, bancs python embarqué, Playwright + Chrome pour les preuves.

---

## Liste de contrôle du lot (cochée par le contrôleur à chaque tâche close = revue conformité + revue qualité + corrections + re-revue + bancs verts)

- [x] T1 — D-27/D-29/D-33 : moteur d'effets (+10 types, Netteté étendue, points de courbe hors du rack) (`196b175`, revue `0569a4f` ; colormatch PIVOTÉ `(val-128)*G+128+O` sur y/u/v, règle unique des courbes + `l5_courbes_vecteurs.json` 60 vecteurs, `_c` hexa strict (injection fermée), huesat force 10 ; reste pour T7 : `_c` ne tolère plus `" #00ff00"`)
- [x] T2 — D-30 masque statique (backend) + effets rendus sur les overlays V2 (`e6ea32f`, revues `2e53857`, `8388b49` ; banc propre `test_montage_l5_masque.py` 58/0 ; V1 `overlay=0:0:shortest=1` (masque bouclé sans fin sinon) ; V2 : copie OPAQUE de la pile (`lutrgb=a=255`) puis alpha d'origine rendu par `blend=c3_mode=multiply` en gbrap — sinon cadre noir (14 effets) puis alpha AU CARRÉ (28 effets) ; masque V2 `maskedmerge` gbrap calculé à la taille de l'overlay (plus de `scale2ref`) ; `_timed` au format `ctx["fmt"]` (V2 = gbrap, sans `fmt` 300/300 identique) ; écarts : `glitch` 48/255, `grain` 7/255 ; restes pour T7 : nom du check `…scale2ref…`, sonde `dims` inutile en cover)
- [x] T3 — D-28 accord de couleur + D-31 scopes + image étalonnée (backend) (`6d98732`, revues `27b6b87`, `9d5b04b` ; offset pivoté `O = μr−128−G(μt−128)` en plage limitée, gain réduit quand O sortirait de ±128 ; `-ss` hors durée ne rend RIEN avec rc 0 → durée du flux v:0 (tag `DURATION` en mkv/webm), recul `max(0,1 ; 1/fps)` + second essai ; cache sûr sous Windows (`os.replace` sur cible ouverte), effets `off` éteints et bornes retirées dans l'image étalonnée ; restes pour T7 : `w=0`→400 vs `w=1`→96, `gather` des deux `frame_stats`, sémaphore `/scopes`)
- [x] T4 — cœur pur client (roues, courbes, masque, grade, temps de source) (`e43c0b0`, revues `463f5c5`, `1e5b164` ; règle unique des courbes rejouée sur les 61 vecteurs partagés, 0 divergence (fuzz 25 311 entrées) ; masque croisé 32/32 avec `mask_region.mask_of` (décimal ASCII des deux côtés) ; effet `off` jamais emporté ni posé ; pchip épinglée au 1e-6 ; vitesse lue sur V1 seulement)
- [x] T5 — panneau « Étalonnage » (roues, courbes, masque, accord, aperçu) + payload + contour du masque (`f60dd60`, revue `f769e9b` ; aucune section neuve (replis R_DZ1/R_DZ2/R_DZ4), panneau après `ovInspector()` ; geste lié au plan SAISI, rien par image en lecture (128,7 → 10,5 ms sur 60 re-rendus), gardes de course bancées en exécution (27 mutations rouges) ; restes pour T7 : BOM dans `mask_region._f`, mention « Lecture » de l'aperçu)
- [x] T6 — scopes sous le lecteur, lightbox, copier/coller de grade (clavier + menus) (`a04930f`, revues `dac4410`, `4bda880`, `04cbc3a` + restes backend `0380ba1` ; section neuve `L5sc1` en queue ; Ctrl+Alt+C/V (Ctrl+Maj+C réservé), un seul chemin/stockage partagé avec le panneau ; lightbox MODALE au clavier ; preuve écran : la barre OUTILS flottante recouvrait TOUTE la rangée du lecteur (défaut préexistant) → rangée remontée en tête de la zone, encart des scopes porté DANS le cadre en `pointer-events:none` ; `/scopes` : sémaphore 2, client parti → 499 sans ffmpeg ; AltGr AZERTY non prouvé au clavier physique)
- [x] T7 — clôture (mutations, banc croisé, conception datée, revue finale, PR) (`c40d4a1` 20 mutations rouges sur 20 + croisé 36/0, `758b98d` conception datée ; revue finale PRÊT À FUSIONNER (227 commandes + 3 267 formes identiques à `81bfde3`) ; retouches `b54087d` (pré-vol de la chaîne dans le harnais de mutations, commentaire daté) et `efd1dea` (note du lecteur sous la rangée remontée, cadre immobile))

Ordonnancement (fichiers disjoints en parallèle, fichiers partagés en série) :
- vague 1 : **T1** (`effects_engine.py`, bancs d'effets) ∥ **T2** (`mask_region.py`, `montage_service.py`) ∥ **T4** (`montage.js` cœur, `test_montage_edition.py`) ;
- vague 2 : **T3** (après T2 : même `montage_service.py`) ∥ **T5** (après T4 : même `montage.js` ; code contre les contrats de T1–T3 écrits ci-dessous) ;
- vague 3 : **T6** (après T5) ; **T7** en dernier.
Les revues tournent EN ARRIÈRE-PLAN sur le SHA livré (worktree temporaire `git worktree add <TMP> <sha>` + copie des deux `.bak_*`, retiré par `git worktree remove --force`) pendant que la tâche suivante avance. Une tâche n'attend jamais la preuve écran d'une autre : le contrôleur joue les preuves par paquets sur 8799.

## Conventions valables pour tout le plan

```powershell
$PY = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"
Set-Location backend
& $PY tests\test_montage_l5.py             # NEUF (T1) — un banc pour tout le backend du lot
& $PY tests\test_montage_etalonnage.py     # pin « etalonnage == 6 » à réaligner en T1
& $PY tests\test_effects_catalog.py ; & $PY tests\test_effects_timing.py   # rendent TOUT le catalogue
& $PY tests\test_montage_edition.py        # 459/0 au départ
& $PY tests\test_montage_bundle.py         # 2271/0
& $PY tests\test_montage_ergonomie.py      # 62/0
& $PY tests\test_montage_l7b.py ; & $PY tests\test_montage_l4.py ; & $PY tests\test_montage_l3.py ; & $PY tests\test_montage_l2.py
& $PY -m pytest tests\test_hygiene_imports.py -q
Set-Location ..
& $PY scripts\patch_bundle_montage.py --check --force-unchained   # 192 ancres (191 triplets) au départ
& $PY scripts\repatch_all.py --from montage ; & $PY scripts\repatch_all.py --list
node --check frontend\dist\assets\index-BEOJX8L5.js ; node --check frontend\patches\montage.js
```

- Un banc = un processus, lu par code de sortie et `=== N passed, M failed ===`. `check(label, cond, detail)`. Règle des assertions négatives (témoin positif dans la même expression), état vide construit, faute n°6 (aucune lecture nue, détail évalué AVANT le court-circuit). Le banc neuf `test_montage_l5.py` reprend l'en-tête de `test_montage_l3.py` l.102-134 (TMP, env, TestClient, `ffmpeg_bin()`, fin `logger.remove()` + `_engine.dispose()` + `rmtree`) et ses fixtures `V1SPEC`/`BUILD`/`OVBUILD`/espion de `/render` (l.148, 169, 645, 1039-1053) — les recopier, ne pas les importer.
- Ancres comptées sur `.bak_montage` (1/0/1) ; ancre consommée → REPLI dans le remplacement hôte (préféré : aucun pin de queue ne bouge) ; toute section neuve prend le préfixe **`L5`** et se met EN QUEUE : elle fait bouger des pins du banc bundle (`PATCHES[-20:]==L7A`, `[-4:]==_L7F`, `_DZ_TAGS[_DZ_I+1:]`, filtre `startswith("L7B")`, compte 191) — les réaligner EN DISANT POURQUOI (écart daté), jamais les affaiblir. `.bak_dzcout` plus récent ⇒ toujours `repatch_all --from montage`. Bundle en OCTETS (CRLF), couche en LF. Sonde `("montage","DzTracks",163)` remesurée et justifiée (elle compte AUSSI les commentaires). Aucun nom d'API navigateur dans les commentaires de la couche (piège `_corps`). `localStorage` en try/catch. Règle E-12 : tout bouton a un `title`, rien ne disparaît, on grise (sinon entrée datée dans `TOLERES`/`_NULLS` de l'ergonomie).
- Backend : `montage_service.py` en CRLF, travailler en octets (Write/Edit ; le Bash de la session désescape `\n` : jamais de heredoc pour du code). Tout service neuf est pur, importé par `montage_service.py`.
- Commits `git commit --only <chemins>`, première ligne sans accent `montage : D-xx - <quoi>`, trailer EXACT `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, push `chantier/montage-l5`. Jamais `git checkout --`, `git stash`, `git add -A`. Aucun serveur relancé (8765 = production de l'utilisateur ; 8799 = preuves du contrôleur). Chaque agent CONTESTE le plan par la mesure (écart daté dans son rapport).
- Aucune dépense (fal, LLM, transcription) dans les bancs ni les preuves — ce lot n'en a besoin nulle part.

## Faits mesurés le 24/09/2026 (relevé lecture seule, état `81bfde3`)

**Binaire.** L'app appelle `ffmpeg` du PATH ; `scripts/launch-silent.vbs` met `%LOCALAPPDATA%\DeepotusVideoGen\bin` EN TÊTE : le binaire de production est **ffmpeg 9.0.1-essentials**, pas 8.1.1 (celui du PATH système, `C:\ffmpeg\ffmpeg-8.1.1-essentials_build\bin`). `effects_preview.ffmpeg_bin()` (l.57) prend `shutil.which("ffmpeg")` : dans un shell de développement c'est 8.1.1. Toutes les mesures ci-dessous ont été rejouées sur les DEUX : valeurs identiques. Scripts et sorties : `<scratchpad>/mesures_l5/`.

**Moteur d'effets** (`backend/app/services/effects_engine.py`, 1152 l.) : `_CATALOG` = 39 entrées (l.989-1091, tuple `(cat, libellé, [params], aide, {surcharges})`, ordre = ordre du rack, `grade_basic` épinglé juste après `grade`), `EFFECTS` = 40 clés (l.737-752, alias `lut`) — DEUX tables à tenir ; `_PARAM_DEFAULTS` l.953-986 (types `range|color|choice|lut` ; nom inconnu → range 0..100 défaut 50) ; `param_spec` l.1111 ; `catalog()` l.1131 ; `CATEGORIES` l.940-949. Constructeur : `(eff, in_lbl, out_lbl, uid, ctx) -> [statements]`, `_one(i,o,filt)` l.38, `_num(eff,key,default,lo,hi)` l.53 (le rendu du Montage n'applique PAS `coerce_params` : chaque constructeur borne lui-même). `build_chain` l.906-928 filtre les types inconnus, remplace un constructeur qui lève par `null`, liste vide → `[in]null[out]`. `_timed` l.840-903 (enveloppe `blend@{uid}env`, bornes locales). « 38 effets » de la conception : FAUX (39/40). `lenscorrection` EXISTE déjà (`_lensdistort` l.460-477). `huesaturation` : 0 occurrence ; `curves` seulement dans GRADES/halation/oldfilm/filmburn. Aucun masque géométrique nulle part (le « Mask du Studio », `graph_effects.py`, vise une couche ENTIÈRE : la conception l.101 « `build_chain` sait déjà appliquer à une région » est FAUSSE).
**Aperçu** : `GET /api/effects/preview` (routes.py:8430, `effects_preview.render_preview` l.348) rend UN effet ; `coerce_params` (l.183-221) ne garde que les params déclarés de type range/color/choice/lut → un paramètre d'un autre type serait supprimé EN SILENCE. Cache `outputs/fxpreview`, `_prune_cache(keep=800, motifs)` l.332.
**Rack client** `frontend/patches/vfxrack.js` (INTOUCHABLE) : `paramRow` l.875-922 — `lut` → champ texte, `color`, `choice` (pastilles ≤ 6), **TOUT AUTRE TYPE → `<input type=range>`** ; `vfxNormCat` l.178 : une catégorie absente de `categories` du backend tombe dans « autres », les catégories servies par le backend font autorité (une catégorie NEUVE déclarée dans `CATEGORIES` apparaît donc toute seule) ; `vfxPreviewUrl` l.380 envoie tous les champs de l'effet sauf `VFX_PRV_SKIP`.
**Bancs qui rendent tout le catalogue** : `test_effects_catalog.py` (chaque effet rendu avec ses défauts sur une image fixe), `test_effects_timing.py` (chaque effet borné t0/t1 sur une vidéo) → tout type neuf doit rendre avec ses défauts. `test_montage_etalonnage.py` l.298-300 : `etalonnage` doit compter **6** → réaligné en T1 (écart daté).
**Rendu Montage** (`montage_service.py`, 5502 l.) : `_build_montage_command` l.3199 ; `_fx` importé l.3385 sous `if not audio_only:` ; chaîne V1 par segment l.3387-3449 (stab → scale/crop cover ou `_reframe_crop` → setsar → vitesse/minterpolate → fps → tblend → zoompan → format=yuv420p → tpad/trim/setpts → **effets EN DERNIER** : `[seg]{chain}[n{k}pre]` + `_fx.build_chain(reff, f"n{k}pre", f"n{k}", f"cfx{k}", {w,h,dur,fps})` l.3438-3449) ; overlays V2 l.3547-3759 : **aucun `build_chain`, le dict V2 (l.4753-4761) ne porte pas `effects`** → un effet posé sur V2 (y compris « étalonnage → tous les plans » sur une piste V2) est envoyé par le client (`renderPayload`, son-vfx-montage.js:3261, `effects` pour TOUS les clips) mais JAMAIS rendu ; post-pass ajustement D-9 l.3901-3951. `/render` l.4465, V1 lu l.4685-4735 (`effects` recopié brut l.4733), V2 l.4737-4761. `_ff_run` l.4354 (`-/filter_complex <fichier>` au-delà de 30 000 car.), `-threads 1` par `-i` l.4000-4028. Routes : `/strip` l.5365 (FileResponse JPEG, `montage_media.strip`), `/title-preview` l.2402 (motif PNG borné `_prev_w`), `_resolve_src` l.2778, `_media_source(request, src, *, video)` l.5134 (`_require_local` 403, 404, 415), `_precalcul_de_fond` l.5399. Aucune route `/thumb`, `/scopes`, `/color-match`.
**Client** : l'aside d'un clip = `DzmPlanProps` (M:6624-6733, monté par R_DZ1, P:4338-4409, gardé `sel.tr==="v1"&&sel.src&&sel.src.job_id`) → `ovInspector()` → … → `vfxStackSection()` (B:5116, rack `DzVfx.Stack`, écritures B:5123-5130 avec rafale 600 ms `DzVfx.hist`) → `gradeAllBtn` (M:1321, `dzmGradeAll` M:1248, `dzmGradeOf` M:1220, `dzmGradeCopy` M:1227 — ne vise que `grade_basic`). Geste commun `dzPlanSet(patch, heavy)` replié dans R_M16REF (P:1060-1064 ; refuse V1 verrouillée, rafale 600 ms, fusion du patch, clé `undefined` supprimée). Payload V1 : R_DZ4 (P:4442, `reframePayload`). D-40 = modèle récent : rangée dans `DzmPlanProps` + replis R_DZ1/R_DZ4 + UNE section `L7Brf1` (aperçu vivant, P:5576-5583, avant DZ1). Lecteur vivant `liveSync()` B:2659-2826 : aucun `style.filter` nulle part ; les éléments du pool sont PARTAGÉS entre plans (remettre `""`). Vignettes : `svmThumb` 78×44 fixe (B:1368) ; `/strip` seulement dans le tiroir Médias (M:6930).
**Clavier** : `SVM_ACTIONS` B:1534-1585 (entrées ajoutées par R_R1, exécutées par R_R2 ; Ctrl+C/V = D-6) ; **Ctrl+Maj+C RÉSERVÉ** (`SVM_COMBO_RESERVED` B:1655, inspecteur des DevTools) ; Alt+Maj+C PRIS (dérivation Maj de la lame) ; Ctrl+Maj+V libre ; Ctrl+Alt+C / Ctrl+Alt+V libres (Ctrl+Alt = AltGr sur AZERTY : AltGr+C et AltGr+V ne produisent aucun caractère en AZERTY français, à confirmer par la preuve). Menus E-6 : actions de `SVM_ACTIONS` apparaissent seules dans ☰ (rubrique par `DZM_MENU_RUB` M:7299) ; menu de clip = littéral `items` de R_EC1 (P:5039 ; assert `R_EC1.count("{sep:!0}") == 4`).
**Comptes au départ** : `len(PATCHES)=191`, `--check` 192 ancres, sonde `DzTracks` 163, bundle 2271/0, édition 459/0 (dernière section [35], `vide_cles` l.1402-1508), ergonomie 62/0.

**Mesures ffmpeg** (9.0.1 = 8.1.1) :
- `colorbalance` : `rs gs bs rm gm bm rh gh bh` (−1..1) + `pl` ; sur un gris 128, `rs=0.3` NE BOUGE RIEN (ombres seules : 0 → 54) — inadapté comme roue « offset ».
- **Roues** : `lutrgb=r='255*pow(clip(L+(val/255)*(G-(L)),0,1),1/Γ)':g=…:b=…` passe ; rampe 0/64/128/192/255 avec L/G/Γ = 0.1/1.2/1.5 → R [54,132,191,242,255], écart ≤ 1 niveau au calcul Python. `eq` `gamma_r/g/b` agit sur les plans YUV, PAS sur RGB (piège).
- **Courbes** : `curves=m='0/0 0.5/0.7 1/1'` (alias `master`/`all`) 128 → 179 ; `r='0/0 0.5/0.6 1/1'` 128 → 153 ; master appliqué APRÈS les canaux ; 64 points passent ; refus −22 si x non strictement croissant, x dupliqué, y hors [0,1] ; UN seul point → constante (TOUJOURS poser x=0 et x=1) ; `interp=pchip` accepté (64 → 83 contre 81 en natural).
- **huesaturation** : options hue (−180..180), saturation (−1..1), intensity, colors (`r+y+g+c+b+m+a`), strength (0..100, défaut 1), rw/gw/bw, lightness ; `saturation=-1:colors=r` ne touche QUE la bande rouge ((200,40,40) → (133,73,73)) ; désaturation complète seulement avec `strength=10`.
- **lutyuv** `clip(val*1.2+10,0,255)` suit la formule (126 → 161) ; 0x808080 vaut Y=126 (plage LIMITÉE) ; PIL `convert("YCbCr")` est en plage PLEINE (JPEG) → conversion obligatoire pour l'accord : `Y_lim = 16 + Y_pl·219/255`, `C_lim = 128 + (C_pl−128)·224/255`.
- **Scopes** (une image, `-ss t -frames:v 1`) : combiné qui marche, 512×512, médiane 0,19 s sur 1080p : `scale=512:-2,format=yuv444p,split=3[a][b][c];[a]waveform=mode=column:display=stack:intensity=0.2[w];[b]vectorscope=mode=color2:graticule=green[v];[c]histogram=display_mode=overlay,scale=256:256[h];[v][h]hstack=inputs=2[vh];[w][vh]vstack=inputs=2` — `hstack` exige des hauteurs égales ; sans `format=yuv444p` après `scale`, vectorscope/histogram échouent (−5).
- **Effets** (1280×720, 2 s, référence 0,23 s) : `hqdn3d` 0,34 s, `atadenoise` 0,26, `deflicker=size=5:mode=am` 0,28, `deband=1thr=…:2thr=…:3thr=…:range=16:blur=1` 0,30, `unsharp` 0,24, `cas=strength=0.6` 0,28, `tmix=frames=3` 0,24, `monochrome=cb=0:cr=0:size=1:high=0` 0,24, `lenscorrection` 0,25, `colortemperature` 0,26 ; **`nlmeans` 88 s (≈1,5 s/image) → ÉCARTÉ** (19 s même allégé). `chromakey=color=0x00FF00:similarity=0.1:blend=0.0` sur V2 puis `overlay` : le vert devient transparent ; `despill=type=green` nettoie le bord ((104,84,85) → (84,0,85)) ; `colorkey` équivalent. Piège : `color=c=green` = 0x007F00.
- **Masque** (effet témoin `hue=s=0,eq=brightness=-0.25`, 1280×720, 3 s ; référence plein cadre 0,29 s) : `geq` recalculé à chaque image 2,19 s (×7) → PROSCRIT ; masque calculé UNE fois `color=c=black:s=WxH:r=FPS:d=1,format=gray,geq=lum='…',trim=end_frame=1,loop=loop=-1:size=1:start=0[m]` 0,36 s, ellipse douce exacte ; `[e]EFFET,format=yuva420p[fx0];[fx0][m]alphamerge[fx];[o][fx]overlay=0:0` : centre = effet (écart 0), coin intact (écart 0), 90 images/3,0 s ; inversion par `negate` du masque exacte. Piège : `drawbox color=white` en gray écrit 235 (plage limitée) → masque plafonné à 92 % : ne PAS utiliser drawbox pour le masque.
- Aucun `.cube` dans le dépôt.

### Décisions prises sur les démentis

1. **D-27 roues** : PAS `colorbalance` (mesuré sans effet sur les tons moyens en offset) ; effet **`wheels`** en `lutrgb` avec la formule mesurée, neuf paramètres **visibles** au rack (curseurs de repli, seule édition possible sur un clip d'AJUSTEMENT D-9 où le panneau Étalonnage n'est pas monté) : `lift_r|g|b` −0,5..0,5 (0), `gamma_r|g|b` 0,25..4 (1), `gain_r|g|b` 0..2 (1). Identité → `null`. L'UI trois disques (canvas maison) est côté client (T5) et convertit disque (x, y) + maître ↔ trois canaux (T4).
2. **D-29 courbes** : effet **`curves`** à points ; les quatre chaînes `pts_m|pts_r|pts_g|pts_b` (« x/y x/y … », 2..16 points, x strictement croissant, extrémités 0 et 1 forcées, valeurs arrondies 1e-3) sont des **paramètres CACHÉS** : le rack rendrait un type inconnu en curseur (mesuré) ; `catalog()` les liste sous une clé neuve `points` (hors `params`), `coerce_params` les garde après `curves_clean` (sinon l'aperçu les perdrait en silence). Rendu `curves=interp=pchip:m='…':r='…':…` (seules les courbes non identité) ; tout identité → `null`. **Teinte/saturation par couleur** = effet **`huesat`** (hue −180..180, saturation −100..100 → /100, strength 1..100, `colors` choix `a r y g c b m`) ; Hue vs Hue/Lum vs Sat/Sat vs Sat **écartés** (conception).
3. **D-33 huit effets** : `lenscorrection` existe déjà (`lensdistort`) et `nlmeans` est écarté (88 s) : les huit sont **`denoise`** (mode `hqdn3d|atadenoise` + intensité), **`deflicker`**, **`deband`**, **Netteté étendue** (`sharpen` gagne `mode` `unsharp|cas`, défaut `unsharp` → commande par défaut octet pour octet inchangée), **`chromakey`** (clé couleur, similarité, fondu, `despill` `aucun|vert|bleu` ; utile sur V2 après T2 — sur V1 l'alpha est perdu par `format=yuv420p` : écart dit dans l'aide), **`tmix`** (`frames` 3|5|7), **`monochrome`** (`cb`, `cr` −1..1), **`huesat`** (compté aussi en D-29). Catalogue : **+10 types** (`wheels`, `curves`, `colormatch`, `huesat`, `monochrome` en `etalonnage` → 11 ; `denoise`, `deflicker`, `deband` dans une catégorie NEUVE `correction` « Correction » ; `chromakey` en `cadrage` ; `tmix` en `mouvement`). La conception disait « +9 » : écart daté.
4. **D-30 masque** : champ de CLIP (V1 et V2) `mask: {shape:"rect"|"ellipse", x, y, w, h (fractions 0..1 du cadre), soft (0..0,5 du petit côté de la forme), inv: bool}` limitant la PILE D'EFFETS du clip ; module pur `mask_region.py` : `mask_of(raw) -> dict|None` (bornes, forme inconnue → None, largeur/hauteur < 0,01 → None) et `mask_graph(m, w, h, fps, lbl) -> str` (geq calculé UNE fois + `trim=end_frame=1,loop=-1`, jamais drawbox) ; branchement dans la chaîne V1 : sans masque, commande OCTET POUR OCTET identique ; avec masque : `[n{k}pre]split[mo{k}][me{k}]` + `build_chain(reff,"me{k}","mf{k}","cfx{k}",ctx)` + `[mf{k}]format=yuva420p[mfa{k}];<masque>[mk{k}];[mfa{k}][mk{k}]alphamerge[mm{k}];[mo{k}][mm{k}]overlay=0:0,format=yuv420p[n{k}]`. Masque sans effet = ignoré.
5. **Effets sur V2** (préalable de chromakey, défaut réel du dépôt) : `/render` lit `effects` et `mask` des clips V2 ; le bloc overlay applique `build_chain` (et le masque) juste APRÈS la mise à l'échelle et AVANT l'opacité/les coins/la rotation, puis `format=rgba` pour garder l'alpha d'un `chromakey`. Sans effet : commande octet pour octet identique.
6. **D-28 accord de couleur** : `color_match.py` = D1 du plan du 03/09 (Reinhard réduit, gain borné 0,5..2) **avec conversion plage pleine → plage limitée** (sinon l'offset est faux sur un `lutyuv` qui travaille en plage limitée) ; `auto_effect(tgt)` = cibles neutres (u, v → 128 plage pleine, écart-type Y relevé à 48 au moins, moyenne Y conservée). Effet `colormatch` visible au rack (six curseurs, conforme au plan D1). Route `POST /api/montage/color-match {target:{src,t}, ref?:{src,t}, auto?:bool}` → `{ok, effect, ref, target}`.
7. **D-31 scopes** : `POST /api/montage/scopes {src, t, effects?, mask?}` → PNG 512×512 (graphe mesuré) calculé sur l'image **étalonnée** (pile du clip appliquée : le scope montre ce que le rendu produira) ; cache `montage_cache` par empreinte ; client : panneau repliable SOUS le lecteur, rafraîchi à l'arrêt (anti-rebond 300 ms), jamais pendant la lecture.
8. **D-32** : Ctrl+Maj+C réservé → actions **`grade_copy` = Ctrl+Alt+C** et **`grade_paste` = Ctrl+Alt+V** (remappables, rubrique « Édition ») + deux entrées du menu de clip + deux boutons du panneau ; presse-papiers `localStorage["dz_montage_grade"]` ; le « grade » = effets des types couleur `DZM_COLOR_TYPES` (`grade`, `lut`, `grade_basic`, `wheels`, `curves`, `colormatch`, `huesat`, `monochrome`) sans bornes temporelles + `mask` ; coller REMPLACE les effets couleur de la cible à la place du premier effet couleur (sinon en queue), garde les autres effets dans leur ordre. **Lightbox** = voile + grille des plans V1 dans l'ordre, chaque vignette = `POST /api/montage/grade-frame` (image étalonnée 240 px au milieu du plan) ; clic = sélectionne le plan et ferme ; Échap ferme. Le bouton « à tous les plans » existant (`grade_basic` seul) reste tel quel (écart daté : non généralisé).
9. **Aperçu** : aucun aperçu vivant par `filter` CSS (il mentirait sur roues/courbes) ; le panneau Étalonnage montre l'**image étalonnée** de la tête (même route `grade-frame`, anti-rebond 400 ms) — c'est l'aperçu de référence.

---

## Tâche 1 — D-27/D-29/D-33 : moteur d'effets

**Fichiers :** modifier `backend/app/services/effects_engine.py` (constructeurs, `EFFECTS`, `_CATALOG`, `_PARAM_DEFAULTS`, `CATEGORIES`, `catalog()`), `backend/app/services/effects_preview.py` (`coerce_params` : points cachés) ; créer `backend/tests/test_montage_l5.py` (section [1]) ; réaligner `backend/tests/test_montage_etalonnage.py` (compte 6 → 11, avec commentaire daté).

Contrats (les autres tâches s'y fient) :

```python
# effects_engine.py
_CURVE_KEYS = ("pts_m", "pts_r", "pts_g", "pts_b")
_HIDDEN = {"curves": _CURVE_KEYS}          # params cachés au rack, listés sous catalog()[t]["points"]

def curves_clean(s) -> str:
    """'x/y x/y …' -> chaîne canonique ; x,y bornés [0,1], arrondis 1e-3, triés,
    x dupliqués fusionnés (dernier gagne), extrémités x=0 et x=1 ajoutées par
    prolongement à la valeur du point le plus proche si absentes, 16 points au plus (au-delà : sous-échantillonné
    en gardant les extrémités). Entrée invalide -> '0/0 1/1'."""

def _wheels(eff, i, o, uid, ctx):   # lutrgb, formule mesurée ; identité -> _one(i, o, "null")
def _curves(eff, i, o, uid, ctx):   # curves=interp=pchip:m='…':r='…':g='…':b='…' (non identité seulement)
def _colormatch(eff, i, o, uid, ctx):  # lutyuv=y='clip(val*G+O,0,255)':u=…:v=…
def _huesat(eff, i, o, uid, ctx):   # huesaturation=hue=…:saturation=…:strength=…:colors=r+y+g+c+b+m+a|<une>
def _monochrome(eff, i, o, uid, ctx)
def _denoise(eff, i, o, uid, ctx)   # mode hqdn3d (4·t:3·t:6·t:4.5·t, t=intensité, défaut 50) | atadenoise
def _deflicker(eff, i, o, uid, ctx) # deflicker=size=N:mode=am, N 2..15
def _deband(eff, i, o, uid, ctx)    # seuils 0.005+0.04·t, range=16, blur=1
def _chromakey(eff, i, o, uid, ctx) # format=yuva420p,chromakey=…[,despill=type=green|blue]
def _tmix(eff, i, o, uid, ctx)      # tmix=frames=3|5|7
# _sharpen : mode 'unsharp' (défaut, commande INCHANGÉE) | 'cas' -> cas=strength=t
```

Bornes (`_PARAM_DEFAULTS`, libellés français) : `lift_*` range −0,5..0,5 pas 0,01 défaut 0 ; `gamma_*` 0,25..4 pas 0,01 défaut 1 ; `gain_*` 0..2 pas 0,01 défaut 1 ; `y_gain|u_gain|v_gain` 0,5..2 défaut 1 ; `y_off|u_off|v_off` −128..128 défaut 0 ; `hue` −180..180 défaut 0 ; `sat` −100..100 défaut 0 (huesat) ; `strength` 1..100 défaut 1 ; `colors` choice `["a","r","y","g","c","b","m"]` ; `cb|cr` −1..1 pas 0,01 défaut 0 ; `mode` : surcharges par entrée (`denoise` `["hqdn3d","atadenoise"]`, `sharpen` `["unsharp","cas"]`) ; `key` color défaut `#00ff00` ; `similarity` 1..100 défaut 10 ; `smooth` 0..100 défaut 0 ; `despill` choice `["aucun","vert","bleu"]` défaut `vert` ; `frames` choice `["3","5","7"]` ; `size` 2..15 défaut 5. Tout nom de paramètre DÉJÀ présent dans `_PARAM_DEFAULTS` avec un autre sens (ex. `size`, `mode`, `blend`) : surcharge par `entry[4]`, jamais de modification du gabarit partagé (mesurer avant).

- [ ] **Étape 1 : banc rouge [1]** (`test_montage_l5.py`, en-tête de l3) :
  - `catalog()` : les dix types neufs présents, `curves` sans `pts_*` dans `params` MAIS `points == ["pts_m","pts_r","pts_g","pts_b"]` (témoin : `grade_basic` n'a PAS de clé `points`) ; `categories()` contient `correction` avec 3 effets ; `etalonnage` = 11.
  - `curves_clean` : `"0.5/0.6"` → `"0/0.6 0.5/0.6 1/0.6"` (extrémité absente = valeur du point le plus proche, jamais un point unique) ; témoin `"0/0 0.5/0.7 1/1"` inchangé ; `"1/1 0/0 0.5/0.7"` trié ; `"0/0 0.5/0.2 0.5/0.7 1/1"` → `"0/0 0.5/0.7 1/1"` (dernier gagne) ; 20 points → 16 dont `0/…` et `1/…` ; `"abc"` et `""` → `"0/0 1/1"` ; y 1,4 → 1.
  - chaque constructeur neuf : identité → la chaîne contient `null` et PAS le filtre (témoin : valeur non neutre → le filtre y est) ; `sharpen` défaut == chaîne d'avant le lot (constante recopiée de `81bfde3`), `mode=cas` → `cas=strength=`.
  - rendu RÉEL (ffmpeg de `ffmpeg_bin()`, `color=c=0x808080:s=64x64:d=1` en rgb24 puis moyenne PIL) : `wheels` gain_r 1,5 → R monte d'au moins 40 et G ±2 ; `curves` pts_m `0/0 0.5/0.7 1/1` → 128 devient 175..183 ; `huesat` colors=r sur la mire trois bandes : bande rouge change, bande verte intacte (≤ 2) ; `colormatch` y_gain 1,2 y_off 10 sur Y ; `chromakey` sur fond 0x00FF00 superposé sur bleu : pixel bleu ≥ 240.
  - `coerce_params("curves", {"pts_m": "0/0 0.5/0.7 1/1", "pts_x": "1"})` garde `pts_m` canonique, jette `pts_x`.
- [ ] **Étape 2 : lancer → rouge** (module sans les types).
- [ ] **Étape 3 : implémenter** (constructeurs bornés par `_num`, `curves_clean`, deux tables, catalogue, `categories`, `coerce_params`), aide française de chaque entrée (≤ 90 caractères ; `chromakey` : « Rend transparente une couleur — sur un plan superposé (V2). »).
- [ ] **Étape 4 : bancs verts** : l5 [1], `test_effects_catalog.py`, `test_effects_timing.py` (ils rendent tout le catalogue : tout type neuf doit rendre avec ses défauts), `test_montage_etalonnage.py` réaligné (6 → 11, commentaire daté 24/09 « L5 : wheels, curves, colormatch, huesat, monochrome »), `test_security_guards.py`, hygiène.
- [ ] **Étape 5 : commit** `montage : D-27 D-29 D-33 - moteur d effets, roues, courbes, huit effets` + push.

## Tâche 2 — D-30 masque statique + effets sur V2 (backend)

**Fichiers :** créer `backend/app/services/mask_region.py` ; modifier `montage_service.py` (chaîne V1 l.3438-3449, bloc overlay V2 l.3547-3759, lecture `/render` V1 l.4685-4735 et V2 l.4737-4761) ; `test_montage_l5.py` section [2].

```python
# mask_region.py — pur, sans ffmpeg
SHAPES = ("rect", "ellipse")
def mask_of(raw) -> dict | None:
    """{shape,x,y,w,h,soft,inv} borné : x,y ∈ [0,1], w,h ∈ [0.01, 1-x|1-y], soft ∈ [0,0.5],
    inv bool ; forme inconnue / non dict / w|h < 0.01 -> None. Arrondi 1e-4."""
def mask_graph(m: dict, w: int, h: int, fps: float, lbl: str) -> str:
    """Une instruction filtergraph : color=c=black:s={w}x{h}:r={fps}:d=1,format=gray,
    geq=lum='<expr>',trim=end_frame=1,loop=loop=-1:size=1:start=0[{lbl}] ;
    ellipse : 255*clip((1-hypot((X-cx)/rx,(Y-cy)/ry))/S,0,1) avec S = max(soft·2,0.002)
    (fraction du rayon) ; rectangle : 255*clip(min(min(X-x0,x1-X),min(Y-y0,y1-Y))/Sp,0,1)
    avec Sp = max(soft·min(pw,ph),1) pixels ; inv -> 255-(…). min() à DEUX arguments."""
```

- [ ] **Étape 1 : banc rouge [2]** : `mask_of` (bornes, forme inconnue → None, `{}` → None, témoin valide rendu) ; `mask_graph` contient `trim=end_frame=1` et `loop=loop=-1` et PAS `drawbox` ; commande V1 SANS `mask` == commande de `81bfde3` octet pour octet (fixture `BUILD` avec et sans effets) ; commande avec `effects` + `mask` contient `alphamerge` ; `mask` sans effets → identique à sans masque ; rendu RÉEL 320×180 2 s `color=gray` + effet `grade_basic` exposition −100 masqué ellipse au centre : pixel centre assombri (écart ≥ 20), coin intact (≤ 2), nombre d'images == 2 s × fps (ffprobe `nb_read_frames` sur `v:0`) ; `inv:true` → l'inverse ; V2 : overlay avec `effects:[{"type":"chromakey"}]` sur une source verte 0x00FF00 au-dessus d'un V1 bleu → pixel du rendu bleu (≥ 240 en B) ; V2 sans effets → commande identique à `81bfde3` ; espion `/render` : `mask` V1 et `effects`/`mask` V2 lus et assainis (masque invalide → absent).
- [ ] **Étape 2 : rouge.** **Étape 3 : implémenter** (MESURER d'abord : `overlay` avec une source bouclée infinie se termine avec la principale — sinon `shortest=1`, écart daté). **Étape 4 : bancs** l5, l3, l4, l7b, l7, l2 verts. **Étape 5 : commit** `montage : D-30 - masque statique et effets rendus sur les overlays V2` + push.

## Tâche 3 — D-28 accord de couleur + D-31 scopes + image étalonnée (backend)

**Fichiers :** créer `backend/app/services/color_match.py`, `backend/app/services/grading.py` ; modifier `montage_service.py` (trois routes) ; `test_montage_l5.py` sections [3] [4].

```python
# color_match.py
def frame_stats(path, t: float = 1.0) -> dict     # {"y":(moy,σ),"u":…,"v":…} en PLAGE LIMITÉE (conversion PIL -> limitée)
def match_effect(ref: dict, tgt: dict) -> dict    # {"type":"colormatch","y_gain",…,"v_off"} gain borné 0.5..2, off -128..128
def auto_effect(tgt: dict) -> dict                # cibles neutres : u,v -> 128, σY >= 48·219/255, moyenne Y conservée
# grading.py
def graded_frame(path, t, effects=None, mask=None, w=512, fmt="png") -> Path   # cache montage_cache, clé sha1
def scopes_png(path, t, effects=None, mask=None) -> Path                        # 512×512, graphe mesuré
```

Routes (`_media_source(request, src, video=True)` pour la garde locale/404/415, `asyncio.to_thread`, `FileResponse` avec `Cache-Control: no-store` pour scopes et `max-age=3600` pour grade-frame) :
- `POST /api/montage/color-match {target:{src,t}, ref?:{src,t}, auto?:bool}` → `{ok, effect, ref, target}` ; ni `ref` ni `auto` → 400.
- `POST /api/montage/scopes {src, t, effects?, mask?}` → `image/png`.
- `POST /api/montage/grade-frame {src, t, effects?, mask?, w?}` → `image/jpeg` (`w` 96..640 pair, défaut 240).
Bornes communes : `t` ≥ 0 (au-delà de la durée → dernière image lisible, mesurer `-ss` hors durée : ffmpeg rend 0 image → reculer à `dur−0,1`), `effects` liste de 16 dicts au plus (au-delà → 400), `mask` par `mask_of`.

- [ ] **Étape 1 : banc rouge [3] [4]** : plan orange `color=c=0xc06030` bruité et plan testsrc2 ; `match_effect` puis rendu par `build_chain` → moyennes Y/U/V alignées à 6/255 (plage limitée, mesurées par `extractplanes` ou PIL reconverti) ; `auto_effect` sur un plan teinté → |u−128| et |v−128| réduits de moitié au moins ; `graded_frame` avec `grade_basic` exposition −100 plus sombre que sans (témoin) ; cache : deuxième appel sans ffmpeg (espion `subprocess.run`) ; `scopes_png` → PNG 512×512 ; routes : 200 + type, 400 (ni ref ni auto, `effects` > 16), 404 source inconnue, 403 hors localhost (entête `client` du TestClient : mesurer comment les bancs l7b testent `_require_local`).
- [ ] **Étape 2–4 : rouge, implémenter, verts** (l5, l7b, hygiène). **Étape 5 : commit** `montage : D-28 D-31 - accord de couleur, scopes et image etalonnee` + push.

## Tâche 4 — cœur pur client

**Fichiers :** `frontend/patches/montage.js` (fonctions pures + exports sur `DzTracks`), `backend/tests/test_montage_edition.py` section [36] (+ clés dans `vide_cles`).

```js
var DZM_COLOR_TYPES=["grade","lut","grade_basic","wheels","curves","colormatch","huesat","monochrome"];
/* roue : disque (x,y) ∈ disque unité + maître m ; angles R 90°, G 210°, B 330° ;
   proj_c = x·cos(θc)+y·sin(θc) ; lift : L_c = clamp(m + 0.25·proj_c, -0.5, 0.5) ;
   gamma : Γ_c = clamp(2^(m + 0.5·proj_c), 0.25, 4) ; gain : G_c = clamp(1 + m + 0.5·proj_c, 0, 2) */
function dzmWheelToRgb(kind,x,y,m)        // -> {r,g,b} arrondis 1e-3 (kind "lift"|"gamma"|"gain")
function dzmWheelFromRgb(kind,rgb)        // -> {x,y,m} (moindres carrés : m = moyenne, x/y = (2/3)Σ(v_c−m)cos|sin θc / k)
function dzmWheelsSet(eff,kind,x,y,m)     // -> NOUVEL effet wheels (crée {type:"wheels"} si eff nul)
function dzmCurveClean(s)                 // mêmes règles que curves_clean (T1) — banc croisé en T7
function dzmCurveParse(s) / dzmCurveStr(pts)
function dzmCurveEval(pts,x)              // pchip (Fritsch–Carlson), comme interp=pchip du rendu
function dzmMaskOf(m)                     // mêmes bornes que mask_of (T2)
function dzmGradeTake(clip)               // -> {effects:[copies sans t0/t1/fade*/ease*/off], mask} | null
function dzmGradePaste(clip,g)            // -> nouveau clip (effets couleur remplacés à la place du 1er, autres gardés, mask posé/retiré)
function dzmColorMatchPut(effects,eff)    // remplace le colormatch existant ou l'ajoute en queue
function dzmSrcTimeAt(clip,head)          // srcIn + (head−start)·(speed||1), borné au plan ; hors plan -> milieu du plan
```

- [ ] **Étape 1 : banc rouge [36]** : aller-retour roue `fromRgb(toRgb(x,y,m))` ≈ (x,y,m) à 1e-2 sur 20 points du disque (hors bornes saturées) ; neutre (0,0,0) → identité exacte (lift 0, gamma 1, gain 1) ; `dzmCurveClean` sur les MÊMES cas que [1] de T1 (valeurs attendues écrites dans ce plan, T1 §Étape 1) ; `dzmCurveEval` monotone sur des points monotones, passe par les points ; `dzmMaskOf` bornes ; `gradeTake` n'emporte ni `t0` ni `grain` (témoin : `wheels` emporté) ; `gradePaste` garde `grain` à sa place et remplace `grade_basic` par `wheels` ; `colorMatchPut` n'en laisse qu'un ; `srcTimeAt` avec vitesse 2 ; pureté (aucune API navigateur, piège `_corps`) ; état vide.
- [ ] **Étape 2–4 : rouge, implémenter, verts** (édition, bundle — le bundle embarque la couche : rejouer `repatch_all --from montage` et la sonde si `DzTracks` bouge). **Étape 5 : commit** `montage : D-27 D-29 D-30 D-32 - coeur pur couleur (client)` + push.

## Tâche 5 — panneau « Étalonnage » + payload + contour du masque

**Fichiers :** `frontend/patches/montage.js` (composant `DzmGradePanel`, lit `r`/`x` à l'appel, hooks après la garde), `scripts/patch_bundle_montage.py` (replis R_DZ1 : montage du panneau à côté de `DzTracks.PlanProps` avec la même garde + hôte `onMatch`/`onFrame` ; R_DZ4 : `mask` dans le payload V1 ; payload V2 : `mask` — mesurer où le payload V2 est construit ; contour : repli dans R_L7BRF1 ou section `L5m1` en queue si aucune ancre hôte ne convient), `frontend/dist/shared/montage.css`, bancs édition [37], bundle, ergonomie.

Contenu du panneau (titre « Étalonnage », rangées `.svm-prop` comme `DzmPlanProps`) :
- **Roues** : trois canvas 96×96 (Lift, Gamma, Gain), point déplaçable (gestes sur `window` comme D-13, pas de `setPointerCapture`), double-clic = remise à zéro, curseur maître sous chaque roue ; écriture `onChange({effects})` par `dzmWheelsSet`, `heavy` au relâcher.
- **Courbes** : canvas 200×200, onglets M/R/G/B, clic = ajoute un point, glisser = déplace (x borné entre voisins), double-clic = retire (extrémités fixes en x), tracé par `dzmCurveEval` ; 16 points max (bouton grisé + `title` au-delà).
- **Masque** : trois boutons Aucun/Rectangle/Ellipse, curseurs X/Y/L/H/Adoucissement, bascule « Inverser » ; grisés sans effet sur le plan (`title` « Le masque limite les effets du plan : ajoutez-en un »).
- **Accord** : « Accorder sur le plan précédent » (voisin gauche V1 par le cœur existant ; grisé sans voisin) et « Auto » → `POST /api/montage/color-match` → `dzmColorMatchPut` ; note d'erreur par `fireNote`.
- **Aperçu étalonné** : `<img>` de `POST /api/montage/grade-frame` (blob → URL révoquée au remplacement), anti-rebond 400 ms, instant = `dzmSrcTimeAt(clip, tête)`.
- **Copier / coller le grade** (boutons ; le clavier et les menus viennent en T6).

- [ ] **Étape 1 : banc rouge [37]** (édition : le composant sous shim React minimal comme [34]) + pins bundle (panneau monté une fois dans R_DZ1, `mask` dans R_DZ4, garde identique à PlanProps) + ergonomie (tout bouton du panneau titré).
- [ ] **Étape 2–4.** Rejouer la chaîne, `--check --force-unchained`, `node --check` ×2, sonde remesurée. **Étape 5 : commit** `montage : D-27 D-29 D-30 D-28 - panneau Etalonnage (client)` + push.

## Tâche 6 — scopes, lightbox, copier/coller de grade

**Fichiers :** `montage.js` (`DzmScopes`, `DzmLightbox`), patcher (actions `grade_copy` Ctrl+Alt+C / `grade_paste` Ctrl+Alt+V dans R_R1/R_R2 ; `DZM_MENU_RUB` « Édition » ; deux entrées du menu de clip dans R_EC1 (garder `{sep:!0}` == 4 ou réaligner le pin en le disant) ; entrée ☰ › Affichage « Lightbox des plans » ; montage des scopes sous le lecteur), `montage.css`, bancs.

- [ ] Scopes : bouton « Scopes » (bascule, `title`, mémorisé `localStorage` `dz_montage_scopes`) sous le lecteur ; PNG de `POST /scopes` pour le plan V1 sous la tête (`effects` et `mask` du plan) ; rafraîchi à l'arrêt, 300 ms d'anti-rebond, jamais pendant la lecture ; hors plan → message « Aucun plan sous la tête ».
- [ ] Lightbox : voile (z-index du voile E-11) + grille ; vignettes `grade-frame` 240 px, file de 3 requêtes au plus ; clic → `setSelId` + tête au début du plan + fermeture ; Échap et clic du voile ferment.
- [ ] Copier/coller : `dzmGradeTake` → `localStorage["dz_montage_grade"]` ; coller sur le clip sélectionné (piste verrouillée → refus dit, démo → refus dit), `pushHistory()` une fois ; notes « Grade copié (n effets) » / « Grade collé ».
- [ ] Bancs édition [38], bundle, ergonomie ; commit `montage : D-31 D-32 - scopes, lightbox, copier coller le grade (client)` + push.

## Tâche 7 — clôture L5

- [ ] `backend/tests/mutations_montage_l5.py` (modèle `mutations_montage_l7b.py`, ≥ 15 mutations en OCTETS couvrant T1–T6, restauration prouvée par sha256 avec retentatives, code de sortie, table des comptes dans le docstring).
- [ ] `backend/tests/test_montage_l5_croise.py` : `curves_clean` == `dzmCurveClean` sur 30 entrées ; `mask_of` == `dzmMaskOf` ; bornes `wheels` du catalogue == bornes du cœur ; `DZM_COLOR_TYPES` ⊂ `catalog()` ; actions `grade_copy/grade_paste` présentes et non réservées ; routes appelées par la couche == routes déclarées.
- [ ] Rejouer TOUS les bancs (un par processus) + tous les bancs croisés des lots précédents (l3, l4, l7, l7b, eb, ec) ; conception datée (l.98-104 et l.176 : « exécuté <date> » + écarts : ffmpeg 9.0.1, +10 types, lenscorrection préexistant, nlmeans écarté, colorbalance démenti, masque geq-une-fois, effets V2, « à tous les plans » non généralisé, D-29 partiel) ; plan coché ; revue finale ; PR vers `main`.

## Auto-revue

Couverture de la conception : D-27 → T1/T4/T5 ; D-28 → T3/T5 ; D-29 → T1/T4/T5 ; D-30 → T2/T4/T5 ; D-31 → T3/T6 ; D-32 → T4/T6 ; D-33 → T1 (+ T2 pour chromakey utile). Noms tenus : `curves_clean`/`dzmCurveClean`, `mask_of`/`dzmMaskOf`, `wheels` (`lift_*`, `gamma_*`, `gain_*`), `colormatch` (`y_gain`… comme D1), `grade-frame`, `scopes`, `color-match`, `DZM_COLOR_TYPES`, `dz_montage_grade`, `grade_copy`/`grade_paste`. Seules valeurs laissées à mesurer : la fin d'`overlay` sur source bouclée (T2), `-ss` hors durée (T3), l'endroit du payload V2 (T5).
