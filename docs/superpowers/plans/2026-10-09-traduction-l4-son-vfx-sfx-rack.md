# Traduction L4 (t144) — Son & VFX, SFX, rack VFX : consigne de saisie

Skill `traduction-deepotus`. Lot : les TROIS couches entières `frontend/patches/sfxstudio.js`,
`frontend/patches/vfxrack.js` et `frontend/patches/son-vfx-montage.js` (écran Son & VFX `DzSonVfx` + écran Montage
`DzMontage` de la même couche). La couche `frontend/patches/montage.js` et le patcher Montage restent à L3 (t143).

## Mécanisme

- Pas de maillon de bundle : les couches sont des sources complètes réinjectées par
  `scripts/refresh_layer.py --layer sfxstudio|vfxrack|sonvfx`.
- Saisie : un fichier par groupe, `scripts/i18n_l4/<groupe>.py`, format de L2 (`scripts/i18n_l4/outils.py` :
  `L`, `S`, `X`, `FRAGMENTS`), avec `CIBLE = "sfxstudio" | "vfxrack" | "sonvfx"`. Positions = couche de BASE
  `ecf945e4` (CRLF), plage de lignes du groupe dans `scripts/i18n_l4_perimetre.py` (`GROUPES`).
- Générateur `scripts/i18n_l4_generer.py` → les trois couches, `scripts/i18n_l4_paires.json` (table réversible,
  couche par couche) et `frontend/shared/i18n/{son,sfx,vfx,montage_svm}.json` ; puis `i18n_assembler.py` et
  `refresh_layer.py` ×3.
- Groupe seul : `python scripts/i18n_l4_generer.py --seul <g> --restes` (n'écrit rien ; contrôle les textes, les
  clés, l'unicité FR→EN contre tous les dictionnaires, la plage, `node --check` de la couche, et liste les restes).

## Groupes et zones de clés

| groupe | couche | lignes (base) | zone |
|---|---|---|---|
| sfx_a | sfxstudio | 1–851 | `sfx.` |
| sfx_b | sfxstudio | 852–fin | `sfx.` |
| vfx | vfxrack | tout | `vfx.` |
| son_a | sonvfx | 1–563 | `son.` |
| son_b | sonvfx | 564–1569 | `son.` |
| montage_a | sonvfx | 1570–4231 | `montage.` |
| montage_b | sonvfx | 4232–5180 | `montage.` |
| montage_c | sonvfx | 5181–5874 | `montage.` |
| montage_d | sonvfx | 5875–fin | `montage.` |

## Règles de saisie

1. Chaque littéral que `--restes` signale devient `L` (littéral entier → `dzT("clé")`), `S` (expression composée →
   `dzT("clé",{n:expr})`) ou `X` (gardé, raison dite). Objectif : `restes : 0`, `node --check : OK`.
2. Clé `<zone>.<objet>.<rôle>` en français ASCII minuscule (`_` permis), objet = l'élément d'écran
   (`montage.export.titre`). Un mot courant réutilisé : `<zone>.commun.<slug du français>` (`montage.commun.fermer`
   = « Fermer »), pour que deux groupes de la même zone tombent sur la même entrée.
3. `fr` = le texte du littéral, à l'identique (ponctuation, espaces, insécables) ; s'il contient un échappement
   (`\'`, `\n`, ` `), le texte DÉCODÉ. `en` = anglais d'interface, court, impératif pour un bouton ; termes
   métier gardés (Render, Studio, Library, LUT, Seedance, ElevenLabs, LUFS, EDL). Variables `{x}` identiques.
4. Composés : `"Piste "+n` → `S(pos, '"Piste "+n', 'dzT("montage.piste.nom",{n:n})', {...: ("Piste {n}", "Track {n}")})`.
   Le code `avant` est EXACT (commence à `pos`) et englobe tous les morceaux de la phrase ; les expressions gardent
   leur sens (mêmes appels, même ordre d'évaluation). Pluriel : deux clés `.un` / `.plusieurs`. Un gabarit
   `` `…${x}…` `` se remplace entier par `S`. Un morceau de gabarit purement technique va dans `FRAGMENTS`.
5. JAMAIS traduire une valeur envoyée au serveur, stockée (localStorage, projet), comparée (`===`, `indexOf`, clés
   d'objet, `switch`), un id, un nom de préréglage enregistré, une expression ffmpeg/CSS, une police, un raccourci
   que le code ANALYSE (`svmComboCanon`, `SVM_COMBO_WORDS`…) : `X` avec la raison. Lire le code autour pour décider.
   Si un même littéral sert à l'affichage ET comme valeur, ne traduire que l'affichage (S sur le site d'affichage)
   ou garder (X) en le disant.
6. Unités : identiques des deux côtés (« dB », « Hz », « s ») → `X` « identique dans les deux langues » ; différentes
   (« Mo » → « MB », « Ko » → « KB ») → `L`.
7. Un même français a UNE traduction dans tout le dictionnaire ; sinon `contexte=True` (réservée à dzT, ignorée par
   la surcouche) quand le sens diffère vraiment.
8. Messages d'erreur montés à l'écran (`throw new Error("…")` affiché, toasts, `title`) : traduits.
9. Ne toucher QUE son fichier de saisie : ni les couches, ni le générateur, ni le périmètre, ni les autres saisies.

## Volet serveur (décision de l'utilisateur, 09/10)

Le rack VFX et le Montage affichent des listes SERVIES par le backend : catalogue d'effets (noms, aides, catégories,
libellés de paramètres), transitions xfade, préréglages de livraison, gabarits de titre. Les tables sources restent
en français ; `backend/app/i18n/catalogues.py` traduit une COPIE de la réponse quand la requête demande l'anglais
(`Accept-Language`, envoyé par le runtime), via `messages.json`. Clés générées par `scripts/i18n_l4_serveur.py`
(python embarqué ; fr lu dans les tables, en écrit dans le script). Routes : `/api/effects/catalog`,
`/api/montage/effects`, `/api/montage/transitions`, `/api/montage/titles`, `/api/montage/deliver-presets`
(paramètre `request` optionnel : deux bancs appellent ces fonctions directement). Banc `test_i18n_l4_serveur.py`.

## Affichage des raccourcis

Les noms de section (`SVM_KEY_SECTIONS`) et les combinaisons (`Maj+Z`, `Échap`…) sont des VALEURS comparées et
analysées : gardées en français dans les données, traduites à l'affichage (puces du panneau, `svmKeyLabel`, qui ne
sert plus qu'à afficher ; `dzFire` lit la combinaison brute).

## Ensuite (hors saisie)

Générateur complet, assembleur, refresh_layer ×3 ; aide des bancs `couche_avant_i18n_l4` / `avant_i18n_l4`
(`backend/tests/_i18n_l1_aide.py`) pour les 16 bancs qui lisent ces couches ; banc `test_i18n_l4.py` ; balayage ;
mutations ; preuve FR/EN sur 8799.
