# Passage de relais : chantier « boîte à outils », suite après t308 et t325 (26/10/2026)

## Où on en est

| Lot | Titre | État |
|---|---|---|
| t305, t306 | Socle et type d'espace / fiche client | fusionnés, installés (25/10) |
| t307 | Projets orientés vers leurs canaux | PR #452, main 2330b389, installé |
| t308 | Assistant de création d'espace, vérification des canaux sans publication | PR #454, main a463cd3d, installé |
| t325 | Nouveau post et Envoyer vers › Scheduler préremplis avec les canaux du projet actif | PR #455, main **646b6d97**, installé |

- **Installation de référence : 646b6d97**, installée le 26/10.
  - Sauvegarde : `%LOCALAPPDATA%\DeepotusVideoGen\_backup_predeploy_20261026-t308-t325`, avec `deepotus.db`.
  - Application relancée sur 8765 et vérifiée à l'écran, en lecture seule.
- **Suivi** : artifact https://claude.ai/artifact/9WVmPNinFLNN3Xxv2EHGht, collection `taches`.
  - t305 à t308 et t325 sont `fait`.
  - Écrire avec `if_version`.
- **Spec** : `docs/superpowers/specs/2026-10-25-boite-a-outils-design.md`.
- **Plan d'ensemble** : `docs/superpowers/plans/2026-10-25-boite-a-outils.md`. Il est détaillé seulement pour A0-A1 : chaque lot écrit son plan détaillé au démarrage.

## Chantier suivant, dans l'ordre du suivi (rang)

1. **t326 (S), petits défauts de t308.** C'est la même zone que t308, il est donc recommandé de la faire d'abord ou de l'intégrer à t309. La fiche du suivi liste les sept points :
   - « Annuler » après l'étape 1 laisse l'espace créé ;
   - une vérification écartée par la garde de révision s'affiche « non vérifié » sans explication ;
   - un compte historique dont les clés changent garde sa vérification ;
   - la date affichée est celle du PC pour un canal porté par le téléphone ;
   - les messages de CoffreVerrouille ne passent pas par L10 (l'anglais montre « le coffre est fermé ») ;
   - une 500 dans `_oauth_callback` si `oublier_verification` échoue ;
   - le piège du focus au clavier manque dans les boîtes partagées.
2. **t309 (L), A4 : validation client et sécurités de publication.** Spec §5.5 :
   - état « à valider », refusé par le Planificateur avec un 409 qui nomme le client ;
   - en `publie_en_son_nom`, une confirmation nominative qui exige un consentement daté **en cours** pour le canal ;
   - une révocation met en pause les posts programmés sur ce canal, comme l'archivage de t210 ;
   - un journal dans la fiche client ;
   - un bandeau « pour qui » avec un liseré dans un espace client.
   - Il s'appuie sur `fiche_client.consentements_en_cours` (t306) et la garde 409 `comptes.verifier_cibles` (t204).
3. **t310 (L), B1 : WhatsApp par Kapso.**
   - **Décision du 26/10, qui remplace celle du 25/10** : une seule clé Kapso au coffre. Chaque client relie son propre compte Meta Business et son numéro par un lien d'installation Kapso (`customers` + `setup_links`), sans compte Kapso à lui. Un `phone_number_id` par espace.
   - Précédé de **t327 (S), B0** : remettre la spec §6 à jour d'après le relevé gokapso (BSUID, messages de service facturés, opt-out Meta, propriété du fil).
   - Lire les notes de t310 dans le suivi (apport gokapso) et la doc Kapso au démarrage.
   - Il reprend aussi la lecture du numéro WhatsApp reportée de t308.
4. **t311 (L), B2 : agent WhatsApp par espace et page WhatsApp.** Après t309 et t310.
   - Options cochées par l'utilisateur après lui : **t328, B3** (diffusions), puis **t329, B5** (appels et agent vocal).

## Mise au point du 26/10 (après ce relais)

- **t326 et t309 sont `fait`** : PR #456 et #457 fusionnées (main 9e4b3ab9) et **installées** le 26/10.
  - **Installation de référence : 9e4b3ab9.** Sauvegarde : `_backup_predeploy_20261026-t326-t309`, avec `deepotus.db`.
  - `test_i18n_l2.py` installé est ancien (banc de dev) : ajouté aux exclusions du script, comme `test_etabli_canevas.py`.
  - 8765 relancé et vérifié à l'écran, en lecture seule.
- **t295 (L4.0) est `fait`** : les fusions sont faites ; la recette iPhone reste en t304.
- **t289 (L4.1) reste `en_cours`** : T10 fusionnée dans main du téléphone (e5f6bc0) ; la recette T11 sur l'Oppo avance sur `chantier/l4-1-recette` (R30 et R31 corrigés), non fusionnée.
- Le suivi affiche maintenant le numéro **tXXX** et le **code de lot** (A4, B1, L4.3, M4…) de chaque tâche, regroupées par lot. Garder ces codes en tête des titres (« B1 : … », « Compagnon L4.3 : … ») pour que la page les reconnaisse.

## Méthode qui a marché (t307, t308, t325)

- **Démarrage du lot.**
  - Créer un worktree depuis **origin/main**, jamais depuis le main local, qui a des centaines de commits de retard : `git worktree add -b chantier/<nom> .claude/worktrees/<nom> origin/main`.
  - Écrire le plan détaillé avec superpowers:writing-plans, le committer, puis l'exécuter avec superpowers:subagent-driven-development.
- **Exécution en sous-agents.**
  - Chaque tâche est relue par un relecteur.
  - À la fin : une relecture finale sur opus, une seule vague de corrections, puis une re-relecture ciblée.
  - Le registre de chaque lot est dans `.superpowers/sdd/<plan>/progress.md`.
- **Bundle.** `frontend/dist/assets/index-BEOJX8L5.js` n'est jamais reconstruit.
  - On le modifie par un maillon de queue `scripts/patch_bundle_<tag>.py`, en octets et en CRLF.
  - L'inverse va en tête de chaîne dans `backend/tests/_i18n_l1_aide.py`. La chaîne actuelle se termine par `dzassistant` puis `dzcanauxpre`.
  - Rien ne doit toucher l'intérieur des blocs `/*__DZ_*_BEGIN__*/`. DzProjetsBar, par exemple, vit dans la couche montage : on passe alors par la voie L3 avec la compensation G1.
- **Textes.**
  - Les clés `dzT` vont dans `frontend/shared/i18n/*.json`, assemblées par `scripts/i18n_assembler.py`. `frontend/shared` doit rester identique à `frontend/dist/shared`.
  - Les messages du serveur passent par L10 : `scripts/i18n_l10_traductions.json`, puis `i18n_l10_erreurs.py --check`.
  - Le catalogue de l'agent se met à jour avec la skill `connaissance-agent`.
- **Bancs.**
  - Le Python embarqué est `%LOCALAPPDATA%/DeepotusVideoGen/runtime/python/python.exe`. Il ignore PYTHONPATH : les bancs ajoutent eux-mêmes le chemin avec `sys.path.insert`.
  - On les lance depuis `backend/` avec `PYTHONUTF8=1`, **un par un**, car certains modifient le bundle ou routes.py.
  - Environ 25 bancs sont déjà rouges sur main. On compare toujours la base et HEAD.
- **Preuves à l'écran.**
  - Sur un backend de preuve, port 8799, avec des données temporaires et sans clé.
  - **Aucun appel réseau réel** : pas de « Vérifier » sur de vrais services.
- **Installation**, uniquement sur demande de l'utilisateur.
  - Script de table des hachages base/installé/cible. Il refuse toute dérive. Exemple : `install_t308_t325.py`, avec BASE = l'installation précédente et CIBLE = la tête de main.
  - Il sauvegarde les fichiers et `deepotus.db` dans `_backup_predeploy_<tag>`, puis copie depuis `git show`.
  - Exclus : les outils de dev restés anciens dans l'installation (`_i18n_l1_aide.py`, `g1_generer.py`, `test_etabli_canevas.py`).
  - Ne copier que si 8765 est libre. Relancer ensuite avec `wscript %LOCALAPPDATA%\DeepotusVideoGen\scripts\launch-silent.vbs`.

## Règles de l'utilisateur

- Pousser, ouvrir une PR, fusionner ou installer : seulement sur sa demande explicite, lot par lot.
- Ne jamais toucher 8765 sans sa demande.
- Aucune clé ou secret dans les journaux, les URL ou les réponses.
- Ne pas toucher le worktree mobile `deepotus-mobile-l4`, où l'utilisateur travaille.
- Refuser les cookies optionnels.
- Répondre en français.

## Laissé de côté (non bloquant)

- Après Envoyer vers › Scheduler, le calendrier n'affiche le brouillon qu'après un rechargement. C'était déjà le cas avant t325.
- Le marqueur `/*dzcanauxpre*/` n'a pas de `__`. Un futur banc qui exécute `_code` sur le bundle devra lire la vue « d'avant dzcanauxpre », comme le fait `test_etabli_canevas`.
- Le banc 2.2 de `test_canaux_preremplis` est fragile s'il y a une reformulation dans AGENT.md.
- Deux bancs rouges sans lien avec ces lots :
  - `test_photolab_formulaires` 8.1 : vendor photocraft absent du worktree ;
  - `test_textes_moteur` W14 : table L6 périmée pour `mod-didact.js`.

## Prompt de démarrage proposé

> Lance t326 puis t309 du chantier boîte à outils : lis `docs/superpowers/handoffs/2026-10-26-boite-a-outils-suite.md`, écris le plan détaillé de chaque lot (worktree depuis origin/main), exécute-le en sous-agents avec relectures et mets à jour le suivi. Ne pousse ni n'installe sans mon accord.
