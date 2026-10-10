# -*- coding: utf-8 -*-
"""Avatar live G5 (t166, 10/10/2026) — le SERVEUR de référence `tools/voixbox/server.py` (RVC local) parle le contrat
du client : lancé pour de vrai (ThreadingHTTPServer dans un fil) avec un MOTEUR FACTICE à la place de torch, et c'est
le client de l'application (`voix_direct`) qui l'interroge : santé et liste des voix, conversion d'un segment PCM,
refus nommés (modèle inconnu, nom piégé, segment trop long, longueur impaire), panne du moteur -> 500 lisible.
Le module s'importe SANS torch.
Run : & $PY tests/test_voixbox_contrat.py (depuis backend/)"""
import asyncio, importlib.util, os, pathlib, sys, tempfile, threading
from http.server import ThreadingHTTPServer
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzvoixbox_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from loguru import logger
logger.remove()
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

RACINE = pathlib.Path(__file__).resolve().parents[2]
SRC = RACINE / "tools" / "voixbox" / "server.py"
spec = importlib.util.spec_from_file_location("voixbox_server", SRC)
VB = importlib.util.module_from_spec(spec); spec.loader.exec_module(VB)
check("C0 le serveur s'importe SANS torch ni rvc", "torch" not in sys.modules and "rvc" not in sys.modules and hasattr(VB, "fabrique"))
check("C0b licence du moteur dite dans l'en-tête (RVC, MIT ; Seed-VC écarté)", "MIT" in SRC.read_text(encoding="utf-8")
      and "Seed-VC" in SRC.read_text(encoding="utf-8"))

MODELES = _tmp / "voix_rvc"
(MODELES / "oli").mkdir(parents=True)
(MODELES / "oli" / "oli_e200.pth").write_bytes(b"poids")
(MODELES / "oli" / "added_IVF.index").write_bytes(b"index")
(MODELES / "sansindex").mkdir()
(MODELES / "sansindex" / "x.pth").write_bytes(b"p")
(MODELES / "vide").mkdir()
(MODELES / "mauvais nom").mkdir()
(MODELES / "mauvais nom" / "y.pth").write_bytes(b"p")


class Faux:
    gpu = "Fausse RTX"
    def __init__(self, racine): self.racine = racine; self.vus = []; self.panne = False
    def convertir(self, nom, pcm, transpose):
        if self.panne: raise RuntimeError("CUDA a calé")
        self.vus.append((nom, len(pcm), transpose))
        return bytes(b ^ 0xFF for b in pcm)       # une « autre » voix, même longueur


moteur = Faux(MODELES)
srv = ThreadingHTTPServer(("127.0.0.1", 0), VB.fabrique(moteur))
threading.Thread(target=srv.serve_forever, daemon=True).start()

from app.config import settings                                    # noqa: E402
from app.services import voix_direct as VD                          # noqa: E402
settings.VOIXBOX_URL = f"http://127.0.0.1:{srv.server_port}"
VD._nvidia_smi = lambda: "NVIDIA GeForce RTX 2080 Ti, 11264"
VD._GPU.update(t=0.0, v=None)

e = asyncio.run(VD.etat())
check("S1 santé : GPU vu (nom, 11 Go), Voixbox répond, voix entraînées listées avec leur index",
      e["local"]["gpu"] == {"nom": "NVIDIA GeForce RTX 2080 Ti", "memoire_go": 11.0} and e["local"]["voixbox"]
      and e["local"]["modeles"] == [{"nom": "oli", "index": True}, {"nom": "sansindex", "index": False}]
      and e["local"]["disponible"] is True, str(e["local"]))
check("S2 un dossier sans .pth ou au nom hors charte n'est pas une voix",
      all(m["nom"] not in ("vide", "mauvais nom") for m in e["local"]["modeles"]))

pcm = bytes(range(256)) * 125                                       # 32 000 octets = 1 s
out, ms = asyncio.run(VD.convertir_segment({"moteur": "local", "modele": "oli", "transpose": 3}, pcm))
check("V1 un segment d'une seconde : converti, même longueur, latence mesurée, transposition transmise",
      out == bytes(b ^ 0xFF for b in pcm) and ms >= 0 and moteur.vus[-1] == ("oli", 32000, 3), str(moteur.vus[-1:]))


def refus(voix, corps):
    try:
        asyncio.run(VD.convertir_segment(voix, corps)); return None
    except VD.Refus as x:
        return x


x = refus({"moteur": "local", "modele": "inconnu"}, pcm)
check("V2 modèle inconnu : 404 nommé", x is not None and x.statut == 404 and "inconnu" in x.message, str(x and x.message))
x = refus({"moteur": "local", "modele": "..%5Coli"}, pcm)
check("V3 nom piégé : 404, le moteur n'est pas appelé", x is not None and x.statut == 404 and len(moteur.vus) == 1)
moteur.panne = True
x = refus({"moteur": "local", "modele": "oli"}, pcm)
check("V4 panne du moteur : 502 qui la dit (jamais une socket coupée)", x is not None and x.statut == 502 and "CUDA" in x.message, str(x and x.message))
moteur.panne = False
import urllib.request                                               # noqa: E402
def poster(corps, q="modele=oli"):
    r = urllib.request.Request(settings.VOIXBOX_URL + "/convertir?" + q, data=corps, method="POST",
                               headers={"Content-Type": "application/octet-stream"})
    try:
        return urllib.request.urlopen(r).status
    except urllib.error.HTTPError as h:
        return h.code
check("V5 serveur : segment de 11 s refusé (413), longueur impaire refusée (400)",
      poster(b"\x00" * (16000 * 2 * 11)) == 413 and poster(b"\x00" * 3) == 400)
srv.shutdown()
settings.VOIXBOX_URL = "http://127.0.0.1:9"
x = refus({"moteur": "local", "modele": "oli"}, pcm)
check("V6 Voixbox éteint : 503 qui dit comment le lancer", x is not None and x.statut == 503 and "README" in x.message, str(x and x.message))
VD._GPU.update(t=0.0, v=None)
e = asyncio.run(VD.etat())
check("V7 éteint : l'état dit « local indisponible » sans planter", e["local"]["voixbox"] is False and e["local"]["disponible"] is False)

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
