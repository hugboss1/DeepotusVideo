# Balayage des fournisseurs → fal.ai (11/10/2026)

- **Code balayé :** `origin/main` b74fdf2a (PR #319), dans un worktree de lecture. Le dossier local `C:\Users\olivi\DeepotusVideo` est resté à d87cc7cc, avec 279 commits de retard.
- **Catalogue fal :** `api.fal.ai/v1/models` (la source de fal.ai/explore), soit 1 514 endpoints actifs. Les prix viennent des pages publiques des modèles (`fal_prix.py`).
- **Méthode :** skill `balayage-fournisseurs-fal`. Lecture seule : aucun tir payant, aucune modification du code.
- **Avertissement :** « performant » est jugé sur la date, la famille et la version. Aucun modèle n'a été testé ici ; les candidats sont à valider par un tir d'essai sous plafond.

## 1. Résumé

- **Où passent les appels.** L'app appelle **16 services distants** et 5 services locaux gratuits. fal porte déjà la plupart des générations lourdes : vidéo, image, 3D, musique, stems et matte vidéo, soit 18 points d'appel `fal_client`.
- **Sept clés payantes servent encore à générer** en dehors de fal : OpenAI, Anthropic, Gemini, ElevenLabs, HeyGen, Meshy et Decart.
- **Toutes ont un équivalent sur fal.** fal revend désormais ces fournisseurs sous sa propre clé : routeur LLM OpenRouter (Claude, GPT, Gemini), ElevenLabs, HeyGen, Meshy, Decart, gpt-image et Veo.
- **Verdict « une seule clé » : OUI pour la création, environ 90 % des gestes.** Restent en dehors : la publication sur les réseaux (connexion OAuth, ce ne sont pas des clés d'IA), Figma, les **avatars personnels HeyGen** et les **voix clonées stockées sur un compte ElevenLabs**.
- **Beaucoup d'ids fal de l'app sont datés** : `esrgan` et `rembg` datent de 2023, `triposr` et `tripo v2.5` de 2024-2025, `flux/schnell`, `seedream v4`, `lyria3`… Des successeurs plus récents existent pour presque toutes les familles.

## 2. Fournisseurs et clés

| Fournisseur | Clé | Usages dans l'app | Remplaçable par fal ? |
|---|---|---|---|
| fal.ai | `FAL_KEY` | Vidéo, extension, lip-sync, image et édition, upscale, détourage, matte, 3D, vues 3D, musique, stems, recast, décor | — (socle) |
| OpenAI | `OPENAI_API_KEY` | Images directes `/v1/images` (R:8502), Whisper, LLM `gpt-4o-mini`, contrôle visuel des proportions, Vectorlab, « décrire » du recast | **Oui.** Images : `openai/gpt-image-2*` (déjà dans la façade). STT : `fal-ai/elevenlabs/speech-to-text/scribe-v2` ou `fal-ai/wizper`. LLM et vision : `openrouter/router[/vision]` |
| Anthropic | `ANTHROPIC_API_KEY` | Routeur LLM (news, scripts, Atelier, traductions, planning), contrôle visuel 3D, contrôle des proportions, Vectorlab, recast | **Oui** via `openrouter/router`, `model=anthropic/claude-*`. L'endpoint OpenAI-compatible (`…/openai/v1/chat/completions`) est fourni. À vérifier : les images passent-elles dans `/vision` pour les contrôles visuels |
| Google Gemini / Veo | `GEMINI_API_KEY` | LLM, Veo natif (`google_video.py`), légendes de la Bibliothèque | **Oui.** Veo : `fal-ai/veo3.1[/fast|/lite]/image-to-video`. LLM : `openrouter/router` (`google/gemini-3.8-flash`). Légendes : `openrouter/router/vision` ou `fal-ai/moondream3-preview/caption` |
| ElevenLabs | `ELEVENLABS_API_KEY` | TTS, SFX, isolation de la voix, STT, liste des voix, solde, **clonage** (`/voices/add`), **changeur de voix** (STS, y compris en direct) | **Partiel.** Sur fal : TTS `elevenlabs/tts/eleven-v4`, `fal-ai/elevenlabs/tts/eleven-v3|multilingual-v2` ; SFX `fal-ai/elevenlabs/sound-effects/v2` ; isolation `fal-ai/elevenlabs/audio-isolation` ; STT scribe-v2 ; changeur `fal-ai/elevenlabs/voice-changer`. **Hors fal :** les voix clonées du compte (fal n'expose que les voix prédéfinies, à vérifier) et le STS en flux temps réel |
| HeyGen | `HEYGEN_API_KEY` | Avatar III/IV/V par look, photo → vidéo parlante, avatar cinématique, création de Photo Avatar, catalogues | **Partiel.** Photo + texte ou audio → `fal-ai/heygen/avatar4/image-to-video` (0,10 $/s). Lip-sync : `fal-ai/heygen/v3/lipsync/precision`. Jumeau numérique : `fal-ai/heygen/avatar5/digital-twin` (0,15 $/s). **Hors fal :** les looks et avatars personnels du compte et le cinématique |
| Meshy | `MESHY_API_KEY` | Texturage (`retexture`), rig + animations, remaillage, conversion fbx/usdz/blend, volet Meshy du Studio 3D, Card Forge mesh3d | **Presque.** Génération : `meshy/v7.1/image-to-3d|text-to-3d|multi-image-to-3d` (0,80 $, 1,20 $ texturé). Rig : `fal-ai/meshy/rigging` + `/multi-animation`. Texture : `meshy/v6-lite/retexture` (0,30 $). Remaillage : `tripo3d/tripo/remesh` ou `fal-ai/hunyuan-3d/v3.1/smart-topology`. **Hors fal :** `convert`, `resize` et `uv-unwrap`, à faire en local avec le Blender déjà intégré (T094/T096) |
| Decart | `DECART_API_KEY` | Avatar live en temps réel `lucy-2.5` (WebRTC depuis le navigateur) | **À vérifier.** `decart/lucy-2-5/realtime` existe sur fal ; la route avait été écartée (commentaire `pricing.py:62`). Il faut tester le mode WebRTC fal avant de basculer |
| Figma | `FIGMA_TOKEN` | Import de gabarits | Non (pas une IA) |
| X, Telegram, YouTube, Instagram, TikTok | OAuth / jetons | Publication et métriques du Planificateur | Non (comptes de l'utilisateur) |
| RSS, r.jina.ai, OSM/AWS terrain, GitHub, HuggingFace | aucune | News, géo, mises à jour, CLIP | Sans objet (gratuit) |
| Voicebox, Voixbox, Ollama, CLAP, Hunyuan3D local | URL locale | TTS, voix live, LLM, recherche de sons, 3D sur le GPU | Sans objet (gratuit, local) |

## 3. Comparatif par fonctionnalité

Verdicts :
- **À jour** : rien à faire.
- **↑ version** : même famille, version plus récente disponible.
- **+ ajouter** : nouvelle famille à ajouter à la liste.
- **→ fal** : bascule d'un fournisseur tiers vers fal.
- **hors fal** : à garder tel quel.

### Vidéo

| Fonction | Actuel (app) | Meilleur(s) sur fal, id exact | Verdict | Liste à enrichir |
|---|---|---|---|---|
| Image → vidéo (Studio, Quick, Épisodes) | `seedance-2.5` par défaut, seedance 2.0 et 2.0 fast, seedance **v1** pro/lite, kling v3 pro/std, pixverse v6, veo3.1 fast | `minimax/h3-max/image-to-video` (0,048 $/s en 768p, promo), `alibaba/wan-3.0/image-to-video` (0,10 $/s en 720p), `google/gemini-omni-flash/v1.1/image-to-video` (0,10 $/s en 720p), `lightricks/ltx-2.5/image-to-video/fast` (0,09 $/s, audio inclus), `fal-ai/kling-video/v3/turbo/pro/image-to-video` (0,14 $/s), `fal-ai/vidu/q4/image-to-video`, `bytedance/seedance-2.0/mini/image-to-video` | + ajouter 4 à 6 ; retirer seedance v1 ; pixverse v6 → `fal-ai/pixverse/c1/image-to-video` | `S\fal_service.py:69-154`, `pricing.py:76-94`, bundle `dzVmRates` |
| Veo natif Google | `veo-3.1-*-generate-preview` (clé Gemini) | `fal-ai/veo3.1/image-to-video`, `/fast`, `fal-ai/veo3.1/lite/image-to-video`, `…/first-last-frame-to-video` | → fal (supprime le besoin d'une clé Gemini pour la vidéo) | `S\google_video.py`, entrées Google de `VIDEO_MODELS` |
| Prolonger un clip | `fal-ai/veo3.1/fast/extend-video`, `veo3.1/extend-video` | `minimax/h3-max/extend-video`, `minimax/h3-max-turbo/extend-video`, `blackforestlabs/flux-3/extend-video`, `fal-ai/ltx-2.3-quality/extend-video` | + ajouter 2 | `S\fal_video_tools.py:24-46` |
| Lip-sync de la voix off | `fal-ai/kling-video/lipsync/audio-to-video` (0,014 $ par tranche de 5 s, imbattable) | `fal-ai/sync-lipsync/v3` (0,133 $/s, qualité), `fal-ai/heygen/v3/lipsync/precision` (0,10 $/s), `veed/lipsync/v2` | À jour (défaut) ; + ajouter une option « qualité » | `S\fal_video_tools.py:121-135` |
| Multi-référence (non branché) | `fal-ai/veo3.1/reference-to-video`, kling v3 `elements` | `bytedance/seedance-2.5/reference-to-video`, `fal-ai/kling-video/o3/4k/reference-to-video`, `minimax/h3-max/reference-to-video`, `alibaba/wan-3.0/reference-to-video` | ↑ avant de brancher | `S\video_refs.py` |
| Avatar live › Recast | wan 2.2 animate replace/move (09/2025), kling v3 motion-control, `decart/lucy-edit/pro` | `minimax/h3-max/recast` (01/10/2026), `fal-ai/id-v2v`, `fal-ai/kling-video/o3/4k/video-to-video/reference` | + ajouter `h3-max/recast` (à essayer contre wan) | `S\recast_service.py:49-70` |
| Avatar live › Direct | Decart `lucy-2.5` (clé Decart) | `decart/lucy-2-5/realtime` sur fal | → fal **si** le WebRTC passe | `S\avatar_live.py:30-31` |
| Matte vidéo, décor | `fal-ai/birefnet/v2/video` | `bria/video/background-removal/v3`, `…/realtime`, `…/green-screen-despill`, `pixelcut/video-background-removal` | + ajouter Bria v3 (cheveux, détails) | `S\matte_service.py:36-41`, `S\decor_service.py:32-39` |

### Avatar (HeyGen)

| Fonction | Actuel | Sur fal | Verdict |
|---|---|---|---|
| Image fixe → vidéo parlante (`/generate/heygen-image`) | HeyGen v3, type image, `avatar_iv` | `fal-ai/heygen/avatar4/image-to-video` (texte + voix, ou `audio_url`) ; alternatives `fal-ai/bytedance/omnihuman/v1.5`, `fal-ai/kling-video/ai-avatar/v2/pro`, `minimax/h3-max/lip-sync/image-to-video` | → fal |
| Avatar par look (III/IV/V), Photo Avatar créé, cinématique | HeyGen v3 | Pas d'accès aux looks du compte. `avatar5/digital-twin` part d'une vidéo, il ne prend pas d'id de look (à vérifier au schéma) | hors fal (clé HeyGen optionnelle) |

### Image

| Fonction | Actuel | Meilleur(s) sur fal | Verdict | Liste |
|---|---|---|---|---|
| Texte → image (façade) | `nano-banana`, `nano-banana-pro`, `gpt-image-2`, `gpt-image-2.5` flare/sunburst ; défaut `flux` = `fal-ai/flux/schnell` | `google/nano-banana-2.1` (06/10), `blackforestlabs/flux-3/text-to-image` (0,048 $/MP après la promo), `bytedance/seedream/v5/pro/text-to-image`, `ideogram/v4.5` (texte dans l'image), `alibaba/qwen-image-3/text-to-image`, `recraft/v4.1/flash/text-to-image` | ↑ nano-banana → 2.1 ; + flux-3, seedream v5, ideogram 4.5. Garder schnell pour les croquis (0,003 $/MP) | `S\image_providers.py:23-50`, R:8926 `/image-models`, `pricing.py:166`, `frontend\shared\dz-champ-ia.js:630`, `materialforge.js:135` |
| Édition, variations | `fal-ai/flux-kontext/dev` par défaut, nano-banana edit | `google/nano-banana-2.1/edit`, `blackforestlabs/flux-3/edit-image`, `bytedance/seedream/v5/pro/edit` (0,0675 $), `alibaba/qwen-image-3/edit` | ↑ Kontext dev → flux-3 edit | R:8777, R:8803 |
| Images OpenAI directes | `/v1/images/generations` (R:8502, clé OpenAI) | `openai/gpt-image-2.5/*` via fal (déjà dans la façade) | → fal (supprimer le chemin hérité) | R:8502 |
| Vues 3D (multi-vue) | `fal-ai/bytedance/seedream/v4/edit` | `bytedance/seedream/v5/pro/edit`, `google/nano-banana-2.1/edit` | ↑ version | `S\asset3d_service.py:465` |
| Upscale | `fal-ai/esrgan` (10/2023) | `topaz/upscale/image/precision` (0,08 $ jusqu'à 24 MP), `fal-ai/seedvr/upscale/image`, `bria/increase-resolution`, `clarityai/crystal-upscaler` | ↑ (gros gain de qualité) | R:8630 |
| Détourage | `fal-ai/imageutils/rembg` (10/2023), sauf le décor en `birefnet/v2` | `fal-ai/birefnet/v2` (déjà utilisé), `fal-ai/bria/background/remove`, `pixelcut/background-removal`, `fal-ai/ideogram/remove-background` | ↑ tout passer en birefnet v2 ou Bria | R:8673, `sprite_service.py:248`, `cards\capture.py:1226` |
| Vectorlab, illustration IA | LLM qui écrit du SVG (Anthropic, OpenAI, Gemini, Ollama) | `fal-ai/recraft/v4.1/text-to-vector`, `recraft/v4/style/text-to-vector` (**vrai SVG**) ; LLM via `openrouter/router` | + ajouter un moteur « Recraft vecteur » ; LLM → fal | `S\vector_illustration.py:47-206` |
| Tuiles (Tile Lab, Material Forge) | image générique | `fal-ai/z-image/turbo/tiling`, `ideogram/v4/tiling`, `fal-ai/seedvr/upscale/image/seamless`, `fal-ai/patina/material` (PBR) | + ajouter (raccord sans couture natif) | `materialforge.js:135`, R:13045 |
| Pixel art (Spritelab) | image générique | `fal-ai/image2pixel` | + ajouter | `spritelab.js:1036` |

### 3D

| Fonction | Actuel | Meilleur(s) sur fal | Verdict | Liste |
|---|---|---|---|---|
| Image → 3D | `tripo` = tripo v2.5 (défaut, 04/2025), tripo h3.1, `hunyuan3d/v2`, `trellis`, `hyper3d/rodin` (v1, 2024), `triposr` (2024) ; local hunyuan 2.1 | `tripo3d/p2/image-to-3d` (1,00-1,30 $), `meshy/v7.1/image-to-3d` (0,80 $, 1,20 $ texturé), `fal-ai/hunyuan-3d/v3.1/pro/image-to-3d` (0,375 $), `fal-ai/hyper3d/rodin/v2.5` (0,40 $), `fal-ai/trellis-2`, `hitem3d/hi3d/v3.0/image-to-3d` | ↑ hunyuan v2 → 3.1, rodin → 2.5, trellis → 2 ; + meshy 7.1, tripo p2 ; retirer triposr ; défaut `tripo` v2.5 → h3.1 ou p2 | `S\asset3d_service.py:71-183`, `cards\forge3d.py:232-246`, `studio3d.js:94-101` |
| Card Forge mesh3d (Meshy direct) | `meshy-6`/`meshy-7` via `openapi/v1/image-to-3d` | `meshy/v7.1/image-to-3d` via fal | → fal | `cards\forge3d.py:3195-3340` |
| Texturage | Meshy `retexture` (`meshy-7`) | `meshy/v6-lite/retexture` (0,30 $), `fal-ai/trellis-2/retexture`, `hitem3d/hi3d/texture` | → fal | `asset3d_service.py:825-957` |
| Rig + animations | Meshy `remesh`, `rigging`, `animations` | `fal-ai/meshy/rigging` (n'importe quel GLB, 697 animations), `fal-ai/meshy/rigging/multi-animation` | → fal | `S\asset3d_rig.py` |
| Remaillage, découpe | Meshy `remesh` | `tripo3d/tripo/remesh` (0,20 $), `fal-ai/hunyuan-3d/v3.1/smart-topology`, `fal-ai/hunyuan-3d/v3.1/part`, `tripo3d/tripo/segment` | → fal | idem |
| Conversion fbx/usdz/blend | Meshy `convert` | aucun | → **local** (Blender déjà embarqué) | `S\mesh_convert.py` |
| Bas-relief (impression 3D) | — | `hitem3d/hi3d/image-to-relief` | + idée (Établi, Vectorlab impression) | — |

### Audio et voix

| Fonction | Actuel | Meilleur(s) sur fal | Verdict | Liste |
|---|---|---|---|---|
| Musique | `lyria3` (défaut), stable-audio 2.5, minimax-music v2.6 et v2, ace-step, `CassetteAI/music-generator` | `google/lyria-3.5`, `elevenlabs/music/v2.5` (0,60 $/min), `minimax/music-3`, `mureka/api/generate/song`, `fal-ai/stable-audio-3/medium/text-to-audio` | ↑ lyria 3.5, stable-audio 3 ; + ElevenLabs music, Mureka. Vérifier la casse `CassetteAI` (fal liste `cassetteai/…`) | `S\music_service.py:42-108` |
| SFX | ElevenLabs direct `/v1/sound-generation` | `fal-ai/elevenlabs/sound-effects/v2`, `mirelo-ai/sfx1.6/text-to-audio`, `sonilo/v1.1/text-to-sound-effects` | → fal ; + **vidéo → bruitage** (`sonilo/v1.1/video-to-sound-effects`, `mirelo-ai/sfx-v1.5/video-to-audio`) pour le Montage | `S\sfx_service.py` |
| Stems | `fal-ai/demucs` | `fal-ai/sam-audio/separate` (séparation guidée par texte, 0,05 $ par 30 s) | À jour ; + SAM Audio | `S\stems_service.py` |
| Isolation de la voix | ElevenLabs direct | `fal-ai/elevenlabs/audio-isolation`, `veed/clean-audio` (0,125 $ pour 10 min) | → fal | `S\voice_clean.py` |
| TTS | ElevenLabs SDK `eleven_multilingual_v2`, ou Voicebox local | `elevenlabs/tts/eleven-v4[-turbo]` (28/09), `fal-ai/elevenlabs/tts/eleven-v3`, `fal-ai/minimax/speech-2.8-hd` (0,10 $ pour 1 000 caractères), `google/gemini-3.8-flash-tts`, `fal-ai/inworld-tts` | → fal pour les voix prédéfinies ; ↑ v2 → v4. Voicebox reste l'option gratuite | `S\elevenlabs_service.py`, bundle `dzVoMeta` |
| Clonage de voix (Atelier, personnages) | ElevenLabs `/v1/voices/add` | `fal-ai/minimax/voice-clone` (1,50 $ par clonage), `fal-ai/qwen-3-tts/clone-voice/1.7b`, `fal-ai/dia-tts/voice-clone` | → fal possible, **mais** l'id de voix vit chez MiniMax/Qwen, pas sur le compte ElevenLabs | `S\voice_clone.py`, `S\avatar_voix.py` |
| Changeur de voix (recast) | ElevenLabs STS `eleven_multilingual_sts_v2` | `fal-ai/elevenlabs/voice-changer` (voix prédéfinies), `fal-ai/chatterbox/speech-to-speech` (0,025 $ pour 1 000 caractères) | → fal pour les rendus en lot | `S\avatar_voix.py` |
| Voix live (avatar direct) | ElevenLabs STS en flux, ou Voixbox local | aucun flux temps réel | hors fal → Voixbox local par défaut | `S\voix_direct.py` |
| Transcription, dictée | ElevenLabs `scribe_v1`, puis OpenAI `whisper-1` | `fal-ai/elevenlabs/speech-to-text/scribe-v2` (0,008 $/min), `fal-ai/wizper`, `nvidia/nemotron-asr-multilingual/asr`, `fal-ai/elevenlabs/forced-alignment` (sous-titres mot à mot) | → fal ; ↑ scribe v1 → v2 | `S\transcribe_service.py:877-1063`, `dictation_service.py` |
| Recherche de sons | CLAP local | aucun | À jour (local) | — |

### Texte et vision (LLM)

| Fonction | Actuel | Sur fal | Verdict |
|---|---|---|---|
| Routeur LLM (news, scripts, Atelier, Épisodes, traductions, Planificateur, Vectorlab, auto-clips) | Anthropic `claude-haiku-4-5-20251001`, sinon OpenAI `gpt-4o-mini`, sinon Gemini `gemini-flash-latest`, sinon Ollama | `openrouter/router` : `anthropic/claude-opus-5.5`, `anthropic/claude-sonnet-5`, `openai/gpt-6-*`, `google/gemini-3.8-flash`, `deepseek/deepseek-v4.1-flash`, `mistralai/mistral-medium-3-5`… facturés au jeton, avec recherche web en option. Endpoint OpenAI-compatible fourni | → fal : un 4ᵉ fournisseur « fal » dans `summarizer.py`, qui permet aussi de **monter de génération** (haiku 4.5 et gpt-4o-mini sont anciens) |
| Contrôles visuels (proportions, identité 3D, « décrire » du recast), légendes de la Bibliothèque | Anthropic vision, `gpt-4o-mini` codé en dur, Gemini 2.5 flash-lite | `openrouter/router/vision`, `fal-ai/moondream3-preview/caption` (0,40 $ par million de jetons en entrée) | → fal ; retirer le `gpt-4o-mini` codé en dur (`proportion_qc.py:85`, `recast_service.py:260`) |

## 4. Modèles à ajouter aux listes (priorités)

1. **Vidéo :**
   - `minimax/h3-max/image-to-video` (le moins cher pour une bonne qualité)
   - `alibaba/wan-3.0/image-to-video`
   - `google/gemini-omni-flash/v1.1/image-to-video`
   - `lightricks/ltx-2.5/image-to-video/fast` (audio natif)
   - `fal-ai/kling-video/v3/turbo/pro/image-to-video`
   - `fal-ai/veo3.1/lite/image-to-video`
   - À retirer : seedance v1 pro/lite.
2. **Image :**
   - `google/nano-banana-2.1[/edit]`
   - `blackforestlabs/flux-3/text-to-image|edit-image`
   - `bytedance/seedream/v5/pro/text-to-image|edit`
   - `ideogram/v4.5[/edit]`
   - `fal-ai/recraft/v4.1/text-to-vector` (pour le Vectorlab)
3. **Utilitaires image :**
   - `topaz/upscale/image/precision` ou `fal-ai/seedvr/upscale/image`
   - `fal-ai/birefnet/v2` partout à la place de rembg
   - `fal-ai/z-image/turbo/tiling`
   - `fal-ai/image2pixel`
4. **3D :**
   - `meshy/v7.1/image-to-3d`
   - `tripo3d/p2/image-to-3d`
   - `fal-ai/hunyuan-3d/v3.1/pro/image-to-3d`
   - `fal-ai/hyper3d/rodin/v2.5`
   - `fal-ai/trellis-2`
   - Post-traitement : `fal-ai/meshy/rigging`, `meshy/v6-lite/retexture`, `tripo3d/tripo/remesh`
5. **Audio :**
   - `google/lyria-3.5`
   - `elevenlabs/music/v2.5`
   - `fal-ai/stable-audio-3/medium/text-to-audio`
   - `fal-ai/elevenlabs/sound-effects/v2`
   - `sonilo/v1.1/video-to-sound-effects`
   - `fal-ai/sam-audio/separate`
6. **Voix :**
   - `elevenlabs/tts/eleven-v4`
   - `fal-ai/minimax/speech-2.8-hd`
   - `fal-ai/elevenlabs/speech-to-text/scribe-v2`
   - `fal-ai/minimax/voice-clone`
7. **LLM :** `openrouter/router` (et `/vision`).

Chaque ajout payant suit le parcours habituel :
- la grille de `pricing.py` et `PAYANTES` ;
- la garde de plafond ;
- les copies frontend : `dzVmRates` dans le bundle, `dz-champ-ia.js` `CATALOGUE_IMAGE`, `materialforge.js` `MODEL_COST`, `studio3d.js` `ENGINES3D`, `cards\forge3d.py`.

## 5. « Tout avec la clé fal ? » : point de vue de l'utilisateur final

**Aujourd'hui**, avec la seule clé fal :
- **Ça marche :** générer des vidéos (hors Veo natif), des images, de la 3D (moteurs fal), de la musique, des stems et le matte/décor.
- **Ça ne marche pas :** la voix off (sauf Voicebox local), les sous-titres et la dictée, toute l'écriture IA (news, scripts, Atelier, traductions, Planificateur), les bruitages, les avatars HeyGen, le rig et le texturage Meshy, et l'avatar live.

En clair, l'app réclame aujourd'hui **4 à 7 clés** pour être complète, avec autant de comptes, de factures et de soldes.

**Après bascule** (lots ci-dessous), la clé fal seule couvre :
- toute l'écriture et la vision IA ;
- la voix off avec les voix prédéfinies ElevenLabs (v4), MiniMax et Gemini ;
- le clonage de voix (MiniMax/Qwen) ;
- les sous-titres et la dictée ;
- bruitages, musique, isolation ;
- l'avatar photo → vidéo parlante ;
- toute la 3D, y compris rig, texture et remaillage ;
- Veo ;
- les images OpenAI.

**Ce qui exige encore une autre clé, et pourquoi :**
- **HeyGen** : les avatars personnels, les looks enregistrés et les Photo Avatars sont liés au compte HeyGen de l'utilisateur. Option avancée.
- **ElevenLabs** : les voix déjà clonées sur le compte de l'utilisateur, et la voix live en flux. Option avancée. Voixbox local fait la voix live gratuitement.
- **Decart** : seulement si le temps réel via fal ne tient pas la latence (à tester).
- **Réseaux sociaux et Figma** : ce ne sont pas des fournisseurs d'IA. Ils restent des connexions de compte dans les Réglages.

**Recommandation : « fal d'abord, clés tierces en option avancée ».**
- **À l'installation**, demander **une seule clé (fal)**. Les autres passent dans Réglages › Fournisseurs › Avancé, avec une phrase par clé qui dit ce qu'elle ajoute (« vos avatars HeyGen personnels », « vos voix ElevenLabs clonées »).
- **Un seul solde, une seule facture, un seul plafond.** La pastille de coût et les plafonds (#16) deviennent plus simples à lire. La mobile (#59) n'a plus qu'une grille de prix.
- **Pour l'utilisateur**, cela veut dire moins de comptes à créer : c'est le premier frein à l'installation.
- **Le local gratuit reste le premier choix quand il suffit** : Voicebox, Voixbox, Hunyuan local, Ollama, CLAP.
- **Points de vigilance :**
  - Dépendance à un seul fournisseur : garder les connecteurs directs en secours plutôt que de les supprimer.
  - Certains tarifs fal sont plus chers que l'API ou l'abonnement direct, par exemple HeyGen via fal à 0,10 $/s contre un forfait HeyGen. Comparer avec `pricing.py` avant de changer un **défaut**.
  - Les voix et avatars déjà créés par l'utilisateur ne migrent pas.

## 6. Plan proposé (lots courts, du plus utile au moins utile)

| Lot | Contenu | Clés supprimées pour l'utilisateur | Fichiers principaux | Bancs à toucher |
|---|---|---|---|---|
| F1 | Fournisseur LLM « fal » (`openrouter/router`, OpenAI-compatible) dans le routeur, la vision et le Vectorlab ; choix du modèle dans les Réglages ; retrait des `gpt-4o-mini` codés en dur | Anthropic, OpenAI, Gemini (texte) | `summarizer.py`, `openai_llm.py`, `gemini_llm.py`, `vector_illustration.py`, `proportion_qc.py`, `asset3d_qc.py`, `recast_service.py`, `library_legendes.py`, `config.py`, `diagnostic.py` | routeur LLM, plafonds, diagnostic des clés |
| F2 | Voix via fal : TTS ElevenLabs v4 et MiniMax, STT scribe-v2, SFX, isolation, clonage MiniMax ; un fournisseur de voix « fal » à côté d'ElevenLabs et Voicebox (t131) | ElevenLabs (sauf voix du compte) | `voice_providers.py`, `elevenlabs_service.py`, `transcribe_service.py`, `dictation_service.py`, `sfx_service.py`, `voice_clean.py`, `voice_clone.py`, bundle `DzVoFournisseur` | voix, sous-titres, PAYANTES |
| F3 | Catalogues fal à jour : vidéo (h3-max, wan 3.0, gemini omni, ltx 2.5, kling turbo, veo lite ; retrait de seedance v1), image (nano-banana 2.1, flux-3, seedream v5, ideogram 4.5), utilitaires (upscale, birefnet partout), musique (lyria 3.5, ElevenLabs music, stable-audio 3) | — | `fal_service.py`, `image_providers.py`, `music_service.py`, `pricing.py`, routes R:8630/8673, copies frontend | bancs figés des listes, pastille de coût (dzcout) |
| F4 | 3D Meshy via fal (génération 7.1, retexture, rig) ; moteurs 3D à jour (tripo p2, hunyuan 3.1, rodin 2.5, trellis 2 ; retrait de triposr) ; conversion locale par Blender | Meshy | `asset3d_service.py`, `asset3d_rig.py`, `mesh_convert.py`, `cards\forge3d.py`, `studio3d.js` | bancs T104-T107, estimations Meshy |
| F5 | Avatar : HeyGen avatar4 photo via fal, lip-sync « qualité » (sync v3) ; HeyGen direct gardé pour les looks personnels | HeyGen (cas photo) | `heygen_service.py`, `pipeline.py`, `fal_video_tools.py` | avatar, plafonds |
| F6 | Veo via fal ; essai de Decart temps réel via fal ; `h3-max/recast` dans le recast | Gemini (vidéo), Decart (si OK) | `google_video.py`, `avatar_live.py`, `recast_service.py` | recast, direct |
| F7 | Installation « une clé » : assistant, Réglages › Avancé, diagnostic, guide utilisateur FR/EN | — | appairage, `guides_fournisseurs.py`, `settings_routes.py`, guide v3 | installation, traduction |

Avant chaque bascule de **défaut** : un tir d'essai sous plafond (comparaison à l'œil plus prix réel relevé) et l'accord de l'utilisateur.
