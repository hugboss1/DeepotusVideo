# Vectorlab — panneau de droite qui ne déborde plus du canevas — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).

> Demande du 17/09/2026 (capture d'écran) : le panneau de droite empile
> une vingtaine de sections depuis les lots B→G et impose sa hauteur à la
> rangée, le document déborde sous le canevas au lieu de défiler. Trois
> niveaux validés par l'utilisateur (« pose les trois niveaux »).

> **RELEVÉ DE LIVRAISON (17/09/2026) : LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ (statiques seuls : aucune relance).**
>
> **Livré** (3 commits `113f67c`→`de96ac1`, poussés) : niveau 1 — `body`
> sans débordement, `.panneau` à `min-height: 0` ; niveau 2 — les dix-sept
> sections du panneau sont des `<details>` (ids des contenus conservés :
> `#panneauStyle`, `#panneauForme`, `#panneauImage`…), `mod-panneaux.js`
> feuille (défauts, lecture / écriture JSON, application aux `<details>`)
> branché dans le cœur sur la clé `dz_vl_panneaux`, chevron ▸ / ▾ ;
> niveau 3 — deux zones : `.panneau-defile` (réglages, défile seule) et
> `.panneau-calques` (tête + liste collées en bas, 40 % au plus, défilement
> propre) ; largeur 210 → 240 px. La section Image se cache par son
> `<details>` (mod-image).
>
> **TDD** : RED constaté (banc `panneaux.test.mjs`, 8 contrôles) ; node
> **992 contrôles**, pytest `test_vector_docs` **37 passed** (les pins des
> ids restent vrais).
>
> **Prouvé en réel** (8799, viewport **1400×700** pour forcer le
> débordement, lecture DOM) : toutes sections ouvertes → le document ne
> grandit pas (`scrollHeight` 700 = fenêtre, `body` `overflow: hidden`), le
> canevas et la rangée finissent à **700** ; le panneau fait **240 px**, sa
> zone de réglages déborde (2 441 px pour 539 visibles) et **défile**
> (`scrollTop` 400) ; les Calques restent visibles en bas (bas = 700, 2
> calques) pendant le défilement ; replier Apparence, Carte, Grille → état
> écrit, **relu après rechargement** (styleDetails false, carte false,
> grille false), sections fermées à **0 px** ; clic sur une tête → rouvre,
> 347 px, état réécrit ; persona Pixel → Forme / Nœuds / Repères / Grille /
> Carte à 0 px, Pixel 362 px, Calques 112 px ; persona Export → Apparence /
> Forme / Image / Repères à 0 px, Export 294 px, Export + 288 px ; retour
> Vecteur → Pixel 0 px, Forme 80 px.
>
> **Deux défauts attrapés par la preuve** : un `<details>` fermé laissait
> son contenu visible (347 px) — `#panneauStyle { display: flex }` bat par
> spécificité la règle du navigateur qui cache le contenu fermé (règle
> `!important` ciblée sur le panneau) ; les règles des personas visaient les
> anciens `div` : les têtes restaient visibles (elles ciblent les sections
> `details` entières).
>
> **Déployé** : 6 fichiers (= base lot G `8cfece4` par hash-object, 1
> absent) → sauvegarde `_backup_predeploy_2026-09-17i-vectorlab-panneau` →
> `git archive de96ac1` → **6 = cible, 112/112 du Vectorlab = cible**.
> Aucun Python touché.
>
> **Reste** : l'état des sections est global (pas par document) ; la zone
> Calques est bornée à 40 % de la hauteur (au-delà elle défile seule) ; à
> moins de 500 px de haut, la zone des réglages devient courte (le
> défilement reste).

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
