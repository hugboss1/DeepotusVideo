# -*- coding: utf-8 -*-
"""t310 tâche 5 (27/10/2026) — B1 WhatsApp via Kapso : grille de prix Meta dans `pricing`, catégorie `whatsapp` de
`plafonds`. Plan docs/superpowers/plans/2026-10-27-t310-whatsapp-kapso.md (tâche 5), spec §6.1 « Coûts Meta ».
Fonctions réelles (`pricing.estimate`, `pricing.save`, `plafonds.verifier`), data-dir temporaire, AUCUN réseau.
Ce que ce banc garde :
  P1  grille vide par défaut : un ValueError par catégorie (marketing, utility, authentication, service), message exact.
  P2  grille saisie par `save` : montants exacts, ligne `provider="meta"`, indicatif saisi avec « + » accepté.
  P3  marché ou catégorie absents d'une grille saisie : ValueError ; catégorie hors vocabulaire : ValueError.
  P4  service : à 999 déjà envoyés la ligne vaut 0 (« dans les 1 000 gratuits »), à 1 000 le tarif plein.
  P5  `save` garde la grille imbriquée (quatre flottants par marché), rejette une catégorie inconnue, un tarif
      illisible ou négatif, sans rien écrire ; une sauvegarde sans la grille ne l'efface pas.
  P6  les autres `kind` donnent le même devis qu'avant.
  P7  `plafonds.CATEGORIES` contient « whatsapp » ; `verifier` chiffre « meta » et l'inscrit au registre, un plafond
      par moteur « meta » est tenu, un prix inconnu est refusé AVANT toute écriture.
Run (depuis backend/) : & $PY tests/test_whatsapp_prix.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwaprix_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


from fastapi import HTTPException                                    # noqa: E402
from app.services import pricing as PR, plafonds as PL               # noqa: E402

CATS = ("marketing", "utility", "authentication", "service")


def refus(o, msg=None):
    try:
        PR.estimate(o)
    except ValueError as e:
        return msg is None or str(e) == msg
    return False


def op(cat, marche="33", deja=0):
    return {"kind": "whatsapp", "categorie": cat, "marche": marche, "service_deja_mois": deja}


# ---- P1 : grille vide -------------------------------------------------------------------------------------------
check("P1.1 la grille par défaut est vide", PR.DEFAULTS["whatsapp_meta_usd"] == {} and PR.load()["whatsapp_meta_usd"] == {})
check("P1.2 1 000 messages de service gratuits par défaut", PR.DEFAULTS["whatsapp_service_gratuits_mois"] == 1000)
for c in CATS:
    check(f"P1.3 grille vide : {c} refusé, message exact",
          lambda c=c: refus(op(c, deja=5000), f"prix WhatsApp inconnu pour 33 / {c} : saisissez la grille de Meta"))

# ---- P2 : grille saisie -----------------------------------------------------------------------------------------
GRILLE = {"33": {"marketing": 0.0859, "utility": 0.0248, "authentication": 0.0248, "service": 0.0},
          "55": {"marketing": 0.0625, "utility": 0.0068, "authentication": 0.0315, "service": 0.0}}
PR.save({"whatsapp_meta_usd": GRILLE})
for c in ("marketing", "utility", "authentication"):
    d = PR.estimate(op(c))
    check(f"P2.1 33 / {c} : {GRILLE['33'][c]}",
          d["total_usd"] == round(GRILLE["33"][c], 4) and len(d["breakdown"]) == 1
          and d["breakdown"][0]["provider"] == "meta" and d["breakdown"][0]["usd"] == round(GRILLE["33"][c], 4), d)
check("P2.2 55 / marketing : 0.0625", PR.estimate(op("marketing", "55"))["total_usd"] == 0.0625)
check("P2.3 indicatif saisi avec « + » : même prix", PR.estimate(op("marketing", "+33"))["total_usd"] == 0.0859)
check("P2.4 la grille relue par load garde les quatre flottants",
      PR.load()["whatsapp_meta_usd"] == GRILLE, PR.load()["whatsapp_meta_usd"])
check("P2.5 la ligne porte un libellé et une unité de message",
      PR.estimate(op("utility"))["breakdown"][0]["unit"] == "msg" and PR.estimate(op("utility"))["breakdown"][0]["label"])

# ---- P3 : absents -----------------------------------------------------------------------------------------------
check("P3.1 marché absent de la grille : refusé",
      lambda: refus(op("marketing", "91"), "prix WhatsApp inconnu pour 91 / marketing : saisissez la grille de Meta"))
PR.save({"whatsapp_meta_usd": {"33": {"marketing": 0.08}}})
check("P3.2 catégorie absente d'un marché saisi : refusée",
      lambda: refus(op("utility"), "prix WhatsApp inconnu pour 33 / utility : saisissez la grille de Meta"))
check("P3.3 catégorie hors vocabulaire : refusée", lambda: refus(op("promo")))
check("P3.4 catégorie absente de l'op : refusée", lambda: refus({"kind": "whatsapp", "marche": "33"}))
PR.save({"whatsapp_meta_usd": GRILLE})

# ---- P4 : service -----------------------------------------------------------------------------------------------
PR.save({"whatsapp_meta_usd": {"33": {**GRILLE["33"], "service": 0.0200}}})
l999 = PR.estimate(op("service", deja=999))
l1000 = PR.estimate(op("service", deja=1000))
check("P4.1 à 999 : ligne à 0 dans les gratuits", l999["total_usd"] == 0.0 and l999["breakdown"][0]["usd"] == 0.0
      and l999["breakdown"][0]["provider"] == "meta" and "1 000" in str(l999["breakdown"][0]["label"]), l999)
check("P4.2 à 1 000 : tarif plein", l1000["total_usd"] == 0.02 and l1000["breakdown"][0]["usd"] == 0.02, l1000)
check("P4.3 à 0 : gratuit", PR.estimate(op("service", deja=0))["total_usd"] == 0.0)
PR.save({"whatsapp_service_gratuits_mois": 10})
check("P4.4 le seuil est celui de la grille (réglable)",
      PR.estimate(op("service", deja=10))["total_usd"] == 0.02 and PR.estimate(op("service", deja=9))["total_usd"] == 0.0)
PR.save({"whatsapp_service_gratuits_mois": 1000})
check("P4.5 compteur illisible : tarif plein, jamais gratuit",
      PR.estimate({**op("service"), "service_deja_mois": "x"})["total_usd"] == 0.02)
check("P4.6 les autres catégories ignorent le seuil",
      PR.estimate(op("marketing", deja=0))["total_usd"] == 0.0859)

# ---- P5 : save --------------------------------------------------------------------------------------------------
PR.save({"whatsapp_meta_usd": GRILLE})
f = pathlib.Path(PR._PRICING_FILE)
avant = f.read_text(encoding="utf-8")
for lib, mauvais in (("catégorie inconnue", {"33": {"promo": 0.1}}),
                     ("tarif négatif", {"33": {"marketing": -1}}),
                     ("tarif illisible", {"33": {"marketing": "cher"}}),
                     ("tarif booléen", {"33": {"marketing": True}}),
                     ("tarif non fini", {"33": {"marketing": float("nan")}}),
                     ("marché qui n'est pas un objet", {"33": 0.1}),
                     ("grille qui n'est pas un objet", [1, 2])):
    def tente(m=mauvais):
        try:
            PR.save({"whatsapp_meta_usd": m})
        except ValueError:
            return True
        return False
    check(f"P5.1 {lib} : ValueError", tente)
check("P5.2 un refus n'écrit rien", f.read_text(encoding="utf-8") == avant)
PR.save({"monthly_budget_usd": 7.0})
check("P5.3 une sauvegarde sans la grille ne l'efface pas", PR.load()["whatsapp_meta_usd"] == GRILLE)
PR.save({"whatsapp_meta_usd": {}})
check("P5.4 une grille vide se sauve (on peut tout retirer)", PR.load()["whatsapp_meta_usd"] == {})
PR.save({"monthly_budget_usd": 0.0, "whatsapp_meta_usd": GRILLE})

# ---- P6 : autres kinds ------------------------------------------------------------------------------------------
check("P6.1 image : 0,003 $", PR.estimate({"kind": "image"})["total_usd"] == 0.003)
check("P6.2 elevenlabs 500 caractères : 0,12 $", PR.estimate({"kind": "elevenlabs", "chars": 500})["total_usd"] == 0.12)
check("P6.3 llm openai 1500/500",
      PR.estimate({"kind": "llm", "provider": "openai", "in_tok": 1500, "out_tok": 500})["total_usd"] == 0.0005)
check("P6.4 lipsync 7 s : 2 paliers de 5 s", PR.estimate({"kind": "lipsync", "duration_s": 7})["total_usd"] == 0.14)
check("P6.5 kind inconnu : devis vide, sans refus",
      PR.estimate({"kind": "zzz"}) == {"breakdown": [], "total_usd": 0.0, "credits": {}})
check("P6.6 un kind voisin ne lève pas", PR.estimate({"kind": "upscale", "n": 2})["total_usd"] == 0.004)

# ---- P7 : plafonds ----------------------------------------------------------------------------------------------
check("P7.1 « whatsapp » est une catégorie de plafond", "whatsapp" in PL.CATEGORIES)


async def p7():
    r = await PL.verifier(op("marketing"), categorie="whatsapp", ref="wa-1")
    st = await PL.etat()
    check("P7.2 verifier chiffre et inscrit au registre sous le moteur « meta »",
          r["devis"]["total_usd"] == 0.0859 and len(r["lignes"]) == 1
          and st["par_moteur"].get("meta", {}).get("effectif_usd") == 0.0859, (r, st["par_moteur"]))
    PL.enregistrer({"par_moteur": {"meta": 0.10}})
    try:
        await PL.verifier(op("marketing"), categorie="whatsapp")
        refuse = False
    except HTTPException as e:
        refuse = e.status_code == 402 and e.detail["dz_plafond"]["moteur"] == "meta"
    check("P7.3 le plafond par moteur « meta » est tenu (402)", refuse)
    r = await PL.verifier(op("marketing"), categorie="whatsapp", confirme=True)
    check("P7.4 confirmé : passe", r["devis"]["total_usd"] == 0.0859)
    avant_l = (await PL.etat())["par_moteur"]["meta"]["lignes"]
    try:
        await PL.verifier(op("marketing", "91"), categorie="whatsapp", confirme=True)
        lev = False
    except ValueError:
        lev = True
    apres_l = (await PL.etat())["par_moteur"]["meta"]["lignes"]
    check("P7.5 un prix inconnu est refusé avant toute écriture", lev and avant_l == apres_l, (avant_l, apres_l))
    l0 = await PL.verifier(op("service", deja=3), categorie="whatsapp")
    check("P7.6 un service gratuit n'encombre pas le registre", l0["lignes"] == [] and l0["devis"]["total_usd"] == 0.0)


asyncio.run(p7())

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
