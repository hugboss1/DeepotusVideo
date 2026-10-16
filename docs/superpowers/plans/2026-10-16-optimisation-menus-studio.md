# Optimisation des menus — 3. Studio (t225-t230)

Date : 16/10/2026. Lot du suivi : « Menus : Studio » (prio 1). Relevé, mesures et causes :
`docs/superpowers/specs/2026-10-16-releve-menus-studio.md` (origin/main 02f8162c).

Demandes de l'utilisateur (16/10) : (1) chaque lien atterrit exactement au MILIEU du rond du port, à l'entrée comme à
la sortie ; (2) plus d'air entre la ligne des étiquettes de ports et l'encart de visualisation, pareil sur tous les
nœuds. Causes mesurées : `qi` (géométrie des liens) et `ud`/`Th` (rendu des ports) calculent chacun leur position
(écart −7 en y, ±1 en x, −14 quand le libellé passe sur deux lignes) ; le port `brand` de Composition spatiale n'est
plus affiché (`dzSpatialSlots` ignore les régions `brand_strip`) → lien au coin du nœud ; le corps des ports fait 16
unités quel que soit leur nombre → la 1re ligne déborde de 6 dans l'encart, les suivantes s'impriment dessus.

## Règles communes à toutes les tâches

- Branche par tâche tirée d'`origin/main` à jour ; une PR par tâche seulement avec l'accord de l'utilisateur.
- Bundle modifié UNIQUEMENT par un patcher. **Nouveau maillon de queue `scripts/patch_bundle_dzstudio.py`**, posé APRÈS
  `dzlogo` (sonde son marqueur `function DzLogoMarque(`), lecture/écriture en OCTETS, `.js.bak_dzstudio` supprimé après
  écriture, paires `(avant, après)` à ancre unique relevées sur le bundle du jour, `--check`, `defaire()`. Le maillon
  `version` reste le dernier.
- Inverse : `avant_dzstudio(bundle)` dans `backend/tests/_i18n_l1_aide.py`, appelé EN TÊTE de `avant_dzlogo` (comme
  `avant_dzlogo` l'est en tête d'`avant_dzreglages`). t225 crée le maillon ; t226-t229 y ajoutent leurs paires (une
  famille de paires par tâche : A*, B*, C*, D*, E*).
- Comptes figés intacts : `x.useState(` = 731 (aucun useState ajouté : useRef/useReducer ou calcul pur),
  `v2.8.0` ×4, `DzTracks` 181 ; remplacements de `scripts/dzglyph_paires.json` intacts ; jamais toucher le littéral Fu.
- Bancs aval à rejouer à chaque tâche : `test_logo_coque.py` (son E6 et son inverse), `test_studio_fl_bundle.py`,
  `test_studio_r8.py` (compte `var sp=dzSpatialSlots(tpl,hit.sc.props||{})` == 1), `test_studio_barre_debordement.py`,
  `test_studio_epingles_bundle.py`, `test_studio_import_bundle.py`, `test_montage_bundle.py`, puis
  `run-tests.ps1` complet (harnais partagé, sortie UTF-8). Rouges préexistantes sur main notées, jamais masquées.
- TDD : banc neuf ROUGE sur 02f8162c d'abord, puis le patch, puis VERT. Mutations : chaque paire défaite ou altérée
  doit faire tomber au moins une vérification (copier les sources AVANT, `cmp` APRÈS restauration).
- Une phrase FR = une traduction : tout texte visible neuf passe par `dzT` avec sa clé FR et EN.
- Preuve au VRAI clic, en FR puis en EN, sur un backend de preuve (python embarqué
  `%LOCALAPPDATA%\DeepotusVideoGen\runtime\python\python.exe`, `sys.path.insert` du worktree, `DEEPOTUS_DATA_DIR`
  jetable, port libre vérifié par requête HTTP, JAMAIS le 8765) ; arrêt : parent ET enfants `spawn_main`, vérifié par
  requête. Mesure navigateur réutilisable (script du relevé) : extrémités des `path` × `getScreenCTM()` contre les
  centres des `span[data-port-side][data-port-id]`.

## t225 — Liens ancrés au milieu des ports (P1, M) — demande 1

1. **Banc d'abord** `backend/tests/test_studio_ancrage.py` (rouge sur 02f8162c) :
   - [A] lecture du bundle : une seule source de géométrie `dzPortGeo` (origine `oy`, pas `Mu`, hauteur de ligne `lh`,
     rond `16`, bordure `1`) utilisée À LA FOIS par `qi` et par `ud`/`Th` (comptes d'occurrences, plus aucun
     `Ru+12+a*Mu` ni `8+n*Mu+2` en dur) ;
   - [B] calcul sous node (extraction de `qi` + `dzPortGeo`) : pour i = 0..5, `qi(in).x` = 1, `qi(out).x` = bi − 1,
     `qi(.).y` = centre du rond = bordure + Ru + `oy` + i·Mu + 8 ;
   - [C] ligne de port : rond ancré en haut de ligne (`alignItems:"flex-start"` ou rond en absolu), étiquette sur UNE
     ligne (`whiteSpace:"nowrap"`, `overflow:hidden`, `textOverflow:"ellipsis"`, `title` = libellé complet) → la hauteur
     de ligne ne dépend plus de la longueur du libellé ni de la langue ;
   - [D] inverse `avant_dzstudio` = bundle d'avant (octet pour octet sur 02f8162c) ; comptes figés.
2. Patcher `patch_bundle_dzstudio.py`, paires A0-A3 : `dzPortGeo` posé devant `qi` ; corps de `qi` ; style de la ligne
   et du rond dans `ud` ; étiquette une ligne + `title`.
3. Inverse `avant_dzstudio` + appel en tête d'`avant_dzlogo` ; bancs aval mis à jour (leurs inverses passent par lui).
4. Mutations (chaque paire, et `x` sans la bordure, `y` sans la demi-ligne).
5. Preuve : graphe « Post reel News », écarts |dx|, |dy| ≤ 0,5 px d'écran pour TOUS les liens à 30 %, 75 %, 105 %,
   150 %, avant et après un vrai glisser de nœud, en FR puis en EN (libellés plus longs) ; capture avec repères.

**Fait le 16/10** : `dzPortGeo={b:1,oy:10,p:Mu,lh:16,r:16}` (A0), `qi` = centre du rond (A1), ligne `ud` de hauteur
`lh`, rond en haut, débord `r/2` (A2), étiquette une ligne + `title` (A3). `oy` garde 10 : la mise en page ne bouge
pas, seuls les bouts des liens rejoignent les ronds (t227 changera `oy`). Banc 40/40 (17 rouges sur 02f8162c), 16
mutants tués, inverse = 02f8162c octet pour octet. Mesure navigateur (8797), 8 liens sur 9 (le 9e, Bandeau de marque →
`brand`, est t226) : écart max 0,000 px avant glisser et ≤ 0,008 px après glisser à 30/75/105/150 %, en FR et en EN ;
lignes de port à 16 unités (ellipse + title sur « HeyGen avatar (reads the script) · av »). Captures :
`docs/superpowers/specs/assets/2026-10-16-studio/t225-*`.

## t226 — Port « brand » de Composition spatiale (P1, S) — demande 1 (Brand strip → Spatial compose)

1. Relevé ciblé d'abord (noté dans la PR) : `dzCompose` lit-il le nœud relié à `brand` pour une région `brand_strip`
   (texte/couleurs du Bandeau de marque) ? Décider avec ce relevé : (a) `dzSpatialSlots` expose aussi un port `brand`
   (type image, libellé de la région) pour la première région `brand_strip` du modèle ; ou (b) si la région n'a pas
   besoin d'entrée, le lien vers un port absent est dessiné en pointillé rouge vers le bord gauche avec une bulle
   « port absent de ce modèle » (clés FR/EN) au lieu du coin (0,0). Défaut : (a), le graphe de départ relie Brand strip.
2. Banc `test_studio_ports_spatial.py` : `dzSpatialSlots(tpl_news_reel)` contient `brand` ; `qi` d'un port introuvable
   ne rend plus jamais `{x:0,y:0}` ; `dzCompose` mappe la région brand_strip au port `brand` ; `test_studio_r8` intact.
3. Paires B* dans `dzstudio` (pas dans `spatialports` : on ne réécrit pas une couche amont). Mutations.
4. Preuve : le lien Brand strip → Composition spatiale arrive au milieu du rond `brand` (≤ 0,5 px), FR et EN ; un
   rendu d'aperçu sans clé n'est pas exigé (dit comme tel).

**Fait le 16/10** : relevé — `dzCompose` sautait la région `brand_strip` (seuls video_slot/image_slot sont lus) et le
backend (template_service) la dessine d'après ses `items` (fond, logo PNG `marks/…`, texte « $DEEPOTUS ») : le nœud
relié à `brand` n'était lu par personne ; le Bandeau de marque ne porte qu'un texte (espace actif) et un emoji. Décision
de l'utilisateur : (a) avec le texte relié. B1 : `dzSpatialSlots` expose `brand` (type image, slot = id de la région,
libellé « brand », aucun texte neuf) pour la 1re région brand_strip, après les ports existants, sans doublon si une
image_slot a déjà pris `brand`. B2 : `qi` d'un port introuvable → bord du nœud, ligne sous le dernier port (plus jamais
(0,0)). B3 : `dzCompose` mappe la région au port ; le texte du Bandeau relié (ou celui du catalogue) remplace le 1er
item texte, le logo PNG reste, l'emoji est ignoré ; texte vide ou identique, autre type de nœud → région intacte. B4 :
`hasMods` inclut ce changement. Sans lien, rendu identique. Garde ajoutée au maillon : marqueur présent mais paires
manquantes → refus (« partiellement appliqué »). Banc `test_studio_ports_spatial.py` 43/43 (18 rouges sur 0b62e7c4),
`test_studio_ancrage` B9 mis à jour (40/40), 14 mutants tués par des checks fonctionnels, inverse = 02f8162c et sans
les B* = 0b62e7c4 octet pour octet. Mesure navigateur (8797), 9 liens sur 9 dont Bandeau de marque → `brand` : écart
max 0,000 px à 30/75/105/150 %, en FR et en EN. Aperçu de l'inspecteur (bandeau « 🐙 DEEPOTUS / $DEEP » en dur) non
touché ; rendu réel sans clé non exigé, non fait. Captures : `docs/superpowers/specs/assets/2026-10-16-studio/t226-*`.

## t227 — En-têtes de ports : air au-dessus de l'encart, même mise en page partout (P1, M) — demande 2

Dépend de t225 (même géométrie `dzPortGeo`).
1. Banc `test_studio_entetes.py` (rouge sur la base t225) :
   - [A] le corps des ports a une hauteur explicite `oy + max(nIn, nOut)·Mu + air` (plus de `minHeight:16`), avec
     `nIn` = ports d'entrée VISIBLES (Concatenate tronqué, `dzNodeInPorts` pour Composition spatiale) ;
   - [B] l'encart (`reef`) et le pied (variante classique) se posent dessous avec la même marge haute pour TOUS les types ;
   - [C] `qi` et le rendu restent alignés (réutilise [B] de t225).
2. Valeurs proposées (à valider à l'œil sur maquette avant patch, capture des deux variantes) : `oy` = 8 sous l'en-tête,
   `lh` = 16, `Mu` = 22, `air` = 10 au-dessus de l'encart → 1 port : encart à 8 + 22 + 10 = 40 sous l'en-tête (au lieu de
   20), plus aucun chevauchement.
3. Paires C* dans `dzstudio`. Mutations (air à 0, nIn ignoré, Concatenate non tronqué).
4. Preuve au navigateur, par type : « encart − bas de la dernière ligne » = `air` (± 0,5) sur News item, News script,
   HeyGen avatar, Illustr. News, Bandeau de marque, Composition spatiale (2 et 5 scènes), Avatar maître, Rendu,
   Génér. d'images ; FR et EN ; variante classique (sans encart) vérifiée aussi. Liens toujours ≤ 0,5 px.

## t228 — A1 : barre du graphe sur deux lignes et canevas (P1, S) — anomalie hors demandes, à trancher

Constat : barre 107 px (`--dz-gbar-h`), canevas à `top:48` fixe → 59 px du graphe sous la barre ; l'encart des
raccourcis chevauche les nœuds. Proposition : le canevas garde toute la hauteur (la barre translucide reste par-dessus)
mais le graphe de départ, « Nouveau » et le recadrage décalent le pan initial de `--dz-gbar-h − 48` pour que l'origine
soit visible ; l'encart des raccourcis se replie en pastille quand il chevauche un nœud. Demander l'avis de l'utilisateur
avant de coder. Banc `test_studio_canevas_barre.py` + preuve à 1500 et 1920 px, inspecteur ouvert et fermé.

## t229 — A2 : boutons de zoom ± centrés sur la vue (P1, S) — anomalie hors demandes

Les boutons zooment autour du coin (0,0) ; la molette autour du curseur. Correctif : les boutons appliquent la même
formule que la molette avec le CENTRE du canevas comme pivot (pan recalculé). Banc `test_studio_zoom_boutons.py`
(formule extraite sous node : le point central du canevas reste fixe à ± 0,5 px). Preuve au vrai clic.

## t230 — Traduction et guide du Studio (P1, S)

Dépend de t225-t229. Clés FR/EN des textes neufs éventuels (bulle t226, pastille t228), banc K « aucune chaîne en dur
dans les paires dzstudio » ; chapitre Studio du guide : scènes montrant des nœuds recapturées avec le skill
guide-deepotus (liens ancrés, en-têtes aérés), guide FR/EN et PDF reconstruits.

## Ordre

t225 → t226 → t227 (même maillon `dzstudio`, à la suite), puis t228 / t229 (indépendantes, après l'avis de
l'utilisateur pour t228), puis t230. Installation après chaque fusion selon la méthode habituelle (table hash-object
juste avant de copier, sauvegarde, pré-vol `sys.path.insert`).
