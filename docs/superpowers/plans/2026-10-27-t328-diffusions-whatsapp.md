# t328 — Diffusions WhatsApp depuis le Planificateur : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** un post du Planificateur dont la cible est un compte WhatsApp part en **diffusion** Kapso (API Broadcasts) vers les contacts de l'espace qui ont donné un accord saisi, avec modèle approuvé obligatoire, devis et plafonds avant l'envoi, validation client respectée, et statut par destinataire relu ensuite.

**Architecture :** un service neuf `whatsapp_diffusions.py` porte la configuration de diffusion d'un post (fichier JSON d'espace), l'audience (variante lot de `whatsapp.controler`), le devis (quantité ajoutée à `_ligne_whatsapp`), le lancement (création du broadcast, destinataires par 1 000, `plafonds.verifier` puis `send` en un seul essai, drapeau `incertain`) et la relecture (statuts, `suppressed` → désinscription, coût réel). Le Planificateur l'appelle par un adaptateur `publishers.register("whatsapp", …)` une fois le verrou `NON_PUBLIABLES` levé. L'écran : un script partagé `dz-diffusion-whatsapp.js` monté par un maillon de queue `dzdiffusion` dans l'inspecteur du post.

**Tech Stack :** FastAPI, SQLAlchemy (ScheduledPost inchangé), httpx via le hook `kapso._requete`, bundle SPA prébâti + maillon de queue, JS sans build, i18n dzT, messages L10.

**Spec :** pas de section dédiée (t328 est une option née du relevé gokapso du 26/10). Autorités : tâche t328 du suivi, spec boîte à outils §6 (Kapso), relevé `docs/superpowers/specs/2026-10-27-kapso-broadcasts-releve.md`, relevé du code `.superpowers/sdd/t328-releve.md`. Décisions prises ici = provisoires, notées « Décision ».

## Global Constraints

- Aucun appel réseau réel dans les bancs ni la preuve : tout passe par `kapso._requete` remplacé.
- Jamais de clé, jeton, URL de média, texte de message, ni identité (numéro) de destinataire dans un log, une réponse d'erreur ou une URL.
- Bancs Python lancés depuis `backend/` avec le python embarqué, PYTHONUTF8=1, au premier plan, un à la fois, aucune boucle en arrière-plan.
- Bundle modifié UNIQUEMENT par le maillon `scripts/patch_bundle_dzdiffusion.py`, posé après `whatsapppage`, `version` reste le dernier ; inverse `avant_dzdiffusion` dans `backend/tests/_i18n_l1_aide.py`.
- Scripts `frontend/shared/*.js` : copie octet pour octet dans `frontend/dist/shared/`.
- Tout libellé écran via `dzT` FR/EN ; tout message d'erreur serveur à texte fixe a son entrée L10.
- Lots de destinataires : **1 000 maximum** par appel `POST /broadcasts/{id}/recipients`.
- `send` : un seul essai (`reessai_ok=False`), jamais rejoué sans relire `GET /broadcasts/{id}`.

## Décisions

1. **Audience** = identités `tel:` de l'état du numéro relié dont l'accord est SAISI (source ≠ `entrant`), hors `stops`, hors `desinscrits_marketing` (pour un modèle marketing). Les `bsuid:` sont écartées et comptées (« non confirmé » chez Kapso). Option : une liste explicite d'identités, filtrée par les mêmes règles. Le consentement client `whatsapp:<pid>` en cours est exigé (refus `consentement`).
2. **Paramètres du modèle** : un seul jeu pour tous les destinataires (pas de personnalisation par contact en v1). Composants construits comme `whatsapp_echanges._corps`, au format Meta.
3. **Devis** : `_ligne_whatsapp` accepte `n` (défaut 1) ; une ligne par marché (indicatif via `whatsapp_echanges._marche`). Réservation unique par `plafonds.verifier(op, "whatsapp", ref=<broadcast_id>, espace_id=eid)` juste avant `send`. Après relecture finale : coût réel = Σ marché (destinataires `sent` × prix) → `plafonds.noter_reel_lignes` (les `suppressed` et `failed` ne sont pas facturés).
4. **Plafond messages** : `_total_mois(espace) + n > plafond_mois` → `WhatsappRefus(code="plafond")` avant toute création chez Kapso.
5. **Stockage** : `espaces/<eid>/whatsapp_diffusions.json` = `{post_id: {compte, modele:{nom, langue, meta_id, categorie}, parametres, identites|null, broadcast_id, statut, incertain, lignes, compteurs:{total, pending, sent, failed, suppressed, delivered, read}, ecartes:{bsuid, stop, accord, marketing}, maj}}`. Écrit sous `whatsapp._verrou_compte(cid)`.
6. **Statut du post** : l'adaptateur rend `PublishResult(ok=True, remote_id=broadcast_id)` dès que `send` a répondu 202 ; la relecture est faite à la demande (route) et par `tick` pour les diffusions non terminées (au plus une relecture par diffusion par minute).
7. **Incertain** : un 5xx, un statut 0 ou une erreur réseau sur `send` → `incertain=True`, réservation gardée, adaptateur `ok=False` avec un détail neutre ; nouveau lancement refusé `code="incertain"` (409) tant que la relecture n'a pas tranché ou que l'utilisateur n'a pas confirmé (`confirme_incertain`). Si la relecture montre `sending|completed` : `incertain=False`, post `posted`.
8. **Validation client** : rien de neuf côté serveur : `fire_post` applique déjà `_controler_client`. La demande de validation au client par WhatsApp (t311) fonctionne telle quelle sur ce post.

## Review Focus

1. Un 5xx sur `send` puis un nouveau « publier » : jamais de second `send` sans relecture (double diffusion facturée).
2. Une audience vide (aucun accord saisi) : refus clair avant toute création chez Kapso, rien de réservé.
3. 2 500 destinataires : 3 appels recipients (1000/1000/500), `errors` lus même en 201, `duplicates` comptés.
4. Contact devenu `suppressed` : il passe dans `desinscrits_marketing` et n'est plus dans l'audience suivante.
5. Post modifié après validation client : validation effacée (existant) et la diffusion ne part pas.

---

### Task 1 : client Kapso Broadcasts

**Files :** Modify `backend/app/services/kapso.py` ; Test `backend/tests/test_kapso_broadcasts.py`

**Interfaces — Produces :**
- `async def creer_broadcast(nom: str, phone_number_id: str, template_id: str) -> dict` → `{"id", "statut"}` (POST `PLATFORM/whatsapp/broadcasts`, corps `{"whatsapp_broadcast": {name, phone_number_id, whatsapp_template_id}}`).
- `async def ajouter_destinataires(broadcast_id: str, destinataires: list[dict]) -> dict` → `{"ajoutes", "doublons", "erreurs": [str]}` ; chaque destinataire `{"phone_number": "+<chiffres>", "components": [...]}` ; `ValueError` si plus de 1 000.
- `async def envoyer_broadcast(broadcast_id: str) -> dict` → `{"statut"}` (POST `/send`, `reessai_ok=False`).
- `async def broadcast(broadcast_id: str) -> dict` → `{"id", "statut", "compteurs"?: dict}` (GET).
- `async def destinataires_broadcast(broadcast_id: str, *, page: int = 1, par_page: int = 100) -> dict` → `{"lignes": [{"phone_number", "statut", "code_erreur", "livre", "lu"}], "pages": int}`.
- `async def arreter_broadcast(broadcast_id: str) -> dict` (PATCH `{"whatsapp_broadcast": {"status": "stopped"}}`).

- [ ] Step 1 : banc (faux `_requete` qui range méthode, chemin, corps) : création → chemin et enveloppe exacts ; 1 001 destinataires → ValueError sans appel ; 201 avec `errors` non vide → erreurs rendues ; `send` en 500 → `KapsoErreur` statut 500 après **un seul** appel ; 429 sur `send` → un seul appel aussi ; pagination `meta.total_pages` lue ; `phone_number` sans `+` en sortie toléré ; `error_details.code` → `code_erreur` ; aucune clé dans les messages d'erreur.
- [ ] Step 2 : lancer, constater l'échec.
- [ ] Step 3 : implémenter avec `_appel`, `_data`, `_lire_erreur`.
- [ ] Step 4 : banc vert + `test_kapso.py` vert.
- [ ] Step 5 : commit.

### Task 2 : audience, devis par quantité, plafond messages

**Files :** Modify `backend/app/services/whatsapp.py`, `backend/app/services/pricing.py`, `backend/app/services/whatsapp_echanges.py` (id Meta dans `_modele_plat`) ; Test `backend/tests/test_whatsapp_audience.py`

**Interfaces — Produces :**
- `def audience_diffusion(cid: str, *, categorie: str, identites: list[str] | None = None) -> dict` → `{"retenus": [identite], "ecartes": {"bsuid": n, "stop": n, "accord": n, "marketing": n}}` ; lit le fichier et la fiche UNE fois ; lève `WhatsappRefus(code="consentement")` si le consentement client manque, `WhatsappRefus(code="accord")` si `retenus` est vide.
- `def verifier_plafond_mois(cid: str, n: int) -> None` → `WhatsappRefus(code="plafond")` si dépassement.
- `_ligne_whatsapp` : clé `n` (entier ≥ 1, défaut 1) multiplie le coût ; le libellé de ligne dit la quantité.
- `_modele_plat` : ajoute `meta_id` (id du brut Meta).

- [ ] Step 1 : banc : accord `entrant` exclu pour TOUTE catégorie (revue finale M8 : Décision 1 l'emporte, un entrant n'est pas un accord de diffusion) ; stop exclu ; désinscrit exclu en marketing seulement ; bsuid écarté et compté ; liste explicite filtrée ; consentement client absent → refus ; audience vide → refus `accord` ; plafond 1000 avec 990 déjà + 20 → refus ; devis `n=3` = 3 × prix ; marché inconnu → ValueError existante ; `meta_id` présent dans `modeles(cid)`.
- [ ] Step 2-4 : échec, implémentation, vert (+ `test_whatsapp_prix.py`, `test_whatsapp_kapso2.py`).
- [ ] Step 5 : commit.

### Task 3 : service `whatsapp_diffusions`

**Files :** Create `backend/app/services/whatsapp_diffusions.py` ; Test `backend/tests/test_whatsapp_diffusions.py` ; Modify `backend/tests/test_plafonds_garde.py` (garde A2 : `plafonds.verifier(` avant `kapso.envoyer_broadcast(` dans `lancer`)

**Interfaces — Consumes :** Tasks 1-2. **Produces :**
- `def lire(post_id: int, espace_id: str) -> dict | None`
- `async def configurer(post_id: int, cid: str, *, modele: dict, parametres: dict | list, identites: list[str] | None) -> dict` → vérifie modèle approuvé (nom+langue) et paramètres (`_verifier_parametres`), range la config, rend `{config, audience: {n, ecartes}, devis: {usd, lignes}}` (devis par `pricing.estimate`, sans réservation). Refus si une diffusion de ce post est déjà lancée.
- `async def lancer(post_id: int, *, confirme_incertain: bool = False) -> dict` → ordre : config présente → `espace_actif` → si `incertain` et pas confirmé : relire, puis refus `code="incertain"` si toujours incertain → audience → plafond mois → modèle encore approuvé → `creer_broadcast` (nom `dz-<post_id>-<horodatage>`) → destinataires par 1 000 → `plafonds.verifier` (ref = broadcast_id) → `envoyer_broadcast` → statut. 4xx sur send : `noter_reel_lignes(lignes, 0.0)`, statut `echec`. 5xx/0 : `incertain=True`. Rend `{broadcast_id, statut, n, incertain}`.
- `async def relire(post_id: int, espace_id: str) -> dict` → GET broadcast + toutes les pages de destinataires ; compteurs ; `suppressed` et code Meta 131050 → `whatsapp.noter_desinscription` ; statut terminal → `noter_reel_lignes(lignes, coût réel)` une seule fois ; `incertain=False` si Kapso montre `sending|completed|stopped|failed`.
- `def a_relire(maintenant) -> list[(post_id, espace_id)]` → diffusions non terminées dont `maj` a plus de 60 s.

- [ ] Step 1 : banc complet sur faux Kapso : parcours nominal 2 500 destinataires (3 lots, devis réservé une fois, rattaché au broadcast) ; send 500 → incertain, réservation gardée, second `lancer` sans confirmation → relecture puis refus 409 `incertain` si Kapso dit `draft`, accepté si confirmé ; send 422 → réservation remise à 0 ; audience vide → aucun appel Kapso ; plafond mois → aucun appel ; relire avec `suppressed` → désinscription posée, coût réel = sent × prix ; journal sans numéro ni texte (grep du fichier de log temporaire) ; `configurer` après lancement → refus.
- [ ] Step 2-4 : échec, implémentation, vert + `test_plafonds_garde.py`.
- [ ] Step 5 : entrées L10 des nouveaux messages + `python scripts/i18n_l10_erreurs.py` puis `--check`, `test_i18n_l10.py`.
- [ ] Step 6 : commit.

### Task 4 : Planificateur et routes

**Files :** Modify `backend/app/services/comptes.py` (lever `NON_PUBLIABLES` pour whatsapp ; garder les autres gardes), `backend/app/services/marketing.py` (`meta["post_id"]` ; relecture des diffusions dans `tick`), un adaptateur `publishers.register("whatsapp", disponible, publier)` dans `whatsapp_diffusions.py` (enregistré là où les autres le sont), `backend/app/api/routes.py`, `backend/tests/test_plafonds_garde.py` (`PAYANTES`) ; Tests `backend/tests/test_scheduler_whatsapp.py`, mise à jour `test_whatsapp_comptes.py`

**Routes :**
- `GET /api/schedule/{post_id}/diffusion` → `{config, audience, devis, etat}` (relit chez Kapso si lancée, `?relire=1`).
- `PUT /api/schedule/{post_id}/diffusion` corps `{modele:{nom, langue}, parametres, identites?}` → `configurer` ; efface `valide_client_le`/`confirme_client` comme une modification du contenu.
- `POST /api/schedule/{post_id}/diffusion/confirmer` corps `{confirme_incertain: true}` → `lancer(..., confirme_incertain=True)` sous les mêmes contrôles que `fire` (client, plafond 402).
- Erreurs via `_wa_erreur` (409 `{message, code}`, 502 Kapso, 402 plafond). Localhost seulement.

- [ ] Step 1 : banc : un post avec un compte whatsapp passe `verifier_cibles` ; `fire` → adaptateur → `lancer` → post `posted`, `remote_ids["whatsapp:<pid>"] = broadcast_id` ; sans config → post `ready` avec erreur claire ; client `valide_par_client` sans validation → 409 existant, aucun appel Kapso ; espace archivé → rien ; `tick` relit une diffusion `sending` ; PUT efface la validation client ; un compte whatsapp d'un autre espace refusé.
- [ ] Step 2-4 : échec, implémentation, vert + `test_scheduler_publish.py`, `test_whatsapp_comptes.py`, `test_whatsapp_validation.py`, `test_plafonds_garde.py`, `test_espaces_scheduler.py`.
- [ ] Step 5 : L10 + `--check`. Commit.

### Task 5 : écran

**Files :** Create `frontend/shared/dz-diffusion-whatsapp.js` (+ copie `frontend/dist/shared/`), `frontend/shared/i18n/diffusion.json`, `frontend/shared/qa/diffusion.test.mjs`, `scripts/patch_bundle_dzdiffusion.py`, `backend/tests/test_diffusion_ecran.py` ; Modify `frontend/dist/index.html` (charger le script), `backend/tests/_i18n_l1_aide.py` (`avant_dzdiffusion` en tête de `avant_whatsapppage`), `frontend/shared/dz-projet-canaux.js` si son filtre exclut whatsapp

- Maillon `dzdiffusion` : retire le filtre `c.plateforme!=="whatsapp"` de `DzPostComptes` et pose, dans l'inspecteur du post, un point de montage `<div data-dz-diffusion={post.id}>` visible quand un compte whatsapp est coché ; ajoute `whatsapp` à la table des canaux `_t` (icône existante du rail WhatsApp).
- `window.__dzDiffusionWhatsapp.monter(el, postId)` : choix du modèle (approuvés, catégorie affichée), champs des paramètres, audience (« N contacts, M écartés : … »), devis en dollars, bouton « Enregistrer la diffusion » (PUT) ; après lancement : statut, compteurs (envoyés, livrés, lus, échecs, retirés du marketing), bouton « Relire » ; état incertain : message et bouton « Confirmer l'envoi » via `await window.__dzDialogue.confirmer(` (jamais `confirm` natif). Réponses périmées ignorées (jeton de requête), délai 30 s.
- [ ] Step 1 : banc node (faux DOM/fetch) : modèle sans paramètres, modèle nommé, audience vide → bouton désactivé et message, 402 → dialogue plafond `dz-plafonds`, 409 incertain → dialogue, FR et EN.
- [ ] Step 2 : banc Python du maillon : appliqué une fois, `--check`, `defaire` rend l'octet d'origine, épingles inchangées.
- [ ] Step 3 : implémenter ; `python scripts/i18n_assembler.py` puis `--check` ; `python scripts/patch_bundle_dzdiffusion.py` ; rejeu `python scripts/repatch_all.py --from dzdiffusion` si la chaîne l'exige.
- [ ] Step 4 : bancs verts + `test_whatsapp_page_ecran.py`, `test_garde_client_ecran.py`, `test_dialogues_partout`.
- [ ] Step 5 : commit.

### Task 6 : connaissance et docs

**Files :** `docs/agent/catalogue/scheduler.json` (+ fiches du panneau), `docs/agent/AGENT.md` (Planificateur ; remplacer « jamais une cible de publication » par la règle de diffusion), `docs/agent/ancres.json`, `AGENTS.md`, `CHANGELOG.md`

- [ ] Step 1 : `python scripts/agent/catalogue.py`, rôles FR/EN rédigés d'après le code, `--check`.
- [ ] Step 2 : `test_agent_catalogue.py` vert.
- [ ] Step 3 : commit.

## Fin

Revue finale de branche, vague de correctifs, puis preuve sur le backend jetable 8798 (faux Kapso étendu aux broadcasts) avec captures FR/EN dans `docs/superpowers/specs/captures/t328/`.
