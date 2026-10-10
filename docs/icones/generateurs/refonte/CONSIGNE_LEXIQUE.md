# Étape 1 — Lexique définitif des icônes DeepotusVideo

Dossier : `C:\Users\olivi\AppData\Local\Temp\claude\C--Users-olivi-DeepotusVideo\5f390379-8af8-4f85-bbcd-1718a3c27423\scratchpad\refonte\` (abrégé `R\`). Ne modifie RIEN ailleurs que dans `R\`.

Lis d'abord `R\CHARTE.md` : ses principes sont la loi de cette étape (surtout 1, 3, 4, 5, 6).

## Entrées
- `..\out2\inventaire-icones.json` : les 2 396 usages de l'app PC (écran, emplacement, libellé, fonction, `nouvelle_cle` = clé du kit affectée, `confiance`, `manque` = clé proposée faute de mieux, `note_affectation`).
- `..\inv\M_mobile.json` : les usages du compagnon mobile (zone "Mobile", champ `equivalent_pc`).
- `R\noms_et_usages.json` : chaque nom (133 clés du kit + ~300 propositions) avec ses usages réels et des exemples. C'est ton point de départ.
- `R\emojis.json` : les 273 usages d'emojis. `R\sans_icone.json` : les 293 usages sans icône prévue.
- `R\design15_27_icones.md` : les 27 icônes en production (rail, Card Forge, catégories). Leurs SENS font foi pour la navigation, les étapes Card Forge et les catégories Game Assets.
- `..\kit_zip\deepotusvideo-icons\` : le kit (SVG + DOCUMENT-IMPLEMENTATION.md). Dix groupes de clés du kit ont un tracé identique (voir ci-dessous) ; c'est à corriger.
  Doublons de tracé du kit : exporter=nav-export ; action-quick=nav-quick ; action-rotation=lab3d-rotation ; action-reglages=nav-parametres ; media-image=nav-photolab ; media-texte=outil-vec-texte ; edit-rogner=outil-photo-recadrer ; nav-spritelab=nav-tilelab ; nav-lab3d=cat-3d=lab3d-cube ; marque-poulpe=marque-favicon=marque-fenetre.

## Travail
1. **Arrêter la liste des fonctions** : regroupe les noms qui désignent la même fonction (ex. `etat-coche` / `action-valider` / `etat-succes` : décide ce qui est un état « réussi », une coche de menu, un bouton « Valider » — trois choses distinctes ou non, mais tranche et justifie), et sépare ceux qui mélangent deux fonctions. Relis les affectations `probable` : garde-les seulement si la fonction est vraiment la même ; sinon crée ou choisis la bonne clé. Supprime les clés du kit qui ne servent aucune fonction réelle de l'app (ex. `nav-export`, `nav-lab3d` s'ils ne sont pas des lieux de l'app ; les catégories du kit qui ne sont pas des catégories de l'app) — liste-les à part comme « retirées ».
2. **Navigation réelle** : le rail du PC (Quick, Studio, Chapitres, Son & VFX, Montage, Scheduler, Templates, News, Bibliothèque, Game Assets, Réglages), les onglets Game Assets (3D, 3D Studio, Assets 2D, Sprites, Tuiles, Matières, Cartes…), les labs (Vectorlab, Photolab, Spritelab, Tilelab, Card Forge, Établi, Matières, Studio 3D, Plateau, Atelier), les catégories de nœuds du Studio, les étapes Card Forge, les onglets du mobile. Chacun a sa clé ; un écran et une action ne partagent jamais de dessin.
3. **Pièges de sens à trancher explicitement** (et à consigner dans `ne_pas_confondre_avec`) : Fermer / Supprimer / Retirer / Annuler (undo) / Abandonner ; Ajouter / Nouveau / Créer ; Dupliquer / Copier / Cloner ; Importer / Télécharger / Charger un fichier ; Exporter / Envoyer vers / Publier / Partager ; Actualiser / Réessayer / Régénérer / Réinitialiser / Restaurer / Rotation ; Réglages (options d'un objet) / Réglages (écran) ; Générer IA / Quick / Aléatoire ; outil Zoom / Zoom avant / Zoom arrière / Ajuster à l'écran ; Lecture / Tester / Lancer ; Lien / Lier / Ouvrir à l'extérieur ; Favori / Épingler / Épingler au mobile ; Aide / Information ; Avertissement / Erreur ; Masquer un calque / Masque de calque ; Sélection (outil) / Tout sélectionner.
4. **Emojis** (CHARTE §1.4) : pour chaque usage de `emojis.json`, décide `emoji_conserve: true` seulement s'il est un CONTENU (emoji inséré dans un post / une légende / sélecteur d'emojis, ou étiquette de type de suggestion du menu Quick). Tous les autres reçoivent une clé.
5. **Usages sans icône** (`sans_icone.json`) : confirme « texte seul » ou attribue une clé si c'est une action de barre d'outils ou une action récurrente.
6. **Brief de dessin** pour chaque clé gardée : une métaphore unique, ce qui est au ton sujet, ce qui est au ton support, le badge éventuel (CHARTE §4), la série (CHARTE §6), et SURTOUT en quoi sa silhouette diffère de ses voisines confusables. Indique `origine` : `design15` (métaphore et composition du tracé en production, à reprendre au plus près — donne la ligne du tableau), `kit` (métaphore du kit bonne, à reprendre — nom du fichier), `kit-a-redessiner` (métaphore du kit fautive : doublon ou confusion — dis pourquoi), `nouveau`. NB : TOUTES les icônes seront redessinées pour respecter la règle du monochrome (CHARTE §3) — le banc a montré que, en un seul ton, les 7 types de calques du kit deviennent le même carré et les 5 états le même disque. `origine` dit seulement d'où vient l'IDÉE.
7. **Mobile** : `mobile: true` si la fonction existe dans le compagnon mobile (d'après `M_mobile.json` et `equivalent_pc`).

## Sorties (dans `R\`)
- `lexique.json` : tableau trié par famille puis nom :
```json
{"cle":"dz-action-supprimer","famille":"action","sens":"Détruit l'élément ou l'envoie à la corbeille.",
 "ne_pas_confondre_avec":[{"cle":"dz-action-fermer","difference":"fermer ne détruit rien : croix nue ; supprimer : corbeille"}],
 "dessin":{"metaphore":"corbeille","sujet":"cuve et couvercle","support":"—","badge":"","serie":""},
 "origine":"kit","reprend":"dz-action-supprimer.svg","mobile":true,"zones":["…"],"usages":95}
```
  Pour `reseau` : `"origine":"logo-tiers","source_logo":"simple-icons:<slug>"`.
- `renommage.json` : `{ "<ancien nom (kit ou proposé)>": "<clé finale>" | null }` pour TOUS les noms de `noms_et_usages.json`.
- `retirees.json` : clés du kit retirées, avec la raison.
- `affectation_finale.json` : `{ "<id>": {"cle": "<clé finale>"|null, "emoji_conserve": bool, "raison": ""} }` pour TOUS les ids de l'inventaire PC ET du mobile. `raison` obligatoire quand la clé finale diffère de `renommage[nouvelle_cle||manque]` ou quand `cle` est null.
- Valide par script node : JSON valides ; chaque id présent ; chaque clé citée existe dans `lexique.json` ; aucune clé du lexique sans usage (sauf justification dans `sens`) ; aucun `sens` en double ; chaque entrée a un `ne_pas_confondre_avec` non vide quand une clé voisine existe.
Écris tes scripts hors de `R\` (dans `..\lex_work\`). Réponse finale courte : nb de clés par famille et par origine, nb d'emojis conservés, nb de clés du kit retirées, et les 10 arbitrages de sens les plus importants (une ligne chacun).
