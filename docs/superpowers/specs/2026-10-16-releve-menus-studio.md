# Relevé « Menus : Studio » — ancrage des liens et en-têtes de ports (16/10/2026)

Relevé fait sur `origin/main` 02f8162c (après #371, maillon de queue `dzlogo`). Lecture seule : rien n'est corrigé ici.
Le plan qui en découle : `docs/superpowers/plans/2026-10-16-optimisation-menus-studio.md`.

## Demandes de l'utilisateur (16/10, deux captures du Studio)

1. **Ancrage des liens** : le bout de chaque courbe doit arriver exactement au MILIEU du rond du port, à l'entrée comme
   à la sortie. Aujourd'hui il arrive à côté (au-dessus ou en dessous). Exemples cités : News item → News script /
   News illust., Brand strip → Spatial compose, HeyGen avatar → Spatial compose.
2. **En-têtes de ports** : la ligne des étiquettes (« prompt · text » … « out · image ») est collée à la bordure haute
   de l'encart de visualisation. Il faut plus d'air, de façon cohérente sur tous les types de nœuds.

## Où est le code (bundle `frontend/dist/assets/index-BEOJX8L5.js`)

| Rôle | Code | Couche qui le pose |
|---|---|---|
| Constantes | `bi=220` (largeur du nœud), `Ru=36` (hauteur d'en-tête), `Mu=22` (pas entre deux ports), `zh=92` (encart), `Eh=30` (pied) | bundle de base |
| Position d'un port **pour les liens** | `qi(type, side, portId, node)` → `{x: side==="in" ? 0 : bi, y: Ru+12+index*Mu}` | base ; `node` en 4e argument + `dzNodeInPorts` posés par `patch_bundle_spatialports.py` (CR-3) |
| Courbe | `es(x1,y1,x2,y2)` = `M x1 y1 C x1+k y1, x2-k y2, x2 y2` (k = max(40, |dx|/2)) | base |
| Tracé des liens | dans `Lh` : `de=W.x+L.x, ce=W.y+L.y, Ee=S.x+J.x, et=S.y+J.y` puis deux `path` (trait + zone de clic 16 px) ; lien en cours de pose idem | base + `patch_bundle_montage.py` (retrait d'un lien au clic) |
| Nœud | `Th` : `div` absolu `left:x, top:y, width:bi`, bordure 1 px ; en-tête `height:Ru` avec `borderBottom` ; **corps des ports** `{position:relative, minHeight:16, padding:"8px 0"}` ; encart (variante `reef`) `{height:zh, margin:"4px 10px 0"}` ; pied | base |
| Port | `ud` : ligne absolue `top: 8+n*Mu+2`, `left/right: -8`, `display:flex; alignItems:center; width:130` ; rond `16×16`, `border:2px` ; étiquette `fontSize:10.5` (libellé + « · type ») | base |
| Ports de Composition spatiale | `dzSpatialSlots(tpl, props)` → ports visibles d'après `tpl.regions` : `video_slot` → reel/avatar/s3…s6, **`image_slot` seulement** → brand/bg | `patch_bundle_spatialports.py` |
| Graphe zoom / pan | conteneur `transform: translate(pan) scale(h)`, `transformOrigin: 0 0` ; le SVG des liens et les nœuds sont dans le MÊME conteneur | base |

Feuille globale : `*,:before,:after{box-sizing:border-box}` (Tailwind) — toutes les hauteurs ci-dessus incluent bordures
et marges intérieures.

## Mesures au navigateur

Backend de preuve sur le **8797** (python embarqué, `sys.path.insert` du worktree, `DEEPOTUS_DATA_DIR` jetable, aucune
clé) ; Studio ouvert sur le graphe de départ « Post reel News » (9 nœuds, 9 liens, variante `reef`). Pour chaque lien :
extrémités du `path` (`getPointAtLength(0 | L)` × `getScreenCTM()`) contre le centre du rond (`getBoundingClientRect`
du `span[data-port-side][data-port-id]`). Écarts en pixels d'écran (lien − centre du rond ; dy < 0 = le lien arrive
AU-DESSUS du rond).

| Zoom | sortie dx | sortie dy | entrée dx | entrée dy | entrée Composition spatiale (dy) |
|---|---|---|---|---|---|
| 30 % | +0,3 | −2,1 | −0,3 | −2,1 | −4,3 |
| 75 % | +0,8 | −5,3 | −0,8 | −5,3 | −10,7 |
| 105 % | +1,1 | −7,4 | −1,0 | −7,4 | −14,9 |
| 150 % | +1,5 | −10,5 | −1,5 | −10,5 | −21,3 |

Après déplacement du nœud Illustr. News (glisser au vrai clic, 105 %) : écarts identiques. Le défaut est donc
**constant en unités du graphe** (≈ +1 / −7, et −14 sur Composition spatiale), multiplié par le zoom ; ni le pan, ni le
zoom, ni le déplacement ne l'introduisent.

Lien **Brand strip → Composition spatiale** : port d'arrivée `brand` **absent du DOM** ; l'extrémité du lien est
exactement au coin haut-gauche du nœud (écart (0, 0) avec son `getBoundingClientRect`).

Captures : `assets/2026-10-16-studio/ancrage-150-reperes.png` (150 %, repères rouges = bouts des liens, verts = centres
des ronds : le rouge est au-dessus du vert), `entetes-150.jpg`, `graphe-105.jpg`.

### En-têtes de ports (unités du graphe, mêmes données)

| Nœud | ports (in+out) | corps | haut étiquette − bas en-tête | encart − bas de la 1re ligne | lignes |
|---|---|---|---|---|---|
| News item | 1 | 16 | 10,4 | **−6** | 16 |
| News script | 3 | 16 | 10,4 | **−28** (3e port) | 16/16/16 |
| HeyGen avatar | 2 | 16 | 10,4 | **−6** | 16/16 |
| Illustr. News | 2 | 16 | 10,4 | **−6** | 16/16 |
| Bandeau de marque | 2 | 16 | 10,4 | **−6** | 16/16 |
| Composition spatiale | 3 | 16 | 10,0 | **−42,4** | 30/30/16 |
| Avatar maître | 2 | 16 | 10,4 | **−6** | 16/16 |
| Rendu | 4 | 16 | 10,4 | **−72** (4e port) | 16×4 |

« encart − bas de ligne » négatif = la ligne d'étiquettes **déborde dans l'encart**. Il n'y a pas « peu d'air » : la
première ligne chevauche déjà la bordure haute de l'encart de 6 unités, et chaque port supplémentaire s'imprime 22
unités plus bas, PAR-DESSUS l'aperçu.

## Causes

### Défaut 1 — ancrage

1. **Deux géométries qui ne se parlent pas.** `qi` place le port à `y = Ru + 12 + i·Mu = 48 + 22i`. Le rendu, lui :
   bordure du nœud 1 + en-tête 36 + `top` de la ligne 10 + demi-ligne 8 = **55 + 22i**. Écart −7 : chaque lien arrive
   au-dessus du rond, partout.
2. **Bordure oubliée en x.** Le rond d'entrée est centré à `x + 1` (bordure 1 px, ligne à `left:-8`, rond de 16), celui
   de sortie à `x + 219` (largeur 220 bordures comprises) ; `qi` donne 0 et 220 → ±1.
3. **Étiquette sur deux lignes.** La ligne du port est `alignItems:center` et `width:130` ; un libellé long (« News reel
   (illustration) · av », « HeyGen avatar (reads the script) · av ») passe sur deux lignes, la ligne fait 30 de haut et
   le rond descend de 7 de plus → −14 sur Composition spatiale. Selon la longueur du libellé (et la langue), le décalage
   change : d'où « au-dessus ou en dessous » selon les nœuds.
4. **Port fantôme `brand`.** `dzSpatialSlots` ne crée les ports image que pour les régions `image_slot` ; la région
   `r_brand` de `tpl_news_reel` est de type `brand_strip` → pas de port `brand` affiché, mais le graphe de départ
   « Post reel News » (et tout graphe enregistré avant CR-3) relie Brand strip → `brand`. `qi` ne trouve pas l'index et
   rend `{x:0, y:0}` : le lien atterrit au coin haut-gauche du nœud.

### Défaut 2 — en-têtes de ports

1. **Corps des ports de hauteur fixe.** `minHeight:16` + `padding:"8px 0"` en `border-box` = 16 au total (le padding
   mange la hauteur minimale) ; les lignes de ports sont toutes `position:absolute`, elles ne poussent rien. L'encart
   commence donc à 16 + 4 (marge) = 20 sous l'en-tête alors que la 1re ligne occupe 10 → 26.
2. **Le nombre de ports n'agrandit pas le corps** : 2e, 3e, 4e ports dessinés par-dessus l'encart (News script, Rendu,
   Composition spatiale).
3. **Libellés longs sur deux lignes** (cause 3 du défaut 1) : la ligne déborde aussi sur sa voisine (30 > pas de 22).

Correctif commun (à faire dans cet ordre, même maillon) : UNE source de géométrie partagée par `qi` et `ud`/`Th`
(origine des ports, pas, hauteur de ligne fixe, rond ancré en haut de ligne et non centré sur une ligne qui grandit,
bordure comptée en x), libellé sur une ligne (ellipse + `title` complet), corps des ports dimensionné
`max(nIn, nOut) · Mu + air`, encart posé dessous avec une marge haute fixe identique pour tous les types.

## Autres anomalies du Studio repérées pendant le relevé (hors des deux demandes)

- **A1 — barre du graphe sur deux lignes, canevas non décalé.** À 1500 px de large (inspecteur ouvert), la barre
  `data-dz-gbar` fait 107 px (`--dz-gbar-h: 107px`) mais le canevas garde `top:48` : 59 px du graphe passent sous la
  barre (le haut des nœuds Article News / Script News est masqué). L'encart des raccourcis (« / nœuds · ⌘K palette ·
  ⌘⏎ exécuter », `top:60`) suit, lui, la barre via la variable et chevauche les nœuds. À trancher : la barre est
  translucide (flou) donc le passage dessous est peut-être voulu, mais l'origine du graphe ne devrait pas y être cachée.
- **A2 — boutons de zoom ± non centrés.** Les boutons changent `h` sans recalculer le pan : le zoom se fait autour du
  coin (0,0) du canevas, la vue « part » vers le haut-gauche (constaté à 150 %), alors que la molette zoome autour du
  curseur.
