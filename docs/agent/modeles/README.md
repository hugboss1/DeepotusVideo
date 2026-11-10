# Fiches modèle — notes de maintenance

Pour les mainteneurs. Ni l'assistant ni l'utilisateur ne lisent ce fichier ; aucune fiche n'y renvoie.

- Contrat : `MODELES.md` (même dossier).
- Conception : `docs/superpowers/specs/2026-11-09-fiches-modeles-scenario-design.md`.
- Plan : `docs/superpowers/plans/2026-11-09-fiches-modeles.md`.
- Relevé des sources : `docs/superpowers/specs/assets/2026-11-09-scenario-skills/`. Il contient environ 1 300 faits
  étiquetés tirés des 171 skills de https://github.com/scenario-labs/skills, relus au commit b96506d du 08/11/2026 :
  - `images.md` ;
  - `video.md` ;
  - `audio_3d.md` ;
  - `transverse.md` ;
  - `appliques_experts.md` ;
  - `index-skills.txt`.
- Licence : les skills de Scenario sont publiés sous MIT. Les fiches reformulent leurs faits sans copier de texte.
  Mentions dans `docs/licences/scenario-mit.md`.

## Journal

| Date | Lot | Contenu |
|---|---|---|
| 2026-11-09 | F0 (t475) | Contrat, tronc commun FR/EN, service `modeles_fiches`, banc et mutations |
| 2026-11-09 | F1 (t476) | Routes /api/modeles, outils modeles_lister / modele_fiche, boîte « modeles », « ? » des sélecteurs et de la pastille |
| 2026-11-09 | F2 (t477) | 9 fiches vidéo FR/EN (19 modèles), colonnes nég./son, règles communes continuité et orbite, épreuve d'application |
| 2026-11-09 | F3 (t490) | 8 fiches image et détourage FR/EN (gpt-image, ideogram, recraft, nano-banana, seedream, qwen-image, flux, detourage), colonnes image du bloc « Membres » (qualité, résolution, références, transparent, retouche, paliers low/high), épreuve d'application |
| 2026-11-10 | F4 (t491) | 17 fiches son et 3D FR/EN (elevenlabs, voicebox, sonilo, mirelo, foley, lyria, minimax-music, stable-audio, ace-step, mureka, cassetteai, tripo, hunyuan3d, trellis, rodin, meshy, sam3-objets), natures `voix` et `modele3d` au catalogue, colonnes son et 3D du bloc « Membres », épreuve d'application |
| 2026-11-09 | F6.1 (t478) | Palier de qualité de GPT Image (2, 2.5, direct et fal) et d'Ideogram 4.5 : `pricing.IMAGE_QUALITES`, choix par modèle dans la pastille, devis et garde au palier servi. Les fiches image (F3) le citeront |
| 2026-11-09 | F6.2 (t479) | Réécriture du prompt d'Ideogram (`enable_prompt_expansion`, texte → image) coupable par modèle : corps `reecriture` ou réglage `image_reecriture:<id>`, interrupteur dans la pastille ; sans choix, défaut fal (active) |
| 2026-11-09 | F6.3 (t480) | GPT Image via fal en plusieurs références (16 au plus) : façade, `image_providers.multi_references` (identité de l'espace en retouche, planche de style du Studio 3D), devis 0,012 $ par référence (`pricing.IMAGE_REF_USD`) |
| 2026-11-09 | F6.4 (t481) | Nano Banana Pro et 2.1 : résolution 1K / 2K / 4K (`pricing.IMAGE_RESOLUTIONS`, rangée « Résolution » de la pastille, réglage `image_resolution:<id>`) et 14 références (`image_providers.ref_max`) ; la retouche suit aussi qualité et résolution |
| 2026-11-09 | F6.5 (t482) | Seedance 2.5 en 1080p : membre à part `seedance-2.5-1080p` (1,164 $/s), servi seulement si on le choisit ; « seedance-2.5 » reste plafonné à 720p. Brouillon + finalisation NON branchés : fal ne publie aucun endpoint qui finalise un `draft_id` |
| 2026-11-09 | F6.6 (t483) | `audio_force` sur les cinq modèles vidéo sans interrupteur qui livrent une piste (MiniMax H3, Gemini Omni ×2, Kling v3 Turbo Pro, Kling 4.0) : le pipeline la retire au téléchargement ; Membres dit « retiré » ; fiches Gemini Omni, MiniMax, Kling FR/EN réécrites |
| 2026-11-09 | F6.7 (t485) | Meshy 7.1 et Rodin 2.5 via fal (schémas relus) : `model_type` de Meshy figé à standard, polycount refusé sans remaillage ; HighPack de Rodin (+0,80 $, devis) et cinq maillages ajoutés. La voie Meshy directe exposait déjà pose, topologie, polycount et remaillage |
| 2026-11-09 | F6.8 (t486) | Musique : `bpm` (40-220) écrit dans le prompt (aucun modèle n'a de champ tempo) ; instrumental de Lyria 3 et 3.5 par le négatif ; prix relevés (Lyria 3 0,04 $, MiniMax 2.6 0,15 $, Lyria 3.5 0,10 $, MiniMax Music 3 0,002 $/s, Stable Audio 3 0,0376 $) |
| 2026-11-09 | F6.9 (t487) | Balises d'émotion ElevenLabs : `VoiceoverService.generate` retire les balises v3 CONNUES avant tout moteur qui ne les lit pas (Multilingual v2, Flash v2.5, Voicebox) — narration d'épisode, animatique et lecture de l'assistant n'avaient pas ce filtre. La fiche voix (F4) le citera |
| 2026-11-09 | F6.10 (t488) | Fond transparent : GPT Image 2 via fal ouvert (schéma relu) ; un fond transparent écrit dans le prompt pose le champ `background` sur un modèle capable, sinon la réponse le dit (`notes`) ; `transparent` au catalogue. Fin du lot F6 |
| 2026-11-09 | FDA (t489) | Atelier DA : paramètre interne `methode` de la planche de personnage (actuel / ancre / ancre_multi, défaut actuel inchangé) et `face_maitre` ; banc `scripts/banc_da_coherence.py` (devis seul sans `--confirme`, tir isolé dans un dossier jetable, M1-M6, rapport, vote). Tir sur accord |
