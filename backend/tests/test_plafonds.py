# -*- coding: utf-8 -*-
"""Plafonds de depense (plan Settings T4, tache #16 du suivi, 29/09/2026) — registre `depenses`, garde, alerte.
Decision de l'utilisateur (29/09) : le plafond GLOBAL est le champ existant « Monthly budget cap »
(pricing.json `monthly_budget_usd`, jamais lu jusqu'ici) ; les plafonds PAR MOTEUR et le seuil d'alerte vivent
dans DATA_ROOT/plafonds.json.
Banc-miroir : les totaux sont relus dans la BASE (SELECT sur `depenses`), le fichier de tarifs est relu sur disque.
Zero reseau, base SQLite jetable.
Run : & $PY tests/test_plafonds.py   (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzplaf_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi import HTTPException                                   # noqa: E402
from sqlalchemy import select                                       # noqa: E402
from app.services import plafonds as P, pricing as PR               # noqa: E402
from app.services.storage import Depense, async_session_factory, init_db  # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


async def _lignes():
    async with async_session_factory() as s:
        return (await s.execute(select(Depense).order_by(Depense.id))).scalars().all()


IMG10 = {"kind": "image", "n": 10, "model": "nano-banana-pro"}   # 10 x 0,15 $ = 1,50 $


async def sc():
    print("\n[0] base SANS init_db (fixtures Cardforge, base ancienne) : le registre crée sa table")
    try:
        e0 = await P.etat()
        r0 = await P.verifier({"kind": "llm", "provider": "ollama", "in_tok": 1, "out_tok": 1}, "atelier")
        check("0.1 etat() et verifier() passent sur une base vierge", e0["global"]["effectif_usd"] == 0.0 and r0["lignes"] == [], "")
    except Exception as e:  # noqa: BLE001
        check("0.1 etat() et verifier() passent sur une base vierge", False, repr(e)[:200])
    await init_db()
    print("\n[1] reglages")
    check("1.1 par defaut : aucun plafond, alerte a 80 %", P.charger() == {"global_usd": 0.0, "par_moteur": {}, "alerte_pct": 80}, json.dumps(P.charger()))
    PR.save({"monthly_budget_usd": 7})
    check("1.2 le plafond global EST monthly_budget_usd de la grille", P.charger()["global_usd"] == 7.0, "")
    e = P.enregistrer({"global_usd": 0, "par_moteur": {"fal": 2, "x": "abc", "heygen": -1}, "alerte_pct": 250})
    check("1.3 enregistrer : global ecrit dans la grille, moteurs valides seulement, alerte bornee 1..100",
          e == {"global_usd": 0.0, "par_moteur": {"fal": 2.0}, "alerte_pct": 100}
          and json.loads((_tmp / "pricing.json").read_text(encoding="utf-8")).get("monthly_budget_usd") == 0.0, json.dumps(e))
    check("1.4 plafonds.json ne porte PAS le global (une seule verite)",
          "global_usd" not in json.loads((_tmp / "plafonds.json").read_text(encoding="utf-8")), "")
    (_tmp / "plafonds.json").write_text("{pas du json", encoding="utf-8")
    check("1.5 plafonds.json illisible : defauts, aucune exception", P.charger()["par_moteur"] == {} and P.charger()["alerte_pct"] == 80, "")
    P.enregistrer({"global_usd": 0, "par_moteur": {}, "alerte_pct": 80})

    print("\n[2] sans plafond : rien ne bloque, tout est enregistre")
    r = await P.verifier(IMG10, "bibliotheque")
    check("2.1 devis = 10 x 0,15 $", abs(r["devis"]["total_usd"] - 1.5) < 1e-6, str(r["devis"]["total_usd"]))
    L = await _lignes()
    check("2.2 une ligne : moteur, categorie, op, estime, reel vide, mois courant",
          len(L) == 1 and L[0].moteur == "fal" and L[0].categorie == "bibliotheque" and L[0].op == "image"
          and abs(L[0].estime_usd - 1.5) < 1e-9 and L[0].reel_usd is None and L[0].mois == P.mois_courant(), "")
    check("2.3 verifier rend les ids des lignes ecrites", r["lignes"] == [L[0].id], json.dumps(r["lignes"]))
    r0 = await P.verifier({"kind": "llm", "provider": "ollama", "in_tok": 10, "out_tok": 10}, "atelier")
    check("2.4 un devis nul (local / gratuit) n'encombre pas le registre", r0["lignes"] == [] and len(await _lignes()) == 1, json.dumps(r0["devis"]))

    print("\n[3] plafond par moteur : refus chiffre, rien d'enregistre")
    P.enregistrer({"global_usd": 0, "par_moteur": {"fal": 2.0}, "alerte_pct": 80})
    try:
        await P.verifier(IMG10, "bibliotheque")
        check("3.1 402 attendu", False)
    except HTTPException as e:
        d = (e.detail or {}).get("dz_plafond", {}) if isinstance(e.detail, dict) else {}
        check("3.1 402 avec detail dz_plafond", e.status_code == 402 and bool(d), str(e.detail)[:200])
        check("3.2 motif moteur, moteur nomme, deja / devis / plafond chiffres",
              d.get("motif") == "moteur" and d.get("moteur") == "fal" and abs(d.get("deja_usd", 0) - 1.5) < 1e-6
              and abs(d.get("devis_usd", 0) - 1.5) < 1e-6 and d.get("plafond_usd") == 2.0, json.dumps(d, ensure_ascii=False))
        check("3.3 le message dit le moteur, le plafond, l'ecran et comment relever",
              "fal" in d.get("message", "") and "2,00" in d.get("message", "") and "bibliotheque" in d.get("message", "")
              and "Réglages" in d.get("message", ""), d.get("message", ""))
    check("3.4 un refus n'enregistre RIEN", len(await _lignes()) == 1, "")
    check("3.4b petits montants lisibles : 0,006 / 0,001 / 0,10 / 0,00 / 2,50",
          [P._fr(x) for x in (0.006, 0.001, 0.1, 0, 2.5, 0.05)] == ["0,006", "0,001", "0,10", "0,00", "2,50", "0,05"],
          str([P._fr(x) for x in (0.006, 0.001, 0.1, 0, 2.5, 0.05)]))
    jeton = P.CONFIRME.set(True)
    try:
        await P.verifier(IMG10, "bibliotheque")
    finally:
        P.CONFIRME.reset(jeton)
    check("3.5 confirme (ContextVar) : ca passe, et c'est enregistre", len(await _lignes()) == 2, "")
    await P.verifier(IMG10, "bibliotheque", confirme=True)
    check("3.6 confirme en argument : idem", len(await _lignes()) == 3, "")

    print("\n[4] plafond global (monthly_budget_usd), tous moteurs confondus")
    P.enregistrer({"global_usd": 5.0, "par_moteur": {}, "alerte_pct": 80})
    try:
        await P.verifier({"kind": "elevenlabs", "chars": 10000}, "son")   # 2,40 $ ; deja 4,50 $
        check("4.1 402 global attendu", False)
    except HTTPException as e:
        check("4.1 motif global", e.status_code == 402 and e.detail["dz_plafond"]["motif"] == "global", str(e.detail)[:200])
    r41 = await P.verifier({"kind": "elevenlabs", "chars": 1000}, "son")           # 0,24 $ -> 4,74 <= 5
    check("4.2 sous le plafond global : passe", len(r41["lignes"]) == 1, "")

    print("\n[5] etat du mois : estime, reel, effectif, alertes")
    P.enregistrer({"global_usd": 5.0, "par_moteur": {"fal": 6.0, "elevenlabs": 10.0}, "alerte_pct": 80})
    et = await P.etat()
    check("5.1 total estime = 4,74 $", abs(et["global"]["estime_usd"] - 4.74) < 1e-6, str(et["global"]))
    check("5.2 aucun reel connu", et["global"]["reel_usd"] == 0.0, "")
    check("5.3 4,74 / 5,00 = 94,8 % du global -> alerte", abs(et["global"]["pct"] - 94.8) < 0.05 and "global" in et["alerte"], json.dumps(et["alerte"]))
    check("5.4 fal a 75 % du sien : pas d'alerte ; detail par moteur", "fal" not in et["alerte"]
          and abs(et["par_moteur"]["fal"]["estime_usd"] - 4.5) < 1e-6 and et["par_moteur"]["fal"]["pct"] == 75.0, json.dumps(et["par_moteur"]["fal"]))
    check("5.5 l'etat dit depuis quand il compte (date de la premiere ligne)", et["depuis"].startswith("20"), et["depuis"])
    et0 = await P.etat("1999-01")
    check("5.6 un mois vide : zeros, pas d'alerte", et0["global"]["effectif_usd"] == 0.0 and et0["alerte"] == [], "")

    print("\n[6] rattachement puis reel")
    check("6.1 reference vide : aucun effet", await P.noter_reel("", 0.10, None) == 0, "")
    check("6.2 reference inconnue : 0 ligne, jamais une ligne inventee", await P.noter_reel("inconnue", 0.10, None) == 0
          and len(await _lignes()) == 4, "")
    r6 = await P.verifier({"kind": "image", "n": 1}, "cartes")                   # flux 0,003 $
    check("6.3 rattachement a posteriori", await P.rattacher(r6["lignes"], "meshy:abc") == 1, "")
    await P.noter_reel("meshy:abc", 0.10, 5.0)
    et2 = await P.etat()
    check("6.4 reel remonte (0,10 $, 5 unites) ; l'estime ne bouge pas", abs(et2["global"]["reel_usd"] - 0.10) < 1e-6
          and abs(et2["global"]["estime_usd"] - 4.743) < 1e-6, json.dumps(et2["global"]))
    check("6.5 effectif = reel la ou il existe, estime ailleurs = 4,74 + 0,10", abs(et2["global"]["effectif_usd"] - 4.84) < 1e-6,
          str(et2["global"]["effectif_usd"]))
    L = await _lignes()
    check("6.6 relu en base : reel_usd et reel_unites sur la seule ligne rattachee",
          [(l.ref, l.reel_usd, l.reel_unites) for l in L if l.reel_usd is not None] == [("meshy:abc", 0.10, 5.0)], "")

asyncio.run(sc())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
