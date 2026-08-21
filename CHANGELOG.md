# Changelog

> Version history for Deepotus Video Gen. The current version, repository layout, and usage are in [`README.md`](README.md).

---

# 🐙 Deepotus Video Gen — v2.4.0 "Cardforge universel"

**Card Forge** passe de l'éditeur 8 modules à un atelier complet : la carte
s'exporte **par couches** prouvées au pixel, les couches se traitent dans un
**graphe 3D** gratuit et local (plan, relief, assemblage, artefact glTF/STL),
et le graphe s'ouvre aux **moteurs image→3D** payants — 5 moteurs fal +
Meshy 6/7 en API directe — avec matières, finitions holographiques et fusion
des GLB moteurs dans l'artefact final. Prix affiché AVANT chaque dépense,
tout le reste à 0 $.

## Export par couches (phase 1)

Six couches nommées par rôle + le composite, recto et verso, PNG alpha au
canvas exact (300 DPI réels, chunks pHYs/sRGB/gAMA/cHRM) ; l'écran PROUVE
l'empilement (0 px d'écart) avant de téléverser, le serveur contre-prouve en
PIL et scelle un manifeste `card-3d/layers-manifest@1` (identité de carte,
bbox mm, coverage mesuré — l'absence se mesure, elle ne se devine pas). Un
corps mal formé ne fait jamais 500 : 400/409/413 nommés, mesurés par tests.

## Le graphe gratuit (phase 2a)

Vocabulaire en bloc miroir JS↔py (layer, plane, relief, assemble, artifact),
`clean_graph` répare et ne lève jamais ; relief SOLIDE fermé par
construction, quad exact ; writer glTF/GLB « écrit juste du premier coup » :
bornes d'accesseurs exactes, zéro champ d'identité, samplers CLAMP, échelle
physique mm→m ; STL binaire local ; metadata façon ERC-721 ; écran liste
honnête + aperçu model-viewer + bordereau.

## Forge 3D (phase 2b)

- **7 moteurs image→3D** sur le nœud `mesh3d` : tripo, hunyuan, trellis,
  rodin, triposr (fal, prix en $) + **meshy-6/meshy-7 en API directe**
  (crédits, grille officielle 20/30/35, **ultra +5 cr** sur v7/latest, des
  DEUX côtés du miroir JS↔py) — prix AVANT, job par nœud (job.json atomique,
  poll avec reprises, orphelins avoués après redémarrage, 409 anti
  double-lancement payant, journal meshy récupérable au 3D Studio).
- **Matières & finitions** : matières de la boutique tuilées au pas physique
  (pack MR glTF), finitions **argent/dorure holographiques** (iridescence +
  clearcoat + anisotropie, `extensionsUsed` uniquement, TANGENT w=−1), TRS
  par élément.
- **Fusion des GLB moteurs** dans l'artefact : réindexation complète, fit à
  la boîte mm de SA couche, identité du doc externe jetée, extensions
  externes déclarées honnêtement ; **STL mixte** gate par `closed` mesuré
  UNE fois (refus motivé, jamais un solide menteur).
- **Écran** : rangées chaînées layer→traitement→matière→transform, moteurs
  et prix servis par `/info` (jamais recopiés), chips d'état, coût du graphe
  avant, `degraded` et `run_id` dits tels quels.
- **2 courses Windows réelles** du job.json trouvées en vérification
  navigateur (250 GET concurrents) et corrigées des deux côtés — un poll ne
  tue plus le job payé qu'il observe.

## Fluidité & outillage

Barre §9.6 sur toutes les surfaces de drag du lab (≤ 1 patch par frame, état
final exact au relâché, poignées 12 px, `touch-action: none`, molette P1
coalescée à la frame) ; lint : **R13 « octets sains »** (zéro NUL/CRLF brut)
et **R14 « échappement »** (interpolations HTML) ; audit de couture des 15
plans et 23 specs — les extraits resynchronisés sur le code livré.

## Chiffres

78 tests forge3d, lint 9 modules 0 violation, ~95 commits depuis v2.3.0,
duels aveugles par tâche, ZÉRO dépense réelle (mock Meshy, fal monkeypatché).

## Reste connu — nommé

Chatoiement holo à juger à l'œil en tournant le viewer ; bloc fluidité à
re-vérifier au pointeur réel ; capture d'aperçu ; cas deux onglets ;
rétention du double stockage meshy3d à arbitrer. (Le chapitre Forge 3D du
guide illustré, d'abord nommé ici en reste, est livré depuis — chapitre 19
FR/EN avec capture réelle, PDF 30 pages.)

---

# 🐙 Deepotus Video Gen — v2.3.0 "Cardforge"

**Card Forge**, nouveau 9ᵉ sous-onglet du hub **Game Assets** : un éditeur de
cartes à jouer complet, des faces importées ou générées par IA jusqu'à
l'export imprimeur et l'export 3D façon NFT — huit modules indépendants
(face, cadre, typographie, données, volume, matières, impression, export 3D)
partageant un même contrat d'état pour rester isolés les uns des autres.

## Ce qui est garanti, mesuré sur les fichiers produits

| Exigence | Preuve |
|---|---|
| **300 DPI réels** | PNG à `canvas_px` exact avec chunk `pHYs` à 11811 px/m (299,9994 DPI) |
| **Fond perdu + zone de sécurité** | 12 formats de carte + planches A4/Letter/A3, tolérance **0 pixel** contre l'arithmétique du domaine |
| **PDF prêt imprimeur** | `MediaBox` **+ TrimBox + BleedBox** sur chaque page, traits de coupe vectoriels — ce que la référence gratuite du domaine (nanDECK) n'a pas |
| **glTF/GLB avec jeu PBR complet** | `.glb` **et** `.gltf` autonome, 8 maps nommées (basecolor, normal, roughness, metallic, ao, height, emissive, orm), attribut `TANGENT` |

## Comment c'est jugé

Chaque module a été construit et vérifié par un protocole de **duel aveugle
certifié** contre un produit réel et gratuit du domaine (Clash of Decks pour
la face/le cadre/la typographie, nanDECK pour le CSV et l'impression, Meshy
pour la 3D, Sorceress Material Forge pour les textures) : deux critiques sans
accès au dépôt ni au web comparent une planche recadrée sur le seul panneau
jugé, à l'aveugle, côtés tirés au sort. **Les 8 modules sont acquis, sur 32
duels sans une seule exception.**

## Reste connu — soldé le 19/08/2026

Les deux restes nommés par les critiques à la clôture du gauntlet sont soldés,
mesures sur les octets à l'appui :

- **Canal d'émission.** Le reproche littéral (« produit et livré dans
  l'archive, câblé par rien ») ne se reproduisait déjà plus au moment où la
  note ci-dessus a été écrite : une émission nulle n'embarque plus la map (ni
  `emissiveTexture`, ni `map_Ke`, ni le PNG), une émission non nulle la livre
  **câblée des deux côtés** — la note avait une version de retard sur le
  code, faute d'avoir été re-mesurée. Le trou réel était ailleurs : aucun
  geste ne permettait d'atteindre le canal sans changer toute la matière
  (dorure ou holographique). Nouveau réglage **Émission (0..1)** dans
  l'export 3D, qui prime sur la finition : encre luminescente sur papier mat,
  ou dorure éteinte — `emissiveFactor` réglé, map câblée dans GLB, glTF et
  MTL, valeur écrite dans les manifestes, bornes publiées par `/info`, le
  défaut ne changeant aucun octet. Trois tests sur les octets livrés.
- **Cadrage de la pose (pièce 01).** Cause première trouvée : le cadre n'a
  **jamais publié sa fenêtre** — `frame.art_window`, la clé que la face lit
  depuis le premier jour, n'était écrite par personne, donc le mode « auto »
  retombait toujours sur la toile entière et la pose par défaut passait sous
  le cadre. Le cadre publie désormais sa fenêtre effective (relue sur le
  calcul qui peint, pas une seconde formule), la molette zoome dans le repère
  de la fenêtre (le même que le painter), et la correction s'offre **en un
  clic** — bouton du panneau et offre contextuelle à côté du chiffre de
  masquage, qui s'efface quand la pose est déjà calée.

Reste connu, non corrigé : l'émission est bornée à 1.0
(`KHR_materials_emissive_strength` n'est pas implémenté — un halo plus fort
ne s'exporte pas), et le contenu de la map d'émission reste dérivé de la
luminance de la carte (seuil réglable) : pas encore de masque d'émission
peint à la main.

---

# 🐙 Deepotus Video Gen — v2.2.0 "Catalogue de démarrage"

Les trois sous-catégories de **Son & VFX** étaient des promesses non câblées :
SFX affichait cinq fausses lignes injouables, VFX particules six vignettes
mortes annonçant « pas encore câblé — $0.06 par élément », Musique « aucun
backend n'existe aujourd'hui ». Un acheteur sans clé ElevenLabs ni clé fal
n'avait rien à essayer, seulement des tarifs.

## Catalogue CC0 embarqué — 606 sons, 80 textures, 5 séquences (22 Mo)

| Pièce | Mécanisme |
|---|---|
| **Source** | 10 packs [kenney.nl](https://kenney.nl), **Creative Commons Zero** — la seule licence redistribuable dans un installeur commercial sans attribution ni contrainte virale. Freesound/Pixabay ont été écartés : leurs licences sont décidées fichier par fichier, jamais récupérables en masse. |
| **Fabrication** | `scripts/build_starter_catalog.py` : *fetch → vérification de la licence DANS chaque archive → curation → index → auto-vérification*. Le contrôle de licence n'est pas décoratif — une source qui cesserait d'être CC0 fait **échouer le build** au lieu de contaminer l'installeur. `--check` confronte `catalog.json` aux fichiers présents dans les deux sens (déclaré-absent ET présent-non-déclaré). |
| **Durées** | lues dans l'en-tête Ogg (granule de la dernière page ÷ fréquence) au moment du build. 606 `ffprobe` au runtime auraient été 606 sous-processus à chaque affichage de liste. |
| **Service** | montage statique sur `/starter` — traversée de chemin, requêtes Range (lecture audio) et en-têtes de cache déjà traités correctement, plutôt qu'une route maison à écrire. Index via `GET /api/starter/catalog`. |
| **Import** | `POST /api/starter/import` recopie l'élément dans la Bibliothèque avec le même sidecar qu'un fichier importé. Il devient un asset utilisateur ordinaire : le tiroir Sons, le Montage et le rendu n'ont aucun cas particulier à connaître. |

## Génération de sprites de particules — locale, gratuite, hors ligne

Un système de particules est un **compositeur**, pas un modèle : il n'y avait
rien à facturer. `particle_service.py` simule l'émetteur en PIL pur (le runtime
embarqué n'a pas numpy) et repasse le résultat dans `sprite_service._assemble`,
déjà écrit pour le Sprite Lab. La sortie est un job `sprite2d` ordinaire —
l'onglet Sprites de la Bibliothèque, la visionneuse GIF, l'export ZIP et le
pack Unity fonctionnent sans une ligne supplémentaire.

**Le « $0.06 par élément » devient « gratuit · local ».** Un tarif qui survit au
câblage est un mensonge d'interface.

12 presets = (texture CC0 + réglages d'émetteur), donc la grille de sélection
est directement exécutable au lieu d'être décorative.

Trois défauts trouvés **en regardant des planches de contact**, invisibles au
test unitaire :

- **frame 0 entièrement transparente** sur les 12 presets — donc une vignette
  noire partout dans l'app. Corrigé : la moitié d'un `burst` naît exactement à
  t=0 (une explosion commence à pleine intensité), et les émetteurs `stream`
  utilisent un temps **cyclique**, ce qui peuple la frame 0 *et* rend la boucle
  réellement raccordée — le « alpha · boucle » des presets cesse d'être un
  mensonge ;
- **textures directionnelles tournées au hasard** — le départ de coup et la
  traînée sont des formes qui pointent quelque part ; corrigé par un mode
  `orient` explicite (`random` / `velocity` / `fixed`) ;
- **effets d'ambiance émis d'un point** — la neige et les braises doivent
  couvrir le cadre ; corrigé par une zone de naissance.

## Musique — 4 modèles fal.ai sur la clé déjà configurée

`fal-ai/lyria3` (défaut), `fal-ai/stable-audio-25/text-to-audio`,
`fal-ai/minimax-music/v2.6`, `CassetteAI/music-generator`, plus 8 ambiances qui
injectent genre, tempo et instrumentation — un prompt de musique vide donne
toujours le même résultat tiède, et l'utilisateur ne devine pas ce qui compte.

Chaque modèle **déclare ses capacités** (durée réglable ou imposée, paroles,
instrumental, graine). Un réglage non supporté est retiré de la charge utile
**et signalé** dans `notes` : taire des paroles ignorées est pire que les
refuser. L'UI grise ce que le modèle sélectionné ne sait pas faire.

## Correctifs

- **Le rail de Son & VFX affichait les VOIX quel que soit le générateur
  sélectionné.** Le rail et les onglets étaient deux états indépendants :
  choisir « VFX particules » laissait une liste de comédiens à l'écran.
  `pickGen`/`pickTab` partagent désormais une seule sélection, dans les deux
  sens.
- Côté SFX, le catalogue livré (gratuit) s'affiche **avant** la carte de
  génération facturée : un utilisateur sans clé atteint quelque chose
  d'utilisable avant d'atteindre un prix.
- **Sprite Lab** : nouvel onglet « ✨ Démarrer », en première position — les
  trois autres (Image / Render / Vidéo) sont vides pour un nouvel utilisateur.

## Outillage

`scripts/reapply_inblock_patches.py`. Rafraîchir le bloc `sonvfx` effaçait
**silencieusement 22 correctifs** de `vfxrack` et `subs`, qui modifient
l'*intérieur* de ce bloc : bundle syntaxiquement valide, quatre marqueurs
présents, taille quasi identique — et pourtant la piste de sous-titres et le
rack VFX avaient disparu de l'éditeur. `repatch_all.py --from sonvfx` ne répare
pas ce cas (il donne aux patchers aval un `.bak` contenant déjà le résultat de
leurs couples hors-bloc, dont les ancres sont alors introuvables).

Le nouvel outil rafraîchit puis rejoue les couples **en ne cherchant les ancres
qu'entre les bornes du bloc**, donc sans jamais dupliquer un couple hors-bloc.
Idempotent, vérifié sur trois passes.

Piège associé, documenté dans le README : les blocs injectés sont en **CRLF**.
Une source de patch réécrite en LF fait échouer toutes les ancres multi-lignes,
sans autre symptôme qu'un `anchor count=0`.

## Tests

47 nouveaux (`backend/tests/test_starter_particles.py`) : licence CC0 de chaque
source, intégrité du catalogue dans les deux sens, exhaustivité des familles,
frame 0 non vide de **chaque** preset, déterminisme à graine fixe, raccord de
boucle, confinement des chemins d'assets, et contrat de chaque modèle de
musique. Suite existante : 50/51 — le seul échec (`test_mesh_optimize`,
gltfpack non provisionné) est antérieur.

---

# 🐙 Deepotus Video Gen — v2.1.0 "3D Studio"

## 🐙 3D Studio Meshy — écran 1 du design « DeepOtus Studio » (spec `INTEGRATION-MESHY.md`)

Pipeline Meshy **réel** : prompt/réf → maillage (preview) → texture PBR
(refine) → remesh quad → auto-rig → animations → export, rendu par le graphe
8 nœuds de la maquette (câbles animés, journal des tâches, panneau nœud
actif avec les noms de champs de l'API, rail moteur/coût/transport).

| Pièce | Mécanisme |
|---|---|
| **Écran** | `frontend/studio3d/` (page standalone, direction Cinema via `deepotus.tokens.css`), montée à `/studio3d` et iframée par le hub Game Assets « 🐙 3D Studio » (`patch_bundle_studio3d.py`). Le sous-onglet 🧊 3D (fal) reste l'onglet par défaut, intact. |
| **Client** | `frontend/meshy/meshy.client.js` (client de référence de la spec, servi à `/meshy/`) : tarifs officiels, `estimatePipeline`, orchestrateur `MeshyPipeline` — le graphe ne pilote rien, il rend l'état émis. |
| **Proxy** | `/api/meshy/{path}` (backend/app/services/meshy_service.py) : la clé `MESHY_API_KEY` ne quitte jamais le serveur, chemins strictement allowlistés (surface docs.meshy.ai), relais SSE `/:id/stream` en streaming. |
| **Coût** | estimé ligne à ligne AVANT chaque lancement (rail + modale de confirmation) ; après coup, seule vérité comptable = `consumed_credits` (tâche FAILED remboursée) ; solde `GET /balance` affiché. |
| **Bibliothèque** | table `meshy_tasks` + rapatriement automatique des binaires dans `outputs/meshy3d/<task_id>/` dès `SUCCEEDED` (les URLs Meshy expirent), servis à `/api/meshy3d/files/…` ; journal `GET /api/meshy3d/tasks`. |
| **Mode mock** | `MESHY_MOCK=1` : simulateur local fidèle (statuts, progress, crédits, GLB/PNG minimaux valides) — pipeline complet sans clé ni crédits, pour la démo et la QA. |

Notes :
- La clé se saisit dans **Réglages → « Meshy 6 (3D · optional) »** (allowlist
  `.env` existante) ; `/api/health` expose `has_meshy` / `meshy_enabled` /
  `meshy_mock`.
- Game Assets 3D (fal tripo/rodin/hunyuan/trellis/triposr) est inchangé ;
  `engine=meshy` sur `/api/assets/3d` renvoie toujours 501 en pointant vers
  le 3D Studio.
- QA : `scripts/qa/qa-studio3d.js` (parcours complet en mock, 15 checks +
  5 captures) ; `qa-shell-audit.js` passe à 20 vues (hub « 3D Studio » +
  `/studio3d/` large et 900px), `DZ_BASE` paramétrable.
- Tests : `backend/tests/test_meshy_service.py` (23 assertions — pricing,
  estimation, allowlist, pipeline mock de bout en bout via le proxy HTTP,
  persistance, rapatriement, SSE, 403/503, non-régression ENGINES fal).

---

# 🐙 Deepotus Video Gen — v2.0.0 "Studio Cinema"

## 🎨 Refonte UI v2 — direction Cinema (design « DeepOtus Studio »)

La direction visuelle **Cinema** (surfaces neutres chaudes `#0a0a0c/#151519`,
accent doré unique `#f0b429`, typo IBM Plex Sans / Space Grotesk / JetBrains
Mono) remplace « Deep Lab » (cyan/bleu nuit) sur toutes les surfaces, sans
toucher au JS du bundle ni à aucune fonctionnalité.

| Surface | Mécanisme |
|---|---|
| **App React (bundle)** | `frontend/dist/theme-v2.css` chargé après le CSS du bundle : redéfinition des tokens Shell Pro (`--bg-*`, `--ink-*`, `--cyan`, `--node-*`…), composants (`.panel`, `.input`, `.btn-primary` aplat doré), 46 utilitaires Tailwind Deep Lab réaccordés. Réversible en retirant le `<link>` de `frontend/dist/index.html`. |
| **Atelier Chapitre** | `frontend/atelier/atelier.css` réécrit (drop-in : 0 sélecteur manquant vs v1.22, `atelier.js` inchangé) + `preview.html` d'aperçu dev-only. |
| **Sprite Lab / Tile Lab** | tokens `:root` de `spritelab.css` basculés Cinema (tilelab hérite). |
| **Tokens partagés** | `frontend/shared/deepotus.tokens.css` (copie servie dans `dist/shared/`) : source unique, thème clair `data-theme="light"`, échappatoire `data-direction="deep"`. |

Notes :
- Les couleurs **de contenu** (overlays vidéo, fonds des templates de rendu,
  color picker) ne changent pas — le thème n'affecte que le chrome de l'UI.
- `IBMPlexSans.ttf` n'est pas encore embarqué dans `/fonts/` : repli propre
  sur Inter (à déposer plus tard dans `frontend/dist/fonts/`).
- Maquettes de référence : projet Claude Design « DeepOtus Studio »
  (`DeepOtus Studio.dc.html`, direction verrouillée `cinema`).

## 📦 Chantiers embarqués dans cette version (lignée d'intégration)

Cette version scelle la lignée v1.16 → v1.22 restée en PR :
Shell Pro (11), Quick Voice Over (V-a), nœud Studio Voiceover + mixage au
render (V-b), casting voix par personnage + VO minuté (atelier-voices),
modèles vidéo fal + Google natif à la volée (W-a), modèles/précision
ElevenLabs + fix résidu 0 octet (W-b), Gemini `gemini-flash-latest` partout
(W-c), pont video-shotcraft de l'agent de découpage (W-d), Sprite Lab,
Tile Lab, Game Assets 3D.

---

# 🐙 Deepotus Video Gen — v1.15.8 "Game Assets Library"

## 🆕 What's new

| Feature | Description |
|---|---|
| **Library → 3D tab** | All generated 3D assets now have their own Library tab: preview thumbnail (engine preview render, falling back to the source shot), full-size **rotating 3D viewer** in the modal, one-click **GLB download**, favorites ★, **Rename** and **Delete**. 3D favorites also appear in *Favoris*. |
| **Guide chapter 17** | New illustrated chapter (FR/EN) covering the whole Game Assets workflow — form, options, pipeline canvas, result cards, Library 3D tab — with fresh screenshots; §16 updated for the one-click import. |
| **One-click migration import** | `IMPORT-TOUT.cmd` + `import-all.ps1`: double-click on the new PC restores app + generations + calendar + keys **and Claude Code sessions**, with a free-disk-space check. `export-migration.ps1` can now bundle the installer (`-Installer`) and Claude sessions (`-IncludeClaude`). |

## 🛡 Security & fixes (code review pass)

| Fix | Description |
|---|---|
| **Path traversal (High)** | `POST /api/assets/3d` accepted any `image_filename` path — a crafted value could upload an arbitrary local file (e.g. the API-keys `.env`) to the fal CDN. Now strictly validated (basename + Library containment) at both route and service level, with fail-fast 400s for bad `views`/`formats`. |
| **Blocking downloads (High)** | Mesh/preview/shot downloads ran synchronously inside the event loop without a timeout: a large or stalled download froze the whole API. Now `asyncio.to_thread` + 120 s timeout. |
| **Game Assets page overflow** | The page had no scroll container and painted over the Job dock — the ghost green "done" chips seen on empty rows at the bottom. Both form and canvas views now scroll properly. |
| **3D jobs leaking as videos** | GLB assets no longer appear in the Studio "Existing render" picker nor in the Scheduler render list. |
| **Robustness** | A failed multi-view boost no longer kills the whole (already paid) job; generation errors now surface as a clear message instead of an eternal "generating" canvas; manifest polling stops re-fetching completed assets every 4 s; unsupported export formats are reported (`skipped_formats`) and the cost estimate now counts extra-format re-exports; new `GET /api/assets/3d/{job}/preview` route. |

Backend: `asset3d_service.py`, `routes.py`, `pricing.py` (+9 tests, 30 green). Frontend bundle: Library 3D tab, Game Assets scroll fix, error surfacing, filters. All verified end-to-end in the running app.

---
# 🐙 Deepotus Video Gen — v1.15.7 "Studio Effects"

## 🆕 What's new

| Feature | Description |
|---|---|
| **Effects / Mask node** (Studio) | New Composition node wired to a new Render `fx` port. 21 ffmpeg effects: **LUT/grade** presets (Teal&Orange, Cyberpunk, Deep-sea, Noir, Vintage…) + user `.cube`, **VHS** (sequenceable line displacement, intensity/speed), **Colorize** presets, parametric **Gradients**, plus grain, vignette, chromatic aberration, glitch, bloom, halation, scanlines/CRT, letterbox, old film, sharpen, blur, dreamy, pixelate, camera shake, mirror, invert. **Thumbnail picker**; apply to the whole render or a **specific node/layer** (targeting resolved backend-side from the source graph). |
| **Preview button** | The top-bar Preview now renders a **cheap, fast** version of the final composition — Seedance/HeyGen slots use their source still (no fal/HeyGen cost), short duration — so you can see framing + overlays + effects **before** the paid Run. |
| **Overlays on every branch (fix)** | Text overlay / Ticker / Separator wired to the Render node now render on **all** composition branches (UGC, montage, spatial compose), not only spatial compose. Rebuilt backend-side from `source_graph` (`graph_overlays`/`graph_effects`). |
| **Migration / export kit** | `export-migration.ps1` + `import-migration.ps1` + bilingual `MIGRATION.md` (Desktop `deepotus-migration`): move the app (with all new features), every generation, the **calendar + scheduled posts**, and API keys to another PC — with a consistent DB snapshot and automatic path-rewrite. Documented in the in-app guide (§16). |

Backend: `effects_engine.py`, `graph_effects.py`, per-region + global `post_effects` in `build_ffmpeg_command`, `TemplateRenderRequest.preview`. Frontend bundle: `Effects` node + Render `fx` port + `DzEffectsPanel` (thumbnails) + Preview wiring. All verified end-to-end in the running app.

---

# 🐙 Deepotus Video Gen — v1.8.0 "Reef Edition"

## 🆕 What's new in v1.8.0

Major UI refonte (Direction B — "Reef") shipped from the Claude Design handoff.
The old 5-tab grid is gone; everything now lives in a Sidebar shell with a
permanent JobDock and a brand-red Deepotus logo.

| Feature | Description |
|---|---|
| **Sidebar shell** | Collapsible left nav (Quick · Studio · Scheduler · Templates · News · Library · Settings), persistent JobDock at the bottom, sticky topbar with health badges + ⌘K command palette. |
| **🌊 Node Studio** | New visual graph editor — drag nodes, connect typed ports (image / video / audio / av / text / data), 30+ node types across 7 categories (Sources / Generators / Audio / Edit / Composition / Master / Output), 4 starter graphs (Seedance solo · Avatar post · News reel · Timeline), live `▶ Run` cascade with halo pulse, `◐ Preview` local-only path, mini-map, inspector. |
| **📅 Scheduler** | Week calendar of scheduled posts + per-post draggable node graph (`Render` → `Caption` → one `Channel` node per target). Bridge from Studio: a `Render` node has a "Schedule this render" CTA that drops a draft on tomorrow's slot. |
| **🐙 Splash + Onboarding** | Animated red rotating logo splash (~2.5s), then 5-step wizard (Welcome / Persona / Providers / Channels / Ready). Replayable from the topbar 🐙 or ⌘K. |
| **👤 Personas** | Persona creator wizard (voice, vocabulary, brand bible). Multiple personas per install; the active one is selectable in Settings and surfaces as a chip in Quick. |
| **🔌 Connected accounts** | Settings → Connected accounts: credential blocks for X / Telegram / YouTube / Instagram with Connect / Manage / Disconnect / Test-post actions. |
| **🎨 Token system** | New `tokens.css` (surfaces, ink, stroke, brand red, cyan / violet / amber / green accents, node port colors, radii, shadows, motion). Single source of truth, themable via the Tweaks panel. |
| **🖼 Library uploads** | Drag-drop or button upload on the Images tab. New uploads get a brand-red border + "NEW" badge. |
| **✨ Prompt generator** | Modal with deterministic ingredient picker (subject / mood / motion / lens / palette / detail) + optional backend `/api/prompt/build` refinement, plus a curated prompt-template gallery in Quick. |

No new backend deps. No new DB columns. Backend version bump only (`/api/health` → `1.8.0`). The legacy `src/components/` (ImagePicker, GenerationForm, …) is kept on disk for rollback but no longer routed.

Upgrade via `scripts/upgrade-from-v1.7.2.ps1` (data-preserving, rebuilds the frontend).

---

> v1.7.2 base below.

# 🐙 Deepotus Video Gen — v1.7.2 "Anti-Cut + Rename Edition"

## 🆕 What's new in v1.7.2

| Feature | Description |
|---|---|
| **No more avatar cut-off** | The renderer no longer truncates a talking avatar. In a **post template** (e.g. `tpl_news_reel`) the output length is now driven by the avatar's *real* duration (`audio.master_track: "from_slot:avatar"` + a tunable `tail_pad_s`), not a fixed canvas duration. In the **timeline**, a clip's own audio (avatar voice) is now carried through the montage, delayed to its position, and never dropped. |
| **Per-clip length mode** | Each timeline clip has **Fixed** (trim/pad to a set length, the old behaviour) or **Source** (play the clip's full real duration — never trims the avatar). |
| **🎯 Fit to source** | One click reads a picked *existing* render's exact duration (ffprobe), locks the clip to it and sets the avatar gauge — so the animation clips can be calibrated to match. |
| **Tail-pad fine-tune** | Per-clip (timeline) and per-template (`audio.tail_pad_s`, news-reel default 0.8s) slider adds a safety pad so the last word/syllable always lands before any fade-out. |
| **Rename renders** | A **Render name** field in the Timeline tab labels the job at creation; the **Job Queue** has an inline rename on any render. Names show in the queue and the "existing" clip/audio pickers. |

`GET /api/jobs/{id}` now returns `duration_real_s` (ffprobe of the final video) and `title`; `PATCH /api/jobs/{id}` renames a render. New DB column `title` (auto-migrated, data-preserving). No new deps.

---

> v1.7.1 base below.

# 🐙 Deepotus Video Gen — v1.7.1 "News-to-Video + Timeline Edition"

## 🆕 What's new in v1.7.1

| Feature | Description |
|---|---|
| **🎬 Timeline editor** | Templates tab → **🎬 Timeline**: a simple Remotion-style montage. Order clips by drag, resize each clip's length (5s steps for Seedance), pick a transition between each (crossfade / cut / fade-black / glitch / slide / flash), **split** a clip in two, choose output **format** (9:16 / 1:1 / 16:9 / 4:5), optional **audio track** (upload/existing, volume), duration-vs-avatar gauge. |
| **Seedance length fit** | Seedance generates ≤10s natively; longer targets (5s increments, up to 60s) are extended via ffmpeg (loop / hold) to match a HeyGen avatar. |
| **Chain → finalise** | The timeline renders to a job (queue) reusable via the **"existing"** source in any post template (e.g. `tpl_news_reel`). |
| **Persistence** | The template draft, slot inputs, timeline structure & sources persist across edit↔render, tab switches and reloads (localStorage + inline render). |

Built-ins: `tpl_timeline`, `tpl_montage_film` (+ the v1.6 layout templates). New Python deps unchanged from v1.7 (`feedparser`, `trafilatura`); no new frontend deps. Upgrade via `scripts/upgrade-from-v1.6.ps1` (data-preserving).

---

> v1.7 base below.

# 🐙 Deepotus Video Gen — v1.7 "News-to-Video Edition"

**Cinematic UGC video generator** for the deepotus Solana memecoin X account. Multi-provider with composition, custom avatars, a visual node template editor, and a daily news-to-video pipeline.

Pipelines:
- **Seedance 2.0** (fal.ai) — image-to-video cinematic clips
- **HeyGen** — talking avatar videos from scripts (with **custom photo avatars**)
- **Composition** — combine both into one video (sequential transition OR split-screen)
- **🎨 Templates** — design reusable multi-clip 9:16 layouts in a visual editor, fill slots with Seedance/HeyGen/uploads/existing renders, render to a single MP4
- **📰 News** — scrape RSS/Atom feeds + article URLs, select headlines, auto-generate a deepotus-voice script + an animated news reel, compose into a post-ready 9:16 MP4

Stack: Python FastAPI · React + Vite + Tailwind + react-konva · SQLite · ffmpeg · fal.ai · HeyGen · ElevenLabs · feedparser · trafilatura.

---

## 🆕 What's new in v1.7

| Feature | Description |
|---|---|
| **📰 News tab** | Manage RSS/Atom feeds + single-article URLs (persisted, `assets/news/`). In-app **daily auto-refresh** while running + manual Refresh. Searchable, checkbox-selectable headline list. |
| **News → script** | Selected headlines → deepotus-voice spoken script (voice mode, FR/EN, length, optional angle) + suggested caption/hashtags. Deterministic + persona-driven. |
| **Brand scrub** | Ingested headlines are scrubbed of hype vocabulary (moon/lambo/1000x/LFG/hodl…, inflection-tolerant) so external text never breaks brand voice — independent of persona config. |
| **News reel (ffmpeg)** | Branded 1080×1920 animated reel: wordmark + per-headline cards (timed fades, drift, accent) + scrolling ticker. Reuses the v1.6 effects engine — no heavy deps. Remotion is an optional engine hook. |
| **One-click Build post** | News reel + HeyGen avatar reading the script, composed via the built-in `tpl_news_reel` template → final post MP4 + caption. |

New Python deps: `feedparser`, `trafilatura`. **After upgrading, run `pip install -r requirements.txt --upgrade` in the backend venv** (the upgrade script does this for you). No auto-posting — the app produces the MP4 + caption; you post to IG/X manually.

---

## 🆕 What's new in v1.6

| Feature | Description |
|---|---|
| **🎨 Templates tab** | A visual node editor (react-konva). Drag region presets onto a 1080×1920 canvas, snap to a 60px grid, set z-index, save reusable JSON templates. 6 built-ins ship pre-loaded. |
| **Layout templates** | `video_slot` / `image_slot` / `text_slot` / `text` / `brand_strip` regions with cover/contain/stretch/crop fit modes, per-region audio volume, fades, and `-14 LUFS` loudness. |
| **Slot-based render** | Render mode: fill each slot with a Seedance generation, a HeyGen avatar, an upload, or text → all slots resolve in parallel → ffmpeg composites a 1080×1920 H.264 MP4. |
| **Voice-mode propagation** | A template-level voice mode (Oracle/Alpha/Zen/Memer) flows into every generated sub-clip that didn't set its own. |
| **🖥️ Desktop launcher** | A Desktop shortcut runs `scripts/launch.ps1` — Step 1 walks you through setting API keys, Step 2 starts the services. |

The 6 built-in templates: classic vstack 50/50, alpha reel 60/30/10, oracle full + lower-third, three-act sequential, PIP corner avatar, hstack left/right dialogue. Built-ins are immutable; saving over one creates a fresh `tpl_user_*` copy. New endpoints are namespaced under `/api/layout-templates` (the existing `/api/templates` Seedance prompt-template endpoint is unchanged).

---

## 🆕 What's new in v1.5

| Feature | Description |
|---|---|
| **📸 Photo Avatar Upload** | Drag-drop a photo (PNG/JPG/WEBP, max 10MB) → HeyGen creates a custom talking avatar in 10-30s. Use it like any HeyGen avatar. Cost: ~$0.20 per avatar creation. |
| **🧠 Universal PromptBuilder** | One Builder that adapts to where you are: HeyGen → generates **scripts** from intent (with voice mode tone); Composition → generates **both sides** (Seedance prompt + HeyGen script) coherently per layout. |
| **Layout-aware coherence** | Composition Builder knows the difference: Sequential → avatar sets up + Seedance pays off; Split → avatar narrates + Seedance shows in parallel. |
| **HeyGen Builder voice modes** | All 4 brand voice modes (Oracle / Alpha / Zen / Memer) produce structurally distinct scripts (hook + body + sign-off). Vocabulary filter still applies. |

### How the Universal Builder works

In **HeyGen mode**: Click "🧠 Show builder" → type your intent → pick voice mode + max words → the builder generates a structured 3-part script (hook, body, sign-off) in your chosen tone. The script auto-fills the Script textarea + caption.

In **Composition mode**: Same UI, but the Builder calls `/api/prompt/build-composition` which produces BOTH a Seedance prompt AND a HeyGen script with explicit coherence:
- **Sequential layout**: Avatar's last words are a transition cue ("Watch.", "Now.", "Look."). Seedance prompt is the visual payoff.
- **Split layout**: Avatar narrates what Seedance is showing simultaneously.

### What's still in v1.5 from earlier versions

From v1.4: Provider tabs (Seedance/HeyGen/Composition), HeyGen integration, composition pipeline (sequential + split-vstack + split-hstack), avatar/voice dropdowns, queue provider badges.
From v1.3.1: Voice modes, vocabulary filter, persona-aware ElevenLabs.
From v1.3: Batch multi-seeds, compare grid, bulk batch delete.
From v1.2: Templates (20), Builder, first-last frame transitions, Job clone/delete.

---

## 🔑 Get your HeyGen API key

1. Go to https://app.heygen.com/api (Settings → API → New Key)
2. Copy the key (format: `sk_V2_hgu_...`)
3. ⚠️ The key is shown once — copy before closing the modal
4. Pricing: pay-as-you-go in credits. Avatar V ~6 credits/min video. Minimum top-up $5.

---

## ⬆️ Upgrade to v1.6

### Recommended — single upgrade from v1.4 (or v1.5) → v1.6

`upgrade-from-v1.4.ps1` is a **full self-contained** upgrade: it backs up your install to `<path>.bak.<timestamp>`, swaps in the v1.6 codebase, and **preserves your user data** — `backend\.env`, `assets\images\`, `assets\outputs\`, `backend\deepotus.db`, and `backend\app\personas\deepotus.json` (never overwritten). No DB migration step (the DB auto-migrates on startup; v1.6 adds no new columns). It works from a v1.4 or v1.5 install.

```powershell
cd C:\path\to\your\downloads
Expand-Archive deepotus-video-gen-v1.6.zip -DestinationPath . -Force
cd deepotus-video-gen
powershell -ExecutionPolicy Bypass -File .\scripts\upgrade-from-v1.4.ps1 -TargetPath "C:\path\to\your\install"
```

### Older installs (v1.0–v1.3)

Use the **migrate** script (backs up, fresh-installs v1.6, restores your data):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\migrate-from-v1.ps1 -InstallPath "C:\path\to\your\old\install"
```

### After upgrading — install the new frontend dependency

v1.6 adds **react-konva** (the visual editor). After any upgrade path, install frontend deps once:

```powershell
cd C:\path\to\your\install\frontend
npm install
```

### Set up the Desktop launcher (optional, recommended)

```powershell
cd C:\path\to\your\install
powershell -ExecutionPolicy Bypass -File .\scripts\create-desktop-shortcut.ps1
```

This adds a **"Deepotus Video Gen"** Desktop shortcut that runs `scripts\launch.ps1`: it walks you through API keys first (opens `backend\.env`), then starts the services. You can also launch manually with `.\scripts\run.ps1`.

Hard-reload the browser (Ctrl+F5). The header should show `v1.6` and a **🎨 Templates** tab.

---

## 🎬 How to use the new providers

### HeyGen mode (avatar video)
1. Click **🎤 HeyGen** in the provider tabs
2. Right panel loads your avatars + voices automatically
3. Pick an avatar (the dropdown shows name/gender)
4. Pick a voice (English + French voices available depending on your account)
5. Write a script (≤4900 chars)
6. Optional: pick a voice mode (Oracle/Alpha/Zen/Memer) — adjusts the tone of the auto-generated caption
7. Click **🎤 Generate Avatar Video**
8. The queue shows the job with a **🎤 HG** badge

### Composition mode (Seedance + HeyGen combined)
1. Click **⚡ Composition** in the provider tabs
2. Pick a **Seedance start image** (left panel) — this becomes the animation side
3. Pick a **Seedance template** (mid panel)
4. Pick an **avatar + voice** (right panel)
5. Write a **script** for the avatar
6. Choose a **layout**:
   - **Sequential**: avatar speaks → cyan flash → Seedance animation plays
   - **Split vstack**: Seedance animation on top, avatar reading on bottom (reaction style)
   - **Split hstack**: Seedance left, avatar right
7. For split modes: choose **audio source** (default: HeyGen avatar voice)
8. Click **🐙 Generate Composition**
9. Both clips generate in parallel (~30-90s), then ffmpeg composes them
10. The queue shows the composition with a **⚡ COMP** badge

### Estimated costs
- Seedance only: ~$0.30 per 5s clip
- HeyGen only: ~$0.40 per 5s avatar clip (varies with avatar engine)
- Composition: ~$0.70 (both costs combined; ffmpeg compositing is free, runs locally)

---

## 🚀 Fresh install (Windows)

This is the **bulletproof** sequence — works on Windows 10/11 with Python 3.13, fresh node, antivirus quirks.

### Prerequisites

- **Python 3.10+** — https://python.org/downloads/  
  ⚠️ Check "Add Python to PATH" during install. If `python` opens Microsoft Store, disable the stubs in `Settings > Apps > Advanced > App execution aliases`.
- **Node.js 20+** — https://nodejs.org
- **ffmpeg** — install steps below

### 1. Extract

```powershell
cd C:\Users\YourName\Projects
Expand-Archive deepotus-video-gen-v1.2.zip -DestinationPath . -Force
cd deepotus-video-gen
```

### 2. Install ffmpeg (one-time)

```powershell
New-Item -ItemType Directory -Force -Path C:\ffmpeg | Out-Null
Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile C:\ffmpeg\ffmpeg.zip
Expand-Archive C:\ffmpeg\ffmpeg.zip -DestinationPath C:\ffmpeg -Force
$ffmpegDir = (Get-ChildItem C:\ffmpeg -Directory | Where-Object { $_.Name -match "ffmpeg" } | Select-Object -First 1).FullName
[Environment]::SetEnvironmentVariable("PATH", "$ffmpegDir\bin;" + [Environment]::GetEnvironmentVariable("PATH","User"), "User")
```

**Close PowerShell, reopen.** Verify with `ffmpeg -version`.

### 3. Antivirus exclusion (only if you have Avast/Norton/McAfee)

In your AV settings, add this folder to "trusted folders" / "exclusions":
- `C:\Users\YourName\Projects\deepotus-video-gen`
- `C:\Users\YourName\AppData\Local\npm-cache`

This avoids `EFTYPE` / `EPERM` errors during npm install.

### 4. Install dependencies

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path .env)) { Copy-Item .env.example .env }

cd ..\frontend
npm install
cd ..

Write-Host "INSTALL COMPLETE" -ForegroundColor Green
```

### 5. Add your fal.ai key

```powershell
notepad backend\.env
```

Paste after `FAL_KEY=`. Save, close.

### 6. Launch

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1
```

Browser opens at `http://localhost:5173` after ~10s.

---

## ⬆️ Upgrade from v1.1

If you already have v1.1 installed somewhere, you can patch it without losing your data:

```powershell
# From the v1.2 folder (the new extract)
powershell -ExecutionPolicy Bypass -File .\scripts\upgrade-from-v1.1.ps1 -TargetPath "C:\path\to\v1.1\install"

# Then upgrade Python deps in the existing venv
cd C:\path\to\v1.1\install\backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt --upgrade
```

The DB auto-migrates on next start — your existing jobs are preserved with `seed: null` (you can't clone them with seed, but everything else works).

---

## 🎬 How to use the new features

### First-last frame transitions
1. Click **"Set End (transition)"** in the image picker (top of left panel)
2. Click any image — it becomes the END frame (violet border)
3. Switch back to **"Set Start"** and pick the start frame
4. Generate — the pipeline auto-routes to Seedance Lite (the variant that supports first-last frame)

### Prompt Builder (free-text → structured prompt)
1. In the Config panel, switch to **"🧠 Builder"** tab
2. Type your intent in plain English/French (e.g. "phone showing chart pumping with shocked face in dark room")
3. Toggle "Inject deepotus DNA" if you want the system to add mascot/deep-sea/brand cues automatically
4. Click **"✨ Generate prompt"** — the result fills the textarea
5. Edit the prompt directly in the textarea if you want
6. Hit **Generate Video** — the builder prompt is used instead of templates

The builder detects camera moves, lighting, and pacing from your text:
- "neon", "cyberpunk" → cyan/magenta neon lighting
- "shocked", "react", "fast" → fast pacing + handheld camera
- "underwater", "abyssal" → bioluminescent lighting
- "push in", "approach" → slow push-in camera
- + 20 more keyword patterns

### Clone for A/B variations
1. Open any completed job in the Queue panel
2. Click **"🔁 Clone"** at the bottom
3. The form pre-fills with the same image, seed, style, prompt
4. Tweak anything you want (prompt, lighting, duration…)
5. Generate — same seed = comparable outputs

### Delete jobs
1. Open a job, click **"🗑"** at the bottom
2. Confirm in the inline dialog
3. DB record + video + audio + caption files are removed

---

## 🔑 Where to get API keys

### fal.ai (required) — pay-per-use
1. Sign up: https://fal.ai
2. Dashboard → Keys → Create new key
3. Pricing: Pro Seedance ~$0.40/5s 1080p, Lite Seedance ~$0.18/5s — **Lite is cheaper, use it for transitions**
4. Add credits via card

### ElevenLabs (optional) — voiceover FR/EN
1. Sign up: https://elevenlabs.io
2. Free tier: ~10k chars/month
3. Settings → API Keys → Copy
4. Default voices in `.env`:
   - EN: `21m00Tcm4TlvDq8ikWAM` (Rachel)
   - FR: `ThT5KcBeYPX3keUQqHPh` (Dorothy)

---

## 📊 Pricing estimate (10 videos/day, mix of Pro and Lite)

| Service | Avg/video | Per day | Per month |
|---|---|---|---|
| fal.ai Seedance (mix Pro/Lite) | ~$0.30 | ~$3.00 | ~$90 |
| ElevenLabs (~30 chars VO) | ~$0.01 | ~$0.10 | ~$3 |
| **Total** | **~$0.31** | **~$3.10** | **~$93** |

(Verify current pricing on fal.ai/ElevenLabs.)

---

## 🔧 Troubleshooting

**Backend "No module named greenlet"**  
→ Already fixed in v1.2 requirements. If migrating from v1.1: `pip install -r requirements.txt --upgrade`.

**`pip install` fails with C++ compiler errors**  
→ Python 3.13 + old version pins. v1.2 uses `>=` ranges that pull prebuilt wheels. Make sure you're using the v1.2 `requirements.txt`.

**npm install fails with `EFTYPE` or `EPERM`**  
→ Antivirus (Avast/Defender) is blocking. Add the project folder to exclusions in your AV settings, then `npm cache clean --force` and retry.

**`python` opens Microsoft Store**  
→ `Settings > Apps > Advanced > App execution aliases` → disable `python.exe` and `python3.exe`. Or use `py` everywhere.

**`ffmpeg` not found**  
→ Re-do step 2 of the install. After install, **close and reopen PowerShell** to refresh PATH.

**fal.ai job fails with "Invalid endpoint"**  
→ Check your fal.ai dashboard — confirm the model is available in your region/account. Try without an end image first (uses Pro endpoint, more universally available).

**End image not working**  
→ Seedance Lite requires both images to be similar dimensions/aspect. Use images of the same aspect ratio for best results.

**DB auto-migration fails**  
→ Manually delete `backend/deepotus.db` (you'll lose old jobs, but it's a fresh start).

---

## 🛠 Development notes

- **Adding more templates**: edit `backend/app/personas/deepotus.json`, restart backend. JSON schema mirrors `PromptTemplate` in `schemas.py`.
- **Adding more personas** (e.g. for Rippled, Werner Wilfre): copy `deepotus.json` to `your_persona.json`, edit, change `Pipeline(persona_id="...")` in `routes.py:20`.
- **Builder keyword detection**: extend dictionaries in `prompt_engine.py` (`CAMERA_KEYWORDS`, `LIGHTING_KEYWORDS`, `PACING_KEYWORDS`).
- **DNA elements**: customize in `prompt_engine.py` `DEEPOTUS_DNA` dict.

---

🐙 **From the deep, for the deep.**
