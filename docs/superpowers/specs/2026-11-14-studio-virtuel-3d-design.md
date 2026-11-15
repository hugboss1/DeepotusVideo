# Studio virtuel 3D — conception (14/11/2026)

But : donner à un créateur qui débute la qualité d'image d'un vrai studio (décor, lumières, profondeur, plusieurs
caméras) sans acheter un meuble. Le studio virtuel s'ajoute à la **capture** (t315), aux **skins** (t316) et au
**Live** (t318) : il ne les remplace pas.

## 1. Ce qui existe et sur quoi on s'appuie

| Brique | Où | Ce qu'on en fait |
|---|---|---|
| Scène de capture à calques | `frontend/shared/dz-capture-scene.js` | le studio est un calque de plus (z 30), sous le skin |
| Skins (cadre, logo, bandeau, alertes) | `dz-skins*.js`, `services/skins.py` | restent PAR-DESSUS le studio, inchangés |
| Live multi-destinations | `dz-live.js`, `services/live.py` | diffuse la scène : le studio y est donc d'office |
| three.js 0.185.1 embarqué | `frontend/dist/assets/three` | moteur d'affichage du studio en direct |
| Pont Blender (MCP) + Poly Haven CC0 | `services/blender_mcp.py` | catalogue en ligne, provenance et licence déjà notées |
| Blender 5.2 installé | `C:\Program Files\Blender Foundation` | fabrique des décors, sans fenêtre (`--background`) |
| Avatar live (fal, Decart) | `services/avatar_live.py` | présentateur de remplacement (lot SV7) |
| Espaces de marque (kit, logo) | `services/espaces.py` | couleurs et logo du studio par défaut |

## 2. Décisions (réponses de l'utilisateur, 14/11)

| # | Sujet | Décision |
|---|---|---|
| D1 | Présentateur | webcam détourée SANS fond vert (local, gratuit) ; fond vert en option ; avatar à la place de la personne |
| D2 | Moteur | three.js dans l'app + Blender en fabrique ; **export en option vers Unreal et Unity** |
| D3 | Catalogue | Poly Haven CC0 + pack maison livré + génération IA à la demande (sous plafond) + import GLB/FBX/OBJ |
| D4 | Blender chez l'utilisateur | facultatif : rien à installer pour utiliser les décors livrés |
| D5 | Décors livrés | 11 : bureau créateur tech, podcast à deux, loft chaleureux, plateau d'actualité, gaming néon, atelier d'impression 3D, vitrine de jeux de plateau, science-fiction, cartoon, football européen, sports américains |
| D6 | Caméras | 3 à 5 par décor, bascule au clavier en direct, mouvements doux automatiques |
| D7 | Contenu | sur un écran du décor ; ou plein écran avec présentateur incrusté ; logo et habillage sur les murs |
| D8 | Machine | portable à carte intégrée : lumières précalculées, 30 i/s en 1080p ; qualité haute pour cartes dédiées |

Choix de Claude (à contester si besoin) :

- C1. **Un décor est une recette** (`deepotus-studio`, JSON) : pièce, matières, lumières, objets, écrans, enseigne,
  place du présentateur, caméras. La même recette est lue par three.js (direct) et par Blender (fabrique, rendu
  photoréaliste, export Unreal/Unity). Le serveur est seul juge du format, comme pour les skins.
- C2. **Deux niveaux de rendu** pour un même décor : « direct » (primitives + matières PBR + lumières temps réel
  limitées, tout de suite, sans Blender) et « fabriqué » (GLB sorti de Blender : volumes biseautés, textures Poly
  Haven, lumières précalculées dans une lightmap). Le décor fabriqué remplace le direct quand il est présent.
- C3. **Le secret reste caché sur l'écran du décor** : la texture de l'écran 3D vient d'un canevas intermédiaire où
  le caviardage est déjà appliqué ; mesure inconnue → écran noir. Aucune source brute « ecran » n'entre dans WebGL.
- C4. Le détourage sans fond vert tourne en local (MediaPipe Selfie Segmentation, Apache 2.0, modèle embarqué,
  aucun CDN) ; s'il manque ou si la machine ne suit pas : repli sur l'encart du skin, jamais d'image cassée.
- C5. Unreal et Unity ne sont PAS des moteurs de l'app : on **exporte** le décor (GLB + recette + notice) pour ceux
  qui veulent y poursuivre. Embarquer un moteur de jeu = 50 à 100 Go, licence, GPU dédié : contraire à D8.
- C6. Le logo de l'application reste figé ; l'enseigne du studio porte le logo de l'ESPACE ou une image du décor.
- C7. Nom dans l'interface : « Studio virtuel » / « Virtual studio » ; préfixe de code `studiov`.

## 3. La recette d'un décor

```
{format: "deepotus-studio", version: 1, nom,
 piece:   {l, p, h (m), sol, mur, plafond: matière, plinthe},
 matieres:{<clé>: {couleur | rôle, rugosite, metal, emission, motif: uni|bois|brique|beton|tissu|pelouse|parquet|grille}},
 lumieres:[{type: cle|appoint|contre|ambiance|neon|fenetre, couleur, intensite, x, y, z, vers:[x,y,z], l, h}],
 objets:  [{type (catalogue), x, y, z, ry, e (échelle), matiere, couleur}],
 ecrans:  [{x, y, z, ry, l, h, source: ecran|image|eteint}],
 enseigne:{actif, source: espace|image|texte, texte, style: neon|panneau|ecran, x, y, z, ry, l},
 presentateur:{x, z, h (m), mode: detoure|fondvert|avatar|encart, ombre, teinte},
 cameras: [{nom, x, y, z, vers:[x,y,z], focale, mouvement: fixe|respiration|travelling|poussee|orbite, amplitude, periode_s}],
 ambiance:{brouillard, exposition, flou_fond, grain, vignette},
 mode: plateau | incruste}
```

Couleurs : un rôle du kit de l'espace (`principale`, `accent`, `texte`, `fond`) ou `#rrggbb`. Mètres, repère three.js
(y vers le haut, le présentateur regarde vers +z, mur du fond à z = −p/2).

## 4. Lots

| Lot | Contenu | État |
|---|---|---|
| SV1 | Recette, service + routes `/api/studiov`, 11 décors livrés (niveau direct), moteur three.js, calque de scène, caméras et mouvements, écran du décor caviardé, enseigne, groupe « Studio virtuel » de la boîte de capture, aperçu | **ce lot** |
| SVH | **Habillage — le décorateur d'intérieur** (14/11, § 6) : vraies textures (pack d'intérieur de 42 matières + les 30 de la Forge + les matières de l'utilisateur), mur du fond, finitions, 16 ambiances lumineuses, 14 styles complets, 127 objets en 20 catégories (67 neufs : rubans LED, panneaux hexagonaux, néons à mot, lettres rétroéclairées, caisson, bibelots par thème), reflets, panneau « Décorer » de l'aperçu, cuisson d'une matière depuis Blender, les 11 décors livrés rhabillés | **fait** |
| SVO | **Objets importés — le socle** (14/11, § 7) : bibliothèque de modèles GLB de l'utilisateur (fichier téléchargé, export d'un objet depuis Blender), lecture du GLB avant de le garder, provenance et licence par objet, droits tirés de la licence (vidéo, export, partage, crédit), licences NC / ND / SA refusées, crédits du décor prêts à coller, objet `modele` de la recette, affichage des modèles par le moteur | **fait** |
| SVA | **Atelier du décor** (14/11, § 8) : trois vues du même décor — par ses caméras, en PLAN (placer meubles, lumières, caméras, présentateur à la souris), en 3D LIBRE (tourner autour de la pièce, choisir d'un clic un pan de mur, un meuble, une lumière, une caméra) ; une matière par pan de mur et par objet ; onglets Caméras (hauteur, focale, visée, mouvement) et Mes objets | **fait** |
| SVB | **Depuis la Bibliothèque de l'application** (15/11, § 9) : les assets que l'utilisateur a générés — illustrations, logos, modèles 3D — entrent dans le studio : tableau, logo mural, kakémono, image sur l'écran du décor, enseigne, modèle 3D posé | **fait** |
| SVC | **Catalogue de produits réels** (15/11, § 10) : les 7 775 modèles 3D d'Amazon Berkeley Objects qui tiennent dans un décor en direct (meubles, luminaires, tapis, art mural, à leur taille réelle), dans leur édition allégée `codepawl/abo-glb` — onglet « Catalogue » (recherche FR/EN, familles, vignettes), téléchargement à la demande d'une révision figée, licence CC BY 4.0 et crédit groupé automatiques, pose au sol / au mur / au plafond, compression Meshopt acceptée, textures ramenées à 1 024 px en qualité légère | **fait** (PR à relire) |
| SV2 | Skill `studio-volumetrique` + fabrique Blender sans fenêtre : GLB biseauté, textures, lightmap, vignette ; les 11 décors passent au niveau « fabriqué » | skill et script livrés avec SV1, cuisson à faire |
| SV3 | Présentateur détouré sans fond vert (MediaPipe embarqué), ombre au sol, teinte par la lumière du décor ; option fond vert | à faire |
| SV4 | Éditeur : déplacer objets, lumières, enseigne, caméras (poignées), réglages par section, annuler/rétablir | à faire |
| SV5 | Catalogue : pack maison (40-80 objets), Poly Haven par le pont, import GLB/FBX/OBJ, pièces de la Bibliothèque | à faire |
| SV6 | Génération IA d'objets (Meshy/fal) sous plafond de dépense, rangée au catalogue | à faire |
| SV7 | Avatar live dans le studio | à faire |
| SV8 | Régie en direct : bascule des caméras au clavier, transitions, mode plein écran incrusté | à faire |
| SV9 | Export Unreal / Unity (GLB + recette + notice), aller-retour Blender pour l'utilisateur qui l'a | à faire |
| SV10 | Traduction EN complète, guide FR/EN, assistant « Demander », suivi des chantiers | à faire |

## 5. Risques

- Détourage local : bords moins nets qu'un fond vert, 5 à 12 ms par image sur carte intégrée → résolution du masque
  réduite (256 px) et lissage temporel ; mesure réelle à faire en SV3.
- Deux contextes graphiques (2D de la scène + WebGL) : une copie d'image par trame. Mesure à faire sur portable.
- Poly Haven : CC0 vérifié à l'import (déjà noté par le pont) ; Sketchfab et Poly Pizza exclus du pack livré.
- Poids de l'installeur : GLB fabriqués + lightmaps ≈ 3 à 6 Mo par décor (Draco + WebP), à mesurer en SV2.

## 6. Lot SVH — l'habillage (demande de l'utilisateur, 14/11 soir)

« Le rendu est trop générique » : le studio doit s'habiller de vraies matières, venues de la Forge ou de Blender, et
se décorer comme on meuble une pièce — meubles, bibelots, couleurs d'éclairage, LED, néons, typographies,
rétroéclairage — avec des objets rangés par catégories.

| # | Sujet | Décision |
|---|---|---|
| H1 | D'où viennent les matières | trois sources, toutes désignées dans la recette par une RÉFÉRENCE (jamais un chemin ni une URL) : `stu:<slug>` le pack d'intérieur du studio (42 matières Poly Haven CC0, `scripts/studiov/composer_textures.py`, 10,6 Mo : couleur 1024 px, normale et rugosité 512 px, vignette) ; `cat:<slug>` les 30 matières du catalogue de la Forge (déjà dans l'installeur) ; `mat:<8hex>` une matière de l'utilisateur dans la Forge |
| H2 | Depuis Blender | l'application lance Blender sans fenêtre (`--disable-autoexec`) sur un fichier .blend, cuit la matière choisie (couleur, normale OpenGL, rugosité, métal) sur une COPIE, et range les cartes dans la Forge : elle devient une matière `mat:` ordinaire. Script livré : `backend/app/studiov/cuire_matiere_blender.py` |
| H3 | Ce qu'on exclut du pack livré | BlenderKit (redistribution et export interdits par ses CGU), Sketchfab et Poly Pizza (licence par modèle, attribution), ShareTextures (CC0 « sur mesure », pas de redistribution). Sûrs : Poly Haven, ambientCG, Kenney, Quaternius (relevé du 14/11) |
| H4 | Teinter | une matière peut être TEINTÉE : sa carte de couleur n'apporte plus que son relief clair / sombre, la couleur vient de la recette (un #hex ou un rôle du kit) — n'importe quelle matière dans n'importe quelle teinte |
| H5 | Échelle | les UV du moteur sont en MÈTRES pour toute matière à texture ou à motif : un carreau mesure sa taille réelle (relevée chez Poly Haven) × `echelle` |
| H6 | Lumière qui déborde | pas de calcul d'éclairage en plus (carte intégrée) : halos additifs (lueur d'un ruban sur le mur ou au sol, d'un néon, d'une lettre rétroéclairée), et une carte de reflets rendue une fois par décor (PMREM) pour les métaux, les laques et les sols cirés |
| H7 | Mots et typographies | quatre objets portent un mot (24 caractères) dans une des 14 polices embarquées : néon à mot, lettres rétroéclairées, caisson lumineux, panneau « ON AIR » ; l'enseigne gagne les styles rétroéclairé et caisson |
| H8 | Le décorateur | dans l'aperçu, panneau « Décorer » d'un décor de l'ESPACE (un décor livré se personnalise par copie) : Style · Matières · Objets · Lumières · Enseigne. Chaque geste est montré aussitôt puis enregistré par le serveur, seul juge du format |
| H9 | Styles et ambiances | un style pose une matière par USAGE (sol, mur, plafond, bois, tissu, cuir, métal) et une ambiance ; une ambiance recolore la clé, l'appoint, le contre, les néons et les objets lumineux — la couleur vive reste dans le fond, jamais sur le visage |

Ajouts à la recette (version 1 inchangée, tout est facultatif) :

```
piece.fond            la matière du mur du fond (défaut : celle des murs)
matieres.<clé>        + texture: "" | stu:… | cat:… | mat:…   + teinte: bool   + usage: sol|mur|plafond|bois|tissu|cuir|metal|pierre|plastique|autre
objets[]              + matiere2 (piètement, structure)   + texte, police (objets à mot seulement)
enseigne              + police   + style: retro | caisson
```

Catalogue servi par `GET /api/studiov/habillage` (`services/studiov_habillage.py`) : textures, familles, finitions,
ambiances, styles. Les cartes du pack : `GET /api/studiov/textures/stu/<slug>/<carte>.jpg` ; celles de la Forge par
ses propres routes. Reste à faire dans ce sillage : poignées de placement à la souris (SV4), modèles GLB réalistes
(SV5), cuisson des lumières (SV2), mesure sur portable à carte intégrée, guide et assistant « Demander » (SV10).

## 7. Lot SVO — les objets importés (14/11)

Les sources qu'on ne peut pas LIVRER (BlenderKit, Sketchfab, Poly Pizza) restent utilisables si c'est l'utilisateur
qui fait entrer l'objet, sous son compte et sous sa licence. Le socle est commun à toutes :

- **Bibliothèque** `DATA_ROOT/studiov/objets/<id>/{modele.glb, fiche.json}` (`services/studiov_objets.py`), celle de
  l'utilisateur, tous espaces confondus. Deux entrées dans ce lot : un fichier GLB qu'il a téléchargé (il déclare la
  source, l'auteur, la licence, l'adresse) ; un objet sorti d'un fichier .blend par l'application
  (`backend/app/studiov/exporter_objet_blender.py`, Blender sans fenêtre) — le chemin des assets BlenderKit.
- **Le GLB est lu avant d'être gardé** : format et version, autonomie (aucun fichier voisin, aucune adresse),
  compression que le moteur n'ouvre pas (Draco, Meshopt, Basis : refus), poids (300 000 triangles au plus ; au-delà de
  60 000 la fiche dit « lourd pour un portable »).
- **Droits tirés de la licence** : CC0 et création = tout ; CC BY = tout, auteur à citer ; BlenderKit Royalty Free =
  vidéo oui, ni export ni partage ; « à vérifier » = l'application n'affirme rien, le décor le signale. Refusées à
  l'import : NC (une chaîne monétisée est un usage commercial), ND (habiller un modèle le modifie), SA, Standard.
- **Crédits du décor** (`GET /api/studiov/{id}/credits`) : les lignes dues, le texte FR / EN à coller sous la vidéo, et
  ce que les licences permettent pour le décor entier (un seul objet BlenderKit interdit son export).
- **Recette** : type `modele` + `ref: "obj:<16 hex>"` — une référence, jamais un chemin. Le moteur charge le GLB par
  l'index servi ; le chargeur three.js embarqué est servi avec ses imports réécrits (`/api/studiov/three/…`, liste
  fermée) car la coque n'a pas de carte d'import.

Relevé du 14/11 pour les connecteurs (non construits) : Poly Pizza a une API documentée (clé de l'utilisateur, en-tête
`x-auth-token`, recherche par mot et par licence, GLB sur `static.poly.pizza`) ; Sketchfab garde sa Download API
(compte de l'utilisateur, filtres `cc0` / `by`, archive glTF en ZIP à convertir, attribution et mention Sketchfab à
afficher). Les deux demandent une clé rangée dans Réglages › Clés : c'est le lot suivant. ShareTextures : import manuel
seulement, sauf accord écrit.

## 8. Lot SVA — l'atelier du décor (14/11)

Demande : voir le studio en plan d'architecte pour placer les meubles, ouvrir les bibliothèques, puis passer dans une
vue 3D pour s'orienter, choisir les pans de mur et les meubles à habiller, placer les lampes, régler la hauteur et la
focale des caméras.

| # | Sujet | Décision |
|---|---|---|
| A1 | Trois vues, un seul décor | « Par les caméras » (ce que le direct montrera), « Plan », « Vue 3D libre ». Un seul « choisi », partagé par le plan, la vue 3D et le panneau : choisir un meuble sur le plan l'entoure en 3D et ouvre ses réglages |
| A2 | Plan | vue de dessus à l'échelle : murs, grille de 50 cm, emprise RÉELLE de chaque meuble (mesurée par le moteur), objets muraux, lumières, caméras et leur champ, présentateur, écrans. Glisser déplace (aimant 5 cm, Alt = libre) ; poignée ronde ou molette = tourner (15°) ; poignée carrée = orienter une caméra ou une lumière ; un objet mural se colle au mur le plus proche |
| A3 | Vue 3D libre | glisser tourne autour de la pièce, Maj + glisser la déplace, la molette approche ; les murs vus de dos s'effacent (maison de poupée). Un clic choisit un objet, un pan de mur, une lumière ou une caméra (repères visibles dans cette vue seulement). « Garder cette vue comme caméra » |
| A4 | Habiller au clic | chaque pan (sol, mur du fond, de gauche, de droite, plafond) a sa matière ; un pan ou un meuble se DÉTACHE de ce qui partageait sa matière au premier changement (les autres ne bougent pas) ; les matières que plus rien n'emploie sont ôtées |
| A5 | Lumières et caméras | lumière choisie : place, hauteur, longueur d'un néon ; ajout d'un projecteur, d'un contre, d'un néon. Caméra : hauteur, focale, visée, mouvement ; ajout (6 au plus), retrait ; présentateur : place, taille, assis |

La géométrie du plan (échelle, emprises, cône d'une caméra, collage au mur, ce qu'on touche) est dans
`dz-studiov-logique.js`, jouée sous node par le banc ; `dz-studiov-plan.js` ne fait que dessiner et écouter la souris.
Reste : poignées de déplacement DANS la vue 3D (aujourd'hui on déplace sur le plan ou par curseurs), annuler / rétablir,
redimensionner la pièce à la souris.

## 9. Lot SVB — depuis la Bibliothèque de l'application (15/11)

Demande : poser dans le studio ce qu'on a généré dans l'application — modèles 3D, illustrations, logos.

- **Onglet « Bibliothèque »** du panneau Décorer : les images de la Bibliothèque (celles de l'espace, cherchées par
  nom ou mot-clé, filtrées par fonction d'origine) et les modèles 3D générés (Game Assets 3D, Établi).
- **Copie à la première utilisation** (doctrine du catalogue de matières de la Forge) : le décor reste entier si
  l'élément quitte ensuite la Bibliothèque. Une image est désignée par son NOM de fichier seul, ramenée à 2 048 px,
  sa transparence gardée (`services/studiov_images.py`, référence `img:<id>`) ; un modèle 3D entre dans les objets du
  studio (`studiov_objets.depuis_bibliotheque` : la version allégée de l'Établi d'abord, sinon la dernière ; il passe
  la même lecture que tout GLB, plafond de triangles compris). La même source, inchangée, n'est copiée qu'une fois.
- **Où va une image** : trois objets neufs — `tableau` (encadré), `logo_mural` (détouré, rétroéclairé si on lui donne
  une couleur), `kakemono` (sur pied, l'image couvre la toile) — ; un écran du décor (`ecrans[].image`, source
  `image`) ; l'enseigne (`enseigne.source = "image"`), qui garde ses styles néon, rétroéclairé, caisson.
- **Droits** : ce que l'utilisateur a généré est à lui (tous droits, rien à citer). Une image importée dans la
  Bibliothèque garde la licence que la Bibliothèque lui connaît : CC BY = créditée dans les crédits du décor, licence
  inconnue = signalée « à vérifier ».

## 10. Lot SVC — le catalogue de produits réels (15/11)

Référence donnée par l'utilisateur : un post de @anxuanng (X, 05/11/2026) — « Amazon made 3D models of 7,953 real
products it sells. I packed all 165 GB into about 12 GB of GLB for three.js » — et son dépôt Hugging Face
`codepawl/abo-glb`.

**Ce que c'est.** Amazon Berkeley Objects (ABO) : 7 953 modèles 3D de produits réellement vendus, chacun à sa taille
réelle en mètres, Y vers le haut, avec ses cartes PBR. L'édition `abo-glb` les ramène de 165 Go à 12 Go : textures WebP
de 2 048 px, géométrie compressée en Meshopt (`EXT_meshopt_compression`, `KHR_mesh_quantization`), triangles
inchangés. 1,2 Mo et 18 000 triangles en médiane. Chaises 1 184, canapés 859, tapis 817, art mural 599, tables 584,
lampes 345…

**Licence.** CC BY 4.0, vérifiée à la source (amazon-berkeley-objects.s3.amazonaws.com) : usage commercial permis,
crédit à Amazon.com obligatoire, lien vers la licence, changements signalés. Les noms de produits et de marques
(AmazonBasics, Rivet, Stone & Beam…) restent des marques : la licence ne donne aucun droit dessus.

| # | Chez eux | Chez nous | Décision |
|---|---|---|---|
| C1 | 12 Go à télécharger d'un bloc | l'installeur ne livre aucun modèle | RIEN n'est livré : la liste (9 Mo) se charge sur un geste, une vignette quand le produit s'affiche, un modèle quand on le pose. `services/studiov_catalogue.py` est le SEUL module du studio à ouvrir le réseau, par UNE fonction, vers une RÉVISION FIGÉE du dépôt ; aucun chemin ne vient de l'écran |
| C2 | Meshopt + WebP (copie `objects/`), ou KTX2 (copies `objects_ktx2/`, `lods/`, `engine/`) | l'import refusait toute compression ; three.js embarque le décodeur Meshopt, pas le transcodeur Basis | on prend `objects/` ; Meshopt est ACCEPTÉ à l'import (Blender 5.3 le lit aussi) ; Draco et Basis restent refusés |
| C3 | « every product drops in at real size » | un modèle importé garde déjà sa taille, base au sol | pose d'après l'origine du fichier : `sol` (base à y = 0), `mur` (centré, le dos à z = 0 : art mural, miroirs, horloges), `plafond` (pendu : suspensions) ; gardée dans la fiche de l'objet, suivie par le moteur, le plan et l'objet neuf |
| C4 | 98 types de produit en anglais, dont de très vagues (« home », « home furniture and decor ») | des familles pour le décorateur | 12 familles FR/EN ; un type vague est rangé d'après le nom du produit ; la recherche accepte « chaise » comme « chair » |
| C5 | 64 Mo de mémoire graphique par modèle (trois cartes de 2 048 px) | cible : portable à carte intégrée | en qualité légère, chaque carte est ramenée à 1 024 px avant son premier envoi à la carte graphique (un quart de la mémoire) ; 178 modèles de plus de 300 000 triangles sont écartés de l'index |
| C6 | crédit laissé à l'utilisateur | les crédits du décor (lot SVO) | la licence CC BY est portée par la source (`abo`, non déclarable à l'import d'un fichier) ; les crédits du décor citent tous les produits d'UNE ligne : titres, Amazon.com, CC BY 4.0 et son adresse, fichiers recompressés par CodePawl, adresse du dépôt |
| C7 | moteur 67.js / Crucible (MIT, piloté par agent) | three.js + Blender | non repris |

Intégrité : la taille du modèle reçu doit égaler celle de l'index (révision figée), il passe ensuite la même lecture
que tout GLB. Les dimensions d'un GLB sont désormais mesurées avec les transformations de ses nœuds et la
normalisation de ses entiers (un modèle quantifié n'a ses mètres que par elles).

**Luminaires.** Un luminaire du catalogue est rangé « lumineux » dans sa fiche (famille des luminaires ; un bougeoir
ne l'est pas, sauf si le nom du produit dit pendant, lamp, light… : Amazon range des suspensions parmi les bougeoirs).
Le moteur lui pose une lueur à son FOYER — le centre de sa partie haute pour une lampe posée, de sa partie basse pour
une suspension, de son corps pour une applique, mesuré sur ses sommets — et une vraie lumière pour les premiers du
décor seulement (2 en qualité légère, 4 en haute). La couleur de l'objet règle sa lumière.

**Assistant et guide.** L'assistant « Demander » connaît l'entrée du studio (« Voir les décors »), « Personnaliser ce
décor » et les éléments de l'onglet Catalogue (5 fiches, un parcours dans AGENT.md) ; le guide a sa section « Tourner
dans un studio virtuel » (chapitre « Filmer l'app et passer en direct », scène capturée en FR et en EN). Les AUTRES
onglets du décorateur (Style, Matières, Objets, Bibliothèque, Imports, Lumières, Caméras, Enseigne) restent à
documenter : lot SV10.

Reste : les copies KTX2 et leurs niveaux de détail (il faudrait embarquer le transcodeur Basis ; la réduction des
textures en qualité légère couvre le besoin de mémoire) ; garder plusieurs produits choisis avant de les poser ; le
reste du décorateur dans le guide et l'assistant (SV10).
