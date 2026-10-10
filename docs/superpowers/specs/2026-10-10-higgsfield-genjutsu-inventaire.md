# Higgsfield Genjutsu — relevé et tableau d'écart (Studio + compagnon mobile)

Date : 10/10/2026. Statut : **VALIDÉ le 10/10/2026** — périmètre G0→G7
(différé + direct, PC + mobile) ; voix en direct : **les deux** (ElevenLabs
cloud par défaut, Seed-VC local proposé si un GPU NVIDIA compatible est
détecté). Phases inscrites au suivi : t161→t168.

## Comment ce relevé a été fait

- Higgsfield exige un compte : l'application n'a **pas** été ouverte. Le relevé
  s'appuie sur la page officielle (higgsfield.ai/blog/higgsfield-genjutsu) et
  trois articles tiers datés de septembre-octobre 2026. Ce qui n'est écrit dans
  aucune de ces sources figure en « non relevé ».
- Briques de remplacement vérifiées sur leur documentation : Decart (Lucy 2.5
  temps réel), fal.ai (Wan 2.2 Animate, Kling Motion Control, Lucy Edit),
  ElevenLabs (Voice Changer), Seed-VC / RVC (conversion de voix locale).
- Dépôt DeepotusVideo et `C:\Users\olivi\deepotus-mobile` parcourus en lecture
  seule. Rien n'a été modifié.

## 1. Ce qu'est Genjutsu (chez eux)

**Correction importante : Genjutsu n'est pas du direct.** C'est un
traitement vidéo vers vidéo **en différé**, lancé le 01/09/2026 et utilisé
comme moteur de « AI Influencer ». Le seul article qui parle de « temps réel »
(blockchain.news) est générique et contredit par tous les autres : un
changement de tenue en 1080p a pris environ 10 minutes chez un testeur.

| Élément | Relevé |
|---|---|
| Mode 1 — **Motion Transfer** | Extrait le jeu d'acteur, les mouvements de caméra, le rythme du montage **et la synchro labiale** d'une vidéo source, puis reconstruit personnage, lieu et univers à partir des images de référence. |
| Mode 2 — **Object Swap** | Remplace UN élément désigné (personnage, tenue, produit, décor) et laisse le reste du plan intact. |
| Vidéo d'entrée | 1 clip de 4 à 30 s (un article tiers dit 3 à 30 s). Vraie prise de vue ou vidéo générée. |
| Références | Jusqu'à 30 images (40 selon un article tiers) : personnage, objet, tenue, produit, lieu, style. |
| Consigne | Facultative : 30+ préréglages ou une courte description. |
| Sortie | 480p, 720p ou 1080p. Cadence, durée maximale et format non publiés. |
| Prix (15 s) | 480p : 40 crédits (~2,00 $) · 720p : 104 (~5,20 $) · 1080p : 144 (~7,20 $). Identique pour les deux modes. |
| Identité | Via « AI Influencer » : 1 photo « Add your face » ; Soul ID entraîné sur 20 à 80 images pour la cohérence ; Soul ID non exportable. |
| Voix | **Non relevé dans Genjutsu.** La voix vit dans l'outil voisin « Recast » (doublage, clonage de voix, voix de référence personnelles). Genjutsu garde l'audio et la synchro labiale de la source. |
| Arrière-plan | Reconstruit par Motion Transfer, ou ciblé par Object Swap. Aucun détourage exposé. |
| API publique | Non relevé (seul `higgsfield/ai-influencer` pour la fiche personnage, ~0,05 $). Modèle sous-jacent non publié. |

### Schéma de fonctionnement (déduit des sources)

```
 vidéo source 4-30 s ──► [extraction] pose · expressions · lèvres · caméra · rythme
                                     │
 1-30 images de réf. ──► [identité] personnage · tenue · objet · décor · style
                                     │
 consigne / préréglage ─────────────►│
                                     ▼
                       [générateur vidéo conditionné]  ── mode Motion Transfer : tout le plan
                                     │                 └─ mode Object Swap : un élément masqué
                                     ▼
                       vidéo 480p/720p/1080p (audio + synchro labiale de la source)
                                     │
                       (Recast, à côté) voix clonée / doublage → remplace la piste
```

## 2. Ce que demande l'utilisateur va plus loin que Genjutsu

La demande vise un **clonage d'avatar en direct, avec la voix, et changement
d'arrière-plan et d'avatar**. Cela recouvre deux produits distincts :

- **A. Recast différé** = l'équivalent exact de Genjutsu (+ la voix de Recast).
- **B. Direct** = webcam → avatar transformé en temps réel, voix convertie,
  décor et personnage changeables à chaud. Higgsfield ne le fait pas ;
  **Decart Lucy 2.5** le fait (sous 40 ms annoncés, 720p, WebRTC).

```
                         ┌──────────────────── A. RECAST DIFFÉRÉ ────────────────────┐
 vidéo (Bibliothèque,    │ fal: Wan 2.2 Animate replace ── garde décor, change perso │
 caméra mobile, upload) ─┤ fal: Kling v3 Motion Control ── perso + nouveau décor     ├─► Bibliothèque
 + images de réf.        │ fal: Lucy Edit Pro ─────────── object swap par consigne   │   (lignée)
                         │ local: BiRefNet + ffmpeg ───── décor remplacé (gratuit)   │
                         │ ElevenLabs Voice Changer ──── voix → voix clonée (timing  │
                         │                               conservé ⇒ lèvres intactes) │
                         └───────────────────────────────────────────────────────────┘
                         ┌──────────────────────── B. DIRECT ─────────────────────────┐
 webcam PC / caméra ─────┤ navigateur ⇄ WebRTC ⇄ Decart Lucy 2.5 (jeton éphémère    │
 mobile + micro          │   frappé par le backend, clé au coffre, plafond vérifié)  │
                         │ set({image: personnage, prompt: décor}) à chaud            ├─► aperçu live
                         │ micro ─► conversion de voix (cloud S2S ou Seed-VC local)   │   + enregistrement
                         │ vidéo retardée pour rester synchro avec la voix           │   → Bibliothèque
                         └───────────────────────────────────────────────────────────┘
```

## 3. Ce qui existe déjà chez nous

| Brique | Où | Réutilisable pour |
|---|---|---|
| Avatars HeyGen v3 (looks, photo avatar, avatar_iii/iv/v) | `backend/app/services/heygen_service.py`, routes `/heygen/*` | Personnages de référence (image d'un look) |
| Studio graphe (nœuds, recette, devis, lancer) | `frontend/src/studio/studio.jsx`, `nodes.jsx`, `services/studio_graph.py` | Nœuds Recast / Voix→voix / Décor |
| TTS ElevenLabs + Voicebox (Kokoro, Chatterbox clonage) | `elevenlabs_service.py`, `voice_providers.py` | Voix ; profils clonés lus seulement |
| Isolation de voix, dictée (MediaRecorder + getUserMedia audio) | `voice_clean.py`, `frontend/shared/dz-champ-ia.js` | Nettoyage avant conversion ; motif de capture |
| Détourage vidéo BiRefNet v2 + calque « derrière » du montage | `matte_service.py`, `frontend/patches/son-vfx-montage.js` | Changement de décor en différé |
| Lipsync Kling | `fal_video_tools.py` | Recaler les lèvres si la voix change de durée |
| Plafonds, garde 402, `_require_local_depense` 403, prix | `plafonds.py`, `routes.py:85`, `pricing.py` | Garde des routes payantes |
| Coffre à clés DPAPI | coffre (#20) | Clé Decart, clé ElevenLabs |
| Bibliothèque + lignée, « Envoyer vers » | `library_index.noter()`, `patch_bundle_libsend.py` | Ranger les sorties |
| Mobile : appairage QR, sync, génération fal directe, expo-camera | `deepotus-mobile/src/ecrans`, `src/lib/fal.ts`, `pc.ts` | Base de l'écran mobile |

## 4. Systèmes manquants

1. **Transport temps réel** : aucun WebRTC ni WebSocket (`main.py:365` le dit).
   Avec Decart, le flux va **du navigateur à Decart directement** ; le backend
   ne fait que frapper un jeton éphémère (TTL 60 s, limité au modèle).
2. **Route de jeton Decart** + clé au coffre + catégorie de plafond « direct »
   comptée **à la seconde** (0,02 $/s via Decart, 0,04 $/s via fal).
3. **Transfert de mouvement / remplacement de personnage** : aucun modèle
   (Wan Animate, Kling Motion Control, Lucy Edit absents).
4. **Voix → voix** : aucune conversion de voix ni clonage dans l'app.
5. **Personnage de référence** : pas d'objet « personnage » (1 à N images +
   voix associée) ; les looks HeyGen et la Bibliothèque en fournissent la matière.
6. **Enregistrement du direct** : MediaRecorder existe pour l'audio seulement.
7. **Mobile** : la caméra ne sert qu'au QR ; pas de WebRTC. Decart publie un
   SDK JS, Python, Android et Swift, **pas React Native** ⇒ passer par une
   WebView qui exécute le SDK JS (getUserMedia fonctionne en WebView Android et
   WKWebView iOS ≥ 14.3) ou par `react-native-webrtc` (build de dev, pas Expo Go).
8. **Garde côté mobile** : `_require_local_depense` refuse tout hôte non local
   (403) ⇒ la route de jeton doit accepter un appareil appairé (Bearer) tout
   en appliquant le plafond.

## 5. Tableau d'écart

| Geste / élément | Chez eux (Genjutsu) | Aujourd'hui chez nous | Décision proposée |
|---|---|---|---|
| Remplacer le personnage en gardant le décor | Object Swap | rien | **Wan 2.2 Animate replace** (fal, ~0,04-0,08 $/s) |
| Nouveau personnage + nouveau décor, même jeu | Motion Transfer | rien | **Kling v3 Motion Control** (fal) |
| Changer un objet / une tenue / le décor par consigne | Object Swap | rien | **Lucy Edit Pro** (fal) |
| Changer seulement le décor | Object Swap (décor) | BiRefNet + calque derrière | **Réutiliser** : détourage + image/vidéo de fond, local et gratuit |
| Références multiples (≤ 30) | oui | images isolées | Objet **Personnage** (≤ 8 images utiles aux modèles retenus) |
| Préréglages (30+) | oui | non | 12 préréglages au départ (décors, styles), extensibles |
| Voix clonée / doublage | Recast | TTS seulement | **ElevenLabs** clonage instantané + Voice Changer ; le timing est conservé donc les lèvres aussi |
| Durée 4-30 s, 480/720/1080p | oui | — | Mêmes bornes ; résolution selon le modèle |
| Prix affiché avant | oui | devis Studio | Devis + garde 402 comme les autres routes payantes |
| **Direct webcam → avatar** | **non** | rien | **Decart Lucy 2.5** WebRTC, jeton éphémère, arrêt auto au plafond |
| Bascule à chaud perso / décor | non | — | `realtimeClient.set({image, prompt})` |
| Voix en direct | non | — | À trancher (voir question) |
| Enregistrer le direct | — | — | MediaRecorder sur flux sortant + voix convertie → Bibliothèque |
| Mobile | app Higgsfield | images fal seulement | Écran **Direct** (WebView + SDK JS) et **Recast** (vidéo filmée → job PC) |
| Consentement | « droits et consentement » | — | Case obligatoire « j'ai le droit d'utiliser ce visage et cette voix » avant tout clonage |

## 6. Phases proposées (si validé)

| Code | Phase | Taille |
|---|---|---|
| G0 | Socle : clé Decart au coffre, prix et plafond « direct » à la seconde, route de jeton éphémère (garde + appareil appairé), objet Personnage + consentement | M |
| G1 | Recast différé : service + routes (Wan replace, Kling motion control, Lucy Edit), devis, garde, Bibliothèque/lignée ; nœud Studio « Recast » | L |
| G2 | Voix : clonage ElevenLabs + Voice Changer sur piste ; nœud Studio « Voix → voix » ; branché en sortie du Recast | M |
| G3 | Décor différé : nœud « Décor » (BiRefNet + fond, local) et préréglages | S |
| G4 | Direct PC : écran Studio « Direct » (webcam → Lucy 2.5), choix du personnage et du décor à chaud, compteur de coût, arrêt auto, enregistrement → Bibliothèque | L |
| G5 | Voix en direct : selon la décision ci-dessous, avec mesure de latence et retard vidéo compensé | M |
| G6 | Mobile : écrans Direct (WebView) et Recast (vidéo filmée → job PC → sync) | L |
| G7 | Aide didactique, traduction FR/EN, chapitre du guide | S |

## 7. Question ouverte

Voix en direct :
- **Cloud ElevenLabs Voice Changer** par segments : aucune installation,
  ~1 à 2 s de décalage (la vidéo est retardée d'autant), payant à l'usage.
- **Seed-VC local** (GPU NVIDIA ≥ 6 Go) : ~0,3-0,4 s, gratuit, clonage à
  partir de 1 à 30 s d'échantillon, roues lourdes dans le Python embarqué ;
  inutilisable depuis le mobile seul (le PC convertit).

## Sources

- https://higgsfield.ai/blog/higgsfield-genjutsu
- https://www.bottlerocketcontent.com/higgsfield-genjutsu-motion-transfer/
- https://aiidelist.com/blog/higgsfield-ai-influencer
- https://www.cachephoto.com/en/cineblog/higgsfield-genjutsu-video-a-video/
- https://higgsfield.ai/blog/AI-Face-Character-Swap-in-Video-Photo-PRO-Guide
- https://docs.platform.decart.ai/models/realtime/lucy-2.5
- https://docs.platform.decart.ai/getting-started/client-tokens
- https://fal.ai/models/decart/lucy-edit/fast/api
- https://fal.ai/kling-motion-control
- https://elevenlabs.io/docs/api-reference/streaming
- https://deepwiki.com/plachtaa/seed-vc

## 8. Relevés et écarts pendant G0 (t161, 10/10/2026)

- **API de jeton Decart** (lue dans `@decartai/sdk` 0.2.8, paru le 08/10) : `POST https://api.decart.ai/v1/client/tokens`,
  en-tête `X-API-KEY`, corps `{expiresIn (1-3600, défaut 60), allowedModels, allowedOrigins,
  constraints.realtime.maxSessionDuration (≥ 10)}`, réponse `{apiKey, expiresAt}`.
- **Un jeton expiré n'arrête pas une session ouverte.** Le plafond est donc porté par `maxSessionDuration` :
  la garde réserve le devis de la durée ENTIÈRE (10 s à 30 min, 5 min par défaut), Decart coupe à la borne, la fin
  de session note le réel (secondes bornées). Pas de battement de cœur à tenir côté client.
- **Prix vérifié** : Lucy 2.5 = 0,02 $/s, mode rapide 0,04 $/s, à la seconde de génération active.
- **Écart G6 :** le SDK publie maintenant une entrée **React Native** (`index.react-native.js`), qui exige
  `@livekit/react-native` + `registerGlobals()` donc un **build de développement Expo** (pas Expo Go). G6 choisira
  entre cette voie native et la WebView au vu de la contrainte de build.
- **Écart G0 → G4 :** le champ de clé des Réglages vit dans le bundle patché (chaîne de patchers), que la session
  Traduction modifie en ce moment. La clé `DECART_API_KEY` est acceptée par `/api/env`, rangée au coffre et listée
  dans les consoles de rotation ; sa SAISIE à l'écran arrive avec l'écran Direct (G4), page autonome hors bundle.
- **Garde réseau :** les deux seules écritures ouvertes au téléphone sont `POST /api/avatar-live/sessions` et
  `/sessions/fin` ; créer ou supprimer un Personnage reste réservé au PC (consentement donné sur le PC).

## 9. Relevé fal pour G1 (10/10/2026, openapi de queue + llms.txt)

| Modèle | Id fal (vérifié 200) | Entrées obligatoires | Options utiles | Prix relevé |
|---|---|---|---|---|
| Remplacer le personnage, garder le décor | `fal-ai/wan/v2.2-14b/animate/replace` | `video_url`, `image_url` | `resolution` 480p/580p/720p (défaut 480p), `video_quality`, `use_turbo`, `seed` | 0,04 / 0,06 / 0,08 $ par seconde de vidéo |
| Animer l'image de réf. avec le mouvement | `fal-ai/wan/v2.2-14b/animate/move` | `video_url`, `image_url` | idem | idem (non relevé séparément) |
| Transfert de mouvement (perso + décor de l'image) | `fal-ai/kling-video/v3/standard/motion-control` | `image_url`, `video_url`, `character_orientation` (image\|video) | `keep_original_sound` (défaut vrai), `elements` (visage frontal + 1-3 vues), `prompt` | 0,126 $/s |
| idem, qualité pro | `fal-ai/kling-video/v3/pro/motion-control` | idem | idem | 0,168 $/s |
| Object swap par consigne | `decart/lucy-edit/pro` | `prompt`, `video_url` | `resolution` 720p (défaut) / 480p, `seed` | 0,15 $/s (720p), 0,10 $/s (480p) |
| idem, rapide | `decart/lucy-edit/fast` | `prompt`, `video_url` | `seed` | non relevé |

Fait notable : Kling Motion Control **garde le son d'origine** par défaut (`keep_original_sound`) et accepte un
« élément » visage (vue frontale + 1-3 vues) pour tenir l'identité — c'est l'usage direct du Personnage (images
0 à 3). `decart/lucy-2-5/realtime` existe aussi sur fal (prompt + `reference_image_url`) : chemin écarté pour le
Direct (0,04 $/s via fal contre 0,02 $/s chez Decart).
