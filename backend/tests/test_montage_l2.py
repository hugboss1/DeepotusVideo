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
accepte 58 transitions (indices 0..57) ; seules trois (les neuf ne comptent
que fade/fadeblack/fadewhite comme xfade natifs) sont dans la table avant ce
lot. Ce lot ajoute les 58 comme cles a part entiere (chacune sa propre cle),
les range en six familles nommees pour le selecteur client, leur donne un
libelle francais, et marque celles jouables EN DIRECT par le lecteur vivant
(D-12 : un voile noir/blanc ou une baisse d'opacite en CSS — tout le reste
n'est visible qu'apres Preview). GET /api/montage/transitions sert ce
catalogue : le client n'en a AUCUNE copie, meme precedent que GET /effects et
GET /media-rules.

L'ETAT VIDE DE CE BANC : la route absente (404 avant l'implementation) ->
`J()` rend `{}`, les cles `familles`/`d20_*` sont donc toutes fausses par
construction et TOUTE la section [1] rougit avant l'etape 2 — c'est le tir
rouge exige par le protocole. Regle des assertions negatives : les deux
verifications negatives de cette section (`n not in MS._XFADE` — absent —,
et « le direct ne couvre QUE les fondus simples ») sont precedees d'un
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
XF58 = ("fade wipeleft wiperight wipeup wipedown slideleft slideright slideup slidedown "
        "circlecrop rectcrop distance fadeblack fadewhite radial smoothleft smoothright "
        "smoothup smoothdown circleopen circleclose vertopen vertclose horzopen horzclose "
        "dissolve pixelize diagtl diagtr diagbl diagbr hlslice hrslice vuslice vdslice "
        "hblur fadegrays wipetl wipetr wipebl wipebr squeezeh squeezev zoomin fadefast "
        "fadeslow hlwind hrwind vuwind vdwind coverleft coverright coverup coverdown "
        "revealleft revealright revealup revealdown").split()
check("d20_les_58_xfade_sont_des_cles_de_la_table",
      all(n in MS._XFADE and MS._XFADE[n][0] == n for n in XF58),
      [n for n in XF58 if n not in MS._XFADE][:5])
check("d20_les_neuf_cles_historiques_sont_gardees_telles_quelles",
      MS._XFADE["cut"] == ("fade", 0.04) and MS._XFADE["glitch"] == ("pixelize", None)
      and MS._XFADE["slide"] == ("slideleft", None) and MS._XFADE["flash"] == ("fadewhite", None)
      and MS._XFADE["crossfade"] == ("fade", None))
check("d20_chaque_xfade_a_une_famille_et_une_seule",
      sorted(n for f in MS._XFADE_FAMILIES.values() for n in f["noms"]) == sorted(XF58),
      len([n for f in MS._XFADE_FAMILIES.values() for n in f["noms"]]))
check("d20_six_familles_nommees",
      list(MS._XFADE_FAMILIES) == ["fondus", "glissements", "volets", "formes", "zooms", "pixels"])
check("d20_chaque_xfade_a_un_libelle_francais", all(n in MS._XFADE_LABELS for n in XF58))
r = c.get("/api/montage/transitions"); d = J(r)
check("d20_la_route_rend_les_familles_et_le_direct",
      r.status_code == 200 and isinstance(d.get("familles"), list) and len(d["familles"]) == 6
      and sum(len(f.get("items", [])) for f in d["familles"]) == 58
      and all(set(i) >= {"id", "label", "live"} for f in d["familles"] for i in f["items"]),
      str(d)[:200])
check("d20_le_direct_ne_couvre_que_les_fondus_simples",
      r.status_code == 200 and sorted(i["id"] for f in d.get("familles", []) for i in f.get("items", []) if i.get("live"))
      == ["fade", "fadeblack", "fadewhite"])
check("d20_un_nom_inconnu_retombe_toujours_en_coupe_franche",
      MS._XFADE.get("zzz", MS._XFADE["cut"]) == ("fade", 0.04))

print(f"\n=== {ok} passed, {fail} failed ===")
c.__exit__(None, None, None)
sys.exit(1 if fail else 0)
