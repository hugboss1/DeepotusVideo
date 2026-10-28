# -*- coding: utf-8 -*-
"""t353 (27/10/2026) — Veille & prospection P2 : le REGISTRE GLOBAL des oppositions (un STOP vaut pour tous les espaces).
Ce que ce banc garde : les identifiants sont normalisés (e-mail en minuscules, numéro avec indicatif, profil sans / final),
le fichier ne contient JAMAIS une adresse ni un numéro en clair (empreintes salées), une même personne = une empreinte,
un registre illisible est mis de côté (jamais écrasé), une origine inconnue est refusée. Data-dir isolé, aucun réseau.
Run (depuis backend/) : & $PY tests/test_oppositions.py"""
import os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzopp_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import oppositions as O                           # noqa: E402

print("[1] normaliser")
check("1a e-mail en minuscules", O.normaliser(" Jean@Exemple.FR ") == "email:jean@exemple.fr", O.normaliser(" Jean@Exemple.FR "))
check("1b numéro saisi avec indicatif", O.normaliser("06 12 34 56 78") == "tel:33612345678", O.normaliser("06 12 34 56 78"))
check("1c identité WhatsApp tel: gardée", O.normaliser("tel:33612345678") == "tel:33612345678")
check("1d bsuid gardé", O.normaliser("bsuid:ABC123") == "bsuid:ABC123")
check("1e profil sans / final, minuscules", O.normaliser("https://X.com/Quelqu1/") == "profil:https://x.com/quelqu1",
      O.normaliser("https://X.com/Quelqu1/"))
check("1f vide ou inconnu = None", O.normaliser("") is None and O.normaliser("bonjour") is None and O.normaliser(None) is None)

print("[2] inscrire puis oppose")
check("2a rien d'inscrit au départ", not O.oppose(["jean@exemple.fr"]) and O.compte() == 0)
n = O.inscrire(["Jean@Exemple.fr", "06 12 34 56 78"], "prospect")
check("2b deux empreintes neuves", n == 2 and O.compte() == 2, str(n))
check("2c oppose par l'e-mail, à la casse près", O.oppose(["JEAN@exemple.fr"]))
check("2d oppose par le numéro sous une autre forme", O.oppose(["+33 6 12 34 56 78"]))
check("2e une autre personne n'est pas opposée", not O.oppose(["paul@exemple.fr"]))
check("2f identifiants inconnus ignorés", O.inscrire(["bonjour", ""], "saisie") == 0)

print("[3] jamais en clair, sel stable")
octets = (_tmp / "espaces" / "oppositions.json").read_bytes()
check("3a ni l'adresse ni le numéro dans le fichier",
      b"jean" not in octets.lower() and b"612345678" not in octets and b"exemple" not in octets.lower())
check("3b la même adresse deux fois = une empreinte", O.inscrire(["jean@exemple.fr"], "whatsapp") == 0 and O.compte() == 2)

print("[4] origine inconnue refusée")
try:
    O.inscrire(["x@y.fr"], "pirate"); refuse = False
except ValueError:
    refuse = True
check("4a origine hors liste = ValueError", refuse and not O.oppose(["x@y.fr"]))

print("[5] registre illisible mis de côté")
f = _tmp / "espaces" / "oppositions.json"
f.write_bytes(b"{cass\xc3\xa9")
check("5a lecture = registre vide", O.compte() == 0 and not O.oppose(["jean@exemple.fr"]))
cotes = list(f.parent.glob("oppositions.json.illisible-*"))
check("5b copie mise de côté avec ses octets", len(cotes) == 1 and cotes[0].read_bytes() == b"{cass\xc3\xa9")
O.inscrire(["paul@exemple.fr"], "saisie")
check("5c un registre neuf repart, la copie reste", O.oppose(["paul@exemple.fr"]) and cotes[0].is_file())

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
