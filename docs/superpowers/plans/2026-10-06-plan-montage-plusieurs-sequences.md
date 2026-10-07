# Montage — plusieurs séquences : transitions et vitesse sur les pistes vidéo hautes, fondus des clips d'ajustement (t117)

> Plan écrit le 06/10/2026 après mesure du terrain (main `fc052852`). Décisions de l'utilisateur (06/10) :
> **(1)** le son d'un plan accéléré suit **la règle de V1 actuelle** ; **(2)** transitions et vitesse vont aux pistes
> vidéo plein cadre **ET** aux pistes d'incrustation.

**But :** lever l'écart assumé de la tâche 20 / P14 du plan-montage (`2026-09-03-plan-montage.md:1898-1901`) : « une
piste "vidéo" n'a ni xfade, ni vitesse, ni effets — les fournir est le chantier "plusieurs séquences" ». Et donner des
fondus d'entrée / sortie aux clips d'ajustement (J1).

## Ce que le terrain dit — mesuré le 06/10/2026

| Fait | Où | Conséquence |
|---|---|---|
| Les **effets** et masques des pistes hautes sont DÉJÀ rendus (lot L5) | `montage_service.py:5450-5467`, `:4279-4338` | hors périmètre ; le commentaire de `dzmGradeAllBtn` (`montage.js:1326-1331`) est périmé → à corriger |
| Chaque plan d'une piste haute = une entrée + un `overlay=…:eof_action=pass:enable='between(t,st,en)'` sur le flux composé, par `layer` croissant | `:4071-4091`, `:4365-4368` | une piste « séquencée » devient UN flux composé UNE fois |
| Le payload jette `transition`, `transition_s`, `speed` (et dz/reframe/retime/stab/matte) hors V1 | `:5417-5467` | les garder pour toute piste vidéo |
| V1 : vrai fondu seulement entre deux plans EN CONTACT, centré sur la jonction, poignées réelles de la source sinon image figée ; coupe 0,04 s (`_cut_tau`) partout ailleurs, trous compris | `:3700-3775` | même loi pour les pistes hautes : on EXTRAIT le calcul des jonctions de V1 en une fonction partagée, V1 l'appelle (identité à l'octet tenue par ses bancs) |
| Vitesse V1 : lecture `d·spd` de source, `setpts=PTS/spd` AVANT `fps`, durée timeline inchangée ; **aucun atempo** — le clip A1 « son du plan » garde sa vitesse, l'écran signale la désynchro (sauf « remplir », qui propage la vitesse au jumeau) | `:105-110`, `:1276-1303`, `montage.js:4931` | décision (1) : même règle, mot pour mot |
| J1 : clips `{start, end, effects}` en post-passe ; `effects_engine._timed` sait DÉJÀ `fade_in` / `fade_out` par effet (sauf `_NO_CROSSFADE`) | `:5468-5477`, `:4587-4593`, `effects_engine.py:1089-1159` | fondus J1 = des champs à transmettre, pas un moteur |
| Écran : vitesse, transitions, losanges de jonction, Alt+T, restauration de `transition` gardés à V1 ; le menu « Transition… » s'ouvre DÉJÀ sur V2 sans effet au rendu (piège) | `patch_bundle_montage.py:3573-3577, 5120-5136, 4128-4131`, base `svmSetV1Speed`, `svmV1Junctions`, restauration `:1932-1933` | levée des portes, une par une, bancs à l'appui |

### Mesures ffmpeg 8.1.1 (06/10/2026, scratchpad `xf/`)
- `xfade` **préserve l'alpha** (rgba et yuva420p : le vide reste (0,0,0,0)).
- Mais il fond en **prémultiplié** contre le transparent : à mi-fondu le rouge vaut (151,0,0,153) → composé tel quel sur
  blanc ≈ (192,102,102) au lieu de (255,102,102) — **halo sombre**.
- `unpremultiply` APRÈS un xfade : (243,102,102) — 12 niveaux d'écart, et faux dès deux fondus enchaînés.
- **Retenu : `premultiply` sur chaque toile AVANT les xfade, `unpremultiply` UNE fois à la fin** : (253,102,102) et
  (154,154,255) pour (255,102,102) / (153,153,255) ; deux fondus enchaînés et une toile à 50 % : ≤ 2 niveaux.

## Architecture

Une piste vidéo haute est **séquencée** quand au moins une de ses jonctions est un vrai fondu (plans en contact,
transition ≠ cut) ou qu'un de ses plans a une vitesse ≠ 1. Sinon : **chemin actuel, commande identique à l'octet**.

Piste séquencée :
1. chaque plan est construit comme aujourd'hui (cover ou transformé, effets, masque, ombre), mais en **horloge
   locale**, puis posé sur une **toile transparente** w×h (`color=black@0`) à sa position ; les points de mouvement
   (horloge GLOBALE aujourd'hui) reçoivent le décalage de la toile ;
2. toiles et trous (toiles transparentes à la durée du trou) sont `premultiply`, enchaînés par `xfade` selon la loi des
   jonctions de V1 (fonction extraite, partagée), poignées réelles lues à la vitesse du plan ;
3. `unpremultiply`, `setpts` au début de la piste, puis UN `overlay=0:0:eof_action=pass` au rang `layer` de la piste.

Vitesse d'un plan haut : `_v1_speed` généralisée (0,25..4), lecture `d·spd`, `setpts=PTS/spd` avant `fps`, durée
timeline inchangée. Son : aucun atempo, le jumeau garde sa vitesse, l'écran le dit — comme V1.

## Tâches

### T1 — la loi des jonctions extraite (backend, aucun changement de rendu)
`_jonctions(segs, seg_durs, fps, cut)` → `(amorce, debord, jonction, vrai)`, extraite de `:3709-3742` ; V1 l'appelle.
Bancs : TOUS les bancs d'identité à l'octet de V1 restent verts (`test_p1_poignees`, `test_coupe_cadence`,
`test_montage_l3`, `test_montage_l5_masque`, `test_montage_l4`, `test_retours_horloge`, `test_matte_compose`,
`test_retours_grade`) + un banc unitaire de la fonction.

### T2 — payload : les pistes hautes gardent transition, durée de transition et vitesse (backend)
Dans la construction des plans hauts (`:5417-5467`) : `transition`, `transition_s`, `speed` (bornée comme V1), `tr`
(l'id de la piste, pour grouper). Rien ne change au rendu tant que T3 n'est pas là. Banc : le payload les porte, un
plan V1 et un plan haut sans ces champs → commande identique à l'octet.

### T3 — le rendu séquencé (backend)
`_sequence_haute(...)` dans `_build_montage_command` : toiles, trous transparents, premultiply / xfade / unpremultiply,
poignées, vitesse, overlay unique au rang `layer`. Bancs-miroirs par ffprobe + PIL sur de VRAIS rendus courts :
durée = timeline ; le plan B tombe sur son `start` ; fondu centré (image du milieu = mélange) ; trou transparent (V1
visible dessous) ; pas de halo (mesure de couleur à mi-fondu) ; incrustation transformée qui fond vers une autre
position ; vitesse ×2 sur un plan haut (le contenu avance deux fois plus vite, la durée timeline ne change pas) ;
piste sans transition ni vitesse → commande identique à l'octet.

### T4 — J1 : fondus d'entrée / sortie des clips d'ajustement (backend)
`fade_in` / `fade_out` (secondes, ≥ 0, bornés à la moitié du clip) transmis aux effets du clip → `_timed`. Banc : la
commande porte le sendcmd de fondu ; sans champ → identique à l'octet.

### T5 — l'écran (patcher du bundle + montage.js)
Levée des portes V1 pour toute piste vidéo : vitesse (inspecteur, menu, `svmSetV1Speed`, payload TT10), losanges de
jonction et popover de transition, Alt+T, restauration de `transition` ; signal de désynchro du jumeau comme V1 ;
titres des boutons de pistes (le banc P14 qui les épingle suit) ; fondus J1 dans l'inspecteur d'un clip d'ajustement ;
commentaire périmé de `dzmGradeAllBtn`. Règles de la chaîne : `scripts/restaurer_bak_montage.py` avant les bancs ;
nouvelles sections en queue du maillon montage ; épingles `x.useState(` relevées si un état est ajouté.

### T6 — mutations, preuve navigateur, déploiement
Mutations (fondu sans premultiply → halo rouge ; jonction non partagée ; vitesse ignorée ; trou noir au lieu de
transparent ; porte V1 rétablie…) ; preuve à l'écran sur un backend de preuve ; installation (Python touché : arrêt,
l'utilisateur relance).

## Découpage en PR
PR 1 = T1 + T2 + T3 + T4 (backend), PR 2 = T5 (écran), chacune avec ses bancs et ses mutations.
