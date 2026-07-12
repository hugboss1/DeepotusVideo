# Voix locales (Voicebox) — remplacer l'abonnement ElevenLabs

Spec d'implémentation, 2026-07-11. Étude du repo https://github.com/jamiepine/voicebox
(MIT) en vue de générer les voix off de DeepotusVideoGen localement, sans
abonnement.

## 1. Ce qu'est Voicebox

« Studio voix local-first », alternative open-source à ElevenLabs :

- **App desktop Tauri** (React/TS) + **backend FastAPI Python** séparé.
- **7 moteurs TTS** téléchargés à la demande : Qwen3-TTS (0.6B/1.7B, clonage
  zéro-shot, 10 langues), Qwen CustomVoice, LuxTTS (EN, 150× temps réel sur
  CPU), **Chatterbox Multilingual** (23 langues DONT LE FRANÇAIS, clonage
  zéro-shot, MIT/Resemble), Chatterbox Turbo (EN, tags `[laugh]`/`[sigh]`),
  TADA (1B/3B), Kokoro (82M, ultra-rapide CPU, 50 voix presets, pas de
  clonage).
- **Clonage de voix** à partir de quelques secondes d'audio, profils
  multi-échantillons.
- **API REST locale** (port 17493) : `POST /generate` (text, profile_id,
  language), `GET /profiles`, `POST /transcribe` (Whisper), `/docs` OpenAPI.
- Fonctionne **sans l'UI desktop** : `docker compose up`, ou le backend
  FastAPI seul. GPU CUDA/DirectML/ROCm/MLX, **repli CPU**.
- Textes longs : chunking + crossfade automatiques (équivalent de notre
  `generate_long`).

## 2. Empreinte ElevenLabs actuelle dans VideoGen

Tout est déjà canalisé — le remplacement est chirurgical :

| Usage | Où | Besoin |
|---|---|---|
| TTS fichier (toutes VO) | `elevenlabs_service.VoiceoverService.generate/generate_long` | texte→mp3/wav, voice_id, langue FR/EN |
| Liste des voix (casting) | `routes._fetch_11l_voices` (labels genre/âge/accent) | catalogue {voice_id, name, labels} |
| Casting par personnage (B v1.21) | `routes.suggest_entity_voice` (LLM croise fiche perso × voix) | inchangé si le catalogue a des labels |
| VO minutée par scène (C v1.22) | routes ~4254-4344 (narrateur + voix perso par segment) | inchangé (passe par VoiceoverService) |
| Pipeline Seedance + slideshow | `pipeline.py`, routes ~920/1099 | inchangé |
| Statut abonnement | routes ~2574, `pricing.py` | devient "local: gratuit" |

## 3. Options

### Option A — Voicebox en service compagnon local (RECOMMANDÉE)

VideoGen appelle l'API REST de Voicebox (127.0.0.1:17493) comme provider de
voix alternatif, sur le modèle exact de `image_providers.py` (façade
FLUX / GPT-Image / Nano-Banana).

- Nouveau `voice_providers.py` : `PROVIDERS = {"elevenlabs": …,
  "voicebox": …}` avec deux opérations : `list_voices()` (GET /profiles →
  {voice_id, name, labels}) et `tts(text, voice_id, language, output_path)`
  (POST /generate, sauvegarde du wav/mp3).
- `VoiceoverService` devient un routeur : réglage atelier `voice_provider`
  (défaut elevenlabs si clé présente, sinon voicebox si joignable).
- Casting (suggest-voice) et VO par scène marchent tels quels : ils
  consomment le catalogue et voice_id, peu importe le provider.
- Clonage de voix : se fait DANS l'UI Voicebox (profils) ; VideoGen les
  voit via /profiles. Pas d'UI de clonage à développer côté VideoGen.
- Réglages UI : un select "Fournisseur de voix" (patch bundle minime) +
  détection `GET /profiles` pour l'état "Voicebox détecté / non lancé".
- ➕ zéro dépendance lourde dans le runtime embarqué, moteurs gérés par
  Voicebox (téléchargements, GPU), MIT, mises à jour indépendantes.
- ➖ l'utilisateur doit installer/lancer Voicebox (MSI Windows ou Docker) ;
  projet jeune → figer le contrat API derrière notre façade; vérifier le
  header `X-Voicebox-Client-Id` et le format audio de sortie.

### Option B — intégrer un moteur TTS dans le backend VideoGen

Vendorer Chatterbox Multilingual (ou Kokoro) dans le runtime python embarqué.

- ➕ un seul process, pas d'app tierce.
- ➖ +3-5 Go (torch CUDA) dans l'installeur, fragile (support Pascal en voie
  d'abandon dans les torch récents), maintenance modèles à notre charge,
  duplique ce que Voicebox fait déjà bien. À ne retenir que si l'Option A
  échoue au POC.

### Option C — cloner l'app Voicebox (UI comprise)

Hors scope : VideoGen a déjà son UI voix (casting, VO par scène) ; on ne
veut que la génération.

## 4. Matériel (laptop de voyage)

GTX 1060 4 Go (Pascal) + i7-7700HQ 4c :

- Kokoro 82M : temps réel large, même en CPU — narrateur EN/FR* d'appoint.
- Chatterbox Multilingual (~350M-1B) : tient en 4 Go VRAM ; attention au
  support CUDA Pascal des torch récents → repli CPU acceptable car nos VO
  sont du BATCH (fichiers de scène), pas du temps réel.
- Qwen3-TTS 1.7B / TADA 3B : limites de la VRAM, à éviter ici.
- \* qualité FR à valider à l'oreille au POC — c'est LE critère.

## 5. Plan d'implémentation (nouvelle session dédiée)

1. **POC (avant tout code)** : installer Voicebox (MSI), télécharger
   Chatterbox Multilingual + Kokoro, générer 2 échantillons FR (narration
   30 s + réplique courte) et 1 clonage de voix FR ; mesurer le temps de
   génération (GPU puis CPU) et juger la qualité à l'oreille.
   **Recette : qualité FR jugée publiable par Olivier + vitesse < 5× durée
   audio, sinon on s'arrête là.**
2. `voice_providers.py` (façade, testable à la test_style_da) + routage
   dans `VoiceoverService` + réglage `voice_provider`.
   **Recette : test unitaire façade (stub HTTP) PASS.**
3. Catalogue casting : mapper /profiles → labels ; adapter le prompt du
   casting agent si labels plus pauvres qu'ElevenLabs.
   **Recette : suggest-voice retourne une voix Voicebox sur un perso.**
4. VO par scène + pipeline sur provider voicebox de bout en bout.
   **Recette : une scène de l'Atelier avec VO FR 100 % locale, écoutée et
   validée, ElevenLabs débranché (clé retirée) pendant l'essai.**
5. Réglages UI (select provider + état de détection), déploiement bundle.

Fallback conservé : ElevenLabs reste le défaut si sa clé est présente ;
Voicebox = alternative gratuite/offline, jamais une régression forcée.
