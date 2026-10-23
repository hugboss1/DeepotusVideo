# -*- coding: utf-8 -*-
"""t285a : la garde des plafonds prend un espace EXPLICITE (`espace_id`) et la catégorie « campagnes ».
Une campagne de l'espace B lancée pendant que A est actif est vérifiée ET inscrite au registre sous B.
Data-dir isolé, aucune clé, rien de payé.
Run (depuis backend/) : & $PY tests/test_plafonds_espace_explicite.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzplespx_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from datetime import datetime                                       # noqa: E402
from app.services import espaces as ES, plafonds as P, pricing as PRI   # noqa: E402
from app.services.storage import Depense                            # noqa: E402

OP = {"kind": "image", "n": 1, "model": "flux"}
C1 = PRI.estimate(OP)["total_usd"]
MOIS = P.mois_courant()
A = ES.lire()["actif"]
B = ES.creer({"nom": "Marque B"})["id"]
ES.modifier(B, {"plafond_usd": 1.0})

async def semer(eid, usd):
    async with P._registre() as s:
        s.add(Depense(quand=datetime.utcnow(), mois=MOIS, moteur="fal", categorie="quick", op="image",
                      estime_usd=usd, espace_id=eid))
        await s.commit()

async def par_espace(eid):
    return sum(v["effectif_usd"] for v in (await P._cumul(MOIS, eid))["par_moteur"].values())

asyncio.run(semer(B, 1.0 - C1 / 2))        # B est à un demi-tir de son plafond ; A n'a aucun plafond
check("S0 l'espace actif n'est pas B", ES.espace_courant() == A and A != B)

async def tir(**kw):
    try:
        return await P.verifier(OP, "campagnes", ref="cid1", **kw)
    except Exception as e:  # noqa: BLE001
        return getattr(e, "detail", repr(e))

print("[B] espace explicite")
d = asyncio.run(tir(espace_id=B))
check("B1 plafond de B appliqué alors que A est actif : 402 portée espace",
      isinstance(d, dict) and d["dz_plafond"]["motif"] == "espace" and d["dz_plafond"]["espace"] == "Marque B", str(d))
check("B2 un refus n'écrit rien", asyncio.run(par_espace(B)) == round(1.0 - C1 / 2, 6))
r = asyncio.run(tir(espace_id=B, confirme=True))
check("B3 confirmé : passe", isinstance(r, dict) and "devis" in r and r["lignes"], str(r))
check("B4 la dépense est inscrite sous B (pas sous A)",
      abs(asyncio.run(par_espace(B)) - (1.0 - C1 / 2 + C1)) < 1e-6 and asyncio.run(par_espace(A)) == 0.0,
      str((asyncio.run(par_espace(B)), asyncio.run(par_espace(A)))))
r = asyncio.run(tir(espace_id=A))
check("B5 le même tir sur A (sans plafond) passe et s'inscrit sous A",
      isinstance(r, dict) and abs(asyncio.run(par_espace(A)) - C1) < 1e-6, str(r))

print("[C] sans espace_id : comportement inchangé")
d = asyncio.run(tir())
check("C1 sans espace_id : l'espace actif (A, sans plafond) ne refuse pas", isinstance(d, dict) and "devis" in d, str(d))
tok = ES.figer(B)
try:
    d = asyncio.run(tir())
finally:
    ES.liberer(tok)
check("C2 sans espace_id sous espace figé B : plafond de B, comme avant",
      isinstance(d, dict) and d.get("dz_plafond", {}).get("motif") == "espace", str(d))
tok = ES.figer(B)
try:
    asyncio.run(tir(confirme=True))
finally:
    ES.liberer(tok)
async def ligne_b():
    async with P._registre() as s:
        return (await P._lignes(s, MOIS, B))
check("C3 sans espace_id la ligne prend l'espace figé (défaut de colonne)", len(asyncio.run(ligne_b())) == 3)
d = asyncio.run(tir(espace_id="esp_inconnu"))
check("C4 espace inconnu : pas de plafond propre, ne casse pas", isinstance(d, dict) and "devis" in d, str(d))

print("[K] catégorie")
check("K1 « campagnes » est une catégorie connue", "campagnes" in P.CATEGORIES)
check("K2 les anciennes y sont toujours", all(c in P.CATEGORIES for c in ("quick", "motion", "mobile", "aide", "direct")))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
