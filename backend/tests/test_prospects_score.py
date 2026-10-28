# -*- coding: utf-8 -*-
"""t354 (28/10/2026) — Veille & prospection P3, tâche 2 : le BARÈME du score et les CANAUX POSSIBLES (purs).
Chaque critère isolé, les bornes (0, 100, ±20), le webmail sans consentement absent, les réseaux en manuel, l'opposé vide.
Run (depuis backend/) : & $PY tests/test_prospects_score.py"""
import pathlib, sys
from datetime import date
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import prospects_score as SC                     # noqa: E402

SC._aujourdhui = lambda: date(2026, 10, 28)


def fiche(**o):
    f = {"id": "pr_00000001", "statut": "propose", "source": {"type": "autre", "date": "2026-01-01"}, "base_legale": "consentement",
         "canaux": [], "consentements": [], "signal": "", "dernier_contact_entrant": None, "entreprise": "", "nom": "X"}
    f.update(o)
    return f


def pts(f):
    return {d["critere"]: d["points"] for d in SC.bareme(f)["details"]}


print("[1] critères isolés")
check("1a rien : base 0", SC.bareme(fiche())["base"] == 0, SC.bareme(fiche()))
check("1b source entrante : +40", pts(fiche(source={"type": "whatsapp", "date": "2026-01-01"})) == {"source_entrante": 40})
check("1c source web : +15", pts(fiche(source={"type": "web", "date": "2026-01-01"})) == {"source_web": 15})
cons = [{"canal": "email", "base_legale": "consentement", "date": "2026-01-01", "moyen": "ecrit", "revoque_le": None}]
check("1d consentement en cours : +20 (et canal joignable +15 avec l'e-mail)", pts(fiche(consentements=cons,
      canaux=[{"type": "email", "valeur": "a@gmail.com"}])) == {"consentement": 20, "canal_possible": 15})
check("1e consentement révoqué : rien", pts(fiche(consentements=[dict(cons[0], revoque_le="2026-02-01")])) == {})
check("1f adresse pro + intérêt légitime : canal +15 et pro +10", pts(fiche(base_legale="interet_legitime_b2b",
      canaux=[{"type": "email", "valeur": "a@studio.fr"}])) == {"canal_possible": 15, "adresse_pro": 10})
check("1g signal : +5", pts(fiche(signal="cherche un studio")) == {"signal": 5})
check("1h contact entrant < 30 j : +10 ; plus ancien : rien", pts(fiche(dernier_contact_entrant="2026-10-10")) == {"contact_recent": 10}
      and pts(fiche(dernier_contact_entrant="2026-09-01")) == {})
tout = fiche(source={"type": "formulaire", "date": "2026-10-01"}, consentements=cons, base_legale="consentement",
             canaux=[{"type": "email", "valeur": "a@studio.fr"}], signal="x", dernier_contact_entrant="2026-10-27")
check("1i tout : 100", SC.bareme(tout)["base"] == 100, SC.bareme(tout))

print("[2] score borné")
check("2a 90 + 20 = 100 (borné)", SC.score(90, 20) == 100)
check("2b 10 - 20 = 0 (borné)", SC.score(10, -20) == 0)
check("2c 50 + 5", SC.score(50, 5) == 55)
for bad in (21, -21, 1.5, "3", True):
    try:
        SC.score(50, bad); leve = False
    except ValueError:
        leve = True
    check(f"2d ajustement {bad!r} refusé", leve)

print("[3] canaux possibles")
c = SC.canaux_possibles(fiche(base_legale="interet_legitime_b2b", canaux=[{"type": "email", "valeur": "a@studio.fr"}]))
check("3a e-mail pro + intérêt légitime : auto après porte", c == [{"canal": "email", "mode": "auto_apres_porte", "raison": c[0]["raison"]}] and c[0]["raison"], c)
check("3b webmail sans consentement e-mail : absent", SC.canaux_possibles(fiche(base_legale="interet_legitime_b2b",
      canaux=[{"type": "email", "valeur": "a@gmail.com"}])) == [])
check("3c webmail avec consentement e-mail : auto", [x["canal"] for x in SC.canaux_possibles(fiche(consentements=cons,
      canaux=[{"type": "email", "valeur": "a@gmail.com"}]))] == ["email"])
wa = [{"canal": "whatsapp", "base_legale": "consentement", "date": "2026-01-01", "moyen": "whatsapp", "revoque_le": None}]
check("3d WhatsApp avec consentement : auto ; sans : absent",
      [x["mode"] for x in SC.canaux_possibles(fiche(consentements=wa, canaux=[{"type": "whatsapp", "valeur": "+33600000001"}]))] == ["auto_apres_porte"]
      and SC.canaux_possibles(fiche(canaux=[{"type": "whatsapp", "valeur": "+33600000001"}])) == [])
r = SC.canaux_possibles(fiche(canaux=[{"type": "x", "valeur": "@a"}, {"type": "instagram", "valeur": "@b"}, {"type": "linkedin", "valeur": "c"}]))
check("3e réseaux : manuel (vous envoyez)", [(x["canal"], x["mode"]) for x in r] == [("x", "manuel"), ("instagram", "manuel"), ("linkedin", "manuel")], r)
check("3f opposé : aucun", SC.canaux_possibles(fiche(statut="oppose", consentements=cons, canaux=[{"type": "email", "valeur": "a@studio.fr"}])) == [])
check("3g un canal manuel ne compte pas au barème", pts(fiche(canaux=[{"type": "x", "valeur": "@a"}])) == {})

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
