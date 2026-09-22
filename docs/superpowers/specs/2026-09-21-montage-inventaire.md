# Montage « aussi poussé que Resolve » — inventaire de NOTRE module Montage (21/09/2026)

> Relevé fait en LECTURE SEULE dans le volet intégré sur le backend du worktree
> `chantier/montage-resolve` (`main` = `97fb58b`, v2.8.0), lancé sur
> `127.0.0.1:8799` avec le python embarqué
> (`%LOCALAPPDATA%\DeepotusVideoGen\runtime\python\python.exe`, 3.13.15) et
> `DEEPOTUS_DATA_DIR` dans le scratchpad de session (données vierges : l'écran
> a donc ouvert la **timeline de démonstration** `teaser_abyss · v4 · 1:04`,
> qui est une maquette — les gestes « projet réel » sont relevés dans le code,
> cité). Viewport émulé 1400 × 900, thème sombre. Rien n'a été rendu, aucun
> crédit dépensé ; le bouton « couleur » du groupe MOT a été basculé par un
> clic tombé sur la barre d'outils flottante (voir §9) et l'état n'est pas
> persisté (démo). État final : backend arrêté, données du scratchpad.
> Sources lues en appui : `frontend/patches/son-vfx-montage.js` (4 871 l.,
> bloc `sonvfx` intouchable), `frontend/patches/montage.js` (4 672 l.,
> `window.DzMontage`), `frontend/patches/vfxrack.js`, `frontend/patches/subs.js`,
> `frontend/patches/sfxstudio.js`, `backend/app/services/montage_service.py`
> (3 148 l.), `effects_engine.py`, `subtitle_service.py`, `sfx_service.py`,
> routes `/api/subtitles/*` de `routes.py`.

## 0. Cadrage

| | |
|---|---|
| Écran | `Montage · Timeline multipiste` (entrée « Montage » de la barre latérale, `id:"montage"`, composant `DzMontage`) |
| Couches | bloc `sonvfx` (V3/V4/V6/V8/V9 de `vfxrack`, S3…S17 de `subs` inlinés) → `montage.js` (patcher `patch_bundle_montage.py`, 66 ancres) → `dzcout`… → `version` (dernier maillon) |
| Backend | `/api/montage/*` (21 routes), `/api/subtitles/*` (19 routes), `/api/effects/catalog`, `/api/effects/preview`, `/api/jobs/{id}` |
| Rendu | UNE commande ffmpeg (`_build_montage_command`), libx264 high 4.0 + aac ; preview 480p (`veryfast`, crf 30, 128k) ou final 1080 (30 i/s) ; sortie MP4 dans la Bibliothèque, brouillon Scheduler |
| Bancs | 10 `test_montage_*.py` (bundle 1301, sources, remplacer, projets, texte, subs_animes, etalonnage, pistes_dyn, pistes_rendu, media, effects) |

## 1. Structure des zones (1400 × 900, px mesurés au DOM)

| Zone | Cotes | Contenu |
|---|---|---|
| Barre latérale de l'application | x 0–231, toute hauteur | 12 écrans (Quick, Studio, Chapitres, Son & VFX, **Montage**, Scheduler, Templates, News, Library, Game Assets, Vectorlab, Settings) |
| En-tête de l'application | y 0–56 | titre « Montage · Timeline multipiste », Quick command ⌘K, pastille coût `$0 · 766 cr` (fal / heygen / voice), `v2.8.0` |
| Barre de titre du Montage | y 56–104 | « Montage » · `teaser_abyss · v4 · 1:04` · chip **NON ENREGISTRÉ** (ou « modifications en attente » / « sauvegarde automatique ») · select **Format** (9:16 vertical, 4:5 feed, 1:1 carré, 16:9 paysage — aligné sur `_CANVAS`) · **Preview 480p (gratuit)** · **Rendre & publier →** · boutons `sons` (B), `narration` (T), `clair` (aperçu de l'autre thème) |
| Colonne gauche — NARRATION | x 232–532, y 104–541 (300 × 437) | panneau repliable (T) : compteur de blocs, select **Voix** (Prophet clonée, Tide, Narrateur humain, Abyss ; voix clonées en tête), note « voix de démonstration — connectez ElevenLabs », blocs numérotés (timecode `00:00:01:08`, durée, nom de fichier, textarea, `110 car. · ~$0.026`, **Narrer**, ▶, 🗑︎), **+ Ajouter un bloc** (clip A1 vide de 4 s hachuré), note « le texte reste local » |
| Centre — LECTEUR | x 532–1100 ; cadre 9:16 = 235 × 417 à (650,114) | timecode `00:00:18:12` en haut à droite, sous-titre incrusté en bas, poignées de l'overlay sélectionné (déplacer / échelle / rotation avec aimant 0/±45/90°), rectangle des zones sûres (G), boutons `source` / `480p` (bascule aperçu direct ↔ proxy), `9:16`, `zones sûres (G)`, `plein écran (F)` ; molette = zoom du lecteur, double-clic = réinitialiser ; drop d'un asset = ajout |
| Colonne droite — INSPECTEUR | x 1100–1400 (300 × 437), défilant | voir §6 |
| Bandeau OUTILS | onglet à (192,415) + barre flottante 831 × 83 à (246,595) | voir §5 |
| Transport | y 541–588 | `00:00:18:12 / 00:01:04:00` (HH:MM:SS:image, 30 i/s) · ◀◀ (coupe précédente ↑) · \|◀ (image −) · ▶ (Espace · L) · ▶\| (image +) · ▶▶ (coupe suivante ↓) · ↶ ↷ · **aimanter** (N) · **lame · Alt+C** · **ripple** (R) · chip **sous-titres 0 %** (ouvre le tiroir S1) · zoom ▁▂▃▅ (100/150/220/320 %, Ctrl+molette continu) · `− 1:04 total +` (durée ±6 s) · **?** raccourcis |
| Règle | y 588–606 (18 px) | graduations toutes les 6 s (pas choisi dans 2…60 pour ≤ 11 ticks), clic/glisser = tête de lecture |
| Pistes | V2 40 px · V1 54 · A1 52 · A2 48 · A3 48 · S1 44 (défilement vertical au-delà de 900) | en-tête 88 px : nom, type, mini-fader de bus (audio), boutons `+` / `M` / `S` / 🔒︎ / ⋮ (poignée de réordonnancement) / ▲ ▼ / × |

## 2. Couleurs (calculées au DOM)

| Rôle | Valeur |
|---|---|
| fond de page | `#0a0a0c` |
| clip vidéo V1 | `rgba(109,157,197,.12)` (jeton `--c-video`) |
| clip overlay V2 et sfx A3 | `rgba(201,115,143,.13)` (`--c-3d`) |
| clip dialogue A1 | `rgba(127,176,105,.13)` (`--c-audio`) |
| clip musique A2 | `rgba(201,183,160,.08)` (`--c-text`) |
| clip sélectionné | `rgba(240,180,41,.20)` + contour or |
| accent / boutons d'action | or (`svm-goldbtn`), pastille coût ambre si minorant |
| trou V1 | hachures « trou — rendu en noir » |

## 3. Typographie

`IBM Plex Sans` (repli Inter) pour l'interface ; `JetBrains Mono` pour
timecodes, durées, timecodes de bloc ; Space Grotesk pour les titres
d'application. Libellés de section en capitales espacées (NARRATION,
MIXAGE, EFFETS SUR CE CLIP, OUTILS).

## 4. Menus

Pas de barre de menus : tout est bouton, chip ou panneau. Menus contextuels :
clic droit sur un **losange d'automation** = retirer le point ; aucun clic
droit sur les clips ni sur les pistes. Palette **Quick command ⌘K** de
l'application (hors Montage).

## 5. Barre d'outils OUTILS (`DZM_TB_PLAN`, flottante, déplaçable, repliable par O)

| Groupe | Boutons | Ce que fait le clic (titre exact abrégé) |
|---|---|---|
| PISTES (action) | **vidéo** · **incrust.** · **audio** | ajoute une piste vidéo plein cadre (ses plans recouvrent V1, son extrait sur la piste dialogue) / une piste d'incrustation (position, échelle, rotation, opacité, muette) / une piste audio (sous les audio, au-dessus des sous-titres). Ctrl+Z NE retire PAS la piste |
| BIBLIOTHÈQUE | **lier** | ouvre la Bibliothèque et pose vidéo / image / rendu sur la piste vidéo la plus haute, à la tête |
| MOT — sélection (bascules exclusives) | **couleur** · **rebond** · **glow** | animation par mot de TOUTE la piste S1 (`proj.subsStyle.wordAnim`, une seule à la fois) ; rebond/glow réservés aux répliques d'une ligne |
| AJOUTS | **emoji** · **texte** | pose un clip de 0,8 s par mot-clé reconnu (feu, lune, vague, poulpe, or, fusée) sur l'overlay le plus haut (`POST /subtitles/emoji-hints`) / ouvre le panneau **Texte** (narration mot par mot) |
| PROJETS | **projets** | liste des projets : enregistrer sous…, ouvrir, dupliquer, renommer, supprimer |
| poignée · ⌖ · × | | déplacer (flèches 8 px, Maj 1 px, aimants bords/tête) · recentrer · replier |

Panneau **Texte** (bouton texte / T) : « 35 mots », mots cliquables (ponctuation
collée), **couper la sélection** (coupe une PLAGE de temps sur toutes les
pistes, ripple — `dzmRippleCut`), compteur « aucun « euh » » (mots de
remplissage via `POST /subtitles/fillers`).

## 6. Inspecteur (colonne droite) — par état de sélection

| État | Rangées relevées |
|---|---|
| Toujours | **CLIP SÉLECTIONNÉ** : nom + 🗑︎ · In · Out (survol : équivalent en images 30 i/s) · **Vitesse** (select 25/50/75/100/150/200/300/400 % sur un clip V1 réel — consomme vitesse × durée de source, durée timeline inchangée, son A1 non ré-échantillonné ; lecture seule ailleurs) |
| Clip V1 avec voisin gauche | **Transition** : select 7 types (coupe sèche, fondu, dissolution, fondu noir, pixélisé, glissement, fondu blanc) · durée 0,1–1 s · « Appliquer à toutes les coupes » ; le losange sur la jonction ouvre le même popover en grille avec vignettes ; « première coupe / trou — pas de transition » |
| Overlay (piste ≠ V1, clip réel) | **Overlay** : Opacité % · X · Y (centre, % du canvas, flèches ±0,5) · Échelle (% largeur) · Rotation (° −180..180) · **Aligner** (9 positions, marge 4 %) · **plein cadre** (cover) · **Trajectoire** : « ◇ position ici » pose un point (t, x, y, rot) à la tête, max 8, ≥ 2 points = mouvement linéaire ; le drag du lecteur édite le point ≤ 0,15 s · réinitialiser |
| Clip audio réel | **Clip audio** : Gain (dB −24..+12, Alt+↑↓) · **Fondus** in / out (0..3 s, D / Maj+D cycle 0/0,3/0,6/1 s, poignées sur le clip) + **courbe** (linéaire, douce, expo, log) · **Vitesse** ×0,5..2 (atempo) · automation : double-clic sur le clip = losange (t, dB, max 12), glisser, clic droit = retirer, « aplatir » · « désynchronisé (vitesse) » quand le jumeau V1 a changé · **Effets** audio (fx chain `sfx_service` : filter, eq3, denoise, deesser, compressor, distortion, echo, reverb, stereo, normalize) |
| Toujours | **MIXAGE** : faders dialogue / musique / sfx (dB, aussi en en-tête de piste) + vu-mètre gradué en lecture (−42..0 dBFS, ticks, zone rouge > −3, crête lente) · **Ducking auto** (switch ; « réglages » : Léger 3:1 / Moyen 6:1 / Fort 10:1, Attaque ms, Retour ms, Seuil, « défaut ») · **Maître de durée** (switch : la voix off ne sera jamais coupée) |
| Clip V1 réel | **EFFETS SUR CE CLIP** : pile (rack `DzVfx.Stack`) — réordonner ▲▼, bypass, ✕, intensité + paramètres, **Bornes temporelles** Début/Fin, **Rampe entrée / sortie** avec 10 courbes (douce, linéaire, accélérée, freinée, douce 2 sens, sinus, anticipation, dépassement, retour, rebond), bascule avant/après ; **+ effet** ouvre le panneau catalogue (catégories, recherche /, favoris ★ / F, vignette d'aperçu rendue sur le clip, pose par clic ou glisser) ; **à tous les plans** (`dzmGradeAll`) pour l'étalonnage |

Catalogue d'effets (`effects_engine._CATALOG`, 38) : **étalonnage** grade
(LUT .cube / 10 presets teal_orange, cyberpunk, deepsea, noir, warm, cold,
vintage, cross, matrix, faded), grade_basic (exposition, contraste,
saturation, température K), colorize (6), invert, posterize · **rétro** vhs,
scanlines, oldfilm, grain, filmburn, dither · **lumière** bloom, halation,
vignette, gradient, radial, lightleak · **atmosphère** rain, snow, embers ·
**distorsion** chroma, glitch, prism, ripple, swirl, lensdistort ·
**mouvement** blur, dirblur, zoomblur, shake, shakezoom · **cadrage**
letterbox (2.39/2.35/1.85/1.33), mirror, kaleido · **stylisation** pixelate,
sharpen, dreamy, glowedge, paper. Paramètres : intensity, speed, angle,
opacity, cx, cy, c0, c1, blend (6 modes), ratio, preset, file.

## 7. Panneaux et tiroirs

| Panneau | Ouverture | Contenu relevé |
|---|---|---|
| **Sous-titres** (tiroir S1, `DzSubs.Drawer`) | chip « sous-titres n % », bouton S1, « + » de l'en-tête S1 | onglet **Répliques** : « Caler la narration écrite » (gratuit, calage sur silences) ou « Transcrire l'audio » (payant, estimation affichée), select **langue** (auto + 16 : fr, en, es, de, it, pt, nl, pl, ru, uk, tr, ar, ja, zh, ko, hi), select **vers** + **Traduire vers …** (P16), liste éditable (début/fin `00:00.000`, caler sur la tête, découper, fusionner, œil, caractères par sous-titre), **+ première réplique**, **importer .srt / .vtt**, **COUVERTURE DU MONTAGE** (x ÷ 62,7 s, « n plans sans sous-titre — traiter n plans ▸ »), **zone sûre 10 %**, **UI réseaux**, export .srt / .vtt / .txt / .ass (Télécharger) · onglet **Style et placement** : encart « APERÇU ET GRAVURE : LES ÉCARTS » (arbitrages mesurés fond/contour/karaoké), **Police** (16 fontes embarquées), Taille px, Couleur, Contour, Marge du bord %, **PRÉRÉGLAGES** (9 + moteur), **Placement** (bas/milieu/haut · centré · marge · largeur), Texte (gras/italique/souligné/capitales), Fond (ajusté/boîte, opacité), Contour et ombre, **Karaoké** (cumulatif · remplissage / boîte), **Animation** (aucune / fondu / pop), Réinitialiser · **Seuils** EBU (car./ligne, lignes, écart min, norme) et avertissements (vitesse de lecture, trop court/long, chevauchement) avec bouton qui corrige |
| **Sons** (tiroir, B, `DzSfx`) | bouton `sons` / `+` d'en-tête audio | onglets Tous · ★ · SFX · Voix · Musique · Importés · Générer ; recherche `/`, tri Récents / Nom / Durée / Favoris d'abord ; « Importer un son », « Générer un SFX » (606 CC0 livrés + génération ElevenLabs sur description), dépôt de fichiers ; raccourcis Espace préécoute, ↑↓, Entrée insérer, F favori, Suppr, B fermer |
| **Bibliothèque** (`__dzLibPicker`) | bouton **lier**, « Bibliothèque… », `+` d'en-tête V | 996 vignettes, tri mtime, recherche, filtre Rendus vidéo / Images / Sons selon la piste, import fichier, Figma ; dépose à la tête de lecture ; « pas une vidéo » chip pour les sources refusées |
| **Projets** | bouton **projets** | `n enregistré`, **enregistrer sous…**, par projet : ouvrir, dupliquer, renommer, supprimer ; `montage_projects/*.json` + `montage_saved.json` (brouillon courant, autosauvegarde) |
| **Raccourcis** | ? | 37 actions remappables (voir §8), stockage local, recherche, réinitialiser |
| **Preview 480p / Rendre & publier** (popover) | boutons de la barre de titre | ligne coût `$0.00`, « rendu ffmpeg (local) · durée », pour le rendu : « publication · brouillon Scheduler — gratuit » ; progression `n % · étape` ; Réessayer ; « Timeline de démonstration — aucune source réelle » en démo |
| **Narration** | T | voir §1 |
| **Rendus plus récents** | inspecteur d'un plan V1 | « Remplacer la source… » / « Revenir à la version précédente » (P6, rapprochement par titre) ; « Ce plan n'est pas une vidéo » ; extraction du son du plan vers A1 (P12) |

## 8. Gestes et raccourcis (relevés dans le panneau ?, 37/37)

| Section | Touche | Action |
|---|---|---|
| Lecture | Espace · J · K · L · ← → (Maj 10) · ↑ ↓ · Home · End · F · G | lecture/pause · molette arrière ×1×2×4 · pause · avant · image ± · coupe précédente/suivante · début/fin · plein écran · zones sûres |
| Montage | Suppr · Alt+C · Ctrl+Z · Ctrl+Y · N · R | supprimer clip ou losange · lame à la tête · annuler · rétablir · aimanter (bords, tête, 0) · ripple |
| Affichage | Ctrl+= · Ctrl+- · Maj+Z · T · O · ? · Ctrl+molette · Échap | zoom crans · zoom 100 % · Narration · barre OUTILS · panneau · zoom continu · fermer |
| Audio | B · M · S (Maj multi) · D · Maj+D · Alt+← → (Maj 10) · Alt+↑ ↓ | tiroir Sons · muet piste du clip · solo · fondu entrée/sortie cycle · décaler 1 image · gain ±1 dB |

| Geste souris | Effet |
|---|---|
| glisser le centre d'un clip | déplacer (aimant 8 px sur bords des autres clips, tête, 0, fin) ; Maj non relevé |
| glisser le bord gauche / droit | rogner / allonger (min 0,3 s ; bord droit V1 en mode ripple décale les suivants) |
| glisser le losange d'une jonction V1 | durée de la transition (bulle « fondu · 0.40 s — poignées : durée · clic : régler ») |
| double-clic sur un clip audio | pose un losange d'automation (t, dB) ; glisser = régler ; clic droit = retirer |
| poignées de fondu aux bords d'un clip audio | fade in / out |
| glisser dans le lecteur sur l'overlay | déplacer ; poignées échelle / rotation (aimant 0/±45/90°) ; double-clic = plein cadre ; flèches ±0,5 % (Maj 2 %), Échap |
| glisser ⋮ d'un en-tête de piste | réordonner (ou ▲ ▼) — l'ordre décide la composition |
| dépôt de fichier / asset dans le lecteur ou une piste | ajout (durées par défaut image 4 s, audio 8 s, vidéo 6 s ; la timeline s'allonge au lieu de rogner) |
| clic sur un mot du panneau Texte | sélection de plage → « couper la sélection » |

## 9. Comportements notés

- La barre OUTILS flottante **recouvre V2 et V1** à sa position d'origine
  (y 595–678 sur des pistes en 606–700) : un clic sur un clip de V2 tombe sur
  ses boutons ; il faut la replier (O) ou la déplacer.
- Deux sortes de pistes vidéo : « vidéo » (plein cadre, recouvre V1, son
  extrait sur dialogue) et « incrust. » (overlay muet) ; V1 seule porte
  transitions, vitesse, effets vidéo et maître de durée ; 400 sans clip V1.
- Le lecteur joue V1 + A1 en direct ; musique et SFX ne jouent en direct
  que via le pool audio P7 ; transitions et effets ne se voient qu'après une
  **Preview 480p** (proxy par source, `POST/GET /proxy`).
- L'historique (Ctrl+Z, 10 pas) ne mémorise que `{clips, mixDb}` : ni les
  pistes, ni la durée, ni le style des sous-titres, ni le projet ouvert.
- Sous-titres = UNE piste S1, une langue à la fois (la traduction remplace le
  texte, temps conservés) ; karaoké par mot gravé en ASS ; `words[]` par
  mot quand la transcription les fournit.
- Coût affiché avant tout déclenchement payant (ElevenLabs, transcription) ;
  rendu et preview toujours gratuits et locaux.
- Autosauvegarde vers `montage_saved.json` ; chip d'état en barre de titre.
- Sortie : MP4 H.264/AAC uniquement, 1080 de haut, 30 i/s, 4 formats ; pas de
  file de rendu (un job à la fois), pas d'export audio seul, pas d'EDL/XML.

## 10. Non relevé

| Élément | Raison |
|---|---|
| Inspecteur Overlay / Clip audio / Effets sur un clip RÉEL, sélecteur Bibliothèque, Rendus plus récents | jeu de données vierge : la démo est une maquette qui refuse ces panneaux ; relevés depuis le code (strings et titres cités) |
| Preview 480p et rendu final réels | non déclenchés (rien à rendre en démo) |
| Comportement Maj/Alt au glisser des clips | aucun modificateur dans `clipDown` : il n'y en a pas |
