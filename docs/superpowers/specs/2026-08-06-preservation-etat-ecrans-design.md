# Préservation de l'état des écrans à la navigation

> Conception validée le 6 août 2026. Cible : bundle compilé
> `frontend/dist/assets/index-BEOJX8L5.js` (patché chirurgicalement, jamais
> recompilé).

## Problème

Changer d'écran détruit le travail en cours. Le commutateur du composant
racine `lg` est un tableau plat de 11 emplacements de la forme
`s==="studio" && r.jsx(Lh,…)` : un écran inactif vaut `false`, donc React
démonte intégralement son arbre. Construire un graphe dans Studio, aller à la
Bibliothèque et revenir rend un canvas vide.

Le dépôt affiche pourtant le principe inverse — `PRODUCT.md`, principe 5 :
« Jamais perdre un brouillon ». Aucune persistance d'état de travail n'existe
aujourd'hui : les 18 clés `localStorage` du bundle ne stockent que des
préférences (rail replié, thème, favoris, modèle choisi).

## Portée retenue

**En session uniquement.** Le travail survit à toute navigation tant que
l'application reste ouverte. Fermer l'application perd le non-sauvegardé,
comme aujourd'hui.

Conséquence directe : l'état est conservé **en mémoire**, pas sur disque. Cela
évite la sérialisation d'objets non sérialisables, et surtout le problème des
brouillons périmés restaurés au démarrage suivant (une timeline qui référence
un rendu supprimé entre-temps).

## Décision d'architecture

### Rejeté : garder les écrans montés

Un patch d'une seule expression (11 substitutions, `display:contents` /
`display:none`) couvrirait tous les écrans d'un coup. Rejeté à cause d'effets
de bord vérifiés dans le code, dont un destructeur :

| Effet | Preuve |
|---|---|
| **`Alt+C` détruit des données depuis n'importe quel écran** | `DzMontage` enregistre `keydown` sur `window` à son montage ; resté monté, la lame découpe un clip et met `dirty` alors que l'utilisateur est ailleurs |
| La touche `/` avale les frappes | Le dock Studio se garde par la présence de `.dz-studio-grid` dans le DOM, pas par l'écran actif |
| 5 sondages réseau permanents | Game Assets 4 s, Bibliothèque 8 s, Réglages 10 s, Scheduler 8 s et 60 s — s'ajoutant aux 4 pollers globaux existants |
| Audio et WebGL maintenus | `AudioContext` de Son & VFX jamais fermé ; `<model-viewer>` de Game Assets ; un aperçu Montage en lecture continuerait à jouer son son |

Rendre l'approche sûre demanderait 6 à 8 patches supplémentaires, ce qui
annule son seul avantage. Dans un bundle non recompilable, changer le modèle
d'exécution de toute l'application est un risque disproportionné.

### Retenu : conservateur d'état en mémoire, par écran

Un objet global unique, injecté une fois en préambule du bundle. Chaque écran
y dépose son état de travail et le relit à son montage.

```js
// injecté une fois, avant tout composant
window.__dzKeep = window.__dzKeep || {
  s: {},
  get(k, d) { return k in this.s ? this.s[k] : d },
  set(k, v) { this.s[k] = v; return v },
  drop(k) { delete this.s[k] }
};
```

Usage dans un écran, par état à préserver :

```js
// initialiseur : reprend la valeur conservée, sinon la valeur d'origine
const [zoom, setZoom] = x.useState(() => __dzKeep.get("studio.zoom", .75));
// miroir : à chaque changement
x.useEffect(() => { __dzKeep.set("studio.zoom", zoom) }, [zoom]);
```

**Aucun cycle de vie n'est modifié.** Les écrans continuent de se démonter :
les sondages s'arrêtent, les raccourcis se désenregistrent, l'audio se coupe,
les contextes WebGL sont libérés. Seul le contenu revient.

**Convention de clé** : `<écran>.<état>` — `studio.graph`, `montage.clips`.
Espace de noms plat, lisible dans la console pendant le débogage.

## Étapes

Chaque étape est un patcher idempotent indépendant, testable et réversible.

### 1. Studio

L'écran de la plainte initiale. Le code recopie déjà le graphe courant dans un
global `__dzG` (déclaré offset ~188452, affecté ~282730) **qui survit au
démontage** : la restauration tient en une expression.

| État | Ancre | Modification |
|---|---|---|
| Graphe | `return ts(structuredClone(Zi[n]))` | `return __dzG?ts(__dzG):ts(structuredClone(Zi[n]))` |
| Nœud sélectionné | `return vn("node")\|\|"n6"` | reprise depuis le conservateur |
| Zoom | `useState(.75)` | idem |
| Pan | `useState({x:0,y:0})` | idem |

`ts()` ne fait que fusionner les propriétés par défaut : idempotent, donc sûr
à appliquer sur un graphe déjà normalisé.

**Précédence** : les points d'entrée externes existants (`__dzRenderGraph`,
`__dzRender`, `__dzTpl` — « rouvrir dans Studio » depuis la Bibliothèque)
doivent **primer** sur l'état conservé. Ouvrir un rendu dans Studio charge son
graphe, il ne restaure pas le précédent.

### 2. Écran actif mémorisé

`useState(sg||t)` repart toujours sur `studio`. Mémoriser l'écran courant dans
`localStorage` (`dz_view`) — c'est une préférence de navigation, pas du
travail, donc la persistance disque est ici légitime et cohérente avec les 18
clés existantes. Le paramètre d'URL `?view=` garde la priorité.

### 3. Montage

Le travail tient dans `clips`, `selId`, `proj`, `dirty`, `fxEdit`. Code non
minifié, ancres uniques (`x.useState(svmDemoClips)`, `var clipsRef=…`).

**Piège à neutraliser** : l'effet de montage appelle `/api/montage/project`
puis écrase l'état avec `setClips(cs); setSelId(…); setPh(0); setDirty(!1)`.
Il doit être conditionné à l'absence d'état conservé — sinon la timeline
restaurée est remplacée par la timeline auto-construite une fraction de
seconde après le retour.

### 4. Quick, News, Épisodes

Les trois écrans restants qui portent du vrai travail :

- **Quick** : prompt, images de référence, preset, durée, ratio, seed.
- **News** : articles sélectionnés, requête, script généré.
- **Épisodes** : titre, script, langue, voix, scènes, illustrations.

## Hors périmètre

- **Bibliothèque, Scheduler, Réglages** : leur état est une position de
  navigation rechargée du backend, pas du travail en cours.
- **Les quatre écrans en iframe** (Sprite Lab, Tile Lab, 3D Studio, Atelier
  Chapitre) rechargent leur document à chaque retour. Les préserver demande de
  modifier ces pages autonomes — lot séparé, à traiter seulement si le besoin
  se confirme à l'usage.
- **Survie au redémarrage de l'application** : explicitement exclu par la
  portée retenue.

## Vérification

Pour chaque étape, dans l'application lancée :

1. Construire un état non trivial sur l'écran (graphe à plusieurs nœuds
   déplacés et zoomés ; timeline avec effets et mixage modifié).
2. Naviguer vers la Bibliothèque, puis vers deux autres écrans, puis revenir.
3. Vérifier que l'état est identique, y compris zoom, pan et sélection.
4. Vérifier qu'un rechargement de la page **repart bien à zéro** (portée en
   session, pas de brouillon fantôme), à l'exception de l'écran actif (étape 2).
5. Vérifier l'absence de régression sur les points sensibles : `Alt+C` ne
   fait rien hors Montage, `/` n'ouvre le dock que dans Studio, aucun sondage
   réseau ne subsiste après avoir quitté un écran (onglet Réseau).

Après chaque patcher : `node --check` sur le bundle, puis la suite backend
(`scripts/run-tests.ps1`) qui doit rester à 31/32.
