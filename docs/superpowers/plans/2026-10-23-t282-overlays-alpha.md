# t282 — Montage : les overlays vidéo transparents se voient (23/10/2026)

Lot « Agent interne (PC) », brief `2026-10-23-chantier-pc-agent-interne.md`. Branche `claude/montage-overlays-alpha-t282`
(base origin/main 9449c85d).

## Constat mesuré (avant correction)

Jeu d'essai : projets `m_cab716a0` (FR) et `m_e7b0119f` (EN), mix 60 s en couches — v1 plans (h264), v2 textes,
v3 transitions, v4 effets (MOV `qtrle`/`argb`, 1080², 30 i/s).

| Surface | Mesure | Cause |
|---|---|---|
| Rendu (MOV qtrle) | 46,6 dB contre `DVG_mix60s_FR` à 12 s | rien à corriger pour ce format |
| Rendu (WebM VP9 + alpha) | coin du plan noir (0,0,0) au lieu du plan | décodeur vp9 natif de ffmpeg : alpha ignoré (seuls les mattes t186 passaient par libvpx-vp9) |
| Lecteur vivant | `<video>` vide | `/api/jobs/{id}/video` brut : Chromium ne décode ni qtrle, ni ProRes, ni png QuickTime |
| Pistes V2+ | aucune vignette | filmstrip réservé à V1, et l'extracteur lit lui aussi le fichier brut |

## Correction

1. `montage_service._build_montage_command` : les entrées d'overlay vidéo prennent `matte_service.decodeur_entree`
   (`-c:v libvpx-vp9` pour un `.webm`, rien sinon) — les deux branches (overlay simple, séquence t117).
2. `montage_media.calque(src)` : la source telle quelle si le navigateur la lit (h264, vp8, vp9, av1), sinon un WebM
   VP9 + alpha ≤ 480 px de haut en cache (`montage_cache/*_calque.webm`, verrou par cible, écriture atomique).
   Mesuré : 8,7 s pour 60 s de qtrle 1080², 2,6 Mo.
3. `GET /api/montage/calque?src=` : même garde que les précalculs (403/404/415), fabrique à la demande comme `/strip`.
4. Couche sonvfx (saisie L4 `montage_a.py` + `montage_d.py`, retouches G1) : le lecteur vivant lit un overlay (rôle
   « o ») sur l'aperçu de calque (`svU`), les pistes vidéo hautes ont leur bande sur damier (`svV`, `svK`,
   `SvFilmstripO` → `SvmFilmstripCalque`). Remplacements à longueur égale, code neuf en fin de couche.

## Preuves

- Banc `backend/tests/test_montage_calques_alpha.py` : 67/0 — rendu des quatre formats (WebM VP9 + alpha, MOV qtrle,
  ProRes 4444, png QuickTime) en cover et transformé avec opacité, aperçu de calque (alpha_mode=1, coin transparent,
  centre opaque), route, écran, jeu réel (PSNR > 35 dB à 3, 12 et 40 s, témoin « plan nu » nettement plus bas).
- Mutations : décodeur d'overlay retiré, calque jamais nécessaire, calque sans alpha → toutes rouges.
- Backend de preuve 8799 (dossier jetable, projets copiés, fichiers réels en lecture seule, base et timeline de
  l'utilisateur non touchées) : vignettes V2-V4 visibles, lecteur vivant chargé sur les trois calques, rendu par la
  route FR 37,7 / 47,0 / 44,6 / 43,1 / 41,9 dB (3,4 / 12 / 25 / 40 / 55 s), EN 35,1 / 38,5 / 38,0 dB.

## Hors périmètre

- Overlay en séquence PNG (dossier d'images) : pas une source du Montage ; un MOV au codec png est couvert.
- La branche « séquence t117 » du décodeur n'est couverte par aucune mutation du banc (une seule branche mutée).
