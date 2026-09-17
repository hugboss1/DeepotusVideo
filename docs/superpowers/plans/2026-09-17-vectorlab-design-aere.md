# Vectorlab — panneau aéré, champs centrés, bulles d'information lisibles — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).

> Demande du 17/09/2026 (capture) : « design plus aéré, chaque champ ou bulle
> d'information centré, lisible, proportionné ». Après le lot « panneau de
> droite » (`c957222`).

> **RELEVÉ DE LIVRAISON** : à écrire ici en fin de lot.

**Goal :** le panneau de droite respire (rythme vertical de 8 px, têtes de
section en petites capitales, sous-sections marquées), chaque champ a la
même hauteur (28 px), les nombres sont centrés, les boutons d'une rangée se
partagent la largeur, et les infobulles (attributs `title`) deviennent des
bulles stylées, centrées sous l'élément, lisibles, jamais hors écran.

**Architecture :** une couche CSS « design aéré » en fin de feuille
(variables `--pan-*`, sélecteurs limités au panneau et aux barres) qui
surcharge les règles des lots sans les réécrire ; `mod-infobulle.js`
FEUILLE pur (`bulle_position(ancre, taille, fenetre, marge)` → `{x, y, dessous}`
centrée sous l'ancre, bornée à la fenêtre, au-dessus si la place manque) +
son `initInfobulle(VL)` qui, au survol d'un `[title]` de l'éditeur, montre
une bulle `.infobulle` et neutralise la bulle native (title → data-tip
pendant le survol, remis au départ).

**Décisions :** les libellés de rangée (`.ap-ligne > span`) gardent une
largeur fixe (64 px) alignée à droite pour que les champs s'alignent en
colonne ; les champs numériques sont centrés ; les infobulles ont 260 px de
large au plus, 12 px, interligne 1,45, sans délai d'apparition (le survol
suffit) ; les `<select>` gardent le popup natif (color-scheme dark).

## Tasks
1. `mod-infobulle.js` (banc `infobulle.test.mjs`) — `bulle_position`, `texte_bulle(title)` (retours à la ligne sur « — » et « · »), `initInfobulle`.
2. CSS « design aéré » : variables, têtes de section, rangées, champs, boutons, pastilles, sous-sections, palette, bulle.
3. Preuve en réel (hauteurs de champs, centrage, bulle centrée et bornée), déploiement statiques, relevé.
