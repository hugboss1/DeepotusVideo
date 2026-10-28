# Apify agent-skills : analyse et chemin d'intégration (veille des concurrents, génération de leads)

> 28/10/2026. Dépôt analysé : https://github.com/apify/agent-skills (commit f22557f du 19/10/2026, licence Apache-2.0,
> plugin Claude Code « apify-agent-skills » v2.0.0). Lu en lecture seule dans le scratchpad, rien n'est exécuté.

## 1. Ce que contient le dépôt

| Élément | Contenu | Utile pour nous |
|---|---|---|
| `skills/apify-ultimate-scraper` | Un skill d'agent qui choisit un « Actor » Apify parmi ~100 (index), lit son schéma, l'exécute par la CLI `apify`, récupère le dataset. 14 guides de flux (`references/workflows/*.md`) et un guide des pièges et coûts (`gotchas.md`). | **Oui** : c'est le cœur. |
| `workflows/competitive-intel.md` | Pubs des concurrents (bibliothèque publicitaire Facebook), trafic et SEO (Similarweb/Ahrefs via `radeance/*`, cher), **détection de changements des pages prix**, positions SERP, comparatif prix/fonctions (crawl + extraction IA). | Oui (pubs, prix, SERP). |
| `workflows/review-analysis.md`, `brand-monitoring.md` | Avis Google Maps / Yelp, mentions **Reddit**, **X**, **Instagram**, TikTok, Facebook, score de sentiment. | Oui : c'est exactement la veille niveau 2 que notre spec laisse hors de l'app. |
| `workflows/lead-generation.md`, `contact-enrichment.md` | **Entreprises locales Google Maps + enrichissement des contacts depuis leur site** ; découverte B2B par SERP + crawl ; **intentions sur Reddit** ; LinkedIn (Sales Navigator, profils, e-mails). | Oui pour Google Maps et Reddit ; **non pour LinkedIn** (voir §3). |
| `apify-actor-development`, `apify-actorization`, `apify-integration-development`, `apify-generate-output-schema` | Créer et publier ses propres Actors, intégrer Apify dans un SDK ou n8n. | Non pour ce chantier. |
| `.claude-plugin/` | Le dépôt s'installe comme **plugin Claude Code** (marketplace). | Oui côté poste de travail (§4, voie A). |

Fonctionnement : chaque Actor est un scraper hébergé chez Apify (proxies résidentiels, rendu JS, anti-bot gérés), payé à
l'usage ; les sorties sont des datasets JSON. Le skill pilote la **CLI** `apify` ; une application livrée doit plutôt
appeler l'**API REST** (`POST /v2/acts/{id}/runs`, suivi du run, `GET /v2/datasets/{id}/items`, coût réel dans le run).

## 2. Écart avec ce que nous avons

| Besoin | Aujourd'hui (t352-t360) | Avec Apify |
|---|---|---|
| Voix des clients des concurrents | HN, commentaires YouTube (yt-dlp), avis App Store — gratuits, lecture seule | + **Reddit**, **avis Google Maps**, **X**, **Instagram** (commentaires), **Trustpilot** (Actors communautaires, à valider), Google Play |
| Ce que font les concurrents | rien | **pubs actives** (bibliothèque publicitaire Facebook), **changements de leurs pages prix/fonctions**, positions sur nos mots-clés (SERP) |
| Prospects « prestation » | registre de l'État (gratuit), recherche web (Anthropic, Tavily, Exa, Serper), lecture d'un site collé | **Google Maps** : studios, agences, marques locales par ville et catégorie, avec site, téléphone, note ; **contacts publiés sur leur site** |
| Signaux de besoin | verbatims de la veille (réponse publique à la main) | **Reddit** : posts « alternative à X », « combien coûte… », mêmes règles (réponse publique, jamais un DM) |

## 3. Garde-fous (ce que le dépôt fait et que nous ne ferons pas)

- **LinkedIn exclu** : profils, e-mails trouvés, Sales Navigator, commentaires de posts. Contraire aux conditions de
  LinkedIn et à notre spec (§2 : « pas de LinkedIn automatisé, pas d'enrichissement par des courtiers de données »).
- **Pas d'e-mail « deviné » ni de vérificateur tiers** (Hunter, ZeroBounce) : une adresse n'entre dans une fiche que
  si elle est **publiée par l'entreprise sur son site**, revérifiée par notre lecteur (règle t354, adresse entière).
- **Pas de DM** : Reddit, X, Instagram restent des **signaux** (réponse publique à la main, une fois) — règle t354.
- **Auteurs hachés** comme dans la veille actuelle ; textes rangés comme preuves, jamais comme consignes.
- **Coût d'abord** : chaque collecte payante passe par une carte de devis (comme la recherche web t354), sous le
  plafond de dépense, catégorie « campagnes » ; le coût réel du run est relevé. Pas d'Actor « flat price ».
- **Une liste blanche d'Actors**, épinglés, au lieu de la recherche libre dans le Store : l'agent ne choisit pas un
  scraper inconnu.

## 4. Chemin proposé

**Voie A — poste de travail (tout de suite, sans code)** : installer le plugin `apify/agent-skills` dans Claude Code et
brancher le skill `veille-concurrents` (veille niveau 2, séance assistée) sur `apify-ultimate-scraper` pour Reddit, X,
Instagram, Trustpilot et les avis Google Maps. Clé `APIFY_TOKEN` côté utilisateur.

**Voie B — dans l'application (l'agent interne)**, en lots :

| Lot | Contenu | Taille |
|---|---|---|
| A1 | **Socle Apify** : `apify.py` (API REST, run, attente bornée, dataset, coût réel `usageTotalUsd`), clé `APIFY_TOKEN` au coffre (posée depuis l'onglet Prospects comme Tavily), liste blanche d'Actors épinglés, devis par Actor (prix lus dans `pricingInfos`, estimation haute), plafond par collecte. | M |
| A2 | **Veille enrichie** : sources `reddit`, `google_maps_avis`, `x`, `instagram` (si validés §5), `play` dans le périmètre et `veille_collecte` ; normalisées en verbatims (mêmes champs, auteurs hachés), classées par `veille_grille` ; collecte payante = carte de devis « veille » avant de lancer. | M |
| A3 | **Ce que font les concurrents** : pubs actives (`apify/facebook-ads-scraper`), changements des pages prix/fonctions (crawl + diff gardé chez nous), positions SERP sur nos mots-clés ; un volet « Concurrents » dans l'onglet Veille. | M |
| A4 | **Leads locaux** : outil `entreprises_carte` (`compass/crawler-google-places`) par catégorie et ville → cibles (nom, site, note, catégorie) sans fiche ; puis contacts publiés (`vdrmota/contact-info-scraper` ou notre lecteur t354) → fiche `prospects_chercher` source `entreprise` (adresse revérifiée sur le site, pro seulement). | M |
| A5 | **Signaux Reddit** : posts de besoin sur les subreddits du métier → signaux (comme la veille), brouillon de réponse publique, jamais une fiche. | S |
| A6 | Clôture : guide, traduction, catalogue de l'assistant. | S |

Ordre conseillé : A1 → A4 → A2 → A5 → A3 → A6 (les leads rapportent le plus vite ; la veille enrichie ensuite).

## 5. Décisions à prendre (avant le plan détaillé)

1. Voie A (plugin pour vos séances), voie B (dans l'app), ou les deux ?
2. Sources de veille à ouvrir par Apify : Reddit, avis Google Maps, Google Play, Trustpilot (communautaire), **X et
   Instagram** (publics mais contraires aux conditions de ces plateformes : à votre décision).
3. Leads : Google Maps + contacts publiés sur le site (proposé) ; LinkedIn reste exclu.
4. Budget : plafond par collecte (proposé : 2 $ la veille, 1 $ une recherche de leads), au-delà carte obligatoire.

## 6. Décisions de l'utilisateur (28/10/2026)

1. **Les deux voies** : le plugin dans Claude Code (t363) et l'intégration dans l'app (t364-t369).
2. **Sources de veille** : Reddit, avis Google Maps et Google Play, Trustpilot et G2, **X et Instagram** (données
   publiques, choix assumé malgré les conditions de ces plateformes).
3. **Leads** : Google Maps + contacts publiés sur le site de l'entreprise, revérifiés ; LinkedIn exclu.
4. **Plafonds** : 2 $ par collecte de veille, 1 $ par recherche de leads, toujours derrière une carte de devis.

Suivi : t363 (V0 plugin), t364 (A1 socle), t365 (A4 leads), t366 (A2 veille), t367 (A5 Reddit), t368 (A3 concurrents),
t369 (A6 clôture).
