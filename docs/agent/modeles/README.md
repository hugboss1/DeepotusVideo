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
| 2026-11-09 | F6.1 (t478) | Palier de qualité de GPT Image (2, 2.5, direct et fal) et d'Ideogram 4.5 : `pricing.IMAGE_QUALITES`, choix par modèle dans la pastille, devis et garde au palier servi. Les fiches image (F3) le citeront |
| 2026-11-09 | F6.2 (t479) | Réécriture du prompt d'Ideogram (`enable_prompt_expansion`, texte → image) coupable par modèle : corps `reecriture` ou réglage `image_reecriture:<id>`, interrupteur dans la pastille ; sans choix, défaut fal (active) |
| 2026-11-09 | F6.3 (t480) | GPT Image via fal en plusieurs références (16 au plus) : façade, `image_providers.multi_references` (identité de l'espace en retouche, planche de style du Studio 3D), devis 0,012 $ par référence (`pricing.IMAGE_REF_USD`) |
