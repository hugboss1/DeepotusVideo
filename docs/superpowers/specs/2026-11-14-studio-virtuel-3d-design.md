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
