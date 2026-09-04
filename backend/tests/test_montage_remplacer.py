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
      48 jobs `done` non-montage a artefact .mp4 et titre NUL de la base de
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
    l'ANCIENNE source). MESURE — il n'existe AUJOURD'HUI que sur un seul
    clip de tout le depot, la maquette de demonstration du bundle (l. 1165),
    et sur aucun des 17 clips de la sauvegarde reelle. Le retrait est donc
    sans effet OBSERVABLE aujourd'hui ; il est la parce que
    `svmApplyProject` recopie les cles inconnues d'une sauvegarde telles
    quelles, et qu'un « Out » herite de l'ancienne source serait un mensonge
    a l'ecran. Exerce par `js_remplace_retire_srcOut`.
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
  84 jobs `done` non-montage dont l'artefact resolu
  (`coalesce(nullif(final_video_path,''), video_path)`) finit par `.mp4` ;
  48 d'entre eux ont un titre NUL ou vide ; 40 ont `duration_s` NUL ou <= 0.
  13 jobs `done` a `provider IS NULL`, tous des .mp4 — aucun ne porte de
  titre AUJOURD'HUI, donc la correction du point [5] ne change rien
  d'OBSERVABLE sur cette base : elle ferme un piege SQL, pas un defaut
  constate.
  Suffixe de titre : 8 lignes portent « (aperçu 480p) », toutes
  `provider='montage'` (3 `done`, 5 `failed`) ; ZERO ligne non-montage en
  porte. Le seul point du depot qui l'ajoute est montage_service.py l. 2253.
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

DIX-HUIT MUTATIONS, jouees le 04/09/2026. PROTOCOLE : le fichier vise est
reecrit sur DISQUE (texte en newlines universelles puis reecrit en CRLF pour
le service et la couche ; en OCTETS pour le bundle, qui melange minifie sans
saut de ligne et blocs CRLF), le banc relance en PROCESSUS NEUF depuis
backend/, le fichier restaure quoi qu'il arrive (try/finally + verification du
sha256) ; scripts scratchpad/mut6_run.py et scratchpad/mut6_bundle.py. Ligne
verte de reference : 75/0 pour ce banc, 304/0 pour test_montage_bundle.py.

  SUR LA ROUTE (banc : celui-ci)
  MV   garde du titre vide retiree      => 74/1, `newer_titre_vide_ne_
       propose_rien` SEULE. (`newer_titre_en_blancs_ne_propose_rien` reste
       VERTE, et c'est juste : « ␣␣␣ » se normalise en chaine vide seulement
       APRES `.strip()`, que la mutation ne touche pas — la ligne mesure
       l'autre moitie de la meme sortie.)
  MP   `coalesce(provider,'')` remplace par `provider != "montage"`
       => 72/3 : `newer_accepte_un_provider_nul`, la ligne d'ORDRE et
       `newer_rend_une_duree_nulle_telle_quelle` (le job a provider NUL est
       aussi celui dont la duree est nulle). C'EST LA MUTATION DU PIEGE SQL.
  MMON clause `provider` entierement retiree => 73/2 :
       `newer_ecarte_nos_propres_rendus_de_montage` et la ligne d'ORDRE.
  MVID test `_is_video_artifact` retire => 73/2 :
       `newer_ecarte_un_nom_de_fichier_sans_extension_analysable` et la ligne
       d'ORDRE. CE CHIFFRE A ETE GAGNE : sur la premiere version du banc,
       cette mutation donnait 74/0 — AUCUNE rouge, parce que le `where` de la
       requete dit deja la meme chose et qu'aucune fixture n'exploitait leur
       seule divergence. La fixture « fichier nomme exactement .mp4 » a ete
       ajoutee POUR CELA.
  MW   `where` de la liste blanche retire => 75/0, AUCUNE rouge, ET C'EST
       DECLARE. Sans `.limit()` sur la requete, ce `where` ne change pas la
       SORTIE : il ne change que le NOMBRE DE LIGNES chargees avant le filtre
       Python. Aucune assertion ne peut donc l'en distinguer, et il serait
       malhonnete de laisser croire le contraire. Il reste parce qu'il est
       gratuit et qu'il maintient la propriete que P8-bis a payee (la requete
       rend des candidats, pas des lignes a jeter) ; c'est un choix de cout,
       pas une correction.
  ML   `.limit(5)` pose sur la requete => 72/3 :
       `plafond_5_pris_apres_le_filtre_de_titre_et_de_video`, la ligne
       d'ORDRE et `newer_accepte_la_casse_et_les_espaces_de_bord`. CE CHIFFRE
       A LUI AUSSI ETE GAGNE : la premiere version posait 20 PLANCHES PNG
       comme bruit, que le `where` retire avant la requete — la mutation
       donnait 74/0. Le bruit est desormais du meme genre que les candidats
       (20 videos d'un AUTRE titre, plus recentes), et il consomme la fenetre.
  MEXI garde d'existence du fichier retiree => 73/2 :
       `newer_ecarte_une_source_disparue` et la ligne d'ORDRE.
  MSUF suffixe d'apercu non normalise => 74/1, `titre_apercu_ignore` SEULE.
  MCAS casse non normalisee => 72/3 :
       `newer_accepte_la_casse_et_les_espaces_de_bord`, `titre_apercu_ignore`
       (son candidat differe aussi par la casse) et la ligne d'ORDRE.
  MDAT garde `completed_at is None` retiree => 73/2 :
       `newer_reference_sans_date_ne_propose_rien` ET `aucun_appel_n_a_
       plante`. La seconde dit ce que la premiere ne dit pas : sans la garde,
       la route LEVE — `completed_at > None` n'est pas une comparaison. La
       garde n'est donc pas un raccourci, c'est la correction.
  MEXT `.mp4` retire de `_VIDEO_EXTS` => 66/9. C'est la mutation qui prouve
       que la route REUTILISE la liste du service au lieu d'en porter une
       copie : neuf lignes tombent, dont toutes celles qui attendent un
       candidat.
  (MSEL n'existe plus : la clause `id != job_id` du plan a ete RETIREE apres
   mesure — elle donnait 74/0, aucune ligne rouge. La comparaison de date est
   STRICTE, donc la reference n'est jamais plus recente qu'elle-meme ; la
   clause etait du code mort et la propriete reste tenue par
   `newer_ne_se_propose_pas_lui_meme`.)

  SUR LE CŒUR JS (banc : celui-ci)
  MJ1  plafond de `src_history` retire => 72/3 : les deux lignes du plafond
       et `js_retour_deux_crans`.
  MJ2  `revertSrc` ne rend plus les bornes => 74/1,
       `js_retour_rend_AUSSI_les_bornes_d_alors` SEULE. C'est l'ECART au plan
       (qui n'empilait que {src, label, at}) qui se mesure ici.
  MJ3  `replaceSrc` mute le clip d'entree => 66/9. La plus large, et elle le
       merite : un cœur qui mute son entree rend inutile l'instantane que
       l'ecran pousse AVANT d'ecrire.
  MJ4  duree inconnue passee sous silence => 74/1, `js_duree_inconnue_le_dit`
       SEULE.
  MJ5  `srcOut` conserve => 74/1, `js_remplace_retire_srcOut` SEULE.
  MJ6  note muette sur les limites de l'annulation => 73/2, les deux lignes
       de la note (ce qu'annuler ne rend pas, et la seconde voie de retour).

  SUR LA CHAINE (banc : test_montage_bundle.py, reference 304/0)
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
d3 = J(api("GET", "/api/montage/newer"))
check("newer_sans_job_id_rend_une_liste_vide", CAND(d3) == [], f"{CAND(d3)}")

# LE GARDE-FOU DU TITRE VIDE — hors plan, impose par la base reelle : 48 des
# 84 jobs video non-montage n'ont PAS de titre. Sans cette sortie, chacun
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
check("newer_un_job_sans_titre_n_est_jamais_candidat",
      isinstance(IDS(d1), list) and I(21) not in IDS(d1), f"{IDS(d1)}")

# Reference SANS `completed_at` : rien a comparer, donc rien a proposer.
pose(I(23), "seedance", F_MP4, "plan_01", None,
     statut=JobStatus.GENERATING_VIDEO.value)
d6 = J(api("GET", "/api/montage/newer?job_id=" + I(23)))
check("newer_reference_sans_date_ne_propose_rien", CAND(d6) == [], f"{CAND(d6)}")

print("\n[1-ter] le suffixe « (aperçu 480p) » et la casse")
# MESURE (protocole en tete) : c'est le SEUL suffixe que ce depot ajoute a un
# titre de job (montage_service.py l. 2253), et il n'apparait que sur des
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
/* DUREE INCONNUE (0) : la base reelle en a 40 sur 84. On ne peut rien
   verifier, et on le DIT plutot que de laisser le plan pointer dans le
   vide. */
var R6=T.replaceSrc(C,{job_id:"j7"},"v7",0,1788000000000);
out.inconnu_end=R6.clip.end;
out.inconnu_srcIn=R6.clip.srcIn;
out.inconnu_warn=R6.warn;
/* `srcOut` decrit la fenetre de l'ANCIENNE source : il est retire. */
var R7=T.replaceSrc({tr:"v1",id:"o",start:0,end:4,srcIn:0,srcOut:9},
  {job_id:"j8"},"v8",20,1788000000000);
out.srcOut_retire=!("srcOut" in R7.clip);
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
check("js_remplace_retire_srcOut", d.get("srcOut_retire") is True,
      str(d.get("srcOut_retire")))
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
check("js_ligne_du_rappel",
      d.get("nl_ligne") == "Version plus récente : plan_01 — remplacer",
      str(d.get("nl_ligne")))
check("js_ligne_du_rappel_sans_titre_nomme_le_job",
      d.get("nl_sans_titre") == "Version plus récente : j9 — remplacer",
      str(d.get("nl_sans_titre")))
check("js_ligne_du_rappel_nulle", d.get("nl_nul") == "", str(d.get("nl_nul")))
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
