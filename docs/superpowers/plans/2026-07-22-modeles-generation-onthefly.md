# Plan (validé 22/07/2026) — Chantiers W : modèles de génération « on the fly »

Demande d'Olivier du 22/07/2026 (post-V-b) : (1) le Seedance du Studio « ne
respecte pas le prompt » ; (2) choix du modèle de génération dans le nœud ou
le panneau ; (3) exploiter les modèles/niveaux de précision ElevenLabs ; (4)
clé Google (Gemini) dans les Settings + modèles Google natifs (Gemini Omni
vidéo, Nano Banana Pro image). Décisions actées via AskUserQuestion 4/4 (§6).

## 0. Diagnostic préalable (fait, preuves en base)

Le job Seedance du 22/07 12:20 a stocké `final_prompt` = le prompt pumpfun
**mot pour mot** (vérifié via `GET /api/jobs`) : la chaîne Prompt node →
compilateur → `custom_prompt` → `PromptEngine.build_prompt` → fal est
**saine**. Cause racine du « prompt non respecté » : la **capacité du
modèle** — `fal_service.py` est verrouillé sur
`fal-ai/bytedance/seedance/v1/pro|lite/image-to-video`, et Seedance v1 en
image-to-video suit mal les transformations sémantiques complexes (logo qui
explose en pluie de pièces) : l'image source domine. Remède = W-a (choix du
modèle), pas un patch de plomberie.

## 1. Chantier W-a — Nœud vidéo multi-modèles (Studio + Quick)

Le nœud `Seedance` devient un générateur vidéo à modèle sélectionnable,
**multi-fournisseurs : fal + Google GenAI**.

- **Backend**
  - `fal_service.py` → registre `VIDEO_MODELS` {id → provider, endpoint,
    label, caps (durées, ratios, end_image?, résolution), prix/s}. Périmètre
    validé W-Q1 : conserver seedance v1 pro/lite (défaut inchangé), ajouter
    **Seedance 2.0 + 2.0 fast**, **Kling v3 pro/standard**, **PixVerse v6**,
    **Veo si présent au catalogue fal du jour**, et **Gemini Omni**
    (Google natif). ⚠ Figer les ids au démarrage du chantier via le
    catalogue fal ET `ListModels` Google — les noms fournis (ex.
    `gemini-omni-flash-preview`) sont des previews mouvants à CONFIRMER,
    certains exigent la facturation activée côté AI Studio.
  - Nouveau `google_video.py` : client Gemini Omni (generate_videos =
    opération longue → submit/poll/download), même contrat que le client fal
    (le pipeline ne voit qu'une interface) ; clé = `GEMINI_API_KEY`
    existante. Pose le client Google GenAI partagé (réutilisé W-c/W-e).
  - `schemas.py` : `video_model: Optional[str]` sur `GenerateRequest`
    (hérité par les slots seedance des templates) ; `pricing.py` : coût par
    modèle (topbar ≈ $ et cartes suivent le modèle choisi) ; gardes serveur
    (durée/ratio clampés aux caps, erreur fournisseur propre dans `job.error`).
- **Bundle** (`patch_bundle_videomodel.py`, baseline post-v1.18.0)
  - Props Seedance : `model:"seedance-v1-pro"` ; select « Modèle » en tête du
    panneau Generator (pattern `DzImgModelSel` déjà en place pour ImageGen) ;
    badge coût de carte par modèle ; les 4 branches du compilateur (solo,
    montage, spatial, UGC) envoient `video_model` ; Quick → même select.
- **Recette W-a** : même graphe (image pump + prompt pumpfun) rendu avec 2
  modèles ≠ → 2 artefacts distincts, `final_prompt` identique en base, coût
  affiché conforme, erreur propre sur modèle indisponible ; tests backend
  mapping modèle→endpoint/provider + clamps ; suites vertes ;
  `qa-videomodel.js` (sélection nœud ET Quick).

## 2. Chantier W-b — ElevenLabs : modèles + précision (+ bug résidu 0 o)

- `elevenlabs_service.py` : `model_id` paramétrable ; **défaut validé W-Q2 :
  `eleven_multilingual_v2`** (`ELEVENLABS_MODEL` configurable). Catalogue
  vérifié (docs 22/07) : `eleven_v3` (expressif, 70+ langues, 5 000 chars),
  `eleven_multilingual_v2` (qualité, 10 000), `eleven_flash_v2_5` (−50 % du
  coût, 75 ms, 40 000) — turbo déprécié. `voice_settings` déjà lus du
  persona : exposer aussi style/speed quand le modèle les supporte.
- Surfaces : Quick Voice Over + nœud Studio Voiceover (select « Modèle » +
  curseurs précision, composant partagé façon DzVoicePicker) ; Chapitres au
  défaut app. Maxlength par modèle. `pricing.py` : multiplicateur (flash 0,5×).
- **Validé W-Q4 : rouvrir les voix library/community** (compte crédité $50) :
  le picker les liste à nouveau, fallback propre si 402/403 réapparaît
  (bandeau inline existant) ; George/Brian restent les défauts.
- **Bug corrigé au passage (cause racine + test)** : un échec
  `/audio/voiceover` laisse un fichier 0 octet dans la Library (constat du
  nettoyage 22/07, mémoire `audio-library-qa-cleanup-20260722`) → écriture
  en fichier temporaire + rename atomique après succès, test de
  non-régression (échec TTS simulé → zéro résidu).
- **Recette W-b** : génération réelle 2 modèles ≠, coûts au multiplicateur,
  réglages précision persistés, voix library jouable OU erreur propre,
  échec TTS → zéro résidu, suites voix vertes.

## 3. Chantier W-c — Gemini à jour partout où utile

- Constat : la clé est **déjà saisissable** (Settings → Clés → « Google
  Gemini », aussi dans l'onboarding et les Provider defaults
  summarizer/planner) ; `gemini_llm.py` appelle déjà
  `generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`.
- À faire : `GEMINI_MODEL` `gemini-2.0-flash` → **`gemini-flash-latest`**
  (alias stable de la doc Google) + champ modèle exposé dans Settings ;
  vérifier la sonde `gemini_enabled` ; s'assurer que toutes les chaînes LLM
  (summarizer, planner, `/prompt/refine` « Refine with AI », textes Atelier)
  énumèrent Gemini ; guide § Réglages.
- **Recette W-c** : clé saisie → `/prompt/refine` et summarizer répondent via
  Gemini (log provider), santé verte, aucun changement sans clé.

## 4. Chantier W-d — Provider defaults « on the fly » (léger)

- Settings → Provider defaults : modèle vidéo par défaut des nouveaux nœuds,
  modèle TTS par défaut (image déjà en place) ; les nœuds naissent avec ces
  défauts, chaque nœud peut dévier.
- **Recette W-d** : changer un défaut → nouveau nœud le porte, nœuds
  existants inchangés, persistance après reload.

## 5. Chantier W-e — Images Google : Nano Banana Pro / 2 (ImageGen)

- Existant : `image_providers.py` a déjà **Nano Banana v1 via fal**
  (`fal-ai/nano-banana` + `/edit`, aspect map, tests).
- Ajouter **Nano Banana Pro** (haute fidélité, texte précis, 4K) et **Nano
  Banana 2** : via fal s'ils y sont hébergés (même client, coût unifié),
  sinon via le client Google GenAI posé en W-a (`gemini-3-pro-image-preview`
  / `nano-banana-2` — ids preview à CONFIRMER via ListModels). Select modèle
  ImageGen déjà en place (DzImgModelSel) : ajout d'entrées + pricing.
- Pattern d'usage cible (note d'Olivier) : **ImageGen (Nano Banana Pro) →
  nœud vidéo (Gemini Omni / Kling)** — déjà naturel dans le Studio, à
  documenter dans le guide comme recette de graphe.
- **Recette W-e** : image générée avec NB Pro (fidélité texte visible),
  édition NB conservée, coûts affichés, pipeline image→vidéo prouvé sur un
  graphe.

## 6. Décisions actées (AskUserQuestion 22/07, 4/4)

| # | Décision |
|---|---|
| W-Q1 | TOUS les modèles proposés : Seedance 2.0 + fast, Kling v3 pro/standard, PixVerse v6, Veo (si dispo fal) **+ Gemini Omni (Google natif) et Nano Banana Pro/2 (→ W-e)** |
| W-Q2 | Défaut TTS = `eleven_multilingual_v2` (surfaces déviantes possibles) |
| W-Q3 | Ordre : **W-a → W-b → W-c → W-d** (W-e ensuite, ajustable) |
| W-Q4 | Voix library ElevenLabs rouvertes avec fallback ; défauts George/Brian conservés |

## 7. Process & risques

- 1 chantier = 1 session neuve ; spec relue avant implémentation ; recette
  prouvée avant le suivant (rythme validé V-a/V-b).
- Patchers bundle en bout de chaîne (baseline post-v1.18.0), anchors comptés
  par occurrences, smoke par interception AVANT déploiement, déploiement §7
  (idle → backup → copie → relance breakaway → probe → QA installée).
- Risques : catalogues fal/Google mouvants (figer les ids AU chantier via
  API) ; previews Google exigeant la facturation (tester tôt avec la clé
  d'Olivier, échouer proprement sinon) ; paramètres non uniformes entre
  familles (mapping par famille + gardes serveur) ; coûts Veo/Kling/Omni
  plus élevés (affichage AVANT Run — topbar ≈ $) ; clés JAMAIS dans le chat
  ni le repo (Settings → .env DATA_ROOT ; mémoire `dataroot-env-bom-utf8`).
