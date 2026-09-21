# -*- coding: utf-8 -*-
"""L2 — TRANSITIONS (D-20), TITRES (D-21), FONDUS EN DIRECT (D-12) cote
backend. En-tete recopie de test_montage_projets.py (env, check, J) : dossier
de donnees NEUF par execution, TestClient sans port ouvert, toute reponse
passee par `J()` et tout acces un `.get` — un banc qui meurt sur un `.json()`
nu ne dit pas quelles assertions manquent.
Run : & $PY tests/test_montage_l2.py   (depuis backend/)

[1] D-20 LE CATALOGUE DES TRANSITIONS. `_XFADE` (montage_service) porte deja
neuf cles historiques (nom libre -> (nom xfade, duree imposee|None)) lues par
`_build_montage_command`. L'ffmpeg livre (8.1.1 essentials, `-h filter=xfade`)
accepte 58 transitions (indices 0..57) ; parmi les neuf cles historiques,
trois (fade, dissolve, fadeblack) SONT deja des noms xfade a part entiere —
`flash` en revanche est un ALIAS dont la VALEUR est `fadewhite`, pas une cle
xfade elle-meme. Ce lot ajoute les 58 comme cles a part entiere (chacune sa propre cle),
les range en six familles nommees pour le selecteur client, leur donne un
libelle francais, et marque celles jouables EN DIRECT par le lecteur vivant
(D-12 : un voile noir/blanc ou une baisse d'opacite en CSS — tout le reste
n'est visible qu'apres Preview). GET /api/montage/transitions sert ce
catalogue : le client n'en a AUCUNE copie, meme precedent que GET /effects et
GET /media-rules.

L'ETAT VIDE DE CE BANC : avant l'implementation, `MS._XFADE_FAMILIES` et
`MS._XFADE_LABELS` n'existent pas du tout (AttributeError sur un acces nu) —
`A(nom, defaut)` (ci-dessous) les lit par `getattr` pour que cette absence
FASSE ROUGIR les assertions au lieu de TUER le banc avant qu'il ait fini de
parler (meme raison que `J()` sur les reponses HTTP). La route elle-meme est
absente (404) -> `J()` rend `{}`, donc `d20_la_route_rend_les_familles_et_le_
direct` rougit aussi. Regle des assertions negatives : la negation de cette
section (« le direct ne couvre QUE les fondus simples ») est precedee d'un
temoin positif (`r.status_code == 200` d'abord, jamais une negation nue).
"""
import json, os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl2_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi.testclient import TestClient                # noqa: E402
from app.main import app                                 # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def J(resp):
    """Corps JSON, ou {} — le banc doit ROUGIR, pas mourir sur un .json() nu."""
    try:
        v = resp.json()
    except Exception:
        return {}
    return v if isinstance(v, dict) else {"_liste": v}


c = TestClient(app, raise_server_exceptions=False)
c.__enter__()

print("\n[1] D-20 le catalogue des transitions est servi par le backend")
from app.services import montage_service as MS


def A(nom, defaut):
    """`getattr` module — un attribut ABSENT (avant l'implementation) doit
    faire ROUGIR les checks qui le lisent, jamais TUER le banc sur un
    AttributeError nu."""
    return getattr(MS, nom, defaut)


XFADE = A("_XFADE", {})
FAMILIES = A("_XFADE_FAMILIES", {})
LABELS = A("_XFADE_LABELS", {})
LIVE = A("_XFADE_LIVE", ())

XF58 = ("fade wipeleft wiperight wipeup wipedown slideleft slideright slideup slidedown "
        "circlecrop rectcrop distance fadeblack fadewhite radial smoothleft smoothright "
        "smoothup smoothdown circleopen circleclose vertopen vertclose horzopen horzclose "
        "dissolve pixelize diagtl diagtr diagbl diagbr hlslice hrslice vuslice vdslice "
        "hblur fadegrays wipetl wipetr wipebl wipebr squeezeh squeezev zoomin fadefast "
        "fadeslow hlwind hrwind vuwind vdwind coverleft coverright coverup coverdown "
        "revealleft revealright revealup revealdown").split()
check("d20_les_58_xfade_sont_des_cles_de_la_table",
      all(n in XFADE and XFADE[n][0] == n for n in XF58),
      [n for n in XF58 if n not in XFADE][:5])
check("d20_les_neuf_cles_historiques_sont_gardees_telles_quelles",
      XFADE.get("cut") == ("fade", 0.04) and XFADE.get("glitch") == ("pixelize", None)
      and XFADE.get("slide") == ("slideleft", None) and XFADE.get("flash") == ("fadewhite", None)
      and XFADE.get("crossfade") == ("fade", None))
check("d20_chaque_xfade_a_une_famille_et_une_seule",
      sorted(n for f in FAMILIES.values() for n in f.get("noms", [])) == sorted(XF58),
      len([n for f in FAMILIES.values() for n in f.get("noms", [])]))
check("d20_six_familles_nommees",
      list(FAMILIES) == ["fondus", "glissements", "volets", "formes", "zooms", "pixels"])
r = c.get("/api/montage/transitions"); d = J(r)
check("d20_la_route_rend_les_familles_et_le_direct",
      r.status_code == 200 and isinstance(d.get("familles"), list) and len(d["familles"]) == 6
      and sum(len(f.get("items", [])) for f in d["familles"]) == 58
      and all(set(i) >= {"id", "label", "live"} for f in d["familles"] for i in f["items"]),
      str(d)[:200])
# Un libelle FRANCAIS, pas seulement une cle presente : chaque `label` de la
# REPONSE doit differer de son `id` — sauf `distance`, dont le libelle EST le
# nom (aucune traduction plus parlante). `distance` verifie explicitement
# l'egalite plutot que d'etre exclu en silence : une famille qui livrerait un
# item sans le distinguer de `distance` doit quand meme rougir.
_items = [i for f in d.get("familles", []) for i in f.get("items", [])]
check("d20_chaque_libelle_est_ecrit_en_francais_non_vide",
      r.status_code == 200 and len(_items) == 58
      and all(isinstance(i.get("label"), str) and i["label"] for i in _items)
      and all(i["label"] != i["id"] for i in _items if i["id"] != "distance")
      and next((i["label"] for i in _items if i["id"] == "distance"), None) == "distance",
      str(_items)[:200])
check("d20_le_direct_ne_couvre_que_les_fondus_simples",
      r.status_code == 200
      and sorted(i["id"] for i in _items if i.get("live")) == ["fade", "fadeblack", "fadewhite"])
# Le repli sur une coupe franche est verifie sur le CODE DE PRODUCTION, pas
# reimplemente ici : deux segments V1 dont le second porte une transition
# INCONNUE ("zzz") -> `_build_montage_command` doit emettre le xfade "fade"
# a 0,04 s (le repli `_XFADE["cut"]`), jamais un filtre nomme "zzz". Forme
# des arguments recopiee du plus petit appel vert de
# tests/test_montage_pistes_rendu.py (v1_spec/ov_spec).
_v1_zzz = [
    {"path": "V1_A.mp4", "src_dur": 4.0, "src_in": 0.0, "start": 0.0, "end": 2.0,
     "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None},
    {"path": "V1_B.mp4", "src_dur": 4.0, "src_in": 0.0, "start": 2.0, "end": 4.0,
     "transition": "zzz", "transition_s": 0.0, "speed": 0.0, "effects": None},
]
_cmd_zzz, _ = MS._build_montage_command(_v1_zzz, [], [], None, w=64, h=64, fps=30,
                                        mix_db={}, ducking=False, duration_master=False,
                                        preview=True, out="zzz.mp4")
_flat = " ".join(_cmd_zzz)
check("d20_un_nom_inconnu_retombe_toujours_en_coupe_franche",
      "transition=fade:duration=0.04" in _flat and "transition=zzz" not in _flat,
      _flat[:300])

print(f"\n=== {ok} passed, {fail} failed ===")
c.__exit__(None, None, None)
sys.exit(1 if fail else 0)
