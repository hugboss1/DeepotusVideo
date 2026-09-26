# Retours d'usage après L6 — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** traiter les quatre retours de l'utilisateur du 26/09 : musique A2 inaudible au rendu, effets « qui ne s'appliquent pas » (invisibles dans le lecteur), aperçu des modifications de couleur dans la fenêtre de visualisation principale, scopes dans une fenêtre flottante plus grande et redimensionnable.

**Architecture :** deux correctifs backend (sémantique du « mix » de l'écho/réverbe dans `sfx_service` ; musique d'une piste en boucle bornée à son clip dans `montage_service`), une extension des routes `grade-frame` (mode « cadre » : image calculée dans la géométrie du lecteur) et `scopes` (taille), et deux composants client (image étalonnée dans le lecteur à l'arrêt ; fenêtre flottante des scopes).

**Tech :** FastAPI, ffmpeg 9.0.1 (app) / 8.1.1 (PATH), bundle patché en octets, bancs python embarqué, Playwright + Chrome.

---

## Liste de contrôle (cochée par le contrôleur : revue conformité + qualité + corrections + re-revue + bancs verts)

- [ ] T1 — `sfx_service` : le « mix » de l'écho et de la réverbe dose la part d'effet, le son sec reste à son niveau
- [ ] T2 — `montage_service` : la musique d'une piste en boucle respecte les bornes de son clip (début, fin, entrée source), boucle à l'intérieur
- [ ] T3 — routes `grade-frame` (mode cadre, haute définition, effets bornés au temps local) et `scopes` (taille)
- [ ] T4 — client : image étalonnée dans la fenêtre principale, à l'arrêt
- [ ] T5 — client : scopes en fenêtre flottante déplaçable/redimensionnable
- [ ] T6 — clôture (mutations, banc croisé, preuve écran, conception/mémoire datées, revue finale, PR)

Ordonnancement : vague 1 **T1** (`sfx_service.py`, banc neuf `test_retours_sfx.py`) ∥ **T2** (`montage_service.py` musique, banc neuf `test_retours_musique.py`) ∥ **T4** (couche + patcher + bundle + CSS, code contre le contrat T3 écrit ici) ; vague 2 **T3** (après T2 : même `montage_service.py` ; `grading.py`, banc neuf `test_retours_grade.py`) ∥ **T5** (après T4 : même patcher) ; **T6** en dernier. Revues en arrière-plan sur le SHA figé.

## Diagnostic mesuré (26/09, `scratchpad/diag_retours/`)

- Rendu final de l'utilisateur `montage_485e5ba3.mp4` reproduit au 0,1 dB par le graphe reconstruit. Musique PRÉSENTE mais ≈ 54 dB sous la source : automation de l'utilisateur (−24,5 dB au départ) + bus −14 + **écho/réverbe −18 dB** (`sfx_service.py` `_fx_echo` l.~394 et `_fx_reverb` l.~409 : `aecho=0.9:{og}:…` avec `og = mix/100` → le gain de sortie s'applique au signal SEC ; « mix 22 % » ≈ −14 dB ; avec `out_gain=1` l'écho ne coûte que −0,4 dB ; défaut présent depuis `e8562db`, 08/08) ; ducking 0 dB (voix off quasi muette : micro débranché, pas de normalisation voulue).
- `/render` ne transmet à la musique ni `start`, ni `end`, ni `srcIn` (`montage_service.py` l.~5178-5186) : elle joue de 0 jusqu'à la fin du rendu en `-stream_loop -1` (l.~4073) quel que soit son clip (11,1 s affichées, 53,6 s jouées). Même lecture dans `/measure` (l.~5388).
- Effets : APPLIQUÉS au rendu (négatif, pixelate mesurés) ; le lecteur vivant n'en montre aucun (décision L5 n°9) — c'est la plainte.
- `graded_frame` (`grading.py`) applique toute la pile `build_chain` mais sur l'image SOURCE entière (pas le cadre 9:16, ni reframe D-40, ni zoom D-13), retire les bornes t0/t1 (un effet borné est montré partout), `w` ≤ 640 (route), pas de sémaphore ; `/scopes` 512 fixe.
- Aucune fenêtre flottante déplaçable+redimensionnable dans la couche ; brique réutilisable : `dzmGpDrag(e, cb)` (M:~4065) ; modèle déplacer+poignée : `DzmDzRects` (M:~6741) ; mémoire bornée : `dzmTbOffGet/Set`, recadrage au resize `dzmTbVeille`.

## Conventions

Celles du plan L6 (`2026-09-25-plan-montage-resolve-L6.md` §Conventions) : un banc par processus lu par code de sortie, `check(label, cond, detail)`, témoins positifs, état vide, faute n°6 ; ancres 1/0/1 sur `.bak_montage`, replis préférés, sections neuves préfixe **`R6`** (groupe `R6 = [...]` posé en queue APRÈS `L6`, pins de queue réalignés EN LE DISANT — `_PQ`, `_DZ_TAGS`, `len(PATCHES)` 200, `PATCHES[-len(_L6T):]`) ; sonde dzcout 177, `useState` 576 ; E-12 ; CSS dans `montage.css` seulement ; `montage_service.py` Edit/Write ; commits `git commit --only`, trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` ; aucun serveur 8765 ; aucune dépense. Comptes au départ (`62f0c75`) : bundle 2341/0, édition 599/0, ergonomie 70/0, l6 110/0, l5 109/0, sources_illisibles 50/0, 201 ancres.

## Tâche 1 — écho et réverbe : « mix » = part d'effet

**Fichiers :** `backend/app/services/sfx_service.py` (`_fx_echo`, `_fx_reverb`) ; banc neuf `backend/tests/test_retours_sfx.py`.
- Le signal sec reste à son niveau (± 0,5 dB mesuré sur un bruit rose, hors queue d'écho) pour TOUT `mix` ; la part d'effet croît avec `mix` ; `mix` < 0,5 → `""` (identité, déjà le cas pour la réverbe ; l'écho aussi). MESURER d'abord `aecho` (in_gain/out_gain/decays) sur les deux binaires et choisir une forme LINÉAIRE (le fragment s'insère dans une chaîne séparée par des virgules : pas de `asplit`/labels) — ex. `aecho=1:1:<delays>:<decays·mix>` ; vérifier qu'aucun écrêtage ne naît (crête de sortie ≤ crête d'entrée + 6 dB sur un signal à −6 dBFS, sinon compensation dite).
- Mesurer ce que fait l'AUDITION WebAudio du rack (`sfxstudio.js`, `live:1` pour echo/reverb : lire comment `mix` y est appliqué) : la nouvelle sémantique doit s'en rapprocher ; écart dit.
- Checks : sec préservé à mix 22/55/100, part d'effet croissante, identité à mix 0, commande des AUTRES types inchangée (constantes de `62f0c75`), rendu réel sur les deux binaires. Changement voulu (daté) : les rendus qui utilisent écho/réverbe deviennent plus forts.
- Commit `montage : retours - echo et reverbe, le mix dose l effet sans baisser le son sec`.

## Tâche 2 — musique bornée à son clip

**Fichiers :** `backend/app/services/montage_service.py` (lecture `/render` l.~5178 et `/measure` l.~5388, builder musique l.~4073-4108) ; banc neuf `backend/tests/test_retours_musique.py`.
- Le dict `music` porte `start`, `end`, `src_in` (et la durée source sondée) ; le builder : entrée `-stream_loop -1` gardée (boucle de la SOURCE), puis `atrim=src_in:src_in+(end-start)` sur la source bouclée (mesurer : `-ss src_in` en entrée vs `atrim` ; la boucle doit repartir du début de la source, pas de `src_in` — dire le choix), `asetpts`, fondus calés sur la fin du CLIP (pas du rendu), puis `adelay=start` ; l'automation `volume_points` reste en temps GLOBAL (c'est le temps de la timeline, comme aujourd'hui ; mesurer qu'après `adelay` l'expression `t` est toujours le temps global, sinon la décaler). Plusieurs clips sur une piste en boucle : mesurer ce que fait `/render` aujourd'hui (premier clip = musique, suivants rangés en sfx) et le dire ; ne changer que le premier.
- Checks : clip 0–11,1 s → musique présente 0–11 s, silence après (RMS < −80 dBFS de 12 s à la fin) ; clip 5–15 → silence avant 5 ; clip plus long que la source → boucle (présente sur toute la durée) ; `srcIn` respecté (corrélation ou marqueur) ; fondu de sortie à la fin du clip ; ducking inchangé ; commande SANS musique inchangée ; `/measure` même lecture ; deux binaires.
- Commit `montage : retours - la musique d une piste en boucle respecte les bornes de son clip`.

## Tâche 3 — `grade-frame` en mode cadre, `scopes` en taille

**Fichiers :** `backend/app/services/grading.py`, `backend/app/services/montage_service.py` (routes l.~5816-5874) ; banc neuf `backend/tests/test_retours_grade.py`.

Contrat (T4/T5 s'y fient) :
```
POST /api/montage/grade-frame  {src, t, effects?, mask?, w?, cadre?}
  cadre = {ratio: "9:16"|"16:9"|"1:1"|"4:5", t_local: float, reframe?: <objet reframe du clip>, dz?: <objet dz du clip>}
  -> avec cadre : l'image source est d'abord mise au CADRE du projet comme au rendu (scale cover + crop, ou reframe D-40 au
     temps local, puis zoom D-13 au temps local), PUIS la pile d'effets (build_chain, bornes t0/t1 RESPECTÉES : un effet
     dont [t0,t1] ne contient pas t_local est retiré ; fondus ignorés), puis le masque ; w (largeur de sortie) 96..1280 pair
     (défaut 720) ; sans cadre : comportement ACTUEL octet pour octet (w 96..640).
POST /api/montage/scopes {src, t, effects?, mask?, size?, cadre?}
  size 256..1024 (défaut 512, carré) ; cadre : même préparation que ci-dessus.
```
Réutiliser les fonctions du rendu pour la géométrie (mesurer lesquelles : `_reframe_crop`, zoompan/`dz`, `_canvas`/`_CANVAS`) plutôt que de les réécrire ; sémaphore 2 sur `grade-frame` comme `/scopes` ; cache par empreinte incluant `cadre`/`size`.
- Checks : sans `cadre` → images identiques (octets) à `62f0c75` ; avec `cadre` 9:16 sur une source 16:9 → image 9:16 (w×(w·16/9)) ; masque ellipse au centre du CADRE (pixel centre affecté, coin intact) ; effet borné [5,6] absent à t_local 2, présent à 5,5 ; `w` 1280 accepté, 1281 → borné ; `size` 1024 → PNG 1024², défaut 512 inchangé ; pins l5 (512×512, w 640) tenus ; deux binaires.
- Commit `montage : retours - image etalonnee dans la geometrie du cadre, scopes a la taille voulue`.

## Tâche 4 — image étalonnée dans la fenêtre principale

**Fichiers :** `frontend/patches/montage.js` (composant `DzmGradeLive`, placé APRÈS `DzmMaskBox`, hors des zones `_GPE`/`_L5Z`/`_L6*`), `scripts/patch_bundle_montage.py` (section `R6gl1` sur l'ancre libre `liveOn?r.jsx("div",{className:"svm-liveov",ref:liveOvRef,` — insérer `liveOn?r.jsx(DzTracks.GradeLive,{clips:clips,head:ph,playing:playing,vzoom:vzoom,ratio:<ratio du projet — mesurer le nom>}):null,` AVANT), `frontend/dist/shared/montage.css`, bancs édition/bundle/ergonomie.
- Comportement : à l'ARRÊT seulement, si le plan V1 sous la tête (`dzmScopesAt`) a au moins un effet actif (ou un masque avec effets), `POST grade-frame` avec `cadre {ratio, t_local, reframe, dz}` et `w` = largeur CSS du cadre × `devicePixelRatio` (borné 1280, pair), anti-rebond 250 ms, `AbortController` + numéro de requête, blob → URL révoquée ; l'`<img>` couvre le cadre (`position:absolute; inset:0; width/height 100%; object-fit:fill` puisque l'image EST au format du cadre), `transform: scale(vzoom)` origine au centre comme `.svm-live`, `pointer-events:none` ; affichée seulement si son empreinte (clip id + t arrondi + pile + cadre) correspond à l'état courant (sinon masquée : jamais une image périmée) ; masquée en lecture ; petite pastille « étalonné » (texte, pas de bouton) dans un coin. Plan sans effet → rien, aucune requête. V2/titres/sous-titres restent AU-DESSUS (ordre DOM). Erreur réseau / 415 (V1 en image fixe) → rien d'affiché, silence (pas de note à chaque arrêt).
- Bancs : édition (composant sous shim : pas de requête en lecture, pas de requête sans effet, empreinte périmée masquée, corps de requête exact avec `cadre`), bundle (section montée une fois, AVANT `.svm-liveov`, pins de queue/sonde/useState réalignés EN LE DISANT), ergonomie (aucun bouton ajouté, ou titré).
- Commit `montage : retours - image etalonnee dans la fenetre principale a l arret`.

## Tâche 5 — scopes en fenêtre flottante

**Fichiers :** `montage.js` (`DzmScopes` : le portail vise la racine `.dzsvm` au lieu de `.svm-frame`), `montage.css`, bancs.
- Fenêtre `.dzm-scwin` (`position:absolute`, z-index entre la barre OUTILS et la lightbox — mesurer, sous 19), barre de titre « Scopes » (déplacer, par `dzmGpDrag`), poignée de coin (redimensionner, carré, 240..1024 px bornés à la racine), bouton « × » titré qui éteint les scopes (comme le bouton « Scopes »), géométrie `{x,y,s}` mémorisée `localStorage["dz_montage_scopes_geo"]` (try/catch, valeur corrompue → défaut en haut à droite), recadrée si la fenêtre du navigateur rétrécit ; image demandée à `size` = côté × devicePixelRatio borné 256..1024 (T3) avec `cadre` comme T4 ; rafraîchie à l'arrêt, 300 ms (inchangé) ; jamais pendant un geste de redimensionnement (requête au relâcher).
- Pins : `_SC_CSS`, `_MASQUES` (5 règles `display:none` : ne pas en ajouter), `sc_rendu` (useState/useEffect, textes), `_L5Z` 3 boutons → 4 avec « × » (réaligner EN LE DISANT), `setPointerCapture` 1.
- Commit `montage : retours - scopes dans une fenetre flottante redimensionnable`.

## Tâche 6 — clôture

- [ ] `backend/tests/mutations_retours_l6.py` (modèle `mutations_montage_l6.py`, ≥ 10 mutations couvrant T1–T5, `--pre-vol`).
- [ ] Banc croisé `backend/tests/test_retours_croise.py` : corps `cadre` du client == contrat accepté par la route ; bornes `w`/`size` client == serveur ; ratio du projet == `_CANVAS`.
- [ ] Tous les bancs Montage rejoués (un par processus), l6/l5/retours sur les deux binaires ; preuve écran 8799 (image étalonnée à l'arrêt identique à une image du rendu au même instant — écart moyen mesuré ; masquée en lecture ; fenêtre des scopes déplacée/redimensionnée, persistante après F5 ; rendu réel : musique présente sur son clip seulement, écho qui ne baisse plus le sec) ; conception datée (décision L5 n°9 amendée : aperçu étalonné à l'arrêt) ; mémoire ; revue finale ; PR.
