# Plan — Fiches modèle (d'après scenario-labs/skills) + banc Atelier DA (09/11/2026)

Conception : `docs/superpowers/specs/2026-11-09-fiches-modeles-scenario-design.md`. Ordre décidé par l'utilisateur :
F0 → F1 → F2 (fiches vidéo) → F6 (réglages de coût) → FDA (Atelier DA) → F3 → F4 → F5 → F7 → F8.
Numéros : F0 = t475 ; les suivants à attribuer au suivi des chantiers.
Une tâche = une branche, une PR, son banc, ses mutations ; base = origin/main (le dossier local est en retard).

Règles transverses (pièges déjà rencontrés) :
- **Nouvelle boîte d'agent.**
  - Retrancher la boîte dans `test_agent_outils` (`test_seulement_dix_outils`).
  - L'ajouter aux 9 agents dans `agent_metier.ACTIFS` et au MCP.
  - Mettre à jour `test_methodes` 4.1, `test_briques` O1 et `test_agent_metier` A1.
- **`agent_outils` n'importe jamais `app.api`.**
- **Clés i18n en minuscules.**
  - Un nouveau `HTTPException` demande sa traduction dans `scripts/i18n_l10_traductions.json`, puis le passage de
    `i18n_l10_erreurs.py`.
- **`frontend/shared/*` est recopié à l'identique** dans `frontend/dist/shared/`.
  - Aucun `border-radius` littéral (`test_charte_bords`) ; seulement des jetons de `dz-charte.css`.
- **AGENT.md est plafonné** (environ 24 650 caractères) : une seule ligne ajoutée, en resserrant ailleurs. Après toute
  modification visible, passer par le skill `connaissance-agent`.
- **Rouges préexistants sur main, à ne pas imputer au lot** :
  - `diffusion_ecran` 6 ;
  - `whatsapp_ecran` 2 ;
  - `whatsapp_page_ecran` 1.4 ;
  - `agents_md` ;
  - `hygiene_lanceurs` (studio).
- **Backend de preuve isolé** sur un port libre (8797 ou 8799), **sans clé Anthropic**, pour prouver sans dépenser.

---

## F0 — Contrat et tronc commun (0 $)

**Fichiers**
- `docs/agent/modeles/MODELES.md` : le contrat adapté de l'AGENTS.md de Scenario, en français, pour les mainteneurs.
  Il couvre :
  - le format et le front-matter (`famille`, `natures`, `ids`, `description` « À utiliser quand… » de 500 caractères
    au plus, `voies`, `releve`, `source`) ;
  - le plan en quatre parties et le budget (cible 600 mots, maximum 1200) ;
  - la règle « versions = données » (aucun plafond du registre recopié) ;
  - la règle « méthodes et métiers sans nom de modèle », avec la liste blanche des outils locaux déterministes ;
  - le glossaire ;
  - les règles d'écriture ;
  - la validation (banc puis épreuve d'application) ;
  - la mention MIT.
- `docs/agent/modeles/fr/_commun.md` et `en/_commun.md` : le tronc commun de règles de prompt (§2 de la conception).
- `docs/agent/modeles/README.md` : sources, dates, commit relu (b96506d), lien vers le relevé.
- `backend/app/services/modeles_fiches.py` :
  - `charger(langue)` lit et valide les fiches ;
  - `fiche(famille_ou_id, langue)` rend le corps, le tronc commun et le bloc « Membres » généré depuis `catalogue_ia`
    (durées, ratios, résolutions, image de fin, audio, négatif, seed, prix, clé présente) ;
  - `famille_de(id)` ;
  - `index(langue)` rend les familles et leurs descriptions.
- `backend/tests/test_modeles_fiches.py`. Le banc **s'active par nature** : une nature n'est contrôlée en couverture
  qu'une fois sa première fiche écrite, ce qui laisse F0 vert sans fiches. Il vérifie :
  - le front-matter et le plan ;
  - la parité FR/EN ;
  - le budget ;
  - les ids existants ;
  - la couverture : chaque id des natures déclarées appartient à une seule fiche ;
  - qu'aucun nombre de durée ou de ratio du registre n'est écrit dans un corps ;
  - qu'aucun nom de modèle génératif n'apparaît dans `docs/agent/metiers/*.md` ni dans `knowledge/methodes.json` (le
    « Seedance » de `monteur.md` est à réécrire en capacité).
- `scripts/mutations_modeles_fiches.py` : id retiré, durée fausse, description trop longue, fiche EN manquante, nom de
  modèle dans un rôle métier.
- `AGENTS.md` : une ligne dans « Fichiers clés » et la règle « nouveau modèle = entrée de registre + prix + membre d'une
  fiche ».
- `docs/licences/scenario-mit.md` : section « Fiches modèle » ; les 171 skills sont sous MIT.

**Fini quand** : le banc est vert, les mutations sont toutes tuées, et `monteur.md` ne nomme plus aucun modèle.

## F1 — Accès : route, outils, « ? » des sélecteurs (0 $)

- **Route `GET /api/modeles/fiche?cle=<famille|id>&langue=fr|en`** et **`GET /api/modeles/index`** : gratuites, en
  lecture, ouvertes aux appareils appairés comme `/api/ia/catalogue`.
- **Outils d'agent** (boîte « modeles », lecture) :
  - `modeles_lister(nature)` : `catalogue_ia` pour toute nature ;
  - `modele_fiche(cle, langue)`.
  - `modeles_video` reste un **alias** : boîte « chapitres » inchangée, aucun banc cassé.
- **« ? » dans `frontend/shared/dz-modeles-ia.js` et `dz-champ-ia.js`** :
  - un bouton à droite du sélecteur ouvre un panneau qui affiche la fiche de la famille du modèle choisi, rendue
    depuis le markdown sans dépendance ;
  - « Fiche à venir » quand la famille n'en a pas encore ;
  - clés i18n `modeles.fiche.*` dans `frontend/shared/i18n/` ;
  - copie identique dans `dist/shared`.
- **Bancs** :
  - `test_modeles_routes` ;
  - `test_agent_modeles` ;
  - `frontend/shared/qa/modeles_fiche.test.mjs`, avec l'ordre des voies et le prix inchangés (`test_encarts_ia`
    reste vert).
- **Mutations.**
- **Connaissance de l'assistant** : skill `connaissance-agent` (nouveau bouton) et une ligne dans AGENT.md.
- **Preuve** : sur le backend de preuve, le « ? » est ouvert en FR puis en EN, avec des captures.

## F2 — Fiches vidéo FR/EN (0 $)

Neuf familles. Chaque fiche part de `docs/superpowers/specs/assets/2026-11-09-scenario-skills/video.md`, complété par
`transverse.md` (modération, coût) et `appliques_experts.md` (faits chiffrés).

| Fiche | Ids Deepotus | Sources principales |
|---|---|---|
| seedance | seedance-v1-pro, -2, -2-fast, -2.5 | scenario-seedance, -drafts, -storyboard, -music-video |
| kling | kling-v3-pro, -standard, -turbo-pro, kling-v4 | scenario-kling |
| veo | veo-3.1(-fast, -lite)-fal, *-google | scenario-veo |
| wan | wan-3.0 | scenario-wan |
| minimax-video | h3-max | scenario-minimax-video |
| ltx | ltx-2.5-fast, -pro | (aucune skill : relevé fal t408 + règles communes) |
| pixverse | pixverse-v6 | (aucune skill : règles communes) |
| gemini-omni | gemini-omni-flash(-google) | scenario-gemini-omni |
| flux-3-max | flux-3-max | (relevé t407 + règles communes) |

- Chaque fiche a ses quatre parties et une ligne `source:`. Les faits sont **reformulés**, sans copie.
- Les écarts relevés dans la conception (§3.E : h3-max 768P/1080P, prix de Gemini Omni par résolution, audio sans
  interrupteur) sont **notés comme à revérifier** dans la fiche. Ils ne sont pas corrigés dans le registre à cette
  étape.
- **Épreuve d'application réduite** (0 $) : sur le backend de preuve, demander à l'agent trois briefs vidéo :
  - teaser vertical de 8 s ;
  - plan qui garde un personnage ;
  - clip musical.

  On vérifie qu'il lit la fiche, choisit un membre compatible et écrit un prompt conforme (mouvement seul, une
  caméra, son nommé en positif). La transcription est jointe à la PR.

## F6 — Réglages de coût (tirs de preuve sur accord)

Un réglage = une sous-tâche. Pour chacun :
- relire le **schéma fal** du jour ;
- ajouter le paramètre au registre (`VIDEO_MODELS` / `FAL_IMAGES` / `MUSIC_MODELS`…) et au prix ;
- l'ajouter au sélecteur ;
- mettre la fiche à jour ;
- banc ;
- **un tir de preuve au palier le plus bas**, après devis et accord.

Ordre : palier de qualité GPT Image et Ideogram → `magic_prompt` d'Ideogram → plusieurs références GPT via fal →
résolution et 14 références de Nano Banana → brouillon et finalisation de Seedance 2.5 → drapeau `audio_force` → Meshy
(pose, remesh, polycount) et Rodin (palier) → musique (bpm, instrumental, lyrics_optimizer) → balises ElevenLabs
limitées à v3 → fond transparent.

## FDA — Banc comparatif de l'Atelier DA (environ 7,5 $, plafond 10 $, sur accord)

Protocole complet : §8 de la conception.

1. **Paramètre interne `methode`** (« actuel » par défaut, puis « ancre » ou « ancre_multi ») dans
   `generate_bible_reference` :
   - il est enregistré dans la recette ;
   - « ancre » fait le contrôle d'identité du corps de face, construit les prompts base + delta et les rend positifs ;
   - « ancre_multi » ajoute les références visage + corps (Nano Banana) ;
   - rien ne change pour l'utilisateur ;
   - banc `test_atelier_methode` : la recette, le texte de base identique à l'octet, la profondeur de chaînage égale à 1
     en mode ancre, « actuel » inchangé à l'octet.
2. **Script `scripts/banc_da_coherence.py`** :
   - devis puis arrêt ;
   - avec `--confirme` et `--max-usd 10`, il tire sur le backend de preuve **avec clés**, sous `plafonds` ;
   - M1 à M6 calculés ;
   - `rapport.md` et `vote.html` (vote enregistré dans `vote.json`).
3. **Tir**, seulement après ton accord sur le devis et sur le corpus (Elias du teaser CHARGE ou non).
4. **Vote** dans `vote.html`, puis décision selon la règle écrite à l'avance.
5. **Bascule éventuelle** du défaut dans une PR séparée, plus une fiche « atelier-da » dans `MODELES.md` (méthode).

## Lots suivants (à détailler à leur tour)

- **F3** : fiches image (gpt-image, nano-banana, flux, seedream, ideogram, qwen-image, recraft) et détourage.
- **F4** : fiches son (10) et 3D (6).
- **F5** : `recommander_modele` (filtres par plafonds, règles CHOIX, prix, alternative chez un autre fournisseur,
  « brouillon d'abord »), `verifier_prompt` sans LLM, épreuve d'application à 5 briefs.
- **F7** : skill `balayage-fournisseurs-fal` sur les candidats du §3.D, entrées de registre retenues.
- **F8** : références d'identité vidéo, multi-plan Kling, prolongation, texte→vidéo, recadrage et extension
  génératifs.
