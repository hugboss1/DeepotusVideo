# -*- coding: utf-8 -*-
"""Plafonds mensuels : la colonne « réel » (tâche #16, plan Settings T6, 29/09/2026).
Meshy : `consumed_credits` de la tâche (seule vérité comptable du fournisseur) remonte sur la ligne rattachée, que
l'état terminal arrive AVANT (texturage, qui attend la fin) ou APRÈS (proxy, puis polling) le rattachement.
HeyGen : le delta du solde avant/après un rendu, SEULEMENT quand il est seul en vol — deux rendus qui se chevauchent,
ou un rendu démarré et fini pendant le nôtre, laissent « réel » vide plutôt que d'inventer un chiffre.
Zéro réseau (lecteur de quota injecté), base SQLite jetable.
Run : & $PY tests/test_plafonds_reel.py   (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzplafr_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
from sqlalchemy import select                                       # noqa: E402
from app.services import plafonds as P, pricing as PR, meshy_service as MS  # noqa: E402
from app.services.storage import Depense, async_session_factory, init_db  # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


async def _ligne(ref):
    async with async_session_factory() as s:
        return (await s.execute(select(Depense).where(Depense.ref == ref))).scalars().all()


async def sc():
    await init_db()
    usd_cr = float(PR.load()["meshy_credit_usd"])

    print("\n[1] devis Meshy : les crédits annoncés, 0 compris")
    check("1.1 20 crédits x meshy_credit_usd", abs(PR.estimate({"kind": "meshy", "credits": 20})["total_usd"] - 20 * usd_cr) < 1e-9, "")
    check("1.2 0 crédit (tâche gratuite) = 0 $, pas le défaut", PR.estimate({"kind": "meshy", "credits": 0})["total_usd"] == 0.0,
          str(PR.estimate({"kind": "meshy", "credits": 0})["total_usd"]))
    check("1.3 crédits inconnus : le défaut de la grille", PR.estimate({"kind": "meshy"})["total_usd"] > 0, "")

    print("\n[2] Meshy : l'état terminal arrive APRÈS le rattachement (proxy puis polling)")
    r = await P.verifier({"kind": "meshy", "credits": 30}, "moteurs3d")
    await MS.record_created("tacheA", "openapi/v1/image-to-3d", {})
    await P.rattacher_meshy(r["lignes"], "tacheA")
    L = await _ligne("meshy:tacheA")
    check("2.1 rattachée, réel encore vide (tâche en cours)", len(L) == 1 and L[0].reel_usd is None, str([(l.ref, l.reel_usd) for l in L]))
    await MS.record_state({"id": "tacheA", "status": "IN_PROGRESS", "progress": 40}, "openapi/v1/image-to-3d")
    check("2.2 un état intermédiaire ne note rien", (await _ligne("meshy:tacheA"))[0].reel_usd is None, "")
    await MS.record_state({"id": "tacheA", "status": "SUCCEEDED", "progress": 100, "consumed_credits": 25},
                          "openapi/v1/image-to-3d")
    L = await _ligne("meshy:tacheA")
    check("2.3 SUCCEEDED : réel = 25 crédits consommés (et non les 30 annoncés)", L[0].reel_unites == 25.0
          and abs(L[0].reel_usd - 25 * usd_cr) < 1e-9, str((L[0].reel_unites, L[0].reel_usd)))

    print("\n[3] Meshy : l'état terminal arrive AVANT (texturage qui attend la fin)")
    await MS.record_state({"id": "tacheB", "status": "FAILED", "progress": 100, "consumed_credits": 0},
                          "openapi/v1/retexture")
    r = await P.verifier({"kind": "meshy", "credits": 10}, "moteurs3d")
    n = await P.rattacher_meshy(r["lignes"], "tacheB")
    L = await _ligne("meshy:tacheB")
    check("3.1 échec facturé 0 : réel = 0 $ aussitôt noté", n == 1 and L[0].reel_usd == 0.0 and L[0].reel_unites == 0.0,
          str([(l.reel_usd, l.reel_unites) for l in L]))
    et = await P.etat()
    check("3.2 l'effectif du mois compte le réel (0) et non l'estimé", abs(et["par_moteur"]["meshy"]["effectif_usd"] - 25 * usd_cr) < 1e-9,
          str(et["par_moteur"]["meshy"]))
    check("3.3 identifiant vide : rien", await P.rattacher_meshy(r["lignes"], None) == 0, "")
    await MS.record_state({"id": "tacheC", "status": "SUCCEEDED", "consumed_credits": 5}, "openapi/v1/image-to-3d")
    check("3.4 une tâche sans ligne de garde (simulateur, autre voie) : aucune ligne inventée", await _ligne("meshy:tacheC") == [], "")

    print("\n[4] HeyGen : delta du solde, seul en vol")
    solde = {"v": 100.0}

    async def lire():
        return solde["v"]

    r = await P.verifier({"kind": "heygen", "minutes": 1}, "quick", "hg:seul")
    async with P.suivi_heygen("hg:seul", lire):
        solde["v"] -= 3.0
    L = await _ligne("hg:seul")
    cr_usd = float(PR.load()["heygen_credit_usd"])
    check("4.1 réel = 3 crédits consommés x heygen_credit_usd", L and L[0].reel_unites == 3.0
          and abs(L[0].reel_usd - 3 * cr_usd) < 1e-9, str([(l.reel_unites, l.reel_usd) for l in L]))

    print("\n[5] HeyGen : rendus concurrents -> réel vide")
    await P.verifier({"kind": "heygen", "minutes": 1}, "quick", "hg:a")
    await P.verifier({"kind": "heygen", "minutes": 1}, "quick", "hg:b")
    b_part, a_fini = asyncio.Event(), asyncio.Event()

    async def rendu_a():
        async with P.suivi_heygen("hg:a", lire):
            await b_part.wait()
            solde["v"] -= 2.0
        a_fini.set()

    async def rendu_b():
        async with P.suivi_heygen("hg:b", lire):
            b_part.set()
            await a_fini.wait()
            solde["v"] -= 5.0

    await asyncio.gather(rendu_a(), rendu_b())
    la, lb = (await _ligne("hg:a"))[0], (await _ligne("hg:b"))[0]
    check("5.1 chevauchement : ni A ni B ne reçoivent un réel inventé", la.reel_usd is None and lb.reel_usd is None,
          str((la.reel_usd, lb.reel_usd)))

    print("\n[6] HeyGen : un rendu démarré ET fini pendant le nôtre")
    await P.verifier({"kind": "heygen", "minutes": 1}, "quick", "hg:long")
    await P.verifier({"kind": "heygen", "minutes": 1}, "quick", "hg:court")
    async with P.suivi_heygen("hg:long", lire):
        async with P.suivi_heygen("hg:court", lire):
            solde["v"] -= 4.0
        solde["v"] -= 1.0
    ll, lc = (await _ligne("hg:long"))[0], (await _ligne("hg:court"))[0]
    check("6.1 le long ne s'attribue pas les 5 crédits (le court a dépensé pendant lui)", ll.reel_usd is None, str(ll.reel_usd))
    check("6.2 le court non plus (le long était déjà en vol)", lc.reel_usd is None, str(lc.reel_usd))

    print("\n[7] HeyGen : quota illisible -> estimé conservé, aucune exception")

    async def muet():
        raise RuntimeError("réseau coupé")

    await P.verifier({"kind": "heygen", "minutes": 1}, "quick", "hg:muet")
    async with P.suivi_heygen("hg:muet", muet):
        pass
    check("7.1 réel vide, rendu non interrompu", (await _ligne("hg:muet"))[0].reel_usd is None, "")
    check("7.2 compteur de vols revenu à zéro", P._HEYGEN_EN_VOL == 0, str(P._HEYGEN_EN_VOL))

asyncio.run(sc())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
