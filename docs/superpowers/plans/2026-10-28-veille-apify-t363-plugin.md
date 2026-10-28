# V0 (t363) — plugin apify/agent-skills dans Claude Code + skill veille-concurrents : plan

> Spec : `docs/superpowers/specs/2026-10-28-veille-apify-analyse.md` (§4 voie A, §6 décisions). Aucun code de l'app.
> Touche le poste de travail : réglages Claude Code (plugin), la CLI `apify`, et le skill personnel
> `~/.claude/skills/veille-concurrents` (hors dépôt).

**But :** dans une séance Claude Code, la veille niveau 2 (X, Instagram) et les sources que l'app n'a pas encore
(Reddit, avis Google Maps / Play, Trustpilot / G2) se collectent par Apify, avec devis avant chaque run, plafond dur et
les mêmes règles que la veille actuelle (lecture seule, auteurs hachés, verbatims = preuves).

## Décisions (rulings)

1. **Plugin restreint** : seulement `apify-ultimate-scraper@apify-agent-skills` (pas les plugins de développement
   d'Actors). Il apporte le savoir (index, flux, pièges) ; nos règles restent dans `veille-concurrents`.
2. **CLI `apify`** installée globalement (`npm install -g apify-cli`, v1.5.0 au moins). **Le jeton** : vous le posez
   vous-même (`apify login` ou `APIFY_TOKEN` dans vos variables d'environnement) ; Claude ne le tape ni ne le lit.
3. **Liste blanche** dans le skill (`references/apify.md`) : un Actor par source, choisi au relevé de la tâche 2
   (Apify-maintenu d'abord, sinon le communautaire le plus utilisé sur 30 jours, jamais déprécié), avec son schéma
   d'entrée minimal. Hors liste : interdit, sauf ajout validé par vous.
4. **Coût** : avant chaque run, prix lu dans `apify actors info --json` (`currentPricingInfo`), devis dit, et run lancé
   avec `--max-total-charge-usd 2` (plafond dur côté Apify, décision §6.4) ; « flat price » refusé. Le coût réel du run
   (`usageTotalUsd`) est noté dans `limites.md` de la veille.
5. **Normalisation** : un petit script `scripts/apify_vers_brut.py` convertit le dataset de chaque Actor en lignes
   `brut/*.jsonl` au format de `collecte.py` (concurrent, source, url, date, auteur haché, texte, score, requête) ;
   la suite (classement, rapport) ne change pas. Les pseudos ne sont jamais gardés en clair.
6. **LinkedIn exclu** ; pas de DM ; X et Instagram : votre décision du 28/10 (publics, contraires à leurs conditions).

## Tâches

1. **Installer** : `npm install -g apify-cli` ; `claude plugin marketplace add apify/agent-skills` ;
   `claude plugin install apify-ultimate-scraper@apify-agent-skills`. Vérifier : `apify --version`, plugin listé
   (`claude plugin list`). Vous posez le jeton ; vérification `apify info --json` (identité, sans le jeton).
2. **Relever la liste blanche** : pour Reddit, X, Instagram (commentaires), avis Google Maps, Google Play, Trustpilot,
   G2 : `apify actors search … --json` puis `apify actors info <id> --input --json` ; garder un Actor par source avec
   tier, modèle de prix, prix par résultat, champs d'entrée et de sortie utiles. Écrire `references/apify.md`.
3. **Script de normalisation** `apify_vers_brut.py <source> <concurrent> <dataset.json> <brut/>` + son banc (un jeu
   par source, auteurs hachés, dédoublonnage par `cle()` de `collecte.py`).
4. **Skill** : nouvelle étape « Collecte niveau 2 par Apify » dans `SKILL.md` (avant l'étape Chrome, qui reste le
   secours), protocole de devis, plafond, normalisation, journal des coûts ; mise à jour de `sources.md`.
5. **Essai réel borné** (avec votre accord, ≤ 0,50 $) : une source gratuite ou très peu chère (Reddit) sur un
   concurrent ; vérifier le brut, le classement, le coût réel. Puis relecture et commit du skill (dépôt de skills
   personnels, hors DeepotusVideo).

## Points de relecture

- un Actor qui change de schéma (champ de sortie renommé) : le script le dit, jamais une ligne vide silencieuse ;
- un run qui dépasse le plafond : arrêté par Apify (`maxTotalChargeUsd`), résultat partiel gardé et dit ;
- aucun jeton dans un fichier du skill, un journal ou une sortie.
