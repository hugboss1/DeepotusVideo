# A1 (t364) — socle Apify dans l'application : plan

> Spec : `docs/superpowers/specs/2026-10-28-veille-apify-analyse.md` (§3 garde-fous, §4 voie B, §6 décisions).
> Socle seulement : AUCUN outil de l'agent ne s'en sert encore ; t365 (leads Google Maps) et t366 (veille enrichie)
> s'y branchent. Exécution : une branche, une PR, plan validé avant le code.

**But :** l'application sait lancer un Actor Apify de sa **liste blanche**, au **devis** connu d'avance, sous un
**plafond dur** posé chez Apify, relever son **coût réel** et rendre ses résultats ; l'utilisateur pose la clé dans
l'onglet Prospects ; une **carte « collecte »** de l'agent, acceptée, déclenche un run (même circuit que la carte
« recherche » de t354).

## Décisions (rulings)

1. **API REST, pas la CLI** (l'app est livrée aux clients) : `POST /v2/acts/{acteur}/runs` (acteur = `owner~nom`) avec
   `waitForFinish=60`, `maxTotalChargeUsd`, `maxItems`, `timeout`, `memory`, `build` ; suivi par
   `GET /v2/actor-runs/{id}?waitForFinish=60` ; arrêt par `POST /v2/actor-runs/{id}/abort` ; résultats par
   `GET /v2/datasets/{id}/items?clean=true&format=json&limit=N`. Jeton dans l'en-tête `Authorization: Bearer`, jamais
   dans une URL ni un journal. Client httpx, coutures de banc `_POST`, `_GET`, `_DORMIR`.
2. **Plafond dur** : chaque run porte `maxTotalChargeUsd` = le plafond de l'usage (veille 2 $, leads 1 $ — décision
   §6.4) ; Apify arrête le run au-delà. En plus, avant le run : `plafonds.verifier` (catégorie « campagnes ») sur le
   devis ; après : `noter_reel_lignes` avec `usageTotalUsd` (même en échec, comme t354 I4).
3. **Liste blanche** `ACTEURS` (dans `apify.py`) : {clé → acteur, build épinglé, usage `veille`|`leads`, entrée
   autorisée (champs et bornes), champ « nombre de résultats »}. Un acteur hors liste : refus. Les entrées sont
   filtrées champ par champ (aucun champ libre transmis tel quel). La liste du socle : `google_maps` (t365),
   `contacts_site` (t365), `reddit`, `avis_google_maps`, `google_play`, `trustpilot`, `g2`, `x`, `instagram` (t366),
   chaque entrée remplie au relevé de t363 (identifiant, build, prix) — au socle, deux entrées réelles suffisent aux
   bancs (`google_maps`, `reddit`), les autres arrivent avec leur lot.
4. **Devis** : `GET /v2/acts/{acteur}` → `pricingInfos` (l'enregistrement en vigueur) ; `PAY_PER_EVENT` : somme des
   `eventPriceUsd` des évènements de démarrage + par résultat × N (palier : le prix le plus haut, estimation haute) ;
   `PRICE_PER_DATASET_ITEM` : prix unitaire × N ; `FREE` : forfait de calcul `FORFAIT_CALCUL_USD` (0,05 $) ;
   `FLAT_PRICE_PER_MONTH` : refus. Prix gardés 24 h dans `DATA_ROOT/cache/apify`. Le devis ne dépasse jamais le plafond
   de l'usage, sinon refus avant tout run. Kind de pricing `apify` (op `{"kind": "apify", "usd": devis}`).
5. **Durée** : 10 min au plus par run (`timeout=600`) ; au-delà de l'attente, le run est abandonné (`abort`) et ce qui
   est déjà dans le dataset est rendu, marqué partiel.
6. **Clé** : `APIFY_TOKEN` au coffre (SECRETES), posée par `POST /api/prospects/recherche/cle` (fournisseur `apify`,
   comme Tavily ; pas dans Réglages › Clés, même raison qu'en t354). Le panneau « Recherche web » montre « Apify :
   prêt / clé à poser ».
7. **Carte « collecte »** (genre neuf du format v1) : `{acteur, usage, entree, max, devis_usd}` ; acceptée, la route
   réserve (clé 503, plafond 402) sous le verrou, écrit la décision, puis lance le run HORS du verrou (même schéma que
   t354 I5 : jamais rejouée) ; le fait « terminee » porte le nombre de résultats, le coût réel et un dépôt JSON des
   résultats lisible par l'agent (les textes reviennent ENCADRÉS comme des preuves). **Le compagnon** reçoit le genre
   dans `format.ts` (leçon t359 : un genre inconnu y invalide la conversation).

## Tâches

1. **`apify.py`** : `ACTEURS`, `configure()`, `devis(cle, n)`, `op(cle, n)`, `async lancer(cle, entree, n, plafond)` →
   `{items, cout_usd, statut, partiel, run_id}` ; erreurs `SansCle`, `ApifyRefus(message, code)`,
   `ApifyEchec(message, cout_usd)`. Banc `test_apify.py` (faux serveur : run fini d'emblée, run à suivre, run trop
   long → abort + partiel, FAILED avec coût, 402 du compte Apify, prix PPE / par résultat / gratuit / forfait refusé,
   acteur hors liste, champ d'entrée non autorisé, jeton jamais dans un message ni dans l'URL).
2. **Pricing et coffre** : kind `apify` dans `pricing.py` ; `APIFY_TOKEN` dans `config.py` et `coffre.SECRETES` ;
   fournisseur `apify` accepté par la route de clé ; `GET /api/prospects/recherche` le liste. Bancs mis à jour.
3. **Carte « collecte »** : `agent_format.GENRES_CARTE`, schéma et doc du format, route de décision
   (`_reserver_collecte`, `_executer_collecte`, dépôt des résultats) ; écran `dz-campagnes.js` (requête, devis, nombre
   de résultats, coût réel) ; **compagnon** `format.ts` + rendu minimal ; bancs `test_agent_collecte_carte.py`, node,
   jest.
4. **Écran** : ligne Apify dans le panneau « Recherche web » de l'onglet Prospects ; i18n FR/EN ; messages L10.
5. **Connaissance** (AGENT.md bref, catalogue), relecture d'ensemble, PR ; installation sur votre accord.

## Points de relecture

- un run qui coûte plus que le devis (palier, retries) : `maxTotalChargeUsd` le borne ; le coût réel est noté ;
- un acteur qui change de prix entre devis et run : le devis est recalculé à l'acceptation de la carte ;
- un dataset énorme : `limit` = N, jamais plus ; textes bornés et encadrés ;
- panne réseau après le lancement : le run est relu par son id, jamais relancé (pas de double facturation).
