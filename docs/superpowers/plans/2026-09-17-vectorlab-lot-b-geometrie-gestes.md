# Vectorlab classe Affinity — LOT B : géométrie et gestes de classe Affinity — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module pur).

> Conception validée : `docs/superpowers/specs/2026-09-17-vectorlab-affinity-design.md`
> (§4 lot B ; §2.1–2.4 et 2.10 pour le détail fonction par fonction ; D2
> objet `forme` paramétrique avec `params` et `d` recalculé ; D9 modules
> purs). Branche `chantier/vectorlab-affinity`, après le lot H (`6209c4c`).
> Ce plan est COMMIS avant le code.

> **RELEVÉ DE LIVRAISON (17/09/2026) : LOT B LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ (statiques seuls : aucune relance).**
>
> **Livré** (11 commits `d22f39d`→`0738aa4`, poussés) : `mod-formes.js` feuille
> (polygone/hexagone, étoile, engrenage, flèche, donut, spirale linéaire ou
> Fibonacci ; `d` recalculé ; poignées rayon/ratio/profondeur/tête) ;
> `mod-crayon.js` feuille (RDP, Catmull-Rom → C, fermeture auto) ;
> `mod-noeuds.js` (déplacer/aligner/transformer plusieurs ancres, diviser de
> Casteljau, inverser, joindre, coins arrondis Q — rect et forme convertis
> d'abord —, ancres au rectangle) ; `mod-bool.js` lot B (formes aplaties,
> couteau par droite, gomme par trait gonflé, contour ± — dehors =
> complément du retrait du complément —, atomes du Shape Builder,
> constructeur fusionner/retirer) ; modèle : objet `forme` (sx/sy au
> redimensionnement), `op_forme_param`, `op_forme_en_chemin`, `op_incliner`,
> `op_dupliquer_puissance`, `selection_par_attribut`, `formule`,
> `Historique(1000)` + instantanés nommés ; UI `mod-outils2.js` (six outils
> F/B/X/W/C/S, poignées de forme, pivot déplaçable, lasso d'ancres, panneaux
> Forme / Nœuds / Instantanés) ; panneau Apparence : X/Y/L/H à formules,
> inclinaison, puissance, attribut, contour ; crochet `VL.surOverlay` du cœur.
>
> **TDD tenu** : RED ×5. Bancs : node **728 contrôles** (+100 : formes 25,
> crayon 10, noeuds2 22, opsbool2 17, gestes 26), pytest `test_vector_docs`
> **29 passed** (+1). Trois défauts de géométrie attrapés au BANC : les
> unions successives martinez perdent des morceaux (11 247 / 11 846 / 11 616
> pour 12 078) → dehors = complément du retrait, différences progressives ;
> une tangente qui coïncide EXACTEMENT avec un bord égare martinez (483 mm²
> perdus aux coins) → disque +1 % (aussi dans mod-solide) ; anneaux dégénérés
> nettoyés. Trois défauts attrapés par la PREUVE : ids en double après
> couteau/gomme (deux « o3 » — insertion progressive), « 0 coin » sur un rect
> (converti d'abord), poignées de forme invisibles (le cœur appelle sa
> `rendreOverlay` locale → crochet `surOverlay`) et Entrée du constructeur
> muette (mod-tools écrasait `surTouche`/`surOutil` : `initOutils2` passe
> après lui).
>
> **Prouvé en réel** (8799, données isolées, viewport 1400×900) : étoile
> tracée au rayon par drag → r 80, 2 poignées + pivot au DOM ; poignée du
> rayon tirée → **r = 50** exact ; panneau n=7 appliqué ; crayon 25 points
> → chemin **20 C fermé** ; couteau sur un rect → **2 morceaux aux ids
> distincts** ; gomme 20 px → 2 pièces, l'original remplacé ; coin 15 sur un
> rect → **4 Q** ; constructeur : 2 clics → 2 marques d'overlay, Entrée →
> **un chemin de 10 000** (A∖B + A∩B), Alt+Entrée sur l'intersection →
> **15 000**, Échap vide ; lasso d'ancres → **2 ancres** jaunes, drag commun
> déplace les deux ; pivot tiré en (100,450) puis inclinaison →
> `translate(100 450) skewX(20) translate(-100 -450)` ; formules : L
> « +50% » **100→150**, X « *2 » **500→1000**, « abc » refusée en toast ;
> puissance 4 copies Δx 40 rot 10 → x 60/100/140/180, `rotate(40 …)` sur la
> 4e ; attribut « fond » → 7 objets bleus ; contour +8 → copie plus grande ;
> instantané « avant nettoyage » → vidage → restauration **12 objets**,
> historique cap 1 000 ; indices d'outils lus.
>
> **Déployé** : 8 fichiers = base lot H (`abb2de8`) → sauvegarde
> `_backup_predeploy_2026-09-17e-vectorlab-lotB` → copie depuis `git archive
> 0738aa4` → **86 fichiers = cible**, l'app installée sert `mod-outils2.js`
> en 200. **Aucun Python touché : aucune relance nécessaire.**
>
> **Reste** : contour destructif (copie, pas d'offset vivant) ; les
> instantanés vivent dans la session ; le crayon ne lit pas la pression ;
> Shape Builder par clics + Entrée (pas de glisser-fusionner) ; pas de banc
> UI dédié pour `mod-outils2` (les gestes sont prouvés au navigateur).

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
