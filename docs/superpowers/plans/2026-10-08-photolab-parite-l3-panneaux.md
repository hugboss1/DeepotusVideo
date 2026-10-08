# Photolab parité L3 (t153) — panneaux Nuancier, Dégradés, Motifs, Histogramme, Infos, Couches, Compositions

> Relevé : `specs/2026-10-08-photolab-bientot-inventaire.md` (lot 3) ; application de référence relevée en lecture
> seule le 08/10 (espaces « Les indispensables », « Photographie », « Graphique et web », retour à « Graphique et web ») ;
> amont photocraft v0.3.0 (`ui-egui/src/panels.rs`, `preset_panels.rs`, `tone.rs`, `channels_panel.rs`, `comps_ui.rs`).
> Base : origin/main 48f2286e, branche `chantier/photolab-parite-l3`.

## Relevé de référence (08/10, lecture seule)

| Panneau | Ce que la référence montre |
|---|---|
| Nuancier | recherche ; ligne des couleurs récentes ; groupes repliables (dossier + nom) de pastilles ; pied : nouveau groupe, nouvelle nuance, supprimer |
| Dégradés | même navigateur : recherche, groupes (« Basiques », « Bleus »…) de vignettes, même pied |
| Motifs | même navigateur : groupes de vignettes de motifs, même pied |
| Couches | lignes œil + vignette + nom + raccourci (composite Ctrl+2, couleurs Ctrl+3…) ; pied : charger la couche comme sélection, enregistrer la sélection, nouvelle couche, supprimer |
| Histogramme | vue compacte (graphe seul) avec triangle quand les données sont en cache ; la vue étendue (canal, statistiques) est celle de l'amont |
| Infos | blocs R/V/B et C/M/J/N (8 bits), X/Y du pointeur, L/H de la sélection, taille du document, aide de l'outil actif |
| Compositions | « Dernier état du document » en tête, puis les compositions |

Un clic de menu a ouvert par erreur une fenêtre d'aide/licence de la référence : Échap, puis fermée par l'utilisateur ;
rien validé. Onglets cliqués pour la lecture (Nuancier, Dégradés, Couches) restés devant dans « Les indispensables ».

## Faits établis (vrai moteur, 08/10)

- `tools.setColors` / `swapColors` hors historique ; les couleurs ne sont pas dans `doc.inspect` (session.list).
- `document.pixel {x,y}` -> `[r,g,b,a]` en 0..1 (composite) ; hors document `[0,0,0,0]` ; hors historique.
- `gradient.presets.list` -> `{groups:[{name,presets:[{name,stops,transparency}]}],current}` ; `select` hors historique ;
  `apply` -> « New Gradient Fill Layer ». Groupes intégrés : Basics, Blues, Purples, Pinks, Reds.
- `pattern.presets.list` -> `{groups:[{name,patterns:[{id,name,width,height}]}],current}` ; `apply` -> « New Pattern Fill
  Layer » ; `new` (Définir un motif) hors historique. Aucune commande ne rend l'image d'un motif : vignette par un document
  temporaire (`doc.new` + `layer.newFillLayer.pattern` + `doc.render`, refermé).
- `doc.inspect.channels` = `channel.list` ; `channel.target` / `setVisible` hors historique ; `select.saveSelection`
  « Save Selection », `channel.new` « New Channel », `channel.rename` / `delete` « Rename / Delete Channel »,
  `select.loadSelection` « Load Selection ».
- **`doc.render` rend toujours le composite**, quelles que soient la cible et la visibilité des couches : la vue d'une
  ou deux couches est composée par l'écran à partir du rendu (affichage seulement). Le contenu d'une couche alpha n'est
  lisible que par le moteur : sur une COPIE, calque uni noir, `select.loadSelection` de la couche, calque uni blanc
  (masqué par la sélection), rendu.
- `doc.inspect.layerComps` = `[{id,name}]`, `lastAppliedComp` ; `layerComp.list` donne les options ; noms
  d'historique « New Layer Comp », « Apply Layer Comp », « Rename Layer Comp », « Layer Comp Options », « Update Layer
  Comp » ; `restoreLastDocumentState` refusé tant qu'aucune composition n'est appliquée.
- Aucune commande de nuancier dans le moteur : la liste des nuances est une donnée Deepotus (route), la nuance choisie
  passe par `tools.setColors`.

## Décisions

| Entrée | Décision |
|---|---|
| Nuancier | **Adapté** : groupes de nuances gardés par `/api/photolab/nuancier` (données Deepotus, liste blanche) ; défaut = les 40 nuances de l'amont en quatre groupes ; clic = premier plan, Alt+clic = arrière-plan ; nouvelle nuance = premier plan ; renommer un groupe par double-clic ; couleurs récentes |
| Dégradés | **Repris** : liste du moteur, clic = choisir (`select`), double-clic = calque de dégradé (`apply`), nouveau (`new`), groupes / renommer / supprimer (`edit`) |
| Motifs | **Repris** : idem (`pattern.presets.*`), vignettes rendues par le moteur (route, cache par id) ; nouveau = Définir un motif |
| Histogramme | **Repris** (vue étendue de l'amont) : canal RVB / Rouge / Vert / Bleu / Luminosité, moyenne, écart type, médiane, pixels ; `/histogramme` existant |
| Infos | **Repris** : `document.pixel` sous le pointeur (limité en fréquence), R/V/B, C/M/J/N naïf (amont), X/Y, L/H de la sélection, taille |
| Couches | **Repris** : liste, œil, cible (vue composée par l'écran), Ctrl+clic = charger comme sélection (Maj / Alt / Maj+Alt), renommer une alpha par double-clic, pied (charger, enregistrer, nouvelle, supprimer) ; vignettes : couleurs tirées du rendu, alpha par la route |
| Compositions | **Repris** : Dernier état du document, appliquer, précédente / suivante, mettre à jour, nouvelle (dialogue : nom, 3 options, commentaire), supprimer, renommer par double-clic, trois options par ligne, avertissement |
| Raccourcis Ctrl+2..9 des couches | **Repris** : aucun n'était pris (catalogue et écran vérifiés) ; Ctrl+2 = composite, Ctrl+3… = couleurs puis alpha |
| Libellé Fenêtre › « Canaux » | **Gardé** : le catalogue reprend le libellé amont tel quel (banc menus 13.5) ; l'onglet dit « Couches » |

## Tâches

- **A** — service `photolab_nuancier.py` + GET/PUT `/api/photolab/nuancier` ; `PM.vignette_motif(s, id)` + GET
  `/api/photolab/motifs/{id}.png` ; `PM.couches_alpha(s, max_side)` + GET `/api/photolab/couches` (PNG par alpha) ; banc
  `test_photolab_panneaux3.py` sur le vrai moteur.
- **B** — modules purs `mod-nuancier.js`, `mod-presets.js` (Dégradés + Motifs), `mod-infos.js` (Histogramme + Infos),
  `mod-couches.js`, `mod-compositions.js` ; QA `qa/panneaux3.test.mjs`.
- **C** — onglets dans `index.html` (Couleur | Nuancier | Dégradés | Motifs ; Propriétés | Ajustements | Compositions ;
  Calques | Couches | Historique | Navigateur ; nouveau groupe Histogramme | Infos), rail, espaces (GROUPES, PANNEAUX,
  dispositions, copie Python), textes fr/en.
- **D** — mutations, preuve 8799, recomptage (212 -> 198).

## Relevé d'exécution (08/10/2026)

**Faits nouveaux établis en cours de lot.**
- Un calque uni créé sur une sélection n'est PAS masqué par elle : le contenu d'une alpha se rend par calque uni noir,
  calque uni blanc, `select.loadSelection` de la couche puis `layer.layerMask.revealSelection`.
- `select.deselect` est refusé sans sélection (« no selection ») : la copie ne désélectionne que si `hasSelection`.
- `layerComp.new` marque la composition créée comme appliquée ; le « Dernier état du document » n'est retenu qu'en
  appliquant une composition alors qu'aucune composition existante n'est appliquée (amont `comps_cmds.rs` apply).
  Le bouton suit `hasLastDocumentState` (grisé sinon).
- Le moteur a neuf groupes de dégradés (Basics, Blues, Purples, Pinks, Reds, Oranges, Greens, Browns, Grays) : tous
  traduits, ainsi que les préréglages numérotés (« Bleu 03 »).
- `Uint8ClampedArray` arrondit au pair (132,5 -> 132).

**Défaut d'un lot précédent trouvé et corrigé** : en vue en miroir (t152), l'aperçu de la sélection rectangle et le
cadre de recadrage avaient une largeur négative (erreur SVG « width -154 », rien de dessiné) -> `rectVersEcran`.

**Bancs.**
- `test_photolab_panneaux3` : 85/85 (service du nuancier, routes, copie JS, vignettes de motif et couches alpha sur
  le vrai moteur, liste blanche, routes).
- QA node : toutes les séries vertes, dont la nouvelle `panneaux3` (71) ; bancs figés mis à jour (espaces 1.2-1.10,
  2.5, 4.9, 5.4, 5.6 ; panneaux 11.3 ; zones 2.3, 2.4 ; test_photolab_espaces 1c).
- `test_photolab_espaces` 51/51, `test_photolab_textes` 7/7.

**Preuve sur 8799** (gestes réels, vrai backend jetable) :
- Nuancier : 4 groupes, 40 nuances ; clic = premier plan (#e62828), Alt+clic = arrière-plan (#2864e6), récentes en tête ;
  nouveau groupe « Ma marque » (dialogue), nouvelle nuance = premier plan, clic droit + Supprimer ; relu par la route.
- Dégradés : 9 groupes traduits, barre du dégradé courant ; double-clic -> « New Gradient Fill Layer ».
- Motifs : vignettes 64 × 64 rendues par le pont ; double-clic -> « New Pattern Fill Layer » ; Définir un motif depuis
  une sélection 20 × 20 (« Carré bleu ») ; original intact (un seul document, historique inchangé).
- Histogramme : sur un orange #ff8000, R 255, V 128, B 0, luminosité 151 ; 2 000 pixels. Infos sous le pointeur :
  R 255 V 128 B 0, C 0 % M 50 % J 100 % N 0 %, X 20 Y 20, sélection L 12 H 7.
- Couches : cible Vert -> vue en gris 128 ; Ctrl+2 -> composite ; œil du Rouge -> (0,128,0) ; aucun état
  d'historique. Enregistrer la sélection -> « Alpha 1 » (Ctrl+6), vignette blanche dedans / noire dehors ; œil de l'alpha
  -> recouvrement rouge 50 % hors sélection (255,64,0) ; Ctrl+clic -> sélection (5,5,12,7) ; renommer « Visage » ;
  supprimer.
- Compositions : nouvelle (dialogue : nom, position décochée, commentaire en bulle) ; précédente ; options ; renommer ;
  supprimer ; Dernier état du document restauré (calque de nouveau masqué, case cochée).
- Fenêtre : les 7 entrées actives, cochables, chacune ouvre son onglet. Espaces : Photographie -> Histogramme en tête,
  Peinture -> Nuancier devant.
- Écran en anglais vérifié (onglets, groupes, préréglages intégrés, statistiques, infos), puis retour au français.
- Mise en page : champs et graphe en `box-sizing: border-box` (le corps défilait à l'horizontale) ; onglets du groupe
  Calques resserrés (quatre onglets dans 278 px).

**Recomptage** `lister_bientot.mjs` (script corrigé : il reconnaît `data-onglet-co` / `-in` / `-pi`) : 198 (212 avant).
