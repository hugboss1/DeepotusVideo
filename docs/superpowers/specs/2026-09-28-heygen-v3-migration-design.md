# Migration HeyGen v1/v2 → v3 — conception datée (28/09/2026)

Suivi des chantiers, tâche #1 (P0). HeyGen retire ses endpoints v1/v2 le
**1er novembre 2026** (developers.heygen.com, « Endpoint Version
Comparison » : phase de dépréciation jusqu'au 31/10, retrait ensuite).

## Correspondance appliquée

| Usage dans l'app | Avant | Après (v3) |
|---|---|---|
| Génération par défaut (`pipeline.run_heygen`) | `POST /v2/video/generate` | `POST /v3/videos` (type avatar) |
| Statut | `GET /v1/video_status.get` | `GET /v3/videos/{id}` (`failure_message`) |
| Liste d'avatars | `GET /v2/avatars` + groupes photo | `GET /v3/avatars/looks` (private puis public, 50/page) |
| Moteurs d'un look | — | `GET /v3/avatars/looks/{id}` (`supported_api_engines`) |
| Liste de voix | `GET /v2/voices` | `GET /v3/voices` (private puis public, 100/page) |
| Quota / santé | `GET /v2/user/remaining_quota` | `GET /v3/users/me` (wallet / subscription / usage_based) |
| Avatar depuis une photo | `upload.heygen.com/v1/talking_photo` | `POST /v3/avatars` (type photo, base64) + statut du look |

Retirées faute d'appelant : `upload_asset` (v1), groupes photo v2
(`create_photo_avatar_group`, `upload_photo_to_group`, `train…`,
`get_photo_avatar_status`, `list_photo_avatar_groups`), traduction v2.
`heygen_service.py` ne contient plus aucun chemin `/v1/` ni `/v2/` (banc 6.2).
Les formes renvoyées à l'UI sont conservées (`avatar_id`, `avatar_name`,
`preview_image_url`, `avatar_type`, `preview_audio`…) : aucun patch de bundle.

## Décisions (utilisateur, 28/09)

- **Moteur par défaut : Avatar III**, comme l'ancienne génération v2 (la v3
  prend Avatar IV quand on n'en donne pas). Résolu PAR LOOK : un look sans
  Avatar III prend le premier moteur qu'il déclare. Moteur explicite gardé ;
  l'ancien drapeau `use_avatar_iv` donne `avatar_iv`.
- **Pauses SSML converties en ponctuation** (`ssml_to_plain`) : la v3 ne
  documente pas le SSML ; `<speak>` retiré, `<break …/>` → « … ».
- **Preuve payante autorisée** (1 à 2 générations courtes).

## Mesures réelles (compte de l'utilisateur, 28/09)

- `users/me` : facturation **wallet**, solde en dollars (12,33 $) — l'ancien
  code ne lisait que des crédits ; `remaining_usd` est désormais servi à la
  santé et à `/cost/balances`.
- Génération v3 par défaut, look privé « DEEPOTUS Prophet », voix française,
  script SSML : Avatar III résolu, 4,5 s 1080×1920 avec audio en 220 s,
  **0,08 $** ; silence mesuré 1,47 → 2,04 s à l'emplacement du `<break>` (la
  pause convertie est bien jouée, aucune balise lue).
- Photo avatar v3 : look entraîné (`completed`, moteurs III/IV/V), présent
  dans les looks privés, **1,32 $** — nettement plus cher qu'une génération.
  Écart découvert : un WebP nommé `.jpg` était refusé (« Content type not
  match image/jpeg != image/webp ») → type lu dans les octets, tout format
  autre que PNG/JPEG converti en PNG (Pillow).
- Listes : **9 951 looks en 259 s** (~200 pages), 2 944 voix en 33 s — contre
  ~60 s pour l'ancien `/v2/avatars`. D'où le cache à trois étages : mémoire
  (6 h) → disque `DATA_ROOT/cache/heygen_{avatars,voices}.json` (servi jusqu'à
  30 j, rafraîchi en arrière-plan au-delà de 6 h) → API ; demandes simultanées
  fusionnées. `invalidate_list_cache()` efface aussi le disque.
  Mesuré ensuite en deux processus : 1er lancement 9 951 looks en 263 s
  (copie disque 7,3 Mo), lancement suivant **0,08 s**.

## Écarts datés / limites connues

- Un **ancien talking photo** (id v1) passe aussi par `POST /v3/videos` ; la
  v3 ne documente que les looks. Aucun n'est enregistré dans les castings de
  l'utilisateur (vérifié en base) ; s'il en existe ailleurs, HeyGen renverra
  une erreur lisible — recréer l'avatar depuis la photo.
- La ponctuation ne rend pas la durée exacte d'un `<break time>`.
- L'avatar de test « DeepotusVideo - test migration v3 (a supprimer) » reste
  sur le compte : la v3 n'a pas de suppression documentée.
- Le premier chargement SANS copie disque reste de ~4 min (une fois).
