# Épreuve d'application — fiches son et 3D (lot F4, t491, 10/11/2026)

Protocole :
- **Agent** : un agent vierge (« Directeur son et 3D »), sans accès au dépôt ni au web.
- **Lectures permises**, sur le backend de preuve (port 8794, sans clé, aucune dépense) :
  - `GET /api/ia/catalogue?nature=voix|sfx_texte|sfx_video|musique|modele3d|objets3d` ;
  - `GET /api/modeles/index` ;
  - `GET /api/modeles/fiche`.
- **Trois briefs**. Pour chacun, il rend : modèle, prompt ou texte, réglages, coût estimé et suite.

## Résultat

| Brief | Choix | Conforme aux fiches |
|---|---|---|
| A. Voix off française de 45 s, chaleureuse, chuchotement final, et musique de fond instrumentale, budget serré | Voix : brouillon Voicebox, final Eleven v3 (stabilité Créative, balise `[whispers]`) ; repli Multilingual v2. Musique : Stable Audio 3, 45 s, graine fixée ; repli CassetteAI | Oui : seule balise, aucun autre crochet ; ton jamais écrit dans le script ; pauses par la ponctuation ; Lyria écarté (durée fixe) ; pas de « no vocals » ; un seul tempo |
| B. Bruitage d'un clip de 8 s sans perdre la voix | Sonilo 1.1 vidéo, « Garder la voix », description vide d'abord ; repli Kling vidéo → son ; écarte les modèles qui rendent une vidéo sonorisée | Oui : clip coupé au plan utile ; un plan à la fois ; contrôle de doublon de voix au mixage |
| C. Mascotte (une vue de face) en modèle 3D riggable pour Godot, brouillon d'abord | Brouillon de forme TripoSR ou Hunyuan local ; Rodin 2.5 en A-pose (palier bas puis défaut, même graine) ; repli Meshy 7.1 | Oui : pose demandée au moteur (une seule vue) ; HighPack évité pour le temps réel ; GLB gardé ; rig après validation de la géométrie |

## Manques relevés et suite donnée

1. **Colonne « prompt » lue comme « accepte une description »** (Sonilo et Mirelo vidéo affichaient « non »).
   Corrigé : la colonne s'appelle « prompt requis » / "prompt req." (le catalogue dit « exige une description »).
2. **Meshy 7.1 : la fiche dit qu'il pose un personnage, le catalogue disait non ; Rodin se disait « la seule
   famille ».** Le code envoie la pose aux deux (`moteurs3d_neufs.POSE`). Corrigé : catalogue `tpose` vrai pour
   Meshy 7.1, fiche Rodin « une des deux familles ».
3. **Plage de durée de Kling vidéo → son inconnue.** Corrigé : le catalogue sert `video_s` (durée de la vidéo
   acceptée) et la colonne « s » l'affiche.
4. **« Garder la voix » contre « la piste d'origine ne guide jamais ».** Corrigé : le bruitage suit l'image, la piste
   d'origine ne sert qu'à garder la voix. Son effet exact reste « à confirmer » au premier tir.
5. **« Phrases complètes » des règles communes contre les exemples de musique en descripteurs.** Corrigé : la règle
   vaut pour l'image et la vidéo ; le son suit sa fiche.
6. **PBR affiché à tort** (constat de rédaction) : le drapeau commun valait vrai pour tous les moteurs neufs.
   Corrigé au catalogue : trois états lus au schéma (vrai, « au choix », faux).
7. **Palette des balises d'Eleven v3, liste des voix, débit de lecture** : non listés. Hors fiches (données d'écran) :
   à servir par un outil d'agent (F5).
8. **Prix « à mesurer »** (ElevenLabs SFX via fal, Mirelo, Stable Audio 3 SFX, Hunyuan Foley, ThinkSound, SAM 3) et
   suppléments non chiffrés (HighPack, texture coupée de Meshy, Geometry de Hunyuan v2) : à relever par tirs de
   preuve, avec accord de dépense.
9. **Réglages de Rodin 2.5 (paliers, `quality_mesh_option` par palier), service et coût du rig, export Godot
   (squelette, échelle)** : à reprendre dans `recommander_modele` (F5) et le métier 3D.
10. **Aucune fiche pour retoucher l'image de départ** (bras écartés) : les fiches image de F3 couvrent la retouche ;
    un renvoi explicite sera ajouté par `recommander_modele` (F5).

## Constats produit (relevés par les rédacteurs, non corrigés ici)

- Voix : `sonvfx.voix.vbox_balises` dit encore « le texte part tel quel » (faux depuis t487) ; repli silencieux sur
  ElevenLabs quand Voicebox ne répond pas (page Voix off) ; « Langue du texte » jamais envoyée ; `style` non exposé.
- Musique : `bpm` et le négatif libre jamais envoyés par un écran ; tempo en double avec une vignette d'ambiance ;
  description et paroles coupées sans avertir au-delà de leur limite.
- Effets : « Générer des SFX » tire toujours deux variations ; Stable Audio 3 SFX part à 30 s sans durée réglée ;
  `loop` jamais envoyé.
- 3D : vues générées et ré-exports non comptés au devis des moteurs neufs ; ré-export d'un format manquant tiré aux
  réglages par défaut ; quad de Tripo P2 inatteignable depuis Créer ; aucun écran n'envoie `quality` ; passe HD
  `refine` sans écran ; boîtes et seuil de SAM 3 absents de l'Atelier.
