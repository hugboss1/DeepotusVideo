# Affecter la nouvelle suite d'icônes aux usages réels

Contexte : DeepotusVideo a un inventaire de ses icônes actuelles (une entrée par USAGE : écran, emplacement, libellé, fonction). Une nouvelle suite de 133 icônes `dz-<famille>-<nom>` a été dessinée (liste et sens : `cles.md` dans ce dossier). Il faut dire, pour CHAQUE usage de ton lot, quelle nouvelle clé doit s'y afficher.

Lis `cles.md`, puis ton lot `lotN.json`. Pour chaque entrée, décide selon le SENS (libellé + fonction + emplacement), jamais selon le dessin actuel : un même glyphe actuel peut recevoir des clés différentes (⧉ = dupliquer ici, grouper là).

Sortie : `resN.json` dans ce dossier = un objet `{ "<id>": {...}, ... }` avec UNE clé par id du lot (toutes, sans exception), valeur :
```json
{"cible": "dz-action-supprimer" | null,
 "confiance": "sure" | "probable",
 "manque": "dz-<famille>-<nom-propose>" | "",
 "note": ""}
```
- `cible` : la clé existante qui porte ce sens. `sure` = sens identique ; `probable` = sens voisin acceptable (ex. « Tester » → dz-media-lecture).
- Si AUCUNE clé ne convient : `cible: null` et `manque` = nom d'une clé À AJOUTER à la suite, en respectant le nommage (familles : nav, cat, action, etat, media, edit, outil-vec, outil-px, outil-photo, calque, lab3d, marque ; nom en français, minuscules, sans accent, tirets). RÉUTILISE le même nom de manque pour le même sens (cohérence dans ton lot ; préfère des noms génériques : `dz-action-favori`, `dz-nav-montage`, `dz-cat-sprites`…).
- Les entrées `type: "aucune"` (bouton texte sans icône) : propose une cible seulement si une icône aiderait clairement (barre d'outils, action courante) ; sinon `cible: null, manque: ""` et note « texte seul conseillé ».
- Les décors (role decor, séparateurs, puces ●, flèches dans du texte courant, poignées) : `cible: null, manque: ""`, note « décor, pas d'icône ».
- Attention aux pièges connus : les catégories de la suite (personnage, decor, objet, interface, texture, animation, audio, 3d) ne correspondent PAS aux catégories Game Assets de l'app (3D, 3D Studio, Sprites 2D, Tuiles, Matières, Cartes) ni aux catégories de nœuds du Studio (motion, source, master, output, compose, audio, edit, gen) — n'affecte que si le sens est vraiment le même, sinon manque. Le rail de l'app a Quick, Studio, Chapitres, Son & VFX, Montage, Scheduler, Templates, News, Bibliothèque, Game Assets, Réglages : la suite n'a pas nav-chapitres/son-vfx/montage/templates/news. `dz-action-quick` = l'action Quick (éclair) ; `dz-action-generer` = étincelle de génération IA ; `dz-action-cout` = coût/dépense ; `dz-action-chevron` = tout chevron de repli/déroulé/précédent-suivant de liste (orienté par CSS) ; `dz-action-reglages` = ouvrir des options ; `dz-nav-parametres` = l'écran Réglages.
- Fermer (panneau/dialogue, ne détruit rien) ≠ Supprimer. Annuler (undo) ≠ Fermer.
Écris le fichier, valide-le (`node -e` : JSON.parse + toutes les id du lot présentes + chaque cible ∈ cles.md), puis réponds en 5 lignes : nb sure / probable / null, et les 10 « manque » les plus fréquents avec leur nombre.
