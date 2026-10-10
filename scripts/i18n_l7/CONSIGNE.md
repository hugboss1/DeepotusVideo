# Traduction L7 (t147) — consigne de saisie pour un groupe du Card Forge

Tu écris UN fichier de saisie : `scripts/i18n_l7/<groupe>.py` (le nom t'est donné). Tu ne modifies AUCUN autre fichier
(ni les sources du Card Forge, ni le générateur, ni la saisie des autres groupes : d'autres agents travaillent en
parallèle dans le même dossier). Dossier de travail : `C:\Users\olivi\DeepotusVideo\.claude\worktrees\i18n-l7`.

## Le but
Le Card Forge (`frontend/cardforge/`, scripts CLASSIQUES chargés après le runtime `/shared/dz-i18n.js`) est en
français. L'interface doit pouvoir s'afficher en anglais. Chaque texte AFFICHÉ de ta plage passe par
`dzT("cartes.<zone>.<role>")` (fonction GLOBALE du runtime : rien à importer). Le français reste la langue de
référence : la clé a son `fr` (copié tel quel du code) et son `en`.

## Le format (lis `scripts/i18n_l7/outils.py`)
```python
"""t147 — <groupe> : ce que couvre ta plage, ce qui est GARDÉ et pourquoi (en résumé)."""
from outils import L, S, X, H

PLAGES = {"js/mod-type.js": (3994, 5179)}      # SEULEMENT si on te donne une plage : chaque entrée doit COMMENCER dedans

ENTREES = [
    L("js/mod-x.js", 12, '"Nouveau calque"', "cartes.x.nouveau", "Nouveau calque", "New layer"),
    S("js/mod-x.js", 40, '`${n} cartes`', 'dzT("cartes.x.n", { n })', {"cartes.x.n": ("{n} cartes", "{n} cards")}),
    S("js/mod-x.js", 55, '<button title="Supprimer">', '<button title="${dzT("cartes.x.supprimer")}">', {"cartes.x.supprimer": ("Supprimer", "Delete")}),
    S("js/mod-x.js", 60, "'Les ' + n + ' cartes'", 'dzT("cartes.x.les_n", { n: n })', {"cartes.x.les_n": ("Les {n} cartes", "The {n} cards")}),
    X("js/mod-x.js", 70, '"recto"', "id de face comparé, pas affiché"),
]
```
- `fichier` relatif à `frontend/cardforge/` ; `ligne` = numéro de ligne (1-based) dans la source actuelle (= la BASE
  f788790b : les sources n'ont pas changé).
- `L` : un littéral SIMPLE ("…" '…' ou `…` SANS ${}) entier, guillemets compris, qui devient `dzT("clé")`. `fr` =
  EXACTEMENT le contenu du littéral (les entités HTML `&#183;` telles quelles). `n` = occurrences identiques
  commençant sur la ligne (toutes remplacées), défaut 1.
- `S` : remplacement exact (`avant` → `apres`) pour les gabarits `${}`, le HTML dans une chaîne, les
  CONCATÉNATIONS (très nombreuses ici : `'… ' + x + ' mm …'` — une phrase coupée en morceaux devient UNE clé à
  variables, l'`avant` couvre toute l'expression, même sur plusieurs lignes), les pluriels (`.un` / `.plusieurs`
  choisis par le code). Dans un gabarit `…`, un texte devient `${dzT("clé")}` ; dans du code, `dzT("clé", { n })`.
  Un `\r\n` réel dans `avant`/`apres` s'écrit `\r\n` (les sources sont en CRLF).
- `X` : littéral d'allure française GARDÉ, avec sa raison.
- `H(clé, fr, en)` : seulement pour `index.html` (non modifié : la surcouche traduit le texte EXACT d'un nœud ou d'un
  attribut title/placeholder/aria-label ; JAMAIS dans un `<select>`/`<option>` — signale-les).

## Ce qui ne se traduit PAS (X) — propre au Card Forge
- Le CONTENU des cartes et des jeux : textes de carte, noms de cartes, colonnes et valeurs CSV, données d'exemple
  écrites dans un projet, langues des cartes (le Card Forge a déjà une fonction « langues » pour le contenu, distincte
  de la langue de l'interface).
- Les prompts envoyés aux générateurs d'images ou au LLM (art, styles), et tout texte envoyé au serveur ou écrit
  dans un fichier exporté (PDF, glTF, STL, SVG, JSON, métadonnées d'impression, noms de fichiers).
- Ids, clés de stockage, `data-*`, classes CSS, valeurs comparées, noms de polices, unités seules, formats.
- Messages de `console.*` et gardes de chargement (« mod-x: js/core.js doit etre charge avant ce fichier »).
Les `throw new Error("…")` dont le message est montré à l'utilisateur (attrapé puis affiché) se traduisent.

## Les règles
- Clés `cartes.<zone>.<role>` en ASCII minuscule, chiffres, `_` ; UNIQUEMENT tes zones (on te les donne).
- `en` : anglais d'interface, court ; impératif pour un bouton ; phrase d'aide naturelle, pas de calque mot à mot ;
  vocabulaire d'impression et de jeu de cartes usuel (bleed, safe zone, trim, cut line, card back, frame, gem, art
  box, foil, deck, print sheet, DPI, CMYK, ICC). Garde ponctuation, espaces de bord, `…`, balises HTML.
  Raccourcis : « Maj » → « Shift », « Suppr » → « Del », « Échap » → « Esc », « Entrée » → « Enter ».
- Variables `{x}` identiques en fr et en.
- Un même français a UNE traduction dans TOUS les dictionnaires (`frontend/shared/i18n/*.json`) : si le générateur dit
  « est traduit X, mais Y par … », reprends Y, sauf sens vraiment différent → `contexte=True` (argument de L/H, ou
  3e élément `"contexte"` dans le tuple du dico de S).

## Valider (obligatoire, autant de fois que nécessaire)
```
cd C:\Users\olivi\DeepotusVideo\.claude\worktrees\i18n-l7
PYTHONIOENCODING=utf-8 python scripts/i18n_l7_generer.py --seul <groupe>
```
Il refuse une saisie fausse et liste les RESTES de ta plage. **Objectif : 0 reste.** Le contrôle est une heuristique :
traduis aussi les textes français qu'il ne voit pas (sans accent ni mot courant) — relis ta plage EN ENTIER.

Syntaxe JS : le générateur ne vérifie pas en --seul. Construis la sortie en mémoire et vérifie-la avec node sans
rien écrire dans le dépôt (exemple ci-dessous, à lancer depuis le dossier de travail) :
```python
import sys; sys.path.insert(0, "scripts"); import i18n_l7_generer as G
G.SEUL = "<groupe>"; E = [e for e in G.entrees() if e["groupe"] == "<groupe>"]
textes, neufs, table, dico, gardes, fichiers = G.construire(E)
# écrire neufs["js/mod-x.js"] dans ton scratchpad, puis : node --check <ce fichier>
```

## À la fin
Réponds en quelques lignes : nombre d'entrées L/S/X/H, clés, restes (doit être 0), syntaxe vérifiée, choix délicats
(contenu de carte gardé, pluriels, messages), et ce que tu n'as pas pu traiter.
