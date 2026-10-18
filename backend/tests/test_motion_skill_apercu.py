# -*- coding: utf-8 -*-
"""t236 (lot « Studio : Animation », 18/10/2026) — aperçu d'un skill AVANT son installation.

Le bandeau « Bibliothèque motion » de l'inspecteur de Direction motion montre la licence lue AVANT que l'utilisateur
confirme l'installation (plan § t236, spec 2026-10-17 § B3). La route t233 `POST /api/motion/skills/installer`
téléchargeait et installait d'un seul geste : il manquait `POST /api/motion/skills/apercu`, qui lit SKILL.md et la
licence SANS rien écrire, avec les mêmes refus. L'installation reçoit en retour l'identifiant de licence montré et
refuse si la licence téléchargée au moment de confirmer n'est plus celle-là.

Zéro réseau : le transport httpx de `motion_biblio` est un faux miroir GitHub en mémoire, chaque requête enregistrée.
  [A] aperçu d'un skill MIT : nom, description, dépôt, licence (identifiant + texte), rien d'écrit, rien dans la liste ;
  [R] refus à l'aperçu : sans licence, licence non permissive, déjà installé (sans aucune requête), source refusée ;
  [I] installation avec la licence montrée → acceptée ; licence qui a changé → refusée, rien d'écrit ; sans `licence`
      (appelants t233) → comportement inchangé ;
  [X] boucle locale seulement ; [E] le message neuf sort traduit en anglais.
Run (depuis backend/) : & $PY tests/test_motion_skill_apercu.py"""
import os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ICI = pathlib.Path(__file__).resolve().parent
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmsa_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.pop("DZ_MOTION_MIROIR_GITHUB", None)
sys.path.insert(0, str(ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
import httpx                                                        # noqa: E402
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import motion_biblio as MB                        # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


# Textes écrits pour ce banc (aucun contenu tiers) : une licence MIT de démonstration, un skill de démonstration.
MIT = ("MIT License\n\nCopyright (c) 2026 Banc Apercu\n\nPermission is hereby granted, free of charge, to any person "
       "obtaining a copy\nof this software... THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND.\n")
ISC = ("ISC License\n\nCopyright (c) 2026 Banc Apercu\n\nPermission to use, copy, modify, and/or distribute this "
       "software for any purpose with or without fee is hereby granted.\n")
GPL = "                    GNU GENERAL PUBLIC LICENSE\n                       Version 3, 29 June 2007\n"
SKILL = ("---\nname: apercu-demo\ndescription: Un skill de démonstration écrit pour le banc t236.\n---\n\n"
         "# Aperçu démo\n\nFaites entrer chaque mot par le bas, un temps après l'autre.\n")
R = "https://raw.githubusercontent.com"
MIROIR = {
    f"{R}/banc-apercu/mit/HEAD/SKILL.md": (200, SKILL),
    f"{R}/banc-apercu/mit/HEAD/LICENSE": (200, MIT),
    f"{R}/banc-apercu/change/HEAD/SKILL.md": (200, SKILL.replace("apercu-demo", "apercu-change")),
    f"{R}/banc-apercu/change/HEAD/LICENSE": (200, MIT),
    f"{R}/banc-apercu/sans/HEAD/SKILL.md": (200, SKILL),
    f"{R}/banc-apercu/gpl/HEAD/SKILL.md": (200, SKILL),
    f"{R}/banc-apercu/gpl/HEAD/LICENSE": (200, GPL),
}
REQ = []


def _miroir(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    REQ.append(u)
    st, corps = MIROIR.get(u, (404, "Not Found"))
    return httpx.Response(st, content=corps.encode("utf-8"))


MB._transport = httpx.MockTransport(_miroir)
c = TestClient(app)
cd = TestClient(app, client=("192.168.1.50", 5000))
DONNEES = _tmp / "motion"


def fichiers():
    return sorted(str(p.relative_to(_tmp)) for p in DONNEES.rglob("*")) if DONNEES.is_dir() else []


def post(url, corps, **kw):
    REQ.clear()
    return c.post(url, json=corps, **kw)


print("[A] aperçu d'un skill MIT")
f0 = fichiers()
r = post("/api/motion/skills/apercu", {"source": "banc-apercu/mit"})
ap = r.json() if r.status_code == 200 else {}
check("A1 200 : nom et description de l'en-tête, dépôt, lien GitHub", r.status_code == 200 and ap.get("titre") == "apercu-demo"
      and "banc t236" in (ap.get("description") or "") and (ap.get("source") or {}).get("depot") == "banc-apercu/mit"
      and (ap.get("source") or {}).get("url") == "https://github.com/banc-apercu/mit/tree/HEAD", r.text[:300])
check("A2 la licence lue : identifiant MIT, fichier LICENSE, texte complet", ap.get("licence") == "MIT"
      and ap.get("fichier_licence") == "LICENSE" and ap.get("licence_texte") == MIT and ap.get("notice") is False, ap)
check("A3 l'identifiant que l'installation prendra", ap.get("id") == "skill-banc-apercu-mit", ap.get("id"))
check("A4 RIEN d'écrit dans les données", fichiers() == f0, fichiers())
check("A5 rien dans la liste", not [e for e in c.get("/api/motion/biblio").json()["entrees"] if e["nature"] == "skill"])
check("A6 seulement SKILL.md et LICENSE lus, sur raw.githubusercontent.com",
      REQ == [f"{R}/banc-apercu/mit/HEAD/SKILL.md", f"{R}/banc-apercu/mit/HEAD/LICENSE"], REQ)

print("[R] refus à l'aperçu")
r = post("/api/motion/skills/apercu", {"source": "banc-apercu/sans"})
check("R1 dépôt sans licence → 400 « Aucune licence … installation refusée », rien d'écrit", r.status_code == 400
      and "Aucune licence dans banc-apercu/sans" in r.text and fichiers() == f0, r.text[:200])
r = post("/api/motion/skills/apercu", {"source": "banc-apercu/gpl"})
check("R2 licence non permissive (GPL) → 400 « Licence non reconnue »", r.status_code == 400
      and "Licence non reconnue dans banc-apercu/gpl" in r.text and fichiers() == f0, r.text[:200])
r = post("/api/motion/skills/apercu", {"source": "../etc:passwd"})
check("R3 source refusée → 400, aucune requête", r.status_code == 400 and not REQ, (r.status_code, REQ))
r = post("/api/motion/skills/apercu", {"source": "https://evil.example/a/b"})
check("R4 hôte tiers → 400, aucune requête", r.status_code == 400 and not REQ, (r.status_code, REQ))
r = post("/api/motion/skills/apercu", {})
check("R5 sans source → 400", r.status_code == 400, r.status_code)

print("[I] installation après l'aperçu")
r = post("/api/motion/skills/installer", {"source": "banc-apercu/mit", "licence": "MIT"})
sk = r.json() if r.status_code == 200 else {}
check("I1 licence montrée = licence lue → installé", r.status_code == 200 and sk.get("id") == ap.get("id")
      and sk.get("licence") == "MIT", r.text[:200])
check("I2 le skill est dans la liste", any(e["id"] == sk.get("id") for e in c.get("/api/motion/biblio").json()["entrees"]))
r = post("/api/motion/skills/apercu", {"source": "banc-apercu/mit"})
check("I3 aperçu d'un skill déjà installé → 400, AUCUNE requête", r.status_code == 400 and "déjà installé" in r.text
      and not REQ, (r.status_code, REQ))
f1 = fichiers()
r = post("/api/motion/skills/apercu", {"source": "banc-apercu/change"})
check("I4 aperçu MIT du second dépôt", r.status_code == 200 and r.json().get("licence") == "MIT", r.text[:200])
MIROIR[f"{R}/banc-apercu/change/HEAD/LICENSE"] = (200, ISC)             # la licence change entre l'aperçu et le clic
r = post("/api/motion/skills/installer", {"source": "banc-apercu/change", "licence": "MIT"})
check("I5 la licence a changé depuis l'aperçu → 400, rien d'écrit", r.status_code == 400
      and "a changé depuis l'aperçu (MIT → ISC)" in r.text and fichiers() == f1, r.text[:200])
r = post("/api/motion/skills/installer", {"source": "banc-apercu/change", "licence": "MIT"},
         headers={"Accept-Language": "en"})
check("E1 le refus sort en anglais (L10)", r.status_code == 400 and "has changed since the preview (MIT → ISC)" in r.text,
      r.text[:200])
r = post("/api/motion/skills/installer", {"source": "banc-apercu/change"})
check("I6 sans `licence` (appelants t233) : installation comme avant", r.status_code == 200
      and r.json().get("licence") == "ISC", r.text[:200])

print("[X] boucle locale seulement")
r = cd.post("/api/motion/skills/apercu", json={"source": "banc-apercu/mit"})
check("X1 aperçu depuis le réseau → refusé", r.status_code in (401, 403), r.status_code)
import asyncio                                                      # noqa: E402
from app.api import motion_biblio_routes as MR                      # noqa: E402


class _Client:
    host = "192.168.1.50"


class _Req:                                 # la route elle-même, sans le middleware : sa garde doit refuser d'abord
    client = _Client()

    async def json(self):
        return {"source": "banc-apercu/mit"}


REQ.clear()
try:
    asyncio.run(MR.apercu(_Req())); _st = None
except Exception as e:                                              # noqa: BLE001
    _st = getattr(e, "status_code", None)
check("X2 la route d'aperçu appelle elle-même la garde locale : 403 avant toute requête", _st == 403 and not REQ, (_st, REQ))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
