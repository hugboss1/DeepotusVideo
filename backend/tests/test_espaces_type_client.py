# -*- coding: utf-8 -*-
"""t306 (25/10/2026) — Boite a outils, lot A1 : le TYPE d'un espace (marque / produit / client), son PARENT et le
CLIENT RESPONSABLE. Ce que ce banc garde : l'absence de `type` dans espaces.json vaut « marque » sans reecriture ;
un parent n'existe que pour un produit, et c'est une marque ou un client existant ; le client responsable d'un
espace est lui-meme (client) ou son parent client, MEME ARCHIVE, sinon rien. Data-dir isole, rien de paye.
Sections : 1 type et parent, 2 client responsable (3-5 : fiche client, consentements, routes — taches 5 et 6).
Run (depuis backend/) : & $PY tests/test_espaces_type_client.py"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzetc_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
os.environ["HEYGEN_API_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _leve(exc, fn, *a, **k):
    """True si fn(*a, **k) leve exc."""
    try:
        fn(*a, **k)
    except exc:
        return True
    except Exception:  # noqa: BLE001 — une autre exception n'est pas celle qu'on attend
        return False
    return False


from app.services import espaces as E                               # noqa: E402

print("[1] type et parent")
check("1a Deepotus est une marque", E.actif()["type"] == "marque" and E.actif()["parent"] is None)
octets = (E.dossier() / "espaces.json").read_bytes(); E.lister()
check("1b lire n'ecrit pas le type", (E.dossier() / "espaces.json").read_bytes() == octets)
c = E.creer({"nom": "Boulangerie Lune", "type": "client"})
p = E.creer({"nom": "Pain du matin", "type": "produit", "parent": c["id"]})
check("1c produit d'un client", p["type"] == "produit" and p["parent"] == c["id"])
check("1d type inconnu refuse", _leve(ValueError, E.creer, {"nom": "x", "type": "agence"}))
check("1e parent sur une marque refuse", _leve(ValueError, E.creer, {"nom": "x", "type": "marque", "parent": c["id"]}))
check("1f produit d'un produit refuse", _leve(ValueError, E.creer, {"nom": "x", "type": "produit", "parent": p["id"]}))
check("1g parent inconnu refuse", _leve(ValueError, E.creer, {"nom": "x", "type": "produit", "parent": "esp_00000000"}))

print("[2] client responsable")
check("2a client lui-meme", E.client_responsable(c["id"]) == c["id"])
check("2b produit -> son client", E.client_responsable(p["id"]) == c["id"])
check("2c marque -> aucun", E.client_responsable("deepotus") is None)
E.archiver(c["id"])
check("2d client archive reste responsable", E.client_responsable(p["id"]) == c["id"])

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
