# Inventaire des icônes DeepotusVideo — consigne commune

But : recenser TOUTES les icônes visibles de l'application (pour ensuite redessiner une suite cohérente).
Racine du code (lecture seule, NE RIEN MODIFIER) : `C:\Users\olivi\DeepotusVideo\.claude\worktrees\icones-inventaire`
L'UI réelle de la coque React est le bundle PATCHÉ `frontend/dist/assets/index-BEOJX8L5.js` (2,5 Mo minifié, JSX compilé en `r.jsx("path",{d:...})` / `r.jsxs`). `frontend/src` est un vieux source v1.15 : NE PAS s'en servir comme vérité (seulement pour comprendre un nom).
Les labs sont en vanilla JS sous `frontend/<lab>/`.

## Ce qui compte comme « icône »
Tout pictogramme montré à l'utilisateur : SVG inline, carte d'icônes (dictionnaire nom → tracé), fichier .svg/.png/.ico, emoji utilisé comme icône de bouton/onglet/menu/titre, glyphe Unicode utilisé comme pictogramme (▶ ⏸ ✕ ⟲ ↻ ⚙ ★ ● ▾ › …), police d'icônes. PAS : le texte ordinaire, les illustrations/photos de contenu, les miniatures générées.

## Livrable : UN fichier JSON (UTF-8) à l'emplacement indiqué dans ta mission
Tableau d'objets, UNE ENTRÉE PAR USAGE (une même icône utilisée à 3 endroits = 3 entrées avec le même `cle_visuelle`) :
```json
{
  "id": "zone.ecran.slug-unique",
  "zone": "Coque | Studio | Quick | ... | Vectorlab | Photolab | ...",
  "ecran": "écran / panneau précis",
  "emplacement": "où exactement (barre latérale gauche, barre d'outils, menu contextuel du calque, bouton à droite du titre…)",
  "libelle": "texte visible, title= ou aria-label associé (tel quel), ou \"\"",
  "fonction": "ce que ça PRODUIT / déclenche quand on l'utilise, ou ce que ça signale (une phrase claire, en français)",
  "role": "navigation | action | outil | etat | categorie | media | fichier | edition | lecture | reglage | aide | marque | decor",
  "type": "svg | emoji | glyphe | image | police",
  "cle_visuelle": "nom court partagé par toutes les entrées qui affichent le MÊME dessin (ex. 'caret', 'zap', 'emoji-🎬')",
  "rendu": "SVG AUTONOME complet (<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" ...>…</svg>) avec fill/stroke en currentColor, OU le caractère emoji/glyphe, OU le chemin relatif à la racine du dépôt pour une image",
  "style": "ex. 'plein bicolore (opacity .34)', 'trait 1.6 px', 'trait 2 px lucide', 'emoji couleur', 'glyphe texte'",
  "source": "chemin/relatif:ligne (pour le bundle : offset caractère ou une sous-chaîne unique trouvable)",
  "notes": "doublons, incohérences (même fonction / dessins différents, même dessin / fonctions différentes), icône manquante (bouton texte seul qui mériterait une icône → mettre type \"aucune\" et rendu \"\")"
}
```
Règles :
- `rendu` SVG : reconstitue un SVG valide et autonome. Pour le bundle, convertis les appels `r.jsx/r.jsxs` en balises (camelCase → kebab : strokeWidth→stroke-width, strokeLinecap→stroke-linecap, fillRule→fill-rule…). Méthode conseillée : extraire le littéral d'objet par équilibrage d'accolades (jamais par regex gloutonne), puis l'évaluer sous `node` avec un faux `r={jsx:(t,p)=>…,jsxs:…}` qui sérialise en chaîne. Vérifie que chaque SVG produit se parse (ex. via un parseur XML node simple ou en comptant les balises).
- Les SVG doivent rester fidèles (ne pas redessiner). Si l'icône est définie en `innerHTML` d'une chaîne, recopie-la.
- Sois EXHAUSTIF sur ta zone : parcours tous les fichiers, toutes les barres d'outils, menus, onglets, boutons, badges d'état. Mieux vaut 300 entrées justes que 60 approximatives.
- Pour `fonction`, lis le gestionnaire (onClick / addEventListener / data-action / commande) — ne devine pas d'après le nom.
- Inclure aussi les boutons SANS icône mais qui sont des actions majeures (type "aucune") : utile pour la future suite. Limite-toi aux actions principales (barres d'outils, en-têtes), pas chaque champ de formulaire.
- Termine en écrivant le fichier, puis valide qu'il se charge avec `node -e "JSON.parse(require('fs').readFileSync(F,'utf8'))"`.
- Ta réponse finale (courte) : nombre d'entrées, nombre de `cle_visuelle` distinctes, 5 incohérences les plus frappantes, zones éventuellement non couvertes.
