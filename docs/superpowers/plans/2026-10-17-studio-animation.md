# Plan — lot « Studio : Animation » (17/10/2026)

**Spec :** `docs/superpowers/specs/2026-10-17-studio-animation-releve.md` (relevé daté, licence, options), complétée
par `docs/superpowers/specs/2026-10-18-studio-animation-personnalisation.md` (personnalisation et effort, tableau P1-P9).

**Statut.** t231 est fait sur la branche `claude/studio-animation-06e533`, non poussée.

**t232-t238 sont À LANCER.** L'utilisateur a tranché le 17/10 (§ B5 de la spec) en retenant les trois recommandations :

- Q1 : **A puis B** ;
- Q2 : **(iii) mixte**, le nœud « Direction motion » ;
- Q3 : **(a)** fiches maison + imports + skills.

t238 (B) attend toujours une seconde validation, après t234.

**18/10.** t232-t235 sont faits (t234 : PR #381 ; t235 : commit local 42cb17bf). L'utilisateur a validé le tableau
d'écart P1-P9 de la spec du 18/10 et demandé d'insérer ses tâches AVANT t236 : **t239** (effort des moteurs),
**t240** (personnalisation côté chorégraphe), **t241** (rubrique « Personnaliser » du nœud). Nouvel ordre :
t239 ∥ t240 → t241 → t236 → t237.

---

## Règles communes (tout le lot)

**Base et méthode.**

- Partir d'`origin/main` à jour (`git fetch origin`), une session neuve par tâche.
- Commit par `git commit --only`.
- Pas de push, de PR, de fusion ni d'installation sans accord explicite de l'utilisateur.

**Bundle.** Il n'est modifié QUE par la chaîne de patchers. Lecture et écriture en OCTETS (CRLF). Le blob git est en
LF : le reconvertir en CRLF avant de comparer.

- Le maillon de queue actuel est `scripts/patch_bundle_dzstudio.py` (PAIRES = AB + C + F + D + E + G).
- Le lot ouvre un **maillon de queue neuf `dzmotion`**, posé APRÈS dzstudio dont il sonde le marqueur :
  - son inverse `avant_dzmotion` est appelé EN TÊTE de `avant_dzstudio` dans `backend/tests/_i18n_l1_aide.py` ;
  - `version` reste le dernier maillon.
- Régénérer = défaire avec le patcher de HEAD, puis appliquer le neuf.
- Un banc qui fige « sa famille en fin de PAIRES » est borné à ses propres familles.

**Comptes figés.** Le lot ajoute des `useState` (nœuds neufs) : on pose de nouveaux comptes, chiffrés et justifiés
dans le banc du maillon. Restent intouchables :

- v2.8.0 ×4 ;
- DzTracks 181 ;
- `scripts/dzglyph_paires.json` ;
- le littéral Fu.

**Textes.** Une phrase FR visible = une clé dzT (FR + EN), dans les dictionnaires et par le générateur L1/L6 du lot.
Aucune chaîne en dur dans les paires (banc K, comme t230). Clés `studio.motion.*`.

**Licence (spec § B3).** Ces contenus n'entrent JAMAIS dans le dépôt :

- aucun texte de prompt de prompt-motion.com ;
- aucune vidéo, aucune capture, aucune liste de leurs entrées.

Les imports de l'utilisateur et les skills installés vivent dans `DEEPOTUS_DATA_DIR/motion/`, avec leur attribution et
leur LICENSE. Banc de garde : grep du dépôt sur les titres et les pseudos relevés → 0.

**Moteurs.** Toujours le registre `moteurs_texte`, jamais un fournisseur codé en dur. L'appel passe sous les plafonds de
dépense ; une estimation est faite AVANT l'appel ; Ollama / local = gratuit, fl = « prix à mesurer ». Sans moteur
configuré, ce n'est pas une erreur : un repli déterministe fonctionne.

**Sécurité.** Une sortie de modèle est une DONNÉE :

- JSON validé par schéma, bornes sur chaque nombre, textes tronqués ;
- jamais évaluée ;
- une URL d'image rendue par un modèle n'est jamais téléchargée.

En B (t238), le code produit ne tourne que dans le bac à sable décrit là.

**Bancs.** Banc neuf ROUGE sur la base, puis VERT. Mutations : copier les sources AVANT, `cmp` APRÈS, lancer avec
`PYTHONIOENCODING=utf-8`.

**`run-tests.ps1` complet en fin de tâche.** Rouges préexistantes, au nombre de 11 :

- i18n_l4_serveur ;
- icones_g1 ;
- icones_g4 ;
- library_lignee ;
- montage_bundle (DZ3) ;
- montage_l5_masque ;
- p1_cle_absente ;
- photolab_reglages_moteur ;
- plan_brief ;
- style_da ;
- transfert_integrite.

Un worktree neuf n'a pas `vendor/photocraft-0.3.0` : le copier depuis un autre worktree avant de lancer la suite.

**Preuve.** Au VRAI clic, FR puis EN, sur un backend de preuve :

- python embarqué ;
- `DEEPOTUS_DATA_DIR` jetable ;
- JAMAIS le port 8765.

Pour la largeur, Edge sans fenêtre par CDP (`cdp.py`, `dz_onboarded=1`, `dz_lang=en`). Les moteurs sont simulés par de
faux serveurs (Ollama, fl) : aucune dépense réelle sans accord.

**Mise en place d'un nœud.** La palette ne dépose un nœud que par glisser-déposer HTML5. Pour la mise en place
seulement : `drop` en JS. Tous les gestes jugés se font par de vrais clics.

---

## Tâches

### t231 — Animation : le Preset agit sur l'élément (réparation) — FAIT (branche, non poussée)

Cause et correctif : spec § A.

- Famille G* (G1 applyPreset → keyframes + `dzPresetDe` ; G2 menu dérivé) dans dzstudio.
- Banc `test_studio_animation_preset` 34/34, 12/12 mutants tués.
- Preuve FR/EN au vrai clic et dans le MP4 du rendu backend.

**Installation (après accord)** : le bundle et `scripts/patch_bundle_dzstudio.py` seulement. Aucun Python applicatif
n'est touché : pas de relance, un rechargement forcé suffit.

### t232 — Moteur commun « tirer un texte » (backend, S)

Extraire de `vector_illustration.tirer` un `moteurs_texte.tirer(moteur, modele, prompt, systeme, max_tokens, json=False)`
utilisable hors Vectorlab :

- même ordre de moteurs, mêmes gardes (modèle sain, plafonds, estimation) ;
- le Vectorlab l'appelle sans changement de comportement (banc de non-régression du Vitrail).

Exposer `GET /api/motion/moteurs` = `etat()` + bulle de coût, comme `mod-ia.js`.

Banc avec faux Ollama et faux fl, mutations.

### t233 — Bibliothèque motion : styles maison, imports, skills (backend, M)

`DEEPOTUS_DATA_DIR/motion/` et `services/motion_biblio.py`. Trois sources :

1. **Fiches de style maison**, livrées dans le dépôt (`backend/app/motion/styles/*.json`) :
   - une par thème : kinetic type, product UI, charts, diagrams, shapes, particles, characters, photos, phone, code,
     music ;
   - **rédigées par nous** ;
   - contenu : consigne de style, rythme, easings privilégiés, presets autorisés, durée type, formats.
2. **Imports de l'utilisateur** (nature `prompt`) :
   - champs : titre, texte collé, URL de la fiche, auteur, thèmes ;
   - enregistrés dans les données, jamais dans le dépôt ;
   - attribution obligatoire (URL non vide).
3. **Skills** (nature `skill`) :
   - installés À LA DEMANDE depuis un dépôt GitHub public (`owner/repo[:chemin]`) : téléchargement de SKILL.md + LICENSE
     seulement, refus sans LICENSE reconnue (MIT / Apache-2.0 / BSD / ISC) ;
   - le texte d'origine est gardé, une copie éditable `consigne` est créée, « Revenir à l'original » est possible.

Routes : `GET/POST/PATCH/DELETE /api/motion/biblio`, `POST /api/motion/skills/installer`.

Gardes :

- taille ;
- hôte github.com / raw.githubusercontent.com seulement ;
- aucune exécution des scripts d'un skill (on ne lit que du Markdown).

Bancs : licence refusée, attribution manquante, chemin hors dossier, grep anti-contenu tiers dans le dépôt.

### t234 — Chorégraphe : script + style + source → éléments du nœud Animation (backend, M) — option A

`POST /api/motion/choregraphier`. Il reçoit :

- `{script, direction:{style, source, consigne}, moteur, modele, aspect, duree_s, marque}`.

Il rend :

- `{elements:[…], moteur, modele, cout}`.

Fonctionnement :

- le prompt système impose un **schéma JSON** :
  - types text / sticker / image(filename déjà présent seulement) ;
  - x / y 0-100, scale 0,1-4, rotation ±720, opacity 0-1 ;
  - easings connus ou cubic-bezier, presets de la liste PRESETS ;
  - au plus 24 éléments et 8 clés par élément ;
- la sortie est validée, bornée et réparée (clés triées, t dans 0..1). Si elle est invalide, une seconde tentative, puis
  le **repli déterministe** : une ligne de script = un élément texte, avec les presets du style et un découpage du temps
  proportionnel aux mots ;
- les couleurs et la police viennent du kit de marque de l'espace actif.

Banc :

- faux moteur rendant du JSON valide, invalide, piégé (URL, script, nombres hors bornes) ;
- repli ;
- mesure par `transform_at` que le rendu suit la chorégraphie.

### t235 — Nœud « Direction motion » + entrées `direction` / `script` de l'Animation (bundle, maillon neuf `dzmotion`, L)

**Option (iii).**

**Le nœud « Direction motion »** (catégorie Animations, sortie `direction`) :

- **Style** : liste des fiches maison, par thème ;
- **Source** :
  - « Aucune » ;
  - un **prompt** de la bibliothèque (lecture seule, lien vers la fiche d'origine) ;
  - un **skill** : sélection, et **édition de sa consigne directement dans le nœud** (zone repliable, « Revenir à
    l'original », compteur de caractères) ;
- **Moteur** : sélecteur commun (moteur + modèle + bulle de coût), comme `mod-ia.js` ;
- son encart montre style, source et moteur en une ligne.

**Le nœud Animation** gagne deux entrées :

- `direction` ;
- `script` (type text : Texte, Prompt, Script News…).

L'inspecteur gagne un bouton **« Chorégraphier »**. Il appelle t234 et remplace les éléments, après confirmation s'il
y en a déjà ; Ctrl+Z revient à l'état d'avant. Un champ « Script » sert quand l'entrée `script` n'est pas reliée.

Les ports suivent `dzPortGeo` / `dzPortBodyH` (t225-t227) : le banc d'ancrage est rejoué sur les nouveaux nœuds.

Bancs :

- extraction des vraies fonctions sous node : compilation du graphe → payload de t234 ;
- la consigne éditée part bien dans l'appel ;
- chaîne dzmotion (sans = base octet pour octet, inverse, comptes) ;
- banc K.

### t239 — Effort du modèle : `moteurs_texte` et `GET /api/motion/moteurs` (backend, M) — spec 18/10 § P7

`moteurs_texte.tirer(…, effort=None)` et `tirer_garde(…, effort=None)` :

- `None` / `"auto"` = rien n'est envoyé (le défaut du modèle s'applique) ;
- sinon le niveau est traduit par fournisseur, seulement si CE modèle l'accepte :
  - Anthropic : `output_config.effort` (`low`/`medium`/`high`/`xhigh`/`max` ; `xhigh` à partir d'Opus 4.7 ;
    Haiku 4.5 et les modèles antérieurs le refusent) ;
  - OpenAI, Gemini, Ollama et serveurs locaux, fournisseurs libres : relever la documentation à jour de chacun
    (paramètre, valeurs, modèles concernés) AVANT d'écrire, sans rien supposer ; un fournisseur sans réglage
    connu n'expose que « Auto ».
- Un niveau non accepté n'est JAMAIS envoyé : il retombe sur « Auto », et la réponse le dit (`effort_applique`).
- `estimer(…, effort)` : la sortie maximale estimée croît avec l'effort ; l'estimation reste faite AVANT l'appel,
  sous les plafonds.

`GET /api/motion/moteurs` ajoute, par moteur, `efforts` (les niveaux possibles pour le modèle par défaut) ; une route
`GET /api/motion/moteurs/efforts?moteur=&modele=` donne ceux d'un modèle précis. Le Vectorlab et les autres appelants
gardent leur comportement (effort absent = inchangé, banc de non-régression).

Bancs : faux serveurs par fournisseur (corps reçu : niveau présent ou absent), refus d'un niveau non accepté,
estimation par niveau, non-régression du Vitrail, mutations.

### t240 — Personnalisation côté chorégraphe : champs des fiches, précisions, curseurs, tempo (backend, L) — § P1-P6, P8

Sur la base de t234 (`motion_choregraphe`) et t233 (`motion_biblio`) :

- **P1 — Fiches maison à champs.** Les 11 fiches (écrites par nous) déclarent `champs` : id, libellé FR/EN, aide
  FR/EN, défaut, type texte / nombre / liste, bornes. Leur consigne cite `{{id}}`. `direction.champs` de la requête
  est substitué (vide ou absent → défaut ; texte tronqué, nombre borné, id inconnu ignoré).
- **P2 — Bloc de précisions.** Pour un prompt importé ou un skill : `direction.precisions` (à quoi ça sert, durée,
  couleurs, police, autre chose) est ajouté APRÈS la consigne, avec la règle « en cas de conflit, ces précisions
  priment ». Le texte importé n'est pas modifié.
- **P3 — Tempo.** `tempo_bpm` (40-220, facultatif) : le prompt système le donne ; la validation et le repli calent
  `start` sur les temps (au temps le plus proche, bornes respectées). Format et durée de la requête peuvent
  remplacer ceux du graphe.
- **P4 — Police / palette.** `marque` accepte déjà {couleur, marque, police} : les champs du nœud la remplacent.
- **P5 — Curseurs.** `direction.curseurs = {creativite, rythme, finition}`, entiers 0-4, 2 = neutre. Créativité et
  Rythme ajoutent une phrase de consigne écrite par nous (FR/EN, fichier de données du dépôt) en fin de direction.
  Finition, en option A : 0-1 → une seule tentative avant le repli ; 3-4 → une passe de vérification de plus
  (bornes, lisibilité : pas deux textes au même endroit au même instant, tenue minimale) avant de rendre les éléments.
- **P6.** Rien n'est demandé à l'utilisateur pendant l'appel (les champs du nœud jouent ce rôle).
- `GET /api/motion/biblio/{id}` d'une fiche rend ses `champs` ; les phrases des curseurs sont exposées par une route
  de lecture pour l'écran.

Bancs : substitution (défaut, borne, id inconnu), bloc de précisions (ordre, règle de priorité, texte d'origine
intact), tempo (starts sur les temps), curseurs (phrase présente / absente au neutre, tentatives selon la finition),
garde G3 (nos phrases n'empruntent rien au catalogue), mutations.

### t241 — Rubrique « Personnaliser » de Direction motion (bundle, maillon dzmotion, L) — § P1-P5, P7, P8

Dépend de t235, t239 et t240.

- Rubrique « Personnaliser » générée depuis les `champs` de la fiche choisie : libellé, aide d'une ligne, défaut en
  texte d'exemple (champ vide = défaut).
- Pour un prompt ou un skill : le bloc de précisions (5 champs), avec l'aperçu de la règle « mes précisions priment ».
- Trois curseurs à 5 crans (Créativité, Rythme, Finition) ; le libellé de l'état et la phrase ajoutée sont montrés.
- Tempo (BPM), remplacements facultatifs du format, de la durée, de la police et de la palette (kit de marque par
  défaut).
- **Effort** : sélecteur à côté du modèle, « Auto » puis les niveaux que ce moteur et ce modèle acceptent (t239) ; la
  bulle de coût le mentionne.
- « Reprendre mes précisions » (P8) : copie celles du dernier nœud Direction motion du graphe.
- `dzMotionPayload` envoie `champs`, `precisions`, `curseurs`, `tempo_bpm`, `effort` et les remplacements.
- Une phrase = une clé dzT `studio.motion.*` FR + EN (motion.json) ; hooks par l'alias `dzMoUS` (HOOKS chiffré) ;
  ports et ancrage inchangés.

Bancs : sous node, vraies fonctions (payload complet, champ vide = défaut, effort non proposé quand le modèle ne
l'accepte pas), chaîne dzmotion, banc K. Preuve FR/EN au vrai clic : un champ, un curseur et l'effort modifient le
corps envoyé et la chorégraphie produite (faux moteur qui renvoie ce qu'il reçoit), MP4 conforme.

### t236 — Bandeau de bibliothèque motion dans l'inspecteur (bundle, M)

Rubrique « Bibliothèque motion » de l'inspecteur de « Direction motion » :

- **importer un prompt** : formulaire titre / texte / URL / auteur / thèmes, avec l'attribution affichée ;
- **installer un skill** : saisie `owner/repo[:chemin]` ; la licence lue est montrée AVANT l'installation ;
- **lister, filtrer par thème, supprimer**.

Rien ne part sur le réseau sans un clic.

Depuis t241 : le formulaire d'import montre aussi l'aperçu du bloc de précisions (spec 18/10 § P2).

Preuve : l'import puis la sélection modifient la chorégraphie produite (faux moteur qui renvoie la consigne reçue).

### t237 — Traduction et guide (S)

- Clés FR/EN de t232-t236 (banc K étendu à dzmotion).
- Section « Animer avec l'IA » du chapitre Studio, avec le skill guide-deepotus :
  - scènes à trois temps : Direction motion → Chorégraphier → aperçu ;
  - encadré licence : « les prompts restent à leurs créateurs ».
- Guide FR / EN et PDF reconstruits.

### t238 — Option B « Motion code » (L, À TRANCHER APRÈS t234)

Ne se lance que si l'utilisateur la confirme, après avoir vu la qualité de A.

**Nœud « Rendu motion code ».** Le moteur écrit une page HTML / SVG / Canvas (durée, fps, taille imposées). Elle est
rendue en MP4 par Edge sans fenêtre, image par image (CDP, horloge virtuelle).

**Bac à sable** :

- page en `data:` sans réseau ;
- CSP `default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:` ;
- profil jetable ;
- délai de 120 s et 10 Mo au plus ;
- aucun accès fichier.

**Sortie** `av`, utilisable en `base` de l'Animation ou en entrée du Rendu.

**Coût** : estimé AVANT l'appel, plafond.

**Bancs** : page piégée (fetch, top.location, boucle infinie) → refus ou arrêt propre.

---

## Ordre et dépendances

```
t231 (fait) ─┐
t232 ── t233 ── t234 ── t235 ──┐
                 │              ├── t241 ── t236 ── t237
                 ├── t239 ──────┤
                 └── t240 ──────┘
                 └──────────────────────────────────── t238 (à trancher)
```

- t232 et t233 sont indépendants l'un de l'autre et peuvent tourner en parallèle (fichiers disjoints).
- t234 dépend des deux.
- t235, t241 et t236 touchent le bundle : ils passent un à la fois, dans cet ordre.
- t239 (moteurs_texte, routes) et t240 (motion_choregraphe, motion_biblio, fiches) ont des fichiers disjoints : ils
  peuvent tourner en parallèle, chacun dans sa session.

## Preuves attendues par tâche

| Tâche | Preuve |
|---|---|
| t232 | appel réel au faux Ollama et au faux fl ; le Vitrail inchangé (FR / EN) |
| t233 | installation d'un skill MIT depuis un faux miroir GitHub local ; refus d'un dépôt sans licence ; import d'un prompt avec attribution |
| t234 | MP4 rendu depuis une chorégraphie (positions mesurées, comme t231) ; repli sans moteur |
| t239 | corps reçus par les faux serveurs : niveau d'effort présent quand accepté, absent sinon ; Vitrail inchangé |
| t240 | chorégraphie d'une fiche à champs remplis, curseurs et tempo (starts sur les temps, mesurés) ; bloc de précisions |
| t241 | au vrai clic FR / EN : champ, curseur, tempo et effort changent le corps envoyé et la chorégraphie → MP4 conforme |
| t235 / t236 | au vrai clic FR puis EN : Direction motion → Chorégraphier → éléments dans la liste → Exécuter → MP4 conforme ; consigne de skill éditée → payload modifié |
| t237 | guide FR / EN, scènes, PDF |
