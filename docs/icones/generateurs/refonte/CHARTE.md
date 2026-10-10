# Charte « Deepotus Glyph » — refonte complète des icônes (PC + compagnon mobile)

Application professionnelle de création (vidéo, 2D, 3D) au thème sombre. Les icônes doivent être riches, très lisibles, et ne jamais prêter à confusion.

## 1. Principes non négociables
1. **Une fonction = une icône. Une icône = une fonction.** La même fonction reçoit la même icône partout (PC, labs, mobile). Deux fonctions différentes n'ont jamais le même dessin, même dans des écrans différents.
2. **Silhouette unique.** Chaque icône doit se reconnaître à 16 px **en aplat d'une seule teinte**, sans compter sur l'opacité. Deux icônes dont les silhouettes pleines se confondent sont refusées.
3. **Une écran (nav) ne ressemble jamais à une action.** Une entrée de navigation désigne un lieu, une action désigne un verbe.
4. **Emojis** : seulement comme CONTENU (emojis insérés dans un post / une légende, sélecteur d'emojis, étiquettes de types de suggestions du menu Quick). Jamais comme bouton, onglet, titre, état ou outil.
5. **Logos tiers** (YouTube, Instagram, TikTok, X, Telegram, Figma…) : famille `reseau`, logo monochrome officiel, jamais redessiné à main levée (source à intégrer : simple-icons, CC0). Ne pas les dessiner ici : laisser une entrée avec `rendu` vide et `source_logo`.

## 2. Grille et géométrie
- `viewBox="0 0 24 24"`, zone utile 20 × 20 (de 2 à 22). Rien hors de 1–23.
- Gabarits optiques : cercle Ø20 · carré 18 × 18 · paysage 20 × 16 · portrait 16 × 20. La masse visuelle d'une icône doit égaler celle de ses voisines.
- Épaisseur minimale d'une partie pleine : **2 unités**. Espace minimal entre deux masses (ou découpe) : **1,6 unité**. (À 16 px, 1 unité = 0,67 px.)
- Bords droits principaux posés de préférence sur des multiples de 1,5 (tombent sur le pixel à 16 px).
- Rayons : 1,4 sur les rectangles extérieurs, 0,8 sur les petits éléments. Famille `cat` : angles vifs (rayon 0).
- Coordonnées arrondies au dixième.

## 3. Deux tons
- **Sujet** : `opacity` 1 (implicite). **Support / contenant / trace** : `opacity=".38"`. Aucune autre valeur.
- Le sujet porte le sens ; le support donne le contexte (le bac de « importer », la feuille de « dupliquer », le trait laissé par le pinceau).
- Découpes uniquement par `fill-rule="evenodd"` dans le même tracé. Jamais de forme peinte en couleur de fond.
- **Lisible en un seul ton (règle du monochrome).** Le sujet ne se pose JAMAIS par-dessus le support : le support est évidé à l'emplacement du sujet, avec une **réserve de 1,4 à 1,6** tout autour (evenodd). Ainsi, rendu dans une seule teinte (notification mobile, masque CSS, icône Windows, impression), le dessin reste identique en silhouette et les icônes restent distinctes. Contrôle : le banc rend chaque icône avec toutes les opacités à 1 et compare les silhouettes deux à deux ; recouvrement (IoU) ≥ 0,85 = à revoir, ≥ 0,92 = refusé.
- Conséquence : un « contenant plein » (carré, disque) ne sert jamais de support seul pour toute une famille ; c'est la forme du SUJET qui fait la silhouette, le support l'habille.
- Tout en `fill="currentColor"` posé sur la balise `<svg>`. Aucun `stroke`, sauf éléments filaires : arcs (flèches circulaires), anses (cadenas), ondes, courbes, tracés. Alors `fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"` sur ce seul élément (valeur du kit et du §15, à ne pas changer).

## 4. Grammaire des modificateurs (pour la richesse ET la cohérence)
Un modificateur est un **badge** posé dans le quart bas-droit (cercle Ø9 centré 18,18, ou glyphe équivalent), au ton sujet, séparé du dessin de base par une **réserve de 1,4** (découpe evenodd dans la base). Il s'emploie toujours avec le même sens :
| Badge | Sens | Exemples |
|---|---|---|
| plus | créer / ajouter un élément de ce type | nouveau dossier, ajouter un calque, zoom avant |
| moins | retirer / réduire | zoom arrière, retirer du groupe |
| étincelle | produit par l'IA (payant) | générer une image, générer une voix |
| flèche sortante ↗ | ouvrir ailleurs / externe | ouvrir dans le navigateur, ouvrir dans Quick |
| coche | validé / terminé | tâche faite, post publié |
| horloge | programmé / en attente | post programmé |
| cadenas | verrouillé (variante d'objet) | verrou de position (Photolab) |
Ne pas inventer d'autre badge sans l'ajouter à ce tableau (champ `badge` du lexique).

## 5. Familles et nommage
`dz-<famille>-<nom>` ; nom en français, minuscules, sans accent, mots séparés par des tirets.
`nav` (lieux : écrans, labs, panneaux principaux) · `cat` (catégories, angles vifs) · `action` (verbes communs à toute l'app) · `etat` (états, statuts, propriétés binaires) · `media` (types de média et transport) · `edit` (édition d'objets : alignement, ordre, transformation, booléens, texte) · `outil-vec`, `outil-px`, `outil-photo` (outils de barre d'outils, un outil = un geste) · `calque` (types de calques, réglages) · `lab3d` (3D, impression, matières) · `marque` (Deepotus) · `reseau` (logos tiers).
Un même dessin d'outil commun à plusieurs labs (main, zoom, pipette, texte…) vit dans UNE seule clé de la famille où il est le plus employé ; les autres labs la réutilisent.

## 6. Paires et séries — dessinées ensemble, même base
importer/exporter · télécharger/envoyer vers · visible/masqué · verrouillé/libre · lecture/pause/arrêt/précédent/suivant · annuler/rétablir · zoom avant/arrière · grouper/dégrouper · monter/descendre (pile) · 6 alignements · 2 distributions · 4 booléens · développer/réduire (chevron unique orienté par CSS) · succès/avertissement/erreur/information/attente.

## 7. Tailles d'emploi
- PC : 16 (listes denses, menus), 18 (barres d'outils, rail), 20–24 (en-têtes, vides).
- Mobile (compagnon Expo) : 24 dp dans la barre d'onglets et les en-têtes, 20 dp en ligne ; cible tactile ≥ 44 pt / 48 dp autour de l'icône. Même SVG que le PC, rendu par `react-native-svg` (`SvgXml` ou composants générés), couleur par la prop `color`.
- États : repos `--txt-mid`, survol `--txt-hi`, actif `var(--cat)` ou or de marque, destructif au survol `--fail`, désactivé opacité .4 sur l'élément porteur (jamais dans le SVG).

## 8. Accessibilité
L'icône est `aria-hidden="true" focusable="false"` ; le sens est porté par le bouton (`aria-label` traduit par dzT, `title`). Aucune icône seule pour une action destructive sans libellé ou infobulle.
