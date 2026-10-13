# Plan : Espaces de marque (t200 → t211)

Conception : `docs/superpowers/specs/2026-10-13-espaces-de-marque.md`.

Règles communes à toutes les tâches :
- une PR par tâche, en TDD ;
- mutations rejouées ;
- preuve sur 8799 ;
- installation vérifiée par `git hash-object`.

**L'espace `deepotus` doit rester identique à l'octet** : persona, kit, liste Quick et comptes. Chaque tâche porte une assertion de non-régression sur Deepotus.

| Tâche | Lot | Taille | Contenu | Dépend de |
|---|---|---|---|---|
| t200 | E0 Socle | M | Table `espaces`, `espace_actif`, `DATA_ROOT/espaces/<id>/`, migration vers l'espace `deepotus` (persona.json, kit, contenus.json depuis la liste Quick actuelle), API `/espaces` (lister, créer, activer, archiver), événement `deepotus:espace-refresh`. | — |
| t201 | E1 Persona v2 | M | Persona v2 par espace ; PromptEngine, TTS, News voix, musique, marketing et autoclips lisent l'espace actif (ou celui du job) ; plus de `persona_id="deepotus"` en dur ; `GET/PUT /espaces/{id}/persona`. | t200 |
| t202 | E2 Écran | M | Sélecteur d'espace dans la carte de marque de la barre ; écran Persona branché sur l'API (fin de `PERSONA_PRESETS` en mémoire) ; le kit par défaut de l'espace s'active avec lui ; Réglages › Espaces. | t201 |
| t203 | E3 Comptes | L | Table `comptes_diffusion` ; secrets du coffre en noms espacés `compte.<id>.*` ; migration des clés plates avec repli ; publishers par compte ; OAuth YouTube/TikTok par compte ; Réglages › Comptes de l'espace (plusieurs X, Telegram…). | t200 |
| t204 | E4 Scheduler | L | `scheduled_posts.espace_id` + `cibles` ; écran filtré par espace, choix des comptes ; garde 409 contre un compte d'un autre espace ; métriques et quotas par compte. | t203 |
| t205 | E5 Onboarding | L | Assistant en 8 étapes (produit/URL, audience, personnage, ton/voix, planches d'ambiance devisées, références, interdits, synthèse LLM validée) ; mode manuel sans LLM ; sous plafond. | t202 |
| t206 | E6 Identité visuelle | M | `identite/` (logo, mascotte, produits, palette, typos, style écrit, planche validée) ; descripteurs injectés à la place du « DNA » Deepotus ; références passées aux modèles image→vidéo, édition et avatar. | t205 |
| t207 | E7 Contenus de départ | M | `contenus.json` : modèles Quick, catégories, ingrédients, vibes, templates backend, hashtags générés à l'onboarding ; **Quick affiche les modèles du persona au premier démarrage** ; « Générer » produit ou régénère des modèles de l'espace. | t205 |
| t208 | E8 Codé en dur | S | news_rank, news_chain, User-Agent, schemas, prompt_engine, music, prompts.jsx : lecture de l'espace. | t201 |
| t209 | E9 Bibliothèque et dépenses | M | Projets rattachés à un espace ; filtre de la Bibliothèque ; `depenses.espace_id` ; relevé par espace exportable (facturation client) ; plafond optionnel par espace. | t200 |
| t210 | E10 Client et isolation | M | Export/import d'un espace sans secrets ; archivage ; skill deepotus-comms paramétré par espace ; banc d'isolation (aucune donnée d'un espace visible depuis un autre). | t204, t207 |
| t211 | E11 Traduction et guide | M | Clés FR/EN de tous les écrans neufs ; chapitre du guide « Travailler pour plusieurs marques » avec scènes. | t210 |

Ordre conseillé : t200 → t201 → t202 → t203 → t204 → t208 → t205 → t206 → t207 → t209 → t210 → t211.

À la fin de t204, on peut déjà publier Rippled ou un client sur ses propres comptes. L'onboarding (t205 à t207) vient ensuite.
