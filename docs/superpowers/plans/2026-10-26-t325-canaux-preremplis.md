# t325 — Écrans de création préremplis avec les canaux du projet actif : plan détaillé

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** Bibliothèque › Envoyer vers › Planificateur et Planificateur › Nouveau post créent un brouillon qui vise les
comptes du projet actif, et l'éditeur les montre cochés dès l'ouverture, au lieu de X. L'utilisateur peut les décocher.
S'il n'y a pas de projet actif, ou si le projet n'a aucun canal, X reste la cible comme aujourd'hui.

**Architecture :**
- **Le serveur fait déjà le travail (t307).** `POST /api/schedule` sans `channels` ni `comptes` reprend les canaux du
  projet actif de l'espace **du post** (`library_projects.canaux_par_defaut`, routes.py ~8780). S'il n'en trouve aucun,
  `channels` retombe sur `["x"]` (routes.py ~8752). Un compte périmé est sauté sans erreur. Tout cela est couvert par
  `backend/tests/test_projets_canaux.py`.
- **Ce qui manque est côté écran.** Les deux écrans envoient eux-mêmes `["x"]`, ce qui court-circuite l'héritage :
  - `__dzSendSched`, sortie du maillon `libsend` (au milieu de la chaîne) : `post.channels=post.channels||["x"];` ;
  - le composant Planificateur d'origine (fonction `A`, « Nouveau post ») : `channels:["x"]` dans
    `D.createScheduledPost({...})`.

  Ces deux ancres sont uniques dans le bundle (mesuré le 26/10). Elles sont **hors de tout bloc de couche** : la
  seconde est à l'offset 1 019 704, avant SONVFX (1 226 220). La première vient d'un maillon antérieur ; on la remesure
  à l'étape 1.
- **Un maillon de queue neuf, `dzcanauxpre`, posé après `dzassistant` (t308).**
  - Il retire ces deux défauts. Un appelant qui passe des canaux explicites les garde.
  - L'éditeur s'ouvre déjà sur le post créé (`deepotus:select-post`, `u(T.id)`). `DzPostComptes` montre donc les
    comptes hérités cochés, avec la pastille « non vérifié » de t308 s'il y a lieu.
  - Ce maillon remplit le « de façon visible » de la tâche.
- **Le texte de la boîte « Canaux » (t307) change.** `projets.canaux.explication` dit encore que « Envoyer vers » et le
  Planificateur gardent leurs propres canaux ; il faut l'élargir. Ce texte vit dans `frontend/shared/i18n/projets.json`
  et il est lu par le script partagé `dz-projet-canaux.js` : rien à faire dans la couche montage. Le catalogue de
  l'agent suit.

**Tech Stack :** SPA patchée par une chaîne de maillons (bundle `frontend/dist/assets/index-BEOJX8L5.js`, en octets,
CRLF) ; `dzT` ; bancs autonomes ; Python embarqué.

**Spec :** `docs/superpowers/specs/2026-10-25-boite-a-outils-design.md` §5.4 (note « Livré en t307 »).

**Base :** la branche part de `chantier/boite-assistant-espace` (t308, ec211e85) et non d'origin/main. Les deux lots
posent un maillon de queue et une tête d'inverse : chaîner `dzcanauxpre` après `dzassistant` évite un conflit. Il faut
donc fusionner t308 avant t325.

## Global Constraints

- Le bundle `frontend/dist/assets/index-BEOJX8L5.js` n'est jamais reconstruit.
  - Il ne change que par `scripts/patch_bundle_dzcanauxpre.py`, lu et écrit en **octets** (CRLF), sans fin de ligne
    dans une paire.
  - Le fichier `.js.bak_dzcanauxpre` est supprimé après écriture. `version` reste le dernier maillon.
  - L'inverse `avant_dzcanauxpre` vit dans `backend/tests/_i18n_l1_aide.py`. Il lit les paires du maillon et il est
    appelé **en tête** de `avant_dzassistant`.
  - L'aller-retour `defaire(appliquer(B)) == B` se fait à l'octet.
- Aucune édition dans un bloc `/*__DZ_*_BEGIN__*/ … END`. Si une ancre y tombe : BLOCKED.
- Aucun `x.useState(` ajouté. Les comptes figés des bancs (v2.8.0 ×4, DzTracks 181, confirmations ×30, useState 731)
  restent intacts.
- Les canaux explicites d'un appelant passent tels quels. Seul le défaut `["x"]` posé par l'écran disparaît. Le
  serveur ne change pas.
- `frontend/shared/*` reste identique à l'octet à `frontend/dist/shared/*`. Les textes s'écrivent en FR et en EN dans
  `frontend/shared/i18n/*.json`, assemblés par `scripts/i18n_assembler.py`, et `test_i18n_l0` 2.4 est respecté.
- Les bancs sont des scripts autonomes lancés depuis `backend/` avec
  `"$LOCALAPPDATA/DeepotusVideoGen/runtime/python/python.exe"`, `PYTHONUTF8=1` et `sys.path.insert`. Ils ne touchent
  **jamais** le réseau.
- Ne jamais toucher le port 8765. Ne pas toucher le worktree deepotus-mobile-l4. Ne jamais pousser.
- Les 8 bancs rouges connus de la série (espaces_biblio_depenses, _client, _contenus, _guide, _studio, _textes,
  i18n_l6, icones_g1) le sont déjà sur la base. On compare donc les rouges à la base, et aucun ne doit être nouveau.

## Review Focus

1. **Canaux explicites.** Un appelant de `__dzSendSched` qui fournit `post.channels` (par exemple `["telegram"]`) les
   garde. Seul un tableau absent ou vide part sans `channels`. Banc 1.4.
2. **Projet actif sans canal.** Le post vise X comme avant, sans erreur ni toast d'échec. C'est le repli serveur, déjà
   couvert par t307 ; le banc 1.6 le rejoue par la route.
3. **Compte du projet supprimé ou passé dans un autre espace.** Le post est quand même créé, sur les comptes restants
   ou sur X. La garde t307 le couvre ; on le vérifie par la route en 1.6.
4. **Espace du post.** Un « Nouveau post » créé dans l'espace B prend le projet actif de B, jamais celui de Deepotus.
   Banc 1.6 (route avec `X-Dz-Espace`).
5. **Rien n'est dupliqué.** Retirer le défaut ne double pas un champ de l'objet envoyé et ne casse pas les autres champs
   (`title`, `caption`, `run_at`, `status`, `mode`). Les sondes node 1.2 et 1.3 lisent l'objet réellement passé à
   `D.createScheduledPost`.

---

### Task 1 : le maillon `dzcanauxpre` (t325)

**Files :**
- Create : `scripts/patch_bundle_dzcanauxpre.py`
- Create : `backend/tests/test_canaux_preremplis.py`
- Modify : `backend/tests/_i18n_l1_aide.py`, avec `avant_dzcanauxpre` en tête de `avant_dzassistant`
- Modify : `frontend/dist/assets/index-BEOJX8L5.js`, par le maillon seulement
- Modify : les bancs qui lisent la sortie de `libsend` ou du composant Planificateur et qui doivent désormais la voir
  « avant le maillon aval ». On suit le patron de t308, où `test_agent_planificateur` compare à `avant_dzassistant(B)`.
  On les trouve avec `rg 'channels\|\|\[|Untitled post|avant_dzassistant' backend/tests`.

**Interfaces :**
- Consumes : la chaîne de maillons. Le marqueur de `patch_bundle_dzassistant` (`MARKER`) sert de sonde de précédence.
- Produces :
  - `patch_bundle_dzcanauxpre.MARKER`, `PAIRES`, `appliquer(bundle: bytes) -> bytes` et `defaire(bundle: bytes) ->
    bytes`, suivant la même forme que `patch_bundle_dzassistant` ;
  - `avant_dzcanauxpre(bundle: str) -> str` dans `_i18n_l1_aide.py`.
- Paires, à reprendre telles quelles (vérifier leur unicité à l'étape 1) :
  - **P1** (`__dzSendSched`) : `post.channels=post.channels||["x"];post.status="draft";` →
    `if(!(post.channels&&post.channels.length))delete post.channels;post.status="draft";`
  - **P2** (Planificateur › Nouveau post) : `title:"Untitled post",caption:"",channels:["x"],run_at:U.toISOString()` →
    `title:"Untitled post",caption:"",run_at:U.toISOString()`
  - Le `MARKER` est porté par l'une des deux sorties, sous forme de commentaire `/*dzcanauxpre*/` collé à la fin de la
    sortie P1. Sans fin de ligne.

- [ ] **Étape 1 : relevé.**
  - Mesurer l'offset des deux ancres. Écrire dans le docstring du maillon qu'elles sont hors de tout bloc
    `__DZ_*_BEGIN__`.
  - Vérifier que chaque ancre est unique (`count == 1`).
  - Lister les bancs que le changement fait rougir sur la sortie actuelle, puis lancer la série ciblée sur la base
    (ec211e85) et noter ses rouges.
- [ ] **Étape 2 : écrire `test_canaux_preremplis.py`.**
  - 1.1 Maillon posé : P1 et P2 sont appliquées, le marqueur est présent une fois, et plus aucun `channels:["x"]` ni
    `channels||["x"]` ne reste dans le bundle.
  - 1.2 Sonde node : on extrait `__dzSendSched` du bundle avec un faux `D.createScheduledPost` qui capture l'objet. Sans
    `post.channels`, l'objet n'a pas de clé `channels`. `status` vaut `draft`, `mode` vaut `assisted`, et `run_at` est
    une date ISO.
  - 1.3 Sonde node sur la fonction « Nouveau post », ou, si l'extraction est trop fragile, contrôle textuel exact de la
    sortie P2 : l'objet envoyé n'a ni `channels` ni de champ dupliqué. Dire dans le rapport laquelle des deux est
    faite.
  - 1.4 (Review Focus 1) `__dzSendSched({channels:["telegram"], …})` envoie `channels:["telegram"]`.
    `channels:[]` envoie un objet sans `channels`.
  - 1.5 `avant_dzcanauxpre(bundle)` rend la base à l'octet, et `avant_dzassistant(avant_dzcanauxpre(B))` reste
    cohérent avec la chaîne (même contrôle que t308).
  - 1.6 (Review Focus 2, 3, 4) Par la route `POST /api/schedule` sur des données temporaires (TestClient, sans réseau),
    avec un corps **identique** à ce que P2 envoie maintenant, c'est-à-dire sans `channels` :
    - le projet actif de l'espace B a deux comptes → le post a ces deux `comptes` et `channels` vaut leurs
      plateformes ;
    - aucun projet actif → `channels` vaut `["x"]` ;
    - un des comptes a été supprimé → le post est créé sur l'autre ;
    - l'en-tête `X-Dz-Espace: B` ne prend jamais le projet de Deepotus.
- [ ] **Étape 3 : lancer.** On attend un FAIL (le maillon est absent).
- [ ] **Étape 4 : implémenter** le maillon et l'inverse, sur le patron de `patch_bundle_dzassistant.py` : sonde de
  précédence, `--check`, `.bak` supprimé, appliqué une fois et refusé s'il est déjà posé. Lancer
  `python scripts/patch_bundle_dzcanauxpre.py`.
- [ ] **Étape 5 : lancer**
  - `test_canaux_preremplis` ;
  - `test_projets_canaux` ;
  - `test_espace_assistant_ecran` ;
  - `test_agent_planificateur` ;
  - les bancs trouvés à l'étape 1 ;
  - la série ciblée, en comparant ses rouges à la base.

  Mettre à jour, en suivant le patron « vu avant le maillon aval », les bancs qui comparent la sortie de libsend ou du
  Planificateur. Ne jamais affaiblir un contrôle : le déplacer seulement.
- [ ] **Étape 6 : mutations.** Remettre `||["x"]` dans P1, remettre `channels:["x"]` dans P2, et retirer le test de
  tableau vide. Le banc doit attraper chacune des trois mutations.
- [ ] **Étape 7 : commit.** `planificateur : brouillons préremplis avec les canaux du projet actif (t325)`.

### Task 2 : textes de la boîte « Canaux », catalogue de l'agent, preuve à l'écran (t325)

**Files :**
- Modify : `frontend/shared/i18n/projets.json` (`projets.canaux.explication`, FR et EN), puis
  `python scripts/i18n_assembler.py`
- Modify : le catalogue de l'agent (skill `connaissance-agent`) : la fiche de la boîte « Canaux » et, si elles existent,
  les fiches « Nouveau post » du Planificateur et « Envoyer vers › Planificateur » de la Bibliothèque
- Test : `backend/tests/test_canaux_preremplis.py` (section 2)

**Interfaces :**
- Consumes : la tâche 1, le maillon posé.
- Produces : un texte neuf pour `projets.canaux.explication`. Le sens à rendre, en FR :
  « Quand ce projet est actif, les comptes cochés deviennent la cible par défaut de tout ce qui se crée : brouillons de
  l'assistant, Nouveau post du Planificateur et Envoyer vers › Planificateur. Vous pouvez les décocher dans l'éditeur
  du post. Sans canal coché, X reste la cible. » L'EN dit la même chose. L'implémenteur peut resserrer la phrase sans
  en changer le sens.

- [ ] **Étape 1 : banc 2.1.** Le texte FR ne contient plus « gardent les canaux » et nomme le Planificateur. Le texte EN
  existe et ne contient pas de français. Lancer pour voir le FAIL.
- [ ] **Étape 2 : écrire les textes.** Les assembler, vérifier que shared et dist/shared sont identiques, puis relancer
  2.1, `test_i18n_l0` et les bancs i18n de projets (`rg "projets.canaux" backend/tests`).
- [ ] **Étape 3 : catalogue.** Passer par la skill `connaissance-agent`. `catalogue.py --check` et les bancs agent
  doivent rester verts.
- [ ] **Étape 4 : preuve à l'écran, en FR puis en EN.**
  - Lancer un backend de preuve sur un port libre (pas 8765), avec des données temporaires et sans clé réelle.
  - Préparer un espace avec deux comptes et un projet actif dont ce sont les canaux. Comme les comptes n'ont pas de
    clés, leur pastille sera « non vérifié » ou orange, ce qui convient.
  - Faire « Planificateur › Nouveau post » : l'éditeur s'ouvre avec les deux comptes cochés et X n'est pas coché.
  - Faire « Bibliothèque › Envoyer vers › Planificateur » sur un média de démonstration : même résultat.
  - Ouvrir la boîte « Canaux » pour montrer le texte neuf.
  - Aucun appel réseau réel. Arrêter le backend après la preuve.
  - Captures dans `docs/superpowers/specs/assets/2026-10-26-t325/`.
- [ ] **Étape 5 : spec.** Dans §5.4, ajouter une phrase « *Livré en t325 (26/10/2026)* » après la note t307 : les deux
  écrans préremplissent maintenant les canaux du projet actif, et le filtre du Planificateur ainsi que la pastille
  d'espace du sélecteur restent à faire.
- [ ] **Étape 6 : commit.** `projets : la boîte Canaux dit que les écrans de création suivent le projet actif (t325)`,
  avec un commit à part pour le catalogue si la skill l'impose.
