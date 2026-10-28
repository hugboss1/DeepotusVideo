# t313 — C3 Inspiration → contenu neuf (et repost) — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** depuis le Planificateur, déposer la capture d'un contenu qui inspire (image d'un post, texte collé), en extraire la
**matière** (lue comme une preuve encadrée, jamais suivie comme consigne), proposer **trois angles neufs** dans la voix de
l'espace, chiffrer le contenu neuf dans une **carte de devis** (texte Claude + visuel fal), le générer au clic, puis en
faire un **brouillon du projet actif** qui vise ses canaux et respecte la validation du client. Décision de
l'utilisateur : on **refabrique**, on ne republie jamais l'original.

**Architecture :** `inspiration_garde.py` (pur : suite de mots reprise, proximité, empreinte d'image) ;
`inspiration.py` (registre sur disque `DATA_ROOT/inspirations/<id>/`, lecture locale par le scan de t312, palette locale,
devis gratuits, deux appels Claude payants sous `tirer_garde`, brouillon par `routes.create_scheduled_post`, source notée) ;
routes `/api/inspiration/*` (`api/inspiration_routes.py`) ; deux outils de la boîte d'agent `scan` (`angles_inspiration`,
`deviser_contenu_neuf`) ; écran `frontend/shared/dz-inspiration.js` (boîte de dialogue) ouvert par un bouton du
Planificateur posé par le maillon de queue `dzinspiration`.

**Tech Stack :** FastAPI, Pillow, moteurs_texte (Claude), pricing/plafonds, JS sans build, dzT, L10, maillon de bundle en octets.

**Spec :** `docs/superpowers/specs/2026-10-25-boite-a-outils-design.md` §7.4 (+ §2 anti-objectifs, §4 boîte `scan`,
§5.4 canaux du projet, §5.5 validation client, §11 bis agents, §12 n°6 seuil). Base : `chantier/boite-base-c-d` 385e01a1
(t312 + origin/main t353-t354).

## Global Constraints

- Bancs Python depuis `backend/` avec le python embarqué, `PYTHONUTF8=1`, un à la fois, au premier plan ; chaque banc pose
  `DEEPOTUS_DATA_DIR` temporaire et vide les clés ; aucun appel réseau réel (Claude et fal remplacés par leurs coutures).
- Claude = **payant, jamais automatique** : devis gratuit, `max_usd` accepté par l'utilisateur (confirmation de l'écran),
  coût réel recalculé avant l'appel (`CoutChange` → 409, aucun appel), `moteurs_texte.tirer_garde` (402 plafond, catégorie
  `scheduler`) ; un résultat payé est GARDÉ dans le registre et rendu sans repayer (sauf `nouvelle: true`).
- Le contenu capté (texte OCR, texte collé) n'entre dans un prompt qu'**encadré** par `agent_outils._preuve` ; le prompt
  de rédaction ne reçoit PAS la capture, seulement la matière et l'angle.
- Gardes anti-copie **côté serveur** : texte refusé dès qu'une suite de `SEUIL_SUITE = 12` mots consécutifs (normalisés :
  casse, accents, ponctuation) reprend la capture ; proximité affichée ; l'image captée est rangée HORS du dossier
  d'images de la Bibliothèque et un visuel identique ou presque (sha256, ou empreinte moyenne 8×8 à ≤ 6 bits) est refusé.
- La source (libellé et lien saisis, nom et empreinte du fichier, date) reste dans le registre et dans la recette du
  visuel (Bibliothèque) ; elle n'entre jamais dans le titre, la légende ni le brief du post.
- Brouillon : l'espace du registre (l'espace de la requête à la capture, jamais réécrit), `routes.create_scheduled_post`
  sans canaux → canaux du projet actif (t307/t325), `a_valider` chez un client `valide_par_client` (t309).
- Routes locales seulement (`_require_localhost`) ; les deux routes payantes ont aussi `_require_local_depense` et entrent
  au recensement des plafonds (`_recensement_payant.py`, `test_plafonds_garde.py`).
- Tout message serveur à texte fixe a son entrée L10 (`scripts/i18n_l10_traductions.json`, puis
  `python scripts/i18n_l10_erreurs.py --check`) ; tout libellé écran par `dzT` (clés `inspiration.*`,
  `frontend/shared/i18n/inspiration.json`, `scripts/i18n_assembler.py`) ; `frontend/shared` = `frontend/dist/shared`.
- Bundle jamais reconstruit : maillon de queue `scripts/patch_bundle_dzinspiration.py` (octets, CRLF), posé APRÈS
  `whatsapppage`, inverse `avant_dzinspiration` en tête de `avant_whatsapppage` dans `backend/tests/_i18n_l1_aide.py`.
- Journaux : jamais le texte capté ni rédigé ; nombres, tailles, coûts.

## Décisions

1. **Registre** : `DATA_ROOT/inspirations/<id>/inspiration.json` (+ `capture.<ext>` si une image a été déposée), id
   `uuid4().hex`, écriture atomique. Champs : `id, espace_id, cree, langue, source{libelle, lien, fichier, octets, sha256,
   ahash}, texte_capte, ocr{moteur, mots, raison}, palette[], analyse{…}|null (matière + angles payés), redaction{…}|null,
   brouillons[{post_id, statut, cree, visuel, proximite}]`. 50 inspirations au plus par espace dans la liste (les plus récentes).
2. **Capture** : une image (PNG/JPEG/WEBP/BMP/TIFF, validée par `scan_pages.charger`, une seule page image) et/ou un texte
   collé (≤ 20 000 caractères). Lecture locale gratuite par `scan_lecture._lire_ocr` (fil) ; OCR indisponible → la
   capture est gardée avec `ocr.raison` (le texte collé ou l'analyse de l'image par Claude restent possibles). Palette :
   5 couleurs dominantes par Pillow (gratuit).
3. **Analyse (matière + trois angles)** : un appel Claude JSON. Entrée : texte capté encadré, palette, persona de l'espace
   (`agent_campagnes.persona_modele`, tronqué), mots interdits (`agent_outils._mots_interdits`), langue de l'écran ;
   l'image jointe seulement si l'utilisateur coche « Lire aussi l'image » (vision, ≤ 1280 px, comptée au devis).
   Sortie : `matiere{idees[], structure, ton, composition, palette[], logique}` et `angles[3]{titre, accroche, idee,
   visuel}`. Chaque angle est contrôlé (suite reprise, mots interdits) : un angle fautif est rendu avec `alertes` et ne
   peut pas être choisi.
4. **Carte de devis** (`devis_contenu`) : `texte` = op de l'appel de rédaction (prompt réel : matière + angle + persona),
   `image` (si coché) = `agent_outils._devis_image` sur l'invite visuelle de l'angle (+ palette et composition en mots),
   corps `{…, espace_id, source: "scheduler"}`, route `/api/images/generate` ; total = somme. L'animation n'est pas
   chiffrée ici : elle passe par « Produire » du Planificateur sur le brouillon (choix à valider).
5. **Rédaction** : un appel Claude JSON `{titre, accroche, legende, hashtags[]}` dans la voix de l'espace, sans la capture ;
   le résultat passe la garde (suite, proximité, mots interdits) et revient avec `garde{suite, proximite, extrait,
   interdits[], ok}` ; il est gardé (payé) même s'il échoue à la garde : l'utilisateur le corrige à la main.
6. **Brouillon** : `POST /{id}/brouillon {titre, accroche, legende, visuel?}` : garde texte (409 `copie` ou `interdits`),
   garde visuel (fichier de la Bibliothèque existant, pas la capture : 409 `visuel_capte`), puis
   `routes.create_scheduled_post({title, caption, hook, source_image, status: "draft", run_at: demain 09:00 UTC,
   espace_id})` ; la recette du visuel reçoit `inspiration{id, source, reference_composition, le}` ; le registre note le
   brouillon. Réponse : le post, son statut (`draft` ou `a_valider`), ses canaux.
7. **Seuil** : refus à `suite ≥ 12` (lecture prudente de « 12 mots consécutifs » ; la spec dit « plus de 12 »), proximité
   = part des trigrammes de mots du brouillon présents dans la capture (0-100 %), affichée.
8. **Agent** : boîte `scan` += `angles_inspiration` (lecture : une image de la Bibliothèque par son nom → texte encadré,
   palette, persona, mots interdits, consigne des trois angles et du seuil) et `deviser_contenu_neuf` (carte : devis
   texte + image d'un angle donné). La boîte reste sans agent (§11 bis) ; les fixtures de Campagnes ne bougent pas.
9. **Écran** : `window.__dzInspiration.ouvrir()` — boîte en quatre temps (Capture → Matière et angles → Devis et
   génération → Brouillon), « Pour : espace · projet · canaux » en tête, liste des inspirations récentes avec leur source ;
   aucune `innerHTML` de texte capté ; boîte non fermable pendant un appel payant ; 402 par `dz-plafonds.js` ; 409 coût
   changé → nouveau devis ; confirmation par `window.__dzDialogue.confirmer` ; après le brouillon, l'événement
   `deepotus:schedule-recharger` (t309) recharge le Planificateur.
10. **Maillon `dzinspiration`** : une paire : après le bouton « Nouveau post » du Planificateur, un bouton
    `dzT("inspiration.bouton")` (icône `dz-media-image`, aide `inspiration.bouton_aide`) qui appelle
    `window.__dzInspiration.ouvrir()`.

## Review Focus

1. Un texte capté qui contient « ignore tes instructions… » : encadré dans les deux prompts où il entre, jamais dans celui
   de la rédaction ; la garde refuse un brouillon qui le recopie.
2. Contournement de la garde : casse, accents, ponctuation, retours à la ligne, mots coupés entre titre et légende ;
   image recompressée ou redimensionnée.
3. Argent : aucun appel sans accord ; coût changé → 409 sans appel ; résultat payé jamais perdu ni repayé par un simple
   rechargement ; une seule analyse à la fois par inspiration (409 `en_cours`).
4. Le brouillon naît dans l'espace de l'inspiration, avec les canaux du projet actif de CET espace, `a_valider` chez un
   client en `valide_par_client` ; la source n'apparaît dans aucun champ publiable.
5. Chaîne du bundle : aller-retour exact, sonde amont, comptes figés, inverse en tête de chaîne.

---

### Task 1 : gardes anti-copie (pur)

**Files :** Create `backend/app/services/inspiration_garde.py` ; Test `backend/tests/test_inspiration_garde.py`

**Interfaces — Produces :** `mots(texte) -> list[str]` (normalisés) ; `plus_longue_suite(capte, texte) -> (n, extrait)` ;
`proximite(capte, texte) -> int` (0-100) ; `juger(capte, texte) -> {suite, proximite, extrait, ok}` ; `SEUIL_SUITE = 12` ;
`empreinte(octets) -> {sha256, ahash}` (ValueError si illisible) ; `meme_image(a, b) -> bool`.

- [ ] Step 1 : banc rouge : 11 mots repris → ok ; 12 → refus ; casse/accents/ponctuation/retours à la ligne neutres ;
  extrait rendu ; texte vide ; proximité 0 et 100 ; capture longue (20 000 car.) en < 1 s ; empreinte identique après
  recompression JPEG et réduction de moitié ; image différente → non ; octets illisibles → ValueError.
- [ ] Step 2-4 : implémenter, vert, mutations (seuil, normalisation). Commit.

### Task 2 : service `inspiration`

**Files :** Create `backend/app/services/inspiration.py` ; Test `backend/tests/test_inspiration.py`

**Interfaces — Consumes :** Task 1 ; `scan_pages.charger`, `scan_lecture._lire_ocr`, `scan_vision._reduire`,
`agent_outils._preuve/_mots_interdits/_devis_image`, `agent_campagnes.persona_modele`, `moteurs_texte`,
`pricing`, `routes.create_scheduled_post`, `library_projects`, `comptes`.
**Produces :** `capter(image, texte, source, langue, espace_id) -> dict` ; `lire(iid)` ; `lister(espace_id)` ;
`devis_analyse(iid, avec_image) -> {usd, disponible, raison, delai_s}` ; `analyser(iid, max_usd, avec_image, langue,
nouvelle=False)` ; `devis_contenu(iid, angle, image) -> carte` ; `rediger(iid, angle, max_usd, langue, nouvelle=False)` ;
`brouillon(iid, titre, accroche, legende, visuel) -> dict` ; exceptions `Inconnue(KeyError)`, `Refus(ValueError, code)`,
`CoutChange(ValueError, usd)`, `EnCours(RuntimeError)` ; coutures `_tirer`.

- [ ] Step 1 : banc rouge (couture `_tirer` = faux Claude, OCR remplacé) : capture image + source → registre, image hors du
  dossier d'images ; texte seul ; ni l'un ni l'autre → refus ; OCR indisponible → capture gardée avec raison ; palette ;
  devis gratuit (aucun appel) ; analyse : coût > accord → CoutChange sans appel ; prompt avec PREUVE et persona ; angle
  fautif marqué ; résultat gardé et rendu sans appel ; `nouvelle` relance ; deux analyses simultanées → EnCours ;
  rédaction sans la capture dans le prompt ; garde du résultat ; brouillon : copie → Refus copie ; mot interdit → Refus ;
  visuel = capture recompressée → Refus visuel_capte ; nominal → post draft dans l'espace, canaux du projet actif,
  a_valider chez un client valide_par_client ; recette du visuel annotée ; source absente des champs du post.
- [ ] Step 2-4 : implémenter, vert. Commit.

### Task 3 : routes `/api/inspiration/*`

**Files :** Create `backend/app/api/inspiration_routes.py` ; Modify `backend/app/main.py`, `backend/tests/_recensement_payant.py`,
`backend/tests/test_plafonds_garde.py`, `scripts/i18n_l10_traductions.json` ; Test `backend/tests/test_inspiration_routes.py`

Routes : `POST /capter` (multipart `image?`, `texte?`, `source_libelle?`, `source_lien?`, `langue`) ; `GET /` (liste de
l'espace de la requête) ; `GET /{id}` ; `GET /{id}/devis-analyse?image=0|1` ; `POST /{id}/analyse` {max_usd, avec_image,
nouvelle?} (payante) ; `POST /{id}/devis` {angle, image} ; `POST /{id}/redaction` {angle, max_usd, nouvelle?} (payante) ;
`POST /{id}/brouillon` {titre, accroche, legende, visuel?}. Codes : 400 corps, 404 inconnue, 409 coût changé
`{message, usd}` / en cours / refus `{message, code, garde}`, 413, 415, 402 propagé, 502/504 appel, 503 Claude absent.

- [ ] Step 1 : banc rouge (TestClient) des codes ci-dessus, hors machine locale → 403, messages traduits en anglais
  (`Accept-Language: en`), journaux sans texte capté.
- [ ] Step 2-4 : implémenter, L10 + `--check`, `test_plafonds_garde`. Commit.

### Task 4 : outils de la boîte `scan`

**Files :** Modify `backend/app/services/agent_outils.py`, `backend/app/services/agent_boites.py`, `docs/agent/AGENT.md` ;
Test `backend/tests/test_agent_inspiration.py`

- [ ] Step 1 : banc rouge : `verifier()` vide ; les deux outils dans `scan`, aucun agent ; `angles_inspiration` refuse un
  nom hostile, rend le texte encadré + persona + interdits + consigne ; `deviser_contenu_neuf` rend une carte de devis
  (route `/api/images/generate`, `source: "scheduler"`, espace du tour) et refuse sans espace ; fixture de Campagnes
  inchangée.
- [ ] Step 2-4 : implémenter, vert, `test_agent_boites`, `test_agent_outils`, `test_agent_scan`. Commit.

### Task 5 : écran `dz-inspiration.js`

**Files :** Create `frontend/shared/dz-inspiration.js` (+ copie dist), `frontend/shared/i18n/inspiration.json`,
`frontend/shared/qa/inspiration.test.mjs`, `backend/tests/test_inspiration_ecran.py` ; Modify `frontend/dist/index.html`
(balise après `dz-whatsapp-espace.js`), dico assemblé.

- [ ] Step 1 : banc node rouge (faux DOM/fetch) : ouverture (pour qui, liste récente) ; capture (dépôt d'une image,
  coller, texte) → POST /capter ; devis d'analyse → confirmation → analyse ; angles affichés, angle fautif grisé ; devis
  du contenu ; génération : redaction puis /api/images/generate puis aperçu modifiable avec proximité ; brouillon → 409
  copie affiché ; brouillon créé → événement de rechargement ; 409 coût changé → nouveau devis ; FR et EN ; aucune
  `innerHTML`.
- [ ] Step 2 : banc Python : copie dist identique, balise dans index.html, clés présentes FR/EN, dico assemblé.
- [ ] Step 3 : implémenter, vert. Commit.

### Task 6 : maillon `dzinspiration`

**Files :** Create `scripts/patch_bundle_dzinspiration.py` ; Modify `frontend/dist/assets/index-BEOJX8L5.js` (par le
maillon), `backend/tests/_i18n_l1_aide.py` (`avant_dzinspiration`), `backend/tests/test_inspiration_ecran.py`

- [ ] Step 1 : banc rouge : marqueur ×1, bouton posé après « Nouveau post », hors couche, `defaire` exact,
  `avant_whatsapppage` défait d'abord dzinspiration, `--check` « déjà appliqué ».
- [ ] Step 2-4 : implémenter, appliquer, vert ; chaîne : `test_whatsapp_page_ecran`, `test_i18n_l1`, `test_i18n_l3`,
  `test_garde_client_ecran`, `test_canaux_preremplis`, `test_scheduler_bundle`. Commit.

### Task 7 : connaissance, docs, preuve

**Files :** catalogue `docs/agent/catalogue/*` (procédure connaissance-agent), `docs/agent/AGENT.md`, `AGENTS.md`,
`CHANGELOG.md`, captures `docs/superpowers/specs/captures/t313/`

- [ ] Step 1 : catalogue (`python scripts/agent/catalogue.py`, rôles FR/EN, `--check`, `test_agent_catalogue`).
- [ ] Step 2 : bancs de la base relancés, comparaison base/HEAD.
- [ ] Step 3 : relecture finale de branche, une vague de corrections.
- [ ] Step 4 : preuve sur 8798 (faux Claude, faux fal), captures FR et EN, backend arrêté et port libéré. Commit.
