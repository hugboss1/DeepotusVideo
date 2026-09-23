# -*- coding: utf-8 -*-
"""L4 — BANC CROISE service / route / couche / bundle / juge des medias : les
LISTES que la couche `montage.js` ecrit en dur (cadences `DZM_DEL_FPS`,
cibles `DZM_DEL_LOUD`) doivent etre CELLES du service (`_DELIVER_FPS`,
`_LOUD_TARGETS`), les ids de presets ne doivent exister NULLE PART dans le
client (ils viennent de `GET /api/montage/deliver-presets`), et les
extensions que les presets ecrivent doivent etre connues du juge des medias
-- ou DATEES comme ce que la Bibliotheque et le tiroir Medias ne classent
pas en « video ». Fichier SEPARE de test_montage_l4.py (un processus, un
code de sortie) : il ne monte NI TestClient NI l'app -- il lit la couche, le
bundle, le service, l'index de la Bibliotheque et routes.py en OCTETS,
importe le service seul et appelle la fonction de route directement.
Modeles : test_montage_l3_croise.py (import du service, deux mesures par
borne : le LITERAL et le COMPORTEMENT), test_montage_ec_croise.py (regex
gardees, etat vide).
Run : & $PY tests/test_montage_l4_croise.py   (depuis backend/)

CE QUI EST COMPARE, ET COMMENT. Chaque literal est extrait par une regex
GARDEE : le temoin positif (la regex trouve EXACTEMENT UNE fois) est une
assertion a part entiere, avant toute lecture du groupe -- faute n°6 : aucune
lecture nue, une regex qui ne trouve rien fait ROUGIR le banc, pas mourir.

  [1] D-35 : les ids de `_DELIVER` (import) == les ids ecrits dans la source
      (regex) == les `builtins` que la fonction de route rend ; AUCUN de ces
      ids n'apparait dans `montage.js` ni dans le bundle livre (temoin : dix
      ids cote service, `dzmDeliverOpts` x3 dans le bundle, GET x1 / PUT x1) ;
  [2] D-35 : `_DELIVER_FPS` (import) == `fps` de la route == `DZM_DEL_FPS`
      de la couche (regex) ; la couche construit ses options depuis
      `DZM_DEL_FPS` (x1 dans DzmDeliverRow, x1 dans dzmDeliverPayload) et
      NE LIT PAS `api.fps` (x0, temoins `api.builtins` x1 / `api.presets`
      x1) -- ECART DATE 23/09/2026 : le docstring de la couche annonce
      « le client n'a aucune liste en dur : les cadences viennent de GET »,
      la route sert bien `fps`, mais la couche porte SA liste et personne
      ne lit `fps` de l'API ; c'est CE banc qui tient les deux egales ;
      comportement : `_deliver_resolve` accepte chaque cadence de la couche
      et ignore 48 ;
  [3] D-24 : `_LOUD_TARGETS` (import) == les premiers elements de
      `DZM_DEL_LOUD` (regex, literal JSON) ; `_loud_target` accepte chacune
      et refuse -19, "-14", True ;
  [4] D-35 : les extensions de `_DELIVER` ⊂ `media_rules()["video_exts"]`
      ∪ {.gif, .wav, .mp3, .m4a, .webm, .mov} ; DATE : ce que `video=1`
      (tiroir Medias, `routes.py` passe par le MEME `media_rules`) ne
      classe pas en video = EXACTEMENT {.gif, .m4a, .mp3, .wav} ; les trois
      audio sont dans `_AUDIO_EXTS`, le `.gif` n'est ni video ni image de
      la Bibliotheque (`_IMAGE_EXTS` de library_index).

Regle des assertions negatives : chaque « n'est pas » est precede dans la
MEME expression du temoin positif qui etablit que la mesure a eu lieu.
"""
import asyncio
import json
import os
import re
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl4x_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def lire(rel):
    """Le fichier en OCTETS, decode, LF -- ou "" (le banc rougit, ne meurt pas)."""
    p = os.path.join(ROOT, *rel.split("/"))
    try:
        return open(p, "rb").read().decode("utf-8-sig").replace("\r\n", "\n")
    except OSError:
        return ""


def un(motif, texte, flags=0):
    """LA regex gardee : rend le match si le motif est trouve EXACTEMENT une
    fois, None sinon. Le compte est rendu a part pour le detail des lignes."""
    ms = list(re.finditer(motif, texte, flags))
    return (ms[0] if len(ms) == 1 else None), len(ms)


JS = lire("frontend/patches/montage.js")
BUN = lire("frontend/dist/assets/index-BEOJX8L5.js")
MSV = lire("backend/app/services/montage_service.py")
LIB = lire("backend/app/services/library_index.py")
RTS = lire("backend/app/api/routes.py")
check("x0_couche_bundle_service_index_et_routes_sont_lus_en_octets_et_non_vides",
      len(JS) > 100_000 and len(BUN) > 1_000_000 and len(MSV) > 100_000 and len(LIB) > 2_000 and len(RTS) > 50_000,
      (len(JS), len(BUN), len(MSV), len(LIB), len(RTS)))

try:
    from app.services import montage_service as ms
except Exception as e:                       # le banc rougit, ne meurt pas
    ms = None
    print(f"  (import du service impossible : {e!r})")
check("x0_le_service_est_importe_et_porte_les_quatre_symboles_L4",
      ms is not None and all(hasattr(ms, k) for k in ("_DELIVER", "_DELIVER_FPS", "_LOUD_TARGETS", "media_rules", "_deliver_resolve", "_loud_target", "montage_deliver_presets")),
      ms is not None and [k for k in ("_DELIVER", "_DELIVER_FPS", "_LOUD_TARGETS", "media_rules") if not hasattr(ms, k)])
DEL = dict(getattr(ms, "_DELIVER", {}) or {})
FPS = tuple(getattr(ms, "_DELIVER_FPS", ()) or ())
LOUD = tuple(getattr(ms, "_LOUD_TARGETS", ()) or ())

# -- [1] D-35 : les ids de presets ---------------------------------------
print("\n[1] D-35 : ids de _DELIVER == source == route, et AUCUN dans le client")
mT, nT = un(r'^_DELIVER = \{\n(.*?)^\}\n_DELIVER_DEFAUT = "([a-z0-9_]+)"$', MSV, re.M | re.S)
check("x1_la_table_DELIVER_est_lue_une_fois_dans_la_source_jusqu_a_DELIVER_DEFAUT", nT == 1 and mT is not None, nT)
IDS_SRC = re.findall(r'^    "([a-z0-9_]+)": \{$', mT.group(1), re.M) if mT else []
check("x1_dix_ids_dans_la_source_egaux_aux_cles_importees_defaut_master_1080",
      len(IDS_SRC) == 10 and len(set(IDS_SRC)) == 10 and list(DEL) == IDS_SRC and mT is not None and mT.group(2) == "master_1080" == getattr(ms, "_DELIVER_DEFAUT", None),
      (IDS_SRC, list(DEL)))
ROUTE = None
if ms is not None:
    try:
        ROUTE = asyncio.run(ms.montage_deliver_presets())
    except Exception as e:
        ROUTE = {"erreur": repr(e)}
check("x1_la_route_rend_builtins_id_label_dans_l_ordre_de_la_table_fps_et_presets_vides_sur_base_vide",
      isinstance(ROUTE, dict) and [b.get("id") for b in ROUTE.get("builtins", [])] == IDS_SRC == list(DEL) and len(IDS_SRC) == 10
      and all(b.get("label") == DEL[b["id"]]["label"] for b in ROUTE["builtins"]) and ROUTE.get("presets") == [],
      ROUTE if not isinstance(ROUTE, dict) or "erreur" in ROUTE else [b.get("id") for b in ROUTE.get("builtins", [])])
# AUCUN id dans le client : la couche lit `api.builtins` / `api.presets`, le
# bundle porte la couche (dzmDeliverOpts x2 : la definition et l'appel de
# DzmDeliverRow). `hevc` est un mot court : compte par mot entier.
_ids_js = {i: len(re.findall(r'\b' + i + r'\b', JS)) for i in IDS_SRC}
_ids_bun = {i: len(re.findall(r'\b' + i + r'\b', BUN)) for i in IDS_SRC}
check("x1_aucun_des_dix_ids_dans_la_couche_temoins_api_builtins_x1_api_presets_x1",
      len(IDS_SRC) == 10 and sum(_ids_js.values()) == 0 and JS.count("api.builtins") == 1 and JS.count("api.presets") == 1
      and JS.count("function dzmDeliverOpts(api){") == 1, {k: v for k, v in _ids_js.items() if v})
# MESURE 23/09/2026 : `dzmDeliverOpts(` x3 dans le bundle (le docstring de la
# couche, la definition, l'appel de DzmDeliverRow) ; `/api/montage/deliver-presets`
# x3 (le GET de l'effet L4a, le PUT de dzSavePreset, le docstring de la couche).
check("x1_aucun_des_dix_ids_dans_le_bundle_livre_temoin_dzmDeliverOpts_x3_et_deliver_presets_x3_GET_x1_PUT_x1",
      len(IDS_SRC) == 10 and sum(_ids_bun.values()) == 0 and BUN.count("dzmDeliverOpts(") == 3
      and BUN.count("/api/montage/deliver-presets") == 3 and BUN.count('fetch("/api/montage/deliver-presets")') == 1
      and BUN.count('fetch("/api/montage/deliver-presets",{method:"PUT"') == 1, ({k: v for k, v in _ids_bun.items() if v}, BUN.count("dzmDeliverOpts("), BUN.count("/api/montage/deliver-presets")))
# ETAT VIDE : le meme compteur voit bien un id quand il y en a un (la source
# du service en porte dix) -- sans ce temoin, « 0 dans le client » ne
# prouverait pas que le compteur compte.
check("x1_etat_vide_le_meme_compteur_trouve_chaque_id_au_moins_une_fois_dans_le_service",
      len(IDS_SRC) == 10 and all(len(re.findall(r'\b' + i + r'\b', MSV)) >= 1 for i in IDS_SRC)
      and len(re.findall(r'\bmaster_1080\b', MSV)) >= 2, [i for i in IDS_SRC if not re.search(r'\b' + i + r'\b', MSV)])

# -- [2] D-35 : les cadences ---------------------------------------------
print("\n[2] D-35 : _DELIVER_FPS == fps de la route == DZM_DEL_FPS de la couche")
mF, nF = un(r'^var DZM_DEL_FPS=\[([0-9,]+)\];$', JS, re.M)
mFs, nFs = un(r'^_DELIVER_FPS = \(([0-9, ]+)\)$', MSV, re.M)
FPS_JS = [int(x) for x in mF.group(1).split(",")] if mF else []
FPS_SRC = [int(x) for x in mFs.group(1).replace(" ", "").split(",")] if mFs else []
check("x2_les_deux_literaux_sont_lus_une_fois_chacun", nF == 1 and nFs == 1 and mF is not None and mFs is not None, (nF, nFs))
check("x2_couche_source_import_et_route_portent_la_meme_liste_24_25_30_60",
      FPS_JS == FPS_SRC == list(FPS) == [24, 25, 30, 60] and isinstance(ROUTE, dict) and ROUTE.get("fps") == FPS_JS,
      (FPS_JS, FPS_SRC, list(FPS), isinstance(ROUTE, dict) and ROUTE.get("fps")))
# la couche construit ses options depuis SA liste, et ne lit pas `api.fps`
check("x2_la_couche_rend_ses_options_depuis_DZM_DEL_FPS_x1_map_x1_indexOf_et_ne_lit_jamais_api_fps_ecart_date",
      nF == 1 and JS.count("DZM_DEL_FPS.map(") == 1 and JS.count("DZM_DEL_FPS.indexOf(f)>=0") == 1 and JS.count("DZM_DEL_FPS") == 5
      and JS.count("api.builtins") == 1 and JS.count("api.fps") == 0 and BUN.count("api.fps") == 0 and BUN.count("DZM_DEL_FPS.map(") == 1,
      (JS.count("DZM_DEL_FPS.map("), JS.count("DZM_DEL_FPS.indexOf(f)>=0"), JS.count("DZM_DEL_FPS"), JS.count("api.fps")))
# comportement : chaque cadence de la couche est prise par _deliver_resolve, 48 ignoree
_res = {}
if ms is not None:
    try:
        _res = {f: ms._deliver_resolve("master_1080", f)["fps"] for f in FPS_JS + [48]}
    except Exception as e:
        _res = {"erreur": repr(e)}
check("x2_comportement_deliver_resolve_prend_chaque_cadence_de_la_couche_et_ignore_48",
      len(FPS_JS) == 4 and all(_res.get(f) == f for f in FPS_JS) and _res.get(48) == 30, _res)

# -- [3] D-24 : les cibles de loudness ------------------------------------
print("\n[3] D-24 : _LOUD_TARGETS == DZM_DEL_LOUD de la couche")
mL, nL = un(r'^var DZM_DEL_LOUD=(\[\[.*?\]\]);$', JS, re.M)
mLs, nLs = un(r'^_LOUD_TARGETS = \(([-0-9, ]+)\)$', MSV, re.M)
LOUD_JS = None
if mL:
    try:
        LOUD_JS = json.loads(mL.group(1))
    except ValueError:
        LOUD_JS = None
LOUD_SRC = [int(x) for x in mLs.group(1).replace(" ", "").split(",")] if mLs else []
check("x3_les_deux_literaux_sont_lus_une_fois_chacun_et_la_couche_est_un_JSON_de_paires_valeur_libelle",
      nL == 1 and nLs == 1 and isinstance(LOUD_JS, list) and len(LOUD_JS) == 3
      and all(isinstance(p, list) and len(p) == 2 and isinstance(p[0], int) and isinstance(p[1], str) for p in LOUD_JS), (nL, nLs, LOUD_JS))
check("x3_couche_source_et_import_portent_14_16_23_dans_cet_ordre",
      isinstance(LOUD_JS, list) and [p[0] for p in LOUD_JS] == LOUD_SRC == list(LOUD) == [-14, -16, -23], (LOUD_JS, LOUD_SRC, list(LOUD)))
check("x3_la_couche_rend_ses_options_depuis_DZM_DEL_LOUD_x1_map_x1_some_et_chaque_libelle_porte_sa_valeur_en_moins_typographique",
      nL == 1 and JS.count("DZM_DEL_LOUD.map(") == 1 and JS.count("DZM_DEL_LOUD.some(") == 1 and JS.count("DZM_DEL_LOUD") == 5
      and isinstance(LOUD_JS, list) and all(p[1].startswith("−" + str(-p[0]) + " ") for p in LOUD_JS),
      (JS.count("DZM_DEL_LOUD.map("), JS.count("DZM_DEL_LOUD.some("), LOUD_JS))
_lt = {}
if ms is not None:
    for v in (LOUD_JS or []) and [p[0] for p in LOUD_JS] + [-19, "-14", True]:
        try:
            _lt[repr(v)] = ms._loud_target(v)
        except ValueError:
            _lt[repr(v)] = "refuse"
check("x3_comportement_loud_target_accepte_chaque_cible_de_la_couche_et_refuse_19_la_chaine_et_le_booleen",
      isinstance(LOUD_JS, list) and len(LOUD_JS) == 3 and all(_lt.get(repr(p[0])) == p[0] for p in LOUD_JS)
      and _lt.get("-19") == "refuse" and _lt.get("'-14'") == "refuse" and _lt.get("True") == "refuse", _lt)

# -- [4] D-35 : les extensions vs le juge des medias -----------------------
print("\n[4] D-35 : extensions des presets vs media_rules() -- ce que le tiroir Medias ne classe pas en video, date")
EXTS = sorted({str(v.get("ext")) for v in DEL.values()})
VID = tuple(ms.media_rules().get("video_exts") or ()) if ms is not None else ()
TOL = {".gif", ".wav", ".mp3", ".m4a", ".webm", ".mov"}
check("x4_les_dix_presets_ecrivent_sept_extensions_distinctes_toutes_connues_du_juge_ou_de_la_tolerance_datee",
      len(DEL) == 10 and len(EXTS) == 7 and len(VID) == 6 and set(EXTS) <= set(VID) | TOL, (EXTS, VID))
HORS = sorted(set(EXTS) - set(VID))
check("x4_date_23_09_2026_ce_que_video_1_ne_classe_pas_en_video_est_exactement_gif_m4a_mp3_wav",
      len(EXTS) == 7 and len(VID) == 6 and HORS == [".gif", ".m4a", ".mp3", ".wav"] and ".mp4" in VID and ".webm" in VID and ".mov" in VID, HORS)
mA, nA = un(r'^_AUDIO_EXTS = \(([^)]*)\)$', MSV, re.M)
AUD = re.findall(r'"(\.[a-z0-9]+)"', mA.group(1)) if mA else []
mI, nI = un(r'^_IMAGE_EXTS = \{([^}]*)\}$', LIB, re.M)
IMG = re.findall(r'"(\.[a-z0-9]+)"', mI.group(1)) if mI else []
check("x4_les_trois_audio_sont_dans_AUDIO_EXTS_et_le_gif_n_est_ni_video_ni_image_de_la_Bibliotheque",
      nA == 1 and nI == 1 and len(AUD) >= 5 and len(IMG) == 4 and all(e in AUD for e in (".m4a", ".mp3", ".wav"))
      and ".png" in IMG and ".gif" not in IMG and len(VID) == 6 and ".gif" not in VID, (nA, nI, AUD, IMG))
# routes.py juge `video=1` par le MEME media_rules (temoin de l'unicite du juge)
check("x4_routes_video_1_passe_par_media_rules_x1_et_le_service_le_definit_x1",
      RTS.count("_ms.media_rules().get(\"video_exts\")") == 1 and RTS.count("if video:") == 1
      and MSV.count("def media_rules() -> dict:") == 1 and MSV.count('return {"video_exts": list(_VIDEO_EXTS)}') == 1,
      (RTS.count("_ms.media_rules()"), MSV.count("def media_rules()")))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
