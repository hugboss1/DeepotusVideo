# Vectorlab classe Affinity — LOT B : géométrie et gestes de classe Affinity — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module pur).

> Conception validée : `docs/superpowers/specs/2026-09-17-vectorlab-affinity-design.md`
> (§4 lot B ; §2.1–2.4 et 2.10 pour le détail fonction par fonction ; D2
> objet `forme` paramétrique avec `params` et `d` recalculé ; D9 modules
> purs). Branche `chantier/vectorlab-affinity`, après le lot H (`6209c4c`).
> Ce plan est COMMIS avant le code.

> **RELEVÉ DE LIVRAISON** : à écrire ici en fin de lot.

**Goal :** donner au Vectorlab les gestes vectoriels d'Affinity Designer :
formes paramétriques à poignées, crayon lissé, couteau, gomme vectorielle,
outil Coin et Contour (décalage), nœuds multiples (lasso, aligner,
transformer, diviser, joindre, inverser), inclinaison, pivot déplaçable,
formules dans le panneau, duplication puissance, sélection par attribut,
Shape Builder sur les booléens existants, historique 1 000 pas et
instantanés nommés.

**Architecture :** trois modules purs nouveaux — `mod-formes.js` FEUILLE
(les sept formes → `d`, défauts, validation des paramètres, poignées),
`mod-crayon.js` FEUILLE (simplification Ramer–Douglas–Peucker, lissage
Catmull-Rom → Bézier cubiques, fermeture auto), `mod-noeuds.js` (les
commandes de nœuds multiples, coins arrondis, diviser, joindre, inverser —
sur `chemin_parser/serialiser` de mod-doc) ; `mod-bool.js` gagne le
couteau, la gomme, le contour (décalage) et les atomes du Shape Builder
(martinez) ; `mod-doc.js` gagne l'objet `forme` (compilé par
`mod-formes`), `op_incliner`, `op_dupliquer_puissance`,
`selection_par_attribut`, `formule`, un `Historique` à 1 000 pas avec
instantanés nommés ; l'UI `mod-outils2.js` porte les nouveaux outils
(formes avec poignées de paramètres, crayon, couteau, gomme, coin,
constructeur) et `mod-style.js` les rangées nouvelles (inclinaison, pivot,
formules, puissance, attribut, contour, nœuds, instantanés).

**Décisions d'implémentation (dites au relevé) :**
- `forme` = `{type:"forme", forme, cx, cy, r, params, sx?, sy?, rotation?}` :
  `d` recalculé à la compilation (jamais stocké) ; le redimensionnement pose
  `sx/sy` ; « convertir en courbes » (`op_forme_en_chemin`) fige le `d`.
  L'hexagone est le polygone à 6 côtés (une entrée du menu, pas une forme).
- Le contour (décalage) est DESTRUCTIF ici : il crée un chemin décalé (copie)
  — l'offset vivant non destructif est hors périmètre (dit au spec §2.3).
- Le couteau coupe par une DROITE (le trait tiré) ; la gomme retire le
  contour gonflé du trait ; les deux passent par martinez, les résultats
  sont des chemins.
- Shape Builder : les atomes (régions élémentaires) des formes sélectionnées
  se calculent par martinez ; on les cumule au clic, Entrée fusionne (ou
  Alt+Entrée retire) ; le résultat remplace les formes.
- Les instantanés nommés vivent dans la session (`etat.instantanes`) et se
  proposent à la restauration ; ils ne s'écrivent pas dans le document.
- Le pivot de rotation est un point de `etat` (déplaçable par sa poignée),
  remis au centre à chaque nouvelle sélection.

## Tasks

1. **`mod-formes.js`** (banc `formes.test.mjs`) — `FORMES`, `forme_defaut(nom, cx, cy, r)`,
   `forme_params_valider(nom, params)`, `forme_d(o)` (polygone n, étoile n/ratio,
   engrenage dents/profondeur, flèche longueur/largeur/tête, donut ratio
   (evenodd), spirale tours/type lineaire|fibonacci ouverte), `forme_poignees(o)`
   (→ [{cle, x, y}]), `forme_poignee_deplacer(o, cle, x, y)` (→ patch).
2. **`mod-crayon.js`** (banc `crayon.test.mjs`) — `simplifier(points, tol)` (RDP),
   `lisser_vers_d(points, {tol, fermer, tension})` (Catmull-Rom → C, fermeture si
   fin ≈ début), `est_ferme(points, seuil)`.
3. **`mod-noeuds.js`** (banc `noeuds2.test.mjs`) — `op_noeuds_deplacer(doc,id,indices,dx,dy)`,
   `op_noeuds_aligner(doc,id,indices,mode)`, `op_noeuds_transformer(doc,id,indices,bbAvant,bbApres)`,
   `op_noeud_inserer(doc,id,iSegment,t=0.5)`, `op_chemin_inverser(doc,id)`,
   `op_chemins_joindre(doc,idA,idB)`, `op_coins_arrondir(doc,ids,rayon)`,
   `ancres_dans_rect(segs, rect)`.
4. **`mod-bool.js`** (banc `opsbool2.test.mjs`) — `aplatir` de `forme` ;
   `op_couteau(doc, ids, ligne)`, `op_gomme(doc, ids, d_trait, largeur)`,
   `op_contour(doc, ids, decalage)`, `atomes(multis)`, `point_dans_multi(mp, x, y)`,
   `op_constructeur(doc, ids, atomesChoisis, mode)`.
5. **`mod-doc.js`** (banc `gestes.test.mjs`) — `forme` (validation, compile,
   déplacer/mapper/miroir), `op_forme_param`, `op_forme_en_chemin`,
   `op_incliner(doc, ids, kx, ky, cx, cy)`, `op_dupliquer_puissance(doc, ids, n, pas)`,
   `selection_par_attribut(doc, refId, cle)`, `formule(valeur, texte)`,
   `Historique(1000)` + `instantane(nom, doc)`, `instantanes()`, `restaurer(nom)`.
6. **UI** `mod-outils2.js` + `mod-style.js` + `core.js` + `index.html` + CSS ;
   banc pur `outils2_ui.test.mjs` (libellés des formes, lecture des formules).
7. Miroirs pytest (`test_vector_docs.py`), preuve en réel, déploiement
   (statiques seuls → pas de relance), relevé.
