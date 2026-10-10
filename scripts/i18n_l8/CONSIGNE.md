# Traduction L8 (t148) — consigne de saisie pour un groupe (Atelier, Material Forge, Établi)

Tu écris UN fichier de saisie : `scripts/i18n_l8/<groupe>.py` (le nom t'est donné). Tu ne modifies AUCUN autre fichier
(ni les sources des labs, ni le générateur, ni la saisie des autres groupes : d'autres agents travaillent en parallèle
dans le même dossier). Dossier de travail : `C:\Users\olivi\DeepotusVideo\.claude\worktrees\i18n-l8`.

## Le but
Trois labs statiques de DeepotusVideo sont en français ; leur interface doit pouvoir s'afficher en anglais :
- `frontend/atelier/` — l'Atelier (chapitres : script → entités → bible, scénario, storyboard, voix) ; `atelier.js`
  est un script CLASSIQUE ;
- `frontend/materialforge/` — le Material Forge (matières PBR : maps, raccord, coûts) ; `materialforge.js` CLASSIQUE ;
- `frontend/etabli/` — l'Établi (inspecteur 3D, impression 3D) ; `etabli.js` et `aide.js` sont des MODULES ES.
Tous sont chargés APRÈS `/shared/dz-i18n.js` : chaque texte AFFICHÉ de ta plage passe par `dzT("<zone>.<sous>.<role>")`
(fonction GLOBALE du runtime : rien à importer, même dans un module). Le français reste la langue de référence : la
clé a son `fr` (copié tel quel du code) et son `en`.

Préfixe de clé imposé par le lab : `atelier.` pour frontend/atelier, `matiere.` pour frontend/materialforge,
`etabli.` pour frontend/etabli (le générateur refuse une clé d'un autre lab). Les sous-zones sont libres mais
PRÉFIXÉES par l'abréviation de ton groupe que l'on te donne (ex. groupe `at1` → `atelier.at1_bible.titre`) pour
qu'aucun autre agent n'écrive la même clé.

## Le format (lis `scripts/i18n_l8/outils.py`)
```python
"""t148 — <groupe> : ce que couvre ta plage, ce qui est GARDÉ et pourquoi (en résumé)."""
from outils import L, S, X, H

PLAGES = {"atelier/atelier.js": (1, 750)}      # chaque entrée doit COMMENCER dans ta plage

ENTREES = [
    L("atelier/atelier.js", 12, '"Nouveau chapitre"', "atelier.at1_chap.nouveau", "Nouveau chapitre", "New chapter"),
    S("atelier/atelier.js", 40, '`${n} scènes`', 'dzT("atelier.at1_sc.n", { n })', {"atelier.at1_sc.n": ("{n} scènes", "{n} scenes")}),
    S("atelier/atelier.js", 55, '<button title="Supprimer">', '<button title="${dzT("atelier.at1_x.supprimer")}">', {"atelier.at1_x.supprimer": ("Supprimer", "Delete")}),
    S("atelier/atelier.js", 60, "'Les ' + n + ' plans'", 'dzT("atelier.at1_sb.les_n", { n: n })', {"atelier.at1_sb.les_n": ("Les {n} plans", "The {n} shots")}),
    X("atelier/atelier.js", 70, '"personnage"', "valeur stockée, pas affichée"),
    H("atelier.ath_page.titre", "Atelier — chapitres", "Workshop — chapters"),
]
```
- `fichier` relatif à `frontend/` ; `ligne` = numéro de ligne (1-based) dans la source actuelle (= la BASE 1515d67b :
  les sources n'ont pas changé).
- `L` : un littéral SIMPLE ("…" '…' ou `…` SANS ${}) entier, guillemets compris, qui devient `dzT("clé")`. `fr` =
  EXACTEMENT le contenu du littéral (entités HTML `&#183;` telles quelles). `n` = occurrences identiques commençant
  sur la ligne (toutes remplacées), défaut 1.
- `S` : remplacement exact (`avant` → `apres`) pour les gabarits `${}`, le HTML dans une chaîne, les CONCATÉNATIONS
  (une phrase coupée en morceaux devient UNE clé à variables, l'`avant` couvre toute l'expression, même sur plusieurs
  lignes), les pluriels (`.un` / `.plusieurs` choisis par le code). Dans un gabarit `…`, un texte devient
  `${dzT("clé")}` ; dans du code, `dzT("clé", { n })`. Les sources sont en CRLF : un saut de ligne réel dans
  `avant`/`apres` s'écrit `\r\n`.
- `X` : littéral d'allure française GARDÉ, avec sa raison.
- `H(clé, fr, en)` : seulement pour les pages `.html` (JAMAIS modifiées : la surcouche du runtime traduit à
  l'affichage le texte EXACT — espaces normalisés — d'un nœud texte ou d'un attribut title/placeholder/aria-label/alt).
  Un nœud qui mêle texte et balises (`Durée <b>3 s</b>`) se traduit nœud texte par nœud texte. La surcouche
  n'entre PAS dans `<select>`/`<option>` : fais quand même les H des `<option>` et liste-les dans ta réponse
  (l'intégration ajoutera une passe au démarrage). Le texte posé par le script INLINE d'une page html (preview.html)
  se traite aussi par H (texte exact affiché).

## Ce qui ne se traduit PAS (X)
- Le CONTENU de l'utilisateur et ce qui part au serveur : prompts envoyés aux générateurs (image, vidéo, LLM, TTS),
  textes de script/chapitre/entités, noms de matières ou de fichiers, valeurs enregistrées, corps de requêtes,
  métadonnées écrites dans un GLB/fichier exporté, noms de fichiers.
- Ids, clés de stockage (localStorage), `data-*`, classes CSS, valeurs comparées (`kind === "personnage"`), types MIME,
  noms de polices, unités seules, formats, noms de modèles et de fournisseurs (fal, Meshy, ElevenLabs…).
- Messages de `console.*`.
- Les messages d'erreur RENVOYÉS PAR LE SERVEUR (`d.detail`) : ils seront traduits côté backend (lot L10).
Les `throw new Error("…")` écrits dans le lab dont le message est montré à l'utilisateur se traduisent ; un
`confirm`/`alert`/`__dzDialogue` aussi.

Établi, `aide.js` : le LEXIQUE (titre + texte de chaque terme) se traduit. Le guide anglais existe déjà :
`docs/guide/en.html`, ancres `id="lex-<clé>"` — reprends SON terme et sa phrase anglaise pour chaque clé (cohérence
écran/guide). Les CLÉS de `LEXIQUE` (assise, surplomb…) ne changent pas.

## Les règles
- Clés en ASCII minuscule, chiffres, `_`, points.
- `en` : anglais d'interface, court ; impératif pour un bouton ; phrase d'aide naturelle, pas de calque ; vocabulaire
  usuel du domaine (Atelier : chapter, script, screenplay, storyboard, shot, scene, cast, bible, voice-over ;
  Material Forge : material, map, albedo/base color, normal, roughness, metalness, height, AO, ORM, seamless/tiling,
  seam score ; Établi : bed, overhang, support, brim, raft, infill, wall, layer height, slicer, mesh, manifold,
  decimate, hollow, drain hole, rig, bone). Garde ponctuation, espaces de bord, `…`, balises HTML, emojis.
  Raccourcis : « Maj » → « Shift », « Suppr » → « Del », « Échap » → « Esc », « Entrée » → « Enter ».
- Variables `{x}` identiques en fr et en.
- Un même français a UNE traduction dans TOUS les dictionnaires (`frontend/shared/i18n/*.json`) : si le générateur dit
  « est traduit X, mais Y par … », reprends Y, sauf sens vraiment différent → `contexte=True` (argument de L/H, ou
  3e élément `"contexte"` dans le tuple du dico de S). Les textes TRÈS courts et ambigus (« Face », « Carte »,
  « Relief », « Plan ») : `contexte=True` sur une clé L/S (la surcouche les ignore alors, la clé sert seulement à dzT).

## Valider (obligatoire, autant de fois que nécessaire)
```
cd C:\Users\olivi\DeepotusVideo\.claude\worktrees\i18n-l8
PYTHONIOENCODING=utf-8 python scripts/i18n_l8_generer.py --seul <groupe> > %TEMP%\l8_<groupe>.txt
```
(rediriger dans un fichier puis le lire : la console Windows refuse certains caractères.) Il refuse une saisie fausse
et liste les RESTES de ta plage. **Objectif : 0 reste.** Le contrôle est une heuristique : traduis aussi les textes
français qu'il ne voit pas (sans accent ni mot courant) — relis ta plage EN ENTIER.

Syntaxe JS : le générateur ne vérifie pas en --seul. Construis la sortie en mémoire et vérifie-la avec node sans rien
écrire dans le dépôt (atelier.js / materialforge.js : `node --check f.js` ; etabli.js / aide.js sont des modules :
copie-les en `.mjs` puis `node --check f.mjs`) :
```python
import sys; sys.path.insert(0, "scripts"); import i18n_l8_generer as G
G.SEUL = "<groupe>"; E = [e for e in G.entrees() if e["groupe"] == "<groupe>"]
textes, neufs, table, dico, gardes, fichiers = G.construire(E)
# écrire neufs["atelier/atelier.js"] dans ton dossier temporaire, puis : node --check <ce fichier>
```

## À la fin
Réponds en quelques lignes : nombre d'entrées L/S/X/H, clés, restes (doit être 0), syntaxe vérifiée, choix délicats
(contenu gardé, pluriels, messages), les `<option>` signalées, et ce que tu n'as pas pu traiter.
