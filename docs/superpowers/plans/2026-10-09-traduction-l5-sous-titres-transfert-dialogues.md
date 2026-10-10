# Traduction L5 (t145) — sous-titres, transfert, dialogues : consigne de saisie

## Périmètre
- **Bloc SUBS** du bundle (piste et tiroir de sous-titres du Montage). Il n'a plus de source : `frontend/patches/subs.js`
  est INTOUCHABLE (des patchers aval écrivent dans le bloc ; test_montage_bundle compte la divergence).
- **Couche TRANSFERT** : `frontend/patches/transfert.js`, la source complète du bloc, avec ses lignes de marqueurs.
- **Couche DIALOGUE** : `frontend/shared/dialogue.js` et ses deux copies octet pour octet (`frontend/patches/dialogue.js`,
  `frontend/dist/shared/dialogue.js`).

Bilan : 550 substitutions dans SUBS, 50 dans transfert, 3 dans dialogue, 631 clés (`subs.json`, `transfert.json`,
`dialogue.json`), 103 littéraux gardés, chacun avec sa raison.

## Mécanisme
- Saisie : `scripts/i18n_l5/*.py` (subs_a…subs_e, transfert, dialogue ; format de L2 : L, S, X). Les positions sont
  celles du commit BASE 2b155403, avec les fins de ligne du poste (CRLF).
- `scripts/i18n_l5_generer.py` écrit la table `scripts/i18n_l5_paires.json`, les deux sources et les dictionnaires.
  `--check` vérifie que tout est à jour ; `--seul G [--restes]` contrôle un seul groupe.
- SUBS passe par le maillon de queue `scripts/patch_bundle_i18n_l5.py` (ancres minimales uniques, réversibles :
  `_i18n_l1_aide.avant_i18n_l5`).
- TRANSFERT et DIALOGUE sont réinjectés par `scripts/refresh_layer.py --layer transfert|dialogue` (deux couches
  ajoutées par t145 ; `_coeur` lit ce qu'il y a entre les lignes de marqueurs).

## Ordre de la chaîne (après la fusion avec main, 10/10)
L1, L2, L4 → L3 (couche montage) → L5 (couches transfert et dialogue, puis maillon SUBS) → icônes G1.
- G1 est régénéré sur la base d4c6a2f4 (G0 + L3 + L5, sans G1). 13 ancres de `g1_saisie.py` visaient des textes du
  bloc SUBS que L5 traduit : elles visent maintenant les formes `dzT(...)`. Quand le glyphe « ▸ » demande une icône
  tournée, `__dzGlS` le retire du texte traduit.
- TRANSFERT est devenu une couche pour G1 : ses 3 éditions sont posées dans la source (`COUCHES`, positions de la
  source, `coeurs.transfert` pour un cœur de bloc), et non plus par le maillon. Avant, `transfert.js` en était le
  miroir. `i18n_l5_generer` pose G1 sur `transfert.js` (`appliquer_bloc_g1`).
- Bancs : `avant_dzglyph` défait G1 d'abord, transfert compris. test_i18n_l5 compare dans la vue d'avant G1, avec
  les couches rafraîchissables prises au poste (L3 et G1 sont posés après la BASE de L5).

## Règles
Celles de L3 et L4 : une clé par sens ; `contexte` quand un même français a deux traductions (`subs.spec.fin` « fin »
→ « thin », alors que `montage.mots.fin` → « end ») ; on ne traduit jamais une valeur stockée ou envoyée au serveur.
