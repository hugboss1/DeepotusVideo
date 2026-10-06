# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T12, D3b) — le SERVEUR de référence `tools/clapbox/server.py` parle le contrat du client :
on le lance pour de vrai (HTTPServer dans un fil) avec un MOTEUR FACTICE à la place de torch, et c'est le client
de l'application (`sound_search`) qui l'interroge — santé, indexation multipart, recherche texte. Vérifié aussi :
le multipart est décodé par le paquet `email` (le `cgi` du plan d'origine n'existe plus en Python 3.13), les octets
arrivent intacts, un nom de fichier hostile est réduit à sa feuille, une erreur du moteur rend un 500 lisible
(le client le traduit en indisponibilité nommée), et le module s'importe SANS torch.
Run: python tests/test_clapbox_contrat.py (depuis backend/)"""
import asyncio, importlib.util, os, pathlib, sys, tempfile, threading
from http.server import HTTPServer
_tmp = tempfile.mkdtemp(prefix="dzclapsrv_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
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
spec = importlib.util.spec_from_file_location("clapbox_server", RACINE / "tools" / "clapbox" / "server.py")
CB = importlib.util.module_from_spec(spec); spec.loader.exec_module(CB)
check("le serveur s'importe SANS torch (le moteur seul le charge)", "torch" not in sys.modules and hasattr(CB, "fabrique"))
check("aucun `import cgi` (retiré de Python 3.13)", "import cgi" not in (RACINE / "tools" / "clapbox" / "server.py").read_text(encoding="utf-8"))

class Faux:
    model, dim = "faux-clap", 3
    def __init__(self): self.vus = []; self.panne = False
    def embed_text(self, texts):
        return [[1.0, 0.0, 0.0] if "grince" in t else [0.0, 0.0, 1.0] for t in texts]
    def embed_audio(self, paths):
        if self.panne: raise RuntimeError("le modèle a calé")
        self.vus += [(p.name, p.read_bytes()) for p in paths]
        return [[1.0, 0.0, 0.0] if "porte" in p.name else [0.0, 1.0, 0.0] for p in paths]
moteur = Faux()
srv = HTTPServer(("127.0.0.1", 0), CB.fabrique(moteur))
threading.Thread(target=srv.serve_forever, daemon=True).start()

from app.config import settings
from app.services import sound_search as SS, sfx_service as S
settings.CLAPBOX_URL = f"http://127.0.0.1:{srv.server_port}"
SS._reach_cache.update(t=0.0, ok=False)
check("santé : le client voit Clapbox (vrai GET /health du serveur de référence)", SS.resolve_embedder() == "clapbox")
audio = S._audio_dir()
OCTETS = {"porte.wav": b"RIFF\x00\x01porte" + bytes(range(256)), "vent.wav": b"RIFF\r\n--vent--\r\n" * 3}
for n, b in OCTETS.items(): (audio / n).write_bytes(b)
r = asyncio.run(SS.reindex())
check("indexation de bout en bout : deux sons, dimension du serveur", r["indexed"] == 2 and r["dim"] == 3 and r["model"] == "faux-clap", str(r))
recus = {n.split("_", 1)[1]: b for n, b in moteur.vus}
check("multipart : les OCTETS arrivent intacts (y compris \\r\\n-- et \\x00)", recus == OCTETS, str({k: len(v) for k, v in recus.items()}))
res = asyncio.run(SS.search("une porte qui grince", k=1))
check("recherche texte de bout en bout : porte.wav", [x["name"] for x in res] == ["porte.wav"], str(res))
corps = (b"--B\r\nContent-Disposition: form-data; name=\"files\"; filename=\"..\\\\..\\\\evil.wav\"\r\n\r\nX\r\n"
         b"--B\r\nContent-Disposition: form-data; name=\"autre\"; filename=\"z.wav\"\r\n\r\nY\r\n--B--\r\n")
lus = CB.lire_multipart(corps, "multipart/form-data; boundary=B")
check("nom hostile réduit à sa feuille, champ étranger ignoré", [n for n, _ in lus] == ["evil.wav"] or
      [n for n, _ in lus] == [pathlib.Path("..\\..\\evil.wav").name], str(lus))
check("corps non multipart : liste vide", CB.lire_multipart(b"x", "application/json") == [])
moteur.panne = True
(audio / "neuf.wav").write_bytes(b"RIFF neuf")
try:
    asyncio.run(SS.reindex()); check("panne du moteur : refus nommé côté client", False)
except SS.SearchUnavailable as e:
    check("panne du moteur : HTTP 500 lisible, traduit en indisponibilité NOMMÉE", "500" in str(e) and "calé" in str(e), str(e))
srv.shutdown()
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
