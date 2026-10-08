# Photolab parité L5 (t155) — peinture et retouche

> Relevé : `specs/2026-10-08-photolab-bientot-inventaire.md` (§5, lot L5). Skill `parite-photolab`.
> Base : origin/main 4dcae97f, branche `chantier/photolab-parite-l5`. Décision D1 tenue : chaque geste validé = UNE
> commande `paint.*` du moteur ; l'écran ne dessine qu'un APERÇU (contour SVG) pendant le geste.

## Faits établis (08/10/2026)

**Vrai moteur** (photocraft-cli 0.3.0 installé, sonde `scratchpad/sonde/sonde.py`) :
- Les 18 commandes répondent sur un document 64 × 64 et renvoient `{damage}`. L'historique les nomme en anglais :
  « Brush Tool », « Pencil », « Mixer Brush », « Clone Stamp », « Healing Brush », « Spot Healing Brush »,
  « History Brush », « Background Eraser », « Magic Eraser », « Paint Bucket », « Gradient », « Dodge Tool »,
  « Burn Tool », « Sponge Tool », « Blur Tool », « Sharpen Tool », « Smudge Tool ».
- Tampon et correcteur : il faut `source`, `offset`, ou une source posée par `cloneSource.set {source}`, faute de quoi
  le moteur refuse. Après un `cloneSource.set`, le décalage est appairé au trait suivant puis conservé (`aligned`).
- `brush.get` renvoie la pointe complète (taille 13 par défaut, dureté 0..1, espacement 0..10, angle, rondeur,
  flipX/Y, pressureSize vrai). `tools.setBrush {preset}` applique un préréglage (24 préréglages intégrés).
- `tool.presets.list` : 5 préréglages intégrés {name, tool}. `gradient.presets.list` : groupes + `current`.
- Unités : `paint.stroke` (pinceau, gomme) prend opacité, flux et dureté en 0..1 ; les outils de retouche prennent
  dureté, opacité et flux en 0..100.
- Pas de commande pour l'outil Pièce : il reste « bientôt » (Bloqué moteur).

**Pont** : la liste blanche admet les 18 commandes avec les paramètres prévus. `tools.setBrush` n'admet que `preset`
et `reset`, car le registre résume ses champs en « …BrushSettings fields ». Il faut donc une liste explicite des champs
de la pointe (tâche A1).

**Référence** (Photoshop 2026, lecture seule, Loupe, 08/10) — barres d'options :
- Pinceau : préréglage │ forme (taille) │ Paramètres │ Mode │ Opacité + pression │ Flux + aérographe │ Lissage +
  options │ angle │ pression pour la taille │ symétrie.
- Gomme : Mode Pinceau / Crayon / Carré │ Opacité │ Flux │ Lissage │ Effacer d'après l'historique.
- Gomme d'arrière-plan : échantillonnage ×3 │ Limites │ Tolérance % │ Protéger la couleur de premier plan.
- Gomme magique : Tolérance │ Lissage │ Contigu │ Échantillonner tous les calques │ Opacité.
- Tampon : Mode │ Opacité │ Flux │ Aligné │ Échantillon (calque actif / actif et inférieurs / tous).
- Correcteur localisé : Mode │ Type (Contenu pris en compte / Créer une texture / Similarité des couleurs).
- Densité : Gamme │ Exposition │ Protéger les tons. Éponge : Mode │ Flux │ Vibrance.
- Dégradé : 5 styles │ Inverser │ Tramage. Pot : Premier plan / Motif │ Mode │ Opacité │ Tolérance │ Lissage │
  Contigus │ Tous les calques.
- Les lettres B, E, S, J, O, G, Y, avec Maj pour passer d'un outil à l'autre du groupe.
- Flou, Netteté et Doigt ne figurent pas dans la barre de l'espace actif : relevés depuis l'amont
  (inventaire B §2.3).

## Décisions (écarts assumés)

| Chez eux | Chez nous | Pourquoi |
|---|---|---|
| Puce de forme (menu flottant Taille / Dureté) | Taille et Dureté directement dans la barre (variante « Studio » de photocraft) | pas de menu flottant de plus |
| Gomme en mode Carré | Pinceau ou Crayon seulement | aucune commande carrée dans le moteur |
| Pot : Mode, Tous les calques | absents | `paint.bucket` n'a pas ces clés |
| Pot : Motif | plus tard (L3 Motifs) | |
| Correcteur localisé : Mode, Échantillonner tous les calques | absents | `paint.spotHealing` n'a pas ces clés |
| Symétrie, aérographe, angle dans la barre | absents de la barre ; l'angle est dans Paramètres de pinceau | |
| Paramètres de pinceau : 14 sections | la section « Forme de la pointe » seulement (taille, dureté, espacement, angle, rondeur, retourner X / Y) | le reste dans un lot ultérieur |
| Pièce | reste « bientôt » | absente du moteur |

## Tâches

**A — pont (backend)**
- A1 `photolab_registre.verifier` : `CHAMPS_POINTE` pour `tools.setBrush` (size 1..5000, hardness 0..1,
  spacing 0.01..10, spacingEnabled, angle −180..180, roundness 0.01..1, flipX, flipY, opacity 0..1, flow 0..1).
  Ajoutés avec `setdefault`, comme les gammes de la Correction sélective.
- A2 banc `tests/test_photolab_peinture.py` :
  - [1] liste blanche : les 18 commandes et les paramètres de l'écran passent ; refus attendus pour une clé
    inconnue, `size` hors bornes de la pointe, un `preset` vide trop long, `points` au-delà de 100 000 valeurs ;
  - [2] VRAI moteur : chaque commande change le rendu (empreinte) et ajoute exactement l'état d'historique attendu ;
    tampon sans source refusé, accepté après `cloneSource.set` ;
  - [3] chaque nom d'historique a sa clé `photolab.histo.*` dans `mod-historique.js` et dans le dictionnaire.

**B — module pur `js/mod-peinture.js`** (QA `qa/peinture.test.mjs`)
- B1 `OUTILS_PEINTURE`, l'outil → la commande et la conversion d'unités ; `commandeTrait(outil, points, options,
  couleurs)` ; `commandeClic` (pot, gomme magique) ; `commandeDegrade(de, a, options, maj)`, avec Maj qui cale par 45°.
- B2 gestes : `contraindreTrait` (Maj : 0, 45 ou 90°, verrouillé après 3 points), `ligneDepuis` (Maj-clic depuis la
  fin du trait précédent), `pointAvecPression` (stylet : pression ; souris : sans).
- B3 clavier : `tailleCran` ([ et ] ÷/× 1,25, bornée 1..5000), `dureteCran` (Maj+[ et ] ±25 %),
  `accumulateurChiffres` (1→10 %, 0→100 %, deux chiffres en moins de 800 ms = valeur exacte ; Maj = flux).
- B4 options : défauts et bornes par outil ; types `nombre`, `case`, `choix`, `liste`.

**C — écran**
- C1 `mod-outils.js` : les 18 outils passent `p2: true` ; Pièce reste « bientôt » ; `OPTIONS` lues depuis
  mod-peinture ; nouveau type d'option `liste` (sélecteur, pour le mode de fusion).
- C2 `mod-peinture.js` côté DOM : gestes (`PL.gestes.<outil>`), aperçu `trait` / `ligne` / `pointe` (cercle de la taille
  au survol), Alt = pipette (pinceau, crayon, dégradé, pot), Alt-clic = source (tampon, correcteur), touches [ ] Maj
  chiffres, synchronisation de la pointe (`brush.get` au premier document).
- C3 `mod-gestes.js` : les nouveaux aperçus.
- C4 panneau « Pinceaux » (groupe `#grpPinceaux`, onglets Pinceaux │ Paramètres de pinceau │ Source de duplication │
  Outils prédéfinis), bouton de rail `brush` ; `window.panel.{brushes, brushSettings, cloneSource, toolPresets}`
  ajoutés à `TRAITES_PAR_ECRAN` + `PL.actions` ; F5 = Paramètres de pinceau (catalogue).
- C5 historique : 17 noms traduits (`photolab.histo.*`).
- C6 dictionnaire `photolab.json` (fr / en) : options, panneau, messages (« Alt-clic pour définir la source »).

**D — preuve et finitions**
- D1 bancs figés à mettre à jour : outils.test 1.5 (11 → 29 actifs), 2.11 (B), 2.16 (W inchangé) ; menus (comptes
  « bientôt ») ; textes (clés).
- D2 mutations (sources copiées avant, `cmp` après) : conversion d'unités, contrainte 45°, accumulateur de chiffres,
  garde de source du tampon, A1.
- D3 preuve sur 8799 : peindre un trait, gommer, tamponner après Alt-clic, densité, dégradé, pot ; vérifier
  l'historique et les pixels (document.pixel) ; lire le DOM.
- D4 fiches didactiques : Pinceau, Tampon de duplication.
- D5 recompter avec `lister_bientot.mjs` : 237 entrées de menu → 233 ; 34 outils → 16 ; total des « bientôt »
  284 → 262 (Pièce reste).

## Relevé d'exécution (08/10/2026)

**Bancs.**
- `test_photolab_peinture` : 104/104.
- QA node : 25 séries vertes, dont les nouvelles `peinture` (66), `pinceaux` (24) et `options-peinture` (12, la vraie
  barre d'options sous le faux DOM). Épingles mises à jour : outils 1.5 / 2.11 / 3.2, panneaux 11.3, zones 2.3 / 2.4.
- Bancs backend Photolab et `test_i18n_l0` : verts, sauf 7 rouges d'environnement (`apropos` 3, `installeur` 2,
  `reglages_moteur` 2). Ces mêmes rouges apparaissent à l'identique sur une copie propre de `origin/main` : moteur
  et licences absents du worktree, fixture en CRLF.

**Mutations** : 12 sur 12 tuées, sources restaurées et vérifiées par `cmp`.
- M1 dureté du pinceau en 0..100, M2 Maj sans calage, M3 fenêtre des chiffres, M4 source du tampon,
  M5 Gomme d'après l'historique, M6 clic hors du document, M7 pointe sur une liste fixe d'outils, M8 F5 non traité
  par l'écran, M9 nom d'historique non traduit, M10 et M11 liste blanche de la pointe, M12 liste de la barre d'options.
- La M12 survivait aux bancs purs : d'où le banc `options-peinture`.

**Preuve sur 8799** (vrai moteur, gestes par `PointerEvent` sur `#toile`, touches par `KeyboardEvent`) :
- B, puis ] ] : taille 13 → 20 ; l'aperçu fait 20 px × zoom.
- Trait rouge : pixel (300, 50) = #ff0000 ; historique « Pinceau ».
- Tampon : sans source, « Alt-clic sur l'image pour définir la source. » ; Alt-clic sur le soleil → « Source définie. »,
  puis le jaune est recopié sur l'herbe.
- Densité + : (240, 200, 60) → (226, 188, 57). Dégradé avec Maj : calé à 0°. Pot : bleu. Gomme et Correcteur de tache :
  passent par le moteur. Historique traduit à chaque geste.
- Chiffres : 4 puis 5 → opacité 45 % ; Maj+7 → flux 70 % ; Maj+[ → dureté 75. Alt-clic du pinceau = pipette, sans
  état d'historique.
- Panneau : le préréglage « Soft Round » donne taille 45 et dureté 0 ; angle 30° écrit dans le moteur ; source lue
  (320, 190) ; le préréglage d'outil « Soft Eraser 60 px » fait passer à la Gomme en 60 px. F5 ouvre « Paramètres de
  pinceau ».
- Défaut trouvé à l'écran et corrigé : un préréglage de gomme changeait aussi la taille du Pinceau (`cibleSynchro`).
- Écran en anglais vérifié (options, onglets, rail, infobulles), puis retour au français.
- Recomptage `lister_bientot.mjs` : 233 entrées de menu + 16 outils + 11 onglets + 2 boutons = 262 (284 avant).
- Fiches « Pinceau (B) » et « Tampon de duplication (S) » : trois temps capturés dans la page ; l'encart s'ouvre au
  `pointermove` (animation de 320 px, phrase présente).
