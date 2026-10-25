# Correctifs finaux t306 (25/10/2026)

## Changements
1. **Un seul consentement actif par canal.**
   - `fiche_client.valider` : si plusieurs lignes actives sur un canal, la plus recente (date, puis position) est gardee ; les autres sont CLOSES a la date de la gardee (pas supprimees, la preuve reste).
   - `fiche_client.revoquer` : ferme TOUTES les lignes actives du canal, UNE seule ligne de journal `revocation` par geste.
   - `espaces_paquet._ecarts_fiche` : une ligne `ignores` par ligne remplacee (« consentement n°i : un autre, plus récent (n°j), court déjà pour le canal X, celui-ci est clos »).
   - Bancs 5q (revoquer ferme les deux lignes, valider contourne), 5r (lecture normalisee), 5s, 5t (import : un actif + ignores).
2. `espaces.client_responsable` suit le parent seulement si le type est `produit`. Banc 2f. (`_vue` inchange.)
3. AGENTS.md:47 : ecritures locales seulement, GET aussi lisible par les appareils appaires.
4. ConflitClient : « révoquez-les » / EN « revoke them » ; `scripts/i18n_l10_traductions.json` (cle + fr + en, ordre et CRLF conserves) ; `erreurs.json` regenere.

## Commandes / sorties
- test_espaces_type_client 80/0 ; test_espaces_socle 50/0 ; test_espaces_onboarding 47/0 ; test_espaces_comptes 42/0 ; test_i18n_l10 25 ok, 0 echec.
- `i18n_l10_erreurs.py --check` : 2662 gabarits, 0 sans traduction, 0 fautif, 0 orpheline, « à jour ».
- test_espaces_client : rouge connu et preexistant (`[dzespace] ancre x0 (attendu 1)`), non lie.
- Mutation : `for x in en_cours:` -> `en_cours[:1]` dans `revoquer` : `FAIL 5q`, 79/1 ; restaure, `cmp` identique.
