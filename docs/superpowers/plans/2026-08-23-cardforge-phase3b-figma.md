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
  complètes]}` (models.py:172, exemple :277-286 ; paire étiquette+valeur =
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
  patch/frame. **Écart de nudge** : la spec nomme le patron P2 (« pas 1 mm,
  Maj = 0,2 mm » :307) ; P3 fait 0,5 / Maj=5 (:228) — l'INVERSE de Maj.
- **Notes T1-3a à solder ici** : les 3 passes d'encre dupliquent l'objet de
  neutralisation (:3410/:3704/:3908 — helper partagé demandé) ; le filtre
  R14 (`Html|paint`) ne balaie ni renderInsp ni les futures galDraw-like ;
  la branche arcTo du banc inexerçable (accumulation de chemin à ajouter si
  bon marché).
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
3. **La palette d'éléments vit dans P3** (panneau + bouton overlay) : trois
   entrées GÉNÉRIQUES toujours là — « zone de texte » (addSlot d'aujourd'hui),
   « zone de statistique » (paire étiquette+valeur, la forme _duel_ligne
   généralisée), « calque d'image » — PLUS les éléments du MODÈLE quand
   `doc.type.preset` correspond à un modèle servi (fetch /models une fois,
   cache par preset, 404/absence tolérée : la palette dit « modèle sans
   éléments » ou rien). Instanciation = append des slots de l'élément avec
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

- [ ] `lock` 36e clé (parité JSON stricte, presets byte-identiques) ; overlay
      et clavier REFUSENT drag/resize/nudge/delete sur un slot verrouillé
      (sélection et panneau libres) ; badge cadenas (liste + hbox).
- [ ] Nudge 1 mm / Maj 0,2 mm (pin ; l'ancien 0,5/5 mort).
- [ ] `soloClone` : les 3 sites (:3410/:3704/:3908) passent par le helper,
      pin de compte (== 3 aujourd'hui, le message dit pourquoi).
- [ ] R14 : filtre de noms élargi (renderInsp, galDraw*, et le futur
      paletteHtml de la 3b) — le lint intégral reste 0 sur tout le dépôt
      (si l'élargissement révèle un site réel non échappé : le corriger,
      c'est le but).
- [ ] Mutation : verrou ignoré au drag (rougit), nudge à 0,5 (rougit),
      soloClone contourné (compte rougit).

### Task 2 : le calque d'image (kind + route + painter + éditeur)

**Files:** mod-type.js, type.py, test_cards_type.py (+ mod-type.css).

- [ ] Vocabulaire : `kind` ("text"|"image", défaut "text"), `src`, `fit`
      (contain|cover) — 39 clés, parité, presets intacts.
- [ ] Backend : `POST /type/image` (raw body, patron texture.py:post_paper,
      `img_{n}.png` compteur SANS écrasement, plafonds nombre=12/taille/
      MAX_IMPORT_PX, jamais-500 nommé) + `GET /type/image/{name}` (whitelist
      du motif de nom, no-store ? NON — cache ok, fichiers immuables par
      compteur) + purge à la suppression du slot ? NON — les fichiers
      restent (un slot supprimé peut être annulé) ; un GC honnête = 3c, dit.
- [ ] Painter z=60 : un slot image dessine son image dans sa boîte (fit,
      rotation, opacité, plaque DESSOUS), cache d'Image objets (patron
      IMGS — l'aperçu ne re-décode pas à chaque frame) ; image absente/404 =
      damier + nom (état, pas d'erreur) ; slots image EXCLUS des 3 passes
      d'encre et du juge de lisibilité (sans objet — testé).
- [ ] Éditeur : le panneau de slot bascule ses sections selon kind (typo
      masquée pour image ; import par dépôt/collage — patrons mod-face,
      réduction client MAX_IMPORT_PX avant envoi) ; « + calque d'image »
      dans la palette T3.
- [ ] Banc : painter image mesuré au pixel (fit contain vs cover, opacité,
      plaque dessous, rotation) ; la route bornée (13e image → refus nommé) ;
      RED d'abord partout.

### Task 3 : la palette d'éléments

**Files:** mod-type.js, test_cards_type.py (+ css).

- [ ] Palette (panneau + overlay) : zone de texte / zone de statistique
      (paire étiquette+valeur généralisée — 2 slots liés par la naissance,
      pas par un lien persistant) / calque d'image / + les éléments du
      MODÈLE (fetch /models, cache par preset, tolérance totale : pas de
      modèle → les 3 génériques seuls ; éléments épuisés ou absents → dit).
- [ ] Instanciation : append + uniquification d'ids CLIENT (la règle
      serveur norm_slots — renommer, jamais jeter — recopiée et ÉPINGLÉE
      contre type.py par un test de parité de comportement) ; UNE entrée
      HIST ; sélection posée sur le premier slot né ; plafond SLOTS_MAX
      respecté AVANT (refus nommé).
- [ ] GEN/génération : le fetch /models est async — garde sur le changement
      de deck (le cache meurt avec le deck ; patron MANIFEST 2d-T2 : garde
      par étiquette AVANT l'écriture du cache).
- [ ] Banc : les 3 génériques + un élément de modèle réel (superstar
      stat7) ; collision d'ids (élément ajouté 2×) → renommage identique au
      serveur ; plafond ; RED d'abord.

### Task 4 : la liste de calques multi-bandes

**Files:** mod-type.js, mod-type.css, test_cards_type.py (+ core.js SEULEMENT
si une capacité « aller au module » doit naître proprement — la vérifier
d'abord, et alors qa/pins).

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
  aux slots image (exclusion testée) ; le fetch /models async sous
  changement de deck (garde par étiquette — le C1 ne se refera pas une
  4e fois) ; « aller au module » sans nouvelle surface de pouvoir pour
  les jetons.
- Hors périmètre 3b, consigné : motifs du catalogue (3c, avec le Sceau),
  GC des images orphelines (3c), multi-sélection (jamais demandée),
  calques sous l'illustration (z<20 — demanderait une bande nouvelle).
