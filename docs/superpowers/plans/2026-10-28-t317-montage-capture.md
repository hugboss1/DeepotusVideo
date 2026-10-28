# t317 — D3 : montage après coup des captures — plan détaillé

> **Pour l'exécutant :** SOUS-SKILL REQUISE : superpowers:executing-plans (ou subagent-driven-development), tâche par
> tâche, TDD. Les étapes se cochent dans `.superpowers/sdd/2026-10-28-t317-montage-capture/progress.md`.

**But :** monter après coup une capture de t315 façon Screen Studio : zooms automatiques sur les clics (ajustables,
supprimables), coupes des temps morts (attentes de génération accélérées ou coupées), chapitres tirés des changements
d'écran, sous-titres par le chemin existant, format 16:9 / 9:16 / 1:1, rendu ffmpeg vers la Bibliothèque (avec sa
recette), puis brouillon au Planificateur sur les canaux du projet actif.

**Architecture :** le brut + la piste d'événements restent intacts ; un document `montage.json` (éditable) est proposé
par le serveur d'après `.dzclics.json`, ajusté dans un éditeur (module partagé hors bundle), puis rendu par UN ffmpeg
(zoompan sur le temps d'entrée, recadrage au format qui suit les zooms, segments accélérés/coupés, chapitres en
métadonnées), sous-titres gravés ensuite par `quick_finish`. Aperçu : les mêmes formules en JS sur un canvas.

**Tech :** FastAPI (`backend/app`), ffmpeg 8/9 (`effects_preview.ffmpeg_bin`), modules ES `frontend/shared`, node pour
les bancs d'écran, Python embarqué pour les bancs.

**Spec :** `docs/superpowers/specs/2026-10-25-boite-a-outils-design.md` §8.4 (et §4 boîte `capture`, §8.7, §12 pts 8
et 11). **Base :** `chantier/boite-skins` f1cf9bd9 (t315 + t316). **Branche :** `chantier/boite-montage-capture`.
**Port de preuve :** 8797. Contrats repris : « Contrat pour t316-t319 » (plan t315), « Contrat pour t317-t319 » (plan
t316).

## Global Constraints

- Bundle `index-BEOJX8L5.js` jamais touché : AUCUN maillon (l'éditeur vit dans `frontend/shared/dz-montage-capture*.js`
  chargé par `index.html`). `dz-capture.js` et `dz-capture-scene.js` NON modifiés (t318 en parallèle) : entrées par
  l'événement `dz-capture:fin` et par observation de la boîte de départ.
- Textes visibles : clés `montagecap.*` (3 segments) dans `frontend/shared/i18n/montagecap.json`, assemblées ;
  libellés FR uniques face à la surcouche (test_i18n_l0 2.4). Tout `raise`/`HTTPException` neuf → L10.
- Boucle locale seulement (`routes._require_localhost`) sur toutes les routes neuves.
- Transcription = PAYANTE : devis (`estimate_transcription`) puis `confirme_cout:true` + `max_usd`, puis
  `plafonds.verifier`, sinon rien n'est lancé. Le calage d'un texte connu (gratuit) est le défaut.
- Aucun outil d'agent ne publie : le Planificateur reçoit un BROUILLON (status `draft`) sans canaux → t307 pose les
  canaux du projet actif de l'espace du post.
- Jamais le 8765/8799 ; flux factices en preuve ; aucun appel réseau réel.

## Relevé (28/10)

- ffmpeg du PATH 8.1.1, embarqué 9.0.1 : `zoompan` connaît `it` (temps d'entrée) — essai sur testsrc2 1440×900 WebM :
  zoom ×1,8 entre 1 et 3 s, durée conservée (6,0 s). Les WebM de MediaRecorder n'ont ni durée ni index : remux
  `-c copy` vers `<piste>.remux.webm` (le brut reste tel quel).
- Pas de chapitres vidéo existants : `manuscript_agent.segment_chapters` découpe des TEXTES (inutile ici). Les chapitres
  sortent en métadonnées FFMETADATA et en texte « 00:00 Titre » (description YouTube, légende du brouillon).
- Sous-titres : `quick_finish.segments_for(video, text, source=align|transcribe)` + `burn(video, segs, ratio)` ;
  CANVAS 16:9 1920×1080, 9:16 1080×1920, 1:1 1080×1080 = nos tailles de sortie.
- Planificateur : `POST /api/schedule` sans `channels` ni `comptes` → `library_projects.canaux_par_defaut(espace)`.
- Bibliothèque : `routes._sfx_video_job(dest, titre, provider="capture", etape=…)` (provider `capture` déjà gratuit) +
  `library_index.noter(..., "capture", kind="video", parent=<scène>, relation="montage", recette=…)`.
- Source du rendu : la piste `scene` (caviardée à chaque image, habillée par le skin). La piste brute `ecran` n'a que le
  flou DOM : la remonter avec la caméra perdrait les caches opaques du compositeur (§8.2) et la place de l'encart
  (non journalisée). Choix prudent noté : le zoom agrandit aussi l'encart incrusté.
- Recast sur l'encart : l'encart est incrusté dans `scene` et sa place n'est pas journalisée → pas petit. Laissé en suite.

## Décisions (valeurs)

- **montage.json v1** `{version:1, capture_id, format:"16:9"|"9:16"|"1:1", zooms:[{id, t0, t1, k, x, y}],
  coupes:[{id, t0, t1, mode:"accelerer"|"couper", vitesse:2|4|8|16}], chapitres:[{id, t, titre, ecran}],
  sous_titres:{source:"aucun"|"texte"|"transcrire", texte, langue:"fr"|"en"}}` ; t en ms source ; x, y 0..1.
- **Zooms auto** : un par clic non secret, fenêtre `[t-500, t+1500]` ; clic suivant à < 800 ms de la fin et à < 0,35 du
  centre (x et y) → même zoom (fin repoussée, centre = moyenne) ; durée ≤ 8 000 ms ; `k` = `styleZoom.k` du skin de la
  session s'il est lisible, sinon 1,8 ; bornes k 1,1..2,5 ; rampe 400 ms (smoothstep) ; jamais deux zooms qui se
  chevauchent (le suivant commence à la fin du précédent).
- **Coupes** : paire `generation_debut`/`generation_fin` du même `job_id` d'au moins 3 000 ms → `[debut+500, fin-500]`,
  `accelerer` ×8 ; chevauchements fusionnés. Son d'un passage accéléré : silence. Aucune coupe d'« inactivité »
  (la voix peut parler : suite).
- **Chapitres** : premier à 0 (écran du premier événement `ecran`, sinon `""`) ; un par changement d'écran ; un chapitre
  de moins de 3 000 ms est absorbé par le précédent ; `titre` vide = l'écran affiche le libellé de l'écran
  (mot capitalisé, ex. « Studio ») ; le serveur fait de même au rendu.
- **Validation serveur** (`valider`) : liste blanche des champs, t bornés à `[0, duree]`, `t1 > t0 + 200`, 200 zooms,
  200 coupes, 100 chapitres, titres ≤ 80 sans contrôle, texte ≤ 20 000, chevauchements de zooms rognés, de coupes
  fusionnés ; une coupe ne peut couvrir toute la durée (refus 400).
- **Rendu** : `fps=30` → `zoompan` (taille source paire) → `crop` au rapport du format centré sur `cx(t), cy(t)` borné
  → `scale` à la taille du format → `split`/`trim`/`setpts` par segment (vitesse) ; audio `atrim` ou `anullsrc`
  (accéléré, ou source sans son) → `concat` ; graphe dans un fichier (`-/filter_complex`) ; chapitres remappés au temps
  de sortie (`-map_chapters`) ; libx264 veryfast crf 20, yuv420p, aac 160k, `+faststart`. Un rendu à la fois par
  capture (409). Fichier `outputs/captures/montage_<AAAAMMJJ-HHMMSS>_<id>_<format>.mp4`.

## Fichiers

- Créer `backend/app/services/capture_montage.py`, `backend/app/api/capture_montage_routes.py` ; modifier
  `backend/app/main.py` (routeur `/api/capture-montage`), `agent_outils.py` + `agent_boites.py` (boîte `capture`).
- Créer `frontend/shared/dz-montage-capture-logique.js`, `dz-montage-capture.js` (+ copies `frontend/dist/shared`),
  `frontend/shared/i18n/montagecap.json` ; modifier `frontend/dist/index.html`, dico assemblé.
- L10 `scripts/i18n_l10_traductions.json` ; catalogue `docs/agent/catalogue/*.json`, `docs/agent/AGENT.md`.
- Bancs : `test_capture_montage_service.py`, `test_capture_montage_routes.py`, `test_capture_montage_ecran.py` (node),
  `test_agent_capture.py`.

## Review Focus

1. Capture sans aucun clic ni écran (piste vide, clics décochés) → proposition vide mais rendu possible (16:9 sans zoom).
   Test : service [P] « piste vide » et routes « rendre sans zoom ».
2. Capture sans voix (aucune piste audio dans `scene`) → rendu avec silence, sous-titres « texte » refusés proprement.
   Test : routes « source muette ».
3. Montage envoyé par l'écran avec des zooms qui se chevauchent / hors durée / NaN → rogné ou 400, jamais un ffmpeg
   qui plante. Test : service [V].
4. Transcription demandée sans clé ou sans confirmation → aucun appel, devis rendu. Test : routes « devis ».
5. Deux « Rendre » simultanés → 409 au second. Test : routes « verrou ».

---

### Tâche 1 — service `capture_montage.py`, partie pure (TDD)

**Interfaces produites :** `proposer(clics: dict, *, k=None) -> dict` ; `valider(m, duree_ms, capture_id) -> dict`
(lève `RefusMontage(message, statut)`) ; `segments(m, duree_ms) -> list[tuple[int,int,int]]` (a, b, vitesse ;
vitesse 1 hors coupe) ; `vers_sortie(t_ms, segs) -> float` (ms) ; `chapitres_sortie(m, segs) -> list[{t, titre}]` ;
`texte_chapitres(ch) -> str` (« 00:00 Titre », mm:ss ou h:mm:ss) ; `ffmetadata(ch, total_ms) -> str` ;
`zoom_a(m, t_ms) -> (z, cx, cy)` ; `expressions(m) -> {z, cx, cy}` (chaînes ffmpeg en secondes, variable `T`) ;
`TAILLES = {"16:9": (1920,1080), "9:16": (1080,1920), "1:1": (1080,1080)}`.

- [ ] Banc `test_capture_montage_service.py` [P] proposition : 3 clics groupés → 1 zoom (centre moyen), clic secret
  ignoré, 2 clics éloignés → 2 zooms sans chevauchement, k du skin borné ; génération 10 s → coupe ×8 `[+500, -500]`,
  génération de 2 s ignorée ; chapitres (absorption < 3 s, premier à 0) ; piste vide → listes vides.
  [V] validation : champ inconnu retiré, NaN/bool refusés, t borné, chevauchement rogné, coupe pleine durée 400, titre
  nettoyé. [T] temps : segments complémentaires, `vers_sortie` (coupe retirée, accélérée /8), chapitre dans une coupe
  ramené au début du segment suivant, texte « 00:00 », FFMETADATA. [Z] `zoom_a` = 1 hors zooms, k au milieu,
  rampe monotone ; `expressions` évaluées par un mini-évaluateur Python (`clip`, `between`) = `zoom_a`.
- [ ] Rouge, puis implémenter, vert ; mutations : rampe linéaire au lieu de smoothstep (rouge [Z]), absorption retirée.
- [ ] Commit « montage capture : proposition, validation, temps de sortie, expressions de zoom (t317) ».

### Tâche 2 — rendu ffmpeg (TDD sur vraie vidéo courte)

**Interfaces :** `remuxer(cid, piste) -> Path` (WebM → `<piste>.remux.webm` caché, MP4 rendu tel quel) ;
`sonder(p) -> {largeur, hauteur, duree_ms, audio: bool}` ; `graphe(m, segs, src, fmt) -> str` ;
`rendre(cid, m, dest_dossier) -> {fichier: Path, duree_ms, chapitres, texte}` ; `lire_montage(cid)`/`ecrire_montage(cid,
m)` (`DATA_ROOT/captures/<id>/montage.json`, écriture atomique).
- [ ] Banc [R] : fausse capture (testsrc2 1440×900 + sine, WebM 6 s, sans durée) → remux a une durée ; rendu 16:9 =
  1920×1080, 9:16 = 1080×1920, 1:1 ; coupe 2..4 s accélérée ×8 → durée ≈ 4,25 s ; coupe « couper » → ≈ 4 s ; chapitres
  présents (`ffprobe -show_chapters`) ; zoom visible (pixel au centre d'une image zoomée ≠ non zoomée) ; source muette
  → piste audio présente ; graphe sans chemin utilisateur.
- [ ] Commit « montage capture : remux des WebM, rendu ffmpeg (zooms, format qui suit les zooms, coupes, chapitres) ».

### Tâche 3 — routes `/api/capture-montage` + L10

`GET /captures` (sessions `terminee`, plus récentes d'abord : id, date, durée, montage enregistré, rendus) ;
`GET /{cid}` → `{capture:{id, duree_ms, cadre, skin}, evenements, montage, propose: bool}` (proposé si aucun
enregistré) ; `PUT /{cid}` {montage} → validé, écrit ; `POST /{cid}/proposer` → proposition neuve (non écrite) ;
`POST /{cid}/rendre` {montage?, titre?, confirme_cout?, max_usd?} : transcription → `{ok:false, devis}` tant que non
confirmée (409 si le devis dépasse `max_usd` + 0,0005), `plafonds.verifier({"kind":"transcribe",…}, "capture")` ; rendu
dans un fil ; sous-titres (`quick_finish.segments_for` + `burn`, échec dit sans perdre le rendu) ; job `capture`
(étape « Montage ») ; index `capture` (parent = scène, relation `montage`, recette = résumé du montage) → `{job_id,
fichier, duree_s, chapitres_texte, sous_titres}`. Capture non close → 409 ; d'un autre id → 400/404.
- [ ] Banc `test_capture_montage_routes.py` (TestClient, ffmpeg réel, transcribe remplacé) : 403 hors local partout ;
  liste ; lecture proposée ; PUT validé et relu ; rendre → job + index (parent, recette) ; verrou 409 ; devis puis
  confirmation (faux transcribe appelé une fois, plafonds écrit) ; source muette + « texte » → rendu ok, sous-titres
  dits impossibles ; L10 anglais. Mutation : garde locale retirée → rouge.
- [ ] Commit.

### Tâche 4 — outil d'agent `lire_piste_clics` (boîte `capture`)

Nature `lecture` ; args `{capture: id}` ; rend durée, écrans (chapitres proposés), clics (t, écran, fiche, libellé) —
libellés ENCADRÉS (`_preuve`), 300 clics au plus. Boîte `capture` = `["lire_piste_clics"]`, `agents: []` (comme `scan` :
§11 bis, le Tutoriel est « Demander » ; la fixture Campagnes reste figée), `mobile: False`.
- [ ] Banc `test_agent_capture.py` : boîte saine (`verifier()` vide), hors boîte pour Campagnes, lecture d'une piste,
  id invalide refusé, libellé hostile encadré ; `test_agent_boites` reste vert.
- [ ] Commit.

### Tâche 5 — éditeur côté écran

`dz-montage-capture-logique.js` (pur) : `zoomA(m, t)` (= Python), `segments`, `versSortie`, `horloge(ms)`,
`ajouterZoom(m, t, x, y)`, `cadreFormat(fmt, l, h, cx, cy)`. `dz-montage-capture.js` : `window.__dzMontageCapture =
{ouvrir(id?), liste()}` ; boîte plein écran (charte dialogue) : aperçu canvas (zoom + recadrage du format, saut des
coupes, vitesse), lecture/pause, frise (zooms, coupes, chapitres, clics) ; listes réglables (zoom : début, fin,
niveau, supprimer ; « Zoom ici » ; coupe : mode, vitesse, supprimer ; chapitre : titre, supprimer) ; format ;
sous-titres (aucun / texte connu gratuit / transcrire payant avec devis à confirmer) ; « Proposer à nouveau »,
« Enregistrer », « Rendre » ; résultat : Bibliothèque, texte des chapitres, « Planifier un brouillon » (POST
/api/schedule, status draft, sans canaux). Entrées : bouton « Monter la capture » dans la boîte de fin (`dz-capture:fin`),
lien « Monter une capture… » posé dans la boîte de départ (observation, sans modifier dz-capture.js).
- [ ] Banc `test_capture_montage_ecran.py` (node) : `zoomA` JS = Python sur 50 instants ; segments/versSortie ;
  cadre 9:16 borné ; faux DOM : entrée posée dans la boîte de fin, éditeur ouvert, devis jamais confirmé d'office ;
  livraison : copies shared == dist, balise unique après dz-capture.js, pas d'alert/confirm/prompt ni emoji, clés
  FR/EN employées et assemblées.
- [ ] Commit.

### Tâche 6 — catalogue, L10, preuve, relecture

Fiches `montagecap.*` (connaissance-agent, `catalogue.py --check`), AGENT.md ; L10 `--check` ; preuve 8797 FR/EN
(capture factice → éditeur → zooms, coupe, chapitres, 9:16 → rendu → brouillon) dans
`docs/superpowers/specs/captures/t317/` ; relecture finale indépendante, une vague de corrections ; bancs base/HEAD.

## Contrat pour t319

- **Piste → étapes** : `capture_montage.proposer(clics)` rend déjà les CHAPITRES (écran par écran) et les ZOOMS (un par
  geste, centre, début/fin) : un brouillon de tutoriel = un chapitre par écran, une étape par zoom (sa fiche du
  catalogue = celle du clic le plus proche dans `evenements`). `vers_sortie(t, segments(m, duree))` donne l'instant de
  l'étape dans la vidéo montée (captures des trois temps : `t0`, milieu, `t1` du zoom).
- **Lecture** : `GET /api/capture-montage/{cid}` → `{capture, evenements, montage}` ; outil d'agent
  `lire_piste_clics` (boîte `capture`, aucun agent ne la déclare encore : t319 l'ajoute à « Demander » s'il lui faut).
- **Rendu** : `POST /api/capture-montage/{cid}/rendre` rend `{job_id, fichier, chapitres_texte}` ; la recette d'index
  porte `capture_id`, `format`, nombres de zooms/coupes/chapitres. Un export `.dzparcours` peut joindre ce mp4 et la
  piste. Formules de zoom partagées : `zoomA` (JS) = `zoom_a` (Python), à réutiliser pour surligner pendant la lecture.
