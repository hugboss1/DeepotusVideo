# Vectorlab — retrait des redondances (les menus détachés gardent la main) et miniatures de calques — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).

> Demande du 17/09/2026 : « supprime tout ce qui est redondant en conservant
> les dernières modifications (les menus détachés), supprime uniquement ce
> qui était avant ; et une miniature par calque qui représente son contenu ».

> **RELEVÉ DE LIVRAISON (17/09/2026) : LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ (statiques seuls : aucune relance).**
>
> **Retiré (l'ancien)** : l'en-tête « Image ▾ » et son menu (le champ
> fichier caché reste) ; dans Apparence les rangées Aligner ×2, distribuer
> / miroir / dupliquer, Ordre, Grouper / Dégrouper, Booléens ; la liste de
> forme du panneau Forme ; les boutons Diviser / Inverser / Joindre / Coins
> du panneau Nœuds ; la section Symboles d'Apparence + ; la grille des
> polices du panneau Texte ; la liste du mode de tranche d'Export + ; les
> boutons Tout / Aucune / Inverser / Croître / Contracter / Par couleur du
> panneau Pixel. Chaque panneau garde une note d'une ligne qui renvoie au
> menu.
>
> **Conservé (le nouveau)** : les menus détachés, désormais branchés sur
> `VL.actions.<module>` que chaque module expose (selection : aligner,
> distribuer, miroir, dupliquer, ordre, grouper, degrouper, booleen ;
> noeuds : diviser, inverser, joindre, coins ; pixel : tout, aucune,
> inverser, croitre, contracter, couleur ; image : biblio, fichier, coller,
> generer, vectoriser ; symboles : detacher, supprimer) — plus aucune
> dépendance à un bouton retiré ; le menu Sélection gagne distribuer /
> miroir / dupliquer (21 entrées), le menu Symboles gagne Détacher et
> Supprimer.
>
> **Miniatures** : `vignette_calque_svg(doc, id, w, h, image)` PURE dans
> mod-layers — ce calque seul (les autres RETIRÉS du clone : cachés, ils se
> compileraient en `display:none`), sans fond de page, damier, ids de defs
> préfixés, `data-objet` retirés — dans une rangée en grille (vignette 40×28
> à gauche sur deux lignes, nom, commandes). Banc `vignettes.test.mjs` (RED
> puis 5 contrôles) ; node **993 contrôles sur 62 bancs**, pytest **40
> passed** (le pin du lot A suit les actions).
>
> **Prouvé en réel** (8799, 1400×900) : les 14 redondances absentes du DOM
> ; menu Sélection **21 entrées** → Grouper crée un groupe, Dégrouper rend 2
> objets, Aligner à droite déplace, Dupliquer sélectionne la copie ; Nœuds →
> Inverser change le `d` ; Symboles → Créer, poser (instance), Détacher (2
> objets), Supprimer (plus de symbole) ; Image → Fichier ouvre le champ
> fichier ; Pixel → Tout = 64 px de masque, Inverser ; Tranche → mode
> planches et note du panneau ; miniatures : rangée 60 px sans débordement,
> vignette 40×28 avec damier et 9 éléments pour c1, aucun `data-objet` ; un
> calque « haut » à une ellipse → sa vignette n'a qu'une ellipse de sa
> couleur et pas le rouge de c1 (capture).
>
> **Deux défauts attrapés par la preuve** : la garde des actions image
> référençait encore le menu d'en-tête retiré (Fichier muet) ; `#flyout`
> en `display: flex` battait l'attribut `hidden` (boîte vide de 14 px sous
> la barre).
>
> **Déployé** : 12 fichiers (= base `884cae7` par hash-object, 1 absent)
> → sauvegarde `_backup_predeploy_2026-09-17p-vectorlab-redondances` →
> `git archive 3be776e` → **12 = cible, 119/119 du Vectorlab = cible**.
>
> **Reste** : les miniatures se recompilent à chaque rendu (un document de
> centaines d'objets par calque les rendra lentes : cache par calque à
> prévoir si besoin) ; les ids de dégradés d'une vignette sont préfixés
> mais un dégradé référencé sans defs propres tombe sur celui du canevas.

**Goal :** ce que les menus détachés couvrent disparaît du panneau et de
l'en-tête ; les menus ne dépendent plus d'aucun bouton retiré (ils
appellent les ACTIONS que chaque module expose) ; chaque rangée de calque
montre une miniature du contenu du calque seul.

**Redondances retirées (l'ancien) → ce qui reste (le nouveau) :**
- en-tête « Image ▾ » → menu Image de la barre (les gestes de pose restent
  dans mod-image, appelés par leurs fonctions) ;
- panneau Apparence : rangées Aligner ×2, distribuer / miroir / dupliquer,
  Ordre, Grouper / Dégrouper, Booléens → menu Sélection (qui gagne
  distribuer, miroir, dupliquer) ;
- panneau Forme & gestes : la liste de la forme → menu Forme (les
  paramètres de la forme sélectionnée, la largeur de gomme et le rayon de
  coin restent : valeurs libres) ;
- panneau Nœuds : Diviser / Inverser / Joindre / Coins → menu Nœuds (les
  alignements d'ancres restent) ;
- panneau Texte : la grille des polices → menu Typographies (Déposer et
  Système restent des boutons du panneau, que le menu appelle) ;
- panneau Apparence + : section Symboles → menu Symboles (qui gagne
  Détacher et Supprimer) ;
- panneau Pixel : Tout / Aucune / Inverser / Croître / Contracter / Par
  couleur → menu Sélection raster ;
- panneau Export + : la liste du mode de tranche → menu Tranches.

**Architecture :** chaque module expose ses actions sur `VL.actions.<module>`
(mod-style : aligner, distribuer, miroir, ordre, grouper, degrouper,
booleen, dupliquer ; mod-outils2 : noeuds.* ; mod-pixelui : pixel.* ;
mod-image : image.* ; mod-apparence2 : symboles.detacher/supprimer) ; les
menus de mod-flyout les appellent (plus de `cliquer` par id pour ces
actions) ; `mod-layers.js` gagne `vignette_calque_svg(doc, calqueId, w, h,
image)` PURE (compile le document avec ce seul calque visible, sans fond,
dans une boîte w×h, fond damier) et l'affiche dans chaque rangée.

## Tasks
1. `vignette_calque_svg` (banc `vignettes.test.mjs`, RED) ; `VL.actions` par module ; menus re-câblés.
2. Retraits (HTML / JS) ; audit de lisibilité rejoué ; preuve (chaque menu joue son action sans le bouton ; miniatures = contenu du calque) ; déploiement statiques ; relevé.
