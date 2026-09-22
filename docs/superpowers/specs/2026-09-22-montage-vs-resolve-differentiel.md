# Différentiel DaVinci Resolve 21.1 ↔ Montage (DeepotusVideo) — mesuré le 22/09/2026

> **Deux côtés, deux sondes.** Côté Resolve : l'application native sur le bureau
> (relevé `2026-09-22-davinci-resolve-app-inventaire.md`, Loupe 200 %) et le
> site (`2026-09-21-davinci-resolve-inventaire.md`). Côté Montage : une sonde
> **Playwright** (`scripts/qa/probe-montage-playwright.mjs`, Chrome local,
> viewport 1400 × 900, backend du worktree sur 8799, données vierges + deux
> mp4 `testsrc2` envoyés par `POST /api/videos/upload` → projet RÉEL de deux
> plans V1 et deux jumeaux A1) qui relève le DOM et l'API. Playwright ne pilote
> pas une application Qt : Resolve n'a pas pu être sondé par lui, et son API de
> script Python est passée en Studio (ReadMe 21.1). Le fichier brut de la sonde
> est `probe.json` (scratchpad de la session), les captures `montage.png`,
> `library_envoyer.png`, `chapitres.png`, `studio.png`.
>
> **Les quatre fonctions demandées restent le fil conducteur** : (1) récupérer
> dans Montage les rendus et vidéos de Studio, (2) et de Chapitres, (3) créer
> un montage neuf, (4) envoyer vers le Scheduler en fin de montage. Elles sont
> reprises en §1, avant l'ergonomie (§2) et le design (§3). Les décisions
> proposées sont celles du tableau `2026-09-22-montage-vs-resolve-app-design.md`
> (E-1…E-14) ; ce différentiel les ÉTAYE par la mesure, il ne les remplace pas.

## 0. Ce que la sonde a mesuré chez nous (1400 × 900, projet réel)

| Mesure | Valeur |
|---|---|
| Racine `.dzsvm` | x 232 (rail de navigation à gauche), 1168 × 844 |
| Barre de titre `.svm-titlebar` | 48 px ; boutons : `bibliothèque` (« Réinitialiser depuis la Bibliothèque — écrase la sauvegarde »), `<select>` Format (`9:16 · vertical / 4:5 · feed / 1:1 · carré / 16:9 · paysage`), `Preview 480p (gratuit)`, `Rendre & publier →`, `sons` (B), `narration` (T), `clair` (thème) |
| Bande centrale `.svm-mid` | 397 px : tiroir Narration 300 + lecteur 568 (cadre 9:16 = 212 × 377) + **inspecteur 300 px** (`width:300px; flex:0 0 auto; resize:none`) |
| Timeline `.svm-tl` | 399 px (`min-height 356 / max-height 432`), transport 46 px, pistes 352 px |
| Barre OUTILS `#dzm-toolbar` | flottante 831 × 83 à (246, 412) — au-dessus du transport, **sur le pied du tiroir Narration et du lecteur** ; onglet `.dzm-tbtab` 121 × 21 ; 5 groupes : `pistes` (vidéo · incrust. · audio), `biblio` (lier), `mot` (couleur · rebond · glow), `ajouts` (emoji · texte), `projets` (projets) |
| Transport | **34** boutons : OUTILS▾, poignée, les 12 de la barre, ◀◀ \|◀ ▶ ▶\| ▶▶, ↶ ↷, aimanter, lame · Alt+C, ripple, ◆ 0 (marqueurs), T+, sous-titres 0 %, zoom ▁▂▃▅, −, … |
| Pistes par défaut | 7 : `T1 titres` 40 · `V2 overlay/VFX` 40 · `V1 vidéo` 54 (2 clips) · `A1 dialogue` 52 (2 clips) · `A2 musique` 48 · `A3 sfx` 48 · `S1 sous-titres` 44 ; chaque en-tête porte `🔒︎ + ⋮ ▲ ▼ ×` (les pistes audio : `+MS` = muet/solo) |
| Inspecteur | libellés `Clip sélectionné · In · Out · Vitesse · Transition · Mixage` (projet sans overlay ni audio sélectionné) |
| Popover « Rendre & publier » | `.svm-pop`, **sans voile** : « rendu ffmpeg (local) · 0:14 · $0.00 — publication · brouillon Scheduler · gratuit — Rendu local 1080 (aucun crédit consommé), puis brouillon dans le Scheduler — rien n'est publié sans ta validation. » boutons `Fermer` / `Rendre & publier` |
| Mots absents du DOM du Montage | `Nouveau`, `Nouveau montage`, `Nouveau projet`, `Studio`, `Chapitres`, `Scheduler`, `Envoyer vers`, `Importer`, `Médias` — tous **0** occurrence ; `Rendre & publier` 1, `Preview 480p` 1, `bibliothèque` 2, `projets` 2 |
| Library | onglets `Images 6 · Renders 2 · 3D 0 · Sprites 0 · Audio 0 · Favoris 0 · Établi 0` ; actions `Upload video · Importer un son · Upload image · Prompt manager · Create image` ; les deux mp4 envoyés sont dans **Renders** (provider `ugc`) |
| Chapitres | écran vide de données : **1 bouton** (« Quick command… ⌘K »), 0 mention de « montage » |
| Studio | 19 boutons (`New · Save · Preview · Run · Export …`) ; la seule mention est le gabarit **« Timeline montage — 4 clips → xfade → render »** (un graphe Studio qui RENDU un montage, pas un envoi vers l'écran Montage) |
| API | `GET /api/montage/project` → 200, 4 clips (2 V1), `saved:false` ; `GET /projects` → 0 ; **`POST /projects {name, timeline:{clips:[]}}` → 400 « Aucune timeline à enregistrer. »** ; `GET /api/jobs` → 2 (`ugc`) ; `GET /api/schedule` → 0 ; 27 routes `montage/episodes/schedule/upload` dans l'OpenAPI |
| Console | 0 erreur |

## 1. Les quatre fonctions demandées — différentiel

| # | Fonction demandée | Resolve (mesuré) | Montage (mesuré) | Écart | Décision (rappel) |
|---|---|---|---|---|---|
| 1 | **Récupérer dans Montage les rendus de Studio** | Pas de « Studio » chez eux, mais un **Media Pool unique** partagé par toutes les pages (Media/Cut/Edit) : tout média importé ou rendu (Deliver → « Add to media pool ») est à portée de glisser, avec bins, Smart Bins, recherche, tri, vue grille/liste | Le Montage n'affiche **aucune** entrée nommée Studio (0 occurrence) ; un rendu Studio n'arrive que (a) tout seul, parmi les 4 derniers jobs vidéo quand aucune sauvegarde n'existe (`GET /project`), (b) par le sélecteur `lier` (12 rendus au plus, panneau « Ajouter sur la piste V1 »), (c) par Library → Renders → « Envoyer vers… » → « 🎞 Montage — clip vidéo », qui pose sur `v2` en dur | pas de provenance, plafond 12, piste `v2` en dur, aucun retour depuis Studio (Studio n'a que le gabarit « Timeline montage ») | **E-2** tiroir Médias avec chips de provenance et pagination ; **E-3** bouton « Ouvrir dans le Montage » depuis Studio, pose V1 + A1 |
| 2 | **Récupérer les vidéos de Chapitres** | Idem : un épisode rendu serait un clip du pool, découpable ; Resolve importe aussi des **timelines** (XML/EDL) avec leurs coupes | Chapitres : **1 bouton** à l'écran (aucune action vers le Montage, 0 mention) ; l'épisode (`provider="episode"`, `.mp4` 9:16) passe par les mêmes trois chemins que ci-dessus ; posé sur `v2` il est **muet** (le son gravé n'est lu que par le jumeau A1 créé par `GET /project`) ; ses scènes ne sont pas transmises | aucun chemin nommé, piste fausse, son perdu, scènes perdues | **E-3** « Ouvrir dans le Montage » depuis un épisode terminé : V1 + A1, **un clip par scène** avec un marqueur (D-5) |
| 3 | **Créer un montage neuf** | **Project Manager** (⌂, Shift+0) : fenêtre modale à cartes, `New Project` → projet VIDE ; `File ▸ New Timeline… (Ctrl+N)` ; `Open Recent Project ▸` ; `Save Project As…` | 0 occurrence de « Nouveau » ; panneau `projets` = « enregistrer sous… / renommer / dupliquer / ouvrir → remplacer ? / × → supprimer ? » ; **`POST /projects` refuse 400 une timeline vide** ; `bibliothèque` → « écraser la sauvegarde ? » repose les 4 derniers rendus | pas de « neuf », pas de vide, « ouvrir » destructif à deux clics | **E-1** bouton « Nouveau montage » + `{vide:true}` accepté + grille de cartes de projets + instantané avant « ouvrir » |
| 4 | **Envoyer vers le Scheduler en fin de montage** | Page **Deliver** : presets (Custom, H.264/H.265 Master, ProRes, **YouTube · Vimeo · TikTok · Dropbox ▸**, Presentations, Audio Only…), `File Name`, `Location`, `Add to Render Queue`, **Render Queue** + `Render All` ; **Quick Export** sur Cut/Edit/Deliver ; la publication (YouTube/Vimeo/TikTok) est un preset choisi AVANT le rendu, jamais un effet de bord | `Rendre & publier →` : rendu + brouillon Scheduler **automatique** (demain 09:00, `["x","telegram"]` en dur, légende « nom 🐙 »), navigation forcée vers le Scheduler à 900 ms, créé par le **client** (rien si l'onglet est fermé) ; `Preview 480p` = seul rendu sans brouillon ; 0 occurrence de « Scheduler » dans le DOM avant le popover | pas de bouton « Envoyer vers le Scheduler », pas de choix de canaux/heure, pas de master sans brouillon, fragilité | **E-4** rendre / publier séparés, bandeau de fin de rendu à trois boutons, formulaire canaux + date, `POST /api/montage/publish` côté backend, `project_id` transmis ; **E-5** barre de titre « Preview · Rendre · Publier » ; presets = **D-35 (L4)** |

## 2. Ergonomie — différentiel mesuré

| Sujet | Resolve (mesuré) | Montage (mesuré par la sonde) | Écart | Décision |
|---|---|---|---|---|
| Navigation | 8 **pages** (barre basse 34 px, icône + libellé, actif souligné rouge) ; barre d'interface haute qui ne change que les panneaux ; nom du projet toujours au centre | 1 écran ; rail de navigation à gauche (232 px) commun à toute l'application (Quick, Studio, Chapitres, Son & VFX, Montage, Scheduler, Templates, News, Library…) ; nom du projet dans `.svm-projmeta` de la barre de titre | Resolve sépare *importer / monter / livrer* ; nous mélangeons tout dans 1168 × 844 | **E-7** trois vues « Médias · Montage · Livraison » (`data-view`) |
| Menus | 13 menus, raccourcis en regard, désactivés visibles ; menus contextuels partout | aucune barre de menus ; 34 boutons de transport à infobulle ; raccourcis dans un panneau « ? » ; pas de menu contextuel sur clip ni piste | l'action existe, le point d'entrée manque | **E-6** menu ☰ + contextuels |
| Inspecteur | panneau à bascule (bouton haut droite), fermé par défaut, redimensionnable, presets (21.1), tête de lecture indiquée | `aside.svm-insp` **300 px, `resize:none`, `flex:0 0 auto`**, toujours ouvert ; 6 libellés à vide | rigide | **E-8** bascule + poignée 260–480 px ; **E-13** tête dans l'inspecteur |
| Timeline | hauteur libre (séparateur), double timeline en Cut, timecode 22 px, options « durée des clips » / « échelle auto des ondes » ; 21.1 : couper/coller des trous | `.svm-tl` **399 px** bornée `356…432` (`max-height 48vh`), 7 pistes de 40–54 px → 352 px de pistes visibles, défilement interne au-delà ; pas de mini-carte (D-7 en L7) | plafond dur | **E-9** séparateur + D-7 remonté ; **E-14** trou sélectionnable |
| Barre d'outils | fixe, dans la barre de timeline (sélection · trim · dynamic trim · lame · insert/overwrite/replace · courbes · lien · verrou · drapeau · marqueur · zoom) | flottante 831 × 83 à (246, 412) : **elle recouvre le pied du tiroir Narration (y 104–501) et du lecteur** à 1400 × 900 (D-1 l'a sortie des pistes, pas de la bande centrale) ; 5 groupes, 12 boutons ; repliable sur un onglet 121 × 21 | recouvrement mesuré | **E-10** option « ancrer dans le transport » |
| Popovers | modaux (voile) pour ce qui engage (Project Manager, presets, Quick Export) | `.svm-pop` **sans voile** (mesuré `voile:false` sur le popover de rendu) : tout reste cliquable pendant un mode armé | — | **E-11** voile sous les modes |
| Pistes | en-têtes avec nom, verrou, auto-select, muet/solo, couleur ; réordonnancement par glisser | en-têtes `nom · type · 🔒︎ · + · ⋮ · ▲ · ▼ · ×` (+ `M S` sur l'audio) — plus dense que Resolve mais **7 icônes par piste**, sans couleur de piste | densité | **E-12** audit (grisé, pas masqué ; infobulle partout) — déjà vrai sur le transport (34/34 avec `title`) |
| Import | page Media : arbre des volumes + glisser vers le pool ; File ▸ Import ▸ ; Quick Export | Library : `Upload video / Importer un son / Upload image` ; le Montage n'importe pas lui-même (0 « Importer ») | l'import est ailleurs | **E-2** tiroir Médias avec « Importer un fichier » |

## 3. Design — différentiel

| Sujet | Resolve | Montage | Décision |
|---|---|---|---|
| Palette | fonds ≈ #1f1f21 (barres) / #28282a (panneaux), viewer noir, texte #d6d6d6 / #8f8f8f, **un seul accent rouge** (page active, sélection) + bleu pour les états (drapeau, marqueur, zoom) | thème « Cinema » sombre + thème clair (`clair`), damier 45° sous le cadre, or `.svm-goldbtn` pour l'action principale, chips de couleur par piste (`--c-video`, `--c-audio`, `--c-text`, `--c-3d`) | **Conservé** : notre charte a plus de couleur par piste, c'est un atout de lecture ; aligner seulement la **hiérarchie des boutons** (un seul « or » par écran : Rendre) |
| Typographie | Open Sans ≈ 11–13 px, timecode 22 px tabulaire | `--f-mono` 10 px pour les chips et libellés secondaires, timecode `.svm-tcmain` | **Conservé** ; agrandir le timecode du transport (E-9, avec le séparateur) |
| Densité | grandes zones vides, 8 pages | tout visible, 34 boutons de transport, 5 groupes flottants | E-7 / E-10 |
| États | désactivé gris, jamais masqué ; infobulle systématique | idem sur le transport (mesuré) ; certains boutons disparaissent selon l'état (chips d'en-tête) | E-12 |

## 4. Ce que le différentiel ne couvre pas

- Resolve avec un projet chargé (inspecteur par état, barres contextuelles) : projet vide sur le bureau, import refusé en lecture seule.
- Nos panneaux « projets » et « lier » : la sonde a mesuré leur existence et leurs infobulles, pas leur contenu ouvert (le clic synthétique a ouvert la fenêtre de la barre d'outils à la place — à corriger dans la sonde, ce n'est pas un défaut du Montage) ; leurs libellés exacts sont dans `2026-09-22-montage-vs-resolve-app-design.md` §0, relevés dans le code.
- Les chips de provenance de la Bibliothèque (`__dzSrcChips`) : non isolées par la sonde (elle a ramassé le rail de navigation).

## 5. Rappel des décisions à valider (inchangées)

**Lot E-A (P0)** : E-1 nouveau montage vide + grille de projets · E-3 « Ouvrir dans le Montage » depuis Studio et Chapitres (V1 + A1, scènes) + correction `v2` · E-4 rendre / publier séparés + `POST /publish` backend.
**Lot E-B** : E-2 tiroir Médias · E-5 trois verbes · E-11 voile · E-8 inspecteur · E-9 séparateur + D-7.
**Lot E-C** : E-6 menus · E-7 trois vues · E-10 ancrage · E-12 audit · E-13 / E-14.
