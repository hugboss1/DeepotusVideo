# Épreuve d'application — fiches image et détourage (lot F3, t490, 09/11/2026)

Protocole :
- **Agent** : un agent vierge (« Directeur artistique »), sans accès au dépôt ni au web.
- **Lectures permises**, sur le backend de preuve (port 8794, sans clé, aucune dépense) :
  - `GET /api/ia/catalogue?nature=image|detourage_image|detourage_video` ;
  - `GET /api/modeles/index` ;
  - `GET /api/modeles/fiche`.
- **Trois briefs**. Pour chacun, il rend : modèle, prompt, réglages, coût estimé et suite.

## Résultat

| Brief | Choix | Conforme aux fiches |
|---|---|---|
| A. Autocollant « LA TORRÉFACTION », 3 pistes pas chères, fond transparent | Ideogram 4.5 (réécriture coupée, 3 pistes en low, final high) puis détourage `local-chroma` ; repli GPT Image 2.5 Sunburst via fal (fond transparent natif) | Oui : réécriture coupée pour un nom exact ; fond uni d'une couleur éloignée du sujet ; contrôle sur fond sombre et clair ; PNG de bout en bout ; relecture lettre à lettre, accent compris |
| B. Mascotte, 3 poses cohérentes, 16:9, budget serré | Nano Banana 2.1 en 1K, deux références à rôle unique ; repli FLUX 3 | Oui : format dans le champ ; un appel par pose ; base + delta ; chaque pose vérifiée contre les photos, jamais contre la pose d'avant |
| C. Chien à poils longs : photo et vidéo de 6 s | Photo : `local-rembg` d'abord, puis BiRefNet v2 ; vidéo : aperçu sur une image, puis BiRefNet v2 vidéo ; replis Bria | Oui : local d'abord ; jumeau image avant la vidéo ; `.mov` / `.webm` gardé jusqu'au Montage ; « prix à mesurer » essayé sur une seule image |

Constat de cadre : sur le backend de preuve, tous les membres payants sont `dispo:false` (aucune clé) ; l'agent l'a
relevé et a construit ses plans quand même, ce qui est le comportement voulu.

## Manques relevés et suite donnée

1. **Pas de seed : le final en high n'est pas la piste low retenue** (Ideogram, GPT Image). Corrigé : puce dans les
   deux fiches (nouveau tirage voisin, prévoir deux finaux ou garder la piste low).
2. **BiRefNet vidéo classé « à la seconde » alors que son prix est « à mesurer ».** Corrigé : la puce dit les deux.
3. **Réglages de BiRefNet** (« réglé lourd ») sans dire ce que l'app fixe. Corrigé d'après `detourage.REGISTRE` : image
   en modèle lourd, haute résolution de travail, affinage des bords ; vidéo en modèle léger, résolution plus basse.
4. **« Un logo n'est jamais généré » contre Ideogram et Recraft.** Corrigé dans `_commun` : le logo EXISTANT d'une
   marque s'incruste ; un logo neuf se dessine (fiche Recraft).
5. **Langue du prompt implicite.** Corrigé dans `_commun` : prompt en anglais, texte affiché dans sa langue, accents
   compris.
6. **« 9 références » de Nano Banana : limite de l'app ou du fournisseur ?** Corrigé : Membres donne la limite de
   l'app.
7. **Nano Banana Pro part en 1K sans choix**, alors que 2K coûte pareil. Corrigé : puce [PIÈGE].
8. **Jumeau d'aperçu de VEED et Pixelcut vidéo non cité.** Corrigé (BiRefNet pour VEED, Pixelcut pour Pixelcut vidéo).
9. **Fond transparent natif contre `local-chroma` gratuit : aucune comparaison des bords.** Non tranché : à mesurer
   (banc de détourage, plus tard).
10. **FeyNobg, Pixelcut, Bria : aucune comparaison de qualité sur la fourrure** ; FeyNobg non décrit. À mesurer : prix
    « à mesurer » et qualité inconnue, la fiche ne promet rien.
11. **Tailles en pixels par format et par membre, formats acceptés, nombre d'images par appel** (Ideogram, Nano).
    Hors fiches : à exposer par le catalogue et `recommander_modele` (F5).
12. **Coût réel des références de Nano Banana 2.1 et arrondi des tranches d'images** (VEED, SAM 3.1). À relever par
    tirs de preuve, avec accord de dépense.
13. **Impression (DPI, CMYK, fond perdu), contour d'autocollant, assemblage d'une planche.** Hors périmètre des fiches
    modèle : relève des métiers (Card Forge, Vectorlab).
14. **Recraft et lettres accentuées, rendu « bombé » en vecteur plat.** À vérifier par un tir de preuve.

Constat produit : Recraft 4.1 vecteur n'est proposé par aucun écran (servi seulement à l'agent, sortie SVG). La fiche
le dit ; l'exposer au Vectorlab est un chantier séparé.
