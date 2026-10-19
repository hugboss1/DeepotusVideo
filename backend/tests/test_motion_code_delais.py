# -*- coding: utf-8 -*-
"""Rendu motion code : délais (19/10/2026, PR #390, demande de l'utilisateur). Une page de 15 s écrite par Anthropic
dépassait les 180 s d'appel : le dépassement remontait en erreur brute (500) et l'inspecteur affichait « La chorégraphie
a échoué. » ; le rendu, lui, était borné à 120 s quel que soit le nombre d'images (15 s × 60 i/s = 900 images). Ce que ce
banc garde :
  [E] l'écriture : délai d'appel DELAI_ECRITURE (420 s) ; un délai dépassé ou une erreur du moteur → une NOUVELLE
      tentative (même en Finition ≤ 1), qui demande une page plus courte après un délai ; deux échecs → page de repli
      avec la raison VRAIE (`delai`, `erreur_moteur`) ; une réponse illisible reste `sortie_invalide` ; le plafond
      (402) remonte toujours, sans repli ;
  [R] le rendu : délai total = max(120 s, 0,5 s par image), passé par `rendre` ; 20 s par commande inchangé ;
  [T] les textes : raisons, échec de l'écriture et aide pendant l'écriture, en FR et en EN, dans motion.json et les
      deux dictionnaires ; le bundle les affiche (dzMotionRaison, DzMotionCode).
Run (depuis backend/) : & $PY tests/test_motion_code_delais.py"""
import asyncio, json, os, pathlib, re, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmcdel_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parents[1]
sys.path.insert(0, str(ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
import httpx                                                        # noqa: E402
from fastapi import HTTPException                                   # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:400]}")


from app.services import motion_code as MC                          # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import pricing                                    # noqa: E402

PAGE = ("```html\n<html><body><script>window.dzFrame=function(t){document.body.style.opacity=1}</script></body></html>"
        "\n```")
appels = []
reponses = []


async def faux_tirer(moteur, modele, p, sy, mx, json=False, *, categorie="motion", ref=None, timeout=90.0, effort=None):
    appels.append({"prompt": p, "timeout": timeout})
    r = reponses.pop(0)
    if isinstance(r, BaseException):
        raise r
    return r


MT.tirer_garde = faux_tirer
MT.connu = lambda m: True
MT.configure = lambda m: True
MT.modele_sain = lambda m: "modele-test"
MT.effort_applique = lambda *a, **k: ""
MT.estimer = lambda *a, **k: {}
pricing.estimate = lambda *a, **k: {"total_usd": 0.01}


def ecrire(rep, finition=2):
    appels.clear()
    reponses[:] = list(rep)
    corps = {"script": "DEEPOTUS\nLe studio vidéo", "moteur": "anthropic", "modele": "claude-test",
             "direction": {"curseurs": {"finition": finition}}, "aspect": "9:16", "duree_s": 15, "fps": 30}
    try:
        return asyncio.run(MC.ecrire(corps, "fr"))
    except BaseException as e:  # noqa: BLE001
        return {"exception": e}


print("[E] écriture")
check("E0 DELAI_ECRITURE = 420 s", getattr(MC, "DELAI_ECRITURE", None) == 420.0, getattr(MC, "DELAI_ECRITURE", None))
r = ecrire([PAGE])
check("E1 l'appel part avec le délai d'écriture", appels and appels[0]["timeout"] == getattr(MC, "DELAI_ECRITURE", -1)
      and r.get("repli") is False, (appels[:1], r))
r = ecrire([httpx.ReadTimeout("timed out"), httpx.ReadTimeout("timed out")])
check("E2 délai dépassé deux fois → repli « delai », aucune exception, deux tentatives",
      "exception" not in r and r.get("repli") is True and r.get("raison") == "delai" and r.get("tentatives") == 2,
      r)
r = ecrire([httpx.ReadTimeout("timed out"), PAGE], finition=1)
check("E3 délai dépassé puis page → nouvelle tentative MÊME en Finition 1, page du moteur gardée",
      r.get("repli") is False and r.get("tentatives") == 2 and len(appels) == 2, r)
check("E4 … la seconde demande une page plus courte (sans parler de refus)",
      len(appels) == 2 and "plus courte" in appels[1]["prompt"] and "refusée" not in appels[1]["prompt"],
      appels[-1:])
r = ecrire([TimeoutError("timed out"), TimeoutError("timed out")])
check("E5 TimeoutError (délai de l'exécuteur) → « delai » aussi", r.get("raison") == "delai", r)
r = ecrire([RuntimeError("Anthropic HTTP 529 — overloaded"), httpx.ConnectError("refused")])
check("E6 erreur HTTP du moteur puis réseau coupé → repli « erreur_moteur »",
      "exception" not in r and r.get("raison") == "erreur_moteur" and r.get("tentatives") == 2, r)
r = ecrire([RuntimeError("Anthropic HTTP 529 — overloaded"), PAGE], finition=1)
check("E7 erreur du moteur puis page → nouvelle tentative même en Finition 1", r.get("repli") is False
      and len(appels) == 2, r)
r = ecrire([RuntimeError("réponse illisible"), RuntimeError("réponse illisible")])
check("E8 réponse illisible deux fois → « sortie_invalide » (inchangé)", r.get("raison") == "sortie_invalide", r)
r = ecrire([RuntimeError("réponse illisible")], finition=1)
check("E9 réponse illisible en Finition 1 → une seule tentative (inchangé)", len(appels) == 1
      and r.get("raison") == "sortie_invalide", (len(appels), r))
r = ecrire([HTTPException(402, {"code": "dz_plafond"})])
check("E10 plafond dépassé → le 402 remonte, aucun repli", isinstance(r.get("exception"), HTTPException)
      and r["exception"].status_code == 402, r)

print("[R] rendu")
f = getattr(MC, "delai_rendu", None)
check("E11 delai_rendu : 120 s au moins, 0,5 s par image au-delà",
      f is not None and MC.DELAI_PAR_IMAGE == 0.5 and f(12, 1) == 120 and f(30, 15) == 225 and f(60, 15) == 450
      and f(60, 60) == 1800, [f(a, b) for a, b in ((12, 1), (30, 15), (60, 15), (60, 60))] if f else None)
vus = {}
_rp = MC.rendre_page
MC.rendre_page = lambda html, sortie, **k: vus.update(k) or {"images": 0}
MC.lire = lambda pid: "<html></html>"
try:
    MC.rendre("mc-0000000000000000", _tmp / "x.mp4", aspect="9:16", fps=60, duree_s=15)
finally:
    MC.rendre_page = _rp
check("E12 rendre passe le délai calculé (60 i/s × 15 s → 450 s)", vus.get("delai") == 450, vus)
check("E13 délai par commande inchangé (20 s) et plancher 120 s", MC.DELAI_APPEL == 20 and MC.DELAI == 120)

print("[T] textes")
mj = json.loads((RACINE / "frontend" / "shared" / "i18n" / "motion.json").read_text("utf-8"))
CLES = ("studio.motion.raison_delai", "studio.motion.raison_erreur_moteur", "studio.motion.code_echec",
        "studio.motion.code_en_cours_aide")
check("T1 motion.json : les quatre clés, FR et EN non vides et différents",
      all(k in mj and mj[k].get("fr") and mj[k].get("en") and mj[k]["fr"] != mj[k]["en"] for k in CLES),
      [k for k in CLES if k not in mj])
for dico in ("frontend/shared/dz-i18n-dico.js", "frontend/dist/shared/dz-i18n-dico.js"):
    t = (RACINE / dico).read_text("utf-8")
    check(f"T2 {dico} porte les quatre clés", all(f'"{k}":' in t for k in CLES), dico)
check("T3 « délai » dit le temps attendu (7 min) ; l'aide le dit aussi",
      "7" in mj.get(CLES[0], {}).get("fr", "") and "7" in mj.get(CLES[3], {}).get("fr", ""),
      (mj.get(CLES[0]), mj.get(CLES[3])))
b = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_text("utf-8")
m = re.search(r"function dzMotionRaison\(c\)\{[^}]*\}", b)
check("T4 bundle : dzMotionRaison traduit « delai » et « erreur_moteur »",
      m and 'c==="delai"?dzT("studio.motion.raison_delai")' in m.group(0)
      and 'c==="erreur_moteur"?dzT("studio.motion.raison_erreur_moteur")' in m.group(0), m and m.group(0)[-300:])
i = b.find("function DzMotionCode(")
dmc = b[i:b.find("\"code-html\"", i)] if i >= 0 else ""
check("T5 bundle : l'écriture qui échoue dit « code_echec », jamais « La chorégraphie a échoué »",
      'dzMotionErreur(j,"studio.motion.code_echec")' in dmc and 'dzT("studio.motion.code_echec")' in dmc
      and "studio.motion.echec" not in dmc, dmc[:120])
check("T6 bundle : pendant l'écriture, l'aide dit combien de temps attendre",
      'msg:dzT("studio.motion.code_en_cours_aide")' in dmc)

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
