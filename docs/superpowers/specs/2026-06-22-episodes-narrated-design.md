# Épisodes narrés (« Roman DeepotusVerse ») — Design

**Date:** 2026-06-22
**Auteur:** Claude + hugboss1

## But

Transformer un **chapitre de roman** (texte) en **vidéo narrée illustrée**, diffusable en épisodes sur Instagram + YouTube :
téléverser le script → choisir une voix + langue → générer la **voix off complète** → générer des **illustrations + animations enchaînées** au fil de la narration → **exporter dans le Scheduler**.

## Décisions cadrées

1. **Emplacement** : nouvelle page dédiée **« Épisodes »** (workflow guidé), cohérente avec Quick/News/Scheduler.
2. **Animation** : **Ken Burns** (zoom/pan lent sur les stills) par défaut, **Seedance optionnel** par scène clé.
3. **Export** : **brouillon dans le Scheduler** (vidéo + légende programmables ; publication IG/YT manuelle). Publication directe IG/YT = hors scope v1.

## Modèle clé — narration **par scènes**

Le chapitre est découpé en **scènes**. Chaque scène porte `{ texte, clip de narration (TTS), illustration, mouvement }`.
La durée visuelle d'une scène = la durée de **son** clip de narration → l'image change pile quand le narrateur arrive à ce passage (sync parfaite, sans alignement fragile).
La **voix off complète du chapitre** = la concaténation des narrations de scènes, sauvegardée dans la Librairie audio (un .mp3 réutilisable).

> Réconciliation des phases : en **Phase 1** (avant l'existence des scènes), on narre le **chapitre entier** en une fois (TTS découpé) → un .mp3 standalone dans la Librairie (le besoin immédiat « voix off complète »). Dès que les scènes existent (**Phase 2+**), la narration est (re)générée **par scène** pour le timing, et la voix off complète devient leur concaténation (qui met à jour le même .mp3).

## Modèle de données (store JSON, comme `outputs/_graphs/`)

Fichier `outputs/_episodes/{id}.json`, fichiers média sous `outputs/episodes/{id}/`.

```
Episode {
  id, title, language ("en"|"fr"), voice_id,
  script,                       # texte complet du chapitre
  narration_path,               # mp3 complet (concat des scènes)
  duration_s,
  scenes: [Scene],
  status: "draft"|"narrated"|"illustrated"|"rendered",
  final_video_path, created_at
}
Scene {
  id, index,
  text,                         # extrait narré de cette scène
  illustration_prompt,
  image_filename,               # illustration générée (dans le dossier images)
  motion: "kenburns"|"seedance"|"still",
  motion_params,                # kenburns: {zoom,dir}; seedance: {prompt,style}
  narration_path,               # mp3 TTS de cette scène
  duration_s,                   # = durée du mp3 de la scène
  clip_path                     # clip de scène rendu (cache, optionnel)
}
```

## Endpoints

| Endpoint | État | Rôle |
|---|---|---|
| `GET /voices` | **NOUVEAU** | Liste des voix ElevenLabs (pour le sélecteur) |
| `POST /audio/voiceover` | **EXISTE** (à étendre) | TTS d'un texte → mp3 dans la Librairie. Étendre : texte long (découpe + concat) + `voice_id` |
| `POST /episodes/scenes` | **NOUVEAU** | `{script, language}` → IA → `[{text, illustration_prompt}]` |
| `GET/POST/PUT /episodes`, `GET /episodes/{id}` | **NOUVEAU** | CRUD store JSON |
| `POST /episodes/{id}/narrate` | **NOUVEAU** | TTS par scène (voice_id, langue) → durées → concat narration complète |
| `POST /episodes/{id}/render` | **NOUVEAU** | Rend la vidéo chapitre (visuel par scène calé sur sa narration) |
| `POST /images/generate` | **EXISTE** | Illustration par scène |
| `POST /generate` (Seedance) | **EXISTE** | Animation Seedance d'une scène (option) |
| `POST /schedule` | **EXISTE** | Export final → brouillon de post |

## Le rendu chapitre (le cœur)

Étend le build **séquentiel** existant (`render_mode:"sequential"`, `build_sequential_command`) :
- Par scène, un **segment** dont la durée = la durée du mp3 de narration de la scène :
  - `motion=kenburns`/`still` : l'image → filtre `zoompan` (Ken Burns : zoom/pan lent) sur `duration_s` ;
  - `motion=seedance` : le clip Seedance de la scène, bouclé/coupé (`-stream_loop`/`-t`) à `duration_s`.
- Chaque segment reçoit l'**audio de narration** de sa scène.
- **Concat** des segments dans l'ordre → vidéo + narration continue.
- Réutilise la chaîne audio (loudnorm) ; la narration est la piste maîtresse (durée du rendu = somme des scènes).

## Page « Épisodes » — UI en 4 étapes (design existant)

Réutilise les primitives UI (`ie` sections, `O` fields, `K` boutons, `re` selects, `DzAudioPicker`, le pattern 3-colonnes de News). Étapes via un stepper :

1. **Script & voix** — zone de texte (coller) + bouton « Téléverser .txt » ; sélecteurs **voix** (ElevenLabs) + **langue** ; bouton « Générer la narration » → lecteur audio + durée. Sauve l'épisode.
2. **Scènes (storyboard)** — liste éditable des scènes (extrait + prompt d'illustration), réordonner / ajouter / supprimer / régénérer le découpage.
3. **Illustrations & animation** — par scène : « Générer l'illustration » (modèle d'image courant), choix **Ken Burns / Seedance / fixe**, aperçu. Régénérable individuellement.
4. **Assemblage & export** — « Assembler l'épisode » → aperçu vidéo → « Envoyer au Scheduler » (préremplit titre/légende/vidéo).

## Phases d'implémentation

- **Phase 1 — Narration (colonne vertébrale)** : `GET /voices`, `/audio/voiceover` texte long + voice_id ; page « Épisodes » étape 1 (script + voix/langue + narration → Librairie audio + lecteur). *Livrable : téléverser un chapitre → voix off complète sauvegardée.*
- **Phase 2 — Storyboard** : `/episodes/scenes` (IA) + CRUD épisode ; étape 2 (scènes éditables).
- **Phase 3 — Illustrations & animation** : étape 3 (image par scène + Ken Burns/Seedance + aperçu).
- **Phase 4 — Assemblage & export** : `/episodes/{id}/render` (build séquentiel + Ken Burns + narration par scène) ; étape 4 (aperçu + envoi Scheduler).

Chaque phase est livrable et vérifiable indépendamment (node-check + rendu ffmpeg réel + endpoint).

## Hors scope (v1)

- Publication automatique IG/YouTube (OAuth/API) — phase ultérieure.
- Détection musicale de fond (le BGM existant via MusicTrack reste disponible si on assemble dans le Studio).
- Multi-locuteurs / voix par personnage (une voix par épisode pour l'instant).

## Cohérence / réutilisation

ElevenLabs (`VoiceoverService`), `/images/generate` (FLUX/OpenAI), Seedance (`/generate`), le build séquentiel + Concatenate, la Librairie (audio/images/renders), le Scheduler, le pattern UI de la page News. Aucune dépendance nouvelle lourde.
