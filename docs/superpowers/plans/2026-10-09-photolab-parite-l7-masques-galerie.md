# Photolab parité L7 (t157) — masques, liens, filtres dynamiques, Sélectionner et masquer, Galerie de filtres, Sélection d'objet

> Relevé : `specs/2026-10-08-photolab-bientot-inventaire.md` (lot 7) ; amont photocraft v0.3.0 `ui-egui/src/gallery_ui.rs`,
> `panels.rs`, `mask_thumbs_ui.rs`, `smart_ui.rs`, `layer_menu_ui.rs`, `retouch_ui.rs` ; moteur `gallery_cmds.rs`,
> `smartselect_cmds.rs`, `smart_cmds.rs`. Base : origin/main a2b9a7ab, branche `chantier/photolab-parite-l7`.

## Périmètre

- Panneau Calques : boutons **Lier** et **Masque** (grisés « bientôt ») ; vignette de masque, chaîne, masque désactivé,
  indicateur de lien, **filtres dynamiques** sous un objet dynamique (aujourd'hui invisibles).
- Sélection › **Sélectionner et masquer…** (`select.selectAndMask`, absent du moteur → écran sur `select.refineEdge`).
- Filtre › **Galerie de filtres…** (`filter.filterGallery`, sans écran : `effects` json).
- Outil **Sélection d'objet** (W, p2:false).

## Faits établis (vrai moteur, 09/10)

- `doc.inspect` : `hasMask`, `linkGroup` (null | n), `kind: "Smart Object"`, `smartFilters [{command, params, blend,
  opacity, visible}]`, `smartFiltersEnabled`. Aucun état « masque activé / lié » : seules les bascules le rendent
  (`layer.layerMask.enabled` → `{enabled}`, `.linked` → `{linked}`).
- `doc.render` rend TOUJOURS le composite : `view.layerMask` (gris, rubis) n'y change rien. La vignette d'un masque se
  fabrique sur copie comme celle des couches alpha (`select.loadSelection {channel:"mask", layer}` → calque blanc masqué
  sur calque noir).
- `layer.linkLayers {}` bascule (délie si la sélection est déjà un groupe de liens) ; « Link Layers ».
- Masque : `revealSelection` / `hideSelection` / `revealAll` / `hideAll` (« Add Layer Mask »).
- `select.refineEdge` exige une sélection ; sorties selection | layerMask | newLayer | newLayerWithMask (les deux
  dernières masquent la source et activent la copie) ; historique « Select and Mask ».
- `select.object {rect:[x,y,w,h], mode, sampleAllLayers}` → `{bounds, selected, changed}` ; « Object Selection » ;
  rien trouvé = sélection inchangée.
- `filter.filterGallery` : `effects: [{filter: <clé>, params: {…}, visible}]` (ou clés à plat) ; `visible:false` sauté ;
  **valeur hors bornes = défaut du filtre, en silence** (99 → 4) : l'écran borne et le pont refuse ; `{list:true}` = 47
  filtres en 6 catégories ; un seul effet → historique du nom de l'effet, plusieurs → « Filter Gallery ».
- Filtres dynamiques : `filter.convertForSmartFilters`, puis chaque filtre s'ajoute à `smartFilters` ;
  `layer.smartFilter.setParams {layer, index, params}` (« Edit Smart Filter »), `setVisible` (« Smart Filter Visibility »),
  `delete`, `move`, `blendingOptions`, `disableSmartFilters`.

## Référence (Photoshop 2026, relevé 09/10, lecture seule, document jetable fermé sans enregistrer)

- Sélectionner et masquer : espace à part ; Mode d'affichage (7 vues : Pelure d'oignon O, Cadre de sélection actif M,
  Incrustation V, Sur noir A, Sur blanc T, Noir et blanc K, Sur calques Y ; F parcourt, X coupe), Afficher le contour,
  Afficher l'original (P), Aperçu haute qualité, Transparence (%) ; Détection des contours : Rayon (px), Rayon dynamique ;
  Améliorations globales : Arrondi, Contour progressif (px), Contraste (%), Décalage du contour (%) ; Effacer la sélection,
  Inverser ; Paramètres de sortie ; Mémoriser les paramètres ; Réinitialiser, OK, Annuler. Outils de pinceau d'affinage.
- Le reste (galerie, Lier, Masque, sélection d'objet, sous-lignes des filtres dynamiques) : le comportement de l'amont
  ci-dessous est conforme à la référence ; l'écran de 5120 px rend la référence lente à lire, la barre contextuelle y
  propose une génération en nuage (jamais cliquée).

## Décisions

| Entrée | Chez eux (référence / amont) | Chez nous | Décision |
|---|---|---|---|
| Masque (bouton) | sélection ? révéler : tout révéler ; Alt = masquer ; déjà masqué → masque vectoriel | idem (`layer.layerMask.*`, `layer.vectorMask.add {hide}`) | **Repris** |
| Lier (bouton) | ≥ 2 calques, bascule ; icône de lien sur la ligne | idem (`layer.linkLayers`) ; actif aussi sur un calque déjà lié | **Repris** |
| Vignette de masque | chaîne (clic = lier/délier), Maj-clic = désactiver (croix rouge), Alt-clic = voir le masque, Ctrl-clic = sélection | vignette rendue par le moteur (route `/masques`) ; mêmes gestes ; Alt-clic montre le masque seul sur la toile (image du pont, pas de rubis) ; l'état activé / lié est tenu par l'écran (le moteur ne le relit pas) comme les verrous | **Adapté** |
| Filtres dynamiques | en-tête (œil global), une ligne par filtre (œil, nom, double-clic = rééditer, options de fusion, supprimer, glisser) | tout cela ; rééditer = dialogue du filtre AVEC aperçu (`setParams` joué sur copie), la galerie se rouvre avec sa pile (l'amont ne le sait pas) | **Repris, mieux que l'amont** |
| Sélectionner et masquer | espace à part, 7 vues, curseurs, sortie, pinceaux | dialogue non modal : 7 vues calculées par le moteur sur copie (Cadre de sélection = composite + cadre de la sélection affinée), Transparence, curseurs du moteur (Rayon 0..250, Arrondi, Contour progressif 0..250, Contraste, Décalage), Inverser, Décontaminer + Quantité, Sortie (4 sorties du moteur), Échantillonner tous les calques, Mémoriser, Réinitialiser ; F / X / lettres des vues ; Alt+Ctrl+R ; bouton dans la barre des outils de sélection | **Adapté** — pinceaux d'affinage et sorties « nouveau document » **Écartés** (absents du moteur) ; sans sélection : refusé et dit (le moteur l'exige) |
| Galerie de filtres | aperçu, 6 dossiers à vignettes, liste, paramètres, pile d'effets (œil, nouveau, supprimer, ordre) | idem ; aperçu = `/apercu` du moteur ; vignettes rendues par le moteur sur une réduction du document ; couleurs de premier / arrière-plan | **Repris** |
| Sélection d'objet (W) | glisser un rectangle ; Maj ajoute, Alt retire ; Échantillonner tous les calques ; Sélectionner un sujet ; mode Lasso | rectangle + modes + cases ; « Sélectionner un sujet », « Sélectionner et masquer… » | **Repris**, mode Lasso **Écarté** (le moteur ne prend qu'un rectangle) |
| Convertir pour les filtres dynamiques | — | sorti de `SANS_EDITEUR` (il y était parce que l'écran ne montrait pas les filtres) | **Rouvert** |

## Relevé d'exécution (09/10/2026)

**Pont.** `photolab_registre` : pile de la galerie vérifiée effet par effet contre `filter.gallery.<clé>` (`_galerie` :
filtre connu, clés `filter/params/visible`, bornes du registre, couleurs « #rrggbb » ou 0..1, 1 à 20 effets) ;
`select.refineEdge` borné (rayon 0..250, contour 0..1000 : `px` sans bornes au registre). `photolab_moteur` :
`verifier_filtre_dynamique` (clés du filtre VISÉ lues dans doc.inspect, pour /executer et /apercu), aperçu des
`layer.smartFilter.*`, galerie sortie de `FILTRES_HORS_APERCU`, `masques` (vignette sur copie : masque chargé en sélection
sur un calque blanc au-dessus d'un noir), `apercu_masque` (7 vues composées sur copie), `catalogue_galerie`,
`vignettes_galerie` (centre du document aplati, recadré 80:56, 160×112, filtre par défaut, rendu, annulé). Routes
`/masques`, `/masquer/apercu`, `/galerie`, `/galerie/vignettes`.

**Écran.** `mod-galerie` (dossiers à vignettes, liste, réglages par `fabriquerControle`, pile, aperçu moteur),
`mod-masquer` (dialogue non modal, 7 vues, F / X / P / lettres, Alt+Ctrl+R par décorateur de menu, Mémoriser en stockage
local), `mod-calques` (Lier, Masque, vignette + chaîne + croix rouge, Maj / Alt / Ctrl-clic, badge de l'objet
dynamique, sous-lignes des filtres : œil global et par filtre, double-clic = réédition avec aperçu, options de fusion,
supprimer, glisser), `mod-selection` + `mod-outils` (Sélection d'objet, boutons d'action dans la barre), dialogue générique
réutilisable pour la réédition (`options.initiales`, `versCommande`, `apercu`).

**Défauts trouvés en route.** Vignette de masque arrivée mais jamais posée (le crochet ne reposait que celle du calque) ;
icônes `unlink` et `chevron-up` absentes (chaîne et bouton vides : `chevron-up` et `app-window` reprises de l'amont) ;
clé de catégorie « Brush Strokes » -> `_brush__strokes` ; clé `samplealllayers` mal orthographiée ; Alt+Ctrl+R sans effet
(le catalogue n'a pas ce raccourci) ; 11 textes français à deux traductions ; aucun ne passait les bancs avant correction,
chacun a son cas (qa/masques 5.2, 4.15-4.16, 7.11, 7.12).

**Bancs.** `test_photolab_masques` 79/79 (vrai moteur : liste blanche, vignettes de masque, 7 vues, galerie égale à
l'octet à l'application réelle, réédition égale à l'octet, routes) ; QA `masques` 70 ; bancs figés mis à jour (champs
2.20-2.22, dialogue 1.4 et 8.5b, menus 4.6 et 4.9, outils 1.5, 2.5, 2.16, 4.1-4.4c, 4.11, formulaires 2.2-2.3b,
libellés 1.6-1.6b). Photolab, `test_i18n_l0` : verts hors les 7 rouges d'environnement connus.
- Mutations : 16 sur 16 tuées (8 au pont : bornes de la galerie, réédition, aperçu et route de setParams, vignette de
  masque inversée, sortie admise, bornes de refineEdge, opacité de l'incrustation ; 8 à l'écran), sources restaurées et
  vérifiées par `cmp`.

**Preuve sur 8799** (gestes réels, vrai backend jetable, FR puis EN) : Sélection d'objet autour du soleil -> [219, 89,
203, 203] « Object Selection » ; Sélectionner et masquer par le bouton de la barre puis par Alt+Ctrl+R, vues Incrustation,
Noir et blanc (K), Cadre de la sélection (M : cadre affiné plus petit que celui du document), sortie Masque de fusion ->
« Select and Mask » ; vignette du masque, Maj-clic (croix rouge, puis rétabli), chaîne déliée, Alt-clic (masque seul sur
la toile) ; Galerie : Découpage puis Grain de film (12) en deux calques d'effet, 5 aperçus, « Filter Gallery » ;
Convertir pour les filtres dynamiques, Flou gaussien et Galerie en sous-lignes (le dernier en haut) ; double-clic : rayon
4 -> 10 et niveaux 5 -> 7 avec aperçu, « Edit Smart Filter », pile inchangée (2) ; œil du filtre, œil global, options de
fusion (Produit 60 %), glisser (ordre inversé), supprimer ; Lier (groupe 1, icônes), Masque Alt (« Add Layer Mask »), puis
masque vectoriel.

**Recomptage** `lister_bientot.mjs` : 153 (157 avant), plus les 2 boutons isolés du panneau Calques (Lier, Masque).

**Fiche d'aide.** Aucune : la Sélection d'objet partage l'emplacement de la baguette (`pl-outil-magicWand`, fiche
existante) et les nouveaux boutons et dialogues n'ont pas d'id stable à viser.
