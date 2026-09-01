# L'Établi — la plaque, la manipulation mesurée et l'extraction par élément

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.
> Un sous-agent frais par tâche, puis deux revues — conformité d'abord, qualité ensuite.

**Goal :** rendre la sélection *décente*. Aujourd'hui on coche des noms dans une liste
sans voir ce qu'on coche. Après : les pièces s'étalent sur une plaque, on les mesure,
on les déplace au clavier, on en extrait ce qu'on veut — ensemble ou une par une — et
la Bibliothèque les range sous leur génération mère.

**Demande de l'utilisateur, mot pour mot :** « pour pouvoir sélectionner décemment il
faut intégrer une étape intermédiaire de visualisation sur plaque pour voir les
différents éléments répartis sur la plaque », plus deux options de manipulation (le
gizmo actuel et une vue isométrique), une graduation visible, un repère 3D donnant la
position de chaque sélection par rapport à l'origine, le déplacement au clavier, et
l'extraction d'éléments enregistrables avant envoi au slicer.

---

## Ce que le terrain dit — mesuré le 01/09/2026

| Fait | Conséquence |
|---|---|
| `frontend/lib3d/viewer.js` n'a **ni grille, ni axes, ni caméra orthographique** (0 occurrence) | tout est à construire, dans le canevas **partagé** |
| `print3d` connaît le plateau : **Centauri Carbon 2, 256 mm**, et il **avertit sans interdire** (`print3d.py:338-344`) | la plaque a une taille vraie ; la vue peut dire « ça ne rentre pas » |
| Un GLB n'a **aucune échelle en mm** ; `mettre_a_l_echelle(tris, cible_mm)` étire la plus grande dimension | une règle en mm **ment** tant qu'aucune taille cible n'est déclarée |
| Aucun packing 2D n'existe dans le dépôt | l'étalement est à écrire, et à garder simple |
| `charger()` pose `api.gltf`, `selection.js` pose `userData.indexGltf` par `parser.associations` | les pièces sont déjà identifiées et adressables côté serveur |

## La règle qui domine ce plan

**La plaque est une VUE, jamais une mutation.** Étaler les pièces ne doit pas alimenter
`S.enAttente`. Sans cette garde, l'utilisateur étale, clique « écrire la version », et
son modèle est **éclaté définitivement** sur le disque. Un banc l'épingle en T1 — pas
une intention, une assertion.

Corollaire : quitter la plaque doit **rendre** le modèle assemblé, sans passer par un
rechargement (le verrou de sérialisation coûte un téléchargement).

---

## Task 1 — la plaque

**Files :** créer `frontend/lib3d/plaque.js` ; modifier `frontend/etabli/etabli.js`,
`etabli.css`, `index.html` ; banc.

- Bascule **Assemblé / Sur la plaque** dans l'en-tête.
- Étalement : boîte englobante par pièce (`Box3.setFromObject` sur chaque nœud indexé),
  rangement en étagères par ordre de surface décroissante, marge constante.
- Un **plateau** avec sa grille, dimensionné sur l'**empreinte de
  l'étalement**, en **unités du modèle**.
- **Une couleur par pièce** et une liste latérale avec **œil** (montrer/masquer),
  comme la capture de référence.
- **Rien n'entre dans `S.enAttente`.** Les positions d'étalement vivent hors du modèle
  (décalage appliqué à l'affichage), et le retour à « Assemblé » les annule sans
  recharger.

### Task 1 — LIVRÉE. Trois écarts au plan, tous mesurés

Consignés ici parce que **c'est ce document que les tâches 2 à 6 liront**.

1. **PAS DE 256 mm.** Le plan prescrivait « un plateau dessiné à l'échelle
   (256 mm par défaut) » — et le tableau « Ce que le terrain dit » du présent
   document dit lui-même qu'une règle en mm **ment** tant qu'aucune taille
   cible n'est déclarée. Les deux ne pouvaient pas tenir ensemble. Un GLB n'a
   aucune échelle : c'est `print3d.mettre_a_l_echelle(tris, cible_mm)` qui en
   fabrique une, à l'écriture d'un STL. Le plateau est donc en unités du
   modèle, et un banc **interdit** ` mm`, `cible_mm` et `256` dans le module
   comme dans l'interface. **La graduation en mm de la tâche 3 devra d'abord
   poser une taille cible** ; sans elle, elle n'a rien à afficher.

2. **Les pièces sont les nœuds indexés les plus BAS qui portent de la
   géométrie**, pas les plus hauts. `mesh_edit.reparer` **ajoute un nœud
   d'enveloppe à chaque réparation** : tout modèle passé par « Réparer
   l'assise » n'a qu'un seul nœud au sommet, et « le plus haut » n'y étale
   rien. Mesuré en navigateur, puis au banc.

3. **Le plan d'étalement se choisit sur les pièces**, il n'est pas le sol. Les
   douze pièces du modèle de l'utilisateur sont des **plans** (0,0630 × 0,0880
   × ~0) : leur empreinte au sol vaut largeur × zéro, et le rangement donnait
   douze étagères d'une pièce — douze plans coplanaires empilés le long de
   l'axe de vue. L'axe d'empilement est donc celui où les pièces n'ont pas
   d'étendue, avec hystérésis pour qu'un modèle quasi cubique garde le
   plancher. **La tâche 2 doit le savoir** : ses vues face / dessus / profil
   n'auront pas le même sens selon l'axe d'empilement retenu.

**Leçon de méthode, et elle vaut pour les tâches suivantes :** les deux
défauts vivaient dans du code qui ne tourne que dans un navigateur, où aucun
miroir de texte ne peut les voir. La décision d'étalement a été sortie dans
des fonctions **pures** (`piecesDe`, `axeEmpile`, `rangerEnEtageres`,
`disposer`, `versLocalLineaire`) que le banc **exécute** dans node sur les
cotes réelles du modèle. Toute décision géométrique des tâches 2 à 4 devrait
suivre le même partage.

## Task 2 — la vue isométrique

**Files :** `frontend/lib3d/viewer.js` ; banc.

Caméra **orthographique** commutable, plus des vues face / dessus / profil. Le cadrage
conscient de l'aspect (livré en P2+P3, seuil 0,813) doit continuer de valoir — une
caméra ortho se cadre autrement, **mesurer** avant d'écrire. Le gizmo reste ; ce qui
change est qu'on peut s'y fier.

## Task 3 — graduation, repère, lecture

**Files :** `frontend/lib3d/viewer.js`, `frontend/etabli/etabli.js` ; banc.

Grille graduée, axes à l'origine, et lecture numérique **x / y / z de la sélection par
rapport à l'origine**. Unités glTF, **et mm dès qu'une taille cible est posée** — jamais
de mm inventés.

## Task 4 — le clavier

**Files :** `frontend/etabli/etabli.js` ; banc.

Flèches pour déplacer la sélection au pas de la grille ; un modificateur pour un pas
fin, un autre pour ×10. Ne pas voler le clavier aux champs de saisie. Les déplacements
au clavier **sont** des transformations : ils alimentent `enAttente`, contrairement à
l'étalement.

## Task 5 — extraire, ensemble ou une par une

**Files :** `backend/app/api/routes.py`, `frontend/etabli/etabli.js` ; banc.

Choix au moment d'extraire. « Une par une » écrit **un fichier par élément**. Réutiliser
`mesh_edit.extraire` (qui **renumérote** — d'où `ORDRE_ECRITURE`), et ne pas casser
l'enchaînement des versions.

## Task 6 — la Bibliothèque hiérarchique

**Files :** `backend/app/api/routes.py`, `scripts/patch_bundle_*.py`, bundle ; banc.

Les éléments extraits se rangent en **sous-groupes sous leur génération mère** (ou sous
la version dont ils sortent). L'onglet « Établi » les affiche groupés plutôt qu'à plat.

---

## Pièges hérités, à ne pas redécouvrir

- `_code()` **ampute 45 %** d'un bundle minifié (des `/*` dans des littéraux) — jamais
  sur `frontend/dist`.
- Huit bancs de ce chantier étaient satisfaits par leur **propre prose** : toute
  assertion nouvelle se prouve par **mutation**.
- `Path("..").name` vaut `".."` — un nom se **refuse**, il ne s'aplatit pas.
- Comptes rigides du banc à préserver : `data-libelle="${esc(` 2, `ligneEcart(null` 2,
  `cadrer(S.vueA)` **4** (2 avant la tâche 1 : l'entrée et la sortie de la
  plaque re-cadrent, l'aspect changeant dans les deux sens — la paire d'origine
  est désormais gardée site par site), `add("erreur")` 3,
  `numero !== _demandeB` 4, `perimerEcart();` 2,
  `designerAuClic(` 1.
- `class="head-btn"` vaut **3** depuis la tâche 1 (la bascule « Assemblé / Sur
  la plaque »), et l'invariant est devenu auto-portant : le banc compare le
  nombre de `<button>` de l'en-tête à celui des porteurs de la classe.
- Le canevas est **partagé** (spec §12) : ce qui est général va dans `lib3d/`, ce qui
  est propre à l'Établi reste dans `etabli/`.
