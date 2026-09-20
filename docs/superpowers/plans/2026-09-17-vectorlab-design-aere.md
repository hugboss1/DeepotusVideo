# Vectorlab — panneau aéré, champs centrés, bulles d'information lisibles — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).

> Demande du 17/09/2026 (capture) : « design plus aéré, chaque champ ou bulle
> d'information centré, lisible, proportionné ». Après le lot « panneau de
> droite » (`c957222`).

> **RELEVÉ DE LIVRAISON (17/09/2026) : LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ (statiques seuls : aucune relance).**
>
> **Livré** (commits `9d34d6d`→`a1cc6ce`, poussés) : couche CSS « design
> aéré » (variables `--pan-*`, rythme vertical de 8 px, têtes de section en
> petites capitales de 36 px avec chevron, sous-sections marquées, libellés
> alignés à droite sur 64 px, champs de 28 px à coins arrondis et nombres
> centrés — formules X · Y · L · H comprises —, boutons à hauteur égale
> centrés, rangées d'icônes à largeur partagée, pastilles 28 px, palette 22
> px, calques compacts à nom lisible, barre d'outils 38 px arrondie) ;
> `mod-infobulle.js` feuille (position centrée sous l'ancre, bornée à la
> fenêtre, au-dessus si la place manque ; texte coupé aux « — » et « · »)
> + `initInfobulle` (au survol d'un `[title]` des barres et du panneau, bulle
> stylée 12 px / 260 px max, title natif neutralisé puis rendu).
>
> **TDD** : RED constaté (banc `infobulle.test.mjs`, 8 contrôles) ; node
> **953 contrôles sur 59 bancs** (somme par banc — les totaux annoncés aux
> lots précédents comptaient des lignes en double du harnais), pytest
> `test_vector_docs` **37 passed**.
>
> **Prouvé en réel** (8799, viewport 1400×900, lecture DOM et capture) :
> **77 champs et boutons visibles, tous à 28 px** ; libellés tous à 64 px
> alignés à droite ; champ L à `text-align: center` ; tête Apparence 36 px
> en capitales ; les six boutons Aligner tiennent sur leur rangée (19 px
> chacun, centrés) ; bulle sur « Grouper » : visible, **écart de centre 0
> px**, 260 px, 12 px, `title` retiré pendant le survol et rendu après ;
> bulle d'un outil de la barre gauche bornée à 8 px du bord, deux lignes ;
> outils 38 px arrondis ; noms de calques lisibles (aucune troncature) ;
> capture : rangées régulières, colonnes alignées.
>
> **Deux défauts attrapés par la preuve** : les six boutons Aligner
> débordaient de la rangée (marge interne + largeur mini) → rangées
> d'icônes à largeur partagée sans marge ; les noms de calques étaient
> écrasés à 12 px par les boutons de rangée → contrôles de calque compacts
> (24 px, opacité 38 px, nom à 40 px minimum).
>
> **Déployé** : 4 fichiers (= base `de96ac1` par hash-object, 2 absents) →
> sauvegarde `_backup_predeploy_2026-09-17j-vectorlab-aere` → `git archive
> a1cc6ce` → **4 = cible, 114/114 du Vectorlab = cible**. Aucun Python.
>
> **Reste** : les `<select>` gardent leur popup natif ; la bulle n'a pas de
> délai d'apparition (le survol suffit) ; les dialogues (`.vl-dlg`) gardent
> le title natif.

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
