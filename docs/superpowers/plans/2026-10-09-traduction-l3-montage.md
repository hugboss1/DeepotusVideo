# Traduction L3 (t143) — Montage (couche montage.js) : consigne de saisie

Skill `traduction-deepotus`. Mécanisme de L4 (`docs/superpowers/plans/2026-10-09-traduction-l4-son-vfx-sfx-rack.md`),
appliqué à la seule couche `frontend/patches/montage.js` (window.DzTracks : pistes, barre d'outils flottante, projets,
tiroirs Médias et Texte, étalonnage, scopes, voix off, menus contextuels, raccourcis, livraison, titres…).

## Périmètre

- Tout ce qui reste en dur dans `montage.js` après L1 (Bibliothèque, Réglages) et L2 (Studio, Templates), y compris
  quelques aides de leurs composants que leurs relevés avaient laissées (`dzSendStudioRendu`, `dzMasqueSvg`,
  `dzAnimStyle`…). Les littéraux que L1/L2 ont GARDÉS restent gardés (le contrôle les ignore).
- Le patcher Montage : ses sections pour l'écran Montage vivent dans les blocs SONVFX (traduits par L4) et MONTAGE
  (cette couche) — aucune paire native à ajouter. Les textes en dur qui restent HORS couche dans ses sections
  (`__dzLibPicker` de la Bibliothèque, prolongation de clip, impression 3D, import Figma) ne sont pas du Montage : restes
  de L1 / Game Assets, signalés à part. « Voix par défaut de l'app » est un nom ENREGISTRÉ (castings) : valeur.

## Mécanisme

- Saisie : `scripts/i18n_l3/<groupe>.py` (`CIBLE = "montage"`, format `L`/`S`/`X`/`FRAGMENTS` de `outils.py`),
  positions = couche de BASE `be7f9e9f` (CRLF). Générateur `scripts/i18n_l3_generer.py` (`--seul G --restes`
  valide un groupe : textes, clés, unicité FR→EN contre TOUS les dictionnaires, plage, `node --check`).
- Sorties : `frontend/patches/montage.js`, `scripts/i18n_l3_paires.json`, `frontend/shared/i18n/montage.json` ; puis
  `i18n_assembler.py` et `refresh_layer.py --layer montage --force`.

## Groupes

| groupe | lignes (base) | contenu (indicatif) |
|---|---|---|
| montage_a | 1–1035 | pistes par défaut, ajout/retrait, tiroir Texte, mots animés, emoji |
| montage_b | 1036–1946 | tiroir Texte (suite), étalonnage global, projets |
| montage_c | 1947–2724 | remplacement de source, durées, sous-titres traduits, overlays |
| montage_d | 2725–3529 | audio des plans, jumeaux, extraction, barre d'outils (icônes, libellés) |
| montage_e | 3530–6345 | barre d'outils (câblage, géométrie), plage, modes d'insertion, marqueurs, transitions, titres, livraison |
| montage_f | 6346–7067 | plan (zoom, recadrage, retime), tiroir Médias, autoclips |
| montage_g | 7068–7799 | minimap, menus contextuels, raccourcis, copier-coller, jump cuts, comparaison |
| montage_h | 7800–8925 | scènes, panneau d'étalonnage, bruit, voix off |
| montage_i | 8926–fin | voix off (suite), scopes, visionneuse, épingles, aides L1/L2 restantes |

## Règles de saisie (celles de L4, plus deux)

1. Chaque littéral signalé par `--restes` devient `L`, `S` ou `X`. Objectif : `restes : 0`, `node --check : OK`.
2. Clé `montage.<objet>.<rôle>` (ASCII minuscule, `_` permis). La zone `montage.` est PARTAGÉE avec L4
   (`frontend/shared/i18n/montage_svm.json`, l'écran DzMontage) : une clé déjà prise là est REFUSÉE par le générateur.
   Préférer un objet propre à la couche (`montage.pistes.*`, `montage.barre.*`, `montage.medias.*`…). Mot courant
   partagé entre groupes : `montage.mots.<slug du français>`.
3. `fr` = le texte du littéral à l'identique (décodé s'il porte un échappement) ; `en` = anglais d'interface court.
   Reprendre les traductions DÉJÀ posées pour le même français (le générateur l'exige) — lire
   `frontend/shared/i18n/montage_svm.json` et `sfx.json` pour le vocabulaire du Montage : plan = clip,
   piste = track, tête de lecture = playhead, rendu = render, Bibliothèque = Library, tiroir = drawer,
   étalonnage = grading, incrustation = overlay, sous-titres = subtitles.
4. Composés : `S` avec variables `{x}` ; pluriel `.un` / `.plusieurs` ; gabarit entier par `S`.
   **Un S sur plusieurs lignes GARDE le même nombre de `\r\n`** (dans le `dzT(…)`, jamais entre `dzT(` et la clé) :
   le contrôle range les restes par numéro de ligne.
5. JAMAIS traduire une valeur envoyée au serveur, stockée (projet, localStorage), comparée (`===`, `indexOf`, clé
   d'objet, `switch`), un id, une expression ffmpeg/CSS, une combinaison de touches analysée, un libellé enregistré
   dans le projet (« son du plan », noms de pistes par défaut s'ils sont stockés…) : `X` avec la raison. Lire le code.
   Si un même littéral sert à l'affichage ET comme valeur, traduire au site d'affichage (`S`) ou garder (`X`).
6. Unités identiques → `X` ; différentes → `L`. Un même français a UNE traduction dans tout le dictionnaire, sinon
   `contexte=True` quand le sens diffère vraiment.
7. Ne toucher QUE son fichier de saisie.
