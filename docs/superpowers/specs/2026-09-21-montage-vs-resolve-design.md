# Montage « aussi poussé que Resolve » — conception depuis les deux inventaires (21/09/2026)

> Inventaires : `2026-09-21-davinci-resolve-inventaire.md` (chez eux) et
> `2026-09-21-montage-inventaire.md` (chez nous, relevé en réel sur 8799 +
> code). Équivalent chez nous : couche `frontend/patches/montage.js`
> (`window.DzMontage`, patcher `patch_bundle_montage.py`), bloc `sonvfx`
> (intouchable), `vfxrack.js`, `subs.js`, `backend/app/services/
> montage_service.py`, `effects_engine.py`, `sfx_service.py`,
> `subtitle_service.py`. **Décisions à valider par l'utilisateur AVANT tout
> plan et tout code.** Rien de ce qui existe n'est modifié : chaque ligne
> « Conservé » reste octet pour octet ; chaque « À faire » s'ajoute par un
> champ optionnel du payload (commande ffmpeg identique en son absence,
> règle R1…S1 déjà en vigueur), une section neuve du patcher `montage` (ou
> d'un maillon aval neuf) et un banc autonome.

## 0. Contraintes mesurées qui bornent les décisions

| Fait mesuré (21/09) | Conséquence |
|---|---|
| ffmpeg 8.1.1 essentials livré : `vidstabdetect/transform`, `deshake`, `minterpolate`, `xfade` (**58** transitions), `rubberband`, `arnndn`, `afftdn`, `sidechaincompress`, `loudnorm`, `ebur128`, `chromakey`, `zoompan`, `scdet`, `vectorscope`, `waveform`, `histogram`, `curves`, `colorbalance`, `selectivecolor`, `huesaturation`, `lut3d`, `tmix`, `deflicker`, `nlmeans/hqdn3d/atadenoise`, `xstack`, `drawtext` — TOUS présents ; encodeurs `libx264`, `libx265`, `h264_nvenc`, `hevc_nvenc`, `prores_ks`, `libvpx-vp9`, `libaom-av1`, `libopus`, `libmp3lame`, `gif` | stabilisation, retime à flux optique, 58 transitions, elastic wave, réduction de bruit audio/vidéo, ducking, loudness, incrustation fond vert, dynamic zoom, détection de plans, scopes, roues primaires, courbes, HDR-moins tiennent **sans aucune bibliothèque** |
| Python embarqué 3.13 : stdlib + Pillow, **pas de numpy, pas d'OpenCV, pas de whisper local** ; transcription = ElevenLabs Scribe ou OpenAI whisper-1 (payants) | tout suivi d'objet / visage, masque magique, voice isolation, super scale, IA « Neural Engine » est **écarté** ou reste une option payante fal existante ; le « calage du texte connu » reste notre voie gratuite |
| Le lot 2 du plan `2026-09-03-plan-montage.md` (D1 accord de couleur, D2 recadrage, D3 auto-clips, D4 titres + transitions, D5 EDL/FCPXML) est **écrit mais jamais construit** (aucun `color_match.py`, `reframe.py`, `edl_export.py` dans `main`) | ces cinq tâches sont reprises telles quelles dans les lots ci-dessous, pas réinventées |
| L'historique n'empile que `{clips, mixDb}` (`pushHistory`, `DZM_HIST_MAX=10`) | tout ajout de propriété de clip ou de piste passe par le même point d'écriture ; l'extension de l'historique est un préalable (D-0) |
| Le lecteur ne montre transitions/effets qu'après une Preview 480p ; la barre OUTILS flottante recouvre V2/V1 à sa place d'origine | deux irritants P0 sans dépendance |
| `effects_engine.build_chain` s'applique à un segment V1 ou au cadre final (post-pass) ; le Montage n'émet que par clip V1 | un « clip d'ajustement » = un post-pass borné t0/t1 : mécanisme existant à exposer |
| 4 formats `_CANVAS`, MP4 H.264/AAC 1080/30 seulement ; un job de rendu à la fois ; `/measure` rend LUFS/TP/LRA | la « page Deliver » est une table de presets + une file, pas un moteur neuf |

## 1. Tableau d'écart

Priorités : **P0** irritant ou préalable structurel · **P1** parité de montage
quotidien · **P2** finition (couleur, audio, stabilité) · **P3** confort ou
rare. « Conservé » = déjà là, on n'y touche pas.

### 1.1 Timeline, découpe, trim (page Edit / Cut)

| Chez eux (Resolve) | Aujourd'hui chez nous | Décision | Prio |
|---|---|---|---|
| Pistes V/A illimitées, ciblage, verrou, sync, réordonnancement | pistes dynamiques `vidéo` / `incrust.` / `audio` / S1, verrou 🔒︎, ▲▼ et ⋮, ordre = composition (`svmTracksOf`, P1/P14) | **Conservé** | — |
| Historique complet (toute action annulable) | `pushHistory` : clips + mix seulement ; pistes, durée, style S1, projet hors historique (dit dans chaque titre) | **À faire D-0** : `dzmHistPush(etat)` pur (clips, mixDb, tracks, dur, subsStyle, segments), même pile, `DZM_HIST_MAX` 10 → 50 ; les six titres « Ctrl+Z NE retire PAS » sont réécrits — **exécuté 21/09/2026** : `dzmHistSnap` / `dzmHistApply` purs, l'instantané porte SEPT clés (`clips, mixDb, tracks, dur, subsStyle, range, markers`), `DZM_HIST_MAX` 50, les six titres réécrits ; **écarts** : une clé ABSENTE du projet est portée par l'instantané et RESTAURÉE ABSENTE (`s[k]=p[k]` sans condition — sans quoi « Annuler » laissait la piste ajoutée sur le projet de démonstration, qui n'a pas de clé `proj.tracks`) ; la coalescence est de 600 ms sur la durée et de 600 ms sur le style S1, donc deux gestes plus rapprochés que cela ne font qu'un seul pas d'annulation | P0 |
| Barre d'outils fixe au-dessus de la timeline | barre OUTILS flottante, origine (246,595) = SUR V2/V1 | **À faire D-1** : origine sous le transport et à droite des en-têtes, hors des pistes (`dzmTbGeo`) ; aimant conservé — **exécuté 21/09** : origine au-dessus du transport (`bottom:calc(100% + 8px)`) ; mesuré 1400 × 900 : barre y 446–529, transport 542, clip V2 cliquable ; **écart mesuré à 1400 × 720** : la barre dépliée (y 269–352) recouvre le pied du cadre de prévisualisation (y 114–354, zone du sous-titre incrusté) sans recouvrir aucune commande — elle reste repliable (O) et déplaçable ; à traiter si un usage sur petit écran le demande | P0 |
| Insert · Overwrite · Replace · Fit to Fill · Place on Top · Append at End · Ripple Overwrite (overlay au dépôt + boutons) | un seul mode : pose à la tête sur la piste choisie, la timeline s'allonge (`dzmAdd`, P10) ; « Remplacer la source… » (P6) = Replace à durée égale ; « Envoyer vers → Montage » | **À faire D-2** : `dzmInsertMode(clips, clip, mode)` pur avec 5 modes — insérer (ripple des suivants), écraser, ajouter en fin, poser au-dessus (piste vidéo libre suivante), écraser en ripple ; sélecteur dans le picker Bibliothèque et l'overlay du lecteur au dépôt (5 zones) ; Fit to Fill = Replace + `speed` calculé (C4 existe) — **exécuté 21/09/2026** : SIX modes (`ecraser, inserer, fin, dessus, ripple_ecraser, remplir`) dans `DZM_MODES`, cœur pur `dzmInsere` / `dzmInsereUn` / `dzmCarve` / `dzmPose`, rangée `DzmModeBar` dans le sélecteur d'assets, et `addAsset` passe désormais par `DzTracks.insere` ; **écarts** : `inserer` et `ripple_ecraser` ne rippent QUE la piste visée (choix assumé — le ripple de Resolve est lui aussi local à la piste) ; le jumeau audio n'est posé que s'il n'existe pas déjà (`twinPlan`), donc A1 peut se désynchroniser après un « insérer » ; le mode n'est PAS persisté et retombe sur « écraser » au rechargement ; Fit to Fill est le mode `remplir`, dont la vitesse est écrêtée à [0,25 ; 4] et l'écrêtage est DIT dans la note ; l'overlay au dépôt (5 zones) n'est PAS livré — seule la rangée du sélecteur l'est | P1 |
| Trim contextuel : Ripple · Roll · Slip · Slide, trim en lecture, asymétrique | bord gauche/droit = rogner/allonger (min 0,3 s), bord droit V1 + R = ripple ; pas de roll, slip, slide ; `srcIn` porté par les clips | **À faire D-3** : dans `clipDown`… non — le bloc est intouchable : couche aval `dzmTrim` qui intercepte `pointerdown` sur la jonction (roll = les deux bords, durée totale fixe), **Alt+glisser centre = slip** (déplace `srcIn` sans bouger start/end), **Maj+glisser centre = slide** (voisins compensent) ; curseur qui change ; fonctions pures `dzmRoll/Slip/Slide` bancées sous node — **exécuté 21/09/2026** : `dzmSlip` (Alt + glisser le centre, bornes fixes, `srcIn -= ds × vitesse`), `dzmSlide` (Maj + glisser le centre, les deux voisins compensent) et `dzmRoll` (Alt + glisser le losange de jonction, T3b sur `.svm-junc` pour que les coupes FRANCHES aient elles aussi une poignée), tous purs et rejoués depuis l'état du `pointerdown` ; **écarts** : la borne HAUTE du slip est inconnue à l'écran (`dzmPose` retire `srcDur` du clip posé, donc la couche n'a pas la longueur de la source et ne peut pas l'imposer) ; pas de curseur contextuel — c'est le `title` du clip qui énonce les trois gestes ; le roll ne vit que sur V1 (seules les jonctions V1 portent une poignée) ; pas de trim en lecture ; pas de trim asymétrique ; la borne de tête de source (`srcIn ≥ 0`) est tenue pour le slide et pour le roll | P1 |
| Trim editor A/B dans le viewer, compteurs, nudge | — | **À faire D-3b** (après D-3) : popover de jonction existant (transition) gagne deux vignettes A/B (`/strip` existe) et ±1 image | P3 |
| Smart indicator (coupe la plus proche de la tête) | aimant N sur bords/tête/0 ; ↑↓ coupe précédente/suivante | **Conservé** ; D-2 pose « à la coupe la plus proche » quand la tête n'est pas sur une coupe | — |
| Swap / shuffle de clips | glisser le centre | **À faire D-4** : Ctrl+←/→ sur un clip V1 sélectionné = échanger avec le voisin (`dzmSwap` pur) — **exécuté 21/09/2026** : Ctrl+← et Ctrl+→ échangent le clip sélectionné avec son voisin de CONTACT (≤ 0,1 s, `dzmVoisins`) en figeant les DEUX bornes extérieures du couple, si bien qu'un trou ou un chevauchement toléré reste au raccord INTÉRIEUR au lieu d'être absorbé ; **écarts** : la transition est une propriété du bord ENTRANT, donc un fondu DISPARAÎT si le plan qui le porte devient le premier de sa piste ; le jumeau A1 ne suit PAS (seule la piste du clip échangé bouge) ; et quand deux voisins sont à la même borne, `dzmVoisins` retient le `end` maximal à gauche — règle héritée, l'égalité exacte n'est pas tranchée | P3 |
| Marqueurs (couleur, titre, description, mots-clés, durée) et annotations | aucun marqueur ; losanges = transition / automation / position | **À faire D-5** : `proj.markers[] {t, dur?, color, title, note}`, M (déjà pris : muet) → **Maj+M** pose, panneau index (liste, aller-à, supprimer), rendus sur la règle ; exportés dans le JSON projet ; annotations **écartées** — **exécuté 21/09/2026** : marqueurs `{id, t, color, title, note}` (`dzmMarkerAdd` / `Remove` / `Update` / `Next`, `dzmMarkersFrom`), Maj+M pose ou retire à la tête, Ctrl+↑ et Ctrl+↓ vont au précédent et au suivant, Ctrl+M ouvre l'index (titre validé au blur, couleur au change), losanges sur la règle, persistés par `POST /save` et réassainis par `_save_record` ; **écarts** : pas de `dur`, donc pas de marqueur de PLAGE ; pas d'annotations ; pas de mots-clés ; l'espacement minimal est de 0,15 s avec une borne LARGE (`<=`) aux TROIS endroits qui la tiennent, si bien qu'un couple plus serré que 0,15 s est FUSIONNÉ à la restauration — c'est toujours le premier des deux qui reste | P1 |
| Timelines empilées / onglets, copier-coller entre timelines | projets nommés (ouvrir, dupliquer…), un seul ouvert | **À faire D-6** : copier/coller de clips (Ctrl+C/V) entre projets via presse-papiers local (`dz_montage_clipboard`) ; onglets **écartés** | P3 |
| Double timeline (Cut) | zoom 4 crans + Ctrl+molette, `− total +` | **Conservé** ; **À faire D-7** : mini-carte de la timeline entière (30 px) au-dessus de la règle, clic = centrer (`dzmMinimap` pur sur les clips) | P2 |
| Boring detector (plans trop longs, jump cuts) | — | **À faire D-8** : `dzmBoring(clips, maxS, minFrames)` pur → surlignages gris/rouge sur V1, seuils dans un popover | P3 |
| Source tape, sync bin, multicam, Multi Source | — (E1 du plan) | **Écarté** : sources générées 1080p, jamais multi-caméra | — |
| Adjustment clips (effet sur tout ce qui est dessous, borné) | effets par clip V1 avec t0/t1 ; post-pass global existe dans `build_chain` mais non exposé au Montage | **À faire D-9** : piste `ajust.` (kind `adjust`) dont chaque clip porte une pile d'effets appliquée en post-pass sur `[t0,t1]` (`_build_montage_command` : champ optionnel `adjust_clips`) ; même rack `DzVfx.Stack` | P1 |
| Raccourcis entièrement personnalisables, presets Premiere/FCP/Avid, export | 37 actions remappables, stockage local, recherche | **Conservé** ; **À faire D-10** : preset « Resolve » (JKL, I/O, Ctrl+B lame, Ctrl+T transition) + export/import JSON du mappage | P3 |
| I / O points d'entrée-sortie, marquage audio/vidéo séparé | in/out = bords du clip ; pas de plage de timeline | **À faire D-11** : plage I/O sur la règle (`proj.range`), utilisée par D-2 (Fit to Fill), par « couper la sélection » (P3 existant) et par le rendu partiel (D-30) — **exécuté 21/09/2026** : plage `proj.range` = `{in, out}` (`dzmRangeSet` / `dzmRangeFrom` / `dzmRangeLen` purs, barre `DzmRangeBar` sur la règle), I et U posent l'entrée et la sortie, X efface la plage, Maj+X coupe la plage en ripple, plage persistée par `POST /save` et assainie par `_save_record` ; **écarts** : quand la plage ne CHANGE pas, la poser sort TÔT sans écrire ni empiler un pas d'historique (visible sur le projet de démonstration, qui n'a aucune clé `range`) ; une demi-plage (entrée seule ou sortie seule) est NOTÉE mais ne dessine pas de bande et n'allume pas « remplir » ; « couper la plage » rippe TOUTES les pistes non verrouillées et non bouclées (`dzmCutOpts`), pas seulement la piste ciblée | P2 |

### 1.2 Lecture et viewer

| Chez eux | Chez nous | Décision | Prio |
|---|---|---|---|
| JKL, images, plein écran, zones sûres, waveform overlay, scrub audio | J/K/L ×1×2×4, ← →, F, G, waveforms sur clips, vu-mètre | **Conservé** | — |
| Transitions et effets visibles en lecture | après Preview 480p seulement | **Adapté D-12** : lecture directe des `xfade` simples (fondu, noir, blanc) en CSS dans le lecteur (opacité), les autres restent « après preview » et le disent — **exécuté 22/09/2026** : `dzmVeil` + `.svm-xfveil` écrit par `liveSync` (voile noir/blanc/opacité triangulaire sur ±s/2 autour du raccord, cache `_dzVeil`) ; **écarts** : seuls `fade`, `fadeblack`, `fadewhite` (`_XFADE_LIVE`) ; pas de crossfade A/B (un seul hôte) : `fade` et `fadeblack` se voient pareil en direct ; à égalité d'alpha entre deux jonctions l'ordre du tableau tranche ; les sous-titres restent au-dessus du voile comme au rendu | P2 |
| On-screen controls transform (PIP), dynamic zoom (rectangles vert/rouge) | poignées overlay (déplacer, échelle, rotation, aimants), Aligner 9 positions, trajectoire (≤ 8 points, linéaire) | **Conservé** ; **À faire D-13 Dynamic zoom** sur un clip V1 : deux rectangles début/fin dans le lecteur → `zoompan` (ou `crop+scale` par expression `t`) ; champ optionnel `dz:{x0,y0,w0,x1,y1,w1}` ; ease douce/linéaire | P1 |
| Keyframes (losange) sur TOUT réglage, éditeur de courbes sous le clip, ease bézier, loop/pingpong | trajectoire x/y/rot (overlay), automation dB (audio, 12 pts), bornes + rampe d'effet (10 courbes) | **Adapté D-14** : étendre les points de trajectoire à `scale` et `opacity` (payload `motion_points[].scale/opacity`, `_mp_lerp_expr` généralisé) ; pas d'éditeur de courbes générique — les rampes d'effet gardent leurs 10 courbes | P2 |
| Retime : rampes de vitesse par courbe, optical flow / frame blending / nearest, Speed Warp | vitesse constante 25…400 % sur V1 (setpts), aucune interpolation | **À faire D-15** : qualité `retime:"nearest"|"blend"|"flow"` (`tblend` / `minterpolate=mi_mode=mci`) sur V1 ; **rampes** = « diviser le clip à la tête puis vitesses différentes » (lame existante) + option « lisser la jonction » ; Speed Warp **écarté** (IA) | P2 |
| Stabilisation (camera lock, zoom, crop, smoothing, strength) | — | **À faire D-16** : propriété de clip V1 `stab:{smooth, crop, zoom}` → passe 1 `vidstabdetect` (job en tâche de fond, cache par source comme `/proxy`), passe 2 `vidstabtransform` dans la commande ; bouton « Stabiliser » + curseurs | P2 |
| Correction d'objectif | — | **À faire D-17** : effet `lensdistort` existe (catalogue) → **Conservé** ; renommer la fiche « Distorsion d'objectif » avec un preset « corriger » | P3 |
| Smooth Cut (gomme un jump cut par flux optique) | — | **À faire D-18** : transition `smooth` = `minterpolate` sur 0,2 s autour de la jonction (segment court) ; mesurée sur banc ; si le résultat est mauvais, écartée et dite | P3 |
| Picture in picture Resolve FX (taille, position, coins arrondis, ombre) | overlay piste incrust. : x/y/échelle/rotation/opacité | **Conservé** ; **À faire D-19** : `radius` (coins, via `geq`/masque alpha) et `shadow` sur overlay | P3 |

### 1.3 Transitions, titres, graphiques

| Chez eux | Chez nous | Décision | Prio |
|---|---|---|---|
| > 100 transitions, aperçu au survol, durée par glisser | 7 (`SVM_TRANS`, `_XFADE`), losange glissable, « à toutes les coupes » | **À faire D-20** (= D4 du plan, transitions) : exposer les **58** `xfade` en galerie par familles (fondus, glissements, volets, zooms, pixels, formes) avec vignette animée générée une fois par ffmpeg (paire de couleurs), `_XFADE` étendu, `SVM_TRANS` inchangé (couche aval ajoute) — **exécuté 22/09/2026** : `_XFADE` 58 + familles + `GET /transitions`, galerie `DzTracks.TransGrid` par familles avec aperçu animé CSS par famille (pas de vignette ffmpeg), `<select>` de l'inspecteur, `svmTransLabel` lit le catalogue ; **écarts** : durée 0,1–1 s conservée ; `crossfade`/`xfade` hérités acceptés ; `fadewhite` sans voile dans l'aperçu (le voile blanc du bundle est accroché à `flash`) ; galerie reconstruite à chaque cran du curseur (perf non mesurée) ; popover bornée 52vh (mesuré 399 px dans le volet) ; `distance` classé en fondu | P1 |
| Titres 2D (Text, Text+), lower thirds, > 100 Fusion titles, style par caractère, emoji, navigateur de polices | S1 sous-titres (16 fontes, 9 préréglages, karaoké, fondu/pop) ; narration ; aucun clip « titre » | **À faire D-21** (= D4 titres) : piste/clip **Titre** (kind `title`) rendu en ASS (même moteur, `\pos/\an/\t`) avec 8 gabarits animés dans la charte (titre plein cadre, tiers inférieur, légende, compteur, chapitre, citation, hashtag, CTA) ; champs texte/police/taille/couleur/position/entrée-sortie ; **pas** de style par caractère ni de 3D — **exécuté 22/09/2026** : `titles.py` (8 gabarits ASS `plein_cadre, tiers_inferieur, legende, compteur, chapitre, citation, hashtag, cta`, mesurés à l'image, `font_line_height` appliqué, repli par largeur mesurée), piste `t1` genre `title` gravée avant S1 (`titles_ass` `[tt{j}]`), routes `/titles` et `/title-preview` (cache borné), `Maj+T`/chip T+/« + » de T1, `DzTracks.TitleInspector` (8 cartes PNG, texte/sous-texte/couleur/police/taille), aperçu vivant `.svm-livetitle` sous le voile ; **écarts** : position et entrée/sortie portées par le GABARIT (pas de champ libre) ; pas de style par caractère, ni 3D, ni emoji, ni navigateur de polices au-delà des 16 embarquées ; boîte OPAQUE (la conception disait `&H60`) et contour encre ; un titre qui dépasse la fin de V1 est coupé par `-t total` (Resolve allonge la timeline) ; aucun `@font-face` pour les 16 fontes → l'aperçu vivant ne montre que le gabarit (ni couleur, ni police, ni taille) — la Preview 480p fait foi ; piste `t1` unique (pas de titres empilés) et déplaçable sous V2 à l'écran alors que le rendu grave au-dessus ; `dzmTtTpl` mutile un nom de gabarit au lieu de le refuser (saisie non libre) ; `_spec_apercu` borne l'aperçu à 10 s ; un carton dont le texte est vidé est refusé à voix haute et le titre précédent conservé ; `sub` sans `text` est perdu | P1 |
| Subtitle generator, pistes multiples = langues, export TTML/SRT/VTT, import TTML/XML | S1 unique, traduction remplace le texte, import .srt/.vtt, export .srt/.vtt/.txt/.ass | **À faire D-22** : pistes S2… (kind `subs`, `lang`), une seule **gravée** (bascule œil), les autres exportées ; TTML export **écarté** (aucun consommateur chez l'utilisateur) | P2 |
| Lottie / OGraf HTML, PSD multi-calques | images PNG/JPG/WebP, sprites VFX (Spritelab) | **Écarté** (Lottie = rendu hors ffmpeg) ; les feuilles de sprites existantes couvrent l'animation | — |
| Fusion : nœuds, particules, trackers, roto, 3D, scripting | nœud Effects du Studio (hors Montage), VFX particules locaux, Vectorlab/Spritelab | **Écarté** dans le Montage (le Studio est notre page « Fusion ») | — |

### 1.4 Audio (page Fairlight + Edit)

| Chez eux | Chez nous | Décision | Prio |
|---|---|---|---|
| Niveau, pan, pitch, EQ 6 bandes par clip ; fader/mixer par piste ; vu-mètres | gain, fondus + courbes, vitesse ×0,5–2 (atempo), automation 12 pts, bus dialogue/musique/sfx, faders d'en-tête, vu-mètre gradué ; fx chain : filter, eq3, denoise, deesser, compressor, distortion, echo, reverb, stereo, normalize | **Conservé** ; **À faire D-23** : `eq` 6 bandes (`anequalizer`, ou 6 × `equalizer`) et `pan` (`pan=`) ajoutés au vocabulaire `sfx_service` (types nouveaux, ordre `_FX_ORDER` étendu) ; pitch **écarté** (rubberband n'est pas requis : atempo conserve déjà la hauteur) | P2 |
| Ducking automatique (source dialogue → cible musique) | ducking auto avec presets/attaque/retour/seuil | **Conservé** | — |
| Normalisation, loudness meters aux normes (bleu/jaune/rouge), analyse hors ligne | `normalize target_lufs` par clip ; `POST /measure` ebur128 (LUFS I / TP / LRA) affiché « dernière mesure » | **À faire D-24** : cible de programme (`-14` YouTube/TikTok, `-16` podcast, `-23` EBU) dans le popover de rendu → `loudnorm` 2 passes sur le mix final (champ optionnel `loudness`), pastille tricolore sur la mesure | P1 |
| Noise reduction (auto / learn), de-esser, de-hummer | denoise (`afftdn`), deesser ; pas de de-hum, pas de « learn » | **À faire D-25** : `dehum` (notch 50/100/150 Hz via `bandreject`) ; « apprendre le bruit » = `afftdn` avec `sn` sur une plage I/O (D-11) ; Voice Isolation IA **écartée** | P2 |
| Enregistrement voix off / multipiste, ADR, Foley sampler | narration TTS ElevenLabs par bloc | **À faire D-26** : bouton **Enregistrer** (MediaRecorder du navigateur → `POST /videos/upload` provider `ugc` → clip A1 à la tête, prises empilées comme clips successifs) ; ADR/Foley **écartés** | P2 |
| Elastic wave (retime sans changer la hauteur) | atempo (hauteur conservée) sur ×0,5–2 | **Conservé** (équivalent) | — |
| Track layers, bounce, external processing, VST | — | **Écarté** (hors périmètre desktop) | — |
| Sound library intégrée (audition, sync à la tête) | tiroir Sons : 606 CC0, favoris, import, génération | **Conservé** | — |
| Sync scrollers, index (clips/pistes/marqueurs), dossiers de pistes | — | D-5 fournit l'index des marqueurs ; le reste **écarté** | — |
| 2 000 pistes, FlexBus, 3D audio | 3 bus fixes, N pistes | **Écarté** | — |

### 1.5 Couleur (page Color)

| Chez eux | Chez nous | Décision | Prio |
|---|---|---|---|
| Roues Lift / Gamma / Gain / Offset + master, barres, log | grade_basic : exposition, contraste, saturation, température ; 10 presets ; LUT .cube ; « à tous les plans » | **Conservé** ; **À faire D-27** : effet `wheels` (`colorbalance` rs/gs/bs · rm/gm/bm · rh/gh/bh + `lumakey`-free master `eq`), UI trois roues (canvas maison, pas de dépendance) dans le rack | P2 |
| Auto color, Shot Match, color chart match | — (D1 du plan écrit, jamais construit) | **À faire D-28** = **D1 du plan** tel quel (stats YCbCr PIL, `lutyuv`, bouton « Accorder sur le plan précédent ») ; auto color = même module vers des cibles neutres (moyenne 128/128, Y étalé) ; chart **écarté** | P2 |
| Courbes (custom RGB/Y, Hue vs Hue/Sat/Lum, Lum vs Sat, Sat vs Sat) | `curves` par presets ffmpeg dans les grades | **À faire D-29** : effet `curves` à points (`curves=r='x/y …'`) avec éditeur canvas ; Hue vs Sat / Lum via `huesaturation` par plage de teinte (6 plages) ; les autres **écartées** | P3 |
| Qualifier (HSL), Power Windows (formes, softness), tracker | moteur Mask du Studio par région (non exposé au Montage) | **À faire D-30** : masque **statique** par clip (rectangle / ellipse, adoucissement, intérieur/extérieur) limitant la pile d'effets — `build_chain` sait déjà appliquer à une région ; qualifier HSL = `colorkey`/`chromakey` en masque ; **tracking écarté** (pas d'OpenCV) | P2 |
| Scopes : parade, waveform, vectorscope, histogram, CIE | — | **À faire D-31** : `GET /montage/scopes?src&t` → PNG `waveform` + `vectorscope` + `histogram` (ffmpeg, une image), panneau repliable sous le lecteur | P2 |
| Nœuds, groupes, versions, gallery de stills, lightbox, compare wipe | grade par clip, « à tous les plans » ; `/strip` (filmstrip) | **À faire D-32** : « copier / coller le grade » (Ctrl+Maj+C/V sur la pile étalonnage), **lightbox** = grille de vignettes V1 avec pile appliquée (vignettes `/effects/preview` existantes) ; nœuds/versions/wipe **écartés** | P3 |
| Resolve FX > 90 (beauty, restoration, light, sharpen, deband…) | 38 effets (grain, bloom, halation, vignette, glitch, blur, letterbox, dreamy…) | **À faire D-33** : 8 effets ffmpeg de plus, sans modèle — `denoise_video` (hqdn3d/nlmeans/atadenoise), `deflicker`, `deband`, `unsharp`/`cas` (fiche « Netteté » existante étendue), `chromakey` (fond vert : couleur, similarité, blend, `despill`), `tmix` (traînée), `monochrome`, `lenscorrection` ; face/beauty/object removal **écartés** | P2 |
| HDR, Dolby Vision, RAW, ACES, color management | — | **Écarté** | — |

### 1.6 Média, projet, livraison (pages Media / Deliver)

| Chez eux | Chez nous | Décision | Prio |
|---|---|---|---|
| Media pool, bins, smart bins, power bins, métadonnées 200 champs, notes ★, tags | Bibliothèque unifiée (996 vignettes, provenance, recherche, « Envoyer vers »), picker par piste | **Conservé** ; notes ★ / tags Good Take **À faire D-34** côté Bibliothèque (hors Montage, table `library_assets`) | P3 |
| Sync audio/vidéo par waveform ou timecode | « son du plan » extrait à l'import (P12) | **Conservé** ; sync par corrélation **écarté** (numpy absent) | — |
| Proxies, Proxy Generator | proxy 480p par source (`/proxy`, cache) | **Conservé** | — |
| Quick Export sur toutes les pages : presets YouTube/Vimeo/TikTok/X, ProRes, H.264/H.265, audio seul, presets maison | MP4 H.264 1080/30 ; preview 480p ; Rendre & publier → brouillon Scheduler | **À faire D-35** : table de **presets de sortie** (`_DELIVER`) — YouTube 1080p/4K H.264, Shorts/TikTok/Reels 9:16 H.264, X 720p, ProRes 422 (`prores_ks`), H.265 (`libx265`/`hevc_nvenc` si présent), WebM VP9, **audio seul** (AAC/MP3/WAV), GIF 480p ; fps 24/25/30/60 ; sélecteur dans le popover ; presets maison sauvegardés (`deliver_presets.json`) | P1 |
| Render queue (plusieurs jobs, batch, remote) | un job à la fois | **À faire D-36** : file locale = liste de `(projet, preset)` exécutée en série par le worker de jobs existant ; « Ajouter à la file » ; remote **écarté** | P2 |
| Résolutions verticales/carrées, 32K, 120 fps | 4 ratios, 1080 | **Conservé** ; D-35 ajoute 4K et 60 fps | — |
| Upload direct YouTube/TikTok/Vimeo/X | brouillon Scheduler (X, TG, YT, IG) validé à la main | **Conservé** (adapté : la validation humaine reste) | — |
| DCP, IMF, MXF | — | **Écarté** | — |
| Export EDL/FCPXML/AAF, import ATEM | — (D5 du plan écrit, jamais construit) | **À faire D-37** = **D5 du plan** (EDL CMX 3600 + FCPXML, spec relue d'abord) | P3 |
| Rendu partiel (in/out) | — | **À faire D-38** : rendu de la plage I/O (D-11) — champ optionnel `range` → `-ss/-t` sur la sortie | P3 |

### 1.7 Collaboration, IA

| Chez eux | Chez nous | Décision | Prio |
|---|---|---|---|
| Cloud, verrous, chat, marqueurs partagés, présentations, live save | autosauvegarde locale, projets nommés, export/import « transfert entre machines » | **Écarté** (mono-utilisateur local) ; **À faire D-39** : **comparaison de deux projets** (ajouté / supprimé / déplacé / rogné, pur `dzmDiff` sur les JSON) — gratuit, utile pour relire une version | P3 |
| Transcription, text based editing, IntelliScript | calage gratuit du texte connu, transcription payante, couper par le texte, mots de remplissage | **Conservé** | — |
| AI Speech Generator (TTS, clonage 10 s) | ElevenLabs (voix clonées) | **Conservé** (payant, déjà) | — |
| Smart Reframe, Super Scale, Magic Mask, Voice Isolation, Music Remixer, CineFocus, Face tools, IntelliSearch, Slate ID, UltraSharpen, Motion Deblur, Close Up, Speed Warp | fal en option par clip (D2 du plan) | **Écarté** sauf **D-40 = D2 du plan** (recadrage par énergie de mouvement PIL, gratuit ; fal en option payante par clip, jamais par défaut) et **D-41 = D3 du plan** (auto-clips 15–60 s depuis épisodes/films, score LLM avec repli heuristique) | P2 / P3 |
| Détection de scènes (media page, Cut) | — | **À faire D-42** : `scdet` → « découper aux changements de plan » sur un import externe (lame automatique), et « plans trop longs » (D-8) | P2 |

## 2. Décisions tranchées (résumé, à valider)

**D-0 — Historique complet.** Une pile, tout l'état, 50 pas. Sans lui, chaque
lot suivant reproduit la phrase « Ctrl+Z ne retire pas… ».

**D-1 — La barre OUTILS ne recouvre plus les pistes.** Origine sous le
transport, hors de la grille.

**D-2 / D-3 — Les cinq modes d'édition et les quatre trims.** C'est le cœur
« Edit » de Resolve ; tout en fonctions pures bancées sous node, gestes :
Alt = slip, Maj = slide, jonction = roll. Écart assumé : pas de trim en
lecture.

**D-9 — Piste d'ajustement** plutôt que nœuds : un post-pass borné, même
rack, même moteur.

**D-13 / D-15 / D-16 — Dynamic zoom, retime à flux optique, stabilisation
vidstab** : les trois « propriétés de clip » de Resolve qui tiennent en ffmpeg
natif, chacune un champ optionnel et une passe.

**D-20 / D-21 — 58 transitions et 8 gabarits de titre** : reprennent D4 du
plan de septembre ; les titres sont de l'ASS, pas du Fusion.

**D-24 / D-35 / D-36 — Livraison** : loudness normée, presets de sortie
(codecs déjà présents), file locale. La publication reste le Scheduler.

**D-27 … D-33 — Couleur** : roues, accord de couleur (D1 du plan), courbes à
points, masque statique, scopes, huit effets ffmpeg de plus. Sans tracker.

**Écartés, et pourquoi** : multicam / source tape / sync bin (sources
générées), Fusion (le Studio est notre page nœuds), tout ce qui demande un
modèle (masques magiques, visages, voice isolation, super scale), cloud et
collaboration (mono-poste), HDR/RAW/DCP, Lottie/OGraf, VST/ADR/Foley, 2 000
pistes, tracking (pas d'OpenCV, pas de numpy).

## 3. Lots proposés (chacun livrable seul ; estimation en jours-agent, deux revues et campagne de mutations comprises)

| Lot | Contenu | Sections patcher / backend | Estimation |
|---|---|---|---|
| **L0 — socle** | D-0 historique complet, D-1 barre hors des pistes, D-11 plage I/O | M27–M29 ; aucun backend | 1,5 j |
| **L1 — édition** | D-2 cinq modes, D-3 roll/slip/slide, D-5 marqueurs + index, D-4 swap | M30–M35 ; `markers` dans le JSON projet | 4 j |
| **L2 — transitions et titres** | D-20 galerie des 58 `xfade` avec vignettes, D-21 clips Titre (8 gabarits ASS), D-12 fondus en lecture directe | M36–M39 ; `_XFADE` étendu, `titles.py`, `_subs_ass` étendu | 4 j |
| **L3 — propriétés de plan** | D-13 dynamic zoom, D-15 retime (nearest/blend/flow + rampes par division), D-16 stabilisation vidstab (job de détection en cache), D-14 keyframes échelle/opacité, D-9 piste d'ajustement | M40–M45 ; champs `dz`, `retime`, `stab`, `adjust_clips`, `motion_points.scale/opacity` | 5 j |
| **L4 — livraison** | D-35 presets de sortie (codecs, 4K, 60 fps, audio seul, GIF), D-24 loudness normée, D-36 file locale, D-38 rendu partiel | M46–M48 ; `_DELIVER`, `loudnorm` 2 passes, file dans le worker de jobs | 3 j |
| **L5 — couleur** | D-27 roues, D-28 accord de couleur (D1 du plan), D-31 scopes, D-33 huit effets, D-30 masque statique, D-32 copier/coller de grade + lightbox, D-29 courbes | M49–M55 ; `color_match.py`, `/scopes`, catalogue +9, masque région | 6 j |
| **L6 — audio** | D-23 EQ 6 bandes + pan, D-25 de-hum + apprentissage du bruit, D-26 enregistrement voix off, D-42 détection de plans | M56–M59 ; vocabulaire `sfx_service` +3, `scdet` | 3 j |
| **L7 — confort** | D-6 presse-papiers inter-projets, D-7 mini-carte, D-8 boring detector, D-10 preset clavier Resolve, D-3b trim A/B, D-19 coins/ombre PIP, D-22 pistes S2 langues, D-39 diff de projets, D-37 EDL/FCPXML (D5), D-40 recadrage (D2), D-41 auto-clips (D3), D-34 notes ★ | M60+ | 8 j (à découper) |

Ordre conseillé : **L0 → L1 → L2 → L3 → L4 → L5 → L6 → L7** (valeur
d'usage décroissante ; L0 est un préalable technique). Total hors L7 :
**≈ 26,5 j**.

## 4. Ce que cette conception ne fait pas

- Elle ne touche à rien d'existant : bloc `sonvfx`, `subs.js`, `vfxrack.js`
  restent intouchables ; toute correction de leurs comportements se porte
  dans un maillon aval (règle de `chaine-patchers-bundle`).
- Elle ne promet aucune IA : chaque ligne « IA » de Resolve est écartée ou
  renvoyée à une option fal déjà payante et déjà cadrée (E2 du plan).
- Elle n'ajoute aucune dépendance : ffmpeg 8.1.1 livré, Pillow, stdlib ;
  toute vignette, roue ou courbe est dessinée en canvas maison.
- Aucun plan ni code avant la validation de ce tableau.
