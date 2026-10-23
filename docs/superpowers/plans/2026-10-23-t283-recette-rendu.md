# t283 — Bibliothèque → Quick / Studio : la recette de génération suit le rendu (23/10/2026)

Lot « Agent interne (PC) », brief `2026-10-23-chantier-pc-agent-interne.md`. Branche `claude/recette-biblio-t283`
(base origin/main 2658f7ab).

## Relevé (avant)

- Quick a déjà sa recette par job (`services/quick_recipe.py`, `outputs/_recipes/{job}.json`, `GET /api/jobs/{id}/recipe`)
  et « Rouvrir dans Quick » dans la fiche modale (`__dzReopenQuick` : recette Quick, sinon repli `__dzQuickFromJob`
  depuis les colonnes du job). Le repli reprend `final_prompt`, qui est le prompt EXACT envoyé (prompt libre + caméra
  + curseurs). L'ambiance « cinematic » ou « hybrid » n'ajoute aucun mot-clé.
- Les clips Seedance de la campagne (`9ba81b30…`, `3cba8ed2…`, `3dbe4363…`) ont été lancés par l'API, sans recette
  Quick ni graphe : leurs colonnes (prompt, négatif, modèle, durée, format, graine, image de départ) suffisent.
- Le menu « Envoyer vers » d'un rendu n'a aucune entrée Quick. « Studio — nouveau graphe » ne fait que re-rendre le
  clip (`ExistingRender → Render`).
- `/api/videos/upload` n'accepte aucune métadonnée. La fiche (`DzFiche`, bloc MONTAGE) ignore les rendus.
- Le prompt de la musique (Son & VFX) est dans `audio/_sfx_meta.json`, mais la fiche audio ne le lit pas. Les images
  générées par le Photolab gardent déjà leur recette (`LibraryAsset.recette`).

## Décisions de l'utilisateur (23/10)

1. Studio : nouvelle entrée « Studio — refaire la génération » (Image de départ [+ de fin] + Prompt positif et négatif
   + Seedance + Render) ; « Studio — nouveau graphe » garde son rôle.
2. Graine : nouvelle par défaut ; la case « Reprendre la graine d'origine » de la fiche la remet.
3. Imports : champ facultatif `recette` (JSON) à l'upload ET fichier `<nom>.recette.json` à côté de la vidéo.
4. Musique : la fiche audio montre aussi le prompt et le modèle gardés par Son & VFX.

## Tâches

- **B1** `services/recette_rendu.py` + `GET /api/jobs/{id}/recette` : une recette unifiée lue dans l'ordre suivant :
  1. recette Quick (le formulaire exact) ;
  2. colonnes du job ;
  3. recette d'import jointe (`_recipes/{job}.import.json`), sinon le fichier `<stem>.recette.json` à côté de la vidéo.

  Elle donne `source`, `prompt`, `negative`, `model`, `duration_s`, `aspect_ratio`, `seed`, `style`, `template_id`,
  `image`, `image_end`, `provider`, `espace_id`, `parent_job_id`, `studio` (le graphe source existe), `quick` (la
  recette brute) et `import`. Aucun coût n'est repris : l'écran le réestime.
- **B2** `/api/videos/upload` : `recette` facultative (JSON objet, 64 Ko au plus, sinon 400) enregistrée à côté du job.
- **B3** `library_fiche` : sans recette de génération, un son prend `prompt` et `model` dans `_sfx_meta.json`
  (origine « son-vfx »).
- **F** Maillon de queue `dzrecette` (après dzsonvfx, inverse `avant_dzrecette` en tête de `avant_dzsonvfx`) :
  - `__dzRecetteQuick(id, garder)` : recette → formulaire Quick. Graine neuve sauf `garder`. Ambiance « hybrid » si
    le style est hybrid, « cinematic » sinon (aucun mot-clé ajouté).
  - `__dzRecetteStudio(id, garder)` : le graphe de génération.
  - « Envoyer vers » d'un rendu : « Quick — reprendre la recette » et « Studio — refaire la génération ».
  - Fiche modale d'un rendu : panneau `DzRecetteRendu`. Il montre la source, le prompt, le négatif (replié), le
    modèle, la durée, le format, la graine et l'image de départ, plus la recette d'import (source, composition,
    variables, prompts des clips). Il porte la case « Reprendre la graine d'origine » et les deux boutons.
  - Hooks par alias : `x.useState(` reste à 731.
  - Textes : `frontend/shared/i18n/recette.json` (FR/EN).
- **Clôture** : fiches du catalogue de l'assistant (`connaissance-agent`), guide (`guide-deepotus`), preuve FR et EN
  sur 8799.

## Fini quand

Ouvrir `9ba81b30…` dans Quick redonne son prompt exact. Un import avec recette l'affiche dans sa fiche. Les bancs sont
verts, avec mutations. La preuve à l'écran est faite en FR et en EN.

## Preuves (23/10)

- Banc `backend/tests/test_recette_rendu.py` : **37/0**. Il couvre la recette unifiée (Quick, job, gabarit avec
  graphe), l'import (recette jointe, fichier posé à côté, refus 400 d'une recette illisible, d'une recette qui n'est pas
  un objet ou de plus de 64 Ko), la fiche audio Son & VFX et le maillon (aller-retour, comptes figés, CRLF, clés à
  trois segments traduites).
- Mutations : prompt saisi ignoré, recette d'upload non gardée, fiche audio sans le fichier de métadonnées Son & VFX,
  source « quick » masquée. Les quatre rougissent.
- Série ciblée de 118 bancs : les rouges restants sont tous identiques sur `origin/main`, vérifiés sur une copie
  propre (espaces ×5, i18n_l4_serveur, i18n_l6, icones_g1 3.5, montage_bundle DZ3, library_lignee I1,
  library_picker figma).
- Épingles mises à jour, en le disant :
  - `test_quick_bundle` : A3 passe de 4 à 5 appels à `__dzReopenQuick`, A5 de 3 à 4 `deepotus:quick-recipe` ;
  - le panneau se place APRÈS DzSemblables, parce que l'enchaînement DzLignee → DzFiche → DzCommentaires →
    DzSemblables est épinglé.
- Backend de preuve 8799 (données jetables) :
  - clip `9ba81b30` → « Ouvrir dans Quick » : prompt exact, image de départ, hybrid, Seedance 2.5, 5 s, 9:16, graine
    neuve ; coût réestimé, rien de lancé ;
  - clip `3cba8ed2` → « Envoyer vers › Studio — refaire la génération » : graphe Image → Seedance ← Prompt (positif
    et négatif) → Render ;
  - mix FR importé avec une recette HyperFrames : la fiche montre la composition, les variables et les prompts des
    trois clips ;
  - écrans vérifiés en FR et en EN ; la case « Reprendre la graine d'origine » redonne 433115813.
- Assistant : fiches `recette.panneau.ouvrir_quick` et `recette.panneau.ouvrir_studio` rédigées (écran Bibliothèque,
  chapitre « bibliotheque »). Elles sortent en tête pour « comment je refais cette vidéo avec le même prompt ? » (FR) et
  pour la même question en anglais. Le guide gagne la section « Refaire un rendu à partir de sa recette » (FR et EN).

## Constat hors périmètre

`/api/videos/upload` écrit `aspect_ratio="9:16"` en dur, même pour un import en 1:1 (le mix 60 s). La recette d'un
import l'ignore désormais, mais la colonne du job reste fausse : le corriger (sonder le format) serait une petite
tâche à part.
