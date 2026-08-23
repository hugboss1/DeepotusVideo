# Cardforge — phase 3b : l'édition directe type Figma (§6.1 complet)

Suite de la 3a (archétypes livrés). Contrat : spec §6.1
(docs/superpowers/specs/2026-08-19-cardforge-universel-design.md:302-316) —
sélection/drag/poignées SUR l'aperçu (livré en partie), **palette d'ajout
d'éléments** (zone de texte, zone de statistique étiquette+valeur, calque
d'image/motif), **liste de calques ordonnée** (ordre z dans les bornes du z
gelé, réordonnancement, verrouillage, œil), gestes en `M.patch` sous le jeton
du module propriétaire (une entrée d'annulation PAR GESTE), barre de fluidité
§9.6 sur chaque surface neuve. Amender à la source (leçon ×9).

## Faits de reconnaissance (23/08, ancres vérifiées)

- **Le calque flottant P3 EST ~80 % du §6.1** (mod-type.js §8 :4129-4323) :
  8 poignées, drag/resize à pointer-capture + rAF coalescé, clavier (flèches,
  Alt=resize, Ctrl+D duplique, Delete, Ctrl+Z/Y), snap 0,25 mm (Alt lève),
  actif seulement quand LE panneau P3 porte `.on` ET `type.show_boxes`
  (`visible()` :4143, MutationObserver sur la classe du panneau :1302).
  Sélection UNIQUE `doc.type.sel`. La liste du panneau (renderList
  :1543-1662) a DÉJÀ : œil (`on`, :1638), monter/descendre (`moveSlot`),
  drag-réordonnancement HTML5 natif, corbeille, « + Slot » générique
  (`addSlot` :1485, plafond SLOTS_MAX=40), presets. **Manquent** : verrou,
  palette d'ÉLÉMENTS des modèles, paire étiquette+valeur, calque d'image,
  liste multi-bandes.
- **PAS de « calques P2 » comme objets** : doc.frame = booléens/enums peints
  en DUR (gem, banner, plate, socles, corner…) — aucune pile ordonnée. P6 =
  exactement 2 rôles figés (paper z10, over z30 — « calque z = 30 » au
  libellé), UN import de papier écrasé à chaque fois. P1 = UNE image.
  **Le seul empilement utilisateur-ordonné du lab est la liste P3.**
- **Z gelé** (core.js:82) : 10 texture / 20 face / 30 texture / 40 frame /
  60 type / 70 frame / 90 core. Dans la bande 60, l'ordre = l'ordre du
  tableau `slots` (peint dans l'ordre, :1230). Lecture inter-modules LÉGALE
  par `CF.get` d'état publié (patron art_window — mod-face lit
  frame.art_window :1769) ; ÉCRITURE jamais (jeton scellé).
- **Éléments des modèles (3a-T3)** : `{id, label, hint, slots:[35 clés
  complètes — **36 depuis la T1**, `lock` est arrivé]}` (models.py:172,
  exemple :277-286 ; paire étiquette+valeur =
  `_duel_ligne` :302-317). **Le deck n'en garde AUCUNE copie** — le seul fil
  est `doc.type.preset` = l'id du modèle (:1063) ; l'écran doit fetch
  `GET /models` et retrouver l'entrée par preset.
- **Imports d'image, 2 précédents** : A) mod-face IndexedDB
  (`dz_cardforge_face`, browser-local, clé `local:` — ne voyage PAS avec le
  deck) ; B) texture.py `/paper` (serveur, deck-scoped,
  `decks/{did}/texture/paper.png`, `_store_image`, 64 Mo cap, UN fichier
  écrasé). Un calque d'image de deck doit VOYAGER avec le deck → patron B.
- **HIST** : P3 pousse AVANT le geste et POP si rien n'a bougé (:4215,
  :4292) ; P2 pousse À LA RELÂCHE (:2674). Les deux coalescent ≤1
  patch/frame. ~~**Écart de nudge**~~ : la spec nomme le patron P2 (« pas 1 mm,
  Maj = 0,2 mm » :307) ; P3 faisait 0,5 / Maj=5 (:228) — l'INVERSE de Maj.
  **SOLDÉ en T1.**
- **Notes T1-3a à solder ici** : ~~les 3 passes d'encre dupliquent l'objet de
  neutralisation (:3410/:3704/:3908 — helper partagé demandé)~~ **SOLDÉ (T1,
  `soloClone`)** ; ~~le filtre R14 (`Html|paint`) ne balaie ni renderInsp ni
  les futures galDraw-like~~ **SOLDÉ (T1, critère = le sink innerHTML ; 11
  vraies fautes trouvées et corrigées)** ; la branche arcTo du banc
  inexerçable (accumulation de chemin à ajouter si bon marché) — RESTE.
- **Tailles** : mod-frame 5033 l., mod-type 4323 l. (le fichier de la 3b),
  mod-face 4050, core 2254. mod-type va grossir : viser des AJOUTS de
  fonctions courtes ; si une tâche dépasse ~400 l. nettes, LE DIRE.

## Décisions de conception 3b

1. **Le calque d'image/motif = un KIND de slot P3** — la voie que la spec
   nomme (« instanciés comme des objets Cardforge ORDINAIRES (slots P3 /
   calques P2) ») et la seule qui hérite GRATUITEMENT de l'overlay, de
   l'ordre, de l'œil, du verrou, de HIST et de la fluidité. `kind:
   "text"|"image"` (défaut "text" — parité JSON, les 4 presets
   byte-identiques), `src` (`"img:{fichier}"` deck-scoped), `fit`
   (contain|cover). Un slot image ignore les clés typographiques (inertes,
   pas retirées — la parité stricte prime) ; plate/opacity/rotate/on/lock
   s'appliquent. La bande z=60 place ces calques AU-DESSUS du cadre de base
   (40) et SOUS le décor haut (70) — dit à l'écran. Les motifs du CATALOGUE
   (P2 backs, matières) = 3c avec le travail de motifs du Sceau — dit.
2. **Stockage des images de slots : serveur, deck-scoped** (patron
   texture.py:post_paper) — `POST /api/cards/{did}/type/image` →
   `decks/{did}/type/img_{n}.png` (compteur, PAS d'écrasement), borné
   (nombre ≤ 12, taille, MAX_IMPORT_PX partagé), servi par GET, référencé
   `src: "img:img_{n}.png"`. Le deck voyage entier (export/duplication —
   la duplication 3a copie déjà le dossier). Dépôt/collage dans l'éditeur
   de slot (patrons drop de mod-face).
3. **La palette d'éléments vit dans P3** (~~panneau + bouton overlay~~ **la
   BARRE du panneau seule — amendé en T3**, voir la note de livraison : le
   calque d'édition réécrit tout son innerHTML à chaque frame d'un glisser,
   un contrôle qui y vivrait serait recréé et recâblé à 60 Hz, sur la carte,
   là où la main glisse) : trois
   entrées GÉNÉRIQUES toujours là — « zone de texte » (addSlot d'aujourd'hui),
   « zone de statistique » (paire étiquette+valeur, la forme _duel_ligne
   généralisée), « calque d'image » — PLUS les éléments du MODÈLE quand
   `doc.type.preset` correspond à un modèle servi (~~fetch /models une fois,
   cache par preset~~ **le plan ne disait pas PAR OÙ — amendé en T3 : par
   `CF.models`, une capacité de LECTURE neuve du CORE (patron `CF.images`),
   sur la liste que la galerie a déjà chargée et cachée. `M.api` est confiné
   à /api/cards/<did>/type et la liste vit ailleurs ; un `window.fetch` nu
   dans une pièce rouvrait le « fetch libre » retiré par `makeApi`, et une
   table recopiée est refusée par le banc du contrat. Le cache est celui du
   CORE, donc UN seul, et il n'est pas « par preset » : le catalogue est
   entier, les offres se dérivent du preset AU MOMENT DE PEINDRE**),
   404/absence tolérée : la palette dit « modèle sans
   éléments » ou rien. Instanciation = append des slots de l'élément avec
   UNIQUIFICATION d'ids CLIENT identique à la règle serveur (norm_slots
   renomme, ne jette jamais — T3-F11) ; UNE entrée HIST par ajout.
4. **La liste de calques est P3-possédée, multi-bandes en LECTURE** :
   une section « Calques » dans le panneau P3 — les bandes fixes (papier
   z10, illustration z20, effet z30, cadre z40, décor haut z70) en rangées
   LECTURE SEULE dérivées de l'état PUBLIÉ (`CF.get` des sous-arbres
   concernés : texture.paper, face.src, frame.family…), chacune avec un
   bouton « aller au module » (`CF` n'expose pas show() aux jetons ? le
   VÉRIFIER — sinon le clic sur l'item de rail équivalent, ou une capacité
   à ajouter au CORE proprement) ; la bande type (z60) = la liste EXISTANTE
   enrichie (œil, verrou, ordre, kind badgé). AUCUNE écriture inter-modules
   (cloisonnement T4-3a).
5. **Verrou** : clé `lock` (bool, défaut false) — 36e clé, parité JSON.
   Verrouillé = ni drag, ni poignées, ni nudge, ni Delete par CLAVIER ;
   reste SÉLECTIONNABLE (pour déverrouiller) et éditable au panneau (le
   verrou protège des gestes de scène, pas de l'intention). Badge cadenas
   liste + overlay.
6. **Nudge aligné sur la spec** : flèches 1 mm, Maj = 0,2 mm (le patron P2
   nommé §6.1:307), Alt=resize conservé. L'ancien 0,5/5 disparaît — pin.
7. **Passes d'encre** : helper partagé `soloClone(slot, garde)` remplaçant
   les 3 copies (+ pin de COMPTE d'appels — la 4e passe future doit le
   prendre) ; les slots `kind:"image"` sont EXCLUS des passes d'encre
   (mesures typographiques sans objet) — dit et testé.

### Task 1 : fondations P3 — verrou, nudge-spec, soloClone, R14

**Files:** mod-type.js, type.py, test_cards_type.py, scripts/qa/lint_cardforge.py.

- [x] `lock` 36e clé (parité JSON stricte, presets byte-identiques) ; overlay
      et clavier REFUSENT drag/resize/nudge/delete sur un slot verrouillé
      (sélection et panneau libres) ; badge cadenas (liste + hbox).
- [x] Nudge 1 mm / Maj 0,2 mm (pin ; l'ancien 0,5/5 mort).
- [x] `soloClone` : les 3 sites (:3410/:3704/:3908) passent par le helper,
      pin de compte (== 3 aujourd'hui, le message dit pourquoi).
- [x] R14 : filtre de noms élargi (renderInsp, galDraw*, et le futur
      paletteHtml de la 3b) — le lint intégral reste 0 sur tout le dépôt
      (si l'élargissement révèle un site réel non échappé : le corriger,
      c'est le but).
- [x] Mutation : verrou ignoré au drag (rougit), nudge à 0,5 (rougit),
      soloClone contourné (compte rougit).

> **Livré (T1)** — 35 → **36 clés** par slot (`lock`, bool, défaut false),
> égalité JSON stricte tenue des deux côtés (mod-type.js:113 ↔ type.py:444-456).
> Le backend ne l'INTERPRÈTE pas, il le TRANSPORTE : aucun painter ne le lit,
> et c'est ce qui garde les 4 gabarits byte-identiques (prouvé : même empreinte
> FNV-1a avec et sans la clé, et un slot verrouillé rend exactement comme le
> même déverrouillé). Il est dans le document et non dans un état d'écran
> parce qu'un bloc protégé qui redevient libre à la réouverture ne protège rien.
>
> · **Le banc de gestes (BANC_VERROU)** — nouveau, et c'est le vrai apport de
>   la tâche : il fait tourner `MOD.init(host)` dans un DOM de paille et
>   récupère les écouteurs **là où le module les pose** (pointerdown sur le
>   calque posé sur `document.body`, keydown sur le document), puis joue des
>   gestes dessus. Il ne teste donc pas une fonction interne choisie à la main.
>   Il rend aussi le HTML du calque et celui de la liste : les tâches 2-4
>   (kind image, palette, liste multi-bandes) peuvent s'y brancher.
> · **Le verrou ne garde JAMAIS le panneau** — champs X/Y/L/H, centrer/remplir,
>   leviers du relevé d'audit et remèdes compris : TOUTE écriture de réglage
>   passe par `patchSlot`, et `patchSlot` ne regarde pas `lock` (voulu, testé —
>   un garde là enfermerait le bloc pour de bon, y compris contre le clic qui
>   le déverrouille). La liberté du panneau est entière, pas « quelques
>   champs » : le verrou n'arrête que la main sur l'aperçu et la touche pressée
>   au hasard.
> · **Le refus est un NON-DÉMARRAGE**, pas un geste joué puis annulé : sur un
>   bloc verrouillé, `onOvDown` sort AVANT `pushUndo()` et avant de brancher
>   `pointermove` — le banc compte 0 écouteur pointermove (1 sur le contrôle).
>   Rien à reprendre dans HIST, rien à défaire.
> · **DÉCISION — Ctrl+D sur un bloc verrouillé est PERMIS, et la copie naît
>   OUVERTE.** Dupliquer ne touche pas au bloc protégé : ça en pose un AUTRE,
>   à 2 mm, avec un id neuf — un acte d'intention (comme un réglage du panneau),
>   pas un geste de scène. Et le verrou marque un bloc DÉJÀ placé ; une copie
>   qu'on vient de créer, elle, se place. Née fermée, elle aurait refusé le
>   glisser qui la suit d'une seconde sans que rien à l'écran ne dise pourquoi.
> · **Suppr est refusé AVEC UN MOT** (toast), les flèches en silence : une
>   flèche se répète, un toast par pression noierait l'écran — et son refus se
>   lit sur le cadenas de la boîte, qui est sous les yeux. Suppr, non : un
>   effacement qui ne se produit pas se lit comme une touche morte.
> · **Nudge** : `NUDGE_MM = 1, NUDGE_FINE_MM = 0.2` (mod-type.js:235).
>   `NUDGE_BIG_MM` n'existe plus (pin sur son absence) ; le mémo du panneau dit
>   les mêmes chiffres que le code ; le pas est MESURÉ au banc, pas relu
>   (flèche → +1 mm, Maj → +0,2 mm, Alt → +1 mm de largeur, Alt+Maj → +0,2 mm
>   de hauteur), et l'ancien 0,5 restauré par mutation rougit.
> · **`soloClone(slot, garde)`** (mod-type.js:3422) remplace les 3 littéraux.
>   Le seul écart entre les sites était l'OMBRE : la passe du halo la garde
>   (c'est elle qui la mesure), les deux autres la coupent — d'où
>   `soloClone(slot, { shadow: true })`, une fois et une seule. Pin de compte
>   (3 appels) avec le message qui dit la règle de la 4ᵉ passe, + pin qu'aucun
>   littéral de neutralisation ne subsiste HORS du helper.
> · **L'équivalence est PROUVÉE, pas raisonnée** : ces trois passes ne tournent
>   que dans un navigateur, une dérive d'un cheveu n'aurait fait rougir
>   personne. Le banc se fait ouvrir la fermeture par une mutation
>   (`globalThis.__solo = soloClone;` avant la parenthèse finale, sur la COPIE)
>   et compare la SÉRIALISATION du helper aux deux littéraux d'avant, recopiés
>   mot pour mot, sur un slot qui porte tout ce qu'il doit neutraliser : mêmes
>   clés, mêmes valeurs, même ordre — plus « le slot source n'est pas muté » et
>   « les deux gardes ne rendent pas le même objet ». Un `shadow_dy` oublié
>   dans le helper fait rougir (vérifié par mutation).
> · **R14 — mécanisme, pas liste de noms.** Une fonction est balayée si son nom
>   contient Html/paint **ou si son corps pose du HTML** (`innerHTML`/
>   `outerHTML`/`insertAdjacentHTML`) : le sink est le fait mécanique, un nom
>   n'est qu'une intention. Mesure : **+65 fonctions** balayées sur les 9
>   pièces, surcoût nul (0,50 s → 0,51 s — le corps est déjà découpé).
>   **11 vraies valeurs d'attribut non échappées trouvées et corrigées** :
>   mod-type `renderList` (2 : `au.masked`, `m.over_chars` → `Number(...)`),
>   mod-face `renderPanel` (2) + `fillPalettes` (1, + `p.sky[1]`/`p.glow` dans
>   le `style=` voisin, hors portée mécanique de la règle mais même faute),
>   mod-solid `buildStatics` (6). Aucune n'était exploitable aujourd'hui
>   (tables statiques locales) — c'est un cliquet, il se pose avant.
> · **La position d'attribut se reconnaît maintenant à DEUX motifs**, et il en
>   faut deux. L'élargissement a mis la règle devant des fonctions qui écrivent
>   du HTML **et des phrases**, et une phrase finit par `nom=` aussi bien
>   qu'une balise (« ligne y=42 », « 300 DPI = 12 / mm² », « tile?mat=…&seed=7 »
>   — 5 faux signalements dans mod-frame et mod-texture). **Premier réflexe :
>   exiger le guillemet. C'ÉTAIT UNE RÉGRESSION** — signalée à la revue, et
>   vraie : `'<div data-id=' + s.id + '>'` (attribut NON cité, patron DOM-XSS
>   réel, et le PIRE des deux — une simple ESPACE y pose un attribut de plus,
>   pas besoin de refermer un guillemet) était attrapé par l'ancienne règle
>   dans les fonctions nommées, et le guillemet exigé le faisait rater PARTOUT.
>   **Réparé** : motif 1 = `nom="` cité ; motif 2 = `nom=` nu **mais dans une
>   balise encore ouverte** (`_dans_balise_ouverte` : dernier `<` après dernier
>   `>`). Ce qui sépare la balise de la phrase n'est pas le guillemet, c'est le
>   chevron — une phrase n'a pas de `<`. Différentiel mesuré : aucune classe
>   que l'ancienne règle attrapait n'est perdue, la classe 2 est désormais vue
>   AUSSI hors des fonctions nommées, les 5 proses restent muettes, dépôt réel
>   à 0, coût 0,52 s.
> · **Limite résiduelle, assumée et écrite dans le lint** : un SECOND attribut
>   nu dans la MÊME balise construite en plusieurs fragments
>   (`'<div id=' + a + ' name=' + b + '>'`) n'est pas vu — le fragment
>   `' name='` ne porte pas le `<` qui l'ouvre. Le voir demanderait de suivre
>   l'état de balise À TRAVERS les fragments, c'est-à-dire un analyseur, pas
>   une règle lexicale. Le premier attribut, lui, est vu, et il fait déjà
>   rougir la ligne.
> · Les deux sens sont testés (sonde citée ET sonde nue rougissent, prose non,
>   position texte non), les 5 faux positifs connus sont ÉPINGLÉS sur les vraies
>   lignes de mod-frame/mod-texture (avec vérification que la prose est toujours
>   là, pour que le pin ne devienne pas creux), et deux mutations tuent : R14
>   rétréci au filtre de noms, et second motif retiré.
> · **Compte** : 108 → **122 tests** dans test_cards_type.py (15 neufs, 1
>   remplacé — l'ancien `test_les_mesures_d_encre_ignorent_la_plaque` épinglait
>   les 3 littéraux que le helper supprime). Lint intégral 0. `node --check` OK
>   sur les 3 JS touchés. Hors périmètre déclaré mais nécessaire :
>   test_cards_models.py (35 → 36 clés, nom du test) et le commentaire
>   models.py:149 — les modèles partent de `SLOT_DEFAULTS`, ils n'ont rien eu
>   à changer d'autre.
>
> **Reste à l'œil (2 min)** : verrouiller un bloc dans le vrai navigateur et
> sentir que le glisser refuse (curseur « interdit », cadenas ambre sur la
> boîte), que le panneau continue de le régler, et que la flèche fait bien
> 1 mm / 0,2 mm à la main.

> **CLOSE (T1 — dbfdbb9 + fast-follow 71028c5, revue : MERGEABLE AS-IS,
> régression R14 rattrapée).** Le verrou est un NON-DÉPART (0 écouteur posé,
> rien à dépiler — prouvé par la sonde « entrée fantôme » du réviseur : un
> vrai drag + un refusé + UN SEUL Ctrl+Z = retour complet) ; nudge 1/0,2 ;
> soloClone à byte-égalité PROUVÉE en ouvrant la fermeture. **R14 passé du
> nom au SINK** (+65 fonctions, 11 vraies fautes corrigées dans 3 modules) —
> puis la revue a montré que l'exigence de guillemet faisait tomber à ZÉRO
> la détection d'attribut non cité (pire que l'ancien état dans les
> fonctions nommées) : rattrapé par un SECOND motif dont le discriminateur
> est LE CHEVRON (dernier `<` après dernier `>` = l'interpolation tombe dans
> une balise ouverte) — différentiel : aucune classe perdue, le non-cité vu
> partout, les 5 faux positifs de prose propres (épinglés SUR leurs lignes,
> avec leur présence assertée pour que le pin ne se vide pas), limite
> résiduelle (2e attribut nu d'une même balise multi-fragments) écrite dans
> la règle. Le verrou ne gate JAMAIS le panneau (pinned : `patchSlot` sans
> `lock` — une garde là enfermerait le bloc pour de bon). 122 tests,
> 11/11 suites, lint 0 à 0,52 s.

### Task 2 : le calque d'image (kind + route + painter + éditeur)

**Files:** mod-type.js, type.py, test_cards_type.py (+ mod-type.css).

- [x] Vocabulaire : `kind` ("text"|"image", défaut "text"), `src`, `fit`
      (contain|cover) — 39 clés, parité, presets intacts.
- [x] Backend : `POST /type/image` (raw body, patron texture.py:post_paper,
      `img_{n}.png` compteur SANS écrasement, plafonds nombre=12/taille/
      MAX_IMPORT_PX, jamais-500 nommé) + `GET /type/image/{name}` (whitelist
      du motif de nom, no-store ? NON — cache ok, fichiers immuables par
      compteur) + purge à la suppression du slot ? NON — les fichiers
      restent (un slot supprimé peut être annulé) ; un GC honnête = 3c, dit.
- [x] Painter z=60 : un slot image dessine son image dans sa boîte (fit,
      rotation, opacité, plaque DESSOUS), cache d'Image objets (patron
      IMGS — l'aperçu ne re-décode pas à chaque frame) ; image absente/404 =
      damier + nom (état, pas d'erreur) ; slots image EXCLUS des 3 passes
      d'encre et du juge de lisibilité (sans objet — testé).
- [x] Éditeur : le panneau de slot bascule ses sections selon kind (typo
      masquée pour image ; import par dépôt/collage — patrons mod-face,
      réduction client MAX_IMPORT_PX avant envoi) ; « + calque d'image »
      dans la palette T3.
- [x] Banc : painter image mesuré au pixel (fit contain vs cover, opacité,
      plaque dessous, rotation) ; la route bornée (13e image → refus nommé) ;
      RED d'abord partout.

> **Livré (T2)** — 36 → **39 clés** (`kind` "text"|"image", `src`, `fit`
> "contain"|"cover"), égalité JSON stricte tenue (mod-type.js:109 ↔
> type.py:477). Les quatre gabarits sont byte-identiques, PROUVÉ au banc de
> pixels (même empreinte FNV-1a avec les trois clés aux défauts et sans elles
> du tout) : « text » est exactement ce que le painter faisait avant qu'il y
> ait un `kind`.
>
> · **La NATURE se pose à la NAISSANCE, et le panneau la MONTRE sans la
>   basculer** (`addImgSlot` :1758, bouton « + Image » à côté de « + Slot »).
>   Une bascule sur un bloc existant aurait changé le SENS de ses réglages sous
>   la main : un `src` sur un bloc de texte ne veut rien dire, une police et une
>   casse sur un calque d'image non plus — et elle posait trois questions sans
>   bonne réponse (que faire du texte saisi ? de l'image importée ? de
>   l'ajustement ?). La manœuvre honnête — créer l'autre, déplacer la boîte,
>   supprimer le premier — tient en deux clics et laisse UNE trace dans HIST,
>   ce qu'une bascule silencieuse ne ferait pas. La palette de la T3 appellera
>   `addImgSlot` : elle n'aura pas à savoir ce qu'est un calque d'image.
> · **L'exclusion est un NON-ENTRÉE dans `MEAS`**, pas un filtre à chaque
>   passe : le painter sort AVANT `layoutSlot` (:1467), donc le relevé ne porte
>   jamais un calque d'image et les trois passes d'encre n'ont rien à ignorer.
>   Les gardes sont écrites QUAND MÊME là où une passe repart de `slots()`
>   (contrôle photométrique :3959, second tirage :4521, **et le contrôle de
>   SÉRIE :4637 — la quatrième, celle qu'on oublie**, qui aurait compté un
>   calque « vide » sur les 200 cartes du deck). `isImage` est le SEUL test de
>   nature du module (pin de compte : `kind === "image"` n'apparaît qu'une
>   fois).
> · **Côté serveur, l'exclusion est DITE colonne par colonne** (type.py:975) :
>   `size_px`, `min_px`, `read_pt`, `read_px`, `posed_pt`, `under_read`,
>   `missing_glyphs` valent `None` — et non 0, qui se lirait comme une mesure.
>   **La GÉOMÉTRIE, elle, reste jugée** : une image qui sort du cadre de
>   composition est un défaut de fabrication comme un autre, la coupe emporte
>   ses pixels exactement comme elle emporterait des glyphes. C'est la
>   LISIBILITÉ qui est sans objet, pas le confinement — testé dans les deux
>   sens.
> · **Le compteur, et pourquoi il ne recycle pas.** `img_{n}.png` avec n =
>   MAX + 1, jamais « le premier trou libre » : un slot supprimé se rattrape
>   par Ctrl+Z, et un numéro recyclé aurait fait revenir le bloc annulé avec
>   une AUTRE image. C'est aussi la raison de **l'absence de route DELETE** —
>   effacer des octets sur un geste réversible. Le ramassage des images
>   orphelines est consigné pour la 3c, dans le code. Le non-écrasement est
>   prouvé PAR MUTATION : compteur cassé à « toujours 1 » → l'écrasement a bien
>   lieu, donc le test d'origine mesure quelque chose.
> · **Liste blanche AVANT le disque, mesuré et pas relu** : un mouchard
>   remplace le lecteur de fichier et n'est JAMAIS appelé sur les onze noms
>   refusés (`job.json`, `img_1.PNG`, `%2e%2e%2f…`, `img_1.png%00.txt`…), et
>   il l'est sur un nom légal. Le cache est PERMIS (`immutable`) et c'est une
>   conséquence du compteur : `img_7.png` ne change jamais de contenu.
>   `FileResponse` refusé pour la raison de 2c (re-stat à l'envoi = 500 sur une
>   pièce jamais-500) — le mot reste dans la docstring, la chose non (pin sur
>   l'import et l'appel).
> · **Le mécanisme de re-peinture est celui du module, pas un nouveau** : le
>   painter ATTEND ses images comme il attend ses polices (`ensureImgs` mirroir
>   d'`ensureFonts`, même course bornée à 2,5 s des 4 s du CORE), et une image
>   qui arrive après la course redemande un rendu sous la MÊME garde que
>   `loadFont` (« seulement si un calque vivant porte ce fichier »). Piège
>   attrapé à la relecture : le cache doit recevoir la PROMESSE avant que le
>   chargement démarre — un échec synchrone écrivait l'état puis se faisait
>   écraser par la promesse, et la boîte restait au damier pour toujours.
> · **Le damier n'est pas une erreur, c'est un état** — et il porte LE NOM du
>   fichier manquant : « le calque est cassé » et « ce fichier-là n'est pas
>   arrivé » ne se réparent pas pareil. Il est doublé d'un badge dans la liste,
>   parce qu'un calque masqué, hors face ou caché sous un autre serait parti à
>   l'impression sans que rien ne l'ait annoncé. `src` VIDE, lui, ne peint rien
>   du tout : c'est un calque qui vient de naître, pas un manque.
> · **Trois blocs du panneau sont désormais PARTAGÉS** (`inspHead`,
>   `inspPlaque`, `inspBoite` :2139-2177) au lieu d'être recopiés pour la
>   seconde nature — la leçon de `soloClone`, appliquée à l'éditeur. Le
>   branchement commun (`wireInspCommun` :2323) est piloté par les ATTRIBUTS
>   (`data-k`), donc ajouter un réglage au panneau d'image n'oblige à rien.
>   **Conséquence sur deux tests d'avant** : leur oracle était l'ordre des
>   LIGNES DU FICHIER, qui ne dit plus l'ordre de l'ÉCRAN (la plaque est écrite
>   avant `renderInsp` et s'affiche après) ; ils lisent maintenant le panneau
>   RENDU par le banc, ce qui est l'oracle qu'ils voulaient depuis le début.
> · **Le même conteneur porte deux relevés** (`syncInspMeas`) : le pied de la
>   section « Boîte » est réécrit après chaque mise en page, et il suit la
>   nature du bloc — sinon « image 200 x 100 px » se faisait écraser par
>   « corps 10 pt » à la première frame. Le relevé d'image publie le chiffre
>   qui décide de l'impression : combien de pixels d'image par pixel de toile,
>   et « la toile agrandit » quand il passe sous 1.
> · **Compte** : 122 → **152 tests** dans test_cards_type.py (30 neufs, 0
>   supprimé ; 5 amendés — le compte de clés ×3, et les deux tests d'ordre du
>   panneau passés au panneau rendu). test_cards_models.py 154 (36 → 39 dans le
>   nom et le compte). Lint intégral 0. `node --check` OK. **mod-type.js prend
>   ~500 lignes nettes — au-dessus des ~400 annoncées par le plan** : le
>   painter d'image (cache + damier + cadrage) et le second panneau sont deux
>   surfaces neuves, et la moitié du volume est en commentaires. Le fichier
>   passe 4411 → 4940 lignes ; la T4 (liste multi-bandes) devra viser plus
>   court ou déclarer un découpage.
>
> **Reste à l'œil (3 min)** : déposer une vraie image dans le navigateur et
> sentir le cadrage (entière vs remplir), la rotation, l'opacité, la plaque
> dessous ; couper le fichier sur le disque pour voir le damier nommé ; coller
> (Ctrl+V) une image dans un calque sélectionné.

> **RONDE DE REVUE (T2) — FIX-FIRST, 2 bloquants + 2 moyens + 2 bas + 2
> avenants, tous soldés.** Ce que la revue a mesuré et que la livraison
> n'avait pas vu :
>
> · **B1 — `src` se normalisait en la CHAÎNE « undefined ».** La garde nulle
>   portait sur l'opérande TESTÉ et non sur le RÉSULTAT : `SRC_RE` accepte la
>   chaîne vide, donc le test passait, et c'est `String(undefined)` qui était
>   rangé. Les 21 slots des quatre gabarits sortaient avec `src: "undefined"` —
>   une source illégale que le backend RÉPARAIT à chaque chargement, c'est-à-
>   dire l'idempotence que ce même commit venait d'inscrire dans models.py:149.
>   **La vraie leçon n'est pas la ligne, c'est le TEST** : la parité des deux
>   normaliseurs était épinglée par des MATCHS DE SOURCE (« cette ligne est dans
>   le fichier »), et un match de source ne dit rien de ce que le code FAIT.
>   Remplacé par une **parité d'EXÉCUTION** — `normSlot` ouvert par mutation
>   (patron `__solo`), 13 entrées (document vide, absences explicites, slot
>   d'avant la 3b, hostiles sur chaque clé neuve), comparaison clé par clé avec
>   `norm_slot`, **plus l'idempotence JS** (`normSlot(normSlot(x)) ==
>   normSlot(x)`) et **plus les gabarits rendus** (`norm_slot(s) == s` sur les
>   21 slots : le backend n'a rien à réparer).
> · **B2 — la course d'écriture : 6 imports simultanés → 1 fichier, 4 clients
>   convaincus d'avoir écrit `img_1.png`, 2 vrais 500** (`PermissionError 13` /
>   WinError 32 sur un `.tmp` partagé, reproduit au banc avant correction).
>   Atteignable sans rien d'exotique : deux Ctrl+V rapprochés (le collage est
>   posé sur `document`, `M.busy` grise le panneau mais pas le clavier), deux
>   onglets. **Le compteur ne pouvait pas protéger : c'est une LECTURE**, et
>   deux imports la font en même temps. Remède en trois pièces — temporaire
>   unique (`img_{n}.{uuid}.tmp`), numéro **RÉSERVÉ** par `O_CREAT|O_EXCL` avec
>   passage au suivant sur collision (leçon de la création exclusive 2c), et
>   plafond **recompté après la réservation sur les numéros jusqu'au nôtre** (le
>   premier arrivé garde sa place, le surnuméraire rend la sienne — sans quoi
>   deux imports partis à 11 images auraient tous deux écrit la 13e). Plus une
>   garde de vol à l'écran : le second import est un NON-DÉPART. Test : 6 POST
>   `asyncio.gather` → 6 noms distincts, 6 tailles distinctes sur le disque,
>   zéro 500, zéro `.tmp` survivant. La mutation a changé de cible avec le
>   remède : un compteur qui MENT (toujours « 1 ») ne fait plus perdre aucune
>   image, alors qu'avant il écrasait.
> · **M3 — bombe de pixels, sur les DEUX portes.** Le corps est pesé (64 Mo),
>   la TRAME ne l'était pas : un PNG de zéros de moins d'un mégaoctet déclare
>   12000 x 12000, soit 144 Mpx, soit un demi-gigaoctet de tampon par requête —
>   et le plafond par défaut de la bibliothèque se contente d'AVERTIR jusqu'à
>   179 Mpx avant de décoder quand même. `IMG_MAX_PIXELS = 32 Mpx` (large pour
>   une image ramenée à 4096 px de côté), lu dans l'EN-TÊTE **avant** `load()`,
>   refus 413 nommé avec les dimensions. **`texture.py:_store_image` avait la
>   même forme et est corrigé dans la même passe**, avec son test — les deux
>   pièces portent le même chiffre, recopié et non partagé (règle 8).
> · **M4 — le refactor avait fait SORTIR le HTML du champ de R14.** `inspHead`,
>   `inspPlaque`, `inspBoite` et `imgMeasInner` RETOURNENT des chaînes : ni nom
>   en `Html|paint`, ni sink `innerHTML =`. Mutation de contrôle : dé-échapper
>   `esc(s.label)` dans `inspHead` rendait **zéro signalement**. Troisième
>   critère ajouté, du même principe qu'en T1 (le fait, pas l'intention) :
>   `return '<` — cherché dans `sans_com` (chaînes intactes) avec le délimiteur
>   vérifié sur `masque`, pour qu'un `return '<` ÉCRIT DANS un texte affiché
>   n'en soit pas un. **Différentiel mesuré : +29 fonctions balayées sur les 9
>   pièces** (mod-type +15, mod-face +6, les autres 1 à 2), **0 nouveau
>   signalement**, coût 1,26 → 1,30 s. La mutation est désormais ATTRAPÉE.
> · **L5 — le lecteur d'image n'avait pas sa ceinture.** Mesuré, et c'était
>   pire qu'annoncé : `_read_slot_image(did, "../meta.json")` rendait l'état
>   interne du jeu. La route filtrait, la fonction non — alors que c'est ELLE
>   qui compose le chemin. Doctrine `deck_dir` (motif PUIS confinement)
>   appliquée là où le chemin naît ; un ramasse-miettes de la 3c ou une palette
>   T3 qui l'appellerait n'héritait de rien.
> · **L6 (pré-existant, adjacent) — `contract.is_valid_did` lisait son motif
>   avec `match`.** `$` accepte un saut de ligne FINAL : `"deck_a1b2c3d4\n"`
>   passait, ressortait de `deck_dir` en chemin valide, et aurait fait naître un
>   dossier de jeu au nom invisible. C'est le piège que ce dépôt nomme deux fois
>   dans ses propres commentaires. Passé en `fullmatch`, avec cinq entrées de
>   plus dans le test de traversée (saut de ligne, CRLF, espaces de tête et de
>   queue) et un pin sur le mot `fullmatch` lui-même. **52 appelants, une seule
>   porte** — suite cards entière relancée.
> · **Avenants.** (a) La police du damier n'était jamais chargée quand un deck
>   ne portait que des calques d'image : le nom du fichier manquant se composait
>   dans la fonte de repli à la première frame et dans la bonne à l'export —
>   deux rendus différents du même document, sur des octets qui partent à
>   l'impression. `DAMIER_FONT` est désormais joint aux familles attendues,
>   **et seulement quand un damier va vraiment être peint** (on ne le sait
>   qu'APRÈS la course des images). (b) Le compte du message d'import est
>   recompté sur le disque APRÈS l'écriture (`n` / `max`, « 2 / 12 ») : calculé
>   avant la réservation, il mentait dès que deux imports se croisaient.
> · **Compte** : 152 → **162 tests** dans test_cards_type.py (+10),
>   test_cards_texture.py +1 (la bombe), test_cards_core.py amendé (traversée).
>   Lint intégral 0 avec le critère élargi.

> **CLOSE (T2 — 5d51744 + ronde 4c588d4, revue adverse : FIX-FIRST soldé).**
> Le calque d'image est un slot ORDINAIRE (39 clés, presets FNV-identiques,
> contain/cover mesurés au pixel avec clip SOUS rotation, plaque dessous,
> zéro passe de glyphe) ; QUATRE passes d'encre trouvées et gardées (la 4e —
> le contrôle de série :4637 — aurait compté un calque « vide » sur 200
> cartes) ; route à compteur max+1 jamais recyclé, whitelist avant le
> disque, Cache-Control immutable. **B1 de revue : la garde nulle sur
> l'opérande testé, pas le résultat** → src="undefined" sur chaque slot
> pré-3b, normaliseur non idempotent — LE VRAI DÉFAUT ÉTAIT LE TEST (parité
> par source-match) : remplacé par la parité d'EXÉCUTION (13 entrées
> clé-à-clé, idempotence JS, les 21 slots de presets assertés
> norm_slot(s)==s — le backend n'a RIEN à réparer). **B2 : la course
> d'upload** (6 concurrents → 1 fichier, 4 confirmés sur img_1, 2 vrais
> 500 — le double Ctrl+V l'atteignait) → réservation O_CREAT|O_EXCL à tmp
> unique + n-suivant-sur-collision + plafond RE-COMPTÉ après la
> revendication + garde de vol client. M3 : bombe de pixels bornée à
> l'EN-TÊTE avant load() (32 Mpx nommés), type.py ET texture.py (même forme
> mesurée). M4 : le refactor avait sorti 4 fabriques HTML du champ R14
> (elles RETOURNENT sans sink) → 3e critère `return '<` (délimiteur vérifié
> contre le masque), +29 fonctions, 0 faux positif. L5 pire qu'annoncé (le
> lecteur rendait meta.json) → ceinture à la naissance du chemin. L6 :
> is_valid_did en fullmatch (52 sites, une porte). Avenants : la police du
> damier jointe aux familles attendues SEULEMENT quand un damier va
> vraiment se peindre (déterminisme premier-frame/export) ; toast re-compté
> du disque APRÈS l'écriture. 162 tests, 11/11 suites, lint 0 au critère
> élargi. mod-type.js +500 l. nets déclarés (T4 vise plus court).

### Task 3 : la palette d'éléments

**Files:** mod-type.js, test_cards_type.py (+ css) **+ core.js (amendement
T3 : la capacité de lecture `CF.models`, 42 lignes — voir la note)**.

- [x] Palette (~~panneau + overlay~~ **barre du panneau seule, amendé**) :
      zone de texte / zone de statistique
      (paire étiquette+valeur généralisée — 2 slots liés par la naissance,
      pas par un lien persistant) / calque d'image / + les éléments du
      MODÈLE (~~fetch /models, cache par preset~~ **`CF.models`, cache du
      CORE, offres dérivées du preset à la peinture**, tolérance totale : pas
      de modèle → les 3 génériques seuls ; éléments absents → dit).
- [x] Instanciation : append + uniquification d'ids CLIENT (la règle
      serveur norm_slots — renommer, jamais jeter — recopiée et ÉPINGLÉE
      contre type.py par un test de parité de comportement) ; UNE entrée
      HIST ; sélection posée sur le premier slot né ; plafond SLOTS_MAX
      respecté AVANT (refus nommé).
- [x] ~~GEN/génération : garde sur le changement de deck~~ **MESURÉ ET
      RÉFUTÉ (voir la note) : changer de jeu est une NAVIGATION, le cache
      meurt avec la page, et le catalogue n'est pas propre à un jeu. La
      garde qui existe VRAIMENT est celle de l'ouverture du menu (`PAL_SEQ`),
      la seule chose qui change sous une réponse en vol.**
- [x] Banc : les 3 génériques + un élément de modèle réel (superstar
      stat7) ; collision d'ids (élément ajouté 2×) → renommage identique au
      serveur ; plafond ; RED d'abord.

> **Livré (T3)** — 162 → **183 tests** (+21, 0 supprimé, 0 amendé).
> mod-type.js **+281 lignes nettes** (4984 → 5265 l.), core.js +42, css +12.
> Au-dessus des ~250 visés, sous les 400 du plan — la moitié du volume est en
> commentaires (le pavé de la section 6bis PORTE la décision d'architecture,
> c'est là qu'elle se relira).
> Lint intégral 0, `node --check` OK sur les deux JS, batterie `--geom` du
> contrat OK.
>
> · **LA QUESTION D'ARCHITECTURE DE LA TÂCHE — par où P3 lit le catalogue.**
>   Le plan disait « fetch /models » sans dire PAR OÙ, et il n'y avait pas de
>   voie légale : `M.api` est confiné à `/api/cards/<did>/type` (core.js:
>   `subPath` LÈVE sur un chemin absolu et sur `..`) tandis que la liste vit
>   à `/api/cards/models`, hors de tout sous-préfixe de pièce. Trois voies
>   pesées, deux fermées : (a) un `window.fetch` nu — **rien ne l'attrape**,
>   ni le lint (aucune règle réseau : R1-R14 relues) ni le CORE (`fetch`
>   reste sur le global, il n'y a ni CSP ni Proxy) : le confinement est une
>   DOCTRINE, et c'est précisément pour cela qu'un seul module qui la casse
>   la casse pour les huit autres — mesuré : **zéro `fetch(` dans les neuf
>   `mod-*.js` aujourd'hui**, épinglé désormais ; (b) une table de modèles
>   recopiée à l'écran — refusée EXPLICITEMENT par le banc du contrat
>   (« prouver que l'écran consomme GET /api/cards/models et non une table
>   recopiée »), et un modèle PERSO n'y serait jamais.
>   **Retenu : le CORE expose la lecture — `CF.models`, le patron `CF.images`
>   (« le SEUL dehors, tenu par le CORE »).** Et la doctrine n'est pas le
>   seul argument : cette liste est **déjà chargée et cachée dans le CORE**
>   pour la galerie de démarrage (`galModelsList`). Une seconde copie dans
>   P3, c'étaient deux requêtes et deux caches de la même liste, dont l'un
>   devenait faux dès le premier « enregistrer comme modèle » (seul celui du
>   CORE est rafraîchi ; formulation corrigée par la ronde — voir N2 : un cache
>   d'AUTORITÉ et un INSTANTANÉ, pas « deux caches »). La copie rendue est
>   **profonde et gelée** — sans
>   quoi le premier module qui écrit dedans empoisonne la galerie et les huit
>   autres pièces dans le même onglet (le raisonnement de `models.model()`
>   côté backend, appliqué à l'écran) — et une route absente rend une LISTE
>   VIDE, pas une panne (même règle que `images.models`). Aucune écriture
>   n'est ouverte : POST/DELETE /models restent au CORE.
>   **Le registre n'a pas eu à bouger** : `CF.models` est sur le GLOBAL, pas
>   sur le jeton — la batterie du contrat n'énumère ni les clés de `CF` ni
>   celles du jeton (vérifié), donc aucun pin de contrat à amender.
>   `test_cards_core.py` reste vert.
>
> · **LA GARDE QUE LE PLAN DEMANDAIT N'EXISTE PAS, ET C'EST MESURÉ.** Le plan
>   voulait une étiquette de deck avant l'écriture du cache (leçon C1).
>   Vérification : **changer de jeu est une NAVIGATION** — `core.js:galGo`
>   fait `location.assign` (repli `location.reload`), donc la fermeture du
>   module, le cache et la requête en vol meurent avec le document ; et le
>   catalogue **n'est pas propre à un jeu** (GET /models ne prend pas de
>   `did`), donc il n'y a rien de deck-shaped à invalider. Une étiquette de
>   deck ici aurait été du code mort faisant CROIRE qu'un danger est couvert.
>   Ce qui change vraiment sous une réponse en vol, ce sont **le preset**
>   (poser un gabarit le réécrit sans recharger) et **l'ouverture du menu**.
>   D'où les deux vraies protections, et elles sont de nature différente :
>   le preset est traité **par construction** (le cache porte le catalogue
>   ENTIER, les offres se dérivent du preset au moment de peindre — il n'y a
>   pas de drapeau à oublier) ; l'ouverture, elle, a une étiquette
>   (`PAL_SEQ`), et le banc la mesure en ouvrant DEUX menus pendant qu'UNE
>   requête est en vol (catalogue ralenti à 150 ms) : le premier reste à
>   trois entrées, le second en reçoit quatre. Garde retirée par mutation →
>   le menu fermé se fait repeindre → rouge.
>
> · **L'uniquification est le MIROIR EXACT de `norm_slots`, prouvé par
>   EXÉCUTION** (leçon B1 : un match de source ne dit rien de ce que le code
>   FAIT). `normSlots` normalise PUIS renomme, dans cet ordre, et le suffixe
>   reprend l'id ENTIER (« stat7 » → « stat72 »). Batterie de 8 collisions
>   jouée des deux côtés, comparée clé par clé — dont **le cas à 24 signes**,
>   la borne du motif d'id : le suffixe la dépasse et le serveur **ne
>   re-valide pas** après avoir renommé. C'est CE cas qui a décidé que
>   `naitre` écrit par `mpatch` et non par `commit` : `commit` repasse tout
>   dans `normSlot`, qui aurait remplacé l'id renommé par « slotN » — une
>   divergence avec le serveur créée par la normalisation elle-même.
>   Ce qui n'est PAS recopié du serveur : la troncature `rows[:SLOTS_MAX]`.
>   Le plafond est dit AVANT avec son arithmétique ; le recopier ici en
>   aurait fait une coupe MUETTE, et cette pièce n'en fait pas.
>
> · **Une naissance = une porte.** Les quatre naissances (texte,
>   statistique, image, élément de modèle) passent par `naitre` : c'est la
>   seule façon que « une entrée d'annulation par geste », « la sélection sur
>   le premier né » et « le plafond compté avant » tiennent toutes les trois
>   sans être réécrites quatre fois (la leçon de `soloClone`, prise avant la
>   quatrième copie ; pin : UN SEUL `pushUndo()` dans la zone des
>   naissances, et zéro `commit(`). Le refus de plafond porte son
>   arithmétique — « 39 slot(s) + 2 = 41, le maximum est 40 » — au lieu du
>   « 40 slots au maximum » d'avant, qui ne disait pas combien il en manque ;
>   et un élément est refusé ENTIER, jamais posé à moitié.
>
> · **La zone de statistique générique** reprend la FORME de
>   `models.py:_duel_ligne` (étiquette à gauche, valeur à droite, boîtes
>   adjacentes) sans son habillage : ni plaque zébrée ni encre de duel — un
>   cartouche isolé n'est pas un tableau. **Écart assumé au « polices neutres
>   de SLOT_DEFAULTS » du plan : la valeur naît en JetBrainsMono.** Ce n'est
>   pas un goût — une colonne de chiffres composée dans une proportionnelle
>   danse d'une carte à l'autre du jeu, c'est un défaut de SÉRIE, et c'est
>   justement ce que le contrôle de série de cette pièce mesure. Un clic
>   suffit à en changer. Les deux blocs ne sont **pas liés ensuite** : ils
>   naissent ensemble puis vivent seuls (aucune clé de document ne les
>   apparie — la spec n'en nomme aucune, et une paire dont on supprime la
>   moitié n'a rien d'invalide).
>
> · **La palette DIT, elle ne se contente pas d'être courte.** Quatre états
>   nommés : catalogue en route, catalogue injoignable (avec la phrase du
>   backend — et un CORE plus ancien que la pièce le dit aussi, au lieu de
>   lever « CF.models is not a function »), modèle SANS éléments (nommé, avec
>   son libellé), et **le silence — réservé au seul cas où il n'y a rien à
>   dire** : ce jeu ne vient pas d'un modèle (un gabarit local n'en est pas
>   un). Un élément sans slot ne compte pas, même règle qu'au backend
>   (`_elements_normalises`) : ce serait un bouton qui ne pose rien.
>   Dans tous les cas les trois génériques restent OFFERTS ET POSABLES —
>   testé : catalogue absent, on pose quand même une zone de texte.
>
> · **R14 et l'échappement.** Tout ce qui vient du catalogue traverse `esc` —
>   libellés et phrases d'un modèle PERSO sont un fichier JSON du dossier de
>   données, donc de la donnée serveur écrite par quelqu'un. Les deux
>   positions sont couvertes par DEUX cliquets différents, et c'est
>   volontaire : `data-o="…"` est une valeur d'ATTRIBUT, **R14 la juge
>   mécaniquement** (mutation : `esc(o.id)` → `o.id`, le lint sort 1 et
>   nomme R14 — vérifié dans une copie du dépôt) ; le `hint` est en position
>   TEXTE, que la règle déclare hors de sa portée depuis la T1 — c'est donc
>   le BANC qui le tient (mutation : `esc(o.hint)` → `o.hint`, le `<img>` du
>   poison réapparaît dans le menu rendu).
>
> · **Pourquoi pas de bouton sur le calque d'édition** (le plan disait
>   « panneau + overlay ») : `paintOverlay` réécrit tout son innerHTML à
>   chaque frame d'un glisser (coalescé au rAF). Un contrôle qui vit là est
>   recréé et recâblé à 60 Hz, sur la carte, à l'endroit exact où la main
>   glisse. Poser un élément est un acte d'INTENTION, pas un geste de scène :
>   sa place est la barre, où « + Slot » et « + Image » vivent déjà.
>
> · **Mutations qui tuent** (6, toutes jouées) : suffixe d'uniquification
>   d'une autre forme (`stat7_2`) → parité rouge ; paire née en DEUX gestes →
>   un Ctrl+Z n'en défait qu'un, rouge ; plafond non compté → 41 slots,
>   rouge ; garde d'étiquette retirée → le menu fermé repeint, rouge ;
>   `esc(o.hint)` retiré → poison rendu, rouge ; `esc(o.id)` retiré → R14
>   sort 1. **RED d'abord vérifié en bloc** : les 21 tests neufs joués contre
>   le dépôt sans l'implémentation (mise de côté par `git stash`) → **21/21
>   rouges**, puis verts.
>
> **Reste à l'œil (2 min)** : ouvrir « + Élément » dans le vrai navigateur
> sur un jeu né de « Superstar du stade » — vérifier que « 7e statistique »
> y est avec sa phrase, qu'un clic la pose à sa zone avec sa plaque, qu'un
> second clic pose « stat72 », et qu'une zone de statistique générique naît
> bien en deux boîtes accolées.

> **RONDE DE REVUE (T3) — FIX-FIRST, 3 correctifs + 4 notes prises + 2
> consignées + le test de rotation de la T2 enfin joué.** Ce que la revue a
> mesuré et que la livraison n'avait pas vu :
>
> · **F1 — Échap ne fermait rien sur un jeu VIDE.** La branche était SOUS
>   `if (!s) return`, et `selSlot()` est nul EXACTEMENT quand le document n'a
>   aucun bloc — c'est-à-dire l'état d'un jeu neuf, celui où l'on ouvre
>   justement la palette. Mesuré : jeu vide + Échap → la réponse du catalogue
>   revenait repeindre un menu que l'utilisateur croyait fermé. La branche est
>   hissée au-dessus de la garde (elle n'a pas besoin de sélection) ; **le même
>   défaut cachait l'Échap du menu de POLICES, et il est plus vieux que cette
>   tâche** — les deux fermetures remontent ensemble. Mutation : branche
>   redescendue → le menu fermé se fait repeindre, rouge.
>
> · **F2 — UN espace de noms, DEUX vocabulaires : « arcane » collisionnait
>   DÉJÀ.** `doc.type.preset` recevait les clés des quatre gabarits locaux
>   (`applyPreset`) ET les identifiants de modèles (`instancier`). « arcane »
>   est les deux : un deck posé sur le GABARIT se voyait offrir les quatre
>   éléments de l'archétype d'usine — sur un design dont il n'était pas né,
>   c'est-à-dire l'inverse exact de ce que la §6bis affirmait. Et rien
>   n'empêchait un perso nommé « Champion » de reproduire le cas sur les trois
>   autres (`_slug` réserve les ids d'usine, pas les clés de gabarits).
>   **Retenu : (a), la PROVENANCE dite à la naissance** — `models.py:
>   PRESET_MODELE = "modele:"`, `instancier` écrit `preset = "modele:<id>"`.
>   Les deux sens sont fermés PAR CONSTRUCTION et non par une liste de noms
>   réservés à tenir à jour : ni une clé de gabarit ni un slug
>   (`[^a-z0-9]+` → `-`) ne peut contenir « : ». **(b) écartée pour deux
>   raisons mesurées** : renommer le gabarit « arcane » est une rupture de
>   parité JSON dans `type.py` (le miroir byte-à-byte des quatre gabarits), et
>   surtout la collision SURVIVAIT pour l'existant — un vieux deck au preset
>   « arcane » re-matchait le modèle. Une troisième voie (« refuser un preset
>   qui est aussi une clé de gabarit ») a été écartée par mesure inverse :
>   elle aurait rendu le modèle d'usine « arcane » inatteignable pour les decks
>   qui en naissent VRAIMENT.
>   **La provenance vient de l'IDENTITÉ, pas de ce que le modèle DÉCLARE** :
>   `m["type"]["preset"]` n'est plus lu, parce que sur un perso il porte ce que
>   SON deck d'origine déclarait — donc, depuis ce changement, la provenance
>   d'un AUTRE modèle. Un deck né de « mon-modele » aurait annoncé venir de
>   « superstar ».
>   **Ce que ça ne rattrape pas, écrit plutôt que caché** : un deck instancié
>   AVANT ce changement porte l'id nu, indiscernable d'une clé de gabarit.
>   L'écran ne devine pas — deviner est exactement ce qui a produit le défaut —
>   donc il ne propose rien ; la palette étant née avec cette ronde, aucun
>   comportement existant ne se perd, et recréer le jeu depuis la galerie
>   rétablit la provenance. Fichiers : `models.py` (+ constante et
>   `instancier`), `test_cards_models.py` (la parité 3a amendée À LA SOURCE +
>   un test neuf), **`qa/test_core_contract.mjs`** (le pin de relecture SUR LE
>   DISQUE attendait `preset === 'superstar'`), `mod-type.js`. Mutation :
>   `modelCourant` remis à l'id nu → le deck-gabarit « arcane » reçoit de
>   nouveau les éléments du modèle, rouge.
>
> · **F3 — deux états muets, nommés.** (a) le preset désigne un modèle ABSENT
>   d'un catalogue CHARGÉ (perso supprimé, jeu rapporté d'une autre machine) :
>   « le modèle « X » n'est plus servi par ce backend » — « ce jeu n'a pas de
>   modèle » et « le sien n'est plus là » ne se réparent pas pareil.
>   (b) **`!MODELS` est FAUX pour un tableau vide** : la liste vide que
>   `modelsPublic` fabrique quand la route est absente ne disait rien du tout.
>   Or tout backend qui a la route sert au moins les sept archétypes d'usine :
>   une liste vide ne veut pas dire « ce poste n'a pas de modèles », elle veut
>   dire « personne n'a répondu ». Le cas (b) est désormais éprouvé **de bout
>   en bout** (banc du CORE ci-dessous), pas seulement côté écran.
>   **Et un PIN D'AVANT a attrapé les deux phrases** : le panneau de cette
>   pièce ne dit ni « backend » ni « verdict » (« un panneau de produit parle
>   du produit »), et mes deux notes disaient « servi par ce backend ». Elles
>   parlent maintenant du POSTE ; le diagnostic technique, lui, n'est pas perdu
>   — il est passé dans l'INFOBULLE de la phrase, où celui qui le cherche le
>   trouve et où il n'encombre personne. Le message de repli d'un CORE trop
>   ancien a été réécrit dans la même langue.
>   **Conséquence : une valeur d'attribut de plus, et R14 NE LA VOIT PAS.** La
>   règle ne juge que les lectures POINTÉES (`a.b`) ; `title="' +
>   esc(MODELS_ERR) + '"` est une variable NUE. L'élargir aux identifiants nus
>   ferait rougir tout `class="' + cls + '"` du dépôt — la limite est donc
>   NOMMÉE (dans le code, et par un test qui vérifie que R14 sort bien 0 sur ce
>   mutant-là, pour que le jour où la règle grandira on s'en aperçoive) et
>   l'échappement est tenu par le BANC : message d'échec empoisonné, rendu
>   relu, mutation `esc` retiré → le `<img>` sort, rouge.
>
> · **N1 — LE BANC DU CORE, et c'est le vrai apport de la ronde.** La copie
>   profonde gelée de `CF.models` était épinglée par MATCH DE SOURCE : le
>   mutant qui rend une copie NON gelée passait, `deepFreeze` restant écrit
>   ailleurs dans le fichier. Le banc charge le VRAI `core.js` dans un `vm`
>   sans DOM (patron `qa/test_core_contract.mjs:loadCF`) avec `fetch`
>   bouchonné, puis **ÉCRIT vraiment** dans ce que la capacité a rendu — mode
>   strict, donc une copie gelée LÈVE — et relit pour prouver que le cache de
>   la galerie n'a pas bougé. Deux mutants tuent : copie sans gel (les
>   écritures passent) et **pas de copie du tout (le cache du CORE répond
>   « PIRATE » à la lecture suivante)**. Le banc pin aussi « UNE requête, un
>   cache » (la seconde lecture ne repart pas au réseau) et les deux branches
>   d'erreur : route absente → liste VIDE, backend qui parle → l'erreur REMONTE.
>
> · **N3 — la bascule de pièce AU CLAVIER orphelinait le popover.** Il vit sur
>   `document.body` ; Entrée sur le rail produit un `click` sans `pointerdown`,
>   donc la fermeture au clic dehors ne court pas et le menu restait seul
>   au-dessus d'un autre module. Il part maintenant avec la classe du panneau —
>   le MutationObserver du calque d'édition, même raison. Le banc a reçu un
>   `MutationObserver` de paille (node n'en a pas) : sans lui, cette branche
>   n'était pas même POSÉE au banc. Mutation : observateur remis à son ancien
>   corps → le menu survit, rouge.
>
> · **N4 — `MODELS_ERR` survivait au départ du retry**, si bien que la palette
>   disait « injoignable » pendant qu'une requête FRAÎCHE volait : l'état faux,
>   au moment précis où l'utilisateur refaisait le geste. Nettoyé à l'entrée
>   d'`ensureModels` — **et la demande PART désormais AVANT la première
>   peinture**, sans quoi le correctif restait invisible (la note est peinte
>   synchroniquement, elle affichait donc encore l'échec d'avant). Mutation :
>   nettoyage retiré → « injoignable » sur la 3ᵉ ouverture, rouge.
>
> · **N2 — la note de livraison disait faux.** Ce n'était pas « deux requêtes
>   et deux caches » : la galerie en aurait fait une et P3 une autre, soit
>   **une requête de plus et un second cache — un cache d'AUTORITÉ (celui du
>   CORE, rafraîchi par « enregistrer comme modèle ») et un INSTANTANÉ en
>   lecture qui, lui, ne se serait jamais rafraîchi**. C'est cet instantané qui
>   devenait faux, pas « l'un des deux ».
>
> · **Consignés, non corrigés.** **N5** : le renommage peut fabriquer un id de
>   plus de 24 signes (`aaa…a` + `2`), que `normSlot` refuserait s'il y
>   repassait — hérité de `norm_slots`, parité TENUE des deux côtés (c'est la
>   raison pour laquelle `naitre` n'appelle pas `commit`) ; le corriger
>   demanderait de changer le SERVEUR, donc une passe à lui seul. **N6** :
>   `normSlot` singulier diverge de `norm_slot` sur les blancs et les valeurs
>   falsy (pré-T1) ; la batterie de parité ne fait varier que l'`id`, elle ne
>   l'aurait pas vu. À reprendre dans une passe de parité dédiée.
>
> · **LE TEST DE ROTATION DE LA T2, écrit et jamais exécuté, est joué.** Déposé
>   en section 11.4. Son auteur avait prévu ±2 px « au premier run » en
>   RAISONNANT ; **mesure : l'écart maximum est de 0,39 px** sur les huit
>   valeurs — la tolérance est donc RESSERRÉE à ±1 px (l'arrondi
>   d'échantillonnage au demi-pixel, et rien d'autre : à ±2, une dérive d'un
>   pixel serait passée). Le mutant demandé — **le clip hissé HORS de la
>   rotation**, le refactor plausible (« il ne dépend que de la boîte, sortons-le
>   de la branche ») — est joué et rougit : l'image déborde de sa boîte visible
>   sur ses deux petits côtés.
>
> · **Compte** : 183 → **199 tests** dans test_cards_type.py (+16 : 14 pour la
>   ronde, 2 pour la rotation ; 2 amendés — le pin R14 et la formulation du
>   catalogue injoignable — et les presets de modèle préfixés dans 9 autres) ;
>   test_cards_models.py 154 → **155**. mod-type.js 5265 → 5344 l. (+79 nets),
>   models.py +26, qa/test_core_contract.mjs +6, **core.js inchangé par la
>   ronde**. Lint intégral 0, `node --check` OK, batterie `--geom` du contrat
>   OK, 11/11 suites cards vertes.
>
> **Reste à l'œil (+1 min)** : sur un jeu VIDE, ouvrir « + Élément » puis
> Échap — le menu doit partir ; et changer de pièce au CLAVIER pendant que le
> menu est ouvert.

### Task 4 : la liste de calques multi-bandes

**Files:** mod-type.js, mod-type.css, test_cards_type.py (+ core.js SEULEMENT
si une capacité « aller au module » doit naître proprement — la vérifier
d'abord, et alors qa/pins). **Note T3 : core.js a DÉJÀ reçu une capacité de
lecture (`CF.models`, §9bis + la clé sur le global gelé) ; le patron et son
pin existent donc — `test_P3_lit_le_catalogue_par_LE_CORE_et_par_AUCUN_RESEAU_NU`
dans test_cards_type.py. La batterie du contrat n'énumère pas les clés de
`CF` ni celles du jeton : une capacité de LECTURE sur le global ne demande
pas d'amender qa/. Une capacité qui AGIT (« aller au module » = `CF.show`)
n'est pas le même objet — la peser à part.**

- [ ] Section « Calques » : bandes fixes en lecture (10 papier / 20
      illustration / 30 effet / 40 cadre / 70 décor haut — libellé + résumé
      dérivé de l'état publié + « aller au module ») ; bande 60 = la liste
      slots EXISTANTE (œil/verrou/ordre/badges kind) intégrée sous la rangée
      40 et sur la rangée 70 (l'ordre VISUEL = l'ordre de peinture réel,
      c'est le point).
- [ ] « Aller au module » : vérifier ce que les jetons peuvent faire —
      sinon, le clic simule le rail (patron mod-data:focusCard « on pilote
      les BOUTONS du CORE ») ; AUCUNE écriture inter-modules.
- [ ] Pins : l'ordre affiché des bandes == Z_TABLE (dérivé, pas recopié) ;
      les rangées fixes n'émettent aucun patch ; la bande 60 réordonne
      comme avant (les pins existants tiennent).

### Task 5 : intégration 3b

- [ ] Suite cards complète, lint intégral 0 (R14 élargi compris), contrat,
      node --check, cf_deploy -Backend + -Check 0 écart.
- [ ] Navigateur réel : instancier superstar → palette montre « 7e
      statistique » → l'ajouter → elle naît à sa zone avec sa plaque ;
      ajouter une zone de statistique générique ; importer un calque
      d'image (dépôt) → il se peint dans sa boîte, drag/poignées/rotation ;
      verrouiller → le drag refuse, le panneau édite ; œil ; réordonner →
      la peinture suit ; la liste de calques montre les bandes dans l'ordre
      réel ; nudge 1/0,2 senti ; Ctrl+D/Delete/undo.
- [ ] Plan+mémoire+push ; restes à l'œil.

## Auto-revue du plan

- Le kind image dans P3 est LA lecture de la spec qui maximise le réemploi
  (overlay/ordre/œil/verrou/HIST/fluidité gratuits) ; l'alternative « pile
  de calques P2 » restructurerait le plus gros fichier du lab pour un
  résultat équivalent à l'écran.
- Stockage serveur deck-scoped : voyage avec le deck (duplication 3a le
  copie déjà), pas d'IndexedDB browser-local pour un ASSET de deck.
- La liste multi-bandes ne lit que l'état PUBLIÉ et n'écrit jamais hors
  jeton — le cloisonnement de la 3a-T4 reste entier.
- Risques nommés : mod-type.js grossit (annoncer si >400 l. nets/tâche) ;
  la parité JSON stricte à CHAQUE ajout de clé ; les passes d'encre face
  aux slots image (exclusion testée) ; ~~le fetch /models async sous
  changement de deck (garde par étiquette — le C1 ne se refera pas une
  4e fois)~~ **RÉFUTÉ EN T3, mesuré : changer de jeu est une navigation
  (`galGo` → `location.assign`), le cache et la requête en vol meurent avec
  la page, et le catalogue n'est pas propre à un jeu. La garde réelle est
  celle de l'OUVERTURE du menu, et le preset est traité par construction
  (offres dérivées à la peinture). Risque non nommé par le plan et trouvé en
  T3 : le plan supposait que P3 POUVAIT atteindre /models — `M.api` le
  refuse, la voie a dû naître (voir la note T3)** ; « aller au module » sans
  nouvelle surface de pouvoir pour les jetons.
- Hors périmètre 3b, consigné : motifs du catalogue (3c, avec le Sceau),
  GC des images orphelines (3c), multi-sélection (jamais demandée),
  calques sous l'illustration (z<20 — demanderait une bande nouvelle).
