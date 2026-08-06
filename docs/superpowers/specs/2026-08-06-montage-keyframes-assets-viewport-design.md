# Montage — keyframes d'effets, flux d'assets, viewport

> Conception validée le 6 août 2026. Cible : `DzMontage` dans
> `frontend/patches/son-vfx-montage.js` (injecté dans le bundle compilé par
> `scripts/patch_bundle_sonvfx.py`) et `backend/app/services/{montage,effects_engine}.py`.

## Demande

1. Bouton d'ajout d'assets depuis la bibliothèque, filtré par type de fichier.
2. Points clés posés à la tête de lecture pour piloter les effets.
3. Courbes de Bézier éditables pour les ease in / ease out de début et fin d'effet.
4. Zoom molette sur le viewport, et sélecteur de format parmi ceux de l'application.
5. Glisser-déposer d'un rendu ou d'un asset dans le viewport et dans les pistes.
6. Play / pause à la barre d'espace.

Sémantique retenue pour les points clés : **un point d'entrée et un point de
sortie par effet**, l'intensité montant puis redescendant selon une courbe
éditable. Pas d'automation multi-points sur paramètres arbitraires.

## Contrainte majeure : ffmpeg ne rampe pas uniformément

Relevé sur le binaire livré (ffmpeg 9.0), vérifié par exécution :

| Capacité | Effets concernés |
|---|---|
| Rampe continue native par expression `t` | vignette, letterbox, shake, gradient |
| Rampe par commandes différées (`sendcmd`) | blur, chroma, bloom, dreamy, halation |
| Ni l'un ni l'autre | grain, sharpen |
| Refusent même `enable=between()` | pixelate, mirror, vhs, shake (chaînes contenant `scale`, `crop`, `pad`, `hstack`) |

Une implémentation au cas par cas donnerait donc un comportement différent
selon l'effet — découvert au rendu, pas à l'édition.

### Mécanisme retenu : fondu dry/wet universel

```
[in]split=2[a][b];
[b]<chaîne d'effet inchangée>[p];
[a][p]blend=all_mode=normal:all_opacity=<rampe>:enable='between(t,t0,t1)'[out]
```

Vérifié fonctionnel sur les 20 effets, y compris `pixelate`. Comportement
identique partout, aucun builder d'effet à modifier. Coût : une passe de
filtrage et un blend par effet animé.

**Exception `shake`** : mélanger une image secouée avec une image fixe produit
un dédoublement fantôme, pas un tremblement atténué. Pour lui, l'amplitude est
modulée directement dans son expression `crop`, qui utilise déjà `t`.

### Bézier : échantillonnée, pas approchée

`animation_service.py` sait **déjà** interpréter `cubic-bezier(a,b,c,d)`
(`_bezier_y_for_x`, résolution de Newton + bissection) — toute la couche
d'interpolation est réutilisable telle quelle.

ffmpeg n'ayant pas de boucles, la courbe ne peut pas y être résolue. On
l'échantillonne côté Python et on émet une suite de commandes temporisées :
courbe **exacte**, au prix d'un escalier au pas d'échantillonnage
(imperceptible à 25 pas/seconde sur un fondu). L'alternative — une forme
paramétrique continue — diverge de la courbe dessinée dès que les abscisses
de contrôle sont asymétriques, et cette divergence ne se voit pas à l'écran.
Précédent à ne pas répéter : `dzEase` côté aperçu n'implémente que 4 des 10
easings du backend, et personne ne l'a remarqué.

## Deux bugs à corriger au passage

- **Le format 4:5 ment.** Proposé par les menus du bundle et géré par
  `animation_service`, il est absent de `_CANVAS` (`montage_service.py`) : un
  rendu 4:5 retombe silencieusement en 9:16. À corriger avant d'exposer un
  sélecteur de format, sinon on expose un choix qui n'est pas honoré.
- **`Alt+C` n'a aucune garde de saisie.** L'écran contient des `<input
  type="range">` (opacité, intensité). Tout raccourci global doit tester
  `input`/`textarea`/`select`/`isContentEditable` — modèle existant dans le
  bundle pour la palette `/` — et appeler `preventDefault()`.

## Lots

### Lot 1 — viewport et raccourcis

- **Barre d'espace** : play/pause de l'aperçu, avec garde de saisie et
  `preventDefault` (l'espace scrolle la page par défaut). La même garde est
  ajoutée à `Alt+C`. L'écouteur reste monté/démonté avec `DzMontage` — un
  écouteur `window` survivant au démontage rendrait la lame destructrice
  depuis n'importe quel écran (cf. `patch_bundle_keepstate.py`).
- **Zoom molette du viewport** : `onWheel` sur `.svm-frame`, facteur borné,
  réinitialisation au double-clic. Ne pas confondre avec le zoom horizontal
  de la timeline (`SVM_ZOOMW`), qui reste inchangé.
- **Sélecteur de format** : lié à `proj.ratio`, déjà transporté de bout en
  bout (`/api/montage/project` → `proj.ratio` → payload de rendu). Le cadre
  `.svm-frame` a un `aspect-ratio: 9/16` figé en CSS : il doit suivre la
  valeur choisie. Valeurs exposées : celles réellement supportées après
  correction — `9:16`, `16:9`, `1:1`, `4:5`.

### Lot 2 — flux d'assets

- **Bouton d'ajout par piste**, généralisant `openOvPicker`/`ovPicker`/
  `addOverlay` (aujourd'hui réservés à V2). Sources filtrées par piste :
  vidéos et rendus terminés sur V1/V2 (`/api/jobs` + `/api/images`), fichiers
  audio sur A1/A2/A3 (`/api/audio`). Pose à la tête de lecture, comme
  l'existant.
- **Glisser-déposer** vers le viewport et vers les bandes de pistes. Aucun
  gestionnaire DnD n'existe dans le Montage ; modèles à recopier depuis le
  bundle (`application/node-type` du Studio, `text/dz-post` du Scheduler).
  Le dépôt sur le viewport vise la piste vidéo principale ; le dépôt sur une
  bande vise cette piste, à la position horizontale du curseur.

### Lot 3 — keyframes et courbes

- Points d'entrée/sortie posés à la tête de lecture sur l'effet sélectionné,
  stockés dans le dict d'effet (`t0`, `t1`, `ease_in`, `ease_out`). Le dict
  traverse déjà `renderPayload` → `/api/montage/render` → `build_chain` sans
  validation intermédiaire : **aucun changement de contrat d'API**.
- Éditeur de courbe de Bézier (deux poignées, aperçu SVG) — à construire
  intégralement, il n'en existe aucun dans le frontend.
- Génération des rampes dans `build_chain`, qui reçoit aujourd'hui un `ctx`
  limité à `{w, h}` : y ajouter `dur` et `fps` du clip.
- **Référentiel temporel** : sur les segments V1, `setpts=PTS-STARTPTS`
  s'exécute avant les effets, donc `t` est **local au clip**. Les overlays V2
  utilisent au contraire un `enable=between()` en temps **absolu**. Deux
  conventions dans le même fichier — `t0`/`t1` des effets sont locaux au clip.

## Contraintes de réalisation

Toute évolution passe par un patcher idempotent supplémentaire appliqué au
bundle compilé, en JavaScript sans JSX (`r.jsx`, `x.useState`). Le bundle
porte déjà les couches `sonvfx`, `keepstate`, `keepview`. `DzMontage` n'existe
que dans `frontend/patches/son-vfx-montage.js` — c'est ce fichier qu'on édite,
puis `patch_bundle_sonvfx.py` rafraîchit le bloc dans le bundle.

## Vérification

Par lot, dans l'application lancée :

- **Lot 1** : espace bascule la lecture ; espace dans un curseur d'intensité
  ne bascule rien ; `Alt+C` idem ; la molette zoome le viewport sans toucher
  la timeline ; changer de format modifie le cadre **et** le rendu produit
  (contrôler les dimensions de sortie avec ffprobe, notamment en 4:5).
- **Lot 2** : ajouter un rendu sur V1 et un son sur A2 depuis les boutons ;
  déposer un asset sur le viewport et sur une bande ; vérifier que le clip
  créé porte le bon `tr` et la bonne source, et qu'il rend.
- **Lot 3** : un effet avec entrée à 1 s et sortie à 3 s sur un clip de 5 s ;
  extraire des images à 0,5 s / 2 s / 4 s et vérifier que l'effet est absent,
  présent, puis absent ; comparer une courbe symétrique et une courbe
  asymétrique.

Après chaque patcher : `node --check` sur le bundle, puis `scripts/run-tests.ps1`
qui doit rester à 31/32.
