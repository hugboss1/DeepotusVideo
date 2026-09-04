# Montage — reprise à la tâche 6 (P5, projets nommés)

> **Pour l'agent qui ouvre cette session :** tu reprends l'exécution du plan
> `2026-09-03-plan-montage.md` à sa **tâche 6**. Les tâches 1 à 5 sont livrées,
> revues deux fois chacune et commises. Ce document te donne l'état du terrain,
> les conventions, les pièges déjà payés, et ce que la méthode a coûté et
> rapporté — pour que tu ne les redécouvres pas.
>
> **REQUIRED SUB-SKILL** : `superpowers:subagent-driven-development` — un
> sous-agent frais par tâche, puis **deux revues** (conformité d'abord, qualité
> ensuite), et une boucle de correction jusqu'au vert sur chacune.

---

## Où en est le chantier

Worktree `C:\Users\olivi\DeepotusVideo\.claude\worktrees\nervous-chandrasekhar-82b3df`,
branche `claude/sad-chaum-c3f949`, assise sur `main` = `11e0897`. Arbre propre.
**Ne travaille que dans ce worktree** ; d'autres sessions Claude occupent les
autres. **Jamais `git stash`** (pile partagée).

| commit | tâche |
|---|---|
| `a485011` + `58c37df` | **P0** — la musique ne s'arrête plus à la dernière syllabe de la voix |
| `57ff7d0` | **P1** — pistes dynamiques, leur ordre décide du rendu |
| `ffcd7d9` | **P2** — sous-titres animés mot par mot, emoji du mot-clé |
| `3caed24` | **P3** — monter par le texte, couper une plage de temps |
| `1d0859a` | **P4** — étalonnage de base sous la LUT |

En amont, `a8c4abd` porte le balayage et l'index des dix-sept plans.

**Ta tâche** : `docs/superpowers/plans/2026-09-03-plan-montage.md`, **lignes 635
à 707** (tâche 6, P5 — projets nommés : liste, ouvrir, dupliquer, renommer).
Restent ensuite les tâches 7 (l. 708), 8 (l. 731), puis le lot différenciant
9 à 13 (l. 821 à 1122) et la campagne de mutations (l. 1131).

## Les bancs, et leur compte au moment du passage de relais

Tous **autonomes** : un processus par fichier, lancés depuis `backend/`.

```powershell
$PY = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"
Set-Location backend
& $PY tests\test_montage_pistes_rendu.py     #  33 passed, 0 failed
& $PY tests\test_montage_pistes_dyn.py       #  20 passed, 0 failed
& $PY tests\test_subs_animes.py              #  65 passed, 0 failed
& $PY tests\test_montage_texte.py            # 113 passed, 0 failed
& $PY tests\test_montage_etalonnage.py       #  22 passed, 0 failed
& $PY tests\test_montage_bundle.py           # 141 passed, 0 failed
```

**Jamais `pytest tests`** en bloc. `test_subtitle_service.py`,
`test_subs_normes_api.py` et `test_transcribe_service.py` sont de style pytest
et ne tournent pas en script : `python -m pytest tests\<fichier>.py -q`, fichier
par fichier.

## Interdits absolus

- **Ne lance JAMAIS le backend** : ni `launch.ps1`, ni `launch-silent.vbs`, ni
  `uvicorn`, ni `python -m app.main`. C'est l'utilisateur qui relance
  l'application installée dans `%LOCALAPPDATA%\DeepotusVideoGen`.
  `fastapi.testclient.TestClient` **est** autorisé : il n'ouvre aucun port.
- **Ne lance JAMAIS `scripts/run-tests.ps1`** (26 minutes).

## La chaîne de patch — le piège le plus cher du dépôt

`frontend/patches/son-vfx-montage.js` **ne se rafraîchit pas**. Mesuré : le bloc
correspondant du bundle porte les remplacements V3/V4/V6/V8/V9 de
`patch_bundle_vfxrack.py` et S3…S17 de `patch_bundle_subs.py` — **vingt
sections** que cette copie ne sait pas rejouer (`.bak_vfxrack` et `.bak_subs`
sont gitignorés et absents, et l'ancre V10 est déjà consommée). Relancer
`patch_bundle_sonvfx.py` les effacerait sans retour.

Toute l'interface nouvelle vit donc dans **une couche neuve** et **un patcher
neuf**, en queue de chaîne :

| élément | état |
|---|---|
| couche | `frontend/patches/montage.js` — `window.DzTracks` |
| patcher | `scripts/patch_bundle_montage.py` — tag `montage`, `.bak_montage`, **13 ancres** (M1-inject + M3…M13) |
| feuille | `frontend/dist/shared/montage.css`, liée après `subs.css` |
| miroir | `backend/tests/test_montage_bundle.py` |

Après toute édition de la couche ou du patcher :
`& $PY scripts\patch_bundle_montage.py --check` puis sans `--check` ;
`& $PY scripts\repatch_all.py --list` doit finir par `montage OK` ;
`test_montage_bundle` doit rester vert, **`bloc_EST_la_couche_octet_pour_octet`
compris**. Chaque ancre doit valoir **exactement 1** avant écriture — le patcher
abandonne sans écrire sinon, et il l'a réellement fait une fois (P3).

**Deux gardes que les tâches précédentes ont posées et qu'il faut respecter :**
- la couche ne doit **citer aucune ancre du patcher**, même en commentaire — le
  commentaire finit dans le bundle et l'ancre s'y compte deux fois. Un contrôle
  général le vérifie pour les treize.
- `node --check` sur le `.js` lit en sémantique **script** : il ne voit pas une
  double déclaration au premier niveau. Le bundle est chargé en `type="module"`,
  où c'est une `SyntaxError`. L'assertion `node_check_module` existe pour ça.
  **Vérifie qu'un nom neuf est libre** : `DzMontage` est le composant du bundle.

## Les cinq fautes que ce chantier a payées — ne les refais pas

1. **Un chiffre non mesuré, ou mesuré sous un protocole non nommé.** Coût :
   trois tours sur P0, deux sur P2, trois sur P4. Cas d'école : une durée citée
   de mémoire qui n'était même pas déterministe (la même commande rendait trois
   valeurs) ; un écart de couleur qui mesurait la perte du codec et non le
   filtre — démontré en passant le **témoin** dans le même protocole ; une
   taille de vignette republiée sans être refaite après une correction qui la
   changeait. **Nomme le protocole dès qu'un chiffre en dépend.**
2. **Une assertion qui reste verte quand on supprime ce qu'elle teste.** Une
   douzaine trouvées, dont plusieurs par les implémenteurs eux-mêmes. Formes
   récurrentes : comparaison à une liste ou un dict vide, `all()` sur du vide,
   comparaison par sous-chaîne alors que le nom muté contient l'ancien,
   comparaison de deux résultats l'un à l'autre au lieu d'un littéral, et un
   `detail` évalué **avant** l'appel qui fait **mourir** le banc au lieu de le
   faire rougir. **Prouve chaque assertion par mutation, et dis si elle rougit
   seule.**
3. **Une correction qu'aucun test n'exerce.** Elle ne vaut pas mieux qu'une
   affirmation non mesurée.
4. **Un geste destructif sans retour.** P1 laissait retirer la piste de
   sous-titres en un clic, emportant tout le sous-titrage, sans moyen de la
   recréer. `pushHistory()` avant, une seule entrée pour un lot, et **dis dans
   la note ce que « annuler » ne restaure pas** (l'historique ne mémorise que
   `{clips, mixDb}` : pas `proj.dur`, pas les pistes).
5. **Le code du plan est une intention, pas une vérité.** Ancres qui n'existent
   pas, seuils qui discriminent à marge nulle, fonction prise dans le mauvais
   module, branche qui met une piste à durée nulle. **Mesure, adapte, et
   déclare l'écart.**

## Ce que la méthode a rapporté, pour que tu la tiennes

Les revues n'ont pas seulement poli du style. Elles ont trouvé, sur cinq
tâches : un banc qui nommait un ducking qu'il n'exerçait pas (on pouvait
supprimer la fonction entière sans une rougeur) ; une piste de sous-titres
supprimable sans retour ; des identifiants de clip en double sur le **geste
principal** d'une tâche, alors que l'interface sélectionne et écrit par
identifiant ; un ordre de filtres qui faisait qu'un curseur « saturation » à
zéro rendait du sépia ; un bouton qui écrivait sur la mauvaise piste ; un banc
qui pouvait bénir un bundle n'exécutant pas la couche qu'il mesure ; et une
inversion d'étiquettes dans un message de commit qui disait le contraire de ce
qu'il démontrait deux phrases plus haut.

**Trois fois, un agent a contredit sa revue avec des mesures, et il avait
raison les trois fois.** Encourage-le : demande de contester plutôt que
d'appliquer quand un point te paraît faux après mesure.

## Conventions de commit

Sujet **sans accents** (apostrophes permises), corps **accentué** en français,
pied `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. Jamais de
guillemets doubles dans un `-m` ; `git commit -F -` avec heredoc si long.
Densité d'accents des cinq corps livrés : 24, 132, 108, 163, 97 — un corps à
zéro a fait échouer une revue.

## La dette de vérification au navigateur — cinq lots en attente

Rien de tout cela n'est mesurable sans l'application démarrée **par
l'utilisateur**. Ne la lance pas ; consigne ce qui s'ajoute.

- **P1** : « + vidéo » / « + audio », les flèches ▲▼ au clavier et à la souris,
  la croix à deux temps sur une piste porteuse de clips, le **glisser-déposer**
  des en-têtes par la poignée, et la timeline qui grandit puis défile (à huit
  pistes, 426 px : la borne ne mord que sous une fenêtre d'environ 887 px).
- **P2** : la chip « mot : couleur / rebond / glow », le bouton emoji, et que
  **Ctrl+Z retire tous** les clips posés.
- **P3** : le panneau « Texte » dans la colonne d'inspection — sélection au
  clic-glissé, marquage des remplissages, « retirer les N hésitations », et le
  comportement clavier (les écouteurs sont là, node ne les évalue pas).
- **P4** : les quatre curseurs dans le rack VFX, la vignette d'aperçu, et le
  bouton « appliquer cet étalonnage à tous les plans » avec son libellé variable
  selon la piste.
- **Transverse** : la **largeur réelle** de la barre de transport et de la
  colonne d'inspection, qui ont reçu tous ces boutons sans qu'on ait pu les voir.

## Restes assumés, déjà déclarés — ne les rouvre pas sans raison

- Un **second clip** du bus musique prend le bon gain mais reste rangé dans les
  bruitages : ni bouclé, ni ducké.
- Le rapport de `_subs_ass` **ne quitte pas le serveur** : son seul lecteur est
  une ligne de journal que personne n'ouvre. Le panneau n'apprend donc rien
  d'une animation qui n'a pas eu lieu.
- Le **glow** n'est pas mesuré à l'image (sa surface se confondrait avec celle
  du rebond) ; seule sa balise est lue.
- Le repli hors ligne du catalogue d'effets de `vfxrack.js` liste **20** effets
  quand le moteur en sert **40**, et trois de ses six familles n'existent plus.
  Dérive **antérieure**, dans un maillon amont que cette chaîne ne rejoue pas :
  elle mérite sa propre tâche.
- `/subtitles/export?format=ass` ignore `word_anim` comme il ignore déjà `anim`.
- Les effets d'un clip **d'overlay** n'arrivent jamais au rendu : seul le dict
  V1 porte `effects`. Le bouton d'étalonnage global le dit dans son titre.
