# Traduction L9 (t149) — consigne de saisie pour un groupe (Spritelab, Tile Lab, Studio3D, Plateau, Lib3D)

Tu écris UN fichier de saisie : `scripts/i18n_l9/<groupe>.py` (le nom t'est donné). Tu ne modifies AUCUN autre fichier
(ni les sources des labs, ni le générateur, ni la saisie des autres groupes : d'autres agents travaillent en parallèle
dans le même dossier). Dossier de travail : `C:\Users\olivi\DeepotusVideo\.claude\worktrees\i18n-l9`.

## Le but
Ces labs statiques de DeepotusVideo sont en français ; leur interface doit pouvoir s'afficher en anglais :
- `frontend/spritelab/` — le Spritelab (planches de sprites, animation, hitboxes, directions, squelette, exports
  moteur) ; `spritelab.js` est un script CLASSIQUE, les autres `.js` sont des MODULES ES ;
- `frontend/tilelab/` — le Tile Lab (jeux de tuiles, blob 47/16, peintre de niveau, exports Tiled/LDtk/Godot) ;
  `tilelab.js`, `jeu.js`, `peintre.js` sont CLASSIQUES, `feuille_tuiles.js` et `envoi.js` des MODULES ;
- `frontend/studio3d/` — le Studio3D (modèles 3D générés : fal, Meshy, local, vues, banc d'essai) ; MODULES ;
- `frontend/plateau/` — le Plateau 3D (mise en scène caméra, keyframes) ; MODULES ;
- `frontend/lib3d/` — la bibliothèque 3D partagée (visionneuse, plaque, sélection, rig) ; MODULES.
Chaque texte AFFICHÉ de ta plage passe par `dzT("<zone>.<sous>.<role>")`, écrit EXACTEMENT ainsi dans ta saisie (le
générateur le réécrit ensuite pour qu'il marche aussi sous node : ne t'en occupe pas, n'importe rien). Le français reste
la langue de référence : la clé a son `fr` (copié tel quel du code) et son `en`.

Préfixe de clé imposé par le dossier : `sprites.` pour frontend/spritelab, `tuiles.` pour frontend/tilelab,
`studio3d.` pour frontend/studio3d, `plateau.` pour frontend/plateau, `lib3d.` pour frontend/lib3d (le générateur
refuse une clé d'un autre dossier). Les sous-zones sont libres mais PRÉFIXÉES par l'abréviation de ton groupe que l'on
te donne (ex. groupe `sp1` → `sprites.sp1_anim.lecture`) pour qu'aucun autre agent n'écrive la même clé.

## Le format (lis `scripts/i18n_l9/outils.py`)
```python
"""t149 — <groupe> : ce que couvre ta plage, ce qui est GARDÉ et pourquoi (en résumé)."""
from outils import L, S, X, H

PLAGES = {"spritelab/spritelab.js": (1, 700)}      # chaque entrée doit COMMENCER dans ta plage (si on t'en donne une)

ENTREES = [
    L("spritelab/spritelab.js", 77, '"délai dépassé"', "sprites.sp1_gen.delai", "délai dépassé", "timed out"),
    S("spritelab/spritelab.js", 696, '`${r.os} os et ${r.pieces} pièce(s) retirés`',
      '`${dzT("sprites.sp1_sk.retires", { os: r.os, pieces: r.pieces })}`',
      {"sprites.sp1_sk.retires": ("{os} os et {pieces} pièce(s) retirés", "{os} bone(s) and {pieces} part(s) removed")}),
    S("spritelab/spritelab.js", 55, '<button title="Supprimer">', '<button title="${dzT("sprites.sp1_x.supprimer")}">', {"sprites.sp1_x.supprimer": ("Supprimer", "Delete")}),
    S("spritelab/spritelab.js", 60, "'Les ' + n + ' images'", 'dzT("sprites.sp1_f.les_n", { n: n })', {"sprites.sp1_f.les_n": ("Les {n} images", "The {n} frames")}),
    X("spritelab/spritelab.js", 70, '"boucle"', "valeur stockée/comparée, pas affichée"),
    H("sprites.sph_page.titre", "Spritelab — planches", "Spritelab — sheets"),
]
```
- `fichier` relatif à `frontend/` ; `ligne` = numéro de ligne (1-based) dans la source actuelle (= la BASE 7f99c72c :
  les sources n'ont pas changé).
- `L` : un littéral SIMPLE ("…" '…' ou `…` SANS ${}) entier, guillemets compris, qui devient `dzT("clé")`. `fr` =
  EXACTEMENT le contenu du littéral (entités HTML `&#183;` telles quelles). `n` = occurrences identiques commençant
  sur la ligne (toutes remplacées), défaut 1.
- `S` : remplacement exact (`avant` → `apres`) pour les gabarits `${}`, le HTML dans une chaîne, les CONCATÉNATIONS
  (une phrase coupée en morceaux devient UNE clé à variables, l'`avant` couvre toute l'expression, même sur plusieurs
  lignes), les pluriels (`.un` / `.plusieurs` choisis par le code). Dans un gabarit `…`, un texte devient
  `${dzT("clé")}` ; dans du code, `dzT("clé", { n })`. Les sources sont en CRLF : un saut de ligne réel dans
  `avant`/`apres` s'écrit `\r\n`. Les clés d'un `apres` s'écrivent `dzT("clé"` (guillemets doubles, juste après la
  parenthèse) : c'est ce motif que le générateur reconnaît.
- `X` : littéral d'allure française GARDÉ, avec sa raison.
- `H(clé, fr, en)` : seulement pour les pages `.html` (JAMAIS modifiées : la surcouche du runtime traduit à
  l'affichage le texte EXACT — espaces normalisés — d'un nœud texte ou d'un attribut title/placeholder/aria-label/alt).
  Un nœud qui mêle texte et balises (`Durée <b>3 s</b>`) se traduit nœud texte par nœud texte. La surcouche
  n'entre PAS dans `<select>`/`<option>` : fais quand même les H des `<option>` et liste-les dans ta réponse
  (l'intégration ajoutera une passe au démarrage). Un texte posé dans une page par un script qui n'est PAS dans la
  liste des fichiers du générateur se traite aussi par H (texte exact affiché).

## Ce qui ne se traduit PAS (X)
- Le CONTENU de l'utilisateur et ce qui part au serveur : prompts envoyés aux générateurs (image, vidéo, 3D, LLM —
  ex. les prompts anglais de directions.js), noms de fichiers, valeurs enregistrées, corps de requêtes, métadonnées
  écrites dans un fichier exporté (JSON Tiled/LDtk/Godot, .tres, GLB, Spine, zip), noms de sections/tags/animations
  saisis par l'utilisateur.
- Ids, clés de stockage (localStorage), `data-*`, classes CSS, valeurs comparées (`mode === "boucle"`), types MIME,
  noms de polices, unités seules, formats, noms de modèles, de moteurs et de fournisseurs (fal, Meshy, Tiled, LDtk,
  Godot, Unity, Spine…), noms propres de palettes (Game Boy, Sweetie 16…).
- Messages de `console.*`.
- Les messages d'erreur RENVOYÉS PAR LE SERVEUR (`d.detail`) : ils seront traduits côté backend (lot L10).
Les `throw new Error("…")` écrits dans le lab dont le message est montré à l'utilisateur (toast, statut) se traduisent ;
un `confirm`/`alert`/`__dzDialogue`/`toast` aussi. ATTENTION : un message d'erreur dont un AUTRE code compare le texte
(`e.message === "…"`, `.includes("…")`, `startsWith`) — vérifie avant de traduire, et garde la comparaison cohérente.

## Les règles
- Clés en ASCII minuscule, chiffres, `_`, points.
- `en` : anglais d'interface, court ; impératif pour un bouton ; phrase d'aide naturelle, pas de calque ; vocabulaire
  usuel du domaine (Spritelab : sprite sheet, frame, cell, tag, loop, ping-pong, hitbox, hurtbox, pivot, bone, part,
  onion skin, palette, outline ; Tile Lab : tileset, tile, autotile, blob, terrain, variant, level painter, collision ;
  Studio3D : model, mesh, texture, rig, LOD, views, turntable ; Plateau : camera, shot, keyframe, focal length, sensor,
  dolly, orbit). Garde ponctuation, espaces de bord, `…`, balises HTML, emojis.
  Raccourcis : « Maj » → « Shift », « Suppr » → « Del », « Échap » → « Esc », « Entrée » → « Enter ».
- Le lab tutoie en français (« choisis une tuile ») : l'anglais est neutre (« pick a tile »).
- Variables `{x}` identiques en fr et en.
- Un même français a UNE traduction dans TOUS les dictionnaires (`frontend/shared/i18n/*.json`) : si le générateur dit
  « est traduit X, mais Y par … », reprends Y, sauf sens vraiment différent → `contexte=True` (argument de L/H, ou
  3e élément `"contexte"` dans le tuple du dico de S). Les textes TRÈS courts et ambigus (« Face », « Carte »,
  « Relief », « Plan », « Os », « Pièce ») : `contexte=True` (la surcouche les ignore alors, la clé sert seulement à dzT).

## Valider (obligatoire, autant de fois que nécessaire)
```
cd C:\Users\olivi\DeepotusVideo\.claude\worktrees\i18n-l9
PYTHONIOENCODING=utf-8 python scripts/i18n_l9_generer.py --seul <groupe> > %TEMP%\l9_<groupe>.txt
```
(rediriger dans un fichier puis le lire : la console Windows refuse certains caractères.) Il refuse une saisie fausse
et liste les RESTES de ta plage. **Objectif : 0 reste.** Le contrôle est une heuristique : traduis aussi les textes
français qu'il ne voit pas (sans accent ni mot courant, mots seuls en minuscules ou en CAPITALES, `textContent =`,
`innerHTML`, `title`, `placeholder`, `aria-label`) — relis ta plage EN ENTIER.

Syntaxe JS : le générateur ne vérifie pas en --seul. Construis la sortie en mémoire et vérifie-la avec node sans rien
écrire dans le dépôt (script classique : `node --check f.js` ; module ES : copie-le en `.mjs` puis
`node --check f.mjs`) :
```python
import sys; sys.path.insert(0, "scripts"); import i18n_l9_generer as G
G.SEUL = "<groupe>"; E = [e for e in G.entrees() if e["groupe"] == "<groupe>"]
textes, neufs, table, dico, gardes, fichiers = G.construire(E)
# écrire neufs["spritelab/spritelab.js"] dans ton dossier temporaire (%TEMP%), puis : node --check <ce fichier>
```
N'écris RIEN dans `frontend/` ni ailleurs dans le dépôt hors de ton fichier de saisie.

## À la fin
Réponds en quelques lignes : nombre d'entrées L/S/X/H, clés, restes (doit être 0), syntaxe vérifiée, choix délicats
(contenu gardé, pluriels, messages comparés), les `<option>` signalées, et ce que tu n'as pas pu traiter.
