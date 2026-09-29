# -*- coding: utf-8 -*-
"""Tableau des dépenses, réel contre estimé (plan Settings T18 — tâche #21, 29/09/2026).
Banc-miroir : les lignes sont écrites par la VRAIE garde (`plafonds.verifier`) et rapprochées par les VRAIS chemins
(`meshy_service.record_state`, `plafonds.suivi_heygen`) ; le banc ne fabrique aucune ligne à la main. Il recalcule
lui-même les totaux attendus depuis les tarifs de la grille. Témoin : la base fa8762e n'a pas de `tableau`.
Run : & $PY tests/test_depenses_tableau.py   (depuis backend/)"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzdep_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
from app.services import meshy_service as MS, plafonds as P, pricing as PR  # noqa: E402
from app.services.storage import init_db                            # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


racine = pathlib.Path(__file__).resolve().parents[2]
vieux = subprocess.run(["git", "show", "fa8762e:backend/app/services/plafonds.py"], cwd=racine, capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base fa8762e")
check("0.1 TÉMOIN : pas de tableau réel/estimé", vieux and "async def tableau(" not in vieux, "")


def par(t):
    return {(l["moteur"], l["categorie"]): l for l in t["lignes"]}


async def sc():
    await init_db()
    grille = PR.load()
    cr = float(grille["meshy_credit_usd"])
    print("\n[1] mois vide")
    t = await P.tableau()
    check("1.1 aucun tir : aucune ligne, totaux nuls, couverture 0, pas de date inventée",
          t["lignes"] == [] and t["total"] == {"estime_usd": 0.0, "reel_usd": 0.0, "effectif_usd": 0.0, "couverture_pct": 0.0}
          and t["depuis"] == "", json.dumps(t))

    print("\n[2] les tirs, posés par la vraie garde")
    await P.verifier({"kind": "image", "n": 4, "model": "flux"}, "quick")                 # fal, jamais rapprochable
    await P.verifier({"kind": "elevenlabs", "chars": 1000}, "son")                         # ElevenLabs
    # Meshy moteurs3d : DEUX tirs, un seul rapproché (par le vrai chemin du proxy : rattacher puis record_state)
    g1 = await P.verifier({"kind": "meshy", "credits": 30}, "moteurs3d")
    await P.rattacher_meshy(g1["lignes"], "t1")
    await MS.record_state({"id": "t1", "status": "SUCCEEDED", "consumed_credits": 22}, "openapi/v1/image-to-3d")
    await P.verifier({"kind": "meshy", "credits": 10}, "moteurs3d")                        # jamais rattaché
    # Meshy cartes : un tir, rapproché, facturé 0 (tâche échouée)
    g3 = await P.verifier({"kind": "meshy", "credits": 20}, "cartes")
    await P.rattacher_meshy(g3["lignes"], "t3")
    await MS.record_state({"id": "t3", "status": "FAILED", "consumed_credits": 0}, "openapi/v1/image-to-3d")
    # HeyGen : un tir sans réel (quota illisible)
    await P.verifier({"kind": "heygen", "minutes": 1}, "quick", "hg:x")

    async def muet():
        raise RuntimeError("quota illisible")
    async with P.suivi_heygen("hg:x", muet):
        pass

    t = await P.tableau()
    L = par(t)
    fal = L[("fal", "quick")]
    check("2.1 fal : état « estime », 4 × tarif FLUX, ni réel ni écart inventés", fal["etat"] == "estime" and fal["tirs"] == 1
          and abs(fal["estime_usd"] - 4 * float(grille["flux_image_usd"])) < 1e-9 and fal["reel_usd"] is None and fal["ecart_usd"] is None, json.dumps(fal))
    check("2.2 ElevenLabs : « estime »", L[("elevenlabs", "son")]["etat"] == "estime")
    m3 = L[("meshy", "moteurs3d")]
    check("2.3 Meshy mêlé : « reel-partiel », 1 rapproché sur 2, et c'est dit", m3["etat"] == "reel-partiel" and m3["tirs"] == 2 and m3["rapproches"] == 1, json.dumps(m3))
    check("2.4 effectif calculé LIGNE par LIGNE : 22 crédits réels + 10 estimés (le plan aurait perdu les 10)",
          abs(m3["effectif_usd"] - (22 + 10) * cr) < 1e-9 and abs(m3["estime_usd"] - 40 * cr) < 1e-9, json.dumps(m3))
    check("2.5 l'écart porte sur le seul tir rapproché : réel − estimé = 22 − 30 crédits", abs(m3["ecart_usd"] - (22 - 30) * cr) < 1e-9
          and m3["reel_unites"] == 22.0, json.dumps(m3))
    mc = L[("meshy", "cartes")]
    check("2.6 un réel de 0 $ (tâche échouée) est un RÉEL, pas une absence", mc["etat"] == "reel" and mc["reel_usd"] == 0.0
          and abs(mc["ecart_usd"] + 20 * cr) < 1e-9 and mc["effectif_usd"] == 0.0, json.dumps(mc))
    hg = L[("heygen", "quick")]
    check("2.7 HeyGen jamais rapproché : « estime-non-rapproche », pas noyé dans « estime »", hg["etat"] == "estime-non-rapproche" and hg["ecart_usd"] is None, json.dumps(hg))

    print("\n[3] totaux")
    tt = t["total"]
    check("3.1 les totaux sont la somme des lignes", abs(tt["estime_usd"] - sum(l["estime_usd"] for l in t["lignes"])) < 1e-9
          and abs(tt["effectif_usd"] - sum(l["effectif_usd"] for l in t["lignes"])) < 1e-9, json.dumps(tt))
    check("3.2 la couverture dit quelle part de l'effectif est vraiment facturée", abs(tt["reel_usd"] - 22 * cr) < 1e-9
          and abs(tt["couverture_pct"] - round(100 * tt["reel_usd"] / tt["effectif_usd"], 1)) < 1e-9, json.dumps(tt))
    check("3.3 le tableau et l'état des plafonds disent le même effectif", abs(tt["effectif_usd"] - (await P.etat())["global"]["effectif_usd"]) < 1e-9)
    check("3.4 trié par effectif décroissant", [l["effectif_usd"] for l in t["lignes"]] == sorted((l["effectif_usd"] for l in t["lignes"]), reverse=True))
    check("3.5 dit depuis quand il compte", t["depuis"].startswith("20") and t["mois"] == P.mois_courant())
    check("3.6 un autre mois : vide", (await P.tableau("1999-01"))["lignes"] == [])

asyncio.run(sc())

print("\n[4] la route")
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
with TestClient(app, client=("127.0.0.1", 50000)) as c:
    j = c.get("/api/reglages/depenses").json()
    check("4.1 /api/reglages/depenses sert le tableau du mois", len(j["lignes"]) == 5 and j["mois"] == P.mois_courant(), str(len(j.get("lignes", []))))
    check("4.2 mois illisible : 400", c.get("/api/reglages/depenses?mois=2026-9").status_code == 400)
    check("4.3 mois explicite", c.get("/api/reglages/depenses?mois=1999-01").json()["lignes"] == [])
with TestClient(app, client=("192.168.1.20", 50000)) as c2:
    check("4.4 hors boucle locale : refusé", c2.get("/api/reglages/depenses").status_code == 403)

print("\n[5] l'écran (bundle livré)")
import shutil                                                       # noqa: E402
_B = racine / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
s = _B.read_text(encoding="utf-8")
vb = subprocess.run(["git", "show", "fa8762e:frontend/dist/assets/index-BEOJX8L5.js"], cwd=racine, capture_output=True).stdout.decode("utf-8")
check("5.0 TÉMOIN : la base n'a pas DzDepenses", vb and "function DzDepenses(" not in vb)
dz = s[s.find("function DzDepenses("):s.find("function xm(")]
check("5.1 DzDepenses x1, monté DEUX fois : sous les plafonds (Pricing & budget) et en bas du Diagnostic",
      s.count("function DzDepenses(") == 1 and s.count("r.jsx(DzDepenses,{})") == 2
      and s.count("r.jsx(DzPlafonds,{}),r.jsx(DzDepenses,{})]});}") == 1
      and s.count("children:'Rien à signaler.'})]}),r.jsx(DzDepenses,{})]})}") == 1)
check("5.2 il ne lit que /api/reglages/depenses, et se recharge avec les plafonds (événement dz-plafonds)",
      dz.count("fetch(") == 1 and "fetch('/api/reglages/depenses')" in dz
      and "window.addEventListener('dz-plafonds',h)" in dz and "window.removeEventListener('dz-plafonds',h)" in dz)
check("5.3 les quatre états sont écrits en toutes lettres, jamais confondus",
      all(x in dz for x in ("'réel'", "('réel '+l.rapproches+'/'+l.tirs)", "'estimé, non rapproché'", ":'estimé'"))
      and dz.count("e==='estime-non-rapproche'?'amber'") == 1)
check("5.4 un réel ou un écart absent s'affiche « — », jamais 0", "l.reel_usd==null?'—'" in dz and "l.ecart_usd==null?'—'" in dz)
check("5.5 l'écart dit ce qu'il mesure (bulle) et le sens des couleurs : plus cher en rouge",
      "title:'réel − estimé, sur les seuls tirs rapprochés'" in dz and "l.ecart_usd>0?'var(--red)':'var(--green)'" in dz)
check("5.6 montants formatés comme le serveur (dzUsd, déjà bancé contre plafonds._fr)", dz.count("dzUsd(") >= 5)
_n = shutil.which("node")
_nc = subprocess.run([_n, "--check", str(_B)], capture_output=True, text=True) if _n else None
check("5.7 node --check du bundle entier", _nc is not None and _nc.returncode == 0, (_nc.stderr[-200:] if _nc else ""))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
