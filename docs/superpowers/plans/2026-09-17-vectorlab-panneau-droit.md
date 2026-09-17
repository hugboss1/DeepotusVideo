# Vectorlab — panneau de droite qui ne déborde plus du canevas — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).

> Demande du 17/09/2026 (capture d'écran) : le panneau de droite empile
> une vingtaine de sections depuis les lots B→G et impose sa hauteur à la
> rangée, le document déborde sous le canevas au lieu de défiler. Trois
> niveaux validés par l'utilisateur (« pose les trois niveaux »).

> **RELEVÉ DE LIVRAISON** : à écrire ici en fin de lot.

**Goal :** le canevas garde la hauteur de la fenêtre ; le panneau défile
seul ; ses sections se replient et se souviennent ; les calques restent
toujours sous la main.

**Architecture :** niveau 1 = trois règles CSS (`.panneau` min-height 0 +
overflow, `body` overflow hidden) ; niveau 2 = toutes les sections en
`<details>` (ids conservés) + `mod-panneaux.js` FEUILLE pur (état
ouvert/replié par id ↔ JSON de localStorage, défauts) branché dans le cœur ;
niveau 3 = le panneau devient deux zones : `.panneau-defile` (réglages,
flex 1, défile) et `.panneau-calques` (tête + liste, hauteur bornée à 40 %,
défile seule) ; largeur 210 → 240 px.

**Décisions :** l'état des sections est global à l'utilisateur (clé
`dz_vl_panneaux`), pas au document ; les sections dynamiques (Image) se
cachent par leur `<details>` ; les pins pytest des ids restent vrais.

## Tasks
1. `mod-panneaux.js` (banc `panneaux.test.mjs`) — `PANNEAUX_DEFAUT`, `etat_lire(json)`, `etat_poser(etat, id, ouvert)`, `etat_serialiser(etat)`, `appliquer(etat, details[])` (pur sur des objets `{id, open}`).
2. CSS niveaux 1 et 3, `index.html` (details partout, deux zones), `mod-image.js` (cache le details), `core.js` (init).
3. Preuve en réel (hauteur de rangée = fenêtre, panneau qui défile, calques visibles, état relu après rechargement), déploiement statiques, relevé.
