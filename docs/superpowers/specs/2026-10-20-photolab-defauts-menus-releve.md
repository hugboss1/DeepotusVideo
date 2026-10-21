# Photolab — défauts des menus relevés par le catalogue de l'assistant (#415) : relevé et décisions

Relevé du 20/10/2026, sur `origin/main` 0f9b3feb (photocraft 0.10.0 épinglé). Source : section « Constats » de la PR
hugboss1/DeepotusVideo#415. Chaque défaut a été revérifié dans le code de l'écran (`mod-menus.js` construireMenus /
actionEntree, `mod-cycle.js` PL.executer, `mod-champs.js`, `mod-texte.js`, `mod-calques.js`, `mod-raccourcis.js`,
`mod-fichier.js`) et **sondé sur le vrai moteur** (`photocraft-cli 0.10.0 serve`, document 200 × 100 jetable).

« Chez eux » = le comportement usuel d'un logiciel de retouche de référence (dialogue, champs, effet) et celui du
moteur photocraft quand il diffère. Relevé du comportement de référence fait de mémoire, **non revérifié** sur
l'application installée (pas de session computer-use pour ce chantier ; à faire sur demande).

Décisions : **Corriger** (lot), **Bientôt** (griser : l'entrée sort du catalogue de l'assistant), **Garder** (et
documenter). Le comportement voulu des 15 « Nouveau calque de réglage » n'est pas touché.

## Faits mesurés sur le moteur qui changent le tri

| Commande | Réponse du moteur 0.10 |
|---|---|
| `edit.colorSettings` | **toujours refusée** : « uses ambient filesystem paths and is disabled » (automation) |
| `layer.smartObjects.revealInFinder` (avec ou sans `dryRun`) | **toujours refusée** (même raison) |
| `layer.videoLayers.newVideoLayerFromFile`, `replaceFootage`, `reloadFrame` | **toujours refusées** (même raison) |
| `layer.videoLayers.newBlankVideoLayer` | crée un calque « Video Layer 1 » (`kind: Pixel`) et une timeline `{current, duration, fps}` |
| `insertBlankFrame`, `duplicateFrame`, `deleteFrame`, `interpretFootage`, `showAlteredVideo`, `restore*` | répondent `{frames: n}` : n'agissent que sur la timeline, que l'écran ne montre nulle part |
| `edit.purge.videoCache` | « nothing to purge (no video layers) » ; marche sans document mais `PL.executer` n'envoie rien sans document |
| `type.resolveMissingFonts {}` | `{missing: ["Famille"]}` (liste) ; `{map: {…}}` remplace |
| `edit.checkSpelling {}` | `{count, misspellings: [{layer, start, end, word, suggestions}]}` |
| `image.analysis.countTool` | relit `{groups, total}` ; l'outil Comptage de l'écran existe déjà (mod-mesure, `count.*`) |
| `view.newGuide {orientation}` | « missing `position` » — l'entrée échoue toujours |
| `layer.layerContentOptions` | `{editor: "fill" \| "adjustment:<kind>", layer}` — dit QUEL éditeur ouvrir ; refus sur un calque de pixels |
| `layer.new.artboardFromGroup` | s'exécute (groupe choisi requis), aucun paramètre de dialogue côté moteur |
| `image.trap` | `{width: px ≥ 1 = 1}` mal écrit dans le registre (clé sans guillemets) → **aucun champ** parsé ; CMYK requis |
| `layer.layerMask.enabled {}` | **bascule** (rend `{enabled}`) ; `doc.inspect` ne dit pas si le masque est actif (l'écran le suit dans `PL.etat.etatsMasques`) |
| `pattern.list` | liste les motifs (id, nom, taille) même sans document |
| `layer.duplicate {document: "new"}` | crée un nouveau document avec la copie |

## 1. Entrées actives sans effet visible

| Entrée | Chez eux | Chez nous (code + moteur) | Décision |
|---|---|---|---|
| Texte › Résoudre les polices manquantes… | Dialogue : chaque police manquante, une police de remplacement à choisir | `actionEntree` = executer `{}` ; la liste rendue par le moteur est jetée par `PL.executer` | **Corriger** (lot C) : dialogue sur mesure — familles manquantes, liste des polices installées (`type.fonts`) par famille, `{map}` ; « aucune police manquante » s'il n'y en a pas |
| Texte › Options de langue › Composeur Moyen-Orient et Asie du Sud | Change le moteur de composition des paragraphes | Coche d'écran (`prefs.composeur`) jamais relue ; le moteur n'a **aucune** commande de composeur | **Bientôt** (retirer de TRAITES_PAR_ECRAN) |
| Édition › Purger › Cache vidéo | Vide le cache des images vidéo | Rien envoyé sans document ; sans calque vidéo affiché, rien à purger | **Bientôt** (suit les calques vidéo) |
| Édition › Paramètres de couleur… | Dialogue des espaces de travail | Dialogue générique ouvert, mais le moteur **refuse toujours** la commande en automation | **Bientôt** |
| Édition › Barre d'outils… | Dialogue : outils montrés / rangés dans « outils supplémentaires », réinitialiser | Dialogue générique (« reset » seul) ; le moteur range bien `hidden/order` mais la barre de l'écran (mod-outils) ne les relit jamais | **Corriger** (lot C) : dialogue d'ÉCRAN (cases « montrer » par outil + Réinitialiser), gardé dans les préférences de l'écran comme Édition › Raccourcis clavier ; le moteur n'est pas appelé |
| Image › Analyse › Outil Compteur | Choisit l'outil Comptage | executer → relit, rien ne change | **Corriger** (lot A) : action d'écran = `PL.choisirOutil("count")` |
| (même famille) Image › Analyse › Outil Règle | Choisit l'outil Règle | Dialogue générique « clear » seul | **Corriger** (lot A, ajouté) : `PL.choisirOutil("ruler")` |
| Calque › Calques vidéo (12 entrées) + Calque › Rastériser › Vidéo | Calques vidéo pilotés par le panneau Montage (timeline) | 3 toujours refusées par le moteur ; les autres agissent sur une timeline invisible ; « Nouveau calque vidéo vide » ne donne qu'un calque de pixels | **Bientôt** (13 entrées) — un panneau Timeline serait un chantier à part |
| Calque › Objets intelligents › Afficher dans le Finder | Ouvre l'explorateur sur le fichier lié | Dialogue « dryRun » ; le moteur **refuse toujours** | **Bientôt** |

## 2. Dialogues incomplets

| Entrée | Chez eux | Chez nous | Décision |
|---|---|---|---|
| Affichage › Nouveau repère… | Orientation, Position (unités), Couleur | `position` (requise) et `color` sont de type « ? » → cachés ; le moteur répond « missing position » | **Corriger** (lot B) : champs complétés par l'écran — position (nombre + unité px / %), couleur (liste du moteur) |
| Sélection › Charger la sélection… | Document, Couche, Inverser, Opération | `channel` (requise, « ? ») cachée | **Corriger** (lot B) : liste de choix `PL.choixDialogue` — Transparence, Masque de calque, Composite, couches de couleur et couches alpha lues dans `doc.inspect.channels`, Masque rapide |
| Calque › Dupliquer le calque… | Nom, Destination : document ouvert ou Nouveau | `document` (« ? ») caché | **Corriger** (lot B) : liste de choix — ce document / nouveau document / autres documents ouverts |
| Calque › Nouveau calque de remplissage › Motif… | Choix du motif, échelle, angle, lier | `pattern` (union) caché : toujours le premier motif | **Corriger** (lot B) : liste de choix des motifs (`pattern.list`) |
| Édition › Déformation de la perspective · Calque › Objets intelligents › Déformation de la perspective | Plans tracés puis déformés à la souris (deux modes) | `planes` (requise, struct) cachée : le dialogue n'a que redresser / interpolation | **Bientôt** (2 entrées, comme la Déformation de la marionnette : `SANS_EDITEUR`) |
| Édition › Vérifier l'orthographe… | Dialogue : mot fautif, suggestions, Ignorer / Tout ignorer / Changer / Tout changer / Ajouter | Dialogue générique sans la liste ; le résultat est jeté | **Corriger** (lot C) : dialogue sur mesure — fautes une à une, suggestions, Changer / Tout changer / Ignorer / Ajouter au dictionnaire (`action: change/changeAll/addToDictionary`, `ignore`) |

## 3. « … » qui s'exécute sans dialogue

| Entrée | Chez eux | Chez nous | Décision |
|---|---|---|---|
| Interpréter le métrage… · Remplacer le métrage… · Nouveau calque vidéo à partir d'un fichier… | Dialogue / choix de fichier | Calques vidéo | **Bientôt** (avec les calques vidéo, §1) |
| Calque › Options de contenu du calque… | Ouvre l'éditeur du calque de remplissage ou de réglage | executer ; le moteur rend l'éditeur à ouvrir, jeté | **Corriger** (lot B) : action d'écran — l'éditeur que le moteur désigne (panneau Propriétés, comme le double-clic sur la vignette) ; refus signalé sur un calque de pixels |
| Calque › Nouveau › Plan de travail d'après un groupe… | Dialogue nom + taille | Le moteur n'a ni nom ni taille : s'exécute | **Garder**, libellé sans « … » à l'écran (menus.json intact) |
| Image › Recouvrement… (1 px fixe) | Dialogue Largeur (CMYK seulement) | Registre mal écrit → aucun champ ; 1 px toujours | **Corriger** (lot B) : champ `width` (px, ≥ 1) complété par le pont (structurer), banc de bornes ; le refus « CMYK requis » du moteur reste le message |

## 4. Libellés trompeurs

| Entrée | Chez eux | Chez nous | Décision |
|---|---|---|---|
| Fichier › Enregistrer sous… | Enregistre une copie sous un nouveau nom / format | Ouvre « Exporter sous » (téléchargement), rien dans la Bibliothèque | **Corriger** (lot B) : dialogue Nom + format (PNG / JPEG, qualité) → route `/bibliotheque` (`nom`) : un NOUVEAU fichier dans la Bibliothèque ; « Exporter sous… » reste le téléchargement |
| Calque › Masque de calque › Activer le masque de calque | Libellé qui suit l'état : « Désactiver » quand le masque est actif, « Activer » sinon | Libellé fixe « Activer » ; bascule moteur ; l'état suivi par le panneau Calques (`etatsMasques`) n'est pas mis à jour par le menu | **Corriger** (lot A) : action d'écran partagée avec le Maj+clic du panneau (`enabled` explicite, état mis à jour) ; libellé Activer / Désactiver selon l'état ; même traitement pour « Lier / Délier le masque de calque » (même défaut) |

## 5. Raccourcis

| Entrée | Chez eux | Chez nous | Décision |
|---|---|---|---|
| Édition › Couper / Copier / Coller / Effacer | Ctrl+X, Ctrl+C, Ctrl+V, Suppr | Absents de menus.json → aucun raccourci | **Corriger** (lot A) : `RACCOURCIS_ECRAN` (mod-raccourcis) + affichage du raccourci dans le menu (Annuler / Rétablir en profitent : Ctrl+Z n'y est pas affiché non plus) ; Suppr ne part pas quand un outil le prend déjà (tracé, tranche, courbe) ni dans un champ de saisie |

## Lots proposés

- **Lot A — menus d'écran** : 19 entrées grisées « bientôt » (composeur, Paramètres de couleur, Cache vidéo,
  Afficher dans le Finder, 13 vidéo, 2 Déformation de la perspective), Outil Compteur / Règle, masque Activer /
  Lier, raccourcis Ctrl+C/X/V/Suppr, libellé du Plan de travail. Bancs : `qa/menus.test.mjs`, `qa/raccourcis.test.mjs`,
  `qa/calques-m7.test.mjs`.
- **Lot B — dialogues complétés** : Nouveau repère, Charger la sélection, Dupliquer le calque, Remplissage Motif,
  Recouvrement, Options de contenu, Enregistrer sous. Bancs `qa/champs.test.mjs`, `qa/documents.test.mjs`,
  `qa/fichier.test.mjs`, `backend/tests/test_photolab_registre*.py`.
- **Lot C — dialogues sur mesure** : polices manquantes, orthographe, barre d'outils.
- **Fin** : `scripts/agent/catalogue.py`, rôles des fiches `photolab.menu.*` touchées réécrits (les 19 grisées sortent
  du catalogue), `catalogue.py --check` et les quatre `test_agent_*` verts, PR vers main. Rien installé.
