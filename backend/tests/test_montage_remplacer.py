# -*- coding: utf-8 -*-
"""P6 — REMPLACER LA SOURCE D'UN PLAN SANS PERDRE SON MONTAGE.

Run : & $PY tests/test_montage_remplacer.py   (depuis backend/)

LE GESTE : l'utilisateur a regenere un plan. Il veut echanger la SOURCE d'un
clip — ses bornes, ses effets, sa transition et son mixage restant en place.
Deux moities : une route qui PROPOSE (GET /api/montage/newer, rapprochement
par le titre, dit heuristique) et un cœur JS PUR qui remplace
(`DzTracks.replaceSrc`) plus son retour arriere (`DzTracks.revertSrc`).

CE QUI EST FERME ICI
  [1] GET /newer ne propose que des VIDEOS. C'est la lecon de la tache 15 :
      `sprite2d` range sa planche PNG et `asset3d` son maillage GLB dans la
      MEME colonne `final_video_path` qu'un rendu `seedance`. Une route
      « versions plus recentes » qui ne filtre pas proposerait une planche de
      sprites comme nouvelle version d'un plan. `_is_video_artifact` et
      `_VIDEO_EXTS` sont REUTILISES, jamais recopies — la mutation MEXT le
      prouve (retirer `.mp4` de `_VIDEO_EXTS` doit faire rougir ce banc).
  [2] LE FILTRE NE CONSOMME PAS LA FENETRE. La requete borne des CANDIDATS,
      pas des lignes brutes : le plafond de 5 est pris APRES le filtre de
      titre, en Python. La section [1-quater] pose 20 non-video homonymes
      PLUS RECENTES que 7 videos homonymes ; un `.limit(5)` sur la requete
      rendrait 0 candidat. C'est la mutation ML.
  [3] LE TITRE EST COMPARE NORMALISE : sans le suffixe « (aperçu 480p) »
      (MESURE, voir PROTOCOLE ci-dessous : c'est le seul suffixe que ce
      depot ajoute a un titre de job), sans espaces de bord, sans casse.
  [4] LE GARDE-FOU DU TITRE VIDE, qui n'est PAS au plan et que la base
      REELLE impose : un titre normalise vide ne propose RIEN. Sans lui, les
      61 jobs `done` non-montage a artefact .mp4 et titre NUL de la base de
      l'utilisateur se proposeraient mutuellement comme « versions plus
      recentes ». Mutation MV.
  [5] LE PIEGE SQL DU `provider != "montage"` : en SQL, `NULL != 'montage'`
      vaut NULL, donc la ligne est ECARTEE. MESURE sur une COPIE de la base
      reelle : 13 jobs `done` portent `provider IS NULL`, et les 13 sont des
      .mp4. La clause est donc ecrite `coalesce(provider,'') != 'montage'`.
      Mutation MP.
  [6] LE CŒUR PUR, sous node : bornes/effets/transition intacts, `srcIn`
      ramene a 0 et `end` raccourci quand la nouvelle source ne couvre pas
      la fenetre, `src_history` empile puis plafonne, `revertSrc` depile ET
      REND LES BORNES D'ALORS.
  [7] LES DEUX BOUTONS et le rappel « version plus recente », executes sous
      node avec le meme stub `r` que test_montage_bundle.py.

CE QUE CE BANC N'AFFIRME PAS
  * Il ne mesure PAS le bundle : les sections M15/M16 et leurs comptes
    d'ancres sont le miroir de test_montage_bundle.py, qui lit le fichier
    LIVRE. Ce banc-ci lit la COUCHE (frontend/patches/montage.js) et le
    SERVICE. Les deux sont necessaires : la couche peut etre juste et le
    bundle ne pas la porter.
  * `pushHistory` et `undo` sont des hooks du composant du bundle, hors de
    portee du shim node. « Annuler restaure le clip d'avant » reste une
    DEDUCTION de trois faits mesures (un seul pushHistory, pousse AVANT
    l'ecriture, sur un etat que le geste ne mute pas — `Object.assign` rend
    un objet neuf) ; RIEN NE L'EXERCE ici. C'est pour cela que `src_history`
    existe : un second retour, celui-la mesure.
  * Aucun octet n'est decode. Les fixtures ne sont pas des medias valides :
    ce que le code sous test lit, c'est l'EXTENSION du chemin range en base
    et l'EXISTENCE du fichier.
  * `srcOut` : le champ est RETIRE du clip remplace (il decrit la fenetre de
    l'ANCIENNE source) — ET RENDU par le retour arriere. MESURE — il
    n'existe AUJOURD'HUI que sur un seul clip de tout le depot, la maquette
    de demonstration du bundle (l. 1165), et sur aucun des 17 clips de la
    sauvegarde reelle. Le retrait est donc sans effet OBSERVABLE
    aujourd'hui ; il est la parce que `svmApplyProject` recopie les cles
    inconnues d'une sauvegarde telles quelles, et qu'un « Out » herite de
    l'ancienne source serait un mensonge a l'ecran — le champ EST LU
    (son-vfx-montage.js : `sel.srcOut != null ? sel.srcOut : (sel.end -
    sel.start) * vitesse`, la ligne « Out » de l'inspecteur).
    LA DECISION, prise le 05/09/2026 et non plus tacite : les deux moities
    sont symetriques. `replaceSrc` retire `srcOut` du clip mais le MEMORISE
    dans l'entree d'historique, a cote de `srcIn` et `end` ; `revertSrc` le
    rend quand — et seulement quand — l'entree le porte. L'alternative
    (l'exclure nommement de l'assertion d'aller-retour) aurait laisse un
    couple qui n'est pas l'inverse de lui-meme, sur le seul champ que
    l'inspecteur lit en priorite. Exerce par `js_remplace_retire_srcOut`,
    `js_srcOut_memorise_puis_rendu_par_le_retour`,
    `js_srcOut_n_est_pas_invente_quand_le_clip_n_en_avait_pas` et
    `js_l_aller_retour_est_l_identite_CLE_POUR_CLE`.
  * QUE `src_history` SURVIT A L'ENREGISTREMENT. C'est une DEDUCTION de deux
    lectures, pas une mesure de bout en bout : `_save_record` range
    `"clips": clips` TEL QUEL (aucune liste blanche de cles) et la
    restauration cote client recopie chaque clip sauvegarde par un
    `Object.assign` (donc les cles inconnues avec). Aucun banc ne joue
    l'aller-retour enregistrer / recharger / revenir en arriere.
  * NI L'ARMEMENT NI SON EXTINCTION. Le mode remplacement est une `useRef` du
    composant du bundle et son desarmement un `useEffect` : hors de portee du
    shim node, qui ne joue que le cœur pur. test_montage_bundle.py en mesure
    la PRESENCE, la place et l'ORDRE (le court-circuit precede la resolution
    de piste), pas le comportement.
    COMPORTEMENT DECLARE, faute de pouvoir l'exercer : armer sur le plan A
    puis selectionner le plan B avant de choisir un asset remplace bien A —
    c'est pour A qu'on a arme. L'ecran le DIT deux fois : la note nomme le
    libelle de A, et la selection revient sur A.
  * CE QUE LE MODE ARME PREND, ET CE QU'IL REFUSE — declare ici parce que la
    portee du court-circuit n'est pas evidente, et parce que le selecteur
    n'a NI VOILE NI BACKDROP (`.svm-pop` : absolute, top 52 px, right 18 px,
    width 300 px, z-index 20 — lu dans shared/son-vfx-montage.css) : c'est
    un panneau de 300 px en haut a droite, tout le reste de l'ecran reste
    cliquable, et le mode reste arme tant qu'`ovPick` ne bouge pas.
      - LE GLISSER-DEPOSER d'une vignette sur une bande passe par le MEME
        `addAsset` et devient donc un remplacement : la piste visee et
        l'instant du depot sont JETES (un remplacement n'en veut pas).
        C'est ASSUME, pas subi — glisser une vignette du selecteur, c'est
        choisir dans le selecteur. Le panneau le DIT desormais pendant qu'il
        est arme (section M15b du patcher : titre « Remplacer la source de
        « X » », note « un glisser-deposer compte aussi comme un choix »).
      - `sfxInsert` (tiroir Sons, dont l'etat `sfxOn` est INDEPENDANT
        d'`ovPick` et rendu hors du panneau) appelait
        `addAsset({audio:fn},…,"audio",…)` et le court-circuit l'acceptait :
        MESURE sous node, le `src` d'un plan V1 devenait `{audio:"…"}`,
        avec ses bornes, ses effets et sa transition, et sa fin ramenee a la
        duree du .wav. Ce chemin-la n'etait PAS assumable : le refus de
        genre pose en M15 le ferme, et test_montage_bundle.py le mesure.
        `replaceSrc` lui-meme reste sans opinion sur le genre — c'est le
        composant qui connait la piste du plan, pas le cœur pur.
  * LE COMPOSANT du rappel n'est pas execute non plus (il a des hooks et
    interroge le reseau). Seule sa ligne — `newerLine` — est mesuree ici,
    plus son EXISTENCE et son unique appelant.

PROTOCOLE DES CHIFFRES CITES CI-DESSUS — tous pris le 2026-09-04 sur une
COPIE en lecture seule de %LOCALAPPDATA%\\DeepotusVideoGenData\\deepotus.db
(+ -wal + -shm, copies ensemble), interrogee par le module `sqlite3` de la
bibliotheque standard, jamais l'originale :
  120 jobs, 116 `done` ; par fournisseur : seedance 35, template 33,
  NULL 13, ugc 9, sprite2d 8, asset3d 7, heygen 5, montage 4, news 1,
  animation 1.
  97 jobs `done` non-montage dont l'artefact resolu
  (`coalesce(nullif(final_video_path,''), video_path)`) finit par `.mp4` ;
  61 d'entre eux ont un titre NUL ou vide ; 53 ont `duration_s` NUL ou <= 0.
  CES TROIS CHIFFRES ONT ETE FAUX, et la faute vaut plus que les chiffres :
  le commit 2fff6b6 ecrivait 84 / 48 / 40, mesures avec un `where` en
  `provider != 'montage'` — C'EST-A-DIRE SOUS LE BUG QUE CE MEME COMMIT
  REMPLACE. Les 13 jobs `done` a `provider IS NULL` tombaient de la mesure
  exactement comme ils tombaient de la requete : 84+13 = 97, 48+13 = 61,
  40+13 = 53. Le protocole etait nomme et la mesure faite ; ce qui manquait,
  c'est de mesurer sous la clause LIVREE et non sous celle qu'on jetait.
  CONTROLE CROISE (04/09/2026, meme copie) : `where provider != 'montage'`
  rend 99 lignes `done`, `coalesce(...)` en rend 112 — ecart 13, exactement
  les 13 lignes a provider NUL.
  13 jobs `done` a `provider IS NULL`, tous des .mp4 — aucun ne porte de
  titre AUJOURD'HUI, donc la correction du point [5] ne change rien
  d'OBSERVABLE sur cette base : elle ferme un piege SQL, pas un defaut
  constate.
  Suffixe de titre : 8 lignes portent « (aperçu 480p) », toutes
  `provider='montage'` (4 `done`, 4 `failed` — et non « 3 / 5 » comme
  l'ecrivait 2fff6b6) ; ZERO ligne non-montage en porte. La base ne compte
  que 4 jobs `montage` `done` : TOUS le portent, le suffixe est la marque de
  tout apercu et non une exception. Le seul point du depot qui l'ajoute est
  montage_service.py l. 2406 (2fff6b6 disait 2253 : le numero du fichier
  PARENT, d'avant ses propres ajouts).
  CONSEQUENCE, dite plutot que tue : les candidats excluant `montage`, ce
  suffixe ne peut mordre que sur le job de REFERENCE (le clip qu'on
  remplace). Il est normalise quand meme — c'est une ligne de regex — mais
  son gain reel est celui-la, pas celui que le plan laissait croire.
  Homonymes exploitables (jobs `done` non-montage, artefact .mp4, titre non
  vide, partages a plusieurs) : 3 groupes, 12 jobs — « tweet_2026-05-20 »
  (7), « last launch 2 » (3), « backdoorpromo » (2).
  Cout de `src_history` : un enregistrement JSON pese 149 o (mesure sur
  {src:{job_id:<uuid>}, label 28 car., srcIn, end, at) ; plafond 10 par
  clip, `_SAVE_MAX_CLIPS = 400` — soit 596 ko de PLAFOND theorique ajoute a
  montage_saved.json, qui pese 5 980 o aujourd'hui (17 clips). Ce plafond
  demande 4 000 remplacements : c'est une borne, pas un cout.

VINGT-HUIT MUTATIONS. Vingt et une venaient de 2fff6b6 ; TOUTES CELLES QUI SE
MESURENT SUR CE BANC ONT ETE REJOUEES contre le fichier LIVRE, parce que la
correction de la branche vide y ajoute deux lignes et que laisser des totaux
pris sur un banc de 75 aurait ete la faute meme que le PROTOCOLE ci-dessus
corrige : citer un chiffre mesure sur autre chose que ce qu'on livre. Les NOMS
des lignes rouges sont inchanges d'une campagne a l'autre — c'est ce qui prouve
que la mutation rejouee est bien la meme, et que seul le total a bouge (+2 en
vertes, failed inchange).
(2fff6b6 annoncait « DIX-HUIT » ; sa liste en portait 20, plus MSEL en note.)
PROTOCOLE : le fichier vise est reecrit sur DISQUE (texte en newlines
universelles puis reecrit en CRLF pour le service et la couche ; en OCTETS
pour le bundle, qui melange minifie sans saut de ligne et blocs CRLF), le banc
relance en PROCESSUS NEUF depuis backend/, le fichier restaure quoi qu'il
arrive (try/finally + verification du sha256) ; scripts scratchpad/mut6_run.py,
scratchpad/mut6_bundle.py et scratchpad/muts.py. Une mutation dont l'ancre
n'est pas UNIQUE est refusee plutot que jouee au hasard : MW et MWR portent la
ligne PRECEDENTE dans leur ancre, parce que le meme `where` de liste blanche
existe aussi dans `montage_project` (l. 1083) et que le muter LA aurait mesure
une autre route. Ligne verte de reference : 77/0 pour ce banc, 304/0 pour
test_montage_bundle.py.

  SUR LA ROUTE (banc : celui-ci)
  MV   garde du titre vide retiree      => 76/1, `newer_titre_vide_ne_
       propose_rien` SEULE. (`newer_titre_en_blancs_ne_propose_rien` reste
       VERTE, et c'est juste : « ␣␣␣ » se normalise en chaine vide seulement
       APRES `.strip()`, que la mutation ne touche pas — la ligne mesure
       l'autre moitie de la meme sortie.)
  MP   `coalesce(provider,'')` remplace par `provider != "montage"`
       => 74/3 : `newer_accepte_un_provider_nul`, la ligne d'ORDRE et
       `newer_rend_une_duree_nulle_telle_quelle` (le job a provider NUL est
       aussi celui dont la duree est nulle). C'EST LA MUTATION DU PIEGE SQL —
       et c'est aussi, mot pour mot, la clause sous laquelle 2fff6b6 avait
       compte 84 / 48 / 40 au lieu de 97 / 61 / 53.
  MMON clause `provider` entierement retiree => 75/2 :
       `newer_ecarte_nos_propres_rendus_de_montage` et la ligne d'ORDRE.
  MVID test `_is_video_artifact` retire => 75/2 :
       `newer_ecarte_un_nom_de_fichier_sans_extension_analysable` et la ligne
       d'ORDRE. CE CHIFFRE A ETE GAGNE : sur la premiere version du banc,
       cette mutation donnait 74/0 — AUCUNE rouge, parce que le `where` de la
       requete dit deja la meme chose et qu'aucune fixture n'exploitait leur
       seule divergence. La fixture « fichier nomme exactement .mp4 » a ete
       ajoutee POUR CELA.
  MW   `where` de la liste blanche RETIRE => 77/0, AUCUNE rouge, ET C'EST
       DECLARE. Attention a la portee EXACTE de cet aveu, que 2fff6b6
       elargissait a tort : ce n'est pas « aucune assertion ne peut distinguer
       ce `where` », c'est « aucune ne peut distinguer sa direction
       PERMISSIVE ». Retirer le garde ne change que le NOMBRE DE LIGNES
       chargees avant le filtre Python — jamais la sortie, puisqu'il n'y a pas
       de `.limit()`. Sa direction DANGEREUSE, elle, est mesuree neuf fois :
       voir MWR. Le garde reste parce qu'il est gratuit et qu'il maintient la
       propriete que P8-bis a payee (la requete rend des candidats, pas des
       lignes a jeter) ; ce n'est pas du code non teste, c'est un garde dont
       une seule direction est observable — et c'est ce qu'il doit etre par
       construction, le filtre Python re-decidant derriere lui.
  MWR  `where` rendu SUR-RESTRICTIF (`_fp.ilike("%.mov")` seul) => 68/9. La
       mutation que 2fff6b6 n'avait pas jouee, et celle qui tient le garde :
       neuf lignes tombent, exactement celles de MEXT. Un `where` trop etroit
       ecarte des candidats legitimes AVANT que Python ne les voie, et ca, ce
       banc le voit.
  ML   `.limit(5)` pose sur la requete => 74/3 :
       `plafond_5_pris_apres_le_filtre_de_titre_et_de_video`, la ligne
       d'ORDRE et `newer_accepte_la_casse_et_les_espaces_de_bord`. CE CHIFFRE
       A LUI AUSSI ETE GAGNE : la premiere version posait 20 PLANCHES PNG
       comme bruit, que le `where` retire avant la requete — la mutation
       donnait 74/0. Le bruit est desormais du meme genre que les candidats
       (20 videos d'un AUTRE titre, plus recentes), et il consomme la fenetre.
  MEXI garde d'existence du fichier retiree => 75/2 :
       `newer_ecarte_une_source_disparue` et la ligne d'ORDRE.
  MSUF suffixe d'apercu non normalise => 76/1, `titre_apercu_ignore` SEULE.
  MCAS casse non normalisee => 74/3 :
       `newer_accepte_la_casse_et_les_espaces_de_bord`, `titre_apercu_ignore`
       (son candidat differe aussi par la casse) et la ligne d'ORDRE.
  MDAT garde `completed_at is None` retiree => 75/2 :
       `newer_reference_sans_date_ne_propose_rien` ET `aucun_appel_n_a_
       plante`. La seconde dit ce que la premiere ne dit pas : sans la garde,
       la route LEVE — `completed_at > None` n'est pas une comparaison. La
       garde n'est donc pas un raccourci, c'est la correction.
  MEXT `.mp4` retire de `_VIDEO_EXTS` => 68/9. C'est la mutation qui prouve
       que la route REUTILISE la liste du service au lieu d'en porter une
       copie : neuf lignes tombent, dont toutes celles qui attendent un
       candidat.
  MTIT filtre de titre ENTIEREMENT retire => 71/6, dont
       `newer_un_job_sans_titre_n_est_jamais_candidat`. C'est la mutation qui
       a demasque une assertion STRUCTURELLEMENT VIDE : jusqu'a la correction
       du 04/09-bis, cette ligne comparait a une reponse prise AVANT que sa
       fixture n'existe, et elle restait VERTE ici (voir MOLD).
  MSEL clause `id != job_id` du plan REMISE => 77/0, aucune ligne rouge.
       C'est du code MORT : la comparaison de date est STRICTE, donc la
       reference n'est jamais plus recente qu'elle-meme. La propriete, elle,
       est bien tenue — voir MGE.
  MGE  `completed_at > ref` devenu `>=` => 75/2 :
       `newer_ne_se_propose_pas_lui_meme` et la ligne d'ORDRE. C'est la
       CONTRE-EPREUVE de MSEL : la clause retiree etait morte, mais la
       propriete qu'elle pretendait tenir est mesuree, et par la STRICTESSE.
  MORI `origin` du dict `empty` mis a "depot" => 76/1,
       `newer_vide_dit_aussi_son_origine_heuristique` SEULE.
  MOK  `ok` du dict `empty` mis a False => 76/1, `newer_vide_reste_un_ok`
       SEULE. Ces deux-la sont NEUVES : le contrat porte DEUX dicts (celui du
       chemin vide et celui du succes) et un seul etait tenu. Les 76 autres
       lignes restent VERTES sous chacune — donc sur le banc de 2fff6b6, qui
       ne portait pas ces deux-ci, les deux mutations donnaient 75/0 : la
       reponse la plus FREQUENTE, celle d'un plan sans homonyme, pouvait
       diverger de l'autre en silence.

  SUR LE BANC LUI-MEME (ce que la correction du 04/09-bis a ferme)
  MOLD l'assertion d'AVANT remise (`I(21) not in IDS(d1)`), MTIT jouee en
       meme temps => 72/5, et la ligne est VERTE. C'est la preuve directe :
       `d1` est pris ~70 lignes avant que I(21) ne soit en base, donc aucun
       changement de la route ne pouvait la faire rougir.
  M21  la requete REJOUEE mais l'assertion portant le SEUL I(21) — le
       correctif minimal — MTIT jouee en meme temps => 72/5, et la ligne est
       ENCORE VERTE. Rejouer la requete ne suffisait donc pas : le plafond de
       5 cache I(21), le plus ancien des trois jobs sans titre, derriere cinq
       homonymes plus recents. Seule la forme LIVREE (les trois jobs sans
       titre, pas un seul) rougit — c'est I(22) qui la fait rougir, et le
       temoin de la ligne le montre.

  SUR LE CŒUR JS (banc : celui-ci)
  MJ1  plafond de `src_history` retire => 74/3 : les deux lignes du plafond
       et `js_retour_deux_crans`.
  MJ2  `revertSrc` ne rend plus les bornes => 76/1,
       `js_retour_rend_AUSSI_les_bornes_d_alors` SEULE. C'est l'ECART au plan
       (qui n'empilait que {src, label, at}) qui se mesure ici.
  MJ3  `replaceSrc` mute le clip d'entree => 68/9. La plus large, et elle le
       merite : un cœur qui mute son entree rend inutile l'instantane que
       l'ecran pousse AVANT d'ecrire.
  MJ4  duree inconnue passee sous silence => 76/1, `js_duree_inconnue_le_dit`
       SEULE.
  MJ5  `srcOut` conserve => 76/1, `js_remplace_retire_srcOut` SEULE.
  MJ6  note muette sur les limites de l'annulation => 75/2, les deux lignes
       de la note (ce qu'annuler ne rend pas, et la seconde voie de retour).

  SUR LA CHAINE (banc : test_montage_bundle.py, reference 304/0 — ce banc-la
  n'a pas bouge, ses comptes non plus)
  MB   couche modifiee SANS rejouer le patcher => 303/1,
       `bloc_EST_la_couche_octet_pour_octet` SEULE. Le bundle n'executerait
       plus le fichier que ce banc-ci mesure.
  MR1  declaration d'`addAsset` renommee dans le bundle (un rebuild)
       => 301/3 : `M15-remplace-mode_remplace`,
       `M16a_appelle_addAsset_qui_est_declare` et
       `M16src_appelle_addAsset_qui_est_declare`.
  MR2  etat du selecteur d'assets renomme dans le bundle => 303/1,
       `M16src_appelle_ovPick_qui_est_declare` SEULE. C'est ce que le
       controle a DEUX FACES achete : une seule face (l'appel) serait restee
       verte sur ce rebuild-la.
"""
import asyncio
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp6_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from httpx import AsyncClient, ASGITransport                # noqa: E402
from app.main import app                                    # noqa: E402
from app.services import montage_service as M               # noqa: E402
from app.services.storage import (JobRecord, async_session_factory,  # noqa: E402
                                  init_db)
from app.models.schemas import JobStatus                    # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
LAYER = ROOT / "frontend" / "patches" / "montage.js"
SERVICE = ROOT / "backend" / "app" / "services" / "montage_service.py"

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


_plantages = 0


def temoin(e):
    """TEMOIN d'un appel qui a LEVE — meme parade que test_montage_sources.py
    (faute n°6 du chantier : un banc qui MEURT n'imprime aucun compte et
    emporte en silence tout ce qui suit).

    NUMEROTE (deux echecs ne se valent jamais, donc `a == b` entre deux
    temoins reste rouge) et DISTINGUABLE (jamais `None`, qui rendrait verte
    toute comparaison a None ; jamais `[]`, qui rendrait verte toute
    comparaison a la liste vide — or ce banc en fait beaucoup). C'est une
    CHAINE finissant par « ·ECHEC#n »."""
    global _plantages
    _plantages += 1
    return "%s: %s ·ECHEC#%d" % (type(e).__name__, e, _plantages)


class _RepIllisible:
    """Reponse-temoin : `status_code` negatif — jamais 200 —, et `.json()`
    releve pour que `J()` pose son propre temoin par-dessus."""

    def __init__(self, t):
        self.status_code = -1
        self.text = t

    def json(self):
        raise ValueError(self.text)


def api(method, path, **kw):
    """Appel HTTP contre l'app ASGI, garde comprise : une exception que
    FastAPI ne rattrape pas (NameError dans la route…) TRAVERSE
    ASGITransport et tuerait le banc au milieu d'une section."""
    async def go():
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=180.0) as c:
            return await c.request(method, path, **kw)
    try:
        return asyncio.run(go())
    except Exception as e:
        t = temoin(e)
        print(f"  ----  {method} {path} a leve : {t}")
        return _RepIllisible(t)


def J(resp):
    """Corps JSON, ou un dict-temoin. JAMAIS un dict VIDE : `{}` rendrait
    verte une comparaison `d.get("candidates", []) == []`."""
    try:
        v = resp.json()
    except Exception as e:
        return {"_illisible": temoin(e)}
    return v if isinstance(v, dict) else {"_liste": v}


def CAND(d):
    """La liste des candidats, ou un TEMOIN distinguable de la liste vide.

    Le piege que cette fonction ferme est la faute n°2 dans sa forme la plus
    courante ici : la moitie des lignes de ce banc comparent a `[]`. Une
    reponse illisible, un 500, une cle absente — tout cela rendrait `[]` et
    verdirait CES LIGNES-LA en meme temps qu'il casse les autres. On rend
    donc une chaine-temoin, qui n'egale ni `[]` ni aucune liste."""
    if not isinstance(d, dict) or "candidates" not in d:
        return "SANS_CLE_candidates: %r" % (d,)
    v = d["candidates"]
    return v if isinstance(v, list) else "candidates_n_est_pas_une_liste: %r" % (v,)


def IDS(d):
    """Les job_id des candidats, dans l'ordre servi — ou le temoin de CAND."""
    v = CAND(d)
    if not isinstance(v, list):
        return v
    out = []
    for c in v:
        out.append(c.get("job_id") if isinstance(c, dict) else "ENTREE_NON_DICT:%r" % (c,))
    return out


# ─────────────────────────────────────────────────────────── fixtures ──────
LIB = pathlib.Path(TMP) / "lib"
LIB.mkdir(parents=True, exist_ok=True)
F_MP4 = LIB / "plan.mp4"
F_MP4B = LIB / "plan_v2.mp4"
F_PNG = LIB / "sheet.png"
F_GLB = LIB / "model.glb"
F_ABSENT = LIB / "efface.mp4"          # jamais cree
# UN FICHIER NOMME EXACTEMENT « .mp4 ». C'est la SEULE divergence connue
# entre le `where` de la requete (qui filtre la CHAINE, `LIKE '%.mp4'`)
# et `_is_video_artifact` (qui filtre l'EXTENSION ANALYSEE, et
# `PurePath("C:/a/.mp4").suffix` vaut ''). Elle est ici pour que le test
# Python porte quelque chose : sans cette ligne, le retirer laissait le
# banc ENTIEREMENT VERT (mutation MVID, mesuree a 74/0).
F_SANS_EXT = LIB / ".mp4"
for f, b in ((F_MP4, b"\x00faux mp4"), (F_MP4B, b"\x00faux mp4 v2"),
             (F_PNG, b"\x89PNG\r\n\x1a\nfaux"), (F_GLB, b"glTF\x02faux"),
             (F_SANS_EXT, b"\x00sans extension")):
    f.write_bytes(b)

T0 = datetime(2026, 9, 1, 12, 0, 0)


def I(n):
    """Un identifiant de job lisible et unique."""
    return "%08d-0000-0000-0000-000000000000" % n


asyncio.run(init_db())


def pose(jid, provider, path, titre, quand, dur=None, statut=None):
    """FIXTURE GARDEE — l'invariant « rougir plutot que mourir » vaut de bout
    en bout : une insertion qui leve (cle primaire deja prise) emporterait en
    silence toutes les sections suivantes AVANT le moindre compte."""
    async def go():
        async with async_session_factory() as s:
            s.add(JobRecord(id=jid, provider=provider,
                            status=(statut or JobStatus.DONE.value),
                            progress=100, title=titre,
                            image_filename=jid[:8] + ".png",
                            final_video_path=(str(path) if path else None),
                            video_path=(str(path) if path else None),
                            duration_s=dur, completed_at=quand))
            await s.commit()
    try:
        asyncio.run(go())
    except Exception as e:
        print(f"  ----  pose({jid[:8]}, {provider}) a leve : {temoin(e)}")


print("\n[1] GET /api/montage/newer — le rapprochement par le titre")
# La REFERENCE : le plan pose sur la timeline, le plus ancien de sa famille.
pose(I(1), "seedance", F_MP4, "plan_01", T0)
# LE candidat : meme titre, plus recent.
pose(I(2), "seedance", F_MP4B, "plan_01", T0 + timedelta(minutes=10), dur=3.0)
# Plus ANCIEN que la reference : ce n'est pas une « version plus recente ».
pose(I(3), "seedance", F_MP4B, "plan_01", T0 - timedelta(minutes=10))
# Titre DIFFERENT : rien a voir.
pose(I(4), "seedance", F_MP4B, "plan_02", T0 + timedelta(minutes=20))
# LES DEUX CAS DE LA TACHE 15 : meme titre, plus recents, PAS des videos.
pose(I(5), "sprite2d", F_PNG, "plan_01", T0 + timedelta(minutes=30))
pose(I(6), "asset3d", F_GLB, "plan_01", T0 + timedelta(minutes=31))
# Nos PROPRES rendus : un montage n'est pas une nouvelle version d'un plan.
pose(I(7), "montage", F_MP4B, "plan_01", T0 + timedelta(minutes=32))
# Fichier disparu : proposer une source que le rendu ne resoudra pas serait
# offrir un piege — GET /project elague deja les clips dans ce cas.
pose(I(8), "seedance", F_ABSENT, "plan_01", T0 + timedelta(minutes=33))
# CASSE et espaces de bord.
pose(I(9), "seedance", F_MP4B, "  PLAN_01 ", T0 + timedelta(minutes=5))
# `provider` NUL — le piege du `!=` en SQL (13 lignes dans la base reelle).
pose(I(10), None, F_MP4B, "plan_01", T0 + timedelta(minutes=6))
# Nom de fichier SANS extension analysable : le `where` l'accepte, le
# test Python le refuse — c'est lui qui decide.
pose(I(12), "seedance", F_SANS_EXT, "plan_01", T0 + timedelta(minutes=34))
# Pas `done` : une generation en cours n'est pas une version.
pose(I(11), "seedance", F_MP4B, "plan_01", T0 + timedelta(minutes=40),
     statut=JobStatus.GENERATING_VIDEO.value)

d1 = J(api("GET", "/api/montage/newer?job_id=" + I(1)))
# ORDRE : du plus recent au plus ancien. Litteral complet, pas un `in`.
check("newer_rend_les_homonymes_plus_recents_du_plus_recent_au_plus_ancien",
      IDS(d1) == [I(2), I(10), I(9)], f"{IDS(d1)}")
check("newer_dit_son_origine_heuristique", d1.get("origin") == "heuristique",
      f'origin={d1.get("origin")!r}')
check("newer_ok", d1.get("ok") is True, f'ok={d1.get("ok")!r}')
# Chaque candidat porte les quatre champs du contrat, et rien d'invente.
_c1 = CAND(d1)
_prem = _c1[0] if isinstance(_c1, list) and _c1 else None
check("newer_chaque_candidat_porte_les_quatre_champs",
      isinstance(_prem, dict)
      and sorted(_prem.keys()) == ["completed_at", "duration_s", "job_id", "title"],
      f"{_prem!r}")
check("newer_rend_le_titre_tel_qu_il_est_en_base",
      isinstance(_prem, dict) and _prem.get("title") == "plan_01",
      f"{_prem!r}")
# La duree sert a `replaceSrc` : elle vient de la base, NULL comprise.
_c2 = next((c for c in _c1 if isinstance(c, dict) and c.get("job_id") == I(2)),
           None) if isinstance(_c1, list) else None
check("newer_rend_la_duree_de_la_source", _c2 is not None
      and _c2.get("duration_s") == 3.0, f"{_c2!r}")
_c10 = next((c for c in _c1 if isinstance(c, dict) and c.get("job_id") == I(10)),
            None) if isinstance(_c1, list) else None
check("newer_rend_une_duree_nulle_telle_quelle", _c10 is not None
      and _c10.get("duration_s") is None, f"{_c10!r}")

# Les six exclusions, une ligne chacune : une ligne agregee ne dirait pas
# lequel des six cotes a cede.
_ids1 = IDS(d1)
check("newer_ecarte_le_plus_ancien",
      isinstance(_ids1, list) and I(3) not in _ids1, f"{_ids1}")
check("newer_ecarte_un_autre_titre",
      isinstance(_ids1, list) and I(4) not in _ids1, f"{_ids1}")
check("newer_ecarte_la_planche_de_sprites",
      isinstance(_ids1, list) and I(5) not in _ids1, f"{_ids1}")
check("newer_ecarte_le_maillage_3d",
      isinstance(_ids1, list) and I(6) not in _ids1, f"{_ids1}")
check("newer_ecarte_nos_propres_rendus_de_montage",
      isinstance(_ids1, list) and I(7) not in _ids1, f"{_ids1}")
check("newer_ecarte_une_source_disparue",
      isinstance(_ids1, list) and I(8) not in _ids1, f"{_ids1}")
check("newer_ecarte_un_job_qui_n_est_pas_done",
      isinstance(_ids1, list) and I(11) not in _ids1, f"{_ids1}")
# LE TEST PYTHON EST LA SEULE AUTORITE, et cette ligne est la seule qui
# le montre : le `where` de la requete accepte ce chemin-la.
check("newer_ecarte_un_nom_de_fichier_sans_extension_analysable",
      isinstance(_ids1, list) and I(12) not in _ids1, f"{_ids1}")
# Les deux ACCEPTATIONS qui tiennent une clause a elles seules.
check("newer_accepte_la_casse_et_les_espaces_de_bord",
      isinstance(_ids1, list) and I(9) in _ids1, f"{_ids1}")
check("newer_accepte_un_provider_nul",
      isinstance(_ids1, list) and I(10) in _ids1, f"{_ids1}")
# La reference elle-meme ne se propose jamais.
check("newer_ne_se_propose_pas_lui_meme",
      isinstance(_ids1, list) and I(1) not in _ids1, f"{_ids1}")

print("\n[1-bis] job_id inconnu, vide, sans date, titre vide")
d2 = J(api("GET", "/api/montage/newer?job_id=inconnu-1234"))
check("newer_job_inconnu_rend_une_liste_vide", CAND(d2) == [], f"{CAND(d2)}")
check("newer_job_inconnu_reste_un_200",
      api("GET", "/api/montage/newer?job_id=inconnu-1234").status_code == 200)
# LA BRANCHE « AUCUN CANDIDAT » PORTE LES MEMES DEUX LITTERAUX QUE CELLE DU
# SUCCES, et RIEN ne les mesurait : `origin` et `ok` n'etaient lus que sur
# `d1`. MESURE (04/09/2026, mutations MORI et MOK) : chacune rougit ici
# SEULE (76/1) et les 76 autres lignes restent vertes — donc sur le banc
# de 2fff6b6, qui ne portait pas ces deux-ci, elles donnaient 75/0. Les deux
# dicts pouvaient donc diverger en silence — et c'est la reponse la PLUS
# FREQUENTE que voit un utilisateur, celle d'un plan sans homonyme.
check("newer_vide_dit_aussi_son_origine_heuristique",
      d2.get("origin") == "heuristique", f'origin={d2.get("origin")!r}')
check("newer_vide_reste_un_ok", d2.get("ok") is True, f'ok={d2.get("ok")!r}')
d3 = J(api("GET", "/api/montage/newer"))
check("newer_sans_job_id_rend_une_liste_vide", CAND(d3) == [], f"{CAND(d3)}")

# LE GARDE-FOU DU TITRE VIDE — hors plan, impose par la base reelle : 61 des
# 97 jobs video non-montage n'ont PAS de titre. Sans cette sortie, chacun
# proposerait les quatre autres comme « versions plus recentes ».
pose(I(20), "seedance", F_MP4, None, T0)
pose(I(21), "seedance", F_MP4B, None, T0 + timedelta(minutes=1))
pose(I(22), "seedance", F_MP4B, "   ", T0 + timedelta(minutes=2))
d4 = J(api("GET", "/api/montage/newer?job_id=" + I(20)))
check("newer_titre_vide_ne_propose_rien", CAND(d4) == [], f"{CAND(d4)}")
d5 = J(api("GET", "/api/montage/newer?job_id=" + I(22)))
check("newer_titre_en_blancs_ne_propose_rien", CAND(d5) == [], f"{CAND(d5)}")
# ... et un job SANS titre n'est jamais propose non plus, meme a un autre
# job sans titre : la ligne ci-dessus pourrait etre verte par la seule sortie
# du REFERENT, celle-ci tient l'autre cote.
# LA REQUETE EST REJOUEE ICI, ET C'EST UNE CORRECTION. 2fff6b6 comparait a
# `d1`, pris ~70 lignes PLUS HAUT — avant que les trois jobs sans titre
# n'existent. La fixture n'etait pas en base quand la reponse etait prise :
# AUCUN changement de la route ne pouvait faire rougir cette ligne. PROUVE
# par la mutation MOLD (l'assertion d'avant remise, filtre de titre retire
# en meme temps) : 72/5 ici, 70/5 sur le banc de 2fff6b6 qui ne portait pas
# les deux lignes de la branche vide — cinq lignes rouges, et celle-ci
# VERTE. Son commentaire affirmait « tenir l'autre cote » ; elle ne tenait
# rien.
# ET ELLE PORTE LES TROIS JOBS SANS TITRE, pas le seul I(21) : rejouer la
# requete NE SUFFIT PAS. Mutation M21 (requete rejouee, assertion sur le
# seul I(21)) => 72/5, ENCORE VERTE — le plafond de 5 cache I(21), le plus
# ancien des trois, derriere cinq homonymes plus recents. Sous la forme
# livree, c'est I(22) qui la fait rougir, et le temoin de la ligne le
# montre. La propriete est « AUCUN job a titre normalise vide n'est
# propose », pas « celui-la n'y est pas ».
d1b = J(api("GET", "/api/montage/newer?job_id=" + I(1)))
_ids1b = IDS(d1b)
_sans_titre = [I(20), I(21), I(22)]
check("newer_un_job_sans_titre_n_est_jamais_candidat",
      isinstance(_ids1b, list)
      and [x for x in _sans_titre if x in _ids1b] == [],
      f"{_ids1b}")

# Reference SANS `completed_at` : rien a comparer, donc rien a proposer.
pose(I(23), "seedance", F_MP4, "plan_01", None,
     statut=JobStatus.GENERATING_VIDEO.value)
d6 = J(api("GET", "/api/montage/newer?job_id=" + I(23)))
check("newer_reference_sans_date_ne_propose_rien", CAND(d6) == [], f"{CAND(d6)}")

print("\n[1-ter] le suffixe « (aperçu 480p) » et la casse")
# MESURE (protocole en tete) : c'est le SEUL suffixe que ce depot ajoute a un
# titre de job (montage_service.py l. 2406), et il n'apparait que sur des
# jobs `montage`. Les candidats excluant `montage`, il ne peut mordre que sur
# la REFERENCE — c'est exactement ce que cette section joue.
pose(I(30), "montage", F_MP4, "plan_09 (aperçu 480p)", T0)
pose(I(31), "seedance", F_MP4B, "Plan_09", T0 + timedelta(minutes=10))
d7 = J(api("GET", "/api/montage/newer?job_id=" + I(30)))
check("titre_apercu_ignore", IDS(d7) == [I(31)], f"{IDS(d7)}")

print("\n[1-quater] le plafond de 5 borne des CANDIDATS, pas des lignes")
# 20 VIDEOS d'un AUTRE titre, plus recentes que 7 videos homonymes. Le bruit
# doit passer le `where` — sinon la requete ne le voit jamais et un
# `.limit(5)` ne se remarque pas : MESURE, avec 20 planches PNG a la place, la
# mutation ML laissait le banc a 74/0. Ici elle rend 0 candidat, parce que les
# cinq lignes les plus recentes sont TOUTES du bruit. C'est la lecon de
# P8-bis, appliquee a une route qui, elle, ne borne rien en SQL.
for k in range(20):
    pose(I(100 + k), "seedance", F_MP4B, "plan_bruit",
         T0 + timedelta(minutes=200 + k))
for k in range(7):
    pose(I(140 + k), "seedance", F_MP4B, "plan_seuil",
         T0 + timedelta(minutes=100 + k))
pose(I(160), "seedance", F_MP4, "plan_seuil", T0)
d8 = J(api("GET", "/api/montage/newer?job_id=" + I(160)))
# Les CINQ plus recentes des sept, dans l'ordre : litteral complet.
check("plafond_5_pris_apres_le_filtre_de_titre_et_de_video",
      IDS(d8) == [I(146), I(145), I(144), I(143), I(142)], f"{IDS(d8)}")

print("\n[2] le cœur JS, EXECUTE sous node")
# Meme montage que test_montage_bundle.py : shim par FICHIER (jamais
# `node -e` : la ligne de commande Windows plafonne a 32 767 caracteres),
# `"use strict"` en PROLOGUE (concatene, celui de la couche cesserait d'etre
# une directive et le cœur tournerait RELACHE ici alors que le navigateur
# l'execute strict), stub `r` pour que le CORPS des composants sans hook soit
# executable.
JSX = 'var r={jsx:function(t,p,k){return{t:t,p:p,k:k}},jsxs:function(t,p,k){return{t:t,p:p,k:k}}};\n'
probe = r"""
var out={};
var T=window.DzTracks;
/* MARQUEUR de « rend null ». `out.x=null` se relit `None` en Python, ce que
   rend AUSSI une cle ABSENTE : une demi-douzaine de lignes de ce banc
   seraient vertes sur un shim qui n'a rien produit — la faute n°2 exacte.
   Une chaine ne peut etre confondue avec ni l'un ni l'autre. */
function NUL(v){return v===null?"NULL":("PAS_NULL:"+JSON.stringify(v))}
/* le clip du plan : bornes, effets, transition, et une fenetre de source
   qui commence a 1 s. */
var C={tr:"v1",id:"v",start:2,end:8,srcIn:1,src:{job_id:"j1"},label:"plan_01",
       effects:[{type:"grain"}],transition:"fade",transition_s:0.4,
       fx:[{n:"glow"}]};
var R=T.replaceSrc(C,{job_id:"j2"},"plan_01 v2",3.0,1788000000000);
out.rep_src=R.clip.src;
out.rep_label=R.clip.label;
out.rep_effects=R.clip.effects;
out.rep_transition=R.clip.transition;
out.rep_transition_s=R.clip.transition_s;
out.rep_fx=R.clip.fx;
out.rep_start=R.clip.start;
out.rep_end=R.clip.end;
out.rep_srcIn=R.clip.srcIn;
out.rep_warn_non_vide=(typeof R.warn==="string"&&R.warn.length>0);
out.rep_warn=R.warn;
out.rep_note=R.note;
out.rep_hist=R.clip.src_history;
/* le clip d'ENTREE n'est pas mute : c'est ce qui rend `pushHistory()` utile
   (l'instantane pousse avant l'ecriture doit rester l'etat d'avant). */
out.rep_entree_intacte=JSON.stringify(C)===JSON.stringify(
  {tr:"v1",id:"v",start:2,end:8,srcIn:1,src:{job_id:"j1"},label:"plan_01",
   effects:[{type:"grain"}],transition:"fade",transition_s:0.4,
   fx:[{n:"glow"}]});
/* SOURCE ASSEZ LONGUE : rien ne bouge, aucun avertissement. */
var R2=T.replaceSrc(C,{job_id:"j3"},"plan_01 v3",20,1788000000000);
out.long_srcIn=R2.clip.srcIn;
out.long_end=R2.clip.end;
out.long_warn=R2.warn;
/* BORNE EXACTE : srcIn + duree consommee == duree de la source. */
var R3=T.replaceSrc(C,{job_id:"j4"},"v4",7,1788000000000);
out.borne_srcIn=R3.clip.srcIn;
out.borne_end=R3.clip.end;
out.borne_warn=R3.warn;
/* FENETRE seulement decalee : la source couvre la duree du plan mais pas a
   partir de l'ancien point d'entree. */
var R4=T.replaceSrc(C,{job_id:"j5"},"v5",6.5,1788000000000);
out.glisse_srcIn=R4.clip.srcIn;
out.glisse_end=R4.clip.end;
out.glisse_warn_non_vide=(R4.warn.length>0);
out.glisse_pas_raccourci=(R4.clip.end===8);
/* VITESSE : a x2 le plan consomme deux fois plus de source. */
var CS={tr:"v1",id:"s",start:0,end:4,srcIn:0,speed:2};
var R5=T.replaceSrc(CS,{job_id:"j6"},"v6",4,1788000000000);
out.vit_end=R5.clip.end;
out.vit_warn_non_vide=(R5.warn.length>0);
/* DUREE INCONNUE (0) : la base reelle en a 53 sur 97 (mesure du 05/09/2026
   sous la clause LIVREE `coalesce(provider,'') != 'montage'` ; « 40 sur 84 »
   etait la meme mesure prise sous le defaut que cette clause repare). On ne
   peut rien verifier, et on le DIT plutot que de laisser le plan pointer
   dans le vide. */
var R6=T.replaceSrc(C,{job_id:"j7"},"v7",0,1788000000000);
out.inconnu_end=R6.clip.end;
out.inconnu_srcIn=R6.clip.srcIn;
out.inconnu_warn=R6.warn;
/* `srcOut` decrit la fenetre de l'ANCIENNE source : il est retire du clip
   remplace — ET MEMORISE dans l'entree d'historique, pour que le retour
   puisse le rendre. Les deux moities, mesurees separement. */
var R7=T.replaceSrc({tr:"v1",id:"o",start:0,end:4,srcIn:0,srcOut:9},
  {job_id:"j8"},"v8",20,1788000000000);
out.srcOut_retire=!("srcOut" in R7.clip);
out.srcOut_memorise=R7.clip.src_history[0].srcOut;
out.srcOut_rendu=T.revertSrc(R7.clip).clip.srcOut;
/* un clip qui n'en portait PAS n'en gagne pas au retour : la cle absente de
   l'entree dit au retour de ne rien poser (une pile ecrite par une version
   anterieure n'en a pas). */
out.srcOut_pas_invente=("srcOut" in T.revertSrc(R.clip).clip);
out.srcOut_pas_memorise=("srcOut" in R.clip.src_history[0]);
/* L'ALLER-RETOUR COMME UN TOUT, et non champ par champ : une cle AJOUTEE ou
   PERDUE par l'une des deux moities passait sous une liste de champs. La
   comparaison est CANONIQUE (cles triees recursivement) parce que `delete`
   puis reaffectation deplacent une cle en fin d'objet : c'est l'ORDRE qui
   change, pas le contenu, et c'est le contenu qui est la propriete. */
function CAN(v){
  if(v===null||typeof v!=="object")return JSON.stringify(v);
  if(Array.isArray(v))return "["+v.map(CAN).join(",")+"]";
  return "{"+Object.keys(v).sort().map(function(k){
    return JSON.stringify(k)+":"+CAN(v[k])}).join(",")+"}"}
var AR0={tr:"v1",id:"ar",start:2,end:8,srcIn:1,srcOut:9,src:{job_id:"j1"},
  label:"plan_01",effects:[{type:"grain"}],transition:"fade",
  transition_s:0.4,fx:[{n:"glow"}],speed:1.5,volume_points:[[0,1]],
  motion_points:[{t:0,x:0.5,y:0.5}],opacity:0.8};
/* duree COURTE a dessein : le remplacement bouge `srcIn` ET `end`, donc le
   retour doit rendre les deux — plus `srcOut`, plus le reste intact. */
out.ar_avant=CAN(AR0);
out.ar_apres=CAN(T.revertSrc(
  T.replaceSrc(AR0,{job_id:"j2"},"v2",2,1788000000000).clip).clip);
/* PLAFOND de l'historique : 10 entrees, les plus anciennes tombent. */
var acc={tr:"v1",id:"p",start:0,end:2,srcIn:0,src:{job_id:"j0"},label:"L0"};
for(var i=1;i<=12;i++)acc=T.replaceSrc(acc,{job_id:"j"+i},"L"+i,20,1000+i).clip;
out.hist_len=acc.src_history.length;
out.hist_premier=acc.src_history[0].label;
out.hist_dernier=acc.src_history[acc.src_history.length-1].label;
/* RETOUR ARRIERE : depile, rend la source, le libelle ET LES BORNES. */
var V=T.revertSrc(R.clip);
out.rev_src=V.clip.src;
out.rev_label=V.clip.label;
out.rev_srcIn=V.clip.srcIn;
out.rev_end=V.clip.end;
out.rev_hist_absent=!("src_history" in V.clip);
out.rev_effets_intacts=JSON.stringify(V.clip.effects);
out.rev_note=V.note;
out.rev_sans_historique=NUL(T.revertSrc({tr:"v1",id:"z",start:0,end:1}));
out.rev_nul=NUL(T.revertSrc(null));
/* deux crans d'affilee */
var V2=T.revertSrc(T.revertSrc(acc).clip);
out.rev2_label=V2.clip.label;
out.rev2_hist_len=V2.clip.src_history.length;
/* ── les deux boutons et le rappel ──────────────────────────────────────── */
var armed=0;
var b1=T.replaceBtn({id:"v",tr:"v1",src:{job_id:"j1"},label:"plan_01"},
  function(){armed++});
b1.p.onClick();
out.btn_label=b1.p.children;
out.btn_arme=armed;
out.btn_titre_dit_ce_qui_est_garde=(b1.p.title.indexOf("bornes")>=0
  &&b1.p.title.indexOf("effets")>=0&&b1.p.title.indexOf("transition")>=0);
/* un clip SANS source (les clips de la maquette de demonstration n'en ont
   pas) : pas de bouton — on ne remplace pas une source qui n'existe pas. */
out.btn_sans_src=NUL(T.replaceBtn({id:"d",tr:"v1",label:"demo"},function(){}));
out.btn_nul=NUL(T.replaceBtn(null,function(){}));
var reverted=0;
var b2=T.revertBtn(R.clip,function(){reverted++});
b2.p.onClick();
out.rev_btn_label=b2.p.children;
out.rev_btn_appelle=reverted;
out.rev_btn_nomme_l_ancien=(b2.p.title.indexOf("plan_01")>=0);
out.rev_btn_sans_historique=NUL(T.revertBtn({id:"z",tr:"v1"},function(){}));
/* la ligne du rappel « version plus recente » — PURE, donc mesurable ici ;
   le composant qui l'affiche interroge le reseau et n'est pas execute. */
out.nl_ligne=T.newerLine({job_id:"j9",title:"plan_01",
  completed_at:"2026-09-04T13:42:36Z",duration_s:3});
out.nl_sans_titre=T.newerLine({job_id:"j9"});
out.nl_nul=T.newerLine(null);
out.hint_existe=(typeof T.NewerHint==="function");
/* CINQ CANDIDATS HOMONYMES — la forme que la route rend PAR CONSTRUCTION,
   puisque le titre EST la cle du rapprochement. Les cinq dates sont celles
   du groupe « tweet_2026-05-20 » de la base reelle (7 jobs, plafond 5).
   Reduite au titre, la ligne rendait cinq boutons rigoureusement
   identiques — libelle ET aria-label. */
var HOM=[["a","2026-07-02T00:19:46",null],["b","2026-07-02T00:08:52",null],
         ["c","2026-07-01T23:40:56",null],["d","2026-07-01T23:39:35",null],
         ["e","2026-06-29T18:04:50",8]].map(function(t){
  return {job_id:t[0],title:"tweet_2026-05-20",completed_at:t[1],
          duration_s:t[2]}});
out.hom_lignes=HOM.map(function(c){return T.newerLine(c)});
out.hom_distinctes=(function(){var vu={},n=0;
  out.hom_lignes.forEach(function(l){if(!vu[l]){vu[l]=1;n++}});return n})();
/* LA SECONDE. Deux « backdoorpromo » de la base sont termines a 36 s
   d'intervalle : a la minute ils tombent encore dans deux minutes
   distinctes, mais a vingt secondes d'ecart ils auraient rendu la MEME
   chaine. Ces deux-ci sont a 18 s. */
out.sec_a=T.newerLine({job_id:"x",title:"backdoorpromo",
  completed_at:"2026-07-01T14:55:34"});
out.sec_b=T.newerLine({job_id:"y",title:"backdoorpromo",
  completed_at:"2026-07-01T14:55:52"});
/* CE QUE LE TROU DEVIENT AU RENDU depend de la PISTE — TROIS cas, pas deux.
   V1 est la piste de BASE, dont les trous sont rendus `color=c=black`
   (montage_service.py, branche `s.get("gap")`) ; une piste d'INCRUSTATION
   pose ses clips en `overlay … enable='between(t,st,en)'` et laisse voir
   celle du dessous ; une piste SON pose les siens en `atrim`+`adelay` puis
   `amix` — rien ne remplit le trou, cette piste se TAIT, et aucune piste du
   dessous n'y « reapparait ». La bascule ne tenait que sur `tr==="v1"`,
   donc TOUTE piste non-V1 etait appelee piste d'overlay : la phrase juste
   pour V2 s'etait installee sur A1/A2/A3, et sur un clip SANS `tr`.
   CE N'EST PAS THEORIQUE : `replaceBtn` n'est garde que sur `sel.src` et le
   refus de genre de M15 PERMET audio->audio. Mesure sur la sauvegarde reelle
   de l'utilisateur (assets/montage_saved.json, 17 clips) : 8 portent une
   source — 4 v1, 2 v2, UN a1 et UN a2 — donc deux des huit boutons de
   remplacement possibles sont sur du son. Les 9 clips `s1` n'ont pas de
   source : le bouton ne s'y montre jamais, et la phrase ne dit donc rien
   d'une piste de sous-titres. */
out.warn_v2=T.replaceSrc(Object.assign({},C,{tr:"v2"}),{job_id:"jv2"},"v2",
  3.0,1788000000000).warn;
var CA={tr:"a2",id:"a",start:0,end:8,srcIn:0,src:{audio:"m.wav"},
        label:"musique"};
out.warn_a2=T.replaceSrc(CA,{audio:"n.wav"},"neuf",3.0,1788000000000).warn;
out.warn_a1=T.replaceSrc(Object.assign({},CA,{tr:"a1"}),{audio:"n.wav"},
  "neuf",3.0,1788000000000).warn;
/* SANS `tr` : `dzmKindOf("")` rend "video" — la MEME regle que `trackKind`
   du bundle — et le clip n'est pas v1, donc il recoit la phrase de
   l'incrustation. Ce cas recevait deja celle-la ; ce qui change, c'est
   qu'il ne la partage plus avec l'audio. */
out.warn_sans_tr=T.replaceSrc({id:"n",start:0,end:8,srcIn:0,
  src:{job_id:"jn"},label:"sans_tr"},{job_id:"jz"},"neuf",3.0,
  1788000000000).warn;
/* Une piste de SOUS-TITRES n'est NI v1, NI une incrustation, NI du son :
   `dzmKindOf("s1")` rend "subs", et la phrase s'arrete sans rien affirmer.
   Inatteignable en pratique (aucun clip `s1` ne porte de source), mais un
   cœur PUR se mesure sur ce qu'on lui donne, pas sur ce qu'on croit qu'il
   recevra. */
out.warn_s1=T.replaceSrc(Object.assign({},C,{tr:"s1"}),{job_id:"js1"},"s1",
  3.0,1788000000000).warn;
/* LA LARGEUR RENDUE, faute de navigateur : le nombre de caracteres AVANT
   l'ellipse. `.dzm-newerb` est `white-space:nowrap; overflow:hidden;
   text-overflow:ellipsis` dans une colonne de 300 px — de 42 a 48
   caracteres visibles (le calcul est en tete de `dzmNewerLine`). On coupe
   au PIRE cas, 42, et on demande que les deux discriminants y tiennent
   ENTIERS. C'est ce prefixe-la que l'utilisateur voyant lit. */
function COUPE(l){return String(l).slice(0,42)}
out.coupe_hom=out.hom_lignes.map(COUPE);
out.coupe_sec_a=COUPE(out.sec_a);out.coupe_sec_b=COUPE(out.sec_b);
out.coupe_hom_distinctes=(function(){var vu={},n=0;
  out.coupe_hom.forEach(function(l){if(!vu[l]){vu[l]=1;n++}});return n})();
console.log(JSON.stringify(out));
"""
shim = pathlib.Path(TMP) / "shim.js"
shim.write_text('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + JSX
                + LAYER.read_bytes().decode("utf-8-sig") + "\n" + probe,
                encoding="utf-8")
r = subprocess.run(["node", str(shim)], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
if r.returncode != 0:
    check("js_shim_execute", False, (r.stderr or "")[-600:])
    d = {}
else:
    check("js_shim_execute", True)
    # Rougir, pas mourir : `splitlines()[-1]` sur une sortie vide leve
    # IndexError, `json.loads` sur une derniere ligne qui n'est pas du JSON
    # leve JSONDecodeError — et node peut sortir rc=0 dans les deux cas.
    _lignes = r.stdout.strip().splitlines()
    _derniere = _lignes[-1] if _lignes else ""
    try:
        d = json.loads(_derniere) if _derniere else None
        _mal = "" if isinstance(d, dict) and d else "sortie sans objet JSON"
    except Exception as _e:
        d, _mal = None, "%s: %s" % (type(_e).__name__, _e)
    if not isinstance(d, dict):
        d = {}
    check("js_shim_rend_un_objet_json", _mal == "",
          f"{_mal} — {len(_lignes)} ligne(s), derniere={_derniere[:160]!r}")

check("js_remplace_pose_la_nouvelle_source",
      d.get("rep_src") == {"job_id": "j2"}, str(d.get("rep_src")))
check("js_remplace_pose_le_nouveau_libelle",
      d.get("rep_label") == "plan_01 v2", str(d.get("rep_label")))
check("js_remplace_garde_les_effets",
      d.get("rep_effects") == [{"type": "grain"}], str(d.get("rep_effects")))
check("js_remplace_garde_la_transition",
      d.get("rep_transition") == "fade" and d.get("rep_transition_s") == 0.4,
      f'{d.get("rep_transition")} / {d.get("rep_transition_s")}')
check("js_remplace_garde_les_chips_fx_historiques",
      d.get("rep_fx") == [{"n": "glow"}], str(d.get("rep_fx")))
check("js_remplace_garde_le_debut", d.get("rep_start") == 2,
      str(d.get("rep_start")))
check("js_remplace_ramene_srcIn_a_zero", d.get("rep_srcIn") == 0,
      str(d.get("rep_srcIn")))
check("js_remplace_raccourcit_la_fin_a_5", d.get("rep_end") == 5,
      str(d.get("rep_end")))
check("js_remplace_avertit_quand_la_source_est_plus_courte",
      d.get("rep_warn_non_vide") is True, str(d.get("rep_warn")))
# Le texte doit porter les DEUX durees : « plus courte » sans chiffres
# n'apprend rien a qui doit decider s'il rogne ou s'il rallonge.
check("js_avertissement_donne_les_deux_durees",
      isinstance(d.get("rep_warn"), str) and "3.00" in d["rep_warn"]
      and "6.00" in d["rep_warn"], str(d.get("rep_warn")))
# GESTE DESTRUCTIF : la note doit dire ce qu'« annuler » NE RESTAURE PAS.
check("js_note_dit_les_limites_de_l_annulation",
      isinstance(d.get("rep_note"), str)
      and "durée du projet" in d["rep_note"] and "pistes" in d["rep_note"],
      str(d.get("rep_note")))
check("js_note_nomme_la_seconde_voie_de_retour",
      isinstance(d.get("rep_note"), str)
      and "version précédente" in d["rep_note"], str(d.get("rep_note")))
# `src_history` : LITTERAL complet. Une comparaison par sous-chaine ou un
# `len(...) == 1` resterait vert sur une entree amputee de ses bornes — et
# c'est justement des bornes que depend le retour arriere.
check("js_historique_empile_l_ancienne_source_ET_SES_BORNES",
      d.get("rep_hist") == [{"src": {"job_id": "j1"}, "label": "plan_01",
                             "srcIn": 1, "end": 8, "at": 1788000000000}],
      str(d.get("rep_hist")))
check("js_remplace_ne_mute_pas_le_clip_d_entree",
      d.get("rep_entree_intacte") is True, str(d.get("rep_entree_intacte")))
check("js_source_assez_longue_ne_bouge_rien",
      d.get("long_srcIn") == 1 and d.get("long_end") == 8
      and d.get("long_warn") == "",
      f'{d.get("long_srcIn")} {d.get("long_end")} {d.get("long_warn")!r}')
check("js_borne_exacte_ne_bouge_rien",
      d.get("borne_srcIn") == 1 and d.get("borne_end") == 8
      and d.get("borne_warn") == "",
      f'{d.get("borne_srcIn")} {d.get("borne_end")} {d.get("borne_warn")!r}')
check("js_fenetre_decalee_ramene_le_point_d_entree_sans_raccourcir",
      d.get("glisse_srcIn") == 0 and d.get("glisse_pas_raccourci") is True
      and d.get("glisse_warn_non_vide") is True,
      f'{d.get("glisse_srcIn")} {d.get("glisse_end")}')
check("js_vitesse_double_consomme_deux_fois_plus_de_source",
      d.get("vit_end") == 2 and d.get("vit_warn_non_vide") is True,
      str(d.get("vit_end")))
check("js_duree_inconnue_ne_touche_a_rien",
      d.get("inconnu_end") == 8 and d.get("inconnu_srcIn") == 1,
      f'{d.get("inconnu_end")} {d.get("inconnu_srcIn")}')
check("js_duree_inconnue_le_dit",
      isinstance(d.get("inconnu_warn"), str)
      and "inconnue" in d["inconnu_warn"], str(d.get("inconnu_warn")))
# CE QUE LE TROU DEVIENT AU RENDU, dit PISTE PAR PISTE — TROIS cas.
# `_build_montage_command` pose un `color=c=black` sur les trous de V1 (la
# piste de BASE) ; V2 et au-dela sont des OVERLAYS
# (`overlay … enable='between(t,st,en)'`), l'incrustation s'arrete plus tot
# et c'est la piste du dessous qui reapparait ; une piste SON pose ses clips
# en `atrim`+`adelay` puis `amix`, rien ne remplit le trou et il n'y a
# AUCUNE piste du dessous a faire reapparaitre.
# La bascule d'avant ne testait que `tr==="v1"`, donc elle appelait piste
# d'overlay TOUT ce qui n'est pas V1 — l'audio compris. Une phrase fausse en
# avait remplace une autre, sur un autre ensemble de pistes. Trois lignes,
# une par cas, parce que deux ne suffisaient pas.
check("js_le_trou_de_V1_est_annonce_rendu_en_noir",
      isinstance(d.get("rep_warn"), str)
      and "rendu en noir à l'export" in d["rep_warn"], str(d.get("rep_warn")))
check("js_le_trou_d_une_incrustation_n_est_PAS_annonce_noir",
      isinstance(d.get("warn_v2"), str) and "noir" not in d["warn_v2"]
      and "piste du dessous" in d["warn_v2"]
      and "piste son" not in d["warn_v2"], str(d.get("warn_v2")))
# LE CAS AUDIO. Ni noir, ni piste du dessous : du silence. Et la RESERVE de
# la piste BOUCLEE, qui est le cas de l'unique clip A2 de la sauvegarde
# reelle : `_build_montage_command` prend le PREMIER clip d'une piste `loop`
# comme entree `music`, en `-stream_loop -1` coupee par `-t total`. Ses
# `start`/`end`/`srcIn` ne sont JAMAIS lus (il n'entre pas dans `a_clips`,
# ni donc dans `audio_end`) : le raccourcir ne change RIEN au rendu.
# Promettre un silence y aurait ete la meme faute d'un cran plus loin —
# vrai pour A1/A3, faux pour le clip que l'utilisateur a reellement.
check("js_le_trou_d_une_piste_son_est_du_silence_pas_une_piste_du_dessous",
      isinstance(d.get("warn_a1"), str)
      and "noir" not in d["warn_a1"]
      and "piste du dessous" not in d["warn_a1"]
      and "piste son" in d["warn_a1"]
      and "s'entend" in d["warn_a1"], str(d.get("warn_a1")))
check("js_le_cas_de_la_piste_bouclee_est_dit_et_non_promis_muet",
      isinstance(d.get("warn_a2"), str)
      and "BOUCLÉE" in d["warn_a2"]
      and d.get("warn_a2") == d.get("warn_a1"),
      f'a2={d.get("warn_a2")}\n      a1={d.get("warn_a1")}')
# UN CLIP SANS `tr` suit `dzmKindOf` comme les autres : "video", pas v1,
# donc l'incrustation. Il partageait la phrase avec l'audio ; il ne la
# partage plus.
_QUEUE = "et la timeline garde un trou derrière lui"


def _fate(w):
    """La QUEUE de l'avertissement — la part qui depend de la piste.

    Comparer les chaines entieres melerait la piste aux DUREES (les deux
    clips de sonde n'ont pas les memes bornes) : la ligne serait rouge pour
    une raison qui n'est pas la sienne.
    """
    i = (w or "").find(_QUEUE)
    return None if i < 0 else w[i + len(_QUEUE):]


check("js_un_clip_sans_piste_suit_la_regle_video",
      _fate(d.get("warn_sans_tr")) is not None
      and _fate(d.get("warn_sans_tr")) == _fate(d.get("warn_v2")),
      f'{d.get("warn_sans_tr")}')
# ET RIEN N'EST AFFIRME D'UNE PISTE QU'ON N'A PAS MESUREE. « subs » n'est ni
# v1, ni une incrustation, ni du son : la phrase s'arrete au trou.
check("js_une_piste_de_sous_titres_ne_recoit_aucune_des_trois_phrases",
      isinstance(d.get("warn_s1"), str)
      and "noir" not in d["warn_s1"]
      and "piste du dessous" not in d["warn_s1"]
      and "piste son" not in d["warn_s1"]
      and d["warn_s1"].endswith("garde un trou derrière lui."),
      str(d.get("warn_s1")))
check("js_remplace_retire_srcOut", d.get("srcOut_retire") is True,
      str(d.get("srcOut_retire")))
# ...ET LE MEMORISE, pour que le retour puisse le rendre. `srcOut` est LU :
# son-vfx-montage.js affiche `sel.srcOut != null ? sel.srcOut :
# (sel.end - sel.start) * vitesse` dans la ligne « Out » de l'inspecteur. Le
# garder apres un remplacement ferait mentir cette ligne ; ne pas le rendre
# apres un retour la ferait mentir dans l'AUTRE sens.
check("js_srcOut_memorise_puis_rendu_par_le_retour",
      d.get("srcOut_memorise") == 9 and d.get("srcOut_rendu") == 9,
      f'mémorisé={d.get("srcOut_memorise")} rendu={d.get("srcOut_rendu")}')
check("js_srcOut_n_est_pas_invente_quand_le_clip_n_en_avait_pas",
      d.get("srcOut_pas_invente") is False
      and d.get("srcOut_pas_memorise") is False,
      f'rendu={d.get("srcOut_pas_invente")} '
      f'mémorisé={d.get("srcOut_pas_memorise")}')
# L'ALLER-RETOUR COMME UN TOUT. Les six lignes `rev_*` ci-dessous verifient
# le retour CHAMP PAR CHAMP : une cle AJOUTEE ou PERDUE par l'une des deux
# moities passait dessous — et c'est exactement ce qui arrivait, `srcOut`
# etant supprime par `replaceSrc` et absent de l'entree d'historique. Cette
# ligne-ci a ROUGI avant le correctif (mesure du 05/09/2026 : identite vraie
# sur un clip sans `srcOut`, FAUSSE des qu'il en portait un) ; elle force la
# decision a etre explicite plutot que tacite.
check("js_l_aller_retour_est_l_identite_CLE_POUR_CLE",
      isinstance(d.get("ar_avant"), str) and d.get("ar_avant") == d.get("ar_apres"),
      f'\n      avant={d.get("ar_avant")}\n      après={d.get("ar_apres")}')
check("js_historique_plafonne_a_dix", d.get("hist_len") == 10,
      str(d.get("hist_len")))
check("js_historique_jette_les_plus_anciennes",
      d.get("hist_premier") == "L2" and d.get("hist_dernier") == "L11",
      f'{d.get("hist_premier")} .. {d.get("hist_dernier")}')
check("js_retour_rend_la_source_precedente",
      d.get("rev_src") == {"job_id": "j1"} and d.get("rev_label") == "plan_01",
      f'{d.get("rev_src")} {d.get("rev_label")}')
check("js_retour_rend_AUSSI_les_bornes_d_alors",
      d.get("rev_srcIn") == 1 and d.get("rev_end") == 8,
      f'{d.get("rev_srcIn")} {d.get("rev_end")}')
check("js_retour_depile_et_retire_l_historique_vide",
      d.get("rev_hist_absent") is True, str(d.get("rev_hist_absent")))
check("js_retour_garde_les_effets",
      d.get("rev_effets_intacts") == '[{"type":"grain"}]',
      str(d.get("rev_effets_intacts")))
check("js_retour_sans_historique_rend_null",
      d.get("rev_sans_historique") == "NULL" and d.get("rev_nul") == "NULL",
      f'{d.get("rev_sans_historique")} / {d.get("rev_nul")}')
check("js_retour_deux_crans", d.get("rev2_label") == "L10"
      and d.get("rev2_hist_len") == 8,
      f'{d.get("rev2_label")} {d.get("rev2_hist_len")}')
check("js_bouton_remplacer_arme_une_fois", d.get("btn_arme") == 1,
      str(d.get("btn_arme")))
check("js_bouton_remplacer_porte_le_libelle_du_plan",
      d.get("btn_label") == "Remplacer la source…", str(d.get("btn_label")))
check("js_bouton_remplacer_dit_ce_qui_est_garde",
      d.get("btn_titre_dit_ce_qui_est_garde") is True,
      str(d.get("btn_titre_dit_ce_qui_est_garde")))
check("js_bouton_remplacer_absent_sans_source",
      d.get("btn_sans_src") == "NULL" and d.get("btn_nul") == "NULL",
      f'{d.get("btn_sans_src")} / {d.get("btn_nul")}')
check("js_bouton_retour_appelle_le_retour", d.get("rev_btn_appelle") == 1,
      str(d.get("rev_btn_appelle")))
check("js_bouton_retour_porte_son_libelle",
      d.get("rev_btn_label") == "Revenir à la version précédente",
      str(d.get("rev_btn_label")))
check("js_bouton_retour_nomme_la_source_qu_il_rendra",
      d.get("rev_btn_nomme_l_ancien") is True,
      str(d.get("rev_btn_nomme_l_ancien")))
check("js_bouton_retour_absent_sans_historique",
      d.get("rev_btn_sans_historique") == "NULL",
      str(d.get("rev_btn_sans_historique")))
# L'ORDRE DE LA LIGNE : les deux DISCRIMINANTS d'abord, le titre ensuite, le
# verbe en queue. Le titre est la CLE du rapprochement, donc le meme pour
# tous par construction : c'est la seule part de la ligne dont la troncature
# ne coute rien. Le libelle est tronque a l'ellipse (voir les lignes de
# largeur plus bas) ; ce qui est en tete est ce qui survit.
check("js_ligne_du_rappel",
      d.get("nl_ligne") == "04/09 13:42:36 UTC · 3,0 s · plan_01 — remplacer",
      str(d.get("nl_ligne")))
check("js_ligne_du_rappel_sans_titre_nomme_le_job",
      d.get("nl_sans_titre") == "durée inconnue · j9 — remplacer",
      str(d.get("nl_sans_titre")))
check("js_ligne_du_rappel_nulle", d.get("nl_nul") == "", str(d.get("nl_nul")))
# LE POINT DE CETTE LIGNE. Le TITRE est la cle du rapprochement : tous les
# candidats le partagent PAR CONSTRUCTION. Reduite au titre, la ligne rendait
# N boutons rigoureusement identiques — et l'infobulle conseillait
# « verifiez le titre », un conseil que la construction rend impossible a
# suivre. MESURE sur la base reelle : trois groupes homonymes exploitables,
# « tweet_2026-05-20 » (7 jobs), « last launch 2 » (3), « backdoorpromo » (2)
# — donc jusqu'a CINQ boutons jumeaux a l'ecran (plafond 5).
check("js_cinq_candidats_homonymes_donnent_cinq_lignes_distinctes",
      d.get("hom_distinctes") == 5,
      f'{d.get("hom_distinctes")} distincte(s) — {d.get("hom_lignes")}')
# La DUREE est le second discriminant, et le seul qui dise a l'avance si le
# plan va etre RACCOURCI. Elle est DITE inconnue plutot que tue : c'est le
# cas majoritaire en base (53 des 97), et c'est exactement l'avertissement
# que `replaceSrc` rendra.
check("js_la_ligne_annonce_une_duree_inconnue_plutot_que_de_la_taire",
      isinstance(d.get("hom_lignes"), list) and len(d["hom_lignes"]) == 5
      and all("durée inconnue" in _l for _l in d["hom_lignes"][:4])
      and "8,0 s" in d["hom_lignes"][4],
      str(d.get("hom_lignes")))
check("js_la_seconde_separe_deux_rendus_de_la_meme_minute",
      d.get("sec_a") != d.get("sec_b")
      and isinstance(d.get("sec_a"), str) and "14:55:34" in d["sec_a"]
      and "14:55:52" in (d.get("sec_b") or ""),
      f'{d.get("sec_a")} / {d.get("sec_b")}')
# ─────────────────────────────────────────────────────────────────────────
# LA LARGEUR RENDUE. Les trois lignes ci-dessus tenaient le CONTENU de la
# chaine ; elles etaient vertes sur une ligne dont l'utilisateur VOYANT ne
# lisait rien du discriminant. `.dzm-newerb` est `white-space:nowrap;
# overflow:hidden; text-overflow:ellipsis` (shared/montage.css) dans une
# colonne `.svm-insp` de 300 px : de 233 a 249 px utiles, soit de 42 a 48
# caracteres a 9 px selon la fonte resolue — une BORNE, pas un nombre, et
# rien ici ne rend une page. On mesure donc au PIRE cas, 42 caracteres.
# DANS L'ANCIEN ORDRE les secondes tombaient au caractere 48 a 54 : les
# cinq boutons « tweet_2026-05-20 » redevenaient IDENTIQUES a l'ecran, et
# les deux « backdoorpromo » a 36 s d'ecart — la paire meme qui justifiait
# d'afficher la seconde — aussi. Ces deux lignes-ci sont celles qui
# rougissent si le prefixe partage revient en tete.
check("js_les_lignes_restent_distinctes_UNE_FOIS_TRONQUEES_a_42_caracteres",
      d.get("coupe_hom_distinctes") == 5,
      f'{d.get("coupe_hom_distinctes")} distincte(s) sur 5 — '
      f'{d.get("coupe_hom")}')
check("js_la_seconde_survit_a_la_troncature",
      isinstance(d.get("coupe_sec_a"), str)
      and "14:55:34" in d["coupe_sec_a"]
      and "14:55:52" in (d.get("coupe_sec_b") or "")
      and d.get("coupe_sec_a") != d.get("coupe_sec_b"),
      f'{d.get("coupe_sec_a")} / {d.get("coupe_sec_b")}')
# LA DUREE AUSSI, y compris dans sa forme la plus longue (« durée
# inconnue », 14 caracteres, le cas MAJORITAIRE en base : 53 des 97).
check("js_la_duree_survit_a_la_troncature_meme_quand_elle_est_inconnue",
      isinstance(d.get("coupe_hom"), list) and len(d["coupe_hom"]) == 5
      and all("durée inconnue" in _l for _l in d["coupe_hom"][:4])
      and "8,0 s" in d["coupe_hom"][4],
      str(d.get("coupe_hom")))
check("js_le_composant_du_rappel_existe", d.get("hint_existe") is True,
      str(d.get("hint_existe")))

print("\n[3] la couche ne recopie NI la route NI une extension")
_src = LAYER.read_bytes().decode("utf-8-sig")
# La liste d'extensions vit dans montage_service.py et NULLE PART ailleurs
# (P9 l'avait deja arrete pour `isVideoJob`) : cette ligne le tient pour la
# couche entiere, P6 comprise.
check("la_couche_ne_recopie_aucune_extension_video",
      not any(e in _src for e in (".mp4", ".mov", ".webm", ".mkv", ".m4v")),
      "montage.js ecrit une extension video en dur")
# L'ARIA-LABEL EST LA LIGNE, pas un second libelle. `DzmNewerHint` a des
# hooks : node ne peut pas l'executer, et c'est la SOURCE qui doit dire que
# le discriminant atteint aussi les lecteurs d'ecran. Sans cette ligne, cinq
# boutons pouvaient redevenir cinq aria-labels identiques sans qu'aucune
# assertion ne bouge.
check("l_aria_label_du_rappel_EST_la_ligne_discriminante",
      _src.count('"aria-label":DZM_NEWER_H+" : "+dzmNewerLine(c),') == 1
      and _src.count("children:dzmNewerLine(c)}") == 1,
      "le rappel affiche une ligne et en annonce une autre")
# ET LE SENS PARTAGE EST SORTI DES BOUTONS : dit UNE fois par l'en-tete
# `.dzm-newerh`, jamais N fois dans N libelles tronques. C'est la moitie du
# correctif de largeur ; l'autre est l'ordre de la ligne, tenu plus haut.
check("l_en_tete_porte_le_sens_partage_et_la_ligne_ne_le_repete_pas",
      _src.count('var DZM_NEWER_H="Rendus plus récents portant ce titre";')
      == 1
      and _src.count('className:"dzm-newerh"') == 1
      # le LITTERAL JS, pas la prose : le commentaire qui explique le
      # correctif cite forcement la phrase qu'il retire.
      and _src.count('"Version plus récente : "') == 0,
      "le préfixe partagé est encore répété dans chaque bouton")
# L'EN-TETE, LUI, NE PEUT PAS ETRE COUPE — et ce n'est pas un oubli de CSS,
# c'est LA raison pour laquelle il existe. Une regle qui gagnerait `nowrap`
# et `ellipsis` par symetrie avec `.dzm-newerb` reproduirait le defaut a
# l'endroit meme cense le corriger.
_css = (ROOT / "frontend" / "dist" / "shared"
        / "montage.css").read_bytes().decode("utf-8-sig")
_h = _css.find(".dzsvm .dzm-newerh{")
_hb = _css.find("}", _h)
check("l_en_tete_du_rappel_ne_peut_pas_etre_tronque",
      _h > 0 and "nowrap" not in _css[_h:_hb]
      and "ellipsis" not in _css[_h:_hb],
      f"règle .dzm-newerh absente ou tronquable : {_css[_h:_hb + 1]!r}")
# L'INFOBULLE NE CONSEILLE PLUS DE VERIFIER LE TITRE : il est le meme pour
# tous par construction. Elle nomme ce qui distingue reellement.
check("l_infobulle_du_rappel_pointe_le_vrai_discriminant",
      "Vérifiez le titre avant de remplacer" not in _src
      and "c'est la date et la durée" in _src,
      "l'infobulle conseille encore un contrôle impossible à faire")
# LE MEME CHIFFRE MESURE, CITE A TROIS ENDROITS — le service, la couche et ce
# banc. Le commit 82c2689 a corrige le service et LAISSE les deux autres :
# « 40 des 84 » a survecu dans montage.js ET DANS LE BUNDLE LIVRE. Trois
# copies d'une mesure, aucune ligne pour les tenir ensemble : cette ligne-ci
# est cette ligne. Elle ne juge pas la mesure (le PROTOCOLE du docstring s'en
# charge), elle juge qu'aucune des trois n'est restee en arriere.
# La POPULATION est la meme dans les trois — les jobs video `done`
# non-montage sous la clause LIVREE, 97 — et seul le sous-ensemble compte
# change (53 sans duree, 61 sans titre). Un fichier reste en arriere et le
# denominateur redevient 84 : c'est ce que cette ligne voit.
_svc = SERVICE.read_bytes().decode("utf-8")
_moi = pathlib.Path(__file__).read_bytes().decode("utf-8")
check("le_chiffre_de_la_duree_inconnue_est_le_meme_partout",
      "53 des 97 jobs vidéo `done` non-montage ont `duration_s`" in _src
      and "53 sur 97" in _moi
      and "61 des 97 jobs vidéo `done` non-montage n'ont PAS de titre"
      in _svc,
      "une des trois citations de la mesure est restée en arrière")
# UN SEUL APPELANT dans la couche. On compte la forme `fetch("…` et non le
# chemin nu : le chemin est cite une seconde fois dans l'en-tete de contrat de
# la couche, ou il DOIT etre lisible. Ce qui ne doit pas se dedoubler, c'est
# l'appel — deux appelants divergeraient sur les parametres.
check("la_couche_n_a_qu_un_appelant_de_la_route_newer",
      _src.count('fetch("/api/montage/newer') == 1,
      f"""count={_src.count('fetch("/api/montage/newer')}""")
_svc = SERVICE.read_bytes().decode("utf-8-sig")
check("le_service_declare_la_route_newer",
      _svc.count('@router.get("/newer")') == 1,
      f"""count={_svc.count('@router.get("/newer")')}""")
# `_is_video_artifact` REUTILISE, pas recopie : la route ne doit porter
# aucune liste d'extensions a elle.
check("la_route_reutilise_is_video_artifact",
      _svc.count("_is_video_artifact") >= 3
      and _svc.count("_VIDEO_EXTS = (") == 1,
      f'{_svc.count("_is_video_artifact")} appels')

# La ligne qui dit que le banc a ROUGI plutot que MEURE.
check("aucun_appel_n_a_plante", _plantages == 0,
      f"{_plantages} appel(s) ont leve — voir les lignes « ---- » ci-dessus")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
