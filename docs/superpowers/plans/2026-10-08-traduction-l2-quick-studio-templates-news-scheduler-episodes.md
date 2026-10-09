# Traduction L2 — Quick, Studio, Templates, News, Scheduler, Épisodes (t142)

Skill `traduction-deepotus`. Base FR (langue de référence), EN par le dictionnaire ; `dzT(clé, vars)` global (chargé
avant le bundle), langue fixée au chargement (`dzSetLang` recharge). Suite de L1 (t141, PR #272).

## Périmètre mesuré (08/10/2026, main 419caf63)

Vues routées par la coque (`s==="quick"` → `um`, `"studio"` → `Lh`, `"templates"` → `fm`, `"news"` → `pm`,
`"scheduler"` → `Lm`, `"episodes"` → `DzChapitres`), leur fermeture, et les composants de la couche qu'elles
appellent, en douze groupes de saisie (`scripts/i18n_l2_perimetre.py`, `GROUPES`) :

| Cible | Groupes |
|---|---|
| bundle | quick, studio_a (graphe, palette, inspecteur, rendu, composition), studio_b (panneaux de nœuds), studio_c (catalogue des nœuds `Me`, catégories `Qr`, carte `Th`), templates, news, scheduler, episodes |
| couche `frontend/patches/montage.js` | studio_couche (recette, import de graphe, duel, épingles, fournisseur de voix, curseur), templates_couche (réagencement, masque, échantillon, animation, composants, export, Figma, éditeur de texte, vignette), templates_tables (styles de texte, types et courbes d'animation) |

Exclus : composants du Montage (L3), du Son & VFX (L4), sous-titres et dialogues (L5), l'Atelier Chapitre
(`/atelier`, L8), ceux de L1 (dont `zm`, la page News des Réglages) et `shared/dz-champ-ia.js` (champ IA partagé par
tous les écrans, reste connu de L1). Balayage lexical : ~2 000 littéraux candidats, bruit compris ; 1 302
substitutions dans le bundle, 249 dans la couche, 1 465 clés, 406 littéraux gardés et motivés.

## Mécanisme

Celui de L1, à deux cibles : saisie positionnelle `scripts/i18n_l2/<groupe>.py` (L / S / X, plus `FRAGMENTS` pour
un morceau de gabarit gardé, `CIBLE = "couche"` pour la couche), générateur `scripts/i18n_l2_generer.py`
(positions dans le bundle et la couche de BASE 419caf63, ancres minimales uniques dans la base ET dans la base dont la
couche est rafraîchie, remplacement unique après application), table `scripts/i18n_l2_paires.json` (paires du
bundle + substitutions de la couche), maillon de queue `scripts/patch_bundle_i18n_l2.py` APRÈS `i18n_l1` (sonde son
marqueur), `.bak` supprimé, `version` reste le dernier maillon. Dictionnaires
`frontend/shared/i18n/{quick,studio,templates,news,scheduler,episodes}.json` assemblés par `scripts/i18n_assembler.py`.

Ordre de reconstruction : bundle de base → `i18n_l2_generer.py` → `i18n_assembler.py` → `restaurer_bak_montage.py` →
`refresh_layer.py --layer montage` → `patch_bundle_i18n_l2.py`.

La couche L2 se pose PAR-DESSUS la couche L1 : `i18n_l1_generer.py --check` attend la couche L1 + les
substitutions L2 (`i18n_l2_generer.appliquer_couche`), et `test_i18n_l1` rejoue L1 depuis la couche L1 reconstruite
(`couche_avant_i18n_l2`).

`--seul G --restes` valide un groupe et liste ce qui reste en dur dans ses composants.

Rien d'envoyé au serveur ni de stocké n'est traduit : types de nœuds du Studio comparés (`type==="Render"`), prompts
par défaut, noms par défaut d'un layout ou d'une recette créés, `voice_name` enregistré (« Voix par défaut de
l'app »), posts d'exemple, contenu de démonstration des régions. Les titres du catalogue des nœuds sont traduits
(« Composition spatiale », « Enchaînement », « Rendu »…) et les messages du Studio qui les citent suivent.

## Bancs

- `test_i18n_l2.py` : générateur à jour ; maillon (octets, rejeu sur la base + couche rafraîchie, double application
  refusée, refus sans L1 en amont, aucun .bak) ; la traduction se défait exactement (`avant_i18n_l2`, et
  `avant_i18n` défait L2 puis L1) ; couche du générateur, couche L1 reconstruite sans git ; chaque `dzT` du lot
  résolu, fr/en non vides, mêmes variables, variables fournies par l'appel ; runtime sous node ; AUCUN texte visible
  restant dans le périmètre ; compteurs figés (`x.useState(` 731, `DzTracks` 181) ; `node --check`.
- `backend/tests/_i18n_l1_aide.py` : `avant_i18n` et `couche_avant_i18n` défont L2 avant L1 (bancs amont « x1 »).
- Bancs existants qui lisent un texte du périmètre : mis à jour (clé + valeur du dictionnaire).
- Mutations ; balayage ; preuve FR et EN sur le serveur de preuve (Quick, Studio, Templates, News, Scheduler,
  Épisodes).
