# Traduction L6 (t146) — consigne de saisie pour un groupe de fichiers du Vectorlab

Tu écris UN fichier de saisie : `scripts/i18n_l6/<groupe>.py` (le nom du groupe t'est donné). Tu ne modifies
AUCUN autre fichier (ni les sources du Vectorlab, ni le générateur, ni la saisie des autres groupes — d'autres agents
travaillent en parallèle dans le même dossier). Dossier de travail :
`C:\Users\olivi\DeepotusVideo\.claude\worktrees\i18n-l6`.

## Le but
Le Vectorlab (lab statique, `frontend/vectorlab/`) est en français. L'interface doit pouvoir s'afficher en anglais.
Chaque texte AFFICHÉ des fichiers de ton groupe passe par `T("vectorlab.<zone>.<role>")` (fonction importée de
`./mod-i18n.js` — l'import est ajouté AUTOMATIQUEMENT par le générateur, ne l'écris pas). Le français reste la
langue de référence : la clé a son texte `fr` (copié tel quel du code) et son `en`.

## Le format (lis `scripts/i18n_l6/outils.py`, et l'exemple `scripts/i18n_l6/statut.py`)
```python
"""t146 — <groupe> : ce que couvrent ces fichiers, et ce qui est GARDÉ et pourquoi (en résumé)."""
from outils import L, S, X, H

ENTREES = [
    L("js/mod-x.js", 12, '"Nouveau calque"', "vectorlab.calques.nouveau", "Nouveau calque", "New layer"),
    S("js/mod-x.js", 40, '`${n} calques`', 'T("vectorlab.calques.n", { n })', {"vectorlab.calques.n": ("{n} calques", "{n} layers")}),
    S("js/mod-x.js", 55, '<button title="Supprimer">', '<button title="${T("vectorlab.calques.supprimer")}">', {"vectorlab.calques.supprimer": ("Supprimer", "Delete")}),
    X("js/mod-x.js", 70, '"select"', "id d'outil comparé, pas affiché"),
]
```
- `fichier` relatif à `frontend/vectorlab/` ; `ligne` = numéro de ligne (1-based) dans la source ACTUELLE du fichier
  (identique à la BASE e7fb1ac1 : les sources n'ont pas changé, sauf `js/mod-statut.js` déjà fait — ne le touche pas).
- `L` : un littéral SIMPLE ("…" '…' ou `…` SANS ${}) entier, guillemets compris, qui devient `T("clé")`. Le `fr`
  doit être EXACTEMENT le contenu du littéral. `n` = nombre d'occurrences identiques COMMENÇANT sur cette ligne
  (toutes remplacées) — défaut 1.
- `S` : remplacement exact de code (`avant` → `apres`), pour les gabarits `${}`, le HTML dans une chaîne, les
  concaténations, les pluriels. Garde l'`avant` court mais unique sur sa ligne. Dans un gabarit HTML (`…`), un
  texte devient `${T("clé")}` ; dans du code, `T("clé", { n })`. Pluriel : deux clés `.un` / `.plusieurs`, choisies
  par le code (`T(n > 1 ? "…plusieurs" : "…un", { n })`). Si `apres` contient un retour de ligne, écris `\r\n`.
- `X` : littéral d'allure française GARDÉ, avec sa raison : id, nom d'outil interne, clé de stockage, valeur envoyée
  au serveur ou écrite dans le document (.vlab/SVG/JSON), valeur COMPARÉE (`=== "Calque"`), nom propre, nom de
  police, unité, regex, sélecteur CSS, texte identique dans les deux langues, commentaire dans une chaîne.
- `H(clé, fr, en)` : seulement pour `index.html` (dont le texte n'est PAS modifié : la surcouche du runtime le traduit
  à l'affichage par correspondance EXACTE du texte, espaces normalisés, nœuds texte et attributs title/placeholder/
  aria-label). Le `fr` = le texte exact du nœud ou de l'attribut.

## Les règles
- Clés : `vectorlab.<zone>.<role>`, ASCII minuscule, chiffres, `_` ; ta ZONE est imposée (on te la donne) — n'utilise
  QUE tes zones (deux groupes ne doivent pas créer la même clé).
- `en` : anglais d'interface, court ; impératif pour un bouton (« Exporter » → « Export ») ; phrase d'aide naturelle,
  pas de calque mot à mot ; termes d'Affinity/Illustrator en anglais (Layers, Swatches, Stroke, Fill, Artboard,
  Boolean, Node tool, Pen tool, Corner, Pixel persona…). Garde la ponctuation et les espaces de bord (`" · "`),
  les `…`, les `**gras**`, les raccourcis (Ctrl+Z ; « Maj » → « Shift », « Suppr » → « Del », « Échap » → « Esc »,
  « Entrée » → « Enter », « Espace » → « Space »).
- Variables `{x}` identiques en fr et en.
- Un même texte français n'a qu'UNE traduction dans TOUS les dictionnaires (`frontend/shared/i18n/*.json`). Si le
  générateur dit « est traduit X, mais Y par … », reprends Y — sauf si le sens diffère vraiment ici : alors
  `contexte=True` (argument de L/H, ou 3e élément `"contexte"` dans le tuple du dico de S).
- Ne traduis JAMAIS ce qui n'est pas affiché : ids, `data-*`, noms de classes, clés de localStorage, valeurs du
  document, messages de `console.*`, textes envoyés au serveur (prompts d'IA compris, SAUF un texte d'exemple
  affiché que l'utilisateur copie lui-même), valeurs comparées. Dans le doute, lis le code autour.
- Les `throw new Error("…")` dont le message est AFFICHÉ à l'utilisateur (attrapé puis montré) se traduisent ;
  ceux qui ne le sont jamais : X.
- Les commentaires ne sont jamais des littéraux (le contrôle les ignore).

## Valider (obligatoire, autant de fois que nécessaire)
```
cd C:\Users\olivi\DeepotusVideo\.claude\worktrees\i18n-l6
set PYTHONIOENCODING=utf-8 && python scripts/i18n_l6_generer.py --seul <groupe>
```
(sous bash : `PYTHONIOENCODING=utf-8 python scripts/i18n_l6_generer.py --seul <groupe>`). Il refuse une saisie
fausse (ligne, littéral introuvable, fr ≠ littéral, conflit de traduction…) et liste les RESTES : littéraux d'allure
française encore en dur dans tes fichiers. **Objectif : 0 reste** (chaque reste est traduit, ou gardé par X avec sa
raison). Le contrôle est une heuristique : un reste qui n'est pas du français (« Inter », un nom de fonte) se garde
par X ; un texte français qu'il ne voit pas (sans accent ni mot courant, ex. « Contour », « Remplissage ») doit
quand même être traduit — relis tes fichiers EN ENTIER, ne te fie pas qu'aux restes.

Vérifie aussi la syntaxe JS des fichiers produits SANS rien écrire sur disque : le générateur ne t'y aide pas en
--seul ; relis chaque `apres` (guillemets, `${}` seulement dans un gabarit, virgules).

## À la fin
Réponds en quelques lignes : nombre d'entrées L/S/X/H, clés créées, restes (doit être 0), les choix délicats
(valeurs gardées, pluriels, textes d'IA), et tout ce que tu n'as pas pu traiter.
