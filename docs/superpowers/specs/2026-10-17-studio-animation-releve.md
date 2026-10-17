# Studio, nœud Animation — relevé du 17/10/2026

Base : `origin/main` 39241c15 (lot « Menus : Studio » t225-t230 livré et installé). Deux parties :

- **A.** La réparation du champ « Preset » (demande 1) : cause, correctif, preuve.
- **B.** Le relevé préalable à l'enrichissement de la section Animation (demandes 2-3) :
  - le catalogue de https://prompt-motion.com/ et sa licence ;
  - les moteurs IA déjà disponibles dans l'application ;
  - les options de conception.

Le plan daté est `docs/superpowers/plans/2026-10-17-studio-animation.md`. **Rien n'est codé pour la partie B tant que
l'utilisateur n'a pas tranché les questions du § B5.**

---

## A. « Preset » n'agit pas sur l'élément sélectionné

### A1. Ce que fait le nœud (bundle `frontend/dist/assets/index-BEOJX8L5.js`, composant `DzAnimation`)

**Création d'un élément.** `mk(t)` (+ Texte / + Sticker / + Image) crée toujours deux `keyframes` :

- t 0 : y 60, échelle 0,6, opacité 0, easing `easeOutBack` ;
- t 1 : y 45, échelle 1, opacité 1.

L'élément porte aussi `preset:null`.

**L'aperçu.** `sampleAt` lit les clés par `dzKfs(el)`. Dès qu'il y a deux `keyframes` ou plus, ce sont elles qui sont
lues ; `from` / `to` ne servent que d'ancienne forme de repli.

**Le rendu backend.** Le chemin est le suivant :

- « Exécuter » envoie `POST /api/animate` avec `elements: anim.props.elements`, tels quels ;
- `animation_service.render_animation` appelle `transform_at`, qui passe par `kfs_of(el)` ;
- `kfs_of` applique **la même priorité** que l'aperçu : `keyframes` d'abord, `from` / `to` seulement à défaut.

**Le défaut.** `applyPreset(name)` n'écrivait que `from`, `to`, `easing` et `preset`. Conséquences :

- le preset était enregistré et affiché dans le menu ;
- mais l'aperçu et le rendu l'ignoraient tous les deux ;
- le menu affichait `cur.preset`, si bien que re-choisir le même preset ne déclenchait aucun `onChange`.

L'utilisateur restait coincé.

### A2. Correctif — maillon de queue `dzstudio`, famille G* (PAIRES = AB + C + F + D + E + G)

**G1.** `applyPreset` écrit deux `keyframes` :

- t 0 = le `from` du preset, avec son easing ;
- t 1 = son `to`.

Il fait aussi trois choses :

- il retire `from` / `to` ;
- il garde tout le reste de l'élément (texte, style, fichier, start / dur / hold) ;
- il ramène la keyframe active à 0 (`setAk(0)`).

`dzPresetDe(el)` rend le nom du preset seulement si les clés de l'élément sont **exactement** les siennes (deux clés,
mêmes valeurs). Sinon, il rend "".

**G2.** Le menu Preset affiche `dzPresetDe(cur)`. Un preset périmé ou retouché à la main s'affiche « — » et peut être
choisi de nouveau. Un simple changement d'easing garde le nom du preset.

Contraintes respectées :

- aucun texte visible neuf ;
- aucun `useState` (731) ;
- v2.8.0 ×4, DzTracks 181 ;
- `scripts/dzglyph_paires.json` et le littéral Fu non touchés.

Le banc K de t230 (`test_studio_traduction_guide` K1) comptait 19 paires figées. Il est borné à
`19 + len(PAIRES_G)`.

### A3. Bancs, mutations, preuve

**Banc neuf `backend/tests/test_studio_animation_preset.py` : 34/34** (18 rouges sur la base).

- [A] câblage ;
- [F] sous node, avec les vraies fonctions extraites du bundle :
  - les 8 presets, depuis un élément neuf et depuis un élément à 3 clés ;
  - le menu se dérive des clés : périmé, retouché, easing seul, 3e clé ;
- [R] `animation_service.transform_at` suit le preset au début et à la fin de l'entrée. Pour slide-down à mi-entrée :
  y 50, opacité 0,75 ;
- [D] chaîne :
  - sans G = 39241c15 octet pour octet ;
  - inverse = 02f8162c ;
  - aller-retour exact ;
  - garde « partiel » ;
  - `--check`.

**Voisins Studio verts :**

| Banc | Résultat |
|---|---|
| zoom_boutons | 26 |
| canevas_barre | 31 |
| apercu_bandeau | 38 |
| entetes | 40 |
| ports_spatial | 43 |
| ancrage | 40 |
| traduction_guide | 16 |

**Mutations : 12/12 tuées.** Chaque mutant tombe aussi sur un test de comportement (A, F ou R), pas seulement sur la
chaîne. Les sources ont été copiées avant ; `cmp` est identique après.

**Preuve au vrai clic** sur un backend de preuve (port 8796, `DEEPOTUS_DATA_DIR` jetable, python embarqué) :

- **FR** : + Texte, puis Preset slide-down :
  - Courbe → easeOut, clé 1/2 y 35, clé 2/2 y 55 ;
  - Exécuter : le graphe enregistré porte `keyframes` y 35 → 55 ;
  - dans le MP4, le texte est centré à ~51 % à 0,4 s et à ~56 % à 0,8 s. Avant le correctif, il finissait à 45 %.
- **EN** : + Text, puis Preset pop :
  - y 50, scale 0,3 ;
  - y retouché à 40 → le menu affiche « — » ;
  - re-choix de pop → y 50 ;
  - Run : texte centré à ~51 %, largeur 178 → 282 px.

Les captures sont dans le dossier de notes partagé : `preset-*.jpg/png`.

**Limite de la mise en place.** La palette n'ajoute un nœud que par glisser-déposer HTML5, que le volet navigateur ne
simule pas. Le nœud Animation a donc été posé par un `drop` en JS. Tous les gestes testés sont de vrais clics.

---

## B. Enrichir la section Animation : relevé préalable

### B1. Comment le relevé de prompt-motion.com a été fait (lecture seule)

**Le site est injoignable depuis ce poste.** prompt-motion.com est servi par Cloudflare (188.114.96/97.5) :

- curl en IPv4 / IPv6, le volet navigateur, le Chrome de l'utilisateur et WebFetch échouent tous (délai de connexion
  dépassé) ;
- `www.` répond 301 vers l'apex, qui reste muet ;
- le reste du web répond, cloudflare.com compris.

**Relevé fait sur l'archive Wayback.** Index CDX, puis pages brutes `id_` ; les fiches sont stockées en zstd et
décompressées par node. Ont été lus :

- l'accueil du 05/10 ;
- le flux RSC de l'accueil du 09/10 (233 cartes) ;
- `/templates` (11/10) ;
- 6 fiches.

Aucun compte, aucun formulaire, aucune action. La liste des métadonnées (titre, date, nature, thèmes, auteur, format),
**sans aucun texte de prompt**, est rangée hors dépôt :
`side-session-notes/local_912dd7aa…/prompt-motion-catalogue-meta-20261009.json`.

**Conséquence pour la conception.** Une lecture « en direct » du site depuis l'application de l'utilisateur échouerait
aujourd'hui sur cette machine.

### B2. Ce qu'est le catalogue

**Le site.** Sa description : *« A collection of motion videos made with Claude Opus 5.5, with the prompts and skills
behind them. »*

- Curateur : @p4nthera_ (lien X).
- Menus :
  - Templates ;
  - Submit ;
  - « All videos » (grille en maçonnerie, aperçu vidéo au survol, bouton « Pause previews ») ;
  - Blog ;
  - « Customize a prompt ».

**Une fiche (entrée)** comporte :

- le titre ;
- le créateur (pseudo X + « View post ») ;
- des thèmes ;
- un bloc **Prompt** (texte + Copy, « This prompt was taken directly from @… ’s post ») et/ou un bloc **Skill** ;
- Model (toujours Opus 5.5) ;
- parfois Iterations (« One-shot ») ;
- parfois Stack (« HyperFrames ») ;
- Posted (date).

Le bloc **Skill** contient une description, une commande `npx skills add …` et « View repo ».

**Volume (09/10) : 233 entrées, 216 créateurs, du 23/09 au 08/10.**

| Nature | Entrées |
|---|---|
| Prompt seul | 229 |
| Skill seul | 3 |
| Prompt + Skill | 1 |

**Les 11 thèmes** (`contentTags`, souvent 2 ou 3 par entrée) :

| Thème | Entrées | Exemples de titres |
|---|---|---|
| product-ui | 100 | Shape morphing through UI states, Photo print app launch film |
| kinetic-type | 97 | Bold kinetic type showreel, Motion designer showreel |
| music | 50 | Abstract motion design reel |
| shapes | 44 | TypingMind logo reveal |
| particles | 43 | History of AI timeline |
| charts | 33 | Derivative concept explainer |
| diagrams | 31 | Negroni recipe animation, Animated business explainer |
| characters | 27 | Lighthouse keeper silent short, Pelican riding a bicycle |
| photos | 23 | Engraving-style Claude ad, Travel visa service promo |
| phone | 22 | UGC ad generator promo |
| code | 21 | Recursion explained in genres |

**Formats** : 200 horizontaux (surtout 1920×1080, quelques 1920×816), 19 verticaux (720×1280), 14 carrés.

**Les prompts sont très courts.** Trois exemples :

- « Go all out. » ;
- « Make a 1-minute educational video about <url> with synthesized voice narration. » ;
- « Make a 45-second silent short film… Invent the story. »

Toute la direction vient du modèle et des **skills** : c'est là qu'est la valeur à reprendre.

**Les 4 skills** — tous des dépôts GitHub. Licences vérifiées par `gh api` le 17/10 :

| Entrée | Commande | Dépôt | Licence |
|---|---|---|---|
| Cinetic skill launch film (@LexnLin) | `npx skills add Leonxlnx/cinetic` | Leonxlnx/cinetic, 238 ★ | **MIT** |
| Animated agent session story (@jake11moran), Stack HyperFrames | `npx skills add heygen-com/hyperframes-community-skills --skill session-story` | heygen-com/hyperframes-community-skills | **Apache-2.0** |
| Indian civilisation history film (@BuildFastWithAI), prompt + skill | `npx skills@latest add https://github.com/buildfastwithai/buildfast-skills` | buildfastwithai/buildfast-skills | **MIT** |
| Reddit marketing tool launch video (@anthonyriera) | non relevé | non relevé | à vérifier |

La fiche de la 4e entrée n'est pas archivée.

**Les « Templates »** sont deux prompts réécrits par le site, avec des champs à personnaliser :

- « The 3D template » ;
- « The showreel prompt » (le prompt d'origine sert dans 51 vidéos).

Annoncés ensuite : explainer, product film, short film.

**Non relevé :**

- le texte des 233 prompts (seules 6 fiches sont archivées) ;
- le blog ;
- le formulaire Submit ;
- la page « Customize a prompt » en action ;
- la fiche anthonyriera.

### B3. Licence et conditions d'usage — ce qu'on peut mettre dans le dépôt

**Le site n'a aucune page de licence ni de conditions.** Il n'y a ni Terms, ni License, ni Privacy, ni © dans
l'accueil. Sa seule mention, en pied de chaque page : **« Videos and prompts belong to their creators, linked on each
entry. »**

1. **Textes des prompts et vidéos : PAS dans le dépôt.**
   - Ils appartiennent à 216 créateurs.
   - Aucune licence n'est accordée, ni par le site, ni par la plupart des posts d'origine (posts X).
   - Ni copie, ni « catalogue embarqué », ni captures des vidéos.
2. **La compilation (titres, thèmes, sélection) est l'œuvre du curateur.** Elle ne vient pas non plus dans le dépôt.
   - La **taxonomie** (11 noms de thèmes génériques : « kinetic type », « charts »…) est une idée, pas une œuvre : on
     peut s'en servir.
3. **Les skills sont sous MIT / Apache-2.0** : réutilisables, à condition de garder l'avis de copyright et la licence
   (Apache : aussi le NOTICE et la mention des modifications).
   - Choix recommandé : **ne pas les vendre dans le dépôt**, mais les **installer à la demande** dans le dossier de
     données de l'utilisateur, depuis leur dépôt, avec la licence affichée et conservée à côté.
   - S'ils devaient un jour être embarqués : dossier `vendor/` avec LICENSE / NOTICE, comme photocraft.
4. **Ce qu'on peut livrer sans risque** :
   - nos **propres** fiches de style, rédigées par nous, rangées par les 11 thèmes ;
   - un **import par l'utilisateur** d'une entrée qu'il a lui-même copiée (prompt collé + lien vers la fiche et le
     post). Elle est enregistrée dans `DEEPOTUS_DATA_DIR` (jamais dans le dépôt), avec l'attribution affichée.

### B4. Les moteurs IA déjà présents dans l'application (lus dans le code, base 39241c15)

**Moteurs de texte (les « harnais » qui peuvent écrire une chorégraphie ou un script).**

Registre `backend/app/services/moteurs_texte.py`. `tous()` les donne dans cet ordre :

- les intégrés `anthropic`, `openai`, `gemini`, `ollama` ;
- les fournisseurs libres compatibles OpenAI `fl:<id>` (t222 : DeepSeek, OpenRouter, Mistral, Groq…) ;
- les serveurs locaux `local:<id>` (t223 : Ollama, LM Studio, llama.cpp).

`etat()` donne une ligne par moteur : configuré, modèle sain, alerte.

Exposition par l'API :

- `GET /api/settings/provider-defaults` → `moteurs` ;
- `GET /api/settings/provider-defaults/modeles?moteur=` → la vraie liste des modèles.

Appel d'un moteur et d'un modèle **précis** : `vector_illustration.tirer(moteur, modele, prompt, systeme, …)`. C'est ce
qu'utilise déjà le panneau IA du Vectorlab. Côté écran, le module commun `mod-ia.js` (t197) porte le sélecteur de
moteur et les bulles de coût :

- ollama / local → « gratuit » ;
- fl → « prix à mesurer » ;
- intégrés → payant.

Le repli par rôle passe par `summarizer._chat_dispatch` (rôle Résumé) et les plafonds de dépense.

**Générateurs (images, vidéo, son), surtout via fal.**

- `/api/ia/catalogue` ;
- `catalogue_ia.py` ;
- les nœuds Génér. d'images, Seedance, Illustr. News, SFX / musique (G5), VFX (G6).

Ils produisent des **médias** que le nœud Animation sait déjà poser (+ Image, ou l'entrée `base`). Ils ne
chorégraphient pas.

**Rendu de l'animation.** `animation_service.render_animation` : Pillow image par image sur une base ffmpeg.

- Éléments : texte, sticker, image.
- Clés : x, y, scale, rotation, opacity ; easings, dont cubic-bezier.
- Rendu fidèle et sans réseau, mais **pas de code arbitraire**. Il ne connaît ni formes vectorielles, ni particules, ni
  graphiques, ni masques.

### B5. Options de conception — à trancher par l'utilisateur

Ce qui fait un motion design dans le catalogue, c'est un modèle qui **écrit du code d'animation**, guidé par un skill.
Notre nœud Animation, lui, sait jouer une **liste d'éléments à clés**. D'où trois questions.

**Q1 — Que produit le harnais IA ?**

- **A, « Chorégraphe » (recommandé pour commencer).** Le moteur de texte choisi rend un JSON validé et borné :
  éléments, textes, presets, keyframes, easings, start / dur / hold. Il remplit le nœud Animation existant.
  - Avantages : rendu Pillow actuel, aucun code exécuté, coût minime, marche avec Ollama / local.
  - Limite : seulement texte, sticker et image en mouvement.
- **B, « Motion code ».** Le moteur écrit une page HTML / SVG / Canvas animée, rendue en MP4 par Edge sans fenêtre.
  - Points à traiter : bac à sable sans réseau, CSP stricte, délai et taille bornés, aucune ressource externe.
  - Avantages : le plus fidèle au catalogue (formes, particules, graphiques, diagrammes).
  - Limites : coût et risque nettement plus élevés ; qualité très dépendante du modèle (mauvaise en local).
- **A puis B.** A d'abord (lot court). B ensuite, comme un nœud « Rendu motion code » branché en `base` de l'Animation.

**Q2 — Nœuds ou bandeaux ?**

- **(i) Trois nœuds** branchés sur trois entrées neuves de l'Animation (`style`, `script`, `source`) :
  - « Style motion » : thème, rythme, palette du kit de marque actif, moteur ;
  - « Script motion » : texte à animer, ou relié à Texte / Prompt / Script News ;
  - « Source motion » : un prompt ou un skill de la bibliothèque, avec éditeur.
  - Plus un bouton « Chorégraphier » dans l'inspecteur de l'Animation.
- **(ii) Un seul bandeau « Direction IA »** dans l'inspecteur de l'Animation : Style, Script, Source et Moteur dans
  quatre rubriques repliables, sans nouveau port.
- **(iii) Mixte (recommandé).**
  - Un nœud « Direction motion » (sortie `direction`) qui porte Style + Source + Moteur, réutilisable sur plusieurs
    Animations.
  - Le **script** arrive par l'entrée `script`, depuis n'importe quel nœud texte existant (Texte, Prompt, Script News),
    ou depuis un champ du nœud.
  - Un **skill** s'y sélectionne et **son prompt s'édite dans le nœud** : zone de texte « Consigne du skill » =
    SKILL.md (ou son prompt d'amorce), avec un bouton pour revenir à l'original.

**Q3 — Le catalogue livré** (contrainte de licence, § B3) :

- **(a)** nos 11 fiches de style maison + import manuel par l'utilisateur (prompt collé + lien) + skills installés à
  la demande depuis GitHub (licence affichée) ;
- **(b)** idem, sans import manuel ;
- **(c)** seulement nos fiches.

Recommandation : (a).

**Décision de l'utilisateur (17/10) : A puis B, (iii), (a)** — les trois recommandations.

**Recommandation d'ensemble : A puis B, (iii), (a).** Le lot est découpé pour que A soit utile seul (t232-t237).
B (t238) attend une seconde validation, après mesure de la qualité de A.

Maquette des options : `docs/superpowers/specs/assets/2026-10-17-studio-animation/maquette.svg`.
